"""Unit tests for Quant-AI pure-Python technical indicators engine."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.quant import TechnicalIndicators


class TestTechnicalIndicators(unittest.TestCase):
    def test_calculate_sma(self):
        """Simple Moving Average computes accurate sliding window average."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        sma = TechnicalIndicators.calculate_sma(data, period=3)
        self.assertEqual(sma[:2], [None, None])
        self.assertEqual(sma[2:], [20.0, 30.0, 40.0])

    def test_calculate_sma_invalid_period(self):
        """SMA raises ValueError on zero or negative period."""
        with self.assertRaises(ValueError):
            TechnicalIndicators.calculate_sma([1.0, 2.0], period=0)

    def test_calculate_ema(self):
        """Exponential Moving Average computes exponentially weighted series."""
        data = [10.0, 11.0, 12.0, 13.0, 14.0]
        ema = TechnicalIndicators.calculate_ema(data, period=3)
        self.assertEqual(ema[:2], [None, None])
        self.assertAlmostEqual(ema[2], 11.0, places=2)
        self.assertIsNotNone(ema[3])
        self.assertIsNotNone(ema[4])

    def test_calculate_rsi(self):
        """Relative Strength Index calculates bounded 0-100 values."""
        data = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
        rsi = TechnicalIndicators.calculate_rsi(data, period=14)
        for val in rsi:
            if val is not None:
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 100.0)


if __name__ == "__main__":
    unittest.main()
