"""Comprehensive deterministic backend hardening test suite for QuantAI Company Comparison Engine.

Covers input security, company identity, negative earnings, ratio edge cases,
period alignment, FX validation, scoring methodology, and provider resilience.
"""

from __future__ import annotations

import asyncio
import math
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.company_analysis_services import CompanyProfileResult, FinancialHealthResult
from api.comparison_services import (
    ComparisonCompanyData,
    build_category_winners,
    build_comparison_metrics,
    build_confidence,
    build_financial_strength,
    build_momentum_score,
    comparison_metric,
    is_verified_fx,
    overall_advantage,
    _financial_strength,
    _period_alignment,
    _winner,
)
from api.fx_services import FXRateResult
from api.market_intelligence_services import EventRadarResult, HistoryResult
from api.research_errors import ResearchError
from api.research_orchestrator import ResearchOrchestrator
from api.research_schemas import (
    CompanyCandidate,
    CompanyComparisonInterpretation,
    CompanyIdentity,
    ComparisonIdentity,
    ComparisonWinner,
    CompanyOverview,
    ErrorCategory,
    FXConversion,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    HistoryPeriod,
    HistoryPoint,
    IdentifierConfidence,
    MarketSignal,
    MarketSnapshot,
    NewsItem,
    PeriodAlignment,
    PriceHistoryBundle,
    ResearchEvent,
    ResearchMode,
    ResearchRequest,
    ServiceState,
    SourceRecord,
)
from api.research_services import EntityResolution, NewsDataResult


STAMP = "2026-08-24T00:00:00Z"


def make_source(data_type: str, symbol: str = "AAPL") -> SourceRecord:
    return SourceRecord(
        source="Controlled Test Source",
        url=f"https://example.test/{symbol}/{data_type}",
        retrieved_at=STAMP,
        data_type=data_type,
    )


def make_company_data(
    symbol: str = "AAPL",
    identifier: str = "A",
    currency: str = "USD",
    revenue: float | None = 1000.0,
    net_income: float | None = 200.0,
    fcf: float | None = 150.0,
    pe_ratio: float | None = 25.0,
    period_end: str | None = "2025-09-30T00:00:00Z",
) -> ComparisonCompanyData:
    entity = CompanyIdentity(
        symbol=symbol,
        name=f"{symbol} Corp",
        exchange="NMS",
        sector="Technology",
        industry="Software",
        currency=currency,
        identifier_confidence=IdentifierConfidence.HIGH,
    )
    identity = ComparisonIdentity(
        identifier=identifier,
        company_name=f"{symbol} Corp",
        ticker=symbol,
        exchange="NMS",
        sector="Technology",
        industry="Software",
        currency=currency,
        market_cap=2_000_000_000,
    )
    market = MarketSnapshot(
        current_price=150.0,
        currency=currency,
        market_cap=2_000_000_000,
        daily_change=1.5,
        daily_change_percent=1.0,
        as_of=STAMP,
    )
    financial = FinancialHealth(
        revenue=revenue,
        net_income=net_income,
        eps=5.0 if net_income else None,
        profit_margin=(net_income / revenue) if (net_income and revenue) else None,
        operating_margin=0.25 if revenue else None,
        free_cash_flow=fcf,
        total_cash=500.0,
        total_debt=100.0,
        pe_ratio=pe_ratio,
        price_to_sales=2.0 if revenue else None,
        dividend_yield=0.015,
        currency=currency,
        fiscal_period_end=period_end,
    )
    momentum = MarketSignal(
        signal="BULLISH",
        score=72,
        factors=["Moving average alignment", "Positive RSI momentum"],
    )
    sources = [
        make_source("company", symbol),
        make_source("financial", symbol),
        make_source("history", symbol),
    ]
    return ComparisonCompanyData(
        identifier=identifier,
        entity=entity,
        identity=identity,
        market=market,
        financial=financial,
        momentum=momentum,
        sources=sources,
        states={
            "company": ServiceState.AVAILABLE,
            "financials": ServiceState.AVAILABLE,
            "history": ServiceState.AVAILABLE,
        },
    )


class FakeEntityService:
    async def resolve(self, query: str) -> EntityResolution:
        clean = query.strip().upper()
        symbol_map = {"APPLE": "AAPL", "AAPL": "AAPL", "MICROSOFT": "MSFT", "MSFT": "MSFT", "TCS": "TCS.NS", "TCS.NS": "TCS.NS"}
        symbol = symbol_map.get(clean)
        if not symbol:
            raise ResearchError(ErrorCategory.ENTITY_NOT_FOUND, detail=f"No entity for {query}")
        name = "Apple Inc." if symbol == "AAPL" else "Microsoft Corporation" if symbol == "MSFT" else "Tata Consultancy"
        curr = "INR" if symbol.endswith(".NS") else "USD"
        identity = CompanyIdentity(
            symbol=symbol,
            name=name,
            exchange="NMS",
            sector="Technology",
            industry="Software",
            currency=curr,
            identifier_confidence=IdentifierConfidence.HIGH,
        )
        return EntityResolution(
            company=identity,
            candidates=[CompanyCandidate(symbol=symbol, name=name, exchange="NMS", quote_type="EQUITY")],
            source=make_source("entity", symbol),
        )


class FakeProfileService:
    async def fetch(self, entity: CompanyIdentity):
        overview = CompanyOverview(
            company_name=entity.name,
            ticker=entity.symbol,
            exchange=entity.exchange,
            sector=entity.sector,
            industry=entity.industry,
            country="United States",
            headquarters="Headquarters",
            website="https://example.test",
            business_description="Test profile",
            employees=1000,
            market_cap=2_000_000_000,
            currency=entity.currency,
        )
        info = {"regularMarketPrice": 150.0, "marketCap": 2_000_000_000, "currency": entity.currency, "exchange": entity.exchange}
        return CompanyProfileResult(overview, None, info, ServiceState.AVAILABLE, ServiceState.AVAILABLE, None, make_source("company", entity.symbol), None, STAMP), FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class FakeFinancialService:
    async def fetch(self, entity: CompanyIdentity, _profile):
        rev = 1000.0 if entity.symbol == "AAPL" else 900.0 if entity.symbol == "MSFT" else 80_000.0
        health = FinancialHealth(
            revenue=rev,
            net_income=250.0,
            eps=5.0,
            profit_margin=0.25,
            operating_margin=0.30,
            free_cash_flow=200.0,
            total_cash=500.0,
            total_debt=100.0,
            pe_ratio=25.0,
            price_to_sales=2.0,
            dividend_yield=0.01,
            currency=entity.currency,
            fiscal_period_end="2025-09-30T00:00:00Z",
        )
        return FinancialHealthResult(health, ServiceState.AVAILABLE, None, make_source("financial", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class FakeHistoryService:
    async def fetch(self, entity: CompanyIdentity):
        pts = [HistoryPoint(timestamp=f"2026-01-{(i % 28) + 1:02d}T00:00:00Z", close=100.0 + i, volume=1000) for i in range(30)]
        bundle = PriceHistoryBundle(intraday=pts[:5], daily=pts, available_periods=list(HistoryPeriod), default_period=HistoryPeriod.ONE_MONTH, freshness=FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP))
        return HistoryResult(bundle, ServiceState.AVAILABLE, None, make_source("history", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.LIVE, retrieved_at=STAMP)


class FakeNewsService:
    async def fetch(self, entity: CompanyIdentity):
        item = NewsItem(title=f"News for {entity.symbol}", publisher="Test Publisher", url="https://example.test", published_at=STAMP)
        return NewsDataResult([item], ServiceState.AVAILABLE, None, [make_source("news", entity.symbol)])


class FakeEventService:
    async def fetch(self, entity: CompanyIdentity):
        ev = ResearchEvent(event_type="earnings_date", title=f"{entity.symbol} Earnings", date="2026-10-24T00:00:00Z", importance="high", source="Test")
        return EventRadarResult([ev], ServiceState.AVAILABLE, None, make_source("event", entity.symbol), STAMP), FreshnessRecord(state=FreshnessState.RECENT, retrieved_at=STAMP)


class FakeAnalysisService:
    async def synthesize(self, _req_id: str, _report):
        return CompanyComparisonInterpretation(
            executive_summary="Executive summary test",
            key_difference="Key difference test",
            company_a_strengths=["Strength A"],
            company_b_strengths=["Strength B"],
            overall_assessment="Overall assessment test",
            confidence="high",
        )


class FakeFXService:
    async def fetch(self, base: str | None, quote: str | None) -> FXRateResult:
        if base == "USD" and quote == "INR":
            conv = FXConversion(base_currency="USD", quote_currency="INR", rate=80.0, source="Test FX", source_symbol="USDINR=X", url="https://example.test", retrieved_at=STAMP)
            return FXRateResult(conv, None, make_source("fx", "USDINR=X"))
        return FXRateResult(None, ResearchError(ErrorCategory.CURRENCY_COMPARISON_UNAVAILABLE, detail="FX unavailable", retryable=True), None)


class TestComparisonBackendHardening(unittest.TestCase):
    """Deterministic unit tests validating M09 Comparison Engine hardening."""

    def test_request_input_validation_empty_and_duplicate(self):
        """Reject empty, whitespace, and identical company comparison requests."""
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "", "company_b": "MSFT"})
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "AAPL", "company_b": ""})
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "AAPL", "company_b": "AAPL"})
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "aapl", "company_b": "AAPL"})

    def test_request_input_validation_malicious_characters(self):
        """Reject XSS tags, control characters, null bytes in company identifiers."""
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "<script>alert(1)</script>", "company_b": "MSFT"})
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "AAPL\x00", "company_b": "MSFT"})
        with self.assertRaises(ValueError):
            ResearchRequest.model_validate({"mode": "company_comparison", "company_a": "AAPL\nDROP", "company_b": "MSFT"})

    def test_negative_earnings_pe_ratio_protection(self):
        """Negative or non-positive P/E must return INSUFFICIENT_DATA and explicit note."""
        metric = comparison_metric(
            "pe_ratio",
            -5.0,
            25.0,
            unit="ratio",
            higher_is_better=False,
            currency_a="USD",
            currency_b="USD",
        )
        self.assertEqual(metric.winner, ComparisonWinner.INSUFFICIENT_DATA)
        self.assertIsNone(metric.difference)
        self.assertIn("undefined or non-comparable for negative", metric.note or "")

        # Both negative P/E
        metric_both_neg = comparison_metric(
            "pe_ratio",
            -12.0,
            -4.0,
            unit="ratio",
            higher_is_better=False,
            currency_a="USD",
            currency_b="USD",
        )
        self.assertEqual(metric_both_neg.winner, ComparisonWinner.INSUFFICIENT_DATA)

        # Zero P/E (break-even / undefined)
        metric_zero = comparison_metric(
            "pe_ratio",
            0.0,
            20.0,
            unit="ratio",
            higher_is_better=False,
            currency_a="USD",
            currency_b="USD",
        )
        self.assertEqual(metric_zero.winner, ComparisonWinner.INSUFFICIENT_DATA)

        # Normal positive P/E: lower is better (cheaper)
        metric_normal = comparison_metric(
            "pe_ratio",
            15.0,
            25.0,
            unit="ratio",
            higher_is_better=False,
            currency_a="USD",
            currency_b="USD",
        )
        self.assertEqual(metric_normal.winner, ComparisonWinner.A)
        self.assertEqual(metric_normal.difference, -10.0)

    def test_nan_and_infinity_filtering(self):
        """Non-finite floats (NaN, Inf, -Inf) must be safely filtered and not crash."""
        nan_metric = comparison_metric(
            "revenue",
            float("nan"),
            1000.0,
            unit="currency",
            higher_is_better=True,
            currency_a="USD",
            currency_b="USD",
            period_a="2025-09-30T00:00:00Z",
            period_b="2025-09-30T00:00:00Z",
        )
        self.assertIsNone(nan_metric.company_a_value)
        self.assertEqual(nan_metric.winner, ComparisonWinner.INSUFFICIENT_DATA)

        inf_metric = comparison_metric(
            "eps",
            float("inf"),
            5.0,
            unit="per_share",
            higher_is_better=True,
            currency_a="USD",
            currency_b="USD",
        )
        self.assertIsNone(inf_metric.company_a_value)
        self.assertEqual(inf_metric.winner, ComparisonWinner.INSUFFICIENT_DATA)

    def test_missing_period_metadata_protection(self):
        """Flow metrics with missing period metadata must not declare an absolute winner."""
        metric = comparison_metric(
            "revenue",
            1000.0,
            900.0,
            unit="currency",
            higher_is_better=True,
            currency_a="USD",
            currency_b="USD",
            period_a="2025-09-30T00:00:00Z",
            period_b=None,
        )
        self.assertEqual(metric.winner, ComparisonWinner.INSUFFICIENT_DATA)
        self.assertIn("Reporting period metadata is missing", metric.note or "")

    def test_verified_fx_validation(self):
        """FX conversion must enforce positive, finite rates and complete metadata."""
        valid_fx = FXConversion(
            base_currency="USD",
            quote_currency="EUR",
            rate=0.92,
            source="Yahoo Finance",
            source_symbol="USDEUR=X",
            url="https://finance.yahoo.com/quote/USDEUR=X",
            retrieved_at=STAMP,
        )
        self.assertTrue(is_verified_fx(valid_fx, "USD", "EUR"))
        self.assertFalse(is_verified_fx(valid_fx, "EUR", "USD"))
        self.assertFalse(is_verified_fx(valid_fx, "GBP", "EUR"))

        zero_fx = FXConversion.model_construct(
            base_currency="USD",
            quote_currency="EUR",
            rate=0.0,
            source="Test",
            source_symbol="USDEUR=X",
            retrieved_at=STAMP,
        )
        self.assertFalse(is_verified_fx(zero_fx, "USD", "EUR"))

        neg_fx = FXConversion.model_construct(
            base_currency="USD",
            quote_currency="EUR",
            rate=-1.5,
            source="Test",
            source_symbol="USDEUR=X",
            retrieved_at=STAMP,
        )
        self.assertFalse(is_verified_fx(neg_fx, "USD", "EUR"))

        nan_fx = FXConversion.model_construct(
            base_currency="USD",
            quote_currency="EUR",
            rate=float("nan"),
            source="Test",
            source_symbol="USDEUR=X",
            retrieved_at=STAMP,
        )
        self.assertFalse(is_verified_fx(nan_fx, "USD", "EUR"))

    def test_fx_applied_only_to_monetary_metrics(self):
        """Cross-currency FX must normalize monetary values but never touch percentages or ratios."""
        fx = FXConversion(
            base_currency="USD",
            quote_currency="INR",
            rate=80.0,
            source="Test",
            source_symbol="USDINR=X",
            url="https://example.test",
            retrieved_at=STAMP,
        )
        company_a = make_company_data("AAPL", identifier="A", currency="USD", revenue=1000.0, pe_ratio=20.0)
        company_b = make_company_data("TCS", identifier="B", currency="INR", revenue=90_000.0, pe_ratio=25.0)

        metrics = build_comparison_metrics(company_a, company_b, fx_conversion=fx)
        by_name = {m.metric: m for m in metrics}

        rev = by_name["revenue"]
        self.assertEqual(rev.company_a_comparison_value, 80_000.0)
        self.assertEqual(rev.currency, "INR")
        self.assertTrue(rev.currency_comparable)
        self.assertEqual(rev.winner, ComparisonWinner.B)

        pe = by_name["pe_ratio"]
        self.assertIsNone(pe.fx_conversion)
        self.assertIsNone(pe.company_a_comparison_value)
        self.assertEqual(pe.company_a_value, 20.0)
        self.assertEqual(pe.company_b_value, 25.0)
        self.assertEqual(pe.winner, ComparisonWinner.A)

        pm = by_name["profit_margin"]
        self.assertIsNone(pm.fx_conversion)
        self.assertIsNone(pm.company_a_comparison_value)

    def test_financial_strength_negative_revenue_guard(self):
        """Negative revenue must not produce inverted financial strength factors."""
        bad_health = FinancialHealth(
            revenue=-500.0,
            profit_margin=-0.50,
            free_cash_flow=100.0,
            total_cash=200.0,
            total_debt=100.0,
        )
        score, factors = _financial_strength(bad_health)
        self.assertIsNone(score)
        self.assertEqual(factors, ["Profit margin was available."])

    def test_overall_advantage_tie_and_false_precision(self):
        """Overall advantage must handle ties and close category results honestly."""
        company_a = make_company_data("AAPL", identifier="A", pe_ratio=20.0)
        company_b = make_company_data("MSFT", identifier="B", pe_ratio=20.0)
        metrics = build_comparison_metrics(company_a, company_b)
        strength = build_financial_strength(company_a, company_b)
        momentum = build_momentum_score(company_a, company_b)
        categories = build_category_winners(metrics, strength, momentum)
        confidence = build_confidence(metrics, categories)

        winner, explanation = overall_advantage(categories, confidence)
        self.assertIn(winner, (ComparisonWinner.TIE, ComparisonWinner.INSUFFICIENT_DATA))
        self.assertTrue(len(explanation) > 0)


class TestComparisonAsyncOrchestration(unittest.IsolatedAsyncioTestCase):
    """Async orchestration and resilience checks for comparison engine."""

    async def asyncSetUp(self):
        self.orchestrator = ResearchOrchestrator(
            entity_service=FakeEntityService(),
            company_profile_service=FakeProfileService(),
            financial_health_service=FakeFinancialService(),
            history_service=FakeHistoryService(),
            news_service=FakeNewsService(),
            event_service=FakeEventService(),
            comparison_analysis_service=FakeAnalysisService(),
            fx_rate_service=FakeFXService(),
        )

    async def test_full_comparison_orchestration(self):
        """Orchestrate end-to-end comparison with validated contracts."""
        req = ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="AAPL", company_b="MSFT")
        resp = await self.orchestrator.research("comp-full-test", req)
        report = resp.company_comparison
        self.assertIsNotNone(report)
        self.assertEqual(report.company_a.ticker, "AAPL")
        self.assertEqual(report.company_b.ticker, "MSFT")
        self.assertTrue(len(report.metrics) >= 10)
        self.assertIsNotNone(report.financial_strength)
        self.assertIsNotNone(report.momentum)
        self.assertIsNotNone(report.comparison_confidence)

    async def test_same_resolved_ticker_rejection(self):
        """Comparing Apple and AAPL resolves to same ticker and fails fast."""
        req = ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="Apple", company_b="AAPL")
        with self.assertRaises(ResearchError) as ctx:
            await self.orchestrator.research("comp-same-ticker", req)
        self.assertEqual(ctx.exception.category, ErrorCategory.VALIDATION_ERROR)

    async def test_cross_currency_orchestration_with_fx(self):
        """Comparing USD and INR triggers verified FX conversion."""
        req = ResearchRequest(mode=ResearchMode.COMPANY_COMPARISON, company_a="AAPL", company_b="TCS")
        resp = await self.orchestrator.research("comp-fx-test", req)
        report = resp.company_comparison
        self.assertIsNotNone(report)
        self.assertEqual(len(report.fx_conversions), 1)
        self.assertEqual(report.fx_conversions[0].base_currency, "USD")
        self.assertEqual(report.fx_conversions[0].quote_currency, "INR")


if __name__ == "__main__":
    unittest.main()
