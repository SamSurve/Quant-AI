# End-to-End AAPL Integration Test

- [ ] Start the unchanged AgentOS finance backend with a valid `XAI_API_KEY` and verify its health.
- [x] Route the browser frontend to the live AgentOS base URL without modifying backend code.
- [ ] Trigger the AAPL “Build brief” workflow through the frontend path and capture the backend request.
- [ ] Verify the response supplies and renders price, metrics, analysis, news/source content, and a chart when the agent supplies dated price data.
- [ ] Confirm the visible loading state and a real connection/error state.
- [ ] Report exact results and only frontend configuration changes, if one is necessary.

## Credentialed AAPL Re-test

- [ ] Verify the secured `XAI_API_KEY` is available to the existing backend process without printing it.
- [ ] Start the unchanged backend with that inherited runtime environment.
- [ ] Execute the AAPL request through the real browser interaction path and validate response-backed displays.
- [ ] Report only pass status or the remaining integration error.

## Temporary Credentialed Test Session

- [ ] Start the existing AgentOS backend with the user-provided key scoped to the process environment only.
- [ ] Run the real AAPL browser workflow and inspect the live AgentOS response-backed interface.
- [ ] Stop the temporary backend process and report the verification outcome without disclosing the credential.

## Groq Migration and Live Research Verification

- [x] Verify the supported Agno Groq model integration and the existing agent’s current runtime dependencies.
- [x] Replace the xAI model configuration with Groq using `GROQ_API_KEY` only, removing xAI-specific dependencies and environment requirements.
- [x] Add reliable company-name and supported Indian-ticker resolution without introducing hardcoded market results.
- [x] Preserve AgentOS, YFinance, and web/news search tools while improving source-backed output structure.
- [x] Verify the frontend renders the converted backend response with live price, metrics, analysis, news, and price history when returned.
- [x] Run live end-to-end requests for NVIDIA/NVDA, Apple/AAPL, Microsoft/MSFT, Tesla/TSLA, and Reliance/RELIANCE.NS.
- [x] Re-run the NVIDIA and Apple browser workflows and record all requested pass/fail checks.

## Secured Groq Live Test Run

- [ ] Confirm `GROQ_API_KEY` is available to the temporary AgentOS runtime without revealing it.
- [ ] Start the Groq AgentOS backend and confirm it exposes `groq-finance-agent`.
- [ ] Execute live research for NVIDIA, Apple, Microsoft, Tesla, and Reliance using company-name inputs.
- [ ] Verify NVIDIA and Apple through the actual frontend Build brief interaction and inspect response-backed displays.
- [ ] Confirm price, company information, metrics, news, analysis, and price-history data are sourced from the live response when available.

## Temporary Backend-only Groq Credential

- [x] Inject the user-provided credential into the isolated backend process environment only and verify its availability without printing it.
- [x] Complete live AgentOS research for NVIDIA, Apple, Microsoft, Tesla, and Reliance.
- [x] Complete NVIDIA and Apple browser Build brief verification with response-backed displays.
- [x] Remove temporary credential material and stop the test backend before reporting results.

## Complete Local Project ZIP

- [ ] Inventory the final Groq backend, Analyst’s Ledger frontend, package manifests, proxy settings, and required source assets.
- [ ] Assemble one clean project directory with backend, frontend, root `.env.example`, and key-free local run instructions.
- [ ] Verify required files, dependency manifests, secret exclusion, ZIP extraction, and local configuration references.
- [ ] Deliver the complete downloadable ZIP archive.

## Final Package-Only Delivery

- [ ] Verify the already assembled release tree and provide its downloadable key-free ZIP without further application changes.

## Vercel Deployment Conversion

- [ ] Audit the final Groq backend and Analyst’s Ledger frontend against Vercel’s Python function and Vite deployment requirements.
- [ ] Add a Vercel-compatible AgentOS entrypoint, Vercel configuration, and deployment manifests without exposing `GROQ_API_KEY`.
- [ ] Route production frontend requests through a same-origin API path while retaining local Vite-to-AgentOS proxy behavior.
- [ ] Validate the production Vite build and the production-equivalent API route for AAPL, NVDA, MSFT, TSLA, and RELIANCE.NS.
- [ ] Document exact Vercel environment variables and GitHub deployment steps, then provide a complete updated ZIP.

## Vercel ZIP-only Delivery

- [ ] Package the complete Vercel-ready repository, including the local Analyst’s Ledger assets, without a Manus checkpoint.
- [ ] Verify archive extraction, required Vercel files, and exclusion of API-key values before delivery.

## Production Deployment Resilience Fixes

- [ ] Replace the nested Python requirements reference with a root Vercel-compatible dependency manifest.
- [ ] Add server-side bounded retry/backoff and clean error normalization for Groq 429, quota, rate-limit, and transient 5xx failures.
- [ ] Surface temporary AI unavailability in the existing dashboard without changing its design or exposing credentials.
- [ ] Validate the Vercel configuration, Python dependency resolution, production build, and error behavior.

## Vercel AgentOS 404 Repair

- [ ] Trace the frontend’s deployed AgentOS URL and the Vercel rewrite/function mount path responsible for the 404.
- [ ] Correct the production API route while preserving AgentOS, Groq, YFinance, DDGS, and the Analyst’s Ledger UI.
- [ ] Validate `/api/agents`, the finance-agent run route, and production build behavior for AAPL, MSFT, NVDA, and TSLA.
- [ ] Record the exact changed files and Vercel deployment action required to apply the fix.

## Final Updated ZIP

- [ ] Package the final Vercel AgentOS route repair and Groq resilience updates with all existing project source and assets.
- [ ] Verify the fresh archive contains the repaired API files, excludes API-key values, and can be extracted successfully.

## QuantAI Multi-provider Production Upgrade

- [ ] Audit the current AgentOS model wiring, real market/news tools, API routes, and secret boundary before adding a provider abstraction.
- [ ] Implement the prior provider migration with explicit modes and bounded one-way failover.
- [ ] Preserve real YFinance, DDGS/news, company/ticker resolution, Vercel `/api` routing, and the existing Analyst’s Ledger design.
- [ ] Add only minimal provider and research-status feedback needed for resilient, user-friendly behavior.
- [ ] Simulate provider success, rate-limit, 5xx, timeout, and all-unavailable paths without consuming external quotas.
- [ ] Validate real market data, news, company resolution, AgentOS routes, local backend behavior, production build, Vercel configuration, and secret exclusion.
- [ ] Update the server-side environment and deployment documentation, package the final project, and report every requested validation result.

## Vercel Python Cache-path Deployment Repair

- [x] Audit tracked and untracked repository artifacts, Vercel ignore rules, Python function configuration, and build commands to identify the cache-path failure cause.
- [x] Exclude or remove Python caches, bytecode, local Vercel output, test-generated files, and other non-production artifacts without removing required source.
- [x] Perform a clean production validation from a removed-cache, fresh-install state and record every required result.
- [x] Remove all generated artifacts and repeat the full validation independently from scratch.
- [x] Review the final diff and credential exclusions, then commit the verified fix; no GitHub remote was configured to receive a push.

## QuantAI Phase 2: Production Backend Rebuild

- [x] Define versioned typed research, status, source, warning, and normalized error schemas without changing provider behavior.
- [x] Build deterministic entity-resolution, market-data, news, cache, request-protection, timeout, and correlation-log services behind testable interfaces.
- [x] Add bounded parallel research orchestration and validated structured AI synthesis that returns partial results safely.
- [x] Expose stable same-origin typed research routes while retaining the existing AgentOS API routes for conversational compatibility.
- [x] Add and run backend regression tests for validation, ambiguity, provider/data failures, cache/deduplication, timeouts, error safety, route compatibility, and credential exclusion.
- [x] Validate local backend imports/routes, frontend production build, Vercel configuration, changed-file review, and Phase 2 limitations before reporting.

## QuantAI Phase 3: Production AI Provider Engine

- [x] Audit every existing provider dependency, configuration, router, structured-output integration, test, and documentation reference before migration.
- [x] Implement server-only Groq primary, Groq secondary, and OpenRouter Ox Alpha configuration with normalized failure classifications, bounded sequential fallback, and process-local provider health cooldowns.
- [x] Preserve typed analysis validation, deterministic research independence, and technically useful AgentOS compatibility under the new provider layer.
- [x] Remove former-provider code, SDK dependency, variables, tests, and non-historical documentation references without affecting unrelated libraries.
- [x] Add and run the full simulated provider matrix, local API/build/security/Vercel validations; live provider validation remains pending because no server-side credentials were present.
- [x] Review provider order, loop prevention, safe error boundary, final source scans, known limitations, and Phase 4 work before reporting.

## QuantAI Phase 3: Credentialed Live Verification

- [ ] Safely verify the supplied local environment contains the expected server-only provider variables without reading or recording their values.
- [ ] Perform one minimal live structured request through Groq primary, Groq secondary, and OpenRouter Ox Alpha, validating the existing analysis schema.
- [ ] Perform one real typed AAPL request, verify deterministic market/news data and successful AI analysis, and rerun controlled no-network fallback simulations.
- [ ] Validate Git/environment exclusion, source/build/log credential safety, local API routes, Python/TypeScript/Vite/Vercel checks, and remove temporary credentialed artifacts.
- [ ] Deliver a safe PASS/FAIL report that contains no secret values, provider payloads, or sensitive logs.

## QuantAI Phase 4: Market Intelligence

- [x] Audit the existing typed research response, deterministic source adapters, history/news/event availability, cache contract, and current dashboard consumers.
- [x] Define backward-compatible `market_intelligence` schemas for market pulse, normalized OHLCV history, deterministic signals, news intelligence, events, sources, freshness, warnings, and constrained executive interpretation.
- [x] Build deterministic cache-aware market, history, signal, news, and event services that return null, empty, or unavailable states rather than fabricated values.
- [x] Assemble one source-transparent Market Intelligence response with bounded parallel fetches and a validated provider-engine AI brief.
- [x] Integrate the existing Build brief workflow with typed Market Intelligence fields without redesigning Analyst’s Ledger.
- [x] Add and run ticker, invalid/ambiguous, partial-failure, cache, source/freshness, security, local route, build, Vercel, and real deterministic-data validation; document process-local limitations and Phase 5 boundary.

## QuantAI Phase 5: Company Deep Analysis

- [x] Audit reusable Phase 2–4 contracts/adapters and define typed company overview, financial health, governance, competitive-evidence, valuation, provenance, and evidence-bound AI schemas.
- [x] Build cache-aware deterministic services for factual company, financial, leadership/governance, and valuation-input data without fabricating missing values.
- [x] Orchestrate one bounded `company_deep_analysis` report with concurrent independent sources, safe partial failures, compact evidence context, and validated AI interpretation.
- [x] Add the minimum Deep Analysis control and structured factual/interpretive sections to Analyst’s Ledger without a final UI redesign.
- [x] Add no-network and route regressions for factual-data preservation, partial failures, source provenance, valuation, competitor-data absence, malformed AI, and Phase 4 backward compatibility.
- [x] Run real deterministic AAPL/NVDA/MSFT validation plus full Phase 2–5 test/build/security/Vercel checks, senior-review findings, documentation, and Phase 6 recommendations.

## QuantAI Phase 6: Company Comparison

- [x] Audit Phase 2–5 contracts/services and define typed dual-company request, identifiers, provenance, availability, currency/period alignment, deterministic scores, winners, and evidence-bound interpretation schemas.
- [x] Build deterministic dual-company acquisition and comparison services reusing existing entity, market, history, company, financial, news, event, cache, and freshness adapters without duplicate browser or market calls.
- [x] Implement safe metric normalization, period alignment, missing/currency handling, deterministic financial-strength and momentum scoring, category winners, and explicit insufficient-data states.
- [x] Orchestrate one bounded `company_comparison` report with concurrent independent services, compact validated AI context, partial-failure resilience, and no factual AI authority.
- [x] Add minimal Company A/Company B controls and structured comparison sections to Analyst’s Ledger without a final UI redesign.
- [x] Add no-network/route tests, real AAPL/MSFT/NVDA comparison validation, full Phase 2–6 regression/build/security/Vercel checks, senior review, documentation, and next-priority report.

## QuantAI Phase 7: Premium Frontend Transformation

- [x] Audit the current frontend, Phase 7 directives, existing theme system, responsive behavior, data contracts, and reusable components without modifying backend/provider architecture.
- [x] Define and document a single premium financial-research design direction; implement a coherent global light, dark, and system theme foundation with persistent preference and accessible contrast.
- [x] Add refined top navigation, workflow switching, mobile navigation, typography, number treatment, and a short reduced-motion-safe startup experience without fake destinations or generic SaaS patterns.
- [x] Recompose the research dashboard and all three flagship workflow views into polished, data-first editorial research experiences while preserving existing BFF calls and unavailable-data honesty.
- [x] Improve search, loading, error, ambiguity, responsive tables/charts, accessibility, provenance, and source states without creating unsupported backend functionality.
- [x] Run frontend, backend regression, visual, mobile, accessibility, build, Vercel, security, and independent review checks; document the final transformation, limitations, and next priorities.

## QuantAI Phase 8A: Final Pre-deployment Audit

- [x] Establish the repository, branch, remote, origin/main baseline, and exact local Phase 1–7 delta without staging, committing, pushing, or deploying.
- [x] Perform an aggressive non-disclosing credential, ignored-file, provider-architecture, Gemini-removal, and frontend endpoint safety audit.
- [x] Verify backend route/workflow contracts, deterministic evidence boundary, safe errors, provider fallback, caching, limits, provenance, freshness, and frontend-to-BFF compatibility.
- [x] Validate Vercel packaging and run Python compilation, all existing regressions, TypeScript, production build, configuration checks, and deterministic local HTTP smoke checks with provider keys blanked.
- [x] Review documentation, build performance, final diff hygiene, generated/debug/local artifacts, and make only clearly safe material fixes if required.
- [x] Conduct independent senior review and deliver a no-push final pre-deployment report with an explicit SAFE TO PUSH or NOT SAFE TO PUSH recommendation.

## QuantAI Phase 8B: Verify and Prepare the Correct GitHub Remote

- [ ] Capture the current local main head, remote configuration, unstaged/staged/untracked state, and preserve the complete Phase 1–7 release set without mutation.
- [ ] Verify connected GitHub access to `SamSurve/QuantAI`, retrieve its `main` metadata/history, and compare it to local `main` without overwriting either side.
- [ ] Determine common ancestry, commits unique to local and GitHub, GitHub-only divergence, modified files, and untracked files; stop before any merge/reset if GitHub has unreconciled changes.
- [ ] Change or prepare the origin remote only if the comparison is safe, then verify that no file deletion, staging, commit, push, deployment, or environment mutation occurred.
- [ ] Deliver the required Phase 8B no-push remote-target decision as either SAFE TO PREPARE PUSH or NOT SAFE — REQUIRES REVIEW.

## QuantAI Phase 8C: Prepare New SamSurve/Quant-AI Repository

- [x] Capture the complete preserved local Phase 1–7 release baseline and confirm no files, staging, commit, push, deployment, or environment settings have been mutated.
- [x] Verify connected GitHub access to the empty `SamSurve/Quant-AI` repository and confirm its `main` target without altering the existing remote.
- [x] Re-run non-disclosing credential, provider-removal, ignored-file, generated-artifact, and build/test validation for the complete release set.
- [x] Prepare the local `origin` remote and definitive commit inventory only for the verified empty target; do not stage, commit, push, force-push, merge unrelated histories, or discard Phase 1–7 work.
- [x] Deliver the Phase 8C no-push readiness report with the connected repository, branch, intended commit files, security/build evidence, and SAFE TO PUSH or NOT SAFE recommendation.

## QuantAI Phase 8D: Authorized First Production Repository Push

- [ ] Reconfirm `origin` is `SamSurve/Quant-AI`, local branch is `main`, the remote target is empty, and the authorized release inventory is complete before mutation.
- [ ] Run a final non-disclosing credential, secret-file, provider-removal, generated-artifact, and diff-hygiene scan before staging.
- [ ] Stage only the verified Phase 1–7 release files and confirm no `.env`, provider key, build output, cache, log, or temporary path is staged.
- [ ] Create the authorized `Quant-AI Phase 1-7 production release` commit and push it normally to `origin/main` without force-push, amendment, deployment, or unrelated history changes.
- [ ] Verify the remote `main` commit and branch, record the exact commit hash, and confirm no Vercel deployment was performed.
