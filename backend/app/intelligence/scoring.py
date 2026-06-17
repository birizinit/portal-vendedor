"""Score de prioridade da carteira (0–100).

Responde "a quem o vendedor deve dar atenção AGORA". Combina dinheiro na mesa
(cotações abertas, negócios abertos), pressão de recompra (frequência estourada)
e valor histórico do cliente. Tudo a partir de campos já no espelho — sem
chamadas extras ao Ploomes.
"""
from __future__ import annotations

from typing import Any

from app.util import norm


def compute_priority(c: dict[str, Any]) -> float:
    score = 0.0

    days = c.get("days_without_purchase")
    freq = c.get("buy_frequency_days")
    # pressão de recompra: passou do ciclo habitual
    if days is not None and freq:
        ratio = days / freq if freq else 0
        if ratio >= 1.0:
            score += min(34, 14 + (ratio - 1.0) * 20)
    elif days is not None:
        d = int(days)
        if 30 <= d < 90:
            score += 12 + (d - 30) * 0.15
        elif d >= 90:
            score += 20

    # dinheiro na mesa: cotações abertas
    oq = int(c.get("open_quotes") or 0)
    if oq:
        score += 20 + min(10, oq * 4)
    ov = float(c.get("open_quotes_value") or 0)
    if ov >= 2000:
        score += min(16, ov / 3000)

    # negócios abertos no funil
    if int(c.get("open_deals") or 0) > 0:
        score += 10
        odv = float(c.get("open_deals_value") or 0)
        if odv >= 2000:
            score += min(10, odv / 5000)

    # valor histórico — cliente importante merece atenção
    rev = float(c.get("revenue_12m") or 0)
    if rev >= 5000:
        score += min(14, rev / 8000)

    # status comercial
    st = norm(c.get("client_status"))
    if any(x in st for x in ("inativ", "bloque", "suspens")):
        score -= 6   # ainda aparece, mas com prioridade menor no cockpit "hoje"

    return round(max(0.0, min(100.0, score)), 1)


def score_kind(value: float) -> str:
    """Classe de cor p/ o front: hi / mid / lo."""
    if value >= 55:
        return "hi"
    if value >= 28:
        return "mid"
    return "lo"
