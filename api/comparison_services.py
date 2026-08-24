"""Deterministic Company Comparison services for QuantAI Phase 6.

The module reuses the cached entity, company-profile, financial, history, news,
and event adapters. It never asks an LLM to calculate a metric, winner, score,
period alignment, currency conversion, or confidence level.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .company_analysis_services import CompanyProfileResult, CompanyProfileService, FinancialHealthResult, FinancialHealthService, market_snapshot_from_profile
from .market_intelligence_services import EventRadarResult, HistoryResult, EventRadarService, PriceHistoryService, calculate_market_signal, unavailable_freshness
from .research_errors import ResearchError
from .research_schemas import (
    CompanyDeepAnalysisFreshness,
    ComparisonCategoryWinner,
    ComparisonConfidence,
    ComparisonIdentity,
    ComparisonMetric,
    ComparisonProvenance,
    ComparisonScore,
    ComparisonWinner,
    ErrorCategory,
    FinancialHealth,
    FreshnessRecord,
    FreshnessState,
    MarketSignal,
    MarketSnapshot,
    NewsItem,
    PeriodAlignment,
    ResearchEvent,
    ServiceState,
    SourceRecord,
)
from .research_services import CompanyIdentity, NewsDataResult, NewsService


@dataclass
class ComparisonCompanyData:
    identifier: str
    entity: CompanyIdentity
    identity: ComparisonIdentity
    market: MarketSnapshot | None = None
    financial: FinancialHealth | None = None
    momentum: MarketSignal | None = None
    news: list[NewsItem] = field(default_factory=list)
    events: list[ResearchEvent] = field(default_factory=list)
    freshness: CompanyDeepAnalysisFreshness | None = None
    sources: list[SourceRecord] = field(default_factory=list)
    warnings: list[ResearchError] = field(default_factory=list)
    states: dict[str, ServiceState] = field(default_factory=dict)


async def prepare_comparison_company(
    identifier: str,
    entity: CompanyIdentity,
    profile_service: CompanyProfileService,
    financial_service: FinancialHealthService,
    history_service: PriceHistoryService,
    news_service: NewsService,
    event_service: EventRadarService,
) -> ComparisonCompanyData:
    """Fetch one company’s independent deterministic sources with cache reuse."""

    profile: CompanyProfileResult | None = None
    profile_freshness = unavailable_freshness()
    warnings: list[ResearchError] = []
    sources: list[SourceRecord] = []
    states = {"company": ServiceState.UNAVAILABLE, "financials": ServiceState.NOT_REQUESTED, "history": ServiceState.NOT_REQUESTED, "news": ServiceState.NOT_REQUESTED, "events": ServiceState.NOT_REQUESTED}
    try:
        profile, profile_freshness = await profile_service.fetch(entity)
        states["company"] = profile.company_status
        states["governance"] = profile.governance_status
        if profile.company_source:
            sources.append(profile.company_source)
        if profile.governance_source:
            sources.append(profile.governance_source)
        if profile.warning:
            warnings.append(profile.warning)
    except Exception as error:
        warnings.append(ResearchError(category=ErrorCategory.COMPANY_UNAVAILABLE, detail=f"comparison profile failed: {type(error).__name__}", retryable=True))

    target = entity
    if profile and profile.overview:
        target = CompanyIdentity(
            symbol=entity.symbol,
            name=profile.overview.company_name or entity.name,
            exchange=profile.overview.exchange or entity.exchange,
            sector=profile.overview.sector or entity.sector,
            industry=profile.overview.industry or entity.industry,
            currency=profile.overview.currency or entity.currency,
            identifier_confidence=entity.identifier_confidence,
        )

    financial_task = asyncio.create_task(financial_service.fetch(target, profile))
    history_task = asyncio.create_task(history_service.fetch(target))
    news_task = asyncio.create_task(news_service.fetch(target))
    events_task = asyncio.create_task(event_service.fetch(target))
    financial_outcome, history_outcome, news_outcome, events_outcome = await asyncio.gather(financial_task, history_task, news_task, events_task, return_exceptions=True)

    financial: FinancialHealthResult | None = None
    financial_freshness = unavailable_freshness()
    if not isinstance(financial_outcome, BaseException):
        financial, financial_freshness = financial_outcome
        states["financials"] = financial.status
        if financial.source:
            sources.append(financial.source)
        if financial.warning:
            warnings.append(financial.warning)
    else:
        states["financials"] = ServiceState.UNAVAILABLE
        warnings.append(ResearchError(category=ErrorCategory.FINANCIALS_UNAVAILABLE, detail=f"comparison financial failed: {type(financial_outcome).__name__}", retryable=True))

    history: HistoryResult | None = None
    history_freshness = unavailable_freshness()
    if not isinstance(history_outcome, BaseException):
        history, history_freshness = history_outcome
        states["history"] = history.status
        if history.source:
            sources.append(history.source)
        if history.warning:
            warnings.append(history.warning)
    else:
        states["history"] = ServiceState.UNAVAILABLE
        warnings.append(ResearchError(category=ErrorCategory.HISTORY_UNAVAILABLE, detail=f"comparison history failed: {type(history_outcome).__name__}", retryable=True))

    news: NewsDataResult | None = None
    news_freshness = unavailable_freshness()
    if not isinstance(news_outcome, BaseException):
        news = news_outcome
        states["news"] = news.status
        sources.extend(news.sources)
        if news.warning:
            warnings.append(news.warning)
        if news.status != ServiceState.UNAVAILABLE:
            news_freshness = FreshnessRecord(state=FreshnessState.RECENT, retrieved_at=(news.sources[0].retrieved_at if news.sources else None), cache_scope="process_local")
    else:
        states["news"] = ServiceState.UNAVAILABLE
        warnings.append(ResearchError(category=ErrorCategory.NEWS_UNAVAILABLE, detail=f"comparison news failed: {type(news_outcome).__name__}", retryable=True))

    events: EventRadarResult | None = None
    events_freshness = unavailable_freshness()
    if not isinstance(events_outcome, BaseException):
        events, events_freshness = events_outcome
        states["events"] = events.status
        if events.source:
            sources.append(events.source)
        if events.warning:
            warnings.append(events.warning)
    else:
        states["events"] = ServiceState.UNAVAILABLE
        warnings.append(ResearchError(category=ErrorCategory.EVENTS_UNAVAILABLE, detail=f"comparison events failed: {type(events_outcome).__name__}", retryable=True))

    market = market_snapshot_from_profile(profile.info, target.currency, profile.retrieved_at) if profile else None
    momentum = calculate_market_signal(history.history.daily) if history and history.history and history.history.daily else None
    overview = profile.overview if profile else None
    identity = ComparisonIdentity(
        identifier=identifier,  # type: ignore[arg-type]
        company_name=overview.company_name if overview else target.name,
        ticker=target.symbol,
        exchange=overview.exchange if overview else target.exchange,
        sector=overview.sector if overview else target.sector,
        industry=overview.industry if overview else target.industry,
        country=overview.country if overview else None,
        currency=overview.currency if overview else target.currency,
        market_cap=overview.market_cap if overview else (market.market_cap if market else None),
    )
    freshness = _company_freshness(profile_freshness, financial_freshness, history_freshness, news_freshness, events_freshness)
    return ComparisonCompanyData(
        identifier=identifier,
        entity=target,
        identity=identity,
        market=market,
        financial=financial.financial_health if financial else None,
        momentum=momentum,
        news=news.items if news else [],
        events=events.events if events else [],
        freshness=freshness,
        sources=sources,
        warnings=warnings,
        states=states,
    )


def comparison_metric(
    metric: str,
    value_a: float | None,
    value_b: float | None,
    *,
    unit: str,
    higher_is_better: bool,
    currency_a: str | None,
    currency_b: str | None,
    period_a: str | None = None,
    period_b: str | None = None,
    source_a: SourceRecord | None = None,
    source_b: SourceRecord | None = None,
) -> ComparisonMetric:
    monetary = unit in {"currency", "per_share"}
    aligned = _period_alignment(period_a, period_b)
    currencies_match = not monetary or (currency_a is not None and currency_a == currency_b)
    note: str | None = None
    if monetary and not currencies_match:
        note = "CURRENCY_COMPARISON_UNAVAILABLE: no verified conversion rate was used."
    elif monetary and period_a and period_b and aligned != PeriodAlignment.ALIGNED:
        note = "Reporting periods are not sufficiently aligned for an absolute-value winner."
    elif aligned == PeriodAlignment.NOT_ALIGNED:
        note = "Reporting periods are not aligned; no winner is calculated."
    available = value_a is not None and value_b is not None
    period_safe = aligned != PeriodAlignment.NOT_ALIGNED
    if monetary and period_a and period_b:
        period_safe = aligned == PeriodAlignment.ALIGNED
    can_compare = available and currencies_match and period_safe
    winner = _winner(value_a, value_b, higher_is_better) if can_compare else ComparisonWinner.INSUFFICIENT_DATA
    difference = value_a - value_b if can_compare and value_a is not None and value_b is not None else None
    return ComparisonMetric(
        metric=metric,
        company_a_value=value_a,
        company_b_value=value_b,
        unit=unit,  # type: ignore[arg-type]
        winner=winner,
        difference=difference,
        difference_basis="company_a_minus_company_b" if difference is not None else None,
        currency=currency_a if currencies_match else None,
        currency_comparable=currencies_match,
        period_a=period_a,
        period_b=period_b,
        period_alignment=aligned,
        availability="available" if can_compare else ("partial" if value_a is not None or value_b is not None else "unavailable"),
        note=note,
        provenance_a=_provenance(source_a, period_a),
        provenance_b=_provenance(source_b, period_b),
    )


def build_comparison_metrics(company_a: ComparisonCompanyData, company_b: ComparisonCompanyData) -> list[ComparisonMetric]:
    fa, fb = company_a.financial, company_b.financial
    ma, mb = company_a.market, company_b.market
    financial_source_a = _source_of(company_a.sources, "financial")
    financial_source_b = _source_of(company_b.sources, "financial")
    market_source_a = _source_of(company_a.sources, "company")
    market_source_b = _source_of(company_b.sources, "company")
    ca, cb = company_a.identity.currency, company_b.identity.currency
    pa, pb = (fa.fiscal_period_end if fa else None), (fb.fiscal_period_end if fb else None)
    return [
        comparison_metric("market_cap", ma.market_cap if ma else None, mb.market_cap if mb else None, unit="currency", higher_is_better=True, currency_a=ca, currency_b=cb, source_a=market_source_a, source_b=market_source_b),
        comparison_metric("revenue", fa.revenue if fa else None, fb.revenue if fb else None, unit="currency", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("net_income", fa.net_income if fa else None, fb.net_income if fb else None, unit="currency", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("eps", fa.eps if fa else None, fb.eps if fb else None, unit="per_share", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("profit_margin", fa.profit_margin if fa else None, fb.profit_margin if fb else None, unit="percentage", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("operating_margin", fa.operating_margin if fa else None, fb.operating_margin if fb else None, unit="percentage", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("free_cash_flow", fa.free_cash_flow if fa else None, fb.free_cash_flow if fb else None, unit="currency", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("total_cash", fa.total_cash if fa else None, fb.total_cash if fb else None, unit="currency", higher_is_better=True, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("total_debt", fa.total_debt if fa else None, fb.total_debt if fb else None, unit="currency", higher_is_better=False, currency_a=ca, currency_b=cb, period_a=pa, period_b=pb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("pe_ratio", fa.pe_ratio if fa else None, fb.pe_ratio if fb else None, unit="ratio", higher_is_better=False, currency_a=ca, currency_b=cb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("price_to_sales", fa.price_to_sales if fa else None, fb.price_to_sales if fb else None, unit="ratio", higher_is_better=False, currency_a=ca, currency_b=cb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("dividend_yield", fa.dividend_yield if fa else None, fb.dividend_yield if fb else None, unit="percentage", higher_is_better=True, currency_a=ca, currency_b=cb, source_a=financial_source_a, source_b=financial_source_b),
        comparison_metric("momentum_score", company_a.momentum.score if company_a.momentum else None, company_b.momentum.score if company_b.momentum else None, unit="score", higher_is_better=True, currency_a=ca, currency_b=cb, source_a=_source_of(company_a.sources, "history"), source_b=_source_of(company_b.sources, "history")),
    ]


def build_financial_strength(company_a: ComparisonCompanyData, company_b: ComparisonCompanyData) -> ComparisonScore:
    score_a, factors_a = _financial_strength(company_a.financial)
    score_b, factors_b = _financial_strength(company_b.financial)
    return ComparisonScore(
        company_a_score=score_a,
        company_b_score=score_b,
        winner=_winner(score_a, score_b, True),
        factors_a=factors_a,
        factors_b=factors_b,
        methodology="Score uses available profitability, free-cash-flow margin, and net-cash-to-revenue observations. At least two validated dimensions are required; it is not an investment recommendation.",
    )


def build_momentum_score(company_a: ComparisonCompanyData, company_b: ComparisonCompanyData) -> ComparisonScore:
    score_a = company_a.momentum.score if company_a.momentum else None
    score_b = company_b.momentum.score if company_b.momentum else None
    return ComparisonScore(
        company_a_score=score_a,
        company_b_score=score_b,
        winner=_winner(score_a, score_b, True),
        factors_a=company_a.momentum.factors if company_a.momentum else [],
        factors_b=company_b.momentum.factors if company_b.momentum else [],
        methodology="Existing deterministic Market Intelligence momentum scores based on price trend, moving-average alignment, volume context, and disclosed volatility; not a trading signal.",
    )


def build_category_winners(metrics: list[ComparisonMetric], financial_strength: ComparisonScore, momentum: ComparisonScore) -> list[ComparisonCategoryWinner]:
    by_name = {metric.metric: metric for metric in metrics}
    def category(name: str, metric_names: list[str], fallback: ComparisonWinner = ComparisonWinner.INSUFFICIENT_DATA) -> ComparisonCategoryWinner:
        comparable = [by_name[item] for item in metric_names if item in by_name and by_name[item].winner != ComparisonWinner.INSUFFICIENT_DATA]
        winners = [metric.winner for metric in comparable]
        winner = _aggregate_winners(winners) if winners else fallback
        return ComparisonCategoryWinner(category=name, winner=winner, supporting_metrics=[metric.metric for metric in comparable], explanation=_category_explanation(name, winner, comparable))  # type: ignore[arg-type]
    return [
        ComparisonCategoryWinner(category="financial_strength", winner=financial_strength.winner, supporting_metrics=["financial_strength_score"], explanation="Deterministic financial-strength score from available profitability, cash-generation, and balance-sheet observations."),
        category("growth", ["revenue"], ComparisonWinner.INSUFFICIENT_DATA),
        category("profitability", ["profit_margin", "operating_margin"]),
        category("cash_generation", ["free_cash_flow"]),
        category("balance_sheet", ["total_cash", "total_debt"]),
        category("valuation", ["pe_ratio", "price_to_sales"]),
        ComparisonCategoryWinner(category="market_momentum", winner=momentum.winner, supporting_metrics=["momentum_score"] if momentum.winner != ComparisonWinner.INSUFFICIENT_DATA else [], explanation="Existing deterministic market-momentum comparison; not a trading recommendation."),
        category("dividend_profile", ["dividend_yield"]),
        ComparisonCategoryWinner(category="risk", winner=ComparisonWinner.INSUFFICIENT_DATA, supporting_metrics=[], explanation="Insufficient verified structured risk data for a deterministic risk winner."),
    ]


def build_confidence(metrics: list[ComparisonMetric], categories: list[ComparisonCategoryWinner]) -> ComparisonConfidence:
    comparable = [metric for metric in metrics if metric.winner != ComparisonWinner.INSUFFICIENT_DATA]
    aligned = [metric for metric in comparable if metric.period_alignment in {PeriodAlignment.ALIGNED, PeriodAlignment.PARTIALLY_ALIGNED}]
    categories_available = [category for category in categories if category.winner != ComparisonWinner.INSUFFICIENT_DATA]
    score = min(100, round((len(comparable) / max(1, len(metrics))) * 55 + (len(aligned) / max(1, len(comparable))) * 25 + (len(categories_available) / max(1, len(categories))) * 20))
    level = "high" if score >= 75 else "medium" if score >= 50 else "low" if score > 0 else "insufficient"
    reasons = [f"{len(comparable)} of {len(metrics)} metrics are safely comparable.", f"{len(categories_available)} of {len(categories)} category outcomes have deterministic evidence."]
    if any(not metric.currency_comparable for metric in metrics):
        reasons.append("Some monetary metrics use different currencies and were not converted.")
    if any(metric.period_alignment == PeriodAlignment.NOT_ALIGNED for metric in metrics):
        reasons.append("Some financial periods are not aligned and have no winner.")
    return ComparisonConfidence(score=score if score else None, level=level, reasons=reasons[:6])


def overall_advantage(categories: list[ComparisonCategoryWinner], confidence: ComparisonConfidence) -> tuple[ComparisonWinner, str]:
    if confidence.score is None or confidence.score < 50:
        return ComparisonWinner.INSUFFICIENT_DATA, "INSUFFICIENT_DATA: comparison coverage or alignment is too limited to determine an overall advantage."
    counts = {ComparisonWinner.A: 0, ComparisonWinner.B: 0}
    for category in categories:
        if category.winner in counts:
            counts[category.winner] += 1
    if counts[ComparisonWinner.A] == counts[ComparisonWinner.B]:
        return ComparisonWinner.TIE, "Deterministic category outcomes are balanced; no overall advantage is forced."
    leading = ComparisonWinner.A if counts[ComparisonWinner.A] > counts[ComparisonWinner.B] else ComparisonWinner.B
    if abs(counts[ComparisonWinner.A] - counts[ComparisonWinner.B]) < 2:
        return ComparisonWinner.INSUFFICIENT_DATA, "Category outcomes are too close to establish an overall advantage without false precision."
    return leading, f"{leading.value} leads in more available deterministic categories; this is not an investment recommendation."


def _company_freshness(company: FreshnessRecord, financials: FreshnessRecord, history: FreshnessRecord, news: FreshnessRecord, events: FreshnessRecord):
    from .research_schemas import CompanyDeepAnalysisFreshness
    return CompanyDeepAnalysisFreshness(company=company, financials=financials, governance=company, competitors=unavailable_freshness(), market=company, news=news, events=events, analysis=FreshnessRecord(state=FreshnessState.UNAVAILABLE, cache_scope="none"))


def _source_of(sources: list[SourceRecord], data_type: str) -> SourceRecord | None:
    return next((source for source in sources if source.data_type == data_type), None)


def _provenance(source: SourceRecord | None, as_of: str | None) -> ComparisonProvenance | None:
    return ComparisonProvenance(source=source.source, url=source.url, retrieved_at=source.retrieved_at, data_type=source.data_type, as_of=as_of) if source else None  # type: ignore[arg-type]


def _period_alignment(period_a: str | None, period_b: str | None) -> PeriodAlignment:
    if not period_a or not period_b:
        return PeriodAlignment.NOT_AVAILABLE
    if period_a == period_b:
        return PeriodAlignment.ALIGNED
    try:
        left = datetime.fromisoformat(period_a.replace("Z", "+00:00"))
        right = datetime.fromisoformat(period_b.replace("Z", "+00:00"))
        return PeriodAlignment.PARTIALLY_ALIGNED if abs((left - right).days) <= 183 else PeriodAlignment.NOT_ALIGNED
    except ValueError:
        return PeriodAlignment.NOT_ALIGNED


def _winner(value_a: float | int | None, value_b: float | int | None, higher_is_better: bool) -> ComparisonWinner:
    if value_a is None or value_b is None:
        return ComparisonWinner.INSUFFICIENT_DATA
    if abs(float(value_a) - float(value_b)) < 1e-9:
        return ComparisonWinner.TIE
    if higher_is_better:
        return ComparisonWinner.A if value_a > value_b else ComparisonWinner.B
    return ComparisonWinner.A if value_a < value_b else ComparisonWinner.B


def _financial_strength(financial: FinancialHealth | None) -> tuple[int | None, list[str]]:
    if not financial:
        return None, []
    dimensions: list[float] = []
    factors: list[str] = []
    if financial.profit_margin is not None:
        dimensions.append(_clip(50 + financial.profit_margin * 100, 0, 100))
        factors.append("Profit margin was available.")
    if financial.free_cash_flow is not None and financial.revenue not in {None, 0}:
        dimensions.append(_clip(50 + (financial.free_cash_flow / financial.revenue) * 100, 0, 100))
        factors.append("Free-cash-flow margin was available.")
    if financial.total_cash is not None and financial.total_debt is not None and financial.revenue not in {None, 0}:
        dimensions.append(_clip(50 + ((financial.total_cash - financial.total_debt) / financial.revenue) * 100, 0, 100))
        factors.append("Net cash relative to revenue was available.")
    return (round(sum(dimensions) / len(dimensions)) if len(dimensions) >= 2 else None, factors)


def _aggregate_winners(winners: list[ComparisonWinner]) -> ComparisonWinner:
    count_a, count_b = winners.count(ComparisonWinner.A), winners.count(ComparisonWinner.B)
    if count_a == count_b:
        return ComparisonWinner.TIE if winners else ComparisonWinner.INSUFFICIENT_DATA
    return ComparisonWinner.A if count_a > count_b else ComparisonWinner.B


def _category_explanation(name: str, winner: ComparisonWinner, metrics: list[ComparisonMetric]) -> str:
    if not metrics:
        return f"Insufficient validated {name.replace('_', ' ')} metrics for a winner."
    if winner == ComparisonWinner.INSUFFICIENT_DATA:
        return f"Available {name.replace('_', ' ')} metrics do not support a safe winner."
    if winner == ComparisonWinner.TIE:
        return f"Available {name.replace('_', ' ')} metric outcomes are balanced."
    return f"{winner.value} leads on more available deterministic {name.replace('_', ' ')} metrics."


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
