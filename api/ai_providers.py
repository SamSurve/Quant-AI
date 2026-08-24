"""Server-only, one-way AI provider engine for QuantAI.

The public API receives only a generic availability state. Provider order, model
selection, cooldowns, and credentials remain inside this module. The process-local
health store is suitable for a Vercel MVP warm instance but is intentionally
replaceable by a shared implementation in a later phase.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
import os
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator, TypeVar

from agno.agent import Agent
from agno.exceptions import ModelProviderError
from agno.models.base import Model
from agno.models.groq import Groq
from agno.models.openrouter import OpenRouter
from agno.models.response import ModelResponse
from pydantic import BaseModel, ValidationError

from .research_logging import log_research_event


USER_FRIENDLY_UNAVAILABLE = "AI analysis is temporarily unavailable. Please try again shortly."
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_OPENROUTER_MODEL = "stealth/ox-alpha"
DEFAULT_PROVIDER_ORDER = ("groq_primary", "groq_secondary", "openrouter_ox_alpha")
PROVIDER_ATTEMPT_TIMEOUT_SECONDS = 8
PERMANENT_FAILURE_COOLDOWN_SECONDS = 300
REPEATED_FAILURE_COOLDOWN_SECONDS = 60
REPEATED_FAILURE_THRESHOLD = 2

_ACTIVE_PROVIDER: ContextVar[str | None] = ContextVar("quantai_active_provider", default=None)
_REQUEST_ID: ContextVar[str | None] = ContextVar("quantai_provider_request_id", default=None)


class ProviderFailureCategory(str, Enum):
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    SERVER_ERROR = "SERVER_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProviderFailure:
    category: ProviderFailureCategory
    detail: str
    cooldown_seconds: int | None = None

    @property
    def retryable_by_next_provider(self) -> bool:
        return True


def _status_code(error: BaseException) -> int | None:
    for attribute in ("status_code", "status", "code"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value
    return None


def classify_provider_failure(error: BaseException) -> ProviderFailure:
    """Normalize provider-specific errors without retaining sensitive payloads."""

    status = _status_code(error)
    message = str(error).lower()
    if status == 429 or any(token in message for token in ("rate limit", "quota", "too many requests")):
        return ProviderFailure(ProviderFailureCategory.RATE_LIMITED, "rate limited")
    if status == 408 or isinstance(error, TimeoutError) or any(token in message for token in ("timeout", "timed out", "deadline exceeded")):
        return ProviderFailure(ProviderFailureCategory.TIMEOUT, "timeout")
    if status in {401, 403} or any(token in message for token in ("unauthorized", "forbidden", "authentication", "invalid api key")):
        return ProviderFailure(ProviderFailureCategory.AUTHENTICATION_FAILURE, "authentication failure", PERMANENT_FAILURE_COOLDOWN_SECONDS)
    if status == 404 or any(token in message for token in ("model not found", "unknown model", "does not exist")):
        return ProviderFailure(ProviderFailureCategory.MODEL_NOT_FOUND, "model unavailable", PERMANENT_FAILURE_COOLDOWN_SECONDS)
    if status in {500, 502, 503, 504, 529} or any(token in message for token in ("service unavailable", "overloaded", "internal server error")):
        return ProviderFailure(ProviderFailureCategory.SERVER_ERROR, "server error")
    if isinstance(error, (ConnectionError, OSError)) or any(token in message for token in ("connection", "network", "dns", "transport")):
        return ProviderFailure(ProviderFailureCategory.CONNECTION_ERROR, "connection error")
    if isinstance(error, (ValidationError, ValueError, TypeError)):
        return ProviderFailure(ProviderFailureCategory.MALFORMED_RESPONSE, "malformed response")
    return ProviderFailure(ProviderFailureCategory.UNKNOWN, type(error).__name__)


@dataclass
class ProviderHealth:
    consecutive_failures: int = 0
    unavailable_until: float = 0.0
    last_category: ProviderFailureCategory | None = None


class ProviderHealthStore:
    """Process-local cooldown state; inject a shared store for multi-instance use."""

    def __init__(self) -> None:
        self._state: dict[str, ProviderHealth] = {}

    def is_available(self, provider_name: str) -> bool:
        return self._state.get(provider_name, ProviderHealth()).unavailable_until <= time.monotonic()

    def record_success(self, provider_name: str) -> None:
        self._state[provider_name] = ProviderHealth()

    def record_failure(self, provider_name: str, failure: ProviderFailure) -> None:
        state = self._state.setdefault(provider_name, ProviderHealth())
        state.consecutive_failures += 1
        state.last_category = failure.category
        cooldown = failure.cooldown_seconds
        if cooldown is None and state.consecutive_failures >= REPEATED_FAILURE_THRESHOLD:
            cooldown = REPEATED_FAILURE_COOLDOWN_SECONDS
        if cooldown:
            state.unavailable_until = time.monotonic() + cooldown

    def safe_status(self, configured_names: tuple[str, ...]) -> dict[str, Any]:
        # Names/models are intentionally omitted from browser-visible health output.
        available = sum(1 for name in configured_names if self.is_available(name))
        return {
            "configured_count": len(configured_names),
            "available_count": available,
            "health_scope": "process_local",
        }


@dataclass(frozen=True)
class AIProvider:
    """Common configured provider interface used by AgentOS and typed synthesis."""

    name: str
    model_id: str
    model: Model
    configured: bool


def _configured_groq(name: str, key_name: str, model_name: str) -> AIProvider:
    api_key = os.getenv(key_name)
    model_id = os.getenv(model_name, DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    return AIProvider(
        name=name,
        model_id=model_id,
        model=Groq(
            id=model_id,
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


def build_groq_primary_provider() -> AIProvider:
    return _configured_groq("Groq primary", "GROQ_API_KEY_PRIMARY", "GROQ_MODEL_PRIMARY")


def build_groq_secondary_provider() -> AIProvider:
    return _configured_groq("Groq secondary", "GROQ_API_KEY_SECONDARY", "GROQ_MODEL_SECONDARY")


def build_openrouter_provider() -> AIProvider:
    api_key = os.getenv("OPENROUTER_API_KEY")
    model_id = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip() or DEFAULT_OPENROUTER_MODEL
    return AIProvider(
        name="OpenRouter Ox Alpha",
        model_id=model_id,
        model=OpenRouter(
            id=model_id,
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


def ordered_providers_from_environment(candidates: dict[str, AIProvider]) -> tuple[AIProvider, ...]:
    """Allow only a complete, duplicate-free permutation of known provider slots."""

    requested = tuple(
        item.strip().lower()
        for item in os.getenv("AI_PROVIDER_ORDER", ",".join(DEFAULT_PROVIDER_ORDER)).split(",")
        if item.strip()
    )
    if len(requested) != len(DEFAULT_PROVIDER_ORDER) or set(requested) != set(DEFAULT_PROVIDER_ORDER):
        requested = DEFAULT_PROVIDER_ORDER
    return tuple(candidates[name] for name in requested)


def _safe_provider_error(model_id: str) -> ModelProviderError:
    return ModelProviderError(
        message=USER_FRIENDLY_UNAVAILABLE,
        status_code=503,
        model_name="QuantAI",
        model_id=model_id,
    )


@dataclass
class ProviderRouter(Model):
    """One-way Model adapter for AgentOS: Groq primary → secondary → OpenRouter."""

    providers: tuple[AIProvider, ...] = ()
    health_store: ProviderHealthStore = field(default_factory=ProviderHealthStore)

    @classmethod
    def from_environment(cls) -> "ProviderRouter":
        return cls(
            id="quantai-provider-engine",
            name="QuantAI Provider Engine",
            provider="QuantAI",
            providers=ordered_providers_from_environment(
                {
                    "groq_primary": build_groq_primary_provider(),
                    "groq_secondary": build_groq_secondary_provider(),
                    "openrouter_ox_alpha": build_openrouter_provider(),
                }
            ),
            retries=0,
            retry_with_guidance=False,
            retry_with_guidance_limit=0,
        )

    def provider_status(self) -> dict[str, Any]:
        configured_names = tuple(provider.name for provider in self.providers if provider.configured)
        return {
            "strategy": "sequential_one_way",
            **self.health_store.safe_status(configured_names),
        }

    def _candidate_providers(self) -> tuple[AIProvider, ...]:
        configured = tuple(provider for provider in self.providers if provider.configured)
        active_name = _ACTIVE_PROVIDER.get()
        if active_name:
            for index, provider in enumerate(configured):
                if provider.name == active_name:
                    return configured[index:]
        return configured

    def _record_attempt(self, provider: AIProvider, attempt: int, started: float, outcome: str) -> None:
        log_research_event(
            "provider_attempt",
            request_id=_REQUEST_ID.get(),
            provider=provider.name,
            model=provider.model_id,
            attempt=attempt,
            duration_ms=round((time.monotonic() - started) * 1000),
            outcome=outcome,
        )

    def _call_sync(self, method_name: str, *args: Any, **kwargs: Any) -> ModelResponse:
        candidates = self._candidate_providers()
        for attempt, provider in enumerate(candidates, start=1):
            if not self.health_store.is_available(provider.name):
                self._record_attempt(provider, attempt, time.monotonic(), "cooldown_skip")
                continue
            started = time.monotonic()
            try:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quantai-provider")
                future = executor.submit(getattr(provider.model, method_name), *args, **kwargs)
                try:
                    response = future.result(timeout=PROVIDER_ATTEMPT_TIMEOUT_SECONDS)
                except FutureTimeoutError as error:
                    future.cancel()
                    raise TimeoutError("provider attempt timed out") from error
                finally:
                    # A timed-out upstream library call cannot always be interrupted,
                    # but the request advances without waiting for that thread.
                    executor.shutdown(wait=False, cancel_futures=True)
                self.health_store.record_success(provider.name)
                _ACTIVE_PROVIDER.set(provider.name)
                self._record_attempt(provider, attempt, started, "success")
                return response
            except Exception as error:
                failure = classify_provider_failure(error)
                self.health_store.record_failure(provider.name, failure)
                self._record_attempt(provider, attempt, started, failure.category.value)
        raise _safe_provider_error(self.id)

    async def _call_async(self, method_name: str, *args: Any, **kwargs: Any) -> ModelResponse:
        candidates = self._candidate_providers()
        for attempt, provider in enumerate(candidates, start=1):
            if not self.health_store.is_available(provider.name):
                self._record_attempt(provider, attempt, time.monotonic(), "cooldown_skip")
                continue
            started = time.monotonic()
            try:
                response = await asyncio.wait_for(
                    getattr(provider.model, method_name)(*args, **kwargs),
                    timeout=PROVIDER_ATTEMPT_TIMEOUT_SECONDS,
                )
                self.health_store.record_success(provider.name)
                _ACTIVE_PROVIDER.set(provider.name)
                self._record_attempt(provider, attempt, started, "success")
                return response
            except Exception as error:
                failure = classify_provider_failure(error)
                self.health_store.record_failure(provider.name, failure)
                self._record_attempt(provider, attempt, started, failure.category.value)
        raise _safe_provider_error(self.id)

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
        raise NotImplementedError("QuantAI ProviderRouter delegates response parsing to configured providers.")

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        raise NotImplementedError("QuantAI ProviderRouter delegates stream parsing to configured providers.")

    def structured_engine(self) -> "StructuredProviderEngine":
        return StructuredProviderEngine(self.providers, self.health_store)


Schema = TypeVar("Schema", bound=BaseModel)
StructuredRunner = Callable[[AIProvider, str, type[Schema]], Awaitable[Any]]


class StructuredProviderEngine:
    """Provider-neutral structured-analysis operation with one attempt per provider."""

    def __init__(
        self,
        providers: tuple[AIProvider, ...],
        health_store: ProviderHealthStore,
        runner: StructuredRunner | None = None,
    ) -> None:
        self.providers = providers
        self.health_store = health_store
        self._runner = runner or self._run_agent

    async def generate_structured(self, prompt: str, schema: type[Schema], request_id: str | None = None) -> Schema:
        token = _REQUEST_ID.set(request_id)
        try:
            for attempt, provider in enumerate((provider for provider in self.providers if provider.configured), start=1):
                if not self.health_store.is_available(provider.name):
                    self._log_attempt(provider, attempt, time.monotonic(), "cooldown_skip")
                    continue
                started = time.monotonic()
                try:
                    output = await asyncio.wait_for(
                        self._runner(provider, prompt, schema), timeout=PROVIDER_ATTEMPT_TIMEOUT_SECONDS
                    )
                    analysis = self._validate_output(output, schema)
                    self.health_store.record_success(provider.name)
                    self._log_attempt(provider, attempt, started, "success")
                    return analysis
                except Exception as error:
                    failure = classify_provider_failure(error)
                    self.health_store.record_failure(provider.name, failure)
                    self._log_attempt(provider, attempt, started, failure.category.value)
            raise _safe_provider_error("quantai-provider-engine")
        finally:
            _REQUEST_ID.reset(token)

    @staticmethod
    async def _run_agent(provider: AIProvider, prompt: str, schema: type[Schema]) -> Any:
        agent = Agent(
            model=provider.model,
            output_schema=schema,
            use_json_mode=True,
            instructions=[
                "Return only the requested structured interpretation.",
                "Use only the supplied deterministic context and never invent factual market values.",
            ],
            markdown=False,
            debug_mode=False,
        )
        response = await agent.arun(prompt)
        return response.content

    @staticmethod
    def _validate_output(output: Any, schema: type[Schema]) -> Schema:
        if output is None or output == "":
            raise ValueError("empty structured provider output")
        if isinstance(output, schema):
            return output
        if isinstance(output, str):
            return schema.model_validate_json(output)
        return schema.model_validate(output)

    @staticmethod
    def _log_attempt(provider: AIProvider, attempt: int, started: float, outcome: str) -> None:
        log_research_event(
            "provider_attempt",
            request_id=_REQUEST_ID.get(),
            provider=provider.name,
            model=provider.model_id,
            attempt=attempt,
            duration_ms=round((time.monotonic() - started) * 1000),
            outcome=outcome,
        )


def provider_runtime_status(router: ProviderRouter) -> dict[str, Any]:
    """Expose safe aggregate configuration metadata only; never credentials/models/names."""

    return router.provider_status()
