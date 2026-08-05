"""
Citation Registry Service

Maintains a global citation registry during a single explain request to:
1. Deduplicate citations using (doc, section, chunk_id)
2. Assign stable sequential citation IDs
3. Enforce citation budget limits

Principles:
- Same citation content gets same ID within one request
- IDs are stable and sequential
- Budget control prevents citation bloat
- Graceful degradation on failures
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CitationKey:
    """
    Unique key for citation deduplication.

    Two citations are considered the same if they have the same:
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
class RegisteredCitation:
    """A registered citation with stable ID."""
    id: int
    doc: str
    section: str
    quote: str
    chunk_id: str
    priority: int = 0  # Higher = more important
    finding_types: Set[str] = field(default_factory=set)  # Which finding types use this


@dataclass
class CitationBudget:
    """
    Citation budget configuration.

    Controls maximum number of citations in final response.
    """
    max_citations: int = 5
    prefer_finding_specific: bool = True
    deprioritize_sop: bool = True

    # Priority weights for citation types
    PRIORITY_WEIGHTS = {
        "ml_signal": 10,
        "rule_signal": 9,
        "graph_signal": 8,
        "account_profile": 7,
        "network_behavior": 6,
        "action_recommendation": 5,  # SOP citations get lower priority
        "generic": 1
    }


class CitationRegistry:
    """
    Registry for managing citations within a single explain request.

    Responsibilities:
    1. Deduplicate citations by (doc, section, chunk_id)
    2. Assign stable sequential IDs
    3. Enforce citation budget limits
    4. Prioritize finding-specific citations over generic ones
    """

    def __init__(self, budget: Optional[CitationBudget] = None):
        """
        Initialize citation registry.

        Args:
            budget: Citation budget configuration
        """
        self.budget = budget or CitationBudget()
        self._citations: Dict[CitationKey, RegisteredCitation] = OrderedDict()
        self._next_id = 1
        self._lock_counter = 0  # Simple counter for basic thread safety
        self._registration_count = 0  # Track total registration attempts

    def register(
        self,
        doc: str,
        section: str,
        quote: str,
        chunk_id: str,
        finding_type: Optional[str] = None
    ) -> int:
        """
        Register a citation and return its stable ID.

        If the citation (by key) already exists, return the existing ID.
        Otherwise, assign a new sequential ID.

        Args:
            doc: Document filename
            section: Section path
            quote: Citation text
            chunk_id: Chunk identifier
            finding_type: Type of finding using this citation

        Returns:
            Stable citation ID
        """
        key = CitationKey(doc=doc, section=section, chunk_id=chunk_id)
        self._registration_count += 1  # Track registration attempt

        if key in self._citations:
            # Existing citation — return its ID
            existing = self._citations[key]
            # Track finding type if provided
            if finding_type:
                existing.finding_types.add(finding_type)
            return existing.id

        # New citation — assign new ID
        citation = RegisteredCitation(
            id=self._next_id,
            doc=doc,
            section=section,
            quote=quote,
            chunk_id=chunk_id,
            priority=self._calculate_priority(doc, section, finding_type)
        )

        if finding_type:
            citation.finding_types.add(finding_type)

        self._citations[key] = citation
        self._next_id += 1

        return citation.id

    def _calculate_priority(self, doc: str, section: str, finding_type: Optional[str]) -> int:
        """
        Calculate citation priority for budget enforcement.

        Higher priority citations are more likely to be included when budget is exceeded.

        Args:
            doc: Document filename
            section: Section path
            finding_type: Type of finding

        Returns:
            Priority score (higher = more important)
        """
        # Base priority from finding type
        if finding_type:
            base = self.budget.PRIORITY_WEIGHTS.get(
                finding_type.lower(),
                self.budget.PRIORITY_WEIGHTS["generic"]
            )
        else:
            base = self.budget.PRIORITY_WEIGHTS["generic"]

        # Boost for finding-specific policy matches
        section_lower = section.lower()
        doc_lower = doc.lower()

        # Finding-to-policy alignment boosts
        if finding_type == "ml_signal" and ("ml" in doc_lower or "anomaly" in section_lower):
            base += 3
        elif finding_type == "graph_signal" and ("network" in section_lower or "cluster" in section_lower):
            base += 3
        elif finding_type == "rule_signal" and ("transaction" in section_lower or "behavior" in section_lower):
            base += 3
        elif finding_type == "account_profile" and ("kyc" in doc_lower or "cdd" in doc_lower):
            base += 3

        # Deprioritize generic SOP/investigation procedure citations
        if self.budget.deprioritize_sop:
            if "sop" in doc_lower or "workflow" in section_lower or "procedure" in section_lower:
                base -= 2

        return max(1, base)  # Ensure minimum priority of 1

    def get_all_citations(self) -> List[RegisteredCitation]:
        """
        Get all registered citations in ID order.

        Returns:
            List of citations sorted by ID
        """
        return sorted(self._citations.values(), key=lambda c: c.id)

    def get_citations_within_budget(self) -> List[RegisteredCitation]:
        """
        Get citations within budget limits.

        If total citations exceed budget, return highest-priority ones.
        Ensures at least one citation per finding type if possible.

        Returns:
            List of citations within budget
        """
        all_citations = self.get_all_citations()

        if len(all_citations) <= self.budget.max_citations:
            return all_citations

        # Need to trim — sort by priority (highest first)
        sorted_by_priority = sorted(
            all_citations,
            key=lambda c: (c.priority, -len(c.finding_types)),  # Higher priority, more finding types first
            reverse=True
        )

        # Take top N
        trimmed = sorted_by_priority[:self.budget.max_citations]

        # Re-sort by ID for stable output
        trimmed = sorted(trimmed, key=lambda c: c.id)

        logger.warning(
            f"Citation budget exceeded: {len(all_citations)} citations "
            f"reduced to {len(trimmed)} (budget={self.budget.max_citations})"
        )

        return trimmed

    def get_citation_dict(self) -> List[Dict]:
        """
        Get citations as dict list for API response.

        Returns:
            List of citation dicts compatible with PolicyCitation schema
        """
        citations = self.get_citations_within_budget()

        return [
            {
                "id": c.id,
                "doc": c.doc,
                "section": c.section,
                "quote": c.quote,
                "chunk_id": c.chunk_id
            }
            for c in citations
        ]

    def get_stats(self) -> Dict:
        """
        Get registry statistics for monitoring.

        Returns:
            Dict with stats
        """
        all_citations = self.get_all_citations()

        return {
            "registration_attempts": self._registration_count,
            "total_registered": len(all_citations),
            "deduplication_saved": self._registration_count - len(all_citations),
            "unique_chunks": len(set(c.chunk_id for c in all_citations))
        }


def create_citation_registry(max_citations: int = 5) -> CitationRegistry:
    """
    Factory function to create a CitationRegistry instance.

    Args:
        max_citations: Maximum citations per explanation

    Returns:
        New CitationRegistry instance
    """
    budget = CitationBudget(max_citations=max_citations)
    return CitationRegistry(budget=budget)
