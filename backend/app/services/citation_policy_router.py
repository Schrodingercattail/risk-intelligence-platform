"""
Citation Policy Router

Enforces strict domain constraints BEFORE RAG retrieval.
Determines which policy documents and sections are allowed for each finding type.

This is the FIRST line of defense against semantically incorrect citations.

Architecture:
    Finding -> FindingType classification -> CitationPolicyRouter -> Allowed scope -> RAG retrieval
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FindingType(Enum):
    """Types of risk findings with strict domain constraints."""
    ML_SIGNAL = "ml_signal"
    RULE_SIGNAL = "rule_signal"
    GRAPH_SIGNAL = "graph_signal"
    ACCOUNT_PROFILE = "account_profile"
    TRANSACTION_BEHAVIOR = "transaction_behavior"
    ACTION_RECOMMENDATION = "action_recommendation"
    UNKNOWN = "unknown"


@dataclass
class PolicyScope:
    """
    Defines the allowed retrieval scope for a finding type.

    Attributes:
        allowed_docs: Set of policy document filenames that can be cited
        allowed_sections: Set of section keywords that are relevant
        forbidden_sections: Set of section keywords that MUST be avoided
        search_terms: Search terms to use for RAG retrieval
    """
    allowed_docs: Set[str]
    allowed_sections: Set[str]
    forbidden_sections: Set[str]
    search_terms: List[str]


class CitationPolicyRouter:
    """
    Routes findings to appropriate policy domains BEFORE RAG retrieval.

    STRICT RULES:
    - ML_SIGNAL → Explainability policies only
    - GRAPH_SIGNAL → Network/Relationship policies only
    - ACCOUNT_PROFILE → KYC/CDD policies only
    - RULE_SIGNAL/TRANSACTION_BEHAVIOR → AML transaction policies only
    - ACTION_RECOMMENDATION → Investigation SOP only
    """

    # Domain definitions for each finding type
    DOMAIN_POLICIES = {
        FindingType.ML_SIGNAL: PolicyScope(
            allowed_docs={
                "Risk_Scoring_Explainability_Guide.md",
            },
            allowed_sections={
                "evidence", "ml", "model", "explanation", "pattern", "anomaly", "detection",
                "explainability", "scoring", "factor"
            },
            forbidden_sections={
                # Never cite transaction sections for ML findings
                "transaction", "velocity", "burst", "suspicious indicators",
                # Never cite KYC sections for ML findings
                "kyc", "cdd", "customer", "verification", "onboarding",
                # Never cite network sections for ML findings
                "network", "cluster", "shared device", "relationship"
            },
            search_terms=["ML pattern detection", "anomaly", "model evidence", "scoring"]
        ),

        FindingType.GRAPH_SIGNAL: PolicyScope(
            allowed_docs={
                "AML_Suspicious_Indicators.md",
            },
            allowed_sections={
                # ONLY network/relationship sections
                "network", "relationship", "cluster", "shared device", "shared ip",
                "linked", "connection", "risky cluster"
            },
            forbidden_sections={
                # Never cite transaction sections for graph findings
                "transaction", "velocity", "burst", "amount", "geolocation",
                # Never cite KYC sections for graph findings
                "kyc", "cdd", "customer", "verification"
            },
            search_terms=["network", "cluster", "shared device", "linked accounts", "relationship"]
        ),

        FindingType.ACCOUNT_PROFILE: PolicyScope(
            allowed_docs={
                "KYC_CDD_Requirements.md",
            },
            allowed_sections={
                "account", "kyc", "cdd", "customer", "verification", "onboarding",
                "identity", "new account", "account age", "enhanced due diligence"
            },
            forbidden_sections={
                # Never cite transaction sections for account profile
                "transaction", "velocity", "trading", "burst",
                # Never cite network sections for account profile
                "network", "cluster", "shared device"
            },
            search_terms=["account", "kyc", "cdd", "verification", "onboarding", "new account"]
        ),

        FindingType.RULE_SIGNAL: PolicyScope(
            allowed_docs={
                "AML_Suspicious_Indicators.md",
            },
            allowed_sections={
                "transaction", "velocity", "burst", "amount", "suspicious",
                "indicator", "behavior", "pattern", "activity"
            },
            forbidden_sections={
                # Never cite KYC sections for rule findings
                "kyc", "cdd", "customer", "verification", "onboarding"
            },
            search_terms=["suspicious indicators", "transaction velocity", "burst patterns"]
        ),

        FindingType.TRANSACTION_BEHAVIOR: PolicyScope(
            allowed_docs={
                "AML_Suspicious_Indicators.md",
            },
            allowed_sections={
                "transaction", "velocity", "burst", "amount", "frequency",
                "trading", "pattern", "behavior"
            },
            forbidden_sections={
                # Never cite KYC sections for transaction findings
                "kyc", "cdd", "customer", "verification",
                # Never cite network sections unless relevant
                "network"  # Transaction findings shouldn't cite network
            },
            search_terms=["transaction velocity", "burst patterns", "trading frequency"]
        ),

        FindingType.ACTION_RECOMMENDATION: PolicyScope(
            allowed_docs={
                "Investigation_and_Action_SOP.md",
            },
            allowed_sections={
                "investigation", "action", "review", "workflow", "sop",
                "procedure", "triage", "escalation"
            },
            forbidden_sections=set(),  # All SOP sections are allowed
            search_terms=["investigation", "action", "review", "procedure"]
        ),

        FindingType.UNKNOWN: PolicyScope(
            allowed_docs=set(),  # No documents allowed for unknown types
            allowed_sections=set(),
            forbidden_sections=set(),
            search_terms=[]
        ),
    }

    def __init__(self):
        """Initialize the citation policy router."""
        pass

    def get_allowed_scope(self, finding_type: FindingType) -> PolicyScope:
        """
        Get the allowed retrieval scope for a finding type.

        Args:
            finding_type: The type of finding

        Returns:
            PolicyScope with allowed docs, sections, and search terms
        """
        return self.DOMAIN_POLICIES.get(finding_type, self.DOMAIN_POLICIES[FindingType.UNKNOWN])

    def is_document_allowed(self, finding_type: FindingType, doc_name: str) -> bool:
        """
        Check if a document is allowed for a finding type.

        Args:
            finding_type: The type of finding
            doc_name: Policy document filename

        Returns:
            True if the document is in the allowed set
        """
        scope = self.get_allowed_scope(finding_type)
        return doc_name in scope.allowed_docs

    def is_section_allowed(self, finding_type: FindingType, doc_name: str, section: str) -> bool:
        """
        Check if a section is allowed for a finding type.

        A section is allowed if:
        1. The document is allowed for this finding type
        2. The section contains at least one allowed_section keyword
        3. The section does NOT contain any forbidden_section keyword

        Args:
            finding_type: The type of finding
            doc_name: Policy document filename
            section: Section path/content

        Returns:
            True if the section can be cited for this finding type
        """
        scope = self.get_allowed_scope(finding_type)

        # Check 1: Document must be allowed
        if doc_name not in scope.allowed_docs:
            logger.debug(
                f"Document '{doc_name}' not allowed for {finding_type.value}"
            )
            return False

        section_lower = section.lower() if section else ""

        # Check 2: Section must contain at least one allowed keyword
        has_allowed = any(keyword in section_lower for keyword in scope.allowed_sections)
        if not has_allowed:
            # Special case: If no specific keywords, allow if no forbidden keywords
            # This handles generic sections like "Scope" or "Introduction"
            pass

        # Check 3: Section must NOT contain forbidden keywords
        has_forbidden = any(keyword in section_lower for keyword in scope.forbidden_sections)
        if has_forbidden:
            logger.debug(
                f"Section '{section}' contains forbidden keywords for {finding_type.value}"
            )
            return False

        return True

    def get_search_terms(self, finding_type: FindingType) -> List[str]:
        """
        Get domain-specific search terms for RAG retrieval.

        Args:
            finding_type: The type of finding

        Returns:
            List of search terms for RAG
        """
        scope = self.get_allowed_scope(finding_type)
        return scope.search_terms

    def get_allowed_docs_list(self, finding_type: FindingType) -> List[str]:
        """
        Get list of allowed document names for RAG retrieval.

        Args:
            finding_type: The type of finding

        Returns:
            List of allowed document filenames
        """
        scope = self.get_allowed_scope(finding_type)
        return list(scope.allowed_docs)

    def validate_citation_relevance(
        self,
        finding_type: FindingType,
        doc_name: str,
        section: str,
        quote: str
    ) -> Tuple[bool, str]:
        """
        Validate that a citation is relevant for a finding type.

        This is the FINAL validation before a citation is returned.

        Args:
            finding_type: The type of finding
            doc_name: Policy document filename
            section: Section path
            quote: Citation quote text

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check document is allowed
        if not self.is_document_allowed(finding_type, doc_name):
            return False, f"Document '{doc_name}' not allowed for {finding_type.value}"

        # Check section is allowed
        if not self.is_section_allowed(finding_type, doc_name, section):
            return False, f"Section '{section}' not allowed for {finding_type.value}"

        # Check section is not too generic
        if self.is_generic_section(section):
            return False, f"Section '{section}' is too generic for citation"

        # Check quote is not metadata
        if self._is_metadata_quote(quote):
            return False, "Quote contains document metadata"

        return True, "Valid"

    def _is_metadata_quote(self, quote: str) -> bool:
        """
        Check if a quote is document metadata (not policy content).

        Args:
            quote: Citation quote text

        Returns:
            True if the quote is metadata
        """
        if not quote:
            return False

        quote_lower = quote.lower()

        # Metadata patterns
        metadata_patterns = [
            "status: demo template",
            "status:demo template",
            "> status:",
            "purpose:",
            "> purpose:",
            "non-authoritative",
            "non authoritative",
            "replace with your organization",
            "before production use",
            "provide citable",
        ]

        for pattern in metadata_patterns:
            if pattern in quote_lower:
                return True

        # Short quotes with metadata keywords
        if len(quote) < 100:
            if any(word in quote_lower for word in ["status", "purpose", "template"]):
                return True

        return False

    def is_generic_section(self, section: str) -> bool:
        """
        Check if a section is too generic to be a useful citation.

        Generic sections like "Scope", "Introduction", "Purpose", "Explanation Objectives"
        are allowed by domain rules but don't provide specific policy guidance.

        Args:
            section: Section path/title

        Returns:
            True if the section is too generic
        """
        if not section:
            return False

        section_lower = section.lower()

        # Generic section patterns
        generic_patterns = [
            " / 1. scope",
            " / 1. introduction",
            " / 1. purpose",
            "explanation objectives",
            " / about",
            " / overview",
        ]

        for pattern in generic_patterns:
            if pattern in section_lower:
                return True

        return False


# Singleton instance
_policy_router_instance = None


def get_citation_policy_router() -> CitationPolicyRouter:
    """Get the singleton CitationPolicyRouter instance."""
    global _policy_router_instance
    if _policy_router_instance is None:
        _policy_router_instance = CitationPolicyRouter()
    return _policy_router_instance


def create_citation_policy_router() -> CitationPolicyRouter:
    """Factory function to create a new CitationPolicyRouter instance."""
    return CitationPolicyRouter()
