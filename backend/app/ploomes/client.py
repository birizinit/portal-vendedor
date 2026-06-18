"""Cliente assíncrono do Ploomes (OData v4).

- Autentica via header 'User-Key'.
- Respeita o limite de 120 req/min (token bucket) com retry/backoff em 429/5xx.
- Cache TTL curto para leituras repetidas.
- Leitura: Contacts/Orders/Quotes/Deals/Users/Fields.
- Escrita (gated por ação do usuário): registros de interação (anotações).
  Criação de quotes/orders fica para v2.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import settings
from app.ploomes.ratelimit import AsyncTokenBucket, TTLCache

log = logging.getLogger("portal.ploomes")
_RETRY_STATUS = {429, 500, 502, 503, 504}


class PloomesClient:
    def __init__(self) -> None:
        self._bucket = AsyncTokenBucket(settings.ploomes_rate_limit)
        self._cache = TTLCache(settings.ploomes_cache_ttl)
        self._client = httpx.AsyncClient(
            base_url=settings.ploomes_base_url,
            headers={"User-Key": settings.ploomes_api_key},
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kw) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            await self._bucket.acquire()
            try:
                resp = await self._client.request(method, path, **kw)
                if resp.status_code in _RETRY_STATUS and attempt < 2:
                    wait = 0.8 * (attempt + 1)
                    log.warning("Ploomes %s %s -> %s, retry em %.1fs",
                                method, path, resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except httpx.TransportError as e:
                last_exc = e
                if attempt < 2:
                    await asyncio.sleep(0.8 * (attempt + 1))
                    continue
                log.error("Ploomes %s %s falhou (rede): %s", method, path, e)
                raise
        if last_exc:
            raise last_exc
        return {}

    async def get(self, path: str, params: Optional[dict] = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict) -> Any:
        return await self._request("POST", path, json=json)

    async def get_all(self, path: str, params: Optional[dict] = None, *,
                      page: int = 100, max_pages: int = 200) -> list[dict]:
        """Paginação automática via $top/$skip; retorna lista de `value`."""
        out: list[dict] = []
        skip = 0
        base = dict(params or {})
        base["$top"] = page
        for _ in range(max_pages):
            base["$skip"] = skip
            data = await self.get(path, params=dict(base))
            rows = data.get("value") or []
            if not rows:
                break
            out.extend(rows)
            if len(rows) < page:
                break
            skip += page
            await asyncio.sleep(0.03)
        return out

    # -- metadados (com cache) ----------------------------------------------
    async def users(self) -> list[dict]:
        cached = self._cache.get("users")
        if cached is not None:
            return cached
        rows = await self.get_all("/Users", {"$select": "Id,Name,Email"},
                                  page=300, max_pages=20)
        self._cache.set("users", rows)
        return rows

    async def pipelines(self) -> list[dict]:
        cached = self._cache.get("pipelines")
        if cached is not None:
            return cached
        data = await self.get("/Deals@Pipelines", {"$select": "Id,Name", "$top": 200})
        rows = data.get("value", [])
        self._cache.set("pipelines", rows)
        return rows

    async def stages(self) -> list[dict]:
        cached = self._cache.get("stages")
        if cached is not None:
            return cached
        data = await self.get("/Deals@Stages", {
            "$select": "Id,Name,PipelineId,Ordination",
            "$orderby": "PipelineId,Ordination", "$top": 300,
        })
        rows = data.get("value", [])
        self._cache.set("stages", rows)
        return rows

    async def fields_catalog(self) -> dict[str, str]:
        """Mapa FieldKey->Nome de todos os campos customizados (paginado)."""
        rows = await self.get_all("/Fields", {"$select": "Key,Name"},
                                  page=300, max_pages=20)
        return {r["Key"]: (r.get("Name") or r["Key"]) for r in rows if r.get("Key")}

    # -- interações (registros) --------------------------------------------
    async def interactions_for_contact(self, contact_id: int, top: int = 15) -> list[dict]:
        """Últimos registros de interação de um contato (leitura ao vivo)."""
        data = await self.get("/InteractionRecords", {
            "$filter": f"ContactId eq {int(contact_id)}",
            "$orderby": "Date desc", "$top": top,
            "$select": "Id,Date,TypeId,Title,Content,CreatorId,DealId",
        })
        return data.get("value", [])

    async def create_interaction(self, payload: dict) -> dict:
        """Cria um registro de interação (anotação) no Ploomes.
        Escrita — só após ação explícita do usuário."""
        data = await self.post("/InteractionRecords", payload)
        rows = data.get("value") if isinstance(data, dict) else None
        return (rows[0] if rows else data) or {}

    # -- negócios / deals ---------------------------------------------------
    async def deals_for_contact(self, contact_id: int, top: int = 20) -> list[dict]:
        """Negócios (deals) de um contato, com o estágio (leitura ao vivo)."""
        data = await self.get("/Deals", {
            "$filter": f"ContactId eq {int(contact_id)}",
            "$orderby": "LastUpdateDate desc", "$top": top,
            "$select": "Id,Title,Amount,StatusId,StageId,PipelineId",
            "$expand": "Stage($select=Id,Name)",
        })
        return data.get("value", [])

    async def intake_stage(self, pipeline_name: str) -> tuple[Optional[int], Optional[int]]:
        """Resolve (pipeline_id, primeiro_stage_id) do funil de entrada pelo nome.
        Dinâmico (tolera mudança de Id), com cache."""
        cached = self._cache.get("intake_stage")
        if cached is not None:
            return cached
        pls = await self.pipelines()
        name = (pipeline_name or "").lower()
        pid = next((p["Id"] for p in pls if (p.get("Name") or "").lower() == name), None)
        if pid is None:
            pid = next((p["Id"] for p in pls if name in (p.get("Name") or "").lower()), None)
        stage_id = None
        if pid is not None:
            ps = [s for s in await self.stages() if s.get("PipelineId") == pid]
            if ps:
                stage_id = min(ps, key=lambda s: s.get("Ordination") or 0)["Id"]
        result = (pid, stage_id)
        self._cache.set("intake_stage", result)
        return result

    async def create_deal(self, payload: dict) -> dict:
        """Cria um negócio (deal) no Ploomes. Escrita — só após ação do usuário."""
        data = await self.post("/Deals", payload)
        rows = data.get("value") if isinstance(data, dict) else None
        return (rows[0] if rows else data) or {}


_client: Optional[PloomesClient] = None


def get_ploomes() -> Optional[PloomesClient]:
    """Instância única (criada sob demanda) se a chave estiver configurada."""
    global _client
    if not settings.ploomes_configured:
        return None
    if _client is None:
        _client = PloomesClient()
    return _client


async def close_ploomes() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
