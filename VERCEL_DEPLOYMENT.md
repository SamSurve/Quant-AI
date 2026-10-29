# Vercel Deployment Guide — Python-First Architecture

## Architecture

QuantAI is deployed as a high-performance Python-first application powered by **FastAPI**, **Jinja2**, and **HTMX**. Vercel routes all browser requests directly to `api/index.py` using Vercel Python Serverless Functions.

The application serves server-rendered HTML pages, HTMX partial fragments, and high-performance vanilla CSS/JS static assets directly from the Python runtime, eliminating the need for Node.js, pnpm, Express, or a React/Vite build pipeline in production.

All core market intelligence, technical price charts, financial statements, balance sheets, and peer comparisons run deterministically using Yahoo Finance data without requiring external AI keys. Optional AI analyst synthesis is provided via an automated multi-provider failover router (Groq primary → Groq secondary → OpenRouter fallback).

## Required Vercel Environment Variables

| Name | Required | Scope | Value |
| --- | --- | --- | --- |
| `GROQ_API_KEY_PRIMARY` | Optional (enables AI) | Production, Preview, Development | Server-only credential for the primary Groq provider. |
| `GROQ_MODEL_PRIMARY` | No | Production, Preview, Development | Optional first Groq model; defaults to `openai/gpt-oss-120b`. |
| `GROQ_API_KEY_SECONDARY` | Recommended | Production, Preview, Development | Server-only credential for the secondary Groq provider. |
| `GROQ_MODEL_SECONDARY` | No | Production, Preview, Development | Optional second Groq model; defaults to `openai/gpt-oss-120b`. |
| `OPENROUTER_API_KEY` | Recommended final fallback | Production, Preview, Development | Server-only OpenRouter bearer token. |
| `OPENROUTER_MODEL` | No | Production, Preview, Development | Final fallback model; defaults to `stealth/ox-alpha`. |
| `AI_PROVIDER_ORDER` | No | Production, Preview, Development | A duplicate-free permutation of `groq_primary,groq_secondary,openrouter_ox_alpha`; defaults to that exact order. |

> **Security Note:** Provider credentials are strictly server-only. Never expose API keys or commit a `.env` file. If no provider credentials are configured, the application operates in 100% deterministic mode and safely returns complete financial data with graceful partial notices when AI synthesis is requested.

## Typed Research Contract & Endpoints

- `GET /`: Dashboard overview.
- `GET /market` or `GET /symbol/:symbol`: Market Intelligence workspace with interactive price charts.
- `GET /analysis` or `GET /symbol/:symbol/analysis`: Audited financial statements and corporate governance.
- `GET /compare`: Side-by-side peer comparison matrix with currency protection.
- `GET /research` or `POST /research`: Dedicated AI Research Desk supporting all 4 modes (`standard`, `market_intelligence`, `company_deep_analysis`, `company_comparison`).
- `GET /search?q=...`: Instant search suggestions for listed equities.
- `GET /health/live`: Container and process liveness probe (`{"status": "live"}`).
- `GET /health/ready`: Readiness probe verifying templates and static assets (`{"status": "ready", ...}`).
- `GET /api/health`: Diagnostic health report with safe provider configuration status.
- `POST /api/agents/groq-finance-agent/runs`: Conversational research agent endpoint.

## GitHub to Vercel Deployment

1. Push this repository to GitHub on branch `main`.
2. In Vercel, select **Add New → Project**, import the GitHub repository, and leave the project root at repository root.
3. Vercel automatically detects `vercel.json` and Python dependencies in `requirements.txt`. No Node.js build commands or output directories are needed.
4. In **Settings → Environment Variables**, add your optional `GROQ_API_KEY_PRIMARY`, `GROQ_API_KEY_SECONDARY`, and `OPENROUTER_API_KEY` for Production and Preview environments.
5. Deploy. Verify `/health/live` and `/health/ready`, then test research queries (`AAPL`, `MSFT`, `NVDA`).

## Local Development & Validation

```bash
# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt pytest httpx

# Run local development server
uvicorn api.index:app --reload --host 127.0.0.1 --port 8000

# Run automated regression tests
pytest -v
```
