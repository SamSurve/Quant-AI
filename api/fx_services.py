"""Verified FX conversion adapter for deterministic cross-currency comparison.

The adapter uses the project's existing Yahoo Finance/yfinance market-data path.
It returns an explicit rate, pair direction, source symbol, URL, and retrieval
timestamp; a missing or invalid quote remains unavailable and is never estimated.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Any

import yfinance as yf

from .research_cache import AsyncTTLCache
from .research_errors import ResearchError
from .research_schemas import ErrorCategory, FXConversion, SourceRecord
from .research_services import EXTERNAL_TIMEOUT_SECONDS, utc_stamp


FX_TTL_SECONDS = 60 * 15


def _quote_url(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol}"


@dataclass(frozen=True)
class FXRateResult:
    conversion: FXConversion | None
    warning: ResearchError | None
    source: SourceRecord | None


class FXRateService:
    """Retrieve only a source-returned base-to-quote FX rate for supported pairs."""

    def __init__(self, cache: AsyncTTLCache[FXRateResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, base_currency: str | None, quote_currency: str | None) -> FXRateResult:
        base = (base_currency or "").upper().strip()
        quote = (quote_currency or "").upper().strip()
        if not base or not quote or base == quote:
            return FXRateResult(None, None, None)
        result, _ = await self._cache.get_or_load(
            f"fx:{base}:{quote}",
            FX_TTL_SECONDS,
            lambda: self._fetch_uncached(base, quote),
        )
        return result

    async def _fetch_uncached(self, base_currency: str, quote_currency: str) -> FXRateResult:
        for symbol, inverse in (
            (f"{base_currency}{quote_currency}=X", False),
            (f"{quote_currency}{base_currency}=X", True),
        ):
            quote_rate = await self._latest_close(symbol)
            if quote_rate is None:
                continue
            rate = 1 / quote_rate if inverse else quote_rate
            if not math.isfinite(rate) or rate <= 0:
                continue
            retrieved_at = utc_stamp()
            conversion = FXConversion(
                base_currency=base_currency,
                quote_currency=quote_currency,
                rate=rate,
                source="Yahoo Finance via yfinance",
                source_symbol=symbol,
                url=_quote_url(symbol),
                retrieved_at=retrieved_at,
            )
            source = SourceRecord(
                source=conversion.source,
                url=conversion.url,
                retrieved_at=conversion.retrieved_at,
                data_type="fx",
            )
            return FXRateResult(conversion, None, source)
        return FXRateResult(
            None,
            ResearchError(
                ErrorCategory.CURRENCY_COMPARISON_UNAVAILABLE,
                detail=f"verified FX quote unavailable for {base_currency}/{quote_currency}",
                retryable=True,
            ),
            None,
        )

    @staticmethod
    async def _latest_close(symbol: str) -> float | None:
        try:
            frame = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: yf.Ticker(symbol).history(
                        period="5d",
                        interval="1d",
                        auto_adjust=False,
                        actions=False,
                    )
                ),
                timeout=EXTERNAL_TIMEOUT_SECONDS,
            )
        except (TimeoutError, Exception):
            return None
        return _last_finite_close(frame)


def _last_finite_close(frame: Any) -> float | None:
    """Return the newest finite Yahoo close without assuming a dataframe schema beyond Close."""

    try:
        closes = frame["Close"].dropna().tolist()
    except Exception:
        return None
    for value in reversed(closes):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed) and parsed > 0:
            return parsed
    return None
