"""Unit tests for calendarbot_lite.lite_parser module - Core parsing functionality."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock, patch

import pytest
from icalendar import Calendar

from calendarbot_lite.calendar.lite_models import LiteCalendarEvent, LiteICSParseResult
from calendarbot_lite.calendar.lite_parser import LiteICSParser, _DateTimeWrapper, _SimpleEvent

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings():
    """Mock settings for parser."""
    settings = Mock()
    settings.enable_rrule_expansion = True
    settings.rrule_expansion_days = 365
    settings.max_occurrences_per_rule = 250
    settings.raw_components_superset_limit = 1500
    # RRULE worker pool settings
    settings.rrule_worker_concurrency = 1
    settings.expansion_days_window = 365
    settings.expansion_time_budget_ms_per_rule = 200
    settings.expansion_yield_frequency = 50
    return settings


@pytest.fixture
def parser(mock_settings):
    """Create parser instance."""
    return LiteICSParser(mock_settings)


# Sample ICS content for testing
SIMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-1
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Test Meeting
DESCRIPTION:Test description
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

EMPTY_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR
"""

INVALID_ICS_MISSING_BEGIN = """VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR
"""

INVALID_ICS_MISSING_END = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
"""

ALL_DAY_EVENT_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:all-day-1
DTSTART;VALUE=DATE:20250115
DTEND;VALUE=DATE:20250116
SUMMARY:All Day Event
STATUS:CONFIRMED
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR
"""

FREE_EVENT_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:free-event-1
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Free Time
STATUS:CONFIRMED
TRANSP:TRANSPARENT
SHOW-AS:FREE
END:VEVENT
END:VCALENDAR
"""

CANCELLED_EVENT_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:cancelled-1
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Cancelled Meeting
STATUS:CANCELLED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""


class TestLiteICSParserInit:
    """Test parser initialization."""

    def test_init_creates_parser(self, mock_settings):
        """Test that parser initializes with required components."""
        parser = LiteICSParser(mock_settings)

        assert parser.settings == mock_settings
        assert parser.rrule_expander is not None
        assert parser._streaming_parser is not None
        assert parser._datetime_parser is not None
        assert parser._attendee_parser is not None
        assert parser._event_parser is not None
        assert parser._event_merger is not None
        assert parser._rrule_orchestrator is not None


class TestValidateICSContent:
    """Test ICS content validation."""

    def test_validate_valid_ics(self, parser):
        """Test validation of valid ICS content."""
        assert parser.validate_ics_content(SIMPLE_ICS) is True

    def test_validate_empty_content(self, parser):
        """Test validation of empty content."""
        assert parser.validate_ics_content("") is False
        assert parser.validate_ics_content("   ") is False
        assert parser.validate_ics_content(None) is False

    def test_validate_missing_begin_marker(self, parser):
        """Test validation fails when BEGIN:VCALENDAR is missing."""
        assert parser.validate_ics_content(INVALID_ICS_MISSING_BEGIN) is False

    def test_validate_missing_end_marker(self, parser):
        """Test validation fails when END:VCALENDAR is missing."""
        assert parser.validate_ics_content(INVALID_ICS_MISSING_END) is False

    def test_validate_malformed_ics(self, parser):
        """Test validation of completely malformed ICS."""
        malformed = "This is not ICS content at all"
        assert parser.validate_ics_content(malformed) is False


class TestParseICSContentBasic:
    """Test basic ICS content parsing."""

    @pytest.mark.smoke  # Critical path: Core parsing functionality
    def test_parse_simple_event(self, parser):
        """Test parsing a simple single event."""
        result = parser.parse_ics_content(SIMPLE_ICS)

        assert result.success is True
        assert result.error_message is None
        assert len(result.events) > 0

        # Verify event details
        event = result.events[0]
        assert event.subject == "Test Meeting"
        assert event.is_cancelled is False

    def test_parse_empty_calendar(self, parser):
        """Test parsing calendar with no events."""
        result = parser.parse_ics_content(EMPTY_ICS)

        assert result.success is True
        assert len(result.events) == 0

    def test_parse_empty_content(self, parser):
        """Test parsing empty content returns failure."""
        result = parser.parse_ics_content("")

        assert result.success is False
        assert "Empty ICS content" in result.error_message

    def test_parse_none_content(self, parser):
        """Test parsing None content returns failure."""
        result = parser.parse_ics_content(None)

        assert result.success is False
        assert "Empty ICS content" in result.error_message

    def test_parse_whitespace_only(self, parser):
        """Test parsing whitespace-only content."""
        result = parser.parse_ics_content("   \n\t  ")

        assert result.success is False
        assert "Empty ICS content" in result.error_message

    def test_parse_with_source_url(self, parser):
        """Test parsing includes source URL in result."""
        source_url = "https://calendar.example.com/cal.ics"
        result = parser.parse_ics_content(SIMPLE_ICS, source_url=source_url)

        assert result.source_url == source_url

    def test_parse_extracts_metadata(self, parser):
        """Test parsing extracts calendar metadata."""
        ics_with_metadata = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Company//Test Product//EN
X-WR-CALNAME:Test Calendar
X-WR-CALDESC:A test calendar description
X-WR-TIMEZONE:America/New_York
BEGIN:VEVENT
UID:event1
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
SUMMARY:Event 1
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""
        result = parser.parse_ics_content(ics_with_metadata)

        assert result.success is True
        assert result.calendar_name == "Test Calendar"
        assert result.calendar_description == "A test calendar description"
        assert result.timezone == "America/New_York"
        assert result.ics_version == "2.0"
        assert "Test Company" in result.prodid


class TestParseEventFiltering:
    """Test event filtering logic."""

    def test_filter_excludes_free_events(self, parser):
        """Test that free/available events are filtered out."""
        result = parser.parse_ics_content(FREE_EVENT_ICS)

        assert result.success is True
        # Free events should be filtered in post-processing
        # The event is parsed but filtered by is_busy_status check
        if result.events:
            assert all(e.is_busy_status for e in result.events)

    def test_filter_excludes_cancelled_events(self, parser):
        """Test that cancelled events are filtered out."""
        result = parser.parse_ics_content(CANCELLED_EVENT_ICS)

        assert result.success is True
        # Cancelled events should be filtered out
        if result.events:
            assert all(not e.is_cancelled for e in result.events)

    def test_filter_busy_events_method(self, parser):
        """Test filter_busy_events() method."""
        # Create mock events
        busy_event = Mock(spec=LiteCalendarEvent)
        busy_event.is_busy_status = True
        busy_event.is_cancelled = False

        free_event = Mock(spec=LiteCalendarEvent)
        free_event.is_busy_status = False
        free_event.is_cancelled = False

        cancelled_event = Mock(spec=LiteCalendarEvent)
        cancelled_event.is_busy_status = True
        cancelled_event.is_cancelled = True

        events = [busy_event, free_event, cancelled_event]
        filtered = parser.filter_busy_events(events)

        assert len(filtered) == 1
        assert filtered[0] == busy_event


class TestShouldUseStreaming:
    """Test streaming parser selection logic."""

    def test_should_use_streaming_large_content(self, parser):
        """Test that large content triggers streaming parser."""
        # Create content larger than streaming threshold (10MB)
        large_content = "x" * (11 * 1024 * 1024)  # 11MB

        assert parser._should_use_streaming(large_content) is True

    def test_should_use_streaming_small_content(self, parser):
        """Test that small content uses traditional parser."""
        assert parser._should_use_streaming(SIMPLE_ICS) is False

    def test_should_use_streaming_empty_content(self, parser):
        """Test that empty content returns False."""
        assert parser._should_use_streaming("") is False

    def test_should_use_streaming_none_raises(self, parser):
        """Test that None content raises TypeError."""
        with pytest.raises(TypeError, match="ICS content cannot be None"):
            parser._should_use_streaming(None)

    def test_should_use_streaming_non_string_raises(self, parser):
        """Test that non-string content raises AttributeError."""
        with pytest.raises(AttributeError, match="must be a string"):
            parser._should_use_streaming(12345)


class TestParseOptimized:
    """Test parse_ics_content_optimized() method."""

    def test_optimized_uses_streaming_for_large(self, parser):
        """Test that optimized method uses streaming for large content."""
        large_content = "x" * (11 * 1024 * 1024)  # 11MB

        with patch.object(parser, '_parse_with_streaming') as mock_streaming:
            mock_streaming.return_value = LiteICSParseResult(success=True, events=[])
            parser.parse_ics_content_optimized(large_content)

            mock_streaming.assert_called_once()

    def test_optimized_uses_traditional_for_small(self, parser):
        """Test that optimized method uses traditional parser for small content."""
        with patch.object(parser, 'parse_ics_content') as mock_traditional:
            mock_traditional.return_value = LiteICSParseResult(success=True, events=[])
            parser.parse_ics_content_optimized(SIMPLE_ICS)

            mock_traditional.assert_called_once()


class TestGetCalendarProperty:
    """Test _get_calendar_property() helper."""

    def test_get_existing_property(self, parser):
        """Test getting an existing calendar property."""
        cal = Calendar.from_ical(SIMPLE_ICS)
        prodid = parser._get_calendar_property(cal, "PRODID")

        assert prodid is not None
        assert "Test" in prodid

    def test_get_missing_property(self, parser):
        """Test getting a missing property returns None."""
        cal = Calendar.from_ical(SIMPLE_ICS)
        result = parser._get_calendar_property(cal, "NONEXISTENT")

        assert result is None

    def test_get_property_exception_returns_none(self, parser):
        """Test that exceptions during property access return None."""
        cal = Mock()
        cal.get = Mock(side_effect=Exception("Test error"))

        result = parser._get_calendar_property(cal, "PRODID")
        assert result is None


class TestSimpleEventWrapper:
    """Test _SimpleEvent and _DateTimeWrapper helper classes."""

    def test_simple_event_initialization(self):
        """Test _SimpleEvent initializes with None values."""
        event = _SimpleEvent()

        assert event.start is None
        assert event.end is None
        assert event.id is None
        assert event.subject is None
        assert event.is_recurring is None

    def test_datetime_wrapper_initialization(self):
        """Test _DateTimeWrapper wraps datetime correctly."""
        dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        wrapper = _DateTimeWrapper(dt)

        assert wrapper.date_time == dt
        assert wrapper.time_zone == timezone.utc

    def test_datetime_wrapper_no_timezone(self):
        """Test _DateTimeWrapper with naive datetime."""
        dt = datetime(2025, 1, 15, 10, 0, 0)
        wrapper = _DateTimeWrapper(dt)

        assert wrapper.date_time == dt
        # When no tzinfo, time_zone defaults to UTC via getattr
        # The actual implementation returns dt.tzinfo which is None for naive datetimes
        assert wrapper.time_zone is None or wrapper.time_zone == timezone.utc


class TestExpandRecurringEvents:
    """Test recurring event expansion orchestration."""

    def test_expand_recurring_events_no_rrule(self, parser):
        """Test that non-recurring events return empty list."""
        events: list[Any] = []
        components: list[Any] = []

        result = parser._expand_recurring_events(events, components)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_expand_recurring_delegates_to_orchestrator(self, parser):
        """Test that expansion delegates to RRuleOrchestrator."""
        events: list[Any] = []
        components: list[Any] = []

        with patch.object(parser._rrule_orchestrator, 'expand_recurring_events') as mock_expand:
            mock_expand.return_value = []
            parser._expand_recurring_events(events, components)

            mock_expand.assert_called_once_with(events, components)


class TestMergeAndDeduplicateEvents:
    """Test event merging and deduplication."""

    def test_merge_expanded_events_delegates(self, parser):
        """Test that merge delegates to event merger."""
        original: list[Any] = []
        expanded: list[Any] = []

        with patch.object(parser._event_merger, 'merge_expanded_events') as mock_merge:
            mock_merge.return_value = []
            parser._merge_expanded_events(original, expanded)

            mock_merge.assert_called_once_with(original, expanded)

    def test_deduplicate_events_delegates(self, parser):
        """Test that deduplication delegates to event merger."""
        events: list[Any] = []

        with patch.object(parser._event_merger, 'deduplicate_events') as mock_dedup:
            mock_dedup.return_value = []
            parser._deduplicate_events(events)

            mock_dedup.assert_called_once_with(events)


class TestParseDateTimeHelpers:
    """Test datetime parsing helper methods."""

    def test_parse_datetime_delegates(self, parser):
        """Test that _parse_datetime delegates to datetime parser."""
        dt_prop = Mock()

        with patch.object(parser._datetime_parser, 'parse_datetime') as mock_parse:
            mock_parse.return_value = datetime.now(timezone.utc)
            parser._parse_datetime(dt_prop)

            mock_parse.assert_called_once_with(dt_prop, None)

    def test_parse_datetime_optional_delegates(self, parser):
        """Test that _parse_datetime_optional delegates to datetime parser."""
        dt_prop = Mock()

        with patch.object(parser._datetime_parser, 'parse_datetime_optional') as mock_parse:
            mock_parse.return_value = None
            parser._parse_datetime_optional(dt_prop)

            mock_parse.assert_called_once_with(dt_prop)


class TestParseAttendee:
    """Test attendee parsing."""

    def test_parse_attendee_delegates(self, parser):
        """Test that _parse_attendee delegates to attendee parser."""
        attendee_prop = Mock()

        with patch.object(parser._attendee_parser, 'parse_attendee') as mock_parse:
            mock_parse.return_value = None
            parser._parse_attendee(attendee_prop)

            mock_parse.assert_called_once_with(attendee_prop)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
