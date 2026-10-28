/**
 * Dedicated Company Comparison workflow.
 * Uses the exact /api/research backend contract (mode: company_comparison).
 * Strictly renders source-returned data; never invents winners, scores, or values.
 */

import { useState, useRef } from "react";
import {
  AlertCircle,
  ArrowRightLeft,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Flame,
  Globe2,
  Info,
  LoaderCircle,
  Newspaper,
  Scale,
  Search,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react";
import { runCompanyComparison, type TypedResearchResponse } from "@/lib/research";
import { getAgentosUrl } from "@/lib/agentos";

type ComparisonProps = {
  initialCompanyA?: string;
  initialCompanyB?: string;
};

const quickPairs = [
  { a: "AAPL", b: "MSFT", label: "AAPL vs MSFT" },
  { a: "NVDA", b: "AMD", label: "NVDA vs AMD" },
  { a: "GOOGL", b: "META", label: "GOOGL vs META" },
  { a: "V", b: "MA", label: "V vs MA" },
];

function formatMetricValue(value: number | null | undefined, unit: string, currency?: string | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (unit === "currency") {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
      notation: Math.abs(value) >= 1_000_000 ? "compact" : "standard",
      maximumFractionDigits: 2,
    }).format(value);
  }
  if (unit === "percentage") {
    return `${(value * (Math.abs(value) <= 1 ? 100 : 1)).toFixed(2)}%`;
  }
  if (unit === "ratio" || unit === "per_share" || unit === "score") {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return value.toLocaleString();
}

function winnerBadge(winner: "A" | "B" | "TIE" | "INSUFFICIENT_DATA", symbolA: string, symbolB: string) {
  if (winner === "A") {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-[var(--positive)]/15 text-[var(--positive)]">{symbolA}</span>;
  }
  if (winner === "B") {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-[var(--positive)]/15 text-[var(--positive)]">{symbolB}</span>;
  }
  if (winner === "TIE") {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-[var(--surface-subtle)] text-[var(--ink-soft)]">Tie</span>;
  }
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium text-[var(--ink-faint)]">N/A</span>;
}

function periodBadge(alignment: "ALIGNED" | "PARTIALLY_ALIGNED" | "NOT_ALIGNED" | "NOT_AVAILABLE") {
  if (alignment === "ALIGNED") {
    return <span className="text-[10px] text-[var(--positive)] font-medium">Aligned</span>;
  }
  if (alignment === "PARTIALLY_ALIGNED") {
    return <span className="text-[10px] text-[var(--provenance)] font-medium">Partial</span>;
  }
  if (alignment === "NOT_ALIGNED") {
    return <span className="text-[10px] text-[var(--negative)] font-medium">Unaligned</span>;
  }
  return null;
}

export function CompanyComparison({ initialCompanyA = "AAPL", initialCompanyB = "MSFT" }: ComparisonProps) {
  const [companyA, setCompanyA] = useState(initialCompanyA);
  const [companyB, setCompanyB] = useState(initialCompanyB);
  const [includeAnalysis, setIncludeAnalysis] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonData, setComparisonData] = useState<TypedResearchResponse["company_comparison"] | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  async function handleCompare(a = companyA, b = companyB) {
    const normA = a.trim();
    const normB = b.trim();

    if (!normA || !normB) {
      setError("Please enter two company tickers or names to compare.");
      return;
    }
    if (normA.toUpperCase() === normB.toUpperCase()) {
      setError("Company A and Company B must be different companies.");
      return;
    }

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setError(null);

    try {
      const response = await runCompanyComparison(normA, normB, includeAnalysis, getAgentosUrl(), controller.signal);
      if (controller.signal.aborted) return;
      if (!response.company_comparison) {
        throw new Error("No comparison data was returned by the research service.");
      }
      setComparisonData(response.company_comparison);
    } catch (err) {
      if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;
      setError(err instanceof Error ? err.message : "Failed to load company comparison.");
    } finally {
      setIsLoading(false);
    }
  }

  const report = comparisonData;
  const symbolA = report?.company_a.ticker || companyA.toUpperCase();
  const symbolB = report?.company_b.ticker || companyB.toUpperCase();

  return (
    <div className="space-y-6">
      {/* Control Deck */}
      <section className="terminal-hero p-5 sm:p-7 border border-[var(--rule)] bg-[var(--surface)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="research-kicker">
              <span className="size-1.5 rounded-full bg-[var(--provenance)]" />
              Comparative Analytics
            </div>
            <h2 className="mt-2 font-serif text-2xl sm:text-3xl text-[var(--ink)] tracking-tight">
              Company Comparison
            </h2>
            <p className="mt-1 text-xs sm:text-sm text-[var(--ink-soft)] max-w-2xl">
              Side-by-side deterministic fundamental, market, and strength comparison backed by audited FX rates and period alignment.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-[var(--ink-soft)] cursor-pointer">
              <input
                type="checkbox"
                checked={includeAnalysis}
                onChange={(e) => setIncludeAnalysis(e.target.checked)}
                className="rounded border-[var(--rule)]"
              />
              <span>Include AI Synthesis</span>
            </label>
          </div>
        </div>

        {/* Input Pair Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleCompare();
          }}
          className="mt-5 grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr_auto] gap-3 items-center"
          aria-label="Compare two companies"
        >
          <div className="flex items-center gap-2 border border-[var(--rule-strong)] bg-[var(--surface-raised)] px-3 py-2.5 transition-colors focus-within:border-[var(--research-indigo)] focus-within:ring-1 focus-within:ring-[var(--research-indigo)]">
            <span className="text-xs font-mono font-bold text-[var(--research-indigo)]" aria-hidden="true">A</span>
            <label htmlFor="comparison-company-a" className="sr-only">First company ticker or symbol</label>
            <input
              id="comparison-company-a"
              value={companyA}
              onChange={(e) => setCompanyA(e.target.value)}
              placeholder="Company A (e.g. AAPL)"
              aria-label="First company ticker or symbol"
              autoComplete="off"
              className="min-w-0 flex-1 bg-transparent text-sm font-medium text-[var(--ink)] outline-none placeholder:text-[var(--ink-faint)]"
            />
          </div>

          <div className="flex justify-center text-[var(--ink-faint)]" aria-hidden="true">
            <ArrowRightLeft className="size-4" />
          </div>

          <div className="flex items-center gap-2 border border-[var(--rule-strong)] bg-[var(--surface-raised)] px-3 py-2.5 transition-colors focus-within:border-[var(--provenance)] focus-within:ring-1 focus-within:ring-[var(--provenance)]">
            <span className="text-xs font-mono font-bold text-[var(--provenance)]" aria-hidden="true">B</span>
            <label htmlFor="comparison-company-b" className="sr-only">Second company ticker or symbol</label>
            <input
              id="comparison-company-b"
              value={companyB}
              onChange={(e) => setCompanyB(e.target.value)}
              placeholder="Company B (e.g. MSFT)"
              aria-label="Second company ticker or symbol"
              autoComplete="off"
              className="min-w-0 flex-1 bg-transparent text-sm font-medium text-[var(--ink)] outline-none placeholder:text-[var(--ink-faint)]"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !companyA.trim() || !companyB.trim()}
            className="research-primary-button w-full sm:w-auto flex items-center justify-center gap-2 h-10 px-5"
          >
            {isLoading ? <LoaderCircle className="size-4 animate-spin" /> : <Scale className="size-4" />}
            <span>{isLoading ? "Comparing…" : "Compare"}</span>
          </button>
        </form>

        {/* Quick Picks */}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--ink-soft)]" role="group" aria-label="Quick comparative pairs">
          <span className="ledger-label">Quick pairs:</span>
          {quickPairs.map((pair) => (
            <button
              key={pair.label}
              type="button"
              aria-label={`Compare ${pair.label}`}
              onClick={() => {
                setCompanyA(pair.a);
                setCompanyB(pair.b);
                void handleCompare(pair.a, pair.b);
              }}
              className="font-mono text-xs px-2 py-0.5 rounded border border-[var(--rule)] bg-[var(--surface-subtle)] hover:border-[var(--research-indigo)] transition-colors focus-visible:ring-1 focus-visible:ring-[var(--research-indigo)]"
            >
              {pair.label}
            </button>
          ))}
        </div>
      </section>

      {/* Error Alert */}
      {error && (
        <div className="flex items-start gap-3 border-l-2 border-[var(--negative)] bg-[color-mix(in_oklab,var(--negative)_8%,var(--surface))] p-4 text-sm" role="alert" aria-live="assertive">
          <AlertCircle className="size-4 shrink-0 text-[var(--negative)] mt-0.5" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <strong className="font-semibold text-[var(--ink)]">Comparison Notice</strong>
            <p className="mt-0.5 text-xs text-[var(--ink-soft)]">{error}</p>
          </div>
          <button type="button" onClick={() => setError(null)} className="text-[var(--ink-faint)] hover:text-[var(--ink)] focus-visible:ring-1 focus-visible:ring-[var(--ink)] p-1 rounded" aria-label="Dismiss comparison notice">
            <X className="size-4" />
          </button>
        </div>
      )}

      {/* Results View */}
      {report && (
        <div className="space-y-6" id="comparison-results" aria-live="polite">
          {/* Header Cards (Company A vs Company B) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card A */}
            <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-[var(--research-indigo)]" />
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="ledger-label">Company A</span>
                  <h3 className="font-serif text-2xl font-bold text-[var(--ink)] mt-1">
                    {report.company_a.ticker}
                  </h3>
                  <p className="text-xs text-[var(--ink-soft)] font-medium">
                    {report.company_a.company_name || "—"}
                  </p>
                </div>
                <span className="px-2 py-1 text-[10px] font-mono font-semibold rounded bg-[var(--surface-subtle)] text-[var(--ink-soft)] border border-[var(--rule)]">
                  {report.company_a.exchange || "—"} · {report.company_a.currency || "USD"}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-xs border-t border-[var(--rule)] pt-3">
                <div>
                  <span className="text-[var(--ink-faint)]">Sector / Industry</span>
                  <p className="font-medium text-[var(--ink)] truncate">
                    {[report.company_a.sector, report.company_a.industry].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
                <div>
                  <span className="text-[var(--ink-faint)]">Market Cap</span>
                  <p className="font-mono font-semibold text-[var(--ink)]">
                    {formatMetricValue(report.company_a.market_cap, "currency", report.company_a.currency)}
                  </p>
                </div>
              </div>
            </div>

            {/* Card B */}
            <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-[var(--provenance)]" />
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="ledger-label">Company B</span>
                  <h3 className="font-serif text-2xl font-bold text-[var(--ink)] mt-1">
                    {report.company_b.ticker}
                  </h3>
                  <p className="text-xs text-[var(--ink-soft)] font-medium">
                    {report.company_b.company_name || "—"}
                  </p>
                </div>
                <span className="px-2 py-1 text-[10px] font-mono font-semibold rounded bg-[var(--surface-subtle)] text-[var(--ink-soft)] border border-[var(--rule)]">
                  {report.company_b.exchange || "—"} · {report.company_b.currency || "USD"}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-xs border-t border-[var(--rule)] pt-3">
                <div>
                  <span className="text-[var(--ink-faint)]">Sector / Industry</span>
                  <p className="font-medium text-[var(--ink)] truncate">
                    {[report.company_b.sector, report.company_b.industry].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
                <div>
                  <span className="text-[var(--ink-faint)]">Market Cap</span>
                  <p className="font-mono font-semibold text-[var(--ink)]">
                    {formatMetricValue(report.company_b.market_cap, "currency", report.company_b.currency)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Overall Advantage & Confidence Banner */}
          <div className="p-5 border border-[var(--rule)] bg-[var(--surface)]">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--rule)] pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-5 text-[var(--research-indigo)]" />
                <span className="font-semibold text-sm text-[var(--ink)]">Overall Comparison Verdict</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--ink-faint)]">Advantage:</span>
                {winnerBadge(report.overall_advantage, symbolA, symbolB)}
                <span className="text-xs text-[var(--ink-faint)] ml-2">Confidence:</span>
                <span className="text-xs font-mono font-semibold uppercase text-[var(--ink)]">
                  {report.comparison_confidence.level}
                </span>
              </div>
            </div>
            <p className="mt-3 text-sm text-[var(--ink-soft)] leading-relaxed">
              {report.overall_explanation}
            </p>
            {report.comparison_confidence.reasons.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-[var(--ink-faint)]">
                {report.comparison_confidence.reasons.map((reason, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-[var(--surface-subtle)] border border-[var(--rule)]">
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Dual Score Cards: Financial Strength & Momentum */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Financial Strength */}
            <div className="p-5 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="flex items-center justify-between">
                <span className="ledger-label">Financial Strength</span>
                {winnerBadge(report.financial_strength.winner, symbolA, symbolB)}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 text-center border-y border-[var(--rule)] py-3">
                <div>
                  <span className="text-xs font-mono font-bold text-[var(--research-indigo)]">{symbolA}</span>
                  <p className="font-mono text-2xl font-bold text-[var(--ink)] mt-1">
                    {report.financial_strength.company_a_score ?? "—"}
                  </p>
                </div>
                <div className="border-l border-[var(--rule)]">
                  <span className="text-xs font-mono font-bold text-[var(--provenance)]">{symbolB}</span>
                  <p className="font-mono text-2xl font-bold text-[var(--ink)] mt-1">
                    {report.financial_strength.company_b_score ?? "—"}
                  </p>
                </div>
              </div>
              <div className="mt-3 text-xs text-[var(--ink-soft)] space-y-1">
                {report.financial_strength.factors_a.map((f, i) => (
                  <p key={i} className="truncate">• {symbolA}: {f}</p>
                ))}
                {report.financial_strength.factors_b.map((f, i) => (
                  <p key={i} className="truncate">• {symbolB}: {f}</p>
                ))}
              </div>
            </div>

            {/* Momentum */}
            <div className="p-5 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="flex items-center justify-between">
                <span className="ledger-label">Momentum & Trend</span>
                {winnerBadge(report.momentum.winner, symbolA, symbolB)}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 text-center border-y border-[var(--rule)] py-3">
                <div>
                  <span className="text-xs font-mono font-bold text-[var(--research-indigo)]">{symbolA}</span>
                  <p className="font-mono text-2xl font-bold text-[var(--ink)] mt-1">
                    {report.momentum.company_a_score ?? "—"}
                  </p>
                </div>
                <div className="border-l border-[var(--rule)]">
                  <span className="text-xs font-mono font-bold text-[var(--provenance)]">{symbolB}</span>
                  <p className="font-mono text-2xl font-bold text-[var(--ink)] mt-1">
                    {report.momentum.company_b_score ?? "—"}
                  </p>
                </div>
              </div>
              <div className="mt-3 text-xs text-[var(--ink-soft)] space-y-1">
                {report.momentum.factors_a.map((f, i) => (
                  <p key={i} className="truncate">• {symbolA}: {f}</p>
                ))}
                {report.momentum.factors_b.map((f, i) => (
                  <p key={i} className="truncate">• {symbolB}: {f}</p>
                ))}
              </div>
            </div>
          </div>

          {/* Category Winners */}
          {report.category_winners && report.category_winners.length > 0 && (
            <div className="p-5 border border-[var(--rule)] bg-[var(--surface)]">
              <span className="ledger-label">Category Outcomes</span>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {report.category_winners.map((cat) => (
                  <div key={cat.category} className="p-3 border border-[var(--rule)] bg-[var(--surface-raised)]">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-xs text-[var(--ink)] capitalize">{cat.category.replace(/_/g, " ")}</span>
                      {winnerBadge(cat.winner, symbolA, symbolB)}
                    </div>
                    <p className="mt-2 text-[11px] text-[var(--ink-soft)] leading-snug">
                      {cat.explanation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metric Comparison Table */}
          <div className="border border-[var(--rule)] bg-[var(--surface)] overflow-hidden">
            <div className="p-4 border-b border-[var(--rule)] flex items-center justify-between">
              <div>
                <span className="ledger-label">Audited Fundamentals</span>
                <h4 className="font-serif text-lg font-bold text-[var(--ink)] mt-0.5">Detailed Metric Matrix</h4>
              </div>
              {report.fx_conversions.length > 0 && (
                <div className="text-[11px] font-mono text-[var(--provenance)] bg-[var(--provenance)]/10 px-2.5 py-1 rounded">
                  FX: {report.fx_conversions[0].base_currency}/{report.fx_conversions[0].quote_currency} = {report.fx_conversions[0].rate.toFixed(4)}
                </div>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs" aria-label="Audited fundamentals and metric comparison matrix">
                <caption className="sr-only">Detailed comparative metrics between {symbolA} and {symbolB}</caption>
                <thead>
                  <tr className="border-b border-[var(--rule)] bg-[var(--surface-subtle)] text-[var(--ink-faint)]">
                    <th scope="col" className="p-3 font-semibold">Metric</th>
                    <th scope="col" className="p-3 font-semibold text-right">{symbolA}</th>
                    <th scope="col" className="p-3 font-semibold text-right">{symbolB}</th>
                    <th scope="col" className="p-3 font-semibold text-right">Diff</th>
                    <th scope="col" className="p-3 font-semibold text-center">Advantage</th>
                    <th scope="col" className="p-3 font-semibold text-center">Alignment</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--rule)]">
                  {report.metrics.map((row) => (
                    <tr key={row.metric} className="hover:bg-[var(--surface-raised)] transition-colors">
                      <th scope="row" className="p-3 font-medium text-[var(--ink)] capitalize text-left font-normal">
                        {row.metric.replace(/_/g, " ")}
                        {row.currency && (
                          <span className="ml-1 text-[10px] text-[var(--ink-faint)] font-mono">({row.currency})</span>
                        )}
                      </th>
                      <td className="p-3 text-right font-mono font-medium text-[var(--ink)]">
                        {formatMetricValue(row.company_a_value, row.unit, row.currency_a || report.company_a.currency)}
                      </td>
                      <td className="p-3 text-right font-mono font-medium text-[var(--ink)]">
                        {formatMetricValue(row.company_b_value, row.unit, row.currency_b || report.company_b.currency)}
                      </td>
                      <td className="p-3 text-right font-mono text-[var(--ink-soft)]">
                        {row.difference !== null && row.difference !== undefined ? (
                          <span className={row.difference > 0 ? "text-[var(--positive)]" : row.difference < 0 ? "text-[var(--negative)]" : ""}>
                            {row.difference > 0 ? "+" : ""}{formatMetricValue(row.difference, row.unit, row.currency)}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="p-3 text-center">
                        {winnerBadge(row.winner, symbolA, symbolB)}
                      </td>
                      <td className="p-3 text-center">
                        {periodBadge(row.period_alignment)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="p-3 text-[11px] text-[var(--ink-faint)] border-t border-[var(--rule)]">
              Cross-currency values are converted at verified market FX rates. Comparison winners require matching or aligned reporting periods.
            </p>
          </div>

          {/* Analyst Interpretation Synthesis */}
          {report.analyst_interpretation && (
            <div className="p-5 border border-[var(--rule)] bg-[var(--surface)] space-y-4">
              <div className="flex items-center gap-2 border-b border-[var(--rule)] pb-3">
                <Info className="size-5 text-[var(--research-indigo)]" />
                <h4 className="font-serif text-lg font-bold text-[var(--ink)]">Analyst Synthesis</h4>
              </div>

              {report.analyst_interpretation.executive_summary && (
                <div>
                  <span className="ledger-label">Executive Summary</span>
                  <p className="mt-1 text-sm text-[var(--ink-soft)] leading-relaxed">
                    {report.analyst_interpretation.executive_summary}
                  </p>
                </div>
              )}

              {report.analyst_interpretation.key_difference && (
                <div>
                  <span className="ledger-label">Key Strategic Distinction</span>
                  <p className="mt-1 text-sm text-[var(--ink)] font-medium leading-relaxed">
                    {report.analyst_interpretation.key_difference}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-[var(--rule)] pt-3">
                <div>
                  <span className="ledger-label text-[var(--research-indigo)]">{symbolA} Core Strengths</span>
                  <ul className="mt-2 space-y-1.5 text-xs text-[var(--ink-soft)]">
                    {report.analyst_interpretation.company_a_strengths.map((str, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="size-1 rounded-full bg-[var(--research-indigo)] mt-1.5 shrink-0" />
                        <span>{str}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <span className="ledger-label text-[var(--provenance)]">{symbolB} Core Strengths</span>
                  <ul className="mt-2 space-y-1.5 text-xs text-[var(--ink-soft)]">
                    {report.analyst_interpretation.company_b_strengths.map((str, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="size-1 rounded-full bg-[var(--provenance)] mt-1.5 shrink-0" />
                        <span>{str}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* News & Events Side-by-Side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* News A */}
            <div className="p-4 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="flex items-center gap-2 mb-3">
                <Newspaper className="size-4 text-[var(--research-indigo)]" />
                <span className="font-semibold text-xs text-[var(--ink)]">{symbolA} Recent News</span>
              </div>
              {report.company_a_news.length > 0 ? (
                <ul className="space-y-2 text-xs divide-y divide-[var(--rule)]">
                  {report.company_a_news.slice(0, 4).map((item, i) => (
                    <li key={i} className="pt-2">
                      <p className="text-[var(--ink)] font-medium leading-snug">{item.title}</p>
                      <span className="text-[10px] text-[var(--ink-faint)]">{item.publisher}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[var(--ink-faint)]">No recent news returned.</p>
              )}
            </div>

            {/* News B */}
            <div className="p-4 border border-[var(--rule)] bg-[var(--surface)]">
              <div className="flex items-center gap-2 mb-3">
                <Newspaper className="size-4 text-[var(--provenance)]" />
                <span className="font-semibold text-xs text-[var(--ink)]">{symbolB} Recent News</span>
              </div>
              {report.company_b_news.length > 0 ? (
                <ul className="space-y-2 text-xs divide-y divide-[var(--rule)]">
                  {report.company_b_news.slice(0, 4).map((item, i) => (
                    <li key={i} className="pt-2">
                      <p className="text-[var(--ink)] font-medium leading-snug">{item.title}</p>
                      <span className="text-[10px] text-[var(--ink-faint)]">{item.publisher}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[var(--ink-faint)]">No recent news returned.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
