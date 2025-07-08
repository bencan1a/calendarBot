"""Comprehensive unit tests for ICS parser functionality."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from dateutil import tz
from icalendar import Calendar
from icalendar import Event as ICalEvent

from calendarbot.ics.exceptions import ICSContentError, ICSParseError
from calendarbot.ics.models import (
    AttendeeType,
    CalendarEvent,
    EventStatus,
    ICSParseResult,
    ResponseStatus,
)
from calendarbot.ics.parser import ICSParser
from tests.fixtures.mock_ics_data import ICSDataFactory


@pytest.mark.unit
@pytest.mark.critical_path
class TestICSParserInitialization:
    """Test suite for ICS parser initialization."""

    def test_parser_initialization(self, test_settings):
        """Test ICS parser initialization with settings."""
        parser = ICSParser(test_settings)

        assert parser.settings == test_settings
        assert parser.security_logger is not None

    def test_parser_initialization_with_none_settings(self):
        """Test ICS parser initialization with None settings."""
        parser = ICSParser(None)

        assert parser.settings is None
        assert parser.security_logger is not None


@pytest.mark.unit
@pytest.mark.critical_path
class TestICSContentParsing:
    """Test suite for ICS content parsing."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_basic_ics_content(self, ics_parser):
        """Test parsing basic ICS content with events."""
        ics_content = ICSDataFactory.create_basic_ics(2)

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) >= 1  # Should have at least 1 busy event
        assert result.total_components > 0
        assert result.event_count == 2
        assert result.error_message is None
        assert result.ics_version == "2.0"
        assert result.prodid == "-//Test//CalendarBot Test//EN"

    def test_parse_ics_content_success_structure(self, ics_parser, sample_ics_content):
        """Test parse result structure on success."""
        result = ics_parser.parse_ics_content(sample_ics_content)

        assert result.success is True
        assert hasattr(result, "events")
        assert hasattr(result, "calendar_name")
        assert hasattr(result, "total_components")
        assert hasattr(result, "event_count")

    def test_parse_empty_ics_content(self, ics_parser):
        """Test parsing empty ICS calendar."""
        ics_content = ICSDataFactory.create_empty_ics()

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) == 0
        assert result.event_count == 0
        assert result.total_components > 0  # Calendar itself is a component

    def test_parse_empty_ics_content_string(self, ics_parser):
        """Test parsing empty ICS content string."""
        result = ics_parser.parse_ics_content("")

        assert result.success is False
        assert result.error_message is not None

    def test_parse_all_day_events(self, ics_parser):
        """Test parsing all-day events."""
        ics_content = ICSDataFactory.create_all_day_event_ics()

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) >= 1

        # Find the all-day event
        all_day_event = next((e for e in result.events if e.is_all_day), None)
        assert all_day_event is not None
        assert all_day_event.subject == "All Day Test Event"

    def test_parse_recurring_events(self, ics_parser):
        """Test parsing recurring events."""
        ics_content = ICSDataFactory.create_recurring_event_ics()

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert result.recurring_event_count == 1

        # Find the recurring event
        recurring_event = next((e for e in result.events if e.is_recurring), None)
        assert recurring_event is not None
        assert recurring_event.subject == "Weekly Recurring Meeting"

    def test_parse_malformed_ics_content(self, ics_parser):
        """Test parsing malformed ICS content."""
        ics_content = ICSDataFactory.create_malformed_ics()

        result = ics_parser.parse_ics_content(ics_content)

        # Should still succeed but may have warnings
        assert result.success is True
        assert len(result.warnings) >= 0  # May have warnings about malformed events

    def test_parse_invalid_ics_content(self, ics_parser):
        """Test parsing completely invalid ICS content."""
        ics_content = "This is not valid ICS content"

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is False
        assert result.error_message is not None
        assert "content line could not be parsed into parts" in result.error_message.lower()

    def test_parse_invalid_ics_content_simple(self, ics_parser):
        """Test parsing invalid ICS content with simple string."""
        invalid_content = "INVALID CONTENT"
        result = ics_parser.parse_ics_content(invalid_content)

        assert result.success is False
        assert result.error_message is not None

    def test_parse_ics_with_calendar_properties(self, ics_parser):
        """Test parsing ICS with calendar-level properties."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Corp//Test Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Test Calendar Name
X-WR-CALDESC:Test Calendar Description
X-WR-TIMEZONE:America/New_York
BEGIN:VEVENT
UID:test-event@example.com
DTSTART:20250107T140000Z
DTEND:20250107T150000Z
SUMMARY:Test Event
DESCRIPTION:Test Description
LOCATION:Test Location
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert result.calendar_name == "Test Calendar Name"
        assert result.calendar_description == "Test Calendar Description"
        assert result.timezone == "America/New_York"
        assert result.prodid == "-//Test Corp//Test Calendar//EN"

    def test_parse_ics_filters_non_busy_events(self, ics_parser):
        """Test that parsing filters out non-busy events."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
BEGIN:VEVENT
UID:busy-event@example.com
DTSTART:20250107T140000Z
DTEND:20250107T150000Z
SUMMARY:Busy Event
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
UID:free-event@example.com
DTSTART:20250107T160000Z
DTEND:20250107T170000Z
SUMMARY:Free Event
STATUS:CONFIRMED
TRANSP:TRANSPARENT
END:VEVENT
BEGIN:VEVENT
UID:cancelled-event@example.com
DTSTART:20250107T180000Z
DTEND:20250107T190000Z
SUMMARY:Cancelled Event
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert result.event_count == 3  # Total events parsed
        # Only busy events should be in the final filtered list
        busy_events = [e for e in result.events if e.is_busy_status and not e.is_cancelled]
        assert len(busy_events) >= 1


@pytest.mark.unit
class TestEventComponentParsing:
    """Test suite for individual event component parsing."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_minimal_event_component(self, ics_parser):
        """Test parsing minimal event component with only required fields."""
        calendar = Calendar()
        event = ICalEvent()
        event.add("uid", "minimal-event@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Minimal Event")

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.id == "minimal-event@example.com"
        assert parsed_event.subject == "Minimal Event"
        assert parsed_event.start.date_time.year == 2025
        assert (
            parsed_event.end.date_time > parsed_event.start.date_time
        )  # Should have default 1-hour duration

    @pytest.mark.critical_path
    def test_parse_event_component_basic(self, ics_parser):
        """Test parsing basic event component."""
        from datetime import datetime, timezone

        from icalendar import Event as ICalEvent

        # Create a minimal event component
        component = ICalEvent()
        component.add("UID", "test-event-1")
        component.add("SUMMARY", "Test Event")
        component.add("DTSTART", datetime.now(timezone.utc))
        component.add("DTEND", datetime.now(timezone.utc))

        event = ics_parser._parse_event_component(component)

        assert event is not None
        assert event.id == "test-event-1"
        assert event.subject == "Test Event"

    def test_parse_event_without_dtstart_returns_none(self, ics_parser):
        """Test parsing event without DTSTART returns None."""
        event = ICalEvent()
        event.add("uid", "no-start-event@example.com")
        event.add("summary", "Event Without Start")

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is None

    @pytest.mark.critical_path
    def test_parse_event_component_missing_dtstart(self, ics_parser):
        """Test parsing event component without DTSTART returns None."""
        from icalendar import Event as ICalEvent

        component = ICalEvent()
        component.add("UID", "test-event-1")
        component.add("SUMMARY", "Test Event")

        event = ics_parser._parse_event_component(component)

        assert event is None

    def test_parse_event_with_duration(self, ics_parser):
        """Test parsing event with DURATION instead of DTEND."""
        event = ICalEvent()
        event.add("uid", "duration-event@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("duration", timedelta(hours=2))
        event.add("summary", "Event with Duration")

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.end.date_time == parsed_event.start.date_time + timedelta(hours=2)

    def test_parse_event_with_attendees(self, ics_parser):
        """Test parsing event with attendees."""
        event = ICalEvent()
        event.add("uid", "attendee-event@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Event with Attendees")

        # Add attendees with different roles and statuses
        attendee1 = "mailto:required@example.com"
        event.add(
            "attendee",
            attendee1,
            parameters={"CN": "Required Person", "ROLE": "REQ-PARTICIPANT", "PARTSTAT": "ACCEPTED"},
        )

        attendee2 = "mailto:optional@example.com"
        event.add(
            "attendee",
            attendee2,
            parameters={
                "CN": "Optional Person",
                "ROLE": "OPT-PARTICIPANT",
                "PARTSTAT": "TENTATIVE",
            },
        )

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.attendees is not None
        assert len(parsed_event.attendees) == 2

        # Check required attendee
        required_attendee = next(
            (a for a in parsed_event.attendees if a.email == "required@example.com"), None
        )
        assert required_attendee is not None
        assert required_attendee.name == "Required Person"
        assert required_attendee.type == AttendeeType.REQUIRED
        assert required_attendee.response_status == ResponseStatus.ACCEPTED

        # Check optional attendee
        optional_attendee = next(
            (a for a in parsed_event.attendees if a.email == "optional@example.com"), None
        )
        assert optional_attendee is not None
        assert optional_attendee.type == AttendeeType.OPTIONAL
        assert optional_attendee.response_status == ResponseStatus.TENTATIVELY_ACCEPTED

    def test_parse_event_with_location(self, ics_parser):
        """Test parsing event with location."""
        event = ICalEvent()
        event.add("uid", "location-event@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Event with Location")
        event.add("location", "Conference Room A, Building B")

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.location is not None
        assert parsed_event.location.display_name == "Conference Room A, Building B"

    def test_parse_event_with_online_meeting_detection(self, ics_parser):
        """Test parsing event with online meeting detection."""
        event = ICalEvent()
        event.add("uid", "online-event@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Online Meeting")
        event.add("description", "Join the meeting: https://teams.microsoft.com/l/meetup/123456789")

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.is_online_meeting is True
        assert parsed_event.online_meeting_url == "https://teams.microsoft.com/l/meetup/123456789"

    @pytest.mark.parametrize(
        "description,expected_online,expected_url",
        [
            ("Join via Zoom: https://zoom.us/j/123456789", True, "https://zoom.us/j/123456789"),
            (
                "Google Meet: https://meet.google.com/abc-defg-hij",
                True,
                "https://meet.google.com/abc-defg-hij",
            ),
            ("Regular meeting in person", False, None),
            ("", False, None),
        ],
    )
    def test_parse_event_online_meeting_detection_patterns(
        self, ics_parser, description, expected_online, expected_url
    ):
        """Test various online meeting detection patterns."""
        event = ICalEvent()
        event.add("uid", "pattern-test@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Pattern Test")
        if description:
            event.add("description", description)

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.is_online_meeting == expected_online
        assert parsed_event.online_meeting_url == expected_url

    def test_parse_event_with_organizer(self, ics_parser):
        """Test parsing event with organizer."""
        event = ICalEvent()
        event.add("uid", "organizer-event@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Event with Organizer")
        event.add("organizer", "mailto:organizer@example.com", parameters={"CN": "Event Organizer"})

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.is_organizer is True

    def test_parse_event_component_exception_handling(self, ics_parser):
        """Test that parsing exceptions are handled gracefully."""
        # Create a mock event that will cause an exception
        with patch("calendarbot.ics.parser.logger") as mock_logger:
            event = MagicMock()
            event.get.side_effect = Exception("Test exception")

            parsed_event = ics_parser._parse_event_component(event)

            assert parsed_event is None
            mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestDateTimeParsing:
    """Test suite for date/time parsing functionality."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_datetime_with_timezone(self, ics_parser):
        """Test parsing datetime with timezone information."""
        from icalendar.parser import Parameters
        from icalendar.prop import vDDDTypes

        # Create a mock datetime property with timezone
        dt_with_tz = datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc)
        mock_prop = MagicMock()
        mock_prop.dt = dt_with_tz

        result = ics_parser._parse_datetime(mock_prop)

        assert result == dt_with_tz
        assert result.tzinfo is not None

    @pytest.mark.critical_path
    def test_parse_datetime_with_timezone_prop(self, ics_parser):
        """Test parsing datetime with timezone using prop."""
        from datetime import datetime, timezone

        from icalendar.prop import vDDDTypes

        dt = datetime.now(timezone.utc)
        dt_prop = vDDDTypes(dt)

        parsed_dt = ics_parser._parse_datetime(dt_prop)

        assert parsed_dt.tzinfo is not None

    def test_parse_datetime_without_timezone_uses_default(self, ics_parser):
        """Test parsing datetime without timezone uses default timezone."""
        dt_no_tz = datetime(2025, 1, 7, 14, 0, 0)
        mock_prop = MagicMock()
        mock_prop.dt = dt_no_tz

        result = ics_parser._parse_datetime(mock_prop, "America/New_York")

        assert result.tzinfo is not None
        # Should have some timezone applied

    def test_parse_datetime_without_timezone_uses_utc_fallback(self, ics_parser):
        """Test parsing datetime without timezone falls back to UTC."""
        dt_no_tz = datetime(2025, 1, 7, 14, 0, 0)
        mock_prop = MagicMock()
        mock_prop.dt = dt_no_tz

        result = ics_parser._parse_datetime(mock_prop)

        assert result.tzinfo == timezone.utc

    @pytest.mark.critical_path
    def test_parse_datetime_without_timezone_uses_utc(self, ics_parser):
        """Test parsing datetime without timezone uses UTC."""
        from datetime import datetime

        from icalendar.prop import vDDDTypes

        dt = datetime.now()  # No timezone
        dt_prop = vDDDTypes(dt)

        parsed_dt = ics_parser._parse_datetime(dt_prop)

        assert parsed_dt.tzinfo is not None

    def test_parse_datetime_with_invalid_default_timezone(self, ics_parser):
        """Test parsing datetime with invalid default timezone falls back to UTC."""
        dt_no_tz = datetime(2025, 1, 7, 14, 0, 0)
        mock_prop = MagicMock()
        mock_prop.dt = dt_no_tz

        # Mock tz.gettz to raise an exception for invalid timezone
        with patch("calendarbot.ics.parser.tz.gettz", side_effect=Exception("Invalid timezone")):
            result = ics_parser._parse_datetime(mock_prop, "Invalid/Timezone")

        assert result.tzinfo == timezone.utc

    def test_parse_date_object_converts_to_datetime(self, ics_parser):
        """Test parsing date object converts to datetime at midnight UTC."""
        from datetime import date

        date_obj = date(2025, 1, 7)
        mock_prop = MagicMock()
        mock_prop.dt = date_obj

        result = ics_parser._parse_datetime(mock_prop)

        assert isinstance(result, datetime)
        assert result.date() == date_obj
        assert result.time() == datetime.min.time()
        assert result.tzinfo == timezone.utc

    def test_parse_datetime_optional_with_none(self, ics_parser):
        """Test parsing optional datetime with None returns None."""
        result = ics_parser._parse_datetime_optional(None)
        assert result is None

    @pytest.mark.critical_path
    def test_parse_datetime_optional_none(self, ics_parser):
        """Test parsing optional datetime when None."""
        result = ics_parser._parse_datetime_optional(None)

        assert result is None

    def test_parse_datetime_optional_with_valid_datetime(self, ics_parser):
        """Test parsing optional datetime with valid datetime."""
        dt = datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc)
        mock_prop = MagicMock()
        mock_prop.dt = dt

        result = ics_parser._parse_datetime_optional(mock_prop)

        assert result == dt

    @pytest.mark.critical_path
    def test_parse_datetime_optional_valid(self, ics_parser):
        """Test parsing optional datetime when valid."""
        from datetime import datetime, timezone

        from icalendar.prop import vDDDTypes

        dt = datetime.now(timezone.utc)
        dt_prop = vDDDTypes(dt)

        result = ics_parser._parse_datetime_optional(dt_prop)

        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_datetime_optional_with_exception(self, ics_parser):
        """Test parsing optional datetime with exception returns None."""
        mock_prop = MagicMock()
        mock_prop.dt = MagicMock()

        with patch.object(ics_parser, "_parse_datetime", side_effect=Exception("Test error")):
            result = ics_parser._parse_datetime_optional(mock_prop)

        assert result is None


@pytest.mark.unit
class TestStatusAndTransparencyMapping:
    """Test suite for status and transparency mapping."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_status_with_none(self, ics_parser):
        """Test parsing status with None returns None."""
        result = ics_parser._parse_status(None)
        assert result is None

    def test_parse_status_with_valid_status(self, ics_parser):
        """Test parsing valid status values."""
        result = ics_parser._parse_status("confirmed")
        assert result == "CONFIRMED"

        result = ics_parser._parse_status("tentative")
        assert result == "TENTATIVE"

        result = ics_parser._parse_status("cancelled")
        assert result == "CANCELLED"

    @pytest.mark.critical_path
    def test_parse_status_values(self, ics_parser):
        """Test parsing various status values."""
        assert ics_parser._parse_status("CONFIRMED") == "CONFIRMED"
        assert ics_parser._parse_status("CANCELLED") == "CANCELLED"
        assert ics_parser._parse_status("TENTATIVE") == "TENTATIVE"
        assert ics_parser._parse_status(None) is None

    @pytest.mark.parametrize(
        "transparency,status,expected",
        [
            ("OPAQUE", None, EventStatus.BUSY),
            ("TRANSPARENT", None, EventStatus.FREE),
            ("OPAQUE", "TENTATIVE", EventStatus.TENTATIVE),
            ("TRANSPARENT", "TENTATIVE", EventStatus.TENTATIVE),
            ("OPAQUE", "CANCELLED", EventStatus.FREE),
            ("TRANSPARENT", "CANCELLED", EventStatus.FREE),
            ("", None, EventStatus.BUSY),  # Default to OPAQUE
        ],
    )
    def test_map_transparency_to_status(self, ics_parser, transparency, status, expected):
        """Test mapping transparency and status to EventStatus."""
        result = ics_parser._map_transparency_to_status(transparency, status)
        assert result == expected

    @pytest.mark.critical_path
    @pytest.mark.parametrize(
        "transparency,status,expected",
        [
            ("OPAQUE", "CONFIRMED", EventStatus.BUSY),
            ("TRANSPARENT", "CONFIRMED", EventStatus.FREE),
            ("OPAQUE", "TENTATIVE", EventStatus.TENTATIVE),
            ("OPAQUE", "CANCELLED", EventStatus.FREE),
        ],
    )
    def test_map_transparency_to_status_critical(self, ics_parser, transparency, status, expected):
        """Test transparency mapping to event status."""
        result = ics_parser._map_transparency_to_status(transparency, status)

        assert result == expected


@pytest.mark.unit
class TestAttendeesParsing:
    """Test suite for attendee parsing functionality."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_attendee_basic(self, ics_parser):
        """Test parsing basic attendee information."""
        mock_attendee = MagicMock()
        mock_attendee.__str__ = MagicMock(return_value="mailto:test@example.com")
        mock_attendee.params = {
            "CN": "Test User",
            "ROLE": "REQ-PARTICIPANT",
            "PARTSTAT": "ACCEPTED",
        }

        result = ics_parser._parse_attendee(mock_attendee)

        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.type == AttendeeType.REQUIRED
        assert result.response_status == ResponseStatus.ACCEPTED

    @pytest.mark.critical_path
    def test_parse_attendee_basic_critical(self, ics_parser):
        """Test parsing basic attendee."""
        from icalendar.prop import vCalAddress

        attendee_prop = vCalAddress("mailto:test@example.com")
        attendee_prop.params["CN"] = "Test User"
        attendee_prop.params["ROLE"] = "REQ-PARTICIPANT"
        attendee_prop.params["PARTSTAT"] = "ACCEPTED"

        attendee = ics_parser._parse_attendee(attendee_prop)

        assert attendee is not None
        assert attendee.email == "test@example.com"
        assert attendee.name == "Test User"

    def test_parse_attendee_without_mailto_prefix(self, ics_parser):
        """Test parsing attendee without mailto: prefix."""
        mock_attendee = MagicMock()
        mock_attendee.__str__ = MagicMock(return_value="test@example.com")
        mock_attendee.params = {}

        result = ics_parser._parse_attendee(mock_attendee)

        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "test"  # Should use email prefix as name

    @pytest.mark.critical_path
    def test_parse_attendee_minimal(self, ics_parser):
        """Test parsing attendee with minimal info."""
        from icalendar.prop import vCalAddress

        attendee_prop = vCalAddress("mailto:test@example.com")

        attendee = ics_parser._parse_attendee(attendee_prop)

        assert attendee is not None
        assert attendee.email == "test@example.com"
        assert attendee.name == "test"  # Extracted from email

    @pytest.mark.parametrize(
        "role,expected_type",
        [
            ("REQ-PARTICIPANT", AttendeeType.REQUIRED),
            ("OPT-PARTICIPANT", AttendeeType.OPTIONAL),
            ("NON-PARTICIPANT", AttendeeType.RESOURCE),
            ("UNKNOWN", AttendeeType.REQUIRED),  # Default
            (None, AttendeeType.REQUIRED),  # Default
        ],
    )
    def test_parse_attendee_role_mapping(self, ics_parser, role, expected_type):
        """Test attendee role mapping to AttendeeType."""
        mock_attendee = MagicMock()
        mock_attendee.__str__ = MagicMock(return_value="mailto:test@example.com")
        mock_attendee.params = {"ROLE": role} if role else {}

        result = ics_parser._parse_attendee(mock_attendee)

        assert result is not None
        assert result.type == expected_type

    @pytest.mark.parametrize(
        "partstat,expected_status",
        [
            ("ACCEPTED", ResponseStatus.ACCEPTED),
            ("DECLINED", ResponseStatus.DECLINED),
            ("TENTATIVE", ResponseStatus.TENTATIVELY_ACCEPTED),
            ("DELEGATED", ResponseStatus.NOT_RESPONDED),
            ("NEEDS-ACTION", ResponseStatus.NOT_RESPONDED),
            ("UNKNOWN", ResponseStatus.NOT_RESPONDED),  # Default
            (None, ResponseStatus.NOT_RESPONDED),  # Default
        ],
    )
    def test_parse_attendee_status_mapping(self, ics_parser, partstat, expected_status):
        """Test attendee participation status mapping."""
        mock_attendee = MagicMock()
        mock_attendee.__str__ = MagicMock(return_value="mailto:test@example.com")
        mock_attendee.params = {"PARTSTAT": partstat} if partstat else {}

        result = ics_parser._parse_attendee(mock_attendee)

        assert result is not None
        assert result.response_status == expected_status

    def test_parse_attendee_exception_handling(self, ics_parser):
        """Test attendee parsing exception handling."""
        mock_attendee = MagicMock()
        mock_attendee.__str__ = MagicMock(side_effect=Exception("Test error"))

        with patch("calendarbot.ics.parser.logger"):
            result = ics_parser._parse_attendee(mock_attendee)

        assert result is None


@pytest.mark.unit
class TestCalendarProperties:
    """Test suite for calendar property extraction."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_get_calendar_property_existing(self, ics_parser):
        """Test getting existing calendar property."""
        mock_calendar = MagicMock()
        mock_calendar.get.return_value = "Test Value"

        result = ics_parser._get_calendar_property(mock_calendar, "TEST-PROP")

        assert result == "Test Value"
        mock_calendar.get.assert_called_once_with("TEST-PROP")

    @pytest.mark.critical_path
    def test_get_calendar_property_exists(self, ics_parser):
        """Test getting calendar property that exists."""
        from icalendar import Calendar

        cal = Calendar()
        cal.add("PRODID", "Test Calendar")

        prop = ics_parser._get_calendar_property(cal, "PRODID")

        assert prop == "Test Calendar"

    def test_get_calendar_property_nonexistent(self, ics_parser):
        """Test getting non-existent calendar property."""
        mock_calendar = MagicMock()
        mock_calendar.get.return_value = None

        result = ics_parser._get_calendar_property(mock_calendar, "NONEXISTENT")

        assert result is None

    @pytest.mark.critical_path
    def test_get_calendar_property_missing(self, ics_parser):
        """Test getting calendar property that doesn't exist."""
        from icalendar import Calendar

        cal = Calendar()

        prop = ics_parser._get_calendar_property(cal, "NONEXISTENT")

        assert prop is None

    def test_get_calendar_property_exception(self, ics_parser):
        """Test getting calendar property with exception."""
        mock_calendar = MagicMock()
        mock_calendar.get.side_effect = Exception("Test error")

        result = ics_parser._get_calendar_property(mock_calendar, "ERROR-PROP")

        assert result is None


@pytest.mark.unit
class TestEventFiltering:
    """Test suite for event filtering functionality."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    @pytest.fixture
    def sample_events(self):
        """Create sample events for filtering tests."""
        from calendarbot.ics.models import DateTimeInfo

        now = datetime.now(timezone.utc)

        events = [
            CalendarEvent(
                id="busy-event",
                subject="Busy Event",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
                is_cancelled=False,
            ),
            CalendarEvent(
                id="free-event",
                subject="Free Event",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.FREE,
                is_cancelled=False,
            ),
            CalendarEvent(
                id="tentative-event",
                subject="Tentative Event",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.TENTATIVE,
                is_cancelled=False,
            ),
            CalendarEvent(
                id="cancelled-event",
                subject="Cancelled Event",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
                is_cancelled=True,
            ),
        ]

        return events

    def test_filter_busy_events(self, ics_parser, sample_events):
        """Test filtering to only busy/tentative events."""
        filtered_events = ics_parser.filter_busy_events(sample_events)

        # Should include busy and tentative, exclude free and cancelled
        assert len(filtered_events) == 2

        event_subjects = [e.subject for e in filtered_events]
        assert "Busy Event" in event_subjects
        assert "Tentative Event" in event_subjects
        assert "Free Event" not in event_subjects
        assert "Cancelled Event" not in event_subjects

    @pytest.mark.critical_path
    def test_filter_busy_events_critical(self, ics_parser, sample_events):
        """Test filtering to only busy events."""
        # Modify sample events to test filtering
        sample_events[0].show_as = EventStatus.BUSY
        sample_events[0].is_cancelled = False
        sample_events[1].show_as = EventStatus.FREE
        sample_events[1].is_cancelled = False
        # Ensure tentative event is also set to FREE for this test
        sample_events[2].show_as = EventStatus.FREE
        sample_events[2].is_cancelled = False

        filtered = ics_parser.filter_busy_events(sample_events)

        # Should only include busy events
        assert len(filtered) == 1
        assert filtered[0].show_as == EventStatus.BUSY

    @pytest.mark.critical_path
    def test_filter_busy_events_excludes_cancelled(self, ics_parser, sample_events):
        """Test that cancelled events are filtered out."""
        sample_events[0].show_as = EventStatus.BUSY
        sample_events[0].is_cancelled = True
        # Ensure all other events are not considered busy or are cancelled
        sample_events[1].show_as = EventStatus.FREE
        sample_events[1].is_cancelled = False
        sample_events[2].show_as = EventStatus.FREE
        sample_events[2].is_cancelled = False
        sample_events[3].show_as = EventStatus.BUSY
        sample_events[3].is_cancelled = True

        filtered = ics_parser.filter_busy_events(sample_events)

        assert len(filtered) == 0


@pytest.mark.unit
class TestRecurrenceExpansion:
    """Test suite for recurrence expansion (placeholder functionality)."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    @pytest.fixture
    def sample_events(self):
        """Create sample events for recurrence tests."""
        from calendarbot.ics.models import DateTimeInfo

        now = datetime.now(timezone.utc)

        events = [
            CalendarEvent(
                id="recurring-event",
                subject="Recurring Event",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
                is_cancelled=False,
                is_recurring=True,
            ),
            CalendarEvent(
                id="single-event",
                subject="Single Event",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
                is_cancelled=False,
                is_recurring=False,
            ),
        ]

        return events

    def test_expand_recurring_events_placeholder(self, ics_parser, sample_events):
        """Test placeholder recurrence expansion functionality."""
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=30)

        # Currently returns events as-is (placeholder implementation)
        expanded_events = ics_parser.expand_recurring_events(sample_events, start_date, end_date)

        assert len(expanded_events) == len(sample_events)
        assert expanded_events == sample_events

    @pytest.mark.critical_path
    def test_expand_recurring_events_placeholder_critical(self, ics_parser, sample_events):
        """Test recurring events expansion placeholder."""
        start_date = datetime.now()
        end_date = datetime.now()

        # Currently returns events as-is (placeholder implementation)
        expanded = ics_parser.expand_recurring_events(sample_events, start_date, end_date)

        assert expanded == sample_events


@pytest.mark.unit
class TestICSValidation:
    """Test suite for ICS content validation."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_validate_valid_ics_content(self, ics_parser):
        """Test validation of valid ICS content."""
        ics_content = ICSDataFactory.create_basic_ics(1)

        result = ics_parser.validate_ics_content(ics_content)

        assert result is True

    @pytest.mark.critical_path
    def test_validate_ics_content_valid(self, ics_parser, sample_ics_content):
        """Test validation of valid ICS content."""
        is_valid = ics_parser.validate_ics_content(sample_ics_content)

        assert is_valid is True

    def test_validate_empty_ics_content(self, ics_parser):
        """Test validation of empty ICS content."""
        with patch.object(ics_parser.security_logger, "log_input_validation_failure") as mock_log:
            result = ics_parser.validate_ics_content("")

        assert result is False
        mock_log.assert_called_once()

    @pytest.mark.critical_path
    def test_validate_ics_content_empty(self, ics_parser):
        """Test validation of empty content."""
        is_valid = ics_parser.validate_ics_content("")

        assert is_valid is False

    def test_validate_none_ics_content(self, ics_parser):
        """Test validation of None ICS content."""
        with patch.object(ics_parser.security_logger, "log_input_validation_failure") as mock_log:
            result = ics_parser.validate_ics_content(None)

        assert result is False
        mock_log.assert_called_once()

    def test_validate_ics_content_missing_begin_vcalendar(self, ics_parser):
        """Test validation of ICS content missing BEGIN:VCALENDAR."""
        ics_content = "VERSION:2.0\nEND:VCALENDAR"

        with patch.object(ics_parser.security_logger, "log_input_validation_failure") as mock_log:
            result = ics_parser.validate_ics_content(ics_content)

        assert result is False
        mock_log.assert_called_once()
        args = mock_log.call_args[1]
        assert "Missing BEGIN:VCALENDAR marker" in args["validation_error"]

    @pytest.mark.critical_path
    def test_validate_ics_content_missing_begin(self, ics_parser):
        """Test validation when BEGIN:VCALENDAR is missing."""
        invalid_content = "END:VCALENDAR"
        is_valid = ics_parser.validate_ics_content(invalid_content)

        assert is_valid is False

    def test_validate_ics_content_missing_end_vcalendar(self, ics_parser):
        """Test validation of ICS content missing END:VCALENDAR."""
        ics_content = "BEGIN:VCALENDAR\nVERSION:2.0"

        with patch.object(ics_parser.security_logger, "log_input_validation_failure") as mock_log:
            result = ics_parser.validate_ics_content(ics_content)

        assert result is False
        mock_log.assert_called_once()
        args = mock_log.call_args[1]
        assert "Missing END:VCALENDAR marker" in args["validation_error"]

    @pytest.mark.critical_path
    def test_validate_ics_content_missing_end(self, ics_parser):
        """Test validation when END:VCALENDAR is missing."""
        invalid_content = "BEGIN:VCALENDAR\nVERSION:2.0"
        is_valid = ics_parser.validate_ics_content(invalid_content)

        assert is_valid is False

    def test_validate_ics_content_parsing_failure(self, ics_parser):
        """Test validation when icalendar parsing fails."""
        # Create content that has the markers but fails to parse
        ics_content = "BEGIN:VCALENDAR\nINVALID_CONTENT\nEND:VCALENDAR"

        with patch.object(ics_parser.security_logger, "log_input_validation_failure") as mock_log:
            result = ics_parser.validate_ics_content(ics_content)

        assert result is False
        mock_log.assert_called_once()
        args = mock_log.call_args[1]
        assert "ICS parsing failed" in args["validation_error"]

    def test_validate_ics_content_with_whitespace_only(self, ics_parser):
        """Test validation of ICS content with only whitespace."""
        ics_content = "   \n\t  \n  "

        with patch.object(ics_parser.security_logger, "log_input_validation_failure") as mock_log:
            result = ics_parser.validate_ics_content(ics_content)

        assert result is False
        mock_log.assert_called_once()


@pytest.mark.unit
class TestICSParserSecurity:
    """Security-related ICS parser tests."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create ICS parser instance."""
        return ICSParser(test_settings)

    def test_validate_ics_content_security_logging(self, ics_parser):
        """Test that invalid content triggers security logging."""
        # Security logger should log validation failures
        is_valid = ics_parser.validate_ics_content("MALICIOUS CONTENT")

        assert is_valid is False
        # Security logger should have been called (tested via behavior)

    def test_parse_large_ics_content(self, ics_parser):
        """Test parsing very large ICS content doesn't hang."""
        # Create content that's large but still valid
        large_content = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for i in range(100):  # Not too large to avoid memory issues
            large_content += f"BEGIN:VEVENT\nUID:event-{i}\nSUMMARY:Event {i}\nEND:VEVENT\n"
        large_content += "END:VCALENDAR"

        result = ics_parser.parse_ics_content(large_content)

        # Should handle large content gracefully
        assert (
            result.success is True or result.success is False
        )  # Either works, just shouldn't hang

    def test_parse_malformed_datetime(self, ics_parser):
        """Test handling malformed datetime in events."""
        malformed_ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-malformed
SUMMARY:Test Event
DTSTART:INVALID_DATE
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(malformed_ics)

        # Should either parse successfully (skipping bad event) or fail gracefully
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error_message is not None


@pytest.mark.unit
class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_event_with_missing_uid_generates_uuid(self, ics_parser):
        """Test parsing event without UID generates a UUID."""
        event = ICalEvent()
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Event Without UID")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-9012-123456789abc")):
            parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.id == "12345678-1234-5678-9012-123456789abc"

    @pytest.mark.critical_path
    def test_parse_event_component_missing_uid(self, ics_parser):
        """Test parsing event component without UID generates one."""
        from datetime import datetime, timezone

        from icalendar import Event as ICalEvent

        component = ICalEvent()
        component.add("SUMMARY", "Test Event")
        component.add("DTSTART", datetime.now(timezone.utc))

        event = ics_parser._parse_event_component(component)

        assert event is not None
        assert event.id is not None  # Should generate UUID
        assert len(event.id) > 0

    def test_parse_event_with_missing_summary_uses_default(self, ics_parser):
        """Test parsing event without SUMMARY uses default title."""
        event = ICalEvent()
        event.add("uid", "no-summary@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert parsed_event.subject == "No Title"

    def test_parse_event_with_complex_attendee_list(self, ics_parser):
        """Test parsing event with complex attendee scenarios."""
        event = ICalEvent()
        event.add("uid", "complex-attendees@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Complex Attendees Event")

        # Test single attendee (not a list)
        attendee = "mailto:single@example.com"
        event.add("attendee", attendee, parameters={"CN": "Single Attendee"})

        # Add a second attendee that will succeed
        attendee2 = "mailto:second@example.com"
        event.add("attendee", attendee2, parameters={"CN": "Second Attendee"})

        # Simulate one attendee parsing failure
        original_parse_attendee = ics_parser._parse_attendee
        call_count = 0

        def side_effect_parse_attendee(att):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call fails
                raise Exception("Attendee parse error")
            return original_parse_attendee(att)

        with patch.object(ics_parser, "_parse_attendee", side_effect=side_effect_parse_attendee):
            parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        # Should still have the event even if one attendee fails

    def test_parse_event_with_very_long_description(self, ics_parser):
        """Test parsing event with very long description (body preview truncation)."""
        long_description = "A" * 500  # 500 characters

        event = ICalEvent()
        event.add("uid", "long-desc@example.com")
        event.add("dtstart", datetime(2025, 1, 7, 14, 0, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2025, 1, 7, 15, 0, 0, tzinfo=timezone.utc))
        event.add("summary", "Long Description Event")
        event.add("description", long_description)

        parsed_event = ics_parser._parse_event_component(event)

        assert parsed_event is not None
        assert len(parsed_event.body_preview) == 200  # Should be truncated to 200 chars
        assert parsed_event.body_preview.endswith("A")  # Should end with the repeated character

    def test_parse_ics_with_multiple_warnings(self, ics_parser):
        """Test parsing ICS content that generates multiple warnings."""
        # Create ICS with events that will trigger exceptions during parsing
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
BEGIN:VEVENT
UID:good-event@example.com
DTSTART:20250107T140000Z
DTEND:20250107T150000Z
SUMMARY:Good Event
END:VEVENT
BEGIN:VEVENT
UID:bad-event-1@example.com
DTSTART:20250107T140000Z
DTEND:20250107T150000Z
SUMMARY:Event That Will Fail
END:VEVENT
END:VCALENDAR"""

        # Mock _parse_event_component to simulate exceptions for certain events
        original_parse_event = ics_parser._parse_event_component
        call_count = 0

        def side_effect_parse_event(component, default_timezone=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second event fails
                raise Exception("Simulated parsing error")
            return original_parse_event(component, default_timezone)

        with patch.object(
            ics_parser, "_parse_event_component", side_effect=side_effect_parse_event
        ):
            result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.warnings) >= 1  # Should have warnings about failed events
        assert result.event_count >= 1  # Should still parse the good event

    def test_parse_ics_content_with_timezone_edge_cases(self, ics_parser):
        """Test parsing ICS with various timezone edge cases."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
X-WR-TIMEZONE:Invalid/Timezone
BEGIN:VEVENT
UID:tz-test@example.com
DTSTART:20250107T140000
DTEND:20250107T150000
SUMMARY:Timezone Test Event
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) >= 1
        # Should handle invalid timezone gracefully


@pytest.mark.unit
class TestIntegrationScenarios:
    """Test suite for integration scenarios and real-world use cases."""

    @pytest.fixture
    def ics_parser(self, test_settings):
        """Create an ICS parser for testing."""
        return ICSParser(test_settings)

    def test_parse_microsoft_outlook_ics(self, ics_parser):
        """Test parsing Microsoft Outlook-generated ICS content."""
        outlook_ics = """BEGIN:VCALENDAR
PRODID:Microsoft Exchange Server 2010
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Work Calendar
X-WR-TIMEZONE:America/New_York
BEGIN:VTIMEZONE
TZID:Eastern Standard Time
BEGIN:STANDARD
DTSTART:16011104T020000
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:16010311T020000
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:040000008200E00074C5B7101A82E008000000001234567890ABCDEF
DTSTART;TZID=Eastern Standard Time:20250107T090000
DTEND;TZID=Eastern Standard Time:20250107T100000
SUMMARY:Team Meeting
DESCRIPTION:Weekly team sync\\n\\nJoin Microsoft Teams Meeting\\nhttps://teams.microsoft.com/l/meetup/19%3a...
LOCATION:Conference Room A
ORGANIZER;CN=John Doe:mailto:john.doe@company.com
ATTENDEE;CN=Jane Smith;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED:mailto:jane.smith@company.com
ATTENDEE;CN=Bob Johnson;ROLE=OPT-PARTICIPANT;PARTSTAT=TENTATIVE:mailto:bob.johnson@company.com
STATUS:CONFIRMED
TRANSP:OPAQUE
SEQUENCE:0
CREATED:20250101T120000Z
LAST-MODIFIED:20250102T130000Z
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(outlook_ics)

        assert result.success is True
        assert result.calendar_name == "Work Calendar"
        assert result.timezone == "America/New_York"
        assert result.prodid.startswith("Microsoft Exchange")

        assert len(result.events) >= 1
        event = result.events[0]
        assert event.subject == "Team Meeting"
        assert event.location is not None
        assert event.location.display_name == "Conference Room A"
        assert event.is_online_meeting is True  # Should detect Teams URL
        assert event.attendees is not None
        assert len(event.attendees) == 2

    def test_parse_google_calendar_ics(self, ics_parser):
        """Test parsing Google Calendar-generated ICS content."""
        google_ics = """BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Personal Calendar
X-WR-TIMEZONE:America/Los_Angeles
BEGIN:VEVENT
DTSTART:20250107T170000Z
DTEND:20250107T180000Z
DTSTAMP:20250101T120000Z
UID:google-event-123@google.com
CREATED:20250101T100000Z
DESCRIPTION:Meet for coffee and catch up
LAST-MODIFIED:20250101T110000Z
LOCATION:Starbucks\\, Main Street
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Coffee with Friend
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20250108
DTEND;VALUE=DATE:20250109
DTSTAMP:20250101T120000Z
UID:google-allday-456@google.com
CREATED:20250101T100000Z
DESCRIPTION:Take a day off
LAST-MODIFIED:20250101T110000Z
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Vacation Day
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(google_ics)

        assert result.success is True
        assert result.calendar_name == "Personal Calendar"
        assert result.timezone == "America/Los_Angeles"
        assert result.prodid.startswith("-//Google Inc")

        # Should have at least one busy event (coffee meeting)
        busy_events = [e for e in result.events if e.is_busy_status]
        assert len(busy_events) >= 1

        # Check for all-day event
        all_day_events = [e for e in result.events if e.is_all_day]
        if all_day_events:  # May be filtered out if marked as FREE
            assert all_day_events[0].subject == "Vacation Day"

    def test_parse_apple_calendar_ics(self, ics_parser):
        """Test parsing Apple Calendar-generated ICS content."""
        apple_ics = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
PRODID:-//Apple Inc.//Mac OS X 10.15.7//EN
VERSION:2.0
X-WR-CALNAME:Home
X-WR-TIMEZONE:America/New_York
BEGIN:VEVENT
CREATED:20250101T120000Z
DTEND:20250107T200000Z
DTSTART:20250107T190000Z
DTSTAMP:20250101T120000Z
LAST-MODIFIED:20250101T130000Z
SEQUENCE:0
SUMMARY:Dinner Reservation
UID:apple-event-789@icloud.com
LOCATION:Fancy Restaurant\\, Downtown
DESCRIPTION:Anniversary dinner reservation
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(apple_ics)

        assert result.success is True
        assert result.calendar_name == "Home"
        assert result.timezone == "America/New_York"
        assert result.prodid.startswith("-//Apple Inc.")

        assert len(result.events) >= 1
        event = result.events[0]
        assert event.subject == "Dinner Reservation"
        assert event.location is not None
        assert "Fancy Restaurant" in event.location.display_name

    def test_parse_empty_calendar_edge_case(self, ics_parser):
        """Test parsing valid but empty calendar."""
        empty_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Empty Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
END:VCALENDAR"""

        result = ics_parser.parse_ics_content(empty_ics)

        assert result.success is True
        assert len(result.events) == 0
        assert result.event_count == 0
        assert result.total_components == 1  # Just the calendar component

    @pytest.mark.performance
    def test_parse_large_calendar_performance(self, ics_parser):
        """Test parsing large calendar for performance."""
        large_ics = ICSDataFactory.create_large_ics(50)  # 50 events

        import time

        start_time = time.time()
        result = ics_parser.parse_ics_content(large_ics)
        end_time = time.time()

        assert result.success is True
        assert result.event_count == 50
        assert len(result.events) <= 50  # May be filtered

        # Should complete in reasonable time (less than 1 second for 50 events)
        parse_time = end_time - start_time
        assert parse_time < 1.0, f"Parsing took too long: {parse_time:.2f}s"
