"""Integration tests for KioskManager orchestration workflows.

Tests the complete 4-phase kiosk startup sequence and component coordination:
1. Web Server Phase: SharedWebServer initialization and readiness
2. Readiness Phase: Web server health validation
3. Browser Phase: BrowserManager startup and navigation
4. Monitoring Phase: Health monitoring and recovery loops

Validates Pi Zero 2W constraints, error recovery, and performance thresholds.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.kiosk.browser_manager import BrowserState, BrowserStatus
from calendarbot.kiosk.manager import KioskManager, KioskStatus
from calendarbot.settings.kiosk_models import KioskSettings
from calendarbot.utils.daemon import DaemonStatus

# Import these in test functions to avoid circular import at module level
# from calendarbot.kiosk.manager import KioskError, KioskManager, KioskStatus

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestKioskManagerOrchestration:
    """Test KioskManager component orchestration and 4-phase startup workflow."""

    async def test_kiosk_startup_when_all_phases_succeed_then_orchestration_complete(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        performance_monitor,
        integration_test_base,
    ) -> None:
        """Test successful 4-phase kiosk startup orchestration."""
        # Setup mock CalendarBot settings
        mock_settings = MagicMock()
        mock_settings.web_port = 8080
        mock_settings.web_host = "127.0.0.1"

        # Import here to avoid circular import
        from calendarbot.kiosk.manager import KioskManager

        # Create KioskManager with mocks
        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock all internal methods to validate orchestration sequence
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=True)
        manager._start_browser = AsyncMock(return_value=True)
        manager._start_health_monitoring = AsyncMock()

        performance_monitor.start_timing("full_kiosk_startup")

        # Execute startup
        result = await manager.start_kiosk()

        startup_duration = performance_monitor.end_timing("full_kiosk_startup")

        # Validate success
        assert result is True, "Kiosk startup should succeed with all phases working"
        assert manager._start_time is not None, "Start time should be recorded"

        # Validate orchestration sequence
        manager._start_web_server.assert_called_once()
        manager._wait_for_web_server_ready.assert_called_once()
        manager._start_browser.assert_called_once()
        manager._start_health_monitoring.assert_called_once()

        # Validate Pi Zero 2W performance constraint
        performance_monitor.assert_performance_threshold("full_kiosk_startup", 30.0)

        logger.info(f"Full kiosk startup completed in {startup_duration:.2f}s")

    async def test_kiosk_startup_when_web_server_fails_then_cleanup_and_fail(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test kiosk startup failure at web server phase triggers cleanup."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock phase 1 failure
        manager._start_web_server = AsyncMock(return_value=False)
        manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        assert result is False, "Startup should fail when web server fails"
        assert manager._last_error is not None, "Error should be recorded"
        manager._cleanup_on_failure.assert_called_once()

    async def test_kiosk_startup_when_readiness_timeout_then_fail_gracefully(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test kiosk startup failure at readiness phase."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock phase 1 success, phase 2 failure
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=False)
        manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        assert result is False
        assert manager._last_error is not None
        assert "Web server failed to become ready" in manager._last_error
        manager._cleanup_on_failure.assert_called_once()

    async def test_kiosk_startup_when_browser_fails_then_web_server_cleanup(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test kiosk startup failure at browser phase cleans up web server."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock phases 1-2 success, phase 3 failure
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=True)
        manager._start_browser = AsyncMock(return_value=False)
        manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        assert result is False
        assert manager._last_error is not None
        assert "Failed to start browser" in manager._last_error
        manager._cleanup_on_failure.assert_called_once()

        # Verify web server was started before browser failure
        manager._start_web_server.assert_called_once()
        manager._wait_for_web_server_ready.assert_called_once()

    async def test_kiosk_shutdown_when_running_then_graceful_component_stop(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        performance_monitor,
    ) -> None:
        """Test graceful kiosk shutdown orchestration."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Setup running state
        manager._shutdown_requested = False
        manager._stop_health_monitoring = AsyncMock()
        manager.browser_manager.stop_browser = AsyncMock(return_value=True)
        manager._stop_web_server = AsyncMock(return_value=True)

        performance_monitor.start_timing("kiosk_shutdown")

        result = await manager.stop_kiosk()

        shutdown_duration = performance_monitor.end_timing("kiosk_shutdown")

        assert result is True
        assert manager._shutdown_requested is True

        # Validate shutdown sequence (reverse of startup)
        manager._stop_health_monitoring.assert_called_once()
        manager.browser_manager.stop_browser.assert_called_once_with(timeout=10)
        manager._stop_web_server.assert_called_once()

        # Shutdown should be fast (no complex operations)
        performance_monitor.assert_performance_threshold("kiosk_shutdown", 15.0)

        logger.info(f"Kiosk shutdown completed in {shutdown_duration:.2f}s")

    async def test_kiosk_restart_when_requested_then_stop_start_cycle(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test kiosk restart orchestration performs stop-start cycle."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        manager.stop_kiosk = AsyncMock(return_value=True)
        manager.start_kiosk = AsyncMock(return_value=True)

        result = await manager.restart_kiosk()

        assert result is True
        assert manager._restart_count == 1

        # Validate restart sequence
        manager.stop_kiosk.assert_called_once_with(timeout=15)
        manager.start_kiosk.assert_called_once()

    async def test_kiosk_restart_when_start_fails_then_increment_count_anyway(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test restart failure still increments restart count for tracking."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        manager.stop_kiosk = AsyncMock(return_value=True)
        manager.start_kiosk = AsyncMock(return_value=False)  # Start fails

        result = await manager.restart_kiosk()

        assert result is False
        assert manager._restart_count == 1  # Count incremented despite failure


@pytest.mark.asyncio
class TestKioskManagerWebServerIntegration:
    """Test KioskManager integration with SharedWebServer component."""

    async def test_start_web_server_when_daemon_running_then_reuse_existing(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test web server startup reuses existing daemon if running."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        # Configure daemon as already running
        mock_daemon_manager.is_daemon_running.return_value = True
        mock_daemon_manager.get_daemon_pid.return_value = 12345

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        result = await manager._start_web_server()

        assert result is True
        mock_daemon_manager.is_daemon_running.assert_called_once()
        mock_daemon_manager.get_daemon_pid.assert_called_once()

        # Should NOT create new daemon
        mock_daemon_manager.create_pid_file.assert_not_called()

    async def test_start_web_server_when_no_daemon_then_create_new(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test web server startup creates new daemon when none running."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080
        mock_settings.web_host = "127.0.0.1"  # Add missing host

        # Configure no existing daemon
        mock_daemon_manager.is_daemon_running.return_value = False

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock CalendarBot app initialization
        manager._initialize_calendarbot_app = AsyncMock()
        mock_app = MagicMock()
        mock_app.display_manager = MagicMock()
        mock_app.cache_manager = MagicMock()
        manager._initialize_calendarbot_app.return_value = mock_app

        # Mock the web server creation - remove invalid SharedWebServer patch
        result = await manager._start_web_server()

        assert result is True
        manager._initialize_calendarbot_app.assert_called_once()
        mock_daemon_manager.create_pid_file.assert_called_once()

    async def test_wait_for_web_server_ready_when_responds_then_success(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test web server readiness check succeeds when server responds."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080
        mock_settings.web_host = "127.0.0.1"

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock aiohttp with proper async context manager behavior
        class MockResponse:
            def __init__(self):
                self.status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def get(self, url, timeout=None):
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch("calendarbot.kiosk.manager.aiohttp.ClientSession", MockSession):
            with patch("calendarbot.kiosk.manager.ClientTimeout"):
                result = await manager._wait_for_web_server_ready(timeout=1)

        assert result is True

    async def test_wait_for_web_server_ready_when_timeout_then_failure(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test web server readiness check fails on timeout."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock connection failure
        with patch("calendarbot.kiosk.manager.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession.side_effect = Exception("Connection failed")

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await manager._wait_for_web_server_ready(timeout=1)

        assert result is False


@pytest.mark.asyncio
class TestKioskManagerBrowserIntegration:
    """Test KioskManager integration with BrowserManager component."""

    async def test_start_browser_when_successful_then_correct_url_navigation(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test browser startup navigates to correct kiosk URL."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080
        mock_settings.web_host = "127.0.0.1"

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        manager.browser_manager.start_browser = AsyncMock(return_value=True)

        result = await manager._start_browser()

        assert result is True

        # Validate correct URL construction
        expected_url = f"http://localhost:8080/{pi_zero_2w_kiosk_settings.target_layout}"
        manager.browser_manager.start_browser.assert_called_once_with(expected_url)

    async def test_start_browser_when_exception_then_handle_gracefully(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test browser startup handles exceptions gracefully."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        manager.browser_manager.start_browser = AsyncMock(
            side_effect=Exception("Browser launch failed")
        )

        result = await manager._start_browser()

        assert result is False


@pytest.mark.asyncio
class TestKioskManagerHealthMonitoring:
    """Test KioskManager health monitoring and recovery loops."""

    async def test_monitoring_loop_when_browser_unhealthy_then_restart_triggered(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test monitoring loop triggers browser restart when unhealthy."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock browser as unhealthy
        manager.browser_manager.is_browser_healthy = MagicMock(return_value=False)
        manager.browser_manager.restart_browser = AsyncMock()
        manager._check_web_server_health = AsyncMock(return_value=True)

        # Run one iteration of monitoring loop
        iteration_count = 0

        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 1:
                manager._shutdown_requested = True

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await manager._monitoring_loop()

        manager.browser_manager.restart_browser.assert_called_once()

    async def test_monitoring_loop_when_web_server_unhealthy_then_restart_triggered(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test monitoring loop triggers web server restart when unhealthy."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock web server as unhealthy, browser as healthy
        manager.browser_manager.is_browser_healthy = MagicMock(return_value=True)
        manager._check_web_server_health = AsyncMock(return_value=False)
        manager._restart_web_server = AsyncMock()

        # Run one iteration of monitoring loop
        iteration_count = 0

        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 1:
                manager._shutdown_requested = True

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await manager._monitoring_loop()

        manager._restart_web_server.assert_called_once()

    async def test_health_monitoring_task_lifecycle(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test health monitoring task can be started and stopped."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Create a proper mock task that behaves like asyncio.Task
        class MockTask:
            def __init__(self):
                self._cancelled = False
                self.cancel = MagicMock()

            def done(self):
                return False  # So cancel() gets called

            def __await__(self):
                # When awaited, raise CancelledError (like real cancelled task)
                import asyncio

                async def _await():
                    raise asyncio.CancelledError()

                return _await().__await__()

        mock_task = MockTask()

        with patch("asyncio.create_task", return_value=mock_task) as mock_create_task:
            # Start monitoring
            await manager._start_health_monitoring()

            assert manager._monitoring_task == mock_task
            mock_create_task.assert_called_once()

            # Stop monitoring (within patch context)
            await manager._stop_health_monitoring()

            mock_task.cancel.assert_called_once()


@pytest.mark.asyncio
class TestKioskManagerStatusReporting:
    """Test KioskManager status reporting and state management."""

    async def test_get_kiosk_status_when_running_then_complete_status(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test status reporting when kiosk is running."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Setup running state
        manager._start_time = datetime.now() - timedelta(minutes=30)
        manager._is_running = MagicMock(return_value=True)
        manager._get_daemon_status = MagicMock(
            return_value=DaemonStatus(pid=12345, port=8080, is_healthy=True)
        )

        # Mock browser status
        browser_status = BrowserStatus(
            state=BrowserState.RUNNING,
            pid=23456,
            start_time=datetime.now() - timedelta(minutes=25),
            uptime=timedelta(minutes=25),
            memory_usage_mb=75,
            cpu_usage_percent=8.2,
            crash_count=0,
            restart_count=0,
            last_restart_time=None,
            is_responsive=True,
            last_health_check=datetime.now(),
            last_error=None,
            error_time=None,
        )
        manager.browser_manager.get_browser_status = MagicMock(return_value=browser_status)

        # Mock system resource monitoring
        manager._get_system_memory_usage = MagicMock(return_value=280)
        manager._get_system_cpu_usage = MagicMock(return_value=18.5)

        status = manager.get_kiosk_status()

        assert isinstance(status, KioskStatus)
        assert status.is_running is True
        assert status.start_time is not None
        assert status.uptime is not None
        assert status.daemon_status is not None
        assert status.browser_status is not None
        assert status.memory_usage_mb == 280
        assert status.cpu_usage_percent == 18.5
        assert status.restart_count == 0
        assert status.last_error is None

    async def test_get_kiosk_status_when_error_then_error_captured(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
    ) -> None:
        """Test status reporting captures errors gracefully."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock error in status checking
        manager._is_running = MagicMock(side_effect=Exception("Status check failed"))

        status = manager.get_kiosk_status()

        assert isinstance(status, KioskStatus)
        assert status.is_running is False
        assert status.last_error == "Status check failed"
        assert status.error_time is not None


@pytest.mark.asyncio
class TestKioskManagerPiZero2WOptimization:
    """Test KioskManager Pi Zero 2W specific optimizations and constraints."""

    async def test_startup_sequence_when_pi_constraints_then_timing_appropriate(
        self,
        resource_constrained_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        performance_monitor,
        integration_test_base,
    ) -> None:
        """Test startup sequence respects Pi Zero 2W timing constraints."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=resource_constrained_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock phases with realistic Pi Zero 2W delays
        async def slow_web_server():
            await asyncio.sleep(0.1)  # Simulate slow startup
            return True

        async def slow_readiness(timeout: int = 30):
            await asyncio.sleep(0.2)  # Simulate readiness check
            return True

        async def slow_browser():
            await asyncio.sleep(0.3)  # Simulate browser startup
            return True

        manager._start_web_server = slow_web_server
        manager._wait_for_web_server_ready = slow_readiness
        manager._start_browser = slow_browser
        manager._start_health_monitoring = AsyncMock()

        # Validate Pi Zero 2W memory constraints
        integration_test_base.assert_pi_zero_2w_constraints(resource_constrained_settings)

        performance_monitor.start_timing("constrained_startup")

        result = await manager.start_kiosk()

        startup_duration = performance_monitor.end_timing("constrained_startup")

        assert result is True
        # Allow longer startup time for resource-constrained settings
        assert startup_duration < 5.0, (
            f"Startup took {startup_duration:.2f}s, too slow even for Pi Zero 2W"
        )

    async def test_memory_optimization_settings_applied(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        integration_test_base,
    ) -> None:
        """Test memory optimization settings are properly applied."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Validate memory constraints are enforced
        integration_test_base.assert_pi_zero_2w_constraints(pi_zero_2w_kiosk_settings)

        # Check browser configuration matches Pi Zero 2W optimization
        browser_config = manager.browser_manager.config
        assert browser_config.memory_limit_mb <= 120, "Browser memory limit too high for Pi Zero 2W"

        # Validate Pi-specific optimizations are enabled
        assert pi_zero_2w_kiosk_settings.pi_optimization.enable_memory_optimization is True
        assert pi_zero_2w_kiosk_settings.pi_optimization.swap_size_mb <= 256
        assert pi_zero_2w_kiosk_settings.pi_optimization.tmpfs_size_mb <= 64
