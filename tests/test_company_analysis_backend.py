"""Automated tests for Company Deep Analysis backend pipeline, financial statement normalization, and ratio validation (M07)."""

import asyncio
import math
import sys
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.company_analysis_services import (
    CompanyProfileService,
    FinancialHealthService,
    CompanyProfileResult,
    FinancialHealthResult,
    StatementPeriod,
    CalculatedRatios,
    FinancialStatementsData,
    CompanyAnalysisBundle,
    compute_financial_ratios,
    _calculate_series_yoy,
    _extract_statement_periods,
    _statement_value,
    _statement_value_for_col,
    fetch_company_analysis_bundle,
)
from api.research_schemas import (
    CompanyIdentity,
    CompanyOverview,
    GovernanceProfile,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    ServiceState,
    ErrorCategory,
    IdentifierConfidence,
    SourceRecord,
)
from api.research_errors import ResearchError


class TestCompanyAnalysisBackend(unittest.TestCase):
    # -------------------------------------------------------------------------
    # 1. Symbol Validation Rejection
    # -------------------------------------------------------------------------
    def test_symbol_validation_rejection(self):
        """Invalid symbols must fail fast with VALIDATION_ERROR without provider calls."""
        async def run_test():
            profile_service = CompanyProfileService()
            fin_service = FinancialHealthService()

            bad_entities = [
                CompanyIdentity(symbol="BAD;SYMBOL", identifier_confidence=IdentifierConfidence.HIGH),
                CompanyIdentity(symbol="AAPL<script>", identifier_confidence=IdentifierConfidence.HIGH),
                CompanyIdentity(symbol="TOOLONGTICKERNAME123", identifier_confidence=IdentifierConfidence.HIGH),
            ]

            for entity in bad_entities:
                p_res, p_fresh = await profile_service.fetch(entity)
                self.assertEqual(p_res.company_status, ServiceState.UNAVAILABLE)
                self.assertEqual(p_res.warning.category, ErrorCategory.VALIDATION_ERROR)
                self.assertEqual(p_fresh.state, FreshnessState.UNAVAILABLE)

                f_res, f_fresh = await fin_service.fetch(entity, p_res)
                self.assertEqual(f_res.status, ServiceState.UNAVAILABLE)
                self.assertEqual(f_res.warning.category, ErrorCategory.VALIDATION_ERROR)
                self.assertEqual(f_fresh.state, FreshnessState.UNAVAILABLE)

        asyncio.run(run_test())

    # -------------------------------------------------------------------------
    # 2. Statement Label Normalization (CamelCase vs Spaced)
    # -------------------------------------------------------------------------
    def test_statement_normalization_case_and_spaces(self):
        """Statement parser must match CamelCase, spaced, and underscore labels reliably."""
        df_camel = pd.DataFrame(
            {"2025-09-30": [100_000.0, 60_000.0, 25_000.0]},
            index=["TotalRevenue", "OperatingIncome", "NetIncomeCommonStockholders"]
        )
        self.assertEqual(_statement_value(df_camel, ["Total Revenue", "Operating Revenue"]), 100_000.0)
        self.assertEqual(_statement_value(df_camel, ["Operating Income"]), 60_000.0)
        self.assertEqual(_statement_value(df_camel, ["Net Income", "Net Income Common Stockholders"]), 25_000.0)

        df_spaced = pd.DataFrame(
            {"2025-09-30": [200_000.0, 120_000.0, 50_000.0]},
            index=["Total Revenue", "Operating Income", "Net Income"]
        )
        self.assertEqual(_statement_value(df_spaced, ["TotalRevenue"]), 200_000.0)
        self.assertEqual(_statement_value(df_spaced, ["OperatingIncome"]), 120_000.0)
        self.assertEqual(_statement_value(df_spaced, ["NetIncome"]), 50_000.0)

    # -------------------------------------------------------------------------
    # 3. Ratio Calculation With Clean Financial Inputs
    # -------------------------------------------------------------------------
    def test_ratios_calculation_with_clean_data(self):
        """compute_financial_ratios must calculate margins, liquidity, returns, and solvency correctly."""
        income_df = pd.DataFrame(
            {
                "2025-09-30": [100_000.0, 60_000.0, 40_000.0, 30_000.0, 20_000.0],
                "2024-09-30": [80_000.0, 50_000.0, 30_000.0, 22_000.0, 15_000.0],
            },
            index=["Total Revenue", "Cost of Revenue", "Gross Profit", "Operating Income", "Net Income"]
        )
        balance_df = pd.DataFrame(
            {
                "2025-09-30": [150_000.0, 60_000.0, 30_000.0, 20_000.0, 30_000.0, 40_000.0, 80_000.0],
            },
            index=[
                "Total Assets", "Current Assets", "Cash And Cash Equivalents",
                "Receivables", "Current Liabilities", "Total Debt", "Stockholders Equity"
            ]
        )
        cash_df = pd.DataFrame(
            {
                "2025-09-30": [28_000.0, -5_000.0, 23_000.0],
            },
            index=["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow"]
        )
        info = {
            "trailingPE": 25.0,
            "priceToSalesTrailing12Months": 5.0,
            "marketCap": 500_000.0,
        }

        ratios = compute_financial_ratios(income_df, balance_df, cash_df, info)

        # Margins: Gross = 40%, Operating = 30%, Net = 20%, FCF = 23%
        self.assertAlmostEqual(ratios.gross_margin, 40.0)
        self.assertAlmostEqual(ratios.operating_margin, 30.0)
        self.assertAlmostEqual(ratios.net_margin, 20.0)
        self.assertAlmostEqual(ratios.fcf_margin, 23.0)

        # Liquidity: Current = 60k/30k = 2.0; Quick = (30k+20k)/30k = 1.67
        self.assertAlmostEqual(ratios.current_ratio, 2.0)
        self.assertAlmostEqual(ratios.quick_ratio, 50_000.0 / 30_000.0)

        # Solvency: Debt to equity = 40k/80k = 0.5
        self.assertAlmostEqual(ratios.debt_to_equity, 0.5)

        # Returns: ROE = 20k/80k = 25%; ROA = 20k/150k = 13.33%
        self.assertAlmostEqual(ratios.return_on_equity, 25.0)
        self.assertAlmostEqual(ratios.return_on_assets, (20_000.0 / 150_000.0) * 100.0)

        # YoY Growth: Rev = (100k - 80k)/80k = +25%; Net Income = (20k - 15k)/15k = +33.33%
        self.assertAlmostEqual(ratios.revenue_growth_yoy, 25.0)
        self.assertAlmostEqual(ratios.net_income_growth_yoy, (5_000.0 / 15_000.0) * 100.0)

    # -------------------------------------------------------------------------
    # 4. Zero Division & Edge Case Handling
    # -------------------------------------------------------------------------
    def test_ratios_calculation_division_by_zero_guard(self):
        """Zero denominators must never raise ZeroDivisionError and safely return None."""
        income_df = pd.DataFrame({"2025-09-30": [0.0, 0.0, 0.0]}, index=["Total Revenue", "Operating Income", "Net Income"])
        balance_df = pd.DataFrame({"2025-09-30": [0.0, 0.0, 0.0, 0.0]}, index=["Total Assets", "Current Liabilities", "Stockholders Equity", "Total Debt"])
        cash_df = pd.DataFrame({"2025-09-30": [0.0]}, index=["Free Cash Flow"])

        ratios = compute_financial_ratios(income_df, balance_df, cash_df, {})

        self.assertIsNone(ratios.gross_margin)
        self.assertIsNone(ratios.operating_margin)
        self.assertIsNone(ratios.net_margin)
        self.assertIsNone(ratios.current_ratio)
        self.assertIsNone(ratios.quick_ratio)
        self.assertIsNone(ratios.debt_to_equity)
        self.assertIsNone(ratios.return_on_equity)
        self.assertIsNone(ratios.return_on_assets)
        self.assertIsNone(ratios.revenue_growth_yoy)

    # -------------------------------------------------------------------------
    # 5. Legitimate Negative Financial Values
    # -------------------------------------------------------------------------
    def test_ratios_calculation_legitimate_negative_values(self):
        """Legitimate negative financial figures (losses, negative FCF, debt adjustments) must be preserved."""
        income_df = pd.DataFrame(
            {"2025-09-30": [50_000.0, -10_000.0]},
            index=["Total Revenue", "Net Income"]
        )
        cash_df = pd.DataFrame(
            {"2025-09-30": [-15_000.0]},
            index=["Free Cash Flow"]
        )
        ratios = compute_financial_ratios(income_df, None, cash_df, {})

        self.assertAlmostEqual(ratios.net_margin, -20.0)
        self.assertEqual(ratios.free_cash_flow, -15_000.0)
        self.assertAlmostEqual(ratios.fcf_margin, -30.0)

    # -------------------------------------------------------------------------
    # 6. NaN & Infinite Filtering
    # -------------------------------------------------------------------------
    def test_nan_and_infinite_filtering(self):
        """NaN and Infinite values must be filtered out to None."""
        df_dirty = pd.DataFrame(
            {"2025-09-30": [float("nan"), float("inf"), -float("inf"), 500.0]},
            index=["Total Revenue", "Operating Income", "Net Income", "Gross Profit"]
        )
        self.assertIsNone(_statement_value(df_dirty, ["Total Revenue"]))
        self.assertIsNone(_statement_value(df_dirty, ["Operating Income"]))
        self.assertIsNone(_statement_value(df_dirty, ["Net Income"]))
        self.assertEqual(_statement_value(df_dirty, ["Gross Profit"]), 500.0)

    # -------------------------------------------------------------------------
    # 7. Multi-Period Series Extraction
    # -------------------------------------------------------------------------
    def test_multi_period_series_extraction(self):
        """_extract_statement_periods must extract chronological statement records with metadata."""
        cols = [pd.Timestamp("2025-09-30"), pd.Timestamp("2024-09-30")]
        df = pd.DataFrame(
            [
                [100_000.0, 80_000.0],
                [20_000.0, 15_000.0],
            ],
            index=["Total Revenue", "Net Income"],
            columns=cols
        )
        periods = _extract_statement_periods(df, "annual", "USD")
        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0].period_end, "2025-09-30")
        self.assertEqual(periods[0].period_type, "annual")
        self.assertEqual(periods[0].currency, "USD")
        self.assertEqual(periods[0].revenue, 100_000.0)
        self.assertEqual(periods[0].net_income, 20_000.0)
        self.assertEqual(periods[1].period_end, "2024-09-30")
        self.assertEqual(periods[1].revenue, 80_000.0)

    # -------------------------------------------------------------------------
    # 8. YoY Growth Calculation
    # -------------------------------------------------------------------------
    def test_yoy_growth_calculation(self):
        """_calculate_series_yoy must calculate percentage change across 2 periods."""
        cols = [pd.Timestamp("2025"), pd.Timestamp("2024")]
        df_growth = pd.DataFrame([[120.0, 100.0]], index=["Total Revenue"], columns=cols)
        self.assertAlmostEqual(_calculate_series_yoy(df_growth, ["Total Revenue"]), 20.0)

        df_decline = pd.DataFrame([[80.0, 100.0]], index=["Total Revenue"], columns=cols)
        self.assertAlmostEqual(_calculate_series_yoy(df_decline, ["Total Revenue"]), -20.0)

        # Single period returns None
        df_single = pd.DataFrame([[100.0]], index=["Total Revenue"], columns=[pd.Timestamp("2025")])
        self.assertIsNone(_calculate_series_yoy(df_single, ["Total Revenue"]))

    # -------------------------------------------------------------------------
    # 9. Partial Failure Resilience
    # -------------------------------------------------------------------------
    def test_partial_failure_resilience(self):
        """If one statement times out or fails, surviving statements remain usable with PARTIAL status."""
        async def run_test():
            fin_service = FinancialHealthService()
            entity = CompanyIdentity(symbol="PARTIAL", identifier_confidence=IdentifierConfidence.HIGH)

            income_df = pd.DataFrame({"2025-09-30": [100_000.0]}, index=["Total Revenue"])
            balance_df = pd.DataFrame({"2025-09-30": [50_000.0]}, index=["Total Assets"])

            with patch.object(fin_service, "_statement") as mock_stmt:
                async def mock_load(_sym, statement, freq="yearly"):
                    if statement == "income":
                        return income_df
                    if statement == "balance":
                        return balance_df
                    # Cash statement fails
                    return ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail="Cash statement timeout")

                mock_stmt.side_effect = mock_load

                res, fresh = await fin_service.fetch(entity, None)
                self.assertEqual(res.status, ServiceState.PARTIAL)
                self.assertIsNotNone(res.financial_health)
                self.assertEqual(res.financial_health.revenue, 100_000.0)
                self.assertIsNotNone(res.warning)
                self.assertEqual(res.warning.category, ErrorCategory.FINANCIALS_UNAVAILABLE)

        asyncio.run(run_test())

    # -------------------------------------------------------------------------
    # 10. Unified Pipeline Bundle Verification
    # -------------------------------------------------------------------------
    def test_fetch_company_analysis_bundle_pipeline(self):
        """fetch_company_analysis_bundle aggregates verified profile, financials, and ratios."""
        async def run_test():
            entity = CompanyIdentity(symbol="MOCK", identifier_confidence=IdentifierConfidence.HIGH)
            mock_profile = CompanyProfileResult(
                overview=CompanyOverview(company_name="Mock Corp", ticker="MOCK", exchange="NYSE", sector="Industrials", currency="USD"),
                governance=GovernanceProfile(),
                info={"marketCap": 1_000_000, "currency": "USD"},
                company_status=ServiceState.AVAILABLE,
                governance_status=ServiceState.AVAILABLE,
                warning=None,
                company_source=SourceRecord(source="Yahoo Finance", url="https://example.test", retrieved_at="2026-10-29", data_type="company"),
                governance_source=None,
                retrieved_at="2026-10-29T00:00:00Z",
            )
            mock_financial = FinancialHealthResult(
                financial_health=FinancialHealth(revenue=500_000.0, net_income=50_000.0, currency="USD"),
                status=ServiceState.AVAILABLE,
                warning=None,
                source=SourceRecord(source="Yahoo Finance", url="https://example.test", retrieved_at="2026-10-29", data_type="financial"),
                retrieved_at="2026-10-29T00:00:00Z",
                statements=FinancialStatementsData(reporting_currency="USD"),
                calculated_ratios=CalculatedRatios(net_margin=10.0),
            )

            p_service = MagicMock(spec=CompanyProfileService)
            p_service.fetch = AsyncMock(return_value=(mock_profile, FreshnessRecord(state=FreshnessState.LIVE)))

            f_service = MagicMock(spec=FinancialHealthService)
            f_service.fetch = AsyncMock(return_value=(mock_financial, FreshnessRecord(state=FreshnessState.LIVE)))

            bundle = await fetch_company_analysis_bundle("MOCK", profile_service=p_service, financial_service=f_service)
            self.assertEqual(bundle.company.symbol, "MOCK")
            self.assertEqual(bundle.overview.company_name, "Mock Corp")
            self.assertEqual(bundle.financial_health.revenue, 500_000.0)
            self.assertEqual(bundle.ratios.net_margin, 10.0)
            self.assertEqual(bundle.profile_status, ServiceState.AVAILABLE)
            self.assertEqual(bundle.financial_status, ServiceState.AVAILABLE)
            self.assertEqual(len(bundle.sources), 2)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
