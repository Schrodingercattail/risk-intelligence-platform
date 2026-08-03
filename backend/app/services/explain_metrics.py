"""
Explain Endpoint Metrics Service

Provides in-memory metrics aggregation and structured logging for the
/api/risk/explain endpoint. Focuses on cache hit rate, fallback rate,
latency percentiles, and rate limit tracking.
"""
import time
import logging
import json
import threading
from collections import deque
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)


class ExplainMetrics:
    """
    In-memory metrics aggregator for /api/risk/explain endpoint.

    Tracks:
    - Request counters (total, success, error, rate limited)
    - Cache performance (hits, misses, hit rate)
    - Fallback behavior (fallback count, rate)
    - Latency distribution (rolling window for p50/p95)

    Fallback Semantics:
        fallback_total includes ALL cases where model-based explanation is used:
        - LLM disabled/no key (model-based explanation by default)
        - LLM attempted but failed/timeout (fallback triggered)
        - Note: fallback_rate = fallback_total / requests_total

        Additional counters for debugging:
        - llm_total: Successful LLM explanations
        - llm_disabled_total: Requests where LLM was not attempted (disabled/no key)
        - llm_failed_total: LLM attempted but failed/timeout

    Latency Semantics:
        - Rolling window of last N requests (default N=1000)
        - Resets on process restart; not cross-worker aware
        - Production: Use Prometheus histograms or APM for distributed deployments
        - p50/p95 calculated as: sort(latencies)[ceil(percentile * N) - 1]
    """

    def __init__(self, latency_window_size: int = 1000):
        """Initialize metrics with rolling window size for latency."""
        self.latency_window_size = latency_window_size

        # Request counters
        self._requests_total = 0
        self._success_total = 0
        self._error_total = 0
        self._rate_limited_total = 0

        # Cache counters
        self._cache_hit_total = 0
        self._cache_miss_total = 0

        # Fallback counters
        self._fallback_total = 0          # Total fallback (both disabled + failed)
        self._llm_total = 0               # Successful LLM explanations
        self._llm_disabled_total = 0      # LLM not attempted (disabled/no key)
        self._llm_failed_total = 0        # LLM attempted but failed/timeout

        # Latency tracking (rolling window)
        self._latencies_ms = deque(maxlen=latency_window_size)

        # Lock for thread safety (basic protection)
        self._lock = threading.Lock()

    def increment_requests(self) -> None:
        """Increment total request counter."""
        with self._lock:
            self._requests_total += 1

    def increment_success(self) -> None:
        """Increment success counter."""
        with self._lock:
            self._success_total += 1

    def increment_error(self) -> None:
        """Increment error counter."""
        with self._lock:
            self._error_total += 1

    def increment_rate_limited(self) -> None:
        """Increment rate limited counter."""
        with self._lock:
            self._rate_limited_total += 1
            self._requests_total += 1

    def increment_cache_hit(self) -> None:
        """Increment cache hit counter."""
        with self._lock:
            self._cache_hit_total += 1

    def increment_cache_miss(self) -> None:
        """Increment cache miss counter."""
        with self._lock:
            self._cache_miss_total += 1

    def increment_fallback(self) -> None:
        """Increment fallback counter."""
        with self._lock:
            self._fallback_total += 1

    def increment_llm(self) -> None:
        """Increment LLM counter (successful LLM explanations)."""
        with self._lock:
            self._llm_total += 1

    def increment_llm_disabled(self) -> None:
        """Increment LLM disabled counter (LLM not attempted due to disabled/no key)."""
        with self._lock:
            self._llm_disabled_total += 1
            self._fallback_total += 1  # Also counts as fallback

    def increment_llm_failed(self) -> None:
        """Increment LLM failed counter (LLM attempted but failed/timeout)."""
        with self._lock:
            self._llm_failed_total += 1
            self._fallback_total += 1  # Also counts as fallback

    def record_latency(self, latency_ms: float) -> None:
        """Record latency in milliseconds."""
        with self._lock:
            self._latencies_ms.append(latency_ms)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            Dict with all metrics and computed rates.

        Note on latency percentiles:
            - Computed over rolling window (last N requests, N=1000)
            - p50: 50th percentile (median)
            - p95: 95th percentile
            - Formula: sorted(latencies)[ceil(percentile * N) - 1]
            - Production: Use Prometheus histograms or APM for distributed deployments
        """
        import math

        with self._lock:
            # Calculate cache hit rate
            cache_requests = self._cache_hit_total + self._cache_miss_total
            cache_hit_rate = (
                self._cache_hit_total / cache_requests if cache_requests > 0
                else 0.0
            )

            # Calculate fallback rate (includes both disabled + failed)
            fallback_rate = (
                self._fallback_total / self._requests_total if self._requests_total > 0
                else 0.0
            )

            # Calculate latency percentiles using correct formula
            latencies = list(self._latencies_ms)
            if latencies:
                latencies_sorted = sorted(latencies)
                n = len(latencies_sorted)
                # Formula: idx = ceil(percentile * N) - 1
                p50_idx = int(math.ceil(0.50 * n)) - 1
                p95_idx = int(math.ceil(0.95 * n)) - 1
                p50 = latencies_sorted[p50_idx]
                p95 = latencies_sorted[p95_idx]
                avg = sum(latencies) / n
            else:
                p50 = 0.0
                p95 = 0.0
                avg = 0.0

            return {
                # Request counters
                "requests_total": self._requests_total,
                "success_total": self._success_total,
                "error_total": self._error_total,
                "rate_limited_total": self._rate_limited_total,

                # Cache metrics
                "cache_hit_total": self._cache_hit_total,
                "cache_miss_total": self._cache_miss_total,
                "cache_hit_rate": round(cache_hit_rate, 4),

                # Fallback metrics
                "fallback_total": self._fallback_total,
                "llm_total": self._llm_total,
                "llm_disabled_total": self._llm_disabled_total,
                "llm_failed_total": self._llm_failed_total,
                "fallback_rate": round(fallback_rate, 4),

                # Latency metrics
                "latency_ms_p50": round(p50, 2),
                "latency_ms_p95": round(p95, 2),
                "latency_ms_avg": round(avg, 2),

                # Metadata
                "latency_sample_count": len(latencies),
            }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._requests_total = 0
            self._success_total = 0
            self._error_total = 0
            self._rate_limited_total = 0
            self._cache_hit_total = 0
            self._cache_miss_total = 0
            self._fallback_total = 0
            self._llm_total = 0
            self._llm_disabled_total = 0
            self._llm_failed_total = 0
            self._latencies_ms.clear()


# Global metrics instance
_explain_metrics = ExplainMetrics()


def get_explain_metrics() -> ExplainMetrics:
    """Get the global explain metrics instance."""
    return _explain_metrics


def log_explain_request(
    status_code: int,
    latency_ms: float,
    cache_hit: bool,
    rate_limited: bool,
    fallback_used: bool,
    explanation_source: Optional[str] = None,
    citations_count: int = 0,
    audience: str = "investigator",
    user_id: Optional[str] = None,
) -> None:
    """
    Log structured JSON line for /api/risk/explain request.

    Args:
        status_code: HTTP status code
        latency_ms: Request duration in milliseconds
        cache_hit: Whether request was served from cache
        rate_limited: Whether request was rate limited
        fallback_used: Whether fallback to model-based explanation was used
        explanation_source: Source of explanation ("LLM" or "MODEL_FALLBACK")
        citations_count: Number of policy citations returned
        audience: Audience mode ("investigator" or "business")
        user_id: Optional user identifier (can be redacted)
    """
    log_entry = {
        "event": "risk_explain",
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "cache_hit": cache_hit,
        "rate_limited": rate_limited,
        "fallback_used": fallback_used,
        "explanation_source": explanation_source,
        "citations_count": citations_count,
        "audience": audience,
    }

    # Optionally include user_id (respect privacy settings)
    if user_id is not None:
        from app.config import settings
        if settings.LOG_REDACT_USER_ID:
            log_entry["user_id"] = "[REDACTED]"
        else:
            log_entry["user_id"] = user_id

    logger.info(json.dumps(log_entry))


def track_explain_request(func):
    """
    Decorator to track metrics and log structured JSON for explain endpoint.

    Usage:
        @track_explain_request
        async def generate_explanation(...):
            ...

    The decorator expects the wrapped function to return a tuple:
        (status_code, latency_ms, cache_hit, rate_limited, explanation_source, citations_count, audience)

    Or it will extract from the function context.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status_code = 200
        cache_hit = False
        rate_limited = False
        fallback_used = False
        explanation_source = None
        citations_count = 0
        audience = kwargs.get("audience", "investigator")
        user_id = kwargs.get("user_id")

        try:
            result = await func(*args, **kwargs)

            # Try to extract metrics from result
            if isinstance(result, dict):
                explanation_source = result.get("explanation_source")
                citations_count = len(result.get("citations", []))

            # Track success
            _explain_metrics.increment_requests()
            _explain_metrics.increment_success()

            status_code = 200

            return result

        except HTTPException as e:
            status_code = e.status_code
            if e.status_code == 429:
                _explain_metrics.increment_rate_limited()
                rate_limited = True
            else:
                _explain_metrics.increment_requests()
                _explain_metrics.increment_error()
            raise

        except Exception as e:
            status_code = 500
            _explain_metrics.increment_requests()
            _explain_metrics.increment_error()
            raise

        finally:
            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            _explain_metrics.record_latency(latency_ms)

            # Determine fallback
            fallback_used = (
                explanation_source == "MODEL_FALLBACK" or
                rate_limited or
                status_code >= 400
            )

            # Log structured JSON
            log_explain_request(
                status_code=status_code,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
                rate_limited=rate_limited,
                fallback_used=fallback_used,
                explanation_source=explanation_source,
                citations_count=citations_count,
                audience=audience,
                user_id=user_id,
            )

    return wrapper
