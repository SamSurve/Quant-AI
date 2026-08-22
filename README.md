# QuantAI Finance Agent

This repository contains the provider-resilient **QuantAI Finance Agent** and its **Analyst’s Ledger** frontend. The browser application is a Vite/React dashboard and the research API is an AgentOS application exposed through a Vercel-compatible FastAPI function.

## What is included

| Component | Location | Role |
| --- | --- | --- |
| Analyst’s Ledger | `client/` | Responsive React dashboard, price cards, chart, news, analysis, loading, and error states. |
| Vercel API function | `api/index.py` | Same-origin FastAPI entrypoint mounted under `/api`. |
| QuantAI provider router | `api/ai_providers.py` | Server-only Gemini-primary/Groq-fallback model selection with bounded retries and clean unavailability errors. |
| QuantAI finance agent | `api/groq_finance_agent.py` | AgentOS, real YFinance company/ticker resolution, DDGS news research, and the provider router. |
| Vercel configuration | `vercel.json` | Vite build output, SPA fallback excluding `/api`, function duration, and no-cache API headers. |

## Local development

For the quickest two-terminal workflow, start the AgentOS server and Vite frontend separately:

```bash
# Terminal 1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set GEMINI_API_KEY and/or GROQ_API_KEY in the terminal environment.
# Set AI_PROVIDER to auto, gemini, or groq (auto is the recommended default).
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
```

## Vercel

Read [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md) for the exact environment variables, GitHub import workflow, Vercel project settings, preview checks, and deployment validation steps.

> `GEMINI_API_KEY`, `GROQ_API_KEY`, and `AI_PROVIDER` are server-only. Do not commit key values, do not use a `VITE_` prefix for any provider setting, and configure them through local process environment variables or Vercel Environment Variables.
