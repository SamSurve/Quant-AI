/**
 * QuantAI BFF contract: deterministic research data is returned as typed JSON.
 * The browser never receives model-provider credentials or provider selection.
 */

import { getAgentosUrl } from "@/lib/agentos";

export type ResearchErrorCategory =
  | "VALIDATION_ERROR"
  | "ENTITY_NOT_FOUND"
  | "AMBIGUOUS_ENTITY"
  | "DATA_UNAVAILABLE"
  | "COMPANY_UNAVAILABLE"
  | "FINANCIALS_UNAVAILABLE"
  | "GOVERNANCE_UNAVAILABLE"
  | "COMPARISON_UNAVAILABLE"
  | "CURRENCY_COMPARISON_UNAVAILABLE"
  | "HISTORY_UNAVAILABLE"
  | "EVENTS_UNAVAILABLE"
  | "NEWS_UNAVAILABLE"
  | "AI_UNAVAILABLE"
  | "RATE_LIMITED"
  | "TIMEOUT"
  | "INTERNAL_ERROR";

export type TypedResearchResponse = {
  request_id: string;
  query: string;
  company: {
    symbol: string;
    name?: string | null;
    exchange?: string | null;
    sector?: string | null;
    industry?: string | null;
    currency?: string | null;
    identifier_confidence: "high" | "medium" | "low" | "ambiguous";
  } | null;
  candidates: Array<{ symbol: string; name?: string | null; exchange?: string | null }>;
  market: {
    current_price?: number | null;
    daily_change?: number | null;
    daily_change_percent?: number | null;
    volume?: number | null;
    market_cap?: number | null;
    pe_ratio?: number | null;
    eps?: number | null;
    fifty_two_week_high?: number | null;
    fifty_two_week_low?: number | null;
    dividend_yield?: number | null;
    price_to_sales?: number | null;
    currency?: string | null;
    market_status?: string | null;
    as_of?: string | null;
  } | null;
  history: Array<{ timestamp: string; open?: number | null; high?: number | null; low?: number | null; close?: number | null; volume?: number | null }>;
  news: Array<{ title: string; summary?: string | null; publisher?: string | null; url?: string | null; published_at?: string | null; relevance: string; sentiment?: string | null }>;
  analysis: {
    executive_summary?: string | null;
    what_is_happening?: string | null;
    bullish_factors: string[];
    bearish_factors: string[];
    risks: string[];
    catalysts: string[];
    what_to_watch?: string[];
    market_sentiment?: "positive" | "neutral" | "negative" | "mixed" | "insufficient" | null;
    confidence?: "low" | "medium" | "high" | null;
    ai_verdict?: string | null;
  } | null;
  events: Array<{ event_type: string; title: string; date?: string | null; importance: string; source?: string | null }>;
  sources: Array<{ source: string; url?: string | null; retrieved_at: string; data_type: string }>;
  market_intelligence?: {
    market_pulse: TypedResearchResponse["market"];
    price_history: {
      intraday: TypedResearchResponse["history"];
      daily: TypedResearchResponse["history"];
      available_periods: Array<"1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "5Y">;
      default_period: "1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "5Y";
      freshness: { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" };
    } | null;
    market_signal: { signal: "BULLISH" | "NEUTRAL" | "BEARISH" | null; score?: number | null; confidence?: number | null; factors: string[]; explanation?: string | null; methodology: string } | null;
    recent_news: TypedResearchResponse["news"];
    event_radar: TypedResearchResponse["events"];
    executive_brief: TypedResearchResponse["analysis"];
    freshness: Record<"company" | "market" | "history" | "news" | "events" | "analysis", { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" }>;
  } | null;
  company_deep_analysis?: {
    company_overview: { company_name?: string | null; ticker: string; exchange?: string | null; sector?: string | null; industry?: string | null; country?: string | null; headquarters?: string | null; website?: string | null; business_description?: string | null; employees?: number | null; market_cap?: number | null; currency?: string | null } | null;
    financial_health: { revenue?: number | null; net_income?: number | null; eps?: number | null; profit_margin?: number | null; operating_margin?: number | null; free_cash_flow?: number | null; total_cash?: number | null; total_debt?: number | null; pe_ratio?: number | null; price_to_sales?: number | null; dividend_yield?: number | null; return_on_equity?: number | null; return_on_assets?: number | null; currency?: string | null; fiscal_period_end?: string | null } | null;
    governance: { ceo?: { name: string; title?: string | null; since?: number | null } | null; key_leadership: Array<{ name: string; title?: string | null; since?: number | null }>; notable_developments: string[] } | null;
    competitive_evidence: { status: "available" | "unavailable"; competitors: string[]; note: string };
    market_context: TypedResearchResponse["market"];
    recent_news: TypedResearchResponse["news"];
    events: TypedResearchResponse["events"];
    analyst_interpretation: { executive_summary?: string | null; business_model?: string | null; financial_health?: string | null; growth_drivers: string[]; competitive_position?: string | null; key_risks: string[]; catalysts: string[]; valuation_view: { classification: "UNDERVALUED" | "FAIRLY_VALUED" | "HIGHLY_VALUED" | "INSUFFICIENT_DATA"; rationale?: string | null; evidence: string[] }; recent_developments: string[]; what_to_watch: string[]; overall_assessment?: string | null; confidence?: "low" | "medium" | "high" | null } | null;
    freshness: Record<"company" | "financials" | "governance" | "competitors" | "market" | "news" | "events" | "analysis", { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" }>;
  } | null;
  company_comparison?: {
    company_a: { identifier: "A"; company_name?: string | null; ticker: string; exchange?: string | null; sector?: string | null; industry?: string | null; country?: string | null; currency?: string | null; market_cap?: number | null };
    company_b: { identifier: "B"; company_name?: string | null; ticker: string; exchange?: string | null; sector?: string | null; industry?: string | null; country?: string | null; currency?: string | null; market_cap?: number | null };
    company_a_status: { identifier: "A"; overall: "available" | "partial" | "unavailable"; company: string; financials: string; history: string; news: string; events: string; message: string };
    company_b_status: { identifier: "B"; overall: "available" | "partial" | "unavailable"; company: string; financials: string; history: string; news: string; events: string; message: string };
    market_a: TypedResearchResponse["market"];
    market_b: TypedResearchResponse["market"];
    financial_a: { revenue?: number | null; net_income?: number | null; eps?: number | null; profit_margin?: number | null; operating_margin?: number | null; free_cash_flow?: number | null; total_cash?: number | null; total_debt?: number | null; pe_ratio?: number | null; price_to_sales?: number | null; dividend_yield?: number | null; return_on_equity?: number | null; return_on_assets?: number | null; currency?: string | null; fiscal_period_end?: string | null } | null;
    financial_b: { revenue?: number | null; net_income?: number | null; eps?: number | null; profit_margin?: number | null; operating_margin?: number | null; free_cash_flow?: number | null; total_cash?: number | null; total_debt?: number | null; pe_ratio?: number | null; price_to_sales?: number | null; dividend_yield?: number | null; return_on_equity?: number | null; return_on_assets?: number | null; currency?: string | null; fiscal_period_end?: string | null } | null;
    momentum_a: { signal: "BULLISH" | "NEUTRAL" | "BEARISH" | null; score?: number | null; confidence?: number | null; factors: string[]; explanation?: string | null; methodology: string } | null;
    momentum_b: { signal: "BULLISH" | "NEUTRAL" | "BEARISH" | null; score?: number | null; confidence?: number | null; factors: string[]; explanation?: string | null; methodology: string } | null;
    company_a_news: TypedResearchResponse["news"];
    company_b_news: TypedResearchResponse["news"];
    company_a_events: TypedResearchResponse["events"];
    company_b_events: TypedResearchResponse["events"];
    fx_conversions: Array<{ base_currency: string; quote_currency: string; rate: number; source: string; source_symbol: string; url?: string | null; retrieved_at: string }>;
    metrics: Array<{
      metric: string;
      company_a_value?: number | null;
      company_b_value?: number | null;
      unit: "currency" | "percentage" | "ratio" | "per_share" | "count" | "score";
      winner: "A" | "B" | "TIE" | "INSUFFICIENT_DATA";
      difference?: number | null;
      difference_basis?: string | null;
      currency?: string | null;
      currency_a?: string | null;
      currency_b?: string | null;
      company_a_comparison_value?: number | null;
      company_b_comparison_value?: number | null;
      currency_comparable: boolean;
      period_a?: string | null;
      period_b?: string | null;
      period_alignment: "ALIGNED" | "PARTIALLY_ALIGNED" | "NOT_ALIGNED" | "NOT_AVAILABLE";
      availability: "available" | "partial" | "unavailable";
      note?: string | null;
      provenance_a?: { source: string; url?: string | null; retrieved_at?: string | null; data_type: string; as_of?: string | null } | null;
      provenance_b?: { source: string; url?: string | null; retrieved_at?: string | null; data_type: string; as_of?: string | null } | null;
      fx_conversion?: { base_currency: string; quote_currency: string; rate: number; source: string; source_symbol: string; url?: string | null; retrieved_at: string } | null;
    }>;
    financial_strength: { company_a_score?: number | null; company_b_score?: number | null; winner: "A" | "B" | "TIE" | "INSUFFICIENT_DATA"; factors_a: string[]; factors_b: string[]; methodology: string };
    momentum: { company_a_score?: number | null; company_b_score?: number | null; winner: "A" | "B" | "TIE" | "INSUFFICIENT_DATA"; factors_a: string[]; factors_b: string[]; methodology: string };
    category_winners: Array<{ category: string; winner: "A" | "B" | "TIE" | "INSUFFICIENT_DATA"; supporting_metrics: string[]; explanation: string }>;
    overall_advantage: "A" | "B" | "TIE" | "INSUFFICIENT_DATA";
    overall_explanation: string;
    comparison_confidence: { score?: number | null; level: "low" | "medium" | "high" | "insufficient"; reasons: string[] };
    competitive_data_note: string;
    analyst_interpretation: { executive_summary?: string | null; key_difference?: string | null; company_a_strengths: string[]; company_b_strengths: string[]; company_a_weaknesses: string[]; company_b_weaknesses: string[]; growth_comparison?: string | null; financial_comparison?: string | null; valuation_comparison?: string | null; risk_comparison?: string | null; market_comparison?: string | null; important_catalysts: string[]; important_risks: string[]; what_to_watch: string[]; overall_assessment?: string | null; confidence?: "low" | "medium" | "high" | null } | null;
    freshness: {
      company_a: Record<"company" | "financials" | "governance" | "competitors" | "market" | "news" | "events" | "analysis", { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" }>;
      company_b: Record<"company" | "financials" | "governance" | "competitors" | "market" | "news" | "events" | "analysis", { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" }>;
      comparison: { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" };
      analysis: { state: "live" | "cached" | "recent" | "unavailable"; retrieved_at?: string | null; as_of?: string | null; cache_scope: "none" | "process_local" };
    };
  } | null;
  status: { overall: "complete" | "partial" | "unavailable"; market: string; financials?: string; governance?: string; competitors?: string; history?: string; news: string; events?: string; company: string; ai: string };
  warnings: Array<{ category: ResearchErrorCategory; message: string; retryable: boolean }>;
};

type TypedResearchError = { request_id?: string; category?: ResearchErrorCategory; message?: string; retryable?: boolean };

export type ResearchErrorKind = "ambiguous" | "not_found" | "ai_unavailable" | "news_unavailable" | "other";

/** Classify only safe public error-envelope copy for UI recovery messaging. */
export function researchErrorKind(message: string): ResearchErrorKind {
  const normalized = message.toLowerCase();
  if (/ambiguous|multiple companies match/.test(normalized)) return "ambiguous";
  if (/not found|unknown|invalid|no supported listed company/.test(normalized)) return "not_found";
  if (/ai analysis is temporarily unavailable|groq service is busy|provider unavailable/.test(normalized)) return "ai_unavailable";
  if (/news/.test(normalized)) return "news_unavailable";
  return "other";
}

async function readJson(response: Response) {
  const body = await response.text();
  try {
    return body ? JSON.parse(body) : {};
  } catch {
    return { message: `Research request failed with ${response.status}.` };
  }
}

export async function runTypedResearch(query: string, includeAnalysis = true, apiUrl = getAgentosUrl(), mode: "standard" | "market_intelligence" | "company_deep_analysis" = "standard", signal?: AbortSignal): Promise<TypedResearchResponse> {
  const response = await fetch(`${apiUrl}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query, include_analysis: includeAnalysis, mode }),
    signal,
  });
  const body = (await readJson(response)) as TypedResearchResponse | TypedResearchError;
  if (!response.ok) {
    const error = body as TypedResearchError;
    throw new Error(error.message || "Research is temporarily unavailable. Please try again shortly.");
  }
  return body as TypedResearchResponse;
}
