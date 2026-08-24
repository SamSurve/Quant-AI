"""Small async cache interface for the Vercel MVP.

This implementation is deliberately process-local. It reduces repeated work in a
warm function instance and coalesces concurrent identical requests, but is not a
shared production cache. The ``AsyncTTLCache`` interface can later be replaced by
a managed cache adapter without changing service contracts.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar


Value = TypeVar("Value")


@dataclass
class CacheEntry(Generic[Value]):
    value: Value
    expires_at: float


class AsyncTTLCache(Generic[Value]):
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry[Value]] = {}
        self._inflight: dict[str, asyncio.Task[Value]] = {}
        self._lock = asyncio.Lock()

    async def get_or_load(self, key: str, ttl_seconds: float, loader: Callable[[], Awaitable[Value]]) -> tuple[Value, bool]:
        """Return ``(value, cache_hit)`` while deduplicating active loads by key."""

        now = time.monotonic()
        owner = False
        async with self._lock:
            cached = self._entries.get(key)
            if cached and cached.expires_at > now:
                return cached.value, True
            if cached:
                self._entries.pop(key, None)

            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(loader())
                self._inflight[key] = task
                owner = True

        try:
            value = await task
        except BaseException:
            if owner:
                async with self._lock:
                    self._inflight.pop(key, None)
            raise

        if owner:
            async with self._lock:
                self._entries[key] = CacheEntry(value=value, expires_at=time.monotonic() + ttl_seconds)
                self._inflight.pop(key, None)
        return value, False

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()
            self._inflight.clear()

    async def snapshot(self) -> dict[str, int]:
        async with self._lock:
            return {"entries": len(self._entries), "inflight": len(self._inflight)}
