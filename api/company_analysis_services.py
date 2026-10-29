"""Deterministic company and financial adapters for QuantAI Company Deep Analysis.

This module exposes only source-provided company/profile/statement data. It
does not infer competitors, market share, leadership changes, or unavailable
financial metrics. Those fields remain null, empty, or explicitly unavailable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import math
import re
from typing import Any

import yfinance as yf

from .market_intelligence_services import (
    _call_with_retry,
    _freshness,
    _quote_url,
    normalize_symbol,
    unavailable_freshness,
)
from .research_cache import AsyncTTLCache
from .research_errors import ResearchError
from .research_schemas import (
    CompanyIdentity,
    CompanyOverview,
    CompetitiveEvidence,
    ErrorCategory,
    FinancialHealth,
    FreshnessRecord,
    GovernanceProfile,
    IdentifierConfidence,
    LeadershipMember,
    MarketSnapshot,
    ServiceState,
    SourceRecord,
)
from .research_services import EXTERNAL_TIMEOUT_SECONDS, _optional_float, _optional_int, dividend_yield_fraction, utc_stamp

LOGGER = logging.getLogger("quantai.company_analysis")

COMPANY_PROFILE_TTL_SECONDS = 60 * 60
FINANCIALS_TTL_SECONDS = 60 * 60 * 6


def _source(data_type: str, symbol: str, retrieved_at: str) -> SourceRecord:
    return SourceRecord(
        source="Yahoo Finance via yfinance",
        url=_quote_url(symbol),
        retrieved_at=retrieved_at,
        data_type=data_type,  # type: ignore[arg-type]
    )


def _normalize_statement_label(label: str) -> str:
    """Normalize label by removing spaces, underscores, and dashes, lowering case."""
    return re.sub(r"[^a-zA-Z0-9]", "", str(label)).lower()


@dataclass(frozen=True)
class StatementPeriod:
    """A single normalized reporting period for a financial statement."""
    period_end: str
    period_type: str  # "annual" or "quarterly"
    currency: str | None = None
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    ebitda: float | None = None
    diluted_eps: float | None = None
    total_assets: float | None = None
    current_assets: float | None = None
    cash_and_equivalents: float | None = None
    total_liabilities: float | None = None
    current_liabilities: float | None = None
    total_debt: float | None = None
    stockholders_equity: float | None = None
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None


@dataclass(frozen=True)
class CalculatedRatios:
    """Deterministically computed valuation, profitability, and solvency ratios."""
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    free_cash_flow: float | None = None
    fcf_margin: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    debt_to_equity: float | None = None
    debt_to_assets: float | None = None
    return_on_equity: float | None = None
    return_on_assets: float | None = None
    revenue_growth_yoy: float | None = None
    net_income_growth_yoy: float | None = None
    pe_ratio: float | None = None
    price_to_sales: float | None = None
    price_to_book: float | None = None


@dataclass(frozen=True)
class FinancialStatementsData:
    """Multi-period annual and quarterly statement records with verified reporting currency."""
    reporting_currency: str | None
    annual_income: list[StatementPeriod] = field(default_factory=list)
    quarterly_income: list[StatementPeriod] = field(default_factory=list)
    annual_balance: list[StatementPeriod] = field(default_factory=list)
    quarterly_balance: list[StatementPeriod] = field(default_factory=list)
    annual_cashflow: list[StatementPeriod] = field(default_factory=list)
    quarterly_cashflow: list[StatementPeriod] = field(default_factory=list)


@dataclass(frozen=True)
class CompanyProfileResult:
    overview: CompanyOverview | None
    governance: GovernanceProfile | None
    info: dict[str, Any]
    company_status: ServiceState
    governance_status: ServiceState
    warning: ResearchError | None
    company_source: SourceRecord | None
    governance_source: SourceRecord | None
    retrieved_at: str | None


@dataclass(frozen=True)
class FinancialHealthResult:
    financial_health: FinancialHealth | None
    status: ServiceState
    warning: ResearchError | None
    source: SourceRecord | None
    retrieved_at: str | None
    statements: FinancialStatementsData | None = None
    calculated_ratios: CalculatedRatios | None = None


@dataclass(frozen=True)
class CompanyAnalysisBundle:
    """Aggregated, verified company profile and financial statements bundle for UI consumption."""
    company: CompanyIdentity
    overview: CompanyOverview | None
    governance: GovernanceProfile | None
    financial_health: FinancialHealth | None
    statements: FinancialStatementsData | None
    ratios: CalculatedRatios | None
    market_context: MarketSnapshot | None
    profile_status: ServiceState
    financial_status: ServiceState
    governance_status: ServiceState
    warning: ResearchError | None
    sources: list[SourceRecord]
    retrieved_at: str | None


class CompanyProfileService:
    """Fetch company profile and source-provided officer information once."""

    def __init__(self, cache: AsyncTTLCache[CompanyProfileResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> tuple[CompanyProfileResult, FreshnessRecord]:
        try:
            sym = normalize_symbol(entity.symbol)
        except ValueError as err:
            now = utc_stamp()
            return CompanyProfileResult(
                None,
                None,
                {},
                ServiceState.UNAVAILABLE,
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.VALIDATION_ERROR, detail=str(err), retryable=False),
                None,
                None,
                now,
            ), unavailable_freshness()

        result, cache_hit = await self._cache.get_or_load(
            f"company-profile:{sym}",
            COMPANY_PROFILE_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> CompanyProfileResult:
        sym = normalize_symbol(entity.symbol)
        try:
            info = await _call_with_retry(
                lambda: yf.Ticker(sym).info or {},
                op_name="company_profile_info",
                symbol=sym,
                timeout=EXTERNAL_TIMEOUT_SECONDS,
                max_retries=1,
            )
        except TimeoutError:
            return CompanyProfileResult(
                None, None, {}, ServiceState.UNAVAILABLE, ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.COMPANY_UNAVAILABLE, detail=f"company profile timeout for {sym}", retryable=True),
                None, None, None
            )
        except Exception as error:
            return CompanyProfileResult(
                None, None, {}, ServiceState.UNAVAILABLE, ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.COMPANY_UNAVAILABLE, detail=f"company profile unavailable for {sym}: {type(error).__name__}", retryable=True),
                None, None, None
            )

        now = utc_stamp()
        headquarters = _headquarters(info)
        overview = CompanyOverview(
            company_name=info.get("longName") or info.get("shortName") or entity.name,
            ticker=sym,
            exchange=info.get("exchange") or entity.exchange,
            sector=info.get("sector") or entity.sector,
            industry=info.get("industry") or entity.industry,
            country=info.get("country"),
            headquarters=headquarters,
            website=info.get("website"),
            business_description=info.get("longBusinessSummary"),
            employees=_optional_int(info.get("fullTimeEmployees")),
            market_cap=_optional_int(info.get("marketCap")),
            currency=info.get("currency") or entity.currency,
        )
        leadership = _leadership(info.get("companyOfficers"))
        ceo = next((person for person in leadership if person.title and "chief executive" in person.title.lower()), None)
        governance = GovernanceProfile(ceo=ceo, key_leadership=leadership, notable_developments=[])
        company_source = _source("company", sym, now)
        governance_source = _source("governance", sym, now)
        governance_state = ServiceState.AVAILABLE if leadership else ServiceState.PARTIAL
        return CompanyProfileResult(overview, governance, info, ServiceState.AVAILABLE, governance_state, None, company_source, governance_source, now)


class FinancialHealthService:
    """Fetch annual and quarterly statements concurrently and calculate normalized metrics."""

    def __init__(self, cache: AsyncTTLCache[FinancialHealthResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity, profile: CompanyProfileResult | None) -> tuple[FinancialHealthResult, FreshnessRecord]:
        try:
            sym = normalize_symbol(entity.symbol)
        except ValueError as err:
            now = utc_stamp()
            return FinancialHealthResult(
                None,
                ServiceState.UNAVAILABLE,
                ResearchError(ErrorCategory.VALIDATION_ERROR, detail=str(err), retryable=False),
                None,
                now,
            ), unavailable_freshness()

        result, cache_hit = await self._cache.get_or_load(
            f"financial-health:{sym}",
            FINANCIALS_TTL_SECONDS,
            lambda: self._fetch_uncached(entity, profile.info if profile else {}),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity, info: dict[str, Any]) -> FinancialHealthResult:
        sym = normalize_symbol(entity.symbol)
        income_task = asyncio.create_task(self._statement(sym, "income", freq="yearly"))
        balance_task = asyncio.create_task(self._statement(sym, "balance", freq="yearly"))
        cash_task = asyncio.create_task(self._statement(sym, "cash", freq="yearly"))
        q_income_task = asyncio.create_task(self._statement(sym, "income", freq="quarterly"))
        q_balance_task = asyncio.create_task(self._statement(sym, "balance", freq="quarterly"))
        q_cash_task = asyncio.create_task(self._statement(sym, "cash", freq="quarterly"))

        outcomes = await asyncio.gather(
            income_task, balance_task, cash_task,
            q_income_task, q_balance_task, q_cash_task,
            return_exceptions=True,
        )
        income_result, balance_result, cash_result = outcomes[0], outcomes[1], outcomes[2]
        q_income_result, q_balance_result, q_cash_result = outcomes[3], outcomes[4], outcomes[5]

        income = income_result if not isinstance(income_result, BaseException) else None
        balance = balance_result if not isinstance(balance_result, BaseException) else None
        cash = cash_result if not isinstance(cash_result, BaseException) else None

        q_income = q_income_result if not isinstance(q_income_result, BaseException) else None
        q_balance = q_balance_result if not isinstance(q_balance_result, BaseException) else None
        q_cash = q_cash_result if not isinstance(q_cash_result, BaseException) else None

        issues = [item for item in outcomes if isinstance(item, ResearchError)]
        now = utc_stamp()
        currency = info.get("currency") or entity.currency or "USD"

        # Calculate ratios
        ratios = compute_financial_ratios(income, balance, cash, info)

        # Build multi-period statement data
        statements = FinancialStatementsData(
            reporting_currency=currency,
            annual_income=_extract_statement_periods(income, "annual", currency),
            quarterly_income=_extract_statement_periods(q_income, "quarterly", currency),
            annual_balance=_extract_statement_periods(balance, "annual", currency),
            quarterly_balance=_extract_statement_periods(q_balance, "quarterly", currency),
            annual_cashflow=_extract_statement_periods(cash, "annual", currency),
            quarterly_cashflow=_extract_statement_periods(q_cash, "quarterly", currency),
        )

        financials = FinancialHealth(
            revenue=_statement_value(income, ["Total Revenue", "Operating Revenue"]),
            net_income=_statement_value(income, ["Net Income", "Net Income Common Stockholders"]),
            eps=_optional_float(info.get("trailingEps")) or _statement_value(income, ["Diluted EPS", "Basic EPS"]),
            profit_margin=(ratios.net_margin / 100.0) if ratios.net_margin is not None else _optional_float(info.get("profitMargins")),
            operating_margin=(ratios.operating_margin / 100.0) if ratios.operating_margin is not None else _optional_float(info.get("operatingMargins")),
            free_cash_flow=ratios.free_cash_flow if ratios.free_cash_flow is not None else _statement_value(cash, ["Free Cash Flow"]),
            total_cash=_optional_float(info.get("totalCash")) or _statement_value(balance, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
            total_debt=_optional_float(info.get("totalDebt")) or _statement_value(balance, ["Total Debt"]),
            pe_ratio=ratios.pe_ratio,
            price_to_sales=ratios.price_to_sales,
            dividend_yield=dividend_yield_fraction(info.get("dividendYield")),
            return_on_equity=(ratios.return_on_equity / 100.0) if ratios.return_on_equity is not None else _optional_float(info.get("returnOnEquity")),
            return_on_assets=(ratios.return_on_assets / 100.0) if ratios.return_on_assets is not None else _optional_float(info.get("returnOnAssets")),
            currency=currency,
            fiscal_period_end=_fiscal_period(income) or _fiscal_period(balance) or _fiscal_period(cash),
        )

        has_values = any(value is not None for key, value in financials.model_dump().items() if key not in {"currency", "fiscal_period_end"})
        if not has_values:
            issue = issues[0] if issues else ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail="financial statement response empty", retryable=True)
            return FinancialHealthResult(None, ServiceState.UNAVAILABLE, issue, None, None, None, None)
        warning = issues[0] if issues else None
        return FinancialHealthResult(
            financials,
            ServiceState.PARTIAL if warning else ServiceState.AVAILABLE,
            warning,
            _source("financial", sym, now),
            now,
            statements,
            ratios,
        )

    @staticmethod
    async def _statement(symbol: str, statement: str, freq: str = "yearly") -> Any | ResearchError:
        try:
            def load() -> Any:
                ticker = yf.Ticker(symbol)
                if statement == "income":
                    return ticker.get_income_stmt(freq=freq)
                if statement == "balance":
                    return ticker.get_balance_sheet(freq=freq)
                return ticker.get_cash_flow(freq=freq)

            return await _call_with_retry(
                load,
                op_name=f"statement_{statement}_{freq}",
                symbol=symbol,
                timeout=EXTERNAL_TIMEOUT_SECONDS,
                max_retries=1,
            )
        except TimeoutError:
            return ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail=f"{statement} statement timeout for {symbol}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail=f"{statement} statement unavailable for {symbol}: {type(error).__name__}", retryable=True)


def compute_financial_ratios(
    income_frame: Any,
    balance_frame: Any,
    cash_frame: Any,
    info: dict[str, Any],
) -> CalculatedRatios:
    """Compute defensible financial ratios handling zero division, negatives, and NaN."""
    rev = _statement_value(income_frame, ["Total Revenue", "Operating Revenue"])
    cogs = _statement_value(income_frame, ["Cost of Revenue", "Reconciled Cost Of Revenue"])
    gross_profit = _statement_value(income_frame, ["Gross Profit"])
    if gross_profit is None and rev is not None and cogs is not None:
        gross_profit = rev - cogs

    op_inc = _statement_value(income_frame, ["Operating Income", "Total Operating Income As Reported"])
    net_inc = _statement_value(income_frame, ["Net Income", "Net Income Common Stockholders"])

    # Balance sheet
    tot_assets = _statement_value(balance_frame, ["Total Assets"])
    curr_assets = _statement_value(balance_frame, ["Current Assets"])
    cash_eq = _statement_value(balance_frame, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash Financial"])
    receivables = _statement_value(balance_frame, ["Receivables", "Accounts Receivable"])
    curr_liab = _statement_value(balance_frame, ["Current Liabilities"])
    tot_debt = _optional_float(info.get("totalDebt")) or _statement_value(balance_frame, ["Total Debt", "Long Term Debt And Capital Lease Obligation"])
    equity = _statement_value(balance_frame, ["Stockholders Equity", "Common Stock Equity"])

    # Cash flow
    op_cf = _statement_value(cash_frame, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
    capex = _statement_value(cash_frame, ["Capital Expenditure", "Purchase Of PPE"])
    fcf = _statement_value(cash_frame, ["Free Cash Flow"])
    if fcf is None and op_cf is not None and capex is not None:
        fcf = op_cf - abs(capex)

    # Margins (percentages)
    gross_margin = None
    if rev and rev > 0 and gross_profit is not None:
        gross_margin = (gross_profit / rev) * 100.0

    operating_margin = None
    if rev and rev > 0 and op_inc is not None:
        operating_margin = (op_inc / rev) * 100.0
    elif _optional_float(info.get("operatingMargins")) is not None:
        operating_margin = _optional_float(info.get("operatingMargins")) * 100.0

    net_margin = None
    if rev and rev > 0 and net_inc is not None:
        net_margin = (net_inc / rev) * 100.0
    elif _optional_float(info.get("profitMargins")) is not None:
        net_margin = _optional_float(info.get("profitMargins")) * 100.0

    fcf_margin = None
    if rev and rev > 0 and fcf is not None:
        fcf_margin = (fcf / rev) * 100.0

    # Solvency / Liquidity
    current_ratio = None
    if curr_assets is not None and curr_liab and curr_liab > 0:
        current_ratio = curr_assets / curr_liab

    quick_ratio = None
    if curr_liab and curr_liab > 0:
        quick_assets = 0.0
        has_quick = False
        if cash_eq is not None:
            quick_assets += cash_eq
            has_quick = True
        if receivables is not None:
            quick_assets += receivables
            has_quick = True
        if has_quick:
            quick_ratio = quick_assets / curr_liab

    debt_to_equity = None
    if tot_debt is not None and equity and equity > 0:
        debt_to_equity = tot_debt / equity

    debt_to_assets = None
    if tot_debt is not None and tot_assets and tot_assets > 0:
        debt_to_assets = tot_debt / tot_assets

    # Returns
    roe = None
    if net_inc is not None and equity and equity > 0:
        roe = (net_inc / equity) * 100.0
    elif _optional_float(info.get("returnOnEquity")) is not None:
        roe = _optional_float(info.get("returnOnEquity")) * 100.0

    roa = None
    if net_inc is not None and tot_assets and tot_assets > 0:
        roa = (net_inc / tot_assets) * 100.0
    elif _optional_float(info.get("returnOnAssets")) is not None:
        roa = _optional_float(info.get("returnOnAssets")) * 100.0

    # YoY Growth across multi-period columns
    rev_growth_yoy = _calculate_series_yoy(income_frame, ["Total Revenue", "Operating Revenue"])
    ni_growth_yoy = _calculate_series_yoy(income_frame, ["Net Income", "Net Income Common Stockholders"])

    # Valuation multiples from info / market price
    pe = _optional_float(info.get("trailingPE"))
    ps = _optional_float(info.get("priceToSalesTrailing12Months"))
    pb = _optional_float(info.get("priceToBook"))
    if pb is None and equity and equity > 0 and _optional_float(info.get("marketCap")):
        pb = _optional_float(info.get("marketCap")) / equity

    return CalculatedRatios(
        gross_margin=gross_margin,
        operating_margin=operating_margin,
        net_margin=net_margin,
        free_cash_flow=fcf,
        fcf_margin=fcf_margin,
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        debt_to_equity=debt_to_equity,
        debt_to_assets=debt_to_assets,
        return_on_equity=roe,
        return_on_assets=roa,
        revenue_growth_yoy=rev_growth_yoy,
        net_income_growth_yoy=ni_growth_yoy,
        pe_ratio=pe,
        price_to_sales=ps,
        price_to_book=pb,
    )


def _calculate_series_yoy(frame: Any, labels: list[str]) -> float | None:
    if frame is None or isinstance(frame, ResearchError) or getattr(frame, "empty", True):
        return None
    columns = getattr(frame, "columns", None)
    if columns is None or len(columns) < 2:
        return None

    val_latest = _statement_value_for_col(frame, columns[0], labels)
    val_prior = _statement_value_for_col(frame, columns[1], labels)

    if val_latest is None or val_prior is None or val_prior == 0:
        return None
    if math.isnan(val_latest) or math.isnan(val_prior):
        return None

    return ((val_latest - val_prior) / abs(val_prior)) * 100.0


def _extract_statement_periods(
    frame: Any,
    period_type: str,
    currency: str | None,
) -> list[StatementPeriod]:
    if frame is None or isinstance(frame, ResearchError) or getattr(frame, "empty", True):
        return []
    columns = getattr(frame, "columns", None)
    if columns is None:
        return []

    periods: list[StatementPeriod] = []
    for col in columns:
        date_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)[:10]
        sp = StatementPeriod(
            period_end=date_str,
            period_type=period_type,
            currency=currency,
            revenue=_statement_value_for_col(frame, col, ["Total Revenue", "Operating Revenue"]),
            cost_of_revenue=_statement_value_for_col(frame, col, ["Cost of Revenue", "Reconciled Cost Of Revenue"]),
            gross_profit=_statement_value_for_col(frame, col, ["Gross Profit"]),
            operating_income=_statement_value_for_col(frame, col, ["Operating Income", "Total Operating Income As Reported"]),
            net_income=_statement_value_for_col(frame, col, ["Net Income", "Net Income Common Stockholders"]),
            ebitda=_statement_value_for_col(frame, col, ["EBITDA", "Normalized EBITDA"]),
            diluted_eps=_statement_value_for_col(frame, col, ["Diluted EPS", "Basic EPS"]),
            total_assets=_statement_value_for_col(frame, col, ["Total Assets"]),
            current_assets=_statement_value_for_col(frame, col, ["Current Assets"]),
            cash_and_equivalents=_statement_value_for_col(frame, col, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
            total_liabilities=_statement_value_for_col(frame, col, ["Total Liabilities Net Minority Interest", "Total Liabilities"]),
            current_liabilities=_statement_value_for_col(frame, col, ["Current Liabilities"]),
            total_debt=_statement_value_for_col(frame, col, ["Total Debt", "Long Term Debt And Capital Lease Obligation"]),
            stockholders_equity=_statement_value_for_col(frame, col, ["Stockholders Equity", "Common Stock Equity"]),
            operating_cash_flow=_statement_value_for_col(frame, col, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]),
            capital_expenditure=_statement_value_for_col(frame, col, ["Capital Expenditure", "Purchase Of PPE"]),
            free_cash_flow=_statement_value_for_col(frame, col, ["Free Cash Flow"]),
        )
        periods.append(sp)
    return periods


def _statement_value(frame: Any, labels: list[str]) -> float | None:
    if frame is None or isinstance(frame, ResearchError) or getattr(frame, "empty", True):
        return None
    index = getattr(frame, "index", [])
    if not hasattr(index, "__iter__"):
        return None

    norm_index_map = {_normalize_statement_label(k): k for k in index}

    for label in labels:
        norm_label = _normalize_statement_label(label)
        actual_key = norm_index_map.get(norm_label)
        if actual_key is None:
            if label in index:
                actual_key = label
            else:
                continue

        row = frame.loc[actual_key]
        values = row.tolist() if hasattr(row, "tolist") else [row]
        for value in values:
            numeric = _optional_float(value)
            if numeric is not None and not math.isnan(numeric) and not math.isinf(numeric):
                return numeric
    return None


def _statement_value_for_col(frame: Any, col: Any, labels: list[str]) -> float | None:
    if frame is None or isinstance(frame, ResearchError) or getattr(frame, "empty", True):
        return None
    index = getattr(frame, "index", [])
    if not hasattr(index, "__iter__"):
        return None

    norm_index_map = {_normalize_statement_label(k): k for k in index}

    for label in labels:
        norm_label = _normalize_statement_label(label)
        actual_key = norm_index_map.get(norm_label)
        if actual_key is None:
            if label in index:
                actual_key = label
            else:
                continue

        try:
            val = frame.at[actual_key, col]
            num = _optional_float(val)
            if num is not None and not math.isnan(num) and not math.isinf(num):
                return num
        except Exception:
            continue
    return None


def _fiscal_period(frame: Any) -> str | None:
    columns = getattr(frame, "columns", None)
    if columns is None or len(columns) == 0:
        return None
    value = columns[0]
    return value.isoformat().replace("+00:00", "Z") if hasattr(value, "isoformat") else str(value)


def unavailable_competitive_evidence() -> CompetitiveEvidence:
    return CompetitiveEvidence(status="unavailable", competitors=[], note="Insufficient verified competitor data. No competitor or market-share claim is shown.")


def market_snapshot_from_profile(info: dict[str, Any], currency: str | None, as_of: str | None) -> MarketSnapshot | None:
    """Create market context from the profile fetch already used for company facts."""
    if not info:
        return None
    values = {
        "current_price": _optional_float(info.get("regularMarketPrice") or info.get("currentPrice")),
        "market_cap": _optional_int(info.get("marketCap")),
        "pe_ratio": _optional_float(info.get("trailingPE")),
        "eps": _optional_float(info.get("trailingEps")),
        "price_to_sales": _optional_float(info.get("priceToSalesTrailing12Months")),
    }
    if not any(value is not None for value in values.values()):
        return None
    return MarketSnapshot(
        current_price=values["current_price"],
        currency=info.get("currency") or currency,
        daily_change=_optional_float(info.get("regularMarketChange")),
        daily_change_percent=_optional_float(info.get("regularMarketChangePercent")),
        volume=_optional_int(info.get("regularMarketVolume") or info.get("volume")),
        market_cap=values["market_cap"],
        pe_ratio=values["pe_ratio"],
        eps=values["eps"],
        fifty_two_week_high=_optional_float(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_optional_float(info.get("fiftyTwoWeekLow")),
        dividend_yield=dividend_yield_fraction(info.get("dividendYield")),
        market_status=info.get("marketState"),
        as_of=as_of,
    )


def _headquarters(info: dict[str, Any]) -> str | None:
    parts = [str(info[key]).strip() for key in ("city", "state", "country") if info.get(key)]
    return ", ".join(parts) if parts else None


def _leadership(raw_officers: Any) -> list[LeadershipMember]:
    if not isinstance(raw_officers, list):
        return []
    members: list[LeadershipMember] = []
    for officer in raw_officers:
        if not isinstance(officer, dict):
            continue
        name = str(officer.get("name") or "").strip()
        if not name:
            continue
        members.append(LeadershipMember(name=name, title=(str(officer.get("title") or "").strip() or None), since=None))
        if len(members) == 8:
            break
    return members


async def fetch_company_analysis_bundle(
    symbol: str,
    *,
    profile_service: CompanyProfileService | None = None,
    financial_service: FinancialHealthService | None = None,
) -> CompanyAnalysisBundle:
    """Convenience pipeline function to fetch and validate all company deep analysis data."""
    clean_sym = normalize_symbol(symbol)
    entity = CompanyIdentity(symbol=clean_sym, identifier_confidence=IdentifierConfidence.HIGH)
    p_service = profile_service or default_company_profile_service
    f_service = financial_service or default_financial_health_service

    profile_res, profile_fresh = await p_service.fetch(entity)
    fin_res, fin_fresh = await f_service.fetch(entity, profile_res)

    market_ctx = market_snapshot_from_profile(profile_res.info, entity.currency, profile_res.retrieved_at) if profile_res else None

    sources: list[SourceRecord] = []
    if profile_res.company_source:
        sources.append(profile_res.company_source)
    if profile_res.governance_source:
        sources.append(profile_res.governance_source)
    if fin_res.source:
        sources.append(fin_res.source)

    warning = profile_res.warning or fin_res.warning
    now = utc_stamp()

    return CompanyAnalysisBundle(
        company=entity,
        overview=profile_res.overview,
        governance=profile_res.governance,
        financial_health=fin_res.financial_health,
        statements=fin_res.statements,
        ratios=fin_res.calculated_ratios,
        market_context=market_ctx,
        profile_status=profile_res.company_status,
        financial_status=fin_res.status,
        governance_status=profile_res.governance_status,
        warning=warning,
        sources=sources,
        retrieved_at=now,
    )


# Exported singleton services for application-wide reuse
default_company_profile_service = CompanyProfileService()
default_financial_health_service = FinancialHealthService()
