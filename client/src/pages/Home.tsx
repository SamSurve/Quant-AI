/**
 * Evidence Briefing visual contract: search, verified facts, signals, reporting,
 * optional interpretation, then an expandable evidence appendix. No data is
 * displayed unless it originates in the existing typed research or AgentOS flow.
 */

import { useEffect, useState } from "react";
import { nanoid } from "nanoid";
import { AlertCircle, ChevronDown, ChevronRight, CircleHelp, FileSearch, LoaderCircle, Network, RefreshCw, Search, Settings2, Sparkles, WifiOff, X } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { ChatPanel, type ChatMessage } from "@/components/ChatPanel";
import { ComparisonPanel } from "@/components/ComparisonPanel";
import { MarketChart } from "@/components/MarketChart";
import { MetricCard } from "@/components/MetricCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { fetchAgentInfo, getAgentosUrl, runFinanceAgent, saveAgentosUrl } from "@/lib/agentos";
import { emptyMarketBrief, marketBriefFromResearch, type MarketBrief } from "@/lib/market";
import { researchErrorKind, runCompanyComparison, runTypedResearch, type TypedResearchResponse } from "@/lib/research";

const starterTickers = ["AAPL", "MSFT", "NVDA", "TSLA"];
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

export default function Home() {
  const [ticker, setTicker] = useState("AAPL");
  const [query, setQuery] = useState("AAPL");
  const [brief, setBrief] = useState<MarketBrief>(emptyMarketBrief);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [connection, setConnection] = useState<Connection>("checking");
  const [connectionNote, setConnectionNote] = useState("Checking Research Desk…");
  const [isResearching, setIsResearching] = useState(false);
  const [activeResearchMode, setActiveResearchMode] = useState<"market_intelligence" | "company_deep_analysis">("market_intelligence");
  const [companyA, setCompanyA] = useState("AAPL");
  const [companyB, setCompanyB] = useState("MSFT");
  const [comparison, setComparison] = useState<NonNullable<TypedResearchResponse["company_comparison"]> | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isChatting, setIsChatting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [endpointDraft, setEndpointDraft] = useState(getAgentosUrl());
  const [researchActivity, setResearchActivity] = useState<ResearchActivity[]>([]);

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

  function recordResearch(type: string, queryLabel: string, status: string, confidence?: string) {
    setResearchActivity((current) => [{ id: nanoid(), type, query: queryLabel, status, confidence }, ...current].slice(0, 5));
  }

  async function requestResearch(symbol = query, mode: "market_intelligence" | "company_deep_analysis" = activeResearchMode) {
    const normalized = symbol.trim();
    if (!normalized || isResearching) return;
    setQuery(normalized);
    setActiveResearchMode(mode);
    setComparison(null);
    // Do not relabel a prior verified record with an unverified input while the
    // entity lookup is pending or fails.  The new ticker appears only after the
    // typed response proves the resolved company identity.
    setBrief(emptyMarketBrief);
    setIsResearching(true);
    setError(null);
    try {
      const research = await runTypedResearch(normalized, true, getAgentosUrl(), mode);
      const typedBrief = marketBriefFromResearch(research);
      setBrief(typedBrief);
      if (typedBrief.ticker !== "—") setTicker(typedBrief.ticker.toUpperCase());
      setMessages((current) => [
        ...current,
        { id: nanoid(), role: "user", content: `${mode === "company_deep_analysis" ? "Create a deep company analysis" : "Create a market intelligence brief"} for ${normalized}.` },
        { id: research.request_id, role: "agent", content: typedBrief.analysis || "Structured deterministic research data were returned without an AI narrative." },
      ]);
      recordResearch(mode === "company_deep_analysis" ? "Deep analysis" : "Market intelligence", typedBrief.ticker === "—" ? normalized : typedBrief.ticker, research.status.overall);
      setConnection("ready");
    } catch (researchError) {
      const message = researchError instanceof Error ? researchError.message : "Could not generate the research record.";
      setError(message);
      setConnection(researchErrorKind(message) === "other" ? "offline" : "ready");
    } finally {
      setIsResearching(false);
    }
  }

  async function requestComparison() {
    const normalizedA = companyA.trim();
    const normalizedB = companyB.trim();
    if (!normalizedA || !normalizedB || isResearching) return;
    setIsResearching(true);
    setIsComparing(true);
    setError(null);
    try {
      const research = await runCompanyComparison(normalizedA, normalizedB, true, getAgentosUrl());
      const report = research.company_comparison;
      if (!report) throw new Error("The comparison response did not include a structured report.");
      setComparison(report);
      const typedBrief = marketBriefFromResearch(research);
      setBrief(typedBrief);
      setTicker(report.company_a.ticker);
      setQuery(report.company_a.ticker);
      setMessages((current) => [
        ...current,
        { id: nanoid(), role: "user", content: `Compare ${report.company_a.ticker} with ${report.company_b.ticker}.` },
        { id: research.request_id, role: "agent", content: report.analyst_interpretation?.executive_summary || "Structured comparison evidence was returned without an AI narrative." },
      ]);
      recordResearch("Comparison", `${report.company_a.ticker} / ${report.company_b.ticker}`, research.status.overall, report.comparison_confidence.level);
      setConnection("ready");
    } catch (comparisonError) {
      const message = comparisonError instanceof Error ? comparisonError.message : "Could not compare the selected companies.";
      setError(message);
      setConnection(researchErrorKind(message) === "other" ? "offline" : "ready");
    } finally {
      setIsResearching(false);
      setIsComparing(false);
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

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="command-bar sticky top-0 z-40 border-b border-[var(--rule)] backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <div className="hidden items-center gap-4 text-xs text-[var(--ink-soft)] sm:flex"><span>Evidence-first market research</span><span className="h-3 w-px bg-[var(--rule)]" /><span className={connection === "ready" ? "text-[var(--provenance)]" : "text-[var(--negative)]"}>{connection === "ready" ? "Research Desk connected" : connection === "checking" ? "Checking Research Desk" : "Research Desk unavailable"}</span></div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button type="button" onClick={() => void verifyConnection()} className="research-icon-button" title="Check research endpoint" aria-label="Check research endpoint">{connection === "checking" ? <LoaderCircle className="size-4 animate-spin" /> : connection === "ready" ? <Network className="size-4 text-[var(--provenance)]" /> : <WifiOff className="size-4 text-[var(--negative)]" />}</button>
            <button type="button" onClick={() => setSettingsOpen(true)} className="research-icon-button" aria-label="Research endpoint settings"><Settings2 className="size-4" /></button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
        {error ? <div className="mb-5 flex items-start gap-3 border-l-2 border-[var(--negative)] bg-[color-mix(in_oklab,var(--negative)_7%,var(--surface))] px-4 py-3 text-sm" role="alert"><AlertCircle className="mt-0.5 size-4 shrink-0 text-[var(--negative)]" /><div className="min-w-0 flex-1"><strong className="font-semibold text-[var(--ink)]">Research request needs attention.</strong><p className="mt-1 text-[var(--ink-soft)]">{recoveryMessage(error)}</p></div><button type="button" onClick={() => setError(null)} className="text-[var(--ink-faint)] hover:text-[var(--ink)]" aria-label="Dismiss message"><X className="size-4" /></button></div> : null}

        <section className="research-masthead" id="market">
          <div className="research-kicker"><span className="size-1.5 rounded-full bg-[var(--provenance)]" /> Live research</div>
          <div className="mt-5 grid gap-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <p className="max-w-2xl font-serif text-4xl leading-[1.02] tracking-[-0.055em] text-[var(--ink)] sm:text-5xl">Search a company, then follow the evidence.</p>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--ink-soft)]">Market facts, reported news, event records, and optional interpretation stay clearly separated.</p>
            </div>
            <p className="research-status max-w-sm">{availabilityCopy(connection, isResearching, brief)}</p>
          </div>
          <form onSubmit={(event) => { event.preventDefault(); void requestResearch(); }} className="mt-7 flex flex-col gap-2 sm:flex-row">
            <label className="sr-only" htmlFor="company-search">Search a company or ticker</label>
            <div className="flex min-w-0 flex-1 items-center gap-3 border border-[var(--rule-strong)] bg-[var(--surface)] px-4 py-3.5 transition-colors focus-within:border-[var(--research-indigo)]"><Search className="size-4 shrink-0 text-[var(--research-indigo)]" /><input id="company-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a company or ticker" className="min-w-0 flex-1 bg-transparent text-base font-medium text-[var(--ink)] outline-none placeholder:font-normal placeholder:text-[var(--ink-faint)]" /><kbd className="hidden border border-[var(--rule)] bg-[var(--surface-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--ink-faint)] sm:inline">↵</kbd></div>
            <button type="submit" disabled={isResearching || !query.trim()} className="research-primary-button">{isResearching && !isComparing ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}{isResearching && !isComparing ? "Researching" : "Research"}</button>
            <button type="button" onClick={() => void requestResearch(query, "company_deep_analysis")} disabled={isResearching || !query.trim()} className="research-secondary-button"><FileSearch className="size-4" /> Deep analysis</button>
          </form>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[var(--ink-soft)]"><span className="ledger-label">Quick search</span>{starterTickers.map((symbol) => <button key={symbol} type="button" onClick={() => void requestResearch(symbol)} disabled={isResearching} className="font-mono font-semibold transition-colors hover:text-[var(--research-indigo)] disabled:opacity-45">{symbol}</button>)}</div>
        </section>

        <section className="research-identity mt-5" aria-live="polite">
          <div className="min-w-0"><p className="ledger-label">{hasResearch ? "Company record" : "Research canvas"}</p><div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1"><h1 className="font-serif text-4xl tracking-[-0.055em] text-[var(--ink)] sm:text-5xl">{ticker}</h1>{brief.companyName !== "—" ? <p className="text-sm font-semibold uppercase tracking-[0.1em] text-[var(--ink-soft)]">{brief.companyName}</p> : null}</div><p className="mt-2 text-sm text-[var(--ink-soft)]">{brief.sector !== "—" ? [brief.sector, brief.industry, brief.exchange].filter((item) => item && item !== "—").join(" · ") : "Awaiting a verified company record."}</p></div>
          <div className="research-price"><p className="ledger-label">{brief.quoteLabel}</p><p className="mt-1 font-mono text-3xl font-semibold tracking-[-0.06em] tabular-nums text-[var(--ink)]">{isResearching ? <span className="inline-block h-7 w-24 align-middle shimmer-line" /> : brief.quote}</p><p className={`mt-1 text-xs font-semibold ${brief.change.startsWith("-") ? "text-[var(--negative)]" : "text-[var(--positive)]"}`}>{isResearching ? "Checking current market record" : brief.change}</p></div>
        </section>

        <section className="research-section mt-8 overflow-hidden" aria-labelledby="snapshot-heading">
          <div className="research-section-heading"><div><p className="ledger-label">Market snapshot</p><h2 id="snapshot-heading">The record at a glance</h2></div><button type="button" onClick={() => void requestResearch(ticker)} disabled={isResearching || isOffline || !hasResearch} className="research-text-button"><RefreshCw className={`size-3.5 ${isResearching ? "animate-spin" : ""}`} /> Refresh</button></div>
          <div className="grid grid-cols-2 border-y border-[var(--rule)] sm:grid-cols-3 lg:grid-cols-6">{brief.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}</div>
          <p className="research-section-foot">Values are shown only when returned by the current market record.</p>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(300px,.65fr)]">
          <section className="research-section overflow-hidden" aria-labelledby="history-heading"><div className="research-section-heading"><div><p className="ledger-label">Price history</p><h2 id="history-heading">Price movement</h2></div><span className="research-state">Returned series only</span></div><MarketChart data={brief.chart} /></section>
          <section className="research-section overflow-hidden" id="signal" aria-labelledby="signal-heading"><div className="research-section-heading"><div><p className="ledger-label">Key signals</p><h2 id="signal-heading">Market signal</h2></div>{brief.signal ? <span className={`research-state ${brief.signal.label === "BULLISH" ? "text-[var(--positive)]" : brief.signal.label === "BEARISH" ? "text-[var(--negative)]" : ""}`}>{brief.signal.label}</span> : null}</div>{brief.signal ? <div className="p-5"><div className="grid grid-cols-2 gap-5 border-b border-[var(--rule)] pb-5"><div><p className="ledger-label">Score</p><p className="mt-2 font-mono text-2xl font-semibold text-[var(--ink)]">{brief.signal.score}</p></div><div><p className="ledger-label">Confidence</p><p className="mt-2 font-mono text-2xl font-semibold text-[var(--ink)]">{brief.signal.confidence}</p></div></div><p className="mt-5 text-sm leading-relaxed text-[var(--ink-soft)]">{brief.signal.explanation}</p><ul className="mt-4 space-y-2 text-xs leading-relaxed text-[var(--ink-soft)]">{brief.signal.factors.map((factor) => <li key={factor} className="flex gap-2"><span className="mt-1.5 size-1 shrink-0 rounded-full bg-[var(--provenance)]" />{factor}</li>)}</ul><details className="research-details mt-5"><summary>Signal method</summary><p>{brief.signal.methodology}</p></details></div> : <div className="p-5"><p className="text-sm leading-relaxed text-[var(--ink-soft)]">Signal unavailable until sufficient deterministic history is sourced.</p></div>}</section>
        </section>

        <div className="mt-8" id="analysis"><AnalysisPanel analysis={brief.analysis} ticker={ticker} isLoading={isResearching && !isComparing} unavailableNotice={brief.aiInterpretationNotice} /></div>

        {brief.deepAnalysis ? <details className="research-disclosure mt-8" open={activeResearchMode === "company_deep_analysis"}><summary><span><span className="ledger-label">Company report</span><strong>Deep analysis</strong></span><ChevronDown className="size-4" /></summary><div className="border-t border-[var(--rule)] p-5 sm:p-7"><div className="grid gap-7 lg:grid-cols-2"><div><p className="ledger-label">Company profile</p><dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-4">{brief.deepAnalysis.overview.slice(0, 8).map((item) => <div key={item.label}><dt className="ledger-label">{item.label}</dt><dd className="mt-1 text-sm text-[var(--ink)]">{item.value}</dd></div>)}</dl></div><div><p className="ledger-label">Financial health</p><div className="mt-3 grid grid-cols-2 gap-x-5 gap-y-4">{brief.deepAnalysis.financials.slice(0, 6).map((metric) => <div key={metric.label}><p className="ledger-label">{metric.label}</p><p className="mt-1 font-mono text-sm text-[var(--ink)]">{metric.value}</p></div>)}</div></div></div><div className="mt-7 grid gap-7 border-t border-[var(--rule)] pt-6 lg:grid-cols-2"><div><p className="ledger-label">Governance</p><p className="mt-2 text-sm font-semibold text-[var(--ink)]">{brief.deepAnalysis.governance.ceo}</p>{brief.deepAnalysis.governance.leadership.length ? <ul className="mt-3 space-y-1 text-xs text-[var(--ink-soft)]">{brief.deepAnalysis.governance.leadership.map((person) => <li key={person}>{person}</li>)}</ul> : <p className="mt-3 text-sm text-[var(--ink-soft)]">No verified leadership record was returned.</p>}</div><div><p className="ledger-label">Competitive evidence</p><p className="mt-2 text-sm leading-relaxed text-[var(--ink-soft)]">{brief.deepAnalysis.competitors.note}</p></div></div></div></details> : null}

        <section className="research-section mt-8 overflow-hidden" id="news" aria-labelledby="news-heading"><div className="research-section-heading"><div><p className="ledger-label">Recent news</p><h2 id="news-heading">What is moving the conversation</h2></div><span className="research-state">Sourced reporting</span></div>{isResearching ? <div className="space-y-3 p-5"><div className="shimmer-line h-5 w-full" /><div className="shimmer-line h-5 w-[86%]" /><div className="shimmer-line h-5 w-[72%]" /></div> : brief.news.length ? <ol className="divide-y divide-[var(--rule)]">{brief.news.slice(0, 6).map((item, index) => <li key={`${item.title}-${index}`} className="grid gap-2 px-5 py-4 sm:grid-cols-[2.5rem_1fr_auto] sm:items-start sm:px-7"><span className="font-mono text-xs text-[var(--provenance)]">{String(index + 1).padStart(2, "0")}</span><div><p className="text-sm leading-relaxed text-[var(--ink)]">{item.url ? <a href={item.url} target="_blank" rel="noreferrer" className="transition-colors hover:text-[var(--research-indigo)] hover:underline">{item.title}</a> : item.title}</p><p className="mt-1 text-xs text-[var(--ink-faint)]">{[item.publisher, displayDate(item.publishedAt)].filter(Boolean).join(" · ") || "Source metadata unavailable"}</p></div>{item.url ? <a href={item.url} target="_blank" rel="noreferrer" className="research-source-link">Open source <ChevronRight className="size-3" /></a> : null}</li>)}</ol> : <div className="p-5 sm:p-7"><p className="text-sm leading-relaxed text-[var(--ink-soft)]">No sourced recent news was returned for this request.</p></div>}</section>

        <section className="research-section mt-8 overflow-hidden" aria-labelledby="events-heading"><div className="research-section-heading"><div><p className="ledger-label">Events</p><h2 id="events-heading">Calendar records</h2></div></div>{brief.events.length ? <ol className="divide-y divide-[var(--rule)]">{brief.events.map((event, index) => <li key={`${event.title}-${event.date}-${index}`} className="grid gap-2 px-5 py-4 sm:grid-cols-[9rem_1fr_auto] sm:items-center sm:px-7"><span className="font-mono text-xs text-[var(--provenance)]">{event.date}</span><div><p className="text-sm font-semibold text-[var(--ink)]">{event.title}</p><p className="mt-1 text-xs text-[var(--ink-faint)]">{event.source}</p></div><span className="research-state">{event.importance}</span></li>)}</ol> : <div className="p-5 sm:p-7"><p className="text-sm leading-relaxed text-[var(--ink-soft)]">No reliable event record was returned for this request.</p></div>}</section>

        <details className="research-disclosure mt-8" id="comparison"><summary><span><span className="ledger-label">Research tool</span><strong>Compare two companies</strong></span><ChevronDown className="size-4" /></summary><div className="border-t border-[var(--rule)] p-5 sm:p-7"><form onSubmit={(event) => { event.preventDefault(); void requestComparison(); }} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]"><label><span className="ledger-label">Company A</span><input value={companyA} onChange={(event) => setCompanyA(event.target.value)} placeholder="AAPL" className="research-input mt-2" /></label><label><span className="ledger-label">Company B</span><input value={companyB} onChange={(event) => setCompanyB(event.target.value)} placeholder="MSFT" className="research-input mt-2" /></label><button type="submit" disabled={isResearching || !companyA.trim() || !companyB.trim()} className="research-secondary-button mt-[22px] h-[48px]"><ChevronRight className="size-4" /> Compare</button></form><ComparisonPanel report={comparison} isLoading={isComparing} /></div></details>

        {hasWarnings ? <details className="research-disclosure mt-8" id="sources"><summary><span><span className="ledger-label">Evidence appendix</span><strong>Sources, freshness, and research notes</strong></span><ChevronDown className="size-4" /></summary><div className="border-t border-[var(--rule)] p-5 sm:p-7"><div className="grid gap-7 lg:grid-cols-[.85fr_1.15fr]"><div><p className="ledger-label">Freshness</p><div className="mt-3 space-y-2">{brief.freshness.length ? brief.freshness.map((item) => <div key={item.label} className="flex items-center justify-between gap-3 border-b border-[var(--rule)] py-2 text-xs"><span className="font-semibold text-[var(--ink)]">{item.label}</span><span className="text-right text-[var(--ink-soft)]">{item.state} · {item.asOf}</span></div>) : <p className="text-sm text-[var(--ink-soft)]">No freshness record was returned.</p>}</div></div><div><p className="ledger-label">Source records</p>{brief.sources.length ? <ul className="mt-3 divide-y divide-[var(--rule)]">{brief.sources.map((source, index) => <li key={`${source.source}-${source.dataType}-${index}`} className="flex items-start justify-between gap-4 py-3 text-xs"><div><p className="font-semibold text-[var(--ink)]">{source.source}</p><p className="mt-1 text-[var(--ink-faint)]">{source.dataType} · {source.retrievedAt}</p></div>{source.url ? <a href={source.url} target="_blank" rel="noreferrer" className="research-source-link">Open source <ChevronRight className="size-3" /></a> : null}</li>)}</ul> : <p className="mt-3 text-sm text-[var(--ink-soft)]">No source records were returned.</p>}</div></div>{brief.warnings.length ? <div className="mt-7 border-l-2 border-[var(--negative)] bg-[color-mix(in_oklab,var(--negative)_6%,var(--surface))] px-4 py-3"><p className="ledger-label">Research notes</p><ul className="mt-2 space-y-1 text-xs leading-relaxed text-[var(--ink-soft)]">{brief.warnings.map((warning) => <li key={`${warning.category}-${warning.message}`}>{warning.message}</li>)}</ul></div> : null}</div></details> : null}

        <details className="research-disclosure mt-8"><summary><span><span className="ledger-label">Research Desk</span><strong>Ask the finance agent</strong></span><ChevronDown className="size-4" /></summary><div className="border-t border-[var(--rule)] p-5 sm:p-7"><div className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_16rem]"><ChatPanel messages={messages} isLoading={isChatting || isResearching} disabled={isOffline} onSend={sendChat} /><aside className="border-l border-[var(--rule)] pl-5"><p className="ledger-label">Recent activity</p>{researchActivity.length ? <ol className="mt-3 space-y-3">{researchActivity.map((entry) => <li key={entry.id}><p className="text-sm font-semibold text-[var(--ink)]">{entry.query}</p><p className="mt-1 text-xs text-[var(--ink-soft)]">{entry.type} · {entry.status}{entry.confidence ? ` · ${entry.confidence}` : ""}</p></li>)}</ol> : <p className="mt-3 text-sm leading-relaxed text-[var(--ink-soft)]">Research activity appears after a returned request.</p>}</aside></div></div></details>
      </main>

      <footer className="mx-auto mt-10 flex max-w-6xl flex-col justify-between gap-2 border-t border-[var(--rule)] px-4 py-5 text-[11px] text-[var(--ink-faint)] sm:flex-row sm:px-6 lg:px-8"><p>QuantAI separates sourced research evidence from optional interpretation.</p><p className="font-mono">{connection === "ready" ? connectionNote : "Research endpoint requires attention"}</p></footer>

      {settingsOpen ? <div className="fixed inset-0 z-50 grid place-items-center bg-black/30 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Research endpoint settings"><div className="w-full max-w-md bg-[var(--surface)] p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div><p className="ledger-label">Connection settings</p><h2 className="mt-1 font-serif text-2xl tracking-[-0.04em] text-[var(--ink)]">Research Desk endpoint</h2></div><button type="button" onClick={() => setSettingsOpen(false)} className="text-[var(--ink-faint)] hover:text-[var(--ink)]" aria-label="Close settings"><X className="size-5" /></button></div><p className="mt-3 text-sm leading-relaxed text-[var(--ink-soft)]">Production uses the same-origin <code className="research-code">/api</code> route. Local Vite development proxies this route to the local backend.</p><label className="mt-5 block"><span className="ledger-label">Base URL</span><input value={endpointDraft} onChange={(event) => setEndpointDraft(event.target.value)} className="research-input mt-2" /></label><div className="mt-6 flex justify-end gap-2"><button type="button" onClick={() => setSettingsOpen(false)} className="research-text-button">Cancel</button><button type="button" onClick={saveEndpoint} className="research-primary-button">Save and test</button></div></div></div> : null}
    </div>
  );
}
