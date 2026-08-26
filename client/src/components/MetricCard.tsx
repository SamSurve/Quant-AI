/** Evidence Terminal Continuum reminder: metric cells keep source-returned figures legible, comfortably padded, and scannable without altering their data mapping. */

import type { Metric } from "@/lib/market";
import { cn } from "@/lib/utils";

/** Final UI Polish visual contract: concise facts become a denser, clearly scannable evidence ledger without adding data. */

export function MetricCard({ metric }: { metric: Metric }) {
  return (
    <article className="research-metric px-5 py-4 transition-colors duration-150 hover:bg-[var(--surface-subtle)] sm:px-5 sm:py-4.5">
      <div className="flex items-center justify-between gap-2"><p className="ledger-label">{metric.label}</p><span className="ledger-signal" /></div>
      <p
        className={cn(
          "mt-2.5 font-mono text-[17px] font-semibold tracking-[-0.035em] tabular-nums sm:text-[18px]",
          metric.tone === "positive" && "text-[var(--positive)]",
          metric.tone === "negative" && "text-[var(--negative)]",
          metric.tone === "neutral" && "text-[var(--ink)]",
        )}
      >
        {metric.value}
      </p>
      {metric.value === "—" ? <p className="mt-2.5 text-[11px] leading-relaxed text-[var(--ink-faint)]">Unavailable</p> : null}
    </article>
  );
}
