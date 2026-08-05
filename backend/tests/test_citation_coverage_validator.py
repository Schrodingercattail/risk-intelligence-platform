"""
Tests for Citation Coverage Validation Service.

Verifies:
1. Unused citation detection
2. Citation-less finding detection
3. Summary coverage validation
4. Domain-balanced summary citation selection
"""
import pytest
from app.services.citation_coverage_validator import (
    CitationCoverageValidator,
    create_citation_coverage_validator,
    CoverageResult,
    PolicyDomain
)


class TestCitationCoverageValidator:
    """Test suite for CitationCoverageValidator."""

    def test_unused_citation_detection(self):
        """Test detection of citations that never appear in text."""
        validator = create_citation_coverage_validator()

        result = validator.validate_coverage(
            summary="Summary text [1][2]",
            key_findings=["Finding 1 [1]", "Finding 2 [2]"],
            recommended_action="Action [1]",
            finding_to_citations={
                "Finding 1": [1],
                "Finding 2": [2]
            },
            all_citation_ids={1, 2, 3}  # Citation 3 never appears
        )

        assert 3 in result.unused_citations
        assert len(result.unused_citations) == 1

    def test_all_citations_used(self):
        """Test when all citations appear in text."""
        validator = create_citation_coverage_validator()

        result = validator.validate_coverage(
            summary="Summary [1][2]",
            key_findings=["Finding 1 [1]", "Finding 2 [2]"],
            recommended_action="Action",
            finding_to_citations={
                "Finding 1": [1],
                "Finding 2": [2]
            },
            all_citation_ids={1, 2}
        )

        assert len(result.unused_citations) == 0
        assert result.is_valid

    def test_citation_less_finding_detection(self):
        """Test detection of findings without citation marks."""
        validator = create_citation_coverage_validator()

        result = validator.validate_coverage(
            summary="Summary [1]",
            key_findings=["Finding 1 [1]", "Finding 2", "Finding 3 [1]"],
            recommended_action="Action",
            finding_to_citations={
                "Finding 1": [1],
                "Finding 2": [],  # No citations
                "Finding 3": [1]
            },
            all_citation_ids={1}
        )

        assert "Finding 2" in result.citation_less_findings
        assert len(result.citation_less_findings) == 1

    def test_coverage_rate_calculation(self):
        """Test coverage rate calculation."""
        validator = create_citation_coverage_validator()

        result = validator.validate_coverage(
            summary="Summary [1][2]",
            key_findings=["Finding 1 [1]"],
            recommended_action="Action",
            finding_to_citations={"Finding 1": [1]},
            all_citation_ids={1, 2, 3, 4}  # 2 used out of 4
        )

        assert result.stats["total_citations"] == 4
        # Unique marks: {1, 2} from summary + {1} from finding = {1, 2} = 2 unique marks
        assert result.stats["total_marks"] == 2
        assert result.stats["coverage_rate"] == 0.5  # 2/4 = 0.5

    def test_summary_citation_selection_domain_balanced(self):
        """Test that summary citations are domain-balanced."""
        validator = create_citation_coverage_validator()

        # Simulate findings with citations from different domains
        finding_to_citations = {
            "Finding 1": [1, 2],  # ML domain
            "Finding 2": [3],      # Network domain
            "Finding 3": [4],      # KYC domain
            "Finding 4": [5]       # SOP domain
        }

        # Mock citations with different domains
        all_citations = [
            {"id": 1, "doc": "ML_Policy.md", "section": "ML Detection", "quote": "ML pattern", "chunk_id": "c1"},
            {"id": 2, "doc": "ML_Policy.md", "section": "ML Scoring", "quote": "Score threshold", "chunk_id": "c2"},
            {"id": 3, "doc": "Network_Policy.md", "section": "Cluster Detection", "quote": "Shared device", "chunk_id": "c3"},
            {"id": 4, "doc": "KYC_Policy.md", "section": "Customer Verification", "quote": "Identity check", "chunk_id": "c4"},
            {"id": 5, "doc": "SOP.md", "section": "Investigation Flow", "quote": "Review process", "chunk_id": "c5"},
        ]

        selected = validator.select_summary_citations(
            finding_to_citations=finding_to_citations,
            all_citations=all_citations,
            top_k=2
        )

        # Should select from different domains
        assert len(selected) == 2
        assert selected[0] < selected[1]  # Sorted for display

    def test_summary_citation_selection_empty(self):
        """Test summary citation selection with no citations."""
        validator = create_citation_coverage_validator()

        selected = validator.select_summary_citations(
            finding_to_citations={},
            all_citations=[],
            top_k=2
        )

        assert selected == []

    def test_domain_detection(self):
        """Test policy domain detection from citations."""
        validator = create_citation_coverage_validator()

        # ML domain
        ml_citation = {"id": 1, "doc": "ML_Guide.md", "section": "ML Pattern Detection", "quote": "Machine learning", "chunk_id": "c1"}
        domain = validator._detect_domain(ml_citation)
        assert domain == PolicyDomain.ML_ANOMALY

        # Network domain
        net_citation = {"id": 2, "doc": "Network.md", "section": "Cluster Analysis", "quote": "Shared device connection", "chunk_id": "c2"}
        domain = validator._detect_domain(net_citation)
        assert domain == PolicyDomain.NETWORK_CLUSTER

        # KYC domain
        kyc_citation = {"id": 3, "doc": "KYC.md", "section": "Customer Verification", "quote": "KYC requirements", "chunk_id": "c3"}
        domain = validator._detect_domain(kyc_citation)
        assert domain == PolicyDomain.KYC_CDD

    def test_extract_marks_from_text(self):
        """Test citation mark extraction from text."""
        validator = create_citation_coverage_validator()

        text = "This is text with [1] and [2] and [1] again"
        marks = validator._extract_marks_from_text(text)

        assert marks == {1, 2}

    def test_extract_marks_empty(self):
        """Test mark extraction from empty text."""
        validator = create_citation_coverage_validator()

        marks = validator._extract_marks_from_text("")
        assert marks == set()

        marks = validator._extract_marks_from_text(None)
        assert marks == set()

    def test_coverage_result_structure(self):
        """Test that CoverageResult has required fields."""
        validator = create_citation_coverage_validator()

        result = validator.validate_coverage(
            summary="Summary [1]",
            key_findings=["Finding [1]"],
            recommended_action="Action",
            finding_to_citations={"Finding": [1]},
            all_citation_ids={1}
        )

        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'issues')
        assert hasattr(result, 'stats')
        assert hasattr(result, 'unused_citations')
        assert hasattr(result, 'citation_less_findings')

    def test_coverage_stats_accuracy(self):
        """Test that coverage stats are calculated correctly."""
        validator = create_citation_coverage_validator()

        result = validator.validate_coverage(
            summary="Summary [1][2]",
            key_findings=["Finding 1 [1]", "Finding 2 [2]", "Finding 3"],
            recommended_action="Action",
            finding_to_citations={
                "Finding 1": [1],
                "Finding 2": [2],
                "Finding 3": []
            },
            all_citation_ids={1, 2, 3}
        )

        assert result.stats["total_citations"] == 3
        assert result.stats["unused_count"] == 1
        assert result.stats["citation_less_count"] == 1

    def test_domain_round_robin_selection(self):
        """Test that domain-balanced selection uses round-robin across domains."""
        validator = create_citation_coverage_validator()

        # Create findings with citations from 3 domains
        finding_to_citations = {
            "ML Finding": [1],
            "Network Finding": [2],
            "KYC Finding": [3]
        }

        all_citations = [
            {"id": 1, "doc": "ML.md", "section": "ML", "quote": "ML text", "chunk_id": "c1"},
            {"id": 2, "doc": "Network.md", "section": "Network", "quote": "Network text", "chunk_id": "c2"},
            {"id": 3, "doc": "KYC.md", "section": "KYC", "quote": "KYC text", "chunk_id": "c3"},
        ]

        # Select 3 citations (should get one from each domain)
        selected = validator.select_summary_citations(
            finding_to_citations=finding_to_citations,
            all_citations=all_citations,
            top_k=3
        )

        assert len(selected) == 3
        assert set(selected) == {1, 2, 3}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
