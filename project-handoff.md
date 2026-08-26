# Project Handoff

Current state: **opposite-trade semantics fix + regenerate findings pipeline fixed + threshold-explicit narrative + documentation checkpoint**. Date: 2026-08-26.

> Role: this file carries **current development state** (what is done, what is
> verified, what is next). Stable facts live in `project-context.md` and
> `docs/architecture.md`.

---

## Completed (this cycle)

### Opposite-trade semantic separation
- `0 < opposite_trade_ratio <= 0.4` → finding "Opposite Trade Ratio" (observed metric, no rule contribution); `> 0.4` → "Coordinated Trading Pattern" (+35). Strict inequality (0.40 does not trigger).
- Applies in `risk_service._create_risk_factors` + `_get_opposite_trade_description`, `evidence_service` (`_THRESHOLD_FINDINGS`, threshold-finding block, rule derivation name/description). Canonical evidence derives from `FeatureTable` under CURRENT semantics — historical cases (U00010) get correct names on regeneration without rescoring.
- Narrative wording is threshold-explicit on both sides; below-threshold phrasing must not imply the rule fired (forbidden phrases listed in the LLM prompt instruction; asserted in `test_regenerate_findings_regression.py` §7).

### Regenerate findings pipeline (root-cause fix)
- Root cause of the empty-findings UI: `apply_narrative_contract`'s canonical-name merge was a pure FILTER — findings not reproduced verbatim by the generator were dropped (fallback's score-summary lines never matched → `key_findings: []`). Fixed by adding `_append_uncovered_canonical()`: after merge, any uncovered canonical finding is appended (name + canonical evidence) — completeness guarantee; canonical evidence stays authoritative for finding existence.
- `_LIST_MARKER_RE` tightened (numbered marker requires trailing whitespace/end) so decimals like `34.4%` are never stripped.
- "Abnormal Withdrawal Behavior" audit: legitimate canonical finding (`FeatureTable.withdrawal_risk_score` = fraction of withdrawals to newly encountered addresses; official ML feature). The old prompt-level omission was REMOVED — all 9 canonical findings are now supplied to the LLM, rendered via a business-language template ("{pct}% of withdrawals were sent to newly encountered addresses"), never the raw sub-score.
- Live verified (U00010): regenerate → 9 findings, `explanation_source: LLM`, scores byte-identical (87.02 / CRITICAL / 99.41 / 85.00 / 59.08), findings survive persistence, browser refresh serves the persisted artifact, zero scoring invocations in the server log.

### Documentation checkpoint
- Created `docs/architecture.md` (layers, data flow, regenerate lifecycle, source-of-truth hierarchy, opposite-trade semantics, failure boundaries, design principles).
- Consolidated the case-variant duplicates: `PROJECT_CONTEXT.md` → `docs/archive/PROJECT_CONTEXT_pre-canonical-evidence.md`; `PROJECT_HANDOFF.md` → `docs/archive/PROJECT_HANDOFF_mvp-v0.5-stage.md` (both were stale pre-canonical-evidence snapshots; the lowercase files are canonical). NOTE: these were FOUR distinct git-tracked files on a case-sensitive volume — a latent hazard for case-insensitive clones, now resolved.
- `project-context.md` updated to stable-facts role; this file updated to current-state role.

### Regression protection
- New: `tests/test_regenerate_findings_regression.py` (no-rescore, scores unchanged, 9 canonical findings each exactly once via signature matching, U00010 = "Opposite Trade Ratio" ≠ "Coordinated Trading Pattern", findings survive persistence + ordinary read, no raw threshold leakage, threshold-wording + forbidden-phrase assertions). Uses a loop-local engine patched into `app.db.session` (avoids asyncpg cross-loop pool contamination between DB tests).
- Updated: `test_canonical_evidence.py`, `test_opposite_trade_semantics.py`, `test_coordinated_trading_citation.py`, `test_narrative_presentation.py` for the threshold-explicit wording contract.

---

## Completed (previous cycle, 2026-08-19)
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
- `docs/architecture/llm-optional-design.md` (now `llm-explanation-design.md`) rewritten as formal LLM Explanation subsystem design.
- `docs/cost-latency-strategy.md` rewritten for 3-tier persistence + 30s timeout.
- `docs/data-contract.md` §21 added (endpoints, ExplanationResponse, CaseExplanation, fingerprint, Canonical Evidence structure, backward compatibility).

---

## Validation (current, 2026-08-26)

- **Backend**: 329 passed, 2 failed — both **pre-existing** `test_citation_coverage_service.py::TestDomainConstraints` (domain-mapping), unrelated to explanation work.
- **Pre-existing**: `test_citation_mapper.py` collection error (imports old `CitationMapper`; module now `DomainAwareCitationMapper`).
- **Frontend**: `npm run build` passes (tsc + vite).
- **Live verification (this cycle)**: U00010 regenerate on the running server — 9 findings, "Opposite Trade Ratio" with below-40%-threshold wording, no forbidden phrasing, AWB LLM-narrated, `RiskEvent.detected_at` unchanged, zero scoring invocations in the server log; browser-refresh path serves the persisted artifact.
- **Docker** (previous cycle): compose config validated; runtime build blocked locally by Docker Hub TLS/network (environment); runtime smoke pending network availability.

---

## Next Direction

**Agent / Tool Calling / investigation orchestration** — NOT yet started; nothing implemented. Candidate ideas (not commitments):
- Tool-calling loop over existing read-only APIs (case evidence, network signals, citations) to draft investigation checklists.
- Explicit tool whitelist + read-only enforcement; every agent conclusion must trace to canonical evidence + citations.
- Keep the architecture boundary: agent/LLM proposes, deterministic layer decides; risk scoring stays untouched.

When starting, update this file with actual scope — do not treat the above as done.
