"""No-network checks for the Vercel production configuration and AgentOS mounts.

Run with ``PYTHONDONTWRITEBYTECODE=1 python tests/test_production_readiness.py``.
The deployment excludes this test directory through ``.vercelignore`` and the
function ``excludeFiles`` rule; it is intentionally kept in source control for
repeatable release validation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.ai_providers import USER_FRIENDLY_UNAVAILABLE
from api.index import app


def check_deployment_files() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    function = config["functions"]["api/index.py"]
    assert config["framework"] == "vite"
    assert config["outputDirectory"] == "dist/public"
    assert function["includeFiles"] == "api/**"
    assert "tests/**" in function["excludeFiles"]
    assert "__pycache__" in function["excludeFiles"]
    assert any(
        rewrite["source"] == "/:path((?!api(?:/|$)).*)"
        and rewrite["destination"] == "/index.html"
        for rewrite in config["rewrites"]
    )
    assert "-r " not in (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"

    deployment_ignore = (ROOT / ".vercelignore").read_text(encoding="utf-8")
    for required_pattern in ("tests/", "__pycache__/", "*.pyc", ".vercel/", "dist/", "node_modules/"):
        assert required_pattern in deployment_ignore

    deployment_docs = (ROOT / "VERCEL_DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "AI_PROVIDER=auto" in deployment_docs
    assert "GEMINI_API_KEY" in deployment_docs
    assert "GROQ_API_KEY" in deployment_docs


def check_agentos_routes() -> None:
    with TestClient(app) as client:
        for path in ("/api", "/api/health", "/", "/health", "/api/agents", "/agents"):
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code, response.text)

        health = client.get("/api/health").json()
        assert health["agent_id"] == "groq-finance-agent"
        assert "provider_runtime" in health
        assert "GEMINI_API_KEY" not in json.dumps(health)
        assert "GROQ_API_KEY" not in json.dumps(health)


def check_missing_provider_behavior() -> None:
    """The user-facing run endpoint must fail safely when no server key exists."""
    with TestClient(app) as client:
        response = client.post(
            "/api/agents/groq-finance-agent/runs",
            data={"message": "Research AAPL", "stream": "false"},
        )
        assert response.status_code in {200, 503}, (response.status_code, response.text)
        body = json.dumps(response.json())
        assert USER_FRIENDLY_UNAVAILABLE in body, body


if __name__ == "__main__":
    check_deployment_files()
    check_agentos_routes()
    check_missing_provider_behavior()
    print("PRODUCTION_READINESS=PASS")
