"""Unit tests for CalendarBot main application class."""

import asyncio
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus
from calendarbot.main import CalendarBot


class TestCalendarBotInitialization:
    """Test CalendarBot initialization and component setup."""

    @pytest.fixture
    def mock_components(self):
        """Mock all major components for isolation."""
        with patch("calendarbot.main.CacheManager") as mock_cache, patch(
            "calendarbot.main.SourceManager"
        ) as mock_source, patch("calendarbot.main.DisplayManager") as mock_display, patch(
            "calendarbot.main.settings"
        ) as mock_settings:

            # Configure mock settings
            mock_settings.log_level = "INFO"
            mock_settings.log_file = None
            mock_settings.config_dir = "/tmp/test"
            mock_settings.refresh_interval = 300
            mock_settings.auto_kill_existing = False

            yield {
                "cache": mock_cache,
                "source": mock_source,
                "display": mock_display,
                "settings": mock_settings,
            }

    def test_init_creates_components(self, mock_components):
        """Test that CalendarBot.__init__ creates all required components."""
        bot = CalendarBot()

        # Verify components are created
        assert bot.cache_manager is not None
        assert bot.source_manager is not None
        assert bot.display_manager is not None
        assert bot.settings is not None

        # Verify initial state
        assert bot.running is False
        assert bot.last_successful_update is None
        assert bot.consecutive_failures == 0
        assert bot.shutdown_event is not None

    def test_init_passes_settings_to_components(self, mock_components):
        """Test that settings are passed correctly to components."""
        bot = CalendarBot()

        # Verify components were created with settings
        mock_components["cache"].assert_called_once_with(mock_components["settings"])
        mock_components["source"].assert_called_once_with(
            mock_components["settings"], bot.cache_manager
        )
        mock_components["display"].assert_called_once_with(mock_components["settings"])


class TestCalendarBotInitializeMethod:
    """Test CalendarBot.initialize() method."""

    @pytest.fixture
    def bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = MagicMock()
            return bot

    @pytest.mark.asyncio
    async def test_initialize_success(self, bot_with_mocks):
        """Test successful initialization of all components."""
        bot = bot_with_mocks

        # Mock successful initialization
        bot.cache_manager.initialize.return_value = True
        bot.source_manager.initialize.return_value = True

        result = await bot.initialize()

        assert result is True
        bot.cache_manager.initialize.assert_called_once()
        bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_cache_manager_failure(self, bot_with_mocks):
        """Test initialization failure when cache manager fails."""
        bot = bot_with_mocks

        # Mock cache manager failure
        bot.cache_manager.initialize.return_value = False
        bot.source_manager.initialize.return_value = True

        result = await bot.initialize()

        assert result is False
        bot.cache_manager.initialize.assert_called_once()
        # Source manager should not be called if cache fails
        bot.source_manager.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_source_manager_failure(self, bot_with_mocks):
        """Test initialization failure when source manager fails."""
        bot = bot_with_mocks

        # Mock source manager failure
        bot.cache_manager.initialize.return_value = True
        bot.source_manager.initialize.return_value = False

        result = await bot.initialize()

        assert result is False
        bot.cache_manager.initialize.assert_called_once()
        bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_exception_handling(self, bot_with_mocks):
        """Test that exceptions during initialization are handled gracefully."""
        bot = bot_with_mocks

        # Mock an exception
        bot.cache_manager.initialize.side_effect = Exception("Database error")

        result = await bot.initialize()

        assert result is False
        bot.cache_manager.initialize.assert_called_once()


class TestCalendarBotFetchAndCacheEvents:
    """Test CalendarBot.fetch_and_cache_events() method."""

    @pytest.fixture
    def bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = MagicMock()
            return bot

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, bot_with_mocks):
        """Test successful event fetching and caching."""
        bot = bot_with_mocks
        initial_failures = bot.consecutive_failures = 2

        # Mock successful health check and fetch
        mock_health = MagicMock()
        mock_health.is_healthy = True
        bot.source_manager.health_check.return_value = mock_health
        bot.source_manager.fetch_and_cache_events.return_value = True

        result = await bot.fetch_and_cache_events()

        assert result is True
        assert bot.last_successful_update is not None
        assert bot.consecutive_failures == 0  # Reset on success
        bot.source_manager.health_check.assert_called_once()
        bot.source_manager.fetch_and_cache_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_unhealthy_source(self, bot_with_mocks):
        """Test handling when source health check fails."""
        bot = bot_with_mocks

        # Mock unhealthy source
        mock_health = MagicMock()
        mock_health.is_healthy = False
        mock_health.status_message = "Connection timeout"
        bot.source_manager.health_check.return_value = mock_health

        result = await bot.fetch_and_cache_events()

        assert result is False
        bot.source_manager.health_check.assert_called_once()
        bot.source_manager.fetch_and_cache_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_fetch_failure(self, bot_with_mocks):
        """Test handling when fetch operation fails."""
        bot = bot_with_mocks
        initial_failures = bot.consecutive_failures

        # Mock healthy source but failed fetch
        mock_health = MagicMock()
        mock_health.is_healthy = True
        bot.source_manager.health_check.return_value = mock_health
        bot.source_manager.fetch_and_cache_events.return_value = False

        result = await bot.fetch_and_cache_events()

        assert result is False
        # consecutive_failures is only incremented on exceptions, not on failed returns
        assert bot.consecutive_failures == initial_failures

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_exception_handling(self, bot_with_mocks):
        """Test exception handling during fetch operation."""
        bot = bot_with_mocks
        initial_failures = bot.consecutive_failures

        # Mock exception during health check
        bot.source_manager.health_check.side_effect = Exception("Network error")

        result = await bot.fetch_and_cache_events()

        assert result is False
        assert bot.consecutive_failures == initial_failures + 1


class TestCalendarBotUpdateDisplay:
    """Test CalendarBot.update_display() method."""

    @pytest.fixture
    def sample_cached_events(self):
        """Create sample cached events for testing."""
        now = datetime.now()
        return [
            type(
                "CachedEvent",
                (),
                {
                    "id": "event1",
                    "subject": "Test Meeting",
                    "start_datetime": now + timedelta(hours=1),
                },
            )(),
            type(
                "CachedEvent",
                (),
                {
                    "id": "event2",
                    "subject": "Another Meeting",
                    "start_datetime": now + timedelta(hours=2),
                },
            )(),
        ]

    @pytest.fixture
    def bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()
            return bot

    @pytest.mark.asyncio
    async def test_update_display_success(self, bot_with_mocks, sample_cached_events):
        """Test successful display update."""
        bot = bot_with_mocks

        # Mock cached events and status
        bot.cache_manager.get_todays_cached_events.return_value = sample_cached_events

        mock_cache_status = MagicMock()
        mock_cache_status.last_update = datetime.now()
        mock_cache_status.is_stale = False
        bot.cache_manager.get_cache_status.return_value = mock_cache_status

        mock_source_info = MagicMock()
        mock_source_info.status = "healthy"
        mock_source_info.url = "https://example.com/calendar.ics"
        bot.source_manager.get_source_info.return_value = mock_source_info

        bot.display_manager.display_events.return_value = True

        result = await bot.update_display()

        assert result is True
        bot.cache_manager.get_todays_cached_events.assert_called_once()
        bot.display_manager.display_events.assert_called_once()

        # Verify status info passed to display
        call_args = bot.display_manager.display_events.call_args
        events_arg, status_info_arg = call_args[0]

        assert events_arg == sample_cached_events
        assert status_info_arg["total_events"] == len(sample_cached_events)
        assert status_info_arg["source_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_update_display_force_cached(self, bot_with_mocks, sample_cached_events):
        """Test display update with forced cached mode."""
        bot = bot_with_mocks

        bot.cache_manager.get_todays_cached_events.return_value = sample_cached_events

        mock_cache_status = MagicMock()
        mock_cache_status.last_update = datetime.now()
        mock_cache_status.is_stale = False
        bot.cache_manager.get_cache_status.return_value = mock_cache_status

        mock_source_info = MagicMock()
        mock_source_info.status = "healthy"
        mock_source_info.url = "https://example.com/calendar.ics"
        bot.source_manager.get_source_info.return_value = mock_source_info

        bot.display_manager.display_events.return_value = True

        result = await bot.update_display(force_cached=True)

        assert result is True

        # Verify offline status when forced cached
        call_args = bot.display_manager.display_events.call_args
        _, status_info_arg = call_args[0]
        assert status_info_arg["connection_status"] == "Offline"
        assert status_info_arg["is_cached"] is True

    @pytest.mark.asyncio
    async def test_update_display_exception_handling(self, bot_with_mocks):
        """Test exception handling during display update."""
        bot = bot_with_mocks

        # Mock exception during cache retrieval
        bot.cache_manager.get_todays_cached_events.side_effect = Exception("Cache error")

        result = await bot.update_display()

        assert result is False


class TestCalendarBotRefreshCycle:
    """Test CalendarBot.refresh_cycle() method."""

    @pytest.fixture
    def bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()
            return bot

    @pytest.mark.asyncio
    async def test_refresh_cycle_fresh_cache(self, bot_with_mocks):
        """Test refresh cycle when cache is fresh."""
        bot = bot_with_mocks

        # Mock fresh cache
        bot.cache_manager.is_cache_fresh.return_value = True
        bot.update_display = AsyncMock(return_value=True)

        await bot.refresh_cycle()

        bot.cache_manager.is_cache_fresh.assert_called_once()
        bot.update_display.assert_called_once_with(force_cached=False)

    @pytest.mark.asyncio
    async def test_refresh_cycle_stale_cache_successful_fetch(self, bot_with_mocks):
        """Test refresh cycle when cache is stale but fetch succeeds."""
        bot = bot_with_mocks

        # Mock stale cache and successful fetch
        bot.cache_manager.is_cache_fresh.return_value = False
        bot.fetch_and_cache_events = AsyncMock(return_value=True)
        bot.update_display = AsyncMock(return_value=True)

        with patch("calendarbot.main.retry_with_backoff") as mock_retry:
            mock_retry.return_value = True

            await bot.refresh_cycle()

        bot.cache_manager.is_cache_fresh.assert_called_once()
        mock_retry.assert_called_once()
        # When cache is stale (is_cache_fresh=False), force_cached=not False = True
        bot.update_display.assert_called_once_with(force_cached=True)

    @pytest.mark.asyncio
    async def test_refresh_cycle_stale_cache_failed_fetch(self, bot_with_mocks):
        """Test refresh cycle when cache is stale and fetch fails."""
        bot = bot_with_mocks

        # Mock stale cache and failed fetch
        bot.cache_manager.is_cache_fresh.return_value = False
        bot.handle_error_display = AsyncMock()

        with patch("calendarbot.main.retry_with_backoff") as mock_retry:
            mock_retry.return_value = False

            await bot.refresh_cycle()

        bot.cache_manager.is_cache_fresh.assert_called_once()
        mock_retry.assert_called_once()
        bot.handle_error_display.assert_called_once_with("Network Issue - Using Cached Data")

    @pytest.mark.asyncio
    async def test_refresh_cycle_exception_handling(self, bot_with_mocks):
        """Test exception handling during refresh cycle."""
        bot = bot_with_mocks

        # Mock exception during cache check
        bot.cache_manager.is_cache_fresh.side_effect = Exception("Database error")
        bot.handle_error_display = AsyncMock()

        await bot.refresh_cycle()

        bot.handle_error_display.assert_called_once()
        # Verify error message contains the exception info
        call_args = bot.handle_error_display.call_args[0][0]
        assert "System Error:" in call_args


class TestCalendarBotScheduler:
    """Test CalendarBot.run_scheduler() method."""

    @pytest.fixture
    def bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()
            bot.refresh_cycle = AsyncMock()
            return bot

    @pytest.mark.asyncio
    async def test_run_scheduler_initial_refresh(self, bot_with_mocks):
        """Test that scheduler performs initial refresh."""
        bot = bot_with_mocks
        bot.running = False  # Will stop after initial refresh

        await bot.run_scheduler()

        # Verify initial refresh was called
        bot.refresh_cycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_scheduler_shutdown_event(self, bot_with_mocks):
        """Test scheduler stops when shutdown event is set."""
        bot = bot_with_mocks
        bot.running = True

        # Set shutdown event immediately
        bot.shutdown_event.set()

        await bot.run_scheduler()

        # Should have done initial refresh but then stopped
        bot.refresh_cycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_scheduler_timeout_triggers_refresh(self, bot_with_mocks):
        """Test that timeout triggers additional refresh cycles."""
        bot = bot_with_mocks
        bot.running = True

        # Mock short refresh interval for testing
        bot.settings.refresh_interval = 0.1

        # Let it run for a short time then stop
        async def stop_after_delay():
            await asyncio.sleep(0.2)
            bot.running = False
            bot.shutdown_event.set()

        # Run both tasks concurrently
        await asyncio.gather(bot.run_scheduler(), stop_after_delay())

        # Should have called refresh multiple times
        assert bot.refresh_cycle.call_count >= 2


class TestCalendarBotStatusAndCleanup:
    """Test CalendarBot status and cleanup methods."""

    @pytest.fixture
    def bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = MagicMock()
            return bot

    @pytest.mark.asyncio
    async def test_status_returns_complete_info(self, bot_with_mocks):
        """Test that status() returns comprehensive status information."""
        bot = bot_with_mocks
        bot.running = True
        bot.last_successful_update = datetime.now()
        bot.consecutive_failures = 2

        # Mock component responses
        mock_source_info = MagicMock()
        mock_source_info.is_configured = True
        mock_source_info.status = "healthy"
        mock_source_info.url = "https://example.com/calendar.ics"
        bot.source_manager.get_source_info.return_value = mock_source_info

        mock_cache_summary = {"total_events": 5, "is_fresh": True}
        bot.cache_manager.get_cache_summary.return_value = mock_cache_summary

        status = await bot.status()

        # Verify status contains expected fields
        assert status["running"] is True
        assert status["last_successful_update"] is not None
        assert status["consecutive_failures"] == 2
        assert status["source_configured"] is True
        assert status["source_status"] == "healthy"
        assert status["source_url"] == "https://example.com/calendar.ics"
        assert status["cache_events"] == 5
        assert status["cache_fresh"] is True
        assert "settings" in status

    @pytest.mark.asyncio
    async def test_status_handles_exceptions(self, bot_with_mocks):
        """Test that status() handles exceptions gracefully."""
        bot = bot_with_mocks

        # Mock exception during status retrieval
        bot.source_manager.get_source_info.side_effect = Exception("Connection error")

        status = await bot.status()

        assert "error" in status
        assert "Connection error" in status["error"]

    @pytest.mark.asyncio
    async def test_cleanup_calls_cache_cleanup(self, bot_with_mocks):
        """Test that cleanup() calls cache manager cleanup."""
        bot = bot_with_mocks

        with patch("calendarbot.main.safe_async_call") as mock_safe_call:
            mock_safe_call.return_value = 5  # 5 events cleaned

            await bot.cleanup()

            mock_safe_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_sets_shutdown_event(self, bot_with_mocks):
        """Test that stop() properly sets shutdown event and running flag."""
        bot = bot_with_mocks
        bot.running = True

        await bot.stop()

        assert bot.running is False
        assert bot.shutdown_event.is_set()


@pytest.mark.asyncio
async def test_calendarbot_integration_flow(test_settings, sample_events):
    """Integration test of CalendarBot main workflow."""
    with patch("calendarbot.main.settings", test_settings):
        bot = CalendarBot()

        # Mock all components
        bot.cache_manager = AsyncMock()
        bot.source_manager = AsyncMock()
        bot.display_manager = AsyncMock()

        # Mock successful initialization
        bot.cache_manager.initialize.return_value = True
        bot.source_manager.initialize.return_value = True

        # Mock successful health check and fetch
        mock_health = MagicMock()
        mock_health.is_healthy = True
        bot.source_manager.health_check.return_value = mock_health
        bot.source_manager.fetch_and_cache_events.return_value = True

        # Mock cache and display operations
        bot.cache_manager.is_cache_fresh.return_value = False
        bot.cache_manager.get_todays_cached_events.return_value = sample_events

        mock_cache_status = MagicMock()
        mock_cache_status.last_update = datetime.now()
        mock_cache_status.is_stale = False
        bot.cache_manager.get_cache_status.return_value = mock_cache_status

        mock_source_info = MagicMock()
        mock_source_info.status = "healthy"
        mock_source_info.url = "https://example.com/calendar.ics"
        bot.source_manager.get_source_info.return_value = mock_source_info

        bot.display_manager.display_events.return_value = True

        # Test the complete flow
        assert await bot.initialize() is True
        assert await bot.fetch_and_cache_events() is True
        assert await bot.update_display() is True

        # Verify components were called in correct order
        bot.cache_manager.initialize.assert_called_once()
        bot.source_manager.initialize.assert_called_once()
        bot.source_manager.health_check.assert_called_once()
        bot.source_manager.fetch_and_cache_events.assert_called_once()
        bot.display_manager.display_events.assert_called_once()
