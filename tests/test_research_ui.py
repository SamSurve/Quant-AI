"""Automated tests for QuantAI Dedicated AI Research Desk UI (Milestone 12).

Verifies that:
- /research renders a dedicated, typed workspace supporting all 4 backend research modes:
    1. standard
    2. company_deep_analysis
    3. market_intelligence
    4. company_comparison
- HTMX requests return partial HTML fragments (#research-content) without <html>/<body> shells.
- Error alerts handle empty queries, identical comparison symbols, and disallowed/XSS characters safely.
- AI failure displays graceful warning banner while preserving deterministic market data and sources.
- Verified SourceRecord evidence stream renders real citations and flags internal records cleanly.
- Old placeholder texts ("Phase 5 AI Research Desk integration pending") are completely removed.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import api.index as index_module
import api.web as web_module
from api.research_schemas import (
    CompanyDeepAnalysisFreshness,
    CompanyDeepAnalysisInterpretation,
    CompanyDeepAnalysisReport,
    CompanyComparisonFreshness,
    CompanyComparisonInterpretation,
    CompanyComparisonReport,
    CompanyIdentity,
    CompanyOverview,
    CompanyValuationView,
    ComparisonCompanyStatus,
    ComparisonConfidence,
    ComparisonIdentity,
    ComparisonScore,
    ComparisonWinner,
    CompetitiveEvidence,
    ErrorCategory,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    GovernanceProfile,
    HistoryPeriod,
    IdentifierConfidence,
    LeadershipMember,
    MarketIntelligenceFreshness,
    MarketIntelligenceReport,
    MarketSignal,
    MarketSnapshot,
    NewsItem,
    OverallState,
    PriceHistoryBundle,
    ResearchEvent,
    ResearchMode,
    ResearchRequest,
    ResearchResponse,
    ResearchWarning,
    ServiceState,
    ServiceStatus,
    SourceRecord,
    StructuredAnalysis,
)
from tests.test_comparison_ui import make_mock_report as make_mock_comparison_report

STAMP = "2026-08-24T16:00:00Z"


def make_standard_response(symbol: str = "AAPL", ai_available: bool = True) -> ResearchResponse:
    company = CompanyIdentity(
        symbol=symbol,
        name="Apple Inc." if symbol == "AAPL" else f"{symbol} Inc.",
        exchange="NASDAQ",
        sector="Technology",
        industry="Consumer Electronics",
        currency="USD",
        identifier_confidence=IdentifierConfidence.HIGH,
    )
    market = MarketSnapshot(
        current_price=225.50,
        currency="USD",
        daily_change=2.75,
        daily_change_percent=1.23,
        volume=54300000,
        as_of=STAMP,
    )
    analysis = None
    if ai_available:
        analysis = StructuredAnalysis(
            market_sentiment="positive",
            confidence="high",
            executive_summary=f"{symbol} exhibits robust free cash flow generation and high-margin services expansion.",
            what_is_happening="Resilient operational momentum with growing installed base across premium segments.",
            bullish_factors=[
                "Active device installed base exceeding 2.2 billion units",
                "High-margin recurring revenue stream growing double-digits",
            ],
            bearish_factors=[
                "Extended consumer replacement cycles in mature markets",
                "App store regulatory scrutiny in major jurisdictions",
            ],
            catalysts=[
                "Next annual developer conference announcement",
                "Q4 fiscal earnings report",
            ],
            risks=[
                "Geopolitical supply-chain concentration",
                "Currency volatility against strong USD",
            ],
            what_to_watch=["Services revenue gross margin trajectory", "Gross margin guidance"],
            ai_verdict=f"Solid enterprise quality with sustained cash generation profile for {symbol}.",
        )

    news = [
        NewsItem(
            title=f"{symbol} Expands Enterprise AI Developer Ecosystem",
            summary=f"Key enterprise developments announced for {symbol} platform.",
            publisher="Financial Times",
            url="https://ft.com/example-news-1",
            published_at="2026-08-24T12:00:00Z",
            relevance="high",
            sentiment="positive",
        ),
    ]

    events = [
        ResearchEvent(
            event_type="Earnings",
            title=f"{symbol} Q4 2026 Earnings Release",
            date="2026-10-28",
            importance="high",
            source="IR Calendar",
        ),
    ]

    sources = [
        SourceRecord(
            source="yfinance",
            url=f"https://finance.yahoo.com/quote/{symbol}",
            retrieved_at=STAMP,
            data_type="market",
        ),
        SourceRecord(
            source="sec_edgar",
            url=None,
            retrieved_at=STAMP,
            data_type="financial",
        ),
    ]

    status = ServiceStatus(
        overall=OverallState.COMPLETE if ai_available else OverallState.PARTIAL,
        market=ServiceState.AVAILABLE,
        news=ServiceState.AVAILABLE,
        company=ServiceState.AVAILABLE,
        ai=ServiceState.AVAILABLE if ai_available else ServiceState.UNAVAILABLE,
    )

    return ResearchResponse(
        request_id=f"test-res-{symbol.lower()}",
        query=symbol,
        company=company,
        market=market,
        news=news,
        events=events,
        analysis=analysis,
        sources=sources,
        status=status,
    )


def make_deep_analysis_response(symbol: str = "NVDA") -> ResearchResponse:
    company = CompanyIdentity(
        symbol=symbol,
        name="NVIDIA Corporation" if symbol == "NVDA" else f"{symbol} Corporation",
        exchange="NASDAQ",
        sector="Technology",
        industry="Semiconductors",
        currency="USD",
        identifier_confidence=IdentifierConfidence.HIGH,
    )
    rec = FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)
    freshness = CompanyDeepAnalysisFreshness(
        company=rec,
        financials=rec,
        governance=rec,
        competitors=rec,
        market=rec,
        news=rec,
        events=rec,
        analysis=rec,
    )
    overview = CompanyOverview(
        company_name="NVIDIA Corporation" if symbol == "NVDA" else f"{symbol} Corporation",
        ticker=symbol,
        exchange="NASDAQ",
        sector="Technology",
        industry="Semiconductors",
        country="United States",
        headquarters="Santa Clara, CA",
    )
    health = FinancialHealth(
        revenue=96_300_000_000,
        net_income=53_000_000_000,
        pe_ratio=45.2,
        price_to_sales=33.2,
        profit_margin=0.55,
        operating_margin=0.62,
        free_cash_flow=40_000_000_000,
        currency="USD",
    )
    governance = GovernanceProfile(
        ceo=LeadershipMember(name="Jensen Huang", title="President & CEO", since=1993),
        key_leadership=[
            LeadershipMember(name="Colette Kress", title="EVP & CFO", since=2013),
        ],
    )
    interpretation = CompanyDeepAnalysisInterpretation(
        executive_summary=f"{symbol} maintains commanding market share in datacenter accelerated computing architectures.",
        growth_drivers=["Hyperscale cloud Capex expansion", "Enterprise sovereign AI cluster deployment"],
        key_risks=["Customer concentration among top 4 cloud providers", "Export control restrictions"],
        confidence="high",
        valuation_view=CompanyValuationView(
            classification="FAIRLY_VALUED",
            rationale="Premium multiple supported by 70%+ gross margins and structural datacenter backlog.",
        ),
    )
    report = CompanyDeepAnalysisReport(
        company_overview=overview,
        financial_health=health,
        governance=governance,
        competitive_evidence=CompetitiveEvidence(status="available", competitors=["AMD", "INTC"]),
        analyst_interpretation=interpretation,
        freshness=freshness,
    )

    sources = [
        SourceRecord(
            source="sec_edgar",
            url="https://sec.gov/edgar/searchedgar/companysearch",
            retrieved_at=STAMP,
            data_type="financial",
        ),
        SourceRecord(
            source="quantai_governance",
            url=None,
            retrieved_at=STAMP,
            data_type="governance",
        ),
    ]

    status = ServiceStatus(
        overall=OverallState.COMPLETE,
        market=ServiceState.AVAILABLE,
        news=ServiceState.AVAILABLE,
        company=ServiceState.AVAILABLE,
        ai=ServiceState.AVAILABLE,
    )

    resp = ResearchResponse(
        request_id=f"test-da-{symbol.lower()}",
        query=symbol,
        company=company,
        company_deep_analysis=report,
        sources=sources,
        status=status,
    )
    return resp


def make_market_intelligence_response(symbol: str = "MSFT") -> ResearchResponse:
    company = CompanyIdentity(
        symbol=symbol,
        name=f"{symbol} Corporation",
        exchange="NASDAQ",
        sector="Technology",
        industry="Software - Infrastructure",
        currency="USD",
        identifier_confidence=IdentifierConfidence.HIGH,
    )
    rec = FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)
    freshness = MarketIntelligenceFreshness(
        company=rec,
        market=rec,
        history=rec,
        news=rec,
        events=rec,
        analysis=rec,
    )
    pulse = MarketSnapshot(
        current_price=415.80,
        currency="USD",
        daily_change=3.40,
        daily_change_percent=0.82,
        volume=18400000,
        as_of=STAMP,
    )
    signal = MarketSignal(
        signal="BULLISH",
        score=78,
        confidence=85,
        factors=["20-day SMA trading above 50-day SMA", "Relative strength indicator at 62 (constructive momentum)"],
        explanation="Multi-timeframe trend alignment indicates sustained upward price momentum.",
    )
    events = [
        ResearchEvent(
            event_type="Conference",
            title="Ignite Technology Keynote",
            date="2026-11-15",
            importance="high",
            source="Corporate Events",
        ),
    ]
    report = MarketIntelligenceReport(
        market_pulse=pulse,
        price_history=PriceHistoryBundle(
            intraday=[],
            daily=[],
            available_periods=[HistoryPeriod.ONE_MONTH, HistoryPeriod.ONE_YEAR],
            freshness=rec,
        ),
        market_signal=signal,
        event_radar=events,
        freshness=freshness,
    )

    sources = [
        SourceRecord(
            source="market_pulse_feed",
            url="https://finance.yahoo.com/quote/MSFT",
            retrieved_at=STAMP,
            data_type="market",
        ),
    ]

    status = ServiceStatus(
        overall=OverallState.COMPLETE,
        market=ServiceState.AVAILABLE,
        news=ServiceState.AVAILABLE,
        company=ServiceState.AVAILABLE,
        ai=ServiceState.AVAILABLE,
    )

    return ResearchResponse(
        request_id=f"test-mi-{symbol.lower()}",
        query=symbol,
        company=company,
        market=pulse,
        market_intelligence=report,
        sources=sources,
        status=status,
    )


class MockResearchOrchestrator:
    """Mock orchestrator dispatching responses across all 4 research modes."""

    def __init__(self, raise_error: Exception | None = None):
        self.raise_error = raise_error
        self.ai_available = True

    async def research(self, request_id: str, request: ResearchRequest) -> ResearchResponse:
        if self.raise_error:
            raise self.raise_error

        if request.mode == ResearchMode.COMPANY_COMPARISON:
            if request.company_a and request.company_b and request.company_a.upper() == request.company_b.upper():
                raise web_module.ResearchError(
                    ErrorCategory.VALIDATION_ERROR,
                    detail="comparison sides resolved to the same ticker",
                )
            report = make_mock_comparison_report(request.company_a or "AAPL", request.company_b or "MSFT")
            status = ServiceStatus(
                overall=OverallState.COMPLETE,
                market=ServiceState.AVAILABLE,
                news=ServiceState.AVAILABLE,
                company=ServiceState.AVAILABLE,
                ai=ServiceState.AVAILABLE,
            )
            return ResearchResponse(
                request_id=request_id,
                query=f"{request.company_a} vs {request.company_b}",
                company_comparison=report,
                sources=[
                    SourceRecord(
                        source="yfinance",
                        url="https://finance.yahoo.com/quote/AAPL",
                        retrieved_at=STAMP,
                        data_type="comparison",
                    )
                ],
                status=status,
            )

        if request.mode == ResearchMode.COMPANY_DEEP_ANALYSIS:
            return make_deep_analysis_response(request.query or "NVDA")

        if request.mode == ResearchMode.MARKET_INTELLIGENCE:
            return make_market_intelligence_response(request.query or "MSFT")

        # Standard mode
        return make_standard_response(request.query or "AAPL", ai_available=self.ai_available)


class TestResearchUI(unittest.TestCase):
    """Test suite for Dedicated AI Research Desk UI rendering and HTMX behavior."""

    def setUp(self):
        self.mock_orchestrator = MockResearchOrchestrator()
        web_module._RESEARCH_ORCHESTRATOR = self.mock_orchestrator
        self.client = TestClient(index_module.app)

    def tearDown(self):
        web_module._RESEARCH_ORCHESTRATOR = None

    def test_research_initial_empty_state_load(self):
        """GET /research with no parameters loads workstation empty state."""
        res = self.client.get("/research")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify page title and header
        self.assertIn("AI Research Desk — QuantAI", html)
        self.assertIn("Dedicated AI Research Desk", html)
        self.assertIn("WORKSTATION READY", html)
        self.assertIn("Evidence-Grounded AI Research Desk", html)

        # Verify 4 modes exist in the selector
        self.assertIn("Standard Thesis", html)
        self.assertIn("Deep Analysis", html)
        self.assertIn("Market Intelligence", html)
        self.assertIn("Peer Comparison", html)

        # Verify curated starter pills
        self.assertIn("AAPL (Standard)", html)
        self.assertIn("NVDA (Deep Analysis)", html)
        self.assertIn("MSFT (Market Intel)", html)
        self.assertIn("AAPL vs MSFT (Comparison)", html)

    def test_research_standard_mode_full_page(self):
        """GET /research?query=AAPL&mode=standard renders standard thesis and market snapshot."""
        res = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify entity badge and market snapshot
        self.assertIn("Apple Inc.", html)
        self.assertIn("AAPL", html)
        self.assertIn("$225.50", html)
        self.assertIn("+2.75", html)

        # Verify AI synthesis card
        self.assertIn("Evidence-Grounded AI Research Synthesis", html)
        self.assertIn("Sentiment: POSITIVE", html)
        self.assertIn("Confidence: HIGH", html)
        self.assertIn("Active device installed base exceeding 2.2 billion units", html)
        self.assertIn("App store regulatory scrutiny in major jurisdictions", html)

        # Verify sources table
        self.assertIn("Sourced Evidence Stream", html)
        self.assertIn("yfinance", html)
        self.assertIn("sec_edgar", html)
        self.assertIn("Internal / Process Grounded", html)

    def test_research_htmx_partial_response(self):
        """GET /research with HX-Request: true returns #research-content fragment."""
        res = self.client.get("/research?query=AAPL&mode=standard", headers={"HX-Request": "true"})
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify fragment returns #research-content
        self.assertIn('<div id="research-content"', html)
        self.assertIn("Apple Inc.", html)
        self.assertIn("Active device installed base exceeding 2.2 billion units", html)

        # Verify no full HTML document shell
        self.assertNotIn("<!DOCTYPE html>", html)
        self.assertNotIn("<html", html)
        self.assertNotIn("<head>", html)
        self.assertNotIn("</body>", html)

    def test_research_deep_analysis_mode(self):
        """GET /research?query=NVDA&mode=company_deep_analysis renders deep analysis bundle."""
        res = self.client.get("/research?query=NVDA&mode=company_deep_analysis")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("NVDA", html)
        self.assertIn("NVIDIA Corporation", html)
        self.assertIn("Semiconductors", html)
        self.assertIn("Financial Health Ratios", html)
        self.assertIn("Jensen Huang", html)

    def test_research_market_intelligence_mode(self):
        """GET /research?query=MSFT&mode=market_intelligence renders signals and pulse quote."""
        res = self.client.get("/research?query=MSFT&mode=market_intelligence")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("MSFT", html)
        self.assertIn("Microsoft Corporation", html)
        self.assertIn("BULLISH", html)
        self.assertIn("78", html)
        self.assertIn("/100", html)
        self.assertIn("Ignite Technology Keynote", html)

    def test_research_company_comparison_mode(self):
        """GET /research?mode=company_comparison&company_a=AAPL&company_b=MSFT renders peer comparison."""
        res = self.client.get("/research?mode=company_comparison&company_a=AAPL&company_b=MSFT")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("AAPL", html)
        self.assertIn("MSFT", html)
        self.assertIn("AAPL Inc. vs MSFT Corp.", html)
        self.assertIn("Normalized Financial Comparison Matrix", html)

    def test_research_comparison_identical_symbols_error(self):
        """Comparing identical symbols renders clean validation error card."""
        res = self.client.get("/research?mode=company_comparison&company_a=AAPL&company_b=AAPL")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("Research Request Blocked", html)
        self.assertIn("Cannot compare company", html)
        self.assertIn("AAPL", html)
        self.assertIn("against itself", html)

    def test_research_comparison_missing_symbol_error(self):
        """Comparing with one missing symbol renders validation error card."""
        res = self.client.get("/research?mode=company_comparison&company_a=AAPL&company_b=")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("Research Request Blocked", html)
        self.assertIn("Please provide both Company A and Company B ticker symbols", html)

    def test_research_empty_query_error(self):
        """Empty query parameter submission renders validation error card."""
        res = self.client.get("/research?query=&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("Research Request Blocked", html)
        self.assertIn("Please enter a valid company name or stock symbol", html)

    def test_research_xss_protection(self):
        """Submitting HTML/script tags is rejected safely without execution."""
        res = self.client.get("/research?query=<script>alert(1)</script>&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn("Research Request Blocked", html)
        self.assertIn("HTML tags and control characters are not permitted", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_research_ai_unavailable_graceful_notice(self):
        """When AI synthesis is unavailable, deterministic data is rendered with an AI warning banner."""
        self.mock_orchestrator.ai_available = False
        res = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify AI warning banner
        self.assertIn("AI Synthesis Notice", html)
        self.assertIn("AI narrative synthesis is currently unavailable", html)

        # Verify deterministic data and sources still rendered
        self.assertIn("Apple Inc.", html)
        self.assertIn("$225.50", html)
        self.assertIn("Sourced Evidence Stream", html)
        self.assertIn("yfinance", html)

    def test_research_sources_and_citations_fidelity(self):
        """Valid URLs render external links while absent URLs show internal grounded tag."""
        res = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify external URL has safe link attributes
        self.assertIn('href="https://finance.yahoo.com/quote/AAPL"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)

        # Verify sec_edgar (url=None) has internal badge
        self.assertIn("Internal / Process Grounded", html)

    def test_research_purged_of_placeholder(self):
        """Verify obsolete placeholder text was completely removed."""
        res = self.client.get("/research")
        html = res.text
        self.assertNotIn("Phase 5 AI Research Desk integration pending", html)



    def test_research_page_contains_chat_panel(self):
        """Dedicated AI Research Desk includes the interactive conversational chat exchange."""
        res = self.client.get("/research")
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("research-chat-panel", html)
        self.assertIn("Research Desk Exchange", html)
        self.assertIn("Pressure-test the thesis", html)
        self.assertIn("Trace the source lane", html)
        self.assertIn("Separate evidence from interpretation", html)
        self.assertIn("Session Ledger", html)

    def test_research_chat_partial_endpoint(self):
        """GET /research/chat returns the chat exchange partial."""
        res = self.client.get("/research/chat")
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("research-chat-panel", html)
        self.assertIn("Open a research ledger with QuantAI", html)

    def test_research_chat_post_turn(self):
        """POST /research/chat returns rendered user query and agent response bubbles."""
        res = self.client.post("/research/chat", data={"message": "Pressure-test the thesis for AAPL"})
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("chat-turn", html)
        self.assertIn("Analyst Query", html)
        self.assertIn("Pressure-test the thesis for AAPL", html)
        self.assertIn("QuantAI Finance Agent", html)
        self.assertIn("agent-markdown", html)

    def test_research_chat_empty_message(self):
        """POST /research/chat with empty or whitespace message returns empty 200 response without error."""
        res = self.client.post("/research/chat", data={"message": "   "})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text.strip(), "")

    def test_research_chat_clear(self):
        """POST /research/chat/clear returns empty chat prompt state."""
        res = self.client.post("/research/chat/clear")
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("chat-empty-state", html)
        self.assertIn("Open a research ledger with QuantAI", html)

    @patch("api.web.agent.run")
    def test_research_chat_handles_agent_exception(self, mock_agent_run):
        """When agent run encounters an exception, friendly fallback message is returned safely."""
        mock_agent_run.side_effect = RuntimeError("Provider circuit breaker open")
        res = self.client.post("/research/chat", data={"message": "Check valuation"})
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("AI analysis is temporarily unavailable", html)
        self.assertIn("deterministic market, deep analysis, and comparison tools remain fully available", html)

if __name__ == "__main__":
    unittest.main()
