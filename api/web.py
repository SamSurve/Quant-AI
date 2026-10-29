"""Web routes and Jinja2 server-rendering for QuantAI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

LOGGER = logging.getLogger("quantai.web")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["web"])


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
        "engine": "FastAPI + Jinja2",
        "version": "1.0.0",
    }
    return safe_render_template(request, "index.html", context)


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
