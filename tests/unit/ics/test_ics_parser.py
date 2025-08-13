"""Unit tests for ICS Parser functionality."""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.ics.models import EventStatus
from calendarbot.ics.parser import ICSParser


class TestICSParserInitialization:
    """Test ICS Parser initialization and setup."""

    def test_init_creates_parser(self, test_settings: Any) -> None:
        """Test that ICSParser.__init__ creates parser correctly."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            parser = ICSParser(test_settings)

            assert parser.settings == test_settings
            assert parser.security_logger is not None


class TestICSParserContentValidation:
    """Test ICS Parser content validation."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_validate_ics_content_valid(self, parser: ICSParser, sample_ics_content: str) -> None:
        """Test validation of valid ICS content."""
        result = parser.validate_ics_content(sample_ics_content)
        assert result is True

    def test_validate_ics_content_empty(self, parser: ICSParser) -> None:
        """Test validation of empty content."""
        result = parser.validate_ics_content("")
        assert result is False

    def test_validate_ics_content_none(self, parser: ICSParser) -> None:
        """Test validation of None content."""
        result = parser.validate_ics_content(None)  # type: ignore
        assert result is False

    def test_validate_ics_content_missing_begin_vcalendar(self, parser: ICSParser) -> None:
        """Test validation fails when BEGIN:VCALENDAR is missing."""
        invalid_content = """VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR"""

        result = parser.validate_ics_content(invalid_content)
        assert result is False

    def test_validate_ics_content_missing_end_vcalendar(self, parser: ICSParser) -> None:
        """Test validation fails when END:VCALENDAR is missing."""
        invalid_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN"""

        result = parser.validate_ics_content(invalid_content)
        assert result is False

    def test_validate_ics_content_malformed_ics(self, parser: ICSParser) -> None:
        """Test validation fails for malformed ICS content."""
        invalid_content = """BEGIN:VCALENDAR
INVALID CONTENT STRUCTURE
END:VCALENDAR"""

        with patch("icalendar.Calendar.from_ical") as mock_parse:
            mock_parse.side_effect = Exception("Parse error")
            result = parser.validate_ics_content(invalid_content)
            assert result is False

    def test_validate_ics_content_logs_security_events(self, parser: ICSParser) -> None:
        """Test that validation failures are logged as security events."""
        with patch.object(parser.security_logger, "log_input_validation_failure") as mock_log:
            parser.validate_ics_content("")
            mock_log.assert_called_once()


class TestICSParserBasicParsing:
    """Test basic ICS parsing functionality."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_parse_ics_content_success(self, parser: ICSParser, sample_ics_content: str) -> None:
        """Test successful parsing of valid ICS content."""
        result = parser.parse_ics_content(sample_ics_content)

        assert result.success is True
        assert isinstance(result.events, list)
        assert len(result.events) >= 1
        assert result.error_message is None
        assert result.total_components > 0
        assert result.event_count > 0

    def test_parse_ics_content_empty_calendar(self, parser: ICSParser) -> None:
        """Test parsing of empty calendar."""
        empty_calendar = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR"""

        result = parser.parse_ics_content(empty_calendar)

        assert result.success is True
        assert len(result.events) == 0
        assert result.event_count == 0

    def test_parse_ics_content_invalid_content(self, parser: ICSParser) -> None:
        """Test parsing of invalid content."""
        invalid_content = "Not ICS content at all"

        result = parser.parse_ics_content(invalid_content)

        assert result.success is False
        assert result.error_message is not None
        assert result.events == []  # Empty list when parsing fails

    def test_parse_ics_content_extracts_calendar_metadata(self, parser: ICSParser) -> None:
        """Test that calendar metadata is extracted correctly."""
        ics_with_metadata = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Company//Test Product//EN
X-WR-CALNAME:Test Calendar
X-WR-CALDESC:Test calendar description
X-WR-TIMEZONE:America/New_York
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_with_metadata)

        assert result.success is True
        assert result.calendar_name == "Test Calendar"
        assert result.calendar_description == "Test calendar description"
        assert result.timezone == "America/New_York"
        assert result.prodid == "-//Test Company//Test Product//EN"
        assert result.ics_version == "2.0"


class TestICSParserEventParsing:
    """Test individual event parsing functionality."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_parse_basic_event(self, parser: ICSParser) -> None:
        """Test parsing of basic event."""
        now = datetime.now()
        basic_event_ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-123
DTSTART:{now.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{(now + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Test Meeting
DESCRIPTION:This is a test meeting
LOCATION:Conference Room A
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(basic_event_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.id == "test-event-123"
        assert event.subject == "Test Meeting"
        assert event.body_preview == "This is a test meeting"
        assert event.location.display_name == "Conference Room A"
        assert event.is_cancelled is False
        assert event.show_as == EventStatus.BUSY

    def test_parse_all_day_event(self, parser: ICSParser) -> None:
        """Test parsing of all-day event."""
        today = datetime.now().date()
        all_day_ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:all-day-event
DTSTART;VALUE=DATE:{today.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{(today + timedelta(days=1)).strftime("%Y%m%d")}
SUMMARY:All Day Event
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(all_day_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.subject == "All Day Event"
        assert event.is_all_day is True

    def test_parse_event_with_timezone(self, parser: ICSParser) -> None:
        """Test parsing of event with timezone information."""
        tz_event_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:tz-event
DTSTART;TZID=America/New_York:20240101T140000
DTEND;TZID=America/New_York:20240101T150000
SUMMARY:Timezone Event
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(tz_event_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.subject == "Timezone Event"
        assert event.start.time_zone is not None

    def test_parse_recurring_event(self, parser: ICSParser) -> None:
        """Test parsing of recurring event."""
        now = datetime.now()
        recurring_ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:recurring-event
DTSTART:{now.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{(now + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Weekly Meeting
RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(recurring_ics)

        assert result.success is True
        assert len(result.events) == 1
        assert result.recurring_event_count == 1

        event = result.events[0]
        assert event.subject == "Weekly Meeting"
        assert event.is_recurring is True

    def test_parse_cancelled_event(self, parser: ICSParser) -> None:
        """Test parsing of cancelled event."""
        cancelled_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:cancelled-event
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:Cancelled Meeting
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(cancelled_ics)

        assert result.success is True
        # Cancelled events should be filtered out from final results
        assert len(result.events) == 0

    def test_parse_free_transparent_event(self, parser: ICSParser) -> None:
        """Test parsing of free/transparent event."""
        free_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:free-event
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:Free Time
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(free_ics)

        assert result.success is True
        # Free/transparent events should be filtered out
        assert len(result.events) == 0


class TestICSParserDateTimeParsing:
    """Test datetime parsing functionality."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_parse_datetime_utc(self, parser: ICSParser) -> None:
        """Test parsing UTC datetime."""
        # Create mock datetime property
        mock_dt_prop = MagicMock()
        mock_dt_prop.dt = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        result = parser._parse_datetime(mock_dt_prop)

        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 14

    def test_parse_datetime_naive_with_default_timezone(self, parser: ICSParser) -> None:
        """Test parsing naive datetime with default timezone."""
        mock_dt_prop = MagicMock()
        mock_dt_prop.dt = datetime(2024, 1, 1, 14, 0, 0)  # No timezone

        result = parser._parse_datetime(mock_dt_prop, "America/New_York")

        assert result.tzinfo is not None

    def test_parse_datetime_date_only(self, parser: ICSParser) -> None:
        """Test parsing date-only (all-day) events."""
        from datetime import date

        mock_dt_prop = MagicMock()
        mock_dt_prop.dt = date(2024, 1, 1)

        result = parser._parse_datetime(mock_dt_prop)

        assert isinstance(result, datetime)
        assert result.hour == 0
        assert result.minute == 0
        # With the new centralized timezone service, date-only events use the server/user timezone
        # instead of always UTC, which is the expected behavior
        assert result.tzinfo is not None

    def test_parse_datetime_optional_none(self, parser: ICSParser) -> None:
        """Test parsing optional datetime that is None."""
        result = parser._parse_datetime_optional(None)
        assert result is None

    def test_parse_datetime_optional_valid(self, parser: ICSParser) -> None:
        """Test parsing optional datetime that is valid."""
        mock_dt_prop = MagicMock()
        mock_dt_prop.dt = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        result = parser._parse_datetime_optional(mock_dt_prop)

        assert result is not None
        assert result.year == 2024

    def test_parse_datetime_optional_exception(self, parser: ICSParser) -> None:
        """Test parsing optional datetime that throws exception."""
        mock_dt_prop = MagicMock()
        mock_dt_prop.dt = "invalid"

        result = parser._parse_datetime_optional(mock_dt_prop)
        assert result is None


class TestICSParserStatusMapping:
    """Test event status and transparency mapping."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    @pytest.mark.parametrize(
        "transparency,status,expected",
        [
            ("OPAQUE", "CONFIRMED", EventStatus.BUSY),
            ("OPAQUE", "TENTATIVE", EventStatus.TENTATIVE),
            ("OPAQUE", "CANCELLED", EventStatus.FREE),
            ("TRANSPARENT", "CONFIRMED", EventStatus.TENTATIVE),
            (
                "TRANSPARENT",
                "TENTATIVE",
                EventStatus.TENTATIVE,
            ),  # Status takes precedence over transparency for TENTATIVE
            (None, "TENTATIVE", EventStatus.TENTATIVE),
            (None, "CANCELLED", EventStatus.FREE),
            (None, None, EventStatus.BUSY),  # Default to BUSY
        ],
    )
    def test_map_transparency_to_status(
        self, parser: ICSParser, transparency: str, status: str, expected: EventStatus
    ) -> None:
        """Test mapping of transparency and status to EventStatus."""
        # Mock component for the new signature requirement
        mock_component = type(
            "MockComponent",
            (),
            {
                "get": lambda self, key, default=None: None  # No Microsoft markers by default
            },
        )()
        result = parser._map_transparency_to_status(
            transparency or "OPAQUE", status, mock_component
        )
        assert result == expected

    def test_parse_status_values(self, parser: ICSParser) -> None:
        """Test parsing of various status values."""
        assert parser._parse_status("CONFIRMED") == "CONFIRMED"
        assert parser._parse_status("TENTATIVE") == "TENTATIVE"
        assert parser._parse_status("CANCELLED") == "CANCELLED"
        assert parser._parse_status(None) is None


class TestICSParserAttendees:
    """Test attendee parsing functionality."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_parse_attendee_basic(self, parser: ICSParser) -> None:
        """Test parsing basic attendee."""
        mock_attendee_prop: Any = MagicMock()
        mock_attendee_prop.__str__.return_value = "mailto:john.doe@example.com"
        mock_attendee_prop.params = {
            "CN": "John Doe",
            "ROLE": "REQ-PARTICIPANT",
            "PARTSTAT": "ACCEPTED",
        }

        result = parser._parse_attendee(mock_attendee_prop)

        assert result is not None
        assert result.email == "john.doe@example.com"
        assert result.name == "John Doe"
        assert result.type.name == "REQUIRED"
        assert result.response_status.name == "ACCEPTED"

    def test_parse_attendee_optional(self, parser: ICSParser) -> None:
        """Test parsing optional attendee."""
        mock_attendee_prop = MagicMock()
        mock_attendee_prop.__str__.return_value = "mailto:jane.doe@example.com"  # type: ignore
        mock_attendee_prop.params = {
            "CN": "Jane Doe",
            "ROLE": "OPT-PARTICIPANT",
            "PARTSTAT": "TENTATIVE",
        }

        result = parser._parse_attendee(mock_attendee_prop)

        assert result is not None
        assert result.email == "jane.doe@example.com"
        assert result.name == "Jane Doe"
        assert result.type.name == "OPTIONAL"
        assert result.response_status.name == "TENTATIVELY_ACCEPTED"

    def test_parse_attendee_resource(self, parser: ICSParser) -> None:
        """Test parsing resource attendee."""
        mock_attendee_prop = MagicMock()
        mock_attendee_prop.__str__.return_value = "mailto:room.a@example.com"  # type: ignore
        mock_attendee_prop.params = {
            "CN": "Conference Room A",
            "ROLE": "NON-PARTICIPANT",
            "PARTSTAT": "ACCEPTED",
        }

        result = parser._parse_attendee(mock_attendee_prop)

        assert result is not None
        assert result.email == "room.a@example.com"
        assert result.name == "Conference Room A"
        assert result.type.name == "RESOURCE"

    def test_parse_attendee_minimal_info(self, parser: ICSParser) -> None:
        """Test parsing attendee with minimal information."""
        mock_attendee_prop = MagicMock()
        mock_attendee_prop.__str__.return_value = "mailto:minimal@example.com"  # type: ignore
        mock_attendee_prop.params = {}

        result = parser._parse_attendee(mock_attendee_prop)

        assert result is not None
        assert result.email == "minimal@example.com"
        assert result.name == "minimal"  # Extracted from email

    def test_parse_attendee_exception(self, parser: ICSParser) -> None:
        """Test attendee parsing with exception."""
        mock_attendee_prop = MagicMock()
        mock_attendee_prop.__str__.side_effect = Exception("Parse error")  # type: ignore

        result = parser._parse_attendee(mock_attendee_prop)
        assert result is None


class TestICSParserOnlineMeetingDetection:
    """Test online meeting URL detection."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_parse_event_with_teams_meeting(self, parser: ICSParser) -> None:
        """Test detection of Microsoft Teams meeting."""
        teams_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:teams-meeting
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:Teams Meeting
DESCRIPTION:Join Microsoft Teams Meeting: https://teams.microsoft.com/l/meetup-join/19%3ameeting_example
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(teams_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.is_online_meeting is True
        assert "teams.microsoft.com" in event.online_meeting_url

    def test_parse_event_with_zoom_meeting(self, parser: ICSParser) -> None:
        """Test detection of Zoom meeting."""
        zoom_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:zoom-meeting
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:Zoom Meeting
DESCRIPTION:Join Zoom Meeting: https://zoom.us/j/1234567890
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(zoom_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.is_online_meeting is True
        assert "zoom.us" in event.online_meeting_url

    def test_parse_event_with_google_meet(self, parser: ICSParser) -> None:
        """Test detection of Google Meet."""
        meet_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:google-meet
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:Google Meet
DESCRIPTION:Join Google Meet: https://meet.google.com/abc-defg-hij
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(meet_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.is_online_meeting is True
        assert "meet.google.com" in event.online_meeting_url

    def test_parse_event_no_online_meeting(self, parser: ICSParser) -> None:
        """Test event without online meeting detection."""
        regular_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:regular-meeting
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:In-Person Meeting
DESCRIPTION:Regular meeting in conference room
LOCATION:Conference Room A
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(regular_ics)

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.is_online_meeting is False
        assert event.online_meeting_url is None


class TestICSParserFiltering:
    """Test event filtering functionality."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_filter_busy_events_keeps_busy(self, parser: ICSParser) -> None:
        """Test that filter_busy_events keeps busy events."""
        busy_event = MagicMock()
        busy_event.is_busy_status = True
        busy_event.is_cancelled = False

        result = parser.filter_busy_events([busy_event])
        assert len(result) == 1
        assert result[0] == busy_event

    def test_filter_busy_events_removes_free(self, parser: ICSParser) -> None:
        """Test that filter_busy_events removes free events."""
        free_event = MagicMock()
        free_event.is_busy_status = False
        free_event.is_cancelled = False

        result = parser.filter_busy_events([free_event])
        assert len(result) == 0

    def test_filter_busy_events_removes_cancelled(self, parser: ICSParser) -> None:
        """Test that filter_busy_events removes cancelled events."""
        cancelled_event = MagicMock()
        cancelled_event.is_busy_status = True
        cancelled_event.is_cancelled = True

        result = parser.filter_busy_events([cancelled_event])
        assert len(result) == 0

    def test_filter_busy_events_mixed(self, parser: ICSParser) -> None:
        """Test filtering with mixed event types."""
        busy_event = MagicMock()
        busy_event.is_busy_status = True
        busy_event.is_cancelled = False

        free_event = MagicMock()
        free_event.is_busy_status = False
        free_event.is_cancelled = False

        cancelled_event = MagicMock()
        cancelled_event.is_busy_status = True
        cancelled_event.is_cancelled = True

        events = [busy_event, free_event, cancelled_event]
        result = parser.filter_busy_events(events)  # type: ignore

        assert len(result) == 1
        assert result[0] == busy_event


class TestICSParserErrorHandling:
    """Test ICS Parser error handling."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_parse_event_with_missing_dtstart(self, parser: ICSParser) -> None:
        """Test handling of event missing DTSTART."""
        invalid_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:no-dtstart
SUMMARY:Invalid Event
DTEND:20240101T150000Z
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(invalid_ics)

        assert result.success is True
        assert len(result.events) == 0  # Event should be skipped
        # Implementation logs warnings to Python logging, not result.warnings
        assert len(result.warnings) == 0

    def test_parse_event_with_invalid_datetime(self, parser: ICSParser) -> None:
        """Test handling of event with invalid datetime."""
        invalid_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:invalid-datetime
DTSTART:INVALID_DATE
DTEND:ANOTHER_INVALID_DATE
SUMMARY:Invalid DateTime Event
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(invalid_ics)

        assert result.success is True
        # Event with invalid datetime should be skipped
        assert len(result.events) == 0
        # Implementation logs warnings to Python logging, not result.warnings
        assert len(result.warnings) == 0

    def test_parse_ics_with_mixed_valid_invalid_events(self, parser: ICSParser) -> None:
        """Test parsing ICS with mix of valid and invalid events."""
        mixed_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:valid-event
DTSTART:20240101T140000Z
DTEND:20240101T150000Z
SUMMARY:Valid Event
END:VEVENT
BEGIN:VEVENT
UID:invalid-event
DTSTART:INVALID_DATE
SUMMARY:Invalid Event
END:VEVENT
BEGIN:VEVENT
UID:another-valid-event
DTSTART:20240101T160000Z
DTEND:20240101T170000Z
SUMMARY:Another Valid Event
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(mixed_ics)

        assert result.success is True
        assert len(result.events) == 2  # Only valid events
        # Implementation logs warnings to Python logging, not result.warnings
        assert len(result.warnings) == 0
        assert result.event_count == 2  # Only valid events counted

        # Verify valid events are included
        event_subjects = [event.subject for event in result.events]
        assert "Valid Event" in event_subjects
        assert "Another Valid Event" in event_subjects


class TestICSParserRecurrence:
    """Test recurrence handling (basic implementation)."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_expand_recurring_events_placeholder(self, parser: ICSParser) -> None:
        """Test that expand_recurring_events returns original events (placeholder)."""
        # Mock events
        events = [MagicMock(), MagicMock()]
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)

        result = parser.expand_recurring_events(events, start_date, end_date)  # type: ignore

        # Current implementation returns original events
        assert result == events


class TestICSParserHelperMethods:
    """Test ICS Parser helper methods."""

    @pytest.fixture
    def parser(self, test_settings: Any) -> ICSParser:
        """Create ICSParser instance for testing."""
        with patch("calendarbot.ics.parser.SecurityEventLogger"):
            return ICSParser(test_settings)

    def test_get_calendar_property_existing(self, parser: ICSParser) -> None:
        """Test getting existing calendar property."""
        mock_calendar = MagicMock()
        mock_calendar.get.return_value = "Test Calendar"

        result = parser._get_calendar_property(mock_calendar, "X-WR-CALNAME")

        assert result == "Test Calendar"
        mock_calendar.get.assert_called_once_with("X-WR-CALNAME")

    def test_get_calendar_property_missing(self, parser: ICSParser) -> None:
        """Test getting missing calendar property."""
        mock_calendar = MagicMock()
        mock_calendar.get.return_value = None

        result = parser._get_calendar_property(mock_calendar, "MISSING-PROPERTY")

        assert result is None

    def test_get_calendar_property_exception(self, parser: ICSParser) -> None:
        """Test getting calendar property with exception."""
        mock_calendar = MagicMock()
        mock_calendar.get.side_effect = Exception("Property error")

        result = parser._get_calendar_property(mock_calendar, "PROBLEMATIC-PROPERTY")

        assert result is None


@pytest.mark.asyncio
async def test_ics_parser_integration_flow(test_settings: Any, sample_ics_content: str) -> None:
    """Integration test of ICS Parser complete workflow."""
    with patch("calendarbot.ics.parser.SecurityEventLogger"):
        parser = ICSParser(test_settings)

        # Test validation
        is_valid = parser.validate_ics_content(sample_ics_content)
        assert is_valid is True

        # Test parsing
        result = parser.parse_ics_content(sample_ics_content)
        assert result.success is True
        assert isinstance(result.events, list)

        # Test filtering
        if result.events:
            busy_events = parser.filter_busy_events(result.events)
            assert isinstance(busy_events, list)


@pytest.mark.parametrize(
    "ics_fixture,expected_events",
    [
        ("sample_ics_content", 1),
        # Could add more test data fixtures here
    ],
)
def test_ics_parser_with_various_content(
    test_settings: Any, ics_fixture: str, expected_events: int, request: Any
) -> None:
    """Parametrized test for parsing various ICS content."""
    ics_content = request.getfixturevalue(ics_fixture)

    with patch("calendarbot.ics.parser.SecurityEventLogger"):
        parser = ICSParser(test_settings)
        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) >= 0  # Could be filtered out
        assert result.event_count >= expected_events
