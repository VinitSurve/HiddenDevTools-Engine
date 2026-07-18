"""
main.py

HiddenDevTools Engine

Entry point for generating one complete Instagram carousel
from the next Draft repositories in Google Sheets.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from settings import OUTPUT_DIR
from sheet_api import (
    get_draft_rows,
    mark_generating,
    mark_ready,
)
from generator import generate_post
from utils import get_next_post_name
from settings import STATUS_COLUMN
from schedule import get_today_schedule





# ==========================================================
# Main
# ==========================================================

def main():

    today = get_today_schedule()

    if today is None:

        print("No schedule found.")

        return

    draft_rows = get_draft_rows(limit=7)

    if not draft_rows:
        print("No Draft rows found.")
        return

    mark_generating(draft_rows)

    post_name = get_next_post_name(OUTPUT_DIR)

    print(f"Creating {post_name}")

    generate_post(
        draft_rows=draft_rows,
        post_name=post_name
    )

    mark_ready(
        draft_rows,
        post_name
    )

    print("\n✅ Post generated successfully!")


# ==========================================================
# Entry Point
# ==========================================================

if __name__ == "__main__":

    main()