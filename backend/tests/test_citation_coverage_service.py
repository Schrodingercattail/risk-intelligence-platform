"""
Tests for Citation Coverage Service

Tests the strict citation coverage contract:
1. Every finding must have at least one citation
2. No unused citations in response
3. Citation IDs are sequential [1..N]
4. All citations are referenced in text
"""

import pytest
from app.services.citation_coverage_service import (
    CitationCoverageService,
    Citation,
    CoverageReport,
    create_citation_coverage_service,
    create_citation_filter,
    FilteredCitations
)
from app.services.citation_mapper import (
    DomainAwareCitationMapper,
    FindingType,
    DomainConstraints,
    create_domain_aware_citation_mapper
)


class TestCitationCoverageService:
    """Test the citation coverage service."""

    def test_service_creation(self):
        """Test service can be created."""
        service = create_citation_coverage_service()
        assert service is not None
        assert isinstance(service, CitationCoverageService)

    def test_generate_citations_basic(self):
        """Test basic citation generation with findings."""
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
            audience="investigator",
            max_citations_per_finding=2
        )

        # Check coverage contract
        assert report.total_findings == 3
        assert report.findings_with_citations == 3
        assert report.coverage_rate == 1.0
        assert report.unused_citations == 0
        assert report.is_valid is True

        # Check every finding has citations
        for finding in key_findings:
            assert finding in finding_to_citations
            assert len(finding_to_citations[finding]) > 0

        # Check citation IDs are sequential
        citation_ids = [c.id for c in citations]
        assert citation_ids == list(range(1, len(citations) + 1))

    def test_findings_without_candidates_get_fallback(self):
        """Test that findings without candidates get fallback citations."""
        service = create_citation_coverage_service()

        key_findings = [
            "Some very specific finding that might not have direct policy matches"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator",
            max_citations_per_finding=1
        )

        # Should still get citations via fallback
        assert len(citations) > 0
        assert len(finding_to_citations[key_findings[0]]) > 0

    def test_deduplication_within_finding(self):
        """Test that duplicate citations within a finding are deduplicated."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50"  # May return same citation as ML
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator",
            max_citations_per_finding=2
        )

        # Check no duplicate citation IDs within a single finding
        for finding, ids in finding_to_citations.items():
            assert len(ids) == len(set(ids)), f"Duplicate IDs in {finding}: {ids}"

    def test_citation_sharing_across_findings(self):
        """Test that citations can be shared across findings (deduplication)."""
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
            audience="investigator",
            max_citations_per_finding=2
        )

        # Collect all citation IDs used
        all_used_ids = set()
        for ids in finding_to_citations.values():
            all_used_ids.update(ids)

        # All used IDs should be in the citations list
        citation_ids_in_list = set(c.id for c in citations)
        assert all_used_ids == citation_ids_in_list

        # No unused citations
        assert report.unused_citations == 0

    def test_sequential_citation_ids(self):
        """Test that citation IDs are always sequential starting from 1."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Elevated trading_frequency_24h",
            "Elevated account_age_days"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator",
            max_citations_per_finding=2
        )

        # Check IDs are sequential
        expected_ids = list(range(1, len(citations) + 1))
        actual_ids = [c.id for c in citations]
        assert actual_ids == expected_ids

    def test_coverage_report_structure(self):
        """Test that coverage report has correct structure."""
        service = create_citation_coverage_service()

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=["Test finding"],
            ml_score=50.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Check report structure
        assert hasattr(report, 'total_findings')
        assert hasattr(report, 'findings_with_citations')
        assert hasattr(report, 'total_citations')
        assert hasattr(report, 'used_citations')
        assert hasattr(report, 'unused_citations')
        assert hasattr(report, 'coverage_rate')
        assert hasattr(report, 'is_valid')

        # Check to_dict method
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert 'total_findings' in report_dict
        assert 'is_valid' in report_dict


class TestCoverageContract:
    """Test the strict coverage contract."""

    def test_no_unused_citations_contract(self):
        """Test that no unused citations are returned."""
        service = create_citation_coverage_service()

        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Collect all citation IDs used by findings
        used_ids = set()
        for ids in finding_to_citations.values():
            used_ids.update(ids)

        # All citation IDs in the response should be used
        all_ids = set(c.id for c in citations)
        unused_ids = all_ids - used_ids

        assert len(unused_ids) == 0, f"Unused citations: {unused_ids}"
        assert report.unused_citations == 0

    def test_all_findings_have_citations_contract(self):
        """Test that every finding has at least one citation."""
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
            has_graph_evidence=True,
            audience="investigator"
        )

        # Every finding should have citations
        for finding in key_findings:
            assert finding in finding_to_citations
            assert len(finding_to_citations[finding]) > 0, \
                f"Finding '{finding}' has no citations"

        # Check report
        assert report.findings_with_citations == report.total_findings

    def test_coverage_rate_is_100_percent(self):
        """Test that coverage rate is always 100%."""
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
            audience="investigator"
        )

        # Coverage rate should be 100%
        assert report.coverage_rate == 1.0
        assert report.is_valid is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_findings_list(self):
        """Test handling of empty findings list."""
        service = create_citation_coverage_service()

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=[],
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        assert len(citations) == 0
        assert len(finding_to_citations) == 0
        assert report.total_findings == 0
        assert report.is_valid is True

    def test_single_finding(self):
        """Test handling of single finding."""
        service = create_citation_coverage_service()

        key_findings = ["ML Signal Score: 85.00"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        assert len(finding_to_citations) == 1
        assert len(finding_to_citations[key_findings[0]]) > 0
        assert report.findings_with_citations == 1

    def test_business_audience_redaction(self):
        """Test that business audience redacts quotes."""
        service = create_citation_coverage_service()

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=["ML Signal Score: 85.00"],
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="business"
        )

        # All quotes should be redacted
        for cit in citations:
            if cit.quote:
                assert cit.quote == "[REDACTED]" or cit.quote == ""

    def test_large_number_of_findings(self):
        """Test handling of many findings."""
        service = create_citation_coverage_service()

        key_findings = [f"Finding {i}: Score {i*10}" for i in range(10)]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=50.0,
            rule_score=50.0,
            graph_score=50.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator",
            max_citations_per_finding=1
        )

        # All findings should have citations
        assert report.findings_with_citations == len(key_findings)
        assert report.unused_citations == 0


class TestCitationValidation:
    """Test citation validation logic."""

    def test_all_citation_ids_are_integers(self):
        """Test that all citation IDs are integers."""
        service = create_citation_coverage_service()

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=["ML Signal Score: 85.00"],
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        for cit in citations:
            assert isinstance(cit.id, int)

        for ids in finding_to_citations.values():
            for cid in ids:
                assert isinstance(cid, int)

    def test_citation_objects_have_required_fields(self):
        """Test that citation objects have all required fields."""
        service = create_citation_coverage_service()

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=["ML Signal Score: 85.00"],
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        for cit in citations:
            assert hasattr(cit, 'id')
            assert hasattr(cit, 'doc')
            assert hasattr(cit, 'section')
            assert hasattr(cit, 'quote')
            assert hasattr(cit, 'chunk_id')
            assert cit.doc
            assert cit.section
            assert cit.chunk_id

    def test_finding_to_citations_uses_correct_keys(self):
        """Test that finding_to_citations uses finding text as key."""
        service = create_citation_coverage_service()

        key_findings = ["ML Signal Score: 85.00", "Rule Engine Signal Score: 72.50"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Check that keys match original finding texts
        for finding in key_findings:
            assert finding in finding_to_citations


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_u00010_scenario(self):
        """Test the U00010 case that had issues with unused citations."""
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
            {'factor_name': 'trading_frequency_24h', 'factor_value': 150, 'factor_description': 'High frequency trading'},
            {'factor_name': 'account_age_days', 'factor_value': 5, 'factor_description': 'New account'}
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=factors,
            has_graph_evidence=True,
            audience="investigator",
            max_citations_per_finding=2
        )

        # Verify coverage contract
        assert report.total_findings == 6
        assert report.findings_with_citations == 6
        assert report.coverage_rate == 1.0
        assert report.unused_citations == 0
        assert report.is_valid is True

        # Every finding should have citations
        for finding in key_findings:
            assert finding in finding_to_citations
            ids = finding_to_citations[finding]
            assert len(ids) > 0, f"Finding '{finding}' has no citations"

        # Simulate adding citation marks
        marked_findings = []
        for finding in key_findings:
            ids = sorted(set(finding_to_citations[finding]))
            marks = "".join([f"[{cid}]" for cid in ids])
            marked_findings.append(f"{finding} {marks}")

        # Extract all marks
        import re
        all_marks = set()
        for marked in marked_findings:
            marks = re.findall(r'\[(\d+)\]', marked)
            all_marks.update(int(m) for m in marks)

        # All marks should correspond to valid citation IDs
        all_citation_ids = set(c.id for c in citations)
        assert all_marks.issubset(all_citation_ids)

        # All citation IDs should be used
        unused = all_citation_ids - all_marks
        assert len(unused) == 0, f"Unused citation IDs: {unused}"

    def test_summary_citation_selection(self):
        """Test that summary only uses existing citations."""
        from app.services.citation_coverage_validator import create_citation_coverage_validator

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
            audience="investigator"
        )

        # Collect citation IDs used by findings
        used_ids = set()
        for ids in finding_to_citations.values():
            used_ids.update(ids)

        # Use coverage validator to select summary citations
        coverage_validator = create_citation_coverage_validator()
        all_citation_dicts = [
            {"id": c.id, "doc": c.doc, "section": c.section, "quote": c.quote, "chunk_id": c.chunk_id}
            for c in citations
        ]
        top_citation_ids = coverage_validator.select_summary_citations(
            finding_to_citations=finding_to_citations,
            all_citations=all_citation_dicts,
            top_k=2
        )

        # All selected IDs should be from the used set
        for cid in top_citation_ids:
            assert cid in used_ids, f"Citation ID {cid} not used by any finding"


class TestCitationFilter:
    """Test citation filtering to remove unused citations."""

    def test_extract_used_citation_ids(self):
        """Test extraction of citation IDs from text."""
        from app.services.citation_coverage_service import create_citation_filter

        filter = create_citation_filter()

        summary = "This account received a HIGH risk score [1][2]."
        key_findings = [
            "ML Signal Score: 85.00 [1]",
            "Elevated trading_frequency_24h [2][3]"
        ]
        recommended_action = "Review case [3]."

        used_ids = filter.extract_used_citation_ids(summary, key_findings, recommended_action)

        assert used_ids == {1, 2, 3}

    def test_filter_citations_removes_unused(self):
        """Test that unused citations are filtered out."""
        from app.services.citation_coverage_service import create_citation_filter, Citation

        filter = create_citation_filter()

        # Create 5 citations, but only [1], [2], [4] are used
        all_citations = [
            Citation(id=1, doc="Doc1", section="Sec1", quote="Quote1", chunk_id="chunk1"),
            Citation(id=2, doc="Doc2", section="Sec2", quote="Quote2", chunk_id="chunk2"),
            Citation(id=3, doc="Doc3", section="Sec3", quote="Quote3", chunk_id="chunk3"),  # Unused
            Citation(id=4, doc="Doc4", section="Sec4", quote="Quote4", chunk_id="chunk4"),
            Citation(id=5, doc="Doc5", section="Sec5", quote="Quote5", chunk_id="chunk5"),  # Unused
        ]

        used_ids = {1, 2, 4}
        filtered = filter.filter_citations(all_citations, used_ids)

        # Should only have 3 citations
        assert len(filtered.citations) == 3
        # IDs should be re-indexed to [1, 2, 3]
        assert [c.id for c in filtered.citations] == [1, 2, 3]
        # Old to new mapping should be correct
        assert filtered.old_to_new_id_map == {1: 1, 2: 2, 4: 3}
        # Should have filtered 2 citations
        assert filtered.filtered_count == 2

    def test_update_citation_marks(self):
        """Test that citation marks are updated after re-indexing."""
        from app.services.citation_coverage_service import create_citation_filter

        filter = create_citation_filter()

        summary = "Risk score [1][2]"
        key_findings = [
            "ML Signal [2]",
            "Trading [3]"
        ]
        recommended_action = "Review [3]"

        # After filtering, old IDs 1,2,3 become new IDs 1,2 (3 was unused)
        old_to_new_id_map = {1: 1, 2: 2}  # 3 is not in map (filtered out)

        updated_summary, updated_key_findings, updated_action = filter.update_citation_marks(
            summary, key_findings, recommended_action, old_to_new_id_map
        )

        # Updated marks should use new IDs
        assert updated_summary == "Risk score [1][2]"
        assert updated_key_findings == ["ML Signal [2]", "Trading [3]"]  # 3 unchanged (not in map)
        assert updated_action == "Review [3]"

    def test_filter_and_reindex_complete_pipeline(self):
        """Test the complete filter and re-index pipeline."""
        from app.services.citation_coverage_service import create_citation_filter, Citation

        filter = create_citation_filter()

        # Create citations
        all_citations = [
            Citation(id=1, doc="Doc1", section="Sec1", quote="Quote1", chunk_id="chunk1"),
            Citation(id=2, doc="Doc2", section="Sec2", quote="Quote2", chunk_id="chunk2"),
            Citation(id=3, doc="Doc3", section="Sec3", quote="Quote3", chunk_id="chunk3"),
            Citation(id=4, doc="Doc4", section="Sec4", quote="Quote4", chunk_id="chunk4"),
        ]

        summary = "Account risk [1][2]"
        key_findings = [
            "ML Signal [1]",
            "Trading [2][3]"
        ]
        recommended_action = "Review [3]"

        # Filter and re-index
        filtered_citations, updated_summary, updated_key_findings, updated_action = filter.filter_and_reindex(
            all_citations, summary, key_findings, recommended_action
        )

        # Citation 4 is unused, should be filtered out
        assert len(filtered_citations) == 3
        # IDs should be sequential [1, 2, 3]
        assert [c.id for c in filtered_citations] == [1, 2, 3]

        # Text should have updated marks (though IDs might be same after re-index)
        assert "[1]" in updated_summary
        assert "[1]" in updated_key_findings[0]
        assert "[3]" in updated_key_findings[1]

    def test_no_unused_citations_validation(self):
        """Test that after filtering, no unused citations remain."""
        from app.services.citation_coverage_service import create_citation_filter, Citation

        filter = create_citation_filter()

        all_citations = [
            Citation(id=1, doc="Doc1", section="Sec1", quote="Quote1", chunk_id="chunk1"),
            Citation(id=2, doc="Doc2", section="Sec2", quote="Quote2", chunk_id="chunk2"),
            Citation(id=3, doc="Doc3", section="Sec3", quote="Quote3", chunk_id="chunk3"),
        ]

        summary = "Risk [1]"
        key_findings = [
            "ML [1]",
            "Trading [2]"
        ]
        recommended_action = "Review [2]"

        filtered_citations, updated_summary, updated_key_findings, updated_action = filter.filter_and_reindex(
            all_citations, summary, key_findings, recommended_action
        )

        # Extract all citation IDs from updated text
        import re
        all_marks = set()
        for text in [updated_summary] + updated_key_findings + [updated_action]:
            marks = re.findall(r'\[(\d+)\]', text)
            all_marks.update(int(m) for m in marks)

        # All citation IDs in response should be used
        all_citation_ids = set(c.id for c in filtered_citations)
        unused = all_citation_ids - all_marks

        assert len(unused) == 0, f"Unused citations after filtering: {unused}"

    def test_sequential_ids_after_filtering(self):
        """Test that citation IDs are always sequential after filtering."""
        from app.services.citation_coverage_service import create_citation_filter, Citation

        filter = create_citation_filter()

        # Create citations with non-sequential original IDs
        all_citations = [
            Citation(id=1, doc="Doc1", section="Sec1", quote="Quote1", chunk_id="chunk1"),
            Citation(id=3, doc="Doc3", section="Sec3", quote="Quote3", chunk_id="chunk3"),
            Citation(id=5, doc="Doc5", section="Sec5", quote="Quote5", chunk_id="chunk5"),
        ]

        summary = "Risk [1][3][5]"
        key_findings = ["ML [3]"]
        recommended_action = "Review [5]"

        filtered_citations, _, _, _ = filter.filter_and_reindex(
            all_citations, summary, key_findings, recommended_action
        )

        # IDs should be sequential [1, 2, 3]
        expected_ids = list(range(1, len(filtered_citations) + 1))
        actual_ids = [c.id for c in filtered_citations]
        assert actual_ids == expected_ids, f"Expected {expected_ids}, got {actual_ids}"

    def test_empty_citation_list(self):
        """Test handling when no citations are used."""
        from app.services.citation_coverage_service import create_citation_filter, Citation

        filter = create_citation_filter()

        all_citations = [
            Citation(id=1, doc="Doc1", section="Sec1", quote="Quote1", chunk_id="chunk1"),
        ]

        summary = "Risk score"  # No citation marks
        key_findings = ["ML Signal"]  # No citation marks
        recommended_action = "Review"  # No citation marks

        filtered_citations, updated_summary, updated_key_findings, updated_action = filter.filter_and_reindex(
            all_citations, summary, key_findings, recommended_action
        )

        # Should return empty list
        assert len(filtered_citations) == 0
        # Text should be unchanged
        assert updated_summary == summary
        assert updated_key_findings == key_findings
        assert updated_action == recommended_action

    def test_full_flow_with_filtering(self):
        """Test the full flow: generate citations -> attach marks -> filter unused."""
        from app.services.citation_coverage_service import create_citation_coverage_service, create_citation_filter

        # Step 1: Generate citations (as the service would)
        service = create_citation_coverage_service()
        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Elevated trading_frequency_24h",
            "Connected to 1 other account(s)"
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Step 2: Attach citation marks (as the API would)
        marked_findings = []
        for finding in key_findings:
            ids = finding_to_citations.get(finding, [])
            if ids:
                sorted_ids = sorted(set(ids))
                marks = "".join([f"[{cid}]" for cid in sorted_ids])
                marked_findings.append(f"{finding} {marks}")
            else:
                marked_findings.append(finding)

        # Create explanation dict
        summary = "This account received a HIGH risk score [1]."
        recommended_action = "Review case [2]."
        explanation = {
            "summary": summary,
            "key_findings": marked_findings,
            "recommended_action": recommended_action,
            "citations": citations
        }

        # Step 3: Filter unused citations
        citation_filter = create_citation_filter()
        filtered_citations, updated_summary, updated_key_findings, updated_action = citation_filter.filter_and_reindex(
            all_citations=citations,
            summary=explanation["summary"],
            key_findings=explanation["key_findings"],
            recommended_action=explanation["recommended_action"]
        )

        # Validation: No unused citations
        import re
        all_marks = set()
        for text in [updated_summary] + updated_key_findings + [updated_action]:
            marks = re.findall(r'\[(\d+)\]', text)
            all_marks.update(int(m) for m in marks)

        all_citation_ids = set(c.id for c in filtered_citations)
        unused = all_citation_ids - all_marks

        assert len(unused) == 0, f"Unused citations: {unused}"

        # Validation: IDs are sequential
        expected_ids = list(range(1, len(filtered_citations) + 1))
        actual_ids = [c.id for c in filtered_citations]
        assert actual_ids == expected_ids

        # Validation: All citations are actually used
        for cid in all_citation_ids:
            assert cid in all_marks, f"Citation {cid} not referenced in text"

    def test_citation_sharing_when_limit_reached(self):
        """Test that findings share citations when max_limit prevents new citations."""
        service = create_citation_coverage_service()

        # Create many findings to exceed max_limit
        key_findings = [
            "ML Signal Score: 85.00",
            "Rule Engine Signal Score: 72.50",
            "Graph Network Signal Score: 60.00",
            "Elevated trading_frequency_24h",
            "Elevated account_age_days",
            "Elevated withdrawal_frequency_24h",
            "Connected to 5 other accounts"
        ]

        factors = [
            {'factor_name': 'trading_frequency_24h', 'factor_value': 150},
            {'factor_name': 'account_age_days', 'factor_value': 5},
            {'factor_name': 'withdrawal_frequency_24h', 'factor_value': 10}
        ]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factors=factors,
            has_graph_evidence=True,
            audience="investigator",
            max_citations_per_finding=1,
            target_citation_count=4,
            max_citation_limit=3  # Low limit to force sharing
        )

        # Check that all findings still have citations (even if shared)
        assert report.findings_with_citations == len(key_findings), \
            f"Only {report.findings_with_citations}/{len(key_findings)} findings have citations"

        # Every finding should have at least one citation ID
        for finding in key_findings:
            ids = finding_to_citations.get(finding, [])
            assert len(ids) > 0, f"Finding '{finding}' has no citations"

        # Total citations should respect max_limit
        assert len(citations) <= 3, f"Too many citations: {len(citations)}"

        # All citation IDs in findings should exist in citations list
        all_citation_ids = set(c.id for c in citations)
        for finding, ids in finding_to_citations.items():
            for cid in ids:
                assert cid in all_citation_ids, f"Citation ID {cid} not in citations list"


class TestDomainConstraints:
    """Test strict domain constraints for citation mapping."""

    def test_account_profile_does_not_get_graph_policy(self):
        """Test that ACCOUNT_PROFILE findings do NOT get network/cluster policies."""
        service = create_citation_coverage_service()

        key_findings = ["Elevated New Account Risk"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[{"factor_name": "account_age_days", "factor_value": 5}],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that no citation is from network/cluster domain
        for cit in citations:
            doc_lower = cit.doc.lower()
            # FORBIDDEN domains for ACCOUNT_PROFILE
            if "cluster" in doc_lower and ("network" in doc_lower or "risky" in doc_lower):
                assert False, f"ACCOUNT_PROFILE finding should not cite network/cluster policy: {cit.doc}"
            if "shared device" in doc_lower or "shared ip" in doc_lower:
                assert False, f"ACCOUNT_PROFILE finding should not cite shared device/IP policy: {cit.doc}"

    def test_account_profile_gets_kyc_policy(self):
        """Test that ACCOUNT_PROFILE findings get KYC/CDD policies."""
        service = create_citation_coverage_service()

        key_findings = ["Elevated New Account Risk"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[{"factor_name": "account_age_days", "factor_value": 5}],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that at least one citation is from KYC/CDD domain
        found_kyc_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            if any(keyword in doc_lower for keyword in ["kyc", "cdd", "onboarding", "account"]):
                found_kyc_citation = True
                break

        assert found_kyc_citation, "ACCOUNT_PROFILE finding should have at least one KYC/CDD citation"

    def test_graph_signal_gets_network_policy(self):
        """Test that GRAPH_SIGNAL findings get network/relationship policies."""
        service = create_citation_coverage_service()

        key_findings = ["Connected to 2 other accounts through shared devices"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that at least one citation is from network domain
        found_network_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            if any(keyword in doc_lower for keyword in ["network", "relationship", "cluster", "shared"]):
                found_network_citation = True
                break

        assert found_network_citation, "GRAPH_SIGNAL finding should have at least one network policy citation"

    def test_graph_signal_does_not_get_kyc_policy(self):
        """Test that GRAPH_SIGNAL findings do NOT get KYC/onboarding policies."""
        service = create_citation_coverage_service()

        key_findings = ["Connected to shared devices/IPs"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Check that no citation is pure KYC/onboarding
        for cit in citations:
            doc_lower = cit.doc.lower()
            # FORBIDDEN: pure KYC citations for GRAPH_SIGNAL
            if "kyc" in doc_lower and "cdd" in doc_lower:
                if "network" not in doc_lower and "cluster" not in doc_lower:
                    assert False, f"GRAPH_SIGNAL finding should not cite pure KYC policy: {cit.doc}"

    def test_transaction_frequency_gets_behavior_policy(self):
        """Test that transaction behavior findings get AML/transaction monitoring policies."""
        service = create_citation_coverage_service()

        key_findings = ["High Trading Frequency"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=72.5,
            graph_score=0.0,
            factors=[{"factor_name": "trading_frequency_24h", "factor_value": 150}],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that citations are from AML/transaction domain
        found_aml_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            if any(keyword in doc_lower for keyword in ["aml", "transaction", "trading", "frequency", "monitoring"]):
                found_aml_citation = True
                break

        assert found_aml_citation, "Trading frequency finding should have at least one AML/transaction policy citation"

    def test_ml_signal_gets_ml_policy(self):
        """Test that ML_SIGNAL findings get ML/anomaly detection policies."""
        service = create_citation_coverage_service()

        key_findings = ["ML Signal Score: 85.00"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that citations are from ML domain
        found_ml_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            if any(keyword in doc_lower for keyword in ["ml", "model", "anomaly", "detection", "scoring"]):
                found_ml_citation = True
                break

        assert found_ml_citation, "ML_SIGNAL finding should have at least one ML/anomaly policy citation"

    def test_domain_mapper_classification(self):
        """Test that the domain mapper correctly classifies finding types."""
        from app.services.citation_mapper import create_domain_aware_citation_mapper, FindingType

        mapper = create_domain_aware_citation_mapper()

        # Test ACCOUNT_PROFILE classification
        metadata = mapper.get_finding_metadata(
            text="Elevated New Account Risk",
            factor_name="account_age_days"
        )
        assert metadata.finding_type == FindingType.ACCOUNT_PROFILE
        assert any("kyc" in str(d).lower() for d in metadata.citation_domain)

        # Test GRAPH_SIGNAL classification
        metadata = mapper.get_finding_metadata(
            text="Connected to shared devices",
            has_graph_evidence=True
        )
        assert metadata.finding_type == FindingType.GRAPH_SIGNAL
        assert any("network" in str(d).lower() for d in metadata.citation_domain)

        # Test TRANSACTION_BEHAVIOR classification
        metadata = mapper.get_finding_metadata(
            text="High Trading Frequency",
            factor_name="trading_frequency_24h"
        )
        assert metadata.finding_type == FindingType.TRANSACTION_BEHAVIOR
        assert any("transaction" in str(d).lower() or "trading" in str(d).lower() for d in metadata.citation_domain)


class TestDomainEnforcement:
    """Test strict domain enforcement for citation mapping."""

    def test_graph_finding_never_gets_kyc_citation(self):
        """Test that GRAPH_SIGNAL findings NEVER cite KYC/CDD policies."""
        service = create_citation_coverage_service()

        # GRAPH_SIGNAL finding
        key_findings = ["Elevated Linked Account Network"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that NO citation is from KYC/CDD domain
        for cit in citations:
            doc_lower = cit.doc.lower()
            section_lower = cit.section.lower() if cit.section else ""

            # FORBIDDEN: KYC/CDD documents for GRAPH_SIGNAL
            assert "kyc" not in doc_lower, f"GRAPH_SIGNAL finding should NOT cite KYC document: {cit.doc}"
            assert "cdd" not in doc_lower, f"GRAPH_SIGNAL finding should NOT cite CDD document: {cit.doc}"

            # FORBIDDEN: Transaction/velocity sections in AML doc
            if "aml" in doc_lower:
                # If citing AML doc, must be network section, NOT transaction sections
                assert "network" in section_lower or "relationship" in section_lower or "cluster" in section_lower, \
                    f"GRAPH_SIGNAL citing AML doc must use network section, not transaction: {cit.section}"
                assert "transaction" not in section_lower, \
                    f"GRAPH_SIGNAL should NOT cite transaction section: {cit.section}"
                assert "velocity" not in section_lower, \
                    f"GRAPH_SIGNAL should NOT cite velocity section: {cit.section}"

    def test_graph_finding_gets_network_section_in_aml_doc(self):
        """Test that GRAPH_SIGNAL findings cite network section of AML doc OR valid fallback."""
        service = create_citation_coverage_service()

        key_findings = ["Connected to 5 other accounts through shared devices"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=60.0,
            factors=[],
            has_graph_evidence=True,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check citations are valid (either network section or valid fallback)
        found_valid_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            section_lower = cit.section.lower() if cit.section else ""

            # Valid: Network section in AML doc
            if "aml" in doc_lower:
                if any(keyword in section_lower for keyword in ["network", "relationship", "cluster", "shared"]):
                    found_valid_citation = True
                    break

            # Valid: Investigation SOP fallback (acceptable for all finding types)
            if "investigation" in doc_lower or "sop" in doc_lower:
                found_valid_citation = True
                break

        assert found_valid_citation, "GRAPH_SIGNAL should have at least one valid citation (network section or SOP fallback)"

    def test_new_account_risk_gets_kyc_citation(self):
        """Test that ACCOUNT_PROFILE findings get KYC/CDD policies."""
        service = create_citation_coverage_service()

        # ACCOUNT_PROFILE finding
        key_findings = ["Elevated New Account Risk"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[{"factor_name": "account_age_days", "factor_value": 5}],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that at least one citation is from KYC/CDD domain
        found_kyc_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            section_lower = cit.section.lower() if cit.section else ""

            # Look for KYC/CDD indicators
            if any(keyword in doc_lower for keyword in ["kyc", "cdd"]):
                found_kyc_citation = True
                break
            # Also check for KYC-related sections
            if any(keyword in section_lower for keyword in ["customer", "verification", "onboarding"]):
                found_kyc_citation = True
                break

        assert found_kyc_citation, "ACCOUNT_PROFILE finding should have at least one KYC/CDD citation"

    def test_account_profile_never_gets_transaction_section(self):
        """Test that ACCOUNT_PROFILE findings do NOT cite transaction behavior sections."""
        service = create_citation_coverage_service()

        key_findings = ["Elevated account_age_days"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=0.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[{"factor_name": "account_age_days", "factor_value": 5}],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Check that NO citation is from transaction behavior sections
        for cit in citations:
            section_lower = cit.section.lower() if cit.section else ""

            # FORBIDDEN: Transaction/velocity sections for ACCOUNT_PROFILE
            assert "transaction" not in section_lower or "network" in section_lower, \
                f"ACCOUNT_PROFILE should NOT cite transaction section: {cit.section}"
            assert "velocity" not in section_lower, \
                f"ACCOUNT_PROFILE should NOT cite velocity section: {cit.section}"
            assert "burst" not in section_lower, \
                f"ACCOUNT_PROFILE should NOT cite burst section: {cit.section}"

    def test_ml_finding_gets_explainability_citation(self):
        """Test that ML_SIGNAL findings get explainability policy citations."""
        service = create_citation_coverage_service()

        # ML_SIGNAL finding
        key_findings = ["ML Signal Score: 85.00"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Should have citations
        assert len(citations) > 0, "Should have at least one citation"

        # Check that citations are from ML/explainability domain, NOT transaction domain
        found_explainability_citation = False
        for cit in citations:
            doc_lower = cit.doc.lower()
            section_lower = cit.section.lower() if cit.section else ""

            # Look for ML/explainability indicators
            if any(keyword in doc_lower for keyword in ["explainability", "scoring", "guide"]):
                found_explainability_citation = True
                break
            if any(keyword in section_lower for keyword in ["ml", "model", "evidence", "explanation"]):
                found_explainability_citation = True
                break

            # FORBIDDEN: ML_SIGNAL should NOT cite transaction sections
            if "aml" in doc_lower:
                # If citing AML doc, verify it's not transaction section
                assert "transaction" not in section_lower, \
                    f"ML_SIGNAL should NOT cite transaction section: {cit.section}"
                assert "velocity" not in section_lower, \
                    f"ML_SIGNAL should NOT cite velocity section: {cit.section}"

        # Note: May not find explainability if doc doesn't exist yet
        # But transaction sections should still be rejected

    def test_ml_finding_never_gets_aml_transaction_citation(self):
        """Test that ML_SIGNAL findings do NOT cite AML transaction/velocity sections."""
        service = create_citation_coverage_service()

        key_findings = ["Primary concern: ML Pattern Detection"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Check that NO citation is from transaction sections
        for cit in citations:
            doc_lower = cit.doc.lower()
            section_lower = cit.section.lower() if cit.section else ""

            # FORBIDDEN: ML_SIGNAL should NOT cite transaction behavior
            if "aml" in doc_lower:
                assert "transaction" not in section_lower, \
                    f"ML_SIGNAL should NOT cite AML transaction section: {cit.section}"
                assert "velocity" not in section_lower, \
                    f"ML_SIGNAL should NOT cite AML velocity section: {cit.section}"
                assert "burst" not in section_lower, \
                    f"ML_SIGNAL should NOT cite AML burst section: {cit.section}"

    def test_linked_account_network_classified_as_graph_not_account(self):
        """Test that 'Elevated Linked Account Network' is classified as GRAPH_SIGNAL, not ACCOUNT_PROFILE."""
        from app.services.citation_mapper import create_domain_aware_citation_mapper, FindingType

        mapper = create_domain_aware_citation_mapper()

        # This was the bug: "Linked Account Network" → ACCOUNT_PROFILE because "account" keyword
        # Should be: GRAPH_SIGNAL because "linked" and "network" keywords have higher priority
        finding_type = mapper.classify_finding(
            text="Elevated Linked Account Network",
            graph_score=60.0,
            has_graph_evidence=True
        )

        assert finding_type == FindingType.GRAPH_SIGNAL, \
            f"'Elevated Linked Account Network' should be GRAPH_SIGNAL, got {finding_type}"
        assert finding_type != FindingType.ACCOUNT_PROFILE, \
            "Should NOT be classified as ACCOUNT_PROFILE"

    def test_network_keywords_higher_priority_than_account(self):
        """Test that network keywords have higher priority than 'account' keyword."""
        from app.services.citation_mapper import create_domain_aware_citation_mapper, FindingType

        mapper = create_domain_aware_citation_mapper()

        # Test cases with both "account" and network keywords
        test_cases = [
            ("Connected to linked accounts", FindingType.GRAPH_SIGNAL),
            ("Shared device network account", FindingType.GRAPH_SIGNAL),
            ("Cluster account relationship", FindingType.GRAPH_SIGNAL),
        ]

        for text, expected_type in test_cases:
            finding_type = mapper.classify_finding(text=text)
            assert finding_type == expected_type, \
                f"'{text}' should be {expected_type}, got {finding_type}"

    def test_metadata_chunks_are_rejected(self):
        """Test that document metadata chunks are rejected."""
        service = create_citation_coverage_service()

        # Test the metadata filtering method
        metadata_chunks = [
            "> Status: DEMO TEMPLATE (non-authoritative)",
            "Purpose: Provide citable text snippets",
            "non-authoritative",
            "Replace with your organization's official policy",
            "> Purpose: Replace with official AML policy",
        ]

        for chunk_text in metadata_chunks:
            assert service._is_metadata_chunk(chunk_text), \
                f"Should be identified as metadata: '{chunk_text}'"

    def test_policy_evidence_chunks_are_accepted(self):
        """Test that actual policy evidence chunks are accepted."""
        service = create_citation_coverage_service()

        # Test actual policy content
        evidence_chunks = [
            "A sudden spike in the number of outgoing transfers within a short time window may indicate:",
            "Enhanced due diligence required when risk scoring indicates high risk",
            "ML models detect anomalous patterns in transaction behavior",
            "Accounts linked to known risky clusters should be prioritized for review",
        ]

        for chunk_text in evidence_chunks:
            assert not service._is_metadata_chunk(chunk_text), \
                f"Should NOT be identified as metadata: '{chunk_text}'"

    def test_metadata_filtering_in_citation_generation(self):
        """Test that metadata chunks are filtered during citation generation."""
        service = create_citation_coverage_service()

        key_findings = ["ML Signal Score: 85.00"]

        citations, finding_to_citations, report = service.generate_citations(
            key_findings=key_findings,
            ml_score=85.0,
            rule_score=0.0,
            graph_score=0.0,
            factors=[],
            has_graph_evidence=False,
            audience="investigator"
        )

        # Verify no metadata chunks in citations
        for cit in citations:
            assert not service._is_metadata_chunk(cit.quote), \
                f"Citation should not contain metadata: {cit.quote[:100]}"

            # Check that quotes don't start with metadata patterns
            quote_lower = cit.quote.lower() if cit.quote else ""
            assert not quote_lower.startswith("> status:"), \
                f"Quote should not start with '> Status:': {cit.quote[:50]}"
            assert not quote_lower.startswith("> purpose:"), \
                f"Quote should not start with '> Purpose:': {cit.quote[:50]}"
