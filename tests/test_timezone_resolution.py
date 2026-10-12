import pytest
import datetime
from datetime import timezone
from utils.timezone import (
    IST,
    get_ist_now,
    get_ist_date_str,
    get_ist_weekday,
    get_ist_day_name
)
from scheduler.content_selector import ContentSelector
from scheduler.orchestrator import SchedulerOrchestrator

def test_timezone_boundary_sunday_utc_to_monday_ist(monkeypatch):
    """
    Test UTC/IST boundary:
    Sunday 2026-10-11 19:00:00 UTC corresponds to Monday 2026-10-12 00:30:00 IST.
    A UTC system clock would say Sunday, but Asia/Kolkata must resolve to Monday.
    """
    sunday_utc = datetime.datetime(2026, 10, 11, 19, 0, 0, tzinfo=timezone.utc)
    
    # Mock get_ist_now to return the localized IST datetime
    monkeypatch.setattr("utils.timezone.get_ist_now", lambda: sunday_utc.astimezone(IST))
    
    assert get_ist_date_str() == "2026-10-12"
    assert get_ist_weekday() == 0  # Monday
    assert get_ist_day_name() == "Monday"
    
    # Content selector must resolve to Monday's niche (github_repo), NOT Sunday
    niche = ContentSelector.get_todays_niche()
    assert niche == "github_repo"

def test_timezone_boundary_monday_late_evening_utc_to_tuesday_ist(monkeypatch):
    """
    Test midnight rollover boundary:
    Monday 2026-10-12 18:35:00 UTC corresponds to Tuesday 2026-10-13 00:05:00 IST.
    Must resolve to Tuesday (weekday 1) and tools_websites.
    """
    monday_late_utc = datetime.datetime(2026, 10, 12, 18, 35, 0, tzinfo=timezone.utc)
    
    monkeypatch.setattr("utils.timezone.get_ist_now", lambda: monday_late_utc.astimezone(IST))
    
    assert get_ist_date_str() == "2026-10-13"
    assert get_ist_weekday() == 1  # Tuesday
    assert get_ist_day_name() == "Tuesday"
    
    niche = ContentSelector.get_todays_niche()
    assert niche == "tools_websites"

def test_explicit_overrides_bypass_clock(monkeypatch):
    """Ensure explicit --day and --date overrides take precedence over clock time."""
    # Regardless of what clock returns:
    monday_utc = datetime.datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("utils.timezone.get_ist_now", lambda: monday_utc.astimezone(IST))
    
    # Override day 3 (Thursday -> prompt_library)
    assert ContentSelector.get_todays_niche(override_day=3) == "prompt_library"
    # Override day 6 (Sunday -> None)
    assert ContentSelector.get_todays_niche(override_day=6) is None
