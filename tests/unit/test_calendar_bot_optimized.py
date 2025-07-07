"""Optimized CalendarBot tests focusing on core functionality and 80% coverage."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.main import CalendarBot


@pytest.mark.unit
@pytest.mark.critical_path
class TestCalendarBotCore:
    """Core CalendarBot functionality tests."""

    @pytest.fixture
    def calendar_bot(
        self, test_settings, mock_cache_manager, mock_source_manager, mock_display_manager
    ):
        """Create CalendarBot with mocked dependencies."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = mock_cache_manager
            bot.source_manager = mock_source_manager
            bot.display_manager = mock_display_manager
            return bot

    @pytest.mark.asyncio
    async def test_initialization_success(self, calendar_bot):
        """Test successful CalendarBot initialization."""
        success = await calendar_bot.initialize()

        assert success is True
        calendar_bot.cache_manager.initialize.assert_called_once()
        calendar_bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_cache_failure(self, calendar_bot):
        """Test initialization failure when cache manager fails."""
        calendar_bot.cache_manager.initialize.return_value = False

        success = await calendar_bot.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_initialization_source_failure(self, calendar_bot):
        """Test initialization failure when source manager fails."""
        calendar_bot.source_manager.initialize.return_value = False

        success = await calendar_bot.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, calendar_bot):
        """Test successful event fetching and caching."""
        # Mock successful health check
        mock_health = MagicMock()
        mock_health.is_healthy = True
        calendar_bot.source_manager.health_check.return_value = mock_health

        success = await calendar_bot.fetch_and_cache_events()

        assert success is True
        assert calendar_bot.last_successful_update is not None
        assert calendar_bot.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_health_failure(self, calendar_bot):
        """Test event fetching when health check fails."""
        mock_health = MagicMock()
        mock_health.is_healthy = False
        mock_health.status_message = "Source unhealthy"
        calendar_bot.source_manager.health_check.return_value = mock_health

        success = await calendar_bot.fetch_and_cache_events()

        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_with_exception(self, calendar_bot):
        """Test event fetching with exception."""
        calendar_bot.source_manager.health_check.side_effect = Exception("Test error")

        success = await calendar_bot.fetch_and_cache_events()

        assert success is False
        assert calendar_bot.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_update_display_success(self, calendar_bot, sample_events):
        """Test successful display update."""
        calendar_bot.cache_manager.get_todays_cached_events.return_value = sample_events

        success = await calendar_bot.update_display()

        assert success is True
        calendar_bot.display_manager.display_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_display_with_stale_cache(self, calendar_bot):
        """Test display update with stale cache."""
        mock_status = MagicMock()
        mock_status.is_stale = True
        calendar_bot.cache_manager.get_cache_status.return_value = mock_status

        success = await calendar_bot.update_display()

        assert success is True
        # Verify stale status reflected in call
        call_args = calendar_bot.display_manager.display_events.call_args
        status_arg = call_args[0][1]
        assert status_arg["connection_status"] == "Offline"

    @pytest.mark.asyncio
    async def test_refresh_cycle_fresh_cache(self, calendar_bot):
        """Test refresh cycle with fresh cache."""
        calendar_bot.cache_manager.is_cache_fresh.return_value = True

        with patch.object(calendar_bot, "update_display", return_value=True) as mock_update:
            await calendar_bot.refresh_cycle()
            mock_update.assert_called_once_with(force_cached=False)

    @pytest.mark.asyncio
    async def test_refresh_cycle_stale_cache_successful_fetch(self, calendar_bot):
        """Test refresh cycle with stale cache and successful fetch."""
        calendar_bot.cache_manager.is_cache_fresh.return_value = False

        with patch.object(calendar_bot, "fetch_and_cache_events", return_value=True), patch.object(
            calendar_bot, "update_display", return_value=True
        ) as mock_update, patch("calendarbot.main.retry_with_backoff", return_value=True):

            await calendar_bot.refresh_cycle()
            mock_update.assert_called_once_with(force_cached=True)

    @pytest.mark.asyncio
    async def test_refresh_cycle_failed_fetch(self, calendar_bot):
        """Test refresh cycle with failed fetch."""
        calendar_bot.cache_manager.is_cache_fresh.return_value = False

        with patch.object(calendar_bot, "handle_error_display") as mock_error, patch(
            "calendarbot.main.retry_with_backoff", return_value=False
        ):

            await calendar_bot.refresh_cycle()
            mock_error.assert_called_once_with("Network Issue - Using Cached Data")

    @pytest.mark.asyncio
    async def test_handle_error_display(self, calendar_bot, sample_events):
        """Test error display handling."""
        calendar_bot.cache_manager.get_todays_cached_events.return_value = sample_events

        await calendar_bot.handle_error_display("Test error")

        calendar_bot.display_manager.display_error.assert_called_once_with(
            "Test error", sample_events
        )

    @pytest.mark.asyncio
    async def test_start_successful(self, calendar_bot):
        """Test successful application start."""
        with patch.object(calendar_bot, "initialize", return_value=True), patch.object(
            calendar_bot, "run_scheduler"
        ) as mock_scheduler, patch.object(calendar_bot, "cleanup"):

            result = await calendar_bot.start()

            assert result is True
            assert calendar_bot.running is True
            mock_scheduler.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_initialization_failure(self, calendar_bot):
        """Test start with initialization failure."""
        with patch.object(calendar_bot, "initialize", return_value=False), patch.object(
            calendar_bot, "cleanup"
        ):

            result = await calendar_bot.start()

            assert result is False

    @pytest.mark.asyncio
    async def test_stop(self, calendar_bot):
        """Test application stop."""
        calendar_bot.running = True

        await calendar_bot.stop()

        assert calendar_bot.running is False
        assert calendar_bot.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_cleanup(self, calendar_bot):
        """Test application cleanup."""
        with patch("calendarbot.main.safe_async_call") as mock_safe_call:
            await calendar_bot.cleanup()
            mock_safe_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_success(self, calendar_bot):
        """Test successful status retrieval."""
        calendar_bot.running = True
        calendar_bot.last_successful_update = datetime.now()
        calendar_bot.consecutive_failures = 1

        status = await calendar_bot.status()

        assert status["running"] is True
        assert status["last_successful_update"] is not None
        assert status["consecutive_failures"] == 1

    @pytest.mark.asyncio
    async def test_status_with_exception(self, calendar_bot):
        """Test status retrieval with exception."""
        calendar_bot.source_manager.get_source_info.side_effect = Exception("Status error")

        status = await calendar_bot.status()

        assert "error" in status
        assert status["error"] == "Status error"


@pytest.mark.unit
class TestCalendarBotUtilities:
    """Test CalendarBot utility functions."""

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        from calendarbot.main import setup_signal_handlers

        mock_bot = MagicMock()

        with patch("signal.signal") as mock_signal:
            setup_signal_handlers(mock_bot)
            assert mock_signal.call_count == 2

    def test_check_first_run_configuration_with_url(self):
        """Test first run check when ICS URL is configured."""
        from calendarbot.main import check_first_run_configuration

        with patch("calendarbot.main.settings") as mock_settings:
            mock_settings.ics_url = "https://example.com/calendar.ics"

            with patch("pathlib.Path.exists", return_value=False):
                result = check_first_run_configuration()
                assert result is True

    def test_check_first_run_configuration_missing(self):
        """Test first run check when configuration is missing."""
        from calendarbot.main import check_first_run_configuration

        with patch("calendarbot.main.settings") as mock_settings:
            mock_settings.ics_url = None

            with patch("pathlib.Path.exists", return_value=False):
                result = check_first_run_configuration()
                assert result is False


@pytest.mark.unit
class TestCalendarBotPerformance:
    """Performance-focused tests."""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_settings, performance_tracker):
        """Test that concurrent operations don't interfere."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = MagicMock()

            # Configure for success
            mock_health = MagicMock()
            mock_health.is_healthy = True
            bot.source_manager.health_check.return_value = mock_health
            bot.source_manager.fetch_and_cache_events.return_value = True

            async def fetch_operation():
                return await bot.fetch_and_cache_events()

            performance_tracker.start_timer("concurrent_operations")

            # Run multiple operations concurrently
            results = await asyncio.gather(fetch_operation(), fetch_operation(), fetch_operation())

            performance_tracker.end_timer("concurrent_operations")

            # All should succeed
            assert all(results)
            performance_tracker.assert_performance("concurrent_operations", 2.0)

    @pytest.mark.asyncio
    async def test_initialization_performance(self, test_settings, performance_tracker):
        """Test initialization performance."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = MagicMock()

            bot.cache_manager.initialize.return_value = True
            bot.source_manager.initialize.return_value = True

            performance_tracker.start_timer("initialization")
            success = await bot.initialize()
            performance_tracker.end_timer("initialization")

            assert success is True
            performance_tracker.assert_performance("initialization", 1.0)
