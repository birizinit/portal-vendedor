"""Camada de banco (espelho local). SQLAlchemy 2.0, engine síncrona.

DATABASE_URL controla o destino: sqlite (dev) ou postgresql (nuvem).
As leituras da API são rápidas (rodam em threadpool do FastAPI); o sync grava
em lote a partir dos dados já baixados do Ploomes.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    """Garante que a pasta do arquivo SQLite exista (evita 'unable to open
    database file' em deploy — Railway/Docker, volume montado, etc.)."""
    if not url.startswith("sqlite"):
        return
    raw = url.split("///", 1)[-1]
    if not raw or raw == ":memory:":
        return
    try:
        Path(raw).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _normalize_url(url: str) -> str:
    """Aceita a DATABASE_URL padrão do Railway/Heroku (postgres:// e
    postgresql://) e força o driver psycopg3 instalado."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_DB_URL = _normalize_url(settings.database_url)
_ensure_sqlite_dir(_DB_URL)

_connect_args = {"check_same_thread": False} if _DB_URL.startswith("sqlite") else {}

engine = create_engine(
    _DB_URL,
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
