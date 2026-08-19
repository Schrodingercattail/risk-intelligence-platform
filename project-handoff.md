# Project Handoff

Current state: **post P1→P4 explanation architecture completion + Docker deployment fixes + documentation synchronization**. Date: 2026-08-19.

---

## Completed

### Detection & Evidence (deterministic, LLM-independent)
- Multi-signal risk detection: ML (LightGBM) + deterministic Rule Engine + Graph detection; fusion 0.5/0.3/0.2; risk-level logic incl. CRITICAL override.
- **Canonical Evidence**: `EvidenceService.get_canonical_evidence()` is the evidence source of truth (`ml / rules / graph / contextual / findings`), with `_derive_rule_evidence()` mirroring the scorer.
- **Unified Findings**: finding and detection source are separate dimensions; RiskFactor rows are feature-level/contextual evidence (NOT ML findings); internal `detection_sources` never surface as "detected by …" labels.

### Explanation layer
- **Claim-level citations** (`ClaimRefiner`): a citation must support the finding's exact claim; uncited findings are valid (first-withdrawal, coordinated-trading, new-account rule currently uncited). "No citation is better than a wrong citation." Graph-zero and contextual account age are never cited.
- **Narrative Contract** (`narrative_contract.py`): backend-owned numbering (findings 1..N, actions restart 1..M, citation IDs independent), canonical-name finding merge, graph-zero extraction, contribution/provenance scrubbing, `validate_narrative_invariants()`. Sections: "What this means (Policy-backed)" / "Key Risk Findings" / "Next Actions (SOP-aligned)".
- **Persisted canonical explanations**: Tier 1 memory cache → Tier 2 `case_explanations` (unique per user+audience; canonical artifact, not a cache) → Tier 3 generate+persist. `version_fingerprint = sha256(audience|risk_event_id|pipeline_run_id|model_version|policy_version)`.
- **Ordinary read** never regenerates; **explicit regeneration** via `POST /api/risk/explain/regenerate` + Investigation UI "Regenerate with LLM" button ("Regenerates the explanation only; risk scores are not recalculated."). Regeneration does NOT touch ML/Rule/Graph/final scores or risk level (contract test `test_regenerate_no_rescore.py`).
- **LLM default/fallback**: LLM default generator when enabled+key; deterministic fallback on unavailable/timeout/error runs the same pipeline and becomes the canonical artifact. Timeout `EXPLAIN_LLM_TIMEOUT_SECONDS=30`. Provider extracts the first `type=="text"` block (thinking-tolerant).
- Replay tooling: `tools/replay_explanation.py` (install saved JSON as canonical artifact, no LLM); `tools/export_llm_explain_eval.py` now uses the regenerate endpoint.

### Docker / deployment
- `policies/` mounted `/policies:ro` (matches both policy-path resolution strategies).
- Frontend mapping 3000→80 (nginx); backend healthcheck via Python stdlib (no curl); LLM env injected via `${VAR:-}` interpolation from local untracked `.env`; `backend/.dockerignore` + `frontend/.dockerignore` added (`.env` excluded from build contexts — verified).
- `case_explanations` created by `create_all` on fresh DB (verified against real `Base.metadata`).

### Documentation synchronized
- README: opening/AI positioning, Canonical Evidence & Unified Findings, Narrative Contract, Explanation Persistence & Cache (3 tiers + fingerprint + regenerate), Risk Detection & Scoring Logic, Observability (`persisted_total`), Screenshots (7 entries, new narrative shots), Regenerate with LLM.
- `docs/architecture/llm-optional-design.md` rewritten as formal LLM Explanation Architecture.
- `docs/cost-latency-strategy.md` rewritten for 3-tier persistence + 30s timeout.
- `docs/data-contract.md` §21 added (endpoints, ExplanationResponse, CaseExplanation, fingerprint, Canonical Evidence structure, backward compatibility).

---

## Validation

- **Backend**: 312 passed, 2 failed — both **pre-existing** `test_citation_coverage_service.py::TestDomainConstraints` (domain-mapping), unrelated to explanation work.
- **Pre-existing**: `test_citation_mapper.py` collection error (imports old `CitationMapper`; module now `DomainAwareCitationMapper`).
- **Frontend**: `npm run build` passes (tsc + vite).
- **Docker**: compose config validated; build context exclusions/inclusions verified; **runtime build blocked locally by Docker Hub TLS/network failure** (base-image pull `python:3.12-slim` times out — environment issue, not Dockerfile). Runtime smoke test pending network availability.
- **Live verification done**: regenerate contract on real endpoints (scores byte-identical, artifact replaced, ordinary read = persisted artifact, metrics `persisted_total`/`llm_total` correct); narrative contract validator passes across ML-heavy / rule-only / graph-heavy / graph-zero case shapes.

---

## Next Direction

**Agent / Tool Calling / investigation orchestration** — NOT yet started; nothing implemented. Candidate ideas (not commitments):
- Tool-calling loop over existing read-only APIs (case evidence, network signals, citations) to draft investigation checklists.
- Explicit tool whitelist + read-only enforcement; every agent conclusion must trace to canonical evidence + citations.
- Keep the architecture boundary: agent/LLM proposes, deterministic layer decides; risk scoring stays untouched.

When starting, update this file with actual scope — do not treat the above as done.
