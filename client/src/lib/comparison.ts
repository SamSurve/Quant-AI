/**
 * Analyst's Ledger visual contract: comparison facts are projected from typed
 * deterministic JSON; AI narrative is displayed separately and never parsed.
 */

import type { TypedResearchResponse } from "@/lib/research";

export type ComparisonReport = NonNullable<TypedResearchResponse["company_comparison"]>;

const labels: Record<string, string> = {
  market_cap: "Market capitalisation",
  revenue: "Revenue",
  net_income: "Net income",
  eps: "Earnings per share",
  profit_margin: "Profit margin",
  operating_margin: "Operating margin",
  free_cash_flow: "Free cash flow",
  total_cash: "Total cash",
  total_debt: "Total debt",
  pe_ratio: "P/E ratio",
  price_to_sales: "Price / sales",
  dividend_yield: "Dividend yield",
  momentum_score: "Momentum score",
};

export function comparisonLabel(metric: string) {
  return labels[metric] || metric.replaceAll("_", " ");
}

export function comparisonValue(value: number | null | undefined, unit: ComparisonReport["metrics"][number]["unit"], currency?: string | null) {
  if (value === null || value === undefined) return "—";
  if (unit === "percentage") return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
  if (unit === "currency" || unit === "per_share") {
    return `${currency ? `${currency} ` : ""}${value.toLocaleString(undefined, { maximumFractionDigits: 2, notation: Math.abs(value) >= 1_000_000 ? "compact" : "standard" })}`;
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function winnerLabel(winner: ComparisonReport["overall_advantage"], aTicker: string, bTicker: string) {
  if (winner === "A") return aTicker;
  if (winner === "B") return bTicker;
  if (winner === "TIE") return "TIE";
  return "INSUFFICIENT DATA";
}

export function categoryLabel(category: string) {
  return category.replaceAll("_", " ");
}
