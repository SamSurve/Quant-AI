"""No-network regression checks for QuantAI's typed research BFF.

Run with ``PYTHONDONTWRITEBYTECODE=1 python tests/test_typed_research_backend.py``.
All external data and AI services are replaced with deterministic fakes.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api.index as index_module
from api.research_cache import AsyncTTLCache
from api.research_errors import ResearchError
from api.research_orchestrator import ResearchOrchestrator
from api.research_protection import ResearchConcurrencyGuard, SlidingWindowRateLimiter
from api.research_schemas import (
    CompanyCandidate,
    CompanyIdentity,
    ErrorCategory,
    IdentifierConfidence,
    MarketSnapshot,
    OverallState,
    ResearchRequest,
    ServiceState,
    SourceRecord,
    StructuredAnalysis,
)
import api.research_services as services_module
from api.research_services import EntityResolution, EntityResolutionService, MarketDataResult, MarketDataService, NewsDataResult, NewsService


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


class FakeEntityService:
    async def resolve(self, _query: str) -> EntityResolution:
        return EntityResolution(
            company=company(),
            candidates=[CompanyCandidate(symbol="AAPL", name="Apple Inc.", exchange="NMS", quote_type="EQUITY")],
            source=SourceRecord(source="Fake entity source", retrieved_at="2026-08-24T00:00:00Z", data_type="entity"),
        )


class FakeMarketService:
    async def fetch(self, entity: CompanyIdentity) -> MarketDataResult:
        return MarketDataResult(
            company=entity,
            market=MarketSnapshot(current_price=200.0, daily_change=2.0, daily_change_percent=1.01, as_of="2026-08-24T00:00:00Z"),
            history=[],
            status=ServiceState.AVAILABLE,
            warning=None,
            sources=[SourceRecord(source="Fake market source", retrieved_at="2026-08-24T00:00:00Z", data_type="market")],
        )


class FailingMarketService:
    async def fetch(self, entity: CompanyIdentity) -> MarketDataResult:
        return MarketDataResult(
            company=entity,
            market=None,
            history=[],
            status=ServiceState.UNAVAILABLE,
            warning=ResearchError(ErrorCategory.TIMEOUT, detail="provider time limit", retryable=True),
            sources=[],
        )


class FakeNewsService:
    async def fetch(self, _company: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult(items=[], status=ServiceState.AVAILABLE, warning=None, sources=[])


class FailingNewsService:
    async def fetch(self, _company: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult(
            items=[],
            status=ServiceState.UNAVAILABLE,
            warning=ResearchError(ErrorCategory.NEWS_UNAVAILABLE, detail="upstream news issue", retryable=True),
            sources=[],
        )


class FakeAnalysisService:
    async def synthesize(self, _research):
        return StructuredAnalysis(executive_summary="Deterministic context is available.", confidence="medium")


class MalformedAnalysisService:
    async def synthesize(self, _research):
        raise ResearchError(ErrorCategory.AI_UNAVAILABLE, detail="malformed structured output", retryable=True)


async def verify_orchestrator_partial_results() -> None:
    orchestrator = ResearchOrchestrator(
        entity_service=FakeEntityService(),
        market_service=FailingMarketService(),
        news_service=FakeNewsService(),
        analysis_service=FakeAnalysisService(),
    )
    response = await orchestrator.research("req-partial", ResearchRequest(query="AAPL"))
    assert response.status.overall == OverallState.PARTIAL
    assert response.status.market == ServiceState.UNAVAILABLE
    assert response.status.news == ServiceState.AVAILABLE
    assert response.status.ai == ServiceState.AVAILABLE
    assert response.analysis and response.analysis.executive_summary
    assert response.warnings[0].category == ErrorCategory.TIMEOUT


async def verify_malformed_ai_is_partial_not_failure() -> None:
    orchestrator = ResearchOrchestrator(
        entity_service=FakeEntityService(),
        market_service=FakeMarketService(),
        news_service=FailingNewsService(),
        analysis_service=MalformedAnalysisService(),
    )
    response = await orchestrator.research("req-ai", ResearchRequest(query="AAPL"))
    assert response.market and response.market.current_price == 200.0
    assert response.status.news == ServiceState.UNAVAILABLE
    assert response.status.ai == ServiceState.UNAVAILABLE
    assert {warning.category for warning in response.warnings} == {ErrorCategory.NEWS_UNAVAILABLE, ErrorCategory.AI_UNAVAILABLE}


async def verify_cache_and_inflight_deduplication() -> None:
    cache: AsyncTTLCache[int] = AsyncTTLCache()
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return 7

    first, second = await asyncio.gather(
        cache.get_or_load("aapl", 60, loader),
        cache.get_or_load("aapl", 60, loader),
    )
    third = await cache.get_or_load("aapl", 60, loader)
    assert calls == 1
    assert first == (7, False)
    assert second == (7, False)
    assert third == (7, True)


async def verify_entity_validation_and_ambiguity() -> None:
    direct = EntityResolutionService()
    direct._search_candidates = lambda _query: [CompanyCandidate(symbol="AAPL", name="Apple Inc.", exchange="NMS", quote_type="EQUITY")]
    resolved = await direct.resolve("AAPL")
    assert resolved.company and resolved.company.symbol == "AAPL"
    assert resolved.company.identifier_confidence == IdentifierConfidence.HIGH

    ambiguous = EntityResolutionService()
    ambiguous._search_candidates = lambda _query: [
        CompanyCandidate(symbol="APLE", name="Apple Hospitality REIT", exchange="NYQ", quote_type="EQUITY"),
        CompanyCandidate(symbol="AAPL", name="Apple Inc.", exchange="NMS", quote_type="EQUITY"),
    ]
    try:
        await ambiguous.resolve("Apple")
    except ResearchError as error:
        assert error.category == ErrorCategory.AMBIGUOUS_ENTITY
    else:
        raise AssertionError("ambiguous company must not silently select the first candidate")

    invalid = EntityResolutionService()
    invalid._search_candidates = lambda _query: []
    try:
        await invalid.resolve("not a listed company")
    except ResearchError as error:
        assert error.category == ErrorCategory.ENTITY_NOT_FOUND
    else:
        raise AssertionError("invalid company must be classified safely")


async def verify_market_and_news_adapters() -> None:
    market_service = MarketDataService()

    async def fake_info(_symbol: str):
        return {"longName": "Apple Inc.", "currency": "USD", "marketCap": 1000, "trailingPE": 20.0}

    async def fake_history(_symbol: str):
        return [
            services_module.HistoryPoint(timestamp="2026-08-22T00:00:00Z", close=198.0, volume=10),
            services_module.HistoryPoint(timestamp="2026-08-23T00:00:00Z", close=200.0, volume=11),
        ]

    market_service._get_info = fake_info
    market_service._get_history = fake_history
    market = await market_service.fetch(company())
    assert market.status == ServiceState.AVAILABLE
    assert market.market and market.market.current_price == 200.0
    assert market.market.daily_change == 2.0

    class FakeDDGS:
        def __init__(self, timeout: int):
            assert timeout > 0

        def news(self, _query: str, max_results: int):
            assert max_results == 8
            return [
                {"title": "Apple update", "url": "https://example.test/a", "source": "Example", "date": "2026-08-24T00:00:00Z", "body": "Summary"},
                {"title": "Apple update", "url": "https://example.test/a", "source": "Example", "date": "2026-08-24T00:00:00Z", "body": "Duplicate"},
                {"title": "Old item", "url": "https://example.test/old", "source": "Example", "date": "2020-01-01T00:00:00Z", "body": "Old"},
            ]

    original_ddgs = services_module.DDGS
    try:
        services_module.DDGS = FakeDDGS
        news = await NewsService().fetch(company())
        assert news.status == ServiceState.AVAILABLE
        assert len(news.items) == 1
        assert news.items[0].url == "https://example.test/a"
    finally:
        services_module.DDGS = original_ddgs


async def verify_request_protection() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60)
    await limiter.check("client")
    try:
        await limiter.check("client")
    except ResearchError as error:
        assert error.category == ErrorCategory.RATE_LIMITED
    else:
        raise AssertionError("rate limiter must safely reject an over-limit request")

    guard = ResearchConcurrencyGuard(max_concurrent=1)
    async with guard.acquire():
        try:
            async with guard.acquire():
                raise AssertionError("unreachable")
        except ResearchError as error:
            assert error.category == ErrorCategory.RATE_LIMITED


asyncio.run(verify_orchestrator_partial_results())
asyncio.run(verify_malformed_ai_is_partial_not_failure())
asyncio.run(verify_cache_and_inflight_deduplication())
asyncio.run(verify_entity_validation_and_ambiguity())
asyncio.run(verify_market_and_news_adapters())
asyncio.run(verify_request_protection())


class RouteFakeOrchestrator:
    async def research(self, request_id: str, payload: ResearchRequest):
        return await ResearchOrchestrator(
            entity_service=FakeEntityService(),
            market_service=FakeMarketService(),
            news_service=FakeNewsService(),
            analysis_service=FakeAnalysisService(),
        ).research(request_id, payload)


original_orchestrator = index_module.research_orchestrator
original_limiter = index_module.research_rate_limiter
try:
    index_module.research_orchestrator = RouteFakeOrchestrator()
    index_module.research_rate_limiter = index_module.SlidingWindowRateLimiter(limit=100, window_seconds=60)
    with TestClient(index_module.app) as client:
        valid = client.post("/api/research", json={"query": "AAPL", "include_analysis": True}, headers={"X-Request-ID": "audit-request-1"})
        assert valid.status_code == 200, valid.text
        valid_body = valid.json()
        assert valid.headers["X-Request-ID"] == "audit-request-1"
        assert valid_body["request_id"] == "audit-request-1"
        assert valid_body["company"]["symbol"] == "AAPL"
        assert valid_body["market"]["current_price"] == 200.0
        assert "GROQ_API_KEY_PRIMARY" not in json.dumps(valid_body)
        assert "GROQ_API_KEY_SECONDARY" not in json.dumps(valid_body)
        assert "OPENROUTER_API_KEY" not in json.dumps(valid_body)

        prefix_stripped = client.post("/research", json={"query": "AAPL", "include_analysis": False})
        assert prefix_stripped.status_code == 200, prefix_stripped.text
        assert prefix_stripped.json()["status"]["ai"] == ServiceState.NOT_REQUESTED.value

        invalid = client.post("/api/research", json={"query": ""})
        assert invalid.status_code == 422
        assert invalid.json()["category"] == ErrorCategory.VALIDATION_ERROR.value
        assert "errors" not in invalid.json()

        oversized = client.post("/api/research", content=b"x", headers={"content-length": "9000", "content-type": "application/json"})
        assert oversized.status_code == 422
        assert oversized.json()["category"] == ErrorCategory.VALIDATION_ERROR.value

        oversized_json = client.post("/api/research", json={"query": "A" * 9_000})
        assert oversized_json.status_code == 422
        assert oversized_json.json()["category"] == ErrorCategory.VALIDATION_ERROR.value

        index_module.research_rate_limiter = index_module.SlidingWindowRateLimiter(limit=1, window_seconds=60)
        first_limited = client.post("/api/research", json={"query": "MSFT"}, headers={"X-Forwarded-For": "203.0.113.5"})
        second_limited = client.post("/api/research", json={"query": "MSFT"}, headers={"X-Forwarded-For": "203.0.113.5"})
        assert first_limited.status_code == 200
        assert second_limited.status_code == 429
        assert second_limited.json()["category"] == ErrorCategory.RATE_LIMITED.value

        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["typed_research"]["path"] == "/api/research"
finally:
    index_module.research_orchestrator = original_orchestrator
    index_module.research_rate_limiter = original_limiter


print("TYPED_RESEARCH_BACKEND_REGRESSION=PASS")
