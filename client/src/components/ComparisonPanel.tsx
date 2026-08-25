/** Final UI Polish visual contract: headline comparison, verified FX, metrics, and source lanes gain denser editorial framing without changing evidence. */

import { ArrowRight, Scale } from "lucide-react";
import { categoryLabel, comparisonLabel, comparisonValue, winnerLabel, type ComparisonReport } from "@/lib/comparison";

type ComparisonPanelProps = { report: ComparisonReport | null; isLoading: boolean };

function winnerClass(winner: ComparisonReport["overall_advantage"]) {
  if (winner === "A" || winner === "B") return "text-[var(--positive)]";
  if (winner === "TIE") return "text-[var(--ink-soft)]";
  return "text-[var(--negative)]";
}

function metricValue(metric: ComparisonReport["metrics"][number], side: "A" | "B") {
  return comparisonValue(side === "A" ? metric.company_a_value : metric.company_b_value, metric.unit, side === "A" ? (metric.currency_a || metric.currency) : (metric.currency_b || metric.currency));
}

function normalizedValue(metric: ComparisonReport["metrics"][number], side: "A" | "B") {
  return comparisonValue(side === "A" ? metric.company_a_comparison_value : metric.company_b_comparison_value, metric.unit, metric.currency);
}

export function ComparisonPanel({ report, isLoading }: ComparisonPanelProps) {
  if (!report && !isLoading) return null;
  if (isLoading) return <div className="mt-7 border-t border-[var(--rule)] pt-5"><p className="ledger-label">Comparison in progress</p><p className="mt-2 text-sm text-[var(--ink-soft)]">Resolving identities and validating comparable source records.</p><div className="mt-4 space-y-2"><div className="shimmer-line h-4 w-full" /><div className="shimmer-line h-4 w-[82%]" /></div></div>;
  if (!report) return null;

  const aTicker = report.company_a.ticker;
  const bTicker = report.company_b.ticker;
  const fxConversions = report.fx_conversions || [];
  const headlineMetrics = report.metrics.filter((metric) => ["market_cap", "revenue", "net_income", "pe_ratio", "profit_margin", "free_cash_flow"].includes(metric.metric)).slice(0, 6);

  return (
    <section className="comparison-report mt-7 border-t border-[var(--rule)] pt-6" aria-label="Company comparison report">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-2.5"><span className="ledger-aperture grid size-8 place-items-center bg-[var(--surface-subtle)] text-[var(--research-indigo)]"><Scale className="size-3.5" /></span><div><p className="ledger-label">Comparison result</p><h2 className="mt-1 font-serif text-2xl tracking-[-0.04em] text-[var(--ink)]">{aTicker} <span className="font-sans text-sm tracking-normal text-[var(--ink-faint)]">vs</span> {bTicker}</h2></div></div>
        <p className={`max-w-xs text-right text-sm font-semibold ${winnerClass(report.overall_advantage)}`}>{winnerLabel(report.overall_advantage, aTicker, bTicker)}</p>
      </div>
      <p className="mt-4 max-w-3xl text-sm leading-relaxed text-[var(--ink-soft)]">{report.overall_explanation}</p>

      <div className="mt-6 grid gap-px border-y border-[var(--rule)] bg-[var(--rule)] sm:grid-cols-2">
        {[{ label: "A", company: report.company_a, status: report.company_a_status, market: report.market_a, financial: report.financial_strength.company_a_score, momentum: report.momentum.company_a_score }, { label: "B", company: report.company_b, status: report.company_b_status, market: report.market_b, financial: report.financial_strength.company_b_score, momentum: report.momentum.company_b_score }].map(({ label, company, status, market, financial, momentum }) => <article key={company.ticker} className="bg-[var(--surface)] p-4"><p className="ledger-label">Company {label}</p><div className="mt-2 flex items-end justify-between gap-3"><div><p className="font-serif text-2xl tracking-[-0.04em] text-[var(--ink)]">{company.ticker}</p><p className="mt-1 text-xs text-[var(--ink-soft)]">{company.company_name || "Company name unavailable"}</p></div><p className="font-mono text-base font-semibold tabular-nums text-[var(--ink)]">{market?.current_price == null ? "—" : `${market.currency || company.currency || ""} ${market.current_price.toLocaleString()}`}</p></div><p className="mt-3 text-xs text-[var(--ink-faint)]">{[company.sector, company.industry, company.exchange].filter(Boolean).join(" · ") || "Profile details unavailable"}</p><div className="mt-4 flex gap-5 border-t border-[var(--rule)] pt-3 text-xs"><p><span className="ledger-label">Financial strength</span><span className="mt-1 block font-mono text-sm text-[var(--ink)]">{financial ?? "—"}</span></p><p><span className="ledger-label">Momentum</span><span className="mt-1 block font-mono text-sm text-[var(--ink)]">{momentum ?? "—"}</span></p></div><p className={`mt-3 text-[11px] ${status.overall === "available" ? "text-[var(--provenance)]" : status.overall === "partial" ? "text-[#8b6d3f]" : "text-[var(--negative)]"}`}>{status.message}</p></article>)}
      </div>

      {fxConversions.length ? <details className="research-details mt-5" open><summary>Verified FX conversion evidence</summary>{fxConversions.map((fx) => <div key={`${fx.base_currency}-${fx.quote_currency}-${fx.retrieved_at}`} className="mt-3 border-l-2 border-[var(--provenance)] bg-[color-mix(in_oklab,var(--provenance)_8%,var(--surface))] px-4 py-3 text-xs"><p className="font-semibold text-[var(--ink)]">1 {fx.base_currency} = {fx.rate.toLocaleString(undefined, { maximumFractionDigits: 6 })} {fx.quote_currency}</p><p className="mt-1 text-[var(--ink-soft)]">{fx.source} · retrieved {fx.retrieved_at}</p>{fx.url ? <a href={fx.url} target="_blank" rel="noreferrer" className="research-source-link mt-2">Open source record <ArrowRight className="size-3" /></a> : null}</div>)}</details> : <p className="mt-5 text-xs leading-relaxed text-[var(--ink-soft)]">Monetary values are ranked only when their source currency and reporting-period evidence support the comparison.</p>}

      <div className="mt-6 grid gap-px border-y border-[var(--rule)] bg-[var(--rule)] sm:grid-cols-2 lg:grid-cols-3">{headlineMetrics.map((metric) => <article key={metric.metric} className="bg-[var(--surface)] p-4"><div className="flex items-start justify-between gap-2"><p className="ledger-label">{comparisonLabel(metric.metric)}</p><p className={`text-[11px] font-semibold ${winnerClass(metric.winner)}`}>{winnerLabel(metric.winner, aTicker, bTicker)}</p></div><div className="mt-3 grid grid-cols-2 gap-3"><div><p className="ledger-label">{aTicker}</p><p className="mt-1 font-mono text-xs text-[var(--ink)]">{metricValue(metric, "A")}</p>{metric.company_a_comparison_value != null ? <p className="mt-1 text-[10px] text-[var(--provenance)]">Normalized · {normalizedValue(metric, "A")}</p> : null}</div><div><p className="ledger-label">{bTicker}</p><p className="mt-1 font-mono text-xs text-[var(--ink)]">{metricValue(metric, "B")}</p>{metric.company_b_comparison_value != null ? <p className="mt-1 text-[10px] text-[var(--provenance)]">Normalized · {normalizedValue(metric, "B")}</p> : null}</div></div><p className="mt-3 text-[10px] text-[var(--ink-faint)]">{metric.period_alignment.replaceAll("_", " ")}</p></article>)}</div>

      <details className="research-details mt-5"><summary>Complete metric ledger and alignment notes</summary><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[680px] border-collapse text-left text-xs"><thead className="border-y border-[var(--rule)] text-[var(--ink-faint)]"><tr><th className="py-2 pr-3">Metric</th><th className="px-3 py-2">{aTicker}</th><th className="px-3 py-2">{bTicker}</th><th className="px-3 py-2">Outcome</th><th className="py-2 pl-3">Evidence</th></tr></thead><tbody>{report.metrics.map((metric) => <tr key={metric.metric} className="border-b border-[var(--rule)] align-top"><th className="py-3 pr-3 font-semibold text-[var(--ink)]">{comparisonLabel(metric.metric)}</th><td className="px-3 py-3 font-mono text-[var(--ink)]">{metricValue(metric, "A")}{metric.company_a_comparison_value != null ? <span className="mt-1 block text-[10px] text-[var(--provenance)]">Normalized · {normalizedValue(metric, "A")}</span> : null}</td><td className="px-3 py-3 font-mono text-[var(--ink)]">{metricValue(metric, "B")}{metric.company_b_comparison_value != null ? <span className="mt-1 block text-[10px] text-[var(--provenance)]">Normalized · {normalizedValue(metric, "B")}</span> : null}</td><td className={`px-3 py-3 font-semibold ${winnerClass(metric.winner)}`}>{winnerLabel(metric.winner, aTicker, bTicker)}</td><td className="py-3 pl-3 text-[var(--ink-soft)]">{metric.note || metric.period_alignment.replaceAll("_", " ")}</td></tr>)}</tbody></table></div></details>

      <details className="research-details mt-5"><summary>Category outcomes, interpretation, and source lanes</summary><div className="mt-4 grid gap-6 lg:grid-cols-2"><div><p className="ledger-label">Category outcomes</p><ul className="mt-3 space-y-3">{report.category_winners.map((category) => <li key={category.category} className="border-b border-[var(--rule)] pb-3"><p className="flex justify-between gap-3 text-sm font-semibold text-[var(--ink)]"><span>{categoryLabel(category.category)}</span><span className={winnerClass(category.winner)}>{winnerLabel(category.winner, aTicker, bTicker)}</span></p><p className="mt-1 text-xs leading-relaxed text-[var(--ink-soft)]">{category.explanation}</p></li>)}</ul></div><div><p className="ledger-label">Optional interpretation</p><p className="mt-3 text-sm leading-relaxed text-[var(--ink-soft)]">{report.analyst_interpretation?.executive_summary || "AI interpretation unavailable. The deterministic comparison record remains available above."}</p><p className="mt-3 text-xs leading-relaxed text-[var(--ink-faint)]">{report.competitive_data_note}</p></div></div><div className="mt-6 grid gap-6 border-t border-[var(--rule)] pt-5 lg:grid-cols-2"><EvidenceLane label={`${aTicker} news and events`} news={report.company_a_news} events={report.company_a_events} /><EvidenceLane label={`${bTicker} news and events`} news={report.company_b_news} events={report.company_b_events} /></div></details>
    </section>
  );
}

function EvidenceLane({ label, news, events }: { label: string; news: ComparisonReport["company_a_news"]; events: ComparisonReport["company_a_events"] }) {
  return <div><p className="ledger-label">{label}</p><div className="mt-3 space-y-3">{[...news.slice(0, 3).map((item) => ({ title: item.title, detail: [item.publisher, item.published_at?.slice(0, 10)].filter(Boolean).join(" · ") || "Source metadata unavailable", href: item.url })), ...events.slice(0, 2).map((item) => ({ title: item.title, detail: [item.date?.slice(0, 10), item.source].filter(Boolean).join(" · ") || "Event source unavailable", href: undefined }))].map((item, index) => <div key={`${item.title}-${index}`} className="border-b border-[var(--rule)] pb-3"><p className="text-xs leading-relaxed text-[var(--ink)]">{item.href ? <a href={item.href} target="_blank" rel="noreferrer" className="hover:text-[var(--research-indigo)] hover:underline">{item.title}</a> : item.title}</p><p className="mt-1 text-[10px] text-[var(--ink-faint)]">{item.detail}</p></div>)}{!(news.length || events.length) ? <p className="text-xs text-[var(--ink-soft)]">No sourced news or event record was returned for this lane.</p> : null}</div></div>;
}
