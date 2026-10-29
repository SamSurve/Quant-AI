"""Deterministic Market Intelligence adapters for QuantAI.

All facts originate in yfinance/Yahoo data and are returned with source and
freshness context. This module never calls an LLM and never converts missing
data into a synthetic value.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, TypeVar

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
from .research_services import EXTERNAL_TIMEOUT_SECONDS, _optional_float, _optional_int, dividend_yield_fraction, utc_stamp

LOGGER = logging.getLogger("quantai.market")

MARKET_PULSE_TTL_SECONDS = 60
HISTORY_TTL_SECONDS = 60 * 5
EVENTS_TTL_SECONDS = 60 * 60 * 6
HISTORY_MAX_DAILY_POINTS = 1_300
HISTORY_MAX_INTRADAY_POINTS = 160

T = TypeVar("T")


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


def normalize_symbol(symbol: str) -> str:
    """Normalize and validate ticker symbol format.

    Rejects invalid characters, spaces inside, and empty input where a symbol is required.
    Enforces the symbol length limit (1 to 16 characters).
    Preserves legitimate symbols including exchange suffixes (.NS, .BO, .HK, .L),
    index carets (^GSPC, ^IXIC), futures/currency signs (GC=F, EURUSD=X), and share classes (BRK.B, BRK-A).

    Raises:
        ValueError: If symbol is empty, exceeds 16 chars, or contains invalid characters.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Ticker symbol cannot be empty.")
    clean = symbol.strip().upper()
    if not clean:
        raise ValueError("Ticker symbol cannot be empty.")
    if len(clean) > 16:
        raise ValueError(f"Ticker symbol exceeds 16 characters: {clean[:20]}...")
    if not re.fullmatch(r"^[A-Z0-9.\-=^]{1,16}$", clean):
        raise ValueError(f"Invalid ticker symbol format: {clean!r}")
    return clean


def slice_history(bundle: PriceHistoryBundle, period: str | HistoryPeriod) -> list[HistoryPoint]:
    """Slice price history bundle points to the requested time horizon."""
    if isinstance(period, str):
        period_str = period.upper()
    else:
        period_str = period.value

    if period_str in ("1D", HistoryPeriod.ONE_DAY.value):
        if bundle.intraday:
            return bundle.intraday
        return bundle.daily[-1:] if bundle.daily else []

    daily = bundle.daily or []
    if not daily:
        return []

    PERIOD_LIMITS: dict[str, int] = {
        "1W": 5,
        "1M": 22,
        "3M": 65,
        "6M": 130,
        "1Y": 252,
        "5Y": len(daily),
    }
    limit = PERIOD_LIMITS.get(period_str, 22)
    return daily[-limit:]


async def _call_with_retry(
    operation: Callable[[], T],
    *,
    op_name: str,
    symbol: str,
    timeout: float = EXTERNAL_TIMEOUT_SECONDS,
    max_retries: int = 1,
    base_delay: float = 0.25,
) -> T:
    """Execute a provider operation with bounded retries and exponential backoff for transient failures."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(asyncio.to_thread(operation), timeout=timeout)
        except TimeoutError as err:
            last_error = err
            LOGGER.warning("%s_timeout symbol=%s attempt=%d/%d", op_name, symbol, attempt + 1, max_retries + 1)
        except Exception as err:
            last_error = err
            # Distinguish transient vs permanent errors
            err_str = str(err).lower()
            if "rate limit" in err_str or "too many requests" in err_str or "429" in err_str or "503" in err_str or "connection" in err_str:
                LOGGER.warning("%s_transient_error symbol=%s attempt=%d/%d err=%s", op_name, symbol, attempt + 1, max_retries + 1, type(err).__name__)
            else:
                # Permanent or client error; do not retry
                break

        if attempt < max_retries:
            await asyncio.sleep(base_delay * (2 ** attempt))

    if isinstance(last_error, TimeoutError):
        raise TimeoutError(f"{op_name} timeout for {symbol}") from last_error
    raise last_error if last_error else RuntimeError(f"{op_name} failed for {symbol}")


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
        try:
            sym = normalize_symbol(entity.symbol)
        except ValueError as err:
            now = utc_stamp()
            return MarketPulseResult(
                entity,
                None,
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.VALIDATION_ERROR, detail=str(err), retryable=False),
                None,
                now,
            ), unavailable_freshness()
        result, cache_hit = await self._cache.get_or_load(
            f"market-pulse:{sym}",
            MARKET_PULSE_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at, result.market.as_of if result.market else None)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> MarketPulseResult:
        sym = normalize_symbol(entity.symbol)
        info_result = await self._info(sym)
        info = info_result if isinstance(info_result, dict) else {}
        issue = info_result if isinstance(info_result, ResearchError) else None

        if not info:
            return MarketPulseResult(
                entity,
                None,
                ServiceState.UNAVAILABLE,
                issue or ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail="market response empty", retryable=True),
                None,
                None,
            )

        now = utc_stamp()
        enriched = CompanyIdentity(
            symbol=sym,
            name=info.get("longName") or info.get("shortName") or entity.name,
            exchange=info.get("exchange") or entity.exchange,
            sector=info.get("sector") or entity.sector,
            industry=info.get("industry") or entity.industry,
            currency=info.get("currency") or entity.currency,
            identifier_confidence=entity.identifier_confidence,
        )

        current_price = _optional_float(info.get("regularMarketPrice") or info.get("currentPrice"))
        if current_price is not None and (current_price <= 0 or math.isnan(current_price) or math.isinf(current_price)):
            current_price = None

        market = MarketSnapshot(
            current_price=current_price,
            currency=info.get("currency") or entity.currency or "USD",
            daily_change=_optional_float(info.get("regularMarketChange")),
            daily_change_percent=_optional_float(info.get("regularMarketChangePercent")),
            volume=_optional_int(info.get("regularMarketVolume") or info.get("volume")),
            market_cap=_optional_int(info.get("marketCap")),
            pe_ratio=_optional_float(info.get("trailingPE")),
            eps=_optional_float(info.get("trailingEps")),
            fifty_two_week_high=_optional_float(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_optional_float(info.get("fiftyTwoWeekLow")),
            dividend_yield=dividend_yield_fraction(info.get("dividendYield")),
            market_status=info.get("marketState"),
            as_of=now,
        )
        return MarketPulseResult(enriched, market, ServiceState.AVAILABLE, None, _source("market", sym, now), now)

    @staticmethod
    async def _info(symbol: str) -> dict[str, Any] | ResearchError:
        try:
            return await _call_with_retry(
                lambda: yf.Ticker(symbol).info or {},
                op_name="market_pulse_info",
                symbol=symbol,
                timeout=EXTERNAL_TIMEOUT_SECONDS,
                max_retries=1,
            )
        except TimeoutError:
            return ResearchError(ErrorCategory.TIMEOUT, detail=f"market pulse timeout for {symbol}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail=f"market pulse unavailable for {symbol}: {type(error).__name__}", retryable=True)

    @staticmethod
    async def _history_frame(symbol: str, *, period: str, interval: str) -> Any | ResearchError:
        try:
            return await _call_with_retry(
                lambda: yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=False),
                op_name=f"history_frame_{period}_{interval}",
                symbol=symbol,
                timeout=EXTERNAL_TIMEOUT_SECONDS,
                max_retries=1,
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
        try:
            sym = normalize_symbol(entity.symbol)
        except ValueError as err:
            now = utc_stamp()
            return HistoryResult(
                None,
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.VALIDATION_ERROR, detail=str(err), retryable=False),
                None,
                now,
            ), unavailable_freshness()
        result, cache_hit = await self._cache.get_or_load(
            f"market-history:{sym}",
            HISTORY_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> HistoryResult:
        sym = normalize_symbol(entity.symbol)
        daily_task = asyncio.create_task(MarketPulseService._history_frame(sym, period="5y", interval="1d"))
        intraday_task = asyncio.create_task(MarketPulseService._history_frame(sym, period="1d", interval="5m"))
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
            available_periods.extend([
                HistoryPeriod.ONE_WEEK,
                HistoryPeriod.ONE_MONTH,
                HistoryPeriod.THREE_MONTHS,
                HistoryPeriod.SIX_MONTHS,
                HistoryPeriod.ONE_YEAR,
                HistoryPeriod.FIVE_YEARS,
            ])

        bundle = PriceHistoryBundle(
            intraday=intraday,
            daily=daily,
            available_periods=available_periods,
            default_period=HistoryPeriod.ONE_MONTH if daily else HistoryPeriod.ONE_DAY,
            freshness=_freshness(False, now),
        )
        warning = issues[0] if issues else None
        return HistoryResult(
            bundle,
            ServiceState.PARTIAL if warning else ServiceState.AVAILABLE,
            warning,
            _source("history", sym, now),
            now,
        )


class EventRadarService:
    """Expose only calendar values that the source actually returns."""

    def __init__(self, cache: AsyncTTLCache[EventRadarResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> tuple[EventRadarResult, FreshnessRecord]:
        try:
            sym = normalize_symbol(entity.symbol)
        except ValueError as err:
            now = utc_stamp()
            return EventRadarResult(
                [],
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.VALIDATION_ERROR, detail=str(err), retryable=False),
                None,
                now,
            ), unavailable_freshness()
        result, cache_hit = await self._cache.get_or_load(
            f"event-radar:{sym}",
            EVENTS_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> EventRadarResult:
        sym = normalize_symbol(entity.symbol)
        try:
            calendar = await _call_with_retry(
                lambda: yf.Ticker(sym).calendar or {},
                op_name="event_radar_calendar",
                symbol=sym,
                timeout=EXTERNAL_TIMEOUT_SECONDS,
                max_retries=1,
            )
        except TimeoutError:
            return EventRadarResult(
                [],
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.TIMEOUT, detail=f"event radar timeout for {sym}", retryable=True),
                None,
                None,
            )
        except Exception as error:
            return EventRadarResult(
                [],
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.EVENTS_UNAVAILABLE, detail=f"event radar unavailable for {sym}: {type(error).__name__}", retryable=True),
                None,
                None,
            )

        now = utc_stamp()
        events: list[ResearchEvent] = []
        for key, title, importance in (
            ("Earnings Date", "Earnings date", "high"),
            ("Ex-Dividend Date", "Ex-dividend date", "medium"),
            ("Dividend Date", "Dividend date", "medium"),
        ):
            value = calendar.get(key) if isinstance(calendar, dict) else None
            for date in _event_dates(value):
                events.append(ResearchEvent(
                    event_type=key.lower().replace(" ", "_"),
                    title=title,
                    date=date,
                    importance=importance,
                    source="Yahoo Finance via yfinance",
                ))

        deduped = _deduplicate_events(events)
        return EventRadarResult(deduped[:6], ServiceState.AVAILABLE, None, _source("event", sym, now), now)


def calculate_market_signal(history: list[HistoryPoint]) -> MarketSignal:
    """Explainable 0-100 score using observed closes/volume, not model output."""
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
            factors.append(f"Latest volume is {volume_ratio:.1f}x the 20-session average.")

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


# Global shared instances for backend & UI reuse
default_market_pulse_service = MarketPulseService()
default_price_history_service = PriceHistoryService()
default_event_radar_service = EventRadarService()
