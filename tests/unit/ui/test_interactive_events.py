"""
Tests for InteractiveController event retrieval functionality.

This module focuses on event retrieval methods including getting events
for specific dates, week ranges, and event processing for date grouping.
"""

from datetime import date, datetime as dt, timedelta
from unittest.mock import Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent


class TestEventRetrievalMethods:
    """Test event retrieval core functionality."""

    @pytest.mark.asyncio
    async def test_get_events_for_date_when_normal_flow_then_returns_events(
        self, interactive_controller, test_date
    ) -> None:
        """Test normal event retrieval for a specific date."""
        mock_events = [Mock(spec=CachedEvent), Mock(spec=CachedEvent)]
        interactive_controller.cache_manager.get_events_by_date_range.return_value = mock_events

        result = await interactive_controller.get_events_for_date(test_date)

        # Verify correct date range calculation
        start_datetime = dt.combine(test_date, dt.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        interactive_controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )
        assert result == mock_events

    @pytest.mark.asyncio
    async def test_get_events_for_date_when_exception_then_returns_empty_list(
        self, interactive_controller, test_date
    ) -> None:
        """Test event retrieval handles exceptions gracefully."""
        interactive_controller.cache_manager.get_events_by_date_range.side_effect = Exception(
            "Test error"
        )

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            result = await interactive_controller.get_events_for_date(test_date)

            mock_logger.exception.assert_called_once()
            assert result == []

    @pytest.mark.asyncio
    async def test_get_events_for_week_when_normal_flow_then_returns_events_grouped_by_date(
        self, interactive_controller, test_date
    ) -> None:
        """Test weekly event retrieval groups events by date."""
        # Create mock events with different dates
        mock_event1 = Mock(spec=CachedEvent)
        mock_event1.start_dt = dt(2024, 1, 15, 10, 0, 0)
        mock_event1.subject = "Event 1"

        mock_event2 = Mock(spec=CachedEvent)
        mock_event2.start_dt = dt(2024, 1, 16, 14, 0, 0)
        mock_event2.subject = "Event 2"

        mock_events = [mock_event1, mock_event2]
        interactive_controller.cache_manager.get_events_by_date_range.return_value = mock_events

        result = await interactive_controller.get_events_for_week(test_date)

        # Verify week range calculation (Monday to Sunday)
        start_of_week = date(2024, 1, 15)  # Monday
        end_of_week = date(2024, 1, 21)  # Sunday
        start_datetime = dt.combine(start_of_week, dt.min.time())
        end_datetime = dt.combine(end_of_week, dt.max.time())

        interactive_controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )

        # Verify result structure - should contain all 7 days
        assert len(result) == 7
        for day_offset in range(7):
            current_date = start_of_week + timedelta(days=day_offset)
            assert current_date in result

        # Verify events are grouped correctly
        assert mock_event1 in result[date(2024, 1, 15)]
        assert mock_event2 in result[date(2024, 1, 16)]

    @pytest.mark.asyncio
    async def test_get_events_for_week_when_exception_then_returns_empty_dict(
        self, interactive_controller, test_date
    ) -> None:
        """Test weekly event retrieval handles exceptions gracefully."""
        interactive_controller.cache_manager.get_events_by_date_range.side_effect = Exception(
            "Test error"
        )

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            result = await interactive_controller.get_events_for_week(test_date)

            mock_logger.exception.assert_called_once()
            assert result == {}


class TestEventDateGrouping:
    """Test event processing for date grouping functionality."""

    def test_process_event_for_date_grouping_when_has_start_dt_then_adds_to_correct_date(
        self, interactive_controller, mock_cached_event
    ) -> None:
        """Test event grouping using start_dt attribute."""
        events_by_date = {date(2024, 1, 15): [], date(2024, 1, 16): []}

        interactive_controller._process_event_for_date_grouping(mock_cached_event, events_by_date)

        assert mock_cached_event in events_by_date[date(2024, 1, 15)]
        assert len(events_by_date[date(2024, 1, 16)]) == 0

    def test_process_event_for_date_grouping_when_has_start_datetime_string_then_parses_and_adds(
        self, interactive_controller
    ) -> None:
        """Test event grouping using start_datetime string parsing."""
        mock_event = Mock(spec=CachedEvent)
        mock_event.subject = "Event 2"
        mock_event.start_datetime = "2024-01-16T14:00:00Z"
        mock_event.start_dt = dt(2024, 1, 16, 14, 0, 0)  # Simulate parsed datetime

        events_by_date = {date(2024, 1, 15): [], date(2024, 1, 16): []}

        interactive_controller._process_event_for_date_grouping(mock_event, events_by_date)

        assert len(events_by_date[date(2024, 1, 15)]) == 0
        assert mock_event in events_by_date[date(2024, 1, 16)]

    def test_process_event_for_date_grouping_when_invalid_datetime_then_logs_and_skips(
        self, interactive_controller
    ) -> None:
        """Test event grouping handles invalid datetime strings gracefully."""
        mock_event = Mock(spec=CachedEvent)
        mock_event.subject = "Test Event"
        mock_event.start_datetime = "invalid-datetime"
        # Remove start_dt to force datetime parsing
        del mock_event.start_dt

        events_by_date = {date(2024, 1, 15): [], date(2024, 1, 16): []}

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            interactive_controller._process_event_for_date_grouping(mock_event, events_by_date)

            # Should log debug messages and skip event
            assert mock_logger.debug.call_count >= 1
            assert len(events_by_date[date(2024, 1, 15)]) == 0
            assert len(events_by_date[date(2024, 1, 16)]) == 0

    def test_process_event_for_date_grouping_when_date_not_in_dict_then_skips_with_debug(
        self, interactive_controller
    ) -> None:
        """Test event grouping skips events for dates not in the target dictionary."""
        mock_event = Mock(spec=CachedEvent)
        mock_event.subject = "Test Event"
        mock_event.start_dt = dt(2024, 1, 17, 10, 0, 0)  # Date not in events_by_date

        events_by_date = {date(2024, 1, 15): [], date(2024, 1, 16): []}

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            interactive_controller._process_event_for_date_grouping(mock_event, events_by_date)

            # Should log debug and not add event anywhere
            assert mock_logger.debug.call_count >= 1
            assert len(events_by_date[date(2024, 1, 15)]) == 0
            assert len(events_by_date[date(2024, 1, 16)]) == 0


if __name__ == "__main__":
    pytest.main([__file__])
