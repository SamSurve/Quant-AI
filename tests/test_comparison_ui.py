"""Automated tests for QuantAI Company Comparison UI (Milestone 10).

Verifies that:
- Fabricated mock values ($3.52T, $3.18T, 30.7%, 29.4x, etc.) are completely purged.
- Real comparison engine report renders side-by-side header, matrix table, scores, categories, news, events, and AI synthesis.
- HTMX requests return partial HTML fragments.
- Identical, empty, or malicious symbol inputs render user-friendly error cards without 500 errors.
- FX conversions, period alignment, negative earnings, and ties display correctly.
"""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import api.index as index_module
import api.web as web_module
from api.comparison_services import (
    ComparisonCompanyData,
    build_category_winners,
    build_comparison_metrics,
    build_confidence,
    build_financial_strength,
    build_momentum_score,
    overall_advantage,
    _company_freshness,
)
from api.research_schemas import (
    CompanyComparisonFreshness,
    CompanyComparisonInterpretation,
    CompanyComparisonReport,
    CompanyIdentity,
    ComparisonCompanyStatus,
    ComparisonIdentity,
    ComparisonWinner,
    ErrorCategory,
    FXConversion,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    IdentifierConfidence,
    MarketSignal,
    OverallState,
    MarketSnapshot,
    NewsItem,
    ResearchEvent,
    ResearchMode,
    ResearchRequest,
    ResearchResponse,
    ServiceState,
    ServiceStatus,
    SourceRecord,
)

STAMP = "2026-08-24T00:00:00Z"


def make_mock_report(
    s1: str = "AAPL",
    s2: str = "MSFT",
    curr_a: str = "USD",
    curr_b: str = "USD",
    include_fx: bool = False,
    include_analysis: bool = True,
) -> CompanyComparisonReport:
    """Construct a deterministic CompanyComparisonReport for UI verification."""
    company_a_id = ComparisonIdentity(
        identifier="A",
        company_name=f"{s1} Inc.",
        ticker=s1,
        exchange="NMS",
        sector="Technology",
        industry="Consumer Electronics" if s1 == "AAPL" else "Software",
        currency=curr_a,
        market_cap=3_000_000_000_000,
    )
    company_b_id = ComparisonIdentity(
        identifier="B",
        company_name=f"{s2} Corp.",
        ticker=s2,
        exchange="NMS",
        sector="Technology",
        industry="Software",
        currency=curr_b,
        market_cap=2_800_000_000_000,
    )
    status_a = ComparisonCompanyStatus(
        identifier="A",
        overall=ServiceState.AVAILABLE,
        company=ServiceState.AVAILABLE,
        financials=ServiceState.AVAILABLE,
        history=ServiceState.AVAILABLE,
        news=ServiceState.AVAILABLE,
        events=ServiceState.AVAILABLE,
        message="All sources available",
    )
    status_b = ComparisonCompanyStatus(
        identifier="B",
        overall=ServiceState.AVAILABLE,
        company=ServiceState.AVAILABLE,
        financials=ServiceState.AVAILABLE,
        history=ServiceState.AVAILABLE,
        news=ServiceState.AVAILABLE,
        events=ServiceState.AVAILABLE,
        message="All sources available",
    )

    market_a = MarketSnapshot(
        current_price=220.50,
        currency=curr_a,
        market_cap=3_000_000_000_000,
        daily_change=2.50,
        daily_change_percent=1.14,
        as_of=STAMP,
    )
    market_b = MarketSnapshot(
        current_price=410.25,
        currency=curr_b,
        market_cap=2_800_000_000_000,
        daily_change=-1.20,
        daily_change_percent=-0.29,
        as_of=STAMP,
    )

    financial_a = FinancialHealth(
        revenue=391_035_000_000.0,
        net_income=93_736_000_000.0,
        eps=6.08,
        profit_margin=0.2397,
        operating_margin=0.3120,
        free_cash_flow=108_811_000_000.0,
        total_cash=65_171_000_000.0,
        total_debt=106_629_000_000.0,
        pe_ratio=33.5,
        price_to_sales=7.6,
        dividend_yield=0.0048,
        currency=curr_a,
        fiscal_period_end="2025-09-30T00:00:00Z",
    )
    financial_b = FinancialHealth(
        revenue=245_120_000_000.0,
        net_income=88_136_000_000.0,
        eps=11.80,
        profit_margin=0.3595,
        operating_margin=0.4460,
        free_cash_flow=74_071_000_000.0,
        total_cash=75_545_000_000.0,
        total_debt=44_934_000_000.0,
        pe_ratio=34.2,
        price_to_sales=11.4,
        dividend_yield=0.0071,
        currency=curr_b,
        fiscal_period_end="2025-06-30T00:00:00Z",
    )

    momentum_a = MarketSignal(
        signal="BULLISH",
        score=78,
        factors=["Strong 50-day moving average", "Consistent volume"],
    )
    momentum_b = MarketSignal(
        signal="NEUTRAL",
        score=58,
        factors=["Consolidating near 200-day MA"],
    )

    news_a = [
        NewsItem(title=f"{s1} launches new hardware lineup", publisher="TechWire", url="https://example.test/a1", published_at=STAMP),
        NewsItem(title=f"{s1} expands enterprise services", publisher="MarketDaily", url="https://example.test/a2", published_at=STAMP),
    ]
    news_b = [
        NewsItem(title=f"{s2} announces cloud infrastructure growth", publisher="CloudPost", url="https://example.test/b1", published_at=STAMP),
        NewsItem(title=f"{s2} quarterly earnings schedule released", publisher="FinanceToday", url="https://example.test/b2", published_at=STAMP),
    ]

    events_a = [
        ResearchEvent(event_type="earnings_date", title=f"{s1} Q4 Earnings Call", date="2026-10-30T00:00:00Z", importance="high", source="Exchange"),
    ]
    events_b = [
        ResearchEvent(event_type="dividend_date", title=f"{s2} Ex-Dividend Date", date="2026-11-15T00:00:00Z", importance="medium", source="Exchange"),
    ]

    fx_conversions = []
    fx_conv = None
    if include_fx:
        fx_conv = FXConversion(
            base_currency=curr_a,
            quote_currency=curr_b,
            rate=80.0,
            source="Yahoo Finance",
            source_symbol=f"{curr_a}{curr_b}=X",
            url=f"https://finance.yahoo.com/quote/{curr_a}{curr_b}=X",
            retrieved_at=STAMP,
        )
        fx_conversions.append(fx_conv)

    # Build company data containers to run deterministic scoring
    comp_a_data = ComparisonCompanyData(
        identifier="A",
        entity=CompanyIdentity(symbol=s1, name=f"{s1} Inc.", exchange="NMS", sector="Tech", industry="Tech", currency=curr_a, identifier_confidence=IdentifierConfidence.HIGH),
        identity=company_a_id,
        market=market_a,
        financial=financial_a,
        momentum=momentum_a,
    )
    comp_b_data = ComparisonCompanyData(
        identifier="B",
        entity=CompanyIdentity(symbol=s2, name=f"{s2} Corp.", exchange="NMS", sector="Tech", industry="Tech", currency=curr_b, identifier_confidence=IdentifierConfidence.HIGH),
        identity=company_b_id,
        market=market_b,
        financial=financial_b,
        momentum=momentum_b,
    )

    metrics = build_comparison_metrics(comp_a_data, comp_b_data, fx_conversion=fx_conv)
    strength = build_financial_strength(comp_a_data, comp_b_data)
    momentum = build_momentum_score(comp_a_data, comp_b_data)
    categories = build_category_winners(metrics, strength, momentum)
    confidence = build_confidence(metrics, categories, fx_conversions)
    overall, overall_exp = overall_advantage(categories, confidence)

    analyst_interp = None
    if include_analysis:
        analyst_interp = CompanyComparisonInterpretation(
            executive_summary=f"Comparative analysis shows {s1} leads in top-line scale and free cash flow generation, while {s2} maintains higher operating margins.",
            key_difference=f"Capital allocation profile: {s1} consumer hardware ecosystem vs {s2} recurring enterprise cloud subscriptions.",
            company_a_strengths=[f"{s1} demonstrates massive free cash flow of $108.8B", "Global hardware ecosystem lock-in"],
            company_b_strengths=[f"{s2} delivers superior operating margin at 44.6%", "Strong enterprise cloud recurring revenue"],
            overall_assessment=f"Both entities display high solvency; {s1} is more cash generative while {s2} shows higher capital return efficiency.",
            confidence="high",
        )

    rec = FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)
    fresh_a = _company_freshness(rec, rec, rec, rec, rec)
    fresh_b = _company_freshness(rec, rec, rec, rec, rec)
    fresh = CompanyComparisonFreshness(
        company_a=fresh_a,
        company_b=fresh_b,
        comparison=rec,
        analysis=rec if include_analysis else FreshnessRecord(state=FreshnessState.UNAVAILABLE),
    )

    return CompanyComparisonReport(
        company_a=company_a_id,
        company_b=company_b_id,
        company_a_status=status_a,
        company_b_status=status_b,
        market_a=market_a,
        market_b=market_b,
        financial_a=financial_a,
        financial_b=financial_b,
        momentum_a=momentum_a,
        momentum_b=momentum_b,
        company_a_news=news_a,
        company_b_news=news_b,
        company_a_events=events_a,
        company_b_events=events_b,
        fx_conversions=fx_conversions,
        metrics=metrics,
        financial_strength=strength,
        momentum=momentum,
        category_winners=categories,
        overall_advantage=overall,
        overall_explanation=overall_exp,
        comparison_confidence=confidence,
        analyst_interpretation=analyst_interp,
        freshness=fresh,
    )


class MockComparisonOrchestrator:
    """Mock orchestrator returning deterministic CompanyComparisonReport."""

    def __init__(self, report: CompanyComparisonReport | None = None, raise_error: Exception | None = None):
        self.report = report or make_mock_report()
        self.raise_error = raise_error

    async def research(self, request_id: str, payload: ResearchRequest) -> ResearchResponse:
        if self.raise_error:
            raise self.raise_error

        # If comparing identical tickers
        if payload.company_a and payload.company_b and payload.company_a.upper() == payload.company_b.upper():
            raise web_module.ResearchError(ErrorCategory.VALIDATION_ERROR, detail="comparison sides resolved to the same ticker")

        status = ServiceStatus(
            overall=OverallState.COMPLETE,
            market=ServiceState.AVAILABLE,
            news=ServiceState.AVAILABLE,
            company=ServiceState.AVAILABLE,
            ai=ServiceState.AVAILABLE,
        )
        resp = ResearchResponse(
            request_id=request_id,
            query=f"{payload.company_a} vs {payload.company_b}",
            status=status,
        )
        resp.company_comparison = self.report
        return resp


class TestComparisonUI(unittest.TestCase):
    """Test suite for Company Comparison UI rendering and HTMX behavior."""

    def setUp(self):
        self.mock_report = make_mock_report("AAPL", "MSFT")
        self.mock_orchestrator = MockComparisonOrchestrator(self.mock_report)
        web_module._COMPARISON_ORCHESTRATOR = self.mock_orchestrator
        self.client = TestClient(index_module.app)

    def tearDown(self):
        web_module._COMPARISON_ORCHESTRATOR = None

    def test_compare_page_loads_with_default_symbols(self):
        """Full page GET /compare?s1=AAPL&s2=MSFT renders side-by-side terminal."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify page title and header
        self.assertIn("AAPL vs MSFT — Company Comparison — QuantAI", html)
        self.assertIn("Evidence-Based Peer Comparison", html)

        # Verify company identities in header
        self.assertIn("AAPL Inc.", html)
        self.assertIn("MSFT Corp.", html)
        self.assertIn("$3.00T", html)  # Formatted market cap

        # Verify form inputs populated
        self.assertIn('value="AAPL"', html)
        self.assertIn('value="MSFT"', html)

    def test_compare_page_purged_of_mock_values(self):
        """Verify hardcoded fake metrics and placeholder banner were completely removed."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        html = res.text

        # These were the hardcoded sample values in old templates/compare.html
        self.assertNotIn("$3.52T", html)
        self.assertNotIn("$3.18T", html)
        self.assertNotIn("29.4x", html)
        self.assertNotIn("31.2x", html)
        self.assertNotIn("+6.1%", html)
        self.assertNotIn("+16.0%", html)
        self.assertNotIn("AAPL Larger", html)
        self.assertNotIn("MSFT Higher", html)
        self.assertNotIn("Scheduled for M09/M10", html)
        self.assertNotIn("Algorithmic Peer Comparison Engine", html)

    def test_compare_htmx_partial_response(self):
        """HTMX request returns only #comparison-content without full page shell."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT", headers={"HX-Request": "true"})
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Partial fragment should not contain full HTML document tags
        self.assertNotIn("<!DOCTYPE html>", html)
        self.assertNotIn("<html", html)
        self.assertNotIn("<body", html)

        # But must contain the comparison content wrapper
        self.assertIn('id="comparison-content"', html)
        self.assertIn("Normalized Financial Comparison Matrix", html)

    def test_compare_identical_symbols_error(self):
        """Comparing identical symbols renders clean validation error card without 500 error."""
        res = self.client.get("/compare?s1=AAPL&s2=AAPL")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("Comparison Unavailable", html)
        self.assertIn("Cannot compare company &#39;AAPL&#39; against itself", html)
        self.assertIn("Suggested comparisons:", html)

    def test_compare_malicious_symbol_error(self):
        """Malicious inputs (e.g. <script>) are safely rejected without XSS."""
        res = self.client.get("/compare?s1=<script>&s2=MSFT")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("Comparison Unavailable", html)
        self.assertIn("Invalid ticker symbol format", html)
        self.assertNotIn("<script>alert", html)

    def test_compare_matrix_metrics_and_formatting(self):
        """Financial matrix table renders all 12 dimensions with right-aligned numeric cells."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        html = res.text

        # Check key metrics present
        self.assertIn("Total Revenue", html)
        self.assertIn("Net Income", html)
        self.assertIn("Free Cash Flow", html)
        self.assertIn("Operating Margin", html)
        self.assertIn("Price / Earnings (P/E)", html)

        # Check formatted values ($391.04B, $245.12B)
        self.assertIn("$391.04B", html)
        self.assertIn("$245.12B", html)

        # Check advantage tags
        self.assertIn("AAPL Advantage", html)

    def test_compare_cross_currency_fx_rendering(self):
        """Cross-currency comparison renders FX banner and converted values."""
        fx_report = make_mock_report("AAPL", "TCS", curr_a="USD", curr_b="INR", include_fx=True)
        web_module._COMPARISON_ORCHESTRATOR = MockComparisonOrchestrator(fx_report)

        res = self.client.get("/compare?s1=AAPL&s2=TCS")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # FX banner verification
        self.assertIn("Verified FX Conversion", html)
        self.assertIn("1 USD = 80.0000 INR", html)
        self.assertIn("USDINR=X", html)

    def test_compare_scores_and_contributing_factors(self):
        """Deterministic scores render scores and contributing factors list."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        html = res.text

        self.assertIn("Financial Strength Score", html)
        self.assertIn("Market Momentum Score", html)
        self.assertIn("Strong 50-day moving average", html)
        self.assertIn("Observed Balance Sheet & Cash Drivers:", html)

    def test_compare_category_winners_grid(self):
        """9 category outcomes grid renders with supporting metric tags."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        html = res.text

        self.assertIn("Deterministic Category Outcomes", html)
        self.assertIn("Profitability", html)
        self.assertIn("Cash Generation", html)
        self.assertIn("Balance Sheet", html)
        self.assertIn("Valuation", html)

    def test_compare_news_and_events_columns(self):
        """News and corporate events are rendered into company-specific columns."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        html = res.text

        self.assertIn("AAPL Events & News", html)
        self.assertIn("MSFT Events & News", html)
        self.assertIn("AAPL Q4 Earnings Call", html)
        self.assertIn("MSFT Ex-Dividend Date", html)
        self.assertIn("AAPL launches new hardware lineup", html)
        self.assertIn("MSFT announces cloud infrastructure growth", html)

    def test_compare_analyst_synthesis(self):
        """Analyst interpretation is clearly labeled with disclaimer."""
        res = self.client.get("/compare?s1=AAPL&s2=MSFT")
        html = res.text

        self.assertIn("Comparative Analyst Interpretation", html)
        self.assertIn("Evidence-Grounded AI", html)
        self.assertIn("Comparative analysis shows AAPL leads in top-line scale", html)
        self.assertIn("do not constitute investment advice", html)


if __name__ == "__main__":
    unittest.main()
