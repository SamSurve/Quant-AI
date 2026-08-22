/**
 * Analyst's Ledger style contract: convert agent-authored markdown into optional dashboard surfaces.
 * Values are never invented; missing fields remain intentionally unavailable.
 */

export type Metric = { label: string; value: string; tone?: "neutral" | "positive" | "negative" };
export type ChartPoint = { label: string; value: number };
export type MarketBrief = {
  companyName: string;
  ticker: string;
  exchange: string;
  sector: string;
  industry: string;
  quote: string;
  change: string;
  metrics: Metric[];
  news: string[];
  chart: ChartPoint[];
  analysis: string;
};

type MarkdownTable = { headers: string[]; rows: string[][] };

const metricKeys = [
  { label: "Market cap", matches: ["market cap", "market capitalization"] },
  { label: "P / E ratio", matches: ["p/e", "p/e ratio", "pe ratio", "price to earnings"] },
  { label: "52-week high", matches: ["52 week high", "52-week high"] },
  { label: "52-week low", matches: ["52 week low", "52-week low"] },
  { label: "Volume", matches: ["volume", "avg volume", "average volume"] },
  { label: "Dividend yield", matches: ["dividend yield"] },
];

function cleanCell(value: string) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .trim();
}

function parseTables(markdown: string): MarkdownTable[] {
  const lines = markdown.split("\n");
  const tables: MarkdownTable[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    const separator = lines[index + 1]?.trim() || "";
    if (!line.startsWith("|") || !separator.startsWith("|") || !/[-:]{3,}/.test(separator)) {
      index += 1;
      continue;
    }

    const headers = line
      .split("|")
      .slice(1, -1)
      .map((cell) => cleanCell(cell).toLowerCase());
    const rows: string[][] = [];
    index += 2;
    while (index < lines.length && lines[index].trim().startsWith("|")) {
      rows.push(lines[index].trim().split("|").slice(1, -1).map(cleanCell));
      index += 1;
    }
    tables.push({ headers, rows });
  }
  return tables;
}

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function findTableValue(tables: MarkdownTable[], terms: string[]) {
  for (const table of tables) {
    const labelIndex = table.headers.findIndex((header) => /metric|measure|item|indicator|field/.test(header));
    const valueIndex = table.headers.findIndex((header) => /value|amount|data|latest|current/.test(header));
    for (const row of table.rows) {
      const label = normalize(row[labelIndex >= 0 ? labelIndex : 0] || "");
      if (terms.some((term) => label.includes(normalize(term)))) {
        const index = valueIndex >= 0 ? valueIndex : row.length > 1 ? 1 : 0;
        return row[index] || "—";
      }
    }
  }

  const flat = tables.flatMap((table) => table.rows);
  for (const row of flat) {
    const joined = normalize(row.join(" "));
    if (terms.some((term) => joined.includes(normalize(term)))) {
      return row.find((cell) => /[$€£₹¥]|\d/.test(cell)) || "—";
    }
  }
  return "—";
}

function extractFallbackValue(markdown: string, terms: string[]) {
  const lines = markdown.split("\n");
  for (const line of lines) {
    const normalizedLine = normalize(line);
    if (terms.some((term) => normalizedLine.includes(normalize(term)))) {
      const match = line.match(/([$€£₹¥]\s?[\d,.]+(?:[BMKT])?|[\d,.]+%?|[\d,.]+\s?[BMKT])/i);
      if (match) return match[0];
    }
  }
  return "—";
}

function findValue(tables: MarkdownTable[], markdown: string, terms: string[]) {
  const fromTable = findTableValue(tables, terms);
  return fromTable !== "—" ? fromTable : extractFallbackValue(markdown, terms);
}

function displayValue(value: string) {
  return value === "—" || /^unavailable$/i.test(value) ? "—" : value;
}

function numberFromCell(value: string) {
  const cleaned = value.replace(/[$€£₹¥,\s]/g, "").replace(/\((.*)\)/, "-$1");
  const match = cleaned.match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : NaN;
}

function extractChart(tables: MarkdownTable[]) {
  for (const table of tables) {
    const dateIndex = table.headers.findIndex((header) => /date|day|period|time/.test(header));
    const priceIndex = table.headers.findIndex((header) => /close|price|value|last/.test(header));
    if (dateIndex < 0 || priceIndex < 0) continue;
    const points = table.rows
      .map((row) => ({ label: row[dateIndex] || "", value: numberFromCell(row[priceIndex] || "") }))
      .filter((point) => point.label && Number.isFinite(point.value))
      .slice(-40);
    if (points.length >= 2) return points;
  }
  return [];
}

function extractNews(markdown: string) {
  const lines = markdown.split("\n");
  const sectionStart = lines.findIndex((line) => /recent news|news (?:highlights|summary)|latest news/i.test(line));
  const candidates = (sectionStart >= 0 ? lines.slice(sectionStart + 1, sectionStart + 12) : lines)
    .filter((line) => /^\s*(?:[-*•]|\d+\.)\s+/.test(line))
    .map((line) => line.replace(/^\s*(?:[-*•]|\d+\.)\s+/, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").trim())
    .filter((line) => line.length > 12)
    .slice(0, 3);
  return candidates;
}

function toneFor(value: string): Metric["tone"] {
  if (/^\+|up|gain|positive/i.test(value)) return "positive";
  if (/^-|down|loss|negative/i.test(value)) return "negative";
  return "neutral";
}

export function parseMarketBrief(markdown: string): MarketBrief {
  const tables = parseTables(markdown);
  const quote = displayValue(findValue(tables, markdown, ["current price", "stock price", "last price", "price"]));
  const change = displayValue(findValue(tables, markdown, ["day change", "change", "daily change", "percent change"]));
  const metrics = metricKeys.map((metric) => {
    const value = displayValue(findValue(tables, markdown, metric.matches));
    return { label: metric.label, value, tone: toneFor(value) };
  });

  return {
    companyName: displayValue(findValue(tables, markdown, ["company name", "company"])),
    ticker: displayValue(findValue(tables, markdown, ["ticker", "symbol"])),
    exchange: displayValue(findValue(tables, markdown, ["exchange"])),
    sector: displayValue(findValue(tables, markdown, ["sector"])),
    industry: displayValue(findValue(tables, markdown, ["industry"])),
    quote,
    change,
    metrics,
    news: extractNews(markdown),
    chart: extractChart(tables),
    analysis: markdown,
  };
}

export const emptyMarketBrief: MarketBrief = {
  companyName: "—",
  ticker: "—",
  exchange: "—",
  sector: "—",
  industry: "—",
  quote: "—",
  change: "Awaiting AgentOS research",
  metrics: metricKeys.map((metric) => ({ label: metric.label, value: "—", tone: "neutral" })),
  news: [],
  chart: [],
  analysis: "",
};
