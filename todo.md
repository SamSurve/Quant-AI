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
- [ ] Implement Gemini-primary and Groq-fallback providers with explicit provider modes and bounded one-way failover.
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
