"""No-network regression coverage for safe AgentOS company-name selection.

Run with ``PYTHONDONTWRITEBYTECODE=1 python tests/test_agentos_entity_resolution.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import groq_finance_agent as agent_module


def candidate(symbol: str, name: str, exchange: str = "NMS") -> dict[str, str]:
    return {"symbol": symbol, "longname": name, "exchange": exchange, "quoteType": "EQUITY"}


class FakeSearch:
    quotes: list[dict[str, str]] = []

    def __init__(self, _query: str, **_kwargs: object) -> None:
        self.quotes = list(type(self).quotes)


class FakeTicker:
    calls: list[str] = []

    def __init__(self, symbol: str) -> None:
        type(self).calls.append(symbol)
        self.symbol = symbol

    @property
    def info(self) -> dict[str, object]:
        return {
            "longName": f"{self.symbol} Holdings",
            "exchange": "NMS",
            "currency": "USD",
            "regularMarketPrice": 100.0,
        }

    def history(self, **_kwargs: object) -> pd.DataFrame:
        return pd.DataFrame(
            {"Close": [99.0, 100.0]},
            index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
        )


def resolve(query: str, quotes: list[dict[str, str]]) -> dict[str, object]:
    FakeSearch.quotes = quotes
    FakeTicker.calls = []
    with patch.object(agent_module.yf, "Search", FakeSearch), patch.object(agent_module.yf, "Ticker", FakeTicker):
        return agent_module.resolve_company_and_market_data(query)


def assert_resolution(query: str, quotes: list[dict[str, str]], expected_symbol: str) -> None:
    response = resolve(query, quotes)
    assert response.get("resolved_symbol") == expected_symbol, response
    assert FakeTicker.calls == [expected_symbol], FakeTicker.calls


def verify_clear_company_names() -> None:
    assert_resolution("Tesla", [candidate("TSLA", "Tesla, Inc."), candidate("TL0.DE", "Tesla, Inc.", "GER")], "TSLA")
    assert_resolution("Apple", [candidate("AAPL", "Apple Inc."), candidate("APC.F", "Apple Inc.", "FRA")], "AAPL")
    assert_resolution("Google", [candidate("GOOG", "Alphabet Inc."), candidate("GOOGL", "Alphabet Inc.", "NAS")], "GOOG")
    assert_resolution(
        "Reliance Industries",
        [candidate("RELIANCE.NS", "Reliance Industries Limited", "NSI"), candidate("RELIANCE.BO", "Reliance Industries Limited", "BSE")],
        "RELIANCE.NS",
    )
    assert_resolution(
        "Tata Motors",
        [candidate("TMCV.NS", "Tata Motors Limited", "NSI"), candidate("TMCV.BO", "Tata Motors Limited", "BSE")],
        "TMCV.NS",
    )


def verify_terminal_ticker() -> None:
    assert_resolution(
        "Tesla, Inc. TSLA",
        [candidate("TSLA", "Tesla, Inc."), candidate("TL0.DE", "Tesla, Inc.", "GER")],
        "TSLA",
    )


def verify_ambiguous_never_fetches_ticker() -> None:
    response = resolve(
        "Acme",
        [candidate("ACMA", "Acme Holdings Inc."), candidate("ACMB", "Acme Holdings Incorporated")],
    )
    assert "Multiple companies match" in str(response.get("error")), response
    assert response.get("candidates"), response
    assert FakeTicker.calls == [], FakeTicker.calls


if __name__ == "__main__":
    verify_clear_company_names()
    verify_terminal_ticker()
    verify_ambiguous_never_fetches_ticker()
    print("AGENTOS_ENTITY_RESOLUTION=PASS")
