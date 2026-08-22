"""Server-side provider abstraction for QuantAI research models.

The router deliberately keeps provider choice behind AgentOS. Browser clients only
communicate with the existing AgentOS routes and never receive provider credentials.
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass
import os
import time
from typing import Any, AsyncIterator, Iterator

from agno.exceptions import ModelProviderError
from agno.models.base import Model
from agno.models.google import Gemini
from agno.models.groq import Groq
from agno.models.response import ModelResponse


USER_FRIENDLY_UNAVAILABLE = "AI analysis is temporarily unavailable. Please try again shortly."
GEMINI_MODEL_ID = "gemini-2.5-flash"
GROQ_MODEL_ID = "openai/gpt-oss-120b"
_ACTIVE_PROVIDER: ContextVar[str | None] = ContextVar("quantai_active_provider", default=None)


def _error_message(error: BaseException) -> str:
    return str(error).lower()


def _is_temporary_provider_error(error: BaseException) -> bool:
    status = getattr(error, "status_code", None)
    if status in {429, 500, 502, 503, 504, 529}:
        return True
    return any(
        marker in _error_message(error)
        for marker in ("rate limit", "quota", "timeout", "timed out", "connection", "overloaded", "temporarily unavailable")
    )


def _safe_provider_error(error: BaseException, provider_name: str, model_id: str) -> ModelProviderError:
    return ModelProviderError(
        message=USER_FRIENDLY_UNAVAILABLE,
        status_code=503,
        model_name=provider_name,
        model_id=model_id,
    )


class ResilientGroq(Groq):
    """Keep Groq retries bounded before the provider router evaluates fallback."""

    retry_attempts = 1
    retry_delays = (1.0,)

    def _can_retry(self, error: ModelProviderError) -> bool:
        return _is_temporary_provider_error(error)

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        for attempt in range(self.retry_attempts + 1):
            try:
                return super().invoke(*args, **kwargs)
            except ModelProviderError as error:
                if attempt == self.retry_attempts or not self._can_retry(error):
                    raise
                time.sleep(self.retry_delays[attempt])
        raise RuntimeError("Unreachable Groq retry state.")

    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        for attempt in range(self.retry_attempts + 1):
            try:
                return await super().ainvoke(*args, **kwargs)
            except ModelProviderError as error:
                if attempt == self.retry_attempts or not self._can_retry(error):
                    raise
                await asyncio.sleep(self.retry_delays[attempt])
        raise RuntimeError("Unreachable Groq retry state.")


@dataclass(frozen=True)
class AIProvider:
    """A future-extensible server-side model provider descriptor."""

    name: str
    model_id: str
    model: Model
    configured: bool


def build_gemini_provider() -> AIProvider:
    api_key = os.getenv("GEMINI_API_KEY")
    return AIProvider(
        name="Gemini",
        model_id=GEMINI_MODEL_ID,
        model=Gemini(
            id=GEMINI_MODEL_ID,
            api_key=api_key,
            timeout=30,
            retries=1,
            delay_between_retries=1,
            exponential_backoff=True,
            retry_with_guidance=False,
            retry_with_guidance_limit=0,
        ),
        configured=bool(api_key),
    )


def build_groq_provider() -> AIProvider:
    api_key = os.getenv("GROQ_API_KEY")
    return AIProvider(
        name="Groq",
        model_id=GROQ_MODEL_ID,
        model=ResilientGroq(
            id=GROQ_MODEL_ID,
            api_key=api_key,
            max_tokens=1600,
            temperature=0.2,
            max_retries=0,
            retries=0,
            retry_with_guidance=False,
            retry_with_guidance_limit=0,
        ),
        configured=bool(api_key),
    )


@dataclass
class ProviderRouter(Model):
    """Select one provider per AgentOS run: Gemini → Groq → clean error.

    A provider is locked in a context variable after its first successful model
    response. Tool-follow-up model calls stay with that provider, preventing a
    Gemini/Groq bounce loop within one research request.
    """

    providers: tuple[AIProvider, ...] = ()
    mode: str = "auto"

    @classmethod
    def from_environment(cls) -> "ProviderRouter":
        requested_mode = os.getenv("AI_PROVIDER", "auto").strip().lower()
        mode = requested_mode if requested_mode in {"auto", "gemini", "groq"} else "auto"
        return cls(
            id="quantai-auto",
            name="QuantAI Provider Router",
            provider="QuantAI",
            providers=(build_gemini_provider(), build_groq_provider()),
            mode=mode,
            retries=0,
            retry_with_guidance=False,
            retry_with_guidance_limit=0,
        )

    def provider_status(self) -> dict[str, Any]:
        candidates = self._candidate_providers()
        return {
            "mode": self.mode,
            "primary": candidates[0].name if candidates else None,
            "fallback": candidates[1].name if len(candidates) > 1 else None,
            "configured_providers": [provider.name for provider in self.providers if provider.configured],
        }

    def _candidate_providers(self) -> tuple[AIProvider, ...]:
        configured = tuple(provider for provider in self.providers if provider.configured)
        if self.mode == "gemini":
            return tuple(provider for provider in configured if provider.name == "Gemini")
        if self.mode == "groq":
            return tuple(provider for provider in configured if provider.name == "Groq")
        return configured

    def _active_or_candidates(self) -> tuple[AIProvider, ...]:
        active_name = _ACTIVE_PROVIDER.get()
        candidates = self._candidate_providers()
        if active_name:
            for index, provider in enumerate(candidates):
                if provider.name == active_name:
                    return candidates[index:]
        return candidates

    def _decorate_response(self, response: ModelResponse, provider: AIProvider, is_backup: bool) -> ModelResponse:
        response.extra = dict(response.extra or {})
        response.extra["quantai_provider"] = provider.name
        response.extra["quantai_provider_status"] = "backup" if is_backup else "primary"
        return response

    def _call_sync(self, method_name: str, *args: Any, **kwargs: Any) -> ModelResponse:
        candidates = self._active_or_candidates()
        if not candidates:
            raise _safe_provider_error(RuntimeError("No configured provider"), "QuantAI", self.id)
        last_error: BaseException | None = None
        for index, provider in enumerate(candidates):
            try:
                response = getattr(provider.model, method_name)(*args, **kwargs)
                _ACTIVE_PROVIDER.set(provider.name)
                return self._decorate_response(response, provider, is_backup=index > 0)
            except Exception as error:
                last_error = error
                if index == len(candidates) - 1:
                    break
        raise _safe_provider_error(last_error or RuntimeError("Provider unavailable"), "QuantAI", self.id)

    async def _call_async(self, method_name: str, *args: Any, **kwargs: Any) -> ModelResponse:
        candidates = self._active_or_candidates()
        if not candidates:
            raise _safe_provider_error(RuntimeError("No configured provider"), "QuantAI", self.id)
        last_error: BaseException | None = None
        for index, provider in enumerate(candidates):
            try:
                response = await getattr(provider.model, method_name)(*args, **kwargs)
                _ACTIVE_PROVIDER.set(provider.name)
                return self._decorate_response(response, provider, is_backup=index > 0)
            except Exception as error:
                last_error = error
                if index == len(candidates) - 1:
                    break
        raise _safe_provider_error(last_error or RuntimeError("Provider unavailable"), "QuantAI", self.id)

    def response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        token = _ACTIVE_PROVIDER.set(None)
        try:
            return super().response(*args, **kwargs)
        finally:
            _ACTIVE_PROVIDER.reset(token)

    async def aresponse(self, *args: Any, **kwargs: Any) -> ModelResponse:
        token = _ACTIVE_PROVIDER.set(None)
        try:
            return await super().aresponse(*args, **kwargs)
        finally:
            _ACTIVE_PROVIDER.reset(token)

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self._call_sync("invoke", *args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return await self._call_async("ainvoke", *args, **kwargs)

    def invoke_stream(self, *args: Any, **kwargs: Any) -> Iterator[ModelResponse]:
        yield self._call_sync("invoke", *args, **kwargs)

    async def ainvoke_stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[ModelResponse]:
        yield await self._call_async("ainvoke", *args, **kwargs)

    def _parse_provider_response(self, response: Any, **kwargs: Any) -> ModelResponse:
        raise NotImplementedError("ProviderRouter delegates parsing to its selected provider.")

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        raise NotImplementedError("ProviderRouter delegates streaming parsing to its selected provider.")


def provider_runtime_status(router: ProviderRouter) -> dict[str, Any]:
    """Expose safe configuration metadata for health checks; never expose credentials."""
    return router.provider_status()
