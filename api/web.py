"""Web routes, destination views, and Jinja2/HTMX server-rendering for QuantAI."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .research_services import EntityResolutionService

LOGGER = logging.getLogger("quantai.web")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["web"])
entity_service = EntityResolutionService()


def safe_render_template(request: Request, template_name: str, context: Dict[str, Any], status_code: int = 200) -> Response:
    """Render a Jinja2 template safely, preventing crashes if a template is corrupted or missing."""
    try:
        return templates.TemplateResponse(
            request=request,
            name=template_name,
            context=context,
            status_code=status_code,
        )
    except Exception as exc:
        LOGGER.exception("template_render_error template=%s error=%s", template_name, exc)
        fallback_html = (
            f"<!DOCTYPE html><html><head><title>QuantAI Error</title></head>"
            f"<body><h1>Rendering Error</h1><p>Failed to render {template_name}.</p></body></html>"
        )
        return HTMLResponse(content=fallback_html, status_code=500)


def sanitize_search_query(raw_query: str) -> str:
    """Strip HTML tags and clamp length for user safety."""
    import re
    cleaned = re.sub(r"<[^>]*>", "", raw_query)
    return cleaned.strip()[:60]


async def resolve_search_candidates(query: str) -> List[Dict[str, Any]]:
    """Resolve symbol and company candidate records using verified research service."""
    clean_query = sanitize_search_query(query)
    if not clean_query:
        return []
    try:
        candidates = await asyncio.to_thread(entity_service._search_candidates, clean_query)
        return [
            {
                "symbol": c.symbol,
                "name": c.name or c.symbol,
                "exchange": c.exchange or "",
                "quote_type": c.quote_type or "EQUITY",
            }
            for c in candidates
        ]
    except Exception as exc:
        LOGGER.warning("symbol_search_failed query=%s error=%s", clean_query, exc)
        return []


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page(request: Request) -> Response:
    """Render the Python-first financial research landing page."""
    accept = request.headers.get("accept", "")
    # Support headless API clients expecting JSON from root
    if "application/json" in accept and "text/html" not in accept:
        from .index import health_payload
        return JSONResponse(content=health_payload())

    context = {
        "active_page": "dashboard",
        "system_status": "operational",
        "engine": "FastAPI + Jinja2 + HTMX",
        "version": "1.0.0",
    }
    return safe_render_template(request, "index.html", context)


@router.get("/market", response_class=HTMLResponse)
async def market_page(request: Request, symbol: str = "SPY") -> Response:
    """Destination A: Market Intelligence page."""
    clean_symbol = symbol.strip().upper()[:16] or "SPY"
    context = {
        "active_page": "market",
        "symbol": clean_symbol,
        "company_name": f"{clean_symbol} Overview",
        "exchange": "US Equities",
    }
    return safe_render_template(request, "market.html", context)


@router.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request, symbol: str = "AAPL") -> Response:
    """Destination B: Company Deep Analysis page."""
    clean_symbol = symbol.strip().upper()[:16] or "AAPL"
    context = {
        "active_page": "analysis",
        "symbol": clean_symbol,
        "company_name": f"{clean_symbol} Fundamental Profile",
        "sector": "Technology",
    }
    return safe_render_template(request, "analysis.html", context)


@router.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request, s1: str = "AAPL", s2: str = "MSFT") -> Response:
    """Destination C: Company Comparison page."""
    clean_s1 = s1.strip().upper()[:16] or "AAPL"
    clean_s2 = s2.strip().upper()[:16] or "MSFT"
    context = {
        "active_page": "compare",
        "s1": clean_s1,
        "s2": clean_s2,
        "s1_name": f"{clean_s1} Corp",
        "s2_name": f"{clean_s2} Corp",
    }
    return safe_render_template(request, "compare.html", context)


@router.get("/research", response_class=HTMLResponse)
async def research_page(request: Request, query: str = "") -> Response:
    """Destination D: Dedicated AI Research Desk workspace."""
    context = {
        "active_page": "research",
        "query": query.strip()[:120],
    }
    return safe_render_template(request, "research.html", context)


@router.get("/search", response_class=HTMLResponse)
async def search_endpoint(request: Request, q: str = "") -> Response:
    """HTMX search endpoint returning partial candidates fragment."""
    clean_query = sanitize_search_query(q)
    candidates = await resolve_search_candidates(clean_query) if clean_query else []
    context = {
        "query": clean_query,
        "candidates": candidates,
    }
    return safe_render_template(request, "partials/search_results.html", context)


@router.get("/health/ready", tags=["operations"])
async def readiness_probe() -> Dict[str, Any]:
    """Readiness probe validating template and static directory availability."""
    templates_ready = TEMPLATES_DIR.is_dir() and (TEMPLATES_DIR / "base.html").exists()
    static_ready = STATIC_DIR.is_dir() and (STATIC_DIR / "css" / "main.css").exists()
    status = "ready" if (templates_ready and static_ready) else "degraded"
    return {
        "status": status,
        "templates_available": templates_ready,
        "static_available": static_ready,
        "runtime": "fastapi-jinja2",
    }


@router.get("/health/live", tags=["operations"])
async def liveness_probe() -> Dict[str, str]:
    """Basic process liveness probe."""
    return {"status": "live"}
