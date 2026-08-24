"""No-network Phase 6 Company Comparison regression checks.

All market, financial, news, event, and AI inputs are deterministic fakes. The
file is intentionally executable directly, matching the existing project suite.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api.index as index_module
from api.company_analysis_services import CompanyProfileResult, FinancialHealthResult
from api.comparison_services import comparison_metric
from api.market_intelligence_services import EventRadarResult, HistoryResult
from api.research_cache import AsyncTTLCache
from api.research_errors import ResearchError
from api.research_orchestrator import CompanyAnalysisSynthesisService, ResearchOrchestrator
from api.research_schemas import (
    CompanyCandidate,
    CompanyComparisonInterpretation,
    CompanyIdentity,
    CompanyOverview,
    ErrorCategory,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    HistoryPeriod,
    HistoryPoint,
    IdentifierConfidence,
    NewsItem,
    PriceHistoryBundle,
    ResearchEvent,
    ResearchMode,
    ResearchRequest,
    ServiceState,
    SourceRecord,
)
from api.research_services import EntityResolution, NewsDataResult


STAMP = "2026-08-24T00:00:00Z"


def source(data_type: str, symbol: str = "AAPL") -> SourceRecord:
    return SourceRecord(source="Controlled source", url=f"https://example.test/{symbol}/{data_type}", retrieved_at=STAMP, data_type=data_type)  # type: ignore[arg-type]


def company(symbol: str) -> CompanyIdentity:
    values = {
        "AAPL": ("Apple Inc.", "Consumer Electronics", "USD"),
        "MSFT": ("Microsoft Corporation", "Software", "USD"),
        "BMW.DE": ("Bayerische Motoren Werke AG", "Auto Manufacturers", "EUR"),
    }
    name, industry, currency = values[symbol]
    return CompanyIdentity(symbol=symbol, name=name, exchange="NMS", sector="Technology", industry=industry, currency=currency, identifier_confidence=IdentifierConfidence.HIGH)


class FakeEntityService:
    async def resolve(self, query: str) -> EntityResolution:
        symbol = {"APPLE": "AAPL", "AAPL": "AAPL", "MICROSOFT": "MSFT", "MSFT": "MSFT", "BMW": "BMW.DE", "BMW.DE": "BMW.DE"}.get(query.upper())
        if not symbol:
            raise ResearchError(ErrorCategory.ENTITY_NOT_FOUND, detail="controlled entity miss")
        identity = company(symbol)
        return EntityResolution(company=identity, candidates=[CompanyCandidate(symbol=symbol, name=identity.name, exchange="NMS", quote_type="EQUITY")], source=source("entity", symbol))


class FakeCompanyProfileService:
    async def fetch(self, entity: CompanyIdentity):
        factor = {"AAPL": 1.0, "MSFT": 0.8, "BMW.DE": 0.3}[entity.symbol]
        overview = CompanyOverview(company_name=entity.name, ticker=entity.symbol, exchange=entity.exchange, sector=entity.sector, industry=entity.industry, country="Controlled country", headquarters="Controlled headquarters", website="https://example.test", business_description="Controlled factual profile.", employees=1000, market_cap=int(3_000_000 * factor), currency=entity.currency)
        info = {"regularMarketPrice": 200 * factor, "marketCap": int(3_000_000 * factor), "trailingPE": 30 * factor, "trailingEps": 6.0, "currency": entity.currency, "exchange": entity.exchange}
        return CompanyProfileResult(overview, None, info, ServiceState.AVAILABLE, ServiceState.PARTIAL, None, source("company", entity.symbol), source("governance", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class RaisingCompanyProfileService:
    async def fetch(self, _entity: CompanyIdentity):
        raise RuntimeError("controlled unexpected profile exception")


class FakeFinancialHealthService:
    async def fetch(self, entity: CompanyIdentity, _profile):
        if entity.symbol == "AAPL":
            values = dict(revenue=1000.0, net_income=250.0, eps=6.0, profit_margin=0.25, operating_margin=0.30, free_cash_flow=300.0, total_cash=200.0, total_debt=50.0, pe_ratio=30.0, price_to_sales=3.0, dividend_yield=0.005, return_on_equity=0.40, return_on_assets=0.20, currency="USD", fiscal_period_end="2025-09-30T00:00:00Z")
        elif entity.symbol == "MSFT":
            values = dict(revenue=900.0, net_income=300.0, eps=7.0, profit_margin=0.33, operating_margin=0.40, free_cash_flow=290.0, total_cash=150.0, total_debt=70.0, pe_ratio=32.0, price_to_sales=4.0, dividend_yield=0.004, return_on_equity=0.42, return_on_assets=0.22, currency="USD", fiscal_period_end="2025-06-30T00:00:00Z")
        else:
            values = dict(revenue=600.0, net_income=80.0, eps=2.0, profit_margin=0.13, operating_margin=0.12, free_cash_flow=90.0, total_cash=80.0, total_debt=150.0, pe_ratio=8.0, price_to_sales=0.5, dividend_yield=0.03, return_on_equity=0.15, return_on_assets=0.05, currency="EUR", fiscal_period_end="2024-12-31T00:00:00Z")
        return FinancialHealthResult(FinancialHealth(**values), ServiceState.AVAILABLE, None, source("financial", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class MissingFinancialHealthService:
    async def fetch(self, _entity: CompanyIdentity, _profile):
        return FinancialHealthResult(None, ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail="controlled financial miss", retryable=True), None, None), FreshnessRecord(state=FreshnessState.UNAVAILABLE)


def history_points(rising: bool) -> list[HistoryPoint]:
    return [HistoryPoint(timestamp=f"2026-01-{(index % 28) + 1:02d}T00:00:00Z", close=(100 + index if rising else 170 - index), volume=1000 + index) for index in range(60)]


class FakeHistoryService:
    async def fetch(self, entity: CompanyIdentity):
        bundle = PriceHistoryBundle(intraday=history_points(True)[:4], daily=history_points(entity.symbol == "AAPL"), available_periods=list(HistoryPeriod), default_period=HistoryPeriod.ONE_MONTH, freshness=FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP))
        return HistoryResult(bundle, ServiceState.AVAILABLE, None, source("history", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class FakeNewsService:
    async def fetch(self, entity: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult([NewsItem(title=f"Controlled {entity.symbol} news", publisher="Example", url=f"https://example.test/{entity.symbol}/news", published_at=STAMP, relevance="high")], ServiceState.AVAILABLE, None, [source("news", entity.symbol)])


class MissingNewsService:
    async def fetch(self, _entity: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.NEWS_UNAVAILABLE, detail="controlled news miss", retryable=True), [])


class FakeEventService:
    async def fetch(self, entity: CompanyIdentity):
        event = ResearchEvent(event_type="earnings_date", title=f"{entity.symbol} controlled earnings date", date="2026-10-24T00:00:00Z", importance="high", source="Controlled source")
        return EventRadarResult([event], ServiceState.AVAILABLE, None, source("event", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.RECENT, retrieved_at=STAMP, cache_scope="process_local")


class MissingEventService:
    async def fetch(self, _entity: CompanyIdentity):
        return EventRadarResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.EVENTS_UNAVAILABLE, detail="controlled event miss", retryable=True), None, None), FreshnessRecord(state=FreshnessState.UNAVAILABLE)


class FakeComparisonAnalysisService:
    async def synthesize(self, _request_id: str, _report) -> CompanyComparisonInterpretation:
        return CompanyComparisonInterpretation(executive_summary="Controlled interpretation only.", key_difference="Controlled evidence-bound distinction.", company_a_strengths=["Controlled analyst interpretation."], company_b_strengths=["Controlled analyst interpretation."], overall_assessment="No investment recommendation.", confidence="medium")


class FailingComparisonAnalysisService:
    async def synthesize(self, _request_id: str, _report):
        raise ResearchError(ErrorCategory.AI_UNAVAILABLE, detail="controlled AI failure", retryable=True)


def comparison_orchestrator(**overrides) -> ResearchOrchestrator:
    defaults = {
        "entity_service": FakeEntityService(),
        "company_profile_service": FakeCompanyProfileService(),
        "financial_health_service": FakeFinancialHealthService(),
        "history_service": FakeHistoryService(),
        "news_service": FakeNewsService(),
        "event_service": FakeEventService(),
        "comparison_analysis_service": FakeComparisonAnalysisService(),
    }
    defaults.update(overrides)
    return ResearchOrchestrator(**defaults)


async def verify_complete_comparison() -> None:
    response = await comparison_orchestrator().research("comparison-complete", ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="AAPL", company_b="MSFT"))
    report = response.company_comparison
    assert report and report.company_a.ticker == "AAPL" and report.company_b.ticker == "MSFT"
    assert report.market_a and report.market_a.current_price == 200.0
    assert report.market_b and report.market_b.current_price == 160.0
    assert report.financial_a and report.financial_a.revenue == 1000.0
    assert report.financial_b and report.financial_b.revenue == 900.0
    assert report.company_a_news[0].title.startswith("Controlled AAPL")
    assert report.company_b_news[0].title.startswith("Controlled MSFT")
    assert report.financial_strength.company_a_score is not None and report.financial_strength.company_b_score is not None
    assert report.momentum.company_a_score is not None and report.momentum.company_b_score is not None
    revenue = next(metric for metric in report.metrics if metric.metric == "revenue")
    assert revenue.company_a_value == 1000.0 and revenue.company_b_value == 900.0
    assert revenue.period_alignment.value == "PARTIALLY_ALIGNED" and revenue.provenance_a and revenue.provenance_b
    assert report.analyst_interpretation and report.analyst_interpretation.executive_summary == "Controlled interpretation only."
    assert {item.data_type for item in response.sources} >= {"entity", "company", "financial", "history", "news", "event", "comparison", "analysis"}


def verify_currency_and_period_protection() -> None:
    foreign = comparison_metric("revenue", 100.0, 100.0, unit="currency", higher_is_better=True, currency_a="USD", currency_b="EUR", period_a="2025-09-30T00:00:00Z", period_b="2025-09-30T00:00:00Z")
    assert foreign.winner.value == "INSUFFICIENT_DATA" and foreign.difference is None and not foreign.currency_comparable
    not_aligned = comparison_metric("revenue", 100.0, 90.0, unit="currency", higher_is_better=True, currency_a="USD", currency_b="USD", period_a="2025-09-30T00:00:00Z", period_b="2024-01-01T00:00:00Z")
    assert not_aligned.winner.value == "INSUFFICIENT_DATA" and not_aligned.period_alignment.value == "NOT_ALIGNED"
    partially_aligned = comparison_metric("revenue", 100.0, 90.0, unit="currency", higher_is_better=True, currency_a="USD", currency_b="USD", period_a="2025-09-30T00:00:00Z", period_b="2025-06-30T00:00:00Z")
    assert partially_aligned.winner.value == "INSUFFICIENT_DATA" and partially_aligned.period_alignment.value == "PARTIALLY_ALIGNED"
    tie = comparison_metric("pe_ratio", 20.0, 20.0, unit="ratio", higher_is_better=False, currency_a="USD", currency_b="USD")
    assert tie.winner.value == "TIE"
    missing = comparison_metric("margin", None, 0.2, unit="percentage", higher_is_better=True, currency_a="USD", currency_b="USD")
    assert missing.winner.value == "INSUFFICIENT_DATA" and missing.availability == "partial"


async def verify_partial_sources_and_ai_failure() -> None:
    response = await comparison_orchestrator(financial_health_service=MissingFinancialHealthService(), news_service=MissingNewsService(), event_service=MissingEventService(), comparison_analysis_service=FailingComparisonAnalysisService()).research("comparison-partial", ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="AAPL", company_b="MSFT"))
    assert response.company_comparison
    assert response.status.financials == ServiceState.UNAVAILABLE
    assert response.status.news == ServiceState.UNAVAILABLE
    assert response.status.events == ServiceState.UNAVAILABLE
    assert response.status.ai == ServiceState.UNAVAILABLE
    assert {warning.category for warning in response.warnings} >= {ErrorCategory.FINANCIALS_UNAVAILABLE, ErrorCategory.NEWS_UNAVAILABLE, ErrorCategory.EVENTS_UNAVAILABLE, ErrorCategory.AI_UNAVAILABLE}


async def verify_unexpected_profile_failure_is_safe_partial_data() -> None:
    response = await comparison_orchestrator(company_profile_service=RaisingCompanyProfileService()).research("comparison-profile-exception", ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="AAPL", company_b="MSFT", include_analysis=False))
    report = response.company_comparison
    assert report and report.company_a_status.overall == ServiceState.PARTIAL and report.company_b_status.overall == ServiceState.PARTIAL
    assert {warning.category for warning in response.warnings} >= {ErrorCategory.COMPANY_UNAVAILABLE}


async def verify_cache_deduplication() -> None:
    cache: AsyncTTLCache[str] = AsyncTTLCache()
    calls = 0

    async def load() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "controlled"

    values = await asyncio.gather(*[cache.get_or_load("comparison-cache", 60, load) for _ in range(5)])
    assert calls == 1 and all(item[0] == "controlled" for item in values)


def verify_numeric_guard_and_validation() -> None:
    try:
        CompanyAnalysisSynthesisService._assert_no_numeric_claims(CompanyComparisonInterpretation(executive_summary="The comparison contains 123 values."))
    except ResearchError as error:
        assert error.category == ErrorCategory.AI_UNAVAILABLE
    else:
        raise AssertionError("numeric comparison narrative was not rejected")
    for payload in ({"mode": "company_comparison", "company_a": "AAPL"}, {"mode": "company_comparison", "company_a": "AAPL", "company_b": "AAPL"}):
        try:
            ResearchRequest.model_validate(payload)
        except ValueError:
            continue
        raise AssertionError("invalid comparison request was accepted")


async def verify_same_resolved_ticker_is_safe_validation_error() -> None:
    try:
        await comparison_orchestrator().research(
            "comparison-same-resolved-ticker",
            ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="Apple", company_b="AAPL", include_analysis=False),
        )
    except ResearchError as error:
        assert error.category == ErrorCategory.VALIDATION_ERROR
    else:
        raise AssertionError("same resolved ticker comparison was accepted")


asyncio.run(verify_complete_comparison())
verify_currency_and_period_protection()
asyncio.run(verify_partial_sources_and_ai_failure())
asyncio.run(verify_unexpected_profile_failure_is_safe_partial_data())
asyncio.run(verify_cache_deduplication())
verify_numeric_guard_and_validation()
asyncio.run(verify_same_resolved_ticker_is_safe_validation_error())


class RouteFakeOrchestrator:
    async def research(self, request_id: str, payload: ResearchRequest):
        return await comparison_orchestrator().research(request_id, payload)


original_orchestrator = index_module.research_orchestrator
original_limiter = index_module.research_rate_limiter
try:
    index_module.research_orchestrator = RouteFakeOrchestrator()
    index_module.research_rate_limiter = index_module.SlidingWindowRateLimiter(limit=100, window_seconds=60)
    with TestClient(index_module.app) as client:
        route_response = client.post("/api/research", json={"mode": "company_comparison", "company_a": "AAPL", "company_b": "MSFT", "include_analysis": True}, headers={"X-Request-ID": "comparison-route"})
        assert route_response.status_code == 200, route_response.text
        body = route_response.json()
        assert body["request_id"] == "comparison-route"
        assert body["company_comparison"]["company_a"]["ticker"] == "AAPL"
        assert body["company_comparison"]["company_b"]["ticker"] == "MSFT"
finally:
    index_module.research_orchestrator = original_orchestrator
    index_module.research_rate_limiter = original_limiter

print("COMPANY_COMPARISON_REGRESSION=PASS")
