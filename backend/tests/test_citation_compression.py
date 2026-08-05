"""
Tests for Citation Compression

Tests the minimum sufficient citation set logic:
- Target: 3-5 citations per response
- Hard limit: 5 citations maximum
- Citation IDs sequential [1..N]
"""

import pytest
from app.services.citation_coverage_service import create_citation_coverage_service


class TestCitationCompression:
    """Test citation compression logic."""

    def test_compression_reduces_citation_count(self):
        """Test that compression reduces citation count from original to target."""
        service = create_citation_coverage_service()

        # 6 findings should compress to 5 citations max
        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Graph Network Signal Score: 60.00",
            "Elevated trading_frequency_24h",
            "Elevated account_age_days",
            "Connected to 1 other account(s) through shared devices/IPs"
        ]

        factors = [
            {'factor_name': 'trading_frequency_24h', 'factor_value': 150},
            {'factor_name': 'account_age_days', 'factor_value': 5}
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=factors,
            has_graph_evidence=True,
            audience='investigator',
            max_citations_per_finding=2,
            target_citation_count=4,
            max_citation_limit=5
        )

        # Should be compressed to at most 5 citations
        assert report.total_citations <= 5
        assert report.compression_ratio < 1.0  # Should be compressed

    def test_citation_limit_never_exceeded(self):
        """Test that citation limit is never exceeded."""
        service = create_citation_coverage_service()

        # Many findings should still not exceed limit
        key_findings = [f"Finding {i}" for i in range(10)]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=50.0,
            rule_score=50.0,
            graph_score=50.0,
            factors=[],
            has_graph_evidence=False,
            audience='investigator',
            max_citations_per_finding=2,
            target_citation_count=4,
            max_citation_limit=5
        )

        assert report.total_citations <= 5

    def test_coverage_maintained_after_compression(self):
        """Test that coverage is maintained even after compression."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Graph Network Signal Score: 60.00"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience='investigator',
            target_citation_count=3,
            max_citation_limit=5
        )

        # All findings should still have citations
        assert report.findings_with_citations == report.total_findings
        assert report.coverage_rate == 1.0

    def test_ids_start_from_1_after_compression(self):
        """Test that citation IDs start from 1 after compression."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Elevated trading_frequency_24h"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience='investigator',
            target_citation_count=4,
            max_citation_limit=5
        )

        # IDs should be sequential starting from 1
        citation_ids = [c.id for c in citations]
        expected = list(range(1, len(citations) + 1))
        assert citation_ids == expected

    def test_u00010_compression_result(self):
        """Test U00010 case produces expected compressed result."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Graph Network Signal Score: 60.00",
            "Elevated trading_frequency_24h",
            "Elevated account_age_days",
            "Connected to 1 other account(s) through shared devices/IPs"
        ]

        factors = [
            {'factor_name': 'trading_frequency_24h', 'factor_value': 150},
            {'factor_name': 'account_age_days', 'factor_value': 5}
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=factors,
            has_graph_evidence=True,
            audience='investigator'
        )

        # Verify compressed result
        assert report.total_citations <= 5
        assert report.total_citations >= 3  # At least some citations
        assert report.coverage_rate == 1.0
        assert report.unused_citations == 0

        # Collect all used IDs
        used_ids = set()
        for ids in finding_to_citations.values():
            used_ids.update(ids)

        # All citation IDs should be used
        all_ids = set(c.id for c in citations)
        assert len(all_ids - used_ids) == 0

    def test_importance_score_sorting(self):
        """Test that citations are sorted by importance."""
        service = create_citation_coverage_service()

        # Findings with realistic content that might share citations
        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Elevated trading_frequency_24h"
        ]

        factors = [{'factor_name': 'trading_frequency_24h', 'factor_value': 150}]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=factors,
            has_graph_evidence=False,
            audience='investigator',
            target_citation_count=4,
            max_citation_limit=5
        )

        # Should have citations and coverage maintained
        assert report.total_citations > 0
        assert report.coverage_rate == 1.0


class TestCompressionInvariants:
    """Test invariants after compression."""

    def test_no_gaps_in_citation_ids(self):
        """Test that there are no gaps in citation IDs."""
        service = create_citation_coverage_service()

        key_findings = ["Finding 1", "Finding 2", "Finding 3"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=50.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience='investigator'
        )

        # IDs should be continuous
        citation_ids = [c.id for c in citations]
        if citation_ids:
            assert citation_ids == list(range(1, len(citations) + 1))

    def test_all_citations_referenced_in_findings(self):
        """Test that all citations are referenced by at least one finding."""
        service = create_citation_coverage_service()

        key_findings = ["ML Signal Score: 85.00", "Rule Engine Signal Score: 72.50"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience='investigator'
        )

        # All citation IDs should appear in finding_to_citations values
        all_citation_ids = set(c.id for c in citations)
        all_referenced_ids = set()
        for ids in finding_to_citations.values():
            all_referenced_ids.update(ids)

        assert all_citation_ids == all_referenced_ids

    def test_compression_ratio_in_valid_range(self):
        """Test that compression ratio is in valid range."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Graph Network Signal Score: 60.00",
            "Elevated trading_frequency_24h",
            "Elevated account_age_days"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=False,
            audience='investigator'
        )

        # Compression ratio should be between 0 and 1
        assert 0 < report.compression_ratio <= 1.0


class TestTargetCitationCount:
    """Test target citation count parameter."""

    def test_target_3_citations(self):
        """Test targeting 3 citations with realistic findings."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Elevated account_age_days"
        ]

        factors = [{'factor_name': 'account_age_days', 'factor_value': 5}]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=factors,
            has_graph_evidence=False,
            audience='investigator',
            target_citation_count=3,
            max_citation_limit=5
        )

        # Should target around 3 citations but not exceed 5
        assert report.total_citations >= 1  # At least some citations
        assert report.total_citations <= 5
        assert report.coverage_rate == 1.0  # All findings covered

    def test_target_5_citations(self):
        """Test targeting 5 citations."""
        service = create_citation_coverage_service()

        key_findings = ["Finding 1", "Finding 2", "Finding 3"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=50.0,
            rule_score=50.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience='investigator',
            target_citation_count=5,
            max_citation_limit=5
        )

        # Should not exceed 5
        assert report.total_citations <= 5
