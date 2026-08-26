/**
 * Analyst's Ledger style contract: render typed BFF research data directly.
 * Markdown parsing remains only for legacy conversational AgentOS responses.
 */

import type { TypedResearchResponse } from "@/lib/research";

/** Evidence Briefing contract: only source-returned records reach visual components. */
export type Metric = { label: string; value: string; tone?: "neutral" | "positive" | "negative" };
export type ChartPoint = { label: string; value: number };
export type HistoryPeriod = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "5Y";
export type BriefNewsItem = { title: string; summary: string | null; publisher: string | null; publishedAt: string | null; url: string | null; sentiment: string | null };
export type MarketBrief = {
  companyName: string;
  ticker: string;
  exchange: string;
  sector: string;
  industry: string;
  quoteLabel: "Current price" | "Latest close";
  quote: string;
  change: string;
  metrics: Metric[];
  news: BriefNewsItem[];
  chart: ChartPoint[];
  priceHistory: { intraday: ChartPoint[]; daily: ChartPoint[]; availablePeriods: HistoryPeriod[]; defaultPeriod: HistoryPeriod };
  analysis: string;
  aiInterpretationNotice: string | null;
  signal: { label: string; score: string; confidence: string; factors: string[]; explanation: string; methodology: string } | null;
  events: Array<{ title: string; date: string; importance: string; source: string }>;
  sources: Array<{ source: string; url: string | null; dataType: string; retrievedAt: string }>;
  warnings: Array<{ category: string; message: string }>;
  freshness: Array<{ label: string; state: string; asOf: string }>;
  deepAnalysis: {
    profile: { description: string | null; country: string | null; headquarters: string | null; website: string | null; employees: string | null; fiscalPeriodEnd: string | null };
    overview: Array<{ label: string; value: string }>;
    financials: Metric[];
    governance: { ceo: string; leadership: string[]; note: string };
    competitors: { note: string; items: string[] };
    interpretation: {
      businessModel: string;
      financialHealth: string;
      growthDrivers: string[];
      competitivePosition: string;
      risks: string[];
      catalysts: string[];
      valuation: { classification: string; rationale: string; evidence: string[] };
      recentDevelopments: string[];
      whatToWatch: string[];
      assessment: string;
      confidence: string;
    } | null;
  } | null;
};

type MarkdownTable = { headers: string[]; rows: string[][] };

const metricKeys = [
  { label: "Market cap", matches: ["market cap", "market capitalization"] },
  { label: "P / E ratio", matches: ["p/e", "p/e ratio", "pe ratio", "price to earnings"] },
  { label: "52-week high", matches: ["52 week high", "52-week high"] },
  { label: "52-week low", matches: ["52 week low", "52-week low"] },
  { label: "Volume", matches: ["volume", "avg volume", "average volume"] },
  { label: "Dividend yield", matches: ["dividend yield"] },
];

function cleanCell(value: string) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .trim();
}

function parseTables(markdown: string): MarkdownTable[] {
  const lines = markdown.split("\n");
  const tables: MarkdownTable[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    const separator = lines[index + 1]?.trim() || "";
    if (!line.startsWith("|") || !separator.startsWith("|") || !/[-:]{3,}/.test(separator)) {
      index += 1;
      continue;
    }

    const headers = line
      .split("|")
      .slice(1, -1)
      .map((cell) => cleanCell(cell).toLowerCase());
    const rows: string[][] = [];
    index += 2;
    while (index < lines.length && lines[index].trim().startsWith("|")) {
      rows.push(lines[index].trim().split("|").slice(1, -1).map(cleanCell));
      index += 1;
    }
    tables.push({ headers, rows });
  }
  return tables;
}

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function findTableValue(tables: MarkdownTable[], terms: string[]) {
  for (const table of tables) {
    const labelIndex = table.headers.findIndex((header) => /metric|measure|item|indicator|field/.test(header));
    const valueIndex = table.headers.findIndex((header) => /value|amount|data|latest|current/.test(header));
    for (const row of table.rows) {
      const label = normalize(row[labelIndex >= 0 ? labelIndex : 0] || "");
      if (terms.some((term) => label.includes(normalize(term)))) {
        const index = valueIndex >= 0 ? valueIndex : row.length > 1 ? 1 : 0;
        return row[index] || "—";
      }
    }
  }

  const flat = tables.flatMap((table) => table.rows);
  for (const row of flat) {
    const joined = normalize(row.join(" "));
    if (terms.some((term) => joined.includes(normalize(term)))) {
      return row.find((cell) => /[$€£₹¥]|\d/.test(cell)) || "—";
    }
  }
  return "—";
}

function extractFallbackValue(markdown: string, terms: string[]) {
  const lines = markdown.split("\n");
  for (const line of lines) {
    const normalizedLine = normalize(line);
    if (terms.some((term) => normalizedLine.includes(normalize(term)))) {
      const match = line.match(/([$€£₹¥]\s?[\d,.]+(?:[BMKT])?|[\d,.]+%?|[\d,.]+\s?[BMKT])/i);
      if (match) return match[0];
    }
  }
  return "—";
}

function findValue(tables: MarkdownTable[], markdown: string, terms: string[]) {
  const fromTable = findTableValue(tables, terms);
  return fromTable !== "—" ? fromTable : extractFallbackValue(markdown, terms);
}

function displayValue(value: string) {
  return value === "—" || /^unavailable$/i.test(value) ? "—" : value;
}

function numberFromCell(value: string) {
  const cleaned = value.replace(/[$€£₹¥,\s]/g, "").replace(/\((.*)\)/, "-$1");
  const match = cleaned.match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : NaN;
}

function extractChart(tables: MarkdownTable[]) {
  for (const table of tables) {
    const dateIndex = table.headers.findIndex((header) => /date|day|period|time/.test(header));
    const priceIndex = table.headers.findIndex((header) => /close|price|value|last/.test(header));
    if (dateIndex < 0 || priceIndex < 0) continue;
    const points = table.rows
      .map((row) => ({ label: row[dateIndex] || "", value: numberFromCell(row[priceIndex] || "") }))
      .filter((point) => point.label && Number.isFinite(point.value))
      .slice(-40);
    if (points.length >= 2) return points;
  }
  return [];
}

function extractNews(markdown: string) {
  const lines = markdown.split("\n");
  const sectionStart = lines.findIndex((line) => /recent news|news (?:highlights|summary)|latest news/i.test(line));
  const candidates = (sectionStart >= 0 ? lines.slice(sectionStart + 1, sectionStart + 12) : lines)
    .filter((line) => /^\s*(?:[-*•]|\d+\.)\s+/.test(line))
    .map((line) => line.replace(/^\s*(?:[-*•]|\d+\.)\s+/, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").trim())
    .filter((line) => line.length > 12)
    .slice(0, 3);
  return candidates;
}

function toneFor(value: string): Metric["tone"] {
  if (/^\+|up|gain|positive/i.test(value)) return "positive";
  if (/^-|down|loss|negative/i.test(value)) return "negative";
  return "neutral";
}

export function parseMarketBrief(markdown: string): MarketBrief {
  const tables = parseTables(markdown);
  const quote = displayValue(findValue(tables, markdown, ["current price", "stock price", "last price", "price"]));
  const change = displayValue(findValue(tables, markdown, ["day change", "change", "daily change", "percent change"]));
  const metrics = metricKeys.map((metric) => {
    const value = displayValue(findValue(tables, markdown, metric.matches));
    return { label: metric.label, value, tone: toneFor(value) };
  });

  return {
    companyName: displayValue(findValue(tables, markdown, ["company name", "company"])),
    ticker: displayValue(findValue(tables, markdown, ["ticker", "symbol"])),
    exchange: displayValue(findValue(tables, markdown, ["exchange"])),
    sector: displayValue(findValue(tables, markdown, ["sector"])),
    industry: displayValue(findValue(tables, markdown, ["industry"])),
    quoteLabel: "Current price",
    quote,
    change,
    metrics,
    news: extractNews(markdown).map((title) => ({ title, summary: null, publisher: null, publishedAt: null, url: null, sentiment: null })),
    chart: extractChart(tables),
    priceHistory: { intraday: [], daily: extractChart(tables), availablePeriods: [], defaultPeriod: "1M" },
    analysis: markdown,
    aiInterpretationNotice: null,
    signal: null,
    events: [],
    sources: [],
    warnings: [],
    freshness: [],
    deepAnalysis: null,
  };
}

export const emptyMarketBrief: MarketBrief = {
  companyName: "—",
  ticker: "—",
  exchange: "—",
  sector: "—",
  industry: "—",
  quoteLabel: "Current price",
  quote: "—",
  change: "Awaiting AgentOS research",
  metrics: metricKeys.map((metric) => ({ label: metric.label, value: "—", tone: "neutral" })),
  news: [],
  chart: [],
  priceHistory: { intraday: [], daily: [], availablePeriods: [], defaultPeriod: "1M" },
  analysis: "",
  aiInterpretationNotice: null,
  signal: null,
  events: [],
  sources: [],
  warnings: [],
  freshness: [],
  deepAnalysis: null,
};

function numberLabel(value: number | null | undefined, options: Intl.NumberFormatOptions = {}) {
  return value === null || value === undefined || !Number.isFinite(value)
    ? "—"
    : new Intl.NumberFormat(undefined, options).format(value);
}

function moneyLabel(value: number | null | undefined, currency?: string | null) {
  return value === null || value === undefined || !Number.isFinite(value)
    ? "—"
    : new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "USD", maximumFractionDigits: 2 }).format(value);
}

function compactMoneyLabel(value: number | null | undefined, currency?: string | null) {
  return value === null || value === undefined || !Number.isFinite(value)
    ? "—"
    : new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "USD", notation: "compact", maximumFractionDigits: 2 }).format(value);
}

function historyPoints(points: Array<{ timestamp: string; close?: number | null }>) {
  return points
    .filter((point) => point.close !== null && point.close !== undefined)
    .map((point) => ({ label: point.timestamp, value: point.close as number }));
}

function typedAnalysisMarkdown(research: TypedResearchResponse) {
  const deep = research.company_deep_analysis?.analyst_interpretation;
  if (deep) {
    const section = (heading: string, values: string[]) => (values.length ? `\n\n## ${heading}\n${values.map((value) => `- ${value}`).join("\n")}` : "");
    return [
      deep.executive_summary ? `## Executive Assessment\n${deep.executive_summary}` : "",
      deep.business_model ? `\n\n## Business Model\n${deep.business_model}` : "",
      deep.financial_health ? `\n\n## Financial Health\n${deep.financial_health}` : "",
      section("Growth Drivers", deep.growth_drivers),
      deep.competitive_position ? `\n\n## Competitive Position\n${deep.competitive_position}` : "",
      section("Key Risks — Analyst Interpretation", deep.key_risks),
      section("Catalysts", deep.catalysts),
      deep.valuation_view ? `\n\n## Valuation View — Analyst Interpretation\n${deep.valuation_view.classification}${deep.valuation_view.rationale ? ` · ${deep.valuation_view.rationale}` : ""}` : "",
      section("Recent Developments", deep.recent_developments),
      section("What to Watch", deep.what_to_watch),
      deep.overall_assessment ? `\n\n## Overall Assessment\n${deep.overall_assessment}` : "",
    ].filter(Boolean).join("\n");
  }
  const analysis = research.market_intelligence?.executive_brief || research.analysis;
  if (!analysis) return "";
  const section = (heading: string, values: string[]) => (values.length ? `\n\n## ${heading}\n${values.map((value) => `- ${value}`).join("\n")}` : "");
  return [
    analysis.executive_summary ? `## Executive Summary\n${analysis.executive_summary}` : "",
    analysis.what_is_happening ? `\n\n## What is happening\n${analysis.what_is_happening}` : "",
    section("Bullish Factors", analysis.bullish_factors),
    section("Bearish Factors", analysis.bearish_factors),
    section("Risks", analysis.risks),
    section("Catalysts", analysis.catalysts),
    section("What to Watch", analysis.what_to_watch || []),
    analysis.market_sentiment ? `\n\n## Market Sentiment\n${analysis.market_sentiment}` : "",
    analysis.ai_verdict ? `\n\n## AI Verdict\n${analysis.ai_verdict}` : "",
  ].filter(Boolean).join("\n");
}

export function marketBriefFromResearch(research: TypedResearchResponse): MarketBrief {
  const intelligence = research.market_intelligence;
  const deep = research.company_deep_analysis;
  const market = intelligence?.market_pulse || deep?.market_context || research.market;
  const currency = research.company?.currency;
  const priceHistory = intelligence?.price_history;
  const dailyHistory = historyPoints(priceHistory?.daily || research.history);
  const intradayHistory = historyPoints(priceHistory?.intraday || []);
  const change = market?.daily_change_percent;
  const deterministicEvidenceAvailable = Boolean(
    market
    || research.news.length
    || research.events.length
    || deep?.company_overview
    || deep?.financial_health
    || intelligence?.price_history
  );
  const aiInterpretationNotice = research.status.ai === "unavailable"
    ? (deterministicEvidenceAvailable
      ? "Market data and evidence are available. AI interpretation is temporarily unavailable."
      : "AI interpretation is temporarily unavailable; no deterministic evidence was returned for this request.")
    : null;
  return {
    companyName: research.company?.name || "—",
    ticker: research.company?.symbol || "—",
    exchange: research.company?.exchange || "—",
    sector: research.company?.sector || "—",
    industry: research.company?.industry || "—",
    quoteLabel: market?.market_status === "HISTORY_CLOSE_FALLBACK" ? "Latest close" : "Current price",
    quote: moneyLabel(market?.current_price, currency),
    change: change === null || change === undefined ? "—" : `${change >= 0 ? "+" : ""}${numberLabel(change, { maximumFractionDigits: 2 })}%`,
    metrics: [
      { label: "Market cap", value: compactMoneyLabel(market?.market_cap, currency) },
      { label: "P / E ratio", value: numberLabel(market?.pe_ratio, { maximumFractionDigits: 2 }) },
      { label: "52-week high", value: moneyLabel(market?.fifty_two_week_high, currency) },
      { label: "52-week low", value: moneyLabel(market?.fifty_two_week_low, currency) },
      { label: "Volume", value: numberLabel(market?.volume, { notation: "compact", maximumFractionDigits: 2 }) },
      { label: "Dividend yield", value: market?.dividend_yield === null || market?.dividend_yield === undefined ? "—" : `${numberLabel(market.dividend_yield * 100, { maximumFractionDigits: 2 })}%` },
      { label: "EPS", value: moneyLabel(market?.eps, currency) },
    ].map((metric) => ({ ...metric, tone: "neutral" as const })),
    news: (intelligence?.recent_news || deep?.recent_news || research.news).map((item) => ({
      title: item.title,
      summary: item.summary?.trim() || null,
      publisher: item.publisher || null,
      publishedAt: item.published_at || null,
      url: item.url || null,
      sentiment: item.sentiment || null,
    })),
    chart: dailyHistory.slice(-60),
    priceHistory: {
      intraday: intradayHistory,
      daily: dailyHistory,
      availablePeriods: (priceHistory?.available_periods || []) as HistoryPeriod[],
      defaultPeriod: (priceHistory?.default_period || "1M") as HistoryPeriod,
    },
    analysis: typedAnalysisMarkdown(research),
    aiInterpretationNotice,
    signal: intelligence?.market_signal ? {
      label: intelligence.market_signal.signal || "UNAVAILABLE",
      score: intelligence.market_signal.score === null || intelligence.market_signal.score === undefined ? "—" : `${intelligence.market_signal.score}/100`,
      confidence: intelligence.market_signal.confidence === null || intelligence.market_signal.confidence === undefined ? "—" : `${intelligence.market_signal.confidence}/100`,
      factors: intelligence.market_signal.factors,
      explanation: intelligence.market_signal.explanation || "Deterministic signal data is unavailable.",
      methodology: intelligence.market_signal.methodology,
    } : null,
    events: (intelligence?.event_radar || deep?.events || research.events || []).map((event) => ({
      title: event.title,
      date: event.date ? event.date.slice(0, 10) : "Date unavailable",
      importance: event.importance,
      source: event.source || "Source unavailable",
    })),
    sources: research.sources.map((source) => ({ source: source.source, url: source.url || null, dataType: source.data_type, retrievedAt: source.retrieved_at })),
    warnings: research.warnings.map((warning) => ({ category: warning.category, message: warning.message })),
    freshness: intelligence ? Object.entries(intelligence.freshness).map(([label, value]) => ({ label, state: value.state, asOf: value.as_of || value.retrieved_at || "Unavailable" })) : deep ? Object.entries(deep.freshness).map(([label, value]) => ({ label, state: value.state, asOf: value.as_of || value.retrieved_at || "Unavailable" })) : [],
    deepAnalysis: deep ? {
      profile: {
        description: deep.company_overview?.business_description || null,
        country: deep.company_overview?.country || null,
        headquarters: deep.company_overview?.headquarters || null,
        website: deep.company_overview?.website || null,
        employees: deep.company_overview?.employees == null ? null : numberLabel(deep.company_overview.employees),
        fiscalPeriodEnd: deep.financial_health?.fiscal_period_end || null,
      },
      overview: [
        ["Company", deep.company_overview?.company_name], ["Ticker", deep.company_overview?.ticker], ["Exchange", deep.company_overview?.exchange], ["Sector", deep.company_overview?.sector], ["Industry", deep.company_overview?.industry], ["Country", deep.company_overview?.country], ["Headquarters", deep.company_overview?.headquarters], ["Employees", numberLabel(deep.company_overview?.employees)], ["Website", deep.company_overview?.website],
      ].filter((item): item is [string, string] => Boolean(item[1])).map(([label, value]) => ({ label, value })),
      financials: [
        { label: "Revenue", value: compactMoneyLabel(deep.financial_health?.revenue, deep.financial_health?.currency) },
        { label: "Net income", value: compactMoneyLabel(deep.financial_health?.net_income, deep.financial_health?.currency) },
        { label: "EPS", value: moneyLabel(deep.financial_health?.eps, deep.financial_health?.currency) },
        { label: "Profit margin", value: deep.financial_health?.profit_margin == null ? "—" : `${numberLabel(deep.financial_health.profit_margin * 100, { maximumFractionDigits: 2 })}%` },
        { label: "Free cash flow", value: compactMoneyLabel(deep.financial_health?.free_cash_flow, deep.financial_health?.currency) },
        { label: "Total cash", value: compactMoneyLabel(deep.financial_health?.total_cash, deep.financial_health?.currency) },
        { label: "Total debt", value: compactMoneyLabel(deep.financial_health?.total_debt, deep.financial_health?.currency) },
        { label: "Operating margin", value: deep.financial_health?.operating_margin == null ? "—" : `${numberLabel(deep.financial_health.operating_margin * 100, { maximumFractionDigits: 2 })}%` },
        { label: "P / Sales", value: numberLabel(deep.financial_health?.price_to_sales, { maximumFractionDigits: 2 }) },
        { label: "ROE", value: deep.financial_health?.return_on_equity == null ? "—" : `${numberLabel(deep.financial_health.return_on_equity * 100, { maximumFractionDigits: 2 })}%` },
        { label: "ROA", value: deep.financial_health?.return_on_assets == null ? "—" : `${numberLabel(deep.financial_health.return_on_assets * 100, { maximumFractionDigits: 2 })}%` },
      ],
      governance: {
        ceo: deep.governance?.ceo ? [deep.governance.ceo.name, deep.governance.ceo.title].filter(Boolean).join(" · ") : "Insufficient verified data.",
        leadership: (deep.governance?.key_leadership || []).map((person) => [person.name, person.title].filter(Boolean).join(" · ")),
        note: (deep.governance?.notable_developments || []).join(" ") || "No sourced management-change assertion is shown.",
      },
      competitors: { note: deep.competitive_evidence.note, items: deep.competitive_evidence.competitors },
      interpretation: deep.analyst_interpretation ? {
        businessModel: deep.analyst_interpretation.business_model || "Insufficient verified data.",
        financialHealth: deep.analyst_interpretation.financial_health || "Insufficient verified data.",
        growthDrivers: deep.analyst_interpretation.growth_drivers,
        competitivePosition: deep.analyst_interpretation.competitive_position || "Insufficient verified data.",
        risks: deep.analyst_interpretation.key_risks,
        catalysts: deep.analyst_interpretation.catalysts,
        valuation: { classification: deep.analyst_interpretation.valuation_view.classification, rationale: deep.analyst_interpretation.valuation_view.rationale || "Insufficient verified data.", evidence: deep.analyst_interpretation.valuation_view.evidence },
        recentDevelopments: deep.analyst_interpretation.recent_developments,
        whatToWatch: deep.analyst_interpretation.what_to_watch,
        assessment: deep.analyst_interpretation.overall_assessment || "Insufficient verified data.",
        confidence: deep.analyst_interpretation.confidence || "Unavailable",
      } : null,
    } : null,
  };
}
