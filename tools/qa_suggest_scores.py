#!/usr/bin/env python3
"""
QA Suggestion Script for Explanation Evaluation

This script reads raw explanation JSON files and outputs rule-based suggestions
for potential quality issues. It uses heuristics ONLY (no LLM) to flag cases
that may need human review.

IMPORTANT: This does NOT replace human rating. It helps reviewers triage
and prioritize which cases to evaluate more carefully.

Usage:
    python tools/qa_suggest_scores.py \\
        --raw-dir eval/raw_explanations \\
        --out eval/qa_suggestions.csv
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Rule-based heuristics for detecting potential issues
# Each function returns (failure_code, description) or None

def check_sensitive_leakage(explanation: Dict) -> Tuple[str, str] | None:
    """
    Check for potential sensitive data leakage.

    Patterns:
    - IP addresses (IPv4 and IPv6)
    - Email addresses
    - Phone numbers (7+ digits with optional separators)
    - Long numeric IDs (10+ digits)
    """
    text_fields = []

    # Collect all text fields
    if "summary" in explanation:
        text_fields.append(str(explanation["summary"]))
    if "key_findings" in explanation:
        for finding in explanation["key_findings"]:
            text_fields.append(str(finding))
    if "recommended_action" in explanation:
        text_fields.append(str(explanation["recommended_action"]))

    combined_text = " ".join(text_fields)

    # Check for IP addresses
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    if re.search(ip_pattern, combined_text):
        return "E1", "Potential IP address leakage"

    # Check for IPv6-like patterns
    ipv6_pattern = r'\b[0-9a-fA-F:]{2,}:[0-9a-fA-F:]{2,}\b'
    if re.search(ipv6_pattern, combined_text):
        return "E1", "Potential IPv6 address leakage"

    # Check for email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if re.search(email_pattern, combined_text):
        return "E1", "Potential email address leakage"

    # Check for phone-like sequences (7+ digits)
    phone_pattern = r'\b[\d\-\(\)\+]{7,}\d\b'
    if re.search(phone_pattern, combined_text):
        return "E1", "Potential phone number leakage"

    # Check for long ID-like numbers (10+ digits)
    id_pattern = r'\b\d{10,}\b'
    if re.search(id_pattern, combined_text):
        return "E3", "Potential internal ID leakage"

    return None


def check_missing_citations(explanation: Dict) -> Tuple[str, str] | None:
    """
    Check for missing citations when citation marks are present.
    """
    text_fields = []

    if "summary" in explanation:
        text_fields.append(str(explanation["summary"]))
    if "key_findings" in explanation:
        for finding in explanation["key_findings"]:
            text_fields.append(str(finding))

    combined_text = " ".join(text_fields)

    # Check for citation marks [n]
    citation_marks = re.findall(r'\[(\d+)\]', combined_text)

    # Check if citations exist
    citations = explanation.get("citations", [])
    citations_count = len(citations)

    # If we have citation marks but no citations, that's a problem
    if citation_marks and citations_count == 0:
        return "D3", "Citation marks present but no citations in response"

    # If we have citations but no citation marks in findings
    if not citation_marks and citations_count > 0:
        return "D2", "Citations present but no citation marks in text"

    return None


def check_redundancy(explanation: Dict) -> Tuple[str, str] | None:
    """
    Check for excessive redundancy in findings.
    """
    if "key_findings" not in explanation:
        return None

    findings = explanation["key_findings"]
    if not findings:
        return None

    # Check if all findings are just "X Score: Y" variations
    score_pattern = re.compile(r'.*Score:\s*\d+.*')
    score_count = sum(1 for f in findings if score_pattern.match(str(f)))

    if score_count == len(findings) and len(findings) > 2:
        return "B2", "All findings are just score repetitions"

    # Check for duplicate findings
    unique_findings = set(str(f).strip() for f in findings)
    if len(unique_findings) < len(findings):
        return "B2", "Duplicate findings detected"

    return None


def check_vague_action(explanation: Dict) -> Tuple[str, str] | None:
    """
    Check for vague or generic recommended actions.
    """
    action = explanation.get("recommended_action", "").lower()

    # Vague action patterns
    vague_patterns = [
        r"^review\s*$",
        r"^review\s+case\s*$",
        r"^investigate\s*$",
        r"^monitor\s*$",
        r"^none\s*$",
        r"^n/a\s*$"
    ]

    for pattern in vague_patterns:
        if re.match(pattern, action.strip()):
            return "C1", "Vague or generic recommended action"

    # Check if action is too short (< 10 chars)
    if len(action.strip()) < 10 and action.strip():
        return "C1", "Recommended action too short/vague"

    return None


def check_missing_action(explanation: Dict) -> Tuple[str, str] | None:
    """
    Check for missing recommended action.
    """
    action = explanation.get("recommended_action")

    if not action or str(action).strip() in ["", "N/A", "None", "null"]:
        return "C2", "No recommended action provided"

    return None


def check_score_mismatch(explanation: Dict) -> Tuple[str, str] | None:
    """
    Check for potential score mismatches between summary and structured data.
    """
    summary = str(explanation.get("summary", ""))

    # Extract risk score mentioned in summary (pattern: "XX.XX/100" or "score XX")
    score_patterns = [
        r'(\d+\.?\d*)\s*/\s*100',
        r'score\s+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s+risk\s+score'
    ]

    # This is a simple heuristic - would need more sophisticated parsing
    # to reliably detect mismatches
    # For now, we flag if score is mentioned but looks suspicious

    return None


# Registry of all rule checks
RULE_CHECKS = [
    ("Sensitive Leakage", check_sensitive_leakage),
    ("Missing Citations", check_missing_citations),
    ("Redundancy", check_redundancy),
    ("Vague Action", check_vague_action),
    ("Missing Action", check_missing_action),
]


def analyze_explanation(user_id: str, explanation: Dict) -> List[Tuple[str, str]]:
    """
    Run all rule checks on an explanation.

    Args:
        user_id: User ID for the explanation
        explanation: Explanation dictionary

    Returns:
        List of (failure_code, description) tuples
    """
    suggestions = []

    for check_name, check_func in RULE_CHECKS:
        try:
            result = check_func(explanation)
            if result:
                suggestions.append(result)
        except Exception as e:
            print(f"  Warning: Check '{check_name}' failed for {user_id}: {e}")

    return suggestions


def main():
    parser = argparse.ArgumentParser(
        description="QA suggestion script for explanation evaluation"
    )
    parser.add_argument(
        "--raw-dir",
        default="eval/raw_explanations",
        help="Directory containing raw explanation JSON files (default: eval/raw_explanations)"
    )
    parser.add_argument(
        "--out",
        default="eval/qa_suggestions.csv",
        help="Output path for suggestions CSV (default: eval/qa_suggestions.csv)"
    )

    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)

    if not raw_dir.exists():
        print(f"Error: Directory not found: {raw_dir}")
        print("Please run export_explain_eval_set.py first to generate raw explanations.")
        sys.exit(1)

    # Find all JSON files
    json_files = list(raw_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {raw_dir}")
        sys.exit(1)

    print(f"Found {len(json_files)} explanation files")
    print()

    # Analyze each explanation
    results = []

    for json_file in json_files:
        user_id = json_file.stem

        try:
            with open(json_file, "r") as f:
                explanation = json.load(f)

            # Check for error in explanation
            if "error" in explanation:
                results.append({
                    "user_id": user_id,
                    "failure_codes": "FETCH_ERROR",
                    "description": explanation.get("error", "Unknown error"),
                    "suggestion_count": 1
                })
                continue

            suggestions = analyze_explanation(user_id, explanation)

            if suggestions:
                failure_codes = ";".join(code for code, _ in suggestions)
                descriptions = "; ".join(f"{code}: {desc}" for code, desc in suggestions)
            else:
                failure_codes = ""
                descriptions = ""

            results.append({
                "user_id": user_id,
                "failure_codes": failure_codes,
                "description": descriptions,
                "suggestion_count": len(suggestions)
            })

        except Exception as e:
            print(f"  Error processing {user_id}: {e}")
            results.append({
                "user_id": user_id,
                "failure_codes": "PARSE_ERROR",
                "description": str(e),
                "suggestion_count": 1
            })

    # Write results to CSV
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    with open(args.out, "w", newline="") as f:
        fieldnames = ["user_id", "failure_codes", "description", "suggestion_count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} suggestions to {args.out}")
    print()

    # Print summary
    flagged = [r for r in results if r["suggestion_count"] > 0]
    print(f"Summary: {len(flagged)}/{len(results)} cases flagged for review")

    if flagged:
        print()
        print("Most common issues:")
        issue_counts = {}
        for r in flagged:
            codes = r["failure_codes"].split(";")
            for code in codes:
                issue_counts[code] = issue_counts.get(code, 0) + 1

        for code, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
            print(f"  {code}: {count} occurrences")

    print()
    print("IMPORTANT: These are SUGGESTIONS based on simple rules.")
    print("Human evaluation is still required for accurate quality assessment.")
    print()
    print("Next steps:")
    print("  1. Review qa_suggestions.csv")
    print("  2. Prioritize cases with suggestions for human review")
    print("  3. Use explain_eval_results.csv to record actual evaluations")


if __name__ == "__main__":
    main()
