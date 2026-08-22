/** Analyst's Ledger visual contract: a quiet evidence chart with no fabricated series. */

import type { ChartPoint } from "@/lib/market";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";

export function MarketChart({ data }: { data: ChartPoint[] }) {
  if (data.length < 2) {
    return (
      <div className="relative min-h-[220px] overflow-hidden border-y border-[#e2dbd0] bg-[#fbfaf7]/70 px-5 py-5">
        <div className="absolute inset-x-0 top-1/2 h-px bg-[#e3ddd2]" />
        <div className="absolute inset-x-0 top-[31%] h-px border-t border-dashed border-[#e9e3d9]" />
        <div className="absolute inset-x-0 top-[69%] h-px border-t border-dashed border-[#e9e3d9]" />
        <div className="relative grid min-h-[178px] grid-cols-[1fr_auto] items-end gap-5">
          <div className="self-center">
            <div className="flex items-center gap-2"><span className="ledger-aperture grid size-8 place-items-center bg-[#edf5f2] text-[#0e8f83]"><BarChart3 className="size-3.5" /></span><p className="ledger-label">Chart protocol / awaiting series</p></div>
            <p className="mt-4 max-w-sm font-serif text-2xl leading-[1.14] tracking-[-0.04em] text-[#303a37]">Price history becomes visible only when the research record includes dated closes.</p>
            <p className="mt-3 max-w-md text-xs leading-relaxed text-[#737b77]">Ask for a dated price-history table. The plot renders agent-supplied figures rather than placeholder market movement.</p>
          </div>
          <div className="space-y-2 border-l border-[#ded6ca] pl-4 font-mono text-[10px] uppercase tracking-[0.1em] text-[#89908a]"><p>Period · —</p><p>Points · 00</p><p>Source · pending</p></div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[220px] w-full border-y border-[#e2dbd0] bg-[#fbfaf7]/50 py-4 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 6, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id="marketArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#0e8f83" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#0e8f83" stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#7a827e" }} minTickGap={30} />
          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#7a827e" }} width={42} />
          <Tooltip
            cursor={{ stroke: "#0e8f83", strokeWidth: 1, strokeDasharray: "3 3" }}
            contentStyle={{ border: "1px solid #ddd5c9", borderRadius: 2, background: "#fcfaf6", boxShadow: "0 8px 24px rgba(30,41,40,.08)", fontSize: 12 }}
            labelStyle={{ color: "#1e2928", fontWeight: 700 }}
            formatter={(value) => [Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }), "Price"]}
          />
          <Area type="monotone" dataKey="value" stroke="#0e8f83" strokeWidth={2} fill="url(#marketArea)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
