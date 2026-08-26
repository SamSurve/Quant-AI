/** Analyst's Ledger visual contract: a quiet evidence chart with no fabricated series. */

import type { ChartPoint } from "@/lib/market";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

/** Evidence Terminal Continuum visual contract: market plots are factual, quiet, and share the workspace surface hierarchy. */

export function MarketChart({ data }: { data: ChartPoint[] }) {
  const { resolvedTheme } = useTheme();
  const palette = resolvedTheme === "dark"
    ? { line: "#A4ACFF", fill: "#A4ACFF", axis: "#9EA7B8", surface: "#181C28", border: "#4A5265", ink: "#F0F1E9" }
    : { line: "#5A67D8", fill: "#5A67D8", axis: "#687080", surface: "#FEFDF9", border: "#CEC9BF", ink: "#202737" };
  if (data.length < 2) {
    return (
      <div className="relative min-h-[220px] overflow-hidden border-y border-[var(--rule)] bg-[var(--surface-raised)] px-5 py-5">
        <div className="absolute inset-x-0 top-1/2 h-px bg-[var(--rule)]" />
        <div className="absolute inset-x-0 top-[31%] h-px border-t border-dashed border-[var(--rule)]" />
        <div className="absolute inset-x-0 top-[69%] h-px border-t border-dashed border-[var(--rule)]" />
        <div className="relative grid min-h-[178px] grid-cols-[1fr_auto] items-end gap-5">
          <div className="self-center">
            <div className="flex items-center gap-2"><span className="ledger-aperture grid size-8 place-items-center bg-[color-mix(in_oklab,var(--provenance)_12%,var(--surface))] text-[var(--provenance)]"><BarChart3 className="size-3.5" /></span><p className="ledger-label">Chart record / awaiting series</p></div>
            <p className="mt-4 max-w-sm font-serif text-2xl leading-[1.14] tracking-[-0.04em] text-[var(--ink)]">Price history appears when the research record includes dated closes.</p>
            <p className="mt-3 max-w-md text-xs leading-relaxed text-[var(--ink-soft)]">The plot only renders returned research data; it never uses placeholder market movement.</p>
          </div>
          <div className="space-y-2 border-l border-[var(--rule)] pl-4 font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--ink-faint)]"><p>Period · —</p><p>Points · 00</p><p>Source · pending</p></div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[220px] w-full border-y border-[var(--rule)] bg-[var(--surface-raised)] py-4 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 6, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id="marketArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={palette.fill} stopOpacity={0.22} />
              <stop offset="95%" stopColor={palette.fill} stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: palette.axis }} minTickGap={30} />
          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: palette.axis }} width={42} />
          <Tooltip
            cursor={{ stroke: palette.line, strokeWidth: 1, strokeDasharray: "3 3" }}
            contentStyle={{ border: `1px solid ${palette.border}`, borderRadius: 4, background: palette.surface, boxShadow: "0 8px 24px rgba(0,0,0,.12)", fontSize: 12 }}
            labelStyle={{ color: palette.ink, fontWeight: 700 }}
            formatter={(value) => [Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }), "Price"]}
          />
          <Area type="monotone" dataKey="value" stroke={palette.line} strokeWidth={2} fill="url(#marketArea)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
