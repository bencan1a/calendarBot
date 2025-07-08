"""Consolidated CalendarBot tests combining comprehensive coverage with optimized critical paths."""

import asyncio
import gc
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from calendarbot.cache.manager import CacheManager
from calendarbot.display.manager import DisplayManager
from calendarbot.main import CalendarBot, check_first_run_configuration, setup_signal_handlers
from calendarbot.sources.manager import SourceManager


@pytest.mark.unit
class TestCalendarBotInitialization:
    """Test suite for CalendarBot initialization."""

    def test_calendar_bot_creation(self, test_settings):
        """Test CalendarBot instance creation."""
        with patch("calendarbot.main.settings", test_settings), patch(
            "calendarbot.main.CacheManager"
        ), patch("calendarbot.main.SourceManager"), patch("calendarbot.main.DisplayManager"):

            bot = CalendarBot()

            assert bot.settings == test_settings
            assert bot.running is False
            assert bot.shutdown_event is not None
            assert bot.cache_manager is not None
            assert bot.source_manager is not None
            assert bot.display_manager is not None
            assert bot.last_successful_update is None
            assert bot.consecutive_failures == 0

    def test_calendar_bot_component_dependencies(self, test_settings):
        """Test that CalendarBot correctly initializes component dependencies."""
        with patch("calendarbot.main.settings", test_settings), patch(
            "calendarbot.main.CacheManager"
        ) as mock_cache, patch("calendarbot.main.SourceManager") as mock_source, patch(
            "calendarbot.main.DisplayManager"
        ) as mock_display:

            bot = CalendarBot()

            # Verify cache manager was created with settings
            mock_cache.assert_called_once_with(test_settings)

            # Verify source manager was created with settings and cache manager
            mock_source.assert_called_once_with(test_settings, bot.cache_manager)

            # Verify display manager was created with settings
            mock_display.assert_called_once_with(test_settings)


@pytest.mark.unit
@pytest.mark.critical_path
class TestCalendarBotCore:
    """Core CalendarBot functionality tests with critical path coverage."""

    @pytest_asyncio.fixture
    async def calendar_bot_mock(self, test_settings):
        """Create CalendarBot with mocked dependencies."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            # Mock the component managers
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = MagicMock()

            yield bot

    @pytest.fixture
    def calendar_bot(
        self, test_settings, mock_cache_manager, mock_source_manager, mock_display_manager
    ):
        """Create CalendarBot with mocked dependencies using fixtures."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()
            bot.cache_manager = mock_cache_manager
            bot.source_manager = mock_source_manager
            bot.display_manager = mock_display_manager
            return bot

    @pytest.mark.asyncio
    async def test_initialize_success(self, calendar_bot_mock):
        """Test successful initialization of all components."""
        # Configure mocks for successful initialization
        calendar_bot_mock.cache_manager.initialize.return_value = True
        calendar_bot_mock.source_manager.initialize.return_value = True

        success = await calendar_bot_mock.initialize()

        assert success is True
        calendar_bot_mock.cache_manager.initialize.assert_called_once()
        calendar_bot_mock.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_cache_manager_failure(self, calendar_bot_mock):
        """Test initialization failure when cache manager fails."""
        calendar_bot_mock.cache_manager.initialize.return_value = False

        success = await calendar_bot_mock.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_initialize_source_manager_failure(self, calendar_bot_mock):
        """Test initialization failure when source manager fails."""
        calendar_bot_mock.cache_manager.initialize.return_value = True
        calendar_bot_mock.source_manager.initialize.return_value = False

        success = await calendar_bot_mock.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_initialize_with_exception(self, calendar_bot_mock):
        """Test initialization with exception during process."""
        calendar_bot_mock.cache_manager.initialize.side_effect = Exception("Init error")

        success = await calendar_bot_mock.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_initialization_success_optimized(self, calendar_bot):
        """Test successful CalendarBot initialization (optimized version)."""
        success = await calendar_bot.initialize()

        assert success is True
        calendar_bot.cache_manager.initialize.assert_called_once()
        calendar_bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_cache_failure_optimized(self, calendar_bot):
        """Test initialization failure when cache manager fails (optimized version)."""
        calendar_bot.cache_manager.initialize.return_value = False

        success = await calendar_bot.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_initialization_source_failure_optimized(self, calendar_bot):
        """Test initialization failure when source manager fails (optimized version)."""
        calendar_bot.source_manager.initialize.return_value = False

        success = await calendar_bot.initialize()

        assert success is False


@pytest.mark.unit
class TestEventFetchingAndCaching:
    """Test suite for event fetching and caching operations."""

    @pytest_asyncio.fixture
    async def calendar_bot_with_mocks(self, test_settings):
        """Create CalendarBot with mocked components for event operations."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            # Mock managers
            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            yield bot

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, calendar_bot_with_mocks):
        """Test successful event fetching and caching."""
        # Mock successful health check and fetch
        mock_health_check = MagicMock()
        mock_health_check.is_healthy = True
        calendar_bot_with_mocks.source_manager.health_check.return_value = mock_health_check
        calendar_bot_with_mocks.source_manager.fetch_and_cache_events.return_value = True

        success = await calendar_bot_with_mocks.fetch_and_cache_events()

        assert success is True
        assert calendar_bot_with_mocks.last_successful_update is not None
        assert calendar_bot_with_mocks.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_health_check_failure(self, calendar_bot_with_mocks):
        """Test event fetching when health check fails."""
        mock_health_check = MagicMock()
        mock_health_check.is_healthy = False
        mock_health_check.status_message = "Source unhealthy"
        calendar_bot_with_mocks.source_manager.health_check.return_value = mock_health_check

        success = await calendar_bot_with_mocks.fetch_and_cache_events()

        assert success is False
        # Should not attempt to fetch when health check fails
        calendar_bot_with_mocks.source_manager.fetch_and_cache_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_fetch_failure(self, calendar_bot_with_mocks):
        """Test event fetching when fetch operation fails."""
        mock_health_check = MagicMock()
        mock_health_check.is_healthy = True
        calendar_bot_with_mocks.source_manager.health_check.return_value = mock_health_check
        calendar_bot_with_mocks.source_manager.fetch_and_cache_events.return_value = False

        success = await calendar_bot_with_mocks.fetch_and_cache_events()

        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_with_exception(self, calendar_bot_with_mocks):
        """Test event fetching with exception during process."""
        calendar_bot_with_mocks.source_manager.health_check.side_effect = Exception(
            "Health check error"
        )

        success = await calendar_bot_with_mocks.fetch_and_cache_events()

        assert success is False
        assert calendar_bot_with_mocks.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracking(self, calendar_bot_with_mocks):
        """Test that consecutive failures are tracked correctly."""
        calendar_bot_with_mocks.source_manager.health_check.side_effect = Exception("Error")

        # First failure
        await calendar_bot_with_mocks.fetch_and_cache_events()
        assert calendar_bot_with_mocks.consecutive_failures == 1

        # Second failure
        await calendar_bot_with_mocks.fetch_and_cache_events()
        assert calendar_bot_with_mocks.consecutive_failures == 2

        # Success resets counter
        calendar_bot_with_mocks.source_manager.health_check.side_effect = None
        mock_health_check = MagicMock()
        mock_health_check.is_healthy = True
        calendar_bot_with_mocks.source_manager.health_check.return_value = mock_health_check
        calendar_bot_with_mocks.source_manager.fetch_and_cache_events.return_value = True

        await calendar_bot_with_mocks.fetch_and_cache_events()
        assert calendar_bot_with_mocks.consecutive_failures == 0


@pytest.mark.unit
class TestDisplayUpdate:
    """Test suite for display update operations."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_display(self, test_settings):
        """Create CalendarBot configured for display testing."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            yield bot

    @pytest.mark.asyncio
    async def test_update_display_success(self, calendar_bot_for_display, sample_events):
        """Test successful display update."""
        # Mock cached events and status
        calendar_bot_for_display.cache_manager.get_todays_cached_events.return_value = sample_events

        mock_cache_status = MagicMock()
        mock_cache_status.last_update = datetime.now()
        mock_cache_status.is_stale = False
        calendar_bot_for_display.cache_manager.get_cache_status.return_value = mock_cache_status

        mock_source_info = MagicMock()
        mock_source_info.status = "healthy"
        mock_source_info.url = "https://example.com/calendar.ics"
        calendar_bot_for_display.source_manager.get_source_info.return_value = mock_source_info

        calendar_bot_for_display.display_manager.display_events.return_value = True

        success = await calendar_bot_for_display.update_display()

        assert success is True
        calendar_bot_for_display.display_manager.display_events.assert_called_once()

        # Verify status info was built correctly
        call_args = calendar_bot_for_display.display_manager.display_events.call_args
        events_arg = call_args[0][0]
        status_arg = call_args[0][1]

        assert events_arg == sample_events
        assert status_arg["connection_status"] == "Online"
        assert status_arg["total_events"] == len(sample_events)

    @pytest.mark.asyncio
    async def test_update_display_with_stale_cache(self, calendar_bot_for_display):
        """Test display update with stale cache."""
        mock_cache_status = MagicMock()
        mock_cache_status.is_stale = True
        calendar_bot_for_display.cache_manager.get_cache_status.return_value = mock_cache_status
        calendar_bot_for_display.cache_manager.get_todays_cached_events.return_value = []

        mock_source_info = MagicMock()
        mock_source_info.status = "stale"
        mock_source_info.url = "https://example.com/calendar.ics"
        calendar_bot_for_display.source_manager.get_source_info.return_value = mock_source_info

        calendar_bot_for_display.display_manager.display_events.return_value = True

        success = await calendar_bot_for_display.update_display()

        assert success is True

        # Verify status reflects stale cache
        call_args = calendar_bot_for_display.display_manager.display_events.call_args
        status_arg = call_args[0][1]
        assert status_arg["connection_status"] == "Offline"
        assert status_arg["is_cached"] is True

    @pytest.mark.asyncio
    async def test_update_display_force_cached(self, calendar_bot_for_display):
        """Test display update with force cached flag."""
        calendar_bot_for_display.cache_manager.get_todays_cached_events.return_value = []
        calendar_bot_for_display.cache_manager.get_cache_status.return_value = MagicMock()
        calendar_bot_for_display.source_manager.get_source_info.return_value = MagicMock()
        calendar_bot_for_display.display_manager.display_events.return_value = True

        success = await calendar_bot_for_display.update_display(force_cached=True)

        assert success is True

        # Verify forced cached status
        call_args = calendar_bot_for_display.display_manager.display_events.call_args
        status_arg = call_args[0][1]
        assert status_arg["is_cached"] is True

    @pytest.mark.asyncio
    async def test_update_display_failure(self, calendar_bot_for_display):
        """Test display update when display manager fails."""
        calendar_bot_for_display.cache_manager.get_todays_cached_events.return_value = []
        calendar_bot_for_display.cache_manager.get_cache_status.return_value = MagicMock()
        calendar_bot_for_display.source_manager.get_source_info.return_value = MagicMock()
        calendar_bot_for_display.display_manager.display_events.return_value = False

        success = await calendar_bot_for_display.update_display()

        assert success is False

    @pytest.mark.asyncio
    async def test_update_display_with_exception(self, calendar_bot_for_display):
        """Test display update with exception."""
        calendar_bot_for_display.cache_manager.get_todays_cached_events.side_effect = Exception(
            "Cache error"
        )

        success = await calendar_bot_for_display.update_display()

        assert success is False

    @pytest.mark.asyncio
    async def test_handle_error_display(self, calendar_bot_for_display, sample_events):
        """Test error display handling."""
        calendar_bot_for_display.cache_manager.get_todays_cached_events.return_value = sample_events

        await calendar_bot_for_display.handle_error_display("Test error message")

        calendar_bot_for_display.display_manager.display_error.assert_called_once_with(
            "Test error message", sample_events
        )

    @pytest.mark.asyncio
    async def test_handle_error_display_with_cache_error(self, calendar_bot_for_display):
        """Test error display when cache access also fails."""
        calendar_bot_for_display.cache_manager.get_todays_cached_events.side_effect = Exception(
            "Cache error"
        )

        # Should not raise exception
        await calendar_bot_for_display.handle_error_display("Primary error")

        calendar_bot_for_display.display_manager.display_error.assert_called_once_with(
            "Primary error", []
        )


@pytest.mark.unit
class TestRefreshCycle:
    """Test suite for refresh cycle operations."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_refresh(self, test_settings):
        """Create CalendarBot configured for refresh testing."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            yield bot

    @pytest.mark.asyncio
    async def test_refresh_cycle_with_fresh_cache(self, calendar_bot_for_refresh):
        """Test refresh cycle when cache is fresh."""
        calendar_bot_for_refresh.cache_manager.is_cache_fresh.return_value = True

        with patch.object(
            calendar_bot_for_refresh, "update_display", return_value=True
        ) as mock_update:
            await calendar_bot_for_refresh.refresh_cycle()

            # Should skip fetching and go directly to display update
            calendar_bot_for_refresh.cache_manager.is_cache_fresh.assert_called_once()
            # When cache is fresh (True), force_cached = not True = False
            mock_update.assert_called_once_with(force_cached=False)

    @pytest.mark.asyncio
    async def test_refresh_cycle_with_stale_cache_successful_fetch(self, calendar_bot_for_refresh):
        """Test refresh cycle with stale cache and successful fetch."""
        calendar_bot_for_refresh.cache_manager.is_cache_fresh.return_value = False

        with patch.object(
            calendar_bot_for_refresh, "fetch_and_cache_events", return_value=True
        ) as mock_fetch, patch.object(
            calendar_bot_for_refresh, "update_display", return_value=True
        ) as mock_update, patch(
            "calendarbot.main.retry_with_backoff"
        ) as mock_retry:

            mock_retry.return_value = True

            await calendar_bot_for_refresh.refresh_cycle()

            mock_retry.assert_called_once()
            # When cache is stale (False), force_cached = not False = True
            mock_update.assert_called_once_with(force_cached=True)

    @pytest.mark.asyncio
    async def test_refresh_cycle_with_stale_cache_failed_fetch(self, calendar_bot_for_refresh):
        """Test refresh cycle with stale cache and failed fetch."""
        calendar_bot_for_refresh.cache_manager.is_cache_fresh.return_value = False

        with patch.object(calendar_bot_for_refresh, "handle_error_display") as mock_error, patch(
            "calendarbot.main.retry_with_backoff"
        ) as mock_retry:

            mock_retry.return_value = False

            await calendar_bot_for_refresh.refresh_cycle()

            mock_error.assert_called_once_with("Network Issue - Using Cached Data")

    @pytest.mark.asyncio
    async def test_refresh_cycle_with_exception(self, calendar_bot_for_refresh):
        """Test refresh cycle with exception during process."""
        calendar_bot_for_refresh.cache_manager.is_cache_fresh.side_effect = Exception("Cache error")

        with patch.object(calendar_bot_for_refresh, "handle_error_display") as mock_error:
            await calendar_bot_for_refresh.refresh_cycle()

            mock_error.assert_called_once()
            error_call = mock_error.call_args[0][0]
            assert "System Error:" in error_call


@pytest.mark.unit
class TestBackgroundOperations:
    """Test suite for background operations."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_background(self, test_settings):
        """Create CalendarBot for background operation testing."""
        test_settings.refresh_interval = 0.1  # Very short interval for testing

        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            yield bot

    @pytest.mark.asyncio
    async def test_run_background_fetch_initial_fetch(self, calendar_bot_for_background):
        """Test background fetch performs initial fetch."""
        calendar_bot_for_background.running = True

        with patch.object(
            calendar_bot_for_background, "fetch_and_cache_events", return_value=True
        ) as mock_fetch:
            # Mock shutdown event to stop after initial fetch
            with patch.object(
                calendar_bot_for_background.shutdown_event, "is_set", return_value=True
            ):
                await calendar_bot_for_background.run_background_fetch()

                # Should perform initial fetch
                mock_fetch.assert_called()

    @pytest.mark.asyncio
    async def test_run_background_fetch_with_interval(self, calendar_bot_for_background):
        """Test background fetch respects interval timing."""
        calendar_bot_for_background.running = True

        with patch.object(
            calendar_bot_for_background, "fetch_and_cache_events", return_value=True
        ) as mock_fetch, patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()) as mock_wait:

            # Set up to stop after one interval
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:
                    calendar_bot_for_background.running = False
                    calendar_bot_for_background.shutdown_event.set()
                raise asyncio.TimeoutError()

            mock_wait.side_effect = side_effect

            await calendar_bot_for_background.run_background_fetch()

            # Should call fetch multiple times (initial + interval)
            assert mock_fetch.call_count >= 2

    @pytest.mark.asyncio
    async def test_run_background_fetch_with_shutdown_signal(self, calendar_bot_for_background):
        """Test background fetch handles shutdown signal."""
        calendar_bot_for_background.running = True

        with patch.object(
            calendar_bot_for_background, "fetch_and_cache_events", return_value=True
        ), patch("asyncio.wait_for") as mock_wait:

            # First call timeout, second call shutdown signal
            mock_wait.side_effect = [asyncio.TimeoutError(), None]
            with patch.object(
                calendar_bot_for_background.shutdown_event, "is_set", return_value=True
            ):
                await calendar_bot_for_background.run_background_fetch()

                # Should exit cleanly when shutdown is signaled

    @pytest.mark.asyncio
    async def test_run_scheduler_similar_to_background_fetch(self, calendar_bot_for_background):
        """Test run_scheduler behaves similarly to run_background_fetch."""
        calendar_bot_for_background.running = True

        with patch.object(calendar_bot_for_background, "refresh_cycle") as mock_refresh:
            with patch.object(
                calendar_bot_for_background.shutdown_event, "is_set", return_value=True
            ):
                await calendar_bot_for_background.run_scheduler()

                # Should perform initial refresh
                mock_refresh.assert_called()


@pytest.mark.unit
class TestApplicationLifecycle:
    """Test suite for application lifecycle operations."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_lifecycle(self, test_settings):
        """Create CalendarBot for lifecycle testing."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            yield bot

    @pytest.mark.asyncio
    async def test_start_successful(self, calendar_bot_for_lifecycle):
        """Test successful application start."""
        with patch.object(
            calendar_bot_for_lifecycle, "initialize", return_value=True
        ), patch.object(
            calendar_bot_for_lifecycle, "run_scheduler"
        ) as mock_scheduler, patch.object(
            calendar_bot_for_lifecycle, "cleanup"
        ) as mock_cleanup:

            result = await calendar_bot_for_lifecycle.start()

            assert result is True
            assert calendar_bot_for_lifecycle.running is True
            mock_scheduler.assert_called_once()
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_initialization_failure(self, calendar_bot_for_lifecycle):
        """Test application start with initialization failure."""
        with patch.object(
            calendar_bot_for_lifecycle, "initialize", return_value=False
        ), patch.object(calendar_bot_for_lifecycle, "cleanup") as mock_cleanup:

            result = await calendar_bot_for_lifecycle.start()

            assert result is False
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_with_auto_kill_existing(self, calendar_bot_for_lifecycle):
        """Test application start with auto kill existing processes."""
        calendar_bot_for_lifecycle.settings.auto_kill_existing = True

        with patch.object(
            calendar_bot_for_lifecycle, "initialize", return_value=True
        ), patch.object(calendar_bot_for_lifecycle, "run_scheduler"), patch.object(
            calendar_bot_for_lifecycle, "cleanup"
        ), patch(
            "calendarbot.main.kill_calendarbot_processes"
        ) as mock_kill:

            mock_kill.return_value = (2, [])  # Killed 2 processes, no errors

            await calendar_bot_for_lifecycle.start()

            mock_kill.assert_called_once_with(exclude_self=True)

    @pytest.mark.asyncio
    async def test_start_with_keyboard_interrupt(self, calendar_bot_for_lifecycle):
        """Test application start with keyboard interrupt."""
        with patch.object(
            calendar_bot_for_lifecycle, "initialize", return_value=True
        ), patch.object(
            calendar_bot_for_lifecycle, "run_scheduler", side_effect=KeyboardInterrupt
        ), patch.object(
            calendar_bot_for_lifecycle, "cleanup"
        ) as mock_cleanup:

            result = await calendar_bot_for_lifecycle.start()

            assert result is True  # Keyboard interrupt is considered successful shutdown
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_with_exception(self, calendar_bot_for_lifecycle):
        """Test application start with exception."""
        with patch.object(
            calendar_bot_for_lifecycle, "initialize", side_effect=Exception("Start error")
        ), patch.object(calendar_bot_for_lifecycle, "cleanup") as mock_cleanup:

            result = await calendar_bot_for_lifecycle.start()

            assert result is False
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, calendar_bot_for_lifecycle):
        """Test application stop."""
        calendar_bot_for_lifecycle.running = True

        await calendar_bot_for_lifecycle.stop()

        assert calendar_bot_for_lifecycle.running is False
        assert calendar_bot_for_lifecycle.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_cleanup(self, calendar_bot_for_lifecycle):
        """Test application cleanup."""
        with patch("calendarbot.main.safe_async_call") as mock_safe_call:
            await calendar_bot_for_lifecycle.cleanup()

            # Should call safe cleanup for cache manager
            mock_safe_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_exception(self, calendar_bot_for_lifecycle):
        """Test cleanup handles exceptions gracefully."""
        with patch("calendarbot.main.safe_async_call", side_effect=Exception("Cleanup error")):
            # Should not raise exception
            await calendar_bot_for_lifecycle.cleanup()


@pytest.mark.unit
class TestStatusReporting:
    """Test suite for status reporting."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_status(self, test_settings):
        """Create CalendarBot for status testing."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            bot.last_successful_update = datetime.now()
            bot.consecutive_failures = 2
            bot.running = True

            yield bot

    @pytest.mark.asyncio
    async def test_status_success(self, calendar_bot_for_status):
        """Test successful status retrieval."""
        # Mock return values
        mock_source_info = MagicMock()
        mock_source_info.is_configured = True
        mock_source_info.status = "healthy"
        mock_source_info.url = "https://example.com/calendar.ics"
        calendar_bot_for_status.source_manager.get_source_info.return_value = mock_source_info

        mock_cache_summary = {"total_events": 10, "is_fresh": True}
        calendar_bot_for_status.cache_manager.get_cache_summary.return_value = mock_cache_summary

        status = await calendar_bot_for_status.status()

        assert status["running"] is True
        assert status["last_successful_update"] is not None
        assert status["consecutive_failures"] == 2
        assert status["source_configured"] is True
        assert status["source_status"] == "healthy"
        assert status["source_url"] == "https://example.com/calendar.ics"
        assert status["cache_events"] == 10
        assert status["cache_fresh"] is True

    @pytest.mark.asyncio
    async def test_status_with_exception(self, calendar_bot_for_status):
        """Test status retrieval with exception."""
        calendar_bot_for_status.source_manager.get_source_info.side_effect = Exception(
            "Status error"
        )

        status = await calendar_bot_for_status.status()

        # Should return error dict when exception occurs
        assert "error" in status
        assert status["error"] == "Status error"


@pytest.mark.unit
class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        mock_bot = MagicMock()

        with patch("signal.signal") as mock_signal:
            setup_signal_handlers(mock_bot)

            # Should set up handlers for SIGINT and SIGTERM
            assert mock_signal.call_count == 2

    def test_check_first_run_configuration_exists(self, tmp_path):
        """Test first run check when configuration exists."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("ics_url: https://example.com/calendar.ics\n")

        with patch("calendarbot.main.settings") as mock_settings:
            mock_settings.ics_config_file = str(config_file)

            result = check_first_run_configuration()

            assert result is True

    def test_check_first_run_configuration_with_url(self):
        """Test first run check when ICS URL is configured."""
        with patch("calendarbot.main.settings") as mock_settings:
            mock_settings.ics_url = "https://example.com/calendar.ics"

            with patch("pathlib.Path.exists", return_value=False):
                result = check_first_run_configuration()
                assert result is True

    def test_check_first_run_configuration_missing(self, tmp_path):
        """Test first run check when configuration is missing."""
        with patch("calendarbot.main.settings") as mock_settings, patch(
            "pathlib.Path.exists", return_value=False
        ):
            mock_settings.ics_url = None

            result = check_first_run_configuration()

            assert result is False

    def test_check_first_run_configuration_empty(self, tmp_path):
        """Test first run check when configuration is empty."""
        with patch("calendarbot.main.settings") as mock_settings, patch(
            "pathlib.Path.exists", return_value=False
        ):
            mock_settings.ics_url = ""  # Empty string should be falsy

            result = check_first_run_configuration()

            assert result is False


@pytest.mark.unit
class TestErrorConditions:
    """Test suite for error conditions and edge cases."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_errors(self, test_settings):
        """Create CalendarBot for error testing."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()

            yield bot

    @pytest.mark.asyncio
    async def test_multiple_consecutive_failures(self, calendar_bot_for_errors):
        """Test behavior with multiple consecutive failures."""
        calendar_bot_for_errors.source_manager.health_check.side_effect = Exception(
            "Persistent error"
        )

        # Simulate multiple failures
        for i in range(5):
            await calendar_bot_for_errors.fetch_and_cache_events()
            assert calendar_bot_for_errors.consecutive_failures == i + 1

    @pytest.mark.asyncio
    async def test_partial_initialization_failure(self, calendar_bot_for_errors):
        """Test partial initialization failure scenarios."""
        # Cache manager succeeds, source manager fails
        calendar_bot_for_errors.cache_manager.initialize.return_value = True
        calendar_bot_for_errors.source_manager.initialize.return_value = False

        success = await calendar_bot_for_errors.initialize()

        assert success is False
        # Verify cache manager was still called
        calendar_bot_for_errors.cache_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_display_update_with_missing_components(self, calendar_bot_for_errors):
        """Test display update when components are missing/None."""
        calendar_bot_for_errors.cache_manager = None

        success = await calendar_bot_for_errors.update_display()

        assert success is False

    @pytest.mark.asyncio
    async def test_scheduler_with_rapid_shutdown(self, calendar_bot_for_errors):
        """Test scheduler behavior with rapid shutdown signal."""
        calendar_bot_for_errors.running = True

        with patch.object(calendar_bot_for_errors, "refresh_cycle") as mock_refresh:
            # Immediate shutdown signal
            with patch.object(calendar_bot_for_errors.shutdown_event, "is_set", return_value=True):
                await calendar_bot_for_errors.run_scheduler()

                # Should handle immediate shutdown gracefully
                mock_refresh.assert_called()


@pytest.mark.unit
@pytest.mark.performance
class TestPerformanceAndConcurrency:
    """Test suite for performance and concurrency aspects."""

    @pytest_asyncio.fixture
    async def calendar_bot_for_performance(self, test_settings, performance_tracker):
        """Create CalendarBot for performance testing."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            bot.cache_manager = AsyncMock()
            bot.source_manager = AsyncMock()
            bot.display_manager = AsyncMock()
            bot.performance_tracker = performance_tracker

            yield bot

    @pytest.mark.asyncio
    async def test_initialization_performance(
        self, calendar_bot_for_performance, performance_tracker
    ):
        """Test initialization performance."""
        calendar_bot_for_performance.cache_manager.initialize.return_value = True
        calendar_bot_for_performance.source_manager.initialize.return_value = True

        performance_tracker.start_timer("initialization")
        success = await calendar_bot_for_performance.initialize()
        performance_tracker.end_timer("initialization")

        assert success is True
        performance_tracker.assert_performance("initialization", 2.0)

    @pytest.mark.asyncio
    async def test_concurrent_fetch_operations(
        self, calendar_bot_for_performance, performance_tracker
    ):
        """Test concurrent fetch operations don't interfere."""
        calendar_bot_for_performance.source_manager.health_check.return_value = MagicMock(
            is_healthy=True
        )
        calendar_bot_for_performance.source_manager.fetch_and_cache_events.return_value = True

        async def fetch_operation():
            return await calendar_bot_for_performance.fetch_and_cache_events()

        performance_tracker.start_timer("concurrent_fetch")

        # Run multiple fetch operations concurrently
        results = await asyncio.gather(fetch_operation(), fetch_operation(), fetch_operation())

        performance_tracker.end_timer("concurrent_fetch")

        # All should succeed
        assert all(results)
        performance_tracker.assert_performance("concurrent_fetch", 5.0)

    @pytest.mark.asyncio
    async def test_concurrent_operations_optimized(self, test_settings, performance_tracker):
        """Test that concurrent operations don't interfere (optimized version)."""
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
    async def test_initialization_performance_optimized(self, test_settings, performance_tracker):
        """Test initialization performance (optimized version)."""
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

    @pytest.mark.asyncio
    async def test_memory_usage_during_long_operation(
        self, calendar_bot_for_performance, performance_tracker
    ):
        """Test memory usage during long-running operations."""
        import gc

        # Mock long-running operations
        async def slow_fetch():
            await asyncio.sleep(0.01)  # Simulate work
            return True

        calendar_bot_for_performance.source_manager.fetch_and_cache_events.side_effect = slow_fetch
        calendar_bot_for_performance.source_manager.health_check.return_value = MagicMock(
            is_healthy=True
        )

        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform multiple operations
        for _ in range(10):
            await calendar_bot_for_performance.fetch_and_cache_events()

        # Force garbage collection after test
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory usage should not grow significantly
        growth_ratio = final_objects / initial_objects
        assert growth_ratio < 1.5, f"Memory usage grew by {growth_ratio:.2f}x"


@pytest.mark.unit
class TestIntegrationBoundaries:
    """Test suite for integration boundaries and mock validation."""

    @pytest_asyncio.fixture
    async def calendar_bot_real_components(self, test_settings):
        """Create CalendarBot with real component interfaces."""
        with patch("calendarbot.main.settings", test_settings):
            bot = CalendarBot()

            # Use real component classes but mock their methods
            with patch("calendarbot.main.CacheManager") as MockCache, patch(
                "calendarbot.main.SourceManager"
            ) as MockSource, patch("calendarbot.main.DisplayManager") as MockDisplay:

                # Configure mock classes to return mock instances
                bot.cache_manager = MockCache.return_value
                bot.source_manager = MockSource.return_value
                bot.display_manager = MockDisplay.return_value

                yield bot

    @pytest.mark.asyncio
    async def test_component_interface_compatibility(self, calendar_bot_real_components):
        """Test that component interfaces are used correctly."""
        # Verify CalendarBot calls expected methods with correct signatures
        bot = calendar_bot_real_components

        # Mock successful async responses (these methods are async)
        bot.cache_manager.initialize = AsyncMock(return_value=True)
        bot.source_manager.initialize = AsyncMock(return_value=True)

        success = await bot.initialize()

        assert success is True

        # Verify correct method calls
        bot.cache_manager.initialize.assert_called_once()
        bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_flow_between_components(self, calendar_bot_real_components):
        """Test data flow between components matches expected patterns."""
        bot = calendar_bot_real_components

        # Mock async data flow methods
        mock_events = [{"summary": "Test Event"}]
        bot.cache_manager.get_todays_cached_events = AsyncMock(return_value=mock_events)
        bot.cache_manager.get_cache_status = AsyncMock(return_value=MagicMock())
        bot.source_manager.get_source_info = AsyncMock(return_value=MagicMock())
        bot.display_manager.display_events = AsyncMock(return_value=True)

        success = await bot.update_display()

        assert success is True

        # Verify data was passed correctly between components
        call_args = bot.display_manager.display_events.call_args
        events_passed = call_args[0][0]
        assert events_passed == mock_events
