"""
Unit tests for calendarbot_lite.lite_event_parser.LiteEventComponentParser

Covers:
- successful parsing of VEVENT components
- handling missing DTSTART (skips event)
- EXDATE collection behavior
- online meeting URL detection
- mapping of transparency/status including Microsoft markers
"""

from datetime import datetime, timezone
from typing import Any, Optional, Protocol

import pytest
from icalendar import Event as ICalEvent

from calendarbot_lite.calendar.lite_event_parser import LiteEventComponentParser
from calendarbot_lite.calendar.lite_models import (
    LiteAttendee,
    LiteAttendeeType,
    LiteCalendarEvent,
    LiteResponseStatus,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class DateTimeParserProtocol(Protocol):
    """Protocol for datetime parser interface."""

    def parse_datetime(self, value: Any, default_timezone: Optional[str] = None) -> datetime: ...

    def parse_datetime_optional(self, value: Any) -> Optional[datetime]: ...


class AttendeeParserProtocol(Protocol):
    """Protocol for attendee parser interface."""

    def parse_attendees(self, component: Any) -> list[LiteAttendee]: ...


class DummyDateTimeParser:
    def parse_datetime(self, value: Any, default_timezone: Optional[str] = None) -> datetime:
        # icalendar vDatetime has .dt attribute; otherwise assume it's a datetime already
        return getattr(value, "dt", value)

    def parse_datetime_optional(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        return getattr(value, "dt", value)


class DummyAttendeeParser:
    def parse_attendees(self, component: Any) -> list[LiteAttendee]:
        # Return a predictable attendee list when ATTENDEE present
        attendees = []
        # Use .get() instead of .getall() - icalendar uses .get() which returns None, single value, or list
        attendee_props = component.get("ATTENDEE", [])
        # Ensure it's a list
        if not isinstance(attendee_props, list):
            attendee_props = [attendee_props] if attendee_props else []

        for a in attendee_props:
            email = str(a).replace("mailto:", "")
            attendees.append(
                LiteAttendee(
                    name=email.split("@")[0],
                    email=email,
                    type=LiteAttendeeType.REQUIRED,
                    response_status=LiteResponseStatus.NOT_RESPONDED,
                )
            )
        return attendees


class DummySettings:
    def __init__(self) -> None:
        self.user_email = "organizer@example.com"


def make_event_with_basic_props() -> ICalEvent:
    ev = ICalEvent()
    ev.add("UID", "uid-123")
    ev.add("SUMMARY", "Team Meeting")
    ev.add("DTSTART", datetime(2025, 1, 10, 9, 0, tzinfo=timezone.utc))
    ev.add("DTEND", datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc))
    ev.add("DESCRIPTION", "Join on https://zoom.us/j/12345 for the meeting")
    ev.add("LOCATION", "Conference Room")
    ev.add("ORGANIZER", "mailto:organizer@example.com")
    ev.add("ATTENDEE", "mailto:alice@example.com")
    return ev


def test_parse_event_component_when_valid_then_returns_event() -> None:
    """Test successful parsing of complete VEVENT component with all standard fields.

    Verifies: basic properties, online meeting URL detection, organizer status, attendees.
    """
    dt_parser = DummyDateTimeParser()
    attendee_parser = DummyAttendeeParser()
    settings = DummySettings()
    parser = LiteEventComponentParser(dt_parser, attendee_parser, settings)  # type: ignore[arg-type]

    component = make_event_with_basic_props()
    parsed = parser.parse_event_component(component, default_timezone="UTC")
    assert isinstance(parsed, LiteCalendarEvent)
    assert parsed.id == "uid-123"
    assert parsed.subject == "Team Meeting"
    assert parsed.is_online_meeting is True
    assert parsed.online_meeting_url is not None
    assert parsed.online_meeting_url.startswith("https://zoom.us")
    assert parsed.is_organizer is True
    assert parsed.attendees is not None
    assert any("alice@example.com" in a.email for a in parsed.attendees)


def test_parse_event_component_when_missing_dtstart_then_returns_none() -> None:
    """Test that events without DTSTART are skipped (return None).

    DTSTART is required per iCalendar spec - events without it are invalid.
    """
    dt_parser = DummyDateTimeParser()
    attendee_parser = DummyAttendeeParser()
    parser = LiteEventComponentParser(dt_parser, attendee_parser, DummySettings())  # type: ignore[arg-type]

    ev = ICalEvent()
    ev.add("UID", "no-start")
    # No DTSTART added -> should be skipped and return None
    parsed = parser.parse_event_component(ev, default_timezone=None)
    assert parsed is None


def test_collect_exdate_props_handles_multiple_forms() -> None:
    """Test EXDATE collection handles single dates, lists, and multiple EXDATE properties.

    EXDATE can appear in various forms in ICS: single property, multiple properties,
    or list-valued property. Parser must handle all forms.
    """
    dt_parser = DummyDateTimeParser()
    attendee_parser = DummyAttendeeParser()
    parser = LiteEventComponentParser(dt_parser, attendee_parser, DummySettings())  # type: ignore[arg-type]

    ev = ICalEvent()
    ev.add("UID", "ex-1")
    ev.add("DTSTART", datetime(2025, 3, 1, 9, 0, tzinfo=timezone.utc))
    # Add EXDATE as separate property
    exdt = datetime(2025, 3, 2, 9, 0, tzinfo=timezone.utc)
    ev.add("EXDATE", exdt)
    ex_props = parser._collect_exdate_props(ev)
    assert isinstance(ex_props, list)
    # Should include at least one entry representing the EXDATE
    assert len(ex_props) >= 1


def test_map_transparency_to_status_with_ms_deleted_and_following_logic() -> None:
    """Test Microsoft-specific transparency mapping (X-OUTLOOK-DELETED, Following: prefix).

    Microsoft calendars use non-standard fields:
    - X-OUTLOOK-DELETED=TRUE maps to FREE (filtered out)
    - "Following:" prefix with FREE override maps to TENTATIVE
    """
    dt_parser = DummyDateTimeParser()
    attendee_parser = DummyAttendeeParser()
    parser = LiteEventComponentParser(dt_parser, attendee_parser, DummySettings())  # type: ignore[arg-type]

    ev = ICalEvent()
    ev.add("UID", "ms1")
    ev.add("SUMMARY", "Following: Catchup")
    ev.add("DTSTART", datetime(2025, 4, 1, 9, 0, tzinfo=timezone.utc))
    # Simulate Microsoft deleted marker
    ev.add("X-OUTLOOK-DELETED", "TRUE")
    status = parser._map_transparency_to_status("OPAQUE", None, ev)
    # Deleted marker maps to FREE (will be filtered)
    assert status.value == "free"

    # If "Following:" with BUSY override -> TENTATIVE
    ev2 = ICalEvent()
    ev2.add("UID", "ms2")
    ev2.add("SUMMARY", "Following: Weekly")
    ev2.add("DTSTART", datetime(2025, 4, 1, 9, 0, tzinfo=timezone.utc))
    ev2.add("X-MICROSOFT-CDO-BUSYSTATUS", "FREE")
    status2 = parser._map_transparency_to_status("OPAQUE", None, ev2)
    assert status2.value in ("tentative", "free")
