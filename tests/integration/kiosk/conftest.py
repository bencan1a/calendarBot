"""Pytest configuration and fixtures for kiosk integration tests.

This module provides comprehensive fixtures for testing kiosk mode integration scenarios,
including Pi Zero 2W resource constraints, component orchestration, and system validation.
"""

import logging
import tempfile
import time
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Import only what's needed to avoid circular imports
from calendarbot.kiosk.browser_manager import BrowserConfig, BrowserState, BrowserStatus
from calendarbot.settings.kiosk_models import (
    KioskBrowserSettings,
    KioskDisplaySettings,
    KioskMonitoringSettings,
    KioskPiOptimizationSettings,
    KioskSecuritySettings,
    KioskSettings,
    KioskSystemSettings,
)

# Import these in fixtures to avoid circular import at module level
# from calendarbot.kiosk.browser_manager import BrowserManager
# from calendarbot.kiosk.manager import KioskManager, KioskStatus
# from calendarbot.utils.daemon import DaemonManager

logger = logging.getLogger(__name__)


class MockSystemResources:
    """Mock system resources for Pi Zero 2W constraint testing."""

    def __init__(self, total_memory_mb: int = 512, cpu_cores: int = 4):
        self.total_memory_mb = total_memory_mb
        self.cpu_cores = cpu_cores
        self.used_memory_mb = 128  # Base system usage
        self.cpu_usage_percent = 5.0  # Base CPU usage

    def allocate_memory(self, amount_mb: int) -> bool:
        """Simulate memory allocation."""
        if self.used_memory_mb + amount_mb <= self.total_memory_mb:
            self.used_memory_mb += amount_mb
            return True
        return False

    def free_memory(self, amount_mb: int) -> None:
        """Simulate memory deallocation."""
        self.used_memory_mb = max(128, self.used_memory_mb - amount_mb)

    def get_available_memory_mb(self) -> int:
        """Get available memory in MB."""
        return self.total_memory_mb - self.used_memory_mb

    def simulate_memory_pressure(self, usage_percent: float) -> None:
        """Simulate memory pressure scenario."""
        target_usage = int(self.total_memory_mb * (usage_percent / 100))
        self.used_memory_mb = max(128, target_usage)


class PerformanceMonitor:
    """Performance monitoring utilities for integration tests."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.metrics: dict[str, Any] = {}

    def start_timing(self, operation: str) -> None:
        """Start timing an operation."""
        self.start_time = time.time()
        self.metrics[operation] = {"start_time": self.start_time}

    def end_timing(self, operation: str) -> float:
        """End timing and return duration."""
        if self.start_time is None:
            raise ValueError("Timer not started")

        duration = time.time() - self.start_time
        self.metrics[operation]["duration"] = duration
        self.metrics[operation]["end_time"] = time.time()

        return duration

    def get_metrics(self) -> dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()

    def assert_performance_threshold(self, operation: str, max_seconds: float) -> None:
        """Assert operation completed within threshold."""
        if operation not in self.metrics:
            raise ValueError(f"No metrics found for operation: {operation}")

        duration = self.metrics[operation]["duration"]
        assert duration <= max_seconds, (
            f"Operation '{operation}' took {duration:.2f}s, exceeding threshold of {max_seconds}s"
        )


class KioskIntegrationTestBase:
    """Base class for kiosk integration tests with common utilities."""

    def __init__(self):
        self.temp_dir: Optional[Path] = None
        self.mock_system: Optional[MockSystemResources] = None
        self.performance_monitor = PerformanceMonitor()

    def setup_test_environment(self) -> Path:
        """Set up isolated test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_system = MockSystemResources()
        return self.temp_dir

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def assert_pi_zero_2w_constraints(self, kiosk_settings: KioskSettings) -> None:
        """Assert settings comply with Pi Zero 2W constraints."""
        # Memory constraints
        total_memory = kiosk_settings.get_total_memory_usage_mb()
        assert total_memory <= 450, f"Total memory usage {total_memory}MB exceeds Pi Zero 2W limit"

        # Browser memory limit
        assert kiosk_settings.browser.memory_limit_mb <= 120, (
            f"Browser memory limit {kiosk_settings.browser.memory_limit_mb}MB too high for Pi Zero 2W"
        )

        # Display resolution reasonable for performance
        pixel_count = kiosk_settings.display.width * kiosk_settings.display.height
        assert pixel_count <= 1920 * 1080, "Display resolution may impact Pi Zero 2W performance"

    def simulate_low_memory_scenario(self) -> None:
        """Simulate low memory scenario for testing."""
        if self.mock_system:
            self.mock_system.simulate_memory_pressure(85.0)  # 85% memory usage


# Core Fixtures


@pytest.fixture
def mock_system_resources() -> MockSystemResources:
    """Provide mock system resources for Pi Zero 2W testing."""
    return MockSystemResources(total_memory_mb=512, cpu_cores=4)


@pytest.fixture
def performance_monitor() -> PerformanceMonitor:
    """Provide performance monitoring utilities."""
    return PerformanceMonitor()


@pytest.fixture
def integration_test_base() -> Generator[KioskIntegrationTestBase, None, None]:
    """Provide base integration test utilities."""
    test_base = KioskIntegrationTestBase()
    test_base.setup_test_environment()

    yield test_base

    test_base.cleanup_test_environment()


# Pi Zero 2W Optimized Settings Fixtures


@pytest.fixture
def pi_zero_2w_kiosk_settings() -> KioskSettings:
    """Pi Zero 2W optimized kiosk settings for testing."""
    return KioskSettings(
        enabled=True,
        auto_start=True,
        target_layout="whats-next-view",
        debug_mode=False,
        # Conservative browser settings for Pi Zero 2W
        browser=KioskBrowserSettings(
            executable_path="chromium-browser",
            startup_delay=8,  # Allow system to stabilize
            startup_timeout=45,  # Longer timeout for slower hardware
            shutdown_timeout=15,
            memory_limit_mb=80,  # Conservative memory limit
            max_restart_attempts=3,
            restart_backoff_factor=1.5,
            cache_clear_on_restart=True,
            disable_extensions=True,
            disable_plugins=True,
            custom_flags=[
                "--disable-dev-shm-usage",  # Critical for low memory
                "--memory-pressure-off",
                "--max_old_space_size=64",  # Conservative heap size
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-gpu",  # GPU acceleration may not help on Pi Zero 2W
            ],
        ),
        # Display optimized for common kiosk screens
        display=KioskDisplaySettings(
            width=480,
            height=800,
            orientation="portrait",
            scale_factor=1.0,
            touch_enabled=True,
            brightness=70,  # Save power
            hide_cursor=True,
            fullscreen_mode=True,
            prevent_zoom=True,
        ),
        # Monitoring tuned for Pi Zero 2W
        monitoring=KioskMonitoringSettings(
            enabled=True,
            health_check_interval=90,  # Less frequent checks
            memory_check_interval=120,
            memory_threshold_mb=350,  # Conservative threshold
            cpu_threshold_percent=75.0,
            remote_monitoring_enabled=False,
            alert_methods=["log"],
        ),
        # Pi-specific optimizations
        pi_optimization=KioskPiOptimizationSettings(
            enable_memory_optimization=True,
            swap_size_mb=256,  # Balanced for SD card wear
            memory_split_mb=64,  # Standard GPU split
            cpu_governor="ondemand",  # Balance performance and power
            enable_tmpfs_logs=True,
            tmpfs_size_mb=32,  # Small tmpfs to reduce SD writes
            enable_thermal_throttling=True,
            thermal_soft_limit=70.0,
            thermal_hard_limit=80.0,
        ),
        # System settings for kiosk deployment
        system=KioskSystemSettings(
            systemd_service_name="calendarbot-kiosk",
            service_user="pi",
            boot_delay=60,  # Extra time for Pi Zero 2W boot
            wait_for_network=True,
            network_timeout=30,
            enable_watchdog=True,
            watchdog_timeout=60,
            ssh_enabled=True,
            update_schedule="weekly",
            x11_display=":0",
        ),
        # Security for remote deployment
        security=KioskSecuritySettings(
            enable_security_logging=True,
            failed_auth_lockout=True,
            max_failed_attempts=3,
            lockout_duration=300,
            audit_enabled=True,
            allowed_domains=["localhost", "127.0.0.1"],
        ),
    )


@pytest.fixture
def high_performance_kiosk_settings() -> KioskSettings:
    """Higher performance kiosk settings for testing edge cases."""
    return KioskSettings(
        enabled=True,
        browser=KioskBrowserSettings(
            memory_limit_mb=100,  # Further reduced to fit within Pi Zero 2W limits
            startup_timeout=30,
            custom_flags=["--enable-gpu-rasterization"],  # Test with GPU enabled via flags
        ),
        display=KioskDisplaySettings(
            width=800,
            height=1080,  # Higher resolution within limits
            brightness=100,
        ),
        monitoring=KioskMonitoringSettings(
            health_check_interval=30,  # More frequent monitoring
            memory_threshold_mb=400,
        ),
    )


@pytest.fixture
def resource_constrained_settings() -> KioskSettings:
    """Extremely resource-constrained settings for stress testing."""
    return KioskSettings(
        enabled=True,
        browser=KioskBrowserSettings(
            memory_limit_mb=64,  # Very low memory within minimum limits
            startup_timeout=60,  # Longer timeouts for slow startup
            max_restart_attempts=5,
        ),
        pi_optimization=KioskPiOptimizationSettings(
            swap_size_mb=128,  # Smaller swap
            tmpfs_size_mb=16,  # Minimal tmpfs
            cpu_governor="powersave",  # Power saving mode
        ),
    )


# Mock Component Fixtures


@pytest.fixture
def mock_daemon_manager() -> MagicMock:
    """Mock daemon manager for testing."""
    # Import here to avoid circular import
    from calendarbot.utils.daemon import DaemonManager

    daemon = MagicMock(spec=DaemonManager)
    daemon.is_daemon_running.return_value = False
    daemon.get_daemon_pid.return_value = None
    daemon.create_pid_file.return_value = 12345
    daemon.cleanup_pid_file.return_value = True
    # Note: get_daemon_status is on DaemonController, not DaemonManager
    return daemon


@pytest.fixture
def mock_browser_manager() -> MagicMock:
    """Mock browser manager for integration testing."""
    # Import here to avoid circular import
    from calendarbot.kiosk.browser_manager import BrowserManager

    browser = MagicMock(spec=BrowserManager)

    # Default healthy state
    browser.start_browser = AsyncMock(return_value=True)
    browser.stop_browser = AsyncMock(return_value=True)
    browser.restart_browser = AsyncMock(return_value=True)
    browser.is_browser_healthy.return_value = True
    browser.clear_cache = AsyncMock(return_value=True)

    # Mock browser status
    browser.get_browser_status.return_value = BrowserStatus(
        state=BrowserState.RUNNING,
        pid=23456,
        start_time=datetime.now() - timedelta(minutes=10),
        uptime=timedelta(minutes=10),
        memory_usage_mb=75,
        cpu_usage_percent=8.5,
        crash_count=0,
        restart_count=0,
        last_restart_time=None,
        is_responsive=True,
        last_health_check=datetime.now(),
        last_error=None,
        error_time=None,
    )

    return browser


@pytest_asyncio.fixture
async def real_browser_manager(
    pi_zero_2w_kiosk_settings: KioskSettings,
) -> AsyncGenerator[Any, None]:
    """Provide real browser manager for integration tests requiring actual browser interaction."""
    # Import here to avoid circular import
    from calendarbot.kiosk.browser_manager import BrowserManager

    config = BrowserConfig(
        memory_limit_mb=pi_zero_2w_kiosk_settings.browser.memory_limit_mb,
        startup_delay=0,  # No delay in tests
        startup_timeout=10,  # Shorter timeout for tests
        window_width=pi_zero_2w_kiosk_settings.display.width,
        window_height=pi_zero_2w_kiosk_settings.display.height,
    )

    browser_manager = BrowserManager(config)

    yield browser_manager

    # Cleanup: ensure browser is stopped
    try:
        await browser_manager.stop_browser()
    except Exception as e:
        logger.warning(f"Error stopping browser manager in fixture cleanup: {e}")


@pytest_asyncio.fixture
async def kiosk_manager(
    pi_zero_2w_kiosk_settings: KioskSettings, mock_daemon_manager: MagicMock
) -> AsyncGenerator[Any, None]:
    """Provide real kiosk manager for integration testing."""
    # Import here to avoid circular import
    from calendarbot.kiosk.manager import KioskManager

    # Mock settings object
    mock_settings = MagicMock()
    mock_settings.web_port = 8080
    mock_settings.web_host = "127.0.0.1"

    manager = KioskManager(
        settings=mock_settings,
        kiosk_settings=pi_zero_2w_kiosk_settings,
        daemon_manager=mock_daemon_manager,
    )

    yield manager

    # Cleanup: ensure kiosk is stopped
    try:
        await manager.stop_kiosk()
    except Exception as e:
        logger.warning(f"Error stopping kiosk manager in fixture cleanup: {e}")


# Browser Automation Fixtures


@pytest.fixture
def browser_automation_config() -> dict[str, Any]:
    """Configuration for browser automation testing."""
    return {
        "headless": True,  # Run headless in CI
        "viewport": {"width": 480, "height": 800},
        "timeout": 30000,  # 30 second timeout
        "browser_args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--memory-pressure-off",
        ],
    }


# Performance Test Fixtures


@pytest.fixture
def memory_constraint_scenarios() -> dict[str, dict[str, Any]]:
    """Memory constraint scenarios for performance testing."""
    return {
        "optimal": {"available_memory_mb": 400, "expected_startup_time": 15},
        "constrained": {"available_memory_mb": 300, "expected_startup_time": 25},
        "critical": {"available_memory_mb": 200, "expected_startup_time": 45},
        "insufficient": {"available_memory_mb": 100, "expected_startup_time": None},  # Should fail
    }


@pytest.fixture
def performance_thresholds() -> dict[str, dict[str, float]]:
    """Performance thresholds for Pi Zero 2W testing."""
    return {
        "startup": {
            "web_server_start": 5.0,  # Web server should start within 5s
            "browser_launch": 20.0,  # Browser should launch within 20s
            "kiosk_ready": 30.0,  # Full kiosk ready within 30s
            "health_check": 2.0,  # Health checks within 2s
        },
        "memory": {
            "max_browser_memory_mb": 120,  # Browser memory limit
            "max_total_memory_mb": 450,  # Total system memory limit
            "memory_leak_threshold": 1.1,  # 10% memory growth tolerance
        },
        "cpu": {
            "max_cpu_percent": 80.0,  # Maximum sustained CPU usage
            "idle_cpu_percent": 15.0,  # CPU usage when idle
        },
    }


# Deployment Test Fixtures


@pytest.fixture
def mock_systemd_environment() -> dict[str, Any]:
    """Mock systemd environment for deployment testing."""
    return {
        "service_files": {
            "calendarbot-kiosk.service": True,
            "calendarbot-kiosk-setup.service": True,
            "calendarbot-network-wait.service": True,
        },
        "systemctl_commands": {
            "enable": True,
            "start": True,
            "status": "active",
            "is-enabled": True,
        },
        "service_user": "pi",
        "service_group": "pi",
    }


@pytest.fixture
def mock_x11_environment() -> dict[str, str]:
    """Mock X11 environment for display testing."""
    return {
        "DISPLAY": ":0",
        "XAUTHORITY": "/home/pi/.Xauthority",
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }


# Error Simulation Fixtures


@pytest.fixture
def error_scenarios() -> dict[str, dict[str, Any]]:
    """Error scenarios for testing recovery mechanisms."""
    return {
        "browser_crash": {
            "component": "browser",
            "error_type": "ProcessExit",
            "recovery_expected": True,
            "max_recovery_time": 15.0,
        },
        "memory_exhaustion": {
            "component": "system",
            "error_type": "MemoryError",
            "recovery_expected": True,
            "max_recovery_time": 30.0,
        },
        "network_failure": {
            "component": "web_server",
            "error_type": "ConnectionError",
            "recovery_expected": True,
            "max_recovery_time": 20.0,
        },
        "disk_full": {
            "component": "logging",
            "error_type": "OSError",
            "recovery_expected": False,
            "max_recovery_time": None,
        },
    }


# Logging and Debug Fixtures


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide test logger with appropriate level."""
    logger = logging.getLogger("kiosk_integration_test")
    logger.setLevel(logging.DEBUG)

    # Add console handler if not exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
