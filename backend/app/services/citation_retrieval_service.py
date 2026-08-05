"""
Citation Retrieval Service (Redesigned)

Implements strict domain-enforced citation retrieval.

Architecture:
    Finding -> FindingType classification -> CitationPolicyRouter -> Allowed scope -> RAG retrieval -> Validation -> Output

Key principles:
1. Domain constraints enforced BEFORE RAG retrieval
2. Only one primary citation per finding (highly relevant)
3. Maximum 5 citations per explanation
4. No metadata chunks in citations
5. Every finding has at least one citation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
import logging
import re

from app.services.policy_rag_service import PolicyRAGService
from app.services.citation_policy_router import (
    CitationPolicyRouter,
    FindingType,
    get_citation_policy_router,
    PolicyScope
)
from app.services.llm_service import sanitize_policy_quote

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A citation with all metadata."""
    id: int
    doc: str
    section: str
    quote: str
    chunk_id: str
    finding_type: Optional[str] = None


@dataclass
class FindingWithCitation:
    """A finding with its assigned citation."""
    finding_text: str
    finding_type: FindingType
    citation_id: Optional[int] = None


@dataclass
class RetrievalResult:
    """Result of citation retrieval."""
    citations: List[Citation]
    finding_to_citations: Dict[str, List[int]]
    total_findings: int
    findings_with_citations: int
    is_valid: bool


class FindingClassifier:
    """
    Classifies findings into their types with strict priority rules.

    Priority order:
    1. Explicit signal keywords (ML signal, Rule signal, Graph signal)
    2. NETWORK/GRAPH keywords (highest for network-related terms)
    3. Factor-based classification
    4. Score-based classification
    5. Text-based keyword matching (last resort)
    """

    # Network-related keywords (highest priority after explicit signal mentions)
    NETWORK_KEYWORDS = [
        "shared device", "shared ip", "shared devices", "shared ips",
        "linked account", "linked accounts", "linked network",
        "network", "cluster", "connection", "connected to"
    ]

    # Account-related keywords (lower priority than network)
    ACCOUNT_KEYWORDS = [
        "account", "kyc", "cdd", "customer", "verification",
        "onboarding", "identity", "new account"
    ]

    # Transaction-related keywords
    TRANSACTION_KEYWORDS = [
        "trading", "frequency", "velocity", "burst", "volume",
        "withdrawal", "transaction"
    ]

    def classify(
        self,
        text: str,
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factor_name: Optional[str] = None,
        has_graph_evidence: bool = False
    ) -> FindingType:
        """
        Classify a finding into its type with strict priority rules.

        Priority order:
        1. Explicit signal score mentions (highest priority)
        2. NETWORK/GRAPH keywords (highest for network-related terms)
        3. Factor-based classification
        4. Text-based keyword matching
        5. Score-based classification (LAST resort, only if no text clues)

        Args:
            text: Finding text content
            ml_score: ML signal score if present
            rule_score: Rule signal score if present
            graph_score: Graph signal score if present
            factor_name: Risk factor name
            has_graph_evidence: Whether graph evidence exists

        Returns:
            FindingType enum value
        """
        text_lower = text.lower()

        # Priority 1: Explicit signal score mentions (highest priority)
        if "ml signal" in text_lower or "lightgbm" in text_lower or "ml score" in text_lower:
            return FindingType.ML_SIGNAL
        if "rule signal" in text_lower or "rule engine" in text_lower:
            return FindingType.RULE_SIGNAL
        if "graph signal" in text_lower or "network signal" in text_lower:
            return FindingType.GRAPH_SIGNAL

        # Priority 1.5: NETWORK/GRAPH keywords (BEFORE generic "account")
        # This prevents "Linked Account Network" → ACCOUNT_PROFILE
        if any(keyword in text_lower for keyword in self.NETWORK_KEYWORDS):
            return FindingType.GRAPH_SIGNAL

        # Priority 2: Factor-based classification (HIGH priority)
        # Factor names provide the most specific classification
        if factor_name:
            factor_lower = factor_name.lower()

            # Network-related factors (check FIRST)
            if any(word in factor_lower for word in [
                "device", "ip", "shared", "connection", "linked", "cluster", "network"
            ]):
                return FindingType.GRAPH_SIGNAL

            # Account-related factors (check AFTER network)
            if any(word in factor_lower for word in [
                "account", "kyc", "age", "customer", "onboarding", "identity"
            ]):
                return FindingType.ACCOUNT_PROFILE

            # Transaction/behavior factors
            if any(word in factor_lower for word in [
                "trading", "frequency", "velocity", "burst", "volume",
                "withdrawal", "transaction"
            ]):
                return FindingType.TRANSACTION_BEHAVIOR

        # Priority 3: Text-based keyword matching (MEDIUM priority)
        # Check for explicit keyword patterns in the finding text
        if any(keyword in text_lower for keyword in self.TRANSACTION_KEYWORDS):
            return FindingType.TRANSACTION_BEHAVIOR
        if any(keyword in text_lower for keyword in self.ACCOUNT_KEYWORDS):
            return FindingType.ACCOUNT_PROFILE

        # Priority 4: Evidence-based classification
        if has_graph_evidence and any(word in text_lower for word in [
            "connected", "shared", "linked"
        ]):
            return FindingType.GRAPH_SIGNAL

        # Priority 5: Score-based classification (LOWEST priority - fallback only)
        # Only use scores if no text/factor clues available
        if graph_score and graph_score > 0:
            return FindingType.GRAPH_SIGNAL
        if ml_score and ml_score > 0:
            return FindingType.ML_SIGNAL
        if rule_score and rule_score > 0:
            return FindingType.RULE_SIGNAL

        return FindingType.UNKNOWN


class CitationRetrievalService:
    """
    Service for retrieving citations with strict domain enforcement.

    Flow:
    1. Classify each finding into its type
    2. Get allowed policy scope from CitationPolicyRouter
    3. RAG retrieval within allowed scope ONLY
    4. Validate each citation for relevance
    5. Assign sequential IDs
    6. Ensure every finding has at least one citation
    """

    def __init__(
        self,
        router: Optional[CitationPolicyRouter] = None,
        rag_service: Optional[PolicyRAGService] = None
    ):
        """
        Initialize citation retrieval service.

        Args:
            router: CitationPolicyRouter instance (creates singleton if None)
            rag_service: PolicyRAGService instance (creates new if None)
        """
        self.router = router or get_citation_policy_router()
        self.rag = rag_service or PolicyRAGService()
        self.classifier = FindingClassifier()

    def retrieve_citations(
        self,
        key_findings: List[str],
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factors: List[dict] = None,
        has_graph_evidence: bool = False,
        audience: str = "investigator",
        max_citations: int = 5
    ) -> RetrievalResult:
        """
        Retrieve citations for findings with strict domain enforcement.

        Args:
            key_findings: List of finding texts
            ml_score: ML signal score
            rule_score: Rule signal score
            graph_score: Graph signal score
            factors: Risk factor list
            has_graph_evidence: Whether graph evidence exists
            audience: Audience mode for quote redaction
            max_citations: Maximum citations to return (default: 5)

        Returns:
            RetrievalResult with citations and mappings
        """
        # Step 1: Classify all findings
        classified_findings = []
        for finding_text in key_findings:
            # Extract factor name if applicable
            factor_name = None
            if factors:
                for factor in factors:
                    if factor.get("factor_name", "").lower() in finding_text.lower():
                        factor_name = factor.get("factor_name")
                        break

            finding_type = self.classifier.classify(
                text=finding_text,
                ml_score=ml_score,
                rule_score=rule_score,
                graph_score=graph_score,
                factor_name=factor_name,
                has_graph_evidence=has_graph_evidence
            )

            classified_findings.append(FindingWithCitation(
                finding_text=finding_text,
                finding_type=finding_type
            ))

        # Step 2: Retrieve one best citation per finding (within allowed scope)
        finding_citations = {}  # finding_text -> Citation
        for finding in classified_findings:
            citation = self._retrieve_best_citation(
                finding=finding,
                audience=audience
            )
            if citation:
                finding_citations[finding.finding_text] = citation
            else:
                logger.warning(
                    f"No citation retrieved for finding: '{finding.finding_text[:50]}...' "
                    f"(type: {finding.finding_type.value})"
                )

        # Step 3: Deduplicate citations by chunk_id
        unique_citations = self._deduplicate_citations(finding_citations)

        # Step 4: Assign sequential IDs and build finding-to-IDs mapping
        citations, finding_to_ids = self._build_final_citations(
            unique_citations=unique_citations,
            finding_citations=finding_citations,
            max_citations=max_citations
        )

        # Step 5: Ensure coverage (every finding has at least one citation)
        finding_to_ids = self._ensure_coverage(
            key_findings=key_findings,
            finding_to_ids=finding_to_ids,
            citations=citations
        )

        # Step 6: Build result
        findings_with_citations = sum(1 for ids in finding_to_ids.values() if ids)

        return RetrievalResult(
            citations=citations,
            finding_to_citations=finding_to_ids,
            total_findings=len(key_findings),
            findings_with_citations=findings_with_citations,
            is_valid=(findings_with_citations == len(key_findings))
        )

    def _retrieve_best_citation(
        self,
        finding: FindingWithCitation,
        audience: str
    ) -> Optional[Citation]:
        """
        Retrieve the ONE best citation for a finding within allowed scope.

        Args:
            finding: FindingWithCitation with type
            audience: Audience mode

        Returns:
            Citation object or None
        """
        finding_type = finding.finding_type

        # Get allowed scope from router
        scope = self.router.get_allowed_scope(finding_type)

        # If no allowed documents, cannot retrieve
        if not scope.allowed_docs:
            logger.debug(
                f"No allowed documents for finding type: {finding_type.value}"
            )
            return None

        # Build search query
        query = " ".join(scope.search_terms[:3])  # Use top 3 terms

        try:
            # RAG retrieval with ALLOWED docs constraint
            chunks = self.rag.search(
                query=query,
                top_k=5,
                allowed_docs=list(scope.allowed_docs)
            )

            if not chunks:
                logger.debug(
                    f"No chunks found for query '{query}' with allowed docs {scope.allowed_docs}"
                )
                return None

            # Find the best chunk that passes validation
            for chunk in chunks:
                # Validate citation relevance
                is_valid, reason = self.router.validate_citation_relevance(
                    finding_type=finding_type,
                    doc_name=chunk.doc,
                    section=chunk.section,
                    quote=chunk.text
                )

                if is_valid:
                    # Sanitize quote based on audience
                    quote = chunk.text[:400].strip()
                    if audience == "business":
                        quote = "[REDACTED]"
                    else:
                        quote = sanitize_policy_quote(quote)

                    return Citation(
                        id=0,  # Will be assigned later
                        doc=chunk.doc,
                        section=chunk.section,
                        quote=quote,
                        chunk_id=chunk.chunk_id,
                        finding_type=finding_type.value
                    )
                else:
                    logger.debug(
                        f"Chunk rejected for '{finding.finding_text[:30]}...': {reason}"
                    )

            # No valid chunk found
            logger.warning(
                f"No valid citation found for finding '{finding.finding_text[:50]}...' "
                f"after validation"
            )
            return None

        except Exception as e:
            logger.warning(
                f"RAG retrieval failed for '{finding.finding_text[:50]}...': {e}"
            )
            return None

    def _deduplicate_citations(
        self,
        finding_citations: Dict[str, Citation]
    ) -> Dict[str, Citation]:
        """
        Deduplicate citations by chunk_id.

        If multiple findings use the same chunk, keep only one citation.
        """
        unique = {}
        seen_chunks = set()

        for finding_text, citation in finding_citations.items():
            if citation.chunk_id not in seen_chunks:
                unique[citation.chunk_id] = citation
                seen_chunks.add(citation.chunk_id)

        return unique

    def _build_final_citations(
        self,
        unique_citations: Dict[str, Citation],
        finding_citations: Dict[str, Citation],
        max_citations: int
    ) -> Tuple[List[Citation], Dict[str, List[int]]]:
        """
        Build final citation list with sequential IDs.

        Returns:
            Tuple of (citations list, finding_to_ids dict)
        """
        # Get the most important citations up to max_citations
        citation_list = list(unique_citations.values())[:max_citations]

        # Assign sequential IDs
        chunk_to_seq = {}
        final_citations = []
        for idx, citation in enumerate(citation_list, start=1):
            citation.id = idx
            final_citations.append(citation)
            chunk_to_seq[citation.chunk_id] = idx

        # Build finding_to_ids mapping
        finding_to_ids = {}
        for finding_text, citation in finding_citations.items():
            if citation.chunk_id in chunk_to_seq:
                finding_to_ids[finding_text] = [chunk_to_seq[citation.chunk_id]]
            else:
                # Citation was filtered out
                finding_to_ids[finding_text] = []

        return final_citations, finding_to_ids

    def _ensure_coverage(
        self,
        key_findings: List[str],
        finding_to_ids: Dict[str, List[int]],
        citations: List[Citation]
    ) -> Dict[str, List[int]]:
        """
        Ensure every finding has at least one citation.

        If a finding has no citations, share the most generic citation.
        """
        # Find findings without citations
        findings_without = [
            f for f in key_findings
            if not finding_to_ids.get(f)
        ]

        if not findings_without:
            return finding_to_ids

        if not citations:
            logger.warning("No citations available to share with findings without citations")
            return finding_to_ids

        # Share the most commonly used citation (or first one)
        shared_citation = citations[0]

        for finding in findings_without:
            finding_to_ids[finding] = [shared_citation.id]
            logger.debug(
                f"Shared citation {shared_citation.id} with finding '{finding[:50]}...'"
            )

        return finding_to_ids


def create_citation_retrieval_service(
    router: Optional[CitationPolicyRouter] = None,
    rag_service: Optional[PolicyRAGService] = None
) -> CitationRetrievalService:
    """
    Factory function to create a CitationRetrievalService instance.

    Args:
        router: Optional CitationPolicyRouter instance
        rag_service: Optional PolicyRAGService instance

    Returns:
        New CitationRetrievalService instance
    """
    return CitationRetrievalService(router=router, rag_service=rag_service)
