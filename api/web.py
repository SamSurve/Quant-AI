"""Web routes, destination views, and Jinja2/HTMX server-rendering for QuantAI."""

from __future__ import annotations

import asyncio
import html
import logging
import math
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .research_services import EntityResolutionService
from .research_schemas import (
    CompanyIdentity,
    IdentifierConfidence,
    ServiceState,
    HistoryPeriod,
)
from .market_intelligence_services import (
    normalize_symbol,
    slice_history,
    calculate_market_signal,
    default_market_pulse_service,
    default_price_history_service,
    default_event_radar_service,
)
from .company_analysis_services import fetch_company_analysis_bundle

LOGGER = logging.getLogger("quantai.web")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def format_currency(val: float | int | None, currency: str = "USD") -> str:
    """Format numerical values into currency representation."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return "N/A"
    sym = "$" if currency == "USD" else f"{currency} "
    return f"{sym}{val:,.2f}"


def format_percent(val: float | None) -> str:
    """Format decimal percentage into human readable string."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return "N/A"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def format_large_number(val: int | float | None) -> str:
    """Format large numbers with B/M/K suffix."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return "N/A"
    abs_val = abs(val)
    if abs_val >= 1_000_000_000_000:
        return f"{val / 1_000_000_000_000:.2f}T"
    if abs_val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.2f}B"
    if abs_val >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return f"{val:,}"


def format_compact_currency(val: float | int | None, currency: str = "USD") -> str:
    """Format currency values with clean B/M/K scale suffix for terminal cards and tables."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return "N/A"
    sym = "$" if currency == "USD" else f"{currency} "
    neg = "-" if val < 0 else ""
    abs_val = abs(val)
    if abs_val >= 1_000_000_000_000:
        return f"{neg}{sym}{abs_val / 1_000_000_000_000:.2f}T"
    if abs_val >= 1_000_000_000:
        return f"{neg}{sym}{abs_val / 1_000_000_000:.2f}B"
    if abs_val >= 1_000_000:
        return f"{neg}{sym}{abs_val / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"{neg}{sym}{abs_val / 1_000:.1f}K"
    return f"{neg}{sym}{abs_val:,.2f}"


# Register template filters
templates.env.filters["currency"] = format_currency
templates.env.filters["compact_currency"] = format_compact_currency
templates.env.filters["percent"] = format_percent
templates.env.filters["large_num"] = format_large_number


def generate_chart_svg_data(points: list, width: int = 800, height: int = 260) -> dict[str, Any] | None:
    """Generate deterministic SVG coordinates and tick metadata for price history points."""
    valid = [p for p in points if getattr(p, "close", None) is not None and not math.isnan(p.close)]
    if not valid:
        return None

    closes = [p.close for p in valid]
    min_price = min(closes)
    max_price = max(closes)
    delta = max_price - min_price
    if delta <= 0:
        delta = 0.01

    pad_top = 20
    pad_bottom = 35
    pad_left = 65
    pad_right = 20
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    n = len(valid)
    svg_points = []
    for i, p in enumerate(valid):
        x = pad_left + (i / max(1, n - 1)) * plot_w
        norm_y = (p.close - min_price) / delta
        y = pad_top + plot_h - (norm_y * plot_h)
        svg_points.append((x, y, p))

    line_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y, _ in svg_points)
    area_d = f"{line_d} L {svg_points[-1][0]:.1f},{pad_top + plot_h:.1f} L {svg_points[0][0]:.1f},{pad_top + plot_h:.1f} Z"

    start_price = closes[0]
    end_price = closes[-1]
    price_change = end_price - start_price
    price_change_pct = (price_change / start_price * 100) if start_price else 0.0
    is_positive = price_change >= 0

    y_ticks = [
        {"y": pad_top, "label": f"${max_price:,.2f}"},
        {"y": pad_top + plot_h / 2, "label": f"${(min_price + max_price) / 2:,.2f}"},
        {"y": pad_top + plot_h, "label": f"${min_price:,.2f}"},
    ]

    x_ticks = []
    if n >= 2:
        x_ticks.append({"x": svg_points[0][0], "label": svg_points[0][2].timestamp[:10]})
        if n >= 4:
            mid_idx = n // 2
            x_ticks.append({"x": svg_points[mid_idx][0], "label": svg_points[mid_idx][2].timestamp[:10]})
        x_ticks.append({"x": svg_points[-1][0], "label": svg_points[-1][2].timestamp[:10]})

    return {
        "width": width,
        "height": height,
        "plot_left": pad_left,
        "plot_top": pad_top,
        "plot_width": plot_w,
        "plot_height": plot_h,
        "line_d": line_d,
        "area_d": area_d,
        "is_positive": is_positive,
        "start_price": start_price,
        "end_price": end_price,
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "min_price": min_price,
        "max_price": max_price,
        "y_ticks": y_ticks,
        "x_ticks": x_ticks,
        "point_count": n,
        "latest_close": end_price,
    }
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
async def market_page(request: Request, symbol: str = "SPY", period: str = "1M") -> Response:
    """Destination A: Market Intelligence page with real, validated financial telemetry."""
    try:
        clean_symbol = normalize_symbol(symbol)
        validation_error = None
    except ValueError as err:
        return safe_render_template(
            request,
            "market.html",
            {
                "active_page": "market",
                "symbol": symbol.strip()[:16],
                "validation_error": str(err),
            },
        )

    entity = CompanyIdentity(symbol=clean_symbol, identifier_confidence=IdentifierConfidence.HIGH)
    pulse_task = asyncio.create_task(default_market_pulse_service.fetch(entity))
    history_task = asyncio.create_task(default_price_history_service.fetch(entity))
    events_task = asyncio.create_task(default_event_radar_service.fetch(entity))

    (pulse_res, pulse_fresh), (hist_res, hist_fresh), (events_res, events_fresh) = await asyncio.gather(
        pulse_task, history_task, events_task
    )

    signal = None
    chart_data = None
    if hist_res.history and hist_res.history.daily:
        signal = calculate_market_signal(hist_res.history.daily)
        points = slice_history(hist_res.history, period)
        chart_data = generate_chart_svg_data(points)
    elif hist_res.history and hist_res.history.intraday:
        points = slice_history(hist_res.history, period)
        chart_data = generate_chart_svg_data(points)

    currency = pulse_res.market.currency if (pulse_res.market and pulse_res.market.currency) else "USD"

    context = {
        "active_page": "market",
        "symbol": clean_symbol,
        "active_period": period.upper(),
        "pulse": pulse_res,
        "freshness": pulse_fresh,
        "currency": currency,
        "chart_data": chart_data,
        "signal": signal,
        "events_result": events_res,
        "validation_error": None,
    }
    return safe_render_template(request, "market.html", context)


@router.get("/market/chart", response_class=HTMLResponse)
@router.get("/market/history", response_class=HTMLResponse)
async def market_chart_partial(request: Request, symbol: str = "SPY", period: str = "1M") -> Response:
    """HTMX partial for historical price chart horizon updates."""
    try:
        clean_symbol = normalize_symbol(symbol)
    except ValueError:
        return safe_render_template(
            request,
            "partials/market_chart.html",
            {
                "symbol": symbol.strip()[:16],
                "active_period": period.upper(),
                "chart_data": None,
                "currency": "USD",
            },
        )

    entity = CompanyIdentity(symbol=clean_symbol, identifier_confidence=IdentifierConfidence.HIGH)
    hist_res, hist_fresh = await default_price_history_service.fetch(entity)
    chart_data = None
    if hist_res.history:
        points = slice_history(hist_res.history, period)
        chart_data = generate_chart_svg_data(points)

    return safe_render_template(
        request,
        "partials/market_chart.html",
        {
            "symbol": clean_symbol,
            "active_period": period.upper(),
            "chart_data": chart_data,
            "currency": "USD",
        },
    )


@router.get("/market/quote", response_class=HTMLResponse)
async def market_quote_partial(request: Request, symbol: str = "SPY") -> Response:
    """HTMX partial for live quote card refresh."""
    try:
        clean_symbol = normalize_symbol(symbol)
    except ValueError:
        return safe_render_template(
            request,
            "partials/market_quote.html",
            {
                "symbol": symbol.strip()[:16],
                "pulse": None,
                "freshness": None,
            },
        )

    entity = CompanyIdentity(symbol=clean_symbol, identifier_confidence=IdentifierConfidence.HIGH)
    pulse_res, pulse_fresh = await default_market_pulse_service.fetch(entity)

    return safe_render_template(
        request,
        "partials/market_quote.html",
        {
            "symbol": clean_symbol,
            "pulse": pulse_res,
            "freshness": pulse_fresh,
        },
    )


@router.get("/market/events", response_class=HTMLResponse)
async def market_events_partial(request: Request, symbol: str = "SPY") -> Response:
    """HTMX partial for corporate event calendar refresh."""
    try:
        clean_symbol = normalize_symbol(symbol)
    except ValueError:
        return safe_render_template(
            request,
            "partials/market_events.html",
            {
                "symbol": symbol.strip()[:16],
                "events_result": None,
            },
        )

    entity = CompanyIdentity(symbol=clean_symbol, identifier_confidence=IdentifierConfidence.HIGH)
    events_res, events_fresh = await default_event_radar_service.fetch(entity)

    return safe_render_template(
        request,
        "partials/market_events.html",
        {
            "symbol": clean_symbol,
            "events_result": events_res,
        },
    )


def _get_statement_periods(bundle: Any, active_type: str, active_freq: str) -> list:
    """Extract matching statement periods based on type and frequency."""
    if not bundle or not bundle.statements:
        return []
    s = bundle.statements
    if active_type == "income":
        return s.annual_income if active_freq == "annual" else s.quarterly_income
    if active_type == "balance":
        return s.annual_balance if active_freq == "annual" else s.quarterly_balance
    if active_type == "cashflow":
        return s.annual_cashflow if active_freq == "annual" else s.quarterly_cashflow
    return s.annual_income if active_freq == "annual" else s.quarterly_income


@router.get("/analysis", response_class=HTMLResponse)
async def analysis_page(
    request: Request,
    symbol: str = "AAPL",
    type: str = "income",
    freq: str = "annual",
) -> Response:
    """Destination B: Company Deep Analysis page with validated fundamental telemetry."""
    try:
        clean_symbol = normalize_symbol(symbol)
        validation_error = None
    except ValueError as err:
        return safe_render_template(
            request,
            "analysis.html",
            {
                "active_page": "analysis",
                "symbol": symbol.strip()[:16],
                "validation_error": str(err),
            },
        )

    bundle = await fetch_company_analysis_bundle(clean_symbol)
    active_type = type.lower() if type.lower() in ("income", "balance", "cashflow") else "income"
    active_freq = freq.lower() if freq.lower() in ("annual", "quarterly") else "annual"
    statement_periods = _get_statement_periods(bundle, active_type, active_freq)
    currency = bundle.overview.currency if (bundle.overview and bundle.overview.currency) else (
        bundle.financial_health.currency if (bundle.financial_health and bundle.financial_health.currency) else "USD"
    )

    context = {
        "active_page": "analysis",
        "symbol": clean_symbol,
        "bundle": bundle,
        "currency": currency,
        "active_type": active_type,
        "active_freq": active_freq,
        "statement_periods": statement_periods,
        "validation_error": None,
    }
    return safe_render_template(request, "analysis.html", context)


@router.get("/analysis/statement", response_class=HTMLResponse)
async def analysis_statement_partial(
    request: Request,
    symbol: str = "AAPL",
    type: str = "income",
    freq: str = "annual",
) -> Response:
    """HTMX partial for statement type and frequency switching."""
    try:
        clean_symbol = normalize_symbol(symbol)
    except ValueError:
        return safe_render_template(
            request,
            "partials/analysis_statements.html",
            {
                "symbol": symbol.strip()[:16],
                "active_type": type.lower(),
                "active_freq": freq.lower(),
                "statement_periods": [],
                "currency": "USD",
            },
        )

    bundle = await fetch_company_analysis_bundle(clean_symbol)
    active_type = type.lower() if type.lower() in ("income", "balance", "cashflow") else "income"
    active_freq = freq.lower() if freq.lower() in ("annual", "quarterly") else "annual"
    statement_periods = _get_statement_periods(bundle, active_type, active_freq)
    currency = bundle.overview.currency if (bundle.overview and bundle.overview.currency) else (
        bundle.financial_health.currency if (bundle.financial_health and bundle.financial_health.currency) else "USD"
    )

    return safe_render_template(
        request,
        "partials/analysis_statements.html",
        {
            "symbol": clean_symbol,
            "active_type": active_type,
            "active_freq": active_freq,
            "statement_periods": statement_periods,
            "currency": currency,
        },
    )


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
