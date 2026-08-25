"""No-network checks for the Vercel production configuration and AgentOS mounts.

Run with ``PYTHONDONTWRITEBYTECODE=1 python tests/test_production_readiness.py``.
The deployment excludes this test directory through ``.vercelignore`` and the
function ``excludeFiles`` rule; it is intentionally kept in source control for
repeatable release validation.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


_PROVIDER_ENV_NAMES = (
    "GROQ_API_KEY_PRIMARY",
    "GROQ_API_KEY_SECONDARY",
    "OPENROUTER_API_KEY",
)
_MODULES_WITH_PROVIDER_CONSTRUCTION = (
    "api.index",
    "api.groq_finance_agent",
    "api.research_orchestrator",
    "api.ai_providers",
)


@contextmanager
def isolated_app(provider_env: dict[str, str]) -> Iterator[tuple[object, str]]:
    """Build FastAPI/AgentOS only after the intended provider environment is set."""

    previous_modules = {
        module_name: sys.modules.pop(module_name)
        for module_name in _MODULES_WITH_PROVIDER_CONSTRUCTION
        if module_name in sys.modules
    }
    with patch.dict(os.environ, provider_env, clear=False):
        try:
            providers = importlib.import_module("api.ai_providers")
            app_module = importlib.import_module("api.index")
            yield app_module.app, providers.USER_FRIENDLY_UNAVAILABLE
        finally:
            for module_name in _MODULES_WITH_PROVIDER_CONSTRUCTION:
                sys.modules.pop(module_name, None)
            sys.modules.update(previous_modules)


def no_provider_environment() -> dict[str, str]:
    return {name: "" for name in _PROVIDER_ENV_NAMES}


def check_deployment_files() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    function = config["functions"]["api/**/*.py"]
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
    for entrypoint in (
        "api/health.py",
        "api/agents.py",
        "api/research.py",
        "api/agents/groq-finance-agent/runs.py",
    ):
        entrypoint_path = ROOT / entrypoint
        assert entrypoint_path.exists(), entrypoint
        assert "from api.index import app" in entrypoint_path.read_text(encoding="utf-8")
    assert "-r " not in (ROOT / "requirements.txt").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "openai" in requirements
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"

    deployment_ignore = (ROOT / ".vercelignore").read_text(encoding="utf-8")
    for required_pattern in ("tests/", "__pycache__/", "*.pyc", ".vercel/", "dist/", "node_modules/"):
        assert required_pattern in deployment_ignore

    deployment_docs = (ROOT / "VERCEL_DEPLOYMENT.md").read_text(encoding="utf-8")
    for required_variable in (
        "GROQ_API_KEY_PRIMARY",
        "GROQ_MODEL_PRIMARY",
        "GROQ_API_KEY_SECONDARY",
        "GROQ_MODEL_SECONDARY",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
    ):
        assert required_variable in deployment_docs


def check_agentos_routes() -> None:
    with isolated_app(no_provider_environment()) as (app, _):
        with TestClient(app) as client:
            for path in ("/api", "/api/health", "/", "/health", "/api/agents", "/agents"):
                response = client.get(path)
                assert response.status_code == 200, (path, response.status_code, response.text)

            health = client.get("/api/health").json()
            assert health["agent_id"] == "groq-finance-agent"
            assert "provider_runtime" in health
            assert health["provider_runtime"]["configured_count"] == 0
            assert health["agentos_runs"]["path"] == "/api/agents/groq-finance-agent/runs"
            assert health["agentos_runs"]["request_limit_bytes"] == 8_192
            assert "GROQ_API_KEY_PRIMARY" not in json.dumps(health)
            assert "GROQ_API_KEY_SECONDARY" not in json.dumps(health)
            assert "OPENROUTER_API_KEY" not in json.dumps(health)


def check_missing_provider_behavior() -> None:
    """The user-facing run endpoint must fail safely when no server key exists."""
    with isolated_app(no_provider_environment()) as (app, unavailable_message):
        with TestClient(app) as client:
            response = client.post(
                "/api/agents/groq-finance-agent/runs",
                data={"message": "Research AAPL", "stream": "false"},
            )
            assert response.status_code in {200, 503}, (response.status_code, response.text)
            body = json.dumps(response.json())
            assert unavailable_message in body, body


def check_agentos_run_protection() -> None:
    """AgentOS multipart runs must enforce the same public request-size boundary."""
    with isolated_app(no_provider_environment()) as (app, _):
        with TestClient(app) as client:
            response = client.post(
                "/api/agents/groq-finance-agent/runs",
                content=b"x" * 9_000,
                headers={"content-type": "application/octet-stream"},
            )
            assert response.status_code == 422, (response.status_code, response.text)
            body = response.json()
            assert body["category"] == "VALIDATION_ERROR"
            assert "request body too large" not in json.dumps(body)


def check_configured_provider_agentos_setup() -> None:
    """Keep configured-provider discovery separate without invoking a real provider."""

    with isolated_app({**no_provider_environment(), "GROQ_API_KEY_PRIMARY": "test-provider-key"}) as (app, _):
        with TestClient(app) as client:
            response = client.get("/api/agents")
            assert response.status_code == 200, response.text
            health = client.get("/api/health").json()
            assert health["provider_runtime"]["configured_count"] == 1


if __name__ == "__main__":
    check_deployment_files()
    check_agentos_routes()
    check_missing_provider_behavior()
    check_agentos_run_protection()
    check_configured_provider_agentos_setup()
    print("PRODUCTION_READINESS=PASS")
