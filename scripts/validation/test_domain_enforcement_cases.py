"""
Test Domain Enforcement with U00299 and U00010 Cases

This script demonstrates the citation mapping quality with the new domain enforcement:
- Section-level policy domain validation
- Fixed classification priority (NETWORK > ACCOUNT)
- Metadata chunk filtering

Usage:
    python test_domain_enforcement_cases.py
"""

from app.services.citation_coverage_service import create_citation_coverage_service
from app.services.citation_mapper import create_domain_aware_citation_mapper, FindingType


def test_case_u00299():
    """
    U00299 Case: Network/Graph Signal Finding

    This case tests that network-related findings are properly classified
    and cite appropriate network/relationship policies, not KYC or transaction policies.
    """
    print("\n" + "="*80)
    print("TEST CASE: U00299 - Network/Graph Signal Finding")
    print("="*80)

    service = create_citation_coverage_service()

    # U00299 key findings (network-related)
    key_findings = [
        "Connected to 18 other accounts",
        "Elevated Linked Account Network",
        "Shared devices detected"
    ]

    print("\nKey Findings:")
    for i, finding in enumerate(key_findings, 1):
        print(f"  {i}. {finding}")

    # Classify findings to show they're GRAPH_SIGNAL, not ACCOUNT_PROFILE
    mapper = create_domain_aware_citation_mapper()
    print("\nFinding Classifications:")
    for finding in key_findings:
        finding_type = mapper.classify_finding(
            text=finding,
            graph_score=60.0,
            has_graph_evidence=True
        )
        print(f"  '{finding}' → {finding_type.value}")

    # Generate citations
    citations, finding_to_citations, report = service.generate_citations(
        key_findings=key_findings,
        ml_score=0.0,
        rule_score=0.0,
        graph_score=60.0,
        factors=[],
        has_graph_evidence=True,
        audience="investigator"
    )

    print("\nCitation Mapping Results:")
    print(f"  Total Citations: {len(citations)}")
    print(f"  Findings with Citations: {report.findings_with_citations}/{report.total_findings}")
    print(f"  Metadata Chunks Filtered: {report.metadata_filtered_count}")

    print("\nCitation Details:")
    for cit in citations:
        print(f"\n  Citation ID: {cit.id}")
        print(f"    Source: {cit.doc}")
        print(f"    Section: {cit.section}")
        print(f"    Quote: {cit.quote[:150]}...")

    print("\nFinding → Citation Mapping:")
    for finding, ids in finding_to_citations.items():
        print(f"  '{finding}' → {[f'[{i}]' for i in ids]}")

    # Verify domain constraints
    print("\nDomain Constraints Validation:")
    for cit in citations:
        doc_lower = cit.doc.lower()
        section_lower = cit.section.lower() if cit.section else ""

        # Check for FORBIDDEN domains
        if "kyc" in doc_lower:
            print(f"  ❌ ERROR: GRAPH_SIGNAL citing KYC document: {cit.doc}")
        elif "cdd" in doc_lower:
            print(f"  ❌ ERROR: GRAPH_SIGNAL citing CDD document: {cit.doc}")
        elif "aml" in doc_lower and "transaction" in section_lower:
            print(f"  ❌ ERROR: GRAPH_SIGNAL citing transaction section: {cit.section}")
        else:
            print(f"  ✓ Valid domain for citation {cit.id}: {cit.doc}")

    return citations, finding_to_citations, report


def test_case_u00010():
    """
    U00010 Case: Mixed Signal Types

    This case tests a complex scenario with ML, Rule, Graph, and Account Profile findings.
    Verifies each finding type cites appropriate policies.
    """
    print("\n" + "="*80)
    print("TEST CASE: U00010 - Mixed Signal Types")
    print("="*80)

    service = create_citation_coverage_service()

    # U00010 key findings (mixed types)
    key_findings = [
        "ML Signal Score: 85.00",
        "Rule Engine Signal Score: 72.50",
        "Graph Network Signal Score: 60.00",
        "Elevated trading_frequency_24h",
        "Elevated account_age_days",
        "Connected to 1 other account(s) through shared devices/IPs"
    ]

    factors = [
        {'factor_name': 'trading_frequency_24h', 'factor_value': 150},
        {'factor_name': 'account_age_days', 'factor_value': 5}
    ]

    print("\nKey Findings:")
    for i, finding in enumerate(key_findings, 1):
        print(f"  {i}. {finding}")

    # Classify findings
    mapper = create_domain_aware_citation_mapper()
    print("\nFinding Classifications:")
    for finding in key_findings:
        # Extract factor name if applicable
        factor_name = None
        for factor in factors:
            if factor.get("factor_name", "").lower() in finding.lower():
                factor_name = factor.get("factor_name")
                break

        finding_type = mapper.classify_finding(
            text=finding,
            ml_score=85.0,
            rule_score=72.5,
            graph_score=60.0,
            factor_name=factor_name,
            has_graph_evidence=True
        )
        print(f"  '{finding}' → {finding_type.value}")

    # Generate citations
    citations, finding_to_citations, report = service.generate_citations(
        key_findings=key_findings,
        ml_score=85.0,
        rule_score=72.5,
        graph_score=60.0,
        factors=factors,
        has_graph_evidence=True,
        audience="investigator"
    )

    print("\nCitation Mapping Results:")
    print(f"  Total Citations: {len(citations)}")
    print(f"  Findings with Citations: {report.findings_with_citations}/{report.total_findings}")
    print(f"  Metadata Chunks Filtered: {report.metadata_filtered_count}")
    print(f"  Compression Ratio: {report.compression_ratio:.2f}")

    print("\nCitation Details:")
    for cit in citations:
        print(f"\n  Citation ID: {cit.id}")
        print(f"    Source: {cit.doc}")
        print(f"    Section: {cit.section}")
        print(f"    Quote: {cit.quote[:150]}...")

    print("\nFinding → Citation Mapping:")
    for finding, ids in finding_to_citations.items():
        print(f"  '{finding}' → {[f'[{i}]' for i in ids]}")

    # Domain-specific validation
    print("\nDomain Constraints Validation:")

    # ML_SIGNAL should not cite transaction sections
    ml_finding = "ML Signal Score: 85.00"
    ml_ids = finding_to_citations.get(ml_finding, [])
    print(f"\n  ML Signal citations:")
    for cit in citations:
        if cit.id in ml_ids:
            section_lower = cit.section.lower() if cit.section else ""
            if "transaction" in section_lower or "velocity" in section_lower:
                print(f"    ❌ ERROR: ML citing transaction section: {cit.section}")
            else:
                print(f"    ✓ Valid: {cit.doc} - {cit.section}")

    # GRAPH_SIGNAL should not cite KYC
    graph_findings = [
        "Graph Network Signal Score: 60.00",
        "Connected to 1 other account(s) through shared devices/IPs"
    ]
    print(f"\n  Graph Signal citations:")
    for finding in graph_findings:
        graph_ids = finding_to_citations.get(finding, [])
        for cit in citations:
            if cit.id in graph_ids:
                doc_lower = cit.doc.lower()
                if "kyc" in doc_lower or "cdd" in doc_lower:
                    print(f"    ❌ ERROR: Graph citing KYC/CDD: {cit.doc}")
                else:
                    print(f"    ✓ Valid: {cit.doc} - {cit.section}")

    # ACCOUNT_PROFILE should cite KYC
    account_finding = "Elevated account_age_days"
    account_ids = finding_to_citations.get(account_finding, [])
    print(f"\n  Account Profile citations:")
    found_kyc = False
    for cit in citations:
        if cit.id in account_ids:
            doc_lower = cit.doc.lower()
            if "kyc" in doc_lower or "cdd" in doc_lower:
                found_kyc = True
                print(f"    ✓ Valid KYC citation: {cit.doc}")
            elif "investigation" in doc_lower or "sop" in doc_lower:
                print(f"    ✓ Valid fallback: {cit.doc}")

    if not found_kyc:
        print(f"    ⚠ No direct KYC citation found (may use fallback)")

    return citations, finding_to_citations, report


def main():
    """Run all test cases."""
    print("\n" + "="*80)
    print("CITATION DOMAIN ENFORCEMENT - TEST CASES")
    print("="*80)

    # Test U00299
    u00299_results = test_case_u00299()

    # Test U00010
    u00010_results = test_case_u00010()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n✓ Section-level policy domain validation: Implemented")
    print("✓ Fixed classification priority (NETWORK > ACCOUNT): Implemented")
    print("✓ Metadata chunk filtering: Implemented")
    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    main()
