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

def utc_to_ist(dt: datetime.datetime) -> datetime.datetime:
    """Convert UTC datetime (aware or naive) to Asia/Kolkata (IST)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)

def get_scheduled_publishing_target(
    now_ist: Optional[datetime.datetime] = None,
    scheduled_at: Optional[datetime.datetime | str] = None,
    scheduled_hour: int = 19,
    scheduled_minute: int = 0,
    max_delay_hours: float = 24.0
) -> dict:
    """
    Computes the intended publishing target date and weekday for schedule-aware execution.
    The daily publishing slot for calendar date D opens at scheduled_hour:scheduled_minute IST.
    Any execution starting between day D 19:00 IST and day D+1 19:00 IST belongs to
    day D's publishing window.

    If scheduled_at is provided, the intended slot is derived from the scheduled/dispatch time,
    and any execution occurring after scheduled_slot + max_delay_hours is marked as expired
    to prevent publishing stale content or colliding with the subsequent day's slot.
    """
    current = now_ist if now_ist is not None else get_ist_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=IST)
    else:
        current = current.astimezone(IST)

    # If trigger/scheduled timestamp is provided, determine intended target slot from it
    if scheduled_at is not None:
        if isinstance(scheduled_at, str):
            clean_ts = scheduled_at.strip()
            if clean_ts.endswith("Z"):
                clean_ts = clean_ts[:-1] + "+00:00"
            trigger_dt = datetime.datetime.fromisoformat(clean_ts)
        else:
            trigger_dt = scheduled_at

        trigger_ist = utc_to_ist(trigger_dt)
        is_trigger_at_or_after = (
            trigger_ist.hour > scheduled_hour or
            (trigger_ist.hour == scheduled_hour and trigger_ist.minute >= scheduled_minute)
        )
        if is_trigger_at_or_after:
            target_date = trigger_ist.date()
        else:
            target_date = trigger_ist.date() - timedelta(days=1)
        is_next_day_rollover = (current.date() > target_date)
    else:
        is_at_or_after_slot = (
            current.hour > scheduled_hour or
            (current.hour == scheduled_hour and current.minute >= scheduled_minute)
        )
        if is_at_or_after_slot:
            target_date = current.date()
            is_next_day_rollover = False
        else:
            # Before 19:00 IST: execution belongs to yesterday's 19:00 IST slot
            target_date = current.date() - timedelta(days=1)
            is_next_day_rollover = True

    scheduled_slot_ist = datetime.datetime.combine(
        target_date,
        datetime.time(scheduled_hour, scheduled_minute)
    ).replace(tzinfo=IST)

    delay_seconds = max(0.0, (current - scheduled_slot_ist).total_seconds())
    is_delayed = delay_seconds > 900.0  # > 15 minutes threshold
    is_expired = delay_seconds >= (max_delay_hours * 3600.0)

    hours, remainder = divmod(int(delay_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        delay_human = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        delay_human = f"{minutes}m {seconds}s"
    else:
        delay_human = f"{seconds}s"

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    target_weekday = target_date.weekday()

    return {
        "target_date_str": target_date.strftime("%Y-%m-%d"),
        "target_date": target_date,
        "target_weekday": target_weekday,
        "target_day_name": day_names[target_weekday],
        "scheduled_slot_ist": scheduled_slot_ist,
        "execution_time_ist": current,
        "delay_seconds": delay_seconds,
        "delay_human": delay_human,
        "is_delayed": is_delayed,
        "is_next_day_rollover": is_next_day_rollover,
        "is_expired": is_expired,
        "slot_deadline_ist": scheduled_slot_ist + timedelta(hours=max_delay_hours)
    }
