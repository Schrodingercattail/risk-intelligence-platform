# Risk Platform — System Architecture

Status: current (2026-08). This document describes the architecture as
implemented, including the explanation-layer semantics introduced with
canonical evidence, the narrative contract, and explanation persistence.
For the data/API field-level contract see `docs/data-contract.md`; for the
detailed LLM Explanation subsystem design see
`docs/architecture/llm-explanation-design.md`.

---

## 1. System Overview

The Risk Intelligence Platform detects abnormal user behavior by combining
three deterministic detection components — a machine-learning model (LightGBM),
a rule engine, and graph/network analysis — into a single fused risk score
per user. Detection output is persisted as immutable `RiskEvent` rows.

Around that detection core sits an **explanation pipeline** that turns a
scored case into an investigator-facing narrative: canonical evidence is
derived from the persisted source data, an optional LLM writes the narrative
under a strict grounding contract, a backend-owned narrative contract aligns
the wording to the canonical findings, and the result is persisted as a
`CaseExplanation` artifact that the Investigation UI serves.

The defining architectural rule: **detection is deterministic and LLM-free;
the LLM only explains.** No explanation-layer operation — generation,
regeneration, citation, or persistence — recalculates risk scores.

## 2. Main Layers

| Layer | Component | Responsibility |
|---|---|---|
| Source / features | `FeatureTable`, raw trade/withdrawal/device/graph tables | Persisted, recomputable source facts (e.g. `opposite_trade_ratio = 0.3438`) |
| Risk scoring | `RiskScoringService` (`risk_service.py`) | ML (0.5) + Rule (0.3) + Graph (0.2) fusion; risk level incl. CRITICAL override |
| Risk result | `RiskEvent` | Immutable historical scoring result: scores, level, pipeline run, model version |
| Derived signals | `RiskFactor` rows | Feature-level/contextual descriptive evidence written at scoring time |
| Canonical evidence | `EvidenceService.get_canonical_evidence()` | **Authoritative findings layer**: unified, deduplicated findings with detection sources, thresholds, contributions |
| LLM explanation | `LLMExplanationService` (`llm_service.py`) | Narrative generation under a grounding contract; deterministic fallback on failure |
| Narrative contract | `narrative_contract.py` | Backend-owned presentation: numbering, merge to canonical names, completeness, scrubbing, invariant validation |
| Persistence | `explanation_store_service.py`, `case_explanations` | Canonical explanation artifact, one row per (user, audience), version-fingerprinted |
| UI | `frontend/src/pages/Investigation.tsx` | Renders the persisted explanation; "Regenerate with LLM" button |

## 3. Data Flow

```
FeatureTable / source data
        ↓
Risk Scoring  (ML + Rule + Graph, deterministic)
        ↓
RiskEvent  (immutable: scores, level, pipeline_run_id, model_version)
        ↓
RiskFactors  (feature-level descriptive evidence, written at scoring time)
        ↓
Canonical Evidence  (rebuilt on demand from CURRENT source data + CURRENT
                     semantic rules — authoritative set of findings)
        ↓
LLM Explanation  (narrative wording only; receives ALL canonical findings;
                  deterministic fallback on failure)
        ↓
Narrative Contract  (aligns wording to canonical findings; numbering;
                     completeness guarantee; scrubbing)
        ↓
CaseExplanation  (persisted canonical artifact, version-fingerprinted)
        ↓
Investigator UI
```

Two distinct lifecycles run through this diagram:

- **Scoring lifecycle** (top half): runs when the pipeline executes. Produces
  `RiskEvent` + `RiskFactor` rows. Never triggered by explanation reads.
- **Explanation lifecycle** (bottom half): runs on demand. Reads persisted
  data, rebuilds canonical evidence, generates/aligns narrative, persists.
  Never writes risk scores.

## 4. The Regenerate Lifecycle

**"Regenerate with LLM" does not rerun risk scoring.**

`POST /api/risk/explain/regenerate` (Investigation UI button) performs:

1. Re-read the persisted `RiskEvent` (latest per user) — scores are read, never computed.
2. Re-read the `FeatureTable` / factors / graph data.
3. Rebuild canonical evidence from that source data using the **current**
   semantic rules (see §6 — this is how a case scored before a semantics fix
   gets correct finding names on regeneration without rescoring).
4. Generate the explanation (LLM, or deterministic fallback on failure).
5. Apply the narrative contract (alignment + completeness).
6. Persist as the new canonical `CaseExplanation` (replaces the previous
   (user, audience) row) and return it.

Why no rescoring: the risk result is a **historical fact** about what the
detection pipeline computed for that source data at that time. Regeneration
is an explanation-level operation over the same facts; recomputing scores
would conflate "what the system detected then" with "how we explain it now",
break audit trail integrity (`pipeline_run_id` / `model_version` provenance),
and make explanation actions capable of changing case priority.

An ordinary read (`POST /api/risk/explain`) never regenerates: it serves the
persisted artifact when its version fingerprint still matches (audience +
risk event identity + pipeline run + model version + policy version).
Regeneration is the only path that replaces a valid artifact.

## 5. Source-of-Truth Hierarchy

From most to least authoritative, for each kind of question:

| Question | Authority |
|---|---|
| What was the risk score / level / component scores? | `RiskEvent` (immutable historical result) |
| What source behavior was observed? | `FeatureTable` / raw source tables |
| Which findings exist for this case? | **Canonical evidence** (`findings[]`) |
| How is a finding worded in the narrative? | LLM narrative, aligned by the narrative contract |
| What policy backs a claim? | Citation layer (claim-level validated policy quotes) |

Consequences:

- The LLM **does not decide which findings exist**. It receives the complete
  canonical finding list; the narrative contract realigns its output to that
  list and appends any canonical finding the narrative failed to cover
  (completeness guarantee — authoritative findings can never be silently
  dropped from the rendered explanation).
- Historical `RiskFactor` labels are descriptive evidence, not the finding
  authority: canonical evidence derives findings from `FeatureTable` values
  under current semantics, so a case scored under old semantics still gets
  current finding names on explanation regeneration (no rescoring needed).
- Risk score semantics (thresholds, contributions, fusion) live in the
  scoring layer only; the narrative presents them in business language.

## 6. `opposite_trade_ratio` Semantics

Business rule (scoring layer, strict inequality — mirrored by the evidence
derivation and the narrative wording):

```
0 < ratio <= 0.4   →  finding "Opposite Trade Ratio"
                      observed metric; coordinated-trading rule NOT triggered
                      (no rule contribution; threshold-explicit narrative:
                       "…was observed, which is below the 40% threshold for
                       the coordinated trading rule")

ratio > 0.4        →  finding "Coordinated Trading Pattern"
                      coordinated-trading rule triggered (+35 rule contribution)
                      ("…exceeded the 40% threshold, triggering the
                       coordinated trading rule")
```

Example: U00010 has `opposite_trade_ratio = 0.3438` (34.38%). Its canonical
evidence contains "Opposite Trade Ratio" — an observed metric below
threshold — and must never be labeled or narrated as "Coordinated Trading
Pattern". The narrative for below-threshold values must not imply the rule
fired (e.g. no "potentially coordinated trading behavior" phrasing);
above-threshold values must state the rule triggered.

The threshold lives in one semantic definition (`_calculate_rule_score`,
mirrored in `EvidenceService._THRESHOLD_FINDINGS` / `_derive_rule_evidence`);
the LLM prompt renders the same distinction via threshold-aware evidence
lines and explicit wording rules.

## 7. Finding / Explanation Responsibilities

| Concern | Owner |
|---|---|
| Detection (does this behavior exist?) | ML / Rule / Graph scoring components |
| Finding existence & names | Canonical evidence (`findings[]`) |
| Finding wording | LLM narrative (aligned by narrative contract); deterministic fallback |
| Numbering / sections / format | Narrative contract (backend-owned; LLM never numbers) |
| Policy citations | Citation layer (claim-level validation; uncited findings are valid) |
| Explanation persistence | `case_explanations` (canonical artifact per user+audience) |
| Risk scores | `RiskEvent` only — never the explanation layer |

Narrative contract invariants (enforced by `validate_narrative_invariants()`):
findings numbered 1..N by the backend; actions restart at 1..M independently;
citation IDs are a third numbering; no score contributions, raw field names,
threshold syntax, or detection-provenance wording in user-facing text;
graph-zero absence is informational context, never a numbered finding.

## 8. Persistence Model

- **`RiskEvent` is immutable history.** Scores, level, `pipeline_run_id`,
  `model_version` are written once by the scoring pipeline. Explanation
  operations never update them.
- **`CaseExplanation` is regenerable.** One row per (user_id, audience) —
  it is the canonical explanation artifact, not a cache. Regeneration
  replaces it; ordinary reads serve it while valid.
- **Tiering** (read path): Tier 1 in-memory TTL cache (performance only;
  expiry never triggers generation) → Tier 2 persisted artifact (served when
  its `version_fingerprint` matches) → Tier 3 generate + persist (only when
  absent/stale, or explicit regeneration).
- **`version_fingerprint`** = `sha256(audience | risk_event_id | pipeline_run_id | model_version | policy_version)`
  — ties the artifact to the exact case version that produced it.
- **Reinterpretation without rescoring**: because canonical evidence is
  rebuilt from `FeatureTable` under current semantics at explanation time,
  semantic fixes (finding renames, threshold-splitting) apply to historical
  cases on their next regeneration while every score stays byte-identical.

## 9. Failure Boundaries

| Failure | Behavior |
|---|---|
| Scoring pipeline fails | No `RiskEvent` is written; explanation endpoints return 404 for the user (nothing to explain). Existing artifacts for other cases unaffected. |
| Canonical evidence build fails | Generation is not attempted from partial state; the request errors. The previously persisted artifact remains intact and keeps being served. |
| LLM unavailable / timeout / provider error | The deterministic model-based fallback runs the SAME citation → narrative-contract → persistence pipeline and its output becomes the canonical artifact (`explanation_source: MODEL_FALLBACK`, `llm_error` surfaced). |
| Narrative contract rejects/normalizes a line | The line is realigned or folded as supporting text; unmatched canonical findings are appended by the completeness rule (never silently dropped); invariant violations are detectable via `validate_narrative_invariants()`. |
| Regeneration fails | The currently displayed (persisted) explanation is preserved; the UI reports failure. No score or artifact mutation. |
| Persistence write fails | The explanation response still returns (persist failure is logged, non-fatal); the next read regenerates. |

Design intent: explanation-layer failures degrade to deterministic output or
to the last good artifact — they never propagate upward into scoring state.

## 10. Design Principles

1. **Canonical evidence is authoritative for finding existence.** The
   explanation pipeline may word findings, align them, or cite them — never
   add, drop, or rename them independently.
2. **The LLM is not authoritative for detection facts.** It receives
   findings; it does not produce them. Its output is realigned to canonical
   findings before persistence.
3. **Regeneration never rescores.** Explanation-level operations cannot
   change risk scores, levels, or component scores.
4. **Persist source facts, not just conclusions.** `FeatureTable` and raw
   tables carry enough detail that canonical evidence (and future semantic
   fixes) can be rebuilt for any historical case without rescoring.
5. **Presentation terminology matches business-rule semantics.** A
   below-threshold observation is named and worded as an observation; a
   triggered rule is named and worded as triggered. Wording drift between
   layers is treated as a defect.
6. **Detection provenance is internal.** Investigators see findings; ML /
   Rule / Graph / Feature source labels stay in canonical evidence.
7. **No citation is better than a wrong citation.** Uncited findings are
   valid; citations must support the finding's exact claim.

## 11. Key Modules

```
backend/app/services/
    risk_service.py              # scoring + RiskFactor creation (detection layer)
    evidence_service.py          # canonical evidence — authoritative findings
    llm_service.py               # prompt/grounding contract, provider, fallback
    narrative_contract.py        # alignment + completeness presentation layer
    explanation_store_service.py # CaseExplanation persistence + fingerprint
    citation_retrieval_service.py# claim-level citation validation
backend/app/api/routes/risk.py   # /explain, /explain/regenerate (HTTP only)
frontend/src/pages/Investigation.tsx  # rendering + regenerate button
```

Related documents:

- **Overall system architecture — this document.** It describes the complete
  Risk Platform architecture at system level and does not duplicate subsystem
  detail.
- **LLM Explanation subsystem** — for the detailed design of the explanation
  layer, including LLM/fallback behavior, prompt grounding, citation
  grounding, persisted explanation artifacts, explicit regeneration,
  timeout/reliability, and observability, see
  [architecture/llm-explanation-design.md](architecture/llm-explanation-design.md).
- `docs/data-contract.md` (§21 explanation artifacts) — field-level contract.
- `docs/cost-latency-strategy.md` — tier economics.
- `CLAUDE.md` — working conventions for this repository.
