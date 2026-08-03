#!/usr/bin/env python3
"""
Export Evaluation Set for /api/risk/explain

This script exports a sample of cases from the investigation queue
for explanation quality evaluation.

Usage:
    python tools/export_explain_eval_set.py \\
        --base-url http://localhost:8000 \\
        --count 30 \\
        --out eval/explain_eval_cases.csv
"""
import argparse
import csv
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


# API endpoint configuration - easy to change if endpoints differ
CASES_ENDPOINT = "/api/risk/cases"
EXPLAIN_ENDPOINT = "/api/risk/explain"


def fetch_cases(base_url: str, risk_levels: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch cases from the investigation queue for specified risk levels.

    Args:
        base_url: Base URL of the API (e.g., http://localhost:8000)
        risk_levels: List of risk levels to fetch (CRITICAL, HIGH, MEDIUM)

    Returns:
        List of case dictionaries
    """
    all_cases = []

    for risk_level in risk_levels:
        # Build URL with query parameters
        params = {"risk_level": risk_level}
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{base_url}{CASES_ENDPOINT}?{query_string}"

        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                cases = data.get("items", [])
                all_cases.extend(cases)
                print(f"Fetched {len(cases)} {risk_level} cases")
        except urllib.error.HTTPError as e:
            print(f"Error fetching {risk_level} cases: {e.code} - {e.reason}")
        except Exception as e:
            print(f"Error fetching {risk_level} cases: {e}")

    return all_cases


def fetch_explanation(base_url: str, user_id: str, audience: str = "investigator") -> Dict[str, Any]:
    """
    Fetch explanation for a specific user.

    Args:
        base_url: Base URL of the API
        user_id: User ID to fetch explanation for
        audience: Audience mode (investigator or business)

    Returns:
        Explanation response dictionary
    """
    url = f"{base_url}{EXPLAIN_ENDPOINT}"
    payload = json.dumps({"user_id": user_id}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    # Add audience as query parameter
    if audience:
        if "?" in url:
            url = f"{url}&audience={audience}"
        else:
            url = f"{url}?audience={audience}"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  Error fetching explanation for {user_id}: {e.code} - {e.reason}")
        return {"error": str(e), "status_code": e.code}
    except Exception as e:
        print(f"  Error fetching explanation for {user_id}: {e}")
        return {"error": str(e)}


def sample_cases(cases: List[Dict[str, Any]], target_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    """
    Sample cases according to target distribution by risk level.

    Args:
        cases: All available cases
        target_counts: Target counts per risk level

    Returns:
        Sampled cases list
    """
    sampled = []

    for risk_level, target_count in target_counts.items():
        # Filter cases by risk level
        level_cases = [c for c in cases if c.get("risk_level") == risk_level]

        # Sample up to target count
        count = min(len(level_cases), target_count)
        sampled.extend(level_cases[:count])

        print(f"Sampled {count} {risk_level} cases (target: {target_count})")

    return sampled


def save_cases_csv(cases: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save cases to CSV file.

    Args:
        cases: List of case dictionaries
        output_path: Path to output CSV file
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "risk_level", "detected_at", "pipeline_run_id"])

        for case in cases:
            writer.writerow([
                case.get("user_id"),
                case.get("risk_level"),
                case.get("detected_at"),
                case.get("pipeline_run_id") or case.get("model_version") or "unknown"
            ])

    print(f"Saved {len(cases)} cases to {output_path}")


def save_raw_explanations(cases: List[Dict[str, Any]], base_url: str, output_dir: str) -> None:
    """
    Save raw explanation JSON files for each case.

    Args:
        cases: List of case dictionaries
        base_url: Base URL of the API
        output_dir: Directory to save raw explanations
    """
    os.makedirs(output_dir, exist_ok=True)

    for case in cases:
        user_id = case.get("user_id")
        if not user_id:
            continue

        print(f"Fetching explanation for {user_id}...")
        explanation = fetch_explanation(base_url, user_id)

        output_path = os.path.join(output_dir, f"{user_id}.json")
        with open(output_path, "w") as f:
            json.dump(explanation, f, indent=2)

    print(f"Saved {len(cases)} raw explanations to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Export evaluation set for /api/risk/explain"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Total number of cases to export (default: 30)"
    )
    parser.add_argument(
        "--out",
        default="eval/explain_eval_cases.csv",
        help="Output path for cases CSV (default: eval/explain_eval_cases.csv)"
    )
    parser.add_argument(
        "--raw-dir",
        default="eval/raw_explanations",
        help="Output directory for raw explanation JSON files (default: eval/raw_explanations)"
    )
    parser.add_argument(
        "--audience",
        default="investigator",
        choices=["investigator", "business"],
        help="Audience mode for explanations (default: investigator)"
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Skip fetching raw explanations (only export cases CSV)"
    )

    args = parser.parse_args()

    # Validate base URL
    if not args.base_url.startswith("http"):
        args.base_url = f"http://{args.base_url}"

    # Remove trailing slash
    args.base_url = args.base_url.rstrip("/")

    print(f"Fetching cases from {args.base_url}")
    print(f"Target count: {args.count}")
    print(f"Output: {args.out}")
    print()

    # Define target distribution
    # For 30 cases: CRITICAL=10, HIGH=15, MEDIUM=5
    total = args.count
    target_counts = {
        "CRITICAL": int(total * 0.33),
        "HIGH": int(total * 0.50),
        "MEDIUM": int(total * 0.17)
    }

    # Adjust for rounding
    total_allocated = sum(target_counts.values())
    if total_allocated < total:
        target_counts["HIGH"] += (total - total_allocated)

    # Fetch all cases
    print("Fetching cases from investigation queue...")
    cases = fetch_cases(args.base_url, list(target_counts.keys()))

    if not cases:
        print("No cases found. Please ensure:")
        print("  1. The backend is running")
        print("  2. The base URL is correct")
        print("  3. There are cases in the Needs Review queue")
        sys.exit(1)

    # Sample cases
    print()
    print("Sampling cases...")
    sampled_cases = sample_cases(cases, target_counts)

    # Save cases CSV
    save_cases_csv(sampled_cases, args.out)

    # Save raw explanations
    if not args.no_raw:
        print()
        print("Fetching raw explanations...")
        save_raw_explanations(sampled_cases, args.base_url, args.raw_dir)

    print()
    print("Export complete!")
    print()
    print("Next steps:")
    print("  1. Review the cases in:", args.out)
    print("  2. Review raw explanations in:", args.raw_dir)
    print("  3. Use explain_eval_results.csv to record evaluations")
    print("  4. Use explain_eval_summary.md to aggregate results")


if __name__ == "__main__":
    main()
