"""
Citation Coverage Validation Service

Ensures citation quality and UX consistency:
1. Every returned citation appears at least once in text
2. Every key_finding has at least one citation
3. Summary uses domain-balanced citation selection

Principles:
- No unused citations in API response
- No citation-less findings
- Domain-diverse summary citations
- Graceful handling of findings with no suitable citations
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PolicyDomain(Enum):
    """Policy domains for citation diversity."""
    ML_ANOMALY = "ml_anomaly"
    NETWORK_CLUSTER = "network_cluster"
    TRANSACTION_BEHAVIOR = "transaction_behavior"
    KYC_CDD = "kyc_cdd"
    INVESTIGATION_SOP = "investigation_sop"
    UNKNOWN = "unknown"


@dataclass
class CoverageIssue:
    """A coverage validation issue."""
    code: str
    message: str
    finding_text: Optional[str] = None
    citation_id: Optional[int] = None


@dataclass
class CoverageResult:
    """Result of citation coverage validation."""
    is_valid: bool
    issues: List[CoverageIssue]
    stats: Dict

    # Specific tracking
    unused_citations: Set[int]
    citation_less_findings: List[str]
    finding_to_citations: Dict[str, List[int]]


class CitationCoverageValidator:
    """
    Validates and ensures citation coverage requirements.

    Responsibilities:
    1. Detect unused citations
    2. Detect citation-less findings
    3. Recommend summary citations based on domain diversity
    4. Validate final coverage
    """

    # Domain detection keywords
    DOMAIN_PATTERNS = {
        PolicyDomain.ML_ANOMALY: [
            "ML", "machine learning", "model", "algorithm",
            "anomaly detection", "pattern detection", "scoring"
        ],
        PolicyDomain.NETWORK_CLUSTER: [
            "network", "cluster", "shared device", "shared IP",
            "connection", "linked", "relationship"
        ],
        PolicyDomain.TRANSACTION_BEHAVIOR: [
            "transaction", "velocity", "amount", "burst",
            "frequency", "trading pattern"
        ],
        PolicyDomain.KYC_CDD: [
            "KYC", "CDD", "customer", "due diligence",
            "verification", "account", "age"
        ],
        PolicyDomain.INVESTIGATION_SOP: [
            "investigation", "SOP", "workflow", "procedure",
            "review", "action", "guidance"
        ]
    }

    def __init__(self):
        """Initialize citation coverage validator."""
        self.issues: List[CoverageIssue] = []

    def validate_coverage(
        self,
        summary: str,
        key_findings: List[str],
        recommended_action: str,
        finding_to_citations: Dict[str, List[int]],
        all_citation_ids: Set[int]
    ) -> CoverageResult:
        """
        Validate citation coverage requirements.

        Args:
            summary: Summary text with citation marks
            key_findings: List of finding texts with citation marks
            recommended_action: Recommended action text
            finding_to_citations: Mapping of finding text to citation IDs
            all_citation_ids: All citation IDs in response

        Returns:
            CoverageResult with validation findings
        """
        self.issues = []
        unused_citations: Set[int] = set()
        citation_less_findings: List[str] = []

        # Extract all marks from text
        all_marks = self._extract_all_marks(summary, key_findings, recommended_action)

        # Check 1: Unused citations
        unused = all_citation_ids - all_marks
        if unused:
            unused_citations = unused
            self.issues.append(CoverageIssue(
                code="UNUSED_CITATION",
                message=f"Citations {sorted(unused)} never appear in text",
                citation_id=None
            ))
            logger.warning(f"Unused citations detected: {sorted(unused)}")

        # Check 2: Citation-less findings
        for finding_text in key_findings:
            finding_marks = self._extract_marks_from_text(finding_text)
            if not finding_marks:
                # Check if this finding has citations assigned but not marked
                assigned_ids = finding_to_citations.get(finding_text, [])
                if not assigned_ids:
                    citation_less_findings.append(finding_text)
                    self.issues.append(CoverageIssue(
                        code="CITATION_LESS_FINDING",
                        message=f"Finding has no citations",
                        finding_text=finding_text[:50]
                    ))
                    logger.warning(f"Citation-less finding: '{finding_text[:50]}'")

        # Determine validity
        is_valid = (not unused_citations) and (not citation_less_findings)

        return CoverageResult(
            is_valid=is_valid,
            issues=self.issues,
            stats={
                "total_citations": len(all_citation_ids),
                "total_marks": len(all_marks),
                "unused_count": len(unused_citations),
                "citation_less_count": len(citation_less_findings),
                "coverage_rate": len(all_marks) / len(all_citation_ids) if all_citation_ids else 1.0
            },
            unused_citations=unused_citations,
            citation_less_findings=citation_less_findings,
            finding_to_citations=finding_to_citations
        )

    def select_summary_citations(
        self,
        finding_to_citations: Dict[str, List[int]],
        all_citations: List[Dict],
        top_k: int = 2
    ) -> List[int]:
        """
        Select summary citations using domain-balanced strategy.

        Strategy:
        1. Group citations by domain
        2. Select from different domains for diversity
        3. Within domain, select by frequency (most used first)

        Args:
            finding_to_citations: Mapping of finding to citation IDs
            all_citations: List of all citation dicts
            top_k: Number of citations to select

        Returns:
            List of citation IDs for summary
        """
        if not all_citations:
            return []

        # Detect domain for each citation
        citation_domains: Dict[int, PolicyDomain] = {}
        for citation in all_citations:
            cid = citation.get("id")
            domain = self._detect_domain(citation)
            citation_domains[cid] = domain

        # Count usage frequency
        citation_freq: Dict[int, int] = {}
        for cids in finding_to_citations.values():
            for cid in cids:
                citation_freq[cid] = citation_freq.get(cid, 0) + 1

        # Group citations by domain
        domain_groups: Dict[PolicyDomain, List[int]] = {}
        for cid in citation_freq.keys():
            domain = citation_domains.get(cid, PolicyDomain.UNKNOWN)
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(cid)

        # Sort within each domain by frequency (descending)
        for domain in domain_groups:
            domain_groups[domain].sort(
                key=lambda cid: citation_freq.get(cid, 0),
                reverse=True
            )

        # Select from diverse domains
        selected: List[int] = []
        domain_order = [
            PolicyDomain.ML_ANOMALY,
            PolicyDomain.TRANSACTION_BEHAVIOR,
            PolicyDomain.NETWORK_CLUSTER,
            PolicyDomain.KYC_CDD,
            PolicyDomain.INVESTIGATION_SOP,
            PolicyDomain.UNKNOWN
        ]

        # Round-robin selection from domains
        added_any = True
        round_num = 0
        while len(selected) < top_k and added_any:
            added_any = False
            for domain in domain_order:
                if len(selected) >= top_k:
                    break
                if domain in domain_groups and domain_groups[domain]:
                    # Get next citation from this domain
                    if round_num < len(domain_groups[domain]):
                        cid = domain_groups[domain][round_num]
                        if cid not in selected:
                            selected.append(cid)
                            added_any = True
            round_num += 1

        # If we still don't have enough, fill with most frequent remaining
        if len(selected) < top_k:
            remaining = [
                cid for cid in citation_freq.keys()
                if cid not in selected
            ]
            remaining.sort(key=lambda cid: citation_freq.get(cid, 0), reverse=True)
            for cid in remaining:
                if len(selected) >= top_k:
                    break
                selected.append(cid)

        # Sort for consistent display
        selected.sort()
        return selected

    def _detect_domain(self, citation: Dict) -> PolicyDomain:
        """
        Detect policy domain from citation content.

        Args:
            citation: Citation dict with doc, section, quote

        Returns:
            Detected PolicyDomain
        """
        text = ""
        if citation.get("section"):
            text += citation["section"].lower()
        if citation.get("quote"):
            text += " " + citation["quote"].lower()
        if citation.get("doc"):
            text += " " + citation["doc"].lower()

        # Score each domain
        domain_scores = {}
        for domain, patterns in self.DOMAIN_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern.lower() in text)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return PolicyDomain.UNKNOWN

    def _extract_all_marks(
        self,
        summary: str,
        key_findings: List[str],
        recommended_action: str
    ) -> Set[int]:
        """Extract all citation marks from all text fields."""
        all_marks: Set[int] = set()

        all_marks.update(self._extract_marks_from_text(summary))
        for finding in key_findings:
            all_marks.update(self._extract_marks_from_text(finding))
        all_marks.update(self._extract_marks_from_text(recommended_action))

        return all_marks

    def _extract_marks_from_text(self, text: str) -> Set[int]:
        """Extract citation marks from a single text."""
        if not text:
            return set()
        import re
        marks = re.findall(r'\[(\d+)\]', text)
        return set(int(m) for m in marks)

    def ensure_finding_coverage(
        self,
        key_findings: List[str],
        finding_to_citations: Dict[str, List[int]],
        factors: List[Dict],
        audience: str
    ) -> Dict[str, List[int]]:
        """
        Ensure every finding has at least one citation.

        For findings without citations, attempt RAG retrieval.

        Args:
            key_findings: List of finding texts
            finding_to_citations: Current mapping
            factors: Risk factors for context
            audience: Audience mode

        Returns:
            Updated finding_to_citations
        """
        from app.services.policy_rag_service import PolicyRAGService

        updated = finding_to_citations.copy()
        rag = PolicyRAGService()

        for finding_text in key_findings:
            if not updated.get(finding_text):
                # Finding has no citations - try RAG
                logger.info(f"Finding without citation: '{finding_text[:50]}', attempting RAG")

                # Generate simple query from finding text
                query = self._generate_fallback_query(finding_text, factors)

                if query:
                    try:
                        chunks = rag.search(query, top_k=1)
                        if chunks:
                            chunk = chunks[0]
                            # This would need citation registration - return for now
                            # The caller should handle registration
                            logger.info(f"Found citation for finding: '{finding_text[:50]}'")
                            # Store finding text for later registration
                            updated[finding_text] = ["FALLBACK_PENDING"]
                        else:
                            logger.warning(f"No citations found for: '{finding_text[:50]}'")
                    except Exception as e:
                        logger.warning(f"RAG failed for finding '{finding_text[:30]}': {e}")

        return updated

    def _generate_fallback_query(self, finding_text: str, factors: List[Dict]) -> Optional[str]:
        """Generate fallback RAG query for a finding."""
        # Extract key terms from finding
        text_lower = finding_text.lower()

        # Check for ML-related
        if "ml" in text_lower or "signal" in text_lower:
            return "ML pattern detection anomaly risk scoring"

        # Check for network-related
        if "shared" in text_lower or "connected" in text_lower or "network" in text_lower:
            return "network relationship cluster shared device connection"

        # Check for account-related
        if "account" in text_lower or "new" in text_lower:
            return "account KYC CDD verification due diligence"

        # Check for trading-related
        if "trading" in text_lower or "frequency" in text_lower or "volume" in text_lower:
            return "trading behavior frequency pattern monitoring"

        # Generic query
        return "risk investigation policy"


def create_citation_coverage_validator() -> CitationCoverageValidator:
    """
    Factory function to create a CitationCoverageValidator instance.

    Returns:
        New CitationCoverageValidator instance
    """
    return CitationCoverageValidator()
