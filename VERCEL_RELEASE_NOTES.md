# Vercel Release Notes

## Exact Files Added or Changed

| File or directory | Change |
| --- | --- |
| `api/__init__.py` | Added Vercel Python function package marker. |
| `api/index.py` | Added FastAPI Vercel entrypoint, `/api/health`, provider-safe runtime metadata, and mounted AgentOS routes. |
| `api/research_schemas.py`, `api/research_errors.py` | Added the stable typed JSON contract and normalized safe error envelopes. |
| `api/research_services.py`, `api/research_cache.py`, `api/research_protection.py`, `api/research_logging.py` | Added deterministic entity/market/news adapters, process-local TTL/dedup cache, bounded anonymous controls, and safe operational logging. |
| `api/research_orchestrator.py` | Added bounded parallel research assembly and validated AI synthesis that treats deterministic source data as authoritative. |
| `api/market_intelligence_services.py` | Added cache-aware market pulse, efficient intraday/five-year OHLCV retrieval, source-returned event radar, freshness records, and transparent deterministic signal calculation. |
| `api/company_analysis_services.py` | Added cache-aware company profile, source-provided leadership, annual financial statement, cash-flow, balance-sheet, and valuation-input services with conservative competitor-evidence absence handling. |
| `api/comparison_services.py` | Added independent dual-company acquisition that reuses existing cache-aware adapters, metric-level provenance, conservative currency/fiscal-period alignment, deterministic scores, category outcomes, confidence, and safe side status. |
| `api/research_orchestrator.py` | Added the bounded `company_deep_analysis` path with concurrent independent deterministic services and an optional evidence-bound AI interpretation. |
| `api/research_schemas.py`, `api/research_errors.py` | Added Company Deep Analysis request mode, factual-versus-interpretation schemas, freshness, and safe company/financial/governance partial-data errors. |
| `api/research_schemas.py`, `api/research_errors.py` | Extended the additive typed contract with `market_intelligence` mode, signal/history/freshness schemas, and safe history/event partial-data errors. |
| `api/ai_providers.py` | Added server-side Groq-primary, Groq-secondary, and OpenRouter Ox Alpha one-way provider routing with normalized failures, bounded attempts, cooldown health, and clean unavailable responses. |
| `api/groq_finance_agent.py` | Preserved the AgentOS backend and real research tools while switching its model to the QuantAI provider router. |
| `requirements.txt` | Retained the flat Vercel Python manifest, removed the unused Google provider SDK, and added the OpenAI-compatible dependency required by Agno’s OpenRouter integration. |
| `.python-version` | Pinned Vercel Python runtime to 3.12. |
| `vercel.json` | Added Vite output, API function, no-cache headers, and API-safe SPA fallback. |
| `vite.config.ts` | Changed local proxy from `/agentos` to `/api`. |
| `client/src/lib/agentos.ts` | Keeps the production default at same-origin `/api` and normalizes temporary provider errors for the existing dashboard. |
| `client/src/lib/research.ts`, `client/src/lib/market.ts`, `client/src/pages/Home.tsx` | Preserved the dashboard design while making **Build brief** request typed `market_intelligence`, with signal, event, source, freshness, and partial-data displays; AgentOS remains for chat. |
| `client/src/lib/comparison.ts`, `client/src/components/ComparisonPanel.tsx`, `client/src/pages/Home.tsx` | Added a minimal Company A/Company B workflow and structured comparison ledger, category outcomes, evidence-bound interpretation, per-side source status, news/events, and provenance without redesigning Analyst’s Ledger. |
| `client/src/components/BrandMark.tsx` and `ChatPanel.tsx` | Retained the existing visual system while applying the provider-independent QuantAI identity. |
| `client/public/assets/` | Added all Analyst’s Ledger visual assets required for local and Vercel deployment. |
| `package.json` and `pnpm-lock.yaml` | Added Vercel build script and refreshed lock metadata. |
| `.gitignore` | Excluded `.vercel/` and retained local secret exclusions. |
| `tests/test_typed_research_backend.py` | Added no-network typed-BFF validation, ambiguity, partial-data, cache/deduplication, timeout, request-size, request-ID, safe-error, and route tests. |
| `tests/test_market_intelligence.py` | Added no-network deterministic signal, Market Intelligence mode, source/freshness, partial-failure, structured AI separation, and public route tests. |
| `tests/test_company_deep_analysis.py` | Added no-network company profile, deterministic financial preservation, governance, source provenance, competitor absence, valuation/risk interpretation, partial-failure, AI-unavailable, and public route tests. |
| `tests/test_company_comparison.py` | Added no-network A/B identity isolation, winners/ties/insufficient state, currency and fiscal-period protections, per-side partial failure, numeric-guard, cache deduplication, request validation, and public route regressions. |
| `README.md` and `VERCEL_DEPLOYMENT.md` | Added provider-safe local setup and exact GitHub-to-Vercel deployment instructions. |

## Required Vercel Environment Variables

| Name | Required environments | Notes |
| --- | --- | --- |
| `GROQ_API_KEY_PRIMARY` | Production, Preview, Development | Server-only first Groq credential. |
| `GROQ_MODEL_PRIMARY` | Production, Preview, Development | Optional first Groq model; defaults to `openai/gpt-oss-120b`. |
| `GROQ_API_KEY_SECONDARY` | Production, Preview, Development | Server-only second Groq credential. |
| `GROQ_MODEL_SECONDARY` | Production, Preview, Development | Optional second Groq model; defaults to `openai/gpt-oss-120b`. |
| `OPENROUTER_API_KEY` | Production, Preview, Development | Server-only final-fallback credential. |
| `OPENROUTER_MODEL` | Production, Preview, Development | Optional final-fallback model; defaults to `stealth/ox-alpha`. |

Leave `VITE_AGENTOS_API_URL` unset to use the deployed same-origin `/api` function. Never use a `VITE_` prefix for provider credentials.

## GitHub and Vercel Deployment

1. Extract the ZIP and push the repository root to GitHub.
2. Import the repository at Vercel and keep the root directory at the repository root.
3. Confirm **Vite** framework, `pnpm install --frozen-lockfile`, `pnpm run build`, and `dist/public` output directory.
4. Add the configured Groq primary/secondary and OpenRouter provider variables to Production, Preview, and Development in Vercel Project Settings.
5. Deploy a preview, verify `/api/health`, then submit `AAPL`, `NVDA`, `MSFT`, `TSLA`, and `RELIANCE.NS` through the dashboard before promoting.

## Local Validation

Provider simulations cover Groq primary success, Groq primary 429/timeout/5xx/model/auth failures, Groq secondary fallback, OpenRouter Ox Alpha final fallback, cooldown skips, malformed output, all-provider safe failure, and bounded one-way routing. The typed research regression covers entity validation, ambiguous entities, normalized market/news results, partial results, malformed AI handling, cache/in-flight deduplication, request-size enforcement, correlation IDs, safe errors, health, and AgentOS compatibility. Market Intelligence regression covers deterministic signal math, typed `market_intelligence` route behavior, source/freshness fields, event radar, AI/fact separation, and partial dependency failures. Company Comparison regression covers A/B isolation, per-side error safety, currency/period winner withholding, scores/category outcomes, numeric AI leakage rejection, cache deduplication, and route validation. Local validation includes TypeScript/Python checks, a production frontend build, same-origin routes, and real deterministic AAPL/MSFT, NVDA/AMD, and GOOG/META comparison structures. Credentialed live AI verification remains intentionally unclaimed when server-side provider variables are unavailable.
