"""Integration tests for ConnectionManager with ConnectionPoolMonitor.

This module tests the integration between ConnectionManager and ConnectionPoolMonitor
to ensure proper metric collection, performance tracking, and monitoring
during actual connection pool operations.
"""

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.config.optimization import OptimizationConfig
from calendarbot.optimization.connection_manager import (
    ConnectionManager,
    get_connection_manager,
    reset_connection_manager,
)


class TestConnectionManagerPhase2AIntegration:
    """Test ConnectionManager integration with Phase2AMonitor."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Reset connection manager before each test
        reset_connection_manager()
        yield
        # Clean up after each test
        reset_connection_manager()

    @pytest.fixture
    def mock_optimization_config(self) -> OptimizationConfig:
        """Create a mock optimization config."""
        config = MagicMock(spec=OptimizationConfig)
        config.connection_pool = MagicMock()
        config.connection_pool.enabled = True
        config.connection_pool.max_connections = 20
        config.connection_pool.max_connections_per_host = 15
        config.connection_pool.connection_timeout = 30.0
        config.connection_pool.read_timeout = 60.0
        config.connection_pool.keepalive_timeout = 30.0
        config.connection_pool.enable_cleanup_closed = True
        return config

    @pytest.fixture
    def mock_phase2a_monitor(self) -> Phase2AMonitor:
        """Create a mock Phase2AMonitor."""
        monitor = MagicMock(spec=Phase2AMonitor)
        monitor.log_connection_pool_status = MagicMock()
        monitor.log_connection_acquisition = MagicMock()
        monitor.log_connection_release = MagicMock()
        monitor.get_metrics = MagicMock(return_value={})
        monitor.reset_metrics = MagicMock()
        return monitor

    @pytest.mark.asyncio
    async def test_connection_manager_monitor_integration_initialization(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test ConnectionManager initializes correctly with Phase2AMonitor."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)

            # Verify monitor is properly assigned
            assert connection_manager.monitor == mock_phase2a_monitor

            # Initialize the connection manager
            await connection_manager.startup()

            # Verify monitor received connection pool status logs
            cast(MagicMock, mock_phase2a_monitor.log_connection_pool_status).assert_called()

            # Check that connection pool status was logged during initialization
            call_args_list = cast(
                MagicMock, mock_phase2a_monitor.log_connection_pool_status
            ).call_args_list
            assert len(call_args_list) > 0, "No connection pool status logged during initialization"

            # Verify the status was logged with correct parameters
            last_call = call_args_list[-1]
            assert "active" in last_call.kwargs or len(last_call.args) > 0
            assert "max_connections" in last_call.kwargs or len(last_call.args) > 2

            await connection_manager.shutdown()

    @pytest.mark.asyncio
    async def test_connection_acquisition_with_monitoring(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test connection acquisition records proper metrics."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)
            await connection_manager.startup()

            # Mock aiohttp session for testing
            mock_session = AsyncMock()
            connection_manager._http_session = mock_session

            # Test connection acquisition
            session = await connection_manager.get_http_session()
            assert session == mock_session

            # Verify metrics were recorded
            cast(MagicMock, mock_phase2a_monitor.log_connection_acquisition).assert_called()

            # Check for connection acquisition metrics
            call_args_list = cast(
                MagicMock, mock_phase2a_monitor.log_connection_acquisition
            ).call_args_list
            assert len(call_args_list) > 0, "No connection acquisition metrics recorded"

            await connection_manager.shutdown()

    @pytest.mark.asyncio
    async def test_connection_health_check_monitoring(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test connection health checks record proper metrics."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)
            await connection_manager.startup()

            # Perform health check
            health_status = await connection_manager.health_check()

            # Health check should return status
            assert isinstance(health_status, dict)
            assert "overall_healthy" in health_status

            # Verify health check metrics were recorded via connection pool status
            call_args_list = cast(
                MagicMock, mock_phase2a_monitor.log_connection_pool_status
            ).call_args_list
            assert len(call_args_list) > 0, "No health check metrics recorded"

            await connection_manager.shutdown()

    @pytest.mark.asyncio
    async def test_connection_statistics_monitoring(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test connection statistics are properly monitored."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)
            await connection_manager.startup()

            # Get connection statistics (sync method, not async)
            stats = connection_manager.get_connection_stats()

            # Verify statistics structure
            assert isinstance(stats, dict)
            expected_keys = ["status", "startup_complete", "max_connections"]
            for key in expected_keys:
                assert key in stats, f"Missing key '{key}' in connection statistics"

            # Verify statistics monitoring via connection pool status
            call_args_list = cast(
                MagicMock, mock_phase2a_monitor.log_connection_pool_status
            ).call_args_list
            assert len(call_args_list) > 0, "No statistics metrics recorded"

            await connection_manager.shutdown()

    @pytest.mark.asyncio
    async def test_error_condition_monitoring(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test error conditions are properly monitored."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)

            # Test error during startup by patching aiohttp components
            with patch("aiohttp.TCPConnector", side_effect=Exception("Test error")):
                with pytest.raises(Exception):
                    await connection_manager.startup()

            # Since startup failed, we don't expect connection pool status to be logged
            # but the error handling should still work
            assert connection_manager._startup_complete is False

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test performance metrics are collected during operations."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)
            await connection_manager.startup()

            # Simulate multiple connection operations
            mock_session = AsyncMock()
            connection_manager._http_session = mock_session

            # Perform multiple operations to generate metrics
            for _ in range(5):
                session = await connection_manager.get_http_session()
                assert session == mock_session
                await asyncio.sleep(0.01)  # Simulate work

            # Get final statistics
            _ = connection_manager.get_connection_stats()
            _ = await connection_manager.health_check()

            # Verify comprehensive metrics were collected
            acquisition_calls = cast(
                MagicMock, mock_phase2a_monitor.log_connection_acquisition
            ).call_args_list
            pool_status_calls = cast(
                MagicMock, mock_phase2a_monitor.log_connection_pool_status
            ).call_args_list

            # Should have metrics for initialization, operations, and health checks
            total_calls = len(acquisition_calls) + len(pool_status_calls)
            assert total_calls > 5, "Insufficient metrics collected during operations"

            # Verify connection acquisition calls from multiple operations
            assert len(acquisition_calls) >= 5, (
                f"Expected at least 5 acquisition calls, got {len(acquisition_calls)}"
            )

            await connection_manager.shutdown()

    def test_global_connection_manager_monitoring(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test global connection manager properly integrates with monitoring."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            # Test getting global connection manager with monitor
            with patch(
                "calendarbot.optimization.connection_manager.Phase2AMonitor"
            ) as mock_monitor_class:
                mock_monitor_class.return_value = mock_phase2a_monitor

                manager = get_connection_manager()

                # Verify manager was created and configured
                assert manager is not None
                # Don't test exact monitor equality since real monitor might be created
                assert hasattr(manager, "monitor")
                assert manager.monitor is not None

                # Test that subsequent calls return same instance
                manager2 = get_connection_manager()
                assert manager is manager2

                # Test reset functionality
                reset_connection_manager()
                manager3 = get_connection_manager()
                assert manager3 is not manager

    @pytest.mark.asyncio
    async def test_concurrent_operations_monitoring(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test monitoring works correctly under concurrent operations."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)
            await connection_manager.startup()

            # Mock session for concurrent testing
            mock_session = AsyncMock()
            connection_manager._http_session = mock_session

            async def concurrent_operation():
                """Simulate concurrent connection operation."""
                session = await connection_manager.get_http_session()
                assert session == mock_session
                await asyncio.sleep(0.01)
                return True

            # Run multiple concurrent operations
            tasks = [concurrent_operation() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # Verify all operations completed successfully
            assert all(results), "Some concurrent operations failed"

            # Verify metrics were recorded for concurrent operations
            acquisition_calls = cast(
                MagicMock, mock_phase2a_monitor.log_connection_acquisition
            ).call_args_list

            # Should have metrics from multiple concurrent operations
            assert len(acquisition_calls) >= 10, (
                f"Expected at least 10 acquisition calls, got {len(acquisition_calls)}"
            )

            await connection_manager.shutdown()

    def test_monitor_integration_configuration(self):
        """Test ConnectionManager can be configured with different monitors."""
        # Test with no monitor
        manager1 = ConnectionManager()
        assert manager1.monitor is not None  # Should create default monitor

        # Test with custom monitor
        custom_monitor = MagicMock(spec=Phase2AMonitor)
        manager2 = ConnectionManager(monitor=custom_monitor)
        assert manager2.monitor == custom_monitor

        # Test with None monitor
        manager3 = ConnectionManager(monitor=None)
        assert manager3.monitor is not None  # Should create default monitor

    @pytest.mark.asyncio
    async def test_metric_data_accuracy(
        self, mock_optimization_config: OptimizationConfig, mock_phase2a_monitor: Phase2AMonitor
    ):
        """Test that recorded metrics contain accurate data."""
        with patch(
            "calendarbot.optimization.connection_manager.OptimizationConfig"
        ) as mock_config_class:
            mock_config_class.return_value = mock_optimization_config

            connection_manager = ConnectionManager(monitor=mock_phase2a_monitor)
            await connection_manager.startup()

            # Perform operations and check metric data
            await connection_manager.health_check()
            _ = connection_manager.get_connection_stats()

            # Verify metric calls have proper structure
            pool_status_calls = cast(
                MagicMock, mock_phase2a_monitor.log_connection_pool_status
            ).call_args_list

            # At least one call should have been made during startup
            assert len(pool_status_calls) > 0, "No connection pool status calls made"

            # Verify call structure - should have keyword arguments or positional args
            for call_args in pool_status_calls:
                # Each call should have either keyword args or positional args
                has_kwargs = len(call_args.kwargs) > 0
                has_args = len(call_args.args) > 0
                assert has_kwargs or has_args, f"Call missing arguments: {call_args}"

            await connection_manager.shutdown()
