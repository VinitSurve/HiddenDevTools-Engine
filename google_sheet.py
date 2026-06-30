
"""
google_sheet.py

Fetches the published Google Sheet and returns a list of dictionaries.
Falls back to sample data if the sheet is unavailable.
"""

import csv
import io
import logging

import requests

from config import (
    SHEET_PUBHTML_URL,
    COL_ID,
    COL_NAME,
    COL_LINK,
    COL_DESC,
    COL_PRICING,
    COL_DIFFICULTY,
    COL_SLIDE_NUM,
    COL_WHY,
    COL_BEST_FOR1,
    COL_BEST_FOR2,
    COL_BEST_FOR3,
    COL_RATING,
    COL_STATUS,
)

logger = logging.getLogger(__name__)


SAMPLE_DATA = [
    {
        COL_ID: "GR001",
        COL_NAME: "Firecrawl",
        COL_LINK: "https://github.com/firecrawl/firecrawl",
        COL_DESC: "AI-ready web scraping and crawling infrastructure that converts websites into clean LLM-ready markdown.",
        COL_PRICING: "Free",
        COL_DIFFICULTY: "Intermediate",
        COL_SLIDE_NUM: "2",
        COL_WHY: "Firecrawl turns messy websites into structured, AI-ready markdown for LLM workflows.",
        COL_BEST_FOR1: "AI Engineers",
        COL_BEST_FOR2: "Startup Founders",
        COL_BEST_FOR3: "RAG Builders",
        COL_RATING: "9.4",
        COL_STATUS: "Draft",
    }
]


def _clean_row(row: dict) -> dict:
    """Trim whitespace and guarantee expected keys exist."""

    cleaned = {}

    for key, value in row.items():
        if key is None:
            continue
        cleaned[key.strip()] = value.strip() if value else ""

    expected = [
        COL_ID,
        COL_NAME,
        COL_LINK,
        COL_DESC,
        COL_PRICING,
        COL_DIFFICULTY,
        COL_SLIDE_NUM,
        COL_WHY,
        COL_BEST_FOR1,
        COL_BEST_FOR2,
        COL_BEST_FOR3,
        COL_RATING,
        COL_STATUS,
    ]

    for key in expected:
        cleaned.setdefault(key, "")

    return cleaned


def _parse_csv(csv_text: str):
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []

    for row in reader:
        row = _clean_row(row)

        if not row[COL_ID]:
            continue

        if not row[COL_NAME]:
            continue

        rows.append(row)

    return rows


def fetch_rows(timeout: int = 20):
    """
    Returns all rows from the published Google Sheet.
    """

    try:
        response = requests.get(
            SHEET_PUBHTML_URL,
            timeout=timeout
        )

        response.raise_for_status()

        rows = _parse_csv(response.text)

        if rows:
            print(f"Loaded {len(rows)} rows from Google Sheets.")
            return rows

        logger.warning("Sheet contained no valid rows.")

    except Exception as exc:
        logger.warning(
            "Using sample data because Google Sheet could not be loaded: %s",
            exc,
        )

    return SAMPLE_DATA
