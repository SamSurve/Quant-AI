"""Vercel entrypoint for the stateless QuantAI AgentOS finance research API.

Vercel delivers requests to ``api/index.py`` under the ``/api`` prefix. The
mounted AgentOS app therefore keeps its native ``/agents`` routes while the
public same-origin path becomes ``/api/agents/...``.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agno.exceptions import ModelProviderError

from .groq_finance_agent import app as agentos_app
from .groq_finance_agent import provider_router
from .ai_providers import provider_runtime_status


app = FastAPI(title="QuantAI Finance Agent API", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.exception_handler(ModelProviderError)
async def model_provider_error_handler(_request: Request, error: ModelProviderError) -> JSONResponse:
    """Keep an uncaught provider issue from becoming a raw server error."""
    return JSONResponse(
        status_code=503,
        content={
            "status": "ERROR",
            "detail": (
                "AI analysis is temporarily unavailable. Please try again shortly."
            ),
            "retryable": True,
        },
    )


def health_payload() -> dict[str, Any]:
    """Return a no-secret readiness response without invoking Groq."""
    return {
        "status": "ok",
        "agent_id": "groq-finance-agent",
        "model": "quantai-auto",
        "provider_runtime": provider_runtime_status(provider_router),
    }


@app.get("/api", tags=["operations"])
@app.get("/api/health", tags=["operations"])
def prefixed_health() -> dict[str, Any]:
    return health_payload()


@app.get("/", include_in_schema=False)
@app.get("/health", include_in_schema=False)
def prefix_stripped_health() -> dict[str, Any]:
    """Support Vercel function adapters that strip the function's `/api` prefix."""
    return health_payload()


app.mount("/api", agentos_app)
# Vercel's Python adapters normally preserve `/api`, but the fallback mount also
# serves AgentOS when a function adapter forwards `/api/agents` as `/agents`.
app.mount("", agentos_app)
