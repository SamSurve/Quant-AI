/** Analyst's Ledger visual contract: offset-aperture mark, graphite ink, Signal Teal focus. */

import { cn } from "@/lib/utils";

const logoUrl = "/assets/analysts-ledger-logo.png";

/** Research Observatory visual contract: the aperture mark anchors every workspace state. */

export function BrandMark({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)} aria-label="QuantAI">
      <span className="ledger-aperture grid size-11 shrink-0 place-items-center overflow-hidden border border-[var(--rule-strong)] bg-[var(--surface-raised)]">
        <img src={logoUrl} alt="" className="size-9 object-contain" />
      </span>
      {!compact && (
          <span className="relative leading-none before:absolute before:-left-2 before:top-1 before:h-7 before:w-px before:bg-[var(--provenance)]">
          <span className="block text-[10px] font-bold uppercase tracking-[0.28em] text-[var(--ink)]">Quant</span>
          <span className="block font-serif text-[1.42rem] tracking-[-0.055em] text-[var(--ink)]">AI</span>
        </span>
      )}
    </div>
  );
}
