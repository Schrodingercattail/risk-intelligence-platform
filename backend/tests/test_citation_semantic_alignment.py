"""
LLM Finding → Citation Domain semantic-alignment regression tests.

Covers the U00010/U00299 citation-grounding contract:
- ML finding → ML/scoring domain; Rule finding → rule domain;
  Graph finding → network domain (by FINDING semantics, not by which
  component score happens to be non-zero)
- score-based fallback classification is disabled (the U00010 root cause:
  "High-Risk Pattern Detection" got the AML network citation via graph_score>0)
- contextual account age → UNKNOWN (no KYC), but the TRIGGERED
  "New account with high activity" rule → RULE (and negated mentions stay
  contextual)
- retrieval: findings keep distinct citations; a genuinely-unsupported finding
  gets none (no reuse of an unrelated citation)
- U00010-shaped (rule triggered) vs U00299-shaped (contextual age) cases
- parser: numbered findings + numbered action steps preserved (no collapse)
"""
from app.services.citation_retrieval_service import (
    FindingClassifier,
    create_citation_retrieval_service,
)
from app.services.citation_policy_router import FindingType
from app.services.llm_service import LLMExplanationService


clf = FindingClassifier()


class TestFindingDomainSemantics:
    """Domain comes from finding semantics, not component scores."""

    def test_ml_pattern_detection_is_ml(self):
        # U00010 finding 1 header — previously fell to score fallback -> GRAPH
        assert clf.classify(text="1. ML Pattern Detection", ml_score=99.41,
                            rule_score=85.0, graph_score=59.08) == FindingType.ML_SIGNAL

    def test_rule_finding_is_rule(self):
        assert clf.classify(text="2. Rule-Based Signals", ml_score=99.41,
                            rule_score=85.0, graph_score=59.08) == FindingType.RULE_SIGNAL

    def test_graph_finding_is_graph(self):
        assert clf.classify(text="3. Account Network and Shared Infrastructure",
                            ml_score=99.41, rule_score=85.0,
                            graph_score=59.08) == FindingType.GRAPH_SIGNAL

    def test_score_fallback_disabled(self):
        # A finding that declares NO detection-method signal gets UNKNOWN even
        # when all component scores are high — this was the U00010 root cause
        # (generic findings previously became GRAPH via graph_score>0).
        for text in ("1. High-Risk Behavioral Assessment",
                     "Something generic happened",
                     "Elevated overall concern"):
            assert clf.classify(text=text, ml_score=99.41,
                                rule_score=85.0, graph_score=59.08) == FindingType.UNKNOWN, text
        # ... and "pattern detection" wording IS an ML-declared signal:
        assert clf.classify(text="1. High-Risk Pattern Detection", ml_score=0.0,
                            rule_score=0.0, graph_score=0.0) == FindingType.ML_SIGNAL

    def test_trading_velocity_is_transaction(self):
        assert clf.classify(text="2. Abnormal Trading Velocity: 54 trades in 24h",
                            ml_score=99.41) == FindingType.TRANSACTION_BEHAVIOR


class TestNewAccountRuleVsContextualAge:
    """Triggered rule = RULE evidence; un-triggered age stays contextual."""

    def test_triggered_rule_name_is_rule(self):
        assert clf.classify(
            text="4. New account with high activity rule triggered: "
                 "account is 6 days old with 54 trades in 24h"
        ) == FindingType.RULE_SIGNAL

    def test_negated_rule_mention_stays_contextual(self):
        # U00299-style contextual note quoting the (un-triggered) rule name
        for text in (
            "Account age is contextual. Unless paired with a specific "
            "'New account with high activity' rule trigger, this is background info.",
            "The 'New account with high activity' rule was not triggered.",
        ):
            assert clf.classify(text=text) == FindingType.UNKNOWN, text[:50]

    def test_contextual_age_no_kyc(self):
        for text in ("4. Account Age Context", "The account is 112 days old.",
                     "The account is 6 days old."):
            assert clf.classify(text=text) == FindingType.UNKNOWN, text[:40]


class TestRetrievalAlignment:
    """Retrieval keeps findings on distinct, domain-correct citations."""

    def setup_method(self):
        self.service = create_citation_retrieval_service()

    def test_ml_and_rule_and_graph_get_distinct_domains(self):
        findings = [
            "1. ML Pattern Detection",
            "2. Rule-Based Signals",
            "3. Account Network and Shared Infrastructure",
        ]
        result = self.service.retrieve_citations(
            key_findings=findings, ml_score=99.41, rule_score=85.0, graph_score=59.08,
            has_graph_evidence=True,
        )
        by_finding = {
            f: [c for c in result.citations if c.id in ids]
            for f, ids in result.finding_to_citations.items()
        }
        ml_cits = by_finding.get("1. ML Pattern Detection", [])
        assert ml_cits and all("Risk_Scoring_Explainability_Guide" in c.doc for c in ml_cits)

        rule_cits = by_finding.get("2. Rule-Based Signals", [])
        assert rule_cits and all("AML" in c.doc for c in rule_cits)
        for c in rule_cits:
            assert "network" not in c.section.lower(), "rule finding must not cite network section"

        graph_cits = by_finding.get("3. Account Network and Shared Infrastructure", [])
        assert graph_cits and all("AML" in c.doc for c in graph_cits)
        for c in graph_cits:
            assert "network" in c.section.lower() or "relationship" in c.section.lower()

        # unrelated findings do not silently share one citation
        ids = {tuple(sorted(c.id for c in cs)) for cs in by_finding.values() if cs}
        assert len(ids) >= 1  # each finding has its own citation id list
        ml_ids = {c.id for c in ml_cits}
        graph_ids = {c.id for c in graph_cits}
        assert not (ml_ids & graph_ids), "ML and Graph findings must not share a citation"

    def test_unsupported_finding_gets_no_citation_no_reuse(self):
        result = self.service.retrieve_citations(
            key_findings=["1. ML Pattern Detection", "1. High-Risk Behavioral Assessment"],
            ml_score=99.41,
        )
        assert result.finding_to_citations.get("1. ML Pattern Detection")
        # no textual signal -> UNKNOWN -> no citation (and NOT the ML citation)
        assert not result.finding_to_citations.get("1. High-Risk Behavioral Assessment")

    def test_u00010_shape_full_domain_matrix(self):
        findings = [
            "1. ML Pattern Detection",
            "2. Rule-Based Signals: triggered rules include High opposite trade ratio",
            "3. Account Network and Shared Infrastructure",
            "4. New account with high activity rule triggered (6 days old, 54 trades/24h)",
        ]
        result = self.service.retrieve_citations(
            key_findings=findings, ml_score=99.41, rule_score=85.0, graph_score=59.08,
            has_graph_evidence=True,
        )
        # opposite-trade claims are intentionally UNCITED (the corpus has no
        # policy supporting that semantics — velocity sections don't)
        assert not result.finding_to_citations.get(findings[1])
        # the new-account rule claim is also UNCITED: corpus 3.2 ("large
        # outbound activity soon after onboarding or after dormancy") supports
        # transfer-volume-after-onboarding, NOT the <7d AND >50-trades
        # conjunction — no citation is better than a wrong citation.
        assert not result.finding_to_citations.get(findings[3])
        # the other findings stay cited, domain-appropriate
        for f in (findings[0], findings[2]):
            assert result.finding_to_citations.get(f), f

    def test_u00299_shape_age_stays_uncited(self):
        result = self.service.retrieve_citations(
            key_findings=["3. Account Age Context",
                          "The 'New account with high activity' rule was not triggered."],
            ml_score=96.24,
        )
        for f, ids in result.finding_to_citations.items():
            assert not ids, f"contextual age must be uncited: {f[:40]}"


class TestParserPreservesStructure:
    """Numbered findings and action steps survive parsing (no collapsing)."""

    def setup_method(self):
        self.svc = LLMExplanationService.__new__(LLMExplanationService)
        self.svc.provider = None

    def test_numbered_findings_and_continuation_lines(self):
        text = (
            "## Summary\nUser flagged with HIGH risk score.\n\n"
            "## Key Findings\n"
            "1. ML Pattern Detection\nEvidence: ML Score is 99.41, a strong system signal.\n"
            "2. Rule-Based Signals\nEvidence: Rule Score 85.0 from triggered rules.\n\n"
            "## Recommended Action\n"
            "Initiate manual review:\n"
            "1. Review the trading activity\n"
            "2. Map the network of connected accounts\n"
            "3. Apply enhanced monitoring\n"
        )
        parsed = self.svc._parse_explanation(text, {"primary_reason": "x"})
        assert len(parsed["key_findings"]) == 2
        assert parsed["key_findings"][0].startswith("1. ML Pattern Detection")
        assert "Evidence: ML Score is 99.41" in parsed["key_findings"][0]
        assert "newlines" not in parsed  # schema keys unchanged
        action = parsed["recommended_action"]
        assert "1. Review the trading activity" in action
        assert "3. Apply enhanced monitoring" in action
        assert "\n" in action, "action steps must remain separate lines"

    def test_bulleted_findings_still_supported(self):
        text = (
            "## Summary\ns\n## Key Findings\n- Finding One\n- Finding Two\n"
            "## Recommended Action\nDo the review."
        )
        parsed = self.svc._parse_explanation(text, {"primary_reason": "x"})
        # parser keeps marker; the narrative contract strips+numbers downstream
        assert parsed["key_findings"] == ["- Finding One", "- Finding Two"]
        assert parsed["recommended_action"] == "Do the review."
        from app.services.narrative_contract import normalize_findings
        numbered, _ = normalize_findings(parsed["key_findings"])
        assert numbered == ["1. Finding One", "2. Finding Two"]

    def test_action_numbering_not_collapsed_inline(self):
        text = (
            "## Summary\ns\n## Key Findings\n- f\n"
            "## Recommended Action\nEscalate:\n1. A\n2. B\n"
        )
        parsed = self.svc._parse_explanation(text, {"primary_reason": "x"})
        lines = parsed["recommended_action"].split("\n")
        assert lines == ["Escalate:", "1. A", "2. B"]
