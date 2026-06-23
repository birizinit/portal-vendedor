"""Modelos do espelho local (dados sincronizados do Ploomes + usuários do portal)."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Seller(Base):
    """Usuário do portal. Vendedor é mapeado ao seu OwnerId do Ploomes."""
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ploomes_owner_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[str] = mapped_column(String(20), default="seller")  # seller | admin
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Contact(Base):
    """Cliente da carteira (espelho de Contacts TypeId=1 do Ploomes)."""
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Ploomes Contact Id
    owner_id: Mapped[int] = mapped_column(Integer, index=True)

    name: Mapped[str] = mapped_column(String(240), default="")
    cnpj: Mapped[str] = mapped_column(String(40), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    phone_tail: Mapped[str] = mapped_column(String(12), default="", index=True)
    city: Mapped[str] = mapped_column(String(120), default="")

    segment_code: Mapped[str] = mapped_column(String(20), default="")
    segment_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    client_status: Mapped[str] = mapped_column(String(60), default="")     # comercial Sankhya (sem emoji)
    lifecycle_status: Mapped[str] = mapped_column(String(60), default="")  # CRM
    cod_parceiro: Mapped[str] = mapped_column(String(30), default="")

    days_without_purchase: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    buy_frequency_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_purchase_date: Mapped[str] = mapped_column(String(40), default="")

    # agregados (preenchidos no sync a partir de Orders/Quotes/Deals)
    last_order_date: Mapped[str] = mapped_column(String(40), default="")
    last_order_value: Mapped[float] = mapped_column(Float, default=0.0)
    revenue_12m: Mapped[float] = mapped_column(Float, default=0.0)
    orders_12m: Mapped[int] = mapped_column(Integer, default=0)
    open_quotes: Mapped[int] = mapped_column(Integer, default=0)
    open_quotes_value: Mapped[float] = mapped_column(Float, default=0.0)
    open_deals: Mapped[int] = mapped_column(Integer, default=0)
    open_deals_value: Mapped[float] = mapped_column(Float, default=0.0)

    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    synced_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_contacts_owner_score", "owner_id", "priority_score"),
    )


class Order(Base):
    """Cabeçalho de pedido (espelho de Orders do Ploomes)."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Ploomes Order Id
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    contact_id: Mapped[int] = mapped_column(Integer, index=True)
    order_number: Mapped[str] = mapped_column(String(40), default="")
    date: Mapped[str] = mapped_column(String(40), default="", index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status_nota: Mapped[str] = mapped_column(String(60), default="")


class OrderItem(Base):
    """Item de pedido — base p/ cross-sell (produtos por ramo/cliente)."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    contact_id: Mapped[int] = mapped_column(Integer, index=True)
    segment_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    product_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    product_name: Mapped[str] = mapped_column(String(240), default="")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    date: Mapped[str] = mapped_column(String(40), default="")


class Quote(Base):
    """Cotação aberta (espelho de Quotes do Ploomes)."""
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Ploomes Quote Id
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    contact_id: Mapped[int] = mapped_column(Integer, index=True)
    date: Mapped[str] = mapped_column(String(40), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status_nota: Mapped[str] = mapped_column(String(60), default="")


class SyncState(Base):
    """Estado da última sincronização por vendedor (para a UI mostrar progresso)."""
    __tablename__ = "sync_state"

    owner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle|running|ok|error
    message: Mapped[str] = mapped_column(Text, default="")
    total: Mapped[int] = mapped_column(Integer, default=0)
    synced: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertDismissal(Base):
    """'OK' do vendedor num alerta — silencia só pelo dia (volta amanhã se
    a situação no Ploomes continuar)."""
    __tablename__ = "alert_dismissals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    contact_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(30), default="")
    dismissed_on: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD (America/Sao_Paulo)

    __table_args__ = (
        Index("ix_dismissal_unique", "owner_id", "contact_id", "kind", unique=True),
    )
