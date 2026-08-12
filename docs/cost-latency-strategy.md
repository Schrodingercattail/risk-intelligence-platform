# Cost & Latency Strategy for `/api/risk/explain`

This document describes the cost and latency controls for the `/api/risk/explain` endpoint, which generates risk case explanations for investigation workflows.

---

## Goals

The `/api/risk/explain` endpoint provides cost-controlled, latency-bounded explanation generation for risk investigations:

- **Operational Continuity:** Investigation workflow remains functional regardless of LLM availability
- **Cost Control:** Rate limiting and caching prevent runaway API costs
- **Latency Boundaries:** Timeout protection ensures predictable response times
- **Transparent Fallback:** Clear indication of explanation source (LLM vs model-based)

---

## Non-Goals

- **Real-time Transaction Decisions:** This endpoint is for investigation workflow support, not transaction-time blocking
- **Per-Request Authorization:** Audience modes (investigator/business) are a demonstration feature; production should enforce RBAC via gateway/SSO
- **SLA Guarantees:** Default settings are starting points; production requires tuning based on traffic patterns

---

## Fallback Behavior

The platform is designed to operate fully without LLM integration. The `/explain` endpoint works in both modes:

### LLM Disabled (Default)

When `ENABLE_LLM_EXPLANATION=false` or no API key is configured:

```python
# Backend returns model-based explanations
explanation = _generate_model_based_explanation(
    risk_event, factors, graph_data
)
# response.explanation_source = "MODEL_FALLBACK"
```

**Behavior:**
- Explanations generated from risk analysis outputs (ML scores, rule hits, graph signals)
- No external API calls
- Zero latency overhead
- No cost incurred

### LLM Enabled

When `ENABLE_LLM_EXPLANATION=true` and `ANTHROPIC_API_KEY` is set:

```python
# Backend calls LLM API with timeout protection
explanation = await llm_service.generate_explanation(...)
# response.explanation_source = "LLM" (success) or "MODEL_FALLBACK" (failure)
```

**Behavior:**
- LLM generates natural language summaries
- Timeout protection (default 5s) with automatic fallback
- API failure falls back to model-based explanation
- Investigation workflow remains functional

### LLM Failure Scenarios

| Failure Type | Behavior | User Experience |
|-------------|----------|-----------------|
| Timeout (≥5s) | Falls back to model-based explanation | Brief delay, then structured response |
| API Error | Falls back to model-based explanation | Brief delay, then structured response |
| Rate Limit (client) | Returns 429 status | Retry with exponential backoff |
| No API Key | Uses model-based explanation immediately | No delay, structured response |

**Critical:** Investigation workflow is never blocked by LLM unavailability or failures.

---

## Rate Limiting

### Implementation

Sliding window rate limiter per client IP:

```python
# backend/app/api/routes/risk.py:87-119
class RateLimiter:
    def __init__(self, requests_per_minute: int = 30)
    def is_allowed(self, client_id: str) -> tuple[bool, Optional[str]]
```

### Default Configuration

```python
EXPLAIN_RATE_LIMIT_PER_MIN: int = 30  # requests per minute per client IP
```

### Behavior

- Window: 60 seconds sliding window
- Scope: Per client IP (x-forwarded-for, x-real-ip, or user_id fallback)
- Exceeded: Returns HTTP 429 with error message

### Production Tuning

Considerations for production environments:

| Traffic Pattern | Suggested Setting | Rationale |
|----------------|-------------------|-----------|
| Low-volume investigations (10-50 concurrent analysts) | 30-60 req/min | Prevents individual abuse while allowing normal workflow |
| High-volume operations (100+ analysts) | 60-120 req/min | Account for parallel investigation workflows |
| API-based integrations | Per-service quotas | Use separate rate limit tiers for automated systems |

---

## Caching

### Implementation

TTL-based LRU cache:

```python
# backend/app/api/routes/risk.py:43-74
class ExplanationCache:
    def __init__(self, max_size: int = 1024, ttl_seconds: int = 600)
```

### Cache Key

Cache keys incorporate all factors that affect explanation output:

```python
key = SHA256(user_id + audience + pipeline_run_id + model_version + policy_version)
```

### Default Configuration

```python
EXPLAIN_CACHE_TTL_SECONDS: int = 600    # 10 minutes
EXPLAIN_CACHE_MAX_SIZE: int = 1024     # max cached entries
```

### Cache Invalidation

- **TTL Expiration:** Entries expire after 600 seconds
- **LRU Eviction:** Oldest entries evicted when cache is full
- **Key Changes:** Different audience, pipeline run, model version, or policy version generate new cache entries

### Production Tuning

| Factor | Consideration |
|--------|---------------|
| TTL | Balance freshness vs cache hit rate. 10 minutes works for static risk data; reduce if real-time updates are frequent |
| Max Size | Estimate concurrent investigations × cache duration. 1024 supports ~100 req/min with 10-minute TTL |

---

## Timeout Protection

### Implementation

Async timeout wrapper with automatic fallback:

```python
# backend/app/services/llm_service.py:329-357
explanation_text = await asyncio.wait_for(
    self.provider.generate_explanation(prompt),
    timeout=settings.EXPLAIN_LLM_TIMEOUT_SECONDS
)
```

### Default Configuration

```python
EXPLAIN_LLM_TIMEOUT_SECONDS: int = 5  # seconds
```

### Behavior

- LLM call timeout → returns `MODEL_FALLBACK` explanation with `llm_error="LLM provider timeout"`
- Other errors → returns `MODEL_FALLBACK` explanation with `llm_error="LLM generation failed"`
- Investigation workflow continues with model-based explanation

### Production Tuning

| Scenario | Suggested Timeout | Rationale |
|----------|-------------------|-----------|
| Standard investigations | 5-10s | Balance responsiveness with LLM processing time |
| Complex explanations | 10-15s | Allow for longer prompts if using larger context windows |
| SLA-critical workflows | 2-3s | Prioritize fallback over waiting for LLM |

---

## Token Limiting

### Implementation

Max tokens parameter in LLM API call:

```python
# backend/app/services/llm_service.py:224-232
message = self.client.messages.create(
    model=settings.ANTHROPIC_MODEL,
    max_tokens=settings.LLM_MAX_TOKENS,
    ...
)
```

### Default Configuration

```python
LLM_MAX_TOKENS: int = 2000  # max tokens per LLM response
```

### Cost Impact

Token limits control response cost, not request cost. For production:

- Monitor average input tokens per request
- Set `LLM_MAX_TOKENS` based on acceptable output length
- Consider prompt optimization to reduce input token costs

---

## Configuration Reference

### All Cost & Latency Settings

```python
# backend/app/config.py

# LLM Integration Toggle
ENABLE_LLM_EXPLANATION: bool = False          # LLM on/off
ANTHROPIC_API_KEY: str = ""                  # API credential

# LLM Model Settings
# Model selection is controlled through ANTHROPIC_MODEL.When using an Anthropic-compatible gateway (e.g. Zhipu GLM),the model id should match the gateway provider's model naming.
ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
LLM_MAX_TOKENS: int = 2000                   # Response size limit
LLM_TEMPERATURE: float = 0.3                 # Response randomness

# Cost & Latency Controls
EXPLAIN_CACHE_TTL_SECONDS: int = 600         # Cache TTL
EXPLAIN_CACHE_MAX_SIZE: int = 1024           # Cache capacity
EXPLAIN_RATE_LIMIT_PER_MIN: int = 30         # Rate limit per client
EXPLAIN_LLM_TIMEOUT_SECONDS: int = 5         # LLM timeout

# Privacy Controls
SHOW_USER_ID_IN_LLM_PROMPT: bool = False     # User ID redaction in LLM prompt
LOG_REDACT_USER_ID: bool = True              # User ID redaction in structured logs
```

---

## Investigator Workflow Considerations

### Do Not Block Investigation UI

The `/explain` endpoint should never block the investigation workflow:

1. **Timeout Fallback:** If LLM exceeds timeout, return model-based explanation immediately
2. **Error Fallback:** If LLM API fails, return model-based explanation with error indicator
3. **Rate Limit Handling:** Return HTTP 429 with clear retry guidance; UI should handle gracefully
4. **Cache-First:** Check cache before any computation or API calls

### Audience Modes

The endpoint supports two output modes via the `audience` query parameter:

- **investigator** (default): Full detail with redacted quotes, complete key_findings
- **business**: Reduced sensitive detail, sanitized quotes

**Note:** This is a demonstration feature. Production should enforce RBAC via API gateway or SSO integration.

---

## Monitoring Metrics

### Suggested Metrics to Track

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `explain_cache_hit_rate` | Gauge | % of requests served from cache | < 50% (may indicate TTL too short) |
| `explain_fallback_rate` | Counter | % of requests falling back to model-based | > 10% (may indicate LLM issues) |
| `explain_latency_p95` | Histogram | 95th percentile response time | > 10s (may indicate timeout setting too high) |
| `explain_429_count` | Counter | Rate limit rejections per minute | > 10/min (may indicate abuse or limit too low) |
| `explain_llm_error_count` | Counter | LLM API errors by type | Any sustained errors |
| `explain_cache_size` | Gauge | Current cache entry count | Near max (may indicate cache too small) |

### Fallback Semantics

The `fallback_rate` metric has specific semantics:

```
fallback_rate = fallback_total / requests_total
```

**`fallback_total` includes ALL cases where model-based explanation is used:**
1. **LLM Disabled/No Key:** LLM was not attempted (disabled or no API key configured)
2. **LLM Failed:** LLM was attempted but failed (timeout or API error)

**Additional counters for debugging:**
- `llm_total`: Successful LLM explanations (explanation_source = "LLM")
- `llm_disabled_total`: LLM not attempted (disabled/no key)
- `llm_failed_total`: LLM attempted but failed/timeout

**Interpretation:**
- High `llm_disabled_total` + Low `fallback_rate`: Platform operating as designed (no LLM configured)
- High `llm_failed_total` + High `fallback_rate`: LLM API issues (check API key, rate limits, network)
- High `llm_total` + Low `fallback_rate`: LLM working correctly

### Latency Percentile Semantics

Latency percentiles (`latency_ms_p50`, `latency_ms_p95`) are computed as follows:

**Implementation:**
- **Rolling Window:** Last N requests held in memory (default N=1000)
- **Calculation:** `sorted(latencies)[ceil(percentile * N) - 1]`
- **Resets:** On process restart; not cross-worker aware

**Production Note:**
This in-memory implementation is suitable for single-process deployments. For production:
- Use **Prometheus histograms** for distributed percentile calculation
- Use **APM solutions** (Datadog, New Relic) for latency tracking
- Consider **external metrics storage** for cross-worker aggregation

### Metric Implementation Example

```python
# Example using Prometheus (pseudo-code)
from prometheus_client import Counter, Histogram, Gauge

explain_cache_hits = Counter('explain_cache_hits', 'Total cache hits')
explain_cache_misses = Counter('explain_cache_misses', 'Total cache misses')
explain_fallbacks = Counter('explain_fallbacks_total', 'Total fallbacks', ['reason'])
explain_latency = Histogram('explain_latency_seconds', 'Explanation latency')
explain_429s = Counter('explain_429s_total', 'Total 429 responses')
```

---

## Implementation Summary

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `RateLimiter` | `backend/app/api/routes/risk.py:87-119` | Per-client rate limiting |
| `ExplanationCache` | `backend/app/api/routes/risk.py:43-74` | TTL-based LRU cache |
| `_generate_cache_key` | `backend/app/api/routes/risk.py:144-156` | Cache key generation |
| `LLMExplanationService` | `backend/app/services/llm_service.py` | LLM integration with timeout |
| `/explain` endpoint | `backend/app/api/routes/risk.py:776-975` | Main endpoint with controls |

### Data Flow

```
Client Request
    │
    ▼
Rate Limit Check ────────► 429 if exceeded
    │
    ▼
Cache Lookup ─────────────► Return cached if hit
    │
    ▼
Fetch Risk Data
    │
    ▼
LLM Enabled? ────────────► No → Model-based explanation
    │ Yes                          │
    ▼                              │
LLM Call (with timeout)           │
    │                              │
    ├──── Timeout ────────────────┤
    ├──── Error ──────────────────┤
    │                              │
    ▼                              ▼
Return Explanation ◄──────────────┘
    │
    ▼
Store in Cache
    │
    ▼
Return Response
```

---

## Related Documentation

- [ML Pipeline Documentation](ml-pipeline.md) — Feature engineering and model scoring
- [Risk Event Lifecycle](risk-event-lifecycle.md) — Investigation workflow
- [Security & Privacy](security_privacy.md) — Data handling and sanitization
