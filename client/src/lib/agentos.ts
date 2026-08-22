/**
 * Analyst's Ledger style contract: backend access stays explicit, reliable, and source-aware.
 * This module connects only to the existing AgentOS API; it does not change agent behavior.
 */

export const AGENT_ID = "groq-finance-agent";
const STORAGE_KEY = "analysts-ledger-agentos-url";
const DEFAULT_API_URL = import.meta.env.PROD ? "/api" : import.meta.env.VITE_AGENTOS_API_URL || "/api";

export type AgentRunResponse = {
  run_id?: string;
  session_id?: string;
  content?: string;
  status?: string;
  detail?: string;
};

export type AgentInfo = {
  id: string;
  name: string;
  model?: { model?: string; provider?: string };
};

export function normalizeApiUrl(value: string) {
  return value.trim().replace(/\/+$/, "");
}

export function getAgentosUrl() {
  if (import.meta.env.PROD) return "/api";
  const saved = localStorage.getItem(STORAGE_KEY);
  return normalizeApiUrl(saved === "/agentos" ? "/api" : saved || DEFAULT_API_URL);
}

export function saveAgentosUrl(value: string) {
  const normalized = normalizeApiUrl(value);
  localStorage.setItem(STORAGE_KEY, normalized);
  return normalized;
}

async function readResponse(response: Response) {
  const body = await response.text();
  try {
    return body ? JSON.parse(body) : {};
  } catch {
    return { detail: body || `Request failed with ${response.status}.` };
  }
}

function friendlyAgentError(value: unknown, status?: number) {
  const message = String(value || "");
  const normalized = message.toLowerCase();
  if (
    status === 429 ||
    status === 503 ||
    /temporarily unavailable|rate.?limit|quota|too many requests|service unavailable|overloaded/.test(normalized)
  ) {
    return "AI analysis is temporarily unavailable. Please wait a few minutes and try again; the dashboard is ready for your next request.";
  }
  return message || `AgentOS request failed${status ? ` (${status})` : ""}.`;
}

export async function fetchAgentInfo(apiUrl = getAgentosUrl()): Promise<AgentInfo> {
  const response = await fetch(`${apiUrl}/agents`, { headers: { Accept: "application/json" } });
  const body = await readResponse(response);
  if (!response.ok) throw new Error(friendlyAgentError(body.detail, response.status));

  const agent = Array.isArray(body) ? body.find((item) => item.id === AGENT_ID) : undefined;
  if (!agent) throw new Error(`The AgentOS instance does not expose ${AGENT_ID}.`);
  return agent as AgentInfo;
}

export async function runFinanceAgent({
  message,
  sessionId,
  apiUrl = getAgentosUrl(),
}: {
  message: string;
  sessionId?: string;
  apiUrl?: string;
}): Promise<AgentRunResponse> {
  const form = new FormData();
  form.append("message", message);
  form.append("stream", "false");
  if (sessionId) form.append("session_id", sessionId);

  const response = await fetch(`${apiUrl}/agents/${AGENT_ID}/runs`, {
    method: "POST",
    body: form,
    headers: { Accept: "application/json" },
  });
  const body = (await readResponse(response)) as AgentRunResponse;
  if (!response.ok) throw new Error(friendlyAgentError(body.detail, response.status));
  if (body.status === "ERROR") throw new Error(friendlyAgentError(body.content || body.detail));
  if (!body.content) throw new Error("The finance agent returned no analysis.");
  return body;
}
