/** Analyst's Ledger visual contract: small caps labels, tabular figures, restrained semantic color. */

import type { Metric } from "@/lib/market";
import { cn } from "@/lib/utils";

/** Research Observatory visual contract: compact, source-aware metric evidence. */

export function MetricCard({ metric }: { metric: Metric }) {
  return (
    <article className="ledger-card group px-4 py-3.5 transition-colors duration-150 hover:bg-[var(--surface)]">
      <div className="flex items-center justify-between gap-2"><p className="ledger-label">{metric.label}</p><span className="ledger-signal" /></div>
      <p
        className={cn(
          "mt-2 font-mono text-[15px] font-semibold tracking-[-0.035em] tabular-nums",
          metric.tone === "positive" && "text-[var(--positive)]",
          metric.tone === "negative" && "text-[var(--negative)]",
          metric.tone === "neutral" && "text-[var(--ink)]",
        )}
      >
        {metric.value}
      </p>
      <p className="mt-2 text-[9px] font-medium uppercase tracking-[0.12em] text-[var(--ink-faint)]">{metric.value === "—" ? "Awaiting source" : "Source record"}</p>
    </article>
  );
}
