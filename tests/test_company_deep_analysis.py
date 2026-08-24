"""No-network regression tests for QuantAI Phase 5 Company Deep Analysis.

All data and analysis values are controlled fakes. This suite verifies that
typed deterministic facts remain outside the AI interpretation boundary.
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
from api.market_intelligence_services import EventRadarResult
from api.research_errors import ResearchError
from api.research_orchestrator import CompanyAnalysisSynthesisService, ResearchOrchestrator
from api.research_schemas import (
    CompanyCandidate,
    CompanyDeepAnalysisInterpretation,
    CompanyIdentity,
    CompanyOverview,
    ErrorCategory,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    GovernanceProfile,
    IdentifierConfidence,
    LeadershipMember,
    NewsItem,
    OverallState,
    ResearchEvent,
    ResearchMode,
    ResearchRequest,
    ServiceState,
    SourceRecord,
)
from api.research_services import EntityResolution, NewsDataResult


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


class FakeEntityService:
    async def resolve(self, _query: str) -> EntityResolution:
        return EntityResolution(company=company(), candidates=[CompanyCandidate(symbol="AAPL", name="Apple Inc.", exchange="NMS", quote_type="EQUITY")], source=source("entity"))


class FakeCompanyProfileService:
    async def fetch(self, entity: CompanyIdentity):
        profile = CompanyProfileResult(
            overview=CompanyOverview(company_name="Apple Inc.", ticker=entity.symbol, exchange="NMS", sector="Technology", industry="Consumer Electronics", country="United States", headquarters="Cupertino, California, United States", website="https://www.apple.com", business_description="Controlled factual profile.", employees=1000, market_cap=3_000_000, currency="USD"),
            governance=GovernanceProfile(ceo=LeadershipMember(name="Controlled CEO", title="Chief Executive Officer"), key_leadership=[LeadershipMember(name="Controlled CEO", title="Chief Executive Officer")], notable_developments=[]),
            info={"regularMarketPrice": 200.0, "regularMarketChange": 2.0, "regularMarketChangePercent": 1.01, "marketCap": 3_000_000, "trailingPE": 30.0, "trailingEps": 6.0, "currency": "USD", "exchange": "NMS"},
            company_status=ServiceState.AVAILABLE,
            governance_status=ServiceState.AVAILABLE,
            warning=None,
            company_source=source("company"),
            governance_source=source("governance"),
            retrieved_at=STAMP,
        )
        return profile, FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class MissingCompanyProfileService:
    async def fetch(self, _entity: CompanyIdentity):
        raise ResearchError(ErrorCategory.COMPANY_UNAVAILABLE, detail="controlled profile failure", retryable=True)


class FakeFinancialHealthService:
    async def fetch(self, _entity: CompanyIdentity, _profile):
        financials = FinancialHealth(revenue=1000.0, net_income=250.0, eps=6.0, profit_margin=0.25, operating_margin=0.30, free_cash_flow=300.0, total_cash=200.0, total_debt=50.0, pe_ratio=30.0, price_to_sales=3.0, dividend_yield=0.005, return_on_equity=0.40, return_on_assets=0.20, currency="USD", fiscal_period_end="2025-09-30T00:00:00Z")
        result = FinancialHealthResult(financials, ServiceState.AVAILABLE, None, source("financial"), STAMP)
        return result, FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class MissingFinancialHealthService:
    async def fetch(self, _entity: CompanyIdentity, _profile):
        result = FinancialHealthResult(None, ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail="controlled financial failure", retryable=True), None, None)
        return result, FreshnessRecord(state=FreshnessState.UNAVAILABLE)


class FakeNewsService:
    async def fetch(self, _entity: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult([NewsItem(title="Controlled news development", publisher="Example", url="https://example.test/news", published_at=STAMP, relevance="high")], ServiceState.AVAILABLE, None, [source("news")])


class FailingNewsService:
    async def fetch(self, _entity: CompanyIdentity) -> NewsDataResult:
        return NewsDataResult([], ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.NEWS_UNAVAILABLE, detail="controlled news failure", retryable=True), [])


class FakeEventService:
    async def fetch(self, _entity: CompanyIdentity):
        result = EventRadarResult([ResearchEvent(event_type="earnings_date", title="Earnings date", date="2026-10-24T00:00:00Z", importance="high", source="Controlled source")], ServiceState.AVAILABLE, None, source("event"), STAMP)
        return result, FreshnessRecord(state=FreshnessState.RECENT, retrieved_at=STAMP, cache_scope="process_local")


class FakeCompanyAnalysisService:
    async def synthesize(self, _request_id: str, _report) -> CompanyDeepAnalysisInterpretation:
        return CompanyDeepAnalysisInterpretation(
            executive_summary="Controlled analyst interpretation.",
            business_model="Controlled interpretation of validated profile data.",
            financial_health="Controlled interpretation of validated financial values.",
            growth_drivers=["Controlled interpretation driver."],
            competitive_position="Insufficient verified data.",
            key_risks=["Analyst interpretation: controlled risk."],
            catalysts=["Controlled interpretation catalyst."],
            valuation_view={"classification": "FAIRLY_VALUED", "rationale": "Analyst interpretation from supplied valuation inputs.", "evidence": ["Available valuation inputs were reviewed."]},
            recent_developments=["Controlled summary of supplied news."],
            what_to_watch=["Controlled watch item."],
            overall_assessment="Controlled assessment.",
            confidence="medium",
        )


class FailingCompanyAnalysisService:
    async def synthesize(self, _request_id: str, _report):
        raise ResearchError(ErrorCategory.AI_UNAVAILABLE, detail="controlled AI failure", retryable=True)


def deep_orchestrator(**overrides):
    defaults = {
        "entity_service": FakeEntityService(),
        "company_profile_service": FakeCompanyProfileService(),
        "financial_health_service": FakeFinancialHealthService(),
        "news_service": FakeNewsService(),
        "event_service": FakeEventService(),
        "company_analysis_service": FakeCompanyAnalysisService(),
    }
    defaults.update(overrides)
    return ResearchOrchestrator(**defaults)


async def verify_complete_company_analysis() -> None:
    response = await deep_orchestrator().research("deep-complete", ResearchRequest(query="AAPL", mode=ResearchMode.COMPANY_DEEP_ANALYSIS))
    report = response.company_deep_analysis
    assert report and report.company_overview and report.company_overview.ticker == "AAPL"
    assert report.financial_health and report.financial_health.revenue == 1000.0
    assert report.governance and report.governance.ceo and report.governance.ceo.name == "Controlled CEO"
    assert report.competitive_evidence.status == "unavailable" and not report.competitive_evidence.competitors
    assert report.analyst_interpretation and report.analyst_interpretation.valuation_view.classification == "FAIRLY_VALUED"
    assert response.market and response.market.current_price == 200.0
    assert response.status.overall == OverallState.PARTIAL  # Competitor evidence is explicitly unavailable.
    assert {item.data_type for item in response.sources} >= {"entity", "company", "governance", "financial", "news", "event", "analysis"}
    # AI cannot overwrite deterministic financial values.
    assert response.company_deep_analysis.financial_health.revenue == 1000.0


async def verify_partial_company_analysis() -> None:
    response = await deep_orchestrator(company_profile_service=MissingCompanyProfileService(), financial_health_service=MissingFinancialHealthService(), news_service=FailingNewsService(), company_analysis_service=FailingCompanyAnalysisService()).research("deep-partial", ResearchRequest(query="AAPL", mode=ResearchMode.COMPANY_DEEP_ANALYSIS))
    assert response.company_deep_analysis and response.company_deep_analysis.events
    assert response.status.company == ServiceState.UNAVAILABLE
    assert response.status.financials == ServiceState.UNAVAILABLE
    assert response.status.news == ServiceState.UNAVAILABLE
    assert response.status.ai == ServiceState.UNAVAILABLE
    assert {warning.category for warning in response.warnings} >= {ErrorCategory.COMPANY_UNAVAILABLE, ErrorCategory.FINANCIALS_UNAVAILABLE, ErrorCategory.NEWS_UNAVAILABLE, ErrorCategory.AI_UNAVAILABLE}


def verify_numeric_narrative_guard() -> None:
    interpretation = CompanyDeepAnalysisInterpretation(executive_summary="The company generated 123 units.")
    try:
        CompanyAnalysisSynthesisService._assert_no_numeric_claims(interpretation)
    except ResearchError as error:
        assert error.category == ErrorCategory.AI_UNAVAILABLE
    else:
        raise AssertionError("numeric company claim was not rejected")


asyncio.run(verify_complete_company_analysis())
asyncio.run(verify_partial_company_analysis())
verify_numeric_narrative_guard()


class RouteFakeOrchestrator:
    async def research(self, request_id: str, payload: ResearchRequest):
        return await deep_orchestrator().research(request_id, payload)


original_orchestrator = index_module.research_orchestrator
original_limiter = index_module.research_rate_limiter
try:
    index_module.research_orchestrator = RouteFakeOrchestrator()
    index_module.research_rate_limiter = index_module.SlidingWindowRateLimiter(limit=100, window_seconds=60)
    with TestClient(index_module.app) as client:
        response = client.post("/api/research", json={"query": "AAPL", "include_analysis": True, "mode": "company_deep_analysis"}, headers={"X-Request-ID": "company-deep-route"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["request_id"] == "company-deep-route"
        assert body["company_deep_analysis"]["company_overview"]["ticker"] == "AAPL"
        assert body["company_deep_analysis"]["financial_health"]["revenue"] == 1000.0
        assert body["company_deep_analysis"]["competitive_evidence"]["status"] == "unavailable"
finally:
    index_module.research_orchestrator = original_orchestrator
    index_module.research_rate_limiter = original_limiter

print("COMPANY_DEEP_ANALYSIS_REGRESSION=PASS")
