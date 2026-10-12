import os
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from settings import STATUS_COLUMN
from config.app_config import config
from settings import SHEET_PUBHTML_URL
from settings import (
    STATUS_COLUMN,
    POST_COLUMN,
    GENERATED_AT_COLUMN,
    GENERATION_ID_COLUMN,
    DRIVE_FOLDER_ID_COLUMN,
    DRIVE_FOLDER_URL_COLUMN,
    INSTAGRAM_MEDIA_ID_COLUMN,
    INSTAGRAM_POST_URL_COLUMN,
    PUBLISHED_AT_COLUMN,
)


# ==========================================================
# Google API Scopes
# ==========================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ==========================================================
# Lazy Google Sheets Client & Spreadsheet
# ==========================================================

_client = None
_spreadsheet = None
_sheets = {}


def get_client():
    """Lazily load credentials and return an authorized gspread client."""
    global _client
    if _client is not None:
        return _client

    sa_file = config.services.google_sheets.service_account_file
    if not sa_file or not os.path.exists(sa_file):
        raise FileNotFoundError(f"Service account file not found: {sa_file}")

    creds = Credentials.from_service_account_file(
        sa_file,
        scopes=SCOPES
    )
    _client = gspread.authorize(creds)
    return _client


def set_client(client_instance):
    """Test seam: inject a mock or custom gspread client."""
    global _client, _spreadsheet, _sheets
    _client = client_instance
    _spreadsheet = None
    _sheets = {}


def reset_client():
    """Reset cached client and worksheet instances."""
    global _client, _spreadsheet, _sheets
    _client = None
    _spreadsheet = None
    _sheets = {}


def get_spreadsheet():
    """Lazily fetch and cache the target spreadsheet instance."""
    global _spreadsheet
    if _spreadsheet is not None:
        return _spreadsheet

    c = get_client()
    _spreadsheet = c.open_by_key(config.services.google_sheets.spreadsheet_id)
    return _spreadsheet


class _LazyClientProxy:
    """Proxy object so existing code accessing `sheet_api.client` works lazily without side effects."""
    def __getattr__(self, name):
        return getattr(get_client(), name)

    def __bool__(self):
        return True


class _LazySpreadsheetProxy:
    """Proxy object so existing code accessing `sheet_api.spreadsheet` works lazily without side effects."""
    def __getattr__(self, name):
        return getattr(get_spreadsheet(), name)

    def __bool__(self):
        return True


client = _LazyClientProxy()
spreadsheet = _LazySpreadsheetProxy()


def __getattr__(name):
    if name == "creds":
        sa_file = config.services.google_sheets.service_account_file
        if not sa_file or not os.path.exists(sa_file):
            raise FileNotFoundError(f"Service account file not found: {sa_file}")
        return Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# ==========================================================
# Extract Spreadsheet ID
# ==========================================================

def get_sheet_id():

    url = SHEET_PUBHTML_URL

    return url.split("/d/e/")[1].split("/")[0]


# ==========================================================
# Open Sheet
# ==========================================================

def open_sheet(sheet_name=None):

    global _sheets

    sheet = get_spreadsheet()

    if sheet_name is None:
        sheet_name = sheet.sheet1.title

    if sheet_name not in _sheets:

        _sheets[sheet_name] = sheet.worksheet(
            sheet_name
        )

    return _sheets[sheet_name]

# ==========================================================
# Get All Rows
# ==========================================================

def get_all_rows(sheet_name=None):

    ws = open_sheet(sheet_name)

    all_vals = ws.get_all_values()
    if not all_vals:
        return []
    
    headers = all_vals[0]
    rows = [dict(zip(headers, row)) for row in all_vals[1:]]

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

def get_draft_rows(limit=7, sheet_name=None):

    rows = get_all_rows(sheet_name)

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
    status,
    sheet_name=None,
):

    update_cell(
        sheet_name,
        row_number,
        STATUS_COLUMN,
        status,
    )

    print(
        f"Row {row_number} -> {status}"
    )

# ==========================================================
# Mark Rows as Generating
# ==========================================================

def mark_generating(rows, sheet_name=None):

    for row in rows:

        update_status(
            row["_row"],
            "Generating",
            sheet_name,
        )

    print()

    print(
        f"{len(rows)} rows marked as Generating."
    )



# ==========================================================
# Update Cell
# ==========================================================

def update_cell(
    sheet_name,
    row_number,
    column,
    value
):

    ws = open_sheet(sheet_name)

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
    post_name,
    sheet_name=None
):

    generation_id = generate_generation_id()

    timestamp = generated_timestamp()

    for row in rows:

        row_number = row["_row"]

        update_cell(
            sheet_name,
            row_number,
            STATUS_COLUMN,
            "Ready"
        )

        update_cell(
            sheet_name,
            row_number,
            POST_COLUMN,
            post_name
        )

        update_cell(
            sheet_name,
            row_number,
            GENERATED_AT_COLUMN,
            timestamp
        )

        update_cell(
            sheet_name,
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

def mark_generated(
    sheet_name,
    row_number,
    generation_id,
    generated_at,
    folder_id,
    folder_url,
):

    update_cell(
        sheet_name,
        row_number,
        STATUS_COLUMN,
        "Generated",
    )

    update_cell(
        sheet_name,
        row_number,
        GENERATED_AT_COLUMN,
        generated_at,
    )

    update_cell(
        sheet_name,
        row_number,
        GENERATION_ID_COLUMN,
        generation_id,
    )

    update_cell(
        sheet_name,
        row_number,
        DRIVE_FOLDER_ID_COLUMN,
        folder_id,
    )

    update_cell(
        sheet_name,
        row_number,
        DRIVE_FOLDER_URL_COLUMN,
        folder_url,
    )

    print(f"✓ Row {row_number} updated")


# ==========================================================
# Mark Rows as Published
# ==========================================================

def mark_published(
    sheet_name,
    row_number,
    media_id,
    post_url,
    published_at,
):
    """
    Update a row after successful Instagram publishing.

    Writes:
    - Status → "Published"
    - Instagram Media ID
    - Instagram Post URL
    - Published At timestamp
    """

    update_cell(
        sheet_name,
        row_number,
        STATUS_COLUMN,
        "Published",
    )

    update_cell(
        sheet_name,
        row_number,
        INSTAGRAM_MEDIA_ID_COLUMN,
        media_id,
    )

    update_cell(
        sheet_name,
        row_number,
        INSTAGRAM_POST_URL_COLUMN,
        post_url,
    )

    update_cell(
        sheet_name,
        row_number,
        PUBLISHED_AT_COLUMN,
        published_at,
    )

    print(f"✓ Row {row_number} → Published")


# ==========================================================
# Mark Rows as Failed
# ==========================================================

def mark_failed(
    sheet_name,
    row_number,
    error_message="",
):
    """
    Update a row after pipeline failure.

    Sets Status to "Failed" so it can be diagnosed
    and retried (by resetting to "Draft").
    """

    update_cell(
        sheet_name,
        row_number,
        STATUS_COLUMN,
        "Failed",
    )

    print(f"✗ Row {row_number} → Failed")
