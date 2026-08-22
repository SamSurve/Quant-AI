/** Analyst's Ledger visual contract: offset-aperture mark, graphite ink, Signal Teal focus. */

import { cn } from "@/lib/utils";

const logoUrl = "/assets/analysts-ledger-logo.png";

export function BrandMark({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)} aria-label="QuantAI">
      <span className="ledger-aperture grid size-11 shrink-0 place-items-center overflow-hidden border border-[#cfc7ba] bg-[#f6f1e9] shadow-[0_5px_12px_rgba(20,30,30,0.06)]">
        <img src={logoUrl} alt="" className="size-9 object-contain" />
      </span>
      {!compact && (
        <span className="relative leading-none before:absolute before:-left-2 before:top-1 before:h-7 before:w-px before:bg-[#0e8f83]">
          <span className="block text-[10px] font-bold uppercase tracking-[0.28em] text-[#1e2928]">Quant</span>
          <span className="block font-serif text-[1.42rem] tracking-[-0.055em] text-[#1e2928]">AI</span>
        </span>
      )}
    </div>
  );
}
