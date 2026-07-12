import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    # Fallback to fixed offset if zoneinfo is unavailable or timezone database missing
    IST = timezone(timedelta(hours=5, minutes=30))

from sheet_api import open_sheet

logger = logging.getLogger(__name__)

class CalendarService:
    @staticmethod
    def get_today_schedule(calendar_rows: Optional[List[Dict]] = None, target_dt: Optional[datetime] = None) -> Optional[Dict]:
        """
        Determine the current day in IST and fetch the corresponding enabled schedule row from Publishing Calendar.
        If target_dt is provided, uses its weekday instead of current IST time.
        """
        if target_dt is not None:
            today = target_dt.strftime("%A")
        else:
            today = datetime.now(IST).strftime("%A")

        if today == "Sunday":
            logger.info(f"UNSUPPORTED_PHASE_DAY: Today is {today} (Weekly Roundup is outside Phase 5A scope). Exiting cleanly.")
            return None

        if calendar_rows is None:
            try:
                ws = open_sheet("Publishing Calendar")
                calendar_rows = ws.get_all_records()
            except Exception as e:
                logger.error(f"Failed to fetch Publishing Calendar: {e}")
                raise

        matching_row = None
        for row in calendar_rows:
            if str(row.get("Day", "")).strip() == today:
                matching_row = row
                break

        if matching_row is None:
            logger.warning(f"NO_CALENDAR_ROW_FOR_DAY: No schedule row found for {today}.")
            return None

        enabled_val = matching_row.get("Enabled", "")
        if isinstance(enabled_val, bool):
            is_enabled = enabled_val
        else:
            is_enabled = str(enabled_val).strip().upper() == "TRUE"

        if not is_enabled:
            logger.info(f"PUBLISHING_DAY_DISABLED: Schedule row for {today} has Enabled={enabled_val}.")
            return None

        return matching_row
