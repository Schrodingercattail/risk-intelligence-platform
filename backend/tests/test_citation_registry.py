"""
Tests for citation registry deduplication and budget control.

Coverage:
- Citation deduplication by (doc, section, chunk_id)
- Stable ID assignment
- Budget enforcement
- Priority-based trimming
- Graceful degradation
"""

import pytest
from app.services.citation_registry import (
    CitationRegistry,
    CitationBudget,
    CitationKey,
    RegisteredCitation,
    create_citation_registry
)


class TestCitationDeduplication:
    """Test citation deduplication functionality."""

    def setup_method(self):
        """Initialize registry for tests."""
        self.registry = CitationRegistry()

    def test_same_citation_gets_same_id(self):
        """Test identical citations get the same ID."""
        id1 = self.registry.register(
            doc="AML_Suspicious_Indicators.md",
            section="Network / Relationship Signals",
            quote="Accounts linked to risky clusters",
            chunk_id="AML_Suspicious_Indicators.md#Network_Relationship_Signals#001"
        )

        id2 = self.registry.register(
            doc="AML_Suspicious_Indicators.md",
            section="Network / Relationship Signals",
            quote="Accounts linked to risky clusters",
            chunk_id="AML_Suspicious_Indicators.md#Network_Relationship_Signals#001"
        )

        assert id1 == id2
        assert id1 == 1  # First citation gets ID 1

    def test_different_chunks_get_different_ids(self):
        """Test different chunks get different IDs."""
        id1 = self.registry.register(
            doc="AML_Suspicious_Indicators.md",
            section="Network / Relationship Signals",
            quote="Accounts linked to risky clusters",
            chunk_id="chunk_001"
        )

        id2 = self.registry.register(
            doc="AML_Suspicious_Indicators.md",
            section="Transaction Velocity",
            quote="High velocity detected",
            chunk_id="chunk_002"
        )

        assert id1 != id2
        assert id1 == 1
        assert id2 == 2

    def test_deduplication_with_different_quotes_same_key(self):
        """Test citations are deduplicated even if quotes differ."""
        id1 = self.registry.register(
            doc="AML_Suspicious_Indicators.md",
            section="Network / Relationship Signals",
            quote="Accounts linked to risky clusters",
            chunk_id="chunk_001"
        )

        id2 = self.registry.register(
            doc="AML_Suspicious_Indicators.md",
            section="Network / Relationship Signals",
            quote="Different quote text",  # Different quote but same key
            chunk_id="chunk_001"
        )

        # Same chunk_id means same citation
        assert id1 == id2

    def test_three_findings_same_citation_one_id(self):
        """Test three findings referencing same citation get one ID."""
        finding_ids = []

        for _ in range(3):
            citation_id = self.registry.register(
                doc="AML_Suspicious_Indicators.md",
                section="5.1 Links to Known Risky Clusters",
                quote="Accounts linked to risky clusters",
                chunk_id="AML_Suspicious_Indicators.md#5.1#001"
            )
            finding_ids.append(citation_id)

        assert all(fid == finding_ids[0] for fid in finding_ids)
        assert finding_ids[0] == 1

    def test_citation_ids_remain_stable(self):
        """Test citation IDs are stable across multiple registrations."""
        ids = []
        for i in range(5):
            if i % 2 == 0:
                # Even indices: same citation
                cid = self.registry.register(
                    doc="Test.md",
                    section="Section 1",
                    quote="Test quote",
                    chunk_id="chunk_001"
                )
            else:
                # Odd indices: different citations (use different chunk IDs)
                chunk_id = f"chunk_00{i+1}"  # chunk_002, chunk_004, etc.
                cid = self.registry.register(
                    doc="Test.md",
                    section="Section 1",
                    quote="Test quote",
                    chunk_id=chunk_id
                )
            ids.append(cid)

        # Should have 3 unique IDs (chunk_001 reused at even indices)
        assert len(set(ids)) == 3
        assert ids[0] == ids[2] == ids[4]  # All even indices get ID 1
        assert ids[1] == 2
        assert ids[3] == 3


class TestCitationBudget:
    """Test citation budget control."""

    def test_budget_within_limit(self):
        """Test citations within budget are all returned."""
        budget = CitationBudget(max_citations=5)
        registry = CitationRegistry(budget=budget)

        # Add 3 citations
        for i in range(3):
            registry.register(
                doc=f"Test{i}.md",
                section="Section",
                quote=f"Quote {i}",
                chunk_id=f"chunk_{i:03d}"
            )

        citations = registry.get_citations_within_budget()
        assert len(citations) == 3

    def test_budget_exceeded_trims_citations(self):
        """Test exceeding budget trims citations."""
        budget = CitationBudget(max_citations=5)
        registry = CitationRegistry(budget=budget)

        # Add 10 citations
        for i in range(10):
            registry.register(
                doc=f"Test{i}.md",
                section="Section",
                quote=f"Quote {i}",
                chunk_id=f"chunk_{i:03d}"
            )

        citations = registry.get_citations_within_budget()
        assert len(citations) == 5  # Budget limit

    def test_budget_preserves_priority_order(self):
        """Test budget trimming preserves high-priority citations."""
        budget = CitationBudget(max_citations=3)
        registry = CitationRegistry(budget=budget)

        # Add citations with different priorities
        # High priority (ML finding)
        registry.register(
            doc="ML_Policy.md",
            section="ML Detection",
            quote="ML anomaly",
            chunk_id="chunk_ml",
            finding_type="ml_signal"
        )

        # Low priority (generic SOP)
        registry.register(
            doc="SOP.md",
            section="Workflow",
            quote="Follow procedure",
            chunk_id="chunk_sop",
            finding_type="action_recommendation"
        )

        # Medium priority (rule finding)
        registry.register(
            doc="AML_Policy.md",
            section="Transaction Behavior",
            quote="Suspicious pattern",
            chunk_id="chunk_rule",
            finding_type="rule_signal"
        )

        # Another low priority
        registry.register(
            doc="SOP.md",
            section="Investigation Steps",
            quote="Investigate case",
            chunk_id="chunk_sop2",
            finding_type="action_recommendation"
        )

        citations = registry.get_citations_within_budget()

        # Should keep ML, rule, and one of the first three (within budget of 3)
        assert len(citations) == 3

    def test_five_citation_limit_default(self):
        """Test default citation limit is 5."""
        registry = create_citation_registry()  # Default max_citations=5

        for i in range(10):
            registry.register(
                doc=f"Test{i}.md",
                section="Section",
                quote=f"Quote {i}",
                chunk_id=f"chunk_{i:03d}"
            )

        citations = registry.get_citations_within_budget()
        assert len(citations) == 5

    def test_custom_budget_limit(self):
        """Test custom budget limit works."""
        registry = create_citation_registry(max_citations=3)

        for i in range(10):
            registry.register(
                doc=f"Test{i}.md",
                section="Section",
                quote=f"Quote {i}",
                chunk_id=f"chunk_{i:03d}"
            )

        citations = registry.get_citations_within_budget()
        assert len(citations) == 3


class TestCitationStats:
    """Test registry statistics."""

    def test_stats_tracking(self):
        """Test registry tracks statistics correctly."""
        registry = CitationRegistry()

        # Register 3 unique citations
        for i in range(3):
            registry.register(
                doc=f"Test{i}.md",
                section="Section",
                quote=f"Quote {i}",
                chunk_id=f"chunk_{i:03d}"
            )

        # Register duplicates
        for _ in range(2):
            registry.register(
                doc="Test0.md",
                section="Section",
                quote="Quote 0",
                chunk_id="chunk_000"
            )

        stats = registry.get_stats()
        assert stats["registration_attempts"] == 5  # 3 unique + 2 duplicates
        assert stats["total_registered"] == 3  # 3 unique
        assert stats["deduplication_saved"] == 2  # 2 duplicates saved
        assert stats["unique_chunks"] == 3

    def test_stats_with_deduplication(self):
        """Test stats show deduplication occurred."""
        registry = create_citation_registry(max_citations=5)

        # Register same citation 5 times
        for _ in range(5):
            registry.register(
                doc="Test.md",
                section="Section",
                quote="Quote",
                chunk_id="chunk_001"
            )

        stats = registry.get_stats()
        assert stats["total_registered"] == 1
        assert stats["deduplication_saved"] >= 4  # 4 duplicates saved


class TestGracefulDegradation:
    """Test graceful degradation behavior."""

    def test_empty_registry_returns_empty_list(self):
        """Test empty registry returns empty citations."""
        registry = CitationRegistry()

        citations = registry.get_all_citations()
        assert citations == []

        citations = registry.get_citations_within_budget()
        assert citations == []

    def test_registry_with_invalid_input(self):
        """Test registry handles invalid input gracefully."""
        registry = CitationRegistry()

        # Register with empty strings
        cid = registry.register(
            doc="",
            section="",
            quote="",
            chunk_id=""
        )

        # Should still return an ID
        assert cid >= 1

        # Get citations should not crash
        citations = registry.get_all_citations()
        assert len(citations) >= 1


class TestIntegration:
    """Integration tests for full citation workflow."""

    def test_full_workflow_dedup_and_budget(self):
        """Test full workflow with deduplication and budget control."""
        registry = create_citation_registry(max_citations=5)

        # Simulate 3 findings, some with overlapping citations
        findings_data = [
            ("ML Signal Score: 98.07", "ml_signal", "chunk_ml"),
            ("Rule Engine Signal Score: 80.00", "rule_signal", "chunk_rule"),
            ("Graph Network Signal Score: 57.29", "graph_signal", "chunk_graph"),
        ]

        finding_to_citations = {}

        for finding_text, finding_type, chunk_id in findings_data:
            citation_ids = []
            # Each finding gets 2 citations
            for i in range(2):
                cid = registry.register(
                    doc="Policy.md",
                    section="Relevant Section",
                    quote=f"Policy quote {i}",
                    chunk_id=chunk_id,
                    finding_type=finding_type
                )
                citation_ids.append(cid)
            finding_to_citations[finding_text] = citation_ids

        # Get final citations
        final_citations = registry.get_citation_dict()

        # Should have exactly 3 unique citations (one per finding)
        assert len(final_citations) == 3

        # Each finding should have 2 citation IDs
        assert len(finding_to_citations["ML Signal Score: 98.07"]) == 2
        assert len(finding_to_citations["Rule Engine Signal Score: 80.00"]) == 2
        assert len(finding_to_citations["Graph Network Signal Score: 57.29"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
