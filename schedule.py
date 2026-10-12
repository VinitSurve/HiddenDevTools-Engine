from datetime import datetime

from sheet_api import open_sheet


def get_today_schedule():

    from utils.timezone import get_ist_day_name
    today = get_ist_day_name()

    ws = open_sheet("Publishing Calendar")

    rows = ws.get_all_records()

    for row in rows:

        if row["Day"].strip() == today:

            return row

    return None