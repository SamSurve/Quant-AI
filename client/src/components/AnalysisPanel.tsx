/** Analyst's Ledger visual contract: editorial pull quote, source-aware markdown, paper texture. */

import { FileText } from "lucide-react";
import { Streamdown } from "streamdown";

/** Research Observatory visual contract: interpretation follows factual evidence and never impersonates a source record. */

function firstMeaningfulLine(markdown: string) {
  return markdown
    .split("\n")
    .map((line) => line.replace(/^#+\s*/, "").replace(/^[-*]\s*/, "").trim())
    .find((line) => line.length > 45 && !line.startsWith("|"))
    ?.slice(0, 180);
}

export function AnalysisPanel({ analysis, ticker, isLoading }: { analysis: string; ticker: string; isLoading: boolean }) {
  const lead = analysis ? firstMeaningfulLine(analysis) : undefined;
  const preAnalysisLead = `A well-formed ${ticker || "company"} brief begins with a sourced signal, then separates evidence from interpretation.`;

  return (
    <section className="ledger-panel overflow-hidden p-5 sm:p-6" aria-label="Research interpretation">
      <div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="ledger-aperture grid size-8 place-items-center bg-[var(--surface-subtle)] text-[var(--research-indigo)]">
              <FileText className="size-3.5" />
            </span>
            <div>
              <p className="ledger-label">Executive interpretation</p>
              <h2 className="mt-0.5 font-serif text-xl tracking-[-0.035em] text-[var(--ink)]">Research brief</h2>
            </div>
          </div>
          <span className="source-chip">Optional interpretation</span>
        </div>

        {isLoading ? (
          <div className="mt-8 space-y-3" aria-label="Loading AI analysis">
            <div className="shimmer-line h-4 w-[86%]" />
            <div className="shimmer-line h-4 w-[74%]" />
            <div className="shimmer-line h-4 w-[93%]" />
            <div className="shimmer-line h-4 w-[58%]" />
          </div>
        ) : analysis ? (
          <div className="mt-7">
            {lead && <p className="max-w-3xl border-l-2 border-[var(--research-indigo)] pl-5 font-serif text-[1.72rem] leading-[1.14] tracking-[-0.045em] text-[var(--ink)] sm:text-[2.25rem]">“{lead}”</p>}
            <div className="agent-markdown mt-6 max-w-none">
              <Streamdown>{analysis}</Streamdown>
            </div>
          </div>
        ) : (
          <div className="mt-8 border-y border-[var(--rule)] bg-[var(--surface-raised)] py-6">
            <div className="flex items-start gap-4"><span className="ledger-aperture grid size-9 shrink-0 place-items-center bg-[var(--surface-subtle)] text-[var(--provenance)]"><FileText className="size-4" /></span><div><p className="ledger-label">Interpretation status</p><p className="mt-3 max-w-3xl border-l-2 border-[var(--research-indigo)] pl-5 font-serif text-[1.72rem] leading-[1.14] tracking-[-0.045em] text-[var(--ink)] sm:text-[2.25rem]">“{preAnalysisLead}”</p></div></div>
            <div className="mt-6 grid gap-px border border-[var(--rule)] bg-[var(--rule)] text-[10px] uppercase tracking-[0.12em] text-[var(--ink-faint)] sm:grid-cols-3"><p className="bg-[var(--surface)] px-3 py-2.5">Evidence status · awaiting</p><p className="bg-[var(--surface)] px-3 py-2.5">Source record · pending</p><p className="bg-[var(--surface)] px-3 py-2.5">Brief type · market context</p></div>
          </div>
        )}
      </div>
    </section>
  );
}
