"""High-precision technical indicators engine for Quant-AI.

Implements standard industry formulas for technical analysis without external
heavy C dependencies, with robust boundary protection and zero-division safety.
"""

from __future__ import annotations

import math
from typing import Sequence
from .schemas import (
    BollingerBandPoint,
    IndicatorsSummary,
    MACDPoint,
    PriceBar,
    StochasticPoint,
    TechnicalIndicatorsResponse,
)


class TechnicalIndicators:
    """Computes technical indicator series and institutional summaries."""

    @staticmethod
    def calculate_sma(series: Sequence[float], period: int) -> list[float | None]:
        """Simple Moving Average."""
        if period <= 0:
            raise ValueError("Period must be positive")
        result: list[float | None] = []
        running_sum = 0.0
        for i, val in enumerate(series):
            running_sum += val
            if i >= period:
                running_sum -= series[i - period]
            if i >= period - 1:
                result.append(round(running_sum / period, 4))
            else:
                result.append(None)
        return result

    @staticmethod
    def calculate_ema(series: Sequence[float], period: int) -> list[float | None]:
        """Exponential Moving Average using standard 2 / (period + 1) multiplier."""
        if period <= 0:
            raise ValueError("Period must be positive")
        result: list[float | None] = [None] * len(series)
        if len(series) < period:
            return result

        k = 2.0 / (period + 1)
        # First EMA value is the SMA of the first `period` elements
        initial_sma = sum(series[:period]) / period
        result[period - 1] = round(initial_sma, 4)

        prev_ema = initial_sma
        for i in range(period, len(series)):
            val = series[i]
            current_ema = (val * k) + (prev_ema * (1.0 - k))
            result[i] = round(current_ema, 4)
            prev_ema = current_ema

        return result

    @staticmethod
    def calculate_rsi(closes: Sequence[float], period: int = 14) -> list[float | None]:
        """Relative Strength Index using J. Welles Wilder's smoothing method."""
        if period <= 0:
            raise ValueError("Period must be positive")
        result: list[float | None] = [None] * len(closes)
        if len(closes) <= period:
            return result

        gains: list[float] = []
        losses: list[float] = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            if diff > 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))

        # First average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0.0:
            result[period] = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            result[period] = round(100.0 - (100.0 / (1.0 + rs)), 2)

        # Subsequent values using Wilder's smoothing
        for i in range(period + 1, len(closes)):
            gain = gains[i - 1]
            loss = losses[i - 1]
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0.0:
                result[i] = 100.0 if avg_gain > 0 else 50.0
            else:
                rs = avg_gain / avg_loss
                result[i] = round(100.0 - (100.0 / (1.0 + rs)), 2)

        return result

    @classmethod
    def calculate_macd(
        cls,
        closes: Sequence[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> list[MACDPoint]:
        """Moving Average Convergence Divergence."""
        timestamps = [str(i) for i in range(len(closes))]
        fast_ema = cls.calculate_ema(closes, fast_period)
        slow_ema = cls.calculate_ema(closes, slow_period)

        macd_raw: list[float | None] = []
        for f, s in zip(fast_ema, slow_ema):
            if f is not None and s is not None:
                macd_raw.append(f - s)
            else:
                macd_raw.append(None)

        # Extract non-None MACD values to compute signal EMA
        valid_indices = [i for i, v in enumerate(macd_raw) if v is not None]
        signal_raw: list[float | None] = [None] * len(closes)

        if len(valid_indices) >= signal_period:
            valid_macd = [macd_raw[i] for i in valid_indices]  # type: ignore
            signal_ema = cls.calculate_ema(valid_macd, signal_period)
            for idx, s_val in zip(valid_indices, signal_ema):
                signal_raw[idx] = s_val

        points: list[MACDPoint] = []
        for i in range(len(closes)):
            m = macd_raw[i]
            s = signal_raw[i]
            h = round(m - s, 4) if (m is not None and s is not None) else None
            points.append(
                MACDPoint(
                    timestamp=timestamps[i],
                    macd=round(m, 4) if m is not None else None,
                    signal=round(s, 4) if s is not None else None,
                    histogram=h,
                )
            )
        return points

    @classmethod
    def calculate_bollinger_bands(
        cls,
        closes: Sequence[float],
        period: int = 20,
        num_std: float = 2.0,
    ) -> list[BollingerBandPoint]:
        """Bollinger Bands with %B and Bandwidth."""
        sma = cls.calculate_sma(closes, period)
        points: list[BollingerBandPoint] = []

        for i, val in enumerate(closes):
            mid = sma[i]
            if mid is None or i < period - 1:
                points.append(BollingerBandPoint(timestamp=str(i)))
                continue

            window = closes[i - period + 1 : i + 1]
            variance = sum((x - mid) ** 2 for x in window) / period
            std_dev = math.sqrt(variance)

            upper = round(mid + (num_std * std_dev), 4)
            lower = round(mid - (num_std * std_dev), 4)
            bandwidth = round((upper - lower) / mid, 4) if mid != 0 else None
            percent_b = (
                round((val - lower) / (upper - lower), 4)
                if (upper - lower) != 0
                else 0.5
            )

            points.append(
                BollingerBandPoint(
                    timestamp=str(i),
                    upper=upper,
                    middle=round(mid, 4),
                    lower=lower,
                    percent_b=percent_b,
                    bandwidth=bandwidth,
                )
            )
        return points

    @staticmethod
    def calculate_atr(bars: Sequence[PriceBar], period: int = 14) -> list[float | None]:
        """Average True Range using Wilder's smoothing."""
        if len(bars) == 0:
            return []
        result: list[float | None] = [None] * len(bars)
        if len(bars) < period:
            return result

        true_ranges: list[float] = []
        for i in range(len(bars)):
            high = bars[i].high if bars[i].high is not None else bars[i].close
            low = bars[i].low if bars[i].low is not None else bars[i].close
            if i == 0:
                tr = high - low
            else:
                prev_close = bars[i - 1].close
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close),
                )
            true_ranges.append(tr)

        initial_atr = sum(true_ranges[:period]) / period
        result[period - 1] = round(initial_atr, 4)

        prev_atr = initial_atr
        for i in range(period, len(bars)):
            current_atr = (prev_atr * (period - 1) + true_ranges[i]) / period
            result[i] = round(current_atr, 4)
            prev_atr = current_atr

        return result

    @staticmethod
    def calculate_stochastic(
        bars: Sequence[PriceBar],
        k_period: int = 14,
        d_period: int = 3,
    ) -> list[StochasticPoint]:
        """Stochastic Oscillator %K and %D."""
        n = len(bars)
        raw_k: list[float | None] = [None] * n
        for i in range(k_period - 1, n):
            window = bars[i - k_period + 1 : i + 1]
            highs = [b.high if b.high is not None else b.close for b in window]
            lows = [b.low if b.low is not None else b.close for b in window]
            highest_high = max(highs)
            lowest_low = min(lows)
            curr_close = bars[i].close

            denom = highest_high - lowest_low
            if denom == 0:
                raw_k[i] = 50.0
            else:
                raw_k[i] = round(((curr_close - lowest_low) / denom) * 100.0, 2)

        # %D is SMA of %K
        points: list[StochasticPoint] = []
        for i in range(n):
            k_val = raw_k[i]
            d_val: float | None = None
            if i >= (k_period - 1) + (d_period - 1):
                valid_k_subset = [
                    raw_k[j] for j in range(i - d_period + 1, i + 1) if raw_k[j] is not None
                ]
                if len(valid_k_subset) == d_period:
                    d_val = round(sum(valid_k_subset) / d_period, 2)

            points.append(
                StochasticPoint(
                    timestamp=bars[i].timestamp,
                    k=k_val,
                    d=d_val,
                )
            )
        return points

    @classmethod
    def compute_all(
        cls,
        symbol: str,
        bars: Sequence[PriceBar],
    ) -> TechnicalIndicatorsResponse:
        """Computes all technical indicators and constructs an institutional response."""
        if not bars:
            raise ValueError("Bars cannot be empty")

        timestamps = [b.timestamp for b in bars]
        closes = [b.close for b in bars]
        latest_close = closes[-1]

        sma_20 = cls.calculate_sma(closes, 20)
        sma_50 = cls.calculate_sma(closes, 50)
        sma_200 = cls.calculate_sma(closes, 200)
        ema_12 = cls.calculate_ema(closes, 12)
        ema_26 = cls.calculate_ema(closes, 26)
        rsi_14 = cls.calculate_rsi(closes, 14)
        macd_points = cls.calculate_macd(closes, 12, 26, 9)
        # Fix timestamps in macd_points
        for i, pt in enumerate(macd_points):
            pt.timestamp = timestamps[i]

        bollinger_points = cls.calculate_bollinger_bands(closes, 20, 2.0)
        for i, pt in enumerate(bollinger_points):
            pt.timestamp = timestamps[i]

        atr = cls.calculate_atr(bars, 14)
        stochastic = cls.calculate_stochastic(bars, 14, 3)

        # Latest summary values
        latest_sma20 = sma_20[-1]
        latest_sma50 = sma_50[-1]
        latest_sma200 = sma_200[-1]
        latest_ema12 = ema_12[-1]
        latest_ema26 = ema_26[-1]
        latest_rsi = rsi_14[-1]
        latest_macd = macd_points[-1].macd
        latest_signal = macd_points[-1].signal
        latest_hist = macd_points[-1].histogram
        latest_bb = bollinger_points[-1]
        latest_atr = atr[-1]
        latest_stoch = stochastic[-1]

        # Determine RSI condition
        rsi_condition = "NEUTRAL"
        if latest_rsi is not None:
            if latest_rsi >= 70:
                rsi_condition = "OVERBOUGHT"
            elif latest_rsi <= 30:
                rsi_condition = "OVERSOLD"

        # Determine MACD crossover
        macd_crossover = "NEUTRAL"
        if len(macd_points) >= 2:
            prev_m = macd_points[-2].macd
            prev_s = macd_points[-2].signal
            curr_m = latest_macd
            curr_s = latest_signal
            if (
                prev_m is not None
                and prev_s is not None
                and curr_m is not None
                and curr_s is not None
            ):
                if prev_m <= prev_s and curr_m > curr_s:
                    macd_crossover = "BULLISH_CROSSOVER"
                elif prev_m >= prev_s and curr_m < curr_s:
                    macd_crossover = "BEARISH_CROSSOVER"

        # Determine overall trend verdict
        trend_score = 0
        if latest_sma20 is not None:
            trend_score += 1 if latest_close > latest_sma20 else -1
        if latest_sma50 is not None:
            trend_score += 1 if latest_close > latest_sma50 else -1
        if latest_sma200 is not None:
            trend_score += 2 if latest_close > latest_sma200 else -2
        if latest_sma20 is not None and latest_sma50 is not None:
            trend_score += 1 if latest_sma20 > latest_sma50 else -1
        if latest_hist is not None:
            trend_score += 1 if latest_hist > 0 else -1

        if trend_score >= 4:
            trend_verdict = "STRONG_UPTREND"
        elif trend_score >= 1:
            trend_verdict = "WEAK_UPTREND"
        elif trend_score <= -4:
            trend_verdict = "STRONG_DOWNTREND"
        elif trend_score <= -1:
            trend_verdict = "WEAK_DOWNTREND"
        else:
            trend_verdict = "NEUTRAL"

        atr_pct = (
            round((latest_atr / latest_close) * 100.0, 2)
            if (latest_atr and latest_close)
            else None
        )

        summary = IndicatorsSummary(
            latest_close=latest_close,
            sma_20=latest_sma20,
            sma_50=latest_sma50,
            sma_200=latest_sma200,
            ema_12=latest_ema12,
            ema_26=latest_ema26,
            rsi_14=latest_rsi,
            rsi_condition=rsi_condition,
            macd=latest_macd,
            macd_signal=latest_signal,
            macd_histogram=latest_hist,
            macd_crossover=macd_crossover,
            bollinger_upper=latest_bb.upper,
            bollinger_middle=latest_bb.middle,
            bollinger_lower=latest_bb.lower,
            bollinger_bandwidth=latest_bb.bandwidth,
            atr_14=latest_atr,
            atr_percent=atr_pct,
            stochastic_k=latest_stoch.k,
            stochastic_d=latest_stoch.d,
            trend_verdict=trend_verdict,
        )

        return TechnicalIndicatorsResponse(
            symbol=symbol,
            summary=summary,
            series_timestamps=timestamps,
            close_series=closes,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            ema_12=ema_12,
            ema_26=ema_26,
            rsi_14=rsi_14,
            macd=macd_points,
            bollinger=bollinger_points,
            atr=atr,
            stochastic=stochastic,
        )
