"""
Simple Citation Service

Redesigned citation generation with focus on investigator UX:
- ONE primary citation per finding
- Citations built ONLY from marks used in text
- Domain-specific RAG queries
- Metadata chunks filtered out

Pipeline:
Finding -> classify domain -> RAG retrieve ONE best citation -> attach mark -> build citations[] from used marks
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict
import re
import logging

from app.services.policy_rag_service import PolicyRAGService
from app.services.llm_service import sanitize_policy_quote

logger = logging.getLogger(__name__)


class FindingDomain(Enum):
    """Finding domains for citation matching."""
    ACCOUNT_PROFILE = "account_profile"      # New account, account age, KYC/CDD
    NETWORK = "network"                      # Shared devices, shared IPs, clusters
    TRANSACTION = "transaction"              # Trading frequency, volume, velocity
    ML_ANOMALY = "ml_anomaly"               # ML signals, pattern detection
    RULE_SIGNAL = "rule_signal"             # Rule engine hits
    UNKNOWN = "unknown"


@dataclass
class FindingWithCitation:
    """A finding with its attached citation."""
    finding_text: str
    citation_id: int  # Assigned after all findings are processed


@dataclass
class Citation:
    """A citation with all metadata."""
    id: int
    doc: str
    section: str
    quote: str
    chunk_id: str


class SimpleCitationService:
    """
    Simple citation service that generates ONE primary citation per finding.

    Domain mapping:
    - account_profile -> KYC_CDD_Requirements.md
    - network -> AML_Suspicious_Indicators.md (network section)
    - transaction -> AML_Suspicious_Indicators.md (transaction section)
    - ml_anomaly -> Risk_Scoring_Explainability_Guide.md
    - rule_signal -> AML_Suspicious_Indicators.md
    """

    # Domain to policy mapping
    DOMAIN_POLICIES = {
        FindingDomain.ACCOUNT_PROFILE: ["KYC_CDD_Requirements.md"],
        FindingDomain.NETWORK: ["AML_Suspicious_Indicators.md"],
        FindingDomain.TRANSACTION: ["AML_Suspicious_Indicators.md"],
        FindingDomain.ML_ANOMALY: ["AML_Suspicious_Indicators.md"],  # Fallback - use general AML policy
        FindingDomain.RULE_SIGNAL: ["AML_Suspicious_Indicators.md"],
    }

    # Domain-specific search terms for RAG
    DOMAIN_SEARCH_TERMS = {
        FindingDomain.ACCOUNT_PROFILE: [
            "account", "kyc", "cdd", "new account", "enhanced", "review"
        ],
        FindingDomain.NETWORK: [
            "shared device", "cluster", "risky", "linked"
        ],
        FindingDomain.TRANSACTION: [
            "velocity", "transfers", "high-velocity", "trading"
        ],
        FindingDomain.ML_ANOMALY: [
            "graph", "pattern", "signals"
        ],
        FindingDomain.RULE_SIGNAL: [
            "suspicious", "indicators", "activity"
        ],
    }

    def __init__(self, rag_service: Optional[PolicyRAGService] = None):
        """Initialize simple citation service."""
        self.rag = rag_service or PolicyRAGService()

    def classify_finding_domain(
        self,
        finding_text: str,
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factor_name: Optional[str] = None
    ) -> FindingDomain:
        """
        Classify a finding into its domain.

        Priority order:
        1. Factor-based classification (highest priority)
        2. Text-based keyword matching
        3. Score-based classification

        Args:
            finding_text: Finding text content
            ml_score: ML signal score
            rule_score: Rule signal score
            graph_score: Graph signal score
            factor_name: Risk factor name

        Returns:
            FindingDomain enum value
        """
        text_lower = finding_text.lower()

        # Priority 1: Factor-based classification
        if factor_name:
            factor_lower = factor_name.lower()

            # Account-related factors
            if any(word in factor_lower for word in [
                "account", "kyc", "age", "customer", "onboarding", "identity"
            ]):
                return FindingDomain.ACCOUNT_PROFILE

            # Network-related factors
            if any(word in factor_lower for word in [
                "device", "ip", "shared", "connection", "linked", "cluster"
            ]):
                return FindingDomain.NETWORK

            # Transaction/behavior factors
            if any(word in factor_lower for word in [
                "trading", "frequency", "velocity", "burst", "volume",
                "withdrawal", "transaction"
            ]):
                return FindingDomain.TRANSACTION

        # Priority 2: Graph evidence + network terms
        if graph_score and graph_score > 0:
            if any(word in text_lower for word in ["connected", "shared", "linked", "account"]):
                return FindingDomain.NETWORK

        # Priority 3: Text-based keyword matching
        if any(word in text_lower for word in ["shared device", "shared ip", "shared devices", "shared ips"]):
            return FindingDomain.NETWORK
        if any(word in text_lower for word in ["connected to", "linked account", "network"]):
            return FindingDomain.NETWORK
        if any(word in text_lower for word in ["trading", "frequency", "velocity", "volume"]):
            return FindingDomain.TRANSACTION
        if any(word in text_lower for word in ["new account", "account age", "kyc", "cdd"]):
            return FindingDomain.ACCOUNT_PROFILE
        if "ml signal" in text_lower or "lightgbm" in text_lower:
            return FindingDomain.ML_ANOMALY
        if "rule signal" in text_lower or "rule engine" in text_lower:
            return FindingDomain.RULE_SIGNAL

        # Priority 4: Score-based classification (last resort)
        if ml_score and ml_score > 0:
            return FindingDomain.ML_ANOMALY
        if rule_score and rule_score > 0:
            return FindingDomain.RULE_SIGNAL
        if graph_score and graph_score > 0:
            return FindingDomain.NETWORK

        return FindingDomain.UNKNOWN

    def retrieve_best_citation(
        self,
        finding_text: str,
        domain: FindingDomain,
        audience: str = "investigator"
    ) -> Optional[Citation]:
        """
        Retrieve the ONE best citation for a finding.

        Args:
            finding_text: Finding text content
            domain: Classified finding domain
            audience: Audience mode for quote redaction

        Returns:
            Citation object or None if no suitable citation found
        """

        if domain == FindingDomain.UNKNOWN:
            logger.warning(f"Cannot retrieve citation for unknown domain: '{finding_text[:50]}...'")
            return None

        # Get allowed policies for this domain
        allowed_policies = self.DOMAIN_POLICIES.get(domain, [])
        if not allowed_policies:
            logger.warning(f"No policies defined for domain: {domain.value}")
            return None

        # Get search terms for this domain
        search_terms = self.DOMAIN_SEARCH_TERMS.get(domain, [])
        if not search_terms:
            logger.warning(f"No search terms for domain: {domain.value}")
            return None

        # Build RAG query
        query = " ".join(search_terms[:3])  # Use top 3 terms

        try:
            # Retrieve candidates from allowed policies ONLY
            chunks = self.rag.search(query, top_k=5, allowed_docs=allowed_policies)

            if not chunks:
                # Fallback: try broader search across all documents
                chunks = self.rag.search(query, top_k=5)
                return None

            # Select best chunk by keyword match with finding text
            best_chunk = self._select_best_chunk(finding_text, chunks)

            logger.info(f"Best chunk for '{finding_text[:40]}...': {best_chunk.doc if best_chunk else 'None'}")

            if not best_chunk:
                return None

            # Sanitize quote based on audience
            quote = best_chunk.text[:400].strip()
            if audience == "business":
                quote = "[REDACTED]"
            else:
                quote = sanitize_policy_quote(quote)

            return Citation(
                id=0,  # Will be assigned later
                doc=best_chunk.doc,
                section=best_chunk.section,
                quote=quote,
                chunk_id=best_chunk.chunk_id
            )

        except Exception as e:
            logger.warning(f"RAG retrieval failed for '{finding_text[:50]}...': {e}")
            return None

    def _select_best_chunk(
        self,
        finding_text: str,
        chunks: List
    ) -> Optional:
        """
        Select the best chunk from RAG results.

        Since RAG already ranks chunks by relevance using domain-specific search terms,
        we simply return the first (highest-scored) chunk.

        Args:
            finding_text: Finding text content (not used, RAG already did the matching)
            chunks: List of PolicyChunk from RAG (already ranked by relevance)

        Returns:
            Best PolicyChunk or None
        """
        if not chunks:
            return None

        # RAG already returns chunks ranked by relevance score
        # Just return the first one (highest RAG score)
        return chunks[0]

    def _tokenize(self, s: str) -> List[str]:
        """Simple tokenization for keyword matching."""
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", " ", s)
        return [t for t in s.split() if len(t) >= 3]

    def generate_citations_for_findings(
        self,
        key_findings: List[str],
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factors: List[dict] = None,
        has_graph_evidence: bool = False,
        audience: str = "investigator"
    ) -> tuple[List[Dict], Dict[str, int]]:
        """
        Generate citations for findings.

        Args:
            key_findings: List of finding texts
            ml_score: ML signal score
            rule_score: Rule signal score
            graph_score: Graph signal score
            factors: Risk factor list
            has_graph_evidence: Whether graph evidence exists
            audience: Audience mode

        Returns:
            Tuple of:
            - List of citation dicts (sequential IDs, only used citations)
            - Dict mapping finding text to citation ID
        """
        findings_with_citations = []
        citations_map = {}  # chunk_id -> citation data
        finding_to_id = {}

        for finding_text in key_findings:
            # Extract factor name if this is a factor-based finding
            factor_name = None
            if factors:
                for factor in factors:
                    if factor.get("factor_name") and factor.get("factor_name").lower() in finding_text.lower():
                        factor_name = factor.get("factor_name")
                        break

            # Classify domain
            domain = self.classify_finding_domain(
                finding_text=finding_text,
                ml_score=ml_score,
                rule_score=rule_score,
                graph_score=graph_score,
                factor_name=factor_name
            )

            # Retrieve ONE best citation
            citation = self.retrieve_best_citation(
                finding_text=finding_text,
                domain=domain,
                audience=audience
            )

            if citation:
                # Use chunk_id as key to deduplicate
                if citation.chunk_id not in citations_map:
                    citations_map[citation.chunk_id] = citation

                finding_to_id[finding_text] = citation.chunk_id
            else:
                # No citation found for this finding
                finding_to_id[finding_text] = None
                logger.warning(f"No citation retrieved for finding: '{finding_text[:50]}...'")

        # Build sequential citations from used chunks only
        final_citations = []
        chunk_to_seq_id = {}

        for seq_id, (chunk_id, citation) in enumerate(citations_map.items(), start=1):
            chunk_to_seq_id[chunk_id] = seq_id
            final_citations.append({
                "id": seq_id,
                "doc": citation.doc,
                "section": citation.section,
                "quote": citation.quote,
                "chunk_id": citation.chunk_id
            })

        # Update finding_to_id with sequential IDs
        finding_to_seq_id = {}
        for finding, chunk_id in finding_to_id.items():
            if chunk_id and chunk_id in chunk_to_seq_id:
                finding_to_seq_id[finding] = chunk_to_seq_id[chunk_id]
            else:
                finding_to_seq_id[finding] = None

        return final_citations, finding_to_seq_id


def create_simple_citation_service(rag_service: Optional[PolicyRAGService] = None) -> SimpleCitationService:
    """Factory function to create a SimpleCitationService instance."""
    return SimpleCitationService(rag_service)
