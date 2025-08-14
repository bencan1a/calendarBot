"""
Unit tests for BrowserManager component.

Tests browser process lifecycle management, memory optimization, crash recovery,
and all aspects of the browser manager functionality with comprehensive mocking.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.kiosk.browser_manager import (
    BrowserConfig,
    BrowserError,
    BrowserManager,
    BrowserState,
    BrowserStatus,
)


class TestBrowserConfig:
    """Test BrowserConfig data class and defaults."""

    def test_browser_config_when_default_then_pi_zero_2w_optimized(self) -> None:
        """Test that default config is optimized for Pi Zero 2W."""
        config = BrowserConfig()

        # Pi Zero 2W optimizations
        assert config.memory_limit_mb == 80  # Conservative for 512MB total
        assert config.window_width == 480
        assert config.window_height == 800
        assert config.executable_path == "chromium-browser"

        # Restart behavior
        assert config.max_restart_attempts == 5
        assert config.restart_backoff_factor == 1.5
        assert config.crash_restart_delay == 3

        # Health monitoring
        assert config.health_check_interval == 30
        assert config.memory_check_interval == 60

    def test_browser_config_when_custom_values_then_settings_applied(self) -> None:
        """Test custom configuration values are properly set."""
        config = BrowserConfig(
            memory_limit_mb=128,
            startup_delay=10,
            max_restart_attempts=3,
            window_width=800,
            window_height=600,
        )

        assert config.memory_limit_mb == 128
        assert config.startup_delay == 10
        assert config.max_restart_attempts == 3
        assert config.window_width == 800
        assert config.window_height == 600


class TestBrowserState:
    """Test BrowserState enum values."""

    def test_browser_state_when_all_values_then_correct_strings(self) -> None:
        """Test all browser state enum values."""
        assert BrowserState.STOPPED.value == "stopped"
        assert BrowserState.STARTING.value == "starting"
        assert BrowserState.RUNNING.value == "running"
        assert BrowserState.CRASHED.value == "crashed"
        assert BrowserState.RESTARTING.value == "restarting"
        assert BrowserState.FAILED.value == "failed"


class TestBrowserStatus:
    """Test BrowserStatus data class."""

    def test_browser_status_when_created_then_all_fields_set(self) -> None:
        """Test BrowserStatus creation with all fields."""
        start_time = datetime.now()
        uptime = timedelta(minutes=30)
        last_restart = datetime.now() - timedelta(minutes=5)
        last_health_check = datetime.now() - timedelta(seconds=30)
        error_time = datetime.now() - timedelta(minutes=1)

        status = BrowserStatus(
            state=BrowserState.RUNNING,
            pid=12345,
            start_time=start_time,
            uptime=uptime,
            memory_usage_mb=75,
            cpu_usage_percent=12.5,
            crash_count=1,
            restart_count=2,
            last_restart_time=last_restart,
            is_responsive=True,
            last_health_check=last_health_check,
            last_error="Test error",
            error_time=error_time,
        )

        assert status.state == BrowserState.RUNNING
        assert status.pid == 12345
        assert status.start_time == start_time
        assert status.uptime == uptime
        assert status.memory_usage_mb == 75
        assert status.cpu_usage_percent == 12.5
        assert status.crash_count == 1
        assert status.restart_count == 2
        assert status.last_restart_time == last_restart
        assert status.is_responsive is True
        assert status.last_health_check == last_health_check
        assert status.last_error == "Test error"
        assert status.error_time == error_time


class TestBrowserError:
    """Test BrowserError exception class."""

    def test_browser_error_when_message_only_then_basic_error(self) -> None:
        """Test BrowserError with message only."""
        error = BrowserError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code is None
        assert error.browser_state is None

    def test_browser_error_when_all_fields_then_complete_error(self) -> None:
        """Test BrowserError with all fields."""
        error = BrowserError(
            "Startup failed", error_code="STARTUP_FAILURE", browser_state=BrowserState.FAILED
        )

        assert str(error) == "Startup failed"
        assert error.message == "Startup failed"
        assert error.error_code == "STARTUP_FAILURE"
        assert error.browser_state == BrowserState.FAILED


class TestBrowserManager:
    """Test BrowserManager class functionality."""

    @pytest.fixture
    def config(self) -> BrowserConfig:
        """Create test browser configuration."""
        return BrowserConfig(
            startup_delay=0,  # Skip delay in tests
            startup_timeout=5,
            shutdown_timeout=2,
            memory_limit_mb=80,
            health_check_interval=1,
            memory_check_interval=1,
        )

    @pytest.fixture
    def manager(self, config: BrowserConfig) -> BrowserManager:
        """Create test browser manager."""
        return BrowserManager(config)

    def test_browser_manager_when_init_then_correct_initial_state(
        self, manager: BrowserManager
    ) -> None:
        """Test BrowserManager initialization."""
        assert manager._state == BrowserState.STOPPED
        assert manager._process is None
        assert manager._current_url is None
        assert manager._crash_count == 0
        assert manager._restart_count == 0
        assert manager._restart_attempts == 0
        assert manager._shutdown_requested is False

    @pytest.mark.asyncio
    async def test_start_browser_when_empty_url_then_raises_browser_error(
        self, manager: BrowserManager
    ) -> None:
        """Test start_browser with empty URL raises error."""
        with pytest.raises(BrowserError) as exc_info:
            await manager.start_browser("")

        assert "URL cannot be empty" in str(exc_info.value)
        assert exc_info.value.error_code == "INVALID_URL"

    @pytest.mark.asyncio
    async def test_start_browser_when_valid_url_then_starts_successfully(
        self, manager: BrowserManager
    ) -> None:
        """Test successful browser startup."""
        test_url = "http://localhost:8080/whats-next-view"

        # Mock subprocess creation
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running

        with (
            patch.object(manager, "_launch_process", return_value=mock_process) as mock_launch,
            patch.object(manager, "_start_monitoring") as mock_monitoring,
            patch.object(manager, "_wait_for_responsive", return_value=True) as mock_responsive,
        ):
            result = await manager.start_browser(test_url)

            assert result is True
            assert manager._state == BrowserState.RUNNING
            assert manager._current_url == test_url
            assert manager._process == mock_process
            assert manager._start_time is not None

            mock_launch.assert_called_once()
            mock_monitoring.assert_called_once()
            mock_responsive.assert_called_once_with(timeout=manager.config.startup_timeout)

    @pytest.mark.asyncio
    async def test_start_browser_when_already_running_then_stops_first(
        self, manager: BrowserManager
    ) -> None:
        """Test start_browser stops existing browser first."""
        manager._state = BrowserState.RUNNING
        test_url = "http://localhost:8080"

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        with (
            patch.object(manager, "stop_browser") as mock_stop,
            patch.object(manager, "_launch_process", return_value=mock_process),
            patch.object(manager, "_start_monitoring"),
            patch.object(manager, "_wait_for_responsive", return_value=True),
        ):
            await manager.start_browser(test_url)

            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_browser_when_launch_fails_then_returns_false(
        self, manager: BrowserManager
    ) -> None:
        """Test start_browser when process launch fails."""
        test_url = "http://localhost:8080"

        with (
            patch.object(manager, "_launch_process", return_value=None),
            patch.object(manager, "_handle_startup_failure") as mock_handle_failure,
        ):
            result = await manager.start_browser(test_url)

            assert result is False
            mock_handle_failure.assert_called_once_with("Failed to launch browser process")

    @pytest.mark.asyncio
    async def test_start_browser_when_not_responsive_then_returns_false(
        self, manager: BrowserManager
    ) -> None:
        """Test start_browser when browser doesn't become responsive."""
        test_url = "http://localhost:8080"
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        with (
            patch.object(manager, "_launch_process", return_value=mock_process),
            patch.object(manager, "_start_monitoring"),
            patch.object(manager, "_wait_for_responsive", return_value=False),
            patch.object(manager, "_handle_startup_failure") as mock_handle_failure,
        ):
            result = await manager.start_browser(test_url)

            assert result is False
            mock_handle_failure.assert_called_once_with("Browser failed to become responsive")

    @pytest.mark.asyncio
    async def test_stop_browser_when_no_process_then_returns_true(
        self, manager: BrowserManager
    ) -> None:
        """Test stop_browser when no process is running."""
        manager._process = None

        with patch.object(manager, "_stop_monitoring") as mock_stop_monitoring:
            result = await manager.stop_browser()

            assert result is True
            assert manager._state == BrowserState.STOPPED
            mock_stop_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_browser_when_graceful_shutdown_then_terminates_cleanly(
        self, manager: BrowserManager
    ) -> None:
        """Test graceful browser shutdown."""
        mock_process = Mock()
        manager._process = mock_process
        manager._state = BrowserState.RUNNING

        with (
            patch.object(manager, "_stop_monitoring") as mock_stop_monitoring,
            patch.object(manager, "_wait_for_process_exit"),
            patch.object(manager, "_cleanup_process_state") as mock_cleanup,
        ):
            # Mock successful wait
            mock_wait_exit_task = AsyncMock()
            with (
                patch("asyncio.create_task", return_value=mock_wait_exit_task),
                patch("asyncio.wait_for"),
            ):
                result = await manager.stop_browser()

                assert result is True
                mock_process.terminate.assert_called_once()
                mock_stop_monitoring.assert_called_once()
                mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_browser_when_timeout_then_kills_process(
        self, manager: BrowserManager
    ) -> None:
        """Test browser force kill on timeout."""
        mock_process = Mock()
        manager._process = mock_process

        with (
            patch.object(manager, "_stop_monitoring"),
            patch.object(manager, "_wait_for_process_exit"),
            patch.object(manager, "_cleanup_process_state"),
            patch("asyncio.create_task"),
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
            patch("asyncio.sleep"),
        ):
            result = await manager.stop_browser()

            assert result is True
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_browser_when_successful_then_returns_true(
        self, manager: BrowserManager
    ) -> None:
        """Test successful browser restart."""
        manager._current_url = "http://localhost:8080"
        manager._restart_attempts = 0

        with (
            patch.object(manager, "stop_browser") as mock_stop,
            patch.object(manager, "start_browser", return_value=True) as mock_start,
            patch.object(manager, "_calculate_restart_delay", return_value=1),
            patch("asyncio.sleep"),
        ):
            result = await manager.restart_browser()

            assert result is True
            assert manager._restart_count == 1
            assert manager._restart_attempts == 1
            assert manager._last_restart_time is not None

            mock_stop.assert_called_once()
            mock_start.assert_called_once_with("http://localhost:8080")

    @pytest.mark.asyncio
    async def test_restart_browser_when_max_attempts_exceeded_then_fails(
        self, manager: BrowserManager
    ) -> None:
        """Test restart fails when max attempts exceeded."""
        manager._restart_attempts = manager.config.max_restart_attempts + 1

        result = await manager.restart_browser()

        assert result is False
        assert manager._state == BrowserState.FAILED

    @pytest.mark.asyncio
    async def test_restart_browser_when_no_url_then_fails(self, manager: BrowserManager) -> None:
        """Test restart fails when no URL available."""
        manager._current_url = None
        manager._restart_attempts = 0

        with (
            patch.object(manager, "stop_browser"),
            patch.object(manager, "_calculate_restart_delay", return_value=0),
        ):
            result = await manager.restart_browser()

            assert result is False

    def test_is_browser_healthy_when_not_running_then_false(self, manager: BrowserManager) -> None:
        """Test health check when browser not running."""
        manager._state = BrowserState.STOPPED
        manager._process = None

        result = manager.is_browser_healthy()

        assert result is False

    def test_is_browser_healthy_when_process_exited_then_false(
        self, manager: BrowserManager
    ) -> None:
        """Test health check when process has exited."""
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited

        manager._state = BrowserState.RUNNING
        manager._process = mock_process

        result = manager.is_browser_healthy()

        assert result is False
        assert manager._state == BrowserState.CRASHED
        assert manager._crash_count == 1

    def test_is_browser_healthy_when_memory_exceeded_then_false(
        self, manager: BrowserManager
    ) -> None:
        """Test health check when memory limit exceeded."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running

        manager._state = BrowserState.RUNNING
        manager._process = mock_process

        with patch.object(manager, "_get_memory_usage", return_value=100):  # Over 80MB limit
            result = manager.is_browser_healthy()

            assert result is False

    def test_is_browser_healthy_when_all_good_then_true(self, manager: BrowserManager) -> None:
        """Test health check when everything is healthy."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running

        manager._state = BrowserState.RUNNING
        manager._process = mock_process

        with patch.object(manager, "_get_memory_usage", return_value=50):  # Under limit
            result = manager.is_browser_healthy()

            assert result is True

    def test_get_browser_status_when_running_then_complete_status(
        self, manager: BrowserManager
    ) -> None:
        """Test get_browser_status with running browser."""
        mock_process = Mock()
        mock_process.pid = 12345

        manager._state = BrowserState.RUNNING
        manager._process = mock_process
        manager._start_time = datetime.now() - timedelta(minutes=30)
        manager._crash_count = 1
        manager._restart_count = 2

        with (
            patch.object(manager, "_get_memory_usage", return_value=75),
            patch.object(manager, "_get_cpu_usage", return_value=15.5),
            patch.object(manager, "is_browser_healthy", return_value=True),
        ):
            status = manager.get_browser_status()

            assert status.state == BrowserState.RUNNING
            assert status.pid == 12345
            assert status.start_time == manager._start_time
            assert status.uptime is not None
            assert status.memory_usage_mb == 75
            assert status.cpu_usage_percent == 15.5
            assert status.crash_count == 1
            assert status.restart_count == 2
            assert status.is_responsive is True

    def test_get_browser_status_when_error_then_failed_status(
        self, manager: BrowserManager
    ) -> None:
        """Test get_browser_status when error occurs."""
        manager._crash_count = 3
        manager._restart_count = 5

        with patch.object(manager, "_get_memory_usage", side_effect=Exception("Test error")):
            status = manager.get_browser_status()

            assert status.state == BrowserState.FAILED
            assert status.pid is None
            assert status.memory_usage_mb == 0
            assert status.cpu_usage_percent == 0.0
            assert status.crash_count == 3
            assert status.restart_count == 5
            assert status.is_responsive is False
            assert status.last_error == "Test error"
            assert status.error_time is not None

    @pytest.mark.asyncio
    async def test_clear_cache_when_running_then_restarts(self, manager: BrowserManager) -> None:
        """Test clear_cache restarts browser when running."""
        manager._state = BrowserState.RUNNING

        with patch.object(manager, "restart_browser", return_value=True) as mock_restart:
            result = await manager.clear_cache()

            assert result is True
            mock_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_when_not_running_then_returns_true(
        self, manager: BrowserManager
    ) -> None:
        """Test clear_cache when browser not running."""
        manager._state = BrowserState.STOPPED

        result = await manager.clear_cache()

        assert result is True

    def test_build_chromium_args_when_called_then_pi_optimized_flags(
        self, manager: BrowserManager
    ) -> None:
        """Test Chromium arguments are optimized for Pi Zero 2W."""
        test_url = "http://localhost:8080"

        args = manager._build_chromium_args(test_url)

        # Check key Pi Zero 2W optimizations
        assert "--kiosk" in args
        assert "--max_old_space_size=64" in args
        assert "--disable-dev-shm-usage" in args
        assert "--memory-pressure-off" in args
        assert "--no-sandbox" in args
        assert "--touch-events=enabled" in args
        assert test_url in args

        # Check window size
        expected_window_size = (
            f"--window-size={manager.config.window_width},{manager.config.window_height}"
        )
        assert expected_window_size in args

    @pytest.mark.asyncio
    async def test_launch_process_when_successful_then_returns_process(
        self, manager: BrowserManager
    ) -> None:
        """Test successful process launch."""
        cmd_args = ["chromium-browser", "--kiosk", "http://localhost:8080"]

        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running

        with (
            patch("subprocess.Popen", return_value=mock_process) as mock_popen,
            patch("asyncio.sleep"),
        ):
            result = await manager._launch_process(cmd_args)

            assert result == mock_process
            mock_popen.assert_called_once()

            # Check environment variables were set
            call_args = mock_popen.call_args
            env = call_args.kwargs["env"]
            assert "DISPLAY" in env
            assert "XAUTHORITY" in env

    @pytest.mark.asyncio
    async def test_launch_process_when_immediate_exit_then_returns_none(
        self, manager: BrowserManager
    ) -> None:
        """Test process launch when process exits immediately."""
        cmd_args = ["chromium-browser", "--kiosk", "http://localhost:8080"]

        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited

        with patch("subprocess.Popen", return_value=mock_process), patch("asyncio.sleep"):
            result = await manager._launch_process(cmd_args)

            assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_responsive_when_timeout_then_false(
        self, manager: BrowserManager
    ) -> None:
        """Test wait_for_responsive timeout."""
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited
        manager._process = mock_process

        with patch("asyncio.sleep"):
            result = await manager._wait_for_responsive(timeout=2)

            assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_responsive_when_responsive_then_true(
        self, manager: BrowserManager
    ) -> None:
        """Test wait_for_responsive success."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running
        manager._process = mock_process

        with patch("asyncio.sleep"):
            result = await manager._wait_for_responsive(timeout=1)

            assert result is True

    def test_get_memory_usage_when_psutil_available_then_returns_memory(
        self, manager: BrowserManager
    ) -> None:
        """Test memory usage calculation with psutil."""
        mock_process = Mock()
        mock_process.pid = 12345
        manager._process = mock_process

        mock_psutil_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB in bytes
        mock_psutil_process.memory_info.return_value = mock_memory_info

        with patch("calendarbot.kiosk.browser_manager.psutil") as mock_psutil:
            mock_psutil.Process.return_value = mock_psutil_process

            result = manager._get_memory_usage()

            assert result == 100  # MB
            mock_psutil.Process.assert_called_once_with(12345)

    def test_get_memory_usage_when_no_process_then_returns_zero(
        self, manager: BrowserManager
    ) -> None:
        """Test memory usage when no process."""
        manager._process = None

        result = manager._get_memory_usage()

        assert result == 0

    def test_get_memory_usage_when_psutil_error_then_returns_zero(
        self, manager: BrowserManager
    ) -> None:
        """Test memory usage when psutil raises error."""
        mock_process = Mock()
        mock_process.pid = 12345
        manager._process = mock_process

        with patch("calendarbot.kiosk.browser_manager.psutil") as mock_psutil:
            mock_psutil.Process.side_effect = Exception("Process not found")

            result = manager._get_memory_usage()

            assert result == 0

    def test_get_cpu_usage_when_psutil_available_then_returns_cpu(
        self, manager: BrowserManager
    ) -> None:
        """Test CPU usage calculation with psutil."""
        mock_process = Mock()
        mock_process.pid = 12345
        manager._process = mock_process

        mock_psutil_process = Mock()
        mock_psutil_process.cpu_percent.return_value = 25.5

        with patch("calendarbot.kiosk.browser_manager.psutil") as mock_psutil:
            mock_psutil.Process.return_value = mock_psutil_process

            result = manager._get_cpu_usage()

            assert result == 25.5
            mock_psutil.Process.assert_called_once_with(12345)

    def test_calculate_restart_delay_when_first_attempt_then_base_delay(
        self, manager: BrowserManager
    ) -> None:
        """Test restart delay calculation for first attempt."""
        manager._restart_attempts = 1

        result = manager._calculate_restart_delay()

        assert result == manager.config.crash_restart_delay

    def test_calculate_restart_delay_when_multiple_attempts_then_exponential_backoff(
        self, manager: BrowserManager
    ) -> None:
        """Test restart delay calculation with exponential backoff."""
        manager._restart_attempts = 3
        manager.config.crash_restart_delay = 2
        manager.config.restart_backoff_factor = 2.0

        result = manager._calculate_restart_delay()

        # 2 * (2.0 ** (3-1)) = 2 * 4 = 8
        assert result == 8

    def test_calculate_restart_delay_when_very_long_then_capped(
        self, manager: BrowserManager
    ) -> None:
        """Test restart delay is capped at 60 seconds."""
        manager._restart_attempts = 10
        manager.config.crash_restart_delay = 10
        manager.config.restart_backoff_factor = 3.0

        result = manager._calculate_restart_delay()

        assert result == 60  # Capped at maximum

    @pytest.mark.asyncio
    async def test_wait_for_process_exit_when_process_running_then_waits(
        self, manager: BrowserManager
    ) -> None:
        """Test waiting for process exit."""
        mock_process = Mock()
        # First call returns None (running), second call returns 0 (exited)
        mock_process.poll.side_effect = [None, 0]
        manager._process = mock_process

        with patch("asyncio.sleep"):
            await manager._wait_for_process_exit()

            assert mock_process.poll.call_count == 2

    def test_cleanup_process_state_when_called_then_resets_state(
        self, manager: BrowserManager
    ) -> None:
        """Test process state cleanup."""
        manager._process = Mock()
        manager._state = BrowserState.RUNNING
        manager._start_time = datetime.now()

        manager._cleanup_process_state()

        assert manager._process is None
        assert manager._state == BrowserState.STOPPED
        assert manager._start_time is None

    @pytest.mark.asyncio
    async def test_handle_startup_failure_when_called_then_sets_error_state(
        self, manager: BrowserManager
    ) -> None:
        """Test startup failure handling."""
        error_msg = "Browser failed to start"

        with (
            patch.object(manager, "_stop_monitoring") as mock_stop,
            patch.object(manager, "_cleanup_process_state") as mock_cleanup,
        ):
            await manager._handle_startup_failure(error_msg)

            assert manager._last_error == error_msg
            assert manager._error_time is not None
            assert manager._state == BrowserState.FAILED

            mock_stop.assert_called_once()
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_monitoring_when_called_then_starts_tasks(
        self, manager: BrowserManager
    ) -> None:
        """Test monitoring task startup."""
        with patch("asyncio.create_task") as mock_create_task:
            mock_health_task = Mock()
            mock_memory_task = Mock()
            mock_create_task.side_effect = [mock_health_task, mock_memory_task]

            await manager._start_monitoring()

            assert manager._health_task == mock_health_task
            assert manager._memory_task == mock_memory_task
            assert mock_create_task.call_count == 2

    @pytest.mark.asyncio
    async def test_stop_monitoring_when_tasks_running_then_cancels_tasks(
        self, manager: BrowserManager
    ) -> None:
        """Test monitoring task cancellation."""

        # Create real asyncio tasks for more realistic testing
        async def dummy_task():
            await asyncio.sleep(10)  # Long running task

        health_task = asyncio.create_task(dummy_task())
        memory_task = asyncio.create_task(dummy_task())

        manager._health_task = health_task
        manager._memory_task = memory_task

        # Verify tasks are running before stopping
        assert not health_task.done()
        assert not memory_task.done()

        await manager._stop_monitoring()

        # Verify tasks were cancelled
        assert health_task.cancelled()
        assert memory_task.cancelled()

    @pytest.mark.asyncio
    async def test_health_monitoring_loop_when_unhealthy_then_triggers_restart(
        self, manager: BrowserManager
    ) -> None:
        """Test health monitoring loop triggers restart on failure."""
        manager._shutdown_requested = False

        with (
            patch.object(manager, "is_browser_healthy", return_value=False),
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        ):  # Stop loop
            try:
                await manager._health_monitoring_loop()
            except asyncio.CancelledError:
                pass

            assert manager._last_health_check is not None
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_monitoring_loop_when_critical_then_triggers_restart(
        self, manager: BrowserManager
    ) -> None:
        """Test memory monitoring loop triggers restart on critical usage."""
        manager._shutdown_requested = False
        manager.config.memory_limit_mb = 100
        manager.config.memory_critical_threshold = 0.9  # 90%

        with (
            patch.object(manager, "_get_memory_usage", return_value=95),
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        ):
            try:
                await manager._memory_monitoring_loop()
            except asyncio.CancelledError:
                pass

            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_monitoring_loop_when_warning_then_clears_cache(
        self, manager: BrowserManager
    ) -> None:
        """Test memory monitoring loop clears cache on warning threshold."""
        manager._shutdown_requested = False
        manager.config.memory_limit_mb = 100
        manager.config.memory_warning_threshold = 0.8  # 80%
        manager.config.memory_critical_threshold = 0.9  # 90%

        with (
            patch.object(manager, "_get_memory_usage", return_value=85),
            patch("asyncio.create_task") as mock_create_task,
            patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        ):
            try:
                await manager._memory_monitoring_loop()
            except asyncio.CancelledError:
                pass

            mock_create_task.assert_called_once()
