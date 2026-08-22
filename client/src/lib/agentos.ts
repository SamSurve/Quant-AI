/**
 * Analyst's Ledger style contract: backend access stays explicit, reliable, and source-aware.
 * This module connects only to the existing AgentOS API; it does not change agent behavior.
 */

export const AGENT_ID = "xai-finance-agent";
const STORAGE_KEY = "analysts-ledger-agentos-url";
const DEFAULT_API_URL = import.meta.env.VITE_AGENTOS_API_URL || "http://localhost:7777";

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
  return normalizeApiUrl(localStorage.getItem(STORAGE_KEY) || DEFAULT_API_URL);
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

export async function fetchAgentInfo(apiUrl = getAgentosUrl()): Promise<AgentInfo> {
  const response = await fetch(`${apiUrl}/agents`, { headers: { Accept: "application/json" } });
  const body = await readResponse(response);
  if (!response.ok) throw new Error(body.detail || "AgentOS is not reachable.");

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
  if (!response.ok) throw new Error(body.detail || `AgentOS request failed (${response.status}).`);
  if (body.status === "ERROR") throw new Error(body.content || "The finance agent returned an error.");
  if (!body.content) throw new Error("The finance agent returned no analysis.");
  return body;
}
