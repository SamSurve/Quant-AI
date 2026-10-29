import assert from "node:assert/strict";
import { friendlyAgentError } from "../client/src/lib/agentos";

const providerMessage = "AI analysis is temporarily unavailable. Please wait a few minutes and try again; the dashboard is ready for your next request.";

assert.equal(friendlyAgentError("upstream provider stack trace", 500), "The Research Desk is temporarily unavailable. Please try again shortly.");
assert.equal(friendlyAgentError("unauthorized", 401), "The Research Desk is unavailable for this session. Please check the configured endpoint.");
assert.equal(friendlyAgentError("quota exceeded", 429), providerMessage);
assert.equal(friendlyAgentError("AI analysis is temporarily unavailable", 200), providerMessage);
assert.equal(friendlyAgentError("Multiple companies match this query.", 409), "Multiple companies match this query.");

console.log("AGENTOS_CLIENT_ERROR_REGRESSION=PASS");
