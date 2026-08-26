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
from api.research_orchestrator import AI_SYNTHESIS_CONTEXT_MAX_CHARS, AI_SYNTHESIS_CONTEXT_MAX_TOKENS, ResearchOrchestrator, bounded_ai_context_json, estimate_ai_tokens
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


def verify_bounded_ai_context() -> None:
    context = {
        "company": {"symbol": "TSLA", "name": "Tesla, Inc.", "sector": "Consumer Cyclical"},
        "market": {"current_price": 200.0, "market_cap": 1000, "pe_ratio": 20.0},
        "history": [{"timestamp": "2026-08-24", "open": 1, "high": 2, "low": 0, "close": 1, "volume": 10} for _ in range(2_000)],
        "news": [{"title": f"Material update {index}", "summary": "verified evidence " * 1_000, "url": "https://example.invalid"} for index in range(8)],
        "events": [{"event_type": "earnings", "title": "Upcoming earnings", "source": "provider"} for _ in range(8)],
        "sources": [{"source": "provider", "url": "https://example.invalid"} for _ in range(100)],
    }
    serialized = bounded_ai_context_json(context)
    bounded = json.loads(serialized)
    assert len(serialized) <= AI_SYNTHESIS_CONTEXT_MAX_CHARS
    assert estimate_ai_tokens(serialized) <= AI_SYNTHESIS_CONTEXT_MAX_TOKENS
    assert "history" not in bounded
    assert "sources" not in bounded
    assert len(bounded["news"]) <= 4
    assert all("url" not in item for item in bounded["news"])
    assert all("source" not in item for item in bounded["events"])


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

    company_name_cases = {
        "Apple": (
            [
                CompanyCandidate(symbol="AAPL", name="Apple Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="APLE", name="Apple Hospitality REIT, Inc.", exchange="NYQ", quote_type="EQUITY"),
                CompanyCandidate(symbol="APC.DE", name="Apple Inc.", exchange="GER", quote_type="EQUITY"),
            ],
            "AAPL",
        ),
        "Tesla": (
            [
                CompanyCandidate(symbol="TSLA", name="Tesla, Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="TL0.F", name="Tesla, Inc.", exchange="FRA", quote_type="EQUITY"),
            ],
            "TSLA",
        ),
        "Tesla, Inc.": (
            [
                CompanyCandidate(symbol="TSLA", name="Tesla, Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="TL0.F", name="Tesla, Inc.", exchange="FRA", quote_type="EQUITY"),
            ],
            "TSLA",
        ),
        "Tesla, Inc. TSLA": (
            [
                CompanyCandidate(symbol="TSLA", name="Tesla, Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="TL0.DE", name="Tesla, Inc.", exchange="GER", quote_type="EQUITY"),
            ],
            "TSLA",
        ),
        "Microsoft": (
            [
                CompanyCandidate(symbol="MSFT", name="Microsoft Corporation", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="MSF.DE", name="Microsoft Corporation", exchange="GER", quote_type="EQUITY"),
            ],
            "MSFT",
        ),
        "NVIDIA": (
            [
                CompanyCandidate(symbol="NVDA", name="NVIDIA Corporation", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="NVDC34.SA", name="NVIDIA Corporation", exchange="SAO", quote_type="EQUITY"),
            ],
            "NVDA",
        ),
        "Google": (
            [
                CompanyCandidate(symbol="GOOG", name="Alphabet Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="GOOP", name="Kurv Yield Premium Strategy Google ETF", exchange="BTS", quote_type="ETF"),
            ],
            "GOOG",
        ),
        "Amazon": (
            [
                CompanyCandidate(symbol="AMZN", name="Amazon.com, Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="AZFL", name="Amazonas Florestal, Ltd", exchange="PNK", quote_type="EQUITY"),
            ],
            "AMZN",
        ),
        "Meta": (
            [
                CompanyCandidate(symbol="META", name="Meta Platforms, Inc.", exchange="NMS", quote_type="EQUITY"),
                CompanyCandidate(symbol="MTA.V", name="Metalla Royalty & Streaming Ltd.", exchange="VAN", quote_type="EQUITY"),
            ],
            "META",
        ),
        "Reliance Industries": (
            [
                CompanyCandidate(symbol="RELIANCE.NS", name="Reliance Industries Limited", exchange="NSI", quote_type="EQUITY"),
                CompanyCandidate(symbol="RELIANCE.BO", name="Reliance Industries Limited", exchange="BSE", quote_type="EQUITY"),
            ],
            "RELIANCE.NS",
        ),
        "Reliance": (
            [
                CompanyCandidate(symbol="RS", name="Reliance Steel & Aluminum Co.", exchange="NYQ", quote_type="EQUITY"),
                CompanyCandidate(symbol="RELIANCE.NS", name="Reliance Industries Limited", exchange="NSI", quote_type="EQUITY"),
                CompanyCandidate(symbol="RELIANCE.BO", name="Reliance Industries Limited", exchange="BSE", quote_type="EQUITY"),
            ],
            "RELIANCE.NS",
        ),
        "Tata Motors": (
            [
                CompanyCandidate(symbol="TMCV.NS", name="Tata Motors Limited", exchange="NSI", quote_type="EQUITY"),
                CompanyCandidate(symbol="TMPV.NS", name="Tata Motors Passenger Vehicles Limited", exchange="NSI", quote_type="EQUITY"),
            ],
            "TMCV.NS",
        ),
        "TCS": (
            [
                CompanyCandidate(symbol="0221.KL", name="TCS Group Holdings Berhad", exchange="KLS", quote_type="EQUITY"),
                CompanyCandidate(symbol="TCSH.TO", name="TCS Holdings Inc.", exchange="TOR", quote_type="EQUITY"),
                CompanyCandidate(symbol="TCS.NS", name="Tata Consultancy Services Limited", exchange="NSI", quote_type="EQUITY"),
                CompanyCandidate(symbol="TCS.TO", name="TCS Transport Canada Inc.", exchange="TOR", quote_type="EQUITY"),
            ],
            "TCS.NS",
        ),
    }
    for query, (candidates, expected_symbol) in company_name_cases.items():
        resolver = EntityResolutionService()
        resolver._search_candidates = lambda _query, candidates=candidates: candidates
        resolved = await resolver.resolve(query)
        assert resolved.company and resolved.company.symbol == expected_symbol, query
        assert resolved.company.identifier_confidence == IdentifierConfidence.HIGH, query

    genuinely_ambiguous = EntityResolutionService()
    genuinely_ambiguous._search_candidates = lambda _query: [
        CompanyCandidate(symbol="ACM1", name="Acme Holdings, Inc.", exchange="NMS", quote_type="EQUITY"),
        CompanyCandidate(symbol="ACM2", name="Acme Technologies, Inc.", exchange="NMS", quote_type="EQUITY"),
    ]
    try:
        await genuinely_ambiguous.resolve("Acme")
    except ResearchError as error:
        assert error.category == ErrorCategory.AMBIGUOUS_ENTITY
    else:
        raise AssertionError("equally strong company-name candidates must remain ambiguous")

    preferred_exchange_is_not_identity = EntityResolutionService()
    preferred_exchange_is_not_identity._search_candidates = lambda _query: [
        CompanyCandidate(symbol="ACM1", name="Acme Holdings Inc.", exchange="NYQ", quote_type="EQUITY"),
        CompanyCandidate(symbol="ACM2", name="Acme Technologies Inc.", exchange="NSI", quote_type="EQUITY"),
    ]
    try:
        await preferred_exchange_is_not_identity.resolve("Acme")
    except ResearchError as error:
        assert error.category == ErrorCategory.AMBIGUOUS_ENTITY
    else:
        raise AssertionError("a preferred exchange must not select a broad company-name prefix")

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
                {"title": "Relative item", "url": "https://example.test/relative", "source": "Example", "date": "Opinion1 day ago", "body": "Relative"},
                {"title": "Old relative item", "url": "https://example.test/old-relative", "source": "Example", "date": "Opinion45 days ago", "body": "Old relative"},
                {"title": "Undated item", "url": "https://example.test/undated", "source": "Example", "date": "Editorial desk", "body": "No date"},
            ]

    original_ddgs = services_module.DDGS
    try:
        services_module.DDGS = FakeDDGS
        news = await NewsService().fetch(company())
        assert news.status == ServiceState.AVAILABLE
        assert len(news.items) == 2
        assert news.items[0].url == "https://example.test/a"
        assert news.items[1].url == "https://example.test/relative"
        assert all(item.published_at and item.published_at.endswith("Z") for item in news.items)
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
verify_bounded_ai_context()
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
