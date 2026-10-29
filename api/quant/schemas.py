"""Pydantic schemas for the Quant-AI Quantitative Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class StrategyType(str, Enum):
    SMA_CROSSOVER = "sma_crossover"
    RSI_MEAN_REVERSION = "rsi_mean_reversion"
    MOMENTUM_BREAKOUT = "momentum_breakout"
    BOLLINGER_REVERSAL = "bollinger_reversal"


class PriceBar(BaseModel):
    timestamp: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: int | None = None


# --- Technical Indicators ---

class IndicatorSeriesPoint(BaseModel):
    timestamp: str
    value: float | None = None


class BollingerBandPoint(BaseModel):
    timestamp: str
    upper: float | None = None
    middle: float | None = None
    lower: float | None = None
    percent_b: float | None = None
    bandwidth: float | None = None


class MACDPoint(BaseModel):
    timestamp: str
    macd: float | None = None
    signal: float | None = None
    histogram: float | None = None


class StochasticPoint(BaseModel):
    timestamp: str
    k: float | None = None
    d: float | None = None


class IndicatorsSummary(BaseModel):
    latest_close: float
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    rsi_condition: str | None = None  # "OVERSOLD", "OVERBOUGHT", "NEUTRAL"
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    macd_crossover: str | None = None  # "BULLISH_CROSSOVER", "BEARISH_CROSSOVER", "NEUTRAL"
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    bollinger_bandwidth: float | None = None
    atr_14: float | None = None
    atr_percent: float | None = None
    stochastic_k: float | None = None
    stochastic_d: float | None = None
    trend_verdict: str  # "STRONG_UPTREND", "WEAK_UPTREND", "NEUTRAL", "WEAK_DOWNTREND", "STRONG_DOWNTREND"


class TechnicalIndicatorsRequest(BaseModel):
    symbol: str | None = None
    bars: list[PriceBar] | None = None
    period: str = "1Y"


class TechnicalIndicatorsResponse(BaseModel):
    symbol: str
    summary: IndicatorsSummary
    series_timestamps: list[str]
    close_series: list[float]
    sma_20: list[float | None]
    sma_50: list[float | None]
    sma_200: list[float | None]
    ema_12: list[float | None]
    ema_26: list[float | None]
    rsi_14: list[float | None]
    macd: list[MACDPoint]
    bollinger: list[BollingerBandPoint]
    atr: list[float | None]
    stochastic: list[StochasticPoint]


# --- Risk Analysis ---

class RiskAnalysisRequest(BaseModel):
    symbol: str | None = None
    bars: list[PriceBar] | None = None
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.045  # 4.5% annual
    portfolio_value: float = 100_000.0
    risk_per_trade_pct: float = 0.01  # 1% standard risk


class RiskMetrics(BaseModel):
    annualized_volatility_pct: float
    daily_volatility_pct: float
    parametric_var_95_daily_pct: float
    parametric_var_99_daily_pct: float
    historical_var_95_daily_pct: float
    historical_var_99_daily_pct: float
    cvar_95_daily_pct: float  # Expected Shortfall
    cvar_99_daily_pct: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float | None = None
    beta_to_benchmark: float | None = None
    alpha_annualized_pct: float | None = None
    kelly_criterion_fraction: float | None = None
    half_kelly_fraction: float | None = None
    recommended_position_value: float | None = None
    recommended_shares: int | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    risk_rating: str  # "LOW", "MODERATE", "ELEVATED", "HIGH", "EXTREME"


class RiskAnalysisResponse(BaseModel):
    symbol: str
    as_of: str
    metrics: RiskMetrics
    drawdown_series: list[dict[str, Any]]
    return_distribution: dict[str, Any]
    explanation: str


# --- Backtesting ---

class BacktestRequest(BaseModel):
    symbol: str | None = None
    bars: list[PriceBar] | None = None
    strategy: StrategyType = StrategyType.SMA_CROSSOVER
    initial_capital: float = 100_000.0
    commission_bps: float = 5.0  # 5 bps = 0.05%
    slippage_bps: float = 3.0    # 3 bps = 0.03%
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class TradeRecord(BaseModel):
    trade_id: int
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: int
    pnl: float
    pnl_percent: float
    return_pct: float
    holding_days: int
    exit_reason: str  # "SIGNAL", "STOP_LOSS", "TAKE_PROFIT", "END_OF_DATA"


class EquityCurvePoint(BaseModel):
    timestamp: str
    equity: float
    cash: float
    benchmark_equity: float
    drawdown_pct: float


class BacktestSummary(BaseModel):
    initial_capital: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float
    buy_and_hold_return_pct: float
    annualized_volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float | None = None
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_trade_return_pct: float
    average_holding_days: float
    exposure_pct: float


class BacktestResponse(BaseModel):
    symbol: str
    strategy: str
    strategy_description: str
    summary: BacktestSummary
    equity_curve: list[EquityCurvePoint]
    trades: list[TradeRecord]


# --- Monte Carlo ---

class MonteCarloRequest(BaseModel):
    symbol: str | None = None
    bars: list[PriceBar] | None = None
    num_simulations: int = 500
    days_forward: int = 252
    initial_price: float | None = None


class MonteCarloSimulationPoint(BaseModel):
    day: int
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class MonteCarloResponse(BaseModel):
    symbol: str
    initial_price: float
    days_forward: int
    num_simulations: int
    annualized_drift_pct: float
    annualized_volatility_pct: float
    paths_summary: list[MonteCarloSimulationPoint]
    expected_terminal_price: float
    median_terminal_price: float
    probability_of_profit_pct: float
    probability_of_drawdown_20_pct: float
