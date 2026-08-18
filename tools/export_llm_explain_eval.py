#!/usr/bin/env python3
"""
Export LLM Explanation Outputs for Evaluation Cases

This script regenerates explanation outputs for the existing evaluation
case set. Unlike export_explain_eval_set.py, it does NOT sample: it reads
every user_id from eval/explain_eval_cases.csv and calls /api/risk/explain
via the explicit regenerate endpoint so each explanation is produced fresh.

Usage:
    python tools/export_llm_explain_eval.py \\
        --base-url http://localhost:8000 \\
        --cases eval/explain_eval_cases.csv \\
        --out-dir eval/llm_raw_explanations
"""
import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


# API endpoint configuration - easy to change if endpoints differ
EXPLAIN_ENDPOINT = "/api/risk/explain/regenerate"  # explicit regeneration (bypass_cache no longer forces fresh generation)


def read_user_ids(cases_path: str) -> List[str]:
    """
    Read the user_id column from the evaluation cases CSV.

    Args:
        cases_path: Path to the cases CSV file

    Returns:
        List of user_id strings, in CSV order. Duplicates are preserved.
    """
    cases_path = Path(cases_path)
    user_ids: List[str] = []

    with cases_path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if "user_id" not in (reader.fieldnames or []):
            print(f"Error: 'user_id' column not found in {cases_path}")
            print(f"  Found columns: {reader.fieldnames}")
            sys.exit(1)

        for row in reader:
            user_id = (row.get("user_id") or "").strip()
            if user_id:
                user_ids.append(user_id)

    return user_ids


def fetch_explanation(
    base_url: str,
    user_id: str,
    audience: str = "investigator",
) -> Dict[str, Any]:
    """
    Fetch a fresh explanation for a specific user.

    Calls the explicit POST /api/risk/explain/regenerate endpoint so the
    server always generates a NEW explanation (bypass_cache on /explain no
    longer forces regeneration — it only skips the in-memory cache tier and
    the persisted canonical explanation is still served).

    Args:
        base_url: Base URL of the API (e.g. http://localhost:8000)
        user_id: User ID to fetch the explanation for
        audience: Audience mode for the explanation (default: investigator)

    Returns:
        Explanation response dictionary, or an error dictionary on failure.
    """
    params = {"audience": audience}
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}{EXPLAIN_ENDPOINT}?{query_string}"

    payload = json.dumps({"user_id": user_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        reason = e.reason
        body = ""
        try:
            body = e.read().decode(errors="replace")
        except Exception:
            pass
        return {
            "error": f"HTTP {e.code} {reason}",
            "status_code": e.code,
            "body": body,
        }
    except urllib.error.URLError as e:
        return {"error": f"URL error: {e.reason}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def save_explanation(
    out_dir: Path,
    user_id: str,
    data: Dict[str, Any],
) -> Path:
    """
    Save a full explanation JSON response to {out_dir}/{user_id}.json.

    Args:
        out_dir: Output directory (created if missing)
        user_id: User ID used for the filename
        data: JSON-serializable response payload

    Returns:
        Path to the written file.
    """
    output_path = out_dir / f"{user_id}.json"
    with output_path.open("w") as f:
        json.dump(data, f, indent=2)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export LLM explanation outputs for the existing eval case set"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--cases",
        default="eval/explain_eval_cases.csv",
        help="Path to the eval cases CSV with a user_id column "
        "(default: eval/explain_eval_cases.csv)",
    )
    parser.add_argument(
        "--out-dir",
        default="eval/llm_raw_explanations",
        help="Output directory for per-user_id JSON files "
        "(default: eval/llm_raw_explanations)",
    )
    parser.add_argument(
        "--audience",
        default="investigator",
        choices=["investigator", "business"],
        help="Audience mode for explanations (default: investigator)",
    )

    args = parser.parse_args()

    # Validate base URL
    base_url = args.base_url
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    base_url = base_url.rstrip("/")

    out_dir = Path(args.out_dir)

    print(f"Base URL: {base_url}")
    print(f"Cases CSV: {args.cases}")
    print(f"Output dir: {out_dir}")
    print(f"Audience: {args.audience} (explicit regeneration)")
    print()

    # Read cases - fatal error if the CSV cannot be read or is empty
    try:
        user_ids = read_user_ids(args.cases)
    except FileNotFoundError:
        print(f"Error: cases CSV not found: {args.cases}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: failed to read cases CSV: {e}")
        sys.exit(1)

    if not user_ids:
        print(f"Error: no user_id rows found in {args.cases}")
        sys.exit(1)

    print(f"Loaded {len(user_ids)} case(s) from {args.cases}")
    print()

    # Create output directory if missing
    out_dir.mkdir(parents=True, exist_ok=True)

    # Fetch and save a fresh explanation for every case
    total = len(user_ids)
    successes = 0
    failures: List[Dict[str, str]] = []

    print(f"Fetching {total} explanation(s) via explicit regeneration...")
    for index, user_id in enumerate(user_ids, start=1):
        print(f"[{index}/{total}] {user_id} ... ", end="", flush=True)
        explanation = fetch_explanation(base_url, user_id, audience=args.audience)

        is_error = isinstance(explanation, dict) and "error" in explanation
        if is_error:
            failures.append(
                {"user_id": user_id, "error": str(explanation.get("error"))}
            )
            print(f"FAILED ({explanation.get('error')})")
        else:
            successes += 1
            print("OK")

        save_explanation(out_dir, user_id, explanation)

    # Summary
    print()
    print(f"Done: {successes}/{total} succeeded, {len(failures)} failed")
    print(f"Saved outputs to: {out_dir}/")

    if failures:
        print()
        print("Failed cases:")
        for failure in failures:
            print(f"  - {failure['user_id']}: {failure['error']}")
        # Incomplete eval set - signal the problem to the operator
        sys.exit(1)


if __name__ == "__main__":
    main()
