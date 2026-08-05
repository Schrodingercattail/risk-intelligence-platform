"""
Tests for CitationNormalizer service.

Verifies:
1. Non-sequential IDs are normalized to sequential [1..N]
2. Duplicate citations are merged by (doc, section, chunk_id)
3. Text citation marks are rewritten correctly
4. Budget limit is enforced
5. Clickable citation mapping remains valid
"""
import pytest
from app.services.citation_normalizer import (
    CitationNormalizer,
    create_citation_normalizer,
    NormalizationResult
)


class TestCitationNormalizer:
    """Test suite for CitationNormalizer."""

    def test_non_sequential_ids_normalized(self):
        """Test that non-sequential IDs (e.g., 4, 7, 9) become 1, 2, 3."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 4, 'doc': 'AML.md', 'section': 'Section 1', 'quote': 'Quote 1', 'chunk_id': 'chunk1'},
            {'id': 7, 'doc': 'KYC.md', 'section': 'Section 2', 'quote': 'Quote 2', 'chunk_id': 'chunk2'},
            {'id': 9, 'doc': 'SOP.md', 'section': 'Section 3', 'quote': 'Quote 3', 'chunk_id': 'chunk3'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # Verify sequential IDs
        assert [c['id'] for c in result.citations] == [1, 2, 3]

        # Verify mapping
        assert result.id_mapping == {4: 1, 7: 2, 9: 3}

    def test_duplicate_citations_merged(self):
        """Test that duplicates with same (doc, section, chunk_id) are merged."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 1, 'doc': 'AML.md', 'section': 'Section 1', 'quote': 'Quote A', 'chunk_id': 'chunk1'},
            {'id': 2, 'doc': 'AML.md', 'section': 'Section 1', 'quote': 'Quote B', 'chunk_id': 'chunk1'},  # Duplicate (same key)
            {'id': 3, 'doc': 'KYC.md', 'section': 'Section 2', 'quote': 'Quote 3', 'chunk_id': 'chunk2'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # First occurrence is kept, second duplicate is removed
        assert result.stats['after_dedup'] == 2
        assert result.stats['final_count'] == 2
        assert result.stats['deduped'] == 1

    def test_text_markers_rewritten_correctly(self):
        """Test that citation marks in text are rewritten using new IDs."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 4, 'doc': 'AML.md', 'section': 'Section 1', 'quote': 'Quote 1', 'chunk_id': 'chunk1'},
            {'id': 7, 'doc': 'KYC.md', 'section': 'Section 2', 'quote': 'Quote 2', 'chunk_id': 'chunk2'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # Test text rewriting
        text = "Finding [4] and [7]"
        rewritten = result.rewrite_text(text)
        assert rewritten == "Finding [1] and [2]"

    def test_budget_limit_enforced(self):
        """Test that only max_citations are returned."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': i, 'doc': f'Doc{i}.md', 'section': f'Section {i}', 'quote': f'Quote {i}', 'chunk_id': f'chunk{i}'}
            for i in range(1, 11)
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # Only 5 should be returned
        assert result.stats['final_count'] == 5
        assert [c['id'] for c in result.citations] == [1, 2, 3, 4, 5]

    def test_clickable_mapping_remains_valid(self):
        """Test that after normalization, all marks map to valid citations."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 3, 'doc': 'AML.md', 'section': 'Sec1', 'quote': 'Q1', 'chunk_id': 'c1'},
            {'id': 8, 'doc': 'KYC.md', 'section': 'Sec2', 'quote': 'Q2', 'chunk_id': 'c2'},
            {'id': 15, 'doc': 'SOP.md', 'section': 'Sec3', 'quote': 'Q3', 'chunk_id': 'c3'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # All citation IDs should be 1, 2, 3
        citation_ids = [c['id'] for c in result.citations]
        assert citation_ids == [1, 2, 3]

        # All marks should map to valid IDs
        marks = [1, 2, 3]
        for mark in marks:
            assert mark in citation_ids

    def test_empty_citations(self):
        """Test handling of empty citation list."""
        normalizer = create_citation_normalizer()
        result = normalizer.normalize([], max_citations=5)

        assert result.citations == []
        assert result.id_mapping == {}
        assert result.stats['final_count'] == 0

    def test_deterministic_sorting(self):
        """Test that citations are sorted deterministically."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 5, 'doc': 'Z.md', 'section': 'Z', 'quote': 'Z', 'chunk_id': 'z'},
            {'id': 1, 'doc': 'A.md', 'section': 'A', 'quote': 'A', 'chunk_id': 'a'},
            {'id': 3, 'doc': 'M.md', 'section': 'M', 'quote': 'M', 'chunk_id': 'm'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # Should be sorted by doc -> section -> chunk_id
        assert result.citations[0]['doc'] == 'A.md'
        assert result.citations[1]['doc'] == 'M.md'
        assert result.citations[2]['doc'] == 'Z.md'

    def test_complex_text_rewriting(self):
        """Test text rewriting with multiple marks in various positions."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 10, 'doc': 'A.md', 'section': 'S1', 'quote': 'Q1', 'chunk_id': 'c1'},
            {'id': 20, 'doc': 'B.md', 'section': 'S2', 'quote': 'Q2', 'chunk_id': 'c2'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # Test various text patterns
        test_cases = [
            ("Text [10]", "Text [1]"),
            ("[10] and [20]", "[1] and [2]"),
            ("[10][20]", "[1][2]"),
            ("End [10] middle [20] end", "End [1] middle [2] end"),
        ]

        for original, expected in test_cases:
            rewritten = result.rewrite_text(original)
            assert rewritten == expected, f"Expected '{expected}', got '{rewritten}'"

    def test_id_mapping_preserves_all_original_ids(self):
        """Test that all original IDs are present in mapping."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 4, 'doc': 'A.md', 'section': 'S1', 'quote': 'Q1', 'chunk_id': 'c1'},
            {'id': 7, 'doc': 'B.md', 'section': 'S2', 'quote': 'Q2', 'chunk_id': 'c2'},
            {'id': 9, 'doc': 'C.md', 'section': 'S3', 'quote': 'Q3', 'chunk_id': 'c3'},
        ]
        result = normalizer.normalize(citations, max_citations=5)

        # All original IDs should be in mapping
        original_ids = {c['id'] for c in citations}
        mapped_original_ids = set(result.id_mapping.keys())
        assert original_ids == mapped_original_ids

    def test_stats_tracking(self):
        """Test that normalization stats are tracked correctly."""
        normalizer = create_citation_normalizer()
        citations = [
            {'id': 1, 'doc': 'A.md', 'section': 'S1', 'quote': 'Q1', 'chunk_id': 'c1'},
            {'id': 2, 'doc': 'A.md', 'section': 'S1', 'quote': 'Q1', 'chunk_id': 'c1'},  # Duplicate
            {'id': 3, 'doc': 'B.md', 'section': 'S2', 'quote': 'Q2', 'chunk_id': 'c2'},
            {'id': 4, 'doc': 'C.md', 'section': 'S3', 'quote': 'Q3', 'chunk_id': 'c3'},
        ]
        result = normalizer.normalize(citations, max_citations=2)

        assert result.stats['original_count'] == 4
        assert result.stats['after_dedup'] == 3
        assert result.stats['final_count'] == 2  # Budget limit
        assert result.stats['deduped'] == 1
        assert result.stats['budget_applied'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
