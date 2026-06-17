"""Utilitários de parsing dos dados do Ploomes/Sankhya."""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from typing import Optional

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿️]+"
)


def strip_emoji(s: Optional[str]) -> str:
    """Remove emojis/ícones (ex.: '🟢 Ativo' -> 'Ativo')."""
    if not s:
        return ""
    return _EMOJI_RE.sub("", str(s)).strip()


def norm(s) -> str:
    """Minúsculas sem acento, para comparação tolerante."""
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def to_int(v) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def to_float(v, default: float = 0.0) -> float:
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def parse_segment(raw) -> tuple[str, str]:
    """'1000003 - REVENDA - LOJA' -> ('1000003', 'REVENDA - LOJA')."""
    s = str(raw or "").strip()
    if not s:
        return "", ""
    m = re.match(r"^\s*(\d+)\s*[-–]\s*(.+)$", s)
    if m:
        return m.group(1), m.group(2).strip()
    return "", s


def parse_frequency_days(raw) -> Optional[int]:
    """Frequência de compra -> dias. Aceita número (dias) ou rótulo textual."""
    if raw is None or raw == "":
        return None
    n = to_int(raw)
    if n is not None and n > 0:
        return n
    t = norm(raw)
    if "diari" in t:
        return 1
    if "semanal" in t:
        return 7
    if "quinzenal" in t:
        return 15
    if "mensal" in t:
        return 30
    if "bimestral" in t:
        return 60
    if "trimestral" in t:
        return 90
    return None


def days_since(date_str: Optional[str]) -> Optional[int]:
    """Dias decorridos desde uma data ISO (tolera com/sem timezone)."""
    s = (date_str or "").strip()
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = dt.datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    today = dt.datetime.now(d.tzinfo) if d.tzinfo else dt.datetime.now()
    delta = (today - d).days
    return delta if delta >= 0 else 0


def only_digits(s: Optional[str]) -> str:
    return "".join(c for c in (s or "") if c.isdigit())
