/** Analyst's Ledger visual contract: small caps labels, tabular figures, restrained semantic color. */

import type { Metric } from "@/lib/market";
import { cn } from "@/lib/utils";

export function MetricCard({ metric }: { metric: Metric }) {
  return (
    <article className="ledger-card group px-4 py-3.5 transition-transform duration-200 motion-safe:hover:-translate-y-0.5">
      <div className="flex items-center justify-between gap-2"><p className="ledger-label">{metric.label}</p><span className="ledger-signal" /></div>
      <p
        className={cn(
          "mt-2 font-mono text-[15px] font-semibold tracking-[-0.035em] tabular-nums",
          metric.tone === "positive" && "text-[#0e8f83]",
          metric.tone === "negative" && "text-[#bd4b38]",
          metric.tone === "neutral" && "text-[#1d2928]",
        )}
      >
        {metric.value}
      </p>
      <p className="mt-2 text-[9px] font-medium uppercase tracking-[0.12em] text-[#969b96]">{metric.value === "—" ? "Awaiting source" : "AgentOS source"}</p>
    </article>
  );
}
