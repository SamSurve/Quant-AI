/**
 * Analyst's Ledger visual contract: an editorial research desk with a reading rail, evidence column, and AI brief.
 * Live values originate from the unchanged AgentOS finance agent; unavailable data is never fabricated.
 */

import { useEffect, useState } from "react";
import { nanoid } from "nanoid";
import { AlertCircle, ArrowUpRight, ChevronRight, CircleHelp, LoaderCircle, Menu, Network, Radio, RefreshCw, Search, Settings2, SlidersHorizontal, WifiOff, X } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { ChatPanel, type ChatMessage } from "@/components/ChatPanel";
import { ComparisonPanel } from "@/components/ComparisonPanel";
import { MarketChart } from "@/components/MarketChart";
import { MetricCard } from "@/components/MetricCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { fetchAgentInfo, getAgentosUrl, runFinanceAgent, saveAgentosUrl } from "@/lib/agentos";
import { emptyMarketBrief, marketBriefFromResearch, parseMarketBrief, type MarketBrief } from "@/lib/market";
import { runCompanyComparison, runTypedResearch, type TypedResearchResponse } from "@/lib/research";

const starterTickers = ["AAPL", "MSFT", "NVDA", "TSLA"];

type Connection = "checking" | "ready" | "offline";
type Workspace = "market" | "deep" | "compare";
type ResearchActivity = { id: string; type: string; query: string; status: string; confidence?: string };

function isTemporaryAiUnavailability(message: string) {
  return /ai analysis is temporarily unavailable|groq service is busy|provider unavailable/i.test(message);
}

function recoveryMessage(message: string) {
  if (/ambiguous/i.test(message)) return "More than one company matched this request. Try a ticker or a more specific company name.";
  if (/not found|unknown|invalid/i.test(message)) return "No verified company record was found. Check the spelling or search by ticker.";
  if (isTemporaryAiUnavailability(message)) return "The available research record remains useful, but the optional AI interpretation is temporarily unavailable. Try again shortly.";
  if (/news/i.test(message)) return "The research record is available with a missing news source. Other sourced evidence remains visible.";
  return "The request could not complete. Check the research endpoint, then try again.";
}

export default function Home() {
  const [ticker, setTicker] = useState("AAPL");
  const [query, setQuery] = useState("AAPL");
  const [brief, setBrief] = useState<MarketBrief>(emptyMarketBrief);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [connection, setConnection] = useState<Connection>("checking");
  const [connectionNote, setConnectionNote] = useState("Checking AgentOS endpoint…");
  const [isResearching, setIsResearching] = useState(false);
  const [activeResearchMode, setActiveResearchMode] = useState<"market_intelligence" | "company_deep_analysis">("market_intelligence");
  const [workspace, setWorkspace] = useState<Workspace>("market");
  const [companyA, setCompanyA] = useState("AAPL");
  const [companyB, setCompanyB] = useState("MSFT");
  const [comparison, setComparison] = useState<NonNullable<TypedResearchResponse["company_comparison"]> | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isChatting, setIsChatting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [endpointDraft, setEndpointDraft] = useState(getAgentosUrl());
  const [menuOpen, setMenuOpen] = useState(false);
  const [riskNoticeVisible, setRiskNoticeVisible] = useState(true);
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
      setConnectionNote(connectionError instanceof Error ? connectionError.message : "AgentOS is unavailable.");
    }
  }

  useEffect(() => {
    void verifyConnection();
  }, []);

  function recordResearch(type: string, queryLabel: string, status: string, confidence?: string) {
    setResearchActivity((current) => [{ id: nanoid(), type, query: queryLabel, status, confidence }, ...current].slice(0, 6));
  }

  async function requestResearch(symbol = query, mode: "market_intelligence" | "company_deep_analysis" = activeResearchMode) {
    const normalized = symbol.trim();
    if (!normalized || isResearching) return;
    setQuery(normalized);
    setTicker(normalized.toUpperCase());
    setActiveResearchMode(mode);
    setWorkspace(mode === "company_deep_analysis" ? "deep" : "market");
    setComparison(null);
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
      const message = researchError instanceof Error ? researchError.message : "Could not generate the market brief.";
      setError(message);
      setConnection(isTemporaryAiUnavailability(message) ? "ready" : "offline");
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
    setWorkspace("compare");
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
      setConnection(isTemporaryAiUnavailability(message) ? "ready" : "offline");
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

  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <header className="command-bar sticky top-0 z-40 border-b border-[var(--rule)] backdrop-blur-md">
        <div className="mx-auto flex h-[72px] max-w-[1536px] items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary research workflows">
            {[{ id: "market", label: "Market intelligence", value: "market" as Workspace }, { id: "market", label: "Deep analysis", value: "deep" as Workspace }, { id: "compare-controls", label: "Compare", value: "compare" as Workspace }].map((item) => <button key={item.label} type="button" aria-current={workspace === item.value ? "page" : undefined} onClick={() => { setWorkspace(item.value); if (item.value === "deep") setActiveResearchMode("company_deep_analysis"); document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth", block: "start" }); }} className={`border-b px-3 py-2 text-xs font-semibold transition-colors ${workspace === item.value ? "border-[var(--research-indigo)] text-[var(--research-indigo)]" : "border-transparent text-[var(--ink-soft)] hover:text-[var(--ink)]"}`}>{item.label}</button>)}
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button type="button" onClick={() => void verifyConnection()} className="hidden items-center gap-2 border border-[var(--rule)] bg-[var(--surface-raised)] px-3 py-2 text-xs font-semibold text-[var(--ink-soft)] transition-colors hover:border-[var(--research-indigo)] hover:text-[var(--research-indigo)] sm:flex" title="Check research endpoint">
              {connection === "checking" ? <LoaderCircle className="size-3.5 animate-spin" /> : connection === "ready" ? <Network className="size-3.5 text-[var(--provenance)]" /> : <WifiOff className="size-3.5 text-[var(--negative)]" />}
              <span>{connection === "ready" ? "Connected" : connection === "checking" ? "Checking" : "Offline"}</span>
            </button>
            <button type="button" onClick={() => setSettingsOpen(true)} className="grid size-9 place-items-center border border-[var(--rule)] bg-[var(--surface-raised)] text-[var(--ink-soft)] transition-colors hover:border-[var(--research-indigo)] hover:text-[var(--research-indigo)]" aria-label="Research endpoint settings">
              <Settings2 className="size-4" />
            </button>
            <button type="button" onClick={() => setMenuOpen((open) => !open)} className="grid size-9 place-items-center border border-[var(--rule)] bg-[var(--surface-raised)] text-[var(--ink-soft)] lg:hidden" aria-label="Toggle research navigation" aria-expanded={menuOpen}><Menu className="size-4" /></button>
          </div>
        </div>
        {menuOpen && <nav className="border-t border-[var(--rule)] bg-[var(--surface)] px-4 py-2 lg:hidden" aria-label="Mobile research workflows">{[{ id: "market", label: "Market intelligence", value: "market" as Workspace }, { id: "market", label: "Deep analysis", value: "deep" as Workspace }, { id: "compare-controls", label: "Compare", value: "compare" as Workspace }].map((item) => <button key={item.label} type="button" aria-current={workspace === item.value ? "page" : undefined} onClick={() => { setWorkspace(item.value); if (item.value === "deep") setActiveResearchMode("company_deep_analysis"); setMenuOpen(false); document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth", block: "start" }); }} className={`block w-full px-2 py-3 text-left text-sm font-semibold ${workspace === item.value ? "text-[var(--research-indigo)]" : "text-[var(--ink-soft)]"}`}>{item.label}</button>)}</nav>}
      </header>

      <main className="mx-auto max-w-[1536px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
        {error && (
          <div className="mb-5 flex items-start gap-3 border border-[color-mix(in_oklab,var(--negative)_45%,var(--rule))] bg-[color-mix(in_oklab,var(--negative)_8%,var(--surface))] px-4 py-3 text-sm text-[var(--ink)]" role="alert">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-[var(--negative)]" />
            <div className="min-w-0 flex-1"><strong className="font-semibold">Research request needs attention.</strong><p className="mt-1 text-[var(--ink-soft)]">{recoveryMessage(error)}</p></div>
            <button type="button" onClick={() => setError(null)} className="text-[var(--ink-faint)] hover:text-[var(--ink)]" aria-label="Dismiss message"><X className="size-4" /></button>
          </div>
        )}

        <div className="grid gap-5 xl:grid-cols-[180px_minmax(0,1fr)_390px] xl:gap-7">
          <aside className="hidden xl:block">
            <div className="sticky top-5 space-y-7">
              <div>
                <p className="ledger-label">Desk index</p>
                <nav className="mt-3 space-y-1 border-l border-[var(--rule)] text-sm" aria-label="Research sections">
	                  <a href="#market" className="group -ml-px flex items-center gap-3 border-l-2 border-[var(--provenance)] py-2 pl-3 font-semibold text-[var(--ink)]"><span className="size-1.5 rounded-full bg-[var(--provenance)]" />Market view</a>
	                  <a href="#comparison" className="group flex items-center gap-3 py-2 pl-3 text-[var(--ink-soft)] transition-colors hover:text-[var(--research-indigo)]"><span className="size-1.5 rounded-full bg-[var(--rule-strong)] group-hover:bg-[var(--research-indigo)]" />Comparison</a>
	                  <a href="#signal" className="group flex items-center gap-3 py-2 pl-3 text-[var(--ink-soft)] transition-colors hover:text-[var(--research-indigo)]"><span className="size-1.5 rounded-full bg-[var(--rule-strong)] group-hover:bg-[var(--research-indigo)]" />Market signal</a>
	                  <a href="#analysis" className="group flex items-center gap-3 py-2 pl-3 text-[var(--ink-soft)] transition-colors hover:text-[var(--research-indigo)]"><span className="size-1.5 rounded-full bg-[var(--rule-strong)] group-hover:bg-[var(--research-indigo)]" />Research brief</a>
	                  <a href="#news" className="group flex items-center gap-3 py-2 pl-3 text-[var(--ink-soft)] transition-colors hover:text-[var(--research-indigo)]"><span className="size-1.5 rounded-full bg-[var(--rule-strong)] group-hover:bg-[var(--research-indigo)]" />News flow</a>
	                  <a href="#sources" className="group flex items-center gap-3 py-2 pl-3 text-[var(--ink-soft)] transition-colors hover:text-[var(--research-indigo)]"><span className="size-1.5 rounded-full bg-[var(--rule-strong)] group-hover:bg-[var(--research-indigo)]" />Sources</a>
                </nav>
              </div>
              <div className="border-t border-[var(--rule)] pt-5">
                <p className="ledger-label">Data protocol</p>
                <p className="mt-2 text-xs leading-relaxed text-[var(--ink-soft)]">Source-returned evidence leads every record. Empty fields stay empty until sourced.</p>
              </div>
              <div className="border border-[var(--rule)] bg-[var(--surface-raised)] p-4">
                <p className="ledger-label">Research standard</p>
                <p className="mt-7 font-serif text-lg leading-tight text-[var(--ink)]">Evidence before conviction.</p>
                <ArrowUpRight className="mt-4 size-4 text-[var(--research-indigo)]" />
              </div>
            </div>
          </aside>

          <div className="min-w-0 space-y-5 sm:space-y-6">
            <section id="market" className="ledger-panel overflow-hidden">
              <div className="p-5 sm:p-7">
                <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="ledger-aperture grid size-4 place-items-center"><span className="size-1.5 rounded-full bg-[#0e8f83]" /></span>
                      <p className="ledger-label">Live research canvas</p>
                    </div>
                    <div className="mt-4 flex items-end gap-3">
                      <div><h1 className="font-serif text-5xl tracking-[-0.06em] text-[var(--ink)] sm:text-6xl">{ticker}</h1>{brief.companyName !== "—" && <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--ink-soft)]">{brief.companyName}</p>}</div>
                      <span className="mb-1.5 border-l border-[var(--rule-strong)] pl-3 text-sm text-[var(--ink-soft)]">{brief.sector !== "—" ? `${brief.sector}${brief.industry !== "—" ? ` · ${brief.industry}` : ""}` : "Financial intelligence for deeper research."}</span>
                    </div>
                  </div>
                  <div className="border-l border-[var(--rule)] pl-4 sm:text-right sm:border-l-0 sm:border-r sm:pr-4 sm:pl-0">
                    <p className="ledger-label">Current price</p>
                    <p className="mt-1 font-mono text-2xl font-semibold tracking-[-0.06em] text-[var(--ink)] tabular-nums sm:text-3xl">{isResearching ? <span className="inline-block h-7 w-24 align-middle shimmer-line" /> : brief.quote}</p>
                    <p className="mt-1 text-xs font-medium text-[var(--positive)]">{isResearching ? (isComparing ? "Preparing comparison evidence" : activeResearchMode === "company_deep_analysis" ? "Validating company evidence" : "Researching market evidence") : brief.change}</p>
                  </div>
                </div>

                <form onSubmit={(event) => { event.preventDefault(); void requestResearch(); }} className="mt-7 flex flex-col gap-2 sm:flex-row">
                  <label className="sr-only" htmlFor="company-search">Search a stock or company</label>
                  <div className="flex min-w-0 flex-1 items-center gap-3 border border-[var(--rule-strong)] bg-[var(--surface)] px-3.5 py-3 transition-colors focus-within:border-[var(--research-indigo)]">
                    <Search className="size-4 shrink-0 text-[var(--research-indigo)]" />
                    <input id="company-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a company or ticker" className="min-w-0 flex-1 bg-transparent text-sm font-medium text-[var(--ink)] outline-none placeholder:font-normal placeholder:text-[var(--ink-faint)]" />
                    <kbd className="hidden border border-[var(--rule)] bg-[var(--surface-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--ink-faint)] sm:inline">↵</kbd>
                  </div>
                  <button type="submit" disabled={isResearching || !query.trim()} className="flex h-[48px] items-center justify-center gap-2 bg-[var(--research-indigo)] px-5 text-sm font-semibold text-[var(--primary-foreground)] transition-all duration-150 hover:brightness-110 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50">
                    {isResearching ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
                    {isResearching ? "Researching" : "Research market"}
                  </button>
                  <button type="button" onClick={() => void requestResearch(query, "company_deep_analysis")} disabled={isResearching || !query.trim()} className={`flex h-[48px] items-center justify-center gap-2 border px-4 text-sm font-semibold transition-all duration-150 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-45 ${activeResearchMode === "company_deep_analysis" ? "border-[var(--research-indigo)] bg-[var(--research-indigo-soft)] text-[var(--research-indigo)]" : "border-[var(--rule-strong)] bg-[var(--surface)] text-[var(--ink-soft)] hover:border-[var(--research-indigo)] hover:text-[var(--research-indigo)]"}`}>
                    <ChevronRight className="size-4" /> Deep analysis
                  </button>
                </form>
	                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="ledger-label mr-1">Quick research</span>
	                  {starterTickers.map((symbol) => (
                    <button key={symbol} type="button" onClick={() => void requestResearch(symbol)} disabled={isResearching} className="border-b border-[var(--rule-strong)] pb-0.5 font-mono text-[11px] font-medium text-[var(--ink-soft)] transition-colors hover:border-[var(--research-indigo)] hover:text-[var(--research-indigo)] disabled:opacity-50">{symbol}</button>
	                  ))}
	                </div>
                <form id="compare-controls" onSubmit={(event) => { event.preventDefault(); void requestComparison(); }} className="mt-4 grid gap-2 border-t border-[var(--rule)] pt-4 sm:grid-cols-[1fr_1fr_auto]">
                  <div><label className="ledger-label" htmlFor="company-a">Company A</label><input id="company-a" value={companyA} onChange={(event) => setCompanyA(event.target.value)} placeholder="AAPL" className="mt-1.5 w-full border border-[var(--rule-strong)] bg-[var(--surface)] px-3 py-2.5 font-mono text-sm font-medium text-[var(--ink)] outline-none transition-colors focus:border-[var(--research-indigo)]" /></div>
                  <div><label className="ledger-label" htmlFor="company-b">Company B</label><input id="company-b" value={companyB} onChange={(event) => setCompanyB(event.target.value)} placeholder="MSFT" className="mt-1.5 w-full border border-[var(--rule-strong)] bg-[var(--surface)] px-3 py-2.5 font-mono text-sm font-medium text-[var(--ink)] outline-none transition-colors focus:border-[var(--research-indigo)]" /></div>
                  <button type="submit" disabled={isResearching || !companyA.trim() || !companyB.trim()} className="mt-[22px] flex h-[42px] items-center justify-center gap-2 border border-[var(--research-indigo)] bg-[var(--research-indigo-soft)] px-4 text-sm font-semibold text-[var(--research-indigo)] transition-all duration-150 hover:bg-[var(--research-indigo)] hover:text-[var(--primary-foreground)] active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-45"><ChevronRight className="size-4" />Compare</button>
	                </form>
	                <div className="mt-5 grid border-t border-[#d4ccbf] pt-3 text-[9px] font-bold uppercase tracking-[0.12em] text-[#6f7873] sm:grid-cols-3"><p><span className="mr-1 text-[#0e8f83]">▾</span> Source lane · Typed research</p><p className="mt-1 sm:mt-0"><span className="mr-1 text-[#0e8f83]">▾</span> Evidence · {brief.analysis ? "interpreted" : "deterministic only"}</p><p className="mt-1 sm:mt-0 sm:text-right"><span className="mr-1 text-[#0e8f83]">▾</span> {brief.exchange !== "—" ? `Exchange · ${brief.exchange}` : `Status · ${isResearching ? "researching" : "ready"}`}</p></div>
              </div>
            </section>

            <section className="ledger-panel overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#e2dbd0] px-5 py-4 sm:px-6">
                <div>
                  <p className="ledger-label">Market snapshot</p>
                  <h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">The evidence, at a glance</h2>
                </div>
                <button type="button" onClick={() => void requestResearch(ticker)} disabled={isResearching || isOffline} className="flex items-center gap-2 border border-[#cfc7bb] bg-[#fffdf9] px-3 py-2 text-xs font-semibold text-[#52605a] transition-colors hover:border-[#0e8f83] hover:text-[#0e8f83] disabled:cursor-not-allowed disabled:opacity-45">
                  <RefreshCw className={`size-3.5 ${isResearching ? "animate-spin" : ""}`} /> Refresh brief
                </button>
              </div>
              <div className="grid grid-cols-2 gap-px bg-[#e4ddd2] sm:grid-cols-3 lg:grid-cols-6">
                {brief.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
              </div>
            </section>

            <section className="ledger-panel overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 sm:px-6">
                <div>
                  <p className="ledger-label">Price history</p>
                  <h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">Price movement</h2>
                </div>
                <span className="source-chip ledger-aperture">Agent supplied</span>
              </div>
              <MarketChart data={brief.chart} />
            </section>

            <section id="signal" className="ledger-panel overflow-hidden">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e2dbd0] px-5 py-4 sm:px-6">
                <div className="flex items-start gap-2"><span className="ledger-aperture mt-0.5 grid size-4 place-items-center"><span className="size-1.5 bg-[#0e8f83]" /></span><div><p className="ledger-label">Market signal</p><h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">Deterministic observation layer</h2></div></div>
                {brief.signal && <div className={`border px-3 py-2 font-mono text-xs font-bold ${brief.signal.label === "BULLISH" ? "border-[#9fcfc6] bg-[#edf8f5] text-[#0e756b]" : brief.signal.label === "BEARISH" ? "border-[#e7c9c2] bg-[#fff5f2] text-[#9b4233]" : "border-[#d9d1c5] bg-[#f8f5ef] text-[#5b6762]"}`}>{brief.signal.label}</div>}
              </div>
              {brief.signal ? <div className="grid gap-5 p-5 sm:grid-cols-[170px_1fr] sm:p-6"><div className="grid grid-cols-2 gap-2"><div className="border border-[#e2dbd0] bg-[#fffdf9] p-3"><p className="ledger-label">Score</p><p className="mt-2 font-mono text-xl font-semibold text-[#1e2928]">{brief.signal.score}</p></div><div className="border border-[#e2dbd0] bg-[#fffdf9] p-3"><p className="ledger-label">Confidence</p><p className="mt-2 font-mono text-xl font-semibold text-[#1e2928]">{brief.signal.confidence}</p></div></div><div><p className="text-sm leading-relaxed text-[#4d5753]">{brief.signal.explanation}</p><ul className="mt-3 space-y-2 border-l border-[#b9ded7] pl-4 text-xs leading-relaxed text-[#5f6864]">{brief.signal.factors.map((factor) => <li key={factor}>{factor}</li>)}</ul><p className="mt-4 text-[10px] leading-relaxed text-[#7a827e]">{brief.signal.methodology}</p></div></div> : <p className="p-5 text-sm text-[#6e7772]">Signal unavailable until sufficient deterministic history is sourced.</p>}
            </section>

            <div id="analysis"><AnalysisPanel analysis={brief.analysis} ticker={ticker} isLoading={isResearching} /></div>

	            {brief.deepAnalysis && (
              <section id="deep-analysis" className="ledger-panel overflow-hidden">
                <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e2dbd0] px-5 py-4 sm:px-6"><div className="flex items-start gap-2"><span className="ledger-aperture mt-0.5 grid size-4 place-items-center"><span className="size-1.5 bg-[#0e8f83]" /></span><div><p className="ledger-label">Company deep analysis</p><h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">Evidence before interpretation</h2></div></div><span className="source-chip ledger-aperture">Typed report</span></div>
                <div className="space-y-0 divide-y divide-[#e5ded3]">
                  <div className="p-5 sm:p-6"><p className="ledger-label">Company snapshot · factual</p><div className="mt-4 grid gap-px bg-[#e5ded3] sm:grid-cols-2 lg:grid-cols-3">{brief.deepAnalysis.overview.map((item) => <div key={item.label} className="bg-[#fffdf9] px-4 py-3"><p className="ledger-label">{item.label}</p><p className="mt-1 break-words text-sm font-medium text-[#35423e]">{item.value}</p></div>)}</div></div>
                  <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6"><div><p className="ledger-label">Financial health · factual</p><div className="mt-4 grid grid-cols-2 gap-px bg-[#e5ded3]">{brief.deepAnalysis.financials.map((metric) => <MetricCard key={metric.label} metric={metric} />)}</div></div><div><p className="ledger-label">Financial health · analyst interpretation</p><p className="mt-4 text-sm leading-relaxed text-[#525c57]">{brief.deepAnalysis.interpretation?.financialHealth || "AI interpretation unavailable. Deterministic financial values remain above when sourced."}</p></div></div>
                  <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6"><div><p className="ledger-label">Business model · analyst interpretation</p><p className="mt-3 text-sm leading-relaxed text-[#525c57]">{brief.deepAnalysis.interpretation?.businessModel || "AI interpretation unavailable. Refer to the sourced company profile and news records."}</p><p className="mt-5 ledger-label">Governance · factual</p><p className="mt-2 text-sm font-semibold text-[#36433f]">{brief.deepAnalysis.governance.ceo}</p>{brief.deepAnalysis.governance.leadership.length ? <ul className="mt-2 space-y-1 text-xs text-[#68716d]">{brief.deepAnalysis.governance.leadership.map((person) => <li key={person}>{person}</li>)}</ul> : null}</div><div><p className="ledger-label">Growth & catalysts · analyst interpretation</p><ul className="mt-3 space-y-2 border-l border-[#b9ded7] pl-4 text-sm leading-relaxed text-[#525c57]">{(brief.deepAnalysis.interpretation?.growthDrivers || []).map((item) => <li key={item}>{item}</li>)}{(brief.deepAnalysis.interpretation?.catalysts || []).map((item) => <li key={item}>{item}</li>)}</ul>{!(brief.deepAnalysis.interpretation?.growthDrivers.length || brief.deepAnalysis.interpretation?.catalysts.length) ? <p className="mt-3 text-sm text-[#6f7873]">Insufficient verified data.</p> : null}</div></div>
                  <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6"><div><p className="ledger-label">Competitive position</p><p className="mt-3 text-sm leading-relaxed text-[#525c57]">{brief.deepAnalysis.interpretation?.competitivePosition || "AI interpretation unavailable."}</p><p className="mt-3 text-xs leading-relaxed text-[#77807b]">{brief.deepAnalysis.competitors.note}</p></div><div><p className="ledger-label">Key risks · analyst interpretation</p><ul className="mt-3 space-y-2 border-l border-[#e3c0b9] pl-4 text-sm leading-relaxed text-[#6a4a43]">{(brief.deepAnalysis.interpretation?.risks || []).map((item) => <li key={item}>{item}</li>)}</ul>{!brief.deepAnalysis.interpretation?.risks.length ? <p className="mt-3 text-sm text-[#6f7873]">Insufficient verified data.</p> : null}</div></div>
                  <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6"><div><p className="ledger-label">Valuation · analyst interpretation</p><p className="mt-3 font-mono text-sm font-bold text-[#0e756b]">{brief.deepAnalysis.interpretation?.valuation.classification || "INSUFFICIENT_DATA"}</p><p className="mt-2 text-sm leading-relaxed text-[#525c57]">{brief.deepAnalysis.interpretation?.valuation.rationale || "Insufficient verified data."}</p></div><div><p className="ledger-label">Executive assessment · analyst interpretation</p><p className="mt-3 text-sm leading-relaxed text-[#525c57]">{brief.deepAnalysis.interpretation?.assessment || "AI interpretation unavailable. Review the sourced facts and partial-data warnings."}</p><p className="mt-3 text-[10px] uppercase tracking-[0.1em] text-[#71807a]">Confidence · {brief.deepAnalysis.interpretation?.confidence || "Unavailable"}</p></div></div>
                </div>
	              </section>
	            )}

            <ComparisonPanel report={comparison} isLoading={isComparing} />

	            <section id="news" className="ledger-panel p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="ledger-label">Recent news</p>
                  <h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">What is moving the conversation</h2>
                </div>
                <SlidersHorizontal className="mt-1 size-4 text-[#0e8f83]" />
              </div>
              {isResearching ? (
                <div className="mt-5 space-y-3"><div className="shimmer-line h-12 w-full" /><div className="shimmer-line h-12 w-[92%]" /><div className="shimmer-line h-12 w-[83%]" /></div>
              ) : brief.news.length ? (
                <ol className="mt-5 divide-y divide-[#e5ded3] border-t border-[#e5ded3]">
                  {brief.news.map((item, index) => <li key={`${item}-${index}`} className="flex gap-4 py-4"><span className="font-mono text-xs text-[#0e8f83]">0{index + 1}</span><p className="text-sm leading-relaxed text-[#3e4845]">{item}</p></li>)}
                </ol>
              ) : (
                <div className="mt-5 border-y border-dashed border-[#ddd5c9] py-0"><div className="grid grid-cols-[auto_1fr] gap-x-4 border-b border-[#eee7dd] py-3"><span className="font-mono text-[10px] text-[#0e8f83]">01</span><p className="text-xs leading-relaxed text-[#737b77]">Source lane reserved for tool-returned news items.</p></div><div className="grid grid-cols-[auto_1fr] gap-x-4 border-b border-[#eee7dd] py-3"><span className="font-mono text-[10px] text-[#0e8f83]">02</span><p className="text-xs leading-relaxed text-[#737b77]">Awaiting a current search result from the finance agent.</p></div><div className="grid grid-cols-[auto_1fr] gap-x-4 py-3"><span className="font-mono text-[10px] text-[#0e8f83]">03</span><p className="text-xs leading-relaxed text-[#737b77]">No unsourced news is shown in this briefing.</p></div></div>
              )}
            </section>

            <section className="ledger-panel overflow-hidden">
              <div className="border-b border-[#e2dbd0] px-5 py-4 sm:px-6"><p className="ledger-label">Event radar</p><h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">Reliable calendar observations</h2></div>
              {brief.events.length ? <ol className="divide-y divide-[#e7dfd4]">{brief.events.map((event, index) => <li key={`${event.title}-${event.date}-${index}`} className="grid gap-2 px-5 py-4 sm:grid-cols-[110px_1fr_auto] sm:items-center sm:px-6"><span className="font-mono text-xs text-[#0e8f83]">{event.date}</span><div><p className="text-sm font-semibold text-[#33403c]">{event.title}</p><p className="mt-1 text-xs text-[#717a75]">{event.source}</p></div><span className="ledger-label text-[#6c756f]">{event.importance}</span></li>)}</ol> : <p className="px-5 py-5 text-sm text-[#6e7772]">No reliable event date was returned for this request.</p>}
            </section>

            <section id="sources" className="ledger-panel overflow-hidden">
              <div className="flex items-start gap-2 border-b border-[#e2dbd0] px-5 py-4 sm:px-6"><span className="ledger-aperture mt-0.5 grid size-4 place-items-center"><span className="size-1.5 bg-[#0e8f83]" /></span><div><p className="ledger-label">Sources & freshness</p><h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">Evidence provenance</h2></div></div>
              <div className="grid gap-px bg-[#e7dfd4] sm:grid-cols-2">{brief.freshness.map((item) => <div key={item.label} className="bg-[#fffdf9] px-5 py-3"><p className="ledger-label">{item.label}</p><p className="mt-1 text-xs font-semibold uppercase tracking-[0.08em] text-[#0e8f83]">{item.state} · <span className="normal-case tracking-normal text-[#66706b]">{item.asOf}</span></p></div>)}</div>
              {brief.sources.length ? <ul className="divide-y divide-[#e7dfd4]">{brief.sources.map((source, index) => <li key={`${source.source}-${source.dataType}-${index}`} className="flex items-start justify-between gap-4 px-5 py-3 text-xs sm:px-6"><div><p className="font-semibold text-[#49544f]">{source.source}</p><p className="mt-1 text-[#7a827e]">{source.dataType} · {source.retrievedAt}</p></div>{source.url ? <a href={source.url} target="_blank" rel="noreferrer" className="shrink-0 text-[#0e8f83] hover:underline">Source</a> : null}</li>)}</ul> : null}
              {brief.warnings.length ? <div className="border-t border-[#e8c8c1] bg-[#fff7f4] px-5 py-4 text-xs text-[#8b493d] sm:px-6"><p className="font-semibold uppercase tracking-[0.1em]">Partial-data warnings</p><ul className="mt-2 space-y-1">{brief.warnings.map((warning) => <li key={`${warning.category}-${warning.message}`}><span className="font-mono">{warning.category}</span> · {warning.message}</li>)}</ul></div> : null}
            </section>
          </div>

          <div className="min-w-0 space-y-5 xl:sticky xl:top-24 xl:self-start">
            <section className="ledger-panel overflow-hidden" aria-label="Analyst’s Ledger research activity">
              <div className="border-b border-[var(--rule)] px-5 py-4"><p className="ledger-label">Analyst’s Ledger</p><h2 className="mt-1 font-serif text-xl tracking-[-0.035em] text-[var(--ink)]">Research activity</h2></div>
              {researchActivity.length ? <ol className="divide-y divide-[var(--rule)]">{researchActivity.map((entry) => <li key={entry.id} className="grid grid-cols-[1fr_auto] gap-3 px-5 py-3"><div><p className="text-xs font-semibold text-[var(--ink)]">{entry.query}</p><p className="mt-1 ledger-label">{entry.type}</p></div><div className="text-right"><p className="font-mono text-[10px] uppercase text-[var(--provenance)]">{entry.status}</p>{entry.confidence ? <p className="mt-1 text-[10px] text-[var(--ink-faint)]">{entry.confidence}</p> : null}</div></li>)}</ol> : <p className="px-5 py-5 text-sm leading-relaxed text-[var(--ink-soft)]">Completed research requests appear here with their returned status and available confidence.</p>}
            </section>
            <ChatPanel messages={messages} isLoading={isChatting || isResearching} disabled={isOffline} onSend={sendChat} />
          </div>
        </div>
      </main>

      <footer className="mx-auto mt-4 flex max-w-[1580px] flex-col justify-between gap-2 border-t border-[#ddd6cb] px-4 py-5 text-[11px] text-[#78817c] sm:flex-row sm:px-6 lg:px-8">
        <p>Dashboard interface only. Agent logic runs through QuantAI with AgentOS, YFinance, and web/news search tools.</p>
        <p className="font-mono">{connection === "ready" ? connectionNote : "AgentOS endpoint requires attention"}</p>
      </footer>

      {riskNoticeVisible && <aside className="fixed bottom-4 right-4 z-30 max-w-[290px] border border-[var(--rule-strong)] bg-[var(--surface)] px-3 py-2.5 text-xs leading-relaxed text-[var(--ink-soft)] shadow-[0_10px_24px_rgba(0,0,0,.12)]" role="note"><div className="flex gap-2"><AlertCircle className="mt-0.5 size-3.5 shrink-0 text-[var(--research-indigo)]" aria-hidden="true" /><p>Markets involve risk. Continue researching and analyzing before making decisions.</p><button type="button" onClick={() => setRiskNoticeVisible(false)} className="-mt-0.5 text-[var(--ink-faint)] hover:text-[var(--ink)]" aria-label="Dismiss market-risk reminder"><X className="size-3.5" /></button></div></aside>}

      {settingsOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#1c2726]/35 p-4 backdrop-blur-[2px]" role="dialog" aria-modal="true" aria-label="AgentOS connection settings">
          <div className="w-full max-w-md border border-[#d6cec2] bg-[#fffdf9] p-5 shadow-[0_24px_60px_rgba(18,29,28,.25)]">
            <div className="flex items-start justify-between gap-4"><div><p className="ledger-label">Connection settings</p><h2 className="mt-1 font-serif text-2xl tracking-[-0.04em]">AgentOS endpoint</h2></div><button type="button" onClick={() => setSettingsOpen(false)} className="text-[#68716d] hover:text-[#1e2928]" aria-label="Close settings"><X className="size-5" /></button></div>
            <p className="mt-3 text-sm leading-relaxed text-[#69716e]">This frontend uses the same-origin <code className="bg-[#f1ede5] px-1 font-mono text-xs">/api</code> route in production, keeping the provider-aware QuantAI AgentOS function behind the deployed application. Local Vite development proxies that route to <code className="bg-[#f1ede5] px-1 font-mono text-xs">http://127.0.0.1:7777</code>. For a deliberately separate AgentOS service, enter its public base URL here.</p>
            <label className="mt-5 block"><span className="ledger-label">Base URL</span><input value={endpointDraft} onChange={(event) => setEndpointDraft(event.target.value)} className="mt-2 w-full border border-[#cfc7bb] bg-[#fffefb] px-3 py-3 font-mono text-sm text-[#283230] outline-none focus:border-[#0e8f83] focus:ring-2 focus:ring-[#0e8f83]/10" /></label>
            <div className="mt-5 flex justify-end gap-2"><button type="button" onClick={() => setSettingsOpen(false)} className="px-4 py-2.5 text-sm font-semibold text-[#66706b] hover:text-[#1e2928]">Cancel</button><button type="button" onClick={saveEndpoint} className="bg-[#1e2928] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#0e8f83]">Save & test</button></div>
          </div>
        </div>
      )}
    </div>
  );
}
