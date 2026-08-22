"""No-network regression checks for QuantAI provider routing.

Run with: python tests/test_provider_failover.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agno.exceptions import ModelProviderError
from agno.models.message import Message
from agno.models.response import ModelResponse
from api.ai_providers import AIProvider, ProviderRouter, USER_FRIENDLY_UNAVAILABLE


class FakeModel:
    def __init__(self, outcomes):
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


def make_router(mode, gemini_outcomes, groq_outcomes):
    gemini = FakeModel(gemini_outcomes)
    groq = FakeModel(groq_outcomes)
    router = ProviderRouter(
        id="quantai-auto",
        name="QuantAI Provider Router",
        provider="QuantAI",
        providers=(
            AIProvider("Gemini", "gemini-test", gemini, True),
            AIProvider("Groq", "groq-test", groq, True),
        ),
        mode=mode,
        retry_with_guidance=False,
        retry_with_guidance_limit=0,
    )
    return router, gemini, groq


def request(router):
    return router.response(messages=[Message(role="user", content="Research AAPL")])


router, gemini, groq = make_router("auto", ["gemini-success"], ["unexpected"])
assert request(router).content == "gemini-success"
assert (gemini.calls, groq.calls) == (1, 0)

for transient_failure in (
    ModelProviderError("rate limit", status_code=429),
    ModelProviderError("service unavailable", status_code=503),
    TimeoutError("timed out"),
    ValueError("malformed provider response"),
):
    router, gemini, groq = make_router("auto", [transient_failure], ["groq-fallback"])
    assert request(router).content == "groq-fallback"
    assert (gemini.calls, groq.calls) == (1, 1)

router, gemini, groq = make_router("groq", ["unexpected"], ["groq-success"])
assert request(router).content == "groq-success"
assert (gemini.calls, groq.calls) == (0, 1)

router, gemini, groq = make_router(
    "auto",
    [ModelProviderError("service unavailable", status_code=503)],
    [ValueError("malformed provider response")],
)
try:
    request(router)
except ModelProviderError as error:
    assert str(error) == USER_FRIENDLY_UNAVAILABLE
    assert error.status_code == 503
else:
    raise AssertionError("both providers unavailable should return a clean temporary-unavailability error")
assert gemini.calls == 1 and groq.calls == 1


async def verify_async_fallback():
    router, gemini, groq = make_router("auto", [TimeoutError("timed out")], ["async-groq-fallback"])
    output = await router.aresponse(messages=[Message(role="user", content="Research MSFT")])
    assert output.content == "async-groq-fallback"
    assert (gemini.calls, groq.calls) == (1, 1)


asyncio.run(verify_async_fallback())

print("PROVIDER_FAILOVER_REGRESSION=PASS")
