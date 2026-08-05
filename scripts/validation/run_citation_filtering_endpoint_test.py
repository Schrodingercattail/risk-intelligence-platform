#!/usr/bin/env python3
"""
Direct API test for citation filtering.

This script calls the /api/risk/explain endpoint directly
to verify that unused citations are filtered out.
"""
import os
import requests
import json

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
TEST_USER_ID = os.getenv("TEST_USER_ID", "U00010")  # Change to test different users

def test_explain_endpoint():
    """Test the /api/risk/explain endpoint."""
    url = f"{API_BASE_URL}/api/risk/explain?bypass_cache=true&audience=investigator"

    payload = {
        "user_id": TEST_USER_ID
    }

    print(f"Testing /api/risk/explain for user: {TEST_USER_ID}")
    print(f"URL: {url}")
    print()

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        print("=" * 60)
        print("API RESPONSE")
        print("=" * 60)
        print()

        # Check summary
        print(f"Summary: {data.get('summary', '')[:100]}...")
        print()

        # Check key_findings
        key_findings = data.get('key_findings', [])
        print(f"Key Findings ({len(key_findings)}):")
        for i, finding in enumerate(key_findings, 1):
            print(f"  {i}. {finding}")
        print()

        # Check citations
        citations = data.get('citations', [])
        print(f"Citations ({len(citations)}):")
        for cit in citations:
            print(f"  [{cit.get('id')}] {cit.get('doc')} - {cit.get('section')}")
        print()

        # Extract all citation marks from text
        import re
        all_marks = set()
        for text in [data.get('summary', '')] + key_findings + [data.get('recommended_action', '')]:
            marks = re.findall(r'\[(\d+)\]', text)
            all_marks.update(int(m) for m in marks)

        all_citation_ids = set(c.get('id') for c in citations)
        unused = all_citation_ids - all_marks

        print("=" * 60)
        print("VALIDATION")
        print("=" * 60)
        print(f"Citation marks in text: {sorted(all_marks)}")
        print(f"Citation IDs in response: {sorted(all_citation_ids)}")
        print(f"Unused citations: {sorted(unused) if unused else 'NONE'}")
        print()

        if len(unused) > 0:
            print("❌ FAIL: Found unused citations in API response!")
            print(f"   {len(unused)} citations are not referenced in the text")
            return False
        else:
            print("✅ SUCCESS: All citations are used in the text!")
            return True

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API server.")
        print(f"   Make sure the backend is running at {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = test_explain_endpoint()
    sys.exit(0 if success else 1)
