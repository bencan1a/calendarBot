"""Tests for main application entry point.

Comprehensive tests for CalendarBot class, signal handlers,
configuration checks, and main entry point functionality.
"""

import asyncio
import signal
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Remove unused import of 'main' async function to test if it causes RuntimeWarning
from calendarbot.main import CalendarBot, check_first_run_configuration, setup_signal_handlers


class TestCalendarBot:
    """Test suite for CalendarBot class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings object."""
        settings = Mock()
        settings.refresh_interval = 300
        settings.cache_ttl = 7200
        settings.display_type = "console"
        settings.auto_kill_existing = True
        settings.ics_url = "https://example.com/calendar.ics"
        settings.log_level = "INFO"
        settings.log_file = None
        settings.config_dir = "/tmp/config"
        return settings

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager."""
        cache_manager = AsyncMock()
        cache_manager.initialize.return_value = True
        cache_manager.get_todays_cached_events.return_value = []
        cache_manager.get_cache_status.return_value = Mock(
            last_update=datetime.now(), is_stale=False
        )
        cache_manager.get_cache_summary.return_value = {"total_events": 5, "is_fresh": True}
        cache_manager.is_cache_fresh.return_value = True
        cache_manager.cleanup_old_events.return_value = 3
        return cache_manager

    @pytest.fixture
    def mock_source_manager(self):
        """Mock source manager."""
        source_manager = AsyncMock()
        source_manager.initialize.return_value = True
        source_manager.health_check.return_value = Mock(
            is_healthy=True, status_message="All sources healthy"
        )
        source_manager.fetch_and_cache_events.return_value = True
        source_manager.get_source_info.return_value = Mock(
            is_configured=True, status="Connected", url="https://example.com/calendar.ics"
        )
        return source_manager

    @pytest.fixture
    def mock_display_manager(self):
        """Mock display manager."""
        display_manager = AsyncMock()
        display_manager.display_events.return_value = True
        display_manager.display_error.return_value = True
        return display_manager

    @pytest.fixture
    def calendar_bot(
        self, mock_settings, mock_cache_manager, mock_source_manager, mock_display_manager
    ):
        """Create CalendarBot instance with mocked dependencies."""
        with patch("calendarbot.main.settings", mock_settings), patch(
            "calendarbot.main.CacheManager", return_value=mock_cache_manager
        ), patch("calendarbot.main.SourceManager", return_value=mock_source_manager), patch(
            "calendarbot.main.DisplayManager", return_value=mock_display_manager
        ), patch(
            "calendarbot.main.setup_logging"
        ):
            bot = CalendarBot()
            bot.cache_manager = mock_cache_manager
            bot.source_manager = mock_source_manager
            bot.display_manager = mock_display_manager
            return bot

    @pytest.mark.asyncio
    async def test_calendar_bot_initialization(self, calendar_bot):
        """Test CalendarBot initialization sets up components correctly."""
        assert calendar_bot.running is False
        assert calendar_bot.shutdown_event is not None
        assert calendar_bot.last_successful_update is None
        assert calendar_bot.consecutive_failures == 0
        assert calendar_bot.cache_manager is not None
        assert calendar_bot.source_manager is not None
        assert calendar_bot.display_manager is not None

    @pytest.mark.asyncio
    async def test_initialize_success(self, calendar_bot):
        """Test successful initialization of all components."""
        result = await calendar_bot.initialize()

        assert result is True
        calendar_bot.cache_manager.initialize.assert_called_once()
        calendar_bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_cache_failure(self, calendar_bot):
        """Test initialization failure when cache manager fails."""
        calendar_bot.cache_manager.initialize.return_value = False

        result = await calendar_bot.initialize()

        assert result is False
        calendar_bot.cache_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_source_failure(self, calendar_bot):
        """Test initialization failure when source manager fails."""
        calendar_bot.source_manager.initialize.return_value = False

        result = await calendar_bot.initialize()

        assert result is False
        calendar_bot.source_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_exception(self, calendar_bot):
        """Test initialization handles exceptions gracefully."""
        calendar_bot.cache_manager.initialize.side_effect = Exception("Init error")

        result = await calendar_bot.initialize()

        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, calendar_bot):
        """Test successful event fetching and caching."""
        result = await calendar_bot.fetch_and_cache_events()

        assert result is True
        assert calendar_bot.consecutive_failures == 0
        assert calendar_bot.last_successful_update is not None
        calendar_bot.source_manager.health_check.assert_called_once()
        calendar_bot.source_manager.fetch_and_cache_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_health_check_failure(self, calendar_bot):
        """Test fetch failure when health check fails."""
        calendar_bot.source_manager.health_check.return_value = Mock(
            is_healthy=False, status_message="Source unavailable"
        )

        result = await calendar_bot.fetch_and_cache_events()

        assert result is False
        calendar_bot.source_manager.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_fetch_failure(self, calendar_bot):
        """Test fetch failure when source manager fails."""
        calendar_bot.source_manager.fetch_and_cache_events.return_value = False

        result = await calendar_bot.fetch_and_cache_events()

        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_exception(self, calendar_bot):
        """Test fetch handles exceptions and increments failure count."""
        calendar_bot.source_manager.health_check.side_effect = Exception("Network error")

        result = await calendar_bot.fetch_and_cache_events()

        assert result is False
        assert calendar_bot.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_update_display_success(self, calendar_bot):
        """Test successful display update."""
        cached_events = [Mock(), Mock()]
        calendar_bot.cache_manager.get_todays_cached_events.return_value = cached_events

        result = await calendar_bot.update_display()

        assert result is True
        calendar_bot.cache_manager.get_todays_cached_events.assert_called_once()
        calendar_bot.cache_manager.get_cache_status.assert_called_once()
        calendar_bot.source_manager.get_source_info.assert_called_once()
        calendar_bot.display_manager.display_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_display_force_cached(self, calendar_bot):
        """Test display update with force_cached flag."""
        result = await calendar_bot.update_display(force_cached=True)

        assert result is True
        # Check that status_info includes force_cached logic
        call_args = calendar_bot.display_manager.display_events.call_args
        status_info = call_args[0][1]
        assert "connection_status" in status_info

    @pytest.mark.asyncio
    async def test_update_display_failure(self, calendar_bot):
        """Test display update failure."""
        calendar_bot.display_manager.display_events.return_value = False

        result = await calendar_bot.update_display()

        assert result is False

    @pytest.mark.asyncio
    async def test_update_display_exception(self, calendar_bot):
        """Test display update handles exceptions."""
        calendar_bot.cache_manager.get_todays_cached_events.side_effect = Exception("Cache error")

        result = await calendar_bot.update_display()

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_error_display_success(self, calendar_bot):
        """Test error display with cached events."""
        cached_events = [Mock()]
        calendar_bot.cache_manager.get_todays_cached_events.return_value = cached_events

        await calendar_bot.handle_error_display("Test error")

        calendar_bot.display_manager.display_error.assert_called_once_with(
            "Test error", cached_events
        )

    @pytest.mark.asyncio
    async def test_handle_error_display_cache_failure(self, calendar_bot):
        """Test error display when cache access fails."""
        calendar_bot.cache_manager.get_todays_cached_events.side_effect = Exception("Cache error")

        await calendar_bot.handle_error_display("Test error")

        # Should still call display_error with empty list as fallback
        calendar_bot.display_manager.display_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_display_exception(self, calendar_bot):
        """Test error display handles exceptions gracefully."""
        calendar_bot.display_manager.display_error.side_effect = Exception("Display error")

        # Should not raise exception
        await calendar_bot.handle_error_display("Test error")

    @pytest.mark.asyncio
    async def test_refresh_cycle_fresh_cache(self, calendar_bot):
        """Test refresh cycle when cache is fresh."""
        calendar_bot.cache_manager.is_cache_fresh.return_value = True

        await calendar_bot.refresh_cycle()

        calendar_bot.cache_manager.is_cache_fresh.assert_called_once()
        # Should update display with fresh data
        calendar_bot.display_manager.display_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_cycle_stale_cache_fetch_success(self, calendar_bot):
        """Test refresh cycle with stale cache and successful fetch."""
        calendar_bot.cache_manager.is_cache_fresh.return_value = False

        with patch("calendarbot.main.retry_with_backoff") as mock_retry:
            mock_retry.return_value = True

            await calendar_bot.refresh_cycle()

            mock_retry.assert_called_once()
            calendar_bot.display_manager.display_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_cycle_stale_cache_fetch_failure(self, calendar_bot):
        """Test refresh cycle with stale cache and fetch failure."""
        calendar_bot.cache_manager.is_cache_fresh.return_value = False

        with patch("calendarbot.main.retry_with_backoff") as mock_retry:
            mock_retry.return_value = False

            await calendar_bot.refresh_cycle()

            mock_retry.assert_called_once()
            calendar_bot.display_manager.display_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_cycle_exception(self, calendar_bot):
        """Test refresh cycle handles exceptions."""
        calendar_bot.cache_manager.is_cache_fresh.side_effect = Exception("Cache error")

        await calendar_bot.refresh_cycle()

        calendar_bot.display_manager.display_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_background_fetch_success(self, calendar_bot):
        """Test background fetch runs initial fetch."""
        calendar_bot.running = False  # Ensure loop exits immediately

        await calendar_bot.run_background_fetch()

        calendar_bot.source_manager.fetch_and_cache_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_background_fetch_with_interval(self, calendar_bot):
        """Test background fetch with timeout intervals."""
        calendar_bot.running = True
        calendar_bot.settings.refresh_interval = 0.1  # Short interval for testing

        # Mock the shutdown event to trigger after short delay
        async def delayed_shutdown():
            await asyncio.sleep(0.05)
            calendar_bot.shutdown_event.set()

        # Start the background fetch and the delayed shutdown concurrently
        await asyncio.gather(calendar_bot.run_background_fetch(), delayed_shutdown())

        # Should call fetch at least once (initial)
        calendar_bot.source_manager.fetch_and_cache_events.assert_called()

    @pytest.mark.asyncio
    async def test_run_background_fetch_exception(self, calendar_bot):
        """Test background fetch handles exceptions."""
        calendar_bot.source_manager.fetch_and_cache_events.side_effect = Exception("Fetch error")
        calendar_bot.running = False

        # Should not raise exception
        await calendar_bot.run_background_fetch()

    @pytest.mark.asyncio
    async def test_run_scheduler_success(self, calendar_bot):
        """Test scheduler runs initial refresh."""
        calendar_bot.running = False  # Ensure loop exits immediately

        await calendar_bot.run_scheduler()

        # Should call refresh_cycle at least once (initial)
        calendar_bot.cache_manager.is_cache_fresh.assert_called()

    @pytest.mark.asyncio
    async def test_run_scheduler_exception(self, calendar_bot):
        """Test scheduler handles exceptions."""
        calendar_bot.cache_manager.is_cache_fresh.side_effect = Exception("Scheduler error")
        calendar_bot.running = False

        # Should not raise exception
        await calendar_bot.run_scheduler()

    @pytest.mark.asyncio
    async def test_start_success(self, calendar_bot):
        """Test successful application start."""
        with patch("calendarbot.main.kill_calendarbot_processes") as mock_kill, patch.object(
            calendar_bot, "run_scheduler", new_callable=AsyncMock
        ) as mock_scheduler:
            mock_kill.return_value = (2, [])

            result = await calendar_bot.start()

            assert result is True
            assert calendar_bot.running is True
            mock_kill.assert_called_once_with(exclude_self=True)
            mock_scheduler.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_with_process_cleanup_warnings(self, calendar_bot):
        """Test start with process cleanup warnings."""
        with patch("calendarbot.main.kill_calendarbot_processes") as mock_kill, patch.object(
            calendar_bot, "run_scheduler", new_callable=AsyncMock
        ) as mock_scheduler:
            mock_kill.return_value = (1, ["Warning: Process xyz"])

            result = await calendar_bot.start()

            assert result is True
            mock_kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_no_auto_kill(self, calendar_bot):
        """Test start without auto-kill enabled."""
        calendar_bot.settings.auto_kill_existing = False

        with patch("calendarbot.main.kill_calendarbot_processes") as mock_kill, patch.object(
            calendar_bot, "run_scheduler", new_callable=AsyncMock
        ) as mock_scheduler:
            result = await calendar_bot.start()

            assert result is True
            mock_kill.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_initialization_failure(self, calendar_bot):
        """Test start with initialization failure."""
        calendar_bot.cache_manager.initialize.return_value = False

        with patch.object(calendar_bot, "run_scheduler", new_callable=AsyncMock) as mock_scheduler:
            result = await calendar_bot.start()

            assert result is False
            mock_scheduler.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_keyboard_interrupt(self, calendar_bot):
        """Test start handles KeyboardInterrupt."""
        with patch.object(calendar_bot, "run_scheduler", new_callable=AsyncMock) as mock_scheduler:
            mock_scheduler.side_effect = KeyboardInterrupt()

            result = await calendar_bot.start()

            assert result is True  # KeyboardInterrupt should return True

    @pytest.mark.asyncio
    async def test_start_exception(self, calendar_bot):
        """Test start handles general exceptions."""
        with patch.object(calendar_bot, "run_scheduler", new_callable=AsyncMock) as mock_scheduler:
            mock_scheduler.side_effect = Exception("Scheduler error")

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
    async def test_cleanup_success(self, calendar_bot):
        """Test successful cleanup."""
        await calendar_bot.cleanup()

        calendar_bot.cache_manager.cleanup_old_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_exception(self, calendar_bot):
        """Test cleanup handles exceptions."""
        calendar_bot.cache_manager.cleanup_old_events.side_effect = Exception("Cleanup error")

        # Should not raise exception
        await calendar_bot.cleanup()

    @pytest.mark.asyncio
    async def test_status_success(self, calendar_bot):
        """Test status reporting."""
        calendar_bot.running = True
        calendar_bot.last_successful_update = datetime(2024, 1, 15, 12, 0, 0)
        calendar_bot.consecutive_failures = 2

        status = await calendar_bot.status()

        assert status["running"] is True
        assert status["last_successful_update"] == "2024-01-15T12:00:00"
        assert status["consecutive_failures"] == 2
        assert status["source_configured"] is True
        assert status["source_status"] == "Connected"
        assert status["cache_events"] == 5
        assert status["settings"]["refresh_interval"] == 300

    @pytest.mark.asyncio
    async def test_status_no_last_update(self, calendar_bot):
        """Test status when no successful update."""
        status = await calendar_bot.status()

        assert status["last_successful_update"] is None

    @pytest.mark.asyncio
    async def test_status_exception(self, calendar_bot):
        """Test status handles exceptions."""
        calendar_bot.source_manager.get_source_info.side_effect = Exception("Status error")

        status = await calendar_bot.status()

        assert "error" in status


class TestSignalHandlers:
    """Test suite for signal handler functionality."""

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        app = Mock()

        with patch("calendarbot.main.signal.signal") as mock_signal:
            setup_signal_handlers(app)

            # Should set up SIGINT and SIGTERM handlers
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, mock_signal.call_args_list[0][0][1])
            mock_signal.assert_any_call(signal.SIGTERM, mock_signal.call_args_list[1][0][1])

    def test_signal_handler_function(self):
        """Test signal handler function creates stop task."""
        app = Mock()

        with patch("calendarbot.main.signal.signal") as mock_signal, patch(
            "calendarbot.main.asyncio.create_task"
        ) as mock_create_task:
            setup_signal_handlers(app)

            # Get the signal handler function
            signal_handler = mock_signal.call_args_list[0][0][1]

            # Call the signal handler
            signal_handler(signal.SIGINT, None)

            # Should create task to stop the app
            mock_create_task.assert_called_once()


class TestConfigurationCheck:
    """Test suite for configuration checking functionality."""

    def test_check_first_run_configuration_project_config_exists(self):
        """Test configuration check when project config exists."""
        with patch("pathlib.Path") as mock_path_class:
            mock_project_config = Mock()
            mock_project_config.exists.return_value = True

            # Create a mock that behaves like a real Path for Path(__file__)
            mock_path_instance = Mock()

            # Create mock for parent / "config" / "config.yaml" chain
            mock_parent = Mock()
            mock_path_instance.parent = mock_parent

            # Mock the operator chains
            mock_config_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_config_dir)
            mock_config_dir.__truediv__ = Mock(return_value=mock_project_config)

            mock_path_class.return_value = mock_path_instance

            result = check_first_run_configuration()

            assert result is True

    def test_check_first_run_configuration_user_config_exists(self):
        """Test configuration check when user config exists."""
        with patch("pathlib.Path") as mock_path_class:
            # Setup mock Path instances
            mock_project_config = Mock()
            mock_project_config.exists.return_value = False

            mock_user_config = Mock()
            mock_user_config.exists.return_value = True

            # Create a mock that behaves like a real Path for Path(__file__)
            mock_path_instance = Mock()

            # Create mock for parent / "config" / "config.yaml" chain
            mock_parent = Mock()
            mock_path_instance.parent = mock_parent

            # Mock the operator chains
            mock_config_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_config_dir)
            mock_config_dir.__truediv__ = Mock(return_value=mock_project_config)

            # Mock Path(__file__)
            mock_path_class.return_value = mock_path_instance

            # Mock Path.home() / ".config" / "calendarbot" / "config.yaml" chain
            mock_home_path = Mock()
            mock_config_path = Mock()
            mock_calendarbot_path = Mock()

            # Set up the chain properly
            mock_home_path.__truediv__ = Mock(return_value=mock_config_path)
            mock_config_path.__truediv__ = Mock(return_value=mock_calendarbot_path)
            mock_calendarbot_path.__truediv__ = Mock(return_value=mock_user_config)

            mock_path_class.home.return_value = mock_home_path

            result = check_first_run_configuration()

            assert result is True

    def test_check_first_run_configuration_env_var_set(self):
        """Test configuration check when environment variable is set."""
        with patch("pathlib.Path") as mock_path_class, patch(
            "calendarbot.main.settings"
        ) as mock_settings:
            # Setup mock Path instances
            mock_project_config = Mock()
            mock_project_config.exists.return_value = False

            mock_user_config = Mock()
            mock_user_config.exists.return_value = False

            # Create a mock that behaves like a real Path for Path(__file__)
            mock_path_instance = Mock()

            # Create mock for parent / "config" / "config.yaml" chain
            mock_parent = Mock()
            mock_path_instance.parent = mock_parent

            # Mock the operator chains
            mock_config_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_config_dir)
            mock_config_dir.__truediv__ = Mock(return_value=mock_project_config)

            # Mock Path(__file__)
            mock_path_class.return_value = mock_path_instance

            # Mock Path.home() / ".config" / "calendarbot" / "config.yaml" chain
            mock_home_path = Mock()
            mock_config_path = Mock()
            mock_calendarbot_path = Mock()

            # Set up the chain properly
            mock_home_path.__truediv__ = Mock(return_value=mock_config_path)
            mock_config_path.__truediv__ = Mock(return_value=mock_calendarbot_path)
            mock_calendarbot_path.__truediv__ = Mock(return_value=mock_user_config)

            mock_path_class.home.return_value = mock_home_path

            # But settings has ICS URL
            mock_settings.ics_url = "https://example.com/calendar.ics"

            result = check_first_run_configuration()

            assert result is True

    def test_check_first_run_configuration_no_config(self):
        """Test configuration check when no configuration found."""
        # Use a different patching strategy for the local import
        with patch("pathlib.Path") as mock_path_class, patch(
            "calendarbot.main.settings"
        ) as mock_settings:
            # Setup mock Path instances that properly support pathlib operations
            mock_project_config = Mock()
            mock_project_config.exists.return_value = False

            mock_user_config = Mock()
            mock_user_config.exists.return_value = False

            # Create a mock that behaves like a real Path for Path(__file__)
            mock_path_instance = Mock()

            # Create mock for parent / "config" / "config.yaml" chain
            mock_parent = Mock()
            mock_path_instance.parent = mock_parent

            # Mock the operator chains
            mock_config_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_config_dir)
            mock_config_dir.__truediv__ = Mock(return_value=mock_project_config)

            # Mock Path(__file__) constructor
            mock_path_class.return_value = mock_path_instance

            # Mock Path.home() / ".config" / "calendarbot" / "config.yaml" chain
            mock_home_path = Mock()
            mock_config_path = Mock()
            mock_calendarbot_path = Mock()

            # Set up the chain properly
            mock_home_path.__truediv__ = Mock(return_value=mock_config_path)
            mock_config_path.__truediv__ = Mock(return_value=mock_calendarbot_path)
            mock_calendarbot_path.__truediv__ = Mock(return_value=mock_user_config)

            mock_path_class.home.return_value = mock_home_path

            # No ICS URL in settings
            mock_settings.ics_url = None

            result = check_first_run_configuration()

            assert result is False


class TestMainEntryPoint:
    """Test suite for main entry point function."""

    @pytest.mark.asyncio
    async def test_main_success(self):
        """Test successful main execution."""
        # Import main only when needed to avoid unused import warnings
        from calendarbot.main import main

        with patch("calendarbot.main.check_first_run_configuration", return_value=True), patch(
            "calendarbot.main.settings"
        ) as mock_settings, patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.main.setup_signal_handlers"
        ):
            mock_settings.ics_url = "https://example.com/calendar.ics"
            mock_bot = Mock()
            mock_bot.start = AsyncMock(return_value=True)
            mock_bot_class.return_value = mock_bot

            result = await main()

            assert result == 0
            mock_bot.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_no_configuration(self):
        """Test main with missing configuration."""
        # Import main only when needed to avoid unused import warnings
        from calendarbot.main import main

        with patch("calendarbot.main.check_first_run_configuration", return_value=False), patch(
            "builtins.print"
        ) as mock_print:
            result = await main()

            assert result == 1
            mock_print.assert_called()

    @pytest.mark.asyncio
    async def test_main_no_ics_url(self):
        """Test main with missing ICS URL."""
        # Import main only when needed to avoid unused import warnings
        from calendarbot.main import main

        with patch("calendarbot.main.check_first_run_configuration", return_value=True), patch(
            "calendarbot.main.settings"
        ) as mock_settings:
            mock_settings.ics_url = None

            result = await main()

            assert result == 1

    @pytest.mark.asyncio
    async def test_main_app_start_failure(self):
        """Test main when app start fails."""
        # Import main only when needed to avoid unused import warnings
        from calendarbot.main import main

        with patch("calendarbot.main.check_first_run_configuration", return_value=True), patch(
            "calendarbot.main.settings"
        ) as mock_settings, patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.main.setup_signal_handlers"
        ):
            mock_settings.ics_url = "https://example.com/calendar.ics"
            mock_bot = Mock()
            mock_bot.start = AsyncMock(return_value=False)
            mock_bot_class.return_value = mock_bot

            result = await main()

            assert result == 1

    @pytest.mark.asyncio
    async def test_main_exception(self):
        """Test main handles exceptions."""
        # Import main only when needed to avoid unused import warnings
        from calendarbot.main import main

        with patch(
            "calendarbot.main.check_first_run_configuration", side_effect=Exception("Test error")
        ):
            result = await main()

            assert result == 1
