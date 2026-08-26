/** Evidence Terminal Continuum reminder: optional AI interpretation is a readable report layer with clear editorial hierarchy, never a substitute for sourced evidence. */

import { FileText } from "lucide-react";
import { Streamdown } from "streamdown";

/** Final UI Polish visual contract: optional interpretation has a stronger editorial anchor while sourced facts remain primary. */

function firstMeaningfulLine(markdown: string) {
  return markdown
    .split("\n")
    .map((line) => line.replace(/^#+\s*/, "").replace(/^[-*]\s*/, "").trim())
    .find((line) => line.length > 45 && !line.startsWith("|"))
    ?.slice(0, 180);
}

export function AnalysisPanel({ analysis, ticker, isLoading, unavailableNotice }: { analysis: string; ticker: string; isLoading: boolean; unavailableNotice?: string | null }) {
  const lead = analysis ? firstMeaningfulLine(analysis) : undefined;
  const preAnalysisLead = unavailableNotice || `A well-formed ${ticker || "company"} brief begins with a sourced signal, then separates evidence from interpretation.`;

  return (
    <section className="research-section research-analysis-panel research-brief-panel overflow-hidden p-6 sm:p-8 lg:p-9" aria-label="Research interpretation">
      <div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="ledger-aperture grid size-8 place-items-center bg-[var(--surface-subtle)] text-[var(--research-indigo)]">
              <FileText className="size-3.5" />
            </span>
            <div>
              <p className="ledger-label">Optional interpretation</p>
              <h2 className="mt-0.5 font-serif text-2xl tracking-[-0.035em] text-[var(--ink)]">Research brief</h2>
            </div>
          </div>
          <span className="research-state">AI-assisted</span>
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
            {lead && <p className="research-brief-lead max-w-4xl border-l-2 border-[var(--research-indigo)] pl-5 font-serif text-[1.8rem] leading-[1.18] tracking-[-0.045em] text-[var(--ink)] sm:text-[2.35rem]">“{lead}”</p>}
            <div className="agent-markdown research-brief-markdown mt-7 max-w-none">
              <Streamdown>{analysis}</Streamdown>
            </div>
          </div>
        ) : (
          <div className="mt-7 border-l-2 border-[var(--provenance)] bg-[var(--surface-raised)] px-5 py-6 sm:px-6">
            <div className="flex items-start gap-4"><span className="ledger-aperture grid size-9 shrink-0 place-items-center bg-[var(--surface-subtle)] text-[var(--provenance)]"><FileText className="size-4" /></span><div><p className="ledger-label">Interpretation status</p><p className="mt-3 max-w-3xl border-l-2 border-[var(--research-indigo)] pl-5 font-serif text-[1.72rem] leading-[1.14] tracking-[-0.045em] text-[var(--ink)] sm:text-[2.25rem]">“{preAnalysisLead}”</p></div></div>
            <p className="mt-5 text-sm leading-relaxed text-[var(--ink-soft)]">{unavailableNotice ? "The sourced market record remains visible above and below this section." : "Interpretation appears only after a sourced research record is returned."}</p>
          </div>
        )}
      </div>
    </section>
  );
}
