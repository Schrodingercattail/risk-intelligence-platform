# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Risk Intelligence Platform** — Multi-Signal Risk Detection & Evidence-Grounded AI Investigation Platform.

**Architecture boundary (most important rule for any change):**
ML, Rule, and Graph components produce structured risk evidence (deterministic, LLM-independent). The **LLM is an explanation/narrative layer only** — never the risk scoring engine, ML decision maker, rule engine, graph detector, evidence source of truth, or citation authority. Regeneration is explanation-level and never recalculates risk scores.

Core chain: Raw Data → Feature Engineering → ML/Rule/Graph scoring → **Canonical Evidence** → Unified Findings → LLM Narrative / Deterministic Fallback → Claim-level Citation → Narrative Contract → Persisted Canonical Explanation.

### Project Context

Inspired by risk management scenarios from consumer finance and digital asset platforms; designed industry-agnostic and transferable across fintech, fraud prevention, e-commerce, and marketplace integrity domains.

**Business Goals:**
- Identify abnormal user behavior patterns across risk-sensitive domains
- Combine multiple risk signals (ML + Rules + Graph) into coherent decisions
- Support investigation workflows with policy-backed explanations, evidence attribution, and RAG-grounded LLM narratives
- Monitor model performance and detect data drift
- Provide explainable risk decisions grounded in evidence and policy

## Technology Stack

- **Backend:** Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy (no Alembic migrations — schema via `Base.metadata.create_all` on startup)
- **ML:** scikit-learn, LightGBM, pandas/numpy, joblib
- **Frontend:** React + TypeScript (Vite; reads `VITE_API_URL`, NOT `REACT_APP_*`), nginx serves build + proxies `/api`

## Core Modules

```
backend/app/services/
    risk_service.py             # ML/Rule/Graph scoring + fusion (0.5/0.3/0.2) — DO NOT change semantics casually
    evidence_service.py         # get_canonical_evidence(): evidence source of truth (ml/rules/graph/contextual/findings)
                                #   + _derive_rule_evidence() (mirrors _calculate_rule_score)
    explanation_store_service.py# Persisted canonical artifacts + version fingerprint (sha256(audience|risk_event_id|pipeline_run_id|model_version|policy_version))
    narrative_contract.py       # Backend-owned presentation: findings 1..N, actions 1..M, merge by canonical names,
                                #   graph-zero extraction, contribution/provenance scrubbing, validate_narrative_invariants()
    llm_service.py              # ClaudeProvider (first type=="text" block — thinking-tolerant), prompt + grounding contract,
                                #   _parse_explanation, deterministic fallback
    citation_retrieval_service.py # ClaimRefiner (claim-level validation) + FindingClassifier (graph-zero & account-age → UNKNOWN)
    citation_policy_router.py / citation_mapper.py / citation_registry.py / citation_coverage_service.py / citation_validator.py
    explain_metrics.py          # Counters incl. persisted_total (persisted reads ≠ generations)
    psi_service.py / model_monitoring_service.py / data_quality_service.py / pipeline_service.py
frontend/src/
    pages/Investigation.tsx     # "Key Risk Findings" (not Top Risk Hypotheses), Regenerate with LLM button, source badge
    utils/explanationFormat.ts  # groupKeyFindings (splits element on \n), splitNumberedSteps (any start number)
    services/api.ts             # generateExplanation + regenerateExplanation
```

## Critical Semantics (must preserve)

1. **RiskFactor ≠ ML finding.** RiskFactor rows are feature-level/contextual descriptive evidence. "Feature used by ML" ≠ "ML detected the finding". Finding→source attribution lives only in canonical evidence `findings[].detection_sources` (internal provenance, never user-facing "detected by" labels).
2. **Unified Findings**: one conceptual finding appears once (detection sources merge on it). Never bucket into ML/Rule/Graph finding lists.
3. **Claim-level citations**: a citation must support the finding's exact claim. Uncited findings are valid (current corpus: first-withdrawal, coordinated-trading, new-account rule). **No citation is better than a wrong citation.** Contextual account age never auto-gets KYC; graph-zero never gets cited and is never a numbered finding.
4. **Narrative Contract** (`narrative_contract.py`): backend owns all numbering (findings 1..N; actions restart at 1..M; citation IDs independent). No contributions (`+N`), no raw thresholds/field names, no detection-source labels in user-facing narrative. Sections: "What this means (Policy-backed)" / "Key Risk Findings" / "Next Actions (SOP-aligned)".
5. **Persistence tiers**: Tier 1 in-memory TTL cache (perf only; expiry never generates) → Tier 2 persisted canonical explanation (`case_explanations` table, unique per user+audience — it is the canonical artifact, not a cache) → Tier 3 generate+persist (only absent/stale/explicit regenerate).
6. **Ordinary read** (`POST /api/risk/explain`) never regenerates while a valid artifact exists. **Explicit regeneration** (`POST /api/risk/explain/regenerate`, UI button "Regenerate with LLM") bypasses read tiers, regenerates the explanation only — risk scores/level untouched.
7. **LLM default/fallback**: with `ENABLE_LLM_EXPLANATION=true` + key set, LLM is the default generator; on unavailable/timeout/provider error the deterministic model-based fallback runs the same citation/narrative/persistence pipeline and becomes the canonical artifact.
8. **Timeout**: `EXPLAIN_LLM_TIMEOUT_SECONDS=30` (thinking-capable gateways need the window; application-level provider timeout, not HTTP SLA).
9. **Gateway responses**: Anthropic-compatible replies may contain thinking+text blocks; provider extracts the first `type=="text"` block (never assume `content[0]`).
10. **Score-based classifier fallback is disabled** (was the U00010 cross-domain citation root cause). Classification comes from finding semantics.

## Development Commands

```bash
# Backend
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
pytest backend/tests/                      # 312 pass; 2 pre-existing failures in
                                          # test_citation_coverage_service (domain-mapping) and
                                          # test_citation_mapper.py collection error (API drift) — pre-existing, leave as-is
python -m pytest tests/test_regenerate_no_rescore.py -v   # regenerate contract (scores unchanged)

# Frontend
cd frontend && npm install && npm run build

# Eval tooling
python tools/export_llm_explain_eval.py --out-dir eval/llm_raw_explanations_v2   # now uses /explain/regenerate
python tools/replay_explanation.py --artifact eval/llm_raw_explanations_v2/U00299.json  # install artifact as canonical (no LLM)
```

## Explanation LLM Configuration

```bash
ENABLE_LLM_EXPLANATION=false          # default; true + key → LLM is default generator
ANTHROPIC_API_KEY=                    # required only when enabling LLM
ANTHROPIC_BASE_URL=                   # optional gateway (e.g. Anthropic-compatible)
ANTHROPIC_MODEL=                      # model id matching gateway naming
EXPLAIN_LLM_TIMEOUT_SECONDS=30        # provider-call timeout
SHOW_USER_ID_IN_LLM_PROMPT=false      # user-id redaction in prompts
LOG_REDACT_USER_ID=true               # user-id redaction in logs
```

Privacy: IPs/emails/phones/long-IDs masked before LLM calls; policy thresholds/percentages redacted from citations. **Never commit `.env`; never bake keys into images** (Docker injects at runtime via `${ANTHROPIC_API_KEY:-}`).

## Docker Deployment Notes

- `policies/` is mounted at **`/policies:ro`** (both `explanation_store_service` `parents[3]` and `policy_rag_service` walk-up resolve there). Missing mount = empty policy RAG = all findings uncited.
- Frontend: host **3000 → container 80** (nginx). Backend healthcheck uses **Python stdlib urllib** (slim image has no curl).
- LLM env injected via Compose interpolation from local untracked `.env`; `backend/.dockerignore` + `frontend/.dockerignore` exclude `.env` from build contexts.
- Schema on fresh DB: `create_all` in `main.py` lifespan (creates `case_explanations` with unique `(user_id, audience)`).

## Architecture Principles

1. **Separation of concerns** — API layer = HTTP only; services = business logic; ML isolated and versioned.
2. **Model evaluation standards** — AUC / KS / PSI; feature importance for explainability.
3. **Rule engine** — configurable strategies; hit logging; risk level hierarchy (incl. CRITICAL override: graph≥50 AND ml≥80 AND rule≥40; CRITICAL ≥90, HIGH ≥70, MEDIUM ≥50, LOW <50).
4. **API design** — RESTful; Pydantic validation; OpenAPI auto-generated. `ExplanationResponse` shape unchanged by the persistence architecture.

**When updating this file:** Add new patterns, commands, and architectural decisions as they emerge.

## Key References

- `README.md` — Canonical Evidence & Unified Findings; Narrative Contract; Explanation Persistence & Cache; Risk Detection & Scoring Logic
- `docs/architecture/llm-explanation-design.md` — LLM Explanation subsystem design (detailed)
- `docs/cost-latency-strategy.md` — latency/cost model, tier semantics
- `docs/data-contract.md` §21 — explanation endpoints/artifact data contract
- `eval/llm_explain_eval_summary.md` — P1 historical baseline (A5 90%; predates narrative contract — historical, not current state)
