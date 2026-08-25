"""No-network regression tests for QuantAI Phase 4 Market Intelligence.

All market/news/events and AI results below are deterministic fakes. This test
never spends provider quota or reaches public market-data endpoints.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.market_intelligence_services import (
    EventRadarResult,
    HistoryResult,
    MarketPulseResult,
    calculate_market_signal,
)
from api.research_errors import ResearchError
from api.research_orchestrator import ResearchOrchestrator
from api.research_schemas import (
    CompanyCandidate,
    CompanyIdentity,
    ErrorCategory,
    FreshnessRecord,
    FreshnessState,
    HistoryPeriod,
    HistoryPoint,
    IdentifierConfidence,
    MarketSnapshot,
    NewsItem,
    OverallState,
    PriceHistoryBundle,
    ResearchEvent,
    ResearchMode,
    ResearchRequest,
    ServiceState,
    SourceRecord,
    StructuredAnalysis,
)
from api.research_services import EntityResolution, NewsDataResult
import api.index as index_module


STAMP = "2026-08-24T00:00:00Z"


def company() -> CompanyIdentity:
    return CompanyIdentity(
        symbol="AAPL",
        name="Apple Inc.",
        exchange="NMS",
        sector="Technology",
        industry="Consumer Electronics",
        currency="USD",
        identifier_confidence=IdentifierConfidence.HIGH,
    )


def source(data_type: str) -> SourceRecord:
    return SourceRecord(source="Controlled source", url="https://example.test/source", retrieved_at=STAMP, data_type=data_type)  # type: ignore[arg-type]


def daily_history(rising: bool = True, count: int = 60) -> list[HistoryPoint]:
    return [
        HistoryPoint(
            timestamp=f"2026-01-{(index % 28) + 1:02d}T00:00:00Z",
            close=(100 + index if rising else 160 - index),
            volume=1_000 + index * 10,
        )
        for index in range(count)
    ]


class FakeEntityService:
    async def resolve(self, _query: str) -> EntityResolution:
        return EntityResolution(
            company=company(),
            candidates=[CompanyCandidate(symbol="AAPL", name="Apple Inc.", exchange="NMS", quote_type="EQUITY")],
            source=source("entity"),
        )


class FakePulseService:
    async def fetch(self, entity: CompanyIdentity):
        pulse = MarketPulseResult(
            company=entity,
            market=MarketSnapshot(
                current_price=200.0,
                currency="USD",
                daily_change=2.0,
                daily_change_percent=1.01,
                volume=2_000,
                market_cap=3_000_000,
                pe_ratio=30.0,
                eps=6.0,
                fifty_two_week_high=220.0,
                fifty_two_week_low=120.0,
                dividend_yield=0.005,
                market_status="REGULAR",
                as_of=STAMP,
            ),
            status=ServiceState.AVAILABLE,
            warning=None,
            source=source("market"),
            retrieved_at=STAMP,
        )
        return pulse, FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class FakeHistoryService:
    async def fetch(self, _entity: CompanyIdentity):
        bundle = PriceHistoryBundle(
            intraday=daily_history(count=4),
            daily=daily_history(),
            available_periods=list(HistoryPeriod),
            default_period=HistoryPeriod.ONE_MONTH,
            freshness=FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP),
        )
        result = HistoryResult(bundle, ServiceState.AVAILABLE, None, source("history"), STAMP)
        return result, FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class UnavailablePulseService:
    async def fetch(self, entity: CompanyIdentity):
        pulse = MarketPulseResult(
            company=entity,
            market=None,
            status=ServiceState.UNAVAILABLE,
            warning=ResearchError(ErrorCategory.DATA_UNAVAILABLE, detail="controlled quote metadata failure", retryable=True),
            source=None,
            retrieved_at=None,
        )
        return pulse, FreshnessRecord(state=FreshnessState.UNAVAILABLE)


class FailingHistoryService:
    async def fetch(self, _entity: CompanyIdentity):
        result = HistoryResult(None, ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.HISTORY_UNAVAILABLE, detail="controlled history failure", retryable=True), None, None)
        return result, FreshnessRecord(state=FreshnessState.UNAVAILABLE)


class FakeNewsService:
    async def fetch(self, _entity: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult(
            items=[NewsItem(title="Controlled company news", publisher="Example", url="https://example.test/news", published_at=STAMP, relevance="high")],
            status=ServiceState.AVAILABLE,
            warning=None,
            sources=[source("news")],
        )


class FailingNewsService:
    async def fetch(self, _entity: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.NEWS_UNAVAILABLE, detail="controlled news failure", retryable=True), [])


class FakeEventService:
    async def fetch(self, _entity: CompanyIdentity):
        result = EventRadarResult(
            [ResearchEvent(event_type="earnings_date", title="Earnings date", date="2026-10-24T00:00:00Z", importance="high", source="Controlled source")],
            ServiceState.AVAILABLE,
            None,
            source("event"),
            STAMP,
        )
        return result, FreshnessRecord(state=FreshnessState.RECENT, retrieved_at=STAMP, cache_scope="process_local")


class FailingEventService:
    async def fetch(self, _entity: CompanyIdentity):
        result = EventRadarResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.EVENTS_UNAVAILABLE, detail="controlled event failure", retryable=True), None, None)
        return result, FreshnessRecord(state=FreshnessState.UNAVAILABLE)


class FakeAnalysisService:
    async def synthesize(self, _research) -> StructuredAnalysis:
        return StructuredAnalysis(
            executive_summary="Controlled interpretation only.",
            what_is_happening="Observed deterministic inputs were interpreted.",
            bullish_factors=["Controlled positive factor."],
            bearish_factors=[],
            risks=["Controlled risk."],
            catalysts=["Controlled catalyst."],
            what_to_watch=["Controlled watch item."],
            market_sentiment="mixed",
            confidence="medium",
            ai_verdict="Interpretation only; no factual values were authored by AI.",
        )


class FailingAnalysisService:
    async def synthesize(self, _research) -> StructuredAnalysis:
        raise ResearchError(ErrorCategory.AI_UNAVAILABLE, detail="controlled AI failure", retryable=True)


def verify_signal_methodology() -> None:
    bullish = calculate_market_signal(daily_history(rising=True))
    bearish = calculate_market_signal(daily_history(rising=False))
    insufficient = calculate_market_signal(daily_history(count=20))
    assert bullish.signal == "BULLISH" and bullish.score is not None and bullish.score >= 60
    assert bearish.signal == "BEARISH" and bearish.score is not None and bearish.score <= 40
    assert insufficient.signal is None and insufficient.score is None and insufficient.confidence == 0
    assert "not investment advice" in bullish.methodology.lower()


async def verify_complete_market_intelligence() -> None:
    orchestrator = ResearchOrchestrator(
        entity_service=FakeEntityService(),
        market_pulse_service=FakePulseService(),
        history_service=FakeHistoryService(),
        news_service=FakeNewsService(),
        event_service=FakeEventService(),
        analysis_service=FakeAnalysisService(),
    )
    response = await orchestrator.research("mi-complete", ResearchRequest(query="AAPL", mode=ResearchMode.MARKET_INTELLIGENCE))
    assert response.market and response.market.current_price == 200.0
    assert response.market_intelligence and response.market_intelligence.market_pulse == response.market
    assert response.market_intelligence.price_history and len(response.market_intelligence.price_history.daily) == 60
    assert response.market_intelligence.market_signal and response.market_intelligence.market_signal.signal == "BULLISH"
    assert response.market_intelligence.event_radar[0].event_type == "earnings_date"
    assert response.market_intelligence.executive_brief and response.market_intelligence.executive_brief.market_sentiment == "mixed"
    assert response.status.overall == OverallState.COMPLETE
    assert {item.data_type for item in response.sources} >= {"entity", "market", "history", "news", "event", "signal", "analysis"}
    assert response.market_intelligence.freshness.market.state == FreshnessState.LIVE
    # AI cannot overwrite deterministic factual values.
    assert response.market.current_price == 200.0


async def verify_partial_failures() -> None:
    orchestrator = ResearchOrchestrator(
        entity_service=FakeEntityService(),
        market_pulse_service=FakePulseService(),
        history_service=FailingHistoryService(),
        news_service=FailingNewsService(),
        event_service=FailingEventService(),
        analysis_service=FailingAnalysisService(),
    )
    response = await orchestrator.research("mi-partial", ResearchRequest(query="AAPL", mode=ResearchMode.MARKET_INTELLIGENCE))
    assert response.market and response.market.current_price == 200.0
    assert response.status.overall == OverallState.PARTIAL
    assert response.status.history == ServiceState.UNAVAILABLE
    assert response.status.news == ServiceState.UNAVAILABLE
    assert response.status.events == ServiceState.UNAVAILABLE
    assert response.status.ai == ServiceState.UNAVAILABLE
    assert {warning.category for warning in response.warnings} >= {ErrorCategory.HISTORY_UNAVAILABLE, ErrorCategory.NEWS_UNAVAILABLE, ErrorCategory.EVENTS_UNAVAILABLE, ErrorCategory.AI_UNAVAILABLE}
    assert response.market_intelligence and response.market_intelligence.freshness.history.state == FreshnessState.UNAVAILABLE


async def verify_history_close_fallback() -> None:
    response = await ResearchOrchestrator(
        entity_service=FakeEntityService(),
        market_pulse_service=UnavailablePulseService(),
        history_service=FakeHistoryService(),
        news_service=FakeNewsService(),
        event_service=FakeEventService(),
        analysis_service=FailingAnalysisService(),
    ).research("mi-history-close-fallback", ResearchRequest(query="AAPL", mode=ResearchMode.MARKET_INTELLIGENCE))
    assert response.market and response.market.current_price == 159.0
    assert response.market.market_status == "HISTORY_CLOSE_FALLBACK"
    assert response.market.as_of == daily_history()[-1].timestamp
    assert response.status.market == ServiceState.PARTIAL
    assert response.market_intelligence and response.market_intelligence.market_pulse == response.market
    assert response.market_intelligence.freshness.market.as_of == daily_history()[-1].timestamp


verify_signal_methodology()
asyncio.run(verify_complete_market_intelligence())
asyncio.run(verify_partial_failures())
asyncio.run(verify_history_close_fallback())


class RouteFakeOrchestrator:
    async def research(self, request_id: str, payload: ResearchRequest):
        return await ResearchOrchestrator(
            entity_service=FakeEntityService(),
            market_pulse_service=FakePulseService(),
            history_service=FakeHistoryService(),
            news_service=FakeNewsService(),
            event_service=FakeEventService(),
            analysis_service=FakeAnalysisService(),
        ).research(request_id, payload)


original_orchestrator = index_module.research_orchestrator
original_limiter = index_module.research_rate_limiter
try:
    index_module.research_orchestrator = RouteFakeOrchestrator()
    index_module.research_rate_limiter = index_module.SlidingWindowRateLimiter(limit=100, window_seconds=60)
    with TestClient(index_module.app) as client:
        response = client.post(
            "/api/research",
            json={"query": "AAPL", "include_analysis": True, "mode": "market_intelligence"},
            headers={"X-Request-ID": "market-intelligence-route"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["request_id"] == "market-intelligence-route"
        assert body["market_intelligence"]["market_signal"]["signal"] == "BULLISH"
        assert body["market_intelligence"]["freshness"]["market"]["state"] == "live"
        assert body["analysis"]["executive_summary"] == "Controlled interpretation only."
        invalid_mode = client.post("/api/research", json={"query": "AAPL", "mode": "unsupported"})
        assert invalid_mode.status_code == 422
        assert invalid_mode.json()["category"] == ErrorCategory.VALIDATION_ERROR.value
finally:
    index_module.research_orchestrator = original_orchestrator
    index_module.research_rate_limiter = original_limiter

print("MARKET_INTELLIGENCE_REGRESSION=PASS")
