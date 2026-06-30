import gspread
from google.oauth2.service_account import Credentials

from config import SHEET_PUBHTML_URL, SHEET_PUBHTML_URL, SPREADSHEET_ID

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

def open_sheet():

    spreadsheet = client.open_by_key(
        SPREADSHEET_ID
    )

    worksheet = spreadsheet.sheet1

    return worksheet

# ==========================================================
# Get All Rows
# ==========================================================

def get_all_rows():

    ws = open_sheet()

    rows = ws.get_all_records()

    print(f"Loaded {len(rows)} rows from Google Sheets.")

    return rows