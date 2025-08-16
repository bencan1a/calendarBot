"""
Browser manager component for kiosk mode with Chromium process lifecycle management.

This module provides robust browser process management optimized for Raspberry Pi Zero 2W
constraints, including memory optimization, crash detection, and automatic recovery
mechanisms for reliable kiosk operation.

Classes:
    BrowserState: Browser process state enumeration
    BrowserStatus: Browser health and status information
    BrowserConfig: Browser configuration optimized for Pi Zero 2W
    BrowserManager: Core browser process management
    BrowserError: Exception for browser-related errors

Example:
    >>> config = BrowserConfig(memory_limit_mb=80)
    >>> manager = BrowserManager(config)
    >>> success = await manager.start_browser("http://localhost:8080/whats-next-view")
    >>> status = manager.get_browser_status()
    >>> print(f"Browser state: {status.state}, Memory: {status.memory_usage_mb}MB")
    >>> await manager.stop_browser()
"""

import asyncio
import contextlib
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

logger = logging.getLogger(__name__)


class BrowserState(Enum):
    """Browser process states for lifecycle management.

    Attributes:
        STOPPED: Browser is not running
        STARTING: Browser is in the process of starting up
        RUNNING: Browser is running and operational
        CRASHED: Browser process has crashed unexpectedly
        RESTARTING: Browser is being restarted after a crash
        FAILED: Browser has failed permanently after max restart attempts
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    FAILED = "failed"


@dataclass
class BrowserStatus:
    """Browser health and status information for monitoring.

    Provides comprehensive status tracking including process information,
    performance metrics, reliability metrics, and error tracking.

    Attributes:
        state: Current browser state
        pid: Process ID of browser (None if not running)
        start_time: When browser was started (None if not running)
        uptime: How long browser has been running (None if not running)
        memory_usage_mb: Current memory usage in megabytes
        cpu_usage_percent: Current CPU usage percentage
        crash_count: Total number of crashes since start
        restart_count: Total number of restarts since start
        last_restart_time: When browser was last restarted (None if never)
        is_responsive: Whether browser is currently responsive
        last_health_check: When last health check was performed (None if never)
        last_error: Last error message (None if no errors)
        error_time: When last error occurred (None if no errors)
    """

    state: BrowserState
    pid: Optional[int]
    start_time: Optional[datetime]
    uptime: Optional[timedelta]

    # Performance metrics
    memory_usage_mb: int
    cpu_usage_percent: float

    # Reliability metrics
    crash_count: int
    restart_count: int
    last_restart_time: Optional[datetime]

    # Health indicators
    is_responsive: bool
    last_health_check: Optional[datetime]

    # Error tracking
    last_error: Optional[str]
    error_time: Optional[datetime]


@dataclass
class BrowserConfig:
    """Browser configuration optimized for Pi Zero 2W memory constraints.

    Provides comprehensive configuration for browser process management,
    memory optimization, crash recovery, and health monitoring specifically
    tuned for 512MB RAM constraints.

    Attributes:
        executable_path: Path to Chromium executable
        startup_delay: Delay in seconds before starting browser
        startup_timeout: Maximum seconds to wait for browser startup
        shutdown_timeout: Maximum seconds to wait for graceful shutdown
        crash_restart_delay: Initial delay in seconds before restarting crashed browser
        max_restart_attempts: Maximum restart attempts per hour
        restart_backoff_factor: Exponential backoff factor for restart delays
        reset_attempts_after: Reset restart attempt counter after this time (seconds)
        health_check_interval: Health check interval in seconds
        response_timeout: Timeout for health check responses in seconds
        memory_check_interval: Memory usage check interval in seconds
        memory_limit_mb: Maximum memory usage before restart (MB)
        memory_warning_threshold: Memory usage percentage to trigger warning
        memory_critical_threshold: Memory usage percentage to trigger restart
        cache_clear_on_restart: Clear browser cache when restarting
        window_width: Browser window width in pixels
        window_height: Browser window height in pixels
        scale_factor: Display scaling factor
        disable_infobars: Disable browser information bars
        disable_session_restore: Disable session restore functionality
        disable_first_run: Disable first-run setup
    """

    # Process management
    executable_path: str = "chromium-browser"
    startup_delay: int = 5
    startup_timeout: int = 30
    shutdown_timeout: int = 10

    # Restart behavior
    crash_restart_delay: int = 3
    max_restart_attempts: int = 5
    restart_backoff_factor: float = 1.5
    reset_attempts_after: int = 3600  # seconds

    # Health monitoring
    health_check_interval: int = 30
    response_timeout: int = 5
    memory_check_interval: int = 60

    # Memory management (optimized for Pi Zero 2W)
    memory_limit_mb: int = 80  # Updated from spec's 128MB to match kiosk settings
    memory_warning_threshold: float = 0.85
    memory_critical_threshold: float = 0.95
    cache_clear_on_restart: bool = True

    # Display settings
    window_width: int = 480
    window_height: int = 800
    scale_factor: float = 1.0

    # Kiosk behavior
    disable_infobars: bool = True
    disable_session_restore: bool = True
    disable_first_run: bool = True


class BrowserError(Exception):
    """Exception raised for browser-related errors.

    Provides specific error handling for browser management operations
    including startup failures, crash detection, and configuration errors.

    Attributes:
        message: Error description
        error_code: Optional error code for categorization
        browser_state: Browser state when error occurred
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        browser_state: Optional[BrowserState] = None,
    ) -> None:
        """Initialize browser error.

        Args:
            message: Error description
            error_code: Optional error code for categorization
            browser_state: Browser state when error occurred
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.browser_state = browser_state


class BrowserManager:
    """Chromium browser process management for Pi Zero 2W kiosk mode.

    Provides robust browser lifecycle management with crash recovery,
    memory optimization, and health monitoring specifically tuned for
    512MB RAM constraints.

    Features:
        - Process lifecycle management (start, stop, restart)
        - Memory usage monitoring and enforcement
        - Crash detection and automatic recovery
        - Health monitoring with configurable intervals
        - Pi Zero 2W optimized Chromium flags
        - Exponential backoff for restart attempts
        - Resource usage tracking

    Example:
        >>> config = BrowserConfig(memory_limit_mb=80)
        >>> manager = BrowserManager(config)
        >>> success = await manager.start_browser("http://localhost:8080")
        >>> if success:
        ...     status = manager.get_browser_status()
        ...     print(f"Browser PID: {status.pid}, Memory: {status.memory_usage_mb}MB")
        >>> await manager.stop_browser()
    """

    def __init__(self, config: BrowserConfig) -> None:
        """Initialize BrowserManager with Pi Zero 2W optimized configuration.

        Args:
            config: Browser configuration settings optimized for Pi Zero 2W
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.BrowserManager")

        # Process management
        self._process: Optional[subprocess.Popen] = None
        self._state = BrowserState.STOPPED
        self._current_url: Optional[str] = None

        # Timing and metrics
        self._start_time: Optional[datetime] = None
        self._crash_count = 0
        self._restart_count = 0
        self._restart_attempts = 0
        self._last_restart_time: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None

        # Error tracking
        self._last_error: Optional[str] = None
        self._error_time: Optional[datetime] = None

        # Control flags
        self._shutdown_requested = False

        # Background tasks
        self._health_task: Optional[asyncio.Task] = None
        self._memory_task: Optional[asyncio.Task] = None

        # Fire-and-forget task tracking (prevents garbage collection)
        self._background_tasks: set[asyncio.Task] = set()

    async def start_browser(self, url: str) -> bool:
        """Start Chromium browser in kiosk mode.

        Launches browser with Pi Zero 2W optimized flags, applies startup delay,
        and waits for browser to become responsive. Includes comprehensive error
        handling and state management.

        Args:
            url: URL to load (typically http://localhost:8080/whats-next-view)

        Returns:
            True if browser started successfully, False otherwise

        Raises:
            BrowserError: If browser fails to start due to configuration or system errors
        """
        if not url or not url.strip():
            raise BrowserError("URL cannot be empty", "INVALID_URL", self._state)

        try:
            if self._state != BrowserState.STOPPED:
                self.logger.warning(f"Browser already in state {self._state}, stopping first")
                await self.stop_browser()

            self.logger.info(f"Starting Chromium browser for URL: {url}")
            self._state = BrowserState.STARTING
            self._current_url = url
            self._shutdown_requested = False

            # Apply startup delay for Pi Zero 2W stability
            if self.config.startup_delay > 0:
                self.logger.info(f"Applying startup delay: {self.config.startup_delay}s")
                await asyncio.sleep(self.config.startup_delay)

            # Build optimized command line arguments
            cmd_args = self._build_chromium_args(url)

            # Start browser process
            self._process = await self._launch_process(cmd_args)

            if self._process:
                self._start_time = datetime.now()
                self._state = BrowserState.RUNNING

                # Start background monitoring
                await self._start_monitoring()

                # Wait for browser to be responsive
                if await self._wait_for_responsive(timeout=self.config.startup_timeout):
                    self.logger.info(f"Browser started successfully (PID: {self._process.pid})")
                    return True
                await self._handle_startup_failure("Browser failed to become responsive")
                return False
            await self._handle_startup_failure("Failed to launch browser process")
            return False

        except Exception as e:
            await self._handle_startup_failure(f"Browser startup error: {e}")
            return False

    async def stop_browser(self, timeout: Optional[int] = None) -> bool:
        """Stop browser gracefully with configurable timeout.

        Attempts graceful shutdown first, then forces termination if needed.
        Cleans up monitoring tasks and process state.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown (uses config default if None)

        Returns:
            True if browser stopped successfully, False otherwise
        """
        if timeout is None:
            timeout = self.config.shutdown_timeout

        try:
            self.logger.info("Stopping Chromium browser")
            self._shutdown_requested = True

            # Stop monitoring tasks first
            await self._stop_monitoring()

            if not self._process:
                self._state = BrowserState.STOPPED
                return True

            # Try graceful shutdown first
            try:
                self._process.terminate()
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process_exit()), timeout=timeout
                )
                self.logger.info("Browser stopped gracefully")

            except TimeoutError:
                # Force kill if graceful shutdown fails
                self.logger.warning("Browser did not stop gracefully, forcing shutdown")
                self._process.kill()
                await asyncio.sleep(1)

            self._cleanup_process_state()
            return True

        except Exception:
            self.logger.exception("Error stopping browser")
            self._cleanup_process_state()
            return False

    async def restart_browser(self) -> bool:
        """Restart browser with exponential backoff and attempt limiting.

        Implements sophisticated restart logic with exponential backoff,
        attempt limiting, and state management for reliable recovery.

        Returns:
            True if restart successful, False otherwise
        """
        try:
            self._restart_count += 1
            self._restart_attempts += 1
            self._last_restart_time = datetime.now()

            self.logger.info(f"Restarting browser (attempt {self._restart_attempts})")

            # Check restart attempt limits
            if self._restart_attempts > self.config.max_restart_attempts:
                self.logger.error("Maximum restart attempts exceeded")
                self._state = BrowserState.FAILED
                return False

            # Stop current browser
            await self.stop_browser()

            # Apply exponential backoff delay
            delay = self._calculate_restart_delay()
            if delay > 0:
                self.logger.info(f"Applying restart delay: {delay}s")
                await asyncio.sleep(delay)

            # Start browser again
            if self._current_url:
                return await self.start_browser(self._current_url)
            self.logger.error("No URL available for restart")
            return False

        except Exception:
            self.logger.exception("Error during browser restart")
            self._state = BrowserState.FAILED
            return False

    def is_browser_healthy(self) -> bool:
        """Check if browser is running and responsive.

        Performs comprehensive health check including process status,
        memory usage validation, and basic responsiveness verification.

        Returns:
            True if browser is healthy, False otherwise
        """
        try:
            if self._state != BrowserState.RUNNING or not self._process:
                return False

            # Check if process is still alive
            if self._process.poll() is not None:
                self.logger.warning("Browser process has exited")
                self._state = BrowserState.CRASHED
                self._crash_count += 1
                return False

            # Check memory usage
            memory_usage = self._get_memory_usage()
            if memory_usage > self.config.memory_limit_mb:
                self.logger.warning(f"Browser memory usage too high: {memory_usage}MB")
                return False

            # TODO: Add more sophisticated health checks in future
            # - HTTP request to check if page is loading
            # - Check if browser is accepting input
            # - Verify DOM elements are present

            return True

        except Exception:
            self.logger.exception("Error checking browser health")
            return False

    def get_browser_status(self) -> BrowserStatus:
        """Get comprehensive browser status and metrics.

        Provides detailed status information including process metrics,
        performance data, reliability statistics, and error tracking.

        Returns:
            Current browser status with comprehensive metrics
        """
        try:
            # Calculate uptime
            uptime = None
            if self._start_time and self._state == BrowserState.RUNNING:
                uptime = datetime.now() - self._start_time

            # Get performance metrics
            memory_usage = self._get_memory_usage()
            cpu_usage = self._get_cpu_usage()

            return BrowserStatus(
                state=self._state,
                pid=self._process.pid if self._process else None,
                start_time=self._start_time,
                uptime=uptime,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                crash_count=self._crash_count,
                restart_count=self._restart_count,
                last_restart_time=self._last_restart_time,
                is_responsive=self.is_browser_healthy(),
                last_health_check=self._last_health_check,
                last_error=self._last_error,
                error_time=self._error_time,
            )

        except Exception as e:
            self.logger.exception("Error getting browser status")
            return BrowserStatus(
                state=BrowserState.FAILED,
                pid=None,
                start_time=None,
                uptime=None,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
                crash_count=self._crash_count,
                restart_count=self._restart_count,
                last_restart_time=self._last_restart_time,
                is_responsive=False,
                last_health_check=None,
                last_error=str(e),
                error_time=datetime.now(),
            )

    async def clear_cache(self) -> bool:
        """Clear browser cache to free memory.

        Currently implemented as browser restart for reliable cache clearing.
        Future versions may implement more sophisticated cache management.

        Returns:
            True if cache cleared successfully, False otherwise
        """
        try:
            self.logger.info("Clearing browser cache")

            # For now, restart browser to clear cache reliably
            # TODO: Implement more sophisticated cache clearing in future
            if self._state == BrowserState.RUNNING:
                return await self.restart_browser()

            return True

        except Exception:
            self.logger.exception("Error clearing cache")
            return False

    def _build_chromium_args(self, url: str) -> list[str]:
        """Build optimized Chromium command line arguments for Pi Zero 2W.

        Creates comprehensive argument list optimized for 512MB RAM constraint,
        kiosk mode operation, and Pi Zero 2W hardware limitations.

        Args:
            url: Target URL to load

        Returns:
            List of command line arguments optimized for Pi Zero 2W
        """
        args = [
            self.config.executable_path,
            # Kiosk mode settings
            "--kiosk",
            "--start-fullscreen",
            f"--window-size={self.config.window_width},{self.config.window_height}",
            f"--force-device-scale-factor={self.config.scale_factor}",
            # Security settings (relaxed for local kiosk)
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            # Memory optimization for 512MB RAM Pi Zero 2W
            "--memory-pressure-off",
            "--max_old_space_size=64",  # Limit V8 heap to 64MB
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-background-networking",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-print-preview",
            "--disable-translate",
            # Performance optimizations
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-ipc-flooding-protection",
            "--disable-hang-monitor",
            "--disable-prompt-on-repost",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-dev-shm-usage",  # Critical for limited memory
            "--disable-gpu",  # May help on Pi Zero 2W
            # Kiosk behavior
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            # Touch optimization for 480x800 display
            "--touch-events=enabled",
            "--enable-pinch",
            # Target URL
            url,
        ]

        # Add conditional flags
        if self.config.disable_infobars:
            args.append("--disable-infobars")
        if self.config.disable_session_restore:
            args.append("--disable-restore-session-state")

        # Remove any empty arguments
        return [arg for arg in args if arg]

    async def _launch_process(self, cmd_args: list[str]) -> Optional[subprocess.Popen]:
        """Launch Chromium process with proper environment setup.

        Creates subprocess with appropriate environment variables and
        process group settings for reliable process management.

        Args:
            cmd_args: Command line arguments for Chromium

        Returns:
            Process handle or None if launch failed
        """
        try:
            # Set environment variables for kiosk mode
            env = os.environ.copy()
            env.update(
                {
                    "DISPLAY": ":0",
                    "XAUTHORITY": "/home/pi/.Xauthority",  # Standard Pi path
                }
            )

            process = subprocess.Popen(
                cmd_args,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,  # Create new process group (thread-safe)
            )

            # Give process time to start
            await asyncio.sleep(1)

            # Check if process started successfully
            if process.poll() is None:
                return process
            self.logger.error("Browser process exited immediately")
            return None

        except Exception:
            self.logger.exception("Failed to launch browser")
            return None

    async def _wait_for_responsive(self, timeout: int) -> bool:
        """Wait for browser to become responsive.

        Basic responsiveness check by monitoring process status.
        Future versions may include HTTP health checks and DOM validation.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if browser becomes responsive, False otherwise
        """
        # For now, just wait and check if process is still alive
        # TODO: Implement more sophisticated responsiveness check
        # - HTTP request to verify page is loaded
        # - Check window is visible
        # - Verify touch input is working

        for _ in range(timeout):
            if self._process and self._process.poll() is None:
                await asyncio.sleep(1)
            else:
                return False

        return bool(self._process and self._process.poll() is None)

    async def _start_monitoring(self) -> None:
        """Start background monitoring tasks for health and memory tracking."""
        try:
            self._health_task = asyncio.create_task(self._health_monitoring_loop())
            self._memory_task = asyncio.create_task(self._memory_monitoring_loop())
            self.logger.debug("Browser monitoring started")

        except Exception:
            self.logger.exception("Failed to start monitoring")

    async def _stop_monitoring(self) -> None:
        """Stop background monitoring tasks gracefully."""
        for task in [self._health_task, self._memory_task]:
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring loop with automatic restart on failure."""
        while not self._shutdown_requested:
            try:
                self._last_health_check = datetime.now()

                if not self.is_browser_healthy():
                    self.logger.warning("Browser health check failed, triggering restart")
                    restart_task = asyncio.create_task(self.restart_browser())
                    self._background_tasks.add(restart_task)
                    restart_task.add_done_callback(self._background_tasks.discard)
                    break

            except Exception:
                self.logger.exception("Error in health monitoring")

            await asyncio.sleep(self.config.health_check_interval)

    async def _memory_monitoring_loop(self) -> None:
        """Background memory monitoring loop with threshold-based actions."""
        while not self._shutdown_requested:
            try:
                memory_usage = self._get_memory_usage()
                memory_percent = memory_usage / self.config.memory_limit_mb

                if memory_percent > self.config.memory_critical_threshold:
                    self.logger.warning(
                        f"Critical memory usage: {memory_usage}MB, restarting browser"
                    )
                    restart_task = asyncio.create_task(self.restart_browser())
                    self._background_tasks.add(restart_task)
                    restart_task.add_done_callback(self._background_tasks.discard)
                    break
                if memory_percent > self.config.memory_warning_threshold:
                    self.logger.warning(f"High memory usage: {memory_usage}MB, clearing cache")
                    cache_task = asyncio.create_task(self.clear_cache())
                    self._background_tasks.add(cache_task)
                    cache_task.add_done_callback(self._background_tasks.discard)

            except Exception:
                self.logger.exception("Error in memory monitoring")

            await asyncio.sleep(self.config.memory_check_interval)

    def _get_memory_usage(self) -> int:
        """Get browser memory usage in MB using psutil if available.

        Returns:
            Memory usage in megabytes, 0 if unable to determine
        """
        try:
            if not self._process or not psutil:
                return 0

            process = psutil.Process(self._process.pid)
            memory_info = process.memory_info()
            return int(memory_info.rss / 1024 / 1024)  # Convert to MB

        except Exception:
            # Handle all psutil exceptions or cases where psutil is None
            self.logger.exception("Error getting memory usage")
            return 0

    def _get_cpu_usage(self) -> float:
        """Get browser CPU usage percentage using psutil if available.

        Returns:
            CPU usage as percentage, 0.0 if unable to determine
        """
        try:
            if not self._process or not psutil:
                return 0.0

            process = psutil.Process(self._process.pid)
            return process.cpu_percent()

        except Exception:
            # Handle all psutil exceptions or cases where psutil is None
            self.logger.exception("Error getting CPU usage")
            return 0.0

    def _calculate_restart_delay(self) -> int:
        """Calculate restart delay with exponential backoff.

        Implements exponential backoff with a maximum delay cap
        to prevent excessive wait times on repeated failures.

        Returns:
            Delay in seconds (capped at 60 seconds)
        """
        if self._restart_attempts == 1:
            return self.config.crash_restart_delay

        delay = self.config.crash_restart_delay * (
            self.config.restart_backoff_factor ** (self._restart_attempts - 1)
        )

        # Cap maximum delay at 60 seconds
        return min(int(delay), 60)

    async def _wait_for_process_exit(self) -> None:
        """Wait for browser process to exit completely."""
        if self._process:
            while self._process.poll() is None:
                await asyncio.sleep(0.1)

    def _cleanup_process_state(self) -> None:
        """Clean up process state after shutdown or crash."""
        self._process = None
        self._state = BrowserState.STOPPED
        self._start_time = None

    async def _handle_startup_failure(self, error_msg: str) -> None:
        """Handle browser startup failure with proper error tracking.

        Args:
            error_msg: Error message describing the failure
        """
        self.logger.error(error_msg)
        self._last_error = error_msg
        self._error_time = datetime.now()
        self._state = BrowserState.FAILED

        await self._stop_monitoring()
        self._cleanup_process_state()
