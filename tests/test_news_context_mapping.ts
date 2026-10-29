import { marketBriefFromResearch } from "../client/src/lib/market";
import type { TypedResearchResponse } from "../client/src/lib/research";

const response = {
  request_id: "news-context-regression",
  query: "AAPL",
  company: { symbol: "AAPL", name: "Apple Inc.", identifier_confidence: "high" },
  candidates: [],
  market: null,
  history: [],
  news: [
    {
      title: "Provider-supplied headline",
      summary: "Provider-supplied factual article context.",
      publisher: "Provider source",
      url: "https://example.com/original-article",
      published_at: "2026-08-25T12:00:00Z",
      relevance: "medium",
      sentiment: null,
    },
    {
      title: "Headline without returned context",
      summary: null,
      publisher: "Provider source",
      url: "https://example.com/second-original-article",
      published_at: "2026-08-25T13:00:00Z",
      relevance: "medium",
      sentiment: null,
    },
  ],
  analysis: null,
  events: [],
  sources: [],
  status: { overall: "partial", market: "unavailable", news: "available", company: "available", ai: "unavailable" },
  warnings: [],
} as TypedResearchResponse;

const brief = marketBriefFromResearch(response);
if (brief.news[0]?.summary !== "Provider-supplied factual article context.") throw new Error("Provider news summary was not preserved.");
if (brief.news[1]?.summary !== null) throw new Error("Missing provider summary was not kept empty.");
if (brief.news[0]?.url !== "https://example.com/original-article") throw new Error("Returned article URL was changed.");
if (brief.news[0]?.publisher !== "Provider source") throw new Error("Returned publisher was changed.");
if (brief.news[0]?.publishedAt !== "2026-08-25T12:00:00Z") throw new Error("Returned publication timestamp was changed.");
console.log("NEWS_CONTEXT_MAPPING_REGRESSION=PASS");
