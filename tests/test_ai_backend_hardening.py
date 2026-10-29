"""Automated regression and hardening test suite for QuantAI AI Research Backend (Milestone 11).

Verifies that:
- Provider routing, health tracking, and failover behave deterministically.
- Unconfigured/missing credentials produce safe unavailable state without crashing startup.
- Provider errors, exceptions, and logs redact secrets and API keys.
- Structured output validation unwraps markdown fences, discards hallucinated extra keys,
  normalizes enum cases, and truncates overflowing lists.
- Bounded prompt and output limits protect against resource exhaustion.
- Deterministic analysis remains 100% independent and functional when AI providers fail.
- Source records and provenance are preserved intact across successful and failed syntheses.
- Numeric claims in qualitative AI narratives are strictly rejected.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agno.exceptions import ModelProviderError
from agno.models.response import ModelResponse
from pydantic import BaseModel, ConfigDict, Field

from api.ai_providers import (
    AIProvider,
    ProviderFailure,
    ProviderFailureCategory,
    ProviderHealthStore,
    ProviderRouter,
    StructuredProviderEngine,
    USER_FRIENDLY_UNAVAILABLE,
    _extract_json_string,
    _sanitize_for_schema,
    classify_provider_failure,
)
from api.research_errors import ResearchError
from api.research_logging import log_research_event, scrub_secrets
from api.research_orchestrator import (
    AnalysisSynthesisService,
    CompanyAnalysisSynthesisService,
    ComparisonSynthesisService,
    ResearchOrchestrator,
)
from api.research_schemas import (
    CompanyDeepAnalysisInterpretation,
    CompanyDeepAnalysisReport,
    CompanyIdentity,
    CompanyComparisonInterpretation,
    CompanyComparisonReport,
    ErrorCategory,
    IdentifierConfidence,
    MarketSnapshot,
    OverallState,
    ResearchMode,
    ResearchRequest,
    ResearchResponse,
    ServiceState,
    ServiceStatus,
    SourceRecord,
    StructuredAnalysis,
)
from api.research_services import EntityResolution, MarketDataResult, NewsDataResult


class SimulatedProviderException(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeModel:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def invoke(self, *_args, **_kwargs):
        self.calls += 1
        if not self.outcomes:
            raise SimulatedProviderException("No more outcomes", 500)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return ModelResponse(content=str(outcome))

    async def ainvoke(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)


def make_test_router(
    primary_outcomes: list[object],
    secondary_outcomes: list[object],
    ox_outcomes: list[object],
) -> tuple[ProviderRouter, FakeModel, FakeModel, FakeModel]:
    p_model = FakeModel(primary_outcomes)
    s_model = FakeModel(secondary_outcomes)
    ox_model = FakeModel(ox_outcomes)

    router = ProviderRouter(
        id="quantai-provider-engine",
        name="QuantAI Provider Engine",
        provider="QuantAI",
        providers=(
            AIProvider("Groq primary", "primary-test", p_model, True),
            AIProvider("Groq secondary", "secondary-test", s_model, True),
            AIProvider("OpenRouter Ox Alpha", "stealth/ox-alpha", ox_model, True),
        ),
        retries=0,
        retry_with_guidance=False,
        retry_with_guidance_limit=0,
    )
    return router, p_model, s_model, ox_model


class TestAIBackendHardening(unittest.TestCase):
    """Milestone 11 AI Research Backend Hardening Test Suite."""

    def test_classify_provider_failure_all_categories(self):
        """Verify accurate classification of provider errors into typed failure categories."""
        # Payload too large
        f = classify_provider_failure(SimulatedProviderException("request context length exceeded", 413))
        self.assertEqual(f.category, ProviderFailureCategory.PAYLOAD_TOO_LARGE)

        # Rate limited
        f = classify_provider_failure(SimulatedProviderException("quota_exceeded: too many requests", 429))
        self.assertEqual(f.category, ProviderFailureCategory.RATE_LIMITED)
        self.assertEqual(f.cooldown_seconds, 60)

        # Timeout
        f = classify_provider_failure(TimeoutError("connection deadline exceeded"))
        self.assertEqual(f.category, ProviderFailureCategory.TIMEOUT)

        # Authentication failure (401 / 403)
        f = classify_provider_failure(SimulatedProviderException("invalid api key provided", 401))
        self.assertEqual(f.category, ProviderFailureCategory.AUTHENTICATION_FAILURE)
        self.assertEqual(f.cooldown_seconds, 300)

        # Model not found
        f = classify_provider_failure(SimulatedProviderException("model does not exist", 404))
        self.assertEqual(f.category, ProviderFailureCategory.MODEL_NOT_FOUND)
        self.assertEqual(f.cooldown_seconds, 300)

        # Server error
        f = classify_provider_failure(SimulatedProviderException("internal server error", 503))
        self.assertEqual(f.category, ProviderFailureCategory.SERVER_ERROR)

        # Connection error
        f = classify_provider_failure(ConnectionError("failed to connect to host"))
        self.assertEqual(f.category, ProviderFailureCategory.CONNECTION_ERROR)

        # Empty response
        f = classify_provider_failure(ValueError("empty structured provider output"))
        self.assertEqual(f.category, ProviderFailureCategory.EMPTY_RESPONSE)

        # Malformed response
        f = classify_provider_failure(ValueError("malformed JSON in provider output"))
        self.assertEqual(f.category, ProviderFailureCategory.MALFORMED_RESPONSE)

    def test_secret_redaction_in_errors_and_logs(self):
        """Provider error messages, exceptions, and structured logs must scrub API keys."""
        groq_leak = "Failed with key gsk_1234567890abcdef1234567890 in header"
        openrouter_leak = "Auth error for token sk-or-v1-abcdef1234567890abcdef1234567890"
        bearer_leak = "Authorization: Bearer secret_token_value_12345"

        self.assertNotIn("gsk_", scrub_secrets(groq_leak))
        self.assertNotIn("sk-or", scrub_secrets(openrouter_leak))
        self.assertNotIn("secret_token", scrub_secrets(bearer_leak))
        self.assertIn("[REDACTED_SECRET]", scrub_secrets(groq_leak))

        # Check classify_provider_failure scrubs secrets
        err = SimulatedProviderException(f"Invalid key: {groq_leak}", 401)
        failure = classify_provider_failure(err)
        self.assertEqual(failure.category, ProviderFailureCategory.AUTHENTICATION_FAILURE)
        self.assertNotIn("gsk_", failure.detail)

    def test_unconfigured_providers_empty_keys(self):
        """Empty or missing API keys produce safe unconfigured state without startup crash."""
        p_unconfigured = AIProvider("Unconfigured Groq", "test-model", FakeModel([]), False)
        health = ProviderHealthStore()
        engine = StructuredProviderEngine((p_unconfigured,), health)

        async def run_unconfigured():
            with self.assertRaises(ModelProviderError) as ctx:
                await engine.generate_structured("prompt", StructuredAnalysis, request_id="req-1")
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertEqual(ctx.exception.message, USER_FRIENDLY_UNAVAILABLE)

        asyncio.run(run_unconfigured())

    def test_provider_routing_failover_transient(self):
        """Primary provider 429 rate-limit triggers immediate transparent fallback to secondary."""
        router, p, s, ox = make_test_router(
            [SimulatedProviderException("rate limit", 429)],
            ['{"executive_summary": "secondary ok", "market_sentiment": "positive"}'],
            ["unexpected"],
        )
        health = router.health_store

        async def run_failover():
            async def fake_runner(provider: AIProvider, prompt: str, schema):
                resp = await provider.model.ainvoke(prompt)
                return resp.content

            engine = StructuredProviderEngine(router.providers, health, runner=fake_runner)
            res = await engine.generate_structured("test", StructuredAnalysis, request_id="r1")
            self.assertEqual(res.executive_summary, "secondary ok")
            self.assertEqual(p.calls, 1)
            self.assertEqual(s.calls, 1)
            self.assertEqual(ox.calls, 0)
            # Primary is now cooled down
            self.assertFalse(health.is_available("Groq primary"))
            self.assertTrue(health.is_available("Groq secondary"))

        asyncio.run(run_failover())

    def test_provider_permanent_error_cooldown_skip(self):
        """401 authentication failure triggers 300s cooldown and subsequent calls skip primary."""
        router, p, s, ox = make_test_router(
            [SimulatedProviderException("unauthorized", 401)],
            ['{"executive_summary": "call 1 ok"}', '{"executive_summary": "call 2 ok"}'],
            ["unexpected"],
        )
        health = router.health_store

        async def run_skip():
            async def fake_runner(provider: AIProvider, prompt: str, schema):
                resp = await provider.model.ainvoke(prompt)
                return resp.content

            engine = StructuredProviderEngine(router.providers, health, runner=fake_runner)
            # Call 1: primary fails 401, secondary succeeds
            res1 = await engine.generate_structured("test 1", StructuredAnalysis, request_id="r1")
            self.assertEqual(res1.executive_summary, "call 1 ok")
            self.assertEqual(p.calls, 1)
            self.assertEqual(s.calls, 1)

            # Call 2: primary is in cooldown, so it must be SKIPPED directly
            res2 = await engine.generate_structured("test 2", StructuredAnalysis, request_id="r2")
            self.assertEqual(res2.executive_summary, "call 2 ok")
            self.assertEqual(p.calls, 1)  # NOT incremented!
            self.assertEqual(s.calls, 2)  # Handled by secondary

        asyncio.run(run_skip())

    def test_structured_validation_markdown_fence_unwrapping(self):
        """Model responses wrapped in markdown code fences are cleanly extracted and validated."""
        raw_markdown = """```json
{
  "executive_summary": "Hardware refresh driving growth",
  "market_sentiment": "positive",
  "confidence": "high",
  "bullish_factors": ["Strong cash flow", "New silicon"]
}
```"""
        analysis = StructuredProviderEngine._validate_output(raw_markdown, StructuredAnalysis)
        self.assertEqual(analysis.executive_summary, "Hardware refresh driving growth")
        self.assertEqual(analysis.market_sentiment, "positive")
        self.assertEqual(analysis.confidence, "high")
        self.assertEqual(len(analysis.bullish_factors), 2)

    def test_structured_validation_discard_hallucinated_extra_keys(self):
        """Hallucinated extra keys from model output are safely stripped without failing extra='forbid'."""
        raw_with_extra = json.dumps({
            "executive_summary": "Valid summary",
            "market_sentiment": "neutral",
            "hallucinated_citation": "http://fake-source.test",
            "extra_metadata": {"score": 99},
        })
        analysis = StructuredProviderEngine._validate_output(raw_with_extra, StructuredAnalysis)
        self.assertEqual(analysis.executive_summary, "Valid summary")
        self.assertEqual(analysis.market_sentiment, "neutral")

    def test_structured_validation_enum_case_normalization(self):
        """Case mismatches on Literals (e.g. 'Positive' or 'HIGH') are normalized to schema values."""
        raw_case = json.dumps({
            "executive_summary": "Normalization test",
            "market_sentiment": "Positive",
            "confidence": "HIGH",
        })
        analysis = StructuredProviderEngine._validate_output(raw_case, StructuredAnalysis)
        self.assertEqual(analysis.market_sentiment, "positive")
        self.assertEqual(analysis.confidence, "high")

    def test_structured_validation_overflow_list_truncation(self):
        """Lists exceeding schema max_length are safely trimmed rather than failing validation."""
        raw_overflow = json.dumps({
            "executive_summary": "Overflow test",
            "bullish_factors": ["1", "2", "3", "4", "5", "6", "7", "8"],  # max_length is 5
        })
        analysis = StructuredProviderEngine._validate_output(raw_overflow, StructuredAnalysis)
        self.assertEqual(len(analysis.bullish_factors), 5)

    def test_structured_validation_malformed_json_rejected(self):
        """Malformed JSON strings raise ValueError with clear diagnostic error."""
        with self.assertRaises(ValueError) as ctx:
            StructuredProviderEngine._validate_output("{invalid json: broken", StructuredAnalysis)
        self.assertIn("malformed JSON", str(ctx.exception))

    def test_structured_validation_empty_output_rejected(self):
        """Empty string or None outputs raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            StructuredProviderEngine._validate_output("", StructuredAnalysis)
        self.assertIn("empty", str(ctx.exception))

    def test_structured_validation_oversized_payload_rejected(self):
        """Output exceeding 65KB is rejected to prevent resource exhaustion."""
        oversized = "x" * 70_000
        with self.assertRaises(ValueError) as ctx:
            _extract_json_string(oversized)
        self.assertIn("exceeds maximum allowable limit", str(ctx.exception))

    def test_prompt_length_limit(self):
        """Prompts exceeding 32,000 characters are rejected before dispatch."""
        engine = StructuredProviderEngine((), ProviderHealthStore())
        oversized_prompt = "Q" * 35_000

        async def run_oversized():
            with self.assertRaises(ValueError) as ctx:
                await engine.generate_structured(oversized_prompt, StructuredAnalysis)
            self.assertIn("exceeds maximum limit", str(ctx.exception))

        asyncio.run(run_oversized())

    def test_deterministic_independence_when_ai_fails(self):
        """Deterministic market and news data remain 100% available and intact when AI fails."""
        # Setup mock services
        company_id = CompanyIdentity(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NMS",
            sector="Technology",
            industry="Consumer Electronics",
            currency="USD",
            identifier_confidence=IdentifierConfidence.HIGH,
        )

        class MockEntityService:
            async def resolve(self, query: str):
                return EntityResolution(
                    company=company_id,
                    candidates=[],
                    source=SourceRecord(source="Test entity source", retrieved_at="2026-08-24T00:00:00Z", data_type="entity"),
                )

        class MockMarketService:
            async def fetch(self, comp):
                return MarketDataResult(
                    company=comp,
                    market=MarketSnapshot(current_price=220.0, as_of="2026-08-24T00:00:00Z"),
                    history=[],
                    status=ServiceState.AVAILABLE,
                    warning=None,
                    sources=[SourceRecord(source="Test market quote", retrieved_at="2026-08-24T00:00:00Z", data_type="market")],
                )

        class MockNewsService:
            async def fetch(self, comp):
                return NewsDataResult(
                    items=[],
                    status=ServiceState.AVAILABLE,
                    warning=None,
                    sources=[SourceRecord(source="Test news stream", retrieved_at="2026-08-24T00:00:00Z", data_type="news")],
                )

        class FailingAnalysisService:
            async def synthesize(self, res):
                raise ResearchError(ErrorCategory.AI_UNAVAILABLE, detail="Simulated AI outage", retryable=True)

        orchestrator = ResearchOrchestrator(
            entity_service=MockEntityService(),
            market_service=MockMarketService(),
            news_service=MockNewsService(),
            analysis_service=FailingAnalysisService(),
        )

        async def run_orchestrator_resilience():
            req = ResearchRequest(query="AAPL", include_analysis=True)
            res = await orchestrator.research("req-resilience-1", req)

            # Deterministic data MUST be present
            self.assertIsNotNone(res.company)
            self.assertIsNotNone(res.market)
            self.assertEqual(res.market.current_price, 220.0)
            self.assertEqual(res.status.market, ServiceState.AVAILABLE)
            self.assertEqual(res.status.news, ServiceState.AVAILABLE)

            # AI status must be UNAVAILABLE, not raising a 500
            self.assertEqual(res.status.ai, ServiceState.UNAVAILABLE)
            self.assertIsNone(res.analysis)

            # Source attribution: market and news sources are preserved intact
            source_types = [s.data_type for s in res.sources]
            self.assertIn("entity", source_types)
            self.assertIn("market", source_types)
            self.assertIn("news", source_types)
            self.assertNotIn("analysis", source_types)

            # Warning must be cleanly present
            warning_cats = [w.category for w in res.warnings]
            self.assertIn(ErrorCategory.AI_UNAVAILABLE, warning_cats)

        asyncio.run(run_orchestrator_resilience())

    def test_deep_analysis_numeric_narrative_guard(self):
        """Quantitative figures in AI narratives are rejected to prevent hallucinated numbers."""
        # Narrative with explicit number claim ($120B)
        with self.assertRaises(ResearchError) as ctx:
            CompanyAnalysisSynthesisService._assert_no_numeric_claims(
                CompanyDeepAnalysisInterpretation(executive_summary="The company posted revenue of $120B.")
            )
        self.assertEqual(ctx.exception.category, ErrorCategory.AI_UNAVAILABLE)

        # Narrative with two-digit number (123)
        with self.assertRaises(ResearchError) as ctx:
            CompanyAnalysisSynthesisService._assert_no_numeric_claims(
                CompanyDeepAnalysisInterpretation(executive_summary="Operating margin reached 45%.")
            )
        self.assertEqual(ctx.exception.category, ErrorCategory.AI_UNAVAILABLE)

        # Clean narrative without numeric claims passes
        clean_interp = CompanyDeepAnalysisInterpretation(
            executive_summary="The company maintains superior gross margin and robust subscription recurring revenue.",
            confidence="high",
        )
        CompanyAnalysisSynthesisService._assert_no_numeric_claims(clean_interp)

    def test_comparison_numeric_narrative_guard(self):
        """Quantitative claims in comparative narrative are also rejected."""
        with self.assertRaises(ResearchError) as ctx:
            CompanyAnalysisSynthesisService._assert_no_numeric_claims(
                CompanyComparisonInterpretation(executive_summary="Company A outperformed by 25%.")
            )
        self.assertEqual(ctx.exception.category, ErrorCategory.AI_UNAVAILABLE)

        clean_comp = CompanyComparisonInterpretation(
            executive_summary="Company A leads on top-line consumer hardware scale while Company B shows stronger recurring enterprise software margins.",
            confidence="high",
        )
        CompanyAnalysisSynthesisService._assert_no_numeric_claims(clean_comp)


if __name__ == "__main__":
    unittest.main()
