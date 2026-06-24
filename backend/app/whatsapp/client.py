"""Cliente Neppo — OAuth2 (password grant), envio ativo e parsing de webhook.

Portado da Central de Inteligência (Cortex), enxuto para o que a Fase 1 precisa:
autenticação com cache de token, envio de texto livre (canal não oficial) e
normalização do webhook de entrada. A leitura de histórico fica no espelho local
(store.py) — a tela nunca varre a API ao vivo.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from typing import Any, Optional

import httpx

from app.config import settings

SEND_PATH = "/chatapi/1.0/api/direct-message/save"


def normalize_phone(phone: str) -> str:
    """Só dígitos, com DDI 55 quando vier sem (telefone BR de 10/11 dígitos)."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    return digits


def phone_tail(phone_or_id: str) -> str:
    """Últimos 8 dígitos — chave canônica para casar WhatsApp ↔ CRM."""
    raw = phone_or_id[3:] if (phone_or_id or "").startswith("wa_") else phone_or_id
    d = normalize_phone(raw)
    return d[-8:] if len(d) >= 8 else d


def clean_message_text(raw: Any) -> str:
    """Mensagens interativas do WhatsApp chegam como JSON (botões/listas).
    Extrai o texto legível; senão devolve o texto como veio."""
    if raw in (None, ""):
        return ""
    s = str(raw).strip()
    if s[:1] not in "{[":
        return s
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return s
    if isinstance(obj, dict):
        t = obj.get("type")
        if t == "button":
            return (obj.get("body") or {}).get("text") or s
        if t == "button_reply":
            br = obj.get("button_reply") or {}
            return br.get("title") or br.get("text") or br.get("id") or s
        if t in ("list_reply", "interactive"):
            node = obj.get("list_reply") or obj.get("interactive") or {}
            return node.get("title") or node.get("text") or s
        for path in (("body", "text"), ("text",), ("title",), ("caption",)):
            cur = obj
            for k in path:
                cur = cur.get(k) if isinstance(cur, dict) else None
            if cur:
                return str(cur)
    return s


class NeppoClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=25.0)
        self._token: Optional[str] = None
        self._token_expires: float = 0.0
        self._token_lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _fetch_token(self) -> str:
        creds = f"{settings.neppo_client_key}:{settings.neppo_client_secret}".encode()
        basic = base64.b64encode(creds).decode()
        resp = await self._http.post(
            settings.neppo_auth_url,
            data={
                "grant_type": "password",
                "username": settings.neppo_username,
                "password": settings.neppo_password,
            },
            headers={"Authorization": f"Basic {basic}"},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.monotonic() + max(60, int(data.get("expires_in", 3600)) - 60)
        return self._token

    async def get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires:
            return self._token
        async with self._token_lock:
            # re-checa dentro do lock: outra corrotina pode já ter renovado
            if self._token and time.monotonic() < self._token_expires:
                return self._token
            return await self._fetch_token()

    async def send_message(self, phone: str, text: str) -> dict:
        """Envio ativo de WhatsApp (texto livre). Dentro da janela de 24h é
        liberado pelo WhatsApp; a checagem da janela é feita no chamador."""
        phone_number = normalize_phone(phone)
        if not phone_number:
            raise ValueError("telefone inválido para envio Neppo")

        body: dict[str, Any] = {
            "phoneNumber": phone_number,
            "channel": "WHATSAPP",
            "message": text,
            "groupName": settings.neppo_group_name,
            "status": "PROCESSANDO",
            "createdBy": settings.neppo_username,
            "groupConfId": settings.neppo_group_conf_id,
        }
        if settings.neppo_user_id:
            body["userId"] = settings.neppo_user_id

        token = await self.get_token()
        url = settings.neppo_base_url.rstrip("/") + SEND_PATH
        resp = await self._http.post(
            url, json=body,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}


_client: Optional[NeppoClient] = None


def get_neppo() -> Optional[NeppoClient]:
    global _client
    if not settings.neppo_enabled:
        return None
    if _client is None:
        _client = NeppoClient()
    return _client


async def close_neppo() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# --- webhook de entrada --------------------------------------------------
def _parse_content(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _phone_from_content(content: dict) -> str:
    for key in ("phone", "phoneNumber", "phoneContact"):
        if content.get(key):
            return str(content[key])
    user = content.get("user") or {}
    if isinstance(user, dict):
        if user.get("phone"):
            return str(user["phone"])
        m = re.search(r"(\d{10,15})", str(user.get("userName") or ""))
        if m:
            return m.group(1)
    return ""


def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def parse_webhook(payload: dict) -> Optional[dict]:
    """Normaliza o webhook Neppo (MESSAGE/SESSION/CHAT_API) ou payload simples.
    Ignora mensagens de agente/bot — só queremos o que o cliente mandou."""
    try:
        component = payload.get("component")
        if component in ("MESSAGE", "SESSION", "CHAT_API"):
            content = _parse_content(payload.get("content"))
            text = content.get("message") or content.get("text") or content.get("body")
            phone = _phone_from_content(content)
            user = content.get("user") or {}
            if isinstance(user, dict) and user.get("typeUser") in ("AGENT", "BOT"):
                return None
            if text and phone:
                name = ""
                if isinstance(user, dict):
                    name = str(user.get("displayName") or user.get("name") or "")
                mid = content.get("id") or payload.get("id")
                return {"phone": str(phone), "text": clean_message_text(text),
                        "name": name, "id": _as_int(mid)}

        phone = payload.get("from") or payload.get("phone") or payload.get("phoneNumber")
        text = payload.get("text")
        msg = payload.get("message")
        if not text and isinstance(msg, dict):
            text = msg.get("text")
        elif not text and isinstance(msg, str):
            text = msg
        if phone and text:
            return {"phone": str(phone), "text": clean_message_text(text),
                    "name": str(payload.get("contactName") or payload.get("name") or ""),
                    "id": _as_int(payload.get("id"))}
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    return None
