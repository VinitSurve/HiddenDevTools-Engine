"""
test_instagram.py

Diagnostic verification script for Instagram Graph API connection, token scopes, and node resolution.
Run this script to diagnose why direct IG node queries return Code 100 Subcode 33 vs nested Page queries.
"""

import json
from services.instagram_service import InstagramService


def run_diagnostic():
    print("=" * 60)
    print("HIDDEN DEV TOOLS — INSTAGRAM GRAPH API DIAGNOSTIC")
    print("=" * 60)

    instagram = InstagramService()

    # 1. Run Diagnostic Tests
    results = instagram.test_connection()

    print("\n--- Diagnostic Results ---")
    print(json.dumps(results, indent=2))

    # 2. Test get_account_info (with fallback)
    print("\n--- Account Info Resolution Test ---")
    info = instagram.get_account_info()
    print(json.dumps(info, indent=2))

    print("\n============================================================")
    print("RECOMMENDED ACTION:")
    print(results.get("recommended_action", "Check logs above."))
    print("============================================================")


if __name__ == "__main__":
    run_diagnostic()