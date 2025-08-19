"""
Tests for InteractiveController display functionality.

This module focuses on display update methods, status information
retrieval, and split display logging setup/cleanup.
"""

from datetime import datetime as dt, timedelta
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent


class TestDisplayUpdateFunctionality:
    """Test display update core functionality."""

    @pytest.mark.asyncio
    async def test_update_display_when_normal_flow_then_displays_events_with_status(
        self, interactive_controller, test_date
    ) -> None:
        """Test normal display update flow."""
        # Set up navigation selected date
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        interactive_controller.navigation = mock_navigation

        # Mock successful event retrieval
        mock_events = [Mock(spec=CachedEvent), Mock(spec=CachedEvent)]
        interactive_controller.cache_manager.get_events_by_date_range.return_value = mock_events

        # Mock status info
        mock_status = {"status": "test", "connection_status": "Online"}
        interactive_controller._get_status_info = AsyncMock(return_value=mock_status)

        await interactive_controller._update_display()

        # Verify event range query
        start_datetime = dt.combine(test_date, dt.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        interactive_controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )

        # Verify display was called with events and status
        interactive_controller._get_status_info.assert_called_once()
        interactive_controller.display_manager.display_events.assert_called_once_with(
            mock_events, mock_status, clear_screen=True
        )

    @pytest.mark.asyncio
    async def test_update_display_when_event_retrieval_fails_then_handles_gracefully(
        self, interactive_controller, test_date
    ) -> None:
        """Test display update handles event retrieval failures."""
        # Set up navigation selected date
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        interactive_controller.navigation = mock_navigation

        # Mock failed event retrieval
        interactive_controller.cache_manager.get_events_by_date_range.side_effect = Exception(
            "Test error"
        )

        # Should not raise exception
        await interactive_controller._update_display()

        # Should not attempt to display
        interactive_controller.display_manager.display_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_display_when_display_fails_then_logs_warning(
        self, interactive_controller, test_date
    ) -> None:
        """Test display failure is logged appropriately."""
        # Set up navigation and successful event retrieval
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        interactive_controller.navigation = mock_navigation

        mock_events = [Mock(spec=CachedEvent)]
        interactive_controller.cache_manager.get_events_by_date_range.return_value = mock_events
        interactive_controller._get_status_info = AsyncMock(return_value={"status": "test"})

        # Mock display failure
        interactive_controller.display_manager.display_events.return_value = False

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            await interactive_controller._update_display()
            mock_logger.warning.assert_called_once_with("Display update failed")


class TestStatusInfoRetrieval:
    """Test status information retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_status_info_when_normal_flow_then_returns_complete_info(
        self, interactive_controller, mock_cache_status
    ) -> None:
        """Test normal status info retrieval returns complete information."""
        # Mock all dependencies
        interactive_controller.cache_manager.get_cache_status.return_value = mock_cache_status
        # These are already mocked in conftest.py

        result = await interactive_controller._get_status_info()

        # Verify all expected keys are present
        expected_keys = [
            "last_update",
            "is_cached",
            "connection_status",
            "interactive_mode",
            "selected_date",
            "is_today",
            "navigation_help",
        ]
        for key in expected_keys:
            assert key in result

        # Verify specific values
        assert result["last_update"] == "2024-01-15T12:00:00Z"
        assert result["is_cached"] is False
        assert result["connection_status"] == "Online"
        assert result["interactive_mode"] is True
        assert result["selected_date"] == "Monday, January 15"
        assert result["is_today"] is False
        assert result["navigation_help"] == "Help text"

    @pytest.mark.asyncio
    async def test_get_status_info_when_cache_is_stale_then_shows_cached_data_status(
        self, interactive_controller, mock_cache_status
    ) -> None:
        """Test stale cache shows 'Cached Data' status."""
        mock_cache_status.is_stale = True
        interactive_controller.cache_manager.get_cache_status.return_value = mock_cache_status
        interactive_controller.navigation.get_display_date.return_value = "Monday, January 15"
        interactive_controller.navigation.is_today.return_value = False
        interactive_controller.keyboard.get_help_text.return_value = "Help text"

        result = await interactive_controller._get_status_info()

        assert result["connection_status"] == "Cached Data"

    @pytest.mark.asyncio
    async def test_get_status_info_when_cache_status_fails_then_returns_fallback_info(
        self, interactive_controller
    ) -> None:
        """Test cache status failure returns fallback information."""
        interactive_controller.cache_manager.get_cache_status.side_effect = Exception("Cache error")
        interactive_controller.navigation.get_display_date.return_value = "Monday, January 15"

        result = await interactive_controller._get_status_info()

        # Should contain fallback keys
        assert "selected_date" in result
        assert "interactive_mode" in result
        assert "error" in result
        assert result["selected_date"] == "Monday, January 15"
        assert result["interactive_mode"] is True
        assert "Cache error" in result["error"]


class TestSplitDisplayLogging:
    """Test split display logging setup and cleanup."""

    def test_setup_split_display_logging_when_supported_then_enables_split_display(
        self, interactive_controller
    ) -> None:
        """Test split display setup when renderer supports it."""
        mock_renderer = Mock()
        mock_renderer.enable_split_display = Mock()
        interactive_controller.display_manager.renderer = mock_renderer

        interactive_controller._setup_split_display_logging()

        mock_renderer.enable_split_display.assert_called_once_with(max_log_lines=5)

    def test_setup_split_display_logging_when_not_supported_then_logs_debug(
        self, interactive_controller
    ) -> None:
        """Test split display setup when renderer doesn't support it."""
        mock_renderer = Mock()
        # Remove enable_split_display attribute to simulate unsupported renderer
        del mock_renderer.enable_split_display
        interactive_controller.display_manager.renderer = mock_renderer

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            interactive_controller._setup_split_display_logging()
            mock_logger.debug.assert_called_once_with(
                "Split display logging not available for current renderer"
            )

    def test_cleanup_split_display_logging_when_supported_then_disables_split_display(
        self, interactive_controller
    ) -> None:
        """Test split display cleanup when renderer supports it."""
        mock_renderer = Mock()
        mock_renderer.disable_split_display = Mock()
        interactive_controller.display_manager.renderer = mock_renderer

        interactive_controller._cleanup_split_display_logging()

        mock_renderer.disable_split_display.assert_called_once()

    def test_cleanup_split_display_logging_when_exception_then_logs_warning(
        self, interactive_controller
    ) -> None:
        """Test split display cleanup handles exceptions gracefully."""
        mock_renderer = Mock()
        mock_renderer.disable_split_display = Mock(side_effect=Exception("Cleanup error"))
        interactive_controller.display_manager.renderer = mock_renderer

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            interactive_controller._cleanup_split_display_logging()
            mock_logger.warning.assert_called_once_with(ANY)


if __name__ == "__main__":
    pytest.main([__file__])
