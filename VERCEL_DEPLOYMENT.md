# Vercel Deployment Guide

## Architecture

The Analyst’s Ledger frontend is built by Vite into `dist/public`. Vercel routes browser requests under `/api/*` to `api/index.py`, which mounts the preserved AgentOS application under `/api`. Consequently, the frontend calls `POST /api/agents/groq-finance-agent/runs` in production without exposing any AI-provider credential or depending on `localhost:7777`. The root `requirements.txt` is intentionally flat because Vercel’s Python builder reads its production dependencies directly from that root manifest.

For local Vite development, the same `/api/*` path is proxied to the local AgentOS server at `http://127.0.0.1:7777` and the `/api` prefix is removed. For production-equivalent local testing, use `vercel dev`; its Python function serves `/api/*` on the same origin as the frontend.

## Required Vercel environment variables

| Name | Required | Scope | Value |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Recommended for `auto` | Production, Preview, and Development | A server-side Google Gemini API key. In `auto` mode, Gemini is tried first. |
| `GROQ_API_KEY` | Recommended for `auto` | Production, Preview, and Development | A server-side Groq API key with access to `openai/gpt-oss-120b`. Groq is the automatic fallback. |
| `AI_PROVIDER` | Yes | Production, Preview, and Development | `auto` (recommended), `gemini`, or `groq`. |
| `AGENTOS_API_URL` | No | Local Vite only | Override target for the Vite local proxy; default is `http://127.0.0.1:7777`. |
| `VITE_AGENTOS_API_URL` | No | Browser override only | Use only for a deliberately separate public AgentOS service. Leave unset for same-origin Vercel deployment. |

> Never add `GEMINI_API_KEY` or `GROQ_API_KEY` with a `VITE_` prefix. Variables prefixed with `VITE_` are included in the browser bundle. In `auto` mode, QuantAI tries Gemini once with one bounded retry, then tries Groq once with one bounded retry. It returns a clear temporary-unavailability message instead of forwarding raw provider errors when neither provider can answer.

## GitHub to Vercel deployment

1. Commit and push this repository to GitHub. The repository root must contain `vercel.json`, `api/index.py`, `requirements.txt`, and `package.json`.
2. In Vercel, select **Add New → Project**, import the GitHub repository, and leave the project root at the repository root.
3. Confirm the framework preset is **Vite**, the install command is `pnpm install --frozen-lockfile`, the build command is `pnpm run build`, and the output directory is `dist/public`.
4. In **Settings → Environment Variables**, add `GEMINI_API_KEY`, `GROQ_API_KEY`, and `AI_PROVIDER=auto` for Production, Preview, and Development. Do not commit a `.env` file or set a browser-visible provider variable.
5. Deploy a preview first. Verify `/api/health`, then use the dashboard to submit `AAPL`, `NVDA`, `MSFT`, `TSLA`, and `RELIANCE.NS`. Promote the preview to production only after those checks succeed.

## Local checks

```bash
pnpm install
pnpm run build

# Production-equivalent local routing (requires Vercel CLI and GROQ_API_KEY in the environment)
npx vercel dev
```

The Vercel Python runtime detects `api/index.py` as a FastAPI application and requires Python 3.12, pinned in `.python-version`. Vercel’s API route prefix is retained because `api/index.py` receives `/api/*` requests. [1] [2]

## References

[1]: https://vercel.com/docs/frameworks/backend/fastapi "Vercel: Deploy a FastAPI app"
[2]: https://vercel.com/academy/python-on-vercel/explore-fastapi-starter "Vercel Academy: Tour the FastAPI Starter"
[3]: https://vercel.com/docs/frameworks/frontend/vite "Vercel: Vite on Vercel"
[4]: https://vercel.com/kb/guide/why-is-my-deployed-project-giving-404 "Vercel: SPA and API route rewrites"
