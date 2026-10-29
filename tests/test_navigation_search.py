"""Automated regression and integration tests for navigation routes and HTMX search (M04)."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from api.index import app


class TestNavigationAndSearch(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_market_intelligence_destination(self):
        """GET /market must render Destination A with active navigation indicator."""
        response = self.client.get("/market")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Market Intelligence", response.text)
        self.assertIn('class="nav-item active"', response.text)
        self.assertIn("SPY", response.text)

    def test_market_intelligence_custom_symbol(self):
        """GET /market?symbol=NVDA must bind the specified symbol."""
        response = self.client.get("/market?symbol=NVDA")
        self.assertEqual(response.status_code, 200)
        self.assertIn("NVDA", response.text)

    def test_company_deep_analysis_destination(self):
        """GET /analysis must render Destination B with active navigation indicator."""
        response = self.client.get("/analysis")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Company Deep Analysis", response.text)
        self.assertIn('class="nav-item active"', response.text)
        self.assertIn("AAPL", response.text)

    def test_company_deep_analysis_custom_symbol(self):
        """GET /analysis?symbol=TSLA must bind the specified symbol."""
        response = self.client.get("/analysis?symbol=TSLA")
        self.assertEqual(response.status_code, 200)
        self.assertIn("TSLA", response.text)

    def test_company_comparison_destination(self):
        """GET /compare must render Destination C with active navigation indicator."""
        response = self.client.get("/compare")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Company Comparison", response.text)
        self.assertIn('class="nav-item active"', response.text)
        self.assertIn("AAPL", response.text)
        self.assertIn("MSFT", response.text)

    def test_company_comparison_custom_pair(self):
        """GET /compare?s1=GOOGL&s2=AMZN must bind both peer symbols."""
        response = self.client.get("/compare?s1=GOOGL&s2=AMZN")
        self.assertEqual(response.status_code, 200)
        self.assertIn("GOOGL", response.text)
        self.assertIn("AMZN", response.text)

    def test_ai_research_desk_destination(self):
        """GET /research must render Destination D with dedicated query workspace."""
        response = self.client.get("/research")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Dedicated AI Research Desk", response.text)
        self.assertIn('class="nav-item active"', response.text)
        self.assertIn("Execute Research", response.text)

    def test_search_empty_input_returns_popular_symbols(self):
        """GET /search with blank query must return popular symbol hints."""
        response = self.client.get("/search?q=")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Popular Symbols", response.text)
        self.assertIn("SPY", response.text)
        self.assertIn("AAPL", response.text)

    def test_search_valid_query_returns_candidates_partial(self):
        """GET /search with valid ticker query must return candidate items with destination links."""
        response = self.client.get("/search?q=AAPL", headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("AAPL", response.text)
        self.assertIn("/market?symbol=AAPL", response.text)
        self.assertIn("/analysis?symbol=AAPL", response.text)

    def test_search_no_results_empty_state(self):
        """GET /search with non-existent query must return clean empty state."""
        response = self.client.get("/search?q=NONEXISTENTZZZZ999")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No securities found matching", response.text)

    def test_search_xss_safety(self):
        """Search query containing script tags must be sanitized and never render executable scripts."""
        malicious = '<script>alert("xss")</script>'
        response = self.client.get(f"/search?q={malicious}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>alert", response.text)
        self.assertNotIn("</script>", response.text)

    def test_htmx_script_served(self):
        """Self-contained HTMX script must be served from static directory."""
        response = self.client.get("/static/js/htmx.min.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("htmx", response.text)


if __name__ == "__main__":
    unittest.main()
