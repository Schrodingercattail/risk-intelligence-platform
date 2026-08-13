"""
Tests for /api/risk/explain observability metrics.

Validates the three explanation-source / fallback cases end to end through the
real production code path (LLMExplanationService -> route metric helper ->
ExplainMetrics), without requiring a database or live LLM:

- Case 1: ENABLE_LLM_EXPLANATION=false      -> MODEL_FALLBACK, fallback_total++
- Case 2: LLM enabled + call succeeds       -> LLM,          fallback_total unchanged
- Case 3: LLM enabled + timeout/failure     -> MODEL_FALLBACK, fallback_total++

Also covers cache hit/miss accounting, fallback_rate math, reset, and an
explicit no-double-counting guard.
"""
import asyncio

from app.config import settings
from app.services.explain_metrics import ExplainMetrics, get_explain_metrics
from app.services.llm_service import LLMExplanationService, LLMProvider
from app.api.routes.risk import (
    _generate_model_based_explanation,
    _record_explanation_source_metrics,
)


RISK_EVENT = {
    "risk_score": 88.0,
    "risk_level": "HIGH",
    "primary_reason": "ML Pattern Detection",
    "ml_score": 90.0,
    "rule_score": 80.0,
    "graph_score": 50.0,
    "recommended_action": "Immediate Investigation",
}
RISK_FACTORS = [{"factor_name": "Shared Device Relationships"}]


class _FakeProvider(LLMProvider):
    """Deterministic LLM provider stub: returns text or raises a chosen error."""

    def __init__(self, *, text=None, exc=None):
        self.text = text
        self.exc = exc

    async def generate_explanation(self, prompt, system_prompt=None):
        if self.exc is not None:
            raise self.exc
        return self.text or "## Summary\nok\n## Key Findings\n- a\n## Recommended Action\nReview"


def _run_explain(metrics, monkeypatch, *, enable_llm, api_key, provider):
    """
    Mirror the /explain route's explanation-generation + source-metric recording.

    Recreates the exact decision the route makes after generating an explanation:
    whether the LLM was enabled and what source the generator reported. Returns
    (explanation, explanation_source, fallback_used).
    """
    monkeypatch.setattr(settings, "ENABLE_LLM_EXPLANATION", enable_llm)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", api_key)

    if enable_llm and api_key:
        service = LLMExplanationService(provider=provider)
        explanation = asyncio.run(
            service.generate_explanation("U1", RISK_EVENT, RISK_FACTORS)
        )
    else:
        explanation = _generate_model_based_explanation(RISK_EVENT, RISK_FACTORS, {})

    source, fallback_used = _record_explanation_source_metrics(metrics, explanation)
    return explanation, source, fallback_used


class TestExplainMetricsCounters:
    """Unit tests for the ExplainMetrics counter semantics."""

    def setup_method(self):
        self.m = ExplainMetrics()

    def test_llm_success_does_not_count_as_fallback(self):
        self.m.increment_llm()
        snap = self.m.get_metrics()
        assert snap["llm_total"] == 1
        assert snap["fallback_total"] == 0

    def test_llm_disabled_counts_as_fallback(self):
        self.m.increment_llm_disabled()
        snap = self.m.get_metrics()
        assert snap["llm_disabled_total"] == 1
        assert snap["fallback_total"] == 1

    def test_llm_failed_counts_as_fallback(self):
        self.m.increment_llm_failed()
        snap = self.m.get_metrics()
        assert snap["llm_failed_total"] == 1
        assert snap["fallback_total"] == 1

    def test_no_double_counting_within_a_single_outcome(self):
        # A failed outcome counts as fallback exactly once; a subsequent success
        # must not add another fallback.
        self.m.increment_llm_failed()
        assert self.m.get_metrics()["fallback_total"] == 1
        self.m.increment_llm()
        assert self.m.get_metrics()["fallback_total"] == 1

    def test_cache_hit_rate(self):
        self.m.increment_cache_hit()
        self.m.increment_cache_hit()
        self.m.increment_cache_miss()
        snap = self.m.get_metrics()
        assert snap["cache_hit_total"] == 2
        assert snap["cache_miss_total"] == 1
        assert snap["cache_hit_rate"] == round(2 / 3, 4)

    def test_fallback_rate_uses_requests_total(self):
        for _ in range(3):
            self.m.increment_requests()
        self.m.increment_llm_disabled()
        self.m.increment_llm_failed()
        snap = self.m.get_metrics()
        assert snap["fallback_total"] == 2
        assert snap["fallback_rate"] == round(2 / 3, 4)

    def test_reset_clears_counters(self):
        self.m.increment_llm_failed()
        self.m.increment_cache_hit()
        self.m.increment_requests()
        self.m.reset()
        snap = self.m.get_metrics()
        assert snap["fallback_total"] == 0
        assert snap["cache_hit_total"] == 0
        assert snap["llm_failed_total"] == 0
        assert snap["requests_total"] == 0


class TestExplanationSourceInstrumentation:
    """End-to-end (service + metric helper) for the three /explain cases."""

    def test_case1_llm_disabled_is_model_fallback(self, monkeypatch):
        metrics = ExplainMetrics()
        explanation, source, fallback_used = _run_explain(
            metrics, monkeypatch, enable_llm=False, api_key="", provider=None
        )

        # Model-based path does not set explanation_source; the helper defaults
        # it to MODEL_FALLBACK, and ExplanationResponse carries the same default.
        assert source == "MODEL_FALLBACK"
        assert fallback_used is True

        snap = metrics.get_metrics()
        assert snap["fallback_total"] == 1
        assert snap["llm_disabled_total"] == 1
        assert snap["llm_total"] == 0
        assert snap["llm_failed_total"] == 0

    def test_case2_llm_success_is_not_fallback(self, monkeypatch):
        metrics = ExplainMetrics()
        explanation, source, fallback_used = _run_explain(
            metrics, monkeypatch,
            enable_llm=True, api_key="test-key",
            provider=_FakeProvider(text="## Summary\nfine\n## Key Findings\n- x\n## Recommended Action\nReview"),
        )

        assert source == "LLM"
        assert fallback_used is False
        assert explanation["explanation_source"] == "LLM"
        assert explanation["llm_error"] is None

        snap = metrics.get_metrics()
        assert snap["llm_total"] == 1
        assert snap["fallback_total"] == 0
        assert snap["llm_failed_total"] == 0

    def test_case3_llm_timeout_is_fallback(self, monkeypatch):
        metrics = ExplainMetrics()
        explanation, source, fallback_used = _run_explain(
            metrics, monkeypatch,
            enable_llm=True, api_key="test-key",
            provider=_FakeProvider(exc=asyncio.TimeoutError()),
        )

        assert source == "MODEL_FALLBACK"
        assert fallback_used is True
        assert explanation["llm_error"] is not None

        snap = metrics.get_metrics()
        assert snap["fallback_total"] == 1
        assert snap["llm_failed_total"] == 1
        assert snap["llm_total"] == 0

    def test_case3_llm_exception_is_fallback(self, monkeypatch):
        metrics = ExplainMetrics()
        _, source, fallback_used = _run_explain(
            metrics, monkeypatch,
            enable_llm=True, api_key="test-key",
            provider=_FakeProvider(exc=RuntimeError("upstream 500")),
        )

        assert source == "MODEL_FALLBACK"
        assert fallback_used is True

        snap = metrics.get_metrics()
        assert snap["fallback_total"] == 1
        assert snap["llm_failed_total"] == 1

    def test_three_cases_on_shared_metrics_no_double_count(self, monkeypatch):
        """All three cases against one metrics instance -> independent counts."""
        metrics = ExplainMetrics()

        _run_explain(metrics, monkeypatch, enable_llm=False, api_key="", provider=None)
        _run_explain(
            metrics, monkeypatch,
            enable_llm=True, api_key="k",
            provider=_FakeProvider(text="## Summary\nok\n## Key Findings\n- a\n## Recommended Action\nr"),
        )
        _run_explain(
            metrics, monkeypatch,
            enable_llm=True, api_key="k",
            provider=_FakeProvider(exc=asyncio.TimeoutError()),
        )

        snap = metrics.get_metrics()
        assert snap["llm_disabled_total"] == 1
        assert snap["llm_total"] == 1
        assert snap["llm_failed_total"] == 1
        # Exactly two fallbacks (disabled + failed); the LLM success is NOT a fallback.
        assert snap["fallback_total"] == 2


class TestExplanationCacheMetrics:
    """Cache hit/miss accounting via the real ExplanationCache."""

    def test_cache_get_set_tracks_hit_and_miss(self):
        from app.api.routes.risk import ExplanationCache

        # ExplanationCache writes to the global metrics instance; isolate + reset it.
        metrics = get_explain_metrics()
        metrics.reset()
        try:
            cache = ExplanationCache(max_size=4, ttl_seconds=60)

            assert cache.get("missing") is None          # miss (key absent)
            cache.set("k", {"v": 1})
            assert cache.get("k") == {"v": 1}            # hit

            snap = metrics.get_metrics()
            assert snap["cache_miss_total"] == 1
            assert snap["cache_hit_total"] == 1
            # Cache lookups must not touch fallback/LLM source totals.
            assert snap["fallback_total"] == 0
            assert snap["llm_total"] == 0
        finally:
            metrics.reset()
