import { marketBriefFromResearch } from "../client/src/lib/market";
import type { TypedResearchResponse } from "../client/src/lib/research";

const response = {
  request_id: "workspace-mapping-regression",
  query: "AAPL",
  company: { symbol: "AAPL", name: "Apple Inc.", currency: "USD", identifier_confidence: "high" },
  candidates: [],
  market: { market_cap: 2345000000, currency: "USD" },
  history: [],
  news: [],
  analysis: null,
  events: [],
  sources: [],
  market_intelligence: {
    market_pulse: { current_price: 100, market_cap: null, currency: "USD" },
    price_history: {
      intraday: [{ timestamp: "2026-08-26T10:00:00Z", close: 99 }, { timestamp: "2026-08-26T10:30:00Z", close: 100 }],
      daily: [{ timestamp: "2026-08-20T00:00:00Z", close: 95 }, { timestamp: "2026-08-26T00:00:00Z", close: 100 }],
      available_periods: ["1D", "1W", "1M", "1Y", "5Y"],
      default_period: "1M",
      freshness: { state: "live", cache_scope: "none" },
    },
    market_signal: null,
    recent_news: [],
    event_radar: [],
    executive_brief: null,
    freshness: { company: { state: "live", cache_scope: "none" }, market: { state: "live", cache_scope: "none" }, history: { state: "live", cache_scope: "none" }, news: { state: "unavailable", cache_scope: "none" }, events: { state: "unavailable", cache_scope: "none" }, analysis: { state: "not_requested", cache_scope: "none" } },
  },
  company_deep_analysis: {
    company_overview: { ticker: "AAPL", market_cap: 1234000000, currency: "USD", business_description: "Returned profile text only." },
    financial_health: { revenue: 123, net_income: null, eps: 2.5, profit_margin: 0.2, operating_margin: 0.25, total_cash: 75, total_debt: 45, currency: "USD", fiscal_period_end: "2026-06-30" },
    governance: null,
    competitive_evidence: { status: "unavailable", competitors: [], note: "Insufficient verified competitor data." },
    market_context: null,
    recent_news: [],
    events: [],
    analyst_interpretation: null,
    freshness: { company: { state: "live", cache_scope: "none" }, financials: { state: "live", cache_scope: "none" }, governance: { state: "unavailable", cache_scope: "none" }, competitors: { state: "unavailable", cache_scope: "none" }, market: { state: "live", cache_scope: "none" }, news: { state: "unavailable", cache_scope: "none" }, events: { state: "unavailable", cache_scope: "none" }, analysis: { state: "not_requested", cache_scope: "none" } },
  },
  status: { overall: "partial", market: "available", financials: "available", governance: "unavailable", competitors: "unavailable", history: "available", news: "unavailable", events: "unavailable", company: "available", ai: "not_requested" },
  warnings: [],
} as TypedResearchResponse;

const brief = marketBriefFromResearch(response);
if (brief.priceHistory.availablePeriods.join(",") !== "1D,1W,1M,1Y,5Y") throw new Error("Workspace added or removed returned history periods.");
if (brief.priceHistory.daily.length !== 2 || brief.priceHistory.intraday.length !== 2) throw new Error("Workspace did not preserve returned history points.");
if (brief.priceHistory.defaultPeriod !== "1M") throw new Error("Workspace changed the returned default history period.");
if (brief.deepAnalysis?.profile.description !== "Returned profile text only.") throw new Error("Workspace changed returned company profile text.");
if (!brief.deepAnalysis?.financials.some((metric) => metric.label === "Revenue" && metric.value !== "—")) throw new Error("Workspace omitted returned revenue.");
if (!brief.deepAnalysis?.financials.some((metric) => metric.label === "Net income" && metric.value === "—")) throw new Error("Workspace did not retain missing financial data as unavailable.");
if (brief.metrics.find((metric) => metric.label === "Market cap")?.value === "—") throw new Error("Workspace did not use an existing returned market-cap fallback.");
if (!brief.deepAnalysis?.financials.some((metric) => metric.label === "Operating margin" && metric.value !== "—")) throw new Error("Workspace omitted a returned compact Financial Health metric.");
console.log("COMPANY_WORKSPACE_MAPPING_REGRESSION=PASS");
