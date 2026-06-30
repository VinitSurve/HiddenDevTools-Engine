import gspread
from google.oauth2.service_account import Credentials
from config import STATUS_COLUMN
from datetime import datetime
from config import SHEET_PUBHTML_URL, SHEET_PUBHTML_URL, SPREADSHEET_ID
from config import (
    STATUS_COLUMN,
    POST_COLUMN,
    GENERATED_AT_COLUMN,
    GENERATION_ID_COLUMN,
)

# ==========================================================
# Google API Scopes
# ==========================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ==========================================================
# Credentials
# ==========================================================

creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)


# ==========================================================
# Extract Spreadsheet ID
# ==========================================================

def get_sheet_id():

    url = SHEET_PUBHTML_URL

    return url.split("/d/e/")[1].split("/")[0]


# ==========================================================
# Open Sheet
# ==========================================================

_sheet = None

def open_sheet():

    global _sheet

    if _sheet is None:

        spreadsheet = client.open_by_key(
            SPREADSHEET_ID
        )

        _sheet = spreadsheet.sheet1

    return _sheet

# ==========================================================
# Get All Rows
# ==========================================================

def get_all_rows():

    ws = open_sheet()

    rows = ws.get_all_records()

    for index, row in enumerate(rows):

        # Actual Google Sheet row number
        # (+2 because row 1 is headers)
        row["_row"] = index + 2

    print(
        f"Loaded {len(rows)} rows from Google Sheets."
    )

    return rows

# ==========================================================
# Get Draft Rows
# ==========================================================

def get_draft_rows(limit=7):

    rows = get_all_rows()

    drafts = []

    for row in rows:

        status = str(
            row.get("Status", "")
        ).strip().lower()

        if status == "draft":

            drafts.append(row)

        if len(drafts) == limit:
            break

    print(
        f"Found {len(drafts)} draft rows."
    )

    return drafts

# ==========================================================
# Update Status
# ==========================================================

def update_status(
    row_number,
    status
):

    ws = open_sheet()

    update_cell(
    row_number,
    STATUS_COLUMN,
    status
)

    print(
        f"Row {row_number} -> {status}"
    )

# ==========================================================
# Mark Rows as Generating
# ==========================================================

def mark_generating(rows):

    for row in rows:

        update_status(
            row["_row"],
            "Generating"
        )

    print()

    print(
        f"{len(rows)} rows marked as Generating."
    )

def mark_generating(rows):

    for row in rows:

        update_status(
            row["_row"],
            "Generating"
        )

    print()

    print(f"{len(rows)} rows marked as Generating.")

# ==========================================================
# Update Cell
# ==========================================================

def update_cell(
    row_number,
    column,
    value
):

    ws = open_sheet()

    ws.update_acell(
        f"{column}{row_number}",
        value
    )
    
# ==========================================================
# Generation ID
# ==========================================================

def generate_generation_id():

    return datetime.now().strftime(
        "GEN_%Y%m%d_%H%M%S"
    )

# ==========================================================
# Generated Timestamp
# ==========================================================

def generated_timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

# ==========================================================
# Mark Rows as Ready
# ==========================================================

def mark_ready(
    rows,
    post_name
):

    generation_id = generate_generation_id()

    timestamp = generated_timestamp()

    for row in rows:

        row_number = row["_row"]

        update_cell(
            row_number,
            STATUS_COLUMN,
            "Ready"
        )

        update_cell(
            row_number,
            POST_COLUMN,
            post_name
        )

        update_cell(
            row_number,
            GENERATED_AT_COLUMN,
            timestamp
        )

        update_cell(
            row_number,
            GENERATION_ID_COLUMN,
            generation_id
        )

        print(
            f'{row["ID"]} -> Ready'
        )

    print()

    print(
        f"{len(rows)} rows marked as Ready."
    )