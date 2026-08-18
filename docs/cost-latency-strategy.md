# Cost & Latency Strategy for `/api/risk/explain`

This document describes the cost and latency controls for the `/api/risk/explain` endpoint, which serves risk case explanations for investigation workflows.

Explanations are **persisted canonical artifacts**, not transient cached responses. The endpoint reads through a three-tier architecture: an in-memory cache, a persisted canonical explanation, and — only when needed — generation.

---

## Goals

The `/api/risk/explain` endpoint provides cost-controlled, latency-bounded explanation serving for risk investigations:

- **Operational Continuity:** Investigation workflow remains functional regardless of LLM availability
- **Cost Control:** Rate limiting, caching, and persisted canonical explanations prevent runaway API costs and repeated generation
- **Latency Boundaries:** Timeout protection and tiered reads bound response times
- **Stable Narratives:** Ordinary reads return the same canonical explanation until an explicit regeneration or a case-version change
- **Transparent Fallback:** Clear indication of explanation source (LLM vs model-based)

---

## Non-Goals

- **Real-time Transaction Decisions:** This endpoint is for investigation workflow support, not transaction-time blocking
- **Per-Request Authorization:** Audience modes (investigator/business) are a demonstration feature; production should enforce RBAC via gateway/SSO
- **SLA Guarantees:** Default settings are starting points; production requires tuning based on traffic patterns

---

## Explanation Persistence & Cache Architecture

### Three-Tier Read/Generation Path

```
                Explanation Request
                       │
                       ▼
                Version Fingerprint
                       │
                       ▼
           ┌──────────────────────┐
           │ Tier 1: Memory Cache │  in-memory TTL cache (performance only)
           └──────────────────────┘
                       │ miss / expiry
                       ▼
          ┌──────────────────────────────┐
          │ Tier 2: Persisted Artifact   │  case_explanations table;
          │     (canonical explanation)  │  one row per user_id + audience
          └──────────────────────────────┘
                  │ absent / stale
                  ▼
          ┌──────────────────────────────┐
          │ Tier 3: Generate + Persist   │  LLM or deterministic fallback
          │ → citations → normalization  │  → citation assembly/validation
          │ → canonical artifact         │  → narrative contract → persist
          └──────────────────────────────┘
```

Explicit `POST /api/risk/explain/regenerate` bypasses the read tiers and intentionally enters generation.

### Tier 1 — In-Memory TTL Cache

```python
# backend/app/api/routes/risk.py
class ExplanationCache:
    def __init__(self, max_size: int = 1024, ttl_seconds: int = 600)
```

**Configuration:**

```python
EXPLAIN_CACHE_TTL_SECONDS: int = 600    # 10 minutes
EXPLAIN_CACHE_MAX_SIZE: int = 1024      # max cached entries
```

**Semantics:**

- Pure performance layer: accelerates repeated reads of the same canonical artifact
- **TTL expiration does NOT trigger LLM generation** — expiry falls through to Tier 2
- LRU eviction when full; per-worker (resets on restart), which is acceptable because Tier 2 survives restarts

**Cache key:** `SHA256(user_id + "|" + audience + "|" + version_fingerprint)` — see fingerprint below.

### Tier 2 — Persisted Canonical Explanation

Stored in the **`case_explanations`** table (one current row per `user_id` + `audience`), alongside the `version_fingerprint` identifying the case/version context it was generated for.

**Semantics:**

- This is the **canonical narrative artifact** for the current case version — not a cache entry
- Ordinary reads return this artifact without calling the LLM
- Survives process restarts and memory-cache expiration
- Prevents repeated generation of the same explanation across page reloads and multiple investigators viewing the same case

### Tier 3 — Generate + Persist

Entered only when:

- No persisted artifact exists (first generation for this case/audience), or
- The persisted artifact is **stale** (its `version_fingerprint` no longer matches the current case context), or
- Explicit regeneration is requested (`/api/risk/explain/regenerate`)

Generation pipeline:

```
LLM (default when enabled) or deterministic model-based fallback
    ↓
canonical evidence assembly
    ↓
citation retrieval + claim-level validation
    ↓
narrative contract normalization (numbering/format)
    ↓
persist as the new canonical artifact (case_explanations)
```

The persisted result — whether produced by the LLM or the deterministic fallback — becomes the current canonical artifact and is served by subsequent ordinary reads.

---

## Version Fingerprint

A persisted explanation is valid only for the same case/version context:

```
version_fingerprint = sha256(
    audience | risk_event_id | pipeline_run_id | model_version | policy_version
)
```

Computed by `compute_explanation_fingerprint()` (`backend/app/services/explanation_store_service.py`). When any fingerprint input changes — a new pipeline run, a different model version, or **when `policy_version` changes** — the stored explanation becomes stale, and the next ordinary read enters Tier 3 and persists a fresh canonical artifact.

> Note: fingerprint validity is based on the `policy_version` value that participates in the fingerprint, not on automatic detection of policy-file content changes.

The in-memory cache key folds in the same fingerprint, so a version change naturally misses Tier 1 as well.

---

## Ordinary Read vs Explicit Regeneration

### Ordinary Read — `POST /api/risk/explain`

```
Tier 1 memory cache
    ↓ miss
Tier 2 persisted canonical artifact
    ↓ absent / stale
Tier 3 generate + persist
```

- Cache expiry alone does **not** imply generation
- A valid persisted artifact satisfies the request with no model call
- Normal page reloads do **not** call the LLM again while the artifact is valid

**`bypass_cache=true`** skips only the Tier 1 memory cache:

```
bypass_cache=true
    ↓
skip Tier 1
    ↓
Tier 2 persisted artifact can still serve the request
```

It does **not** force regeneration, call the LLM, or discard the persisted artifact. To force a new generation, use the explicit regeneration endpoint.

### Explicit Regeneration — `POST /api/risk/explain/regenerate`

**From the Investigation UI, users can select "Regenerate with LLM"** (in the
Policy-backed Narrative header, next to the source badge; the button calls this
endpoint).

- Bypasses both read tiers
- Intentionally generates a new explanation (LLM, or deterministic fallback when unavailable)
- Runs the full citation/evidence/narrative pipeline
- Persists the result as the new canonical artifact for `(user_id, audience)`

**Regenerate with LLM is an explanation-level operation.** It does not rerun
ML inference, deterministic rule scoring, graph scoring, or final risk score
fusion — the risk event's scores and risk level are unchanged; only the
explanation artifact is replaced. Ordinary page loads never regenerate.

---

## LLM Default + Deterministic Fallback

### LLM Disabled (Default Configuration)

When `ENABLE_LLM_EXPLANATION=false` or no API key is configured:

```python
# Backend returns model-based explanations
explanation = _generate_model_based_explanation(risk_event, factors, graph_data)
# response.explanation_source = "MODEL_FALLBACK"
```

- Explanations generated from risk analysis outputs (ML scores, rule hits, graph signals)
- No external API calls, no cost
- The generated explanation is persisted as the canonical artifact like any other

### LLM Enabled — LLM Is the Default Generator

When `ENABLE_LLM_EXPLANATION=true` and `ANTHROPIC_API_KEY` is set, the LLM is the default explanation generator. On failure, the system falls back deterministically:

| Failure Type | Behavior | User Experience |
|-------------|----------|-----------------|
| Timeout (≥ `EXPLAIN_LLM_TIMEOUT_SECONDS`) | Falls back to model-based explanation | Delay up to the timeout, then structured response |
| Provider/API error | Falls back to model-based explanation | Brief delay, then structured response |
| No API key / disabled | Model-based explanation immediately | No delay, structured response |
| Rate limit (client) | Returns 429 status | Retry with backoff |

**Fallback is a generation path, not a temporary response:** a fallback-generated explanation is also persisted as the canonical artifact, and subsequent ordinary reads are served from it rather than recomputing.

**Critical:** Investigation workflow is never blocked by LLM unavailability or failures.

---

## Rate Limiting

Sliding window rate limiter per client IP:

```python
EXPLAIN_RATE_LIMIT_PER_MIN: int = 30  # requests per minute per client IP
```

- Window: 60 seconds sliding window
- Scope: Per client IP (x-forwarded-for, x-real-ip, or user_id fallback)
- Exceeded: Returns HTTP 429 with error message
- Applies to both ordinary reads and regeneration

| Traffic Pattern | Suggested Setting | Rationale |
|----------------|-------------------|-----------|
| Low-volume investigations (10-50 concurrent analysts) | 30-60 req/min | Prevents individual abuse while allowing normal workflow |
| High-volume operations (100+ analysts) | 60-120 req/min | Account for parallel investigation workflows |
| API-based integrations | Per-service quotas | Separate rate limit tiers for automated systems |

---

## Timeout Protection

### Application-Level LLM Timeout

```python
# backend/app/services/llm_service.py
explanation_text = await asyncio.wait_for(
    self.provider.generate_explanation(prompt),
    timeout=settings.EXPLAIN_LLM_TIMEOUT_SECONDS
)
```

```python
EXPLAIN_LLM_TIMEOUT_SECONDS: int = 30  # current default (config.py)
```

- **30 seconds is the current default application-level timeout for the LLM provider call**, not the entire HTTP request SLA
- Reasoning/thinking-capable gateway responses may require a longer execution window than plain chat completions, which is why the default is above naive chat-completion budgets
- The value remains configurable through environment/settings
- On timeout: returns a `MODEL_FALLBACK` explanation with `llm_error="LLM provider timeout"`; other errors set `llm_error="LLM generation failed"` or `"LLM provider error"`

### Latency Components (do not conflate)

| Component | What it covers | Typical order |
|-----------|----------------|---------------|
| Provider latency | Time inside the LLM API call | Variable; reasoning models slower |
| Application timeout | `EXPLAIN_LLM_TIMEOUT_SECONDS` bound on the provider call | 30s default |
| Cache-hit latency | Memory lookup only | Lowest |
| Persisted-read latency | DB read + deserialization, no model call | Low |
| Fresh-generation latency | Provider + citation retrieval + validation + persistence | Highest |
| Total request latency | Everything above plus rate-limit/data-fetch overhead | Path-dependent |

### Interactive Read vs Generation

- **Interactive reads** (valid memory or persisted artifact): fast; no model call
- **Fresh generation:** materially slower — provider latency plus citation assembly, validation, narrative normalization, and persistence
- Do not assume all explanation requests complete within a fixed small budget: the two paths have fundamentally different latency profiles

---

## Token Limiting

```python
LLM_MAX_TOKENS: int = 2000  # max tokens per LLM response
```

Token limits control response cost, not request cost. For production:

- Monitor average input tokens per request
- Set `LLM_MAX_TOKENS` based on acceptable output length
- Consider prompt optimization to reduce input token costs

---

## Cost Implications of Persisted Canonical Explanations

Without canonical persistence, every page reload or cache expiry could cause repeated generation:

```
Without persistence (historical behavior):
N page reads → potentially N generations
```

With the current architecture:

```
N page reads → typically 1 generation + many artifact reads,
               until explicit regeneration or a version change
```

- One generation can serve many ordinary reads
- Cache expiry no longer causes a regeneration storm — expired entries fall through to the persisted artifact
- Process restarts do not destroy canonical explanations (Tier 2 is durable)
- Multiple investigators viewing the same case do not trigger repeated model generation

This is a cost-shaping property, not a strict mathematical guarantee: under concurrent first-generation requests, generation is governed by current application behavior (see Concurrency below).

---

## Concurrency & Generation Storms

Persistence eliminates repeated generation across **cache expiry** and **process restarts**. Concurrent first-generation requests (no artifact yet, or stale) are governed by current application behavior: each such request runs the generation path. There is **no single-flight deduplication or distributed locking** in the current implementation — if concurrent cold requests are a concern in production, add request coalescing or an advisory lock around Tier 3.

---

## Monitoring Metrics

### Metrics Implemented (`/api/risk/metrics/explain`)

| Metric | Meaning |
|--------|---------|
| `requests_total` / `success_total` / `error_total` / `rate_limited_total` | Request counters |
| `cache_hit_total` / `cache_miss_total` / `cache_hit_rate` | Tier 1 in-memory cache performance |
| `persisted_total` | Reads served from the persisted canonical explanation (Tier 2) |
| `llm_total` | Successful LLM **generations** |
| `fallback_total` | Deterministic-fallback **generations** (= `llm_disabled_total` + `llm_failed_total`) |
| `latency_ms_p50` / `latency_ms_p95` / `latency_ms_avg` | Latency percentiles over a rolling window (last 1000 requests) |

**Key semantics:**

- `persisted_total` counts **persisted-artifact reads** — it is *not* an LLM generation count and must not be added to `llm_total`/`fallback_total`
- `llm_total` counts successful LLM generations only
- `fallback_total` counts deterministic fallback generations; `fallback_rate = fallback_total / requests_total`
- Cache hits and persisted reads skip regeneration, so they do not re-enter the LLM/fallback tallies — each logical explanation is counted once

**Interpretation:**

- High `llm_disabled_total` + low `fallback_rate`: platform operating as designed (no LLM configured)
- High `llm_failed_total` + high `fallback_rate`: LLM API issues (check key, rate limits, network)
- High `persisted_total` relative to `llm_total`: artifacts serving many reads — persistence working as intended

Counters are per-worker, in-memory, and reset on process restart. For distributed deployments use Prometheus / an APM instead (histograms for percentiles, external storage for cross-worker aggregation).

### Suggested Production Alerts

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `explain_cache_hit_rate` + `persisted_total` share | Gauge | Low combined artifact-serving rate (may indicate version churn) |
| `explain_fallback_rate` | Counter | > 10% of generations (may indicate LLM issues) |
| `explain_latency_p95` | Histogram | Elevated p95 among generation-path requests |
| `explain_429_count` | Counter | > 10/min (abuse or limit too low) |
| `explain_llm_error_count` | Counter | Sustained errors |

---

## Investigator Workflow Considerations

### Do Not Block Investigation UI

1. **Timeout Fallback:** If the LLM exceeds the timeout, a model-based explanation is returned after the timeout window
2. **Error Fallback:** On LLM API failure, return model-based explanation with error indicator
3. **Rate Limit Handling:** Return HTTP 429 with clear retry guidance; UI should handle gracefully
4. **Tiered Reads:** Check memory cache, then the persisted artifact, before any computation or API calls
5. **Stable Narratives:** Reloads return the same canonical explanation (no flicker of regenerated text)

### Audience Modes

The endpoint supports two output modes via the `audience` query parameter:

- **investigator** (default): Full detail with redacted quotes, complete key findings
- **business**: Reduced sensitive detail, sanitized quotes

**Note:** This is a demonstration feature. Production should enforce RBAC via API gateway or SSO integration.

---

## Configuration Reference

```python
# backend/app/config.py

# LLM Integration Toggle
ENABLE_LLM_EXPLANATION: bool = False          # LLM on/off (LLM is default generator when enabled + key set)
ANTHROPIC_API_KEY: str = ""                   # API credential

# LLM Model Settings
# Model selection is controlled through ANTHROPIC_MODEL. When using an
# Anthropic-compatible gateway (e.g. Zhipu GLM), the model id should match
# the gateway provider's model naming.
ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
LLM_MAX_TOKENS: int = 2000                    # Response size limit
LLM_TEMPERATURE: float = 0.3                  # Response randomness

# Cost & Latency Controls
EXPLAIN_CACHE_TTL_SECONDS: int = 600          # Tier 1 memory-cache TTL
EXPLAIN_CACHE_MAX_SIZE: int = 1024            # Tier 1 memory-cache capacity
EXPLAIN_RATE_LIMIT_PER_MIN: int = 30          # Rate limit per client
EXPLAIN_LLM_TIMEOUT_SECONDS: int = 30         # Application-level LLM provider timeout

# Privacy Controls
SHOW_USER_ID_IN_LLM_PROMPT: bool = False      # User ID redaction in LLM prompt
LOG_REDACT_USER_ID: bool = True               # User ID redaction in structured logs
```

---

## Implementation Summary

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `RateLimiter` | `backend/app/api/routes/risk.py` | Per-client rate limiting |
| `ExplanationCache` | `backend/app/api/routes/risk.py` | Tier 1 in-memory TTL cache (performance only) |
| `ExplanationStoreService` | `backend/app/services/explanation_store_service.py` | Tier 2 persisted canonical artifacts + version fingerprint |
| `CaseExplanation` | `backend/app/models/database.py` | Persistence model (`case_explanations`, unique per user+audience) |
| `narrative_contract` | `backend/app/services/narrative_contract.py` | Deterministic narrative normalization in Tier 3 |
| `LLMExplanationService` | `backend/app/services/llm_service.py` | LLM integration with timeout + deterministic fallback |
| `/explain` endpoint | `backend/app/api/routes/risk.py` | Ordinary read (tiered) |
| `/explain/regenerate` endpoint | `backend/app/api/routes/risk.py` | Explicit regeneration |

### Data Flow

```
Client Request
    │
    ▼
Rate Limit Check ───────────► 429 if exceeded
    │
    ▼
Fetch Risk Event ────────────► 404 if not found
    │
    ▼
Version Fingerprint
    │
    ├──► Tier 1 memory cache hit ──────────► return artifact
    │
    ├──► Tier 2 persisted artifact valid ──► return artifact (seed Tier 1)
    │
    ▼ (absent / stale, or explicit /regenerate)
Tier 3: canonical evidence → LLM or fallback
        → citations → narrative contract → persist artifact
    │
    ▼
Return Explanation
```

---

## Historical Note

Earlier revisions of this document described a single in-memory TTL cache with a 5-second LLM timeout, where cache expiration could lead to regeneration on the next request. That architecture predates persisted canonical explanations. Any historical measurements or budgets based on those assumptions (e.g. 2–3s SLA targets tied to a 5s timeout) should be read as **pre-persistence** context. The current architecture uses a 30-second default LLM timeout, persisted canonical explanations, and a three-tier read/generation path.

---

## Related Documentation

- [ML Pipeline Documentation](ml-pipeline.md) — Feature engineering and model scoring
- [Risk Event Lifecycle](risk-event-lifecycle.md) — Investigation workflow
- [Security & Privacy](security_privacy.md) — Data handling and sanitization
- Project `README.md` — Canonical Evidence, Narrative Contract, and citation architecture
