from schedule import get_today_schedule
from sheet_api import get_draft_rows

today = get_today_schedule()

print(today)

rows = get_draft_rows(
    sheet_name=today["Sheet Name"],
    limit=7
)

print()

print(f"Loaded {len(rows)} rows")