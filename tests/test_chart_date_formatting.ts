import { formatChartDate } from "../client/src/components/MarketChart";

if (formatChartDate("2026-08-03T00:00:00+05:30") !== "Aug 03") throw new Error("Chart date formatter changed the returned calendar date.");
if (formatChartDate("2026-08-27T00:00:00Z") !== "Aug 27") throw new Error("Chart date formatter did not produce the requested readable label.");
if (formatChartDate("not-a-timestamp") !== "not-a-time") throw new Error("Chart date formatter should avoid displaying a raw long invalid value.");
console.log("CHART_DATE_FORMATTING_REGRESSION=PASS");
