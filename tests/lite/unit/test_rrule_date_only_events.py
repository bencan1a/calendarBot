"""Test date-only event parsing in RRULE expander.

This test specifically tests the fix for the crash that occurs when
parsing all-day recurring events (birthdays, holidays).
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path

from calendarbot_lite.calendar.lite_parser import LiteICSParser

pytestmark = pytest.mark.unit


@pytest.fixture
def test_ics_dir():
    """Get the path to test ICS fixtures directory."""
    return Path(__file__).parent.parent.parent / "fixtures" / "ics"


def test_recurring_all_day_birthday_parsing(simple_settings, test_ics_dir):
    """Test that recurring all-day events (birthdays) can be parsed without crashing.

    This tests the fix for date-only event parsing in the fallback parser
    at lite_rrule_expander.py:936-943.
    """
    parser = LiteICSParser(simple_settings)

    # Load the birthday fixture
    ics_path = test_ics_dir / "recurring-all-day-birthday.ics"
    with open(ics_path, "r") as f:
        ics_content = f.read()

    # This should not crash
    result = parser.parse_ics_content(ics_content)

    # Should have succeeded and expanded the recurring event
    assert result.success is True, f"Parse failed: {result.error_message}"
    assert len(result.events) > 0, "Should have parsed at least one event"

    # Check the first event
    first_event = result.events[0]
    assert first_event.subject == "John's Birthday"
    assert first_event.is_all_day is True


def test_recurring_all_day_holiday_parsing(simple_settings, test_ics_dir):
    """Test that recurring all-day events (holidays) can be parsed without crashing.

    This tests the fix for date-only event parsing in the fallback parser
    at lite_rrule_expander.py:936-943.
    """
    parser = LiteICSParser(simple_settings)

    # Load the holiday fixture
    ics_path = test_ics_dir / "recurring-all-day-holiday.ics"
    with open(ics_path, "r") as f:
        ics_content = f.read()

    # This should not crash
    result = parser.parse_ics_content(ics_content)

    # Should have succeeded and expanded the recurring event
    assert result.success is True, f"Parse failed: {result.error_message}"
    assert len(result.events) > 0, "Should have parsed at least one event"

    # Check the first event
    first_event = result.events[0]
    assert first_event.subject == "Independence Day"
    assert first_event.is_all_day is True


def test_mixed_datetime_and_date_events(simple_settings, test_ics_dir):
    """Test parsing a calendar with both datetime and date-only events.

    This ensures the fix doesn't break normal datetime events while
    also handling date-only events correctly.
    """
    parser = LiteICSParser(simple_settings)

    # Create a calendar with both types
    mixed_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
METHOD:PUBLISH
BEGIN:VEVENT
UID:datetime-event@example.com
DTSTAMP:20250101T000000Z
DTSTART:20250315T140000Z
DTEND:20250315T150000Z
SUMMARY:Team Meeting
RRULE:FREQ=WEEKLY;COUNT=5
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
UID:date-event@example.com
DTSTAMP:20250101T000000Z
DTSTART;VALUE=DATE:20250315
DTEND;VALUE=DATE:20250316
SUMMARY:Birthday
RRULE:FREQ=YEARLY;COUNT=5
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    # This should not crash
    result = parser.parse_ics_content(mixed_ics)

    # Should have succeeded and expanded both recurring events
    assert result.success is True, f"Parse failed: {result.error_message}"
    events = result.events
    assert len(events) >= 7, f"Should have at least 7 events (5 weekly + 2 yearly in window), got {len(events)}"

    # Find the datetime and date events
    meeting_events = [e for e in events if e.subject == "Team Meeting"]
    birthday_events = [e for e in events if e.subject == "Birthday"]

    assert len(meeting_events) >= 5, f"Should have at least 5 meeting events, got {len(meeting_events)}"
    assert len(birthday_events) >= 2, f"Should have at least 2 birthday events, got {len(birthday_events)}"

    # Check properties
    assert meeting_events[0].is_all_day is False, "Meeting should not be all-day"
    assert birthday_events[0].is_all_day is True, "Birthday should be all-day"
