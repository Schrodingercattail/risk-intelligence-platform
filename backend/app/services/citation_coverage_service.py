"""
Citation Coverage Service v2

Implements minimum sufficient citation set with strict limits:
- Target: 3-5 unique citations per response
- Hard limit: 5 citations maximum
- Citation IDs sequential [1..N]
- Every finding has at least one citation
- No unused citations

Flow:
1. Collect candidates for each finding
2. Deduplicate by (doc, section, chunk_id)
3. Score citations by importance
4. Select top 3-5 citations
5. Ensure every finding has at least one selected citation
6. Normalize IDs to [1..N]
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict, OrderedDict
import logging

from app.services.policy_rag_service import PolicyRAGService
from app.services.citation_mapper import DomainAwareCitationMapper, FindingMetadata, FindingType
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
    importance_score: float = 0.0


@dataclass
class CitationCandidate:
    """A citation candidate with metadata."""
    doc: str
    section: str
    quote: str
    chunk_id: str
    finding_type: Optional[str] = None
    source_findings: List[str] = field(default_factory=list)  # Which findings use this


@dataclass
class CoverageReport:
    """Validation report for citation coverage."""
    total_findings: int
    findings_with_citations: int
    total_citations: int
    used_citations: int
    unused_citations: int
    coverage_rate: float
    is_valid: bool
    compression_ratio: float = 1.0  # compressed / original
    metadata_filtered_count: int = 0  # Number of chunks rejected as metadata

    def to_dict(self) -> dict:
        return {
            "total_findings": self.total_findings,
            "findings_with_citations": self.findings_with_citations,
            "total_citations": self.total_citations,
            "used_citations": self.used_citations,
            "unused_citations": self.unused_citations,
            "coverage_rate": self.coverage_rate,
            "is_valid": self.is_valid,
            "compression_ratio": self.compression_ratio,
            "metadata_filtered_count": self.metadata_filtered_count
        }


class CitationCoverageService:
    """
    Service that implements minimum sufficient citation set.

    Guarantees:
    - 3-5 citations per response (hard limit: 5)
    - Every finding has at least one citation
    - No unused citations
    - Citation IDs sequential [1..N]
    """

    def __init__(self, rag_service: Optional[PolicyRAGService] = None):
        """Initialize citation coverage service."""
        self.rag = rag_service or PolicyRAGService()
        self.mapper = DomainAwareCitationMapper()
        self._metadata_filtered_count = 0  # Track rejected metadata chunks

    def _is_metadata_chunk(self, chunk_text: str) -> bool:
        """
        Check if a chunk is document metadata (not policy evidence).

        Metadata chunks contain:
        - "Status: DEMO TEMPLATE"
        - "Purpose: ..."
        - "non-authoritative"
        - "Replace with your organization's"
        - "> Status:", "> Purpose:" (blockquotes)

        Args:
            chunk_text: The chunk text to check

        Returns:
            True if the chunk is metadata (should be rejected)
        """
        if not chunk_text:
            return False

        text_lower = chunk_text.lower()

        # Metadata patterns that indicate document header/footer
        metadata_patterns = [
            "status: demo template",
            "status:demo template",
            "> status:",
            "purpose:",
            "> purpose:",
            "non-authoritative",
            "non authoritative",
            "replace with your organization's",
            "replace with your organization",
            "provide citable text",
            "before production use",
        ]

        for pattern in metadata_patterns:
            if pattern in text_lower:
                return True

        # Check if chunk is very short and contains metadata keywords
        # Short chunks (< 100 chars) with "status" or "purpose" are likely metadata
        if len(chunk_text) < 100:
            if any(word in text_lower for word in ["status", "purpose", "template"]):
                return True

        return False

    def generate_citations(
        self,
        key_findings: List[str],
        ml_score: Optional[float],
        rule_score: Optional[float],
        graph_score: Optional[float],
        factors: List[dict],
        has_graph_evidence: bool,
        audience: str = "investigator",
        max_citations_per_finding: int = 2,
        target_citation_count: int = 4,
        max_citation_limit: int = 5
    ) -> Tuple[List[Citation], Dict[str, List[int]], CoverageReport]:
        """
        Generate minimum sufficient citation set.

        Args:
            key_findings: List of finding texts
            ml_score: ML signal score
            rule_score: Rule signal score
            graph_score: Graph signal score
            factors: Risk factor list
            has_graph_evidence: Whether graph evidence exists
            audience: Audience mode for quote redaction
            max_citations_per_finding: Max candidates per finding (for collection)
            target_citation_count: Target number of citations (default: 4)
            max_citation_limit: Hard limit on citations (default: 5)

        Returns:
            Tuple of:
            - List of Citation objects (sequential IDs, all used)
            - Dict mapping finding text to citation IDs
            - CoverageReport with validation results
        """
        # Step 1: Collect candidates for each finding
        finding_candidates = self._collect_candidates(
            key_findings=key_findings,
            ml_score=ml_score,
            rule_score=rule_score,
            graph_score=graph_score,
            factors=factors,
            has_graph_evidence=has_graph_evidence,
            audience=audience,
            max_per_finding=max_citations_per_finding
        )

        # Track true original count (before deduplication/compression) for compression ratio
        true_original_count = sum(len(candidates) for candidates in finding_candidates.values())

        # Step 2: Deduplicate and track which findings use each citation
        deduped_candidates = self._deduplicate_candidates(finding_candidates)

        # Step 3: Score and select top citations
        selected_citations = self._select_top_citations(
            candidates=deduped_candidates,
            target_count=target_citation_count,
            max_limit=max_citation_limit
        )

        # Step 4: Ensure every finding has at least one selected citation
        finding_to_citations = self._assign_citations_to_findings(
            key_findings=key_findings,
            finding_candidates=finding_candidates,
            selected_citations=selected_citations
        )

        # Step 5: Build final citation pool and assign sequential IDs
        final_citations, finding_to_ids = self._build_final_citations(
            selected_citations=selected_citations,
            finding_to_citations=finding_to_citations,
            key_findings=key_findings,
            max_limit=max_citation_limit
        )

        # Step 6: Validate coverage
        report = self._validate_coverage(
            key_findings=key_findings,
            finding_to_ids=finding_to_ids,
            citations=final_citations,
            original_count=true_original_count
        )

        if not report.is_valid:
            logger.warning(
                f"Citation coverage validation failed: "
                f"{report.findings_with_citations}/{report.total_findings} findings covered"
            )

        return final_citations, finding_to_ids, report

    def _collect_candidates(
        self,
        key_findings: List[str],
        ml_score: Optional[float],
        rule_score: Optional[float],
        graph_score: Optional[float],
        factors: List[dict],
        has_graph_evidence: bool,
        audience: str,
        max_per_finding: int
    ) -> Dict[str, List[CitationCandidate]]:
        """Collect citation candidates for each finding with domain constraints."""
        queries = self.mapper.map_findings_to_queries(
            key_findings=key_findings,
            ml_score=ml_score,
            rule_score=rule_score,
            graph_score=graph_score,
            factors=factors,
            has_graph_evidence=has_graph_evidence
        )

        finding_candidates: Dict[str, List[CitationCandidate]] = {}
        self._metadata_filtered_count = 0  # Reset counter for this request

        for finding, query in zip(key_findings, queries):
            candidates = []
            try:
                chunks = self.rag.search(query.query, top_k=query.top_k)

                for chunk in chunks[:max_per_finding]:
                    # FILTER METADATA CHUNKS
                    # Reject chunks that are document metadata, not policy evidence
                    if self._is_metadata_chunk(chunk.text):
                        self._metadata_filtered_count += 1
                        logger.debug(
                            f"Filtered metadata chunk from '{chunk.doc}': "
                            f"chunk starts with '{chunk.text[:60]}...'"
                        )
                        continue  # Skip this chunk
                    # ENFORCE DOMAIN CONSTRAINTS
                    # Only include citations from allowed domains
                    if query.finding_type:
                        # Check if the policy document is in allowed domains
                        from app.services.citation_mapper import DomainConstraints
                        if not DomainConstraints.is_domain_allowed(
                            query.finding_type,
                            chunk.doc,
                            chunk.section  # Pass section for better domain analysis
                        ):
                            # Skip this citation - it's from a forbidden domain
                            logger.debug(
                                f"Skipping citation from '{chunk.doc}' for finding '{finding[:30]}...': "
                                f"domain not allowed for {query.finding_type.value}"
                            )
                            continue

                    quote = chunk.text[:400].strip()
                    if audience == "business":
                        quote = "[REDACTED]"
                    else:
                        quote = sanitize_policy_quote(quote)

                    candidate = CitationCandidate(
                        doc=chunk.doc,
                        section=chunk.section,
                        quote=quote,
                        chunk_id=chunk.chunk_id,
                        finding_type=query.finding_type.value if query.finding_type else None,
                        source_findings=[finding]
                    )
                    candidates.append(candidate)
            except Exception as e:
                logger.warning(f"RAG retrieval failed for '{finding[:50]}': {e}")

            finding_candidates[finding] = candidates

        return finding_candidates

    def _deduplicate_candidates(
        self,
        finding_candidates: Dict[str, List[CitationCandidate]]
    ) -> List[CitationCandidate]:
        """
        Deduplicate candidates by (doc, section, chunk_id).

        Merges source_findings for duplicate candidates.
        """
        candidate_map: Dict[str, CitationCandidate] = {}

        for finding, candidates in finding_candidates.items():
            for candidate in candidates:
                key = f"{candidate.doc}#{candidate.section}#{candidate.chunk_id}"

                if key in candidate_map:
                    # Duplicate: merge source findings
                    existing = candidate_map[key]
                    if finding not in existing.source_findings:
                        existing.source_findings.append(finding)
                else:
                    # New candidate
                    candidate_map[key] = candidate

        return list(candidate_map.values())

    def _select_top_citations(
        self,
        candidates: List[CitationCandidate],
        target_count: int,
        max_limit: int
    ) -> List[CitationCandidate]:
        """
        Select top citations based on importance score.

        Importance factors:
        - Number of findings that use this citation (coverage)
        - Domain diversity (avoid too many from same doc)
        - Finding-specific relevance
        """
        if not candidates:
            return []

        # Score each candidate
        for candidate in candidates:
            candidate.importance_score = self._calculate_importance(candidate, candidates)

        # Sort by importance score (descending)
        scored = sorted(candidates, key=lambda c: c.importance_score, reverse=True)

        # Select top citations with domain diversity consideration
        selected = self._select_with_diversity(scored, target_count, max_limit)

        return selected

    def _calculate_importance(
        self,
        candidate: CitationCandidate,
        all_candidates: List[CitationCandidate]
    ) -> float:
        """Calculate importance score for a citation."""
        score = 0.0

        # Factor 1: Coverage - how many findings use this
        coverage_count = len(candidate.source_findings)
        score += coverage_count * 10  # Each supporting finding = 10 points

        # Factor 2: Domain diversity bonus
        # Penalize if we already have many from same doc
        doc_count = sum(1 for c in all_candidates if c.doc == candidate.doc)
        if doc_count > 1:
            score -= (doc_count - 1) * 2  # Small penalty for duplicates

        # Factor 3: Finding type diversity
        finding_types = set()
        for other in all_candidates:
            if other.chunk_id == candidate.chunk_id:
                if other.finding_type:
                    finding_types.add(other.finding_type)
        score += len(finding_types) * 5  # More finding types = more useful

        return score

    def _select_with_diversity(
        self,
        scored_candidates: List[CitationCandidate],
        target_count: int,
        max_limit: int
    ) -> List[CitationCandidate]:
        """
        Select citations with domain diversity.

        Ensures we don't select too many from the same document.
        """
        if not scored_candidates:
            return []

        selected: List[CitationCandidate] = []
        doc_counts: Dict[str, int] = {}

        for candidate in scored_candidates:
            if len(selected) >= max_limit:
                break

            # Check if we should add this candidate
            doc_count = doc_counts.get(candidate.doc, 0)

            # Allow up to 2 from same doc, but prefer diversity
            if doc_count < 2 or len(selected) < target_count:
                selected.append(candidate)
                doc_counts[candidate.doc] = doc_count + 1

        return selected

    def _assign_citations_to_findings(
        self,
        key_findings: List[str],
        finding_candidates: Dict[str, List[CitationCandidate]],
        selected_citations: List[CitationCandidate]
    ) -> Dict[str, List[str]]:
        """
        Assign selected citations to findings.

        Ensures every finding has at least one citation.
        """
        # Build mapping of chunk_id to selected citation
        selected_chunks = {}
        for cit in selected_citations:
            selected_chunks[cit.chunk_id] = cit

        # Assign citations to findings
        finding_to_citations: Dict[str, List[str]] = {}

        for finding in key_findings:
            candidates = finding_candidates.get(finding, [])
            assigned_chunk_ids = []

            for candidate in candidates:
                if candidate.chunk_id in selected_chunks:
                    assigned_chunk_ids.append(candidate.chunk_id)

            finding_to_citations[finding] = assigned_chunk_ids

        return finding_to_citations

    def _build_final_citations(
        self,
        selected_citations: List[CitationCandidate],
        finding_to_citations: Dict[str, List[str]],
        key_findings: List[str],
        max_limit: int = 5
    ) -> Tuple[List[Citation], Dict[str, List[int]]]:
        """
        Build final citation pool with sequential IDs.
        """
        # Ensure every finding has at least one citation
        # If not, add fallback citations (respecting max_limit)
        selected_citations = self._ensure_coverage(
            selected_citations,
            finding_to_citations,
            key_findings,
            max_limit=max_limit
        )

        # Map chunk_id to sequential ID
        chunk_id_to_seq: Dict[str, int] = {}
        final_citations: List[Citation] = []

        for idx, candidate in enumerate(selected_citations, start=1):
            citation = Citation(
                id=idx,
                doc=candidate.doc,
                section=candidate.section,
                quote=candidate.quote,
                chunk_id=candidate.chunk_id,
                finding_type=candidate.finding_type
            )
            final_citations.append(citation)
            chunk_id_to_seq[candidate.chunk_id] = idx

        # Build finding_to_ids mapping with sequential IDs
        finding_to_ids: Dict[str, List[int]] = {}

        for finding in key_findings:
            chunk_ids = finding_to_citations.get(finding, [])
            sequential_ids = []
            for chunk_id in chunk_ids:
                if chunk_id in chunk_id_to_seq:
                    sequential_ids.append(chunk_id_to_seq[chunk_id])
            finding_to_ids[finding] = sequential_ids

        return final_citations, finding_to_ids

    def _ensure_coverage(
        self,
        selected_citations: List[CitationCandidate],
        finding_to_citations: Dict[str, List[str]],
        key_findings: List[str],
        max_limit: int = 5
    ) -> List[CitationCandidate]:
        """
        Ensure every finding has at least one citation.

        Add fallback citations if needed, but respect max_limit.
        If max_limit prevents covering all findings, share existing citations.
        """
        # Find findings without citations
        findings_without = []
        selected_chunk_ids = set(c.chunk_id for c in selected_citations)

        for finding in key_findings:
            chunk_ids = finding_to_citations.get(finding, [])
            if not chunk_ids or not any(cid in selected_chunk_ids for cid in chunk_ids):
                findings_without.append(finding)

        # Strategy 1: Try to add fallback citations (respecting max_limit)
        for finding in findings_without[:]:  # Iterate copy so we can modify
            if len(selected_citations) >= max_limit:
                break  # Stop if we've hit the limit

            fallback = self._get_fallback_citation(finding)
            if fallback and fallback.chunk_id not in selected_chunk_ids:
                selected_citations.append(fallback)
                selected_chunk_ids.add(fallback.chunk_id)
                # Update finding_to_citations
                if finding not in finding_to_citations:
                    finding_to_citations[finding] = []
                finding_to_citations[finding].append(fallback.chunk_id)
                findings_without.remove(finding)

        # Strategy 2: If still findings without citations, share from existing
        if findings_without and selected_citations:
            # Assign the most shared citation to uncovered findings
            # (This ensures coverage even under max_limit constraint)
            most_shared_citation = max(
                selected_citations,
                key=lambda c: len(c.source_findings),
                default=None
            )
            if most_shared_citation:
                for finding in findings_without:
                    if finding not in finding_to_citations:
                        finding_to_citations[finding] = []
                    finding_to_citations[finding].append(most_shared_citation.chunk_id)
                    # Update source_findings to track this sharing
                    most_shared_citation.source_findings.append(finding)
                    logger.debug(
                        f"Shared citation {most_shared_citation.chunk_id} to finding '{finding[:50]}...'"
                    )

        return selected_citations

    def _get_fallback_citation(self, finding: str) -> Optional[CitationCandidate]:
        """Get fallback citation when no candidates available."""
        query = self._generate_fallback_query(finding)
        if not query:
            return None

        try:
            chunks = self.rag.search(query, top_k=1)
            if chunks:
                chunk = chunks[0]
                return CitationCandidate(
                    doc=chunk.doc,
                    section=chunk.section,
                    quote=chunk.text[:400].strip(),
                    chunk_id=chunk.chunk_id,
                    finding_type="fallback",
                    source_findings=[finding]
                )
        except Exception as e:
            logger.warning(f"Fallback RAG failed for '{finding[:50]}': {e}")

        return None

    def _generate_fallback_query(self, finding: str) -> Optional[str]:
        """Generate fallback RAG query."""
        text_lower = finding.lower()

        if "ml" in text_lower or "signal" in text_lower:
            return "ML pattern detection anomaly risk scoring"
        if "shared" in text_lower or "connected" in text_lower or "network" in text_lower:
            return "network relationship cluster shared device connection"
        if "account" in text_lower or "new" in text_lower:
            return "account KYC CDD verification due diligence"
        if "trading" in text_lower or "frequency" in text_lower:
            return "trading behavior frequency pattern monitoring"

        return "risk investigation policy"

    def _validate_coverage(
        self,
        key_findings: List[str],
        finding_to_ids: Dict[str, List[int]],
        citations: List[Citation],
        original_count: int
    ) -> CoverageReport:
        """Validate citation coverage contract."""
        total_findings = len(key_findings)
        findings_with_citations = sum(1 for f in key_findings if finding_to_ids.get(f))

        total_citations = len(citations)
        used_citation_ids = set()
        for ids in finding_to_ids.values():
            used_citation_ids.update(ids)

        unused_citations = total_citations - len(used_citation_ids)
        coverage_rate = findings_with_citations / total_findings if total_findings > 0 else 1.0

        compression_ratio = len(citations) / original_count if original_count > 0 else 1.0

        is_valid = (
            findings_with_citations == total_findings and
            unused_citations == 0 and
            total_citations <= 5
        )

        return CoverageReport(
            total_findings=total_findings,
            findings_with_citations=findings_with_citations,
            total_citations=total_citations,
            used_citations=len(used_citation_ids),
            unused_citations=unused_citations,
            coverage_rate=coverage_rate,
            is_valid=is_valid,
            compression_ratio=compression_ratio,
            metadata_filtered_count=self._metadata_filtered_count
        )


@dataclass
class FilteredCitations:
    """Result of filtering citations to only used ones."""
    citations: List[Citation]
    old_to_new_id_map: Dict[int, int]
    filtered_count: int


class CitationFilter:
    """
    Filters citations to only include those actually used in text.
    Re-indexes citations sequentially after filtering.
    """

    def __init__(self):
        """Initialize citation filter."""
        pass

    def extract_used_citation_ids(
        self,
        summary: str,
        key_findings: List[str],
        recommended_action: str
    ) -> Set[int]:
        """
        Extract all citation IDs referenced in explanation text.

        Args:
            summary: Explanation summary text
            key_findings: List of finding texts
            recommended_action: Recommended action text

        Returns:
            Set of citation IDs referenced in the text
        """
        import re
        used_ids = set()

        # Extract from summary
        summary_ids = re.findall(r'\[(\d+)\]', summary)
        used_ids.update(int(id) for id in summary_ids)

        # Extract from key_findings
        for finding in key_findings:
            if isinstance(finding, str):
                finding_ids = re.findall(r'\[(\d+)\]', finding)
                used_ids.update(int(id) for id in finding_ids)

        # Extract from recommended_action
        action_ids = re.findall(r'\[(\d+)\]', recommended_action)
        used_ids.update(int(id) for id in action_ids)

        return used_ids

    def filter_citations(
        self,
        all_citations: List[Citation],
        used_citation_ids: Set[int]
    ) -> FilteredCitations:
        """
        Filter citations to only include used ones and re-index sequentially.

        Args:
            all_citations: All citations (some may be unused)
            used_citation_ids: Set of citation IDs that are referenced in text

        Returns:
            FilteredCitations with re-indexed citations
        """
        # Filter to only used citations
        used_citations = [c for c in all_citations if c.id in used_citation_ids]

        # Create mapping from old ID to new sequential ID
        old_to_new_id_map = {}
        for new_id, citation in enumerate(used_citations, start=1):
            old_to_new_id_map[citation.id] = new_id
            citation.id = new_id  # Update to sequential ID

        return FilteredCitations(
            citations=used_citations,
            old_to_new_id_map=old_to_new_id_map,
            filtered_count=len(all_citations) - len(used_citations)
        )

    def update_citation_marks(
        self,
        summary: str,
        key_findings: List[str],
        recommended_action: str,
        old_to_new_id_map: Dict[int, int]
    ) -> Tuple[str, List[str], str]:
        """
        Update citation marks in text after re-indexing.

        Args:
            summary: Explanation summary text
            key_findings: List of finding texts
            recommended_action: Recommended action text
            old_to_new_id_map: Mapping from old IDs to new sequential IDs

        Returns:
            Tuple of (updated_summary, updated_key_findings, updated_action)
        """
        import re

        def replace_marks(text: str) -> str:
            """Replace citation marks with new IDs."""
            def replacer(match):
                old_id = int(match.group(1))
                new_id = old_to_new_id_map.get(old_id, old_id)
                return f"[{new_id}]"

            return re.sub(r'\[(\d+)\]', replacer, text)

        updated_summary = replace_marks(summary)
        updated_key_findings = [
            replace_marks(finding) if isinstance(finding, str) else finding
            for finding in key_findings
        ]
        updated_action = replace_marks(recommended_action)

        return updated_summary, updated_key_findings, updated_action

    def filter_and_reindex(
        self,
        all_citations: List[Citation],
        summary: str,
        key_findings: List[str],
        recommended_action: str
    ) -> Tuple[List[Citation], str, List[str], str]:
        """
        Complete filter and re-index pipeline.

        Args:
            all_citations: All citations (some may be unused)
            summary: Explanation summary text
            key_findings: List of finding texts
            recommended_action: Recommended action text

        Returns:
            Tuple of (filtered_citations, updated_summary, updated_key_findings, updated_action)
        """
        # Step 1: Extract used citation IDs
        used_ids = self.extract_used_citation_ids(summary, key_findings, recommended_action)

        if not used_ids:
            # No citations used - return empty list
            return [], summary, key_findings, recommended_action

        # Step 2: Filter citations to only used ones and re-index
        filtered = self.filter_citations(all_citations, used_ids)

        # Step 3: Update citation marks in text
        updated_summary, updated_key_findings, updated_action = self.update_citation_marks(
            summary, key_findings, recommended_action, filtered.old_to_new_id_map
        )

        logger.info(
            f"Citation filter: {filtered.filtered_count} unused citations removed, "
            f"{len(filtered.citations)} citations after filtering"
        )

        return filtered.citations, updated_summary, updated_key_findings, updated_action


def create_citation_filter() -> CitationFilter:
    """Factory function to create a CitationFilter instance."""
    return CitationFilter()


def create_citation_coverage_service(rag_service: Optional[PolicyRAGService] = None) -> CitationCoverageService:
    """Factory function to create a CitationCoverageService instance."""
    return CitationCoverageService(rag_service)
