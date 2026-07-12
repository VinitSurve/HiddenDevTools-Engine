from datetime import datetime

from sheet_api import open_sheet


def get_today_schedule():

    today = datetime.now().strftime("%A")

    ws = open_sheet("Publishing Calendar")

    rows = ws.get_all_records()

    for row in rows:

        if row["Day"].strip() == today:

            return row

    return None