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
- [ ] Remove temporary credential material and stop the test backend before reporting results.
