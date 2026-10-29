"""Automated tests for Company Deep Analysis UI, Jinja2 rendering, and HTMX statement partials (M08)."""

import asyncio
import sys
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.index import app
from api.company_analysis_services import (
    CompanyAnalysisBundle,
    StatementPeriod,
    CalculatedRatios,
    FinancialStatementsData,
)
from api.research_schemas import (
    CompanyIdentity,
    CompanyOverview,
    GovernanceProfile,
    LeadershipMember,
    FinancialHealth,
    ServiceState,
    IdentifierConfidence,
    SourceRecord,
)


class TestCompanyDeepAnalysisUI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _mock_bundle(self) -> CompanyAnalysisBundle:
        company = CompanyIdentity(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            currency="USD",
            identifier_confidence=IdentifierConfidence.HIGH,
        )
        overview = CompanyOverview(
            company_name="Apple Inc.",
            ticker="AAPL",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            headquarters="Cupertino, California, United States",
            website="https://www.apple.com",
            business_description="Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.",
            employees=161000,
            market_cap=3450000000000,
            currency="USD",
        )
        governance = GovernanceProfile(
            ceo=LeadershipMember(name="Tim Cook", title="Chief Executive Officer", since=2011),
            key_leadership=[
                LeadershipMember(name="Tim Cook", title="Chief Executive Officer", since=2011),
                LeadershipMember(name="Luca Maestri", title="Chief Financial Officer", since=2014),
            ],
        )
        financial_health = FinancialHealth(
            revenue=391035000000.0,
            net_income=93736000000.0,
            eps=6.08,
            profit_margin=0.2397,
            operating_margin=0.3117,
            free_cash_flow=108811000000.0,
            total_cash=29942000000.0,
            total_debt=106629000000.0,
            pe_ratio=34.5,
            price_to_sales=8.82,
            dividend_yield=0.0045,
            return_on_equity=1.45,
            return_on_assets=0.28,
            currency="USD",
            fiscal_period_end="2025-09-30T00:00:00Z",
        )
        statements = FinancialStatementsData(
            reporting_currency="USD",
            annual_income=[
                StatementPeriod(
                    period_end="2025-09-30",
                    period_type="annual",
                    currency="USD",
                    revenue=391035000000.0,
                    cost_of_revenue=210352000000.0,
                    gross_profit=180683000000.0,
                    operating_income=123216000000.0,
                    net_income=93736000000.0,
                    ebitda=134600000000.0,
                    diluted_eps=6.08,
                ),
                StatementPeriod(
                    period_end="2024-09-30",
                    period_type="annual",
                    currency="USD",
                    revenue=383285000000.0,
                    cost_of_revenue=214137000000.0,
                    gross_profit=169148000000.0,
                    operating_income=114301000000.0,
                    net_income=96995000000.0,
                    ebitda=129800000000.0,
                    diluted_eps=6.13,
                ),
            ],
            annual_balance=[
                StatementPeriod(
                    period_end="2025-09-30",
                    period_type="annual",
                    currency="USD",
                    cash_and_equivalents=29942000000.0,
                    current_assets=152985000000.0,
                    total_assets=364980000000.0,
                    current_liabilities=145308000000.0,
                    total_debt=106629000000.0,
                    total_liabilities=308030000000.0,
                    stockholders_equity=56950000000.0,
                )
            ],
            annual_cashflow=[
                StatementPeriod(
                    period_end="2025-09-30",
                    period_type="annual",
                    currency="USD",
                    operating_cash_flow=118264000000.0,
                    capital_expenditure=9453000000.0,
                    free_cash_flow=108811000000.0,
                )
            ],
        )
        ratios = CalculatedRatios(
            gross_margin=46.21,
            operating_margin=31.51,
            net_margin=23.97,
            free_cash_flow=108811000000.0,
            fcf_margin=27.83,
            current_ratio=1.05,
            quick_ratio=0.88,
            debt_to_equity=1.87,
            debt_to_assets=0.29,
            return_on_equity=164.59,
            return_on_assets=25.68,
            revenue_growth_yoy=2.02,
            net_income_growth_yoy=-3.36,
            pe_ratio=34.5,
            price_to_sales=8.82,
            price_to_book=60.58,
        )
        return CompanyAnalysisBundle(
            company=company,
            overview=overview,
            governance=governance,
            financial_health=financial_health,
            statements=statements,
            ratios=ratios,
            market_context=None,
            profile_status=ServiceState.AVAILABLE,
            financial_status=ServiceState.AVAILABLE,
            governance_status=ServiceState.AVAILABLE,
            warning=None,
            sources=[
                SourceRecord(source="Yahoo Finance", url="https://finance.yahoo.com", retrieved_at="2026-10-29", data_type="company")
            ],
            retrieved_at="2026-10-29T16:00:00Z",
        )

    # -------------------------------------------------------------------------
    # 1. Full Page Rendering & Absence of Fabricated Placeholders
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_page_valid_symbol(self, mock_fetch):
        """Full /analysis page renders verified company profile, metrics, statements, and ratios."""
        mock_fetch.return_value = self._mock_bundle()

        resp = self.client.get("/analysis?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text

        # Real profile facts
        self.assertIn("Apple Inc.", html)
        self.assertIn("Cupertino, California", html)
        self.assertIn("161,000", html)
        self.assertIn("Tim Cook", html)

        # Real financial metrics
        self.assertIn("$391.04B", html)  # Revenue
        self.assertIn("$93.74B", html)   # Net Income
        self.assertIn("$108.81B", html)  # Free Cash Flow

        # Statement explorer table
        self.assertIn("Financial Statement Explorer", html)
        self.assertIn("2025-09-30", html)
        self.assertIn("2024-09-30", html)
        self.assertIn("Total Revenue", html)

        # Ratios
        self.assertIn("Deterministic Financial Ratios", html)
        self.assertIn("46.21%", html)  # Gross Margin
        self.assertIn("31.51%", html)  # Operating Margin

        # VERIFY REMOVAL OF OLD FABRICATED PLACEHOLDERS
        self.assertNotIn("34.2x", html)
        self.assertNotIn("30.7%", html)
        self.assertNotIn("Strong (A+)", html)
        self.assertNotIn("Industry avg: 28.5x", html)
        self.assertNotIn("Scheduled for M07/M08", html)

    # -------------------------------------------------------------------------
    # 2. Symbol Validation Rejection
    # -------------------------------------------------------------------------
    def test_analysis_page_invalid_symbol(self):
        """Malformed symbols must display a clear validation alert without server errors."""
        resp = self.client.get("/analysis?symbol=BAD<SCRIPT>")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Invalid Ticker Symbol", resp.text)
        self.assertIn("Invalid ticker symbol format", resp.text)

    # -------------------------------------------------------------------------
    # 3. HTMX Statement Partials (Income, Balance, Cash Flow)
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_statement_partial_income(self, mock_fetch):
        """HTMX statement partial returns rendered Income Statement table."""
        mock_fetch.return_value = self._mock_bundle()

        resp = self.client.get("/analysis/statement?symbol=AAPL&type=income&freq=annual")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Income Statement", html)
        self.assertIn("Total Revenue", html)
        self.assertIn("Gross Profit", html)
        self.assertIn("Net Income", html)
        self.assertIn("$391.04B", html)

    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_statement_partial_balance(self, mock_fetch):
        """HTMX statement partial returns rendered Balance Sheet table."""
        mock_fetch.return_value = self._mock_bundle()

        resp = self.client.get("/analysis/statement?symbol=AAPL&type=balance&freq=annual")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Balance Sheet", html)
        self.assertIn("Cash & Cash Equivalents", html)
        self.assertIn("Total Assets", html)
        self.assertIn("Total Debt", html)
        self.assertIn("Stockholders' Equity", html)
        self.assertIn("$364.98B", html)

    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_statement_partial_cashflow(self, mock_fetch):
        """HTMX statement partial returns rendered Cash Flow statement table."""
        mock_fetch.return_value = self._mock_bundle()

        resp = self.client.get("/analysis/statement?symbol=AAPL&type=cashflow&freq=annual")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Cash Flow", html)
        self.assertIn("Operating Cash Flow", html)
        self.assertIn("Capital Expenditure", html)
        self.assertIn("Free Cash Flow", html)
        self.assertIn("$118.26B", html)

    # -------------------------------------------------------------------------
    # 4. Empty Statement Fallback
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_statement_partial_empty(self, mock_fetch):
        """Empty statement records display honest empty state without crashing."""
        bundle = self._mock_bundle()
        # Clear statement data
        object.__setattr__(bundle, "statements", FinancialStatementsData(reporting_currency="USD"))
        mock_fetch.return_value = bundle

        resp = self.client.get("/analysis/statement?symbol=AAPL&type=income&freq=quarterly")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("No quarterly income statement periods available", html)

    # -------------------------------------------------------------------------
    # 5. Legitimate Negative Financial Values (Net Losses)
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_legitimate_negative_financials(self, mock_fetch):
        """Legitimate negative values (net loss, negative FCF) render with negative styles."""
        bundle = self._mock_bundle()
        object.__setattr__(
            bundle,
            "financial_health",
            FinancialHealth(
                revenue=50_000_000.0,
                net_income=-15_000_000.0,
                free_cash_flow=-20_000_000.0,
                currency="USD",
            ),
        )
        mock_fetch.return_value = bundle

        resp = self.client.get("/analysis?symbol=LOSS")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("-$15.00M", html)
        self.assertIn("-$20.00M", html)
        self.assertIn("change-negative", html)

    # -------------------------------------------------------------------------
    # 6. Missing Optional Profile Fields
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_missing_optional_profile_fields(self, mock_fetch):
        """Missing optional profile fields (description, HQ, employees) render cleanly without crashing."""
        company = CompanyIdentity(symbol="SLIM", identifier_confidence=IdentifierConfidence.HIGH)
        overview = CompanyOverview(ticker="SLIM", company_name="Slim Corp", currency="USD")
        bundle = CompanyAnalysisBundle(
            company=company,
            overview=overview,
            governance=None,
            financial_health=None,
            statements=None,
            ratios=None,
            market_context=None,
            profile_status=ServiceState.AVAILABLE,
            financial_status=ServiceState.UNAVAILABLE,
            governance_status=ServiceState.UNAVAILABLE,
            warning=None,
            sources=[],
            retrieved_at="2026-10-29T16:00:00Z",
        )
        mock_fetch.return_value = bundle

        resp = self.client.get("/analysis?symbol=SLIM")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Slim Corp", html)
        self.assertIn("Unavailable", html)

    # -------------------------------------------------------------------------
    # 7. Empty Governance Leadership Handling
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_governance_empty_leadership(self, mock_fetch):
        """When corporate governance has no listed officers, render honest empty box."""
        bundle = self._mock_bundle()
        object.__setattr__(bundle, "governance", GovernanceProfile(ceo=None, key_leadership=[]))
        mock_fetch.return_value = bundle

        resp = self.client.get("/analysis?symbol=AAPL")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("Corporate officer disclosures are not reported", html)

    # -------------------------------------------------------------------------
    # 8. Statement Partial Quarterly Frequency
    # -------------------------------------------------------------------------
    @patch("api.web.fetch_company_analysis_bundle")
    def test_analysis_statement_partial_quarterly_freq(self, mock_fetch):
        """HTMX statement partial correctly displays quarterly period headers."""
        bundle = self._mock_bundle()
        q_income = [
            StatementPeriod(
                period_end="2025-06-30",
                period_type="quarterly",
                currency="USD",
                revenue=85_777_000_000.0,
                net_income=21_448_000_000.0,
            )
        ]
        object.__setattr__(bundle.statements, "quarterly_income", q_income)
        mock_fetch.return_value = bundle

        resp = self.client.get("/analysis/statement?symbol=AAPL&type=income&freq=quarterly")
        self.assertEqual(resp.status_code, 200)
        html = resp.text
        self.assertIn("2025-06-30", html)
        self.assertIn("$85.78B", html)
        self.assertIn("Quarterly", html)


if __name__ == "__main__":
    unittest.main()
