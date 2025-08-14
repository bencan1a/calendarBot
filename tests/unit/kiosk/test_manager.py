"""Unit tests for kiosk manager component."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.kiosk.browser_manager import BrowserState, BrowserStatus
from calendarbot.kiosk.manager import KioskError, KioskManager, KioskStatus
from calendarbot.settings.kiosk_models import KioskSettings
from calendarbot.utils.daemon import DaemonStatus


class TestKioskManager:
    """Test cases for KioskManager class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock CalendarBot settings."""
        settings = Mock()
        settings.web_port = 8080
        settings.web_host = "127.0.0.1"
        return settings

    @pytest.fixture
    def kiosk_settings(self):
        """Create kiosk settings for testing."""
        return KioskSettings(enabled=True, target_layout="whats-next-view")

    @pytest.fixture
    def mock_daemon_manager(self):
        """Create mock daemon manager."""
        daemon = Mock()
        daemon.is_daemon_running.return_value = False
        daemon.get_daemon_pid.return_value = None
        daemon.create_pid_file.return_value = 12345
        daemon.cleanup_pid_file.return_value = True
        return daemon

    @pytest.fixture
    def manager(self, mock_settings, kiosk_settings, mock_daemon_manager):
        """Create KioskManager instance for testing."""
        with patch("calendarbot.kiosk.manager.BrowserManager") as mock_browser_class:
            mock_browser = Mock()
            mock_browser_class.return_value = mock_browser

            manager = KioskManager(
                settings=mock_settings,
                kiosk_settings=kiosk_settings,
                daemon_manager=mock_daemon_manager,
            )
            manager.browser_manager = mock_browser
            return manager

    def test_init_creates_browser_config_correctly(
        self, mock_settings, kiosk_settings, mock_daemon_manager
    ):
        """Test KioskManager initialization creates correct browser config."""
        with patch("calendarbot.kiosk.manager.BrowserManager") as mock_browser_class:
            mock_browser = Mock()
            mock_browser_class.return_value = mock_browser

            KioskManager(
                settings=mock_settings,
                kiosk_settings=kiosk_settings,
                daemon_manager=mock_daemon_manager,
            )

            # Verify browser manager was created with correct config
            mock_browser_class.assert_called_once()
            config = mock_browser_class.call_args[0][0]

            assert config.memory_limit_mb == kiosk_settings.browser.memory_limit_mb
            assert config.window_width == kiosk_settings.display.width
            assert config.window_height == kiosk_settings.display.height

    @pytest.mark.asyncio
    async def test_start_kiosk_success_four_phases(self, manager):
        """Test successful kiosk startup through all four phases."""
        # Mock all dependencies
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=True)
        manager._start_browser = AsyncMock(return_value=True)
        manager._start_health_monitoring = AsyncMock()

        result = await manager.start_kiosk()

        assert result is True
        assert manager._start_time is not None

        # Verify all phases were called in order
        manager._start_web_server.assert_called_once()
        manager._wait_for_web_server_ready.assert_called_once()
        manager._start_browser.assert_called_once()
        manager._start_health_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_kiosk_failure_web_server(self, manager):
        """Test kiosk startup failure at web server phase."""
        manager._start_web_server = AsyncMock(return_value=False)
        manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        assert result is False
        assert manager._last_error is not None
        manager._cleanup_on_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_kiosk_failure_web_server_ready(self, manager):
        """Test kiosk startup failure at web server ready phase."""
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=False)
        manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        assert result is False
        assert manager._last_error is not None
        manager._cleanup_on_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_kiosk_failure_browser(self, manager):
        """Test kiosk startup failure at browser phase."""
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=True)
        manager._start_browser = AsyncMock(return_value=False)
        manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        assert result is False
        assert manager._last_error is not None
        manager._cleanup_on_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_kiosk_success(self, manager):
        """Test successful kiosk shutdown."""
        manager._shutdown_requested = False
        manager._stop_health_monitoring = AsyncMock()
        manager.browser_manager.stop_browser = AsyncMock(return_value=True)
        manager._stop_web_server = AsyncMock(return_value=True)

        result = await manager.stop_kiosk()

        assert result is True
        assert manager._shutdown_requested is True
        manager._stop_health_monitoring.assert_called_once()
        manager.browser_manager.stop_browser.assert_called_once_with(timeout=10)
        manager._stop_web_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_kiosk_browser_timeout(self, manager):
        """Test kiosk shutdown when browser doesn't stop gracefully."""
        manager._stop_health_monitoring = AsyncMock()
        manager.browser_manager.stop_browser = AsyncMock(return_value=False)
        manager._stop_web_server = AsyncMock(return_value=True)

        result = await manager.stop_kiosk()

        assert result is True  # Should still succeed even if browser doesn't stop gracefully

    @pytest.mark.asyncio
    async def test_restart_kiosk_success(self, manager):
        """Test successful kiosk restart."""
        manager.stop_kiosk = AsyncMock(return_value=True)
        manager.start_kiosk = AsyncMock(return_value=True)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await manager.restart_kiosk()

        assert result is True
        assert manager._restart_count == 1
        manager.stop_kiosk.assert_called_once_with(timeout=15)
        manager.start_kiosk.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_kiosk_failure(self, manager):
        """Test kiosk restart failure."""
        manager.stop_kiosk = AsyncMock(return_value=True)
        manager.start_kiosk = AsyncMock(return_value=False)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await manager.restart_kiosk()

        assert result is False
        assert manager._restart_count == 1

    def test_get_kiosk_status_running(self, manager):
        """Test getting kiosk status when running."""
        manager._start_time = datetime.now() - timedelta(minutes=5)
        manager._is_running = Mock(return_value=True)
        manager._get_daemon_status = Mock(
            return_value=DaemonStatus(pid=12345, port=8080, is_healthy=True)
        )
        manager.browser_manager.get_browser_status = Mock(
            return_value=BrowserStatus(
                state=BrowserState.RUNNING,
                pid=23456,
                start_time=datetime.now(),
                uptime=timedelta(minutes=3),
                memory_usage_mb=80,
                cpu_usage_percent=15.0,
                crash_count=0,
                restart_count=0,
                last_restart_time=None,
                is_responsive=True,
                last_health_check=datetime.now(),
                last_error=None,
                error_time=None,
            )
        )
        manager._get_system_memory_usage = Mock(return_value=300)
        manager._get_system_cpu_usage = Mock(return_value=25.0)

        status = manager.get_kiosk_status()

        assert isinstance(status, KioskStatus)
        assert status.is_running is True
        assert status.start_time is not None
        assert status.uptime is not None
        assert status.daemon_status is not None
        assert status.browser_status is not None
        assert status.memory_usage_mb == 300
        assert status.cpu_usage_percent == 25.0

    def test_get_kiosk_status_error_handling(self, manager):
        """Test kiosk status error handling."""
        manager._is_running = Mock(side_effect=Exception("Test error"))

        status = manager.get_kiosk_status()

        assert isinstance(status, KioskStatus)
        assert status.is_running is False
        assert status.last_error == "Test error"
        assert status.error_time is not None

    @pytest.mark.asyncio
    async def test_start_web_server_existing_daemon(self, manager):
        """Test starting web server with existing daemon."""
        manager.daemon_manager.is_daemon_running.return_value = True
        manager.daemon_manager.get_daemon_pid.return_value = 12345

        result = await manager._start_web_server()

        assert result is True
        manager.daemon_manager.is_daemon_running.assert_called_once()
        manager.daemon_manager.get_daemon_pid.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_web_server_new_daemon(self, manager):
        """Test starting new web server daemon."""
        manager.daemon_manager.is_daemon_running.return_value = False
        manager._initialize_calendarbot_app = AsyncMock()

        mock_app = Mock()
        mock_app.display_manager = Mock()
        mock_app.cache_manager = Mock()
        manager._initialize_calendarbot_app.return_value = mock_app

        with patch(
            "calendarbot.cli.modes.shared_webserver.SharedWebServer"
        ) as mock_shared_server_class:
            mock_shared_server = Mock()
            mock_shared_server.start.return_value = True
            mock_shared_server_class.return_value = mock_shared_server

            result = await manager._start_web_server()

        assert result is True
        manager._initialize_calendarbot_app.assert_called_once()
        manager.daemon_manager.create_pid_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_web_server_ready_no_aiohttp(self, manager):
        """Test waiting for web server ready when aiohttp not available."""
        with patch("calendarbot.kiosk.manager.aiohttp", None):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await manager._wait_for_web_server_ready()

        assert result is True  # Should return True with fallback

    @pytest.mark.asyncio
    async def test_wait_for_web_server_ready_timeout(self, manager):
        """Test web server ready check timeout."""
        with patch("calendarbot.kiosk.manager.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await manager._wait_for_web_server_ready(timeout=1)

        assert result is False

    @pytest.mark.asyncio
    async def test_start_browser_success(self, manager):
        """Test successful browser startup."""
        manager.browser_manager.start_browser = AsyncMock(return_value=True)

        result = await manager._start_browser()

        assert result is True
        expected_url = (
            f"http://localhost:{manager.settings.web_port}/{manager.kiosk_settings.target_layout}"
        )
        manager.browser_manager.start_browser.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_start_browser_failure(self, manager):
        """Test browser startup failure."""
        manager.browser_manager.start_browser = AsyncMock(side_effect=Exception("Browser failed"))

        result = await manager._start_browser()

        assert result is False

    @pytest.mark.asyncio
    async def test_monitoring_loop_browser_unhealthy(self, manager):
        """Test monitoring loop handling unhealthy browser."""
        manager.browser_manager.is_browser_healthy.return_value = False
        manager.browser_manager.restart_browser = AsyncMock()
        manager._check_web_server_health = AsyncMock(return_value=True)

        # Set up to run only one iteration
        iteration_count = 0

        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 1:
                manager._shutdown_requested = True

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await manager._monitoring_loop()

        manager.browser_manager.restart_browser.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitoring_loop_web_server_unhealthy(self, manager):
        """Test monitoring loop handling unhealthy web server."""
        manager.browser_manager.is_browser_healthy.return_value = True
        manager._check_web_server_health = AsyncMock(return_value=False)
        manager._restart_web_server = AsyncMock()

        # Set up to run only one iteration
        iteration_count = 0

        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 1:
                manager._shutdown_requested = True

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await manager._monitoring_loop()

        manager._restart_web_server.assert_called_once()

    def test_is_running_true(self, manager):
        """Test _is_running returns True when conditions met."""
        manager._start_time = datetime.now()
        manager._shutdown_requested = False
        manager.daemon_manager.is_daemon_running.return_value = True

        result = manager._is_running()

        assert result is True

    def test_is_running_false_no_start_time(self, manager):
        """Test _is_running returns False when not started."""
        manager._start_time = None
        manager._shutdown_requested = False
        manager.daemon_manager.is_daemon_running.return_value = True

        result = manager._is_running()

        assert result is False

    def test_is_running_false_shutdown_requested(self, manager):
        """Test _is_running returns False when shutdown requested."""
        manager._start_time = datetime.now()
        manager._shutdown_requested = True
        manager.daemon_manager.is_daemon_running.return_value = True

        result = manager._is_running()

        assert result is False

    def test_is_running_false_daemon_not_running(self, manager):
        """Test _is_running returns False when daemon not running."""
        manager._start_time = datetime.now()
        manager._shutdown_requested = False
        manager.daemon_manager.is_daemon_running.return_value = False

        result = manager._is_running()

        assert result is False

    def test_get_daemon_status_running(self, manager):
        """Test getting daemon status when running."""
        manager.daemon_manager.is_daemon_running.return_value = True
        manager.daemon_manager.get_daemon_pid.return_value = 12345

        status = manager._get_daemon_status()

        assert status is not None
        assert status.pid == 12345
        assert status.port == 8080
        assert status.is_healthy is True

    def test_get_daemon_status_not_running(self, manager):
        """Test getting daemon status when not running."""
        manager.daemon_manager.is_daemon_running.return_value = False

        status = manager._get_daemon_status()

        assert status is None

    def test_get_daemon_status_no_pid(self, manager):
        """Test getting daemon status when PID is None."""
        manager.daemon_manager.is_daemon_running.return_value = True
        manager.daemon_manager.get_daemon_pid.return_value = None

        status = manager._get_daemon_status()

        assert status is None

    def test_get_system_memory_usage_with_psutil(self, manager):
        """Test getting system memory usage with psutil available."""
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value.used = 200 * 1024 * 1024  # 200MB in bytes

            result = manager._get_system_memory_usage()

            assert result == 200

    def test_get_system_memory_usage_without_psutil(self, manager):
        """Test getting system memory usage without psutil."""
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args: ImportError()
            if name == "psutil"
            else __import__(name, *args),
        ):
            result = manager._get_system_memory_usage()

            assert result == 0

    def test_get_system_cpu_usage_with_psutil(self, manager):
        """Test getting system CPU usage with psutil available."""
        with patch("psutil.cpu_percent") as mock_cpu:
            mock_cpu.return_value = 25.5

            result = manager._get_system_cpu_usage()

            assert result == 25.5

    def test_get_system_cpu_usage_without_psutil(self, manager):
        """Test getting system CPU usage without psutil."""
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args: ImportError()
            if name == "psutil"
            else __import__(name, *args),
        ):
            result = manager._get_system_cpu_usage()

            assert result == 0.0

    def test_kiosk_error_init(self):
        """Test KioskError initialization."""
        error = KioskError("Test error", "test_component", "TEST_CODE")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.component == "test_component"
        assert error.error_code == "TEST_CODE"

    def test_kiosk_error_minimal_init(self):
        """Test KioskError initialization with minimal parameters."""
        error = KioskError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.component is None
        assert error.error_code is None
