"""Production Deployment and Operational Readiness Test Suite for QuantAI.

Validates that the repository is completely configured for pure Python-first
FastAPI deployment (e.g., on Vercel), with valid JSON configuration, pinned
Python version, safe .env.example, Git secret exclusion, CI workflow, complete
static assets, templates integrity, and operational probe readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient

from api.index import app


class TestDeploymentReadiness:
    """Validate deployment configuration, asset presence, security, and operational probes."""

    def test_vercel_configuration_valid_json_and_pure_python(self) -> None:
        """vercel.json must be valid JSON and configured for Python FastAPI runtime."""
        vercel_path = ROOT_DIR / "vercel.json"
        assert vercel_path.is_file(), "vercel.json file is missing"

        with open(vercel_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Legacy Vite/Node frontend build settings must be absent
        assert "framework" not in config or config.get("framework") != "vite", "Legacy Vite framework must be removed"
        assert "installCommand" not in config, "Legacy installCommand (pnpm) must be removed"
        assert "buildCommand" not in config, "Legacy buildCommand (pnpm) must be removed"
        assert "outputDirectory" not in config, "Legacy outputDirectory (dist/public) must be removed"

        # Functions configuration must target api/index.py and bundle templates and static files
        functions = config.get("functions", {})
        func_cfg = functions.get("api/index.py") or functions.get("api/**/*.py")
        assert func_cfg is not None, "Functions must define configuration for api/index.py"
        include_files = func_cfg.get("includeFiles", "")
        assert "templates/**" in include_files, "Function bundle must include templates/**"
        assert "static/**" in include_files, "Function bundle must include static/**"

        # Rewrites must route all requests to /api/index.py (no SPA catch-all to index.html)
        rewrites = config.get("rewrites", [])
        assert len(rewrites) >= 1, "At least one rewrite rule must be defined"
        has_api_catchall = any(
            rw.get("destination") == "/api/index.py" for rw in rewrites
        )
        assert has_api_catchall, "Rewrites must direct incoming traffic to /api/index.py"

        # Verify no catch-all rewrite to legacy /index.html
        for rw in rewrites:
            assert rw.get("destination") != "/index.html", "Legacy SPA rewrite to /index.html must not exist"

        # API headers must prevent caching
        headers = config.get("headers", [])
        has_no_store = any(
            any(h.get("key") == "Cache-Control" and "no-store" in h.get("value", "") for h in item.get("headers", []))
            for item in headers
        )
        assert has_no_store, "Cache-Control: no-store header must be configured for API endpoints"

    def test_python_version_pinned(self) -> None:
        """.python-version must exist and pin Python 3.12."""
        py_version_path = ROOT_DIR / ".python-version"
        assert py_version_path.is_file(), ".python-version file is missing"
        version_str = py_version_path.read_text(encoding="utf-8").strip()
        assert version_str.startswith("3.12"), f"Expected Python 3.12, got: {version_str}"

    def test_env_example_safety_and_structure(self) -> None:
        """.env.example must exist, document variables, and contain zero live secrets."""
        env_example_path = ROOT_DIR / ".env.example"
        assert env_example_path.is_file(), ".env.example file is missing"

        content = env_example_path.read_text(encoding="utf-8")

        # Documented variable names must be present
        expected_vars = [
            "GROQ_API_KEY_PRIMARY",
            "GROQ_API_KEY_SECONDARY",
            "OPENROUTER_API_KEY",
            "AI_PROVIDER_ORDER",
        ]
        for var_name in expected_vars:
            assert var_name in content, f"Expected {var_name} to be documented in .env.example"

        # Secret patterns must NOT be present
        secret_patterns = [
            r"gsk_[a-zA-Z0-9]{20,}",
            r"sk-[a-zA-Z0-9]{20,}",
            r"bearer\s+[a-zA-Z0-9\-_]{20,}",
        ]
        for pattern in secret_patterns:
            matches = re.findall(pattern, content, flags=re.IGNORECASE)
            assert len(matches) == 0, f"Found secret leak matching pattern {pattern}: {matches}"

    def test_gitignore_protects_secrets_and_caches(self) -> None:
        """.gitignore must exclude local environment files and Python cache directories."""
        gitignore_path = ROOT_DIR / ".gitignore"
        assert gitignore_path.is_file(), ".gitignore is missing"

        content = gitignore_path.read_text(encoding="utf-8")
        assert ".env" in content
        assert ".venv/" in content or ".venv" in content
        assert "__pycache__/" in content or "__pycache__" in content

    def test_github_actions_ci_workflow(self) -> None:
        """GitHub Actions CI workflow must exist and test on Python 3.12."""
        ci_path = ROOT_DIR / ".github" / "workflows" / "ci.yml"
        assert ci_path.is_file(), ".github/workflows/ci.yml is missing"

        content = ci_path.read_text(encoding="utf-8")
        assert "3.12" in content, "CI workflow must specify Python 3.12"
        assert "pytest" in content, "CI workflow must execute pytest"

    def test_production_static_assets_integrity(self) -> None:
        """Static CSS, JavaScript, and HTMX vendor assets must exist and be valid."""
        css_path = ROOT_DIR / "static" / "css" / "main.css"
        assert css_path.is_file(), "static/css/main.css is missing"
        css_content = css_path.read_text(encoding="utf-8")
        assert len(css_content) > 1000, "main.css is unexpectedly small"
        assert "--bg-base" in css_content or "--bg-surface" in css_content, "main.css missing design tokens"

        js_path = ROOT_DIR / "static" / "js" / "app.js"
        assert js_path.is_file(), "static/js/app.js is missing"
        js_content = js_path.read_text(encoding="utf-8")
        assert len(js_content) > 100, "app.js is unexpectedly small"

        htmx_path = ROOT_DIR / "static" / "js" / "htmx.min.js"
        assert htmx_path.is_file(), "static/js/htmx.min.js is missing"
        htmx_content = htmx_path.read_text(encoding="utf-8")
        assert "htmx" in htmx_content, "htmx.min.js does not contain htmx identifier"

    def test_production_templates_integrity(self) -> None:
        """Jinja2 templates must exist, define base layout, and provide all 4 primary views."""
        templates_dir = ROOT_DIR / "templates"
        assert templates_dir.is_dir(), "templates/ directory is missing"

        base_html = templates_dir / "base.html"
        assert base_html.is_file(), "templates/base.html is missing"
        base_content = base_html.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in base_content
        assert "/static/css/main.css" in base_content
        assert "/static/js/htmx.min.js" in base_content
        assert "{% block content %}" in base_content

        # All four destinations must exist
        destinations = ["market.html", "analysis.html", "compare.html", "research.html"]
        for dest in destinations:
            dest_path = templates_dir / dest
            assert dest_path.is_file(), f"templates/{dest} is missing"
            content = dest_path.read_text(encoding="utf-8")
            assert "{% extends \"base.html\" %}" in content

    def test_operational_probes_and_security(self) -> None:
        """Operational probes (/health/live, /health/ready, /api/health) must return 200 without leaking secrets."""
        client = TestClient(app)

        # Liveness probe
        res_live = client.get("/health/live")
        assert res_live.status_code == 200
        live_json = res_live.json()
        assert live_json.get("status") == "live"

        # Readiness probe
        res_ready = client.get("/health/ready")
        assert res_ready.status_code == 200
        ready_json = res_ready.json()
        assert ready_json.get("status") in {"ready", "degraded", "ok"}

        # API health probe
        res_api = client.get("/api/health")
        assert res_api.status_code == 200
        api_json = res_api.json()
        assert "status" in api_json

        # Ensure no credential leaks in health responses
        for resp in [live_json, ready_json, api_json]:
            dumped = json.dumps(resp)
            assert "gsk_" not in dumped
            assert "sk-" not in dumped

    def test_static_files_served_via_fastapi_mount(self) -> None:
        """FastAPI must serve static CSS and JavaScript files under /static/."""
        client = TestClient(app)

        res_css = client.get("/static/css/main.css")
        assert res_css.status_code == 200
        assert "text/css" in res_css.headers.get("content-type", "")
        assert len(res_css.text) > 500

        res_js = client.get("/static/js/htmx.min.js")
        assert res_js.status_code == 200
        assert "javascript" in res_js.headers.get("content-type", "")
        assert len(res_js.text) > 1000
