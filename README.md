# QuantAI Finance Agent

A high-performance, resilient, Python-first financial intelligence and research platform built with **FastAPI**, **Jinja2**, **HTMX**, and custom vanilla CSS.

All primary financial data—including quotes, multi-period technical charts, audited financial statements, balance sheets, cash flows, corporate governance rosters, and side-by-side peer comparisons—are served deterministically via Yahoo Finance without requiring external AI API keys or heavy Node/React build steps. Optional AI analyst synthesis is provided through a fault-tolerant multi-provider router (Groq primary → Groq secondary → OpenRouter fallback).

---

## Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │            Browser Client              │
                      │  (HTML5 + HTMX + Vanilla CSS / JS)     │
                      └──────────────────┬─────────────────────┘
                                         │ HTTP / HTMX
                                         ▼
                      ┌────────────────────────────────────────┐
                      │          FastAPI Application           │
                      │             (api/index.py)             │
                      ├──────────────────┬─────────────────────┤
                      │  Server Routes   │     Static Assets   │
                      │   (api/web.py)   │    (/static/css,js) │
                      └────────┬─────────┴─────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│     Deterministic Engines     │   │      AI Provider Router       │
│  - Entity Resolution          │   │  - Groq Primary               │
│  - Market Pulse & OHLCV       │   │  - Groq Secondary             │
│  - Statements & Ratios        │   │  - OpenRouter Fallback        │
│  - Peer Comparison Matrix     │   │  - Circuit Breaker & Cooldown │
└───────────────────────────────┘   └───────────────────────────────┘
```

### Component Directory

| Component | Location | Role |
| --- | --- | --- |
| **FastAPI Entrypoint** | `api/index.py` | Production application mounting web routes, static files, rate limits, and health probes. |
| **Web & UI Router** | `api/web.py` | Jinja2 server-rendered pages, HTMX partial responses, formatting filters, and UI handlers. |
| **Templates** | `templates/` | Modular Jinja2 layouts (`base.html`), destinations (`market.html`, `analysis.html`, `compare.html`, `research.html`), and HTMX partials. |
| **Static Assets** | `static/` | High-contrast financial design system (`css/main.css`), minimal client JS (`js/app.js`), and vendor HTMX (`js/htmx.min.js`). |
| **Research Orchestrator** | `api/research_orchestrator.py` | Typed BFF unifying entity resolution, market pulse, history, financial metrics, and structured AI synthesis. |
| **Market Intelligence** | `api/market_intelligence_services.py` | In-memory cached Yahoo/yfinance quotes, multi-period charts (1D to 5Y), event radars, and deterministic signal algorithms. |
| **Company Deep Analysis** | `api/company_analysis_services.py` | Annual/quarterly balance sheets, income statements, cash flows, financial health ratios, and corporate governance rosters. |
| **Company Comparison** | `api/comparison_services.py` | Multi-ticker side-by-side metric matrix, currency conversion guards, period-alignment verification, and scoring engines. |
| **AI Provider Engine** | `api/ai_providers.py` | Multi-tier failover (Groq Primary → Groq Secondary → OpenRouter) with secret scrubbing and circuit breakers. |
| **Vercel Runtime** | `vercel.json` | Pure Python serverless configuration routing all traffic directly to `api/index.py` with asset bundling. |

---

## Primary Destinations & Research Capabilities

1. **Market Intelligence (`/` or `/symbol/:symbol`)**:
   Real-time quote summary, key statistics, interactive SVG price charts across 6 time horizons (1D, 5D, 1M, 6M, 1Y, 5Y), explainable technical signal indicators, company news, and upcoming corporate event calendar.
2. **Company Deep Analysis (`/analysis` or `/symbol/:symbol/analysis`)**:
   Audited multi-year financial statements (Income Statement, Balance Sheet, Cash Flow) across Annual and Quarterly frequencies, key valuation and solvency ratios, and corporate leadership governance data.
3. **Company Comparison (`/compare`)**:
   Side-by-side metric matrix comparing any two tickers, with currency conversion awareness, fiscal period alignment detection, category outcome indicators, and deterministic financial strength and momentum scorecards.
4. **AI Research Desk (`/research`)**:
   Structured synthesis across 4 operational modes (`standard`, `company_deep_analysis`, `market_intelligence`, `company_comparison`) with full provenance audit trails, source citations, and honest graceful fallbacks when AI keys are absent.

---

## Local Development & Quickstart

### Prerequisites
- Python 3.12+
- Git

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/SamSurve/Quant-AI.git
cd Quant-AI

python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt pytest httpx
```

### 2. Configure Environment (Optional)

Copy the configuration template:
```bash
cp .env.example .env
```
> **Note**: All financial data, charts, statements, and comparison calculations work **100% out of the box** without any API keys. To enable AI analyst synthesis, populate `GROQ_API_KEY_PRIMARY` in `.env`.

### 3. Run the Development Server

```bash
uvicorn api.index:app --reload --host 127.0.0.1 --port 8000
```
Open your browser to `http://127.0.0.1:8000`.

---

## Operational Health & Diagnostic Probes

The application provides dedicated operational endpoints for container and serverless health checks:

- `GET /health/live`: Liveness probe verifying process responsiveness (`{"status": "live"}`).
- `GET /health/ready`: Readiness probe verifying templates, static directories, and provider subsystems.
- `GET /api/health`: Diagnostic health report with provider configuration status (never leaking API keys).

---

## Automated Testing & CI

QuantAI features a comprehensive automated test suite spanning backend calculations, failover mechanisms, UI templates, HTMX partials, cross-destination integration, and production readiness.

Run the full test suite:
```bash
pytest -v
```

Run specific test modules:
```bash
# Web & UI regression tests
pytest tests/test_web_foundation.py tests/test_market_ui.py tests/test_company_ui.py tests/test_comparison_ui.py tests/test_research_ui.py tests/test_web_integration.py

# Backend calculation & provider hardening tests
pytest tests/test_ai_backend_hardening.py tests/test_company_analysis_backend.py tests/test_comparison_backend_hardening.py tests/test_market_backend_hardening.py

# Deployment and production readiness tests
pytest tests/test_deployment_readiness.py tests/test_production_readiness.py
```

Automated CI runs via GitHub Actions on every push and pull request to `main` and `python-first-refactor` (`.github/workflows/ci.yml`).

---

## Production Deployment (Vercel)

The repository is configured for direct deployment on Vercel using the Python runtime:

- `vercel.json` configures `api/index.py` as the serverless function handler, bundles `templates/**` and `static/**`, and rewrites all incoming traffic to FastAPI.
- `.python-version` pins the runtime to Python 3.12.
- Configure server-only environment variables in the Vercel Dashboard:
  - `GROQ_API_KEY_PRIMARY` (optional)
  - `GROQ_API_KEY_SECONDARY` (optional)
  - `OPENROUTER_API_KEY` (optional)
  - `AI_PROVIDER_ORDER` (optional)

*Obsolete legacy Vite/React artifacts have been completely retired; the application operates 100% as a pure Python-first system.*
