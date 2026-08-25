/** Analyst's Ledger visual contract: small caps labels, tabular figures, restrained semantic color. */

import type { Metric } from "@/lib/market";
import { cn } from "@/lib/utils";

/** Final UI Polish visual contract: concise facts become a denser, clearly scannable evidence ledger without adding data. */

export function MetricCard({ metric }: { metric: Metric }) {
  return (
    <article className="research-metric px-4 py-3.5 transition-colors duration-150 hover:bg-[var(--surface-subtle)]">
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
      {metric.value === "—" ? <p className="mt-2 text-[10px] text-[var(--ink-faint)]">Unavailable</p> : null}
    </article>
  );
}
