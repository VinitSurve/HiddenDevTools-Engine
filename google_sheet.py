import csv
import io
import logging

import requests

from config import *

logger = logging.getLogger(__name__)


# ==========================================================
# Sample Data (used if Google Sheet is unavailable)
# ==========================================================

SAMPLE_DATA = [
    {
        COL_ID: "GR001",
        COL_NAME: "Firecrawl",
        COL_LINK: "https://github.com/firecrawl/firecrawl",
        COL_DESC: "AI-ready web scraping and crawling infrastructure that converts websites into clean LLM-ready markdown.",
        COL_PRICING: "Free",
        COL_DIFFICULTY: "Intermediate",
        COL_SLIDE_NUM: "2",
        COL_WHY: "Firecrawl turns messy websites into structured AI-ready markdown so developers can build RAG applications, AI agents, chatbots and research systems without creating custom scraping pipelines.",
        COL_BEST_FOR1: "AI Engineers",
        COL_BEST_FOR2: "Startup Founders",
        COL_BEST_FOR3: "RAG Builders",
        COL_RATING: "9.4",
        COL_STATUS: "Published",
    }
]


# ==========================================================
# Fetch Google Sheet
# ==========================================================

def fetch_rows(timeout=15):

    try:

        response = requests.get(
            SHEET_PUBHTML_URL,
            timeout=timeout
        )

        response.raise_for_status()

        rows = parse_csv(response.text)

        if rows:
            print(f"Loaded {len(rows)} rows from Google Sheets.")
            return rows

        print("Google Sheet empty. Using sample data.")

    except Exception as e:

        print(e)
        print("Using sample data.")

    return SAMPLE_DATA


# ==========================================================
# Parse CSV
# ==========================================================

def parse_csv(text):

    reader = csv.DictReader(io.StringIO(text))

    rows = []

    for row in reader:

        clean = {}

        for key, value in row.items():

            if key is None:
                continue

            clean[key.strip()] = value.strip()

        if not clean.get(COL_ID):
            continue

        rows.append(clean)

    return rows
