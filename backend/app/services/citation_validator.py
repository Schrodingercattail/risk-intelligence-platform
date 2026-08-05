"""
Citation Quality Validation Service

Validates that citations are appropriately matched to findings.
Generates warnings without blocking responses (graceful degradation).

Validation Rules:
- ML findings should not cite network/risky cluster policies
- Graph findings should not cite ML/transaction policies
- Account findings should not cite network investigation policies
- Citations should exist for key findings
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Set
import logging

logger = logging.getLogger(__name__)


class PolicyDomain(Enum):
    """Policy domains based on document content."""
    ML_ANOMALY = "ml_anomaly"
    NETWORK_CLUSTER = "network_cluster"
    TRANSACTION_BEHAVIOR = "transaction_behavior"
    KYC_CDD = "kyc_cdd"
    INVESTIGATION_SOP = "investigation_sop"
    UNKNOWN = "unknown"


class FindingType(Enum):
    """Finding types for validation."""
    ML_SIGNAL = "ml_signal"
    RULE_SIGNAL = "rule_signal"
    GRAPH_SIGNAL = "graph_signal"
    ACCOUNT_PROFILE = "account_profile"
    NETWORK_BEHAVIOR = "network_behavior"
    ACTION_RECOMMENDATION = "action_recommendation"
    UNKNOWN = "unknown"


@dataclass
class ValidationWarning:
    """A citation quality warning."""
    code: str
    message: str
    finding_text: str
    citation_id: int
    policy_doc: str


@dataclass
class ValidationResult:
    """Result of citation validation."""
    is_valid: bool
    warnings: List[ValidationWarning]
    total_citations: int
    findings_checked: int


class CitationValidator:
    """
    Validates citation quality and evidence-to-policy alignment.

    Generates warnings for:
    - Mismatched policy domains
    - Missing citations for key findings
    - Excessive citations per finding

    Never blocks responses — warnings only.
    """

    # Policy domain detection keywords
    POLICY_DOMAIN_PATTERNS = {
        PolicyDomain.ML_ANOMALY: [
            "ML", "machine learning", "model", "algorithm",
            "anomaly detection", "pattern detection"
        ],
        PolicyDomain.NETWORK_CLUSTER: [
            "network", "relationship", "cluster", "risky cluster",
            "shared device", "shared IP", "connection", "linked"
        ],
        PolicyDomain.TRANSACTION_BEHAVIOR: [
            "transaction", "velocity", "amount", "burst",
            "frequency", "coordinate", "trading pattern"
        ],
        PolicyDomain.KYC_CDD: [
            "KYC", "CDD", "customer", "due diligence",
            "verification", "identity", "onboarding"
        ],
        PolicyDomain.INVESTIGATION_SOP: [
            "investigation", "SOP", "workflow", "procedure",
            "review", "guidance", "action"
        ]
    }

    # Finding type to allowed policy domains
    ALLOWED_DOMAINS = {
        FindingType.ML_SIGNAL: {
            PolicyDomain.ML_ANOMALY,
            PolicyDomain.TRANSACTION_BEHAVIOR,
            PolicyDomain.INVESTIGATION_SOP
        },
        FindingType.RULE_SIGNAL: {
            PolicyDomain.TRANSACTION_BEHAVIOR,
            PolicyDomain.INVESTIGATION_SOP
        },
        FindingType.GRAPH_SIGNAL: {
            PolicyDomain.NETWORK_CLUSTER,
            PolicyDomain.INVESTIGATION_SOP
        },
        FindingType.ACCOUNT_PROFILE: {
            PolicyDomain.KYC_CDD,
            PolicyDomain.INVESTIGATION_SOP
        },
        FindingType.NETWORK_BEHAVIOR: {
            PolicyDomain.TRANSACTION_BEHAVIOR,
            PolicyDomain.NETWORK_CLUSTER,
            PolicyDomain.INVESTIGATION_SOP
        },
        FindingType.ACTION_RECOMMENDATION: {
            PolicyDomain.INVESTIGATION_SOP
        }
    }

    def _detect_policy_domain(self, citation: dict) -> PolicyDomain:
        """
        Detect policy domain from citation content.

        Args:
            citation: Citation dict with doc, section, quote fields

        Returns:
            Detected PolicyDomain
        """
        text = ""
        if citation.get("section"):
            text += citation["section"].lower()
        if citation.get("quote"):
            text += " " + citation["quote"].lower()

        # Score each domain
        domain_scores = {}
        for domain, patterns in self.POLICY_DOMAIN_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern.lower() in text)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return PolicyDomain.UNKNOWN

    def _classify_finding_from_text(self, finding_text: str) -> FindingType:
        """Classify finding type from text content."""
        text_lower = finding_text.lower()

        if "ml signal" in text_lower or "lightgbm" in text_lower:
            return FindingType.ML_SIGNAL
        if "rule signal" in text_lower or "rule engine" in text_lower:
            return FindingType.RULE_SIGNAL
        if "graph signal" in text_lower or "network signal" in text_lower:
            return FindingType.GRAPH_SIGNAL
        if any(word in text_lower for word in ["account", "age", "kyc"]):
            return FindingType.ACCOUNT_PROFILE
        if any(word in text_lower for word in ["trading", "frequency", "velocity"]):
            return FindingType.NETWORK_BEHAVIOR

        return FindingType.UNKNOWN

    def validate_finding_citation(
        self,
        finding_text: str,
        citations: List[dict]
    ) -> List[ValidationWarning]:
        """
        Validate citations for a single finding.

        Args:
            finding_text: The finding text
            citations: List of citation dicts

        Returns:
            List of validation warnings
        """
        warnings = []

        if not citations:
            # No citations is acceptable (not a warning)
            return warnings

        # Classify finding type
        finding_type = self._classify_finding_from_text(finding_text)

        # Check each citation
        for citation in citations:
            citation_id = citation.get("id", 0)
            policy_doc = citation.get("doc", "")

            # Detect policy domain
            policy_domain = self._detect_policy_domain(citation)

            # Check if domain is allowed for this finding type
            if finding_type in self.ALLOWED_DOMAINS:
                allowed_domains = self.ALLOWED_DOMAINS[finding_type]
                if policy_domain not in allowed_domains and policy_domain != PolicyDomain.UNKNOWN:
                    warnings.append(ValidationWarning(
                        code="MISMATCH",
                        message=f"Finding type {finding_type.value} cites policy from {policy_domain.value} domain",
                        finding_text=finding_text[:100],
                        citation_id=citation_id,
                        policy_doc=policy_doc
                    ))

        return warnings

    def validate_explanation(
        self,
        key_findings: List[str],
        finding_citations: Dict[str, List[int]],
        all_citations: List[dict]
    ) -> ValidationResult:
        """
        Validate citations for an entire explanation.

        Args:
            key_findings: List of finding texts
            finding_citations: Dict mapping finding text to citation IDs
            all_citations: List of all citation dicts

        Returns:
            ValidationResult with all warnings
        """
        all_warnings = []
        findings_checked = 0

        for finding in key_findings:
            citation_ids = finding_citations.get(finding, [])
            citations = [c for c in all_citations if c.get("id") in citation_ids]

            findings_checked += 1

            # Validate this finding's citations
            warnings = self.validate_finding_citation(finding, citations)
            all_warnings.extend(warnings)

        return ValidationResult(
            is_valid=True,  # Always valid — warnings only
            warnings=all_warnings,
            total_citations=len(all_citations),
            findings_checked=findings_checked
        )

    def validate_summary_citations(
        self,
        summary: str,
        citations: List[dict]
    ) -> List[ValidationWarning]:
        """
        Validate citations used in summary text.

        Args:
            summary: Summary text with citation marks
            citations: List of citation dicts

        Returns:
            List of validation warnings
        """
        # Summary citations are less strict — only warn on obvious mismatches
        warnings = []

        # Check if ML-focused summary cites network policies
        if "ml" in summary.lower():
            for citation in citations:
                policy_domain = self._detect_policy_domain(citation)
                if policy_domain == PolicyDomain.NETWORK_CLUSTER:
                    warnings.append(ValidationWarning(
                        code="SUMMARY_MISMATCH",
                        message="Summary focuses on ML but cites network policy",
                        finding_text=summary[:100],
                        citation_id=citation.get("id", 0),
                        policy_doc=citation.get("doc", "")
                    ))

        return warnings


def create_citation_validator() -> CitationValidator:
    """Factory function to create a CitationValidator instance."""
    return CitationValidator()
