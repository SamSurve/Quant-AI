# QuantAI Finance Agent

This repository contains the provider-resilient **QuantAI Finance Agent** and its **Analyst’s Ledger** frontend. The browser application is a Vite/React dashboard and the research API is an AgentOS application exposed through a Vercel-compatible FastAPI function.

## What is included

| Component | Location | Role |
| --- | --- | --- |
| Analyst’s Ledger | `client/` | Responsive React dashboard, price cards, chart, news, analysis, loading, and error states. |
| Vercel API function | `api/index.py` | Same-origin FastAPI entrypoint mounted under `/api`. |
| QuantAI provider engine | `api/ai_providers.py` | Server-only Groq-primary, Groq-secondary, OpenRouter Ox Alpha sequential fallback with bounded per-provider attempts, cooldown health, and clean unavailability errors. |
| Typed research BFF | `api/research_orchestrator.py` | Deterministic entity, market pulse, efficient OHLCV history, signals, news, events, and best-effort structured AI interpretation. |
| Market Intelligence adapters | `api/market_intelligence_services.py` | Cache-aware Yahoo/yfinance market pulse, history, event radar, and transparent deterministic signal methodology. |
| Company Deep Analysis adapters | `api/company_analysis_services.py` | Cache-aware source-provided company profile, leadership, annual financial-statement, cash-flow, balance-sheet, and valuation-input extraction. |
| Company Comparison services | `api/comparison_services.py` | Independent A/B acquisition, source-transparent metric normalization, currency/period protection, deterministic strength/momentum scores, category outcomes, and confidence. |
| QuantAI finance agent | `api/groq_finance_agent.py` | Preserved AgentOS conversational compatibility with real YFinance/DDGS research tools and the provider router. |
| Vercel configuration | `vercel.json` | Vite build output, SPA fallback excluding `/api`, function duration, and no-cache API headers. |

## Local development

For the quickest two-terminal workflow, start the AgentOS server and Vite frontend separately:

```bash
# Terminal 1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set GROQ_API_KEY_PRIMARY and GROQ_MODEL_PRIMARY.
# Optionally set GROQ_API_KEY_SECONDARY/GROQ_MODEL_SECONDARY and OPENROUTER_API_KEY/OPENROUTER_MODEL.
# Provider order is fixed: Groq primary → Groq secondary → OpenRouter Ox Alpha.
# Optionally override order with a duplicate-free permutation in AI_PROVIDER_ORDER,
# for example: groq_primary,groq_secondary,openrouter_ox_alpha.
python -m uvicorn api.index:app --host 127.0.0.1 --port 7777

# Terminal 2
pnpm install
pnpm dev
```

The Vite development server proxies browser requests from `/api/*` to the local AgentOS server, so the frontend retains the same API URL in development and deployment.

## Reliability check

Run the deterministic provider failover regression test without provider credentials or quota usage:

```bash
python tests/test_provider_failover.py
python tests/test_typed_research_backend.py
python tests/test_market_intelligence.py
python tests/test_company_deep_analysis.py
python tests/test_company_comparison.py
```

## Typed research API

`POST /api/research` remains compatible with `{ "query": "AAPL", "include_analysis": true }`. The dashboard uses `{ "query": "AAPL", "include_analysis": true, "mode": "market_intelligence" }` for **Build brief**. This additive mode retains the established root fields and adds a typed `market_intelligence` section containing market pulse, normalized intraday/daily OHLCV history, deterministic signal, normalized/deduplicated news, source-returned event radar, per-service freshness, sources, warnings, and an optional structured executive brief. AgentOS remains available for conversational chat at `/api/agents/groq-finance-agent/runs`.

The Market Intelligence signal is an explainable observation layer based on price momentum, moving-average alignment, volume context, and disclosed realized volatility. It is not a forecast, investment recommendation, or substitute for independent review. Price and source fields are deterministic; the provider engine can only contribute the separately validated executive interpretation. When AI is unavailable, the endpoint returns deterministic data with `AI_UNAVAILABLE` as a partial-result warning instead of inventing an analysis.

`POST /api/research` also supports `{ "query": "AAPL", "include_analysis": true, "mode": "company_deep_analysis" }`. The additive `company_deep_analysis` section separates factual `company_overview`, `financial_health`, `governance`, `market_context`, normalized news/events, and source/freshness records from the optional `analyst_interpretation`. It uses source-provided Yahoo/yfinance profile and annual-statement fields only; unavailable values remain null. The current MVP deliberately returns an explicit unavailable competitor-evidence record rather than manufacturing peer, market-share, management-change, or regulatory claims. Valuation classification and risk/catalyst language are AI interpretations, not factual observations, recommendations, or predictions.

`POST /api/research` additionally accepts the comparison-only body `{ "mode": "company_comparison", "company_a": "AAPL", "company_b": "MSFT", "include_analysis": true }`. It resolves both inputs independently and rejects absent, duplicate, invalid, or ambiguous company selections rather than silently selecting a candidate. The additive `company_comparison` section returns explicit A/B identities, independent safe-side status/freshness, A/B market and financial records, news/events, metric rows, source provenance, deterministic financial-strength and momentum scores, category outcomes, confidence, and an optional `analyst_interpretation`.

Comparison winners are only emitted when both values are available and safe to compare. Monetary and per-share fields are never converted across currencies; differing currencies produce an explicit `CURRENCY_COMPARISON_UNAVAILABLE` note without a winner or difference. Absolute-value financial metrics with only partially aligned fiscal periods also remain `INSUFFICIENT_DATA`; ratio and percentage metrics retain their disclosed period-alignment state. The overall advantage is deliberately withheld when coverage, alignment, or category separation is insufficient. The optional AI brief sees compact validated context only, cannot author numerical facts, events, URLs, competitors, market-share claims, scores, or winners, and is rejected into a safe `AI_UNAVAILABLE` warning if it contains a numeric claim.

The Vercel MVP uses a small process-local TTL cache and in-flight request deduplication. This improves repeated requests within a warm function instance but is not a shared multi-instance cache. The route also applies a 8 KiB request-body limit, a 10-request-per-minute anonymous warm-instance limit, and a four-request warm-instance concurrency guard. These are pragmatic safeguards, not a substitute for a managed shared rate-limit/cache service.

## Vercel

Read [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md) for the exact environment variables, GitHub import workflow, Vercel project settings, preview checks, and deployment validation steps.

> `GROQ_API_KEY_PRIMARY`, `GROQ_API_KEY_SECONDARY`, and `OPENROUTER_API_KEY` are server-only. Do not commit key values, do not use a `VITE_` prefix for any provider setting, and configure them through local process environment variables or Vercel Environment Variables.
