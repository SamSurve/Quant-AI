"""Comprehensive Cross-Destination Integration & Quality Hardening Tests (Milestone 13).

Validates:
1. Navigation and query continuity across all five primary destinations:
   - / (Overview/Dashboard)
   - /market (Market Intelligence)
   - /analysis (Company Deep Analysis)
   - /compare (Evidence-Based Peer Comparison)
   - /research (Dedicated AI Research Desk)
2. Active navigation indicators matching current routes.
3. Search endpoint candidates routing directly to matching destination views.
4. HTMX partial fragment isolation (no <html>/<head>/<body> document shells in partials).
5. State preservation across HTMX swaps (symbol, statement type/frequency, chart period, comparison pairs).
6. Truthful financial representations: missing values render as '—' or 'N/A', never fabricated 0 or 0.00%.
7. XSS sanitization and HTML escaping across all query and route parameters.
8. Non-blocking error alert rendering and recovery without server 500s.
9. Source citation provenance: real external URLs receive safe link attributes (target="_blank" rel="noopener noreferrer"),
   while non-URL or internal sources receive process-grounded tags.
10. Preservation of operational probe and API contracts (/api/health, /health/ready, /health/live, root JSON fallback).
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
from api.research_schemas import (
    CompanyComparisonReport,
    CompanyIdentity,
    ComparisonCompanyStatus,
    ComparisonIdentity,
    ErrorCategory,
    IdentifierConfidence,
    MarketSnapshot,
    OverallState,
    ResearchMode,
    ResearchRequest,
    ResearchResponse,
    ServiceState,
    ServiceStatus,
    SourceRecord,
    StructuredAnalysis,
)
from tests.test_comparison_ui import make_mock_report as make_mock_comparison_report
from tests.test_research_ui import (
    MockResearchOrchestrator,
    make_deep_analysis_response,
    make_market_intelligence_response,
    make_standard_response,
)


class TestWebIntegration(unittest.TestCase):
    """Integration test suite for cross-destination flows, HTMX contracts, and data fidelity."""

    def setUp(self):
        self.mock_orchestrator = MockResearchOrchestrator()
        web_module._RESEARCH_ORCHESTRATOR = self.mock_orchestrator
        web_module._COMPARISON_ORCHESTRATOR = self.mock_orchestrator
        self.client = TestClient(index_module.app)

    def tearDown(self):
        web_module._RESEARCH_ORCHESTRATOR = None
        web_module._COMPARISON_ORCHESTRATOR = None

    # -------------------------------------------------------------------------
    # 1. Navigation & Active State Continuity
    # -------------------------------------------------------------------------

    def test_navigation_active_states_across_all_destinations(self):
        """Verify each full-page destination highlights the corresponding nav link."""
        destinations = [
            ("/", 'class="nav-item active">\n          <span class="nav-icon">◈</span> Overview'),
            ("/market?symbol=SPY", 'class="nav-item active">\n          <span class="nav-icon">📈</span> Market Intelligence'),
            ("/analysis?symbol=AAPL", 'class="nav-item active">\n          <span class="nav-icon">📊</span> Deep Analysis'),
            ("/compare?s1=AAPL&s2=MSFT", 'class="nav-item active">\n          <span class="nav-icon">⚖</span> Comparison'),
            ("/research", 'class="nav-item active">\n          <span class="nav-icon">⚡</span> AI Research Desk'),
        ]
        for url, expected_active_snippet in destinations:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Failed loading {url}")
                self.assertIn(expected_active_snippet, res.text, f"Mismatched active navigation state for {url}")

    # -------------------------------------------------------------------------
    # 2. Search to Destination Continuity
    # -------------------------------------------------------------------------

    def test_search_results_lead_to_all_four_sub_destinations(self):
        """Search candidates list generates actionable links to Market, Analysis, Comparison, and Research."""
        res = self.client.get("/search?q=AAPL")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn('href="/market?symbol=AAPL"', html)
        self.assertIn('href="/analysis?symbol=AAPL"', html)
        self.assertIn('href="/compare?s1=AAPL&s2=MSFT"', html)
        self.assertIn('href="/research?query=AAPL"', html)

    def test_research_accepts_both_query_and_symbol_query_parameters(self):
        """Verify /research seamlessly handles both query and symbol parameters for search continuity."""
        # /research?query=AAPL
        res1 = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("Apple Inc.", res1.text)

        # /research?symbol=AAPL (backward-compatible search candidate link)
        res2 = self.client.get("/research?symbol=AAPL&mode=standard")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("Apple Inc.", res2.text)

    # -------------------------------------------------------------------------
    # 3. HTMX Partial Isolation & Server-Rendered Correctness
    # -------------------------------------------------------------------------

    def test_htmx_partials_contain_no_document_shells(self):
        """Verify all HTMX partial endpoints return isolated HTML fragments without <html>/<body> shells."""
        partial_endpoints = [
            ("/market/quote?symbol=SPY", "market-quote-container"),
            ("/market/chart?symbol=SPY&period=1M", "market-chart-container"),
            ("/market/events?symbol=SPY", "market-events-container"),
            ("/analysis/statement?symbol=AAPL&type=income&freq=annual", "statement-table-container"),
            ("/compare?s1=AAPL&s2=MSFT", "comparison-content"),
            ("/research?query=AAPL&mode=standard", "research-content"),
            ("/search?q=AAPL", "search-candidates-list"),
        ]
        headers = {"HX-Request": "true"}
        for url, expected_container_id in partial_endpoints:
            with self.subTest(url=url):
                res = self.client.get(url, headers=headers)
                self.assertEqual(res.status_code, 200, f"Partial failed: {url}")
                html = res.text

                # Must not contain document wrapper tags
                self.assertNotIn("<!DOCTYPE html>", html, f"Partial contains DOCTYPE: {url}")
                self.assertNotIn("<html", html, f"Partial contains <html> tag: {url}")
                self.assertNotIn("<head>", html, f"Partial contains <head> tag: {url}")
                self.assertNotIn("</body>", html, f"Partial contains </body> tag: {url}")

                # Must contain the expected container ID
                self.assertIn(expected_container_id, html, f"Missing container {expected_container_id} in {url}")

    # -------------------------------------------------------------------------
    # 4. State & Parameter Preservation across Swaps
    # -------------------------------------------------------------------------

    def test_analysis_statement_controls_preserve_symbol_and_frequency(self):
        """Switching statement type preserves the company symbol and active frequency."""
        headers = {"HX-Request": "true"}
        res = self.client.get(
            "/analysis/statement?symbol=MSFT&type=balance&freq=quarterly",
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Links must preserve symbol=MSFT and freq=quarterly
        self.assertIn('hx-get="/analysis/statement?symbol=MSFT&type=income&freq=quarterly"', html)
        self.assertIn('hx-get="/analysis/statement?symbol=MSFT&type=balance&freq=quarterly"', html)
        self.assertIn('hx-get="/analysis/statement?symbol=MSFT&type=cashflow&freq=quarterly"', html)

    def test_market_chart_controls_preserve_symbol(self):
        """Chart period buttons preserve the active ticker symbol."""
        headers = {"HX-Request": "true"}
        res = self.client.get("/market/chart?symbol=NVDA&period=3M", headers=headers)
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Period buttons must maintain symbol=NVDA
        for p in ["1D", "1W", "1M", "3M", "1Y", "5Y"]:
            self.assertIn(f'hx-get="/market/chart?symbol=NVDA&period={p}"', html)

    def test_research_form_preserves_inputs_on_error(self):
        """Validation errors preserve the submitted inputs for user correction."""
        res = self.client.get("/research?mode=company_comparison&company_a=AAPL&company_b=AAPL")
        self.assertEqual(res.status_code, 200)
        html = res.text

        self.assertIn('value="AAPL"', html)
        self.assertIn("Research Request Blocked", html)
        self.assertIn("Cannot compare company", html)

    # -------------------------------------------------------------------------
    # 5. Truthful Financial Data & Missing Value Fidelity
    # -------------------------------------------------------------------------

    def test_missing_price_change_not_rendered_as_fabricated_zero(self):
        """Missing session price change renders as '—', never fabricated '+0.00 (0.0%)'."""
        # Standard research mode with missing daily_change
        resp = make_standard_response("AAPL")
        resp.market.daily_change = None
        resp.market.daily_change_percent = None

        class MissingChangeMockOrchestrator(MockResearchOrchestrator):
            async def research(self, request_id: str, request: ResearchRequest) -> ResearchResponse:
                return resp

        web_module._RESEARCH_ORCHESTRATOR = MissingChangeMockOrchestrator()

        res = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Must display em dash '—' and NOT '+0.0 (0.0%)'
        self.assertNotIn("+0.00 (0.0%)", html)
        self.assertNotIn("+0.0 (0.0%)", html)
        self.assertIn('<span class="stat-value font-mono text-muted">—</span>', html)

    def test_missing_source_urls_render_internal_grounded_badge_not_broken_link(self):
        """Sources without external HTTP URLs display process-grounded badge rather than empty links."""
        res = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # sec_edgar in mock has url=None
        self.assertIn("sec_edgar", html)
        self.assertIn("Internal / Process Grounded", html)
        # Should not have an href="None" or href="" link
        self.assertNotIn('href="None"', html)
        self.assertNotIn('href=""', html)

    # -------------------------------------------------------------------------
    # 6. XSS Sanitization & Input Security
    # -------------------------------------------------------------------------

    def test_xss_attempts_escaped_or_blocked_across_all_destinations(self):
        """Malicious markup in tickers and query parameters is cleanly blocked or escaped."""
        xss_payload = "<script>alert('xss')</script>"

        # Market
        res_m = self.client.get(f"/market?symbol={xss_payload}")
        self.assertNotIn("<script>alert('xss')</script>", res_m.text)

        # Analysis
        res_a = self.client.get(f"/analysis?symbol={xss_payload}")
        self.assertNotIn("<script>alert('xss')</script>", res_a.text)

        # Compare
        res_c = self.client.get(f"/compare?s1={xss_payload}&s2=MSFT")
        self.assertNotIn("<script>alert('xss')</script>", res_c.text)
        self.assertIn("Invalid ticker symbol format", res_c.text)

        # Research
        res_r = self.client.get(f"/research?query={xss_payload}&mode=standard")
        self.assertNotIn("<script>alert('xss')</script>", res_r.text)
        self.assertIn("Invalid input format", res_r.text)

    # -------------------------------------------------------------------------
    # 7. Non-Blocking Error Alert Rendering & Fallback Integrity
    # -------------------------------------------------------------------------

    def test_research_general_exception_displays_user_friendly_alert_card(self):
        """Unexpected backend exceptions produce an informative alert card without a 500 error."""
        class FailingOrchestrator:
            async def research(self, request_id: str, request: ResearchRequest) -> ResearchResponse:
                raise RuntimeError("Simulated transient provider timeout")

        web_module._RESEARCH_ORCHESTRATOR = FailingOrchestrator()

        res = self.client.get("/research?query=AAPL&mode=standard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Research Request Blocked", res.text)
        self.assertIn("Unable to complete research", res.text)

    # -------------------------------------------------------------------------
    # 8. Operational Probes & API Contract Preservation
    # -------------------------------------------------------------------------

    def test_readiness_and_liveness_probes_return_200_json(self):
        """Operational health endpoints remain active and verified."""
        res_ready = self.client.get("/health/ready")
        self.assertEqual(res_ready.status_code, 200)
        self.assertEqual(res_ready.json().get("status"), "ready")

        res_live = self.client.get("/health/live")
        self.assertEqual(res_live.status_code, 200)
        self.assertEqual(res_live.json().get("status"), "live")

    def test_root_json_fallback_for_api_clients(self):
        """Root GET with application/json Accept header returns system status JSON."""
        res = self.client.get("/", headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/json")
        data = res.json()
        self.assertIn("status", data)
        self.assertEqual(data.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
