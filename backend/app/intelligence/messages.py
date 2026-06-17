"""Dicas, insights e mensagens prontas por cliente.

O objetivo do portal: o vendedor entender 100% do cliente e agir rápido. Aqui
geramos (a) insights legíveis sobre a situação e (b) mensagens prontas de
WhatsApp adaptadas ao contexto (cotação parada, recompra atrasada, etc.).
Tudo a partir do que já está no espelho — sem chamadas extras.
"""
from __future__ import annotations

from typing import Any


def _money(v: float) -> str:
    return f"R$ {float(v or 0):,.0f}".replace(",", ".")


# tokens que indicam razão social (não personalizar com eles)
_COMPANY_WORDS = {
    "companhia", "comercio", "comercial", "industria", "industrial", "distribuidora",
    "distribuidor", "comercializadora", "ltda", "me", "eireli", "epp", "sa",
    "atacado", "atacadista", "grupo", "casa", "loja", "supermercado", "mercado",
    "empresa", "servicos", "transportes", "construtora", "condominio",
}


def first_name(name: str) -> str:
    """Primeiro nome para personalizar. Vazio quando o nome parece razão social
    (ex.: 'COMPANHIA DO PAPEL', '63.392.520 GABRIELA') para evitar 'Olá Companhia'."""
    parts = (name or "").strip().split()
    if not parts:
        return ""
    first = parts[0]
    if first[:1].isdigit():  # nome prefixado com CNPJ/código
        first = next((p for p in parts[1:] if p[:1].isalpha()), "")
    import unicodedata
    norm = "".join(
        c for c in unicodedata.normalize("NFD", first.lower())
        if unicodedata.category(c) != "Mn"
    )
    if not first or norm in _COMPANY_WORDS:
        return ""
    return first.title()


def _greet(fn: str) -> str:
    return f"Olá {fn}" if fn else "Olá"


def _is_overdue(c: dict) -> bool:
    d, f = c.get("days_without_purchase"), c.get("buy_frequency_days")
    if d is None:
        return False
    if f:
        return d / f >= 1.3
    return d >= 45


def build_insights(c: dict, top_products: list[dict]) -> list[dict]:
    """Lista de insights {text, tone}. tone: good | warn | bad | info."""
    out: list[dict] = []
    days = c.get("days_without_purchase")
    freq = c.get("buy_frequency_days")
    rev = float(c.get("revenue_12m") or 0)
    n = int(c.get("orders_12m") or 0)

    # recência x frequência
    if freq and days is not None:
        ratio = days / freq
        if ratio >= 2:
            out.append({"text": f"🔴 {days} dias sem comprar — mais que o DOBRO do ciclo "
                                f"habitual (~{freq}d). Risco alto de perda.", "tone": "bad"})
        elif ratio >= 1.3:
            out.append({"text": f"🟠 {days} dias sem comprar — passou do ciclo de ~{freq}d. "
                                f"Momento de ofertar.", "tone": "warn"})
        else:
            falta = max(0, freq - days)
            out.append({"text": f"🟢 Dentro do ciclo (~{freq}d). Próxima compra esperada "
                                f"em ~{falta}d.", "tone": "good"})
    elif days is not None:
        if days >= 90:
            out.append({"text": f"🔴 {days} dias sem comprar.", "tone": "bad"})
        elif days >= 45:
            out.append({"text": f"🟠 {days} dias sem comprar.", "tone": "warn"})

    # valor histórico + ticket médio
    if n > 0:
        ticket = rev / n
        out.append({"text": f"💰 {n} pedidos / 12m · {_money(rev)} "
                            f"(ticket médio {_money(ticket)}).", "tone": "info"})

    # dinheiro na mesa
    oq = int(c.get("open_quotes") or 0)
    if oq:
        out.append({"text": f"📄 {oq} cotação(ões) aberta(s) somando "
                            f"{_money(c.get('open_quotes_value'))} — dar sequência.", "tone": "warn"})
    od = int(c.get("open_deals") or 0)
    if od:
        out.append({"text": f"🤝 {od} negócio(s) aberto(s) no funil "
                            f"({_money(c.get('open_deals_value'))}).", "tone": "info"})

    # produto campeão
    if top_products:
        p = top_products[0]
        out.append({"text": f"⭐ Produto que mais leva: {p['product_name']} "
                            f"({_money(p['total'])} em 12m).", "tone": "info"})

    # status inativo
    st = (c.get("status") or c.get("client_status") or "").lower()
    if any(x in st for x in ("inativ", "bloque", "suspens")):
        out.append({"text": f"⚠️ Status comercial: {c.get('status') or c.get('client_status')}.",
                    "tone": "bad"})

    return out


def reactivation_message(c: dict) -> str:
    """A melhor mensagem de reativação para o cliente (1 linha pronta)."""
    msgs = build_messages(c, [])
    for m in msgs:
        if "reativ" in m["title"].lower():
            return m["text"]
    return msgs[0]["text"] if msgs else ""


def build_crosssell_message(name: str, segment: str, product: str) -> str:
    g = _greet(first_name(name))
    ramo = f" do ramo {segment}" if segment else ""
    return (f"{g}, tudo bem? Clientes{ramo} têm levado bastante *{product}*. "
            f"Quer que eu inclua no seu próximo pedido com uma condição especial? 📦")


def build_messages(c: dict, top_products: list[dict]) -> list[dict]:
    """Mensagens prontas de WhatsApp adaptadas ao contexto."""
    g = _greet(first_name(c.get("name") or ""))
    days = c.get("days_without_purchase")
    freq = c.get("buy_frequency_days")
    oq = int(c.get("open_quotes") or 0)
    prod = top_products[0]["product_name"] if top_products else None
    msgs: list[dict] = []

    if oq:
        msgs.append({
            "title": "Follow-up de cotação",
            "text": (f"{g}, tudo bem? Sobre a cotação em aberto "
                     f"({_money(c.get('open_quotes_value'))}), conseguiu avaliar? "
                     f"Posso ajustar prazo ou condição pra fecharmos ainda esta semana. 👍"),
        })

    if _is_overdue(c):
        extra = f" Vi que costuma repor *{prod}* com a gente." if prod else ""
        ciclo = f" (você costuma comprar a cada ~{freq} dias)" if freq else ""
        msgs.append({
            "title": "Reativação — passou da frequência",
            "text": (f"{g}, tudo bem? Faz {days} dias desde seu último pedido{ciclo}."
                     f"{extra} Separei condições especiais pra repor o estoque — "
                     f"quer que eu já monte o pedido? 😉"),
        })
    elif days is not None and days >= 45:
        msgs.append({
            "title": "Reativação",
            "text": (f"{g}! Sentimos sua falta por aqui 🙂 Faz um tempinho desde a "
                     f"última compra. Temos novidades e condições especiais — posso te enviar?"),
        })

    if not msgs:
        msgs.append({
            "title": "Check-in / oferta",
            "text": (f"{g}, tudo bem? Passando pra saber se está precisando repor "
                     f"algum item. Posso preparar um orçamento rápido pra você. 📦"),
        })

    return msgs
