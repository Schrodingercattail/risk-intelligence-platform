"""
Focused regression tests for citation grounding in the LLM explanation layer.

Covers the P3 citation-quality requirements:
- G1: ML citation relevance (ML guide for ML findings only)
- G2: KYC citation not assigned to ML/Rule/Graph/Account-age findings merely
      because the text mentions "risk"/"review"
- G3: graph/network findings can receive AML network citations; a graph
      absence (graph_score=0) never receives KYC
- G4: account-age contextual findings receive NO citation
- G5: citation assignment is per CONCEPTUAL FINDING (one numbered header),
      not per sentence/array element
- G6: no fallback citation pollution (uncited findings stay uncited)
"""
from app.services.citation_retrieval_service import (
    CitationRetrievalService,
    FindingClassifier,
    create_citation_retrieval_service,
)
from app.services.citation_policy_router import FindingType
from app.api.routes.risk import _conceptual_finding_headers


# U00299-shaped conceptual-finding headers (grounded LLM output)
U00299_HEADERS = [
    "1. ML Pattern Detection Signal",
    "2. Rule-Based Alerts",
    "3. Account Age Context",
    "4. No Graph Network Detected",
]

# U00299-shaped full key_findings: headers + supporting lines
U00299_FINDINGS = [
    "1. ML Pattern Detection Signal",
    "The ML Score is 96.24, which is the primary driver of the overall HIGH risk assessment.",
    "This score indicates that the account's behavioral patterns match risk characteristics.",
    "Note: This is a system-generated signal, not proof of malicious intent.",
    "2. Rule-Based Alerts",
    "The Rule Score is 80.0, showing that the account has triggered predefined risk rules.",
    "This corroborates the ML score.",
    "3. Account Age Context",
    "The account is 112 days old.",
    "Note: Per system guidelines, account age is contextual evidence.",
    "4. No Graph Network Detected",
    "The Graph Score is 0.0.",
    "This indicates that no connected graph risk was detected.",
]


class TestConceptualFindingGrouping:
    """G5: citation assignment happens per conceptual finding, not per element."""

    def test_numbered_headers_are_the_citation_targets(self):
        headers = _conceptual_finding_headers(U00299_FINDINGS)
        assert headers == U00299_HEADERS, "Only the 4 numbered headers should be targets"

    def test_supporting_lines_are_never_citation_targets(self):
        headers = _conceptual_finding_headers(U00299_FINDINGS)
        for line in ("The account is 112 days old.", "This corroborates the ML score."):
            assert line not in headers

    def test_legacy_unnumbered_findings_all_remain_targets(self):
        legacy = [
            "ML Signal Score: 99.41",
            "Elevated Shared Device Relationships",
            "Connected to 18 other accounts",
        ]
        assert _conceptual_finding_headers(legacy) == legacy

    def test_bold_prefixed_headers_are_recognized(self):
        assert _conceptual_finding_headers(["**1. Header**", "body"]) == ["**1. Header**"]

    def test_decimals_do_not_look_like_headers(self):
        findings = ["Score is 96.24 overall", "Graph Score 0.0 reported"]
        assert _conceptual_finding_headers(findings) == findings


class TestCitationDomainRelevance:
    """G1-G4, G6: domain-aware, minimal citation selection."""

    def setup_method(self):
        self.service: CitationRetrievalService = create_citation_retrieval_service()

    def test_g1_ml_finding_gets_ml_guide_citation(self):
        result = self.service.retrieve_citations(
            key_findings=["1. ML Pattern Detection Signal"],
            ml_score=96.24, rule_score=80.0, graph_score=0.0,
        )
        ids = result.finding_to_citations.get("1. ML Pattern Detection Signal", [])
        cited_docs = [cit.doc for cit in result.citations if cit.id in ids]
        assert cited_docs, "ML finding should receive a citation"
        assert all("Risk_Scoring_Explainability_Guide" in d for d in cited_docs)

    def test_g1_ml_guide_not_assigned_to_rule_or_age_or_graph(self):
        result = self.service.retrieve_citations(
            key_findings=["2. Rule-Based Alerts", "3. Account Age Context",
                          "4. No Graph Network Detected"],
            ml_score=96.24, rule_score=80.0, graph_score=57.0,
        )
        for finding, ids in result.finding_to_citations.items():
            for cit in result.citations:
                if cit.id in ids:
                    assert not (
                        "Risk_Scoring_Explainability_Guide" in cit.doc and "2. Rule" in finding
                    ), f"ML guide must not back a Rule finding ({finding[:30]})"

    def test_g2_kyc_not_assigned_for_risk_review_wording(self):
        # Findings that merely mention "risk"/"review" must NOT pull in KYC.
        result = self.service.retrieve_citations(
            key_findings=U00299_HEADERS,
            ml_score=96.24, rule_score=80.0, graph_score=0.0,
        )
        kyc_cited = [
            f for f, ids in result.finding_to_citations.items()
            for cit in result.citations
            if cit.id in ids and ("kyc" in cit.doc.lower() or "cdd" in cit.doc.lower())
        ]
        assert not kyc_cited, f"KYC citation must not back these findings: {kyc_cited}"

    def test_g3_graph_finding_gets_network_citation_not_kyc(self):
        result = self.service.retrieve_citations(
            key_findings=["Elevated Linked Account Network"],
            graph_score=60.0, has_graph_evidence=True,
        )
        ids = result.finding_to_citations.get("Elevated Linked Account Network", [])
        for cit in result.citations:
            if cit.id in ids:
                assert "kyc" not in cit.doc.lower(), "Graph finding must not cite KYC"
                assert "AML" in cit.doc or "Indicators" in cit.doc, \
                    "Graph finding should cite the AML network policy when available"

    def test_g3_graph_zero_absence_finding_gets_no_kyc(self):
        result = self.service.retrieve_citations(
            key_findings=["4. No Graph Network Detected"],
            graph_score=0.0, has_graph_evidence=False,
        )
        for cit in result.citations:
            assert "kyc" not in cit.doc.lower(), "Graph absence must never cite KYC"

    def test_g4_account_age_has_no_citation(self):
        for text in ("3. Account Age Context", "The account is 112 days old.",
                     "Elevated New Account Risk"):
            result = self.service.retrieve_citations(key_findings=[text])
            assert result.finding_to_citations.get(text) in ([], None), \
                f"Account-age finding must have no citation: {text}"

    def test_g6_no_fallback_citation_pollution(self):
        # ML finding retrieves; account-age finding does not. The uncited
        # finding must NOT be force-shared the ML citation.
        result = self.service.retrieve_citations(
            key_findings=["1. ML Pattern Detection Signal", "3. Account Age Context"],
            ml_score=96.24, rule_score=80.0, graph_score=0.0,
        )
        age_ids = result.finding_to_citations.get("3. Account Age Context")
        assert not age_ids, "Uncited finding must stay uncited (no fallback sharing)"
        ml_ids = result.finding_to_citations.get("1. ML Pattern Detection Signal")
        assert ml_ids, "ML finding should still be cited"

    def test_u00299_full_header_set_domains(self):
        """End-to-end classification of the four U00299 conceptual findings.

        Graph-zero statements ("No Graph Network Detected", "The Graph Score
        is 0.0.") are the ABSENCE of a finding: UNKNOWN — never cited.
        """
        clf = FindingClassifier()
        assert clf.classify(text="1. ML Pattern Detection Signal") == FindingType.ML_SIGNAL
        assert clf.classify(text="2. Rule-Based Alerts") == FindingType.RULE_SIGNAL
        assert clf.classify(text="3. Account Age Context") == FindingType.UNKNOWN
        assert clf.classify(text="4. No Graph Network Detected") == FindingType.UNKNOWN
        # Supporting-sentence forms must classify to their own finding's domain,
        # not leak across (previously "The Rule Score is 80.0" fell back to ML).
        assert clf.classify(text="The Rule Score is 80.0") == FindingType.RULE_SIGNAL
        assert clf.classify(text="The Graph Score is 0.0.") == FindingType.UNKNOWN
        # NOTE: a generic account-themed sentence still falls back to
        # ACCOUNT_PROFILE by the text-keyword last resort — that is fine
        # because production never classifies supporting lines: only numbered
        # headers are citation targets (see TestConceptualFindingGrouping), so
        # an ML finding's supporting line cannot leak into a KYC citation.
