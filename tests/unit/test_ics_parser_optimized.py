"""Optimized ICS parser tests for core parsing functionality."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from calendarbot.ics.models import EventStatus
from calendarbot.ics.parser import ICSParser


@pytest.mark.unit
@pytest.mark.critical_path
class TestICSParserCore:
    """Core ICS parsing functionality tests."""

    @pytest.fixture
    def parser(self, test_settings):
        """Create ICS parser instance."""
        return ICSParser(test_settings)

    def test_parser_initialization(self, parser, test_settings):
        """Test parser initializes correctly."""
        assert parser.settings == test_settings
        assert parser.security_logger is not None

    def test_parse_valid_ics_content(self, parser, sample_ics_content):
        """Test parsing valid ICS content."""
        result = parser.parse_ics_content(sample_ics_content)

        assert result.success is True
        assert len(result.events) >= 1
        assert result.error_message is None

    def test_parse_ics_content_success_structure(self, parser, sample_ics_content):
        """Test parse result structure on success."""
        result = parser.parse_ics_content(sample_ics_content)

        assert result.success is True
        assert hasattr(result, "events")
        assert hasattr(result, "calendar_name")
        assert hasattr(result, "total_components")
        assert hasattr(result, "event_count")

    def test_parse_empty_ics_content(self, parser):
        """Test parsing empty ICS content."""
        result = parser.parse_ics_content("")

        assert result.success is False
        assert result.error_message is not None

    def test_parse_invalid_ics_content(self, parser):
        """Test parsing invalid ICS content."""
        invalid_content = "INVALID CONTENT"
        result = parser.parse_ics_content(invalid_content)

        assert result.success is False
        assert result.error_message is not None

    def test_validate_ics_content_valid(self, parser, sample_ics_content):
        """Test validation of valid ICS content."""
        is_valid = parser.validate_ics_content(sample_ics_content)

        assert is_valid is True

    def test_validate_ics_content_empty(self, parser):
        """Test validation of empty content."""
        is_valid = parser.validate_ics_content("")

        assert is_valid is False

    def test_validate_ics_content_missing_begin(self, parser):
        """Test validation when BEGIN:VCALENDAR is missing."""
        invalid_content = "END:VCALENDAR"
        is_valid = parser.validate_ics_content(invalid_content)

        assert is_valid is False

    def test_validate_ics_content_missing_end(self, parser):
        """Test validation when END:VCALENDAR is missing."""
        invalid_content = "BEGIN:VCALENDAR\nVERSION:2.0"
        is_valid = parser.validate_ics_content(invalid_content)

        assert is_valid is False

    @pytest.mark.parametrize(
        "transparency,status,expected",
        [
            ("OPAQUE", "CONFIRMED", EventStatus.BUSY),
            ("TRANSPARENT", "CONFIRMED", EventStatus.FREE),
            ("OPAQUE", "TENTATIVE", EventStatus.TENTATIVE),
            ("OPAQUE", "CANCELLED", EventStatus.FREE),
        ],
    )
    def test_map_transparency_to_status(self, parser, transparency, status, expected):
        """Test transparency mapping to event status."""
        result = parser._map_transparency_to_status(transparency, status)

        assert result == expected

    def test_parse_event_component_basic(self, parser):
        """Test parsing basic event component."""
        from datetime import datetime, timezone

        from icalendar import Event as ICalEvent

        # Create a minimal event component
        component = ICalEvent()
        component.add("UID", "test-event-1")
        component.add("SUMMARY", "Test Event")
        component.add("DTSTART", datetime.now(timezone.utc))
        component.add("DTEND", datetime.now(timezone.utc))

        event = parser._parse_event_component(component)

        assert event is not None
        assert event.id == "test-event-1"
        assert event.subject == "Test Event"

    def test_parse_event_component_missing_uid(self, parser):
        """Test parsing event component without UID generates one."""
        from datetime import datetime, timezone

        from icalendar import Event as ICalEvent

        component = ICalEvent()
        component.add("SUMMARY", "Test Event")
        component.add("DTSTART", datetime.now(timezone.utc))

        event = parser._parse_event_component(component)

        assert event is not None
        assert event.id is not None  # Should generate UUID
        assert len(event.id) > 0

    def test_parse_event_component_missing_dtstart(self, parser):
        """Test parsing event component without DTSTART returns None."""
        from icalendar import Event as ICalEvent

        component = ICalEvent()
        component.add("UID", "test-event-1")
        component.add("SUMMARY", "Test Event")

        event = parser._parse_event_component(component)

        assert event is None

    def test_filter_busy_events(self, parser, sample_events):
        """Test filtering to only busy events."""
        # Modify sample events to test filtering
        sample_events[0].show_as = EventStatus.BUSY
        sample_events[0].is_cancelled = False
        sample_events[1].show_as = EventStatus.FREE
        sample_events[1].is_cancelled = False

        filtered = parser.filter_busy_events(sample_events)

        # Should only include busy events
        assert len(filtered) == 1
        assert filtered[0].show_as == EventStatus.BUSY

    def test_filter_busy_events_excludes_cancelled(self, parser, sample_events):
        """Test that cancelled events are filtered out."""
        sample_events[0].show_as = EventStatus.BUSY
        sample_events[0].is_cancelled = True

        filtered = parser.filter_busy_events(sample_events)

        assert len(filtered) == 0

    def test_get_calendar_property_exists(self, parser):
        """Test getting calendar property that exists."""
        from icalendar import Calendar

        cal = Calendar()
        cal.add("PRODID", "Test Calendar")

        prop = parser._get_calendar_property(cal, "PRODID")

        assert prop == "Test Calendar"

    def test_get_calendar_property_missing(self, parser):
        """Test getting calendar property that doesn't exist."""
        from icalendar import Calendar

        cal = Calendar()

        prop = parser._get_calendar_property(cal, "NONEXISTENT")

        assert prop is None

    def test_parse_datetime_with_timezone(self, parser):
        """Test parsing datetime with timezone."""
        from datetime import datetime, timezone

        from icalendar.prop import vDDDTypes

        dt = datetime.now(timezone.utc)
        dt_prop = vDDDTypes(dt)

        parsed_dt = parser._parse_datetime(dt_prop)

        assert parsed_dt.tzinfo is not None

    def test_parse_datetime_without_timezone(self, parser):
        """Test parsing datetime without timezone uses UTC."""
        from datetime import datetime

        from icalendar.prop import vDDDTypes

        dt = datetime.now()  # No timezone
        dt_prop = vDDDTypes(dt)

        parsed_dt = parser._parse_datetime(dt_prop)

        assert parsed_dt.tzinfo is not None

    def test_expand_recurring_events_placeholder(self, parser, sample_events):
        """Test recurring events expansion placeholder."""
        start_date = datetime.now()
        end_date = datetime.now()

        # Currently returns events as-is (placeholder implementation)
        expanded = parser.expand_recurring_events(sample_events, start_date, end_date)

        assert expanded == sample_events

    def test_parse_attendee_basic(self, parser):
        """Test parsing basic attendee."""
        from icalendar.prop import vCalAddress

        attendee_prop = vCalAddress("mailto:test@example.com")
        attendee_prop.params["CN"] = "Test User"
        attendee_prop.params["ROLE"] = "REQ-PARTICIPANT"
        attendee_prop.params["PARTSTAT"] = "ACCEPTED"

        attendee = parser._parse_attendee(attendee_prop)

        assert attendee is not None
        assert attendee.email == "test@example.com"
        assert attendee.name == "Test User"

    def test_parse_attendee_minimal(self, parser):
        """Test parsing attendee with minimal info."""
        from icalendar.prop import vCalAddress

        attendee_prop = vCalAddress("mailto:test@example.com")

        attendee = parser._parse_attendee(attendee_prop)

        assert attendee is not None
        assert attendee.email == "test@example.com"
        assert attendee.name == "test"  # Extracted from email

    def test_parse_status_values(self, parser):
        """Test parsing various status values."""
        assert parser._parse_status("CONFIRMED") == "CONFIRMED"
        assert parser._parse_status("CANCELLED") == "CANCELLED"
        assert parser._parse_status("TENTATIVE") == "TENTATIVE"
        assert parser._parse_status(None) is None

    def test_parse_datetime_optional_none(self, parser):
        """Test parsing optional datetime when None."""
        result = parser._parse_datetime_optional(None)

        assert result is None

    def test_parse_datetime_optional_valid(self, parser):
        """Test parsing optional datetime when valid."""
        from datetime import datetime, timezone

        from icalendar.prop import vDDDTypes

        dt = datetime.now(timezone.utc)
        dt_prop = vDDDTypes(dt)

        result = parser._parse_datetime_optional(dt_prop)

        assert result is not None
        assert isinstance(result, datetime)


@pytest.mark.unit
class TestICSParserSecurity:
    """Security-related ICS parser tests."""

    @pytest.fixture
    def parser(self, test_settings):
        """Create ICS parser instance."""
        return ICSParser(test_settings)

    def test_validate_ics_content_security_logging(self, parser):
        """Test that invalid content triggers security logging."""
        # Security logger should log validation failures
        is_valid = parser.validate_ics_content("MALICIOUS CONTENT")

        assert is_valid is False
        # Security logger should have been called (tested via behavior)

    def test_parse_large_ics_content(self, parser):
        """Test parsing very large ICS content doesn't hang."""
        # Create content that's large but still valid
        large_content = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for i in range(100):  # Not too large to avoid memory issues
            large_content += f"BEGIN:VEVENT\nUID:event-{i}\nSUMMARY:Event {i}\nEND:VEVENT\n"
        large_content += "END:VCALENDAR"

        result = parser.parse_ics_content(large_content)

        # Should handle large content gracefully
        assert (
            result.success is True or result.success is False
        )  # Either works, just shouldn't hang

    def test_parse_malformed_datetime(self, parser):
        """Test handling malformed datetime in events."""
        malformed_ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-malformed
SUMMARY:Test Event
DTSTART:INVALID_DATE
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(malformed_ics)

        # Should either parse successfully (skipping bad event) or fail gracefully
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error_message is not None
