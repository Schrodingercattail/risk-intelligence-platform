# LLM Explanation Architecture

Optional LLM narrative generation with canonical evidence, policy grounding, citation validation, deterministic fallback, and persisted canonical artifacts.

This document describes how the LLM explanation layer fits into the Risk Platform architecture. Configuration numbers, latency/cost tables, and the full citation taxonomy live in the documents referenced at the end.

---

## Architecture Boundary

The LLM is an **explanation / narrative layer**. It is:

- **NOT** the risk scoring engine
- **NOT** an ML decision maker
- **NOT** the Rule Engine
- **NOT** the Graph detector
- **NOT** the evidence source of truth
- **NOT** the citation authority

The core pipeline:

```
Raw Data
  ↓
Feature Engineering
  ↓
ML / Rule / Graph scoring          (deterministic, LLM-independent)
  ↓
Canonical Evidence                 (source of truth for the explanation layer)
  ↓
Unified Findings
  ↓
LLM Narrative / Deterministic Fallback
  ↓
Claim-level Citation
  ↓
Narrative Contract                 (backend-owned presentation invariants)
  ↓
Persisted Canonical Explanation
```

**Canonical Evidence is the source of truth for the explanation layer.** The LLM organizes supplied evidence and must not invent findings, infer rule triggers from scores, or choose citations.

---

## Optional / Default / Fallback Semantics

LLM integration is optional at the **deployment/configuration level**:

```
ENABLE_LLM_EXPLANATION = true  AND  ANTHROPIC_API_KEY configured
→ LLM is the DEFAULT explanation generator
```

When the LLM is unavailable, times out, or the provider call fails, the **deterministic model-based fallback** is used (`explanation_source = "MODEL_FALLBACK"`).

Fallback is **not a separate explanation architecture** — it is the degradation path of the same pipeline. A fallback-generated explanation runs through the same citation assembly, narrative contract, and persistence, and becomes the canonical artifact for subsequent ordinary reads.

Without any LLM configuration the platform operates fully on the deterministic path.

---

## Canonical Evidence

`EvidenceService.get_canonical_evidence()` is the canonical evidence source for downstream explanation flows (LLM narrative, citation retrieval, investigation UI):

```python
canonical_evidence = {
    "ml": {
        "score",            # 0-100 system signal
        "probability",      # raw model output
        "primary_driver",
    },
    "rules": {
        "score",            # sum of triggered contributions, capped at 100
        "triggered",        # [{rule_name, trigger, threshold, contribution, description}]
        "consistent",       # derived evidence reconciles with the rule score
    },
    "graph": {
        "score",
        "has_evidence",
        "connected_accounts",   # when graph evidence exists
        "note",                 # explicit no-signal note when score = 0
    },
    "contextual": {
        "account_age_days",
        "account_age_note",
    },
    "findings": [ ... ],     # unified findings (see next section)
}
```

**Semantics:**

- **ML**: a system signal / prioritization measure — *not* a calibrated probability of fraud. The ML detector score and individual feature findings are different levels; ML score visibility never claims ML "detected" a specific feature finding.
- **Rules**: deterministic rules derived from actual feature values (`_derive_rule_evidence()`, kept aligned with `RiskScoringService._calculate_rule_score()`). Each triggered rule carries its observed values, threshold, and contribution; the LLM never infers rules from the rule score.
- **Graph**: relationship evidence only when actual graph evidence exists. `graph_score = 0` means "no detected graph signal" — no inference of isolation, evasion, or "lone wolf" behavior.
- **Contextual**: account age and similar context. Contextual evidence does not automatically become a policy-backed risk (see Citation Architecture).

### RiskFactor Semantics

`RiskFactor` rows are **persisted feature-level / contextual descriptive evidence**:

- RiskFactor ≠ ML finding
- RiskFactor ≠ Rule trigger
- RiskFactor ≠ Graph finding

A feature used by the ML model does not mean ML independently detected that finding. This distinction matters: an earlier iteration of the architecture incorrectly treated non-account-age RiskFactors as ML findings; the current architecture does not.

---

## Unified Findings

**Finding** and **detection source** are separate dimensions. The user-facing narrative presents a single unified list — **Key Risk Findings** — not separate "ML findings / Rule findings / Graph findings" buckets.

A finding may carry multiple internal `detection_sources`:

- *High Trading Frequency* → rule and/or feature provenance
- *Shared Device Relationships* → graph and feature provenance

`detection_sources` are **internal provenance**. They are never exposed in the narrative as "detected by Feature/Rule/Graph/ML" labels. The backend builds the unified finding list and deduplicates semantically equivalent findings (one conceptual finding appears once, with merged sources).

---

## LLM Generation Responsibility

The LLM receives the canonical structured evidence and is responsible for:

- Natural-language organization of the supplied findings
- Calibrated, investigation-oriented wording
- Summary generation and finding presentation
- Action wording (review/validation-oriented, no enforcement claims)

The LLM is **not** responsible for:

- Inferring rule triggers from the rule score
- Inventing evidence or unsupported fraud typologies
- Deciding which citation to use
- Numbering findings or actions
- Inserting citation markers

The **backend** owns: finding numbering, action numbering, citation numbering, contribution scrubbing, detection-source scrubbing, and all narrative invariants.

---

## Narrative Contract

The backend enforces a deterministic, case-invariant presentation contract (`narrative_contract.py`). The LLM does not own numbering or formatting.

Stable structure:

### What this means (Policy-backed)
High-level risk interpretation.

### Key Risk Findings
Evidence-backed findings, each with observed evidence.

### Next Actions (SOP-aligned)
Investigation-oriented action steps.

**Contract rules:**

- Findings numbered `1..N`; actions independently numbered `1..M` (always restarting at 1)
- Finding numbering and citation numbering are independent
- No contribution values in the default narrative (retained in Canonical Evidence)
- No raw implementation thresholds; no raw feature names unless justified
- No user-facing detection-source labels
- Graph-zero is neutral context (folded into the summary), not a numbered finding
- Findings without direct policy support may remain uncited

---

## Citation Architecture

```
Canonical Finding
  ↓
Claim refinement
  ↓
Semantic domain classification
  ↓
Policy retrieval (scoped)
  ↓
Claim-level validation
  ↓
Citation attachment if supported
```

**Core principle: no citation is better than a wrong citation.** A finding may exist without a citation.

Currently allowed to remain uncited (no directly matching policy in the corpus):

- First withdrawal to new address
- Coordinated trading (opposite-trade ratio)
- The new-account rule (corpus section on transfers-after-onboarding does not support the young-account AND high-trading conjunction)

Additional guarantees:

- Contextual account age does not automatically receive a KYC/CDD citation
- Graph-zero never receives a citation (absence of signal is not a policy-backed finding)
- The citation's quote must support the finding's **exact claim** — domain membership alone is insufficient
- Every finding in the final list keeps its number regardless of citation presence; citation IDs form their own contiguous sequence

---

## Persisted Canonical Explanation

Explanations are persisted case artifacts, served through three tiers:

```
Request
  ↓
Version Fingerprint
  ↓
Tier 1: In-memory TTL cache        (performance layer)
  ↓ miss / expiry
Tier 2: Persisted Artifact         (case_explanations table — canonical, NOT a cache)
  ↓ absent / stale
Tier 3: Generate + Persist         (LLM or deterministic fallback)
```

- **Tier 1** is a pure performance layer; TTL expiry falls through to Tier 2 and never triggers generation.
- **Tier 2** is the **canonical artifact** — one row per `(user_id, audience)` in `case_explanations`. It survives restarts and cache expiry; ordinary reads return it without any model call. It is not merely a cache: it *is* the current canonical explanation for the case version.
- **Tier 3** is the generation path: canonical evidence → LLM/fallback → claim-level citation assembly → narrative contract → persist as the new canonical artifact.

**Ordinary read** (`POST /api/risk/explain`): cache → persisted artifact → no generation when a valid artifact exists.

**Explicit regeneration** (`POST /api/risk/explain/regenerate`): bypasses the read tiers → generation → citation/narrative pipeline → persist → return.

`bypass_cache=true` on the ordinary endpoint skips only Tier 1; the persisted artifact may still serve the request.

### Version Fingerprint

```
version_fingerprint = sha256(
    audience | risk_event_id | pipeline_run_id | model_version | policy_version
)
```

The fingerprint identifies the case/version context for which a persisted explanation is valid. A new pipeline run, a different model version, or a **`policy_version` change** invalidates the artifact context — the next ordinary read regenerates. (Validity is based on the `policy_version` value participating in the fingerprint, not on automatic detection of policy-file content changes.)

---

## Explicit Regeneration

From the Investigation UI, users can select **"Regenerate with LLM"** (Policy-backed Narrative header, next to the source badge). The button calls the existing `POST /api/risk/explain/regenerate`.

Regeneration:

- Regenerates the **explanation only**
- Does **NOT** rerun ML scoring, rule scoring, graph scoring, or final risk score fusion — the risk event's scores and risk level remain unchanged
- Replaces the current canonical artifact
- Ordinary page opens never regenerate implicitly

UI helper text: *"Regenerates the explanation only; risk scores are not recalculated."*

---

## LLM Response Handling

Anthropic-compatible responses may contain multiple content blocks. The current provider implementation extracts the first block of type `text` rather than assuming the first content block is the final response.

- Thinking/reasoning blocks may precede the text block; the parser tolerates this response shape.
- A malformed response containing no text block raises a clear provider error and triggers the normal fallback path.

---

## Timeout & Reliability

```
EXPLAIN_LLM_TIMEOUT_SECONDS = 30   # current default
```

- Application-level timeout around the **LLM provider call** — not the total HTTP request SLA
- Configurable through environment/settings
- Reasoning/thinking-capable gateways may need longer execution windows (reason for the 30s default)
- Timeout triggers the deterministic fallback path

---

## Observability

Explanation-specific metrics (`/api/risk/metrics/explain`):

| Metric | Meaning |
|--------|---------|
| `llm_total` | Successful LLM generations |
| `fallback_total` | Deterministic-fallback generations (`llm_disabled_total` + `llm_failed_total`) |
| `persisted_total` | Reads served from the persisted canonical artifact |
| `cache_hit_total` / `cache_miss_total` | Tier 1 performance |
| `latency_ms_p50/p95/avg` | Latency percentiles |
| `requests_total` / `error_total` / `rate_limited_total` | Request counters |

**`persisted_total` is not an LLM generation count.** Ordinary persisted reads do not increment generation counters — generations and reads are counted independently.

---

## Cost & Latency Relationship

At the architecture level:

- **Cache** (Tier 1) is a performance optimization
- **Persistence** (Tier 2) provides canonical artifact stability and generation avoidance — ordinary reads of the same case do not repeatedly invoke the LLM
- **Explicit regeneration** is the intentional path for a new generation

Detailed latency budgets, tuning tables, and cost analysis: [`docs/cost-latency-strategy.md`](../cost-latency-strategy.md).

---

## Design Rationale

1. **Canonical Evidence before LLM** — prevents the LLM from becoming an evidence source; scoring stays deterministic and auditable.
2. **Unified Findings** — prevents ML/Rule/Graph presentation duplication; one conceptual finding appears once.
3. **Claim-level citation** — avoids false policy grounding; unsupported findings stay uncited rather than mis-cited.
4. **Persisted canonical artifact** — prevents repeated generation and narrative instability across reloads/restarts.
5. **Explicit regeneration** — narrative changes are intentional user actions, never side effects of cache expiry.
6. **Deterministic fallback** — the platform remains fully functional without LLM availability.
7. **Backend-owned narrative contract** — presentation structure does not drift with LLM output formatting.

---

## Historical Design Notes

The following records earlier review/decision context and is retained for architectural history; it does not describe additional current behavior beyond the sections above.

### Grounding Contract (P2)

An earlier review established the grounding rules now embodied in the prompt and narrative contract: evidence boundary (no invented factors/typologies), account-age as contextual evidence, ML/Graph score semantics (scores are signals; graph zero draws no conclusions), calibrated language, and the investigation-support boundary (no enforcement claims, no "policy requires" wording for unsupported findings). These rules remain in force and are enforced by both the prompt and the backend narrative contract.

### Configuration review

A prior consistency review confirmed: risk scoring is independent of explanation generation; the platform operates in ML-only mode without external dependencies; the `/explain` response contract is identical in LLM and fallback modes; LLM failure degrades gracefully without affecting scoring. Those properties still hold under the current architecture.

---

## Related Documentation

- [README](../../README.md) — product-level architecture, Canonical Evidence, Narrative Contract, persistence overview
- [Cost & Latency Strategy](../cost-latency-strategy.md) — latency budgets, cache/persistence tuning, cost analysis
- [Citation System Design](citation-system-design.md) — citation pipeline components
- [Data Contract](../data-contract.md) — API schemas
