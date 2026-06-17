"""Resolução de campos customizados do Ploomes (OtherProperties / Sankhya).

A conta da Lar Plásticos tem ~1175 campos customizados. Cada um é identificado
por um FieldKey (ex.: "contact_FC5FD398-..."), e o valor fica numa de várias
colunas (ObjectValueName p/ picklists, StringValue, DecimalValue, IntegerValue,
DateTimeValue, BoolValue).

Mantemos os FieldKeys-chave da carteira fixados aqui (descobertos via /Fields),
mais um catálogo opcional FieldKey->Nome carregado da API para leitura genérica.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import DATA_DIR

# --- FieldKeys-chave (Contact) descobertos no Ploomes da Lar Plásticos --------
# Usados diretamente no sync da carteira — não dependem do catálogo carregado.
FK = {
    "frequencia_compra": "contact_76F3AEDE-F021-4EF3-A658-8D1F63C97205",
    "data_ultima_compra": "contact_773ED9C3-59DF-497A-8343-6D231AAE81D0",
    "dias_sem_compra": "contact_FC5FD398-DB02-4E7C-A94D-8753E05F600D",
    "status_cliente": "contact_E07C0529-9ABC-412F-87B4-C5FE75CB78F9",     # comercial (emoji)
    "status_lifecycle": "contact_919382BF-359F-44ED-A28D-7E1DD8B9A432",   # CRM lifecycle
    "segmento": "contact_5782C334-EF2A-4D3F-A67F-D07964295281",           # "1000003 - REVENDA - LOJA"
    "cod_parceiro_sankhya": "contact_7B327F98-39D2-4E7E-9575-2B49540FBBC9",
    "ativo_sankhya": "contact_C65F2E95-FB4F-4B12-8A60-36727A3974BB",
}

# Ordem de preferência ao ler o valor de um OtherProperty.
# ObjectValueName primeiro: em picklists é o texto legível (IntegerValue guarda só o id da opção).
_VALUE_COLUMNS = (
    "ObjectValueName", "StringValue", "DecimalValue",
    "DateTimeValue", "IntegerValue", "BoolValue",
)

_CATALOG_FILE = DATA_DIR / "ploomes_fields.json"


def value_of(op: dict) -> Any:
    """Extrai o valor 'legível' de um item de OtherProperties."""
    for col in _VALUE_COLUMNS:
        v = op.get(col)
        if v not in (None, "", []):
            return v
    big = op.get("BigStringValue")
    if big and "<" not in str(big)[:40]:   # evita HTML de UI
        return big
    return None


def value_by_key(item: dict, field_key: str) -> Any:
    """Valor cru de um OtherProperty de `item` pelo FieldKey (ou None)."""
    if not field_key:
        return None
    for op in item.get("OtherProperties") or []:
        if op.get("FieldKey") == field_key:
            return value_of(op)
    return None


def get(item: dict, alias: str) -> Any:
    """Atalho: valor de um campo-chave por alias (ver dict FK)."""
    return value_by_key(item, FK.get(alias, ""))


# --- Catálogo genérico FieldKey -> Nome (opcional) ---------------------------
class FieldCatalog:
    def __init__(self) -> None:
        self._key_to_name: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if _CATALOG_FILE.exists():
            try:
                self._key_to_name = json.loads(_CATALOG_FILE.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._key_to_name = {}

    def replace(self, key_to_name: dict[str, str]) -> None:
        self._key_to_name = dict(key_to_name)

    def persist(self) -> None:
        try:
            _CATALOG_FILE.write_text(
                json.dumps(self._key_to_name, ensure_ascii=False), "utf-8")
        except OSError:
            pass

    def name(self, key: str) -> str:
        return self._key_to_name.get(key, key)

    def __len__(self) -> int:
        return len(self._key_to_name)


catalog = FieldCatalog()
