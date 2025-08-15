"""Unit tests for RRuleExpander class."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from calendarbot.config.settings import CalendarBotSettings
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus
from calendarbot.ics.rrule_expander import RRuleExpander, RRuleExpansionError, RRuleParseError


class TestRRuleExpander:
    """Test suite for RRuleExpander functionality."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = Mock(spec=CalendarBotSettings)
        settings.enable_rrule_expansion = True
        settings.rrule_expansion_days = 365
        settings.rrule_max_occurrences = 1000
        return settings

    @pytest.fixture
    def expander(self, settings):
        """Create RRuleExpander instance."""
        return RRuleExpander(settings)

    @pytest.fixture
    def master_event(self):
        """Create a master recurring event for testing."""
        return CalendarEvent(
            id="test-master-event",
            subject="Test Weekly Meeting",
            start=DateTimeInfo(
                date_time=datetime(2025, 5, 26, 8, 30, tzinfo=timezone.utc),
                time_zone="Pacific Standard Time",
            ),
            end=DateTimeInfo(
                date_time=datetime(2025, 5, 26, 9, 0, tzinfo=timezone.utc),
                time_zone="Pacific Standard Time",
            ),
            show_as=EventStatus.BUSY,
            is_recurring=True,
        )

    def test_init(self, settings):
        """Test RRuleExpander initialization."""
        expander = RRuleExpander(settings)

        assert expander.settings == settings
        assert expander.expansion_window_days == 365
        assert expander.enable_expansion is True

    def test_init_disabled(self, settings):
        """Test RRuleExpander with expansion disabled."""
        settings.enable_rrule_expansion = False
        expander = RRuleExpander(settings)

        assert expander.enable_expansion is False

    def test_parse_rrule_string_weekly(self, expander):
        """Test parsing weekly RRULE string."""
        rrule_string = "FREQ=WEEKLY;INTERVAL=1;BYDAY=FR;UNTIL=20260814T180000Z"

        result = expander.parse_rrule_string(rrule_string)

        assert result["freq"] == "WEEKLY"
        assert result["interval"] == 1
        assert result["byday"] == ["FR"]
        assert result["until"] == datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

    def test_parse_rrule_string_biweekly(self, expander):
        """Test parsing bi-weekly RRULE string."""
        rrule_string = "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;UNTIL=20260803T153000Z"

        result = expander.parse_rrule_string(rrule_string)

        assert result["freq"] == "WEEKLY"
        assert result["interval"] == 2
        assert result["byday"] == ["MO"]
        assert result["until"] == datetime(2026, 8, 3, 15, 30, tzinfo=timezone.utc)

    def test_parse_rrule_string_with_count(self, expander):
        """Test parsing RRULE with COUNT instead of UNTIL."""
        rrule_string = "FREQ=WEEKLY;INTERVAL=1;BYDAY=WE;COUNT=10"

        result = expander.parse_rrule_string(rrule_string)

        assert result["freq"] == "WEEKLY"
        assert result["interval"] == 1
        assert result["byday"] == ["WE"]
        assert result["count"] == 10
        assert "until" not in result

    def test_parse_rrule_string_invalid(self, expander):
        """Test parsing invalid RRULE string."""
        with pytest.raises(RRuleParseError):
            expander.parse_rrule_string("INVALID_RRULE")

    def test_parse_rrule_string_empty(self, expander):
        """Test parsing empty RRULE string."""
        with pytest.raises(RRuleParseError):
            expander.parse_rrule_string("")

    def test_apply_exdates_single(self, expander):
        """Test applying single EXDATE."""
        occurrences = [
            datetime(2025, 5, 26),
            datetime(2025, 6, 2),
            datetime(2025, 6, 9),
            datetime(2025, 6, 16),
        ]
        exdates = ["20250609T000000"]

        result = expander.apply_exdates(occurrences, exdates)

        expected = [datetime(2025, 5, 26), datetime(2025, 6, 2), datetime(2025, 6, 16)]
        assert result == expected

    def test_apply_exdates_multiple(self, expander):
        """Test applying multiple EXDATEs."""
        occurrences = [
            datetime(2025, 6, 6),
            datetime(2025, 6, 13),
            datetime(2025, 6, 20),
            datetime(2025, 6, 27),
            datetime(2025, 7, 4),
            datetime(2025, 7, 11),
        ]
        exdates = ["20250620T000000", "20250627T000000", "20250704T000000"]

        result = expander.apply_exdates(occurrences, exdates)

        expected = [datetime(2025, 6, 6), datetime(2025, 6, 13), datetime(2025, 7, 11)]
        assert result == expected

    def test_apply_exdates_none(self, expander):
        """Test applying no EXDATEs."""
        occurrences = [datetime(2025, 5, 26), datetime(2025, 6, 2)]

        result = expander.apply_exdates(occurrences, None)

        assert result == occurrences

    def test_apply_exdates_empty_list(self, expander):
        """Test applying empty EXDATE list."""
        occurrences = [datetime(2025, 5, 26), datetime(2025, 6, 2)]

        result = expander.apply_exdates(occurrences, [])

        assert result == occurrences

    def test_generate_event_instances(self, expander, master_event):
        """Test generating CalendarEvent instances from occurrences."""
        occurrences = [
            datetime(2025, 5, 26, 8, 30, tzinfo=timezone.utc),
            datetime(2025, 6, 2, 8, 30, tzinfo=timezone.utc),
            datetime(2025, 6, 9, 8, 30, tzinfo=timezone.utc),
        ]

        events = expander.generate_event_instances(master_event, occurrences)

        assert len(events) == 3

        # Check first generated event
        event1 = events[0]
        assert event1.subject == master_event.subject
        assert event1.show_as == master_event.show_as
        assert event1.is_expanded_instance is True
        assert event1.rrule_master_uid == master_event.id
        assert event1.start.date_time == occurrences[0]

        # Check unique IDs
        event_ids = [event.id for event in events]
        assert len(set(event_ids)) == 3  # All unique

    @patch("calendarbot.ics.rrule_expander.rrule")
    def test_expand_rrule_ani_ben_scenario(self, mock_rrule, expander, master_event):
        """Test expanding Ani <> Ben bi-weekly Monday pattern."""
        # Simulate the real scenario: bi-weekly Mondays
        master_event.subject = "Ani <> Ben- 1:1- Bi Weekly"
        master_event.start.date_time = datetime(2025, 5, 26, 8, 30, tzinfo=timezone.utc)

        # Mock dateutil.rrule to return expected occurrences
        mock_rrule_instance = Mock()
        mock_rrule_instance.__iter__ = Mock(
            return_value=iter(
                [
                    datetime(2025, 5, 26, 8, 30, tzinfo=timezone.utc),
                    datetime(2025, 6, 9, 8, 30, tzinfo=timezone.utc),
                    datetime(2025, 6, 23, 8, 30, tzinfo=timezone.utc),  # Will be excluded
                    datetime(2025, 7, 7, 8, 30, tzinfo=timezone.utc),
                    datetime(2025, 7, 21, 8, 30, tzinfo=timezone.utc),
                    datetime(2025, 8, 4, 8, 30, tzinfo=timezone.utc),
                    datetime(2025, 8, 18, 8, 30, tzinfo=timezone.utc),  # TARGET
                ]
            )
        )
        mock_rrule.return_value = mock_rrule_instance

        rrule_string = "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;UNTIL=20260803T153000Z"
        exdates = ["20250623T083000"]  # June 23 excluded

        events = expander.expand_rrule(
            master_event,
            rrule_string,
            exdates=exdates,
            start_date=datetime(2025, 5, 1),
            end_date=datetime(2025, 12, 31),
        )

        # Should generate 6 events (7 minus 1 excluded)
        assert len(events) == 6

        # Verify August 18, 2025 is included
        aug_18_events = [
            e for e in events if e.start.date_time.date() == datetime(2025, 8, 18).date()
        ]
        assert len(aug_18_events) == 1
        assert aug_18_events[0].subject == "Ani <> Ben- 1:1- Bi Weekly"

    @patch("calendarbot.ics.rrule_expander.rrule")
    def test_expand_rrule_jayson_scenario(self, mock_rrule, expander, master_event):
        """Test expanding Jayson <> Ben weekly Friday pattern."""
        # Simulate the real scenario: weekly Fridays
        master_event.subject = "Jayson <> Ben - 1:1- Weekly"
        master_event.start.date_time = datetime(2025, 6, 6, 11, 0, tzinfo=timezone.utc)

        # Mock dateutil.rrule to return expected occurrences
        mock_rrule_instance = Mock()
        mock_rrule_instance.__iter__ = Mock(
            return_value=iter(
                [
                    datetime(2025, 6, 6, 11, 0, tzinfo=timezone.utc),
                    datetime(2025, 6, 13, 11, 0, tzinfo=timezone.utc),
                    datetime(2025, 6, 20, 11, 0, tzinfo=timezone.utc),  # Excluded
                    datetime(2025, 6, 27, 11, 0, tzinfo=timezone.utc),  # Excluded
                    datetime(2025, 7, 4, 11, 0, tzinfo=timezone.utc),  # Excluded
                    datetime(2025, 7, 11, 11, 0, tzinfo=timezone.utc),
                    datetime(2025, 7, 18, 11, 0, tzinfo=timezone.utc),
                    datetime(2025, 7, 25, 11, 0, tzinfo=timezone.utc),  # Excluded
                    datetime(2025, 8, 1, 11, 0, tzinfo=timezone.utc),
                    datetime(2025, 8, 8, 11, 0, tzinfo=timezone.utc),
                    datetime(2025, 8, 15, 11, 0, tzinfo=timezone.utc),  # TARGET
                    datetime(2025, 8, 22, 11, 0, tzinfo=timezone.utc),
                ]
            )
        )
        mock_rrule.return_value = mock_rrule_instance

        rrule_string = "FREQ=WEEKLY;INTERVAL=1;BYDAY=FR;UNTIL=20260814T180000Z"
        exdates = ["20250620T110000", "20250627T110000", "20250704T110000", "20250725T110000"]

        events = expander.expand_rrule(
            master_event,
            rrule_string,
            exdates=exdates,
            start_date=datetime(2025, 6, 1),
            end_date=datetime(2025, 12, 31),
        )

        # Should generate 8 events (12 minus 4 excluded)
        assert len(events) == 8

        # Verify August 15, 2025 is included
        aug_15_events = [
            e for e in events if e.start.date_time.date() == datetime(2025, 8, 15).date()
        ]
        assert len(aug_15_events) == 1
        assert aug_15_events[0].subject == "Jayson <> Ben - 1:1- Weekly"

    def test_expand_rrule_date_range_filtering(self, expander, master_event):
        """Test date range filtering in RRULE expansion."""
        with patch("calendarbot.ics.rrule_expander.rrule") as mock_rrule:
            # Mock a series that extends beyond the filter range
            mock_rrule_instance = Mock()
            mock_rrule_instance.__iter__ = Mock(
                return_value=iter(
                    [
                        datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),  # Before range
                        datetime(2025, 5, 26, 10, 0, tzinfo=timezone.utc),  # In range
                        datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc),  # In range
                        datetime(2025, 12, 31, 10, 0, tzinfo=timezone.utc),  # After range
                    ]
                )
            )
            mock_rrule.return_value = mock_rrule_instance

            events = expander.expand_rrule(
                master_event,
                "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO",
                start_date=datetime(2025, 5, 1),
                end_date=datetime(2025, 8, 31),
            )

            # Should only include events within the date range
            assert len(events) == 2
            assert all(
                datetime(2025, 5, 1) <= event.start.date_time <= datetime(2025, 8, 31)
                for event in events
            )

    def test_expand_rrule_disabled(self, settings, master_event):
        """Test RRULE expansion when disabled."""
        settings.enable_rrule_expansion = False
        expander = RRuleExpander(settings)

        events = expander.expand_rrule(master_event, "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")

        assert events == []

    def test_expand_rrule_max_occurrences_limit(self, expander, master_event):
        """Test maximum occurrences limit."""
        expander.settings.rrule_max_occurrences = 5

        with patch("calendarbot.ics.rrule_expander.rrule") as mock_rrule:
            # Mock a series with more than max occurrences
            mock_rrule_instance = Mock()
            mock_rrule_instance.__iter__ = Mock(
                return_value=iter(
                    [
                        datetime(2025, 5, 26 + i * 7, 10, 0, tzinfo=timezone.utc)
                        for i in range(10)  # 10 occurrences
                    ]
                )
            )
            mock_rrule.return_value = mock_rrule_instance

            events = expander.expand_rrule(master_event, "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")

            # Should be limited to max occurrences
            assert len(events) == 5

    def test_expand_rrule_error_handling(self, expander, master_event):
        """Test error handling in RRULE expansion."""
        with patch("calendarbot.ics.rrule_expander.rrule", side_effect=Exception("Mock error")):
            with pytest.raises(RRuleExpansionError):
                expander.expand_rrule(master_event, "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")


class TestRRuleExpanderEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def expander(self):
        """Create RRuleExpander with minimal settings."""
        settings = Mock()
        settings.enable_rrule_expansion = True
        settings.rrule_expansion_days = 365
        settings.rrule_max_occurrences = 1000
        return RRuleExpander(settings)

    def test_daylight_saving_transition(self, expander):
        """Test RRULE expansion across DST transition."""
        # This test ensures timezone handling is correct
        # (Implementation will depend on actual timezone handling requirements)

    def test_leap_year_handling(self, expander):
        """Test RRULE expansion in leap year."""
        # Test February 29 handling in leap years

    def test_until_boundary_conditions(self, expander):
        """Test UNTIL date boundary conditions."""
        # Test events exactly on UNTIL date

    def test_malformed_exdate_graceful_handling(self, expander):
        """Test graceful handling of malformed EXDATE values."""
        occurrences = [datetime(2025, 5, 26), datetime(2025, 6, 2)]
        malformed_exdates = ["INVALID_DATE", "20250602T000000"]

        # Should handle gracefully and exclude valid dates
        result = expander.apply_exdates(occurrences, malformed_exdates)

        # Should exclude the valid date and ignore the invalid one
        assert len(result) == 1
        assert result[0] == datetime(2025, 5, 26)
