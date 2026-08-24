"""Best-effort anonymous request controls for the Vercel function MVP."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

from .research_errors import ResearchError
from .research_schemas import ErrorCategory


@dataclass
class SlidingWindowRateLimiter:
    """Process-local limiter; replace with a shared adapter for multi-instance limits."""

    limit: int = 10
    window_seconds: float = 60.0
    _requests: dict[str, deque[float]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def check(self, key: str) -> None:
        now = time.monotonic()
        async with self._lock:
            events = self._requests.setdefault(key, deque())
            while events and events[0] <= now - self.window_seconds:
                events.popleft()
            if len(events) >= self.limit:
                raise ResearchError(ErrorCategory.RATE_LIMITED, detail=f"local limit reached for {key}", retryable=True)
            events.append(now)


class ResearchConcurrencyGuard:
    def __init__(self, max_concurrent: int = 4) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.05)
        except TimeoutError as error:
            raise ResearchError(ErrorCategory.RATE_LIMITED, detail="research concurrency exhausted", retryable=True) from error
        try:
            yield
        finally:
            self._semaphore.release()
