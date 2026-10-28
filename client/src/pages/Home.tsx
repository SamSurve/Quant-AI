/**
 * QuantAI Finance Agent — Responsive Financial Research Desk.
 * Organised into three primary destinations:
 * 1. Market Intelligence
 * 2. Company Deep Analysis
 * 3. Company Comparison
 * Plus dedicated AI Research Workspace (no floating chatbot).
 *
 * Strictly preserves all existing backend contracts, error recovery,
 * and deterministic evidence separation.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { nanoid } from "nanoid";
import {
  AlertCircle,
  BarChart3,
  Calendar,
  ExternalLink,
  BookOpenText,
  Building2,
  ChevronDown,
  ChevronRight,
  FileSearch,
  Landmark,
  Layers,
  LoaderCircle,
  Network,
  Newspaper,
  RefreshCw,
  Scale,
  Search,
  Settings2,
  Sparkles,
  WifiOff,
  X,
} from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { ChatPanel, type ChatMessage } from "@/components/ChatPanel";
import { CompanyComparison } from "@/components/CompanyComparison";
import { MarketChart } from "@/components/MarketChart";
import { MetricCard } from "@/components/MetricCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { fetchAgentInfo, getAgentosUrl, runFinanceAgent, saveAgentosUrl } from "@/lib/agentos";
import { emptyMarketBrief, marketBriefFromResearch, type HistoryPeriod, type MarketBrief } from "@/lib/market";
import { researchErrorKind, runTypedResearch, type TypedResearchResponse } from "@/lib/research";

export type DestinationTab = "market_intelligence" | "company_deep_analysis" | "company_comparison" | "ai_research";

const starterTickers = ["AAPL", "MSFT", "NVDA", "TSLA"];
const historyPeriodLabels: Record<HistoryPeriod, string> = { "1D": "1D", "1W": "1W", "1M": "1M", "3M": "3M", "6M": "6M", "1Y": "1Y", "5Y": "5Y" };
type Connection = "checking" | "ready" | "offline";
type ResearchActivity = { id: string; type: string; query: string; status: string; confidence?: string };

function isTemporaryAiUnavailability(message: string) {
  return researchErrorKind(message) === "ai_unavailable";
}

function recoveryMessage(message: string) {
  const kind = researchErrorKind(message);
  if (kind === "ambiguous") return "More than one company matched. Try a ticker or a more specific company name.";
  if (kind === "not_found") return "No verified company record was found. Check the spelling or search by ticker.";
  if (kind === "ai_unavailable") return "The sourced research record remains useful, but optional AI interpretation is temporarily unavailable.";
  if (kind === "news_unavailable") return "The research record is available with a missing news source. Other sourced evidence remains visible.";
  return "The request could not complete. Check the research endpoint, then try again.";
}

function displayDate(value: string | null) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value.slice(0, 10) : parsed.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function availabilityCopy(connection: Connection, researchInFlight: boolean, brief: MarketBrief) {
  if (researchInFlight) return "Building a sourced research record…";
  if (connection === "offline") return "Research Desk is unavailable.";
  if (brief.aiInterpretationNotice) return "Sourced data available · AI interpretation unavailable";
  if (brief.ticker === "—") return "Ready for a company or ticker.";
  return "Sourced research record available.";
}

function periodSeries(brief: MarketBrief, period: HistoryPeriod) {
  if (period === "1D") return brief.priceHistory.intraday;
  const daily = brief.priceHistory.daily;
  if (!daily.length) return [];
  const latest = new Date(daily[daily.length - 1].label).getTime();
  const days: Record<Exclude<HistoryPeriod, "1D" | "5Y">, number> = { "1W": 7, "1M": 31, "3M": 92, "6M": 184, "1Y": 366 };
  if (period === "5Y") return daily;
  const cutoff = latest - days[period] * 24 * 60 * 60 * 1000;
  return daily.filter((point) => new Date(point.label).getTime() >= cutoff);
}

function performanceSummary(series: Array<{ value: number }>) {
  if (series.length < 2) return null;
  const first = series[0].value;
  const last = series[series.length - 1].value;
  if (!Number.isFinite(first) || !Number.isFinite(last) || first === 0) return null;
  return { change: ((last - first) / first) * 100, high: Math.max(...series.map((point) => point.value)), low: Math.min(...series.map((point) => point.value)) };
}

function workspaceResearchRecord(marketResearch: TypedResearchResponse, deepResearch: TypedResearchResponse | null): TypedResearchResponse {
  if (!deepResearch) return marketResearch;
  return {
    ...marketResearch,
    company: marketResearch.company || deepResearch.company,
    news: marketResearch.news.length ? marketResearch.news : deepResearch.news,
    events: marketResearch.events.length ? marketResearch.events : deepResearch.events,
    analysis: marketResearch.analysis || deepResearch.analysis,
    sources: [...marketResearch.sources, ...deepResearch.sources],
    warnings: [...marketResearch.warnings, ...deepResearch.warnings],
    company_deep_analysis: deepResearch.company_deep_analysis,
    status: {
      ...marketResearch.status,
      financials: deepResearch.status.financials,
      governance: deepResearch.status.governance,
      competitors: deepResearch.status.competitors,
    },
  };
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<DestinationTab>("market_intelligence");
  const [ticker, setTicker] = useState("AAPL");
  const [query, setQuery] = useState("AAPL");
  const [brief, setBrief] = useState<MarketBrief>(emptyMarketBrief);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [connection, setConnection] = useState<Connection>("checking");
  const [connectionNote, setConnectionNote] = useState("Checking Research Desk…");
  const [isResearching, setIsResearching] = useState(false);
  const [activeResearchMode, setActiveResearchMode] = useState<"market_intelligence" | "company_deep_analysis">("market_intelligence");
  const [activeHistoryPeriod, setActiveHistoryPeriod] = useState<HistoryPeriod>("1M");
  const [isChatting, setIsChatting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [endpointDraft, setEndpointDraft] = useState(getAgentosUrl());
  const [researchActivity, setResearchActivity] = useState<ResearchActivity[]>([]);
  const researchSequence = useRef(0);
  const activeResearchController = useRef<AbortController | null>(null);
  const activeResearchKey = useRef<string | null>(null);

  async function verifyConnection(apiUrl = getAgentosUrl()) {
    setConnection("checking");
    try {
      const agent = await fetchAgentInfo(apiUrl);
      setConnection("ready");
      setConnectionNote(`${agent.name} · ${agent.model?.model || "QuantAI"}`);
      setError(null);
    } catch (connectionError) {
      setConnection("offline");
      setConnectionNote(connectionError instanceof Error ? connectionError.message : "Research Desk is unavailable.");
    }
  }

  useEffect(() => { void verifyConnection(); }, []);
  useEffect(() => () => activeResearchController.current?.abort(), []);

  function recordResearch(type: string, queryLabel: string, status: string, confidence?: string) {
    setResearchActivity((current) => [{ id: nanoid(), type, query: queryLabel, status, confidence }, ...current].slice(0, 5));
  }

  async function requestResearch(symbol = query, mode: "market_intelligence" | "company_deep_analysis" = activeResearchMode) {
    const normalized = symbol.trim();
    const requestKey = `${mode}:${normalized.toLocaleUpperCase()}`;
    if (!normalized || (activeResearchController.current && activeResearchKey.current === requestKey)) return;
    activeResearchController.current?.abort();
    const controller = new AbortController();
    activeResearchController.current = controller;
    activeResearchKey.current = requestKey;
    const requestId = researchSequence.current + 1;
    researchSequence.current = requestId;
    setQuery(normalized);
    setActiveResearchMode(mode);
    setBrief(emptyMarketBrief);
    setIsResearching(true);
    setError(null);
    try {
      const [marketResult, deepResult] = await Promise.allSettled([
        runTypedResearch(normalized, true, getAgentosUrl(), "market_intelligence", controller.signal),
        runTypedResearch(normalized, false, getAgentosUrl(), "company_deep_analysis", controller.signal),
      ]);
      if (marketResult.status === "rejected") throw marketResult.reason;
      const research = workspaceResearchRecord(marketResult.value, deepResult.status === "fulfilled" ? deepResult.value : null);
      const typedBrief = marketBriefFromResearch(research);
      if (controller.signal.aborted || requestId !== researchSequence.current) return;
      setBrief(typedBrief);
      setActiveHistoryPeriod(typedBrief.priceHistory.defaultPeriod);
      if (typedBrief.ticker !== "—") setTicker(typedBrief.ticker.toUpperCase());
      setMessages((current) => [
        ...current,
        { id: nanoid(), role: "user", content: `${mode === "company_deep_analysis" ? "Create a deep company analysis" : "Create a market intelligence brief"} for ${normalized}.` },
        { id: research.request_id, role: "agent", content: typedBrief.analysis || "Structured deterministic research data were returned without an AI narrative." },
      ]);
      recordResearch(mode === "company_deep_analysis" ? "Deep analysis" : "Market intelligence", typedBrief.ticker === "—" ? normalized : typedBrief.ticker, research.status.overall);
      setConnection("ready");
    } catch (researchError) {
      if (controller.signal.aborted || (researchError instanceof DOMException && researchError.name === "AbortError") || requestId !== researchSequence.current) return;
      const message = researchError instanceof Error ? researchError.message : "Could not generate the research record.";
      setError(message);
      setConnection(researchErrorKind(message) === "other" ? "offline" : "ready");
    } finally {
      if (requestId === researchSequence.current) {
        setIsResearching(false);
        if (activeResearchController.current === controller) {
          activeResearchController.current = null;
          activeResearchKey.current = null;
        }
      }
    }
  }

  async function sendChat(question: string) {
    const userMessage: ChatMessage = { id: nanoid(), role: "user", content: question };
    const pendingId = nanoid();
    setMessages((current) => [...current, userMessage, { id: pendingId, role: "agent", content: "", pending: true }]);
    setIsChatting(true);
    setError(null);
    try {
      const contextualQuestion = ticker ? `Current ticker context: ${ticker}.\n\n${question}` : question;
      const response = await runFinanceAgent({ message: contextualQuestion, sessionId });
      setSessionId(response.session_id || sessionId);
      setMessages((current) => current.map((item) => (item.id === pendingId ? { id: response.run_id || pendingId, role: "agent", content: response.content || "" } : item)));
      setConnection("ready");
    } catch (chatError) {
      const message = chatError instanceof Error ? chatError.message : "Could not reach the finance agent.";
      setMessages((current) => current.map((item) => (item.id === pendingId ? { id: pendingId, role: "agent", content: `**AgentOS error:** ${message}` } : item)));
      setError(message);
      setConnection(isTemporaryAiUnavailability(message) ? "ready" : "offline");
    } finally {
      setIsChatting(false);
    }
  }

  function saveEndpoint() {
    const saved = saveAgentosUrl(endpointDraft);
    setEndpointDraft(saved);
    setSettingsOpen(false);
    void verifyConnection(saved);
  }

  const isOffline = connection !== "ready";
  const hasResearch = brief.ticker !== "—";
  const hasWarnings = brief.warnings.length > 0 || brief.freshness.length > 0 || brief.sources.length > 0;
  const canvasQuery = query.trim();
  const canvasLabel = hasResearch ? "Company record" : isResearching ? "Research canvas · verifying" : "Research canvas";
  const canvasTitle = hasResearch ? ticker : isResearching ? "Verifying company record" : "No verified company yet";
  const canvasDescription = hasResearch
    ? [brief.sector, brief.industry, brief.exchange].filter((item) => item && item !== "—").join(" · ")
    : isResearching
      ? `Checking a live research record for ${canvasQuery || "the selected query"}.`
      : canvasQuery
        ? `“${canvasQuery}” is ready in the search field but has not been researched.`
        : "Enter a listed company or ticker, then select Research to build a sourced record.";
  const canvasStatus = hasResearch ? brief.quoteLabel : isResearching ? "Researching" : "Not researched";
  const canvasValue = hasResearch ? brief.quote : "—";
  const canvasDetail = hasResearch ? brief.change : isResearching ? "Checking current market record" : "Select Research to source a live record";
  const selectedSeries = useMemo(() => periodSeries(brief, activeHistoryPeriod), [brief, activeHistoryPeriod]);
  const selectedPerformance = useMemo(() => performanceSummary(selectedSeries), [selectedSeries]);
  const compactFinancials = useMemo(() => {
    const labels = ["EPS", "Profit margin", "Total cash", "Total debt", "Operating margin"];
    return labels.map((label) => brief.deepAnalysis?.financials.find((metric) => metric.label === label) || { label, value: "—", tone: "neutral" as const });
  }, [brief.deepAnalysis]);
  const companySummaryDetails = useMemo(() => (brief.deepAnalysis?.overview || []).filter((item) => !["Company", "Ticker", "Website"].includes(item.label)), [brief.deepAnalysis]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Navigation Bar */}
      <header className="command-bar sticky top-0 z-40 border-b border-[var(--rule)] bg-[var(--surface)]/95 backdrop-blur-md">
        <div className="research-command-inner mx-auto flex h-16 max-w-[90rem] items-center justify-between gap-3 px-4 sm:px-6 lg:px-10">
          <BrandMark />

          {/* Primary Destination Switcher */}
          <nav className="flex items-center gap-1 sm:gap-2 overflow-x-auto py-1 scrollbar-none" aria-label="Primary destinations">
            <button
              type="button"
              onClick={() => setActiveTab("market_intelligence")}
              className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-all whitespace-nowrap flex items-center gap-1.5 ${
                activeTab === "market_intelligence"
                  ? "bg-[var(--surface-raised)] text-[var(--research-indigo)] border border-[var(--rule-strong)] shadow-xs"
                  : "text-[var(--ink-soft)] hover:text-[var(--ink)] hover:bg-[var(--surface-subtle)]"
              }`}
            >
              <BarChart3 className="size-3.5" />
              <span>Market Intelligence</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab("company_deep_analysis");
                if (hasResearch && !brief.deepAnalysis) {
                  void requestResearch(ticker, "company_deep_analysis");
                }
              }}
              className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-all whitespace-nowrap flex items-center gap-1.5 ${
                activeTab === "company_deep_analysis"
                  ? "bg-[var(--surface-raised)] text-[var(--research-indigo)] border border-[var(--rule-strong)] shadow-xs"
                  : "text-[var(--ink-soft)] hover:text-[var(--ink)] hover:bg-[var(--surface-subtle)]"
              }`}
            >
              <Building2 className="size-3.5" />
              <span>Deep Analysis</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("company_comparison")}
              className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-all whitespace-nowrap flex items-center gap-1.5 ${
                activeTab === "company_comparison"
                  ? "bg-[var(--surface-raised)] text-[var(--research-indigo)] border border-[var(--rule-strong)] shadow-xs"
                  : "text-[var(--ink-soft)] hover:text-[var(--ink)] hover:bg-[var(--surface-subtle)]"
              }`}
            >
              <Scale className="size-3.5" />
              <span>Company Comparison</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("ai_research")}
              className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-all whitespace-nowrap flex items-center gap-1.5 ${
                activeTab === "ai_research"
                  ? "bg-[var(--surface-raised)] text-[var(--research-indigo)] border border-[var(--rule-strong)] shadow-xs"
                  : "text-[var(--ink-soft)] hover:text-[var(--ink)] hover:bg-[var(--surface-subtle)]"
              }`}
            >
              <BookOpenText className="size-3.5" />
              <span>AI Research Desk</span>
            </button>
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            <div className="hidden xl:flex items-center gap-2 text-xs text-[var(--ink-soft)] mr-1">
              <span className={`size-2 rounded-full ${connection === "ready" ? "bg-[var(--provenance)]" : "bg-[var(--negative)]"}`} />
              <span className="font-mono text-[11px]">{connection === "ready" ? "Connected" : "Offline"}</span>
            </div>
            <ThemeToggle />
            <button
              type="button"
              onClick={() => void verifyConnection()}
              className="research-icon-button"
              title="Check research endpoint"
              aria-label="Check research endpoint"
            >
              {connection === "checking" ? <LoaderCircle className="size-4 animate-spin" /> : connection === "ready" ? <Network className="size-4 text-[var(--provenance)]" /> : <WifiOff className="size-4 text-[var(--negative)]" />}
            </button>
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="research-icon-button"
              aria-label="Research endpoint settings"
            >
              <Settings2 className="size-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="research-shell terminal-workspace mx-auto max-w-[90rem] w-full px-4 py-5 sm:px-6 lg:px-10 lg:py-7 flex-1">
        {/* Global Error Banner */}
        {error ? (
          <div className="mb-5 flex items-start gap-3 border-l-2 border-[var(--negative)] bg-[color-mix(in_oklab,var(--negative)_7%,var(--surface))] px-4 py-3 text-sm" role="alert">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-[var(--negative)]" />
            <div className="min-w-0 flex-1">
              <strong className="font-semibold text-[var(--ink)]">Research request needs attention.</strong>
              <p className="mt-1 text-[var(--ink-soft)]">{recoveryMessage(error)}</p>
            </div>
            <button type="button" onClick={() => setError(null)} className="text-[var(--ink-faint)] hover:text-[var(--ink)]" aria-label="Dismiss message">
              <X className="size-4" />
            </button>
          </div>
        ) : null}

        {/* DESTINATION 1: MARKET INTELLIGENCE */}
        {activeTab === "market_intelligence" && (
          <div className="space-y-6">
            {/* Search and Masthead */}
            <section className="research-masthead terminal-hero p-5 sm:p-7 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="research-kicker">
                <span className="size-1.5 rounded-full bg-[var(--provenance)]" /> Market Intelligence
              </div>
              <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                <div>
                  <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl tracking-tight text-[var(--ink)]">
                    Market Intelligence & Evidence
                  </h1>
                  <p className="mt-2 max-w-2xl text-xs sm:text-sm text-[var(--ink-soft)] leading-relaxed">
                    Search a listed company for deterministic market context, live quote records, technical signals, price action, and sourced event reporting.
                  </p>
                </div>
                <p className="research-status max-w-sm text-xs font-mono">{availabilityCopy(connection, isResearching, brief)}</p>
              </div>

              {/* Search Form */}
              <form onSubmit={(e) => { e.preventDefault(); void requestResearch(); }} className="research-control-deck workspace-search mt-6 flex flex-col gap-2 sm:flex-row">
                <label className="sr-only" htmlFor="company-search">Search a company or ticker</label>
                <div className="research-search-field flex min-w-0 flex-1 items-center gap-3 border border-[var(--rule-strong)] bg-[var(--surface-raised)] px-4 py-3 transition-colors focus-within:border-[var(--research-indigo)]">
                  <Search className="size-4 shrink-0 text-[var(--research-indigo)]" />
                  <input
                    id="company-search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search a company or ticker (e.g. AAPL, Microsoft)"
                    className="min-w-0 flex-1 bg-transparent text-sm font-medium text-[var(--ink)] outline-none placeholder:text-[var(--ink-faint)]"
                  />
                  <kbd className="hidden border border-[var(--rule)] bg-[var(--surface-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--ink-faint)] sm:inline">↵</kbd>
                </div>
                <button type="submit" disabled={!query.trim() || isResearching} className="research-primary-button">
                  {isResearching ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
                  <span>{isResearching ? "Searching…" : "Search"}</span>
                </button>
              </form>

              {/* Quick Picks */}
              <div className="research-quick-search mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--ink-soft)]">
                <span className="ledger-label">Quick search:</span>
                {starterTickers.map((symbol) => (
                  <button key={symbol} type="button" onClick={() => void requestResearch(symbol)} className="font-mono font-semibold transition-colors hover:text-[var(--research-indigo)]">
                    {symbol}
                  </button>
                ))}
              </div>
            </section>

            {/* Company Identity Header */}
            <section className={`research-identity company-record-panel p-5 border border-[var(--rule)] bg-[var(--surface)] ${hasResearch ? "is-verified" : "is-pending"}`} aria-live="polite">
              <div className="research-identity__content">
                <p className="ledger-label">{canvasLabel}</p>
                <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h2 className="font-serif text-3xl sm:text-4xl text-[var(--ink)] tracking-tight">{canvasTitle}</h2>
                  {hasResearch && brief.companyName !== "—" ? <p className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-soft)]">{brief.companyName}</p> : null}
                </div>
                <p className="research-identity__description text-xs text-[var(--ink-soft)] mt-1">{canvasDescription}</p>
              </div>
              <div className="research-price text-right">
                <p className="ledger-label">{canvasStatus}</p>
                <p className="mt-0.5 font-mono text-2xl sm:text-3xl font-semibold tabular-nums text-[var(--ink)]">
                  {isResearching ? <span className="inline-block h-6 w-20 align-middle shimmer-line" /> : canvasValue}
                </p>
                <p className={`mt-0.5 text-xs font-semibold ${hasResearch && brief.change.startsWith("-") ? "text-[var(--negative)]" : hasResearch ? "text-[var(--positive)]" : "text-[var(--ink-faint)]"}`}>
                  {canvasDetail}
                </p>
              </div>
            </section>

            {/* Market Snapshot (6 Core Metrics) */}
            <section className="research-section terminal-snapshot border border-[var(--rule)] bg-[var(--surface)] overflow-hidden" aria-labelledby="snapshot-heading">
              <div className="research-section-heading p-4 border-b border-[var(--rule)] flex items-center justify-between">
                <div>
                  <p className="ledger-label">Market snapshot</p>
                  <h3 id="snapshot-heading" className="text-base font-semibold text-[var(--ink)]">Key Market Indicators</h3>
                </div>
                <button type="button" onClick={() => void requestResearch(ticker)} disabled={isResearching || isOffline || !hasResearch} className="research-text-button flex items-center gap-1.5 text-xs">
                  <RefreshCw className={`size-3.5 ${isResearching ? "animate-spin" : ""}`} /> Refresh
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-y sm:divide-y-0 divide-x divide-[var(--rule)]">
                {brief.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
              </div>
            </section>

            {/* Price Chart & Key Signals */}
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(20rem,0.5fr)]">
              {/* Performance Chart */}
              <section className="research-section border border-[var(--rule)] bg-[var(--surface)] overflow-hidden">
                <div className="research-section-heading p-4 border-b border-[var(--rule)] flex items-center justify-between">
                  <div>
                    <p className="ledger-label">Price and performance</p>
                    <h3 className="text-base font-semibold text-[var(--ink)]">Returned Price Action</h3>
                  </div>
                  <span className="research-state text-xs font-mono">{selectedSeries.length ? `${selectedSeries.length} points` : "Unavailable"}</span>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--rule)] px-4 py-2.5">
                  <div className="flex flex-wrap gap-1" role="tablist">
                    {brief.priceHistory.availablePeriods.map((period) => (
                      <button key={period} type="button" onClick={() => setActiveHistoryPeriod(period)} className={`company-period-tab text-xs px-2 py-1 rounded ${activeHistoryPeriod === period ? "is-active font-bold bg-[var(--surface-raised)]" : ""}`}>
                        {historyPeriodLabels[period]}
                      </button>
                    ))}
                  </div>
                  {selectedPerformance ? (
                    <div className="flex items-center gap-3 text-xs text-[var(--ink-soft)] font-mono">
                      <span>Range: <strong>{selectedPerformance.low.toFixed(2)}–{selectedPerformance.high.toFixed(2)}</strong></span>
                      <span className={selectedPerformance.change >= 0 ? "text-[var(--positive)] font-bold" : "text-[var(--negative)] font-bold"}>
                        {selectedPerformance.change >= 0 ? "+" : ""}{selectedPerformance.change.toFixed(2)}%
                      </span>
                    </div>
                  ) : null}
                </div>
                <MarketChart data={selectedSeries} />
              </section>

              {/* Market Signal */}
              <section className="research-section border border-[var(--rule)] bg-[var(--surface)] overflow-hidden">
                <div className="research-section-heading p-4 border-b border-[var(--rule)] flex items-center justify-between">
                  <div>
                    <p className="ledger-label">Technical signal</p>
                    <h3 className="text-base font-semibold text-[var(--ink)]">Quantitative Pulse</h3>
                  </div>
                  {brief.signal ? (
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${brief.signal.label === "BULLISH" ? "bg-[var(--positive)]/15 text-[var(--positive)]" : brief.signal.label === "BEARISH" ? "bg-[var(--negative)]/15 text-[var(--negative)]" : "bg-[var(--surface-subtle)] text-[var(--ink-soft)]"}`}>
                      {brief.signal.label}
                    </span>
                  ) : null}
                </div>
                {brief.signal ? (
                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3 border-b border-[var(--rule)] pb-3 text-center">
                      <div>
                        <p className="ledger-label">Score</p>
                        <p className="font-mono text-xl font-bold text-[var(--ink)] mt-1">{brief.signal.score}</p>
                      </div>
                      <div className="border-l border-[var(--rule)]">
                        <p className="ledger-label">Confidence</p>
                        <p className="font-mono text-xl font-bold text-[var(--ink)] mt-1">{brief.signal.confidence}</p>
                      </div>
                    </div>
                    <p className="text-xs text-[var(--ink-soft)] leading-relaxed">{brief.signal.explanation}</p>
                    <ul className="space-y-1.5 text-xs text-[var(--ink-soft)]">
                      {brief.signal.factors.map((factor) => (
                        <li key={factor} className="flex gap-2">
                          <span className="mt-1 size-1 shrink-0 rounded-full bg-[var(--provenance)]" />
                          <span>{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="p-5 text-center text-xs text-[var(--ink-soft)]">
                    Market signals appear once sufficient history is sourced.
                  </div>
                )}
              </section>
            </div>

            {/* Recent News & Events */}
            <div className="grid gap-5 md:grid-cols-2">
              {/* News */}
              <section className="research-section border border-[var(--rule)] bg-[var(--surface)] overflow-hidden">
                <div className="p-4 border-b border-[var(--rule)] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Newspaper className="size-4 text-[var(--research-indigo)]" />
                    <h3 className="text-sm font-semibold text-[var(--ink)]">Recent Sourced News</h3>
                  </div>
                  <span className="text-[10px] font-mono text-[var(--ink-faint)]">Filtered by relevance</span>
                </div>
                {brief.news.length ? (
                  <ol className="divide-y divide-[var(--rule)] text-xs">
                    {brief.news.slice(0, 5).map((item, idx) => (
                      <li key={idx} className="p-3.5 hover:bg-[var(--surface-raised)] transition-colors">
                        <p className="font-medium text-[var(--ink)] leading-snug">
                          {item.url ? <a href={item.url} target="_blank" rel="noreferrer" className="hover:underline hover:text-[var(--research-indigo)]">{item.title}</a> : item.title}
                        </p>
                        <p className="mt-1 text-[10px] text-[var(--ink-faint)]">
                          {[item.publisher, displayDate(item.publishedAt)].filter(Boolean).join(" · ")}
                        </p>
                        {item.summary && <p className="mt-1 text-xs text-[var(--ink-soft)] line-clamp-2">{item.summary}</p>}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="p-5 text-center text-xs text-[var(--ink-soft)]">No sourced news available.</div>
                )}
              </section>

              {/* Events */}
              <section className="research-section border border-[var(--rule)] bg-[var(--surface)] overflow-hidden">
                <div className="p-4 border-b border-[var(--rule)] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="size-4 text-[var(--provenance)]" />
                    <h3 className="text-sm font-semibold text-[var(--ink)]">Calendar & Key Events</h3>
                  </div>
                  <span className="text-[10px] font-mono text-[var(--ink-faint)]">Audited dates</span>
                </div>
                {brief.events.length ? (
                  <ol className="divide-y divide-[var(--rule)] text-xs">
                    {brief.events.map((event, idx) => (
                      <li key={idx} className="p-3.5 flex items-start justify-between gap-3 hover:bg-[var(--surface-raised)] transition-colors">
                        <div>
                          <p className="font-medium text-[var(--ink)]">{event.title}</p>
                          <p className="mt-0.5 text-[10px] text-[var(--ink-faint)]">{event.source}</p>
                        </div>
                        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[var(--surface-subtle)] text-[var(--ink-soft)] shrink-0">
                          {event.date}
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="p-5 text-center text-xs text-[var(--ink-soft)]">No upcoming events found.</div>
                )}
              </section>
            </div>
          </div>
        )}

        {/* DESTINATION 2: COMPANY DEEP ANALYSIS */}
        {activeTab === "company_deep_analysis" && (
          <div className="space-y-6">
            <section className="terminal-hero p-5 sm:p-7 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="research-kicker">
                <span className="size-1.5 rounded-full bg-[var(--provenance)]" /> Deep Fundamental Dossier
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h1 className="font-serif text-3xl sm:text-4xl text-[var(--ink)] tracking-tight">
                    {hasResearch ? `${brief.ticker} — Company Deep Analysis` : "Company Deep Analysis"}
                  </h1>
                  <p className="mt-1 text-xs sm:text-sm text-[var(--ink-soft)] max-w-2xl">
                    Audited fundamentals, financial health statement analysis, governance leadership roster, and competitive evidence.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void requestResearch(ticker, "company_deep_analysis")}
                  disabled={isResearching || isOffline || !hasResearch}
                  className="research-primary-button flex items-center gap-2"
                >
                  {isResearching ? <LoaderCircle className="size-4 animate-spin" /> : <FileSearch className="size-4" />}
                  <span>{isResearching ? "Loading…" : "Refresh Analysis"}</span>
                </button>
              </div>
            </section>

            {/* Financial Health Metrics */}
            <section className="border border-[var(--rule)] bg-[var(--surface)] overflow-hidden">
              <div className="p-4 border-b border-[var(--rule)] flex items-center justify-between">
                <div>
                  <span className="ledger-label">Fundamentals</span>
                  <h3 className="text-base font-semibold text-[var(--ink)]">Reported Financial Health</h3>
                </div>
                {brief.deepAnalysis?.profile.fiscalPeriodEnd && (
                  <span className="text-xs font-mono text-[var(--ink-faint)]">Fiscal Period: {brief.deepAnalysis.profile.fiscalPeriodEnd}</span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-y sm:divide-y-0 divide-x divide-[var(--rule)]">
                {compactFinancials.map((metric) => (
                  <MetricCard key={metric.label} metric={metric} variant="compact" />
                ))}
              </div>
            </section>

            {/* Company Overview & Description */}
            {brief.deepAnalysis ? (
              <div className="grid gap-5 md:grid-cols-2">
                <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] space-y-3">
                  <span className="ledger-label">Company Record</span>
                  <h4 className="font-serif text-xl font-bold text-[var(--ink)]">Corporate Profile</h4>
                  <p className="text-xs text-[var(--ink-soft)] leading-relaxed">
                    {brief.deepAnalysis.profile.description || "No corporate description was returned by the provider."}
                  </p>
                  {brief.deepAnalysis.profile.website && (
                    <a
                      href={brief.deepAnalysis.profile.website}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-[var(--research-indigo)] font-semibold hover:underline"
                    >
                      <span>Corporate Website</span>
                      <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>

                <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] space-y-3">
                  <span className="ledger-label">Corporate Attributes</span>
                  <h4 className="font-serif text-xl font-bold text-[var(--ink)]">Metadata & Structure</h4>
                  <dl className="grid grid-cols-2 gap-3 text-xs">
                    {companySummaryDetails.map((item) => (
                      <div key={item.label} className="border-b border-[var(--rule)] pb-2">
                        <dt className="text-[var(--ink-faint)]">{item.label}</dt>
                        <dd className="font-medium text-[var(--ink)] mt-0.5">{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            ) : null}

            {/* Governance & Competitive Position */}
            {brief.deepAnalysis ? (
              <div className="grid gap-5 md:grid-cols-2">
                <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] space-y-3">
                  <span className="ledger-label">Leadership Roster</span>
                  <h4 className="font-serif text-lg font-bold text-[var(--ink)]">Governance & Executive Leadership</h4>
                  <p className="text-xs font-semibold text-[var(--ink)]">CEO: {brief.deepAnalysis.governance.ceo || "—"}</p>
                  {brief.deepAnalysis.governance.leadership.length ? (
                    <ul className="mt-2 space-y-1 text-xs text-[var(--ink-soft)]">
                      {brief.deepAnalysis.governance.leadership.map((person) => (
                        <li key={person} className="flex gap-2 items-center">
                          <span className="size-1 rounded-full bg-[var(--research-indigo)]" />
                          <span>{person}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-[var(--ink-faint)]">No additional leadership records returned.</p>
                  )}
                </div>

                <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] space-y-3">
                  <span className="ledger-label">Industry Positioning</span>
                  <h4 className="font-serif text-lg font-bold text-[var(--ink)]">Competitive Evidence</h4>
                  <p className="text-xs text-[var(--ink-soft)] leading-relaxed">
                    {brief.deepAnalysis.competitors.note || "No specific competitive commentary was returned."}
                  </p>
                </div>
              </div>
            ) : null}

            {/* Research Brief Markdown Synthesis */}
            <div className="border border-[var(--rule)] bg-[var(--surface)] p-5">
              <AnalysisPanel analysis={brief.analysis} ticker={ticker} isLoading={isResearching} unavailableNotice={brief.aiInterpretationNotice} />
            </div>
          </div>
        )}

        {/* DESTINATION 3: COMPANY COMPARISON */}
        {activeTab === "company_comparison" && (
          <CompanyComparison initialCompanyA={ticker} initialCompanyB="MSFT" />
        )}

        {/* DESTINATION 4: AI RESEARCH DESK */}
        {activeTab === "ai_research" && (
          <div className="space-y-6">
            <section className="terminal-hero p-5 sm:p-7 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="research-kicker">
                <span className="size-1.5 rounded-full bg-[var(--provenance)]" /> Autonomous Finance Desk
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl text-[var(--ink)] tracking-tight mt-2">
                AI Financial Research Desk
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-[var(--ink-soft)] max-w-2xl">
                Dedicated research conversation context with access to real-time market data, company filings, and quantitative indicators.
              </p>
            </section>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
              <div className="border border-[var(--rule)] bg-[var(--surface)] p-5">
                <ChatPanel messages={messages} isLoading={isChatting || isResearching} disabled={isOffline} onSend={sendChat} />
              </div>
              <aside className="border border-[var(--rule)] bg-[var(--surface)] p-4 space-y-4">
                <div>
                  <span className="ledger-label">Research Session</span>
                  <h4 className="text-xs font-semibold text-[var(--ink)] mt-1">Active Context</h4>
                  <p className="text-xs text-[var(--ink-soft)] mt-0.5">Ticker: <span className="font-mono font-bold text-[var(--research-indigo)]">{ticker}</span></p>
                </div>
                <div className="border-t border-[var(--rule)] pt-3">
                  <span className="ledger-label">Recent Activity</span>
                  {researchActivity.length ? (
                    <ol className="mt-2 space-y-2 text-xs">
                      {researchActivity.map((entry) => (
                        <li key={entry.id} className="p-2 rounded bg-[var(--surface-subtle)] border border-[var(--rule)]">
                          <p className="font-semibold text-[var(--ink)]">{entry.query}</p>
                          <p className="text-[10px] text-[var(--ink-soft)] mt-0.5">{entry.type} · {entry.status}</p>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-xs text-[var(--ink-faint)] mt-2">No activity recorded yet.</p>
                  )}
                </div>
              </aside>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--rule)] bg-[var(--surface)] py-4 px-4 sm:px-6 lg:px-10 text-[11px] text-[var(--ink-faint)] flex flex-col sm:flex-row items-center justify-between gap-2">
        <p>QuantAI separates verified deterministic research data from optional AI interpretation.</p>
        <p className="font-mono">{connection === "ready" ? connectionNote : "Research endpoint offline"}</p>
      </footer>

      {/* Settings Modal */}
      {settingsOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4 backdrop-blur-xs" role="dialog" aria-modal="true" aria-label="Research endpoint settings">
          <div className="w-full max-w-md bg-[var(--surface)] border border-[var(--rule)] p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="ledger-label">Connection Settings</p>
                <h2 className="mt-1 font-serif text-xl font-bold text-[var(--ink)]">Research Desk Endpoint</h2>
              </div>
              <button type="button" onClick={() => setSettingsOpen(false)} className="text-[var(--ink-faint)] hover:text-[var(--ink)]" aria-label="Close settings">
                <X className="size-5" />
              </button>
            </div>
            <p className="mt-2 text-xs text-[var(--ink-soft)] leading-relaxed">
              Default same-origin <code className="px-1 py-0.5 rounded bg-[var(--surface-subtle)] font-mono text-[10px]">/api</code> route proxies to the local Python backend.
            </p>
            <label className="mt-4 block">
              <span className="ledger-label">Backend API URL</span>
              <input value={endpointDraft} onChange={(e) => setEndpointDraft(e.target.value)} className="mt-1.5 w-full border border-[var(--rule-strong)] bg-[var(--surface-raised)] px-3 py-2 text-xs text-[var(--ink)] font-mono outline-none focus:border-[var(--research-indigo)]" />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setSettingsOpen(false)} className="research-text-button text-xs">Cancel</button>
              <button type="button" onClick={saveEndpoint} className="research-primary-button text-xs px-4 py-2">Save & Test</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
