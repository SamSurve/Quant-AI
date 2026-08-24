"""Safe, classified errors for QuantAI's public research BFF."""

from __future__ import annotations

from dataclasses import dataclass

from .research_schemas import ErrorCategory


SAFE_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.VALIDATION_ERROR: "Provide a valid company name or ticker symbol.",
    ErrorCategory.ENTITY_NOT_FOUND: "No supported listed company or ticker was found for this query.",
    ErrorCategory.AMBIGUOUS_ENTITY: "Multiple companies match this query. Select a listed ticker to continue.",
    ErrorCategory.DATA_UNAVAILABLE: "Market data is temporarily unavailable. Please try again shortly.",
    ErrorCategory.COMPANY_UNAVAILABLE: "Company profile data is temporarily unavailable. Other research data may still be available.",
    ErrorCategory.FINANCIALS_UNAVAILABLE: "Financial statement data is temporarily unavailable. Other research data may still be available.",
    ErrorCategory.GOVERNANCE_UNAVAILABLE: "Governance data is temporarily unavailable. Other research data may still be available.",
    ErrorCategory.COMPARISON_UNAVAILABLE: "Company comparison is temporarily unavailable. Available data may still be shown when sourced.",
    ErrorCategory.CURRENCY_COMPARISON_UNAVAILABLE: "Values use different currencies and cannot be safely compared without a verified conversion rate.",
    ErrorCategory.HISTORY_UNAVAILABLE: "Price history is temporarily unavailable. Other research data may still be available.",
    ErrorCategory.NEWS_UNAVAILABLE: "Current news is temporarily unavailable. Other research data may still be available.",
    ErrorCategory.EVENTS_UNAVAILABLE: "Event data is temporarily unavailable. Other research data may still be available.",
    ErrorCategory.AI_UNAVAILABLE: "AI analysis is temporarily unavailable. Deterministic research data is still available when sourced.",
    ErrorCategory.RATE_LIMITED: "Too many requests were received. Please wait a moment and try again.",
    ErrorCategory.TIMEOUT: "Research took too long to complete. Available partial data has been returned when possible.",
    ErrorCategory.INTERNAL_ERROR: "Research is temporarily unavailable. Please try again shortly.",
}


HTTP_STATUS: dict[ErrorCategory, int] = {
    ErrorCategory.VALIDATION_ERROR: 422,
    ErrorCategory.ENTITY_NOT_FOUND: 404,
    ErrorCategory.AMBIGUOUS_ENTITY: 409,
    ErrorCategory.DATA_UNAVAILABLE: 503,
    ErrorCategory.COMPANY_UNAVAILABLE: 503,
    ErrorCategory.FINANCIALS_UNAVAILABLE: 503,
    ErrorCategory.GOVERNANCE_UNAVAILABLE: 503,
    ErrorCategory.COMPARISON_UNAVAILABLE: 503,
    ErrorCategory.CURRENCY_COMPARISON_UNAVAILABLE: 422,
    ErrorCategory.HISTORY_UNAVAILABLE: 503,
    ErrorCategory.NEWS_UNAVAILABLE: 503,
    ErrorCategory.EVENTS_UNAVAILABLE: 503,
    ErrorCategory.AI_UNAVAILABLE: 503,
    ErrorCategory.RATE_LIMITED: 429,
    ErrorCategory.TIMEOUT: 504,
    ErrorCategory.INTERNAL_ERROR: 500,
}


@dataclass
class ResearchError(Exception):
    """Internal context plus a public-safe category; never serialize ``detail``."""

    category: ErrorCategory
    detail: str = ""
    retryable: bool = False

    @property
    def message(self) -> str:
        return SAFE_MESSAGES[self.category]

    @property
    def status_code(self) -> int:
        return HTTP_STATUS[self.category]
