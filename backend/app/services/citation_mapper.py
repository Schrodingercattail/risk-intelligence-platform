"""
Domain-Aware Citation Mapping Service

Maps risk findings to appropriate policy citations with STRICT domain constraints.
Ensures citation relevance by only retrieving candidates from matching policy domains.

Principles:
- ACCOUNT_PROFILE findings ONLY cite KYC/CDD/onboarding policies
- GRAPH_SIGNAL findings ONLY cite network/relationship policies
- RULE_SIGNAL findings ONLY cite AML/transaction behavior policies
- ML_SIGNAL findings ONLY cite model/anomaly detection policies
- TRANSACTION_BEHAVIOR findings ONLY cite AML/transaction monitoring policies
- ACTION_RECOMMENDATION findings ONLY cite investigation SOP policies

Cross-domain citations are NEVER allowed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class FindingType(Enum):
    """Types of risk findings with strict domain constraints."""
    ACCOUNT_PROFILE = "account_profile"
    GRAPH_SIGNAL = "graph_signal"
    RULE_SIGNAL = "rule_signal"
    ML_SIGNAL = "ml_signal"
    TRANSACTION_BEHAVIOR = "transaction_behavior"
    ACTION_RECOMMENDATION = "action_recommendation"
    NETWORK_BEHAVIOR = "network_behavior"
    UNKNOWN = "unknown"


@dataclass
class CitationQuery:
    """A targeted query for policy citation retrieval."""
    query: str
    finding_type: FindingType
    top_k: int = 2  # Default: 2 citations per finding
    allowed_domains: List[str] = None  # Enforced domain filter

    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = []


@dataclass
class FindingMetadata:
    """Structured metadata for a finding."""
    finding_text: str
    finding_type: FindingType
    evidence_source: str
    citation_domain: List[str]


class DomainConstraints:
    """
    Strict domain constraints for each finding type.

    Uses SECTION-LEVEL validation for multi-domain documents.
    Cross-domain citations are NEVER allowed.
    """

    # EXACT policy document types allowed for each finding type
    # This uses the actual policy document filenames/patterns
    ALLOWED_POLICY_TYPES = {
        FindingType.ACCOUNT_PROFILE: [
            "KYC_CDD_Requirements.md",
            "Customer_Identification_Policy.md",
        ],
        FindingType.GRAPH_SIGNAL: [
            "AML_Suspicious_Indicators.md",  # ONLY section 5: Network/Relationship
            "Network_Relationship_Policy.md",
        ],
        FindingType.RULE_SIGNAL: [
            "AML_Suspicious_Indicators.md",  # Sections 2-4: Transaction/Behavior
            "Transaction_Monitoring_Policy.md",
        ],
        FindingType.ML_SIGNAL: [
            "Risk_Scoring_Explainability_Guide.md",  # ML methodology
        ],
        FindingType.TRANSACTION_BEHAVIOR: [
            "AML_Suspicious_Indicators.md",  # Sections 2-4: Transaction/Behavior
            "Transaction_Monitoring_Policy.md",
        ],
        FindingType.ACTION_RECOMMENDATION: [
            "Investigation_and_Action_SOP.md",
        ],
        FindingType.NETWORK_BEHAVIOR: [
            "AML_Suspicious_Indicators.md",  # Sections 2-4: Transaction behavior
        ],
    }

    # SECTION-LEVEL domain constraints for multi-domain documents
    # Each entry: (doc_name, section_pattern) -> allowed_finding_types
    SECTION_DOMAIN_CONSTRAINTS = {
        # AML_Suspicious_Indicators.md is multi-domain
        ("AML_Suspicious_Indicators.md", "transaction"): {
            FindingType.RULE_SIGNAL,
            FindingType.TRANSACTION_BEHAVIOR,
            FindingType.NETWORK_BEHAVIOR,
        },
        ("AML_Suspicious_Indicators.md", "velocity"): {
            FindingType.RULE_SIGNAL,
            FindingType.TRANSACTION_BEHAVIOR,
            FindingType.NETWORK_BEHAVIOR,
        },
        ("AML_Suspicious_Indicators.md", "burst"): {
            FindingType.RULE_SIGNAL,
            FindingType.TRANSACTION_BEHAVIOR,
            FindingType.NETWORK_BEHAVIOR,
        },
        ("AML_Suspicious_Indicators.md", "amount"): {
            FindingType.RULE_SIGNAL,
            FindingType.TRANSACTION_BEHAVIOR,
            FindingType.NETWORK_BEHAVIOR,
        },
        ("AML_Suspicious_Indicators.md", "geolocation"): {
            FindingType.RULE_SIGNAL,
            FindingType.TRANSACTION_BEHAVIOR,
            FindingType.NETWORK_BEHAVIOR,
        },
        ("AML_Suspicious_Indicators.md", "network"): {
            FindingType.GRAPH_SIGNAL,
            FindingType.RULE_SIGNAL,  # If rule is network-related
        },
        ("AML_Suspicious_Indicators.md", "relationship"): {
            FindingType.GRAPH_SIGNAL,
            FindingType.RULE_SIGNAL,  # If rule is network-related
        },
        ("AML_Suspicious_Indicators.md", "cluster"): {
            FindingType.GRAPH_SIGNAL,
        },
        ("AML_Suspicious_Indicators.md", "shared"): {
            FindingType.GRAPH_SIGNAL,
        },
        ("AML_Suspicious_Indicators.md", "linked"): {
            FindingType.GRAPH_SIGNAL,
        },

        # Risk_Scoring_Explainability_Guide.md is ML domain
        ("Risk_Scoring_Explainability_Guide.md", "evidence"): {
            FindingType.ML_SIGNAL,
            FindingType.RULE_SIGNAL,
        },
        ("Risk_Scoring_Explainability_Guide.md", "ml"): {
            FindingType.ML_SIGNAL,
        },
        ("Risk_Scoring_Explainability_Guide.md", "explanation"): {
            FindingType.ML_SIGNAL,
        },

        # KYC_CDD_Requirements.md is account profile domain
        ("KYC_CDD_Requirements.md", "kyc"): {
            FindingType.ACCOUNT_PROFILE,
        },
        ("KYC_CDD_Requirements.md", "cdd"): {
            FindingType.ACCOUNT_PROFILE,
        },
        ("KYC_CDD_Requirements.md", "customer"): {
            FindingType.ACCOUNT_PROFILE,
        },
        ("KYC_CDD_Requirements.md", "verification"): {
            FindingType.ACCOUNT_PROFILE,
        },
        ("KYC_CDD_Requirements.md", "identity"): {
            FindingType.ACCOUNT_PROFILE,
        },
        ("KYC_CDD_Requirements.md", "onboarding"): {
            FindingType.ACCOUNT_PROFILE,
        },

        # Investigation_and_Action_SOP.md is action domain
        ("Investigation_and_Action_SOP.md", "investigation"): {
            FindingType.ACTION_RECOMMENDATION,
            FindingType.ML_SIGNAL,  # As fallback
            FindingType.GRAPH_SIGNAL,  # As fallback
            FindingType.RULE_SIGNAL,  # As fallback
            FindingType.ACCOUNT_PROFILE,  # As fallback
        },
        ("Investigation_and_Action_SOP.md", "sop"): {
            FindingType.ACTION_RECOMMENDATION,
        },
        ("Investigation_and_Action_SOP.md", "action"): {
            FindingType.ACTION_RECOMMENDATION,
        },
    }

    # Fallback: If no exact match, use section-based constraints
    # Section keywords that define policy document content
    SECTION_DOMAINS = {
        "kyc": [FindingType.ACCOUNT_PROFILE],
        "cdd": [FindingType.ACCOUNT_PROFILE],
        "onboarding": [FindingType.ACCOUNT_PROFILE],
        "network": [FindingType.GRAPH_SIGNAL],
        "cluster": [FindingType.GRAPH_SIGNAL],
        "aml": [FindingType.RULE_SIGNAL, FindingType.TRANSACTION_BEHAVIOR],
        "transaction": [FindingType.TRANSACTION_BEHAVIOR],
        "trading": [FindingType.TRANSACTION_BEHAVIOR],
        "investigation": [FindingType.ACTION_RECOMMENDATION],
        "sop": [FindingType.ACTION_RECOMMENDATION],
        "procedure": [FindingType.ACTION_RECOMMENDATION],
    }

    # Keywords that trigger specific finding types
    TYPE_KEYWORDS = {
        FindingType.ACCOUNT_PROFILE: [
            "new account", "account age", "kyc", "cdd", "onboarding",
            "identity", "verification", "customer", "account age"
        ],
        FindingType.GRAPH_SIGNAL: [
            "shared device", "shared ip", "shared devices", "shared ips",
            "network", "cluster", "connected to", "linked account",
            "relationship", "connection"
        ],
        FindingType.RULE_SIGNAL: [
            "rule engine", "rule signal", "suspicious", "indicators"
        ],
        FindingType.ML_SIGNAL: [
            "ml signal", "ml score", "lightgbm", "model score",
            "anomaly", "prediction"
        ],
        FindingType.TRANSACTION_BEHAVIOR: [
            "trading", "frequency", "velocity", "burst", "volume",
            "transaction", "withdrawal"
        ],
        FindingType.ACTION_RECOMMENDATION: [
            "action", "recommend", "review", "investigate", "procedure"
        ],
    }

    @classmethod
    def get_allowed_policy_types(cls, finding_type: FindingType) -> List[str]:
        """Get allowed policy document types for a finding type."""
        return cls.ALLOWED_POLICY_TYPES.get(finding_type, [])

    @classmethod
    def is_domain_allowed(cls, finding_type: FindingType, policy_doc: str, section: str = "") -> bool:
        """
        Check if a policy document AND section is allowed for a finding type.

        Uses SECTION-LEVEL validation for multi-domain documents.
        Cross-domain citations are NEVER allowed.

        Args:
            finding_type: The type of finding
            policy_doc: Policy document name
            section: Policy section path/content (required for multi-domain docs)

        Returns:
            True if the policy + section is allowed for this finding type
        """
        # First check: exact document name match (for single-domain docs)
        allowed_docs = cls.get_allowed_policy_types(finding_type)
        if policy_doc in allowed_docs:
            # For multi-domain docs, must check section
            if policy_doc == "AML_Suspicious_Indicators.md":
                # MUST validate section for AML doc
                return cls._check_section_domain(finding_type, policy_doc, section)
            # For single-domain docs, document-level match is sufficient
            return True

        # Second check: SECTION-LEVEL validation (primary method for multi-domain docs)
        if section:
            return cls._check_section_domain(finding_type, policy_doc, section)

        # Default: not allowed
        return False

    @classmethod
    def _check_section_domain(cls, finding_type: FindingType, policy_doc: str, section: str) -> bool:
        """
        Check if a section within a document is allowed for a finding type.

        This is the CORE validation method for preventing cross-domain citations.

        Args:
            finding_type: The type of finding
            policy_doc: Policy document name
            section: Policy section path/content

        Returns:
            True if the section is allowed for this finding type
        """
        section_lower = section.lower() if section else ""

        # Check SECTION_DOMAIN_CONSTRAINTS for exact (doc, section_pattern) matches
        for (doc_pattern, section_pattern), allowed_types in cls.SECTION_DOMAIN_CONSTRAINTS.items():
            # Check if doc matches
            if doc_pattern.lower() in policy_doc.lower():
                # Check if section pattern matches
                if section_pattern in section_lower:
                    # Check if finding type is in allowed types
                    if finding_type in allowed_types:
                        return True
                    else:
                        # Section matched but finding type NOT allowed - FORBIDDEN
                        logger.debug(
                            f"Section '{section_pattern}' in '{policy_doc}' NOT allowed for {finding_type.value}"
                        )
                        return False

        # No specific section constraint found - use legacy SECTION_DOMAINS
        for section_keyword, allowed_types in cls.SECTION_DOMAINS.items():
            if finding_type in allowed_types:
                if section_keyword in section_lower:
                    return True

        # Default: not allowed
        return False


class DomainAwareCitationMapper:
    """
    Domain-aware citation mapper with strict constraints.

    Ensures findings only cite policies from their allowed domains.
    """

    def __init__(self):
        """Initialize domain-aware citation mapper."""
        self.constraints = DomainConstraints()

    def classify_finding(
        self,
        text: str,
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factor_name: Optional[str] = None,
        has_graph_evidence: bool = False
    ) -> FindingType:
        """
        Classify a finding into its type with strict rules.

        Priority order (FIXED):
        1. Explicit signal score mentions (highest priority)
        2. NETWORK/GRAPH keywords (elevated above generic keywords)
        3. Factor-based classification
        4. Evidence-based classification
        5. Score-based classification
        6. Text-based keyword matching (last resort)

        CRITICAL FIX: Network-related terms are checked BEFORE generic "account" keyword
        to prevent "Linked Account Network" from being classified as ACCOUNT_PROFILE.

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

        # Priority 1: Direct signal score mentions (highest priority)
        if "ml signal" in text_lower or "lightgbm" in text_lower or "ml score" in text_lower:
            return FindingType.ML_SIGNAL
        if "rule signal" in text_lower or "rule engine" in text_lower:
            return FindingType.RULE_SIGNAL
        if "graph signal" in text_lower or "network signal" in text_lower:
            return FindingType.GRAPH_SIGNAL

        # Priority 1.5: NETWORK/GRAPH keyword matching (BEFORE generic account)
        # This prevents "Linked Account Network" → ACCOUNT_PROFILE misclassification
        network_keywords = [
            "shared device", "shared ip", "shared devices", "shared ips",
            "linked account", "linked accounts", "linked network",
            "network", "cluster", "connection"
        ]
        if any(keyword in text_lower for keyword in network_keywords):
            return FindingType.GRAPH_SIGNAL

        # Priority 2: Factor-based classification
        if factor_name:
            factor_lower = factor_name.lower()

            # Network-related factors (check FIRST before account)
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

        # Priority 3: Evidence-based classification
        if has_graph_evidence and any(word in text_lower for word in [
            "connected", "shared", "linked", "account"
        ]):
            return FindingType.GRAPH_SIGNAL

        # Priority 4: Score-based classification
        if graph_score and graph_score > 0:
            # Only classify as GRAPH_SIGNAL if the finding mentions network-related terms
            if any(word in text_lower for word in ["connected", "shared", "linked"]):
                return FindingType.GRAPH_SIGNAL

        if ml_score and ml_score > 0:
            return FindingType.ML_SIGNAL

        if rule_score and rule_score > 0:
            return FindingType.RULE_SIGNAL

        # Priority 5: Text-based keyword matching (last resort)
        # Check network keywords again for completeness
        if any(keyword in text_lower for keyword in network_keywords):
            return FindingType.GRAPH_SIGNAL

        for finding_type, keywords in DomainConstraints.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return finding_type

        return FindingType.UNKNOWN

    def get_finding_metadata(
        self,
        text: str,
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factor_name: Optional[str] = None,
        has_graph_evidence: bool = False
    ) -> FindingMetadata:
        """
        Generate structured metadata for a finding.

        Args:
            text: Finding text content
            ml_score: ML signal score if present
            rule_score: Rule signal score if present
            graph_score: Graph signal score if present
            factor_name: Risk factor name
            has_graph_evidence: Whether graph evidence exists

        Returns:
            FindingMetadata with classification and domain information
        """
        finding_type = self.classify_finding(
            text=text,
            ml_score=ml_score,
            rule_score=rule_score,
            graph_score=graph_score,
            factor_name=factor_name,
            has_graph_evidence=has_graph_evidence
        )

        # Get allowed policy document types for this type
        allowed_domains = DomainConstraints.get_allowed_policy_types(finding_type)

        # Determine evidence source
        evidence_source = "unknown"
        if factor_name:
            evidence_source = "factor"
        elif has_graph_evidence:
            evidence_source = "graph"
        elif ml_score and ml_score > 0:
            evidence_source = "ml"
        elif rule_score and rule_score > 0:
            evidence_source = "rule"

        return FindingMetadata(
            finding_text=text,
            finding_type=finding_type,
            evidence_source=evidence_source,
            citation_domain=allowed_domains
        )

    def map_finding_to_query(
        self,
        metadata: FindingMetadata,
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factor_name: Optional[str] = None
    ) -> CitationQuery:
        """
        Generate a domain-constrained citation query for a finding.

        ONLY retrieves citations from allowed domains for the finding type.
        Cross-domain citations are NEVER allowed.

        Args:
            metadata: FindingMetadata with classification and domain info
            ml_score: ML score if present
            rule_score: Rule score if present
            graph_score: Graph score if present
            factor_name: Factor name if present

        Returns:
            CitationQuery with domain-constrained search terms
        """
        # Build query using ONLY allowed domain keywords
        query_parts = []

        # Add finding-specific keywords from allowed domains
        for domain in metadata.citation_domain:
            query_parts.append(domain)

        # Add factor-specific terms if available
        if factor_name:
            factor_terms = factor_name.lower().replace("_", " ")
            query_parts.append(factor_terms)

        # Build query (limit to prevent overly broad searches)
        query = " ".join(query_parts[:5])

        # Create citation query with enforced domain constraints
        return CitationQuery(
            query=query,
            finding_type=metadata.finding_type,
            top_k=2,  # Maximum 2 citations per finding
            allowed_domains=metadata.citation_domain
        )

    def map_findings_to_queries(
        self,
        key_findings: List[str],
        ml_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        graph_score: Optional[float] = None,
        factors: Optional[List[dict]] = None,
        has_graph_evidence: bool = False
    ) -> List[CitationQuery]:
        """
        Map multiple findings to domain-constrained citation queries.

        Args:
            key_findings: List of finding texts
            ml_score: ML signal score
            rule_score: Rule signal score
            graph_score: Graph signal score
            factors: Risk factor list
            has_graph_evidence: Whether graph evidence exists

        Returns:
            List of CitationQuery objects, one per finding
        """
        queries = []

        for finding_text in key_findings:
            # Extract factor name if this is a factor-based finding
            factor_name = None
            if factors:
                for factor in factors:
                    if factor.get("factor_name") and factor.get("factor_name").lower() in finding_text.lower():
                        factor_name = factor.get("factor_name")
                        break

            # Generate finding metadata
            metadata = self.get_finding_metadata(
                text=finding_text,
                ml_score=ml_score,
                rule_score=rule_score,
                graph_score=graph_score,
                factor_name=factor_name,
                has_graph_evidence=has_graph_evidence
            )

            # Generate domain-constrained query
            query = self.map_finding_to_query(
                metadata=metadata,
                ml_score=ml_score,
                rule_score=rule_score,
                graph_score=graph_score,
                factor_name=factor_name
            )

            queries.append(query)

        return queries


def create_domain_aware_citation_mapper() -> DomainAwareCitationMapper:
    """Factory function to create a domain-aware citation mapper."""
    return DomainAwareCitationMapper()
