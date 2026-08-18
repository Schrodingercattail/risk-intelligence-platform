"""
Global Narrative Contract — case-invariant tests.

These tests are GENERIC: they run the contract's deterministic assembly and
validator over synthetic payloads shaped like real case types (ML-heavy,
rule-only, graph-heavy, graph-zero, fallback) — no user-id special cases.
"""
from app.services.narrative_contract import (
    apply_narrative_contract,
    normalize_actions,
    normalize_findings,
    validate_narrative_invariants,
)
from app.services.citation_retrieval_service import FindingClassifier
from app.services.citation_policy_router import FindingType


# --------------------------------------------------------------------------- deterministic numbering

class TestFindingNumbering:
    def test_bullets_normalized_and_numbered_from_1(self):
        numbered, note = normalize_findings([
            "- High withdrawal frequency",
            "* First withdrawal to new address",
            "• Linked account network",
        ])
        assert numbered == [
            "1. High withdrawal frequency",
            "2. First withdrawal to new address",
            "3. Linked account network",
        ]
        assert note is None

    def test_model_numbering_stripped_and_renumbered(self):
        # model numbering that starts at 2 or continues a previous count
        numbered, _ = normalize_findings([
            "2. ML Pattern Detection",
            "3. High withdrawal frequency",
            "10. First withdrawal",
        ])
        assert numbered == ["1. ML Pattern Detection", "2. High withdrawal frequency",
                            "3. First withdrawal"]

    def test_bold_numbering_normalized(self):
        numbered, _ = normalize_findings(["**1.** High trading frequency",
                                          "**2.** Coordinated trading pattern"])
        assert numbered == ["1. High trading frequency",
                            "2. Coordinated trading pattern"]

    def test_unnumbered_finding_keeps_position_when_neighbor_cited(self):
        # citation presence must not affect finding numbering
        numbered, _ = normalize_findings([
            "High withdrawal frequency [1]",
            "First withdrawal to new address",
            "Linked account network [2]",
        ])
        assert numbered == [
            "1. High withdrawal frequency [1]",
            "2. First withdrawal to new address",
            "3. Linked account network [2]",
        ]

    def test_multiline_finding_supporting_lines_kept(self):
        numbered, _ = normalize_findings([
            "New account with high activity",
            "The account is 6 days old and recorded 54 trades in 24 hours.",
        ])
        # parser merges continuation lines upstream; contract keeps content
        assert len(numbered) >= 1
        assert all(f.split("\n")[0].startswith(f"{i}. ")
                   for i, f in enumerate(numbered, 1))


class TestActionNumbering:
    def test_independent_scope_restarts_at_1(self):
        out = normalize_actions(
            "Escalate for review:\n1. Escalate.\n2. Verify.\n3. Monitor.")
        assert out.split("\n") == [
            "Escalate for review:", "1. Escalate.", "2. Verify.", "3. Monitor."]

    def test_continued_count_renumbered(self):
        # model wrongly continued findings count into actions
        out = normalize_actions("Escalate:\n10. A\n11. B\n12. C")
        assert out.split("\n") == ["Escalate:", "1. A", "2. B", "3. C"]

    def test_bullet_actions_normalized(self):
        out = normalize_actions("- A\n- B\n- C")
        assert out.split("\n") == ["1. A", "2. B", "3. C"]

    def test_plain_fallback_action_unchanged(self):
        assert normalize_actions("Manual Review") == "Manual Review"


# --------------------------------------------------------------------------- graph zero

class TestGraphZero:
    def test_graph_zero_extracted_from_findings_not_numbered(self):
        numbered, note = normalize_findings([
            "ML Pattern Detection — 96.24/100",
            "Graph detection (score 0) — no signal was detected",
            "High withdrawal frequency",
        ])
        assert numbered == ["1. ML Pattern Detection — 96.24/100",
                            "2. High withdrawal frequency"]
        assert note is not None and "no signal" in note.lower()

    def test_graph_zero_never_gets_citation(self):
        clf = FindingClassifier()
        for text in (
            "3. Graph detection (score 0)",
            "No network relationship was detected",
            "No graph signal was detected",
        ):
            assert clf.classify(text=text, graph_score=0.0) == FindingType.UNKNOWN, text

    def test_graph_zero_folded_into_summary(self):
        payload = {
            "summary": "High risk account.",
            "key_findings": ["ML Pattern Detection — 96.24/100",
                             "No graph signal was detected"],
            "recommended_action": "1. Review.",
            "citations": [],
        }
        apply_narrative_contract(payload)
        assert payload["key_findings"] == ["1. ML Pattern Detection — 96.24/100"]
        assert "no graph signal" in payload["summary"].lower()
        assert "isolated" not in payload["summary"].lower()


# --------------------------------------------------------------------------- scrubbing

class TestScrubbing:
    def test_contribution_points_removed(self):
        p = {"summary": "s", "key_findings": [
            "High opposite trade ratio (+35)",
            "First withdrawal to new address (+20) — contributes +20 to the rule score",
        ], "recommended_action": "Manual Review", "citations": []}
        apply_narrative_contract(p)
        joined = " ".join(p["key_findings"])
        assert "+35" not in joined and "+20" not in joined
        assert "contributes" not in joined

    def test_provenance_removed(self):
        p = {"summary": "s", "key_findings": [
            "High trading frequency — detected by Feature",
            "Shared devices — detected by Graph and Feature",
        ], "recommended_action": "a", "citations": []}
        apply_narrative_contract(p)
        assert "detected by" not in " ".join(p["key_findings"]).lower()


# --------------------------------------------------------------------------- generic validator

def _cited_findings_case():
    return {
        "summary": "ML Pattern Detection — 99.41/100; a system signal, not a "
                   "calibrated probability. Risky account.",
        "key_findings": [
            "1. ML Pattern Detection — 99.41/100; a system signal, not a calibrated probability. [1]",
            "2. High withdrawal frequency — 7 withdrawals in 24 hours. [2]",
            "3. First withdrawal to new address — a first withdrawal was detected.",
            "4. Linked account network — 18 connected accounts. [3]",
        ],
        "recommended_action": "1. Escalate.\n2. Verify withdrawals.\n3. Map the network.",
        "citations": [
            {"id": 1, "doc": "Guide", "section": "2.1", "quote": "q", "chunk_id": "c1"},
            {"id": 2, "doc": "AML", "section": "2.1", "quote": "q", "chunk_id": "c2"},
            {"id": 3, "doc": "AML", "section": "5.1", "quote": "q", "chunk_id": "c3"},
        ],
    }


class TestValidateInvariants:
    def test_compliant_payload_passes(self):
        assert validate_narrative_invariants(_cited_findings_case()) == []

    def test_catches_bad_finding_numbering(self):
        p = _cited_findings_case()
        p["key_findings"][1] = "4. High withdrawal frequency [2]"
        vs = validate_narrative_invariants(p)
        assert any("bad numbering" in v for v in vs)

    def test_catches_action_scope_continuation(self):
        p = _cited_findings_case()
        p["recommended_action"] = "4. Escalate.\n5. Verify."
        vs = validate_narrative_invariants(p)
        assert any("action step" in v for v in vs)

    def test_catches_contribution_leak(self):
        p = _cited_findings_case()
        p["key_findings"][1] = "2. High withdrawal frequency (+25) [2]"
        assert any("contribution" in v for v in validate_narrative_invariants(p))

    def test_catches_provenance(self):
        p = _cited_findings_case()
        p["key_findings"][3] = "4. Linked account network — detected by Graph [3]"
        assert any("provenance" in v for v in validate_narrative_invariants(p))

    def test_catches_graph_zero_as_finding(self):
        p = _cited_findings_case()
        p["key_findings"].append("5. Graph detection (score 0) — no signal was detected")
        assert any("graph-zero" in v for v in validate_narrative_invariants(p))

    def test_catches_raw_threshold_and_fields(self):
        p = _cited_findings_case()
        p["key_findings"][1] = "2. Rule triggered: account_age_days < 7 AND trade_frequency_24h > 50 [2]"
        vs = validate_narrative_invariants(p)
        assert any("raw threshold" in v or "raw field" in v for v in vs)

    def test_catches_dangling_and_unused_citations(self):
        p = _cited_findings_case()
        p["citations"].append({"id": 9, "doc": "X", "section": "s", "quote": "q", "chunk_id": "c9"})
        assert any("marks" in v or "not contiguous" in v
                   for v in validate_narrative_invariants(p))

    def test_catches_ml_without_qualifier(self):
        p = _cited_findings_case()
        # remove the qualifier from BOTH summary and findings -> must be caught
        p["summary"] = "ML 99.41/100 risky."
        p["key_findings"][0] = "1. ML Pattern Detection — 99.41/100. [1]"
        assert any("calibrated-probability" in v or "calibrated probability" in v
                   for v in validate_narrative_invariants(p))

    def test_ml_with_qualifier_anywhere_passes(self):
        p = _cited_findings_case()
        assert not any("calibrated" in v
                       for v in validate_narrative_invariants(p))

    def test_uncited_finding_keeps_number(self):
        p = _cited_findings_case()
        # finding 3 uncited, neighbors cited -> numbering unaffected
        vs = validate_narrative_invariants(p)
        assert not any("finding 3" in v for v in vs)


# --------------------------------------------------------------------------- end-to-end shapes

class TestCaseShapes:
    """Contract applied to synthetic case-type shapes (generic)."""

    def _apply(self, summary, findings, action):
        p = {"summary": summary, "key_findings": findings,
             "recommended_action": action, "citations": []}
        return apply_narrative_contract(p)

    def test_rule_only_graph_zero_shape(self):
        p = self._apply(
            "HIGH risk (72.12/100).",
            ["1. ML Pattern Detection — 96.24/100 system signal",
             "2. High opposite trade ratio — an opposite-trade ratio of 45.24% was observed",
             "3. High withdrawal frequency — 14 withdrawals in 24 hours",
             "4. First withdrawal to new address",
             "5. Graph detection (score 0) — no signal was detected"],
            "1. Review trading.\n2. Verify withdrawals.")
        assert [f.split("\n")[0][:3] for f in p["key_findings"]] == ["1. ", "2. ", "3. ", "4. "]
        assert "no graph signal" in p["summary"].lower()
        assert p["recommended_action"].split("\n")[0].startswith("1.")

    def test_fallback_shape_stable(self):
        p = self._apply(
            "This account received a high risk score (72.12/100).",
            ["ML Signal Score: 96.24", "Rule Engine Signal Score: 80.00",
             "Elevated New Account Risk"],
            "Manual Review")
        assert p["key_findings"] == [
            "1. ML Signal Score: 96.24", "2. Rule Engine Signal Score: 80.00",
            "3. Elevated New Account Risk"]
        assert p["recommended_action"] == "Manual Review"
