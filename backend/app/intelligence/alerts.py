"""Alertas proativos — "o que precisa de ação agora", sem chamada extra ao Ploomes.

Tipos (v1, sobre o espelho da carteira):
  - reactivation : passou do ciclo habitual de compra (frequência estourada)
  - overdue      : muitos dias sem comprar (quando não há frequência conhecida)
  - open_quote   : cotação aberta parada — dar sequência (dinheiro na mesa)
  - inactive     : cliente que comprava e está inativo/bloqueado
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.util import norm

Severity = str  # "high" | "med"


def _money(v: float) -> str:
    return f"R$ {v:,.0f}".replace(",", ".")


def alerts_for_contact(c: Any) -> list[dict]:
    """Gera alertas de um contato (ORM Contact ou dict-like)."""
    g = (lambda k, d=None: getattr(c, k, d)) if not isinstance(c, dict) else (lambda k, d=None: c.get(k, d))
    out: list[dict] = []

    days = g("days_without_purchase")
    freq = g("buy_frequency_days")
    status = norm(g("client_status"))
    rev = float(g("revenue_12m") or 0)
    base = {"contact_id": g("id") or g("contact_id"), "name": g("name"),
            "score": g("priority_score") or 0}

    # 1) Reativação — passou do ciclo habitual
    if days is not None and freq:
        ratio = days / freq if freq else 0
        if ratio >= settings.reactivation_factor:
            out.append({**base, "kind": "reactivation",
                        "severity": "high" if ratio >= 2 else "med",
                        "title": f"{days} dias sem comprar (costuma comprar a cada ~{freq}d)",
                        "detail": "Passou do ciclo — cliente pode estar esfriando."})
    # 2) Atraso sem frequência conhecida
    elif days is not None and days >= 45:
        out.append({**base, "kind": "overdue",
                    "severity": "high" if days >= 90 else "med",
                    "title": f"{days} dias sem comprar",
                    "detail": "Sem compra recente — vale um contato."})

    # 3) Cotação aberta parada
    oq = int(g("open_quotes") or 0)
    if oq:
        val = float(g("open_quotes_value") or 0)
        out.append({**base, "kind": "open_quote",
                    "severity": "high" if val >= 3000 else "med",
                    "title": f"{oq} cotação(ões) aberta(s) · {_money(val)}",
                    "detail": "Dar sequência antes de esfriar."})

    # 4) Inativo que já foi comprador
    if any(x in status for x in ("inativ", "bloque", "suspens")) and rev > 0:
        out.append({**base, "kind": "inactive",
                    "severity": "med",
                    "title": f"Cliente {g('client_status')} — faturou {_money(rev)} nos últimos 12m",
                    "detail": "Candidato a reativação."})

    return out


def build_alerts(contacts: list[Any]) -> dict:
    out: list[dict] = []
    for c in contacts:
        out.extend(alerts_for_contact(c))
    _SEV = {"high": 0, "med": 1}
    out.sort(key=lambda a: (_SEV.get(a["severity"], 2), -(a.get("score") or 0)))
    by_kind: dict[str, int] = {}
    for a in out:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    return {"alerts": out, "count": len(out), "by_kind": by_kind}
