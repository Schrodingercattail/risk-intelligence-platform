"""
Tests for Citation Retrieval Service (Redesigned)

Tests the strict domain enforcement architecture:
- CitationPolicyRouter enforces constraints BEFORE RAG retrieval
- Each finding type only retrieves from allowed domains
- Metadata chunks are rejected
- One primary citation per finding
"""

import pytest
from app.services.citation_retrieval_service import (
    CitationRetrievalService,
    create_citation_retrieval_service,
    FindingClassifier,
    FindingType
)
from app.services.citation_policy_router import (
    CitationPolicyRouter,
    FindingType as RouterFindingType,
    create_citation_policy_router
)


class TestFindingClassifier:
    """Test finding classification with strict priority rules."""

    def setup_method(self):
        """Initialize classifier for tests."""
        self.classifier = FindingClassifier()

    def test_ml_signal_classification(self):
        """Test ML signal is correctly classified."""
        finding_type = self.classifier.classify(
            text="ML Signal Score: 96.24",
            ml_score=96.24
        )
        assert finding_type == FindingType.ML_SIGNAL

    def test_linked_account_network_classified_as_graph(self):
        """Test 'Linked Account Network' is classified as GRAPH_SIGNAL, not ACCOUNT_PROFILE."""
        finding_type = self.classifier.classify(
            text="Elevated Linked Account Network",
            graph_score=60.0,
            has_graph_evidence=True
        )
        assert finding_type == FindingType.GRAPH_SIGNAL
        assert finding_type != FindingType.ACCOUNT_PROFILE

    def test_network_keywords_higher_priority_than_account(self):
        """Test network keywords have higher priority than generic 'account' keyword."""
        test_cases = [
            ("Connected to linked accounts", FindingType.GRAPH_SIGNAL),
            ("Shared device network account", FindingType.GRAPH_SIGNAL),
            ("Cluster account relationship", FindingType.GRAPH_SIGNAL),
        ]

        for text, expected_type in test_cases:
            finding_type = self.classifier.classify(text=text)
            assert finding_type == expected_type, \
                f"'{text}' should be {expected_type}, got {finding_type}"

    def test_account_age_evidence_is_not_citable(self):
        """Account-age evidence is contextual: UNKNOWN (no citation), not KYC.

        No policy document defines an account-age threshold (the only age logic
        is the code-side "New account with high activity" rule), so account-age
        findings must NOT be routed to KYC/CDD.
        """
        finding_type = self.classifier.classify(
            text="Elevated New Account Risk",
            factor_name="account_age_days"
        )
        assert finding_type == FindingType.UNKNOWN

        # Header form emitted by the grounded LLM output
        assert self.classifier.classify(text="3. Account Age Context") == FindingType.UNKNOWN
        # Supporting-line form
        assert self.classifier.classify(text="The account is 112 days old.") == FindingType.UNKNOWN

    def test_kyc_finding_still_classified_as_account_profile(self):
        """Genuinely KYC-related findings still route to ACCOUNT_PROFILE."""
        finding_type = self.classifier.classify(
            text="KYC verification level is NONE"
        )
        assert finding_type == FindingType.ACCOUNT_PROFILE

    def test_rule_and_graph_header_labels_classified(self):
        """Conceptual-finding header labels classify to their signal domain.

        Graph-ZERO statements ("The Graph Score is 0.0.", "No Graph Network
        Detected") are the ABSENCE of a finding: UNKNOWN (never cited).
        """
        assert self.classifier.classify(text="2. Rule-Based Alerts") == FindingType.RULE_SIGNAL
        assert self.classifier.classify(text="The Rule Score is 80.0") == FindingType.RULE_SIGNAL
        assert self.classifier.classify(text="1. ML Pattern Detection Signal") == FindingType.ML_SIGNAL
        assert self.classifier.classify(text="4. No Graph Network Detected") == FindingType.UNKNOWN
        assert self.classifier.classify(text="The Graph Score is 0.0.") == FindingType.UNKNOWN
        assert self.classifier.classify(text="Linked Account Network — 18 accounts") == FindingType.GRAPH_SIGNAL

    def test_rule_signal_classification(self):
        """Test rule signal is correctly classified."""
        finding_type = self.classifier.classify(
            text="Rule Engine Signal Score: 72.50",
            rule_score=72.50
        )
        assert finding_type == FindingType.RULE_SIGNAL

    def test_transaction_frequency_classification(self):
        """Test trading frequency is classified as TRANSACTION_BEHAVIOR."""
        finding_type = self.classifier.classify(
            text="High Trading Frequency",
            factor_name="trading_frequency_24h"
        )
        assert finding_type == FindingType.TRANSACTION_BEHAVIOR


class TestCitationPolicyRouter:
    """Test the CitationPolicyRouter enforces correct domain constraints."""

    def setup_method(self):
        """Initialize router for tests."""
        self.router = create_citation_policy_router()

    def test_ml_signal_allowed_docs(self):
        """Test ML_SIGNAL only allows explainability documents."""
        allowed_docs = self.router.get_allowed_docs_list(RouterFindingType.ML_SIGNAL)
        assert "Risk_Scoring_Explainability_Guide.md" in allowed_docs
        assert "AML_Suspicious_Indicators.md" not in allowed_docs
        assert "KYC_CDD_Requirements.md" not in allowed_docs

    def test_graph_signal_allowed_docs(self):
        """Test GRAPH_SIGNAL only allows AML document (network sections)."""
        allowed_docs = self.router.get_allowed_docs_list(RouterFindingType.GRAPH_SIGNAL)
        assert "AML_Suspicious_Indicators.md" in allowed_docs
        assert "KYC_CDD_Requirements.md" not in allowed_docs

    def test_account_profile_allowed_docs(self):
        """Test ACCOUNT_PROFILE only allows KYC documents."""
        allowed_docs = self.router.get_allowed_docs_list(RouterFindingType.ACCOUNT_PROFILE)
        assert "KYC_CDD_Requirements.md" in allowed_docs
        assert "AML_Suspicious_Indicators.md" not in allowed_docs

    def test_ml_signal_forbidden_sections(self):
        """Test ML_SIGNAL forbids transaction sections."""
        scope = self.router.get_allowed_scope(RouterFindingType.ML_SIGNAL)
        assert "transaction" in scope.forbidden_sections
        assert "velocity" in scope.forbidden_sections
        assert "kyc" in scope.forbidden_sections
        assert "network" in scope.forbidden_sections

    def test_graph_signal_forbidden_sections(self):
        """Test GRAPH_SIGNAL forbids KYC and transaction sections."""
        scope = self.router.get_allowed_scope(RouterFindingType.GRAPH_SIGNAL)
        assert "kyc" in scope.forbidden_sections
        assert "transaction" in scope.forbidden_sections

    def test_section_validation_for_graph_in_aml(self):
        """Test that network section in AML is allowed for GRAPH_SIGNAL."""
        # Network section should be allowed
        is_allowed = self.router.is_section_allowed(
            finding_type=RouterFindingType.GRAPH_SIGNAL,
            doc_name="AML_Suspicious_Indicators.md",
            section="Network / Relationship Signals"
        )
        assert is_allowed, "Network section should be allowed for GRAPH_SIGNAL"

        # Transaction section should be forbidden
        is_allowed = self.router.is_section_allowed(
            finding_type=RouterFindingType.GRAPH_SIGNAL,
            doc_name="AML_Suspicious_Indicators.md",
            section="Transaction Velocity & Burst Patterns"
        )
        assert not is_allowed, "Transaction section should be forbidden for GRAPH_SIGNAL"

    def test_section_validation_for_ml_signal(self):
        """Test that ML_SIGNAL cannot cite transaction sections."""
        # ML section should be allowed
        is_allowed = self.router.is_section_allowed(
            finding_type=RouterFindingType.ML_SIGNAL,
            doc_name="Risk_Scoring_Explainability_Guide.md",
            section="Evidence Types"
        )
        assert is_allowed, "ML evidence section should be allowed"

        # AML transaction section should not be allowed (wrong doc)
        is_allowed = self.router.is_section_allowed(
            finding_type=RouterFindingType.ML_SIGNAL,
            doc_name="AML_Suspicious_Indicators.md",
            section="Transaction Velocity"
        )
        assert not is_allowed, "AML transaction doc should not be allowed for ML_SIGNAL"

    def test_metadata_quote_detection(self):
        """Test that metadata quotes are detected."""
        metadata_quotes = [
            "Status: DEMO TEMPLATE (non-authoritative)",
            "Purpose: Provide citable text",
            "> Status: This is a demo",
            "Replace with your organization's policy",
        ]

        for quote in metadata_quotes:
            is_metadata = self.router._is_metadata_quote(quote)
            assert is_metadata, f"Should detect metadata: '{quote}'"

    def test_valid_content_quotes_accepted(self):
        """Test that actual policy content quotes are accepted."""
        valid_quotes = [
            "A sudden spike in the number of outgoing transfers may indicate:",
            "Enhanced due diligence required when risk scoring indicates high risk",
            "ML models detect anomalous patterns in transaction behavior",
        ]

        for quote in valid_quotes:
            is_metadata = self.router._is_metadata_quote(quote)
            assert not is_metadata, f"Should accept valid content: '{quote}'"

    def test_complete_citation_validation(self):
        """Test complete citation validation for relevance."""
        # Valid: ML signal citing explainability guide
        is_valid, reason = self.router.validate_citation_relevance(
            finding_type=RouterFindingType.ML_SIGNAL,
            doc_name="Risk_Scoring_Explainability_Guide.md",
            section="Evidence Types",
            quote="ML drivers should be described as evidence-backed signals"
        )
        assert is_valid, f"Should be valid: {reason}"

        # Invalid: ML signal citing AML transaction
        is_valid, reason = self.router.validate_citation_relevance(
            finding_type=RouterFindingType.ML_SIGNAL,
            doc_name="AML_Suspicious_Indicators.md",
            section="Transaction Velocity",
            quote="A sudden spike in transfers may indicate:"
        )
        assert not is_valid, "Should reject ML citing AML transaction"


class TestCitationRetrievalService:
    """Test the complete citation retrieval service."""

    def setup_method(self):
        """Initialize service for tests."""
        self.service = create_citation_retrieval_service()

    def test_ml_finding_cannot_retrieve_aml_transaction_citation(self):
        """Test that ML findings cannot retrieve AML transaction citations."""
        result = self.service.retrieve_citations(
            key_findings=["ML Signal Score: 96.24"],
            ml_score=96.24,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(result.citations) > 0, "Should have at least one citation"

        # Check NO citation is from AML transaction sections
        for cit in result.citations:
            # If it's from AML doc, it must NOT be transaction section
            if "AML" in cit.doc:
                section_lower = cit.section.lower() if cit.section else ""
                assert "transaction" not in section_lower, \
                    f"ML finding should NOT cite transaction section: {cit.section}"
                assert "velocity" not in section_lower, \
                    f"ML finding should NOT cite velocity section: {cit.section}"

    def test_graph_finding_cannot_retrieve_kyc_citation(self):
        """Test that GRAPH findings cannot retrieve KYC citations."""
        result = self.service.retrieve_citations(
            key_findings=["Elevated Linked Account Network"],
            ml_score=0.0,
            rule_score=0.0,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Should have citations
        assert len(result.citations) > 0, "Should have at least one citation"

        # Check NO citation is from KYC/CDD
        for cit in result.citations:
            doc_lower = cit.doc.lower()
            assert "kyc" not in doc_lower, \
                f"Graph finding should NOT cite KYC: {cit.doc}"
            assert "cdd" not in doc_lower, \
                f"Graph finding should NOT cite CDD: {cit.doc}"

    def test_account_finding_retrieves_kyc_citation(self):
        """Genuinely KYC-related findings retrieve KYC citations; account-age does not."""
        result = self.service.retrieve_citations(
            key_findings=["KYC verification level is NONE"],
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(result.citations) > 0, "Should have at least one citation"

        # Should have KYC citation
        found_kyc = False
        for cit in result.citations:
            doc_lower = cit.doc.lower()
            if "kyc" in doc_lower or "cdd" in doc_lower:
                found_kyc = True
                break

        assert found_kyc, "KYC finding should have KYC citation"

    def test_account_age_finding_gets_no_citation(self):
        """Account-age evidence must NOT receive a generic KYC citation."""
        result = self.service.retrieve_citations(
            key_findings=["3. Account Age Context"],
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[{"factor_name": "Account Age", "factor_value": 112}],
            has_graph_evidence=False,
            audience="investigator"
        )
        # No domain-relevant policy exists for account age -> no citation at all
        assert result.finding_to_citations.get("3. Account Age Context") in ([], None)
        assert not any(
            "kyc" in cit.doc.lower() or "cdd" in cit.doc.lower()
            for cit in result.citations
        ), "Account-age finding must not cite KYC"

    def test_rule_finding_retrieves_aml_transaction_policy(self):
        """Test that RULE_SIGNAL findings retrieve AML transaction policies."""
        result = self.service.retrieve_citations(
            key_findings=["Rule Engine Signal Score: 72.50"],
            ml_score=0.0,
            rule_score=72.50,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(result.citations) > 0, "Should have at least one citation"

        # Should have AML citation with transaction-related content
        found_aml = False
        for cit in result.citations:
            doc_lower = cit.doc.lower()
            if "aml" in doc_lower:
                section_lower = cit.section.lower() if cit.section else ""
                # Should be transaction-related section
                if any(keyword in section_lower for keyword in ["transaction", "velocity", "suspicious"]):
                    found_aml = True
                    break

        assert found_aml, "Rule finding should have AML transaction citation"

    def test_no_citation_contains_metadata_text(self):
        """Test that no citation quote contains metadata text."""
        result = self.service.retrieve_citations(
            key_findings=[
                "ML Signal Score: 85.00",
                "Elevated Linked Account Network",
                "Elevated New Account Risk"
            ],
            ml_score=85.0,
            rule_score=0.0,
            graph_score=60.0,
            factors=[{"factor_name": "account_age_days", "factor_value": 5}],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Check all citations for metadata
        for cit in result.citations:
            quote_lower = cit.quote.lower() if cit.quote else ""

            # Check for forbidden metadata patterns
            assert "status: demo template" not in quote_lower, \
                f"Citation should not contain 'Status: DEMO TEMPLATE': {cit.quote[:100]}"
            assert "purpose:" not in quote_lower or "explainable" in quote_lower, \
                f"Citation should not contain standalone 'Purpose:': {cit.quote[:100]}"
            assert "non-authoritative" not in quote_lower, \
                f"Citation should not contain 'non-authoritative': {cit.quote[:100]}"

    def test_all_citation_ids_are_sequential(self):
        """Test that citation IDs are always sequential starting from 1."""
        result = self.service.retrieve_citations(
            key_findings=["ML Signal Score: 85.00"],
            ml_score=85.0,
            audience="investigator"
        )

        citation_ids = [cit.id for cit in result.citations]
        expected_ids = list(range(1, len(citation_ids) + 1))

        assert citation_ids == expected_ids, \
            f"Citation IDs should be sequential [1..N], got {citation_ids}"

    def test_every_finding_has_at_least_one_citation(self):
        """Test that every finding has at least one citation."""
        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Elevated Linked Account Network"
        ]

        result = self.service.retrieve_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.50,
            graph_score=60.0,
            has_graph_evidence=True,
            audience="investigator"
        )

        # Every finding should have citations
        assert result.is_valid, "All findings should have citations"
        assert result.findings_with_citations == len(key_findings), \
            f"Expected {len(key_findings)} findings with citations, got {result.findings_with_citations}"

        for finding in key_findings:
            ids = result.finding_to_citations.get(finding, [])
            assert len(ids) > 0, \
                f"Finding '{finding}' should have at least one citation"

    def test_maximum_five_citations(self):
        """Test that maximum 5 citations are returned."""
        # Create 10 findings
        key_findings = [f"Finding {i}" for i in range(10)]

        result = self.service.retrieve_citations(
            key_findings=key_findings,
            ml_score=50.0,
            rule_score=50.0,
            graph_score=50.0,
            has_graph_evidence=True,
            audience="investigator",
            max_citations=5
        )

        assert len(result.citations) <= 5, \
            f"Should have at most 5 citations, got {len(result.citations)}"

    def test_u00299_case_linked_account_network(self):
        """Test U00299 case: Linked Account Network should get network citation, not KYC."""
        result = self.service.retrieve_citations(
            key_findings=["Elevated Linked Account Network"],
            graph_score=60.0,
            has_graph_evidence=True,
            audience="investigator"
        )

        # Check classification
        classifier = FindingClassifier()
        finding_type = classifier.classify(
            text="Elevated Linked Account Network",
            graph_score=60.0,
            has_graph_evidence=True
        )
        assert finding_type == FindingType.GRAPH_SIGNAL, \
            "Should be classified as GRAPH_SIGNAL"

        # Check no KYC citations
        for cit in result.citations:
            doc_lower = cit.doc.lower()
            assert "kyc" not in doc_lower, \
                f"Linked Account Network should NOT cite KYC: {cit.doc}"

    def test_u00010_case_mixed_signal_types(self):
        """Test mixed signal types: each domain gets its own citation; account-age gets none."""
        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "3. Account Age Context"
        ]

        factors = [{"factor_name": "Account Age", "factor_value": 5}]

        result = self.service.retrieve_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.50,
            graph_score=0.0,
            factors=factors,
            has_graph_evidence=False,
            audience="investigator"
        )

        # ML signal should not cite transaction
        ml_ids = result.finding_to_citations.get("ML Signal Score: 85.00", [])
        for cit in result.citations:
            if cit.id in ml_ids:
                section_lower = cit.section.lower() if cit.section else ""
                if "AML" in cit.doc:
                    assert "transaction" not in section_lower, \
                        "ML should not cite transaction section"

        # Account-age is contextual evidence -> NO citation (no KYC fallback)
        age_ids = result.finding_to_citations.get("3. Account Age Context", [])
        assert not age_ids, "Account-age finding must have no citation"
        assert not any(
            "kyc" in cit.doc.lower() for cit in result.citations
        ), "Account-age finding must not cause a KYC citation"


class TestGenericSectionFiltering:
    """Test that generic sections are filtered out during citation retrieval."""

    def setup_method(self):
        """Initialize service for tests."""
        self.service = create_citation_retrieval_service()
        self.router = create_citation_policy_router()

    def test_generic_section_scope_is_filtered(self):
        """Test that 'Scope' sections are filtered out as generic."""
        is_generic = self.router.is_generic_section("AML_Suspicious_Indicators.md / 1. Scope")
        assert is_generic, "Scope section should be identified as generic"

    def test_generic_section_explanation_objectives_is_filtered(self):
        """Test that 'Explanation Objectives' sections are filtered out as generic."""
        is_generic = self.router.is_generic_section(
            "Risk_Scoring_Explainability_Guide.md / 1. Explanation Objectives"
        )
        assert is_generic, "Explanation Objectives section should be identified as generic"

    def test_relevant_section_is_not_generic(self):
        """Test that relevant policy sections are NOT filtered as generic."""
        # Network section should NOT be generic
        is_generic = self.router.is_generic_section(
            "AML_Suspicious_Indicators.md / 5. Network / Relationship Signals"
        )
        assert not is_generic, "Network section should NOT be generic"

        # Transaction section should NOT be generic
        is_generic = self.router.is_generic_section(
            "AML_Suspicious_Indicators.md / 2. Transaction Velocity & Burst Patterns"
        )
        assert not is_generic, "Transaction section should NOT be generic"

    def test_validation_rejects_generic_sections(self):
        """Test that validate_citation_relevance rejects generic sections."""
        # Generic scope section should be rejected
        is_valid, reason = self.router.validate_citation_relevance(
            finding_type=RouterFindingType.ML_SIGNAL,
            doc_name="Risk_Scoring_Explainability_Guide.md",
            section="Risk Scoring Explainability Guide (Demo Template) / 1. Explanation Objectives",
            quote="An explanation should be accurate and readable."
        )
        assert not is_valid, "Generic Explanation Objectives should be rejected"
        assert "too generic" in reason.lower()

        # Generic scope section should be rejected
        is_valid, reason = self.router.validate_citation_relevance(
            finding_type=RouterFindingType.RULE_SIGNAL,
            doc_name="AML_Suspicious_Indicators.md",
            section="AML_Suspicious_Activity_Indicators_Demo_Template / 1. Scope",
            quote="This document lists common suspicious activity indicators."
        )
        assert not is_valid, "Generic Scope section should be rejected"
        assert "too generic" in reason.lower()

    def test_validation_accepts_relevant_sections(self):
        """Test that validate_citation_relevance accepts relevant policy sections."""
        # Network section should be accepted
        is_valid, reason = self.router.validate_citation_relevance(
            finding_type=RouterFindingType.GRAPH_SIGNAL,
            doc_name="AML_Suspicious_Indicators.md",
            section="AML_Suspicious_Activity_Indicators_Demo_Template / 5. Network / Relationship Signals",
            quote="Accounts linked to known risky clusters should be prioritized."
        )
        assert is_valid, f"Network section should be valid, got: {reason}"

        # Transaction section should be accepted
        is_valid, reason = self.router.validate_citation_relevance(
            finding_type=RouterFindingType.TRANSACTION_BEHAVIOR,
            doc_name="AML_Suspicious_Indicators.md",
            section="AML_Suspicious_Activity_Indicators_Demo_Template / 2. Transaction Velocity & Burst Patterns",
            quote="A sudden spike in transfers may indicate account takeover."
        )
        assert is_valid, f"Transaction section should be valid, got: {reason}"

    def test_retrieval_skips_generic_sections(self):
        """Test that retrieval skips generic sections and finds relevant ones."""
        result = self.service.retrieve_citations(
            key_findings=["ML Signal Score: 85.00"],
            ml_score=85.0,
            audience="investigator"
        )

        # Should have at least one citation
        assert len(result.citations) > 0, "Should have at least one citation"

        # Check that NO citation is from a generic section
        for cit in result.citations:
            is_generic = self.router.is_generic_section(cit.section)
            assert not is_generic, \
                f"Citation should not be from generic section: {cit.section}"

        # At least one citation should be from a relevant section
        found_relevant = False
        relevant_keywords = ["evidence", "types", "model", "scoring", "transaction", "network"]
        for cit in result.citations:
            section_lower = cit.section.lower() if cit.section else ""
            if any(keyword in section_lower for keyword in relevant_keywords):
                found_relevant = True
                break

        assert found_relevant, "Should find at least one relevant citation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
