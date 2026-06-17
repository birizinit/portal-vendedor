"""Configuração central do Portal de Inteligência de Carteira.

Lê de variáveis de ambiente / arquivo .env. Sem segredos hard-coded.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Ploomes ---
    ploomes_api_key: str = ""
    ploomes_base_url: str = "https://api2.ploomes.com"
    ploomes_rate_limit: int = 120          # req/min (limite documentado)
    ploomes_cache_ttl: int = 300           # segundos

    # --- Banco ---
    database_url: str = f"sqlite:///{DATA_DIR / 'portal.db'}"

    # --- App / auth ---
    secret_key: str = "dev-secret-trocar-em-producao"
    access_token_minutes: int = 60 * 12
    portal_admin_email: str = "admin@local"
    portal_admin_password: str = "admin"

    # --- Sync ---
    portfolio_sync_page_size: int = 100
    portfolio_sync_max_pages: int = 120
    portfolio_auto_sync_hours: float = 6.0

    # --- Inteligência ---
    reactivation_factor: float = 1.3       # dias_sem_compra / frequência >= fator -> alerta
    stale_deal_days: int = 7               # negócio parado no estágio

    @property
    def ploomes_configured(self) -> bool:
        return bool(self.ploomes_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
