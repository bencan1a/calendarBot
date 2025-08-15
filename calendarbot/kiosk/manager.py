"""
Kiosk manager component - the central orchestrator for kiosk mode operations.

This module provides the central coordination for kiosk mode, integrating with existing
CalendarBot infrastructure (DaemonManager, SharedWebServer) while adding kiosk-specific
functionality for browser management, health monitoring, and system coordination.

Classes:
    KioskStatus: Comprehensive kiosk system status information
    KioskManager: Central coordinator for kiosk mode operations
    KioskError: Exception raised for kiosk-related errors

Example:
    >>> from calendarbot.config.settings import CalendarBotSettings
    >>> from calendarbot.settings.kiosk_models import KioskSettings
    >>>
    >>> settings = CalendarBotSettings()
    >>> kiosk_settings = KioskSettings(enabled=True)
    >>> manager = KioskManager(settings, kiosk_settings)
    >>>
    >>> success = await manager.start_kiosk()
    >>> if success:
    ...     status = manager.get_kiosk_status()
    ...     print(f"Kiosk running: {status.is_running}")
    >>> await manager.stop_kiosk()
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..cli.modes.shared_webserver import SharedWebServer

try:
    import aiohttp
    from aiohttp import ClientTimeout
except ImportError:
    aiohttp = None  # type: ignore
    ClientTimeout = None  # type: ignore

import contextlib

# Optional dependency - psutil for system metrics
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

from ..settings.kiosk_models import KioskSettings
from ..utils.daemon import DaemonManager, DaemonStatus
from .browser_manager import BrowserConfig, BrowserManager, BrowserStatus

logger = logging.getLogger(__name__)


@dataclass
class KioskStatus:
    """Comprehensive kiosk system status information.

    Provides detailed status tracking for all kiosk components including
    overall system state, component health, performance metrics, and error tracking.

    Attributes:
        is_running: Whether the kiosk system is currently running
        start_time: When the kiosk was started (None if not running)
        uptime: How long the kiosk has been running (None if not running)
        daemon_status: Status of the CalendarBot daemon (None if not running)
        browser_status: Status of the browser process (None if not running)
        memory_usage_mb: Current system memory usage in megabytes
        cpu_usage_percent: Current CPU usage as percentage
        restart_count: Total number of kiosk restarts since initialization
        last_error: Last error message (None if no errors)
        error_time: When the last error occurred (None if no errors)
    """

    # Overall status
    is_running: bool
    start_time: Optional[datetime]
    uptime: Optional[timedelta]

    # Component statuses
    daemon_status: Optional[DaemonStatus]
    browser_status: Optional[BrowserStatus]

    # System metrics
    memory_usage_mb: int
    cpu_usage_percent: float

    # Error tracking
    restart_count: int
    last_error: Optional[str]
    error_time: Optional[datetime]


class KioskError(Exception):
    """Exception raised for kiosk-related errors.

    Provides specific error handling for kiosk management operations
    including startup failures, component coordination issues, and system errors.

    Attributes:
        message: Error description
        component: Component where error occurred (optional)
        error_code: Error code for categorization (optional)
    """

    def __init__(
        self, message: str, component: Optional[str] = None, error_code: Optional[str] = None
    ) -> None:
        """Initialize kiosk error.

        Args:
            message: Error description
            component: Component where error occurred
            error_code: Error code for categorization
        """
        super().__init__(message)
        self.message = message
        self.component = component
        self.error_code = error_code


class KioskManager:
    """Central coordinator for kiosk mode operations.

    Integrates with existing CalendarBot infrastructure while adding
    kiosk-specific orchestration, browser management, and health monitoring.
    Provides reliable Pi Zero 2W kiosk operation with comprehensive error
    handling and recovery mechanisms.

    Features:
        - 4-phase startup orchestration workflow
        - Integration with existing DaemonManager and SharedWebServer
        - Browser lifecycle coordination using BrowserManager
        - System health monitoring with automatic recovery
        - Resource usage tracking and optimization
        - Comprehensive error handling and logging

    Example:
        >>> manager = KioskManager(settings, kiosk_settings)
        >>> success = await manager.start_kiosk()
        >>> if success:
        ...     try:
        ...         while True:
        ...             await asyncio.sleep(1)
        ...             status = manager.get_kiosk_status()
        ...             if not status.is_running:
        ...                 break
        ...     except KeyboardInterrupt:
        ...         pass
        >>> await manager.stop_kiosk()
    """

    def __init__(
        self,
        settings: Any,
        kiosk_settings: KioskSettings,
        daemon_manager: Optional[DaemonManager] = None,
    ) -> None:
        """Initialize KioskManager with existing infrastructure integration.

        Args:
            settings: Main CalendarBot settings instance
            kiosk_settings: Kiosk-specific settings configuration
            daemon_manager: Optional custom daemon manager (for testing)
        """
        self.settings = settings
        self.kiosk_settings = kiosk_settings
        self.logger = logging.getLogger(f"{__name__}.KioskManager")

        # Core components - integrate with existing infrastructure
        self.daemon_manager = daemon_manager or DaemonManager()

        # Create browser configuration from kiosk settings
        browser_config = self._create_browser_config()
        self.browser_manager = BrowserManager(browser_config)

        # Shared web server integration
        self.shared_webserver: Optional[SharedWebServer] = None

        # State tracking
        self._start_time: Optional[datetime] = None
        self._restart_count: int = 0
        self._last_error: Optional[str] = None
        self._error_time: Optional[datetime] = None

        # Control flags
        self._shutdown_requested: bool = False
        self._monitoring_task: Optional[asyncio.Task] = None

        self.logger.info("KioskManager initialized successfully")

    async def start_kiosk(self) -> bool:
        """Start complete kiosk system with proper startup orchestration.

        Implements the 4-phase startup workflow:
        1. Start web server using existing daemon infrastructure
        2. Wait for web server to be ready
        3. Start browser pointing to web server
        4. Start health monitoring

        Returns:
            True if kiosk started successfully, False otherwise

        Raises:
            KioskError: If critical startup failure occurs
        """

        async def _start_with_validation() -> None:
            """Inner function to handle startup with proper error raising."""
            self.logger.info("Starting CalendarBot kiosk mode")
            self._start_time = datetime.now()

            # Phase 1: Start web server using existing daemon infrastructure
            if not await self._start_web_server():
                raise KioskError("Failed to start web server", "web_server", "STARTUP_FAILED")

            # Wait for web server to be ready
            if not await self._wait_for_web_server_ready():
                raise KioskError("Web server failed to become ready", "web_server", "READY_TIMEOUT")

            # Phase 3: Start browser pointing to web server
            if not await self._start_browser():
                raise KioskError("Failed to start browser", "browser", "STARTUP_FAILED")

            # Phase 4: Start health monitoring
            await self._start_health_monitoring()

            self.logger.info("Kiosk mode started successfully")

        try:
            await _start_with_validation()
            return True

        except Exception as e:
            self._last_error = str(e)
            self._error_time = datetime.now()
            self.logger.exception("Failed to start kiosk")

            # Cleanup on failure
            await self._cleanup_on_failure()
            return False

    async def stop_kiosk(self, timeout: int = 30) -> bool:
        """Gracefully stop kiosk system with proper cleanup.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown

        Returns:
            True if shutdown completed successfully, False otherwise
        """
        try:
            self.logger.info("Stopping CalendarBot kiosk mode")
            self._shutdown_requested = True

            # Phase 1: Stop health monitoring
            await self._stop_health_monitoring()

            # Phase 2: Stop browser gracefully
            if not await self.browser_manager.stop_browser(timeout=10):
                self.logger.warning("Browser did not stop gracefully, forcing shutdown")

            # Phase 3: Stop web server using daemon manager
            if not await self._stop_web_server(timeout=timeout - 10):
                self.logger.warning("Web server did not stop gracefully")

            self.logger.info("Kiosk mode stopped successfully")
            return True

        except Exception:
            self.logger.exception("Error during kiosk shutdown")
            return False

    def get_kiosk_status(self) -> KioskStatus:
        """Get comprehensive kiosk system status.

        Returns:
            Current kiosk status including all component states
        """
        try:
            # Get component statuses
            daemon_status = self._get_daemon_status()
            browser_status = self.browser_manager.get_browser_status()

            # Calculate uptime
            uptime = None
            if self._start_time:
                uptime = datetime.now() - self._start_time

            # Get system metrics (simplified for now)
            memory_usage = self._get_system_memory_usage()
            cpu_usage = self._get_system_cpu_usage()

            return KioskStatus(
                is_running=self._is_running(),
                start_time=self._start_time,
                uptime=uptime,
                daemon_status=daemon_status,
                browser_status=browser_status,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                restart_count=self._restart_count,
                last_error=self._last_error,
                error_time=self._error_time,
            )

        except Exception as e:
            self.logger.exception("Error getting kiosk status")
            return KioskStatus(
                is_running=False,
                start_time=None,
                uptime=None,
                daemon_status=None,
                browser_status=None,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
                restart_count=self._restart_count,
                last_error=str(e),
                error_time=datetime.now(),
            )

    async def restart_kiosk(self) -> bool:
        """Restart entire kiosk system.

        Returns:
            True if restart successful, False otherwise
        """
        try:
            self.logger.info("Restarting kiosk system")
            self._restart_count += 1

            # Stop first
            await self.stop_kiosk(timeout=15)

            # Brief pause to ensure cleanup
            await asyncio.sleep(2)

            # Start again
            return await self.start_kiosk()

        except Exception:
            self.logger.exception("Error during kiosk restart")
            return False

    def _create_browser_config(self) -> BrowserConfig:
        """Create browser configuration from kiosk settings.

        Returns:
            BrowserConfig instance configured for Pi Zero 2W
        """
        browser_settings = self.kiosk_settings.browser
        display_settings = self.kiosk_settings.display

        return BrowserConfig(
            executable_path=browser_settings.executable_path,
            startup_delay=browser_settings.startup_delay,
            startup_timeout=browser_settings.startup_timeout,
            shutdown_timeout=browser_settings.shutdown_timeout,
            crash_restart_delay=browser_settings.crash_restart_delay,
            max_restart_attempts=browser_settings.max_restart_attempts,
            restart_backoff_factor=browser_settings.restart_backoff_factor,
            reset_attempts_after=browser_settings.reset_attempts_after,
            health_check_interval=browser_settings.health_check_interval,
            response_timeout=browser_settings.response_timeout,
            memory_limit_mb=browser_settings.memory_limit_mb,
            memory_warning_threshold=browser_settings.memory_warning_threshold,
            memory_critical_threshold=browser_settings.memory_critical_threshold,
            cache_clear_on_restart=browser_settings.cache_clear_on_restart,
            window_width=display_settings.width,
            window_height=display_settings.height,
            scale_factor=display_settings.scale_factor,
            disable_infobars=True,
            disable_session_restore=True,
            disable_first_run=True,
        )

    async def _start_web_server(self) -> bool:
        """Start CalendarBot web server using existing daemon infrastructure."""
        try:
            self.logger.info("Starting CalendarBot web server")

            # Check if daemon is already running
            if self.daemon_manager.is_daemon_running():
                existing_pid = self.daemon_manager.get_daemon_pid()
                self.logger.info(f"Using existing CalendarBot daemon (PID {existing_pid})")
                return True

            # Initialize CalendarBot application components
            app = await self._initialize_calendarbot_app()

            # Lazy import to avoid circular dependency
            from ..cli.modes.shared_webserver import SharedWebServer  # noqa

            self.shared_webserver = SharedWebServer(
                settings=self.settings,
                display_manager=app.display_manager,
                cache_manager=app.cache_manager,
            )

            # Start the web server
            success = self.shared_webserver.start()
            if success:
                # Create PID file for daemon tracking
                self.daemon_manager.create_pid_file()
                port = getattr(self.settings, "web_port", 8080)
                self.logger.info(f"Web server started on port {port}")

            return success

        except Exception:
            self.logger.exception("Failed to start web server")
            return False

    async def _wait_for_web_server_ready(self, timeout: int = 30) -> bool:
        """Wait for web server to be ready to serve requests."""
        if not aiohttp:
            self.logger.warning("aiohttp not available, skipping web server readiness check")
            await asyncio.sleep(5)  # Simple delay fallback
            return True

        port = getattr(self.settings, "web_port", 8080)
        layout = self.kiosk_settings.target_layout
        url = f"http://localhost:{port}/{layout}"

        for _attempt in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    timeout_obj = ClientTimeout(total=1) if ClientTimeout else None
                    async with session.get(url, timeout=timeout_obj) as response:
                        if response.status == 200:
                            self.logger.info("Web server is ready")
                            return True

            except Exception:
                pass  # Expected during startup

            await asyncio.sleep(1)

        self.logger.error("Web server failed to become ready within timeout")
        return False

    async def _start_browser(self) -> bool:
        """Start browser pointing to local web server."""
        try:
            port = getattr(self.settings, "web_port", 8080)
            layout = self.kiosk_settings.target_layout
            url = f"http://localhost:{port}/{layout}"

            return await self.browser_manager.start_browser(url)

        except Exception:
            self.logger.exception("Failed to start browser")
            return False

    async def _start_health_monitoring(self) -> None:
        """Start health monitoring task."""
        try:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Health monitoring started")

        except Exception:
            self.logger.exception("Failed to start health monitoring")

    async def _monitoring_loop(self) -> None:
        """Main health monitoring loop with automatic recovery."""
        interval = self.kiosk_settings.monitoring.health_check_interval

        while not self._shutdown_requested:
            try:
                # Check component health
                browser_healthy = self.browser_manager.is_browser_healthy()
                web_server_healthy = await self._check_web_server_health()

                # Handle browser failures
                if not browser_healthy:
                    self.logger.warning("Browser unhealthy, attempting restart")
                    await self.browser_manager.restart_browser()

                # Handle web server failures
                if not web_server_healthy:
                    self.logger.warning("Web server unhealthy, attempting restart")
                    await self._restart_web_server()

            except Exception:
                self.logger.exception("Error in monitoring loop")

            await asyncio.sleep(interval)

    async def _check_web_server_health(self) -> bool:
        """Check if web server is responding properly."""
        if not aiohttp:
            # Fallback: just check if daemon is running
            return self.daemon_manager.is_daemon_running()

        try:
            port = getattr(self.settings, "web_port", 8080)
            layout = self.kiosk_settings.target_layout
            url = f"http://localhost:{port}/{layout}"

            async with aiohttp.ClientSession() as session:
                timeout_obj = ClientTimeout(total=5) if ClientTimeout else None
                async with session.get(url, timeout=timeout_obj) as response:
                    return response.status == 200

        except Exception:
            return False

    def _get_daemon_status(self) -> Optional[DaemonStatus]:
        """Get daemon status using existing DaemonManager."""
        try:
            if self.daemon_manager.is_daemon_running():
                pid = self.daemon_manager.get_daemon_pid()
                if pid is not None:
                    port = getattr(self.settings, "web_port", 8080)
                    return DaemonStatus(
                        pid=pid,
                        port=port,
                        is_healthy=True,  # Simplified for now
                    )
            return None

        except Exception:
            self.logger.exception("Error getting daemon status")
            return None

    def _is_running(self) -> bool:
        """Check if kiosk system is running."""
        return (
            self._start_time is not None
            and not self._shutdown_requested
            and self.daemon_manager.is_daemon_running()
        )

    async def _initialize_calendarbot_app(self) -> Any:
        """Initialize CalendarBot application components."""
        # Import here to avoid circular imports
        from ..main import CalendarBot  # noqa

        app = CalendarBot()
        app.settings = self.settings
        await app.initialize()
        return app

    async def _stop_web_server(self, timeout: int = 20) -> bool:
        """Stop web server using existing daemon infrastructure."""
        try:
            if self.shared_webserver:
                success = self.shared_webserver.stop()
                if not success:
                    self.logger.warning("SharedWebServer stop() returned False")

            # Clean up daemon tracking
            self.daemon_manager.cleanup_pid_file()
            return True

        except Exception:
            self.logger.exception("Error stopping web server")
            return False

    async def _stop_health_monitoring(self) -> None:
        """Stop health monitoring task."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task

    async def _cleanup_on_failure(self) -> None:
        """Clean up resources after startup failure."""
        try:
            await self.browser_manager.stop_browser()
            await self._stop_web_server()
            await self._stop_health_monitoring()

        except Exception:
            self.logger.exception("Error during cleanup")

    async def _restart_web_server(self) -> bool:
        """Restart web server component."""
        try:
            await self._stop_web_server()
            await asyncio.sleep(2)
            return await self._start_web_server()

        except Exception:
            self.logger.exception("Error restarting web server")
            return False

    def _get_system_memory_usage(self) -> int:
        """Get system memory usage in MB.

        Returns:
            Memory usage in megabytes, 0 if unable to determine
        """
        try:
            if psutil is None:
                return 0
            memory = psutil.virtual_memory()
            return int(memory.used / 1024 / 1024)  # Convert to MB
        except Exception:
            return 0

    def _get_system_cpu_usage(self) -> float:
        """Get system CPU usage percentage.

        Returns:
            CPU usage as percentage, 0.0 if unable to determine
        """
        try:
            if psutil is None:
                return 0.0
            return psutil.cpu_percent()
        except Exception:
            return 0.0
