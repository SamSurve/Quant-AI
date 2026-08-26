"""Deterministic external-data services for QuantAI's typed research BFF."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re
from typing import Any

import yfinance as yf
from ddgs import DDGS

from .research_cache import AsyncTTLCache
from .research_errors import ResearchError
from .research_schemas import (
    CompanyCandidate,
    CompanyIdentity,
    ErrorCategory,
    HistoryPoint,
    IdentifierConfidence,
    MarketSnapshot,
    NewsItem,
    ServiceState,
    SourceRecord,
)


ENTITY_TTL_SECONDS = 60 * 60 * 24
MARKET_TTL_SECONDS = 60
NEWS_TTL_SECONDS = 60 * 5
EXTERNAL_TIMEOUT_SECONDS = 12
NEWS_FRESHNESS_DAYS = 30


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_stamp() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if converted == converted else None


def dividend_yield_fraction(value: Any) -> float | None:
    """Normalize yfinance's current percentage-point dividend yield to a fraction.

    QuantAI's typed market and financial contracts represent percentage metrics as
    decimal fractions (for example, 0.0035 for 0.35%). Current yfinance quote
    metadata returns dividendYield in percentage points (for example, 0.35).
    Convert only this known provider field at ingestion; null and invalid values
    remain unavailable rather than being synthesized.
    """

    normalized = _optional_float(value)
    return normalized / 100 if normalized is not None else None


def _optional_int(value: Any) -> int | None:
    converted = _optional_float(value)
    return int(converted) if converted is not None else None


def _normalize_symbol(value: str) -> str:
    return value.strip().upper().replace(" ", "")


def _normalized_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


_CORPORATE_SUFFIXES = frozenset({"ag", "co", "com", "corp", "corporation", "inc", "incorporated", "limited", "llc", "ltd", "nv", "plc", "sa"})
_COMPANY_NAME_ALIASES = {
    "google": frozenset({"alphabet"}),
    # The product explicitly supports the Indian company name / ticker shorthand
    # `TCS`; resolve it by canonical company identity rather than Yahoo rank.
    "tcs": frozenset({"tataconsultancyservices"}),
}
# A small documented search expansion is distinct from selecting an arbitrary
# Yahoo result: plain `RELIANCE` is a required product shorthand for Reliance
# Industries, whose full verified identity is then still resolved by Yahoo.
_COMPANY_SEARCH_EXPANSIONS = {
    "reliance": "Reliance Industries",
    # Tata Motors Passenger Vehicles Limited is the current NSE-listed successor
    # returned by the provider as TMPV.NS. Expand the legacy natural-name query
    # before candidate selection; the provider still supplies the verified ticker.
    "tatamotors": "Tata Motors Passenger Vehicles",
}
_PREFERRED_EXCHANGES = ("NMS", "NYQ", "NGM", "NSI", "BSE")


def _company_name_tokens(value: str | None) -> list[str]:
    """Return comparison tokens while ignoring trailing legal-form label suffixes."""

    tokens = re.findall(r"[a-z0-9]+", (value or "").lower())
    while tokens and tokens[-1] in _CORPORATE_SUFFIXES:
        tokens.pop()
    return tokens


def _canonical_company_name(value: str | None) -> str:
    """Compare company labels while ignoring only trailing legal-form suffixes."""

    return "".join(_company_name_tokens(value))


def company_search_query(query: str) -> str:
    """Expand only documented company shorthand before provider candidate search."""

    return _COMPANY_SEARCH_EXPANSIONS.get(_canonical_company_name(query), query)


def _terminal_ticker(value: str) -> str | None:
    """Return a final explicit ticker token without treating arbitrary name words as symbols."""

    parts = value.strip().split()
    if len(parts) < 2:
        return None
    candidate = _normalize_symbol(parts[-1])
    return candidate if re.fullmatch(r"[A-Z0-9.-]{1,12}", candidate) else None


def _select_preferred_listing(candidates: list[CompanyCandidate]) -> CompanyCandidate | None:
    """Choose only a unique listing from an explicit exchange preference, never list rank."""

    if len(candidates) == 1:
        return candidates[0]
    for exchange in _PREFERRED_EXCHANGES:
        exchange_matches = [candidate for candidate in candidates if candidate.exchange == exchange]
        if len(exchange_matches) == 1:
            return exchange_matches[0]
        if len(exchange_matches) > 1:
            return None
    return None


@dataclass(frozen=True)
class EntityResolution:
    company: CompanyIdentity | None
    candidates: list[CompanyCandidate]
    source: SourceRecord | None


@dataclass(frozen=True)
class MarketDataResult:
    company: CompanyIdentity
    market: MarketSnapshot | None
    history: list[HistoryPoint]
    status: ServiceState
    warning: ResearchError | None
    sources: list[SourceRecord]


@dataclass(frozen=True)
class NewsDataResult:
    items: list[NewsItem]
    status: ServiceState
    warning: ResearchError | None
    sources: list[SourceRecord]


class EntityResolutionService:
    def __init__(self, cache: AsyncTTLCache[EntityResolution] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def resolve(self, query: str) -> EntityResolution:
        normalized_query = _normalize_symbol(query)
        return (
            await self._cache.get_or_load(
                f"entity:{normalized_query}",
                ENTITY_TTL_SECONDS,
                lambda: self._resolve_uncached(query),
            )
        )[0]

    async def _resolve_uncached(self, query: str) -> EntityResolution:
        search_query = company_search_query(query)
        try:
            candidates = await asyncio.wait_for(asyncio.to_thread(self._search_candidates, search_query), timeout=EXTERNAL_TIMEOUT_SECONDS)
        except TimeoutError as error:
            raise ResearchError(ErrorCategory.TIMEOUT, detail=f"entity search timed out: {error}", retryable=True) from error
        except Exception as error:
            raise ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail=f"entity search failed: {error}", retryable=True) from error

        if not candidates:
            explicit_symbol = bool(re.fullmatch(r"[A-Z0-9.-]{1,12}", _normalize_symbol(query)))
            if explicit_symbol:
                company = CompanyIdentity(
                    symbol=_normalize_symbol(query),
                    identifier_confidence=IdentifierConfidence.MEDIUM,
                )
                return EntityResolution(
                    company=company,
                    candidates=[],
                    source=SourceRecord(source="Yahoo Finance via yfinance", retrieved_at=utc_stamp(), data_type="entity"),
                )
            raise ResearchError(ErrorCategory.ENTITY_NOT_FOUND, detail=f"no candidates for {query}")

        selected = self._select_candidate(search_query, candidates)
        if selected is None:
            raise ResearchError(ErrorCategory.AMBIGUOUS_ENTITY, detail=f"ambiguous query {query}")

        candidate, confidence = selected
        return EntityResolution(
            company=CompanyIdentity(
                symbol=candidate.symbol,
                name=candidate.name,
                exchange=candidate.exchange,
                identifier_confidence=confidence,
            ),
            candidates=candidates[:5],
            source=SourceRecord(source="Yahoo Finance via yfinance", retrieved_at=utc_stamp(), data_type="entity"),
        )

    @staticmethod
    def _search_candidates(query: str) -> list[CompanyCandidate]:
        def extract(search: Any) -> list[CompanyCandidate]:
            return [
                CompanyCandidate(
                    symbol=str(item["symbol"]).upper(),
                    name=item.get("longname") or item.get("shortname"),
                    exchange=item.get("exchange"),
                    quote_type=item.get("quoteType"),
                )
                for item in (getattr(search, "quotes", None) or [])
                if item.get("symbol") and item.get("quoteType") in {"EQUITY", "ETF", "MUTUALFUND"}
            ]

        candidates = extract(
            yf.Search(query, max_results=8, news_count=0, lists_count=0, include_cb=False, raise_errors=False)
        )
        if not candidates:
            candidates = extract(
                yf.Search(
                    query,
                    max_results=8,
                    news_count=0,
                    lists_count=0,
                    include_cb=False,
                    enable_fuzzy_query=True,
                    raise_errors=False,
                )
            )
        seen: set[str] = set()
        return [candidate for candidate in candidates if not (candidate.symbol in seen or seen.add(candidate.symbol))]

    @staticmethod
    def _select_candidate(query: str, candidates: list[CompanyCandidate]) -> tuple[CompanyCandidate, IdentifierConfidence] | None:
        normalized_symbol = _normalize_symbol(query)
        direct = [candidate for candidate in candidates if candidate.symbol == normalized_symbol]
        if len(direct) == 1:
            return direct[0], IdentifierConfidence.HIGH

        terminal_ticker = _terminal_ticker(query)
        terminal_ticker_matches = [candidate for candidate in candidates if candidate.symbol == terminal_ticker]
        if terminal_ticker and len(terminal_ticker_matches) == 1:
            return terminal_ticker_matches[0], IdentifierConfidence.HIGH

        normalized_query_name = _normalized_name(query)
        exact_name = [candidate for candidate in candidates if _normalized_name(candidate.name) == normalized_query_name]
        if len(exact_name) == 1:
            return exact_name[0], IdentifierConfidence.HIGH

        canonical_query_name = _canonical_company_name(query)
        canonical_name = [
            candidate
            for candidate in candidates
            if canonical_query_name and _canonical_company_name(candidate.name) == canonical_query_name
        ]
        preferred_canonical_name = _select_preferred_listing(canonical_name)
        if preferred_canonical_name:
            return preferred_canonical_name, IdentifierConfidence.HIGH

        alias_targets = _COMPANY_NAME_ALIASES.get(canonical_query_name, frozenset())
        alias_name = [
            candidate
            for candidate in candidates
            if _canonical_company_name(candidate.name) in alias_targets
        ]
        preferred_alias_name = _select_preferred_listing(alias_name)
        if preferred_alias_name:
            return preferred_alias_name, IdentifierConfidence.HIGH

        query_name_tokens = _company_name_tokens(query)
        prefix_name = [
            candidate
            for candidate in candidates
            if query_name_tokens and _company_name_tokens(candidate.name)[: len(query_name_tokens)] == query_name_tokens
        ]
        # A broad name prefix can match unrelated companies.  Unlike the exact
        # canonical-name and documented-alias paths above, exchange preference
        # cannot prove identity here: selecting it would quietly turn a broad
        # query such as "Reliance" into whichever candidate happens to be on a
        # preferred venue.  Resolve a prefix only when it leaves one company.
        if len(prefix_name) == 1:
            return prefix_name[0], IdentifierConfidence.HIGH

        # Do not silently select the ranked first result for company-name searches.
        # A single fuzzy candidate is useful but is marked medium confidence.
        if len(candidates) == 1:
            return candidates[0], IdentifierConfidence.MEDIUM
        return None


class MarketDataService:
    def __init__(self, cache: AsyncTTLCache[MarketDataResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> MarketDataResult:
        return (
            await self._cache.get_or_load(
                f"market:{entity.symbol}",
                MARKET_TTL_SECONDS,
                lambda: self._fetch_uncached(entity),
            )
        )[0]

    async def _fetch_uncached(self, entity: CompanyIdentity) -> MarketDataResult:
        info_task = asyncio.create_task(self._get_info(entity.symbol))
        history_task = asyncio.create_task(self._get_history(entity.symbol))
        info_result, history_result = await asyncio.gather(info_task, history_task, return_exceptions=True)

        info = info_result if isinstance(info_result, dict) else {}
        history = history_result if isinstance(history_result, list) else []
        issues = [result for result in (info_result, history_result) if isinstance(result, ResearchError)]

        if not info and not history:
            issue = issues[0] if issues else ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail="empty Yahoo response", retryable=True)
            return MarketDataResult(entity, None, [], ServiceState.UNAVAILABLE, issue, [])

        latest_close = history[-1].close if history else None
        previous_close = history[-2].close if len(history) > 1 else None
        daily_change = latest_close - previous_close if latest_close is not None and previous_close is not None else None
        daily_change_percent = (daily_change / previous_close) * 100 if daily_change is not None and previous_close not in {None, 0} else None
        quote_price = latest_close if latest_close is not None else _optional_float(info.get("currentPrice") or info.get("regularMarketPrice"))

        enriched_entity = CompanyIdentity(
            symbol=entity.symbol,
            name=info.get("longName") or info.get("shortName") or entity.name,
            exchange=info.get("exchange") or entity.exchange,
            sector=info.get("sector"),
            industry=info.get("industry"),
            currency=info.get("currency"),
            identifier_confidence=entity.identifier_confidence,
        )
        market = MarketSnapshot(
            current_price=quote_price,
            daily_change=daily_change,
            daily_change_percent=daily_change_percent,
            volume=(history[-1].volume if history else _optional_int(info.get("regularMarketVolume") or info.get("volume"))),
            market_cap=_optional_int(info.get("marketCap")),
            pe_ratio=_optional_float(info.get("trailingPE")),
            eps=_optional_float(info.get("trailingEps")),
            fifty_two_week_high=_optional_float(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_optional_float(info.get("fiftyTwoWeekLow")),
            dividend_yield=_optional_float(info.get("dividendYield")),
            market_status=info.get("marketState"),
            as_of=(history[-1].timestamp if history else utc_stamp()),
        )
        status = ServiceState.PARTIAL if issues else ServiceState.AVAILABLE
        warning = issues[0] if issues else None
        source_types = ["market"] + (["history"] if history else [])
        sources = [SourceRecord(source="Yahoo Finance via yfinance", retrieved_at=utc_stamp(), data_type=data_type) for data_type in source_types]
        return MarketDataResult(enriched_entity, market, history, status, warning, sources)

    @staticmethod
    async def _get_info(symbol: str) -> dict[str, Any] | ResearchError:
        try:
            return await asyncio.wait_for(asyncio.to_thread(lambda: yf.Ticker(symbol).info or {}), timeout=EXTERNAL_TIMEOUT_SECONDS)
        except TimeoutError as error:
            return ResearchError(ErrorCategory.TIMEOUT, detail=f"market info timeout for {symbol}: {error}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail=f"market info failed for {symbol}: {error}", retryable=True)

    @staticmethod
    async def _get_history(symbol: str) -> list[HistoryPoint] | ResearchError:
        try:
            frame = await asyncio.wait_for(
                asyncio.to_thread(lambda: yf.Ticker(symbol).history(period="1mo", interval="1d", auto_adjust=False)),
                timeout=EXTERNAL_TIMEOUT_SECONDS,
            )
        except TimeoutError as error:
            return ResearchError(ErrorCategory.TIMEOUT, detail=f"price history timeout for {symbol}: {error}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail=f"price history failed for {symbol}: {error}", retryable=True)

        points: list[HistoryPoint] = []
        for index, row in frame.tail(30).iterrows():
            timestamp = index.isoformat() if hasattr(index, "isoformat") else str(index)
            points.append(
                HistoryPoint(
                    timestamp=timestamp,
                    open=_optional_float(row.get("Open")),
                    high=_optional_float(row.get("High")),
                    low=_optional_float(row.get("Low")),
                    close=_optional_float(row.get("Close")),
                    volume=_optional_int(row.get("Volume")),
                )
            )
        return [point for point in points if point.close is not None]


class NewsService:
    def __init__(self, cache: AsyncTTLCache[NewsDataResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, company: CompanyIdentity) -> NewsDataResult:
        key = f"news:{company.symbol}"
        return (await self._cache.get_or_load(key, NEWS_TTL_SECONDS, lambda: self._fetch_uncached(company)))[0]

    async def _fetch_uncached(self, company: CompanyIdentity) -> NewsDataResult:
        query = " ".join(part for part in (company.name, company.symbol) if part)
        try:
            raw_items = await asyncio.wait_for(
                asyncio.to_thread(lambda: list(DDGS(timeout=EXTERNAL_TIMEOUT_SECONDS).news(query, max_results=8))),
                timeout=EXTERNAL_TIMEOUT_SECONDS + 1,
            )
        except TimeoutError as error:
            return NewsDataResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.TIMEOUT, detail=f"news timeout: {error}", retryable=True), [])
        except Exception as error:
            return NewsDataResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.NEWS_UNAVAILABLE, detail=f"news failed: {error}", retryable=True), [])

        items: list[NewsItem] = []
        seen: set[str] = set()
        retrieved_at = utc_now()
        cutoff = retrieved_at - timedelta(days=NEWS_FRESHNESS_DAYS)
        for raw in raw_items:
            title = str(raw.get("title") or "").strip()
            url = str(raw.get("url") or "").strip() or None
            if not title:
                continue
            key = url or _normalized_name(title)
            if key in seen:
                continue
            published_at = raw.get("date")
            parsed_date = self._parse_date(published_at, reference_time=retrieved_at)
            # A Recent News record must carry a source-provided time that can be
            # rendered honestly. Skip metadata-only results rather than showing a
            # fabricated or truncated date in the user-facing evidence lane.
            if parsed_date is None or parsed_date < cutoff:
                continue
            seen.add(key)
            items.append(
                NewsItem(
                    title=title,
                    summary=(str(raw.get("body") or "").strip() or None),
                    publisher=(str(raw.get("source") or "").strip() or None),
                    url=url,
                    published_at=parsed_date.isoformat().replace("+00:00", "Z"),
                    relevance="medium",
                )
            )
            if len(items) == 5:
                break

        sources = [
            SourceRecord(source=item.publisher or "DDGS news search", url=item.url, retrieved_at=retrieved_at.isoformat().replace("+00:00", "Z"), data_type="news")
            for item in items
        ]
        return NewsDataResult(items, ServiceState.AVAILABLE, None, sources)

    @staticmethod
    def _parse_date(value: Any, *, reference_time: datetime | None = None) -> datetime | None:
        if not value:
            return None
        raw = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            relative = re.search(r"(?P<count>\d+)\s*(?P<unit>minutes?|hours?|days?|weeks?)\s+ago\s*$", raw, flags=re.IGNORECASE)
            if not relative:
                return None
            count = int(relative.group("count"))
            unit = relative.group("unit").lower()
            delta = (
                timedelta(minutes=count) if unit.startswith("minute")
                else timedelta(hours=count) if unit.startswith("hour")
                else timedelta(days=count) if unit.startswith("day")
                else timedelta(weeks=count)
            )
            return (reference_time or utc_now()) - delta
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
