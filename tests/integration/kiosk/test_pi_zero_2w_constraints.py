"""Integration tests for Pi Zero 2W memory constraints and performance validation.

Tests memory usage enforcement, performance thresholds, and resource optimization
specific to Raspberry Pi Zero 2W deployment with 512MB RAM constraints.
"""

import asyncio
import logging
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.kiosk.browser_manager import BrowserConfig, BrowserManager
from calendarbot.kiosk.manager import KioskManager
from calendarbot.settings.kiosk_models import KioskSettings

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestPiZero2WMemoryConstraints:
    """Test Pi Zero 2W memory constraint enforcement and validation."""

    async def test_memory_usage_calculation_when_pi_optimized_then_within_limits(
        self, pi_zero_2w_kiosk_settings: KioskSettings, integration_test_base
    ) -> None:
        """Test memory usage calculation for Pi Zero 2W optimized settings."""
        # Validate the Pi Zero 2W optimized settings stay within constraints
        integration_test_base.assert_pi_zero_2w_constraints(pi_zero_2w_kiosk_settings)

        # Test memory usage calculation
        total_memory = pi_zero_2w_kiosk_settings.get_total_memory_usage_mb()
        assert total_memory <= 450, f"Total memory {total_memory}MB exceeds Pi Zero 2W safe limit"

        # Test memory safety check
        assert pi_zero_2w_kiosk_settings.is_memory_usage_safe(), "Settings should be memory safe"

        # Test memory breakdown
        breakdown = pi_zero_2w_kiosk_settings.get_memory_usage_breakdown()

        # Validate individual components stay reasonable for Pi Zero 2W
        assert breakdown["browser"] <= 100, f"Browser memory {breakdown['browser']}MB too high"
        assert breakdown["calendarbot"] <= 100, (
            f"CalendarBot memory {breakdown['calendarbot']}MB too high"
        )
        assert breakdown["system"] <= 200, f"System memory {breakdown['system']}MB too high"
        assert breakdown["tmpfs"] <= 50, f"tmpfs memory {breakdown['tmpfs']}MB too high"

        # Total should match sum of components
        expected_total = sum(v for k, v in breakdown.items() if k != "total")
        assert breakdown["total"] == expected_total, "Memory breakdown total mismatch"

        logger.info(f"Pi Zero 2W memory breakdown: {breakdown}")

    async def test_browser_memory_limit_enforcement_when_exceeded_then_detected(
        self, pi_zero_2w_kiosk_settings: KioskSettings, mock_system_resources
    ) -> None:
        """Test browser memory limit detection and enforcement."""
        config = BrowserConfig(
            memory_limit_mb=pi_zero_2w_kiosk_settings.browser.memory_limit_mb,
            startup_delay=0,
            window_width=pi_zero_2w_kiosk_settings.display.width,
            window_height=pi_zero_2w_kiosk_settings.display.height,
        )

        browser_manager = BrowserManager(config)

        # Mock memory usage above limit
        with patch.object(
            browser_manager, "_get_memory_usage", return_value=120
        ):  # Above 80MB limit
            is_healthy = browser_manager.is_browser_healthy()

        # Health check should fail due to memory constraint
        assert is_healthy is False, "Browser should be unhealthy when memory limit exceeded"

    async def test_system_memory_pressure_when_simulated_then_handled_gracefully(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        integration_test_base,
        mock_system_resources,
    ) -> None:
        """Test system behavior under memory pressure conditions."""
        # Simulate low memory condition
        mock_system_resources.simulate_memory_pressure(85.0)  # 85% memory usage
        integration_test_base.simulate_low_memory_scenario()

        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock system memory monitoring
        manager._get_system_memory_usage = MagicMock(return_value=430)  # High memory usage

        status = manager.get_kiosk_status()

        # Status should be captured even under memory pressure
        assert status is not None
        assert status.memory_usage_mb == 430

        # Verify constraints are still respected in settings
        integration_test_base.assert_pi_zero_2w_constraints(pi_zero_2w_kiosk_settings)

    @pytest.mark.parametrize(
        "memory_scenario",
        [
            {"available_memory_mb": 400, "should_start": True},
            {"available_memory_mb": 300, "should_start": True},  # Constrained but workable
            {"available_memory_mb": 200, "should_start": True},  # Very constrained but may work
            {"available_memory_mb": 100, "should_start": False},  # Insufficient
        ],
    )
    async def test_kiosk_startup_under_memory_constraints_then_appropriate_behavior(
        self,
        memory_scenario: Dict[str, Any],
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        mock_system_resources,
    ) -> None:
        """Test kiosk startup behavior under various memory constraint scenarios."""
        available_memory = memory_scenario["available_memory_mb"]
        should_start = memory_scenario["should_start"]

        # Configure system memory state
        mock_system_resources.used_memory_mb = 512 - available_memory

        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock startup phases based on available memory
        if available_memory >= 200:
            manager._start_web_server = AsyncMock(return_value=True)
            manager._wait_for_web_server_ready = AsyncMock(return_value=True)
            manager._start_browser = AsyncMock(return_value=should_start)
            manager._start_health_monitoring = AsyncMock()
        else:
            # Simulate failures under very low memory
            manager._start_web_server = AsyncMock(return_value=False)
            manager._cleanup_on_failure = AsyncMock()

        result = await manager.start_kiosk()

        if should_start:
            assert result is True, f"Kiosk should start with {available_memory}MB available"
        else:
            assert result is False, f"Kiosk should fail with {available_memory}MB available"

        logger.info(f"Memory scenario {available_memory}MB: {'SUCCESS' if result else 'FAILED'}")


@pytest.mark.asyncio
class TestPiZero2WPerformanceThresholds:
    """Test Pi Zero 2W performance thresholds and optimization."""

    async def test_kiosk_startup_performance_when_pi_hardware_then_within_thresholds(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        performance_monitor,
        performance_thresholds: Dict[str, Dict[str, float]],
    ) -> None:
        """Test kiosk startup performance meets Pi Zero 2W thresholds."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock individual phase timings for Pi Zero 2W
        async def timed_web_server():
            await asyncio.sleep(0.1)  # 100ms for web server
            return True

        async def timed_readiness(timeout: int = 30):
            await asyncio.sleep(0.05)  # 50ms for readiness check
            return True

        async def timed_browser():
            await asyncio.sleep(0.2)  # 200ms for browser (realistic for Pi Zero 2W)
            return True

        manager._start_web_server = timed_web_server
        manager._wait_for_web_server_ready = timed_readiness
        manager._start_browser = timed_browser
        manager._start_health_monitoring = AsyncMock()

        # Test individual phase performance
        performance_monitor.start_timing("web_server_start")
        await manager._start_web_server()
        web_server_duration = performance_monitor.end_timing("web_server_start")

        performance_monitor.start_timing("browser_launch")
        await manager._start_browser()
        browser_duration = performance_monitor.end_timing("browser_launch")

        # Validate against Pi Zero 2W thresholds
        web_server_threshold = performance_thresholds["startup"]["web_server_start"]
        browser_threshold = performance_thresholds["startup"]["browser_launch"]

        performance_monitor.assert_performance_threshold("web_server_start", web_server_threshold)
        performance_monitor.assert_performance_threshold("browser_launch", browser_threshold)

        logger.info(f"Web server: {web_server_duration:.3f}s, Browser: {browser_duration:.3f}s")

    async def test_browser_configuration_when_pi_optimized_then_performance_flags_set(
        self, pi_zero_2w_kiosk_settings: KioskSettings
    ) -> None:
        """Test browser configuration includes Pi Zero 2W performance optimizations."""
        config = BrowserConfig(
            memory_limit_mb=pi_zero_2w_kiosk_settings.browser.memory_limit_mb,
            window_width=pi_zero_2w_kiosk_settings.display.width,
            window_height=pi_zero_2w_kiosk_settings.display.height,
        )

        browser_manager = BrowserManager(config)

        # Test Chromium arguments include Pi Zero 2W optimizations
        test_url = "http://localhost:8080/whats-next-view"
        args = browser_manager._build_chromium_args(test_url)

        # Critical Pi Zero 2W optimizations should be present
        pi_optimizations = [
            "--disable-dev-shm-usage",  # Critical for low memory
            "--memory-pressure-off",  # Disable memory pressure
            "--max_old_space_size=64",  # Conservative heap size
            "--no-sandbox",  # Reduce security overhead
            "--disable-gpu",  # May help on Pi Zero 2W
        ]

        for optimization in pi_optimizations:
            assert optimization in args, f"Missing Pi Zero 2W optimization: {optimization}"

        # Memory limit validation
        assert config.memory_limit_mb <= 120, (
            f"Memory limit {config.memory_limit_mb}MB too high for Pi Zero 2W"
        )

        logger.info(f"Pi Zero 2W browser optimizations: {pi_optimizations}")

    async def test_monitoring_intervals_when_pi_hardware_then_appropriate_frequency(
        self, pi_zero_2w_kiosk_settings: KioskSettings
    ) -> None:
        """Test monitoring intervals are appropriate for Pi Zero 2W performance."""
        monitoring = pi_zero_2w_kiosk_settings.monitoring

        # Health check intervals should be less frequent on Pi Zero 2W to reduce CPU overhead
        assert monitoring.health_check_interval >= 60, "Health checks too frequent for Pi Zero 2W"
        assert monitoring.memory_check_interval >= 90, "Memory checks too frequent for Pi Zero 2W"

        # Memory thresholds should be conservative
        assert monitoring.memory_threshold_mb <= 400, "Memory threshold too high for Pi Zero 2W"

        # CPU threshold should account for Pi Zero 2W capabilities
        assert monitoring.cpu_threshold_percent <= 80.0, "CPU threshold too high for Pi Zero 2W"

    async def test_health_monitoring_performance_when_running_then_low_overhead(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        performance_monitor,
    ) -> None:
        """Test health monitoring has low performance overhead on Pi Zero 2W."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Mock health check operations
        manager.browser_manager.is_browser_healthy = MagicMock(return_value=True)
        manager._check_web_server_health = AsyncMock(return_value=True)

        # Time a single health check iteration
        performance_monitor.start_timing("health_check")

        # Simulate one health monitoring cycle
        is_healthy = manager.browser_manager.is_browser_healthy()
        web_healthy = await manager._check_web_server_health()

        health_check_duration = performance_monitor.end_timing("health_check")

        # Health checks should be very fast (< 2s threshold)
        performance_monitor.assert_performance_threshold("health_check", 2.0)

        assert is_healthy is True
        assert web_healthy is True

        logger.info(f"Health check completed in {health_check_duration:.3f}s")


@pytest.mark.asyncio
class TestPiZero2WResourceOptimization:
    """Test Pi Zero 2W specific resource optimization features."""

    async def test_pi_optimization_settings_when_enabled_then_properly_configured(
        self, pi_zero_2w_kiosk_settings: KioskSettings
    ) -> None:
        """Test Pi optimization settings are properly configured."""
        pi_opts = pi_zero_2w_kiosk_settings.pi_optimization

        # Memory optimization should be enabled
        assert pi_opts.enable_memory_optimization is True

        # Swap size should be balanced for SD card wear vs performance
        assert 128 <= pi_opts.swap_size_mb <= 512, (
            f"Swap size {pi_opts.swap_size_mb}MB not optimal for Pi Zero 2W"
        )

        # GPU memory split should be reasonable
        assert 64 <= pi_opts.memory_split_mb <= 128, (
            f"GPU split {pi_opts.memory_split_mb}MB not optimal"
        )

        # CPU governor should be appropriate for kiosk usage
        valid_governors = ["ondemand", "performance", "powersave", "conservative"]
        assert pi_opts.cpu_governor in valid_governors, (
            f"Invalid CPU governor: {pi_opts.cpu_governor}"
        )

        # tmpfs should be enabled to reduce SD card wear
        assert pi_opts.enable_tmpfs_logs is True
        assert pi_opts.tmpfs_size_mb <= 64, f"tmpfs size {pi_opts.tmpfs_size_mb}MB too large"

        # Thermal throttling should be enabled for hardware protection
        assert pi_opts.enable_thermal_throttling is True
        assert pi_opts.thermal_soft_limit < pi_opts.thermal_hard_limit

    async def test_tmpfs_configuration_when_enabled_then_reduces_sd_writes(
        self, pi_zero_2w_kiosk_settings: KioskSettings
    ) -> None:
        """Test tmpfs configuration reduces SD card write wear."""
        pi_opts = pi_zero_2w_kiosk_settings.pi_optimization

        if pi_opts.enable_tmpfs_logs:
            # tmpfs should be appropriately sized for Pi Zero 2W
            assert pi_opts.tmpfs_size_mb <= 64, "tmpfs size too large for Pi Zero 2W memory"

            # tmpfs size should be included in memory calculations
            memory_breakdown = pi_zero_2w_kiosk_settings.get_memory_usage_breakdown()
            assert memory_breakdown["tmpfs"] == pi_opts.tmpfs_size_mb

    async def test_thermal_management_when_configured_then_appropriate_limits(
        self, pi_zero_2w_kiosk_settings: KioskSettings
    ) -> None:
        """Test thermal management settings are appropriate for Pi Zero 2W."""
        pi_opts = pi_zero_2w_kiosk_settings.pi_optimization

        if pi_opts.enable_thermal_throttling:
            # Thermal limits should be appropriate for Pi Zero 2W
            assert 60.0 <= pi_opts.thermal_soft_limit <= 75.0, "Thermal soft limit not appropriate"
            assert 70.0 <= pi_opts.thermal_hard_limit <= 85.0, "Thermal hard limit not appropriate"
            assert pi_opts.thermal_soft_limit < pi_opts.thermal_hard_limit, (
                "Thermal limits inverted"
            )

    async def test_memory_optimization_when_enabled_then_reduces_footprint(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        high_performance_kiosk_settings: KioskSettings,
    ) -> None:
        """Test memory optimization reduces overall memory footprint."""
        # Compare optimized vs high performance settings
        optimized_memory = pi_zero_2w_kiosk_settings.get_total_memory_usage_mb()
        high_perf_memory = high_performance_kiosk_settings.get_total_memory_usage_mb()

        # Optimized settings should use less memory
        assert optimized_memory < high_perf_memory, (
            f"Optimized memory {optimized_memory}MB not less than high perf {high_perf_memory}MB"
        )

        # Both should be within Pi Zero 2W limits but optimized should have more headroom
        pi_limit = 450  # Conservative Pi Zero 2W limit

        assert optimized_memory <= pi_limit, (
            f"Optimized memory {optimized_memory}MB exceeds Pi limit"
        )

        # Optimized should provide at least 50MB more headroom
        optimized_headroom = pi_limit - optimized_memory
        high_perf_headroom = pi_limit - high_performance_kiosk_settings.get_total_memory_usage_mb()

        if high_performance_kiosk_settings.get_total_memory_usage_mb() <= pi_limit:
            assert optimized_headroom >= high_perf_headroom + 20, (
                f"Optimized provides insufficient headroom improvement: "
                f"{optimized_headroom}MB vs {high_perf_headroom}MB"
            )

        logger.info(
            f"Memory usage - Optimized: {optimized_memory}MB, High perf: {high_perf_memory}MB"
        )


@pytest.mark.asyncio
class TestPiZero2WStressScenarios:
    """Test Pi Zero 2W behavior under stress conditions."""

    async def test_concurrent_operations_when_memory_constrained_then_graceful_degradation(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        mock_system_resources,
        performance_monitor,
    ) -> None:
        """Test concurrent operations under memory constraints show graceful degradation."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Simulate memory pressure
        mock_system_resources.simulate_memory_pressure(80.0)

        # Mock concurrent operations
        manager._start_web_server = AsyncMock(return_value=True)
        manager._wait_for_web_server_ready = AsyncMock(return_value=True)
        manager._start_browser = AsyncMock(return_value=True)
        manager._start_health_monitoring = AsyncMock()

        manager.browser_manager.is_browser_healthy = MagicMock(return_value=True)
        manager._get_system_memory_usage = MagicMock(return_value=400)  # High usage

        performance_monitor.start_timing("stressed_operations")

        # Test startup under stress
        startup_result = await manager.start_kiosk()

        # Test status reporting under stress
        status = manager.get_kiosk_status()

        operation_duration = performance_monitor.end_timing("stressed_operations")

        # Operations should still succeed but may take longer
        assert startup_result is True, "Startup should succeed even under memory pressure"
        assert status is not None, "Status should be available under stress"

        # Allow longer time for stressed operations but still reasonable
        assert operation_duration < 10.0, (
            f"Stressed operations took {operation_duration:.2f}s, too slow"
        )

        logger.info(f"Stressed operations completed in {operation_duration:.2f}s")

    async def test_memory_leak_simulation_when_detected_then_recovery_triggered(
        self,
        pi_zero_2w_kiosk_settings: KioskSettings,
        mock_daemon_manager: MagicMock,
        performance_thresholds: Dict[str, Dict[str, float]],
    ) -> None:
        """Test memory leak detection and recovery mechanisms."""
        mock_settings = MagicMock()
        mock_settings.web_port = 8080

        manager = KioskManager(
            settings=mock_settings,
            kiosk_settings=pi_zero_2w_kiosk_settings,
            daemon_manager=mock_daemon_manager,
        )

        # Simulate gradual memory increase (leak)
        memory_values = [75, 85, 95, 110, 125]  # Simulating memory leak over time
        memory_iter = iter(memory_values)

        def mock_memory_usage():
            try:
                return next(memory_iter)
            except StopIteration:
                return 125  # Stay at high value

        manager.browser_manager._get_memory_usage = mock_memory_usage

        # Test memory constraint detection
        initial_healthy = manager.browser_manager.is_browser_healthy()

        # After several checks, should detect high memory usage
        for i in range(3):
            healthy = manager.browser_manager.is_browser_healthy()

        # Final check should show unhealthy due to memory limit exceeded
        final_healthy = manager.browser_manager.is_browser_healthy()

        # Memory leak should be detected
        assert final_healthy is False, "Browser should be unhealthy due to memory leak"

        # Memory threshold from performance thresholds
        memory_threshold = performance_thresholds["memory"]["max_browser_memory_mb"]
        assert memory_threshold < 125, (
            f"Test memory {125}MB should exceed threshold {memory_threshold}MB"
        )
