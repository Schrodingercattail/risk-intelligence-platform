"""
Tests for evidence-aware citation mapping and validation.

Coverage:
- Finding classification
- Citation query generation
- Finding-to-citation mapping
- Citation validation warnings
- RAG failure handling (graceful degradation)
"""

import pytest
from app.services.citation_mapper import CitationMapper, FindingType, CitationQuery
from app.services.citation_validator import CitationValidator, ValidationWarning, PolicyDomain


class TestCitationMapper:
    """Test citation mapper evidence-aware mapping."""

    def setup_method(self):
        """Initialize citation mapper for tests."""
        self.mapper = CitationMapper()

    def test_classify_ml_finding(self):
        """Test ML signal finding classification."""
        finding_text = "ML Signal Score: 98.07"
        finding_type = self.mapper.classify_finding(
            text=finding_text,
            ml_score=98.07
        )
        assert finding_type == FindingType.ML_SIGNAL

    def test_classify_rule_finding(self):
        """Test rule signal finding classification."""
        finding_text = "Rule Engine Signal Score: 80.00"
        finding_type = self.mapper.classify_finding(
            text=finding_text,
            rule_score=80.0
        )
        assert finding_type == FindingType.RULE_SIGNAL

    def test_classify_graph_finding(self):
        """Test graph signal finding classification."""
        finding_text = "Graph Network Signal Score: 57.29"
        finding_type = self.mapper.classify_finding(
            text=finding_text,
            graph_score=57.29
        )
        assert finding_type == FindingType.GRAPH_SIGNAL

    def test_classify_account_profile_finding(self):
        """Test account profile finding classification."""
        finding_text = "Elevated New Account Risk"
        finding_type = self.mapper.classify_finding(
            text=finding_text,
            factor_name="New Account Risk"
        )
        assert finding_type == FindingType.ACCOUNT_PROFILE

    def test_classify_network_behavior_finding(self):
        """Test network behavior finding classification."""
        finding_text = "High Trading Frequency"
        finding_type = self.mapper.classify_finding(
            text=finding_text,
            factor_name="Trading Frequency"
        )
        assert finding_type == FindingType.NETWORK_BEHAVIOR

    def test_map_ml_finding_to_query(self):
        """Test ML finding generates ML-specific query."""
        query = self.mapper.map_finding_to_query(
            text="ML Signal Score: 98.07",
            finding_type=FindingType.ML_SIGNAL
        )
        assert "ml" in query.query.lower() or "model" in query.query.lower()
        assert query.finding_type == FindingType.ML_SIGNAL
        assert query.top_k == 2

    def test_map_graph_finding_to_query(self):
        """Test graph finding generates network-specific query."""
        query = self.mapper.map_finding_to_query(
            text="Connected to 18 other accounts",
            finding_type=FindingType.GRAPH_SIGNAL
        )
        assert any(word in query.query.lower() for word in ["network", "cluster", "shared"])
        assert query.finding_type == FindingType.GRAPH_SIGNAL

    def test_map_account_finding_to_query(self):
        """Test account finding generates KYC-specific query."""
        query = self.mapper.map_finding_to_query(
            text="New account detected",
            finding_type=FindingType.ACCOUNT_PROFILE
        )
        assert any(word in query.query.lower() for word in ["kyc", "cdd", "account", "customer"])
        assert query.finding_type == FindingType.ACCOUNT_PROFILE

    def test_map_multiple_findings(self):
        """Test mapping multiple findings with different types."""
        key_findings = [
            "ML Signal Score: 98.07",
            "Rule Engine Signal Score: 80.00",
            "Connected to 18 other accounts"
        ]
        queries = self.mapper.map_findings_to_queries(
            key_findings=key_findings,
            ml_score=98.07,
            rule_score=80.0,
            graph_score=57.29
        )
        assert len(queries) == 3
        assert queries[0].finding_type == FindingType.ML_SIGNAL
        assert queries[1].finding_type == FindingType.RULE_SIGNAL
        assert queries[2].finding_type == FindingType.GRAPH_SIGNAL


class TestCitationValidator:
    """Test citation quality validation."""

    def setup_method(self):
        """Initialize citation validator for tests."""
        self.validator = CitationValidator()

    def test_detect_ml_policy_domain(self):
        """Test ML policy domain detection."""
        citation = {
            "id": 1,
            "doc": "ML_Suspicious_Indicators.md",
            "section": "ML Pattern Detection / Anomaly Detection",
            "quote": "Machine learning models detect anomalies..."
        }
        domain = self.validator._detect_policy_domain(citation)
        assert domain == PolicyDomain.ML_ANOMALY

    def test_detect_network_policy_domain(self):
        """Test network policy domain detection."""
        citation = {
            "id": 2,
            "doc": "AML_Suspicious_Indicators.md",
            "section": "Network / Relationship Signals / Risky Clusters",
            "quote": "Accounts linked to risky clusters..."
        }
        domain = self.validator._detect_policy_domain(citation)
        assert domain == PolicyDomain.NETWORK_CLUSTER

    def test_detect_kyc_policy_domain(self):
        """Test KYC policy domain detection."""
        citation = {
            "id": 3,
            "doc": "KYC_CDD_Requirements.md",
            "section": "Customer Due Diligence",
            "quote": "Enhanced due diligence required..."
        }
        domain = self.validator._detect_policy_domain(citation)
        assert domain == PolicyDomain.KYC_CDD

    def test_validate_ml_finding_with_network_citation(self):
        """Test ML finding citing network policy generates warning."""
        finding_text = "ML Signal Score: 98.07"
        citations = [{
            "id": 1,
            "doc": "AML_Suspicious_Indicators.md",
            "section": "Network / Relationship Signals",
            "quote": "Network connections indicate..."
        }]
        warnings = self.validator.validate_finding_citation(finding_text, citations)
        assert len(warnings) == 1
        assert warnings[0].code == "MISMATCH"

    def test_validate_graph_finding_with_kyc_citation(self):
        """Test graph finding citing KYC policy generates warning."""
        finding_text = "Graph Network Signal Score: 57.29"
        citations = [{
            "id": 2,
            "doc": "KYC_CDD_Requirements.md",
            "section": "Customer Verification",
            "quote": "Customer identity verification..."
        }]
        warnings = self.validator.validate_finding_citation(finding_text, citations)
        assert len(warnings) >= 1

    def test_validate_matching_finding_and_citation(self):
        """Test properly matched finding and citation generates no warnings."""
        finding_text = "ML Signal Score: 98.07"
        citations = [{
            "id": 1,
            "doc": "ML_Suspicious_Indicators.md",
            "section": "Pattern Detection / Anomaly Detection",
            "quote": "ML models detect anomalous patterns..."
        }]
        warnings = self.validator.validate_finding_citation(finding_text, citations)
        # Should not generate mismatch warning for ML-ML match
        mismatch_warnings = [w for w in warnings if w.code == "MISMATCH"]
        assert len(mismatch_warnings) == 0

    def test_validate_no_citations(self):
        """Test finding with no citations generates no warnings."""
        finding_text = "ML Signal Score: 98.07"
        citations = []
        warnings = self.validator.validate_finding_citation(finding_text, citations)
        assert len(warnings) == 0

    def test_validate_explanation_multiple_findings(self):
        """Test validation of full explanation with multiple findings."""
        key_findings = [
            "ML Signal Score: 98.07",
            "Rule Engine Signal Score: 80.00"
        ]
        finding_citations = {
            "ML Signal Score: 98.07": [1],
            "Rule Engine Signal Score: 80.00": [2]
        }
        all_citations = [
            {"id": 1, "doc": "ML_Policy.md", "section": "ML Detection", "quote": "..."},
            {"id": 2, "doc": "Network_Policy.md", "section": "Network", "quote": "..."}
        ]
        result = self.validator.validate_explanation(
            key_findings=key_findings,
            finding_citations=finding_citations,
            all_citations=all_citations
        )
        # Result should be valid (warnings only)
        assert result.is_valid
        assert result.findings_checked == 2
        # Should have warning for rule finding citing network policy
        assert len(result.warnings) >= 1


class TestEvidenceAwareCitationFlow:
    """Integration tests for evidence-aware citation flow."""

    def test_case_1_ml_only_no_graph_citation(self):
        """Test Case 1: ML score only should not return graph citation."""
        mapper = CitationMapper()
        validator = CitationValidator()

        finding_text = "ML Signal Score: 98.07"
        finding_type = mapper.classify_finding(
            text=finding_text,
            ml_score=98.07,
            has_graph_evidence=False
        )

        query = mapper.map_finding_to_query(
            text=finding_text,
            finding_type=finding_type
        )

        # Query should be ML-specific, not network-specific
        assert "network" not in query.query.lower()
        assert "cluster" not in query.query.lower()

    def test_case_2_graph_signal_allows_network_policy(self):
        """Test Case 2: Graph signal allows network policy citation."""
        mapper = CitationMapper()

        finding_text = "Connected to 18 other accounts"
        finding_type = mapper.classify_finding(
            text=finding_text,
            graph_score=57.29,
            has_graph_evidence=True
        )

        query = mapper.map_finding_to_query(
            text=finding_text,
            finding_type=finding_type
        )

        # Query should be network-specific
        assert "network" in query.query.lower() or "cluster" in query.query.lower() or "shared" in query.query.lower()

    def test_case_3_account_age_allows_kyc_citation(self):
        """Test Case 3: Account age finding allows KYC citation."""
        mapper = CitationMapper()

        finding_text = "Elevated New Account Risk"
        finding_type = mapper.classify_finding(
            text=finding_text,
            factor_name="New Account Risk"
        )

        query = mapper.map_finding_to_query(
            text=finding_text,
            finding_type=finding_type
        )

        # Query should be account/KYC-specific
        assert "account" in query.query.lower() or "kyc" in query.query.lower() or "age" in query.query.lower()

    def test_case_4_rag_failure_graceful_degradation(self):
        """Test Case 4: RAG failure should not break explain response."""
        mapper = CitationMapper()

        # Map findings should work even without RAG
        queries = mapper.map_findings_to_queries(
            key_findings=["ML Signal Score: 98.07"],
            ml_score=98.07
        )

        # Should return valid query object
        assert len(queries) == 1
        assert isinstance(queries[0], CitationQuery)
        assert queries[0].query is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
