# Project Context

Long-lived project facts (updated 2026-08-26). Current development state lives in `project-handoff.md`; full architecture in `docs/architecture.md`.

> Role: this file carries **stable context** (positioning, architecture,
> semantics, conventions). It changes only when the system's facts change.
> The former uppercase duplicates `PROJECT_CONTEXT.md` /
> `PROJECT_HANDOFF.md` were pre-canonical-evidence snapshots and are
> archived under `docs/archive/`.

## Positioning
Multi-Signal Risk Detection & Evidence-Grounded AI Investigation Platform. ML + deterministic rules + graph produce risk evidence; the LLM layer generates RAG-grounded investigation narratives. LLM is an explanation layer — never the scoring engine or decision maker.

## Architecture (current)
- **Detection**: ML / Rule / Graph (deterministic) → fused risk score + level.
- **Canonical Evidence** (`evidence_service.get_canonical_evidence()`): the authoritative findings layer — ml/rules/graph/contextual + unified findings. RiskFactor = feature-level evidence, NOT ML findings. Canonical evidence is rebuilt from `FeatureTable` under CURRENT semantic rules (historical RiskFactor labels never override it).
- **Narrative Contract** (`narrative_contract.py`): alignment + completeness layer — merges LLM wording to canonical finding names and APPENDS any canonical finding the narrative missed; authoritative findings can never be silently dropped. Backend-owned numbering; sections "What this means (Policy-backed)" / "Key Risk Findings" / "Next Actions (SOP-aligned)"; no contributions/raw thresholds/detected-by labels in narrative.
- **Citations**: claim-level validation; uncited findings allowed; "no citation is better than a wrong citation"; graph-zero & account-age never cited.
- **Persistence**: Tier 1 memory cache → Tier 2 `case_explanations` canonical artifact → Tier 3 generate+persist. `version_fingerprint = sha256(audience|risk_event_id|pipeline_run_id|model_version|policy_version)`. Ordinary reads never regenerate.
- **Regeneration**: `POST /api/risk/explain/regenerate` + UI "Regenerate with LLM" — explanation only; re-reads persisted source data, rebuilds canonical evidence with current semantics, regenerates, persists. ML/Rule/Graph/final scores and risk level unchanged.
- **LLM**: default generator when `ENABLE_LLM_EXPLANATION=true` + key; deterministic fallback otherwise/on failure runs the same pipeline. Timeout 30s. Thinking-tolerant response parsing (first `type=="text"` block). Every canonical finding is supplied to the LLM — no intentional prompt omissions.

## `opposite_trade_ratio` semantics (business rule)
```
0 < ratio <= 0.4  → "Opposite Trade Ratio"  — observed metric, rule NOT triggered
ratio > 0.4       → "Coordinated Trading Pattern" — rule triggered (+35)
```
Narrative wording is threshold-explicit on both sides (below: "…below the
40% threshold for the coordinated trading rule"; above: "…exceeded the 40%
threshold, triggering the coordinated trading rule"). Below-threshold values
must never be phrased as the rule firing. U00010 (0.3438) = "Opposite Trade Ratio".

## Conventions
- `RiskEvent` is immutable history; explanation layers never write scores.
- Presentation terminology must match business-rule semantics (see `docs/architecture.md` §6, §10).
- Scoring semantics changes require mirroring in `evidence_service._derive_rule_evidence` + `_THRESHOLD_FINDINGS` and the narrative wording; tests in `test_canonical_evidence.py`, `test_opposite_trade_semantics.py`, `test_regenerate_findings_regression.py` pin the contract.

## Test status
Backend 329 passed; 2 pre-existing failures (`test_citation_coverage_service` domain-mapping) + pre-existing `test_citation_mapper.py` collection error — leave as-is unless explicitly tasked. Frontend `npm run build` passes.

## Historical vs current
P1 evaluation results (`eval/llm_explain_eval_summary.md`, A5 90%) are a **historical baseline** predating the narrative contract/citation fixes — do not read as current behavior.
