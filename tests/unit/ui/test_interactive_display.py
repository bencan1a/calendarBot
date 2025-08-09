"""
Unit tests for InteractiveController display functionality.

This module tests the display update functionality in the InteractiveController class, focusing on:
- Display update methods
- Status information retrieval
- Split display logging setup and cleanup
"""

from datetime import date, datetime as dt, timedelta
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController


class TestDisplayUpdateFunctionality:
    """Test display update functionality in InteractiveController."""

    @pytest.mark.asyncio
    async def test_update_display_when_normal_flow_then_displays_events(self) -> None:
        """Test _update_display normal flow displays events with status info."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create a mock for the navigation object with a selected_date property
        test_date = date(2024, 1, 15)
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        controller.navigation = mock_navigation

        # Mock cache_manager.get_events_by_date_range
        mock_events = [Mock(), Mock()]
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)

        # Mock _get_status_info
        mock_status = {"status": "test"}
        controller._get_status_info = AsyncMock(return_value=mock_status)

        # Mock display_manager.display_events
        controller.display_manager.display_events = AsyncMock(return_value=True)

        # Call the method
        await controller._update_display()

        # Verify get_events_by_date_range was called with correct date range
        start_datetime = dt.combine(test_date, dt.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )

        # Verify _get_status_info was called
        controller._get_status_info.assert_called_once()

        # Verify display_events was called with events and status
        controller.display_manager.display_events.assert_called_once_with(
            mock_events, mock_status, clear_screen=True
        )

    @pytest.mark.asyncio
    async def test_update_display_when_exception_then_handles_gracefully(self) -> None:
        """Test _update_display handles exceptions gracefully."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create a mock for the navigation object with a selected_date property
        test_date = date(2024, 1, 15)
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        controller.navigation = mock_navigation

        # Mock cache_manager.get_events_by_date_range to raise exception
        controller.cache_manager.get_events_by_date_range = AsyncMock(
            side_effect=Exception("Test error")
        )

        # Call the method - should not raise exception
        await controller._update_display()

        # Verify get_events_by_date_range was called
        controller.cache_manager.get_events_by_date_range.assert_called_once()

        # Verify display_events was not called
        controller.display_manager.display_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_display_when_display_fails_then_logs_warning(self) -> None:
        """Test _update_display logs warning when display fails."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create a mock for the navigation object with a selected_date property
        test_date = date(2024, 1, 15)
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        controller.navigation = mock_navigation

        # Mock cache_manager.get_events_by_date_range
        mock_events = [Mock(), Mock()]
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)

        # Mock _get_status_info
        mock_status = {"status": "test"}
        controller._get_status_info = AsyncMock(return_value=mock_status)

        # Mock display_manager.display_events to return False (failure)
        controller.display_manager.display_events = AsyncMock(return_value=False)

        # Mock logger
        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            # Call the method
            await controller._update_display()

            # Verify warning was logged
            mock_logger.warning.assert_called_once_with("Display update failed")

    @pytest.mark.asyncio
    async def test_get_status_info_when_normal_flow_then_returns_complete_info(self) -> None:
        """Test _get_status_info normal flow returns complete status information."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Mock cache_manager.get_cache_status
        mock_cache_status = Mock()
        mock_cache_status.last_update = "2024-01-15T12:00:00Z"
        mock_cache_status.is_stale = False
        controller.cache_manager.get_cache_status = AsyncMock(return_value=mock_cache_status)

        # Mock navigation methods
        controller.navigation.get_display_date = Mock(return_value="Monday, January 15")
        controller.navigation.is_today = Mock(return_value=False)
        controller.keyboard.get_help_text = Mock(return_value="Help text")

        # Call the method
        result = await controller._get_status_info()

        # Verify get_cache_status was called
        controller.cache_manager.get_cache_status.assert_called_once()

        # Verify navigation methods were called
        controller.navigation.get_display_date.assert_called_once()
        controller.navigation.is_today.assert_called_once()
        controller.keyboard.get_help_text.assert_called_once()

        # Verify result contains expected keys
        assert "last_update" in result
        assert "is_cached" in result
        assert "connection_status" in result
        assert "interactive_mode" in result
        assert "selected_date" in result
        assert "is_today" in result
        assert "navigation_help" in result

        # Verify values
        assert result["last_update"] == "2024-01-15T12:00:00Z"
        assert result["is_cached"] is False
        assert result["connection_status"] == "Online"
        assert result["interactive_mode"] is True
        assert result["selected_date"] == "Monday, January 15"
        assert result["is_today"] is False
        assert result["navigation_help"] == "Help text"

    @pytest.mark.asyncio
    async def test_get_status_info_when_stale_cache_then_shows_cached_data(self) -> None:
        """Test _get_status_info with stale cache shows 'Cached Data' status."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Mock cache_manager.get_cache_status with stale cache
        mock_cache_status = Mock()
        mock_cache_status.last_update = "2024-01-15T12:00:00Z"
        mock_cache_status.is_stale = True
        controller.cache_manager.get_cache_status = AsyncMock(return_value=mock_cache_status)

        # Mock navigation methods
        controller.navigation.get_display_date = Mock(return_value="Monday, January 15")
        controller.navigation.is_today = Mock(return_value=False)
        controller.keyboard.get_help_text = Mock(return_value="Help text")

        # Call the method
        result = await controller._get_status_info()

        # Verify connection_status shows cached data
        assert result["connection_status"] == "Cached Data"

    @pytest.mark.asyncio
    async def test_get_status_info_when_exception_then_returns_fallback_info(self) -> None:
        """Test _get_status_info with exception returns fallback information."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Mock cache_manager.get_cache_status to raise exception
        controller.cache_manager.get_cache_status = AsyncMock(side_effect=Exception("Test error"))

        # Mock navigation.get_display_date
        controller.navigation.get_display_date = Mock(return_value="Monday, January 15")

        # Call the method
        result = await controller._get_status_info()

        # Verify get_cache_status was called
        controller.cache_manager.get_cache_status.assert_called_once()

        # Verify result contains fallback keys
        assert "selected_date" in result
        assert "interactive_mode" in result
        assert "error" in result

        # Verify values
        assert result["selected_date"] == "Monday, January 15"
        assert result["interactive_mode"] is True
        assert "Test error" in result["error"]

    def test_setup_split_display_logging_when_supported_then_enables_split_display(self) -> None:
        """Test _setup_split_display_logging enables split display when supported."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create mock renderer with split display support
        mock_renderer = Mock()
        mock_renderer.enable_split_display = Mock()

        # Set up display_manager.renderer
        controller.display_manager.renderer = mock_renderer

        # Call the method
        controller._setup_split_display_logging()

        # Verify enable_split_display was called
        mock_renderer.enable_split_display.assert_called_once_with(max_log_lines=5)

    def test_setup_split_display_logging_when_not_supported_then_logs_debug(self) -> None:
        """Test _setup_split_display_logging logs debug when split display not supported."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create mock renderer without split display support
        mock_renderer = Mock()
        # Remove enable_split_display attribute
        del mock_renderer.enable_split_display

        # Set up display_manager.renderer
        controller.display_manager.renderer = mock_renderer

        # Mock logger
        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            # Call the method
            controller._setup_split_display_logging()

            # Verify debug was logged
            mock_logger.debug.assert_called_once_with(
                "Split display logging not available for current renderer"
            )

    def test_cleanup_split_display_logging_when_supported_then_disables_split_display(self) -> None:
        """Test _cleanup_split_display_logging disables split display when supported."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create mock renderer with split display support
        mock_renderer = Mock()
        mock_renderer.disable_split_display = Mock()

        # Set up display_manager.renderer
        controller.display_manager.renderer = mock_renderer

        # Call the method
        controller._cleanup_split_display_logging()

        # Verify disable_split_display was called
        mock_renderer.disable_split_display.assert_called_once()

    def test_cleanup_split_display_logging_when_exception_then_logs_warning(self) -> None:
        """Test _cleanup_split_display_logging logs warning when exception occurs."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Create mock renderer with split display support that raises exception
        mock_renderer = Mock()
        mock_renderer.disable_split_display = Mock(side_effect=Exception("Test error"))

        # Set up display_manager.renderer
        controller.display_manager.renderer = mock_renderer

        # Mock logger
        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            # Call the method
            controller._cleanup_split_display_logging()

            # Verify warning was logged
            mock_logger.warning.assert_called_once_with(ANY)


if __name__ == "__main__":
    pytest.main([__file__])
