/** Analyst's Ledger visual contract: editorial pull quote, source-aware markdown, paper texture. */

import { FileText, Sparkles } from "lucide-react";
import { Streamdown } from "streamdown";

const briefingImage = "/manus-storage/analysts-ledger-briefing_9a92da5e.jpg";

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
    <section className="ledger-panel relative overflow-hidden p-5 sm:p-6" aria-label="AI generated financial analysis">
      <img src={briefingImage} alt="" className="pointer-events-none absolute inset-y-0 right-0 h-full w-40 object-cover opacity-[0.16] mix-blend-multiply" />
      <div className="relative">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-full bg-[#e8f2f0] text-[#0e8f83]">
              <Sparkles className="size-3.5" />
            </span>
            <div>
              <p className="ledger-label">Agent analysis</p>
              <h2 className="mt-0.5 font-serif text-xl tracking-[-0.035em] text-[#1d2928]">Research brief</h2>
            </div>
          </div>
          <span className="source-chip ledger-aperture">AgentOS sourced</span>
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
            {lead && <p className="max-w-3xl border-l-2 border-[#0e8f83] pl-5 font-serif text-[1.72rem] leading-[1.14] tracking-[-0.045em] text-[#263130] sm:text-[2.25rem]">“{lead}”</p>}
            <div className="agent-markdown mt-6 max-w-none">
              <Streamdown>{analysis}</Streamdown>
            </div>
          </div>
        ) : (
          <div className="mt-8 border-y border-[#ded6cb] bg-[#fbfaf7]/70 py-6">
            <div className="flex items-start gap-4"><span className="ledger-aperture grid size-9 shrink-0 place-items-center bg-[#edf5f2] text-[#0e8f83]"><FileText className="size-4" /></span><div><p className="ledger-label">Opening note / pending research</p><p className="mt-3 max-w-3xl border-l-2 border-[#0e8f83] pl-5 font-serif text-[1.72rem] leading-[1.14] tracking-[-0.045em] text-[#303a37] sm:text-[2.25rem]">“{preAnalysisLead}”</p></div></div>
            <div className="mt-6 grid gap-px border border-[#e3dcd1] bg-[#e3dcd1] text-[10px] uppercase tracking-[0.12em] text-[#727b76] sm:grid-cols-3"><p className="bg-[#fffdf9] px-3 py-2.5">Evidence status · Awaiting</p><p className="bg-[#fffdf9] px-3 py-2.5">Source suite · YFinance + web</p><p className="bg-[#fffdf9] px-3 py-2.5">Brief type · Market context</p></div>
          </div>
        )}
      </div>
    </section>
  );
}
