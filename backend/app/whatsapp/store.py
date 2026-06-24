"""Espelho local das mensagens de WhatsApp — gravação idempotente e leitura.

A tela sempre lê daqui (rápido, previsível). O webhook alimenta o espelho; o
envio assistido também grava a mensagem que sai. O join com o cliente é por
`phone_tail` (últimos 8 dígitos).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.util import only_digits
from app.whatsapp.client import normalize_phone, phone_tail


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def save_message(db: Session, *, phone: str, direction: str, text: str,
                 name: str = "", sent_by: str = "",
                 neppo_id: Optional[int] = None) -> Optional[models.WhatsappMessage]:
    """Grava uma mensagem no espelho. Idempotente por `neppo_id` — webhook
    reentregue não duplica. Retorna a linha criada (ou None se já existia)."""
    if neppo_id is not None:
        existing = db.scalar(
            select(models.WhatsappMessage).where(
                models.WhatsappMessage.neppo_id == neppo_id))
        if existing is not None:
            return None

    row = models.WhatsappMessage(
        neppo_id=neppo_id,
        phone=normalize_phone(phone),
        phone_tail=phone_tail(phone),
        direction=direction if direction in ("in", "out") else "in",
        text=text or "",
        name=name or "",
        sent_by=sent_by or "",
        created_at=_now(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # corrida no neppo_id único — outra entrega gravou primeiro
        db.rollback()
        return None
    db.refresh(row)
    return row


def thread_for_contact(db: Session, contact: models.Contact,
                       limit: int = 40) -> list[models.WhatsappMessage]:
    """Mensagens recentes do cliente (mais antigas -> recentes) pelo phone_tail."""
    tail = contact.phone_tail or only_digits(contact.phone)[-8:]
    if not tail:
        return []
    rows = db.scalars(
        select(models.WhatsappMessage)
        .where(models.WhatsappMessage.phone_tail == tail)
        .order_by(desc(models.WhatsappMessage.created_at))
        .limit(limit)).all()
    return list(reversed(rows))


def last_inbound_at(db: Session, tail: str) -> Optional[dt.datetime]:
    """Quando o cliente mandou a última mensagem (define a janela de 24h)."""
    if not tail:
        return None
    return db.scalar(
        select(models.WhatsappMessage.created_at)
        .where(models.WhatsappMessage.phone_tail == tail,
               models.WhatsappMessage.direction == "in")
        .order_by(desc(models.WhatsappMessage.created_at))
        .limit(1))


def _aware(d: dt.datetime) -> dt.datetime:
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def session_window(last_in: Optional[dt.datetime]) -> dict:
    """Estado da janela de 24h: se está aberta e quantas horas faltam."""
    if last_in is None:
        return {"open": False, "last_inbound_at": None, "hours_left": 0}
    elapsed = (_now() - _aware(last_in)).total_seconds() / 3600
    hours_left = max(0.0, settings.neppo_session_window_hours - elapsed)
    return {
        "open": hours_left > 0,
        "last_inbound_at": _aware(last_in).isoformat(),
        "hours_left": round(hours_left, 1),
    }
