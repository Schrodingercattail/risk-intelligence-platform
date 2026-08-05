#!/usr/bin/env python3
"""
Test script to verify citation filtering works correctly.

Run this script to check if the /api/risk/explain endpoint
correctly filters unused citations.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from app.services.citation_coverage_service import create_citation_coverage_service, create_citation_filter

def test_citation_filtering():
    """Test that unused citations are filtered out."""
    print("=" * 60)
    print("CITATION FILTERING TEST")
    print("=" * 60)
    print()

    # Test case: Generate citations for findings
    key_findings = [
        "Elevated New Account Risk",
        "Connected to 2 other accounts"
    ]

    print(f"Input findings: {key_findings}")
    print()

    # Step 1: Generate citations
    service = create_citation_coverage_service()
    citations, finding_to_citations, report = service.generate_citations(
        key_findings=key_findings,
        ml_score=0.0,
        rule_score=0.0,
        graph_score=60.0,
        factors=[],
        has_graph_evidence=True,
        audience="investigator",
        target_citation_count=4  # Request more to test filtering
    )

    print(f"Generated {len(citations)} citations:")
    for cit in citations:
        print(f"  [{cit.id}] {cit.doc} - {cit.section}")
    print()

    # Step 2: Attach marks
    marked_findings = []
    for finding in key_findings:
        ids = finding_to_citations.get(finding, [])
        if ids:
            sorted_ids = sorted(set(ids))
            marks = "".join([f"[{cid}]" for cid in sorted_ids])
            marked_findings.append(f"{finding} {marks}")
        else:
            marked_findings.append(finding)

    print(f"Marked findings: {marked_findings}")
    print()

    # Step 3: Create explanation
    summary = "This account received a HIGH risk score."
    recommended_action = "Review case."

    # Simulate adding summary marks
    used_ids = set()
    for ids in finding_to_citations.values():
        used_ids.update(ids)

    if used_ids:
        summary_ids = sorted(list(used_ids))[:2]
        summary_marks = "".join([f"[{cid}]" for cid in summary_ids])
        summary = summary + " " + summary_marks

    print(f"Summary: {summary}")
    print(f"Action: {recommended_action}")
    print()

    # Step 4: Filter
    print("-" * 60)
    print("FILTERING UNUSED CITATIONS")
    print("-" * 60)
    citation_filter = create_citation_filter()
    filtered_citations, updated_summary, updated_key_findings, updated_action = citation_filter.filter_and_reindex(
        all_citations=citations,
        summary=summary,
        key_findings=marked_findings,
        recommended_action=recommended_action
    )

    print(f"Original citations: {len(citations)}")
    print(f"Filtered citations: {len(filtered_citations)}")
    print(f"Removed: {len(citations) - len(filtered_citations)} unused citations")
    print()

    # Step 5: Validate
    import re
    all_marks = set()
    for text in [updated_summary] + updated_key_findings + [updated_action]:
        marks = re.findall(r'\[(\d+)\]', text)
        all_marks.update(int(m) for m in marks)

    all_citation_ids = set(c.id for c in filtered_citations)
    unused = all_citation_ids - all_marks

    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    print(f"Citation marks in text: {sorted(all_marks)}")
    print(f"Citation IDs in response: {sorted(all_citation_ids)}")
    print(f"Unused citations: {sorted(unused) if unused else 'NONE'}")
    print()

    # Check results
    if len(unused) > 0:
        print("❌ FAIL: Found unused citations!")
        return False
    else:
        print("✅ SUCCESS: All citations are used!")
        return True

if __name__ == "__main__":
    success = test_citation_filtering()
    sys.exit(0 if success else 1)
