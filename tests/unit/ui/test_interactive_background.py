"""
Tests for InteractiveController background update functionality.

This module focuses specifically on background update loop behavior,
cache status monitoring, and update detection logic.
"""

import asyncio
from datetime import datetime as dt
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestBackgroundUpdateLoop:
    """Test background update loop behavior."""

    @pytest.mark.asyncio
    async def test_background_update_loop_when_running_then_calls_iteration_and_sleeps(
        self, interactive_controller
    ) -> None:
        """Test background loop calls iteration and sleeps between runs."""
        interactive_controller._running = True
        call_count = 0

        async def mock_iteration():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:  # Run twice then stop
                interactive_controller._running = False

        interactive_controller._background_update_iteration = AsyncMock(side_effect=mock_iteration)

        with patch(
            "calendarbot.ui.interactive.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await interactive_controller._background_update_loop()

            # Should call iteration twice and sleep once (after first iteration)
            assert interactive_controller._background_update_iteration.call_count == 2
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_with(30)

    @pytest.mark.asyncio
    async def test_background_update_loop_when_cancelled_then_exits_gracefully(
        self, interactive_controller
    ) -> None:
        """Test background loop handles CancelledError gracefully."""
        interactive_controller._running = True
        interactive_controller._background_update_iteration = AsyncMock(
            side_effect=asyncio.CancelledError()
        )

        # Should not raise exception
        await interactive_controller._background_update_loop()
        interactive_controller._background_update_iteration.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_update_loop_when_exception_then_logs_and_continues(
        self, interactive_controller
    ) -> None:
        """Test background loop logs exceptions and continues running."""
        interactive_controller._running = True
        call_count = 0

        async def failing_iteration():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            interactive_controller._running = False  # Stop after handling exception

        interactive_controller._background_update_iteration = AsyncMock(
            side_effect=failing_iteration
        )

        with patch("calendarbot.ui.interactive.logger") as mock_logger:
            await interactive_controller._background_update_loop()

            # Should log the exception
            mock_logger.exception.assert_called_once_with("Error in background update loop")


class TestBackgroundUpdateIteration:
    """Test individual background update iterations."""

    @pytest.mark.asyncio
    async def test_background_update_iteration_when_first_run_then_updates_display(
        self, interactive_controller, mock_cache_status
    ) -> None:
        """Test first run (no previous timestamp) triggers display update."""
        # Set up first run condition
        interactive_controller._last_data_update = None
        interactive_controller.cache_manager.get_cache_status = AsyncMock(
            return_value=mock_cache_status
        )
        interactive_controller._update_display = AsyncMock()
        interactive_controller.navigation.update_today = Mock()

        await interactive_controller._background_update_iteration()

        # Should update display and set timestamp
        interactive_controller._update_display.assert_called_once()
        interactive_controller.navigation.update_today.assert_called_once()
        assert interactive_controller._last_data_update is not None

    @pytest.mark.asyncio
    async def test_background_update_iteration_when_cache_updated_then_updates_display(
        self, interactive_controller, mock_cache_status
    ) -> None:
        """Test cache update triggers display refresh."""
        # Set up cache update scenario
        interactive_controller._last_data_update = dt.fromisoformat("2024-01-15T12:00:00+00:00")
        mock_cache_status.last_update = "2024-01-15T13:00:00Z"  # Newer timestamp

        interactive_controller.cache_manager.get_cache_status = AsyncMock(
            return_value=mock_cache_status
        )
        interactive_controller._update_display = AsyncMock()
        interactive_controller.navigation.update_today = Mock()

        await interactive_controller._background_update_iteration()

        # Should update display due to cache change
        interactive_controller._update_display.assert_called_once()
        interactive_controller.navigation.update_today.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_update_iteration_when_cache_unchanged_then_skips_display_update(
        self, interactive_controller, mock_cache_status
    ) -> None:
        """Test unchanged cache skips display update but still updates today reference."""
        # Set up unchanged cache scenario
        interactive_controller._last_data_update = dt.fromisoformat("2024-01-15T12:00:00+00:00")
        mock_cache_status.last_update = "2024-01-15T12:00:00Z"  # Same timestamp

        interactive_controller.cache_manager.get_cache_status = AsyncMock(
            return_value=mock_cache_status
        )
        interactive_controller._update_display = AsyncMock()
        interactive_controller.navigation.update_today = Mock()

        await interactive_controller._background_update_iteration()

        # Should skip display update but still update today
        interactive_controller._update_display.assert_not_called()
        interactive_controller.navigation.update_today.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_update_iteration_when_no_cache_timestamp_then_skips_display_update(
        self, interactive_controller, mock_cache_status
    ) -> None:
        """Test missing cache timestamp skips display update."""
        interactive_controller._last_data_update = dt.fromisoformat("2024-01-15T12:00:00+00:00")
        mock_cache_status.last_update = None  # No timestamp available

        interactive_controller.cache_manager.get_cache_status = AsyncMock(
            return_value=mock_cache_status
        )
        interactive_controller._update_display = AsyncMock()
        interactive_controller.navigation.update_today = Mock()

        await interactive_controller._background_update_iteration()

        interactive_controller._update_display.assert_not_called()
        interactive_controller.navigation.update_today.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_update_iteration_when_cache_status_fails_then_propagates_exception(
        self, interactive_controller
    ) -> None:
        """Test cache status failure propagates exception."""
        interactive_controller.cache_manager.get_cache_status = AsyncMock(
            side_effect=Exception("Cache error")
        )

        # Exception should propagate to be handled by the loop
        with pytest.raises(Exception, match="Cache error"):
            await interactive_controller._background_update_iteration()


if __name__ == "__main__":
    pytest.main([__file__])
