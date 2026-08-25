"""No-network regression matrix for QuantAI's one-way provider engine.

Run with ``PYTHONDONTWRITEBYTECODE=1 python tests/test_provider_failover.py``.
All provider outcomes are deterministic simulations; this file never calls an
external model or consumes provider quota.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agno.exceptions import ModelProviderError
from agno.models.message import Message
from agno.models.response import ModelResponse
from api.ai_providers import (
    AIProvider,
    ProviderFailureCategory,
    ProviderHealthStore,
    ProviderRouter,
    StructuredProviderEngine,
    USER_FRIENDLY_UNAVAILABLE,
    build_groq_primary_provider,
    build_groq_secondary_provider,
    build_openrouter_provider,
    classify_provider_failure,
    ordered_providers_from_environment,
)
from api.research_schemas import StructuredAnalysis


class SimulatedProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeModel:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def invoke(self, *_args, **_kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return ModelResponse(content=outcome)

    async def ainvoke(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)


def make_router(primary_outcomes: list[object], secondary_outcomes: list[object], ox_outcomes: list[object]):
    primary = FakeModel(primary_outcomes)
    secondary = FakeModel(secondary_outcomes)
    ox = FakeModel(ox_outcomes)
    router = ProviderRouter(
        id="quantai-provider-engine",
        name="QuantAI Provider Engine",
        provider="QuantAI",
        providers=(
            AIProvider("Groq primary", "primary-test", primary, True),
            AIProvider("Groq secondary", "secondary-test", secondary, True),
            AIProvider("OpenRouter Ox Alpha", "stealth/ox-alpha", ox, True),
        ),
        retries=0,
        retry_with_guidance=False,
        retry_with_guidance_limit=0,
    )
    return router, primary, secondary, ox


def invoke(router: ProviderRouter):
    return router.response(messages=[Message(role="user", content="Research AAPL")])


# TEST 1: Groq #1 success.
router, primary, secondary, ox = make_router(["primary-success"], ["unexpected"], ["unexpected"])
assert invoke(router).content == "primary-success"
assert (primary.calls, secondary.calls, ox.calls) == (1, 0, 0)

# TEST 2: Groq #1 429, Groq #2 succeeds.
router, primary, secondary, ox = make_router([SimulatedProviderError("rate limited", 429)], ["secondary-success"], ["unexpected"])
assert invoke(router).content == "secondary-success"
assert (primary.calls, secondary.calls, ox.calls) == (1, 1, 0)

# TEST 3: Groq #1 timeout, Groq #2 succeeds asynchronously.
async def verify_async_timeout_fallback() -> None:
    router, primary, secondary, ox = make_router([TimeoutError("timed out")], ["secondary-async-success"], ["unexpected"])
    result = await router._call_async("ainvoke", "research")
    assert result.content == "secondary-async-success"
    assert (primary.calls, secondary.calls, ox.calls) == (1, 1, 0)


asyncio.run(verify_async_timeout_fallback())

# TEST 4: Groq #1 5xx, Groq #2 429, Ox succeeds.
router, primary, secondary, ox = make_router(
    [SimulatedProviderError("server failure", 503)],
    [SimulatedProviderError("rate limited", 429)],
    ["ox-success"],
)
assert invoke(router).content == "ox-success"
assert (primary.calls, secondary.calls, ox.calls) == (1, 1, 1)

# TEST 5: A model 404 produces a cooldown and the next request skips it.
router, primary, secondary, ox = make_router(
    [SimulatedProviderError("model not found", 404), "must-remain-skipped"],
    ["secondary-after-404", "secondary-after-cooldown"],
    ["unexpected"],
)
assert invoke(router).content == "secondary-after-404"
assert invoke(router).content == "secondary-after-cooldown"
assert (primary.calls, secondary.calls, ox.calls) == (1, 2, 0)

# TEST 6: Authentication failure has no retry storm and moves forward once.
router, primary, secondary, ox = make_router(
    [SimulatedProviderError("forbidden", 403)], ["secondary-after-auth"], ["unexpected"]
)
assert invoke(router).content == "secondary-after-auth"
assert (primary.calls, secondary.calls, ox.calls) == (1, 1, 0)

# TEST 6A: request-size failure falls forward but does not create an authentication cooldown.
router, primary, secondary, ox = make_router(
    [SimulatedProviderError("request too large", 413), "primary-after-smaller-context"],
    ["secondary-after-413", "unexpected"],
    ["unexpected"],
)
assert invoke(router).content == "secondary-after-413"
assert invoke(router).content == "primary-after-smaller-context"
assert (primary.calls, secondary.calls, ox.calls) == (2, 1, 0)

# TEST 7/9/12: all attempts are bounded and safe after final malformed Ox output.
router, primary, secondary, ox = make_router(
    [SimulatedProviderError("rate limited", 429)],
    [TimeoutError("timed out")],
    [ValueError("malformed response")],
)
try:
    invoke(router)
except ModelProviderError as error:
    assert str(error) == USER_FRIENDLY_UNAVAILABLE
    assert error.status_code == 503
else:
    raise AssertionError("all unavailable providers must resolve to a safe generic error")
assert (primary.calls, secondary.calls, ox.calls) == (1, 1, 1)

# TEST 8: malformed primary response falls forward to Groq #2.
router, primary, secondary, ox = make_router([ValueError("bad structured output")], ["secondary-after-malformed"], ["unexpected"])
assert invoke(router).content == "secondary-after-malformed"
assert (primary.calls, secondary.calls, ox.calls) == (1, 1, 0)

# Explicit classification covers all provider failure classes without payload leaks.
assert classify_provider_failure(SimulatedProviderError("not found", 404)).category == ProviderFailureCategory.MODEL_NOT_FOUND
assert classify_provider_failure(SimulatedProviderError("unauthorized", 401)).category == ProviderFailureCategory.AUTHENTICATION_FAILURE
assert classify_provider_failure(SimulatedProviderError("request too large", 413)).category == ProviderFailureCategory.PAYLOAD_TOO_LARGE
assert classify_provider_failure(SimulatedProviderError("gateway", 502)).category == ProviderFailureCategory.SERVER_ERROR
assert classify_provider_failure(ConnectionError("network unavailable")).category == ProviderFailureCategory.CONNECTION_ERROR
assert classify_provider_failure(ValueError("bad json")).category == ProviderFailureCategory.MALFORMED_RESPONSE
assert classify_provider_failure(TimeoutError("timeout")).category == ProviderFailureCategory.TIMEOUT

# Provider configuration accepts only a duplicate-free, complete sequence.
slot_map = {
    "groq_primary": AIProvider("Groq primary", "primary", FakeModel([]), True),
    "groq_secondary": AIProvider("Groq secondary", "secondary", FakeModel([]), True),
    "openrouter_ox_alpha": AIProvider("OpenRouter Ox Alpha", "ox", FakeModel([]), True),
}
previous_order = os.environ.get("AI_PROVIDER_ORDER")
try:
    os.environ["AI_PROVIDER_ORDER"] = "openrouter_ox_alpha,groq_primary,groq_secondary"
    assert [provider.name for provider in ordered_providers_from_environment(slot_map)] == [
        "OpenRouter Ox Alpha",
        "Groq primary",
        "Groq secondary",
    ]
    os.environ["AI_PROVIDER_ORDER"] = "groq_primary,groq_primary,openrouter_ox_alpha"
    assert [provider.name for provider in ordered_providers_from_environment(slot_map)] == [
        "Groq primary",
        "Groq secondary",
        "OpenRouter Ox Alpha",
    ]
finally:
    if previous_order is None:
        os.environ.pop("AI_PROVIDER_ORDER", None)
    else:
        os.environ["AI_PROVIDER_ORDER"] = previous_order


# Synthetic no-secret rotation isolation: each configured slot must retain its
# own model and credential boundary rather than inheriting a neighboring slot.
rotation_names = (
    "GROQ_API_KEY_PRIMARY",
    "GROQ_MODEL_PRIMARY",
    "GROQ_API_KEY_SECONDARY",
    "GROQ_MODEL_SECONDARY",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
)
rotation_previous = {name: os.environ.get(name) for name in rotation_names}
try:
    os.environ.update(
        {
            "GROQ_API_KEY_PRIMARY": "synthetic-primary",
            "GROQ_MODEL_PRIMARY": "primary-test-model",
            "GROQ_API_KEY_SECONDARY": "synthetic-secondary",
            "GROQ_MODEL_SECONDARY": "secondary-test-model",
            "OPENROUTER_API_KEY": "synthetic-openrouter",
            "OPENROUTER_MODEL": "openrouter-test-model",
        }
    )
    primary_slot = build_groq_primary_provider()
    secondary_slot = build_groq_secondary_provider()
    openrouter_slot = build_openrouter_provider()
    assert (primary_slot.name, primary_slot.model_id, primary_slot.configured) == ("Groq primary", "primary-test-model", True)
    assert (secondary_slot.name, secondary_slot.model_id, secondary_slot.configured) == ("Groq secondary", "secondary-test-model", True)
    assert (openrouter_slot.name, openrouter_slot.model_id, openrouter_slot.configured) == ("OpenRouter Ox Alpha", "openrouter-test-model", True)
    assert primary_slot.model.api_key == "synthetic-primary"
    assert secondary_slot.model.api_key == "synthetic-secondary"
    assert openrouter_slot.model.api_key == "synthetic-openrouter"
finally:
    for name, value in rotation_previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


# Structured-engine tests exercise schema validation and exact fallback sequencing.
async def verify_structured_engine_matrix() -> None:
    primary = AIProvider("Groq primary", "primary", FakeModel([]), True)
    secondary = AIProvider("Groq secondary", "secondary", FakeModel([]), True)
    ox = AIProvider("OpenRouter Ox Alpha", "stealth/ox-alpha", FakeModel([]), True)
    calls: list[str] = []
    outcomes: dict[str, object] = {
        "Groq primary": {
            "executive_summary": "Primary malformed.",
            "bullish_factors": [],
            "bearish_factors": [],
            "risks": [],
            "catalysts": [],
            "confidence": "unsupported-value",
            "ai_verdict": "Malformed confidence.",
        },
        "Groq secondary": SimulatedProviderError("rate limited", 429),
        "OpenRouter Ox Alpha": {
            "executive_summary": "Validated Ox interpretation.",
            "bullish_factors": [],
            "bearish_factors": [],
            "risks": [],
            "catalysts": [],
            "confidence": "low",
            "ai_verdict": "Insufficient deterministic context for a strong conclusion.",
        },
    }

    async def runner(provider: AIProvider, _prompt: str, _schema):
        calls.append(provider.name)
        outcome = outcomes[provider.name]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    engine = StructuredProviderEngine((primary, secondary, ox), ProviderHealthStore(), runner=runner)
    result = await engine.generate_structured("validated input", StructuredAnalysis, request_id="provider-matrix")
    assert result.executive_summary == "Validated Ox interpretation."
    assert calls == ["Groq primary", "Groq secondary", "OpenRouter Ox Alpha"]

    all_fail = StructuredProviderEngine(
        (primary, secondary, ox),
        ProviderHealthStore(),
        runner=lambda *_args: (_ for _ in ()).throw(ValueError("malformed output")),
    )
    try:
        await all_fail.generate_structured("validated input", StructuredAnalysis)
    except ModelProviderError as error:
        assert str(error) == USER_FRIENDLY_UNAVAILABLE
    else:
        raise AssertionError("all malformed structured outputs must fail safely")


asyncio.run(verify_structured_engine_matrix())

print("PROVIDER_ENGINE_REGRESSION=PASS")
