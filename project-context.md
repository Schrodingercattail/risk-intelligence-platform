# Project Context

Snapshot of current state (2026-08-19). Full details: README.md, docs/architecture/llm-optional-design.md, project-handoff.md.

## Positioning
Multi-Signal Risk Detection & Evidence-Grounded AI Investigation Platform. ML + deterministic rules + graph produce risk evidence; the LLM layer generates RAG-grounded investigation narratives. LLM is an explanation layer — never the scoring engine or decision maker.

## Architecture (current)
- **Detection**: ML / Rule / Graph (deterministic) → fused risk score + level.
- **Canonical Evidence** (`evidence_service.get_canonical_evidence()`): evidence source of truth — ml/rules/graph/contextual + unified findings. RiskFactor = feature-level evidence, NOT ML findings.
- **Citations**: claim-level validation; uncited findings allowed; "no citation is better than a wrong citation"; graph-zero & account-age never cited.
- **Narrative Contract** (`narrative_contract.py`): backend-owned numbering/normalization; sections "What this means (Policy-backed)" / "Key Risk Findings" / "Next Actions (SOP-aligned)"; no contributions/raw thresholds/detected-by labels in narrative.
- **Persistence**: Tier 1 memory cache → Tier 2 `case_explanations` canonical artifact → Tier 3 generate+persist. `version_fingerprint = sha256(audience|risk_event_id|pipeline_run_id|model_version|policy_version)`. Ordinary reads never regenerate.
- **Regeneration**: `POST /api/risk/explain/regenerate` + UI "Regenerate with LLM" — explanation only; ML/Rule/Graph/final scores and risk level unchanged.
- **LLM**: default generator when `ENABLE_LLM_EXPLANATION=true` + key; deterministic fallback otherwise/on failure. Timeout 30s. Thinking-tolerant response parsing (first `type=="text"` block).

## Test status
Backend 312 passed; 2 pre-existing failures (`test_citation_coverage_service` domain-mapping) + pre-existing `test_citation_mapper.py` collection error — leave as-is unless explicitly tasked. Frontend `npm run build` passes. Docker build blocked locally by Docker Hub TLS/network (environment, not config); runtime smoke pending.

## Historical vs current
P1 evaluation results (`eval/llm_explain_eval_summary.md`, A5 90%) are a **historical baseline** predating the narrative contract/citation fixes — do not read as current behavior.
