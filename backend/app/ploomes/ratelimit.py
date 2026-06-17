"""Token bucket assíncrono para respeitar o limite de 120 req/min do Ploomes,
e um cache TTL simples em memória para leituras repetidas."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional


class AsyncTokenBucket:
    """Distribui `rate_per_min` tokens ao longo de um minuto (recarga contínua)."""

    def __init__(self, rate_per_min: int) -> None:
        self.capacity = max(1, rate_per_min)
        self.tokens = float(self.capacity)
        self.refill_per_sec = self.capacity / 60.0
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(
                    self.capacity,
                    self.tokens + (now - self._updated) * self.refill_per_sec,
                )
                self._updated = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                deficit = 1.0 - self.tokens
                await asyncio.sleep(deficit / self.refill_per_sec)


class TTLCache:
    """Cache chave->valor com expiração por tempo (segundos)."""

    def __init__(self, ttl: int) -> None:
        self.ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if item is None:
            return None
        exp, val = item
        if time.monotonic() > exp:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Any) -> None:
        self._store[key] = (time.monotonic() + self.ttl, val)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
