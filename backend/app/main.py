"""Portal de Inteligência de Carteira — API (FastAPI).

Fase 1: fundação (Ploomes + espelho + sync + inteligência).
Fase 2: auth (vendedor/admin) + cockpit (KPIs + fila priorizada + alertas).
v1 é READ-ONLY no Ploomes.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session, init_db
from app import models
from app.intelligence.alerts import alerts_for_contact, build_alerts
from app.intelligence.messages import (
    build_crosssell_message, build_insights, build_messages, reactivation_message,
)
from app.ploomes.client import close_ploomes, get_ploomes
from app.security import (
    create_token, current_user, hash_password, require_admin, resolve_owner_id,
    seed_admin, verify_password,
)
from app.sync import portfolio as sync

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("portal")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_admin()
    log.info("Pronto. Ploomes configurado: %s | admin: %s",
             settings.ploomes_configured, settings.portal_admin_email)
    yield
    await close_ploomes()


app = FastAPI(title="Portal de Inteligência de Carteira", version="0.2.0",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


# ===========================================================================
# AUTH
# ===========================================================================
class LoginIn(BaseModel):
    email: str
    password: str


class SellerOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    owner_id: Optional[int] = None


def _seller_out(u: models.Seller) -> SellerOut:
    return SellerOut(id=u.id, name=u.name, email=u.email, role=u.role,
                     owner_id=u.ploomes_owner_id)


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_session)) -> dict:
    user = db.query(models.Seller).filter(
        func.lower(models.Seller.email) == body.email.lower().strip()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos")
    if not user.active:
        raise HTTPException(403, "Usuário inativo")
    return {"token": create_token(user), "user": _seller_out(user).model_dump()}


@app.get("/api/auth/me")
def me(user: models.Seller = Depends(current_user)) -> dict:
    return _seller_out(user).model_dump()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "ploomes_configured": settings.ploomes_configured}


# ===========================================================================
# ADMIN — vendedores do Ploomes e contas do portal
# ===========================================================================
@app.get("/api/ploomes/users")
async def ploomes_users(_: models.Seller = Depends(require_admin)) -> dict:
    pl = get_ploomes()
    if pl is None:
        raise HTTPException(503, "Ploomes não configurado")
    users = await pl.users()
    return {"users": [{"id": u.get("Id"), "name": u.get("Name"),
                       "email": u.get("Email")} for u in users]}


class SellerIn(BaseModel):
    name: str
    email: str
    password: str
    ploomes_owner_id: Optional[int] = None
    role: str = "seller"


@app.get("/api/admin/sellers")
def list_sellers(db: Session = Depends(get_session),
                 _: models.Seller = Depends(require_admin)) -> dict:
    rows = db.scalars(select(models.Seller)).all()
    return {"sellers": [_seller_out(u).model_dump() for u in rows]}


@app.post("/api/admin/sellers")
def create_seller(body: SellerIn, db: Session = Depends(get_session),
                  _: models.Seller = Depends(require_admin)) -> dict:
    role = body.role if body.role in ("seller", "admin") else "seller"
    if role == "seller" and not body.ploomes_owner_id:
        raise HTTPException(400, "Vendedor precisa estar vinculado a um vendedor do Ploomes")
    if db.query(models.Seller).filter(
            func.lower(models.Seller.email) == body.email.lower()).first():
        raise HTTPException(409, "E-mail já cadastrado")
    owner = int(body.ploomes_owner_id) if (role == "seller" and body.ploomes_owner_id) else None
    if owner is not None and db.query(models.Seller).filter_by(ploomes_owner_id=owner).first():
        raise HTTPException(409, "Já existe um usuário vinculado a esse vendedor do Ploomes")
    u = models.Seller(name=body.name, email=body.email.lower().strip(),
                      password_hash=hash_password(body.password),
                      ploomes_owner_id=owner, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return _seller_out(u).model_dump()


class PasswordIn(BaseModel):
    password: str


@app.post("/api/admin/sellers/{seller_id}/password")
def set_seller_password(seller_id: int, body: PasswordIn,
                        db: Session = Depends(get_session),
                        _: models.Seller = Depends(require_admin)) -> dict:
    u = db.get(models.Seller, seller_id)
    if u is None:
        raise HTTPException(404, "Usuário não encontrado")
    if len((body.password or "").strip()) < 4:
        raise HTTPException(422, "A senha precisa ter ao menos 4 caracteres")
    u.password_hash = hash_password(body.password.strip())
    db.commit()
    return {"ok": True, "id": u.id}


# ===========================================================================
# SYNC
# ===========================================================================
@app.post("/api/sync")
async def trigger_sync(owner_id: Optional[int] = None,
                       user: models.Seller = Depends(current_user)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    started = sync.schedule_sync(oid)
    return {"owner_id": oid, "started": started, "running": sync.is_running(oid)}


@app.get("/api/sync")
def sync_status(owner_id: Optional[int] = None,
                user: models.Seller = Depends(current_user),
                db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    st = db.get(models.SyncState, oid)
    if st is None:
        return {"owner_id": oid, "status": "idle", "running": sync.is_running(oid)}
    return {"owner_id": oid, "status": st.status, "message": st.message,
            "total": st.total, "synced": st.synced, "running": sync.is_running(oid),
            "started_at": st.started_at, "finished_at": st.finished_at}


# ===========================================================================
# CARTEIRA + ALERTAS + COCKPIT
# ===========================================================================
def _contact_dto(c: models.Contact) -> dict:
    return {
        "id": c.id, "name": c.name, "cnpj": c.cnpj, "phone": c.phone,
        "city": c.city, "segment": c.segment_name, "status": c.client_status,
        "days_without_purchase": c.days_without_purchase,
        "buy_frequency_days": c.buy_frequency_days,
        "last_order_date": c.last_order_date, "revenue_12m": c.revenue_12m,
        "orders_12m": c.orders_12m,
        "open_quotes": c.open_quotes, "open_quotes_value": c.open_quotes_value,
        "open_deals": c.open_deals, "open_deals_value": c.open_deals_value,
        "priority_score": c.priority_score, "tags": c.tags,
    }


_SORTS = {
    "score": models.Contact.priority_score.desc(),
    "revenue": models.Contact.revenue_12m.desc(),
    "days": models.Contact.days_without_purchase.desc().nullslast(),
    "name": models.Contact.name.asc(),
    "quotes": models.Contact.open_quotes_value.desc(),
}


@app.get("/api/portfolio")
def portfolio(owner_id: Optional[int] = None, offset: int = 0,
              limit: int = Query(50, le=200), q: Optional[str] = None,
              sort: str = "score", filter: str = "all",
              segment: Optional[str] = None,
              user: models.Seller = Depends(current_user),
              db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    C = models.Contact
    stmt = select(C).where(C.owner_id == oid)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(C.name).like(like) | C.cnpj.like(f"%{q}%"))
    if segment:
        stmt = stmt.where(C.segment_name == segment)
    if filter == "open_quotes":
        stmt = stmt.where(C.open_quotes > 0)
    elif filter == "inactive":
        stmt = stmt.where(func.lower(C.client_status).like("inativ%")
                          | func.lower(C.client_status).like("bloque%")
                          | func.lower(C.client_status).like("suspens%"))
    elif filter == "overdue":
        # passou de 45 dias (aprox.; o ratio fino é refinado no front/cockpit)
        stmt = stmt.where(C.days_without_purchase >= 45)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = _SORTS.get(sort, _SORTS["score"])
    rows = db.scalars(stmt.order_by(order).offset(offset).limit(limit)).all()
    return {"total": total, "offset": offset, "limit": limit,
            "items": [_contact_dto(c) for c in rows]}


@app.get("/api/portfolio/segments")
def portfolio_segments(owner_id: Optional[int] = None,
                       user: models.Seller = Depends(current_user),
                       db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    rows = db.execute(
        select(models.Contact.segment_name, func.count())
        .where(models.Contact.owner_id == oid, models.Contact.segment_name != "")
        .group_by(models.Contact.segment_name)
        .order_by(func.count().desc())
    ).all()
    return {"segments": [{"name": r[0], "count": r[1]} for r in rows]}


@app.get("/api/contact/{contact_id}")
def contact_detail(contact_id: int, owner_id: Optional[int] = None,
                   user: models.Seller = Depends(current_user),
                   db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    c = db.get(models.Contact, contact_id)
    if c is None or c.owner_id != oid:
        raise HTTPException(404, "Cliente não encontrado nesta carteira")

    orders = db.scalars(
        select(models.Order).where(models.Order.contact_id == contact_id)
        .order_by(models.Order.date.desc()).limit(50)).all()
    quotes = db.scalars(
        select(models.Quote).where(models.Quote.contact_id == contact_id)
        .order_by(models.Quote.date.desc()).limit(50)).all()
    top = db.execute(
        select(models.OrderItem.product_name,
               func.sum(models.OrderItem.quantity),
               func.sum(models.OrderItem.total),
               func.count())
        .where(models.OrderItem.contact_id == contact_id,
               models.OrderItem.product_name != "")
        .group_by(models.OrderItem.product_name)
        .order_by(func.sum(models.OrderItem.total).desc()).limit(8)).all()

    dto = _contact_dto(c)
    top_products = [{"product_name": r[0], "quantity": float(r[1] or 0),
                     "total": float(r[2] or 0), "orders": r[3]} for r in top]
    return {
        "contact": dto,
        "insights": build_insights(dto, top_products),
        "messages": build_messages(dto, top_products),
        "alerts": alerts_for_contact(c),
        "orders": [{"id": o.id, "date": o.date, "order_number": o.order_number,
                    "amount": o.amount, "status_nota": o.status_nota} for o in orders],
        "quotes": [{"id": qt.id, "date": qt.date, "amount": qt.amount,
                    "status_nota": qt.status_nota} for qt in quotes],
        "top_products": top_products,
    }


_INTERACTION_KINDS = {
    "anotacao": "Anotação",
    "ligacao": "Ligação",
    "whatsapp": "WhatsApp",
    "email": "E-mail",
    "visita": "Visita/Reunião",
}


class InteractionIn(BaseModel):
    kind: str = "anotacao"
    content: str
    title: Optional[str] = None
    deal_id: Optional[int] = None   # se vier, anexa a interação ao card do deal


class DealIn(BaseModel):
    title: Optional[str] = None
    amount: float = 0.0


def _require_owned_contact(db: Session, contact_id: int, oid: int) -> models.Contact:
    c = db.get(models.Contact, contact_id)
    if c is None or c.owner_id != oid:
        raise HTTPException(404, "Cliente não encontrado nesta carteira")
    return c


@app.get("/api/contact/{contact_id}/interactions")
async def list_interactions(contact_id: int, owner_id: Optional[int] = None,
                            user: models.Seller = Depends(current_user),
                            db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    _require_owned_contact(db, contact_id, oid)
    pl = get_ploomes()
    if pl is None:
        raise HTTPException(503, "Ploomes não configurado")
    rows = await pl.interactions_for_contact(contact_id)
    items = [{"id": r.get("Id"), "date": r.get("Date"), "type_id": r.get("TypeId"),
              "title": r.get("Title"), "content": r.get("Content")} for r in rows]
    return {"contact_id": contact_id, "items": items}


@app.post("/api/contact/{contact_id}/interactions", status_code=201)
async def add_interaction(contact_id: int, body: InteractionIn,
                          owner_id: Optional[int] = None,
                          user: models.Seller = Depends(current_user),
                          db: Session = Depends(get_session)) -> dict:
    """Registra uma interação no cliente (escreve no Ploomes)."""
    import datetime as _dt

    oid = resolve_owner_id(user, owner_id)
    _require_owned_contact(db, contact_id, oid)
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(422, "Escreva o conteúdo da interação")

    pl = get_ploomes()
    if pl is None:
        raise HTTPException(503, "Ploomes não configurado")

    kind_label = _INTERACTION_KINDS.get(body.kind, "Anotação")
    # categoriza no texto (TypeId=1 = anotação, o mesmo que o CRM usa)
    prefix = "" if body.kind == "anotacao" else f"[{kind_label}] "
    title = (body.title or "").strip() or f"{kind_label} — {user.name}"
    now = _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    payload = {
        "ContactId": contact_id, "TypeId": 1,
        "Title": title[:200], "Content": f"{prefix}{content}",
        "Date": now,
    }
    if body.deal_id:
        payload["DealId"] = int(body.deal_id)
    try:
        created = await pl.create_interaction(payload)
    except Exception as e:  # noqa: BLE001
        log.exception("falha ao criar interação contato %s", contact_id)
        raise HTTPException(502, f"Não foi possível registrar no Ploomes: {e}")
    return {"ok": True, "id": created.get("Id"),
            "registered_by": user.name, "kind": kind_label}


_DEAL_STATUS = {1: "Aberto", 2: "Ganho", 3: "Perdido"}


@app.get("/api/contact/{contact_id}/deals")
async def contact_deals(contact_id: int, owner_id: Optional[int] = None,
                        user: models.Seller = Depends(current_user),
                        db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    _require_owned_contact(db, contact_id, oid)
    pl = get_ploomes()
    if pl is None:
        raise HTTPException(503, "Ploomes não configurado")
    rows = await pl.deals_for_contact(contact_id)
    items = []
    for d in rows:
        stage = (d.get("Stage") or {}).get("Name") if isinstance(d.get("Stage"), dict) else ""
        items.append({"id": d.get("Id"), "title": d.get("Title") or "Negócio",
                      "amount": float(d.get("Amount") or 0),
                      "stage": stage or "—",
                      "status": _DEAL_STATUS.get(d.get("StatusId"), "Aberto")})
    return {"contact_id": contact_id, "items": items}


@app.post("/api/contact/{contact_id}/deals", status_code=201)
async def create_contact_deal(contact_id: int, body: DealIn,
                              owner_id: Optional[int] = None,
                              user: models.Seller = Depends(current_user),
                              db: Session = Depends(get_session)) -> dict:
    """Cria um negócio no funil 'Entradas e Prospecção' (escreve no Ploomes)."""
    oid = resolve_owner_id(user, owner_id)
    c = _require_owned_contact(db, contact_id, oid)
    pl = get_ploomes()
    if pl is None:
        raise HTTPException(503, "Ploomes não configurado")

    pid, stage_id = await pl.intake_stage(settings.intake_pipeline_name)
    if stage_id is None:
        raise HTTPException(502, f"Funil '{settings.intake_pipeline_name}' "
                                 "ou seu estágio inicial não encontrado no Ploomes")
    title = (body.title or "").strip() or f"{c.name} — {settings.intake_pipeline_name}"
    payload = {
        "Title": title[:200], "ContactId": contact_id, "OwnerId": oid,
        "StageId": stage_id, "Amount": float(body.amount or 0),
    }
    try:
        created = await pl.create_deal(payload)
    except Exception as e:  # noqa: BLE001
        log.exception("falha ao criar deal contato %s", contact_id)
        raise HTTPException(502, f"Não foi possível criar o negócio no Ploomes: {e}")
    return {"ok": True, "id": created.get("Id"), "stage_id": stage_id}


@app.get("/api/alerts")
def alerts(owner_id: Optional[int] = None,
           user: models.Seller = Depends(current_user),
           db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    rows = db.scalars(select(models.Contact).where(
        models.Contact.owner_id == oid)).all()
    return build_alerts(rows)


@app.get("/api/cockpit")
def cockpit(owner_id: Optional[int] = None, top: int = Query(20, le=100),
            user: models.Seller = Depends(current_user),
            db: Session = Depends(get_session)) -> dict:
    """Tudo que a tela 'Hoje' precisa numa chamada: KPIs + fila + alertas."""
    oid = resolve_owner_id(user, owner_id)
    C = models.Contact
    all_rows = db.scalars(select(C).where(C.owner_id == oid)).all()

    total = len(all_rows)
    open_q = sum(c.open_quotes for c in all_rows)
    open_q_val = sum(c.open_quotes_value for c in all_rows)
    open_deals_val = sum(c.open_deals_value for c in all_rows)
    revenue_12m = sum(c.revenue_12m for c in all_rows)
    inactive = sum(1 for c in all_rows
                   if (c.client_status or "").lower().startswith(("inativ", "bloque", "suspens")))

    def overdue(c: models.Contact) -> bool:
        d, f = c.days_without_purchase, c.buy_frequency_days
        if d is None:
            return False
        if f:
            return d / f >= settings.reactivation_factor
        return d >= 45

    overdue_n = sum(1 for c in all_rows if overdue(c))
    # dinheiro na mesa estimado = cotações abertas + recompra esperada de quem estourou frequência
    queue = sorted(all_rows, key=lambda c: c.priority_score, reverse=True)[:top]
    al = build_alerts(all_rows)

    st = db.get(models.SyncState, oid)
    return {
        "owner_id": oid,
        "kpis": {
            "clients": total,
            "open_quotes": open_q,
            "open_quotes_value": round(open_q_val, 2),
            "open_deals_value": round(open_deals_val, 2),
            "revenue_12m": round(revenue_12m, 2),
            "overdue": overdue_n,
            "inactive": inactive,
            "alerts": al["count"],
        },
        "alerts": al["alerts"][:top],
        "alerts_by_kind": al["by_kind"],
        "queue": [_contact_dto(c) for c in queue],
        "sync": {"status": st.status if st else "idle",
                 "finished_at": st.finished_at if st else None,
                 "running": sync.is_running(oid)},
    }


# ===========================================================================
# FASE 4 — INATIVOS & REATIVAÇÃO
# ===========================================================================
_INACTIVE_PREFIX = ("inativ", "bloque", "suspens")


def _risk_bucket(c: models.Contact) -> Optional[tuple[str, str, float]]:
    """Classifica o risco do cliente. Retorna (bucket, motivo, urgência 0-1) ou None."""
    st = (c.client_status or "").lower()
    d, f = c.days_without_purchase, c.buy_frequency_days
    if any(st.startswith(p) for p in _INACTIVE_PREFIX) and c.revenue_12m > 0:
        return ("inactive", f"Status comercial: {c.client_status}", 0.9)
    if d is not None and f:
        ratio = d / f
        if ratio >= settings.reactivation_factor:
            urg = min(1.0, ratio / 3)
            return ("overdue", f"{d} dias sem comprar (ciclo ~{f}d)", urg)
    if d is not None and d >= 90 and not f:
        return ("cold", f"{d} dias sem comprar", min(1.0, d / 365))
    return None


@app.get("/api/reactivation")
def reactivation(owner_id: Optional[int] = None, bucket: str = "all",
                 offset: int = 0, limit: int = Query(40, le=200),
                 user: models.Seller = Depends(current_user),
                 db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    rows = db.scalars(select(models.Contact).where(
        models.Contact.owner_id == oid)).all()

    flagged = []
    by_bucket: dict[str, int] = {}
    revenue_at_risk = 0.0
    for c in rows:
        r = _risk_bucket(c)
        if not r:
            continue
        bk, reason, urg = r
        by_bucket[bk] = by_bucket.get(bk, 0) + 1
        revenue_at_risk += c.revenue_12m
        # potencial de recuperação: histórico ponderado pela urgência
        potential = c.revenue_12m * (0.5 + urg)
        flagged.append((potential, bk, reason, c))

    flagged.sort(key=lambda t: t[0], reverse=True)
    if bucket != "all":
        flagged = [t for t in flagged if t[1] == bucket]

    total = len(flagged)
    page = flagged[offset:offset + limit]
    items = []
    for potential, bk, reason, c in page:
        dto = _contact_dto(c)
        items.append({**dto, "bucket": bk, "reason": reason,
                      "potential": round(potential, 2),
                      "message": reactivation_message(dto)})

    return {"owner_id": oid, "total": total, "offset": offset, "limit": limit,
            "kpis": {"at_risk": len(rows) and sum(by_bucket.values()),
                     "revenue_at_risk": round(revenue_at_risk, 2),
                     "by_bucket": by_bucket},
            "items": items}


# ===========================================================================
# FASE 5 — OPORTUNIDADES / CROSS-SELL POR RAMO
# ===========================================================================
@app.get("/api/opportunities")
def opportunities(owner_id: Optional[int] = None,
                  user: models.Seller = Depends(current_user),
                  db: Session = Depends(get_session)) -> dict:
    oid = resolve_owner_id(user, owner_id)
    OI = models.OrderItem

    # 1) produtos campeões por ramo (na carteira deste vendedor)
    seg_rows = db.execute(
        select(OI.segment_name, OI.product_name,
               func.sum(OI.total), func.count(func.distinct(OI.contact_id)))
        .where(OI.owner_id == oid, OI.segment_name != "", OI.product_name != "")
        .group_by(OI.segment_name, OI.product_name)
    ).all()
    seg_map: dict[str, list[dict]] = {}
    for seg, prod, total, buyers in seg_rows:
        seg_map.setdefault(seg, []).append(
            {"product_name": prod, "total": float(total or 0), "buyers": buyers})
    for seg in seg_map:
        seg_map[seg].sort(key=lambda p: p["total"], reverse=True)
    segments = sorted(
        ({"segment": s, "top_products": p[:6],
          "total": round(sum(x["total"] for x in p), 2)} for s, p in seg_map.items()),
        key=lambda x: x["total"], reverse=True)[:10]

    # 2) o que cada cliente já compra
    bought_rows = db.execute(
        select(OI.contact_id, OI.product_name)
        .where(OI.owner_id == oid, OI.product_name != "").distinct()).all()
    bought: dict[int, set] = {}
    for cid, prod in bought_rows:
        bought.setdefault(cid, set()).add(prod)

    # 3) cross-sell: clientes que NÃO levam o campeão do seu ramo
    contacts = db.scalars(
        select(models.Contact).where(models.Contact.owner_id == oid,
                                     models.Contact.segment_name != "")
        .order_by(models.Contact.revenue_12m.desc())).all()
    cross = []
    for c in contacts:
        champs = seg_map.get(c.segment_name)
        if not champs:
            continue
        have = bought.get(c.id, set())
        missing = [p["product_name"] for p in champs[:8] if p["product_name"] not in have][:3]
        if not missing:
            continue
        cross.append({
            "contact_id": c.id, "name": c.name, "phone": c.phone,
            "segment": c.segment_name, "revenue_12m": c.revenue_12m,
            "priority_score": c.priority_score, "recommend": missing,
            "message": build_crosssell_message(c.name, c.segment_name, missing[0]),
        })
        if len(cross) >= 100:
            break

    return {"owner_id": oid, "segments": segments,
            "cross_sell": cross,
            "meta": {"cross_sell_capped": len(cross) >= 100}}


# ===========================================================================
# FASE 6 — ADMIN: VISÃO DO TODO
# ===========================================================================
@app.get("/api/admin/overview")
async def admin_overview(db: Session = Depends(get_session),
                         _: models.Seller = Depends(require_admin)) -> dict:
    C = models.Contact
    inactive_case = case(
        (func.lower(C.client_status).like("inativ%"), 1),
        (func.lower(C.client_status).like("bloque%"), 1),
        (func.lower(C.client_status).like("suspens%"), 1),
        else_=0)
    overdue_case = case((C.days_without_purchase >= 45, 1), else_=0)

    rows = db.execute(
        select(C.owner_id, func.count(), func.sum(C.revenue_12m),
               func.sum(C.open_quotes_value), func.sum(C.open_deals_value),
               func.sum(C.open_quotes), func.sum(inactive_case),
               func.sum(overdue_case))
        .group_by(C.owner_id)).all()

    # nomes dos vendedores
    names: dict[int, str] = {}
    pl = get_ploomes()
    if pl is not None:
        try:
            for u in await pl.users():
                names[u.get("Id")] = u.get("Name") or str(u.get("Id"))
        except Exception:  # noqa: BLE001
            pass

    sellers = []
    tot = {"clients": 0, "revenue_12m": 0.0, "money_on_table": 0.0,
           "open_quotes_value": 0.0, "open_deals_value": 0.0,
           "inactive": 0, "overdue": 0}
    for (own, cnt, rev, oqv, odv, oq, inact, over) in rows:
        rev, oqv, odv = float(rev or 0), float(oqv or 0), float(odv or 0)
        mot = oqv + odv
        sellers.append({
            "owner_id": own, "name": names.get(own, f"Vendedor {own}"),
            "clients": cnt, "revenue_12m": round(rev, 2),
            "open_quotes": int(oq or 0), "open_quotes_value": round(oqv, 2),
            "open_deals_value": round(odv, 2), "money_on_table": round(mot, 2),
            "inactive": int(inact or 0), "overdue": int(over or 0),
        })
        tot["clients"] += cnt
        tot["revenue_12m"] += rev
        tot["money_on_table"] += mot
        tot["open_quotes_value"] += oqv
        tot["open_deals_value"] += odv
        tot["inactive"] += int(inact or 0)
        tot["overdue"] += int(over or 0)

    sellers.sort(key=lambda s: s["money_on_table"], reverse=True)
    for k in ("revenue_12m", "money_on_table", "open_quotes_value", "open_deals_value"):
        tot[k] = round(tot[k], 2)
    return {"totals": tot, "sellers": sellers}


# ===========================================================================
# FRONTEND (produção): serve o build do React + fallback de SPA.
# Em dev o front roda no Vite (5173) com proxy; aqui é para o deploy num
# serviço só (Railway). Definido por ÚLTIMO para não capturar as rotas /api.
# ===========================================================================
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
    log.info("Frontend servido de %s", _FRONTEND_DIST)
else:
    log.info("Frontend dist não encontrado (%s) — rodando só API (modo dev).",
             _FRONTEND_DIST)
