# QuantAI — Release Notes & Production Architecture

## Pure Python-First Architecture (Milestones 01–15)

QuantAI has completed its full architectural migration from a hybrid Vite/React/Express application to a clean, high-performance, Python-first platform powered by **FastAPI**, **Jinja2**, **HTMX**, and custom vanilla CSS.

### Production Runtime & File Layout

| Component | Location | Role |
| --- | --- | --- |
| **FastAPI Entrypoint** | `api/index.py` | Production entrypoint serving web routes, static files, rate limits, and health probes. |
| **Web & UI Router** | `api/web.py` | Server-rendered pages, HTMX partial endpoints, numerical formatters, and search resolvers. |
| **Templates** | `templates/` | Jinja2 templates for all 5 workspaces (`base.html`, `index.html`, `market.html`, `analysis.html`, `compare.html`, `research.html`) and HTMX partials. |
| **Static Assets** | `static/` | High-contrast financial design system (`css/main.css`), minimal client JS (`js/app.js`), and vendor HTMX (`js/htmx.min.js`). |
| **AI Provider Engine** | `api/ai_providers.py` | Multi-tier failover (Groq Primary → Groq Secondary → OpenRouter fallback) with secret scrubbing and circuit breakers. |
| **Research Orchestrator** | `api/research_orchestrator.py` | Unified typed orchestrator for entity resolution, quotes, charts, financial statements, comparisons, and AI briefs. |
| **Market Intelligence** | `api/market_intelligence_services.py` | Real-time quotes, multi-period OHLCV history, event radars, and explainable signal calculations. |
| **Company Deep Analysis** | `api/company_analysis_services.py` | Audited financial statements, balance sheets, cash flows, and corporate governance rosters. |
| **Company Comparison** | `api/comparison_services.py` | Side-by-side metric matrix, currency conversion guards, period-alignment verification, and scoring engines. |
| **Deployment Runtime** | `vercel.json` | Python-first serverless configuration routing all traffic directly to `api/index.py` with asset bundling. |
| **Python Version** | `.python-version` | Pinned to Python 3.12. |
| **CI/CD Pipeline** | `.github/workflows/ci.yml` | Automated GitHub Actions CI workflow executing pytest on Python 3.12. |

### Retired Legacy Infrastructure

The following legacy Node.js/React/Vite dependencies and artifacts have been completely retired:
- `client/`: Former React/TypeScript single-page application.
- `server/`: Former Express static file server.
- `shared/`: Former TypeScript shared constants.
- `patches/`: Former npm package patches.
- `package.json` & `pnpm-lock.yaml`: Former Node package manifests.
- `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `components.json`: Former frontend build tooling configurations.
- Legacy TypeScript test files in `tests/*.ts`.

All primary application functionality, research tools, and visual layouts have been 100% preserved in the Python runtime.
