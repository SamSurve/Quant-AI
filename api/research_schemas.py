"""Stable typed contract for QuantAI's deterministic research workflow.

The models intentionally use explicit ``None`` and service status fields rather
than invented defaults. They are the public BFF contract; AgentOS markdown
remains a separate compatibility path for conversation.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ServiceState(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    NOT_REQUESTED = "not_requested"


class OverallState(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class IdentifierConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AMBIGUOUS = "ambiguous"


class ErrorCategory(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    AMBIGUOUS_ENTITY = "AMBIGUOUS_ENTITY"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    COMPANY_UNAVAILABLE = "COMPANY_UNAVAILABLE"
    FINANCIALS_UNAVAILABLE = "FINANCIALS_UNAVAILABLE"
    GOVERNANCE_UNAVAILABLE = "GOVERNANCE_UNAVAILABLE"
    COMPARISON_UNAVAILABLE = "COMPARISON_UNAVAILABLE"
    CURRENCY_COMPARISON_UNAVAILABLE = "CURRENCY_COMPARISON_UNAVAILABLE"
    HISTORY_UNAVAILABLE = "HISTORY_UNAVAILABLE"
    NEWS_UNAVAILABLE = "NEWS_UNAVAILABLE"
    EVENTS_UNAVAILABLE = "EVENTS_UNAVAILABLE"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ResearchMode(str, Enum):
    STANDARD = "standard"
    MARKET_INTELLIGENCE = "market_intelligence"
    COMPANY_DEEP_ANALYSIS = "company_deep_analysis"
    COMPANY_COMPARISON = "company_comparison"


class FreshnessState(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    RECENT = "recent"
    UNAVAILABLE = "unavailable"


class HistoryPeriod(str, Enum):
    ONE_DAY = "1D"
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    ONE_YEAR = "1Y"
    FIVE_YEARS = "5Y"


class ResearchRequest(BaseModel):
    """A deliberately small public request surface for deterministic research."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(default="", max_length=80, description="Company name or listed ticker for non-comparison modes.")
    company_a: str | None = Field(default=None, max_length=80, description="First company for comparison mode.")
    company_b: str | None = Field(default=None, max_length=80, description="Second company for comparison mode.")
    include_analysis: bool = Field(default=True, description="Request best-effort AI interpretation.")
    mode: ResearchMode = Field(default=ResearchMode.STANDARD, description="Backward-compatible typed research mode.")

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        return normalized

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> "ResearchRequest":
        if self.mode == ResearchMode.COMPANY_COMPARISON:
            company_a = " ".join((self.company_a or "").split())
            company_b = " ".join((self.company_b or "").split())
            if not company_a or not company_b:
                raise ValueError("Two company names or ticker symbols are required for comparison.")
            if company_a.upper() == company_b.upper():
                raise ValueError("Select two different companies for comparison.")
            self.company_a = company_a
            self.company_b = company_b
            return self
        if not self.query:
            raise ValueError("A company name or ticker is required.")
        return self


class CompanyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str | None = None
    exchange: str | None = None
    quote_type: str | None = None


class CompanyIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    identifier_confidence: IdentifierConfidence


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_price: float | None = None
    currency: str | None = None
    daily_change: float | None = None
    daily_change_percent: float | None = None
    volume: int | None = None
    market_cap: int | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    dividend_yield: float | None = None
    market_status: str | None = None
    as_of: str | None = None


class HistoryPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str | None = None
    publisher: str | None = None
    url: str | None = None
    published_at: str | None = None
    relevance: Literal["high", "medium", "low", "unknown"] = "unknown"
    sentiment: Literal["positive", "neutral", "negative"] | None = None


class ResearchEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    title: str
    date: str | None = None
    importance: Literal["high", "medium", "low", "unknown"] = "unknown"
    source: str | None = None


class FreshnessRecord(BaseModel):
    """Honest source freshness; process-local cache state is explicit."""

    model_config = ConfigDict(extra="forbid")

    state: FreshnessState
    retrieved_at: str | None = None
    as_of: str | None = None
    cache_scope: Literal["none", "process_local"] = "none"


class PriceHistoryBundle(BaseModel):
    """One intraday plus one long daily fetch supports local period selection."""

    model_config = ConfigDict(extra="forbid")

    intraday: list[HistoryPoint] = Field(default_factory=list)
    daily: list[HistoryPoint] = Field(default_factory=list)
    available_periods: list[HistoryPeriod] = Field(default_factory=list)
    default_period: HistoryPeriod = HistoryPeriod.ONE_MONTH
    freshness: FreshnessRecord


class MarketSignal(BaseModel):
    """A deterministic indicator summary, never a trading recommendation."""

    model_config = ConfigDict(extra="forbid")

    signal: Literal["BULLISH", "NEUTRAL", "BEARISH"] | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    confidence: int | None = Field(default=None, ge=0, le=100)
    factors: list[str] = Field(default_factory=list, max_length=6)
    explanation: str | None = Field(default=None, max_length=1_000)
    methodology: str = "Deterministic price, trend, volatility, and volume observations; not investment advice."


class MarketIntelligenceFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: FreshnessRecord
    market: FreshnessRecord
    history: FreshnessRecord
    news: FreshnessRecord
    events: FreshnessRecord
    analysis: FreshnessRecord


class MarketIntelligenceReport(BaseModel):
    """The additive Phase 4 payload; legacy root fields remain populated."""

    model_config = ConfigDict(extra="forbid")

    market_pulse: MarketSnapshot | None = None
    price_history: PriceHistoryBundle | None = None
    market_signal: MarketSignal | None = None
    recent_news: list[NewsItem] = Field(default_factory=list)
    event_radar: list[ResearchEvent] = Field(default_factory=list)
    executive_brief: "StructuredAnalysis | None" = None
    freshness: MarketIntelligenceFreshness


class StructuredAnalysis(BaseModel):
    """Validated interpretation only; deterministic data stays outside this model."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str | None = Field(default=None, max_length=1_200)
    what_is_happening: str | None = Field(default=None, max_length=1_000)
    bullish_factors: list[str] = Field(default_factory=list, max_length=5)
    bearish_factors: list[str] = Field(default_factory=list, max_length=5)
    risks: list[str] = Field(default_factory=list, max_length=5)
    catalysts: list[str] = Field(default_factory=list, max_length=5)
    what_to_watch: list[str] = Field(default_factory=list, max_length=5)
    market_sentiment: Literal["positive", "neutral", "negative", "mixed", "insufficient"] | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    ai_verdict: str | None = Field(default=None, max_length=500)


class CompanyOverview(BaseModel):
    """Factual company profile fields returned only when a source provides them."""

    model_config = ConfigDict(extra="forbid")

    company_name: str | None = None
    ticker: str
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    headquarters: str | None = None
    website: str | None = None
    business_description: str | None = Field(default=None, max_length=12_000)
    employees: int | None = None
    market_cap: int | None = None
    currency: str | None = None


class FinancialHealth(BaseModel):
    """Validated financial observations; values remain null when unavailable."""

    model_config = ConfigDict(extra="forbid")

    revenue: float | None = None
    net_income: float | None = None
    eps: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    free_cash_flow: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    pe_ratio: float | None = None
    price_to_sales: float | None = None
    dividend_yield: float | None = None
    return_on_equity: float | None = None
    return_on_assets: float | None = None
    currency: str | None = None
    fiscal_period_end: str | None = None


class LeadershipMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    title: str | None = None
    since: int | None = None


class GovernanceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ceo: LeadershipMember | None = None
    key_leadership: list[LeadershipMember] = Field(default_factory=list, max_length=8)
    notable_developments: list[str] = Field(default_factory=list, max_length=3)


class CompetitiveEvidence(BaseModel):
    """A deliberately conservative competitive-data boundary for the MVP."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "unavailable"] = "unavailable"
    competitors: list[str] = Field(default_factory=list, max_length=8)
    note: str = "Insufficient verified competitor data."


class CompanyValuationView(BaseModel):
    """Analytical classification only, separate from deterministic valuation inputs."""

    model_config = ConfigDict(extra="forbid")

    classification: Literal["UNDERVALUED", "FAIRLY_VALUED", "HIGHLY_VALUED", "INSUFFICIENT_DATA"] = "INSUFFICIENT_DATA"
    rationale: str | None = Field(default=None, max_length=1_200)
    evidence: list[str] = Field(default_factory=list, max_length=5)


class CompanyDeepAnalysisInterpretation(BaseModel):
    """Evidence-bound AI interpretation; factual source data lives outside this model."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str | None = Field(default=None, max_length=1_500)
    business_model: str | None = Field(default=None, max_length=1_500)
    financial_health: str | None = Field(default=None, max_length=1_500)
    growth_drivers: list[str] = Field(default_factory=list, max_length=6)
    competitive_position: str | None = Field(default=None, max_length=1_200)
    key_risks: list[str] = Field(default_factory=list, max_length=6)
    catalysts: list[str] = Field(default_factory=list, max_length=6)
    valuation_view: CompanyValuationView = Field(default_factory=CompanyValuationView)
    recent_developments: list[str] = Field(default_factory=list, max_length=5)
    what_to_watch: list[str] = Field(default_factory=list, max_length=6)
    overall_assessment: str | None = Field(default=None, max_length=1_200)
    confidence: Literal["low", "medium", "high"] | None = None


class CompanyDeepAnalysisFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: FreshnessRecord
    financials: FreshnessRecord
    governance: FreshnessRecord
    competitors: FreshnessRecord
    market: FreshnessRecord
    news: FreshnessRecord
    events: FreshnessRecord
    analysis: FreshnessRecord


class CompanyDeepAnalysisReport(BaseModel):
    """The additive Phase 5 payload; deterministic facts and interpretation stay distinct."""

    model_config = ConfigDict(extra="forbid")

    company_overview: CompanyOverview | None = None
    financial_health: FinancialHealth | None = None
    governance: GovernanceProfile | None = None
    competitive_evidence: CompetitiveEvidence = Field(default_factory=CompetitiveEvidence)
    market_context: MarketSnapshot | None = None
    recent_news: list[NewsItem] = Field(default_factory=list)
    events: list[ResearchEvent] = Field(default_factory=list)
    analyst_interpretation: CompanyDeepAnalysisInterpretation | None = None
    freshness: CompanyDeepAnalysisFreshness


class PeriodAlignment(str, Enum):
    ALIGNED = "ALIGNED"
    PARTIALLY_ALIGNED = "PARTIALLY_ALIGNED"
    NOT_ALIGNED = "NOT_ALIGNED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class ComparisonWinner(str, Enum):
    A = "A"
    B = "B"
    TIE = "TIE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ComparisonIdentity(BaseModel):
    """A source-backed identity record that cannot be confused with the peer."""

    model_config = ConfigDict(extra="forbid")

    identifier: Literal["A", "B"]
    company_name: str | None = None
    ticker: str
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    market_cap: int | None = None


class ComparisonProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    url: str | None = None
    retrieved_at: str | None = None
    data_type: Literal["entity", "market", "history", "company", "financial", "governance", "news", "event", "signal", "comparison"]
    as_of: str | None = None


class ComparisonMetric(BaseModel):
    """A single metric with explicit values, units, periods, and winner policy."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    company_a_value: float | None = None
    company_b_value: float | None = None
    unit: Literal["currency", "percentage", "ratio", "per_share", "count", "score"]
    winner: ComparisonWinner = ComparisonWinner.INSUFFICIENT_DATA
    difference: float | None = None
    difference_basis: str | None = None
    currency: str | None = None
    currency_comparable: bool = True
    period_a: str | None = None
    period_b: str | None = None
    period_alignment: PeriodAlignment = PeriodAlignment.NOT_AVAILABLE
    availability: Literal["available", "partial", "unavailable"] = "unavailable"
    note: str | None = None
    provenance_a: ComparisonProvenance | None = None
    provenance_b: ComparisonProvenance | None = None


class ComparisonScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_a_score: int | None = Field(default=None, ge=0, le=100)
    company_b_score: int | None = Field(default=None, ge=0, le=100)
    winner: ComparisonWinner = ComparisonWinner.INSUFFICIENT_DATA
    factors_a: list[str] = Field(default_factory=list, max_length=6)
    factors_b: list[str] = Field(default_factory=list, max_length=6)
    methodology: str


class ComparisonCategoryWinner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["financial_strength", "growth", "profitability", "cash_generation", "balance_sheet", "valuation", "market_momentum", "dividend_profile", "risk"]
    winner: ComparisonWinner = ComparisonWinner.INSUFFICIENT_DATA
    supporting_metrics: list[str] = Field(default_factory=list, max_length=5)
    explanation: str


class ComparisonConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int | None = Field(default=None, ge=0, le=100)
    level: Literal["low", "medium", "high", "insufficient"] = "insufficient"
    reasons: list[str] = Field(default_factory=list, max_length=6)


class CompanyComparisonInterpretation(BaseModel):
    """AI interpretation only; deterministic metrics and verdict stay outside this model."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str | None = Field(default=None, max_length=1_500)
    key_difference: str | None = Field(default=None, max_length=1_200)
    company_a_strengths: list[str] = Field(default_factory=list, max_length=6)
    company_b_strengths: list[str] = Field(default_factory=list, max_length=6)
    company_a_weaknesses: list[str] = Field(default_factory=list, max_length=6)
    company_b_weaknesses: list[str] = Field(default_factory=list, max_length=6)
    growth_comparison: str | None = Field(default=None, max_length=1_200)
    financial_comparison: str | None = Field(default=None, max_length=1_200)
    valuation_comparison: str | None = Field(default=None, max_length=1_200)
    risk_comparison: str | None = Field(default=None, max_length=1_200)
    market_comparison: str | None = Field(default=None, max_length=1_200)
    important_catalysts: list[str] = Field(default_factory=list, max_length=6)
    important_risks: list[str] = Field(default_factory=list, max_length=6)
    what_to_watch: list[str] = Field(default_factory=list, max_length=6)
    overall_assessment: str | None = Field(default=None, max_length=1_200)
    confidence: Literal["low", "medium", "high"] | None = None


class CompanyComparisonFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_a: CompanyDeepAnalysisFreshness
    company_b: CompanyDeepAnalysisFreshness
    comparison: FreshnessRecord
    analysis: FreshnessRecord


class ComparisonCompanyStatus(BaseModel):
    """Safe per-side status; it deliberately excludes source exception details."""

    model_config = ConfigDict(extra="forbid")

    identifier: Literal["A", "B"]
    overall: ServiceState
    company: ServiceState
    financials: ServiceState
    history: ServiceState
    news: ServiceState
    events: ServiceState
    message: str


class CompanyComparisonReport(BaseModel):
    """Additive Phase 6 payload; every A/B field remains explicitly isolated."""

    model_config = ConfigDict(extra="forbid")

    company_a: ComparisonIdentity
    company_b: ComparisonIdentity
    company_a_status: ComparisonCompanyStatus
    company_b_status: ComparisonCompanyStatus
    market_a: MarketSnapshot | None = None
    market_b: MarketSnapshot | None = None
    financial_a: FinancialHealth | None = None
    financial_b: FinancialHealth | None = None
    momentum_a: MarketSignal | None = None
    momentum_b: MarketSignal | None = None
    company_a_news: list[NewsItem] = Field(default_factory=list)
    company_b_news: list[NewsItem] = Field(default_factory=list)
    company_a_events: list[ResearchEvent] = Field(default_factory=list)
    company_b_events: list[ResearchEvent] = Field(default_factory=list)
    metrics: list[ComparisonMetric] = Field(default_factory=list, max_length=24)
    financial_strength: ComparisonScore
    momentum: ComparisonScore
    category_winners: list[ComparisonCategoryWinner] = Field(default_factory=list, max_length=9)
    overall_advantage: ComparisonWinner = ComparisonWinner.INSUFFICIENT_DATA
    overall_explanation: str
    comparison_confidence: ComparisonConfidence
    competitive_data_note: str = "COMPETITIVE_DATA_LIMITED: Insufficient verified structured competitor data."
    analyst_interpretation: CompanyComparisonInterpretation | None = None
    freshness: CompanyComparisonFreshness


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    url: str | None = None
    retrieved_at: str
    data_type: Literal["entity", "market", "history", "company", "financial", "governance", "competitor", "news", "event", "signal", "comparison", "analysis"]


class ServiceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall: OverallState
    market: ServiceState
    financials: ServiceState = ServiceState.NOT_REQUESTED
    governance: ServiceState = ServiceState.NOT_REQUESTED
    competitors: ServiceState = ServiceState.NOT_REQUESTED
    history: ServiceState = ServiceState.NOT_REQUESTED
    news: ServiceState
    events: ServiceState = ServiceState.NOT_REQUESTED
    company: ServiceState
    ai: ServiceState


class ResearchWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: ErrorCategory
    message: str
    retryable: bool = False


class ResearchResponse(BaseModel):
    """Public version-one typed result for a single-company research request."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    query: str
    company: CompanyIdentity | None = None
    candidates: list[CompanyCandidate] = Field(default_factory=list)
    market: MarketSnapshot | None = None
    history: list[HistoryPoint] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    events: list[ResearchEvent] = Field(default_factory=list)
    analysis: StructuredAnalysis | None = None
    market_intelligence: MarketIntelligenceReport | None = None
    company_deep_analysis: CompanyDeepAnalysisReport | None = None
    company_comparison: CompanyComparisonReport | None = None
    sources: list[SourceRecord] = Field(default_factory=list)
    status: ServiceStatus
    warnings: list[ResearchWarning] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Safe error envelope used by all BFF validation and protection failures."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    category: ErrorCategory
    message: str
    retryable: bool = False
