# Vercel Deployment Guide

## Architecture

The Analyst’s Ledger frontend is built by Vite into `dist/public`. Vercel routes browser requests under `/api/*` to `api/index.py`, which mounts the preserved AgentOS application under `/api` and exposes a typed research BFF at `POST /api/research`. Consequently, the dashboard’s **Build brief** workflow receives deterministic market/news JSON without exposing any AI-provider credential or depending on `localhost:7777`; AgentOS chat continues to use `POST /api/agents/groq-finance-agent/runs`. The root `requirements.txt` is intentionally flat because Vercel’s Python builder reads its production dependencies directly from that root manifest.

For local Vite development, the same `/api/*` path is proxied to the local AgentOS server at `http://127.0.0.1:7777` and the `/api` prefix is removed. For production-equivalent local testing, use `vercel dev`; its Python function serves `/api/*` on the same origin as the frontend.

## Required Vercel environment variables

| Name | Required | Scope | Value |
| --- | --- | --- | --- |
| `GROQ_API_KEY_PRIMARY` | Yes for primary AI analysis | Production, Preview, and Development | Server-only credential for the first Groq provider. |
| `GROQ_MODEL_PRIMARY` | No | Production, Preview, and Development | Optional first Groq model; defaults to `openai/gpt-oss-120b`. |
| `GROQ_API_KEY_SECONDARY` | Recommended | Production, Preview, and Development | Server-only credential for the second Groq provider. |
| `GROQ_MODEL_SECONDARY` | No | Production, Preview, and Development | Optional second Groq model; defaults to `openai/gpt-oss-120b`. |
| `OPENROUTER_API_KEY` | Recommended final fallback | Production, Preview, and Development | Server-only OpenRouter bearer token. |
| `OPENROUTER_MODEL` | No | Production, Preview, and Development | Final fallback model; defaults to `stealth/ox-alpha`. |
| `AI_PROVIDER_ORDER` | No | Production, Preview, and Development | A duplicate-free permutation of `groq_primary,groq_secondary,openrouter_ox_alpha`; defaults to that exact order. |
| `AGENTOS_API_URL` | No | Local Vite only | Override target for the Vite local proxy; default is `http://127.0.0.1:7777`. |
| `VITE_AGENTOS_API_URL` | No | Browser override only | Use only for a deliberately separate public AgentOS service. Leave unset for same-origin Vercel deployment. |

> Never add a provider credential with a `VITE_` prefix. Variables prefixed with `VITE_` are included in the browser bundle. QuantAI attempts each configured provider at most once per request in fixed order: Groq primary, Groq secondary, then OpenRouter Ox Alpha. Permanent model/auth failures and repeated failures enter a process-local cooldown; the API returns a clear temporary-unavailability message instead of forwarding raw provider errors when all configured providers fail.

## Typed research contract and MVP controls

`POST /api/research` remains backward compatible with `{ "query": "AAPL", "include_analysis": true }`. The dashboard now submits `{ "query": "AAPL", "include_analysis": true, "mode": "market_intelligence" }`, which adds a `market_intelligence` object while retaining the established root fields. Its typed sections are `market_pulse`, normalized `price_history`, `market_signal`, `recent_news`, `event_radar`, `executive_brief`, and per-service `freshness`. Deterministic tool data remains authoritative; AI receives only validated context and contributes a separately validated interpretation.

The same endpoint also accepts `{ "query": "AAPL", "include_analysis": true, "mode": "company_deep_analysis" }`. Its additive `company_deep_analysis` object contains source-provided company overview, financial-health, leadership/governance, market-context, normalized news/events, competitor-evidence status, per-service freshness, and optional analyst interpretation. Company and financial values originate from yfinance/Yahoo profile and annual-statement accessors. The API returns `null`, empty lists, or safe partial warnings when public fields are unavailable; it does not estimate missing financials or manufacture competitors, market-share, or management-change claims.

For Company Comparison, use only `{ "mode": "company_comparison", "company_a": "AAPL", "company_b": "MSFT", "include_analysis": true }`. The endpoint resolves A and B separately, preserves identity and source/freshness isolation for each side, and returns the additive `company_comparison` report. That report includes independent side status, sourced market/financial/news/event data, metric-level A/B values, winner state, availability, period alignment, currency comparability, per-side provenance, deterministic financial-strength and momentum scores, category outcomes, overall confidence, and optional interpretation. The browser receives no provider metadata or credentials.

Raw monetary or per-share values are not ranked across currencies and are not FX converted. The service records `CURRENCY_COMPARISON_UNAVAILABLE` rather than inventing a conversion. It also withholds absolute-value winners when fiscal periods are only partially aligned or not aligned. `TIE` and `INSUFFICIENT_DATA` are valid deterministic outcomes; no winner is forced. AI interpretation receives compact validated comparison context after deterministic assembly and is rejected to a safe `AI_UNAVAILABLE` partial result if it includes numerical claims, unsupported events, URLs, market-share assertions, scores, or winners.

Market Intelligence retrieves one five-year daily OHLCV series and one one-day intraday series, then derives shorter chart periods locally rather than issuing a request per chart control. Market Pulse uses source quote fields, recent news is deduplicated from DDGS, and Event Radar exposes only dates that Yahoo/yfinance returns. Every result identifies its source and freshness/cache state. The deterministic 0–100 signal is an observation layer based on price momentum, moving-average alignment, volume context, and disclosed realized volatility; it is not investment advice or a prediction.

Each response includes an `X-Request-ID` header and matching `request_id` field. Errors use safe categories such as `ENTITY_NOT_FOUND`, `AMBIGUOUS_ENTITY`, `DATA_UNAVAILABLE`, `NEWS_UNAVAILABLE`, `AI_UNAVAILABLE`, `RATE_LIMITED`, and `TIMEOUT`; internal exceptions, paths, prompts, and credentials are not returned.

The current Vercel-compatible implementation deliberately uses process-local cache and anonymous request guards: 8 KiB request-body limit, 10 research requests per minute per warm instance, four concurrent research runs per warm instance, 60-second market-pulse TTL, five-minute history/news TTL, six-hour event TTL, and daily entity TTL. These controls reduce accidental abuse and duplicate work in a warm instance but do **not** create a shared cross-instance cache or global rate limit. Introduce a managed cache/rate-limit service before treating them as a multi-instance production control.

## GitHub to Vercel deployment

1. Commit and push this repository to GitHub. The repository root must contain `vercel.json`, `api/index.py`, `requirements.txt`, and `package.json`.
2. In Vercel, select **Add New → Project**, import the GitHub repository, and leave the project root at the repository root.
3. Confirm the framework preset is **Vite**, the install command is `pnpm install --frozen-lockfile`, the build command is `pnpm run build`, and the output directory is `dist/public`.
4. In **Settings → Environment Variables**, add `GROQ_API_KEY_PRIMARY`, `GROQ_API_KEY_SECONDARY`, and `OPENROUTER_API_KEY` for Production, Preview, and Development. Set model overrides only when needed; do not commit a `.env` file or set a browser-visible provider variable.
5. Deploy a preview first. Verify `/api/health`, then use the dashboard to submit `AAPL`, `NVDA`, `MSFT`, `TSLA`, and `RELIANCE.NS`. Promote the preview to production only after those checks succeed.

## Local checks

```bash
pnpm install
pnpm run build
PYTHONDONTWRITEBYTECODE=1 python tests/test_typed_research_backend.py
PYTHONDONTWRITEBYTECODE=1 python tests/test_market_intelligence.py
PYTHONDONTWRITEBYTECODE=1 python tests/test_company_deep_analysis.py
PYTHONDONTWRITEBYTECODE=1 python tests/test_company_comparison.py

# Production-equivalent local routing (requires Vercel CLI and at least one server-side provider credential)
npx vercel dev
```

The Vercel Python runtime detects `api/index.py` as a FastAPI application and requires Python 3.12, pinned in `.python-version`. Vercel’s API route prefix is retained because `api/index.py` receives `/api/*` requests. [1] [2]

## References

[1]: https://vercel.com/docs/frameworks/backend/fastapi "Vercel: Deploy a FastAPI app"
[2]: https://vercel.com/academy/python-on-vercel/explore-fastapi-starter "Vercel Academy: Tour the FastAPI Starter"
[3]: https://vercel.com/docs/frameworks/frontend/vite "Vercel: Vite on Vercel"
[4]: https://vercel.com/kb/guide/why-is-my-deployed-project-giving-404 "Vercel: SPA and API route rewrites"
