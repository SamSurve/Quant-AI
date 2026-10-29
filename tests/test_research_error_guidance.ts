import { researchErrorKind } from "../client/src/lib/research";

const cases: Array<[string, ReturnType<typeof researchErrorKind>]> = [
  ["Multiple companies match this query. Select a listed ticker to continue.", "ambiguous"],
  ["No supported listed company or ticker was found for this query.", "not_found"],
  ["AI analysis is temporarily unavailable. Please try again shortly.", "ai_unavailable"],
  ["Current news is temporarily unavailable. Other research data may still be available.", "news_unavailable"],
  ["Research is temporarily unavailable. Please try again shortly.", "other"],
];

for (const [message, expected] of cases) {
  if (researchErrorKind(message) !== expected) throw new Error(`Unexpected error kind for ${expected}`);
}

console.log("RESEARCH_ERROR_GUIDANCE_REGRESSION=PASS");
