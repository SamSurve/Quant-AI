/**
 * Analyst's Ledger visual contract: an editorial research desk with a reading rail, evidence column, and AI brief.
 * Live values originate from the unchanged AgentOS finance agent; unavailable data is never fabricated.
 */

import { useEffect, useState } from "react";
import { AlertCircle, ArrowUpRight, ChevronRight, CircleHelp, LoaderCircle, Radio, RefreshCw, Search, Settings2, SlidersHorizontal, WifiOff, X } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { ChatPanel, type ChatMessage } from "@/components/ChatPanel";
import { MarketChart } from "@/components/MarketChart";
import { MetricCard } from "@/components/MetricCard";
import { fetchAgentInfo, getAgentosUrl, runFinanceAgent, saveAgentosUrl } from "@/lib/agentos";
import { emptyMarketBrief, parseMarketBrief, type MarketBrief } from "@/lib/market";

const heroImage = "/assets/analysts-ledger-hero.jpg";
const marketImage = "/assets/analysts-ledger-market.jpg";
const starterTickers = ["AAPL", "MSFT", "NVDA", "TSLA"];

type Connection = "checking" | "ready" | "offline";

function isTemporaryAiUnavailability(message: string) {
  return /ai analysis is temporarily unavailable|groq service is busy|provider unavailable/i.test(message);
}

function makeResearchPrompt(ticker: string) {
  return `Build a current financial research brief for ${ticker}. Use the available stock-price and web/news tools where appropriate. Return markdown with these exact sections: ## Market Snapshot, ## Recent News, and ## Analysis. In Market Snapshot, use a two-column markdown table with Current Price, Day Change, Market Cap, P/E Ratio, 52-Week High, 52-Week Low, Volume, and Dividend Yield whenever the source provides them. Include a short dated price-history table only if you can source it. Mark unavailable fields as unavailable; do not infer or fabricate data.`;
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
  const [isChatting, setIsChatting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [endpointDraft, setEndpointDraft] = useState(getAgentosUrl());

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

  async function requestResearch(symbol = query) {
    const normalized = symbol.trim();
    if (!normalized || isResearching) return;
    setQuery(normalized);
    setTicker(normalized.toUpperCase());
    setIsResearching(true);
    setError(null);
    try {
      const response = await runFinanceAgent({ message: makeResearchPrompt(normalized), sessionId });
      setSessionId(response.session_id || sessionId);
      const parsedBrief = parseMarketBrief(response.content || "");
      setBrief(parsedBrief);
      if (parsedBrief.ticker !== "—") setTicker(parsedBrief.ticker.toUpperCase());
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "user", content: `Create a research brief for ${normalized}.` },
        { id: response.run_id || crypto.randomUUID(), role: "agent", content: response.content || "" },
      ]);
      setConnection("ready");
    } catch (researchError) {
      const message = researchError instanceof Error ? researchError.message : "Could not generate the market brief.";
      setError(message);
      setConnection(isTemporaryAiUnavailability(message) ? "ready" : "offline");
    } finally {
      setIsResearching(false);
    }
  }

  async function sendChat(question: string) {
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const pendingId = crypto.randomUUID();
    setMessages((current) => [...current, userMessage, { id: pendingId, role: "agent", content: "", pending: true }]);
    setIsChatting(true);
    setError(null);
    try {
      const contextualQuestion = ticker ? `Current ticker context: ${ticker}.\n\n${question}` : question;
      const response = await runFinanceAgent({ message: contextualQuestion, sessionId });
      setSessionId(response.session_id || sessionId);
      setMessages((current) => current.map((item) => (item.id === pendingId ? { id: response.run_id || pendingId, role: "agent", content: response.content || "" } : item)));
      setBrief((current) => (response.content ? parseMarketBrief(response.content) : current));
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
    <div className="min-h-screen overflow-x-hidden bg-[#f7f4ee] text-[#1e2928]">
      <header className="border-b border-[#ded7cc] bg-[#fbf9f4]/90 backdrop-blur-md">
        <div className="mx-auto flex h-[72px] max-w-[1580px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <div className="hidden items-center gap-3 md:flex">
            <span className="ledger-label">Research desk</span>
            <span className="h-4 w-px bg-[#d6cec1]" />
              <span className="text-sm text-[#5d6763]">QuantAI Finance Agent</span>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => void verifyConnection()} className="hidden items-center gap-2 border border-[#d7d0c4] bg-[#fffdf9] px-3 py-2 text-xs font-semibold text-[#46504d] transition-colors hover:border-[#0e8f83] hover:text-[#0e8f83] sm:flex" title="Check AgentOS connection">
              {connection === "checking" ? <LoaderCircle className="size-3.5 animate-spin" /> : connection === "ready" ? <Radio className="size-3.5 text-[#0e8f83]" /> : <WifiOff className="size-3.5 text-[#bd4b38]" />}
              <span>{connection === "ready" ? "AgentOS live" : connection === "checking" ? "Checking" : "Connection"}</span>
            </button>
            <button type="button" onClick={() => setSettingsOpen(true)} className="grid size-9 place-items-center border border-[#d7d0c4] bg-[#fffdf9] text-[#55605b] transition-colors hover:border-[#0e8f83] hover:text-[#0e8f83]" aria-label="AgentOS connection settings">
              <Settings2 className="size-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1580px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
        {error && (
          <div className="mb-5 flex items-start gap-3 border border-[#e7c9c2] bg-[#fff5f2] px-4 py-3 text-sm text-[#873b30]" role="alert">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <div className="min-w-0 flex-1"><strong className="font-semibold">AgentOS request needs attention.</strong> <span className="break-words">{error}</span></div>
            <button type="button" onClick={() => setError(null)} className="text-[#9c5449] hover:text-[#653127]" aria-label="Dismiss error"><X className="size-4" /></button>
          </div>
        )}

        <div className="grid gap-5 xl:grid-cols-[180px_minmax(0,1fr)_390px] xl:gap-7">
          <aside className="hidden xl:block">
            <div className="sticky top-5 space-y-7">
              <div>
                <p className="ledger-label">Desk index</p>
                <nav className="mt-3 space-y-1 border-l border-[#d9d1c5] text-sm" aria-label="Research sections">
                  <a href="#market" className="group flex items-center gap-3 border-l-2 border-[#0e8f83] -ml-px py-2 pl-3 font-semibold text-[#25302e]"><span className="size-1.5 rounded-full bg-[#0e8f83]" />Market view</a>
                  <a href="#analysis" className="group flex items-center gap-3 py-2 pl-3 text-[#6b746f] transition-colors hover:text-[#0e8f83]"><span className="size-1.5 rounded-full bg-[#c9c2b6] group-hover:bg-[#0e8f83]" />Research brief</a>
                  <a href="#news" className="group flex items-center gap-3 py-2 pl-3 text-[#6b746f] transition-colors hover:text-[#0e8f83]"><span className="size-1.5 rounded-full bg-[#c9c2b6] group-hover:bg-[#0e8f83]" />News flow</a>
                </nav>
              </div>
              <div className="border-t border-[#d8d0c4] pt-5">
                <p className="ledger-label">Data protocol</p>
                <p className="mt-2 text-xs leading-relaxed text-[#717a75]">Live results are requested from the preserved AgentOS agent. Empty fields stay empty until sourced.</p>
              </div>
              <div className="relative overflow-hidden border border-[#d9d2c7] bg-[#1f2b2a] p-4 text-[#f9f5ed]">
                <img src={marketImage} alt="" className="absolute inset-0 size-full object-cover opacity-35 mix-blend-screen" />
                <div className="relative">
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#b7dcd5]">Signal / 01</p>
                  <p className="mt-7 font-serif text-lg leading-tight">Evidence before conviction.</p>
                  <ArrowUpRight className="mt-4 size-4 text-[#66d4c6]" />
                </div>
              </div>
            </div>
          </aside>

          <div className="min-w-0 space-y-5 sm:space-y-6">
            <section id="market" className="ledger-panel relative overflow-hidden">
              <img src={heroImage} alt="" className="absolute inset-0 size-full object-cover opacity-[0.34] mix-blend-multiply" />
              <div className="relative p-5 sm:p-7">
                <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="ledger-aperture grid size-4 place-items-center"><span className="size-1.5 rounded-full bg-[#0e8f83]" /></span>
                      <p className="ledger-label text-[#466863]">Live research canvas</p>
                    </div>
                    <div className="mt-4 flex items-end gap-3">
                      <div><h1 className="font-serif text-5xl tracking-[-0.06em] text-[#1e2928] sm:text-6xl">{ticker}</h1>{brief.companyName !== "—" && <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#65706b]">{brief.companyName}</p>}</div>
                      <span className="mb-1.5 border-l border-[#c9c1b5] pl-3 text-sm text-[#59635f]">{brief.sector !== "—" ? `${brief.sector}${brief.industry !== "—" ? ` · ${brief.industry}` : ""}` : "Agent-led market view"}</span>
                    </div>
                  </div>
                  <div className="border-l border-[#c6beb2] pl-4 sm:text-right sm:border-l-0 sm:border-r sm:pr-4 sm:pl-0">
                    <p className="ledger-label">Current price</p>
                    <p className="mt-1 font-mono text-2xl font-semibold tracking-[-0.06em] text-[#1e2928] tabular-nums sm:text-3xl">{isResearching ? <span className="inline-block h-7 w-24 align-middle shimmer-line" /> : brief.quote}</p>
                    <p className="mt-1 text-xs font-medium text-[#0e8f83]">{isResearching ? "Gathering tool-sourced quote…" : brief.change}</p>
                  </div>
                </div>

                <form onSubmit={(event) => { event.preventDefault(); void requestResearch(); }} className="mt-7 flex flex-col gap-2 sm:flex-row">
                  <label className="sr-only" htmlFor="company-search">Search a stock or company</label>
                  <div className="flex min-w-0 flex-1 items-center gap-3 border border-[#bdb5a9] bg-[#fffdf9]/90 px-3.5 py-3 shadow-[0_5px_10px_rgba(30,41,40,.04)] focus-within:border-[#0e8f83] focus-within:ring-2 focus-within:ring-[#0e8f83]/10">
                    <Search className="size-4 shrink-0 text-[#0e8f83]" />
                    <input id="company-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search ticker or company (e.g. AAPL)" className="min-w-0 flex-1 bg-transparent text-sm font-medium text-[#263130] outline-none placeholder:font-normal placeholder:text-[#919792]" />
                    <kbd className="hidden border border-[#ddd6cb] bg-[#f4f0ea] px-1.5 py-0.5 font-mono text-[10px] text-[#777f7b] sm:inline">↵</kbd>
                  </div>
                  <button type="submit" disabled={isResearching || !query.trim()} className="flex h-[48px] items-center justify-center gap-2 bg-[#1e2928] px-5 text-sm font-semibold text-[#fbf8f1] transition-all duration-150 hover:bg-[#0e8f83] active:scale-[0.97] disabled:cursor-not-allowed disabled:bg-[#86908c]">
                    {isResearching ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
                    {isResearching ? `Researching ${ticker}…` : "Build brief"}
                  </button>
                </form>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="ledger-label mr-1">Quick symbols</span>
                  {starterTickers.map((symbol) => (
                    <button key={symbol} type="button" onClick={() => void requestResearch(symbol)} disabled={isResearching} className="border-b border-[#c4bcb0] pb-0.5 font-mono text-[11px] font-medium text-[#58615e] transition-colors hover:border-[#0e8f83] hover:text-[#0e8f83] disabled:opacity-50">{symbol}</button>
                  ))}
                </div>
                <div className="mt-5 grid border-t border-[#d4ccbf] pt-3 text-[9px] font-bold uppercase tracking-[0.12em] text-[#6f7873] sm:grid-cols-3"><p><span className="mr-1 text-[#0e8f83]">▾</span> Source lane · AgentOS</p><p className="mt-1 sm:mt-0"><span className="mr-1 text-[#0e8f83]">▾</span> Evidence · {brief.analysis ? "received" : "awaiting request"}</p><p className="mt-1 sm:mt-0 sm:text-right"><span className="mr-1 text-[#0e8f83]">▾</span> {brief.exchange !== "—" ? `Exchange · ${brief.exchange}` : `Status · ${isResearching ? "researching" : "ready"}`}</p></div>
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

            <div id="analysis"><AnalysisPanel analysis={brief.analysis} ticker={ticker} isLoading={isResearching} /></div>

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
          </div>

          <div className="min-w-0 xl:sticky xl:top-5 xl:self-start"><ChatPanel messages={messages} isLoading={isChatting || isResearching} disabled={isOffline} onSend={sendChat} /></div>
        </div>
      </main>

      <footer className="mx-auto mt-4 flex max-w-[1580px] flex-col justify-between gap-2 border-t border-[#ddd6cb] px-4 py-5 text-[11px] text-[#78817c] sm:flex-row sm:px-6 lg:px-8">
        <p>Dashboard interface only. Agent logic runs through QuantAI with AgentOS, YFinance, and web/news search tools.</p>
        <p className="font-mono">{connection === "ready" ? connectionNote : "AgentOS endpoint requires attention"}</p>
      </footer>

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
