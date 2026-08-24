"""Deterministic Market Intelligence adapters for QuantAI Phase 4.

All facts originate in yfinance/Yahoo data and are returned with source and
freshness context. This module never calls an LLM and never converts missing
data into a synthetic value.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yfinance as yf

from .research_cache import AsyncTTLCache
from .research_errors import ResearchError
from .research_schemas import (
    CompanyIdentity,
    ErrorCategory,
    FreshnessRecord,
    FreshnessState,
    HistoryPeriod,
    HistoryPoint,
    MarketSignal,
    MarketSnapshot,
    PriceHistoryBundle,
    ResearchEvent,
    ServiceState,
    SourceRecord,
)
from .research_services import EXTERNAL_TIMEOUT_SECONDS, _optional_float, _optional_int, utc_stamp


MARKET_PULSE_TTL_SECONDS = 60
HISTORY_TTL_SECONDS = 60 * 5
EVENTS_TTL_SECONDS = 60 * 60 * 6
HISTORY_MAX_DAILY_POINTS = 1_300
HISTORY_MAX_INTRADAY_POINTS = 160


def _quote_url(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol}"


def _source(data_type: str, symbol: str, retrieved_at: str) -> SourceRecord:
    return SourceRecord(
        source="Yahoo Finance via yfinance",
        url=_quote_url(symbol),
        retrieved_at=retrieved_at,
        data_type=data_type,  # type: ignore[arg-type]
    )


def _freshness(cache_hit: bool, retrieved_at: str | None, as_of: str | None = None) -> FreshnessRecord:
    return FreshnessRecord(
        state=FreshnessState.CACHED if cache_hit else FreshnessState.LIVE,
        retrieved_at=retrieved_at,
        as_of=as_of or retrieved_at,
        cache_scope="process_local" if cache_hit else "none",
    )


def unavailable_freshness() -> FreshnessRecord:
    return FreshnessRecord(state=FreshnessState.UNAVAILABLE, cache_scope="none")


@dataclass(frozen=True)
class MarketPulseResult:
    company: CompanyIdentity
    market: MarketSnapshot | None
    status: ServiceState
    warning: ResearchError | None
    source: SourceRecord | None
    retrieved_at: str | None


@dataclass(frozen=True)
class HistoryResult:
    history: PriceHistoryBundle | None
    status: ServiceState
    warning: ResearchError | None
    source: SourceRecord | None
    retrieved_at: str | None


@dataclass(frozen=True)
class EventRadarResult:
    events: list[ResearchEvent]
    status: ServiceState
    warning: ResearchError | None
    source: SourceRecord | None
    retrieved_at: str | None


class MarketPulseService:
    """Fetch quote metadata and a small daily window for trustworthy day change."""

    def __init__(self, cache: AsyncTTLCache[MarketPulseResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> tuple[MarketPulseResult, FreshnessRecord]:
        result, cache_hit = await self._cache.get_or_load(
            f"market-pulse:{entity.symbol}",
            MARKET_PULSE_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at, result.market.as_of if result.market else None)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> MarketPulseResult:
        info_result = await self._info(entity.symbol)
        info = info_result if isinstance(info_result, dict) else {}
        issue = info_result if isinstance(info_result, ResearchError) else None

        if not info:
            return MarketPulseResult(entity, None, ServiceState.UNAVAILABLE, issue or ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail="market response empty", retryable=True), None, None)

        now = utc_stamp()
        enriched = CompanyIdentity(
            symbol=entity.symbol,
            name=info.get("longName") or info.get("shortName") or entity.name,
            exchange=info.get("exchange") or entity.exchange,
            sector=info.get("sector") or entity.sector,
            industry=info.get("industry") or entity.industry,
            currency=info.get("currency") or entity.currency,
            identifier_confidence=entity.identifier_confidence,
        )
        market = MarketSnapshot(
            current_price=_optional_float(info.get("regularMarketPrice") or info.get("currentPrice")),
            currency=info.get("currency") or entity.currency,
            daily_change=_optional_float(info.get("regularMarketChange")),
            daily_change_percent=_optional_float(info.get("regularMarketChangePercent")),
            volume=_optional_int(info.get("regularMarketVolume") or info.get("volume")),
            market_cap=_optional_int(info.get("marketCap")),
            pe_ratio=_optional_float(info.get("trailingPE")),
            eps=_optional_float(info.get("trailingEps")),
            fifty_two_week_high=_optional_float(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_optional_float(info.get("fiftyTwoWeekLow")),
            dividend_yield=_optional_float(info.get("dividendYield")),
            market_status=info.get("marketState"),
            as_of=now,
        )
        return MarketPulseResult(enriched, market, ServiceState.AVAILABLE, None, _source("market", entity.symbol, now), now)

    @staticmethod
    async def _info(symbol: str) -> dict[str, Any] | ResearchError:
        try:
            return await asyncio.wait_for(asyncio.to_thread(lambda: yf.Ticker(symbol).info or {}), timeout=EXTERNAL_TIMEOUT_SECONDS)
        except TimeoutError as error:
            return ResearchError(ErrorCategory.TIMEOUT, detail=f"market pulse timeout for {symbol}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail=f"market pulse unavailable for {symbol}: {type(error).__name__}", retryable=True)

    @staticmethod
    async def _history_frame(symbol: str, *, period: str, interval: str) -> Any | ResearchError:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(lambda: yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=False)),
                timeout=EXTERNAL_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return ResearchError(ErrorCategory.TIMEOUT, detail=f"history timeout for {symbol}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.HISTORY_UNAVAILABLE, detail=f"history unavailable for {symbol}: {type(error).__name__}", retryable=True)


class PriceHistoryService:
    """One 5-year daily and one intraday fetch; all shorter periods are derived locally."""

    def __init__(self, cache: AsyncTTLCache[HistoryResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> tuple[HistoryResult, FreshnessRecord]:
        result, cache_hit = await self._cache.get_or_load(
            f"market-history:{entity.symbol}",
            HISTORY_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> HistoryResult:
        daily_task = asyncio.create_task(MarketPulseService._history_frame(entity.symbol, period="5y", interval="1d"))
        intraday_task = asyncio.create_task(MarketPulseService._history_frame(entity.symbol, period="1d", interval="5m"))
        daily_result, intraday_result = await asyncio.gather(daily_task, intraday_task, return_exceptions=True)
        daily = _frame_to_points(daily_result, limit=HISTORY_MAX_DAILY_POINTS) if not isinstance(daily_result, BaseException) else []
        intraday = _frame_to_points(intraday_result, limit=HISTORY_MAX_INTRADAY_POINTS) if not isinstance(intraday_result, BaseException) else []
        issues = [item for item in (daily_result, intraday_result) if isinstance(item, ResearchError)]
        now = utc_stamp()
        if not daily and not intraday:
            issue = issues[0] if issues else ResearchError(ErrorCategory.HISTORY_UNAVAILABLE, detail="history response empty", retryable=True)
            return HistoryResult(None, ServiceState.UNAVAILABLE, issue, None, None)
        available_periods = [HistoryPeriod.ONE_DAY] if intraday else []
        if daily:
            available_periods.extend([HistoryPeriod.ONE_WEEK, HistoryPeriod.ONE_MONTH, HistoryPeriod.THREE_MONTHS, HistoryPeriod.SIX_MONTHS, HistoryPeriod.ONE_YEAR, HistoryPeriod.FIVE_YEARS])
        bundle = PriceHistoryBundle(
            intraday=intraday,
            daily=daily,
            available_periods=available_periods,
            default_period=HistoryPeriod.ONE_MONTH if daily else HistoryPeriod.ONE_DAY,
            freshness=_freshness(False, now),
        )
        warning = issues[0] if issues else None
        return HistoryResult(bundle, ServiceState.PARTIAL if warning else ServiceState.AVAILABLE, warning, _source("history", entity.symbol, now), now)


class EventRadarService:
    """Expose only calendar values that the source actually returns."""

    def __init__(self, cache: AsyncTTLCache[EventRadarResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> tuple[EventRadarResult, FreshnessRecord]:
        result, cache_hit = await self._cache.get_or_load(
            f"event-radar:{entity.symbol}",
            EVENTS_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> EventRadarResult:
        try:
            calendar = await asyncio.wait_for(asyncio.to_thread(lambda: yf.Ticker(entity.symbol).calendar or {}), timeout=EXTERNAL_TIMEOUT_SECONDS)
        except TimeoutError:
            return EventRadarResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.TIMEOUT, detail=f"event radar timeout for {entity.symbol}", retryable=True), None, None)
        except Exception as error:
            return EventRadarResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.EVENTS_UNAVAILABLE, detail=f"event radar unavailable for {entity.symbol}: {type(error).__name__}", retryable=True), None, None)

        now = utc_stamp()
        events: list[ResearchEvent] = []
        for key, title, importance in (
            ("Earnings Date", "Earnings date", "high"),
            ("Ex-Dividend Date", "Ex-dividend date", "medium"),
            ("Dividend Date", "Dividend date", "medium"),
        ):
            value = calendar.get(key) if isinstance(calendar, dict) else None
            for date in _event_dates(value):
                events.append(ResearchEvent(event_type=key.lower().replace(" ", "_"), title=title, date=date, importance=importance, source="Yahoo Finance via yfinance"))
        deduped = _deduplicate_events(events)
        return EventRadarResult(deduped[:6], ServiceState.AVAILABLE, None, _source("event", entity.symbol, now), now)


def calculate_market_signal(history: list[HistoryPoint]) -> MarketSignal:
    """Explainable 0–100 score using observed closes/volume, not model output."""

    rows = [point for point in history if point.close is not None]
    if len(rows) < 21:
        return MarketSignal(
            signal=None,
            score=None,
            confidence=0,
            explanation="Insufficient daily price history for a deterministic trend signal.",
        )

    closes = [float(point.close) for point in rows]
    volumes = [float(point.volume) for point in rows if point.volume is not None]
    latest = closes[-1]
    score = 50
    factors: list[str] = []
    momentum_20 = (latest / closes[-21] - 1) * 100
    if momentum_20 >= 2:
        score += 18
        factors.append(f"20-session momentum is positive ({momentum_20:.1f}%).")
    elif momentum_20 <= -2:
        score -= 18
        factors.append(f"20-session momentum is negative ({momentum_20:.1f}%).")
    else:
        factors.append(f"20-session momentum is limited ({momentum_20:.1f}%).")

    ma20 = sum(closes[-20:]) / 20
    if latest > ma20:
        score += 12
        factors.append("Latest close is above the 20-session average.")
    else:
        score -= 12
        factors.append("Latest close is below the 20-session average.")

    if len(closes) >= 50:
        ma50 = sum(closes[-50:]) / 50
        if ma20 > ma50:
            score += 10
            factors.append("20-session average is above the 50-session average.")
        else:
            score -= 10
            factors.append("20-session average is below the 50-session average.")

    returns = [(closes[index] / closes[index - 1] - 1) for index in range(max(1, len(closes) - 20), len(closes))]
    volatility = math.sqrt(sum(value * value for value in returns) / len(returns)) * math.sqrt(252) * 100 if returns else None
    if volatility is not None:
        factors.append(f"20-session annualized realized volatility is {volatility:.1f}%.")

    if len(volumes) >= 20 and rows[-1].volume is not None:
        average_volume = sum(volumes[-20:]) / 20
        volume_ratio = float(rows[-1].volume) / average_volume if average_volume else None
        if volume_ratio is not None and volume_ratio >= 1.2:
            score += 5 if momentum_20 >= 0 else -5
            factors.append(f"Latest volume is {volume_ratio:.1f}× the 20-session average.")

    score = max(0, min(100, score))
    signal = "BULLISH" if score >= 60 else "BEARISH" if score <= 40 else "NEUTRAL"
    confidence = min(90, 45 + min(len(closes), 60) // 2 + (10 if len(volumes) >= 20 else 0))
    return MarketSignal(
        signal=signal,
        score=score,
        confidence=confidence,
        factors=factors[:6],
        explanation="Score begins at 50 and adjusts for 20-session momentum, price versus moving averages, trend alignment, and unusually high volume. Volatility is disclosed as context rather than treated as directional.",
    )


def _frame_to_points(frame: Any, *, limit: int) -> list[HistoryPoint]:
    if frame is None or isinstance(frame, ResearchError) or getattr(frame, "empty", True):
        return []
    points: list[HistoryPoint] = []
    for index, row in frame.tail(limit).iterrows():
        timestamp = index.isoformat() if hasattr(index, "isoformat") else str(index)
        point = HistoryPoint(
            timestamp=timestamp,
            open=_optional_float(row.get("Open")),
            high=_optional_float(row.get("High")),
            low=_optional_float(row.get("Low")),
            close=_optional_float(row.get("Close")),
            volume=_optional_int(row.get("Volume")),
        )
        if point.close is not None:
            points.append(point)
    return points


def _event_dates(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    dates: list[str] = []
    for item in values:
        if hasattr(item, "isoformat"):
            stamp = item.isoformat()
        else:
            stamp = str(item).strip()
        if stamp and stamp.lower() not in {"nan", "none"}:
            dates.append(stamp.replace("+00:00", "Z"))
    return dates


def _deduplicate_events(events: list[ResearchEvent]) -> list[ResearchEvent]:
    seen: set[tuple[str, str | None]] = set()
    return [event for event in events if not ((key := (event.event_type, event.date)) in seen or seen.add(key))]
