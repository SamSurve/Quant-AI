# Vercel Release Notes

## Exact Files Added or Changed

| File or directory | Change |
| --- | --- |
| `api/__init__.py` | Added Vercel Python function package marker. |
| `api/index.py` | Added FastAPI Vercel entrypoint, `/api/health`, provider-safe runtime metadata, and mounted AgentOS routes. |
| `api/ai_providers.py` | Added server-side Gemini-primary/Groq-fallback provider routing with bounded retries and clean unavailable responses. |
| `api/groq_finance_agent.py` | Preserved the AgentOS backend and real research tools while switching its model to the QuantAI provider router. |
| `requirements.txt` | Added the single flat root Vercel Python dependency manifest. |
| `.python-version` | Pinned Vercel Python runtime to 3.12. |
| `vercel.json` | Added Vite output, API function, no-cache headers, and API-safe SPA fallback. |
| `vite.config.ts` | Changed local proxy from `/agentos` to `/api`. |
| `client/src/lib/agentos.ts` | Keeps the production default at same-origin `/api` and normalizes temporary provider errors for the existing dashboard. |
| `client/src/pages/Home.tsx` | Preserved design while improving company-name input and research-loading copy. |
| `client/src/components/BrandMark.tsx` and `ChatPanel.tsx` | Retained the existing visual system while applying the provider-independent QuantAI identity. |
| `client/public/assets/` | Added all Analyst’s Ledger visual assets required for local and Vercel deployment. |
| `package.json` and `pnpm-lock.yaml` | Added Vercel build script and refreshed lock metadata. |
| `.gitignore` | Excluded `.vercel/` and retained local secret exclusions. |
| `README.md` and `VERCEL_DEPLOYMENT.md` | Added provider-safe local setup and exact GitHub-to-Vercel deployment instructions. |

## Required Vercel Environment Variables

| Name | Required environments | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | Production, Preview, Development | Server-only Gemini credential; primary in `auto` mode. |
| `GROQ_API_KEY` | Production, Preview, Development | Server-only Groq credential; fallback in `auto` mode. |
| `AI_PROVIDER` | Production, Preview, Development | `auto` (recommended), `gemini`, or `groq`. |

Leave `VITE_AGENTOS_API_URL` unset to use the deployed same-origin `/api` function. Never use a `VITE_` prefix for provider credentials.

## GitHub and Vercel Deployment

1. Extract the ZIP and push the repository root to GitHub.
2. Import the repository at Vercel and keep the root directory at the repository root.
3. Confirm **Vite** framework, `pnpm install --frozen-lockfile`, `pnpm run build`, and `dist/public` output directory.
4. Add `GEMINI_API_KEY`, `GROQ_API_KEY`, and `AI_PROVIDER=auto` to Production, Preview, and Development in Vercel Project Settings.
5. Deploy a preview, verify `/api/health`, then submit `AAPL`, `NVDA`, `MSFT`, `TSLA`, and `RELIANCE.NS` through the dashboard before promoting.

## Local Validation

Provider simulations cover Gemini success, Gemini 429/5xx/timeout fallback, explicit Groq success, Groq 429 handling, both-provider failure, and bounded one-way routing. Local validation covers TypeScript, Python compilation, root dependency resolution, Vercel JSON, same-origin and Vite-proxied AgentOS routes, real YFinance company/ticker resolution, DDGS news retrieval, production build, and secret-value scanning.
