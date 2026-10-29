"""Automated regression and integration tests for Python-rendered web foundation (M02)."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.index import app
from api.web import safe_render_template


class TestWebFoundation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_landing_page_renders_html(self):
        """Root GET with default / browser Accept header must return HTML."""
        response = self.client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("QuantAI", response.text)
        self.assertIn("Python-First Financial Research Terminal", response.text)
        self.assertIn("Market Intelligence", response.text)
        self.assertIn("Company Deep Analysis", response.text)
        self.assertIn("Company Comparison", response.text)
        self.assertIn("AI Research Desk", response.text)

    def test_root_json_fallback_for_api_clients(self):
        """Root GET with explicit application/json Accept header must return health payload."""
        response = self.client.get("/", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["agent_id"], "groq-finance-agent")

    def test_readiness_probe(self):
        """Readiness endpoint must report operational status for templates and static assets."""
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["templates_available"])
        self.assertTrue(data["static_available"])
        self.assertEqual(data["runtime"], "fastapi-jinja2")

    def test_liveness_probe(self):
        """Liveness endpoint must return alive."""
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "live"})

    def test_static_css_served(self):
        """Static CSS file must be accessible with correct content-type."""
        response = self.client.get("/static/css/main.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers.get("content-type", ""))
        self.assertIn("--accent-primary", response.text)

    def test_static_js_served(self):
        """Static JS file must be accessible with correct content-type."""
        response = self.client.get("/static/js/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("quantai_theme", response.text)

    def test_existing_api_contracts_preserved(self):
        """Existing /api/health and /health must remain functional and unmodified."""
        resp1 = self.client.get("/api/health")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["status"], "ok")

        resp2 = self.client.get("/health")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["status"], "ok")

    def test_safe_render_template_handles_missing_template(self):
        """Missing template must return 500 response gracefully without an unhandled crash."""
        from starlette.requests import Request
        req = Request({"type": "http", "method": "GET", "path": "/"})
        response = safe_render_template(req, "non_existent_template.html", {})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Rendering Error", response.body)

    def test_landing_page_does_not_present_sample_quotes_as_live_data(self):
        """The landing page may show capabilities, but must never present hard-coded quotes as current."""
        response = self.client.get("/", headers={"Accept": "text/html"})
        self.assertEqual(response.status_code, 200)
        rendered = response.text
        self.assertIn("metric-card", rendered)
        self.assertIn("badge", rendered)
        self.assertIn("data-table", rendered)
        self.assertIn("Research workflow", rendered)
        self.assertIn("AAPL / MSFT", rendered)
        self.assertIn("Fetched on request", rendered)
        self.assertNotIn("584.20", rendered)
        self.assertNotIn("$231.40", rendered)
        self.assertNotIn("$428.15", rendered)

    def test_css_design_system_tokens(self):
        """CSS stylesheet must define core design tokens and responsive rules."""
        response = self.client.get("/static/css/main.css")
        self.assertEqual(response.status_code, 200)
        css = response.text
        self.assertIn("--font-mono", css)
        self.assertIn("--font-sans", css)
        self.assertIn("--space-base", css)
        self.assertIn("--radius-md", css)
        self.assertIn('[data-theme="dark"]', css)
        self.assertIn('[data-theme="light"]', css)
        self.assertIn(":focus-visible", css)
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("@media (max-width: 375px)", css)


if __name__ == "__main__":
    unittest.main()
