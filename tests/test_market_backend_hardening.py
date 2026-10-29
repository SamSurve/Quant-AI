"""Automated regression and hardening tests for Market Intelligence Backend (M05)."""

import asyncio
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.market_intelligence_services import (
    MarketPulseService,
    PriceHistoryService,
    EventRadarService,
    normalize_symbol,
    _call_with_retry,
)
from api.research_schemas import (
    CompanyIdentity,
    FreshnessState,
    ServiceState,
    ErrorCategory,
    IdentifierConfidence,
)


class TestMarketBackendHardening(unittest.TestCase):
    def test_symbol_normalization(self):
        """Symbol normalization must uppercase, strip whitespace, and clamp length."""
        self.assertEqual(normalize_symbol("  aapl  "), "AAPL")
        self.assertEqual(normalize_symbol("spy"), "SPY")
        self.assertEqual(normalize_symbol("brk.b"), "BRK.B")
        self.assertEqual(normalize_symbol("tmpv.ns"), "TMPV.NS")

    def test_call_with_retry_succeeds_first_try(self):
        """Clean call succeeds without retry."""
        async def run_test():
            calls = 0
            def operation():
                nonlocal calls
                calls += 1
                return {"status": "ok"}

            res = await _call_with_retry(operation, op_name="test_op", symbol="AAPL", max_retries=2)
            self.assertEqual(res, {"status": "ok"})
            self.assertEqual(calls, 1)

        asyncio.run(run_test())

    def test_call_with_retry_recovers_from_transient_failure(self):
        """Call recovers on transient error and succeeds on second attempt."""
        async def run_test():
            calls = 0
            def operation():
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise RuntimeError("HTTP 429 Too Many Requests")
                return {"status": "recovered"}

            res = await _call_with_retry(operation, op_name="test_op", symbol="AAPL", max_retries=2, base_delay=0.01)
            self.assertEqual(res, {"status": "recovered"})
            self.assertEqual(calls, 2)

        asyncio.run(run_test())

    def test_call_with_retry_aborts_on_permanent_error(self):
        """Permanent non-transient error must fail fast without wasteful retries."""
        async def run_test():
            calls = 0
            def operation():
                nonlocal calls
                calls += 1
                raise ValueError("Invalid Ticker Symbol Specification")

            with self.assertRaises(ValueError):
                await _call_with_retry(operation, op_name="test_op", symbol="INVALID", max_retries=2, base_delay=0.01)
            self.assertEqual(calls, 1)

        asyncio.run(run_test())

    def test_market_pulse_filters_invalid_prices(self):
        """Negative, zero, and NaN prices must not be surfaced as valid market prices."""
        async def run_test():
            service = MarketPulseService()
            entity = CompanyIdentity(symbol="TEST", identifier_confidence=IdentifierConfidence.HIGH)

            with patch.object(service, "_info", return_value={"regularMarketPrice": -50.0, "currency": "USD"}):
                result, freshness = await service.fetch(entity)
                self.assertEqual(result.status, ServiceState.AVAILABLE)
                self.assertIsNone(result.market.current_price)

            with patch.object(service, "_info", return_value={"regularMarketPrice": float("nan"), "currency": "USD"}):
                result, freshness = await service.fetch(entity)
                self.assertEqual(result.status, ServiceState.AVAILABLE)
                self.assertIsNone(result.market.current_price)

        asyncio.run(run_test())

    def test_market_pulse_cache_hit_freshness(self):
        """Second fetch for same symbol must report CACHED freshness."""
        async def run_test():
            service = MarketPulseService()
            entity = CompanyIdentity(symbol="MOCK", identifier_confidence=IdentifierConfidence.HIGH)

            with patch.object(service, "_info", return_value={"regularMarketPrice": 150.0, "currency": "USD"}):
                res1, fresh1 = await service.fetch(entity)
                self.assertEqual(fresh1.state, FreshnessState.LIVE)

                res2, fresh2 = await service.fetch(entity)
                self.assertEqual(fresh2.state, FreshnessState.CACHED)
                self.assertEqual(res2.market.current_price, 150.0)

        asyncio.run(run_test())

    def test_market_pulse_empty_response_honest_unavailable(self):
        """Empty response from provider must honestly return UNAVAILABLE status without synthetic zero."""
        async def run_test():
            service = MarketPulseService()
            entity = CompanyIdentity(symbol="EMPTY", identifier_confidence=IdentifierConfidence.HIGH)

            with patch.object(service, "_info", return_value={}):
                result, freshness = await service.fetch(entity)
                self.assertEqual(result.status, ServiceState.UNAVAILABLE)
                self.assertIsNone(result.market)
                self.assertIsNotNone(result.warning)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
