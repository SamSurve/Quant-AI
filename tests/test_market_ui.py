"""Automated tests for Market Intelligence UI, routes, HTMX partials, and data validation (M06)."""

import asyncio
import math
import sys
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.index import app
from api.market_intelligence_services import (
    MarketPulseResult,
    HistoryResult,
    EventRadarResult,
)
from api.research_schemas import (
    CompanyIdentity,
    FreshnessRecord,
    FreshnessState,
    HistoryPeriod,
    HistoryPoint,
    MarketSnapshot,
    MarketSignal,
    PriceHistoryBundle,
    ResearchEvent,
    ServiceState,
    ErrorCategory,
    IdentifierConfidence,
    SourceRecord,
    NewsItem,
)
from api.research_errors import ResearchError
from api.research_services import NewsDataResult
from api.web import (
    format_currency,
    format_percent,
    format_large_number,
    generate_chart_svg_data,
)


class TestMarketIntelligenceUI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Format Helper Verification
    # -------------------------------------------------------------------------
    def test_format_helpers(self):
        """Format helpers must handle numbers, zeroes, None, and NaN safely."""
        self.assertEqual(format_currency(123.456), "$123.46")
        self.assertEqual(format_currency(0.0), "$0.00")
        self.assertEqual(format_currency(None), "N/A")
        self.assertEqual(format_currency(float("nan")), "N/A")
        self.assertEqual(format_currency(100.0, "EUR"), "EUR 100.00")

        self.assertEqual(format_percent(1.234), "+1.23%")
        self.assertEqual(format_percent(-0.567), "-0.57%")
        self.assertEqual(format_percent(0.0), "0.00%")
        self.assertEqual(format_percent(None), "N/A")

        self.assertEqual(format_large_number(42_800_000), "42.80M")
        self.assertEqual(format_large_number(2_500_000_000), "2.50B")
        self.assertEqual(format_large_number(1_200_000_000_000), "1.20T")
        self.assertEqual(format_large_number(500), "500")
        self.assertEqual(format_large_number(None), "N/A")

    # -------------------------------------------------------------------------
    # 2. SVG Chart Data Generation
    # -------------------------------------------------------------------------
    def test_generate_chart_svg_data(self):
        """SVG generator must produce valid paths and coordinate bounds."""
        points = [
            HistoryPoint(timestamp="2025-01-01", close=100.0),
            HistoryPoint(timestamp="2025-01-02", close=105.0),
            HistoryPoint(timestamp="2025-01-03", close=110.0),
        ]
        svg_data = generate_chart_svg_data(points, width=800, height=260)
        self.assertIsNotNone(svg_data)
        self.assertTrue(svg_data["is_positive"])
        self.assertIn("M ", svg_data["line_d"])
        self.assertIn(" Z", svg_data["area_d"])
        self.assertEqual(svg_data["point_count"], 3)
        self.assertEqual(svg_data["min_price"], 100.0)
        self.assertEqual(svg_data["max_price"], 110.0)

        # Empty or invalid points return None
        self.assertIsNone(generate_chart_svg_data([]))
        self.assertIsNone(generate_chart_svg_data([HistoryPoint(timestamp="2025-01-01", close=None)]))

    # -------------------------------------------------------------------------
    # 3. Full Market Page Route
    # -------------------------------------------------------------------------
    @patch("api.web.default_market_pulse_service.fetch")
    @patch("api.web.default_price_history_service.fetch")
    @patch("api.web.default_event_radar_service.fetch")
    def test_market_page_valid_symbol(self, mock_events, mock_history, mock_pulse):
        """Full market page renders verified quotes, charts, signals, and events."""
        entity = CompanyIdentity(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            identifier_confidence=IdentifierConfidence.HIGH,
        )
        mock_pulse.return_value = (
            MarketPulseResult(
                company=entity,
                market=MarketSnapshot(
                    current_price=225.50,
                    currency="USD",
                    daily_change=3.25,
                    daily_change_percent=1.46,
                    volume=55_000_000,
                    market_cap=3_400_000_000_000,
                    pe_ratio=32.4,
                    eps=6.95,
                    fifty_two_week_high=237.23,
                    fifty_two_week_low=164.08,
                    dividend_yield=0.005,
                    market_status="REGULAR",
                    as_of="2026-10-29T16:00:00Z",
                ),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=SourceRecord(source="Yahoo Finance via yfinance", url="https://finance.yahoo.com/quote/AAPL", retrieved_at="2026-10-29T16:00:00Z", data_type="market"),
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE, cache_scope="none"),
        )

        daily_points = [
            HistoryPoint(timestamp=f"2026-09-{i:02d}", close=200.0 + i, volume=50000000)
            for i in range(1, 30)
        ]
        mock_history.return_value = (
            HistoryResult(
                history=PriceHistoryBundle(
                    daily=daily_points,
                    intraday=[],
                    available_periods=[HistoryPeriod.ONE_MONTH, HistoryPeriod.ONE_YEAR],
                    default_period=HistoryPeriod.ONE_MONTH,
                    freshness=FreshnessRecord(state=FreshnessState.LIVE),
                ),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=SourceRecord(source="Yahoo Finance via yfinance", url="https://finance.yahoo.com/quote/AAPL", retrieved_at="2026-10-29T16:00:00Z", data_type="market"),
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        mock_events.return_value = (
            EventRadarResult(
                events=[
                    ResearchEvent(
                        event_type="earnings_date",
                        title="Q4 Earnings Release",
                        date="2026-11-05",
                        importance="high",
                        source="Yahoo Finance",
                    )
                ],
                status=ServiceState.AVAILABLE,
                warning=None,
                source=SourceRecord(source="Yahoo Finance via yfinance", url="https://finance.yahoo.com/quote/AAPL", retrieved_at="2026-10-29T16:00:00Z", data_type="market"),
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        resp = self.client.get("/market?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Apple Inc.", html)
        self.assertIn("$225.50", html)
        self.assertIn("+1.46%", html)
        self.assertIn("55.00M", html)
        self.assertIn("$164.08", html)
        self.assertIn("$237.23", html)
        self.assertIn("market-chart-svg", html)
        self.assertIn("Q4 Earnings Release", html)
        self.assertIn("Deterministic Technical Signal", html)
        # Verify no hardcoded M04 placeholders
        self.assertNotIn("$584.20", html)
        self.assertNotIn("42.8M", html)

    def test_market_page_invalid_symbol(self):
        """Invalid symbols must display a clear validation alert and not crash or call providers."""
        resp = self.client.get("/market?symbol=AAPL<script>")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Invalid Ticker Symbol", html)
        self.assertIn("Invalid ticker symbol format", html)

        resp_too_long = self.client.get("/market?symbol=VERYLONGSYMBOLNAME123456")
        self.assertEqual(resp_too_long.status_code, 200)
        self.assertIn("Invalid Ticker Symbol", resp_too_long.text)

    # -------------------------------------------------------------------------
    # 4. HTMX Partial Endpoints
    # -------------------------------------------------------------------------
    @patch("api.web.default_market_pulse_service.fetch")
    def test_market_quote_partial(self, mock_pulse):
        """HTMX quote partial returns rendered quote fragment."""
        entity = CompanyIdentity(symbol="MSFT", identifier_confidence=IdentifierConfidence.HIGH)
        mock_pulse.return_value = (
            MarketPulseResult(
                company=entity,
                market=MarketSnapshot(
                    current_price=415.00,
                    currency="USD",
                    daily_change=2.50,
                    daily_change_percent=0.60,
                    volume=20_000_000,
                    as_of="2026-10-29T16:00:00Z",
                ),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=None,
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        resp = self.client.get("/market/quote?symbol=MSFT")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("MSFT", html)
        self.assertIn("$415.00", html)
        self.assertIn("+0.60%", html)

    @patch("api.web.default_market_pulse_service.fetch")
    def test_market_quote_partial_unavailable(self, mock_pulse):
        """HTMX quote partial gracefully displays honest unavailable state on failure."""
        entity = CompanyIdentity(symbol="FAIL", identifier_confidence=IdentifierConfidence.HIGH)
        mock_pulse.return_value = (
            MarketPulseResult(
                company=entity,
                market=None,
                status=ServiceState.UNAVAILABLE,
                warning=ResearchError(category=ErrorCategory.TIMEOUT, detail="Connection timed out"),
                source=None,
                retrieved_at=None,
            ),
            FreshnessRecord(state=FreshnessState.UNAVAILABLE),
        )

        resp = self.client.get("/market/quote?symbol=FAIL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Market Quote Data Unavailable", html)
        self.assertIn("Connection timed out", html)

    @patch("api.web.default_price_history_service.fetch")
    def test_market_chart_partial(self, mock_history):
        """HTMX chart partial returns SVG chart for requested horizon."""
        daily_points = [
            HistoryPoint(timestamp=f"2026-10-{i:02d}", close=150.0 + i)
            for i in range(1, 15)
        ]
        mock_history.return_value = (
            HistoryResult(
                history=PriceHistoryBundle(
                    daily=daily_points,
                    intraday=[],
                    available_periods=[HistoryPeriod.ONE_MONTH],
                    default_period=HistoryPeriod.ONE_MONTH,
                    freshness=FreshnessRecord(state=FreshnessState.LIVE),
                ),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=None,
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        resp = self.client.get("/market/chart?symbol=AAPL&period=1W")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("market-chart-svg", html)
        self.assertIn("1W", html)
        self.assertIn('aria-pressed="true"', html)

    @patch("api.web.default_event_radar_service.fetch")
    def test_market_events_partial_empty_calendar(self, mock_events):
        """Empty corporate calendar displays honest empty message."""
        mock_events.return_value = (
            EventRadarResult(
                events=[],
                status=ServiceState.AVAILABLE,
                warning=None,
                source=None,
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        resp = self.client.get("/market/events?symbol=SPY")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("No upcoming corporate events", html)

    @patch("api.web.default_event_radar_service.fetch")
    def test_market_events_partial_service_unavailable(self, mock_events):
        """Unavailable corporate radar displays honest error message and retry button."""
        mock_events.return_value = (
            EventRadarResult(
                events=[],
                status=ServiceState.UNAVAILABLE,
                warning=ResearchError(category=ErrorCategory.EVENTS_UNAVAILABLE, detail="Provider down"),
                source=None,
                retrieved_at=None,
            ),
            FreshnessRecord(state=FreshnessState.UNAVAILABLE),
        )

        resp = self.client.get("/market/events?symbol=SPY")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Corporate event radar is currently unavailable", html)
        self.assertIn("Retry Calendar Feed", html)

    @patch("api.web.default_market_pulse_service.fetch")
    def test_market_quote_missing_optional_fields(self, mock_pulse):
        """Quote card with missing optional fields renders clean N/A without failing."""
        entity = CompanyIdentity(symbol="ETF", identifier_confidence=IdentifierConfidence.HIGH)
        mock_pulse.return_value = (
            MarketPulseResult(
                company=entity,
                market=MarketSnapshot(
                    current_price=100.0,
                    currency="USD",
                    daily_change=None,
                    daily_change_percent=None,
                    volume=None,
                    pe_ratio=None,
                    eps=None,
                    fifty_two_week_high=None,
                    fifty_two_week_low=None,
                    dividend_yield=None,
                    as_of=None,
                ),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=None,
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        resp = self.client.get("/market/quote?symbol=ETF")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("$100.00", html)
        self.assertIn("P/E: N/A", html)
        self.assertIn("Div Yield: N/A", html)
        self.assertIn("Unavailable", html)

    @patch("api.web.default_price_history_service.fetch")
    def test_market_chart_partial_empty_history(self, mock_history):
        """Empty price history renders honest fallback state and retry action."""
        mock_history.return_value = (
            HistoryResult(
                history=PriceHistoryBundle(
                    daily=[],
                    intraday=[],
                    available_periods=[],
                    default_period=HistoryPeriod.ONE_MONTH,
                    freshness=FreshnessRecord(state=FreshnessState.UNAVAILABLE),
                ),
                status=ServiceState.UNAVAILABLE,
                warning=ResearchError(category=ErrorCategory.HISTORY_UNAVAILABLE, detail="No historical points"),
                source=None,
                retrieved_at=None,
            ),
            FreshnessRecord(state=FreshnessState.UNAVAILABLE),
        )

        resp = self.client.get("/market/chart?symbol=NODATA&period=1M")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Historical price points are unavailable", html)
        self.assertIn("Retry Period Data", html)



    @patch("api.web.default_price_history_service.fetch")
    def test_market_chart_partial_six_months(self, mock_history):
        """HTMX chart partial returns SVG chart for 6M requested horizon."""
        daily_points = [
            HistoryPoint(timestamp=f"2026-05-{i:02d}", close=140.0 + i)
            for i in range(1, 25)
        ]
        mock_history.return_value = (
            HistoryResult(
                history=PriceHistoryBundle(
                    daily=daily_points,
                    intraday=[],
                    available_periods=[HistoryPeriod.SIX_MONTHS],
                    default_period=HistoryPeriod.SIX_MONTHS,
                    freshness=FreshnessRecord(state=FreshnessState.LIVE),
                ),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=None,
                retrieved_at="2026-10-29T16:00:00Z",
            ),
            FreshnessRecord(state=FreshnessState.LIVE),
        )

        resp = self.client.get("/market/chart?symbol=AAPL&period=6M")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("market-chart-svg", html)
        self.assertIn("6M", html)
        self.assertIn('aria-pressed="true"', html)

    @patch("api.web.default_news_service.fetch")
    def test_market_news_partial_available(self, mock_news):
        """HTMX market news partial returns formatted articles when available."""
        mock_news.return_value = NewsDataResult(
            items=[
                NewsItem(
                    title="Apple Expands Enterprise AI Services",
                    publisher="Reuters",
                    published_at="2026-10-29T10:00:00Z",
                    url="https://example.com/aapl-news",
                    summary="Apple announced new enterprise AI partnerships.",
                    relevance="high",
                    sentiment="positive",
                ),
                NewsItem(
                    title="Q4 Earnings Preview",
                    publisher="Bloomberg",
                    published_at="2026-10-28T14:30:00Z",
                    url="https://example.com/aapl-preview",
                    summary="Analysts raise revenue estimates ahead of quarterly report.",
                    relevance="medium",
                    sentiment="neutral",
                ),
            ],
            status=ServiceState.AVAILABLE,
            warning=None,
            sources=[SourceRecord(source="DuckDuckGo News", retrieved_at="2026-10-29T16:00:00Z", data_type="news")],
        )

        resp = self.client.get("/market/news?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("market-news-container", html)
        self.assertIn("Sourced Recent News", html)
        self.assertIn("2 Articles", html)
        self.assertIn("Apple Expands Enterprise AI Services", html)
        self.assertIn("Reuters", html)
        self.assertIn("https://example.com/aapl-news", html)

    @patch("api.web.default_news_service.fetch")
    def test_market_news_partial_empty(self, mock_news):
        """HTMX market news partial displays honest message when no articles returned."""
        mock_news.return_value = NewsDataResult(
            items=[],
            status=ServiceState.AVAILABLE,
            warning=None,
            sources=[],
        )

        resp = self.client.get("/market/news?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("No sourced recent news was returned", html)

    @patch("api.web.default_news_service.fetch")
    def test_market_news_partial_unavailable(self, mock_news):
        """HTMX market news partial displays honest unavailable notice and retry trigger."""
        mock_news.return_value = NewsDataResult(
            items=[],
            status=ServiceState.UNAVAILABLE,
            warning=ResearchError(category=ErrorCategory.NEWS_UNAVAILABLE, detail="Upstream rate limit"),
            sources=[],
        )

        resp = self.client.get("/market/news?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Recent news stream is currently unavailable", html)
        self.assertIn("Retry News Feed", html)

    def test_market_page_includes_news_container(self):
        """Market page HTML includes the market-news-container partial trigger."""
        resp = self.client.get("/market?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("market-news-container", html)
        self.assertIn("Sourced Recent News", html)

if __name__ == "__main__":
    unittest.main()
