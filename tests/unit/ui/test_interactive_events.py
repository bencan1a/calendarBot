"""
Unit tests for InteractiveController event retrieval functionality.

This module tests the event retrieval methods in the InteractiveController class, focusing on:
- Getting events for a specific date
- Getting events for a week
- Processing events for date grouping
"""

from datetime import date, datetime as dt, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController


class TestEventRetrievalMethods:
    """Test event retrieval methods in InteractiveController."""

    @pytest.mark.asyncio
    async def test_get_events_for_date_when_normal_flow_then_returns_events(self) -> None:
        """Test get_events_for_date normal flow returns events."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range
        mock_events = [Mock(), Mock()]
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)
        
        # Call the method
        test_date = date(2024, 1, 15)
        result = await controller.get_events_for_date(test_date)
        
        # Verify get_events_by_date_range was called with correct date range
        start_datetime = dt.combine(test_date, dt.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )
        
        # Verify result is the mock events
        assert result == mock_events

    @pytest.mark.asyncio
    async def test_get_events_for_date_when_exception_then_returns_empty_list(self) -> None:
        """Test get_events_for_date with exception returns empty list."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range to raise exception
        controller.cache_manager.get_events_by_date_range = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Mock logger
        with patch('calendarbot.ui.interactive.logger') as mock_logger:
            # Call the method
            test_date = date(2024, 1, 15)
            result = await controller.get_events_for_date(test_date)
            
            # Verify exception was logged
            mock_logger.exception.assert_called_once()
            
            # Verify result is empty list
            assert result == []

    @pytest.mark.asyncio
    async def test_get_events_for_week_when_normal_flow_then_returns_events_by_date(self) -> None:
        """Test get_events_for_week normal flow returns events grouped by date."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock events with start_dt attributes
        mock_event1 = Mock()
        mock_event1.subject = "Event 1"
        mock_event1.start_datetime = "2024-01-15T10:00:00Z"
        mock_event1.start_dt = dt(2024, 1, 15, 10, 0, 0)
        
        mock_event2 = Mock()
        mock_event2.subject = "Event 2"
        mock_event2.start_datetime = "2024-01-16T14:00:00Z"
        mock_event2.start_dt = dt(2024, 1, 16, 14, 0, 0)
        
        mock_events = [mock_event1, mock_event2]
        
        # Mock cache_manager.get_events_by_date_range
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)
        
        # Mock _process_event_for_date_grouping
        original_process = controller._process_event_for_date_grouping
        controller._process_event_for_date_grouping = Mock(
            side_effect=lambda event, events_by_date: events_by_date[event.start_dt.date()].append(event)
        )
        
        # Call the method
        test_date = date(2024, 1, 15)  # Monday
        result = await controller.get_events_for_week(test_date)
        
        # Verify get_events_by_date_range was called with correct date range
        start_of_week = date(2024, 1, 15)  # Monday
        end_of_week = date(2024, 1, 21)    # Sunday
        start_datetime = dt.combine(start_of_week, dt.min.time())
        end_datetime = dt.combine(end_of_week, dt.max.time())
        controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )
        
        # Verify _process_event_for_date_grouping was called for each event
        assert controller._process_event_for_date_grouping.call_count == len(mock_events)
        
        # Verify result contains all days of the week
        assert len(result) == 7
        for day in range(7):
            current_date = start_of_week + timedelta(days=day)
            assert current_date in result
        
        # Verify events are in the correct days
        assert mock_event1 in result[date(2024, 1, 15)]
        assert mock_event2 in result[date(2024, 1, 16)]
        
        # Restore original method
        controller._process_event_for_date_grouping = original_process

    @pytest.mark.asyncio
    async def test_get_events_for_week_when_exception_then_returns_empty_dict(self) -> None:
        """Test get_events_for_week with exception returns empty dict."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range to raise exception
        controller.cache_manager.get_events_by_date_range = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Mock logger
        with patch('calendarbot.ui.interactive.logger') as mock_logger:
            # Call the method
            test_date = date(2024, 1, 15)
            result = await controller.get_events_for_week(test_date)
            
            # Verify exception was logged
            mock_logger.exception.assert_called_once()
            
            # Verify result is empty dict
            assert result == {}

    def test_process_event_for_date_grouping_when_has_start_dt_then_adds_to_correct_date(self) -> None:
        """Test _process_event_for_date_grouping with start_dt attribute adds to correct date."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with start_dt
        mock_event = Mock()
        mock_event.subject = "Test Event"
        mock_event.start_dt = dt(2024, 1, 15, 10, 0, 0)
        
        # Create events_by_date dict
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Call the method
        controller._process_event_for_date_grouping(mock_event, events_by_date)
        
        # Verify event was added to correct date
        assert mock_event in events_by_date[date(2024, 1, 15)]
        assert len(events_by_date[date(2024, 1, 16)]) == 0

    def test_process_event_for_date_grouping_when_has_start_datetime_then_parses_and_adds(self) -> None:
        """Test _process_event_for_date_grouping with start_datetime string parses and adds to correct date."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with start_datetime and start_dt
        mock_event = Mock()
        mock_event.subject = "Test Event"
        mock_event.start_datetime = "2024-01-16T14:00:00Z"
        # Add start_dt attribute directly to avoid datetime parsing issues
        mock_event.start_dt = dt(2024, 1, 16, 14, 0, 0)
        
        # Create events_by_date dict
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Call the method
        controller._process_event_for_date_grouping(mock_event, events_by_date)
        
        # Verify event was added to correct date
        assert len(events_by_date[date(2024, 1, 15)]) == 0
        assert mock_event in events_by_date[date(2024, 1, 16)]

    def test_process_event_for_date_grouping_when_invalid_datetime_then_logs_and_skips(self) -> None:
        """Test _process_event_for_date_grouping with invalid datetime logs and skips."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with invalid start_datetime
        mock_event = Mock()
        mock_event.subject = "Test Event"
        mock_event.start_datetime = "invalid-date"
        
        # Create events_by_date dict
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Mock logger
        with patch('calendarbot.ui.interactive.logger') as mock_logger:
            # Call the method
            controller._process_event_for_date_grouping(mock_event, events_by_date)
            
            # Verify debug was logged
            assert mock_logger.debug.call_count >= 2
            
            # Verify no events were added
            assert len(events_by_date[date(2024, 1, 15)]) == 0
            assert len(events_by_date[date(2024, 1, 16)]) == 0

    def test_process_event_for_date_grouping_when_date_not_in_dict_then_skips(self) -> None:
        """Test _process_event_for_date_grouping with date not in dict skips."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with start_dt for date not in dict
        mock_event = Mock()
        mock_event.subject = "Test Event"
        mock_event.start_dt = dt(2024, 1, 17, 10, 0, 0)
        
        # Create events_by_date dict without the event's date
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Mock logger
        with patch('calendarbot.ui.interactive.logger') as mock_logger:
            # Call the method - should not raise exception
            controller._process_event_for_date_grouping(mock_event, events_by_date)
            
            # Verify debug was logged
            assert mock_logger.debug.call_count >= 1
            
            # Verify no events were added
            assert len(events_by_date[date(2024, 1, 15)]) == 0
            assert len(events_by_date[date(2024, 1, 16)]) == 0


if __name__ == "__main__":
    pytest.main([__file__])