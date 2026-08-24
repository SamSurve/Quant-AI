"""Deterministic company and financial adapters for QuantAI Company Deep Analysis.

This module exposes only source-provided company/profile/statement data. It
does not infer competitors, market share, leadership changes, or unavailable
financial metrics. Those fields remain null, empty, or explicitly unavailable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import yfinance as yf

from .market_intelligence_services import _freshness, _quote_url, unavailable_freshness
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
    LeadershipMember,
    MarketSnapshot,
    ServiceState,
    SourceRecord,
)
from .research_services import EXTERNAL_TIMEOUT_SECONDS, _optional_float, _optional_int, utc_stamp


COMPANY_PROFILE_TTL_SECONDS = 60 * 60
FINANCIALS_TTL_SECONDS = 60 * 60 * 6


def _source(data_type: str, symbol: str, retrieved_at: str) -> SourceRecord:
    return SourceRecord(
        source="Yahoo Finance via yfinance",
        url=_quote_url(symbol),
        retrieved_at=retrieved_at,
        data_type=data_type,  # type: ignore[arg-type]
    )


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


class CompanyProfileService:
    """Fetch company profile and source-provided officer information once."""

    def __init__(self, cache: AsyncTTLCache[CompanyProfileResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity) -> tuple[CompanyProfileResult, FreshnessRecord]:
        result, cache_hit = await self._cache.get_or_load(
            f"company-profile:{entity.symbol}",
            COMPANY_PROFILE_TTL_SECONDS,
            lambda: self._fetch_uncached(entity),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity) -> CompanyProfileResult:
        try:
            info = await asyncio.wait_for(asyncio.to_thread(lambda: yf.Ticker(entity.symbol).info or {}), timeout=EXTERNAL_TIMEOUT_SECONDS)
        except TimeoutError:
            return CompanyProfileResult(None, None, {}, ServiceState.UNAVAILABLE, ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.COMPANY_UNAVAILABLE, detail=f"company profile timeout for {entity.symbol}", retryable=True), None, None, None)
        except Exception as error:
            return CompanyProfileResult(None, None, {}, ServiceState.UNAVAILABLE, ServiceState.UNAVAILABLE, ResearchError(ErrorCategory.COMPANY_UNAVAILABLE, detail=f"company profile unavailable for {entity.symbol}: {type(error).__name__}", retryable=True), None, None, None)

        now = utc_stamp()
        headquarters = _headquarters(info)
        overview = CompanyOverview(
            company_name=info.get("longName") or info.get("shortName") or entity.name,
            ticker=entity.symbol,
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
        company_source = _source("company", entity.symbol, now)
        governance_source = _source("governance", entity.symbol, now)
        governance_state = ServiceState.AVAILABLE if leadership else ServiceState.PARTIAL
        return CompanyProfileResult(overview, governance, info, ServiceState.AVAILABLE, governance_state, None, company_source, governance_source, now)


class FinancialHealthService:
    """Fetch annual statements concurrently and merge them with profile valuation inputs."""

    def __init__(self, cache: AsyncTTLCache[FinancialHealthResult] | None = None) -> None:
        self._cache = cache or AsyncTTLCache()

    async def fetch(self, entity: CompanyIdentity, profile: CompanyProfileResult | None) -> tuple[FinancialHealthResult, FreshnessRecord]:
        result, cache_hit = await self._cache.get_or_load(
            f"financial-health:{entity.symbol}",
            FINANCIALS_TTL_SECONDS,
            lambda: self._fetch_uncached(entity, profile.info if profile else {}),
        )
        return result, _freshness(cache_hit, result.retrieved_at)

    async def _fetch_uncached(self, entity: CompanyIdentity, info: dict[str, Any]) -> FinancialHealthResult:
        income_task = asyncio.create_task(self._statement(entity.symbol, "income"))
        balance_task = asyncio.create_task(self._statement(entity.symbol, "balance"))
        cash_task = asyncio.create_task(self._statement(entity.symbol, "cash"))
        income_result, balance_result, cash_result = await asyncio.gather(income_task, balance_task, cash_task, return_exceptions=True)
        income = income_result if not isinstance(income_result, BaseException) else None
        balance = balance_result if not isinstance(balance_result, BaseException) else None
        cash = cash_result if not isinstance(cash_result, BaseException) else None
        issues = [item for item in (income_result, balance_result, cash_result) if isinstance(item, ResearchError)]
        now = utc_stamp()

        financials = FinancialHealth(
            revenue=_statement_value(income, ["Total Revenue", "Operating Revenue"]),
            net_income=_statement_value(income, ["Net Income", "Net Income Common Stockholders"]),
            eps=_optional_float(info.get("trailingEps")) or _statement_value(income, ["Diluted EPS", "Basic EPS"]),
            profit_margin=_optional_float(info.get("profitMargins")),
            operating_margin=_optional_float(info.get("operatingMargins")),
            free_cash_flow=_statement_value(cash, ["Free Cash Flow"]),
            total_cash=_optional_float(info.get("totalCash")) or _statement_value(balance, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
            total_debt=_optional_float(info.get("totalDebt")) or _statement_value(balance, ["Total Debt"]),
            pe_ratio=_optional_float(info.get("trailingPE")),
            price_to_sales=_optional_float(info.get("priceToSalesTrailing12Months")),
            dividend_yield=_optional_float(info.get("dividendYield")),
            return_on_equity=_optional_float(info.get("returnOnEquity")),
            return_on_assets=_optional_float(info.get("returnOnAssets")),
            currency=info.get("currency") or entity.currency,
            fiscal_period_end=_fiscal_period(income) or _fiscal_period(balance) or _fiscal_period(cash),
        )
        has_values = any(value is not None for key, value in financials.model_dump().items() if key not in {"currency", "fiscal_period_end"})
        if not has_values:
            issue = issues[0] if issues else ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail="financial statement response empty", retryable=True)
            return FinancialHealthResult(None, ServiceState.UNAVAILABLE, issue, None, None)
        warning = issues[0] if issues else None
        return FinancialHealthResult(financials, ServiceState.PARTIAL if warning else ServiceState.AVAILABLE, warning, _source("financial", entity.symbol, now), now)

    @staticmethod
    async def _statement(symbol: str, statement: str) -> Any | ResearchError:
        try:
            def load() -> Any:
                ticker = yf.Ticker(symbol)
                if statement == "income":
                    return ticker.get_income_stmt(freq="yearly")
                if statement == "balance":
                    return ticker.get_balance_sheet(freq="yearly")
                return ticker.get_cash_flow(freq="yearly")

            return await asyncio.wait_for(asyncio.to_thread(load), timeout=EXTERNAL_TIMEOUT_SECONDS)
        except TimeoutError:
            return ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail=f"{statement} statement timeout for {symbol}", retryable=True)
        except Exception as error:
            return ResearchError(ErrorCategory.FINANCIALS_UNAVAILABLE, detail=f"{statement} statement unavailable for {symbol}: {type(error).__name__}", retryable=True)


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
        dividend_yield=_optional_float(info.get("dividendYield")),
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


def _statement_value(frame: Any, labels: list[str]) -> float | None:
    if frame is None or isinstance(frame, ResearchError) or getattr(frame, "empty", True):
        return None
    for label in labels:
        if label not in getattr(frame, "index", []):
            continue
        row = frame.loc[label]
        values = row.tolist() if hasattr(row, "tolist") else [row]
        for value in values:
            numeric = _optional_float(value)
            if numeric is not None:
                return numeric
    return None


def _fiscal_period(frame: Any) -> str | None:
    columns = getattr(frame, "columns", None)
    if columns is None or len(columns) == 0:
        return None
    value = columns[0]
    return value.isoformat().replace("+00:00", "Z") if hasattr(value, "isoformat") else str(value)
