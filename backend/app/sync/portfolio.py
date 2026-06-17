"""Sincronização da carteira de um vendedor: Ploomes -> espelho local.

Baixa Contacts (clientes PJ), Orders (12m, com itens), Quotes abertas e Deals
abertos do OwnerId, calcula agregados + score de prioridade e grava em lote.
Roda em background (não bloqueia a API). Respeita o rate limit via PloomesClient.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Any, Optional

from sqlalchemy import delete

from app.config import settings
from app.db import session_scope
from app import models
from app.ploomes.client import get_ploomes
from app.ploomes import fields as F
from app.intelligence.scoring import compute_priority
from app.util import (
    days_since, only_digits, parse_frequency_days, parse_segment,
    strip_emoji, to_float, to_int,
)

log = logging.getLogger("portal.sync")

_TERMINAL = {"FATURADO", "ENTREGUE", "CANCELADO", "CONCLUIDO", "CONCLUÍDO",
             "FINALIZADO", "REJEITADO", "REPROVADO"}
_ORDER_STATUS_FK = "order_E001D84F-9B73-4735-B5C2-98C688422D36"   # Status da Nota (Sankhya)
_QUOTE_STATUS_FK = "quote_FABBEA46-3B2C-4141-B5EC-EAF996F7BCC0"   # Status da Nota (Sankhya)

_running: set[int] = set()


def _compute_frequency_days(date_strs: list[str]) -> Optional[int]:
    """Cadência real de compra = mediana dos intervalos entre pedidos.

    Os campos de frequência do Sankhya quase não são preenchidos (e quando são,
    são rótulos vagos). A cadência real vem do espaçamento dos pedidos. Precisa
    de pelo menos 3 compras (2 intervalos) para ser confiável.
    """
    dates: list[dt.date] = []
    for s in date_strs:
        try:
            dates.append(dt.date.fromisoformat(str(s)[:10]))
        except (ValueError, TypeError):
            continue
    dates = sorted(set(dates))
    if len(dates) < 3:
        return None
    gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return None
    import statistics
    return max(1, int(round(statistics.median(gaps))))


# --------------------------------------------------------------------------- #
# estado da sincronização (para a UI)
# --------------------------------------------------------------------------- #
def _set_state(owner_id: int, **kw) -> None:
    with session_scope() as s:
        st = s.get(models.SyncState, owner_id) or models.SyncState(owner_id=owner_id)
        for k, v in kw.items():
            setattr(st, k, v)
        s.merge(st)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# --------------------------------------------------------------------------- #
# parsing de um contato
# --------------------------------------------------------------------------- #
def _phone(contact: dict) -> str:
    for p in contact.get("Phones") or []:
        ph = str(p.get("PhoneNumber") or p.get("Number") or "")
        if ph:
            return ph
    return ""


def _contact_base(c: dict) -> dict:
    seg_code, seg_name = parse_segment(F.get(c, "segmento"))
    city = c.get("City") or {}
    phone = _phone(c)
    return {
        "id": int(c["Id"]),
        "owner_id": int(c.get("OwnerId") or 0),
        "name": strip_emoji(c.get("Name") or "Cliente"),
        "cnpj": str(c.get("Register") or ""),
        "phone": phone,
        "phone_tail": only_digits(phone)[-8:],
        "city": str(city.get("Name") or "") if isinstance(city, dict) else "",
        "segment_code": seg_code,
        "segment_name": seg_name,
        "client_status": strip_emoji(F.get(c, "status_cliente")),
        "lifecycle_status": strip_emoji(F.get(c, "status_lifecycle")),
        "cod_parceiro": str(F.get(c, "cod_parceiro_sankhya") or ""),
        "days_without_purchase": to_int(F.get(c, "dias_sem_compra")),
        "buy_frequency_days": parse_frequency_days(F.get(c, "frequencia_compra")),
        "last_purchase_date": str(F.get(c, "data_ultima_compra") or ""),
    }


def _build_tags(row: dict) -> list[dict]:
    tags: list[dict] = []
    days = row.get("days_without_purchase")
    freq = row.get("buy_frequency_days")
    if days is not None:
        overdue = bool(freq and days / freq >= settings.reactivation_factor)
        tags.append({"l": f"{days}d sem comprar",
                     "k": "warn" if (overdue or days >= 45) else "info"})
    if row.get("open_quotes"):
        tags.append({"l": f"{row['open_quotes']} cotação aberta", "k": "value"})
    if row.get("open_deals"):
        tags.append({"l": f"{row['open_deals']} negócio aberto", "k": "value"})
    if row.get("segment_name"):
        tags.append({"l": row["segment_name"], "k": "seg"})
    st = (row.get("client_status") or "").lower()
    if any(x in st for x in ("inativ", "bloque", "suspens")):
        tags.append({"l": row["client_status"], "k": "danger"})
    return tags


# --------------------------------------------------------------------------- #
# coletas no Ploomes
# --------------------------------------------------------------------------- #
def _status_nota(rec: dict, fk: str) -> str:
    return strip_emoji(F.value_by_key(rec, fk))


def _is_open(status: str) -> bool:
    return status.strip().upper() not in _TERMINAL


async def _fetch_contacts(pl, owner_id: int) -> list[dict]:
    return await pl.get_all("/Contacts", {
        "$filter": f"TypeId eq 1 and OwnerId eq {owner_id}",
        "$expand": "OtherProperties,Phones,City",
        "$orderby": "Name",
    }, page=settings.portfolio_sync_page_size, max_pages=settings.portfolio_sync_max_pages)


async def _fetch_orders(pl, owner_id: int) -> list[dict]:
    cutoff = (dt.date.today() - dt.timedelta(days=540)).isoformat()  # ~18 meses
    return await pl.get_all("/Orders", {
        "$filter": f"OwnerId eq {owner_id} and Date ge {cutoff}T00:00:00-03:00",
        "$orderby": "Date desc",
        "$expand": "Products,OtherProperties",
    }, page=100, max_pages=settings.portfolio_sync_max_pages)


async def _fetch_quotes(pl, owner_id: int) -> list[dict]:
    return await pl.get_all("/Quotes", {
        "$filter": f"OwnerId eq {owner_id} and LastReview eq true",
        "$orderby": "Date desc",
        "$expand": "OtherProperties",
    }, page=100, max_pages=settings.portfolio_sync_max_pages)


async def _fetch_deals(pl, owner_id: int) -> list[dict]:
    return await pl.get_all("/Deals", {
        "$filter": f"OwnerId eq {owner_id} and StatusId eq 1",
        "$select": "Id,ContactId,Amount,StageId,DaysInStage",
        "$orderby": "LastUpdateDate desc",
    }, page=100, max_pages=settings.portfolio_sync_max_pages)


# --------------------------------------------------------------------------- #
# orquestração
# --------------------------------------------------------------------------- #
async def sync_owner(owner_id: int) -> dict:
    pl = get_ploomes()
    if pl is None:
        _set_state(owner_id, status="error", message="Ploomes não configurado",
                   finished_at=_now())
        return {"ok": False, "error": "ploomes_not_configured"}

    _set_state(owner_id, status="running", message="Sincronizando…",
               started_at=_now(), finished_at=None, total=0, synced=0)
    try:
        contacts_raw = await _fetch_contacts(pl, owner_id)
        _set_state(owner_id, total=len(contacts_raw), synced=0,
                   message=f"{len(contacts_raw)} clientes — buscando pedidos/cotações…")
        orders_raw = await _fetch_orders(pl, owner_id)
        quotes_raw = await _fetch_quotes(pl, owner_id)
        deals_raw = await _fetch_deals(pl, owner_id)

        rows = [_contact_base(c) for c in contacts_raw if c.get("Id")]
        seg_by_contact = {r["id"]: r["segment_name"] for r in rows}

        # ---- agregados de pedidos (12m) + itens p/ cross-sell ----
        order_rows: list[dict] = []
        item_rows: list[dict] = []
        agg_orders: dict[int, dict] = {}
        for o in orders_raw:
            cid = to_int(o.get("ContactId"))
            if not cid:
                continue
            amount = to_float(o.get("Amount"))
            date = str(o.get("Date") or "")
            status = _status_nota(o, _ORDER_STATUS_FK)
            order_rows.append({
                "id": int(o["Id"]), "owner_id": owner_id, "contact_id": cid,
                "order_number": str(o.get("OrderNumber") or ""),
                "date": date, "amount": amount, "status_nota": status,
            })
            a = agg_orders.setdefault(
                cid, {"rev": 0.0, "n": 0, "last_d": "", "last_v": 0.0, "dates": []})
            a["rev"] += amount
            a["n"] += 1
            if date:
                a["dates"].append(date)
            if date > a["last_d"]:
                a["last_d"], a["last_v"] = date, amount
            for it in o.get("Products") or []:
                item_rows.append({
                    "order_id": int(o["Id"]), "owner_id": owner_id, "contact_id": cid,
                    "segment_name": seg_by_contact.get(cid, ""),
                    "product_id": to_int(it.get("ProductId")),
                    "product_name": str(it.get("ProductName") or "")[:240],
                    "quantity": to_float(it.get("Quantity")),
                    "total": to_float(it.get("Total")),
                    "date": date,
                })

        # ---- cotações abertas ----
        quote_rows: list[dict] = []
        agg_quotes: dict[int, dict] = {}
        for q in quotes_raw:
            cid = to_int(q.get("ContactId"))
            if not cid:
                continue
            status = _status_nota(q, _QUOTE_STATUS_FK)
            if not _is_open(status):
                continue
            amount = to_float(q.get("Amount"))
            quote_rows.append({
                "id": int(q["Id"]), "owner_id": owner_id, "contact_id": cid,
                "date": str(q.get("Date") or ""), "amount": amount, "status_nota": status,
            })
            b = agg_quotes.setdefault(cid, {"n": 0, "v": 0.0})
            b["n"] += 1
            b["v"] += amount

        # ---- negócios abertos ----
        agg_deals: dict[int, dict] = {}
        for d in deals_raw:
            cid = to_int(d.get("ContactId"))
            if not cid:
                continue
            e = agg_deals.setdefault(cid, {"n": 0, "v": 0.0})
            e["n"] += 1
            e["v"] += to_float(d.get("Amount"))

        # ---- montar linhas finais de contato ----
        final_contacts: list[dict] = []
        for r in rows:
            cid = r["id"]
            ao = agg_orders.get(cid, {})
            aq = agg_quotes.get(cid, {})
            ad = agg_deals.get(cid, {})
            r["revenue_12m"] = round(ao.get("rev", 0.0), 2)
            r["orders_12m"] = ao.get("n", 0)
            r["last_order_date"] = ao.get("last_d", "")
            r["last_order_value"] = ao.get("last_v", 0.0)
            r["open_quotes"] = aq.get("n", 0)
            r["open_quotes_value"] = round(aq.get("v", 0.0), 2)
            r["open_deals"] = ad.get("n", 0)
            r["open_deals_value"] = round(ad.get("v", 0.0), 2)

            # --- recência: preferir o pedido real (fresco); senão o campo Sankhya ---
            computed_days = days_since(r["last_order_date"]) if r["last_order_date"] else None
            sankhya_days = r["days_without_purchase"]
            r["days_without_purchase"] = (
                computed_days if computed_days is not None else sankhya_days)

            # --- frequência: calcular do histórico real (Sankhya é inútil aqui) ---
            computed_freq = _compute_frequency_days(ao.get("dates", []))
            if computed_freq is not None:
                r["buy_frequency_days"] = computed_freq
            # (se não houver ≥3 pedidos, mantém o que veio do Sankhya, que costuma ser None)

            r["priority_score"] = compute_priority(r)
            r["tags"] = _build_tags(r)
            r["synced_at"] = _now()
            final_contacts.append(r)

        _write_owner(owner_id, final_contacts, order_rows, item_rows, quote_rows)
        _set_state(owner_id, status="ok", synced=len(final_contacts),
                   message=f"{len(final_contacts)} clientes sincronizados",
                   finished_at=_now())
        log.info("sync owner %s: %d contatos, %d pedidos, %d cotações abertas",
                 owner_id, len(final_contacts), len(order_rows), len(quote_rows))
        return {"ok": True, "contacts": len(final_contacts),
                "orders": len(order_rows), "open_quotes": len(quote_rows)}
    except Exception as e:  # noqa: BLE001
        log.exception("sync falhou owner %s", owner_id)
        _set_state(owner_id, status="error", message=str(e)[:300], finished_at=_now())
        return {"ok": False, "error": str(e)}


def _write_owner(owner_id: int, contacts: list[dict], orders: list[dict],
                 items: list[dict], quotes: list[dict]) -> None:
    """Substitui todos os dados do vendedor em uma transação."""
    with session_scope() as s:
        for model in (models.OrderItem, models.Order, models.Quote, models.Contact):
            s.execute(delete(model).where(model.owner_id == owner_id))
        s.bulk_insert_mappings(models.Contact, contacts)
        if orders:
            s.bulk_insert_mappings(models.Order, orders)
        if items:
            s.bulk_insert_mappings(models.OrderItem, items)
        if quotes:
            s.bulk_insert_mappings(models.Quote, quotes)


# --------------------------------------------------------------------------- #
# disparo em background
# --------------------------------------------------------------------------- #
def schedule_sync(owner_id: int) -> bool:
    """Dispara o sync em background; False se já estiver rodando."""
    if owner_id in _running:
        return False
    _running.add(owner_id)

    async def _run() -> None:
        try:
            await sync_owner(owner_id)
        finally:
            _running.discard(owner_id)

    asyncio.create_task(_run())
    return True


def is_running(owner_id: int) -> bool:
    return owner_id in _running
