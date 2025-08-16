"""Integration tests for RRULE expansion in ICS parser."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from calendarbot.config.settings import CalendarBotSettings
from calendarbot.ics.parser import ICSParser


class TestRRuleExpansionIntegration:
    """Integration tests for RRULE expansion with ICS parser."""

    @pytest.fixture
    def settings(self):
        """Create test settings with RRULE expansion enabled."""
        settings = Mock(spec=CalendarBotSettings)
        settings.enable_rrule_expansion = True
        settings.rrule_expansion_days = 365
        settings.rrule_max_occurrences = 1000
        return settings

    @pytest.fixture
    def parser(self, settings):
        """Create ICS parser with RRULE expansion enabled."""
        return ICSParser(settings)

    def test_ani_ben_biweekly_integration(self, parser):
        """Test complete Ani <> Ben bi-weekly scenario integration."""
        # ICS content matching real Ani <> Ben pattern
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Microsoft Exchange Server 2010
BEGIN:VTIMEZONE
TZID:Pacific Standard Time
BEGIN:STANDARD
DTSTART:16010101T020000
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
RRULE:FREQ=YEARLY;INTERVAL=1;BYDAY=1SU;BYMONTH=11
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:16010101T020000
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
RRULE:FREQ=YEARLY;INTERVAL=1;BYDAY=2SU;BYMONTH=3
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;UNTIL=20260803T153000Z;INTERVAL=2;BYDAY=MO;WKST=SU
EXDATE;TZID=Pacific Standard Time:20250623T083000
UID:040000008200E00074C5B7101A82E00800000000C149321915B6DB01000000000000000010000000DA69B381A2934749BF2FFBEE588735EF
SUMMARY:Ani <> Ben- 1:1- Bi Weekly
DTSTART;TZID=Pacific Standard Time:20250526T083000
DTEND;TZID=Pacific Standard Time:20250526T090000
CLASS:PUBLIC
PRIORITY:5
DTSTAMP:20250815T231524Z
TRANSP:OPAQUE
STATUS:CONFIRMED
SEQUENCE:0
LOCATION:Microsoft Teams Meeting
END:VEVENT
END:VCALENDAR"""

        # Parse the ICS content
        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) > 1  # Should have expanded events

        # Find the August 18, 2025 event (target missing event)
        aug_18_events = [
            event
            for event in result.events
            if event.start.date_time.date() == datetime(2025, 8, 18).date()
        ]

        assert len(aug_18_events) == 1
        event = aug_18_events[0]
        assert event.subject == "Ani <> Ben- 1:1- Bi Weekly"
        assert event.is_expanded_instance is True

        # Verify June 23 is excluded (EXDATE)
        june_23_events = [
            event
            for event in result.events
            if event.start.date_time.date() == datetime(2025, 6, 23).date()
        ]
        assert len(june_23_events) == 0

    def test_jayson_ben_weekly_integration(self, parser):
        """Test complete Jayson <> Ben weekly scenario integration."""
        # ICS content matching real Jayson <> Ben pattern
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Microsoft Exchange Server 2010
BEGIN:VTIMEZONE
TZID:Pacific Standard Time
BEGIN:STANDARD
DTSTART:16010101T020000
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
RRULE:FREQ=YEARLY;INTERVAL=1;BYDAY=1SU;BYMONTH=11
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:16010101T020000
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
RRULE:FREQ=YEARLY;INTERVAL=1;BYDAY=2SU;BYMONTH=3
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;UNTIL=20260814T180000Z;INTERVAL=1;BYDAY=FR;WKST=SU
EXDATE;TZID=Pacific Standard Time:20250620T110000,20250627T110000,20250704T110000,20250725T110000
UID:040000008200E00074C5B7101A82E0080000000097DF19F9F2CFDB01000000000000000010000000BA11CAB82945254E98FA66120CB06212
SUMMARY:Jayson <> Ben - 1:1- Weekly
DTSTART;TZID=Pacific Standard Time:20250606T110000
DTEND;TZID=Pacific Standard Time:20250606T113000
CLASS:PUBLIC
PRIORITY:5
DTSTAMP:20250815T231524Z
TRANSP:OPAQUE
STATUS:CONFIRMED
SEQUENCE:0
LOCATION:Microsoft Teams Meeting
END:VEVENT
END:VCALENDAR"""

        # Parse the ICS content
        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) > 1  # Should have expanded events

        # Find the August 15, 2025 event (target missing event)
        aug_15_events = [
            event
            for event in result.events
            if event.start.date_time.date() == datetime(2025, 8, 15).date()
        ]

        assert len(aug_15_events) == 1
        event = aug_15_events[0]
        assert event.subject == "Jayson <> Ben - 1:1- Weekly"
        assert event.is_expanded_instance is True

        # Verify excluded dates are not present
        excluded_dates = [
            datetime(2025, 6, 20).date(),
            datetime(2025, 6, 27).date(),
            datetime(2025, 7, 4).date(),
            datetime(2025, 7, 25).date(),
        ]

        for excluded_date in excluded_dates:
            excluded_events = [
                event for event in result.events if event.start.date_time.date() == excluded_date
            ]
            assert len(excluded_events) == 0

    def test_expansion_disabled_fallback(self, settings):
        """Test that parser works normally when RRULE expansion is disabled."""
        settings.enable_rrule_expansion = False
        parser = ICSParser(settings)

        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO
UID:test-event
SUMMARY:Test Recurring Event
DTSTART:20250526T100000Z
DTEND:20250526T110000Z
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        # Should only have the master event, no expanded instances
        assert len(result.events) == 1
        assert result.events[0].is_recurring is True

    def test_mixed_events_integration(self, parser):
        """Test parsing ICS with both recurring and non-recurring events."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:single-event
SUMMARY:Single Meeting
DTSTART:20250820T100000Z
DTEND:20250820T110000Z
END:VEVENT
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=WE;COUNT=3
UID:recurring-event
SUMMARY:Weekly Standup
DTSTART:20250521T140000Z
DTEND:20250521T150000Z
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        # Should have single event + 3 recurring instances = 4 total
        assert len(result.events) == 4

        # Check single event
        single_events = [e for e in result.events if e.subject == "Single Meeting"]
        assert len(single_events) == 1
        assert single_events[0].is_recurring is False

        # Check recurring events
        recurring_events = [e for e in result.events if e.subject == "Weekly Standup"]
        assert len(recurring_events) == 3

        # Check that all recurring instances are marked correctly
        for event in recurring_events:
            assert event.is_expanded_instance is True

    @pytest.mark.skip(reason="Deduplication of RECURRENCE-ID overrides not yet implemented")
    def test_deduplication_with_explicit_vevent(self, parser):
        """Test deduplication when both RRULE and explicit VEVENT exist."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO;COUNT=3
UID:recurring-master
SUMMARY:Team Meeting
DTSTART:20250526T100000Z
DTEND:20250526T110000Z
END:VEVENT
BEGIN:VEVENT
UID:recurring-master
RECURRENCE-ID:20250526T100000Z
SUMMARY:Team Meeting
DTSTART:20250526T100000Z
DTEND:20250526T110000Z
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        assert result.success is True

        # Should not have duplicates for the same occurrence
        events_on_526 = [
            e for e in result.events if e.start.date_time.date() == datetime(2025, 5, 26).date()
        ]
        assert len(events_on_526) == 1  # No duplicates

    def test_performance_with_large_recurring_series(self, parser):
        """Test performance with large recurring series."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO;COUNT=100
UID:large-series
SUMMARY:Large Recurring Series
DTSTART:20250101T100000Z
DTEND:20250101T110000Z
END:VEVENT
END:VCALENDAR"""

        import time

        start_time = time.time()

        result = parser.parse_ics_content(ics_content)

        end_time = time.time()
        processing_time = end_time - start_time

        assert result.success is True
        assert len(result.events) == 100
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0  # 5 seconds

    def test_error_handling_malformed_rrule(self, parser):
        """Test graceful handling of malformed RRULE."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:INVALID_RRULE_STRING
UID:malformed-event
SUMMARY:Malformed RRULE Event
DTSTART:20250526T100000Z
DTEND:20250526T110000Z
END:VEVENT
END:VCALENDAR"""

        # Should not crash, should gracefully degrade
        result = parser.parse_ics_content(ics_content)

        # Should still parse successfully, just without expansion
        assert result.success is True
        # Should have at least the master event
        assert len(result.events) >= 1

    def test_timezone_handling_in_expansion(self, parser):
        """Test timezone handling in RRULE expansion."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:STANDARD
DTSTART:20071104T020000
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:20070311T020000
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=TU;COUNT=3
UID:timezone-event
SUMMARY:Timezone Test Meeting
DTSTART;TZID=America/Los_Angeles:20250527T090000
DTEND;TZID=America/Los_Angeles:20250527T100000
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        assert len(result.events) == 3

        # All events should have proper timezone information
        for event in result.events:
            assert event.start.time_zone == "America/Los_Angeles"

    def test_complex_exdate_patterns(self, parser):
        """Test complex EXDATE patterns with multiple formats."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=FR;COUNT=10
EXDATE:20250530T100000Z,20250613T100000Z
EXDATE;TZID=UTC:20250627T100000Z
UID:complex-exdate
SUMMARY:Complex EXDATE Test
DTSTART:20250523T100000Z
DTEND:20250523T110000Z
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        # Should have 7 events (10 minus 3 excluded)
        assert len(result.events) == 7

        # Verify excluded dates are not present
        excluded_dates = [
            datetime(2025, 5, 30).date(),
            datetime(2025, 6, 13).date(),
            datetime(2025, 6, 27).date(),
        ]

        for excluded_date in excluded_dates:
            excluded_events = [
                e for e in result.events if e.start.date_time.date() == excluded_date
            ]
            assert len(excluded_events) == 0


class TestRRuleExpansionPerformance:
    """Performance tests for RRULE expansion."""

    @pytest.fixture
    def settings(self):
        """Create performance test settings."""
        settings = Mock(spec=CalendarBotSettings)
        settings.enable_rrule_expansion = True
        settings.rrule_expansion_days = 365
        settings.rrule_max_occurrences = 5000  # Higher limit for performance tests
        return settings

    @pytest.fixture
    def parser(self, settings):
        """Create parser for performance tests."""
        return ICSParser(settings)

    def test_memory_usage_large_expansion(self, parser):
        """Test memory usage with large RRULE expansion."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create ICS with large recurring series
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO;COUNT=1000
UID:large-memory-test
SUMMARY:Large Memory Test
DTSTART:20250101T100000Z
DTEND:20250101T110000Z
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        assert result.success is True
        assert len(result.events) == 1000

        # Memory increase should be reasonable (adjust threshold as needed)
        # Allow up to 100MB increase for 1000 events
        assert memory_increase < 100 * 1024 * 1024

    def test_concurrent_parsing_performance(self, parser):
        """Test performance with concurrent parsing operations."""
        import threading
        import time

        def parse_ics():
            ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=WE;COUNT=50
UID:concurrent-test
SUMMARY:Concurrent Test Meeting
DTSTART:20250101T100000Z
DTEND:20250101T110000Z
END:VEVENT
END:VCALENDAR"""
            return parser.parse_ics_content(ics_content)

        # Run multiple parsing operations concurrently
        threads = []
        results = []

        start_time = time.time()

        for i in range(5):
            thread = threading.Thread(target=lambda: results.append(parse_ics()))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # All operations should complete successfully
        assert len(results) == 5
        assert all(result.success for result in results)

        # Should complete within reasonable time
        assert total_time < 10.0  # 10 seconds for 5 concurrent operations
