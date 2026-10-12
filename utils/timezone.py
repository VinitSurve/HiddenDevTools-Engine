import datetime
from datetime import timezone, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    # Fallback to fixed offset if zoneinfo is unavailable
    IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now() -> datetime.datetime:
    """Return the current datetime localized to Asia/Kolkata (IST)."""
    return datetime.datetime.now(IST)

def get_ist_date_str(dt: Optional[datetime.datetime] = None) -> str:
    """Return date string 'YYYY-MM-DD' for the given datetime or current IST time."""
    target = dt if dt is not None else get_ist_now()
    if target.tzinfo is None:
        target = target.replace(tzinfo=IST)
    else:
        target = target.astimezone(IST)
    return target.strftime("%Y-%m-%d")

def get_ist_weekday(dt: Optional[datetime.datetime] = None) -> int:
    """Return 0-indexed weekday (0=Monday, 6=Sunday) for the given datetime or current IST time."""
    target = dt if dt is not None else get_ist_now()
    if target.tzinfo is None:
        target = target.replace(tzinfo=IST)
    else:
        target = target.astimezone(IST)
    return target.weekday()

def get_ist_day_name(dt: Optional[datetime.datetime] = None) -> str:
    """Return full day name (e.g. 'Monday') for the given datetime or current IST time."""
    target = dt if dt is not None else get_ist_now()
    if target.tzinfo is None:
        target = target.replace(tzinfo=IST)
    else:
        target = target.astimezone(IST)
    return target.strftime("%A")
