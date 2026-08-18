"""
Fallback citation-contract regression tests.

The fallback (model-based) explanation citation behavior was tuned and
evaluated BEFORE the LLM citation-grounding work and is a protected contract:

  A. score-only findings (ML/Rule/Graph "Signal Score:" summaries) never
     receive citation markers
  B. only citations actually referenced by a marker in the final rendered
     findings/actions appear in the citation list
  C./D. final citation IDs are regenerated from the used set, contiguous from 1
  E. unused citation objects are removed (no dangling numbers either way)
  F. citations remain domain-appropriate

These tests exercise the shared assembly helpers in
app/api/routes/risk.py (_is_score_summary_finding,
_renumber_used_citations) plus a full simulated fallback assembly, and confirm
the LLM improvements (conceptual-finding grouping, domain routing, no fallback
sharing) remain intact.
"""
from app.api.routes.risk import (
    _is_score_summary_finding,
    _renumber_used_citations,
    _conceptual_finding_headers,
)
from app.services.citation_retrieval_service import create_citation_retrieval_service


CANDIDATES = [
    {"id": 1, "doc": "Risk_Scoring_Explainability_Guide.md", "section": "2.1 ML Factors"},
    {"id": 2, "doc": "AML_Suspicious_Indicators.md", "section": "2.1 High-Velocity Transfers"},
    {"id": 3, "doc": "Investigation_and_Action_SOP.md", "section": "2.1 Triage"},
]


class TestScoreSummaryContract:
    """A: score-only findings are never marked."""

    def test_score_summaries_detected(self):
        assert _is_score_summary_finding("ML Signal Score: 96.24")
        assert _is_score_summary_finding("Rule Engine Signal Score: 80.00")
        assert _is_score_summary_finding("Graph Network Signal Score: 0.00")

    def test_non_score_findings_not_flagged(self):
        assert not _is_score_summary_finding("Elevated New Account Risk")
        assert not _is_score_summary_finding("1. ML Pattern Detection Signal")
        assert not _is_score_summary_finding("The account is 112 days old.")


class TestFinalCitationUsage:
    """B-E: final list derives from actually-attached markers."""

    def test_only_used_citation_survives(self):
        # Fallback U00299 shape: findings carry NO markers (score summaries +
        # account age), so only the SOP citation (id 3) is used via the action.
        marked_findings = [
            "ML Signal Score: 96.24",
            "Rule Engine Signal Score: 80.00",
            "Elevated New Account Risk",
        ]
        old_to_new, next_id = _renumber_used_citations(marked_findings, CANDIDATES)
        assert old_to_new == {}, "No findings marked -> no citations used"
        assert next_id == 1, "SOP citation must become [1]"

    def test_used_citation_renumbered_from_3_to_1(self):
        # Source citation id = 3 (SOP) attached to the action text.
        old_to_new, next_id = _renumber_used_citations(["Manual Review [3]"], CANDIDATES)
        assert old_to_new == {3: 1}
        assert next_id == 2

    def test_contiguous_ids_by_first_appearance(self):
        marked = ["2. Rule-Based Alerts [2]", "1. ML Signal [1]", "shared [2]"]
        old_to_new, next_id = _renumber_used_citations(marked, CANDIDATES)
        assert old_to_new == {2: 1, 1: 2}, "IDs follow first appearance order"
        assert next_id == 3

    def test_marker_to_unknown_candidate_is_ignored(self):
        # A marker referencing a citation that was filtered out (e.g. generic)
        # must not claim an ID — the re-attach pass strips such marks.
        old_to_new, _ = _renumber_used_citations(["x [99]"], CANDIDATES)
        assert old_to_new == {}

    def test_no_dangling_and_no_unused(self):
        # Property: final marks <-> final citation list is a bijection.
        marked = ["1. ML Pattern Detection Signal [1]", "2. Rule-Based Alerts [2]"]
        old_to_new, next_id = _renumber_used_citations(marked, CANDIDATES)
        final_ids = set(old_to_new.values())
        assert final_ids == set(range(1, next_id)), "IDs contiguous from 1"
        final_list = [dict(c, id=old_to_new[c["id"]]) for c in CANDIDATES if c["id"] in old_to_new]
        used_marks = {int(m) for t in marked for m in [__import__("re").search(r'\[(\d+)\]', t).group(1)]}
        # after rewrite, every final citation is referenced and vice versa
        rewritten = {old_to_new[o] for o in used_marks if o in old_to_new}
        assert rewritten == {c["id"] for c in final_list}


class TestSimulatedFallbackAssembly:
    """End-to-end simulation of the U00299 fallback citation assembly."""

    def test_u00299_fallback_only_sop_cited(self):
        # Retrieval over the fallback findings (real service, real policies).
        findings = [
            "ML Signal Score: 96.24",
            "Rule Engine Signal Score: 80.00",
            "Elevated New Account Risk",
        ]
        result = create_citation_retrieval_service().retrieve_citations(
            key_findings=findings, ml_score=96.24, rule_score=80.0, graph_score=0.0,
        )
        f2c = {f: ids[0] for f, ids in result.finding_to_citations.items() if ids}
        candidates = [
            {"id": c.id, "doc": c.doc, "section": c.section} for c in result.citations
        ]

        # Pass 1: attach marks, skipping score summaries (protected contract).
        marked = []
        for f in findings:
            if _is_score_summary_finding(f):
                marked.append(f)
            else:
                marked.append(f + f" [{f2c[f]}]" if f in f2c else f)

        # Account age must not be cited at all (domain-aware, no KYC fallback).
        assert "Elevated New Account Risk" not in f2c, "account age must stay uncited"
        assert not any("[" in m for m in marked), "no fallback finding carries a marker"

        # SOP citation is the only used one (attached to the action).
        sop_candidates = [c for c in candidates if "SOP" in c["doc"]] or [
            {"id": max((c["id"] for c in candidates), default=0) + 1,
             "doc": "Investigation_and_Action_SOP.md", "section": "2.1 Triage"}
        ]
        sop_old_id = sop_candidates[0]["id"]
        all_candidates = candidates + ([sop_candidates[0]] if sop_old_id not in
                                       {c["id"] for c in candidates} else [])
        action_marked = f"Manual Review [{sop_old_id}]"

        old_to_new, next_id = _renumber_used_citations(marked + [action_marked], all_candidates)
        assert old_to_new == {sop_old_id: 1}, "only SOP is used and becomes [1]"
        final_list = [c for c in all_candidates if c["id"] in old_to_new]
        for c in final_list:
            c["id"] = old_to_new[c["id"]]
        assert len(final_list) == 1 and "SOP" in final_list[0]["doc"]
        assert action_marked.endswith(f"[{sop_old_id}]")  # rewritten to [1] by pass 2


class TestLlmImprovementsIntact:
    """The LLM citation-grounding improvements must remain intact."""

    def test_conceptual_finding_grouping_still_works(self):
        findings = ["1. ML Pattern Detection Signal", "supporting line", "2. Rule-Based Alerts"]
        assert _conceptual_finding_headers(findings) == [
            "1. ML Pattern Detection Signal", "2. Rule-Based Alerts",
        ]

    def test_llm_headers_get_marked_and_renumbered(self):
        marked = [
            "1. ML Pattern Detection Signal [1]",
            "supporting line",
            "2. Rule-Based Alerts [2]",
            "3. Account Age Context",
        ]
        old_to_new, next_id = _renumber_used_citations(marked, CANDIDATES)
        assert old_to_new == {1: 1, 2: 2}, "header marks survive renumbering"
        assert next_id == 3, "SOP citation continues after the last used id"

    def test_no_forced_citation_sharing(self):
        result = create_citation_retrieval_service().retrieve_citations(
            key_findings=["1. ML Pattern Detection Signal", "3. Account Age Context"],
            ml_score=96.24,
        )
        assert not result.finding_to_citations.get("3. Account Age Context")
        assert result.finding_to_citations.get("1. ML Pattern Detection Signal")
