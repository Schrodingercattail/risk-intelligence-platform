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


class ClaimRefiner:
    """
    Refines a finding's DOMAIN type into a CLAIM-specific scope.

    A citation must support what the finding actually CLAIMS, not merely share
    a domain. Two findings in the same domain can make different claims with
    different policy support: "High withdrawal frequency" claims a velocity /
    count anomaly (supported by AML 2.1 High-Velocity Transfers), while
    "First withdrawal to new address" claims a FIRST-time / new-destination
    event — which the current policy corpus does NOT address. The latter must
    therefore receive NO citation rather than a velocity citation that does
    not support it.

    Each entry maps claim patterns to:
      - search_terms: claim-specific RAG query (falls back to domain terms)
      - required_section_keywords: at least one must appear in the section for
        the citation to be considered supportive of THIS claim
    """

    CLAIM_RULES = [
        {
            "patterns": ("first withdrawal",),
            "search_terms": ["first withdrawal", "new withdrawal address", "new payee"],
            "required_section_keywords": ["first withdrawal", "new address", "new payee",
                                          "beneficiary"],
        },
        {
            # Coordinated-trading claim: opposite-trade ratio / alternating
            # buy-sell / offsetting positions. The current policy corpus has
            # NO section supporting this semantics (velocity/structuring/
            # fund-movement sections do not cover it), so findings matching
            # this rule stay UNCITED unless a genuinely matching section
            # exists (required keywords would have to appear in it).
            "patterns": ("opposite-trade", "opposite trade", "coordinated trading",
                         "offsetting position", "alternating buy"),
            "search_terms": ["opposite trade", "coordinated trading", "offsetting positions"],
            "required_section_keywords": ["opposite trade", "coordinated trading",
                                          "offsetting position", "alternating buy",
                                          "wash trad"],
        },
        {
            "patterns": ("withdrawal frequency", "withdrawal velocity",
                         "withdrawals in 24h", "withdrawals in the"),
            "search_terms": ["withdrawal frequency", "transfer velocity", "burst"],
            "required_section_keywords": ["velocity", "frequency", "burst", "spike",
                                          "short time window"],
        },
        {
            # Claim: the deterministic rule "New account with high activity"
            # = young account (<7d) AND high TRADING frequency (>50/24h), as a
            # CONJUNCTION. The corpus's 3.2 section ("large outbound activity
            # soon after onboarding or shortly after a dormant period")
            # supports transfer-volume-after-onboarding, not the trading-
            # frequency + young-age conjunction — it does NOT support this
            # claim, so the finding stays uncited unless a section explicitly
            # covers BOTH the young-account AND high-trading conditions
            # (keywords must evidence the conjunction, e.g. "new account AND
            # high trading activity").
            "patterns": ("new account with high activity",),
            "search_terms": ["new account high trading activity",
                             "young account high activity rule",
                             "new account AND high trading"],
            "required_section_keywords": [
                "new account and high trading", "young account and high",
                "new account with high activity", "account creation and trading",
            ],
        },
    ]

    @classmethod
    def refine_search_terms(cls, finding_text: str, domain_terms: List[str]) -> List[str]:
        """Claim-specific search terms when the finding matches a claim rule."""
        low = finding_text.lower()
        for rule in cls.CLAIM_RULES:
            if any(p in low for p in rule["patterns"]):
                return rule["search_terms"] + [
                    t for t in domain_terms if t not in rule["search_terms"]
                ][:2]
        return domain_terms

    @classmethod
    def claim_supported(cls, finding_text: str, section: str, quote: str) -> bool:
        """
        Whether a retrieved section actually supports THIS finding's claim.

        Returns True when no specific claim rule matches (domain validation is
        then sufficient). When a claim rule matches, the section or quote must
        contain at least one of the claim's required keywords — e.g. a
        high-velocity section supports a frequency claim but NOT a
        first-withdrawal/new-address claim.
        """
        low = finding_text.lower()
        for rule in cls.CLAIM_RULES:
            if any(p in low for p in rule["patterns"]):
                text = f"{section} {quote}".lower()
                return any(k in text for k in rule["required_section_keywords"])
        return True


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

    # Account-related keywords (lower priority than network).
    # KYC/CDD domain requires a GENUINE KYC signal word — a bare "account"
    # mention is not enough (it routed ML evidence sentences like "the
    # account's behavior..." to KYC). "new account" is also absent: account
    # age is contextual evidence, never a KYC citation (see classify()).
    ACCOUNT_KEYWORDS = [
        "kyc", "cdd", "customer due diligence", "verification",
        "onboarding", "identity", "customer", "enhanced due diligence",
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

        # Priority 0: The deterministic "New account with high activity" RULE
        # (account_age_days < 7 AND trade_frequency_24h > 50) is RULE evidence
        # when triggered — NOT contextual account age. It must be recognized
        # by its rule name BEFORE the account-age contextual guard below.
        # Negated mentions (the rule NOT being triggered, e.g. in the
        # contextual account-age note) stay contextual.
        if "new account with high activity" in text_lower and not any(
            n in text_lower for n in (
                "not triggered", "unless paired", "did not trigger",
                "threshold not met", "not met",
            )
        ):
            return FindingType.RULE_SIGNAL

        # Account-age evidence is CONTEXTUAL: no policy document defines an
        # account-age threshold (the only age-related logic is the code-side
        # deterministic rule "New account with high activity":
        # account_age_days < 7 AND trade_frequency_24h > 50). Account-age
        # findings therefore get NO citation (UNKNOWN scope) rather than a
        # generic KYC citation.
        if any(p in text_lower for p in (
            "account age", "days old", "new account", "account aging",
            "deliberate aging",
        )):
            return FindingType.UNKNOWN

        # Priority 0.5: GRAPH-ZERO informational notes (BEFORE any graph/ML
        # keyword branch, since "no graph signal" contains "graph signal").
        # The absence of a finding is not a policy-backed risk finding: it
        # never receives any citation (not network, not KYC, not ML-guide).
        if re.search(
            r"no\s+(?:detected\s+)?(graph|network)\s+(signal|relationship|network)|"
            r"graph\s+(?:detection\s+)?score\s*(?:of\s*)?(?:is\s*)?0(?:\.0)?\b|"
            r"no\s+connected\s+(graph|network)|"
            r"score\s*\(?(?:0|0\.0)\)?(?![\d.])",
            text_lower,
        ):
            return FindingType.UNKNOWN

        # Priority 1: Explicit signal mentions (highest priority).
        # Recognize the label forms the explanation layer emits, both in
        # conceptual-finding headers ("Rule-Based Alerts", "ML Pattern
        # Detection Signal") and in sentence bodies ("The Rule Score is 80.0").
        # RULE is checked first so a rule finding whose body also mentions the
        # ML score is not swallowed by the ML patterns.
        if any(p in text_lower for p in (
            "rule signal", "rule engine", "rule score", "rule-based", "rule based",
            "predefined risk rule", "risk rule",
        )):
            return FindingType.RULE_SIGNAL
        if any(p in text_lower for p in (
            "ml signal", "ml score", "ml pattern", "lightgbm", "machine learning",
            "pattern detection",
        )):
            return FindingType.ML_SIGNAL
        if any(p in text_lower for p in (
            "graph signal", "network signal", "graph score", "graph network",
        )):
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

            # Account-age factors are contextual evidence -> no citation
            # (no policy defines an account-age threshold)
            if "age" in factor_lower or "account_age" in factor_lower:
                return FindingType.UNKNOWN

            # Account-related factors (check AFTER network/age)
            if any(word in factor_lower for word in [
                "account", "kyc", "customer", "onboarding", "identity"
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

        # Priority 5: Score-based classification is DISABLED.
        # The old fallback (graph_score>0 -> GRAPH, ml_score>0 -> ML ...) let a
        # finding with NO textual signal of its own — e.g. an ML/Rule combined
        # header like "High-Risk Pattern Detection" — be classified purely from
        # whichever component score happened to be non-zero, producing
        # cross-domain citation mismatches (an ML finding citing the AML
        # network policy). A finding that declares no detection-method signal
        # has no domain basis for a citation.
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
    6. Findings with no domain-relevant citation intentionally receive NONE
       (no fallback citation sharing — domain enforcement is authoritative)
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
            max_citations=max_citations,
            all_findings=key_findings,
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

        # Build search query — claim-refined when the finding matches a
        # specific claim rule (e.g. "First withdrawal to new address" searches
        # for first-withdrawal/new-address policy, not generic velocity).
        search_terms = ClaimRefiner.refine_search_terms(
            finding.finding_text, scope.search_terms)
        query = " ".join(search_terms[:3])

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
                # Validate citation relevance (domain scope)
                is_valid, reason = self.router.validate_citation_relevance(
                    finding_type=finding_type,
                    doc_name=chunk.doc,
                    section=chunk.section,
                    quote=chunk.text
                )
                if is_valid:
                    # Validate CLAIM support: the section must support what
                    # this finding actually claims (prevents e.g. a velocity
                    # citation being reused for a first-withdrawal claim).
                    if not ClaimRefiner.claim_supported(
                        finding.finding_text, chunk.section, chunk.text
                    ):
                        logger.debug(
                            f"Chunk rejected (claim mismatch) for "
                            f"'{finding.finding_text[:40]}...': section "
                            f"'{chunk.section[:40]}' does not support the claim"
                        )
                        continue

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
        max_citations: int,
        all_findings: Optional[List[str]] = None
    ) -> Tuple[List[Citation], Dict[str, List[int]]]:
        """
        Build final citation list with sequential IDs.

        Every finding passed for retrieval keeps an entry in the mapping:
        cited findings -> [id]; uncited findings -> [] (the finding itself is
        still valid — it simply has no policy grounding, and must not be
        dropped or given an unrelated citation).

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

        # Build finding_to_ids mapping (every finding kept; uncited -> [])
        finding_to_ids = {}
        for finding_text in (all_findings or list(finding_citations.keys())):
            citation = finding_citations.get(finding_text)
            if citation is not None and citation.chunk_id in chunk_to_seq:
                finding_to_ids[finding_text] = [chunk_to_seq[citation.chunk_id]]
            else:
                # Uncited (no claim-supporting policy) or citation filtered out
                finding_to_ids[finding_text] = []

        return final_citations, finding_to_ids

    def _ensure_coverage(
        self,
        key_findings: List[str],
        finding_to_ids: Dict[str, List[int]],
        citations: List[Citation]
    ) -> Dict[str, List[int]]:
        """
        Citations are deliberately NOT forced onto findings that retrieved none.

        Domain enforcement is authoritative: if no domain-relevant policy
        citation exists for a finding, the finding simply has NO citation.
        The previous behavior force-shared citations[0] with every uncited
        finding, which mis-grounded unrelated findings (e.g. an ML-guide
        citation attached to rule/graph/account-age lines). `is_valid` in the
        result remains informational only.
        """
        uncited = [f for f in key_findings if not finding_to_ids.get(f)]
        if uncited:
            logger.debug(
                f"{len(uncited)} finding(s) have no domain-relevant citation "
                f"(by design — no fallback citation is attached)"
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
