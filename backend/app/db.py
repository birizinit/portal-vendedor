"""Camada de banco (espelho local). SQLAlchemy 2.0, engine síncrona.

DATABASE_URL controla o destino: sqlite (dev) ou postgresql (nuvem).
As leituras da API são rápidas (rodam em threadpool do FastAPI); o sync grava
em lote a partir dos dados já baixados do Ploomes.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sessão transacional com commit/rollback automático."""
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_session() -> Iterator[Session]:
    """Dependency do FastAPI (apenas leitura nas rotas)."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def init_db() -> None:
    from app import models  # noqa: F401 — registra os modelos
    Base.metadata.create_all(engine)
