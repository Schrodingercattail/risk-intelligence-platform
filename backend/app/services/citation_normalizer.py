"""
Citation Normalization Service

Performs final citation cleanup before API response:
1. Deduplicates citations by (doc, section, chunk_id)
2. Sorts citations deterministically for stable output
3. Reassigns sequential IDs starting from 1
4. Provides old_id -> new_id mapping for text rewriting

This ensures:
- Citation marks [n] in text always match citations[n-1]
- No gaps in citation IDs
- No orphaned citation marks
- Frontend can reliably render clickable citations
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CitationKey:
    """
    Unique key for citation deduplication.

    Two citations are the same if they have the same:
    - doc (document filename)
    - section (section path)
    - chunk_id (chunk identifier)
    """
    doc: str
    section: str
    chunk_id: str

    def __str__(self) -> str:
        return f"{self.doc}#{self.section}#{self.chunk_id}"


@dataclass
class NormalizedCitation:
    """A citation with normalized ID."""
    id: int
    doc: str
    section: str
    quote: str
    chunk_id: str
    original_id: int  # Track original ID for mapping


@dataclass
class NormalizationResult:
    """
    Result of citation normalization.

    Attributes:
        citations: List of normalized citations with sequential IDs
        id_mapping: Mapping from old IDs to new IDs
        stats: Statistics about the normalization process
    """
    citations: List[Dict]
    id_mapping: Dict[int, int]
    stats: Dict

    def rewrite_text(self, text: str) -> str:
        """
        Rewrite citation marks in text using new ID mapping.

        Args:
            text: Text with citation marks like [1], [2], etc.

        Returns:
            Text with rewritten citation marks
        """
        if not self.id_mapping:
            return text

        # Sort by old_id in descending order to avoid overlapping replacements
        # e.g., [10] should be replaced before [1]
        for old_id in sorted(self.id_mapping.keys(), reverse=True):
            new_id = self.id_mapping[old_id]
            # Replace all occurrences of [old_id] with [new_id]
            text = text.replace(f"[{old_id}]", f"[{new_id}]")

        return text


class CitationNormalizer:
    """
    Normalizes citations for consistent frontend rendering.

    Flow:
    1. Accept citations from CitationRegistry
    2. Deduplicate by (doc, section, chunk_id)
    3. Sort deterministically
    4. Reassign sequential IDs from 1
    5. Provide old->new ID mapping for text rewriting
    """

    def __init__(self):
        """Initialize citation normalizer."""
        self._dedup_count = 0
        self._original_count = 0

    def normalize(
        self,
        citations: List[Dict],
        max_citations: int = 5
    ) -> NormalizationResult:
        """
        Normalize citations for API response.

        Args:
            citations: List of citation dicts from CitationRegistry
            max_citations: Maximum citations to return (budget limit)

        Returns:
            NormalizationResult with normalized citations and ID mapping
        """
        self._original_count = len(citations)
        self._dedup_count = 0

        if not citations:
            return NormalizationResult(
                citations=[],
                id_mapping={},
                stats={
                    "original_count": 0,
                    "after_dedup": 0,
                    "final_count": 0,
                    "deduped": 0,
                    "budget_applied": max_citations
                }
            )

        # Step 1: Deduplicate by (doc, section, chunk_id)
        unique_citations = self._deduplicate(citations)

        # Step 2: Sort deterministically (by doc, then section, then chunk_id)
        sorted_citations = self._sort_deterministically(unique_citations)

        # Step 3: Apply budget limit
        trimmed_citations = sorted_citations[:max_citations]

        # Step 4: Reassign sequential IDs starting from 1
        normalized_citations, id_mapping = self._reassign_ids(trimmed_citations)

        # Build stats
        stats = {
            "original_count": self._original_count,
            "after_dedup": len(unique_citations),
            "final_count": len(normalized_citations),
            "deduped": self._dedup_count,
            "budget_applied": max_citations
        }

        # Log if reduction occurred
        if stats["original_count"] > stats["final_count"]:
            logger.info(
                f"Citation normalization: {stats['original_count']} -> "
                f"{stats['after_dedup']} (dedup) -> {stats['final_count']} (budget={max_citations})"
            )

        return NormalizationResult(
            citations=normalized_citations,
            id_mapping=id_mapping,
            stats=stats
        )

    def _deduplicate(self, citations: List[Dict]) -> List[Dict]:
        """
        Deduplicate citations by (doc, section, chunk_id).

        Args:
            citations: List of citation dicts

        Returns:
            List of unique citations (first occurrence kept)
        """
        seen: Set[CitationKey] = set()
        unique: List[Dict] = []

        for citation in citations:
            key = CitationKey(
                doc=citation.get("doc", ""),
                section=citation.get("section", ""),
                chunk_id=citation.get("chunk_id", "")
            )

            if key not in seen:
                seen.add(key)
                unique.append(citation)
            else:
                self._dedup_count += 1
                logger.debug(f"Deduplicated citation: {key}")

        return unique

    def _sort_deterministically(self, citations: List[Dict]) -> List[Dict]:
        """
        Sort citations deterministically for stable output.

        Order: doc -> section -> chunk_id (all ascending)

        Args:
            citations: List of citation dicts

        Returns:
            Sorted list of citations
        """
        return sorted(
            citations,
            key=lambda c: (
                c.get("doc", ""),
                c.get("section", ""),
                c.get("chunk_id", "")
            )
        )

    def _reassign_ids(
        self,
        citations: List[Dict]
    ) -> Tuple[List[Dict], Dict[int, int]]:
        """
        Reassign sequential IDs starting from 1.

        Args:
            citations: List of citation dicts

        Returns:
            Tuple of (citations with new IDs, old_id -> new_id mapping)
        """
        normalized = []
        id_mapping: Dict[int, int] = {}

        for new_id, citation in enumerate(citations, start=1):
            old_id = citation.get("id", 0)
            id_mapping[old_id] = new_id

            normalized.append({
                "id": new_id,
                "doc": citation.get("doc", ""),
                "section": citation.get("section", ""),
                "quote": citation.get("quote", ""),
                "chunk_id": citation.get("chunk_id", "")
            })

        return normalized, id_mapping


def create_citation_normalizer() -> CitationNormalizer:
    """
    Factory function to create a CitationNormalizer instance.

    Returns:
        New CitationNormalizer instance
    """
    return CitationNormalizer()
