"""Unit tests for ConnectionManager class."""

from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from calendarbot.config.optimization import OptimizationConfig
from calendarbot.optimization.connection_manager import (
    ConnectionManager,
    ConnectionManagerError,
    get_connection_manager,
    reset_connection_manager,
)


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(
            max_connections=50,
            max_connections_per_host=25,
            connection_ttl=300,
        )
        self.monitor = Mock(spec=Phase2AMonitor)
        self.manager = ConnectionManager(self.config, self.monitor)

    def teardown_method(self):
        """Clean up after tests."""
        reset_connection_manager()

    def test_init_with_defaults(self):
        """Test ConnectionManager initialization with default config and monitor."""
        manager = ConnectionManager()

        assert manager.config is not None
        assert manager.monitor is not None
        assert manager._startup_complete is False
        assert manager._shutdown_initiated is False
        assert manager._http_session is None
        assert manager._connector is None

    def test_init_with_custom_config_monitor(self):
        """Test ConnectionManager initialization with custom config and monitor."""
        assert self.manager.config == self.config
        assert self.manager.monitor == self.monitor
        assert self.manager._max_connections == 20  # Conservative limit applied
        assert self.manager._max_connections_per_host == 15  # Conservative limit applied

    def test_conservative_limits_applied(self):
        """Test that conservative universal limits are applied regardless of config."""
        high_config = OptimizationConfig(
            max_connections=1000,
            max_connections_per_host=100,  # Use max allowed value
        )
        manager = ConnectionManager(high_config)

        # Should cap at conservative limits
        assert manager._max_connections == 20
        assert manager._max_connections_per_host == 15

    @pytest.mark.asyncio
    async def test_startup_success(self):
        """Test successful ConnectionManager startup."""
        with (
            patch("aiohttp.TCPConnector") as mock_connector_class,
            patch("aiohttp.ClientSession") as mock_session_class,
        ):
            mock_connector = AsyncMock()
            mock_session = AsyncMock()
            mock_connector_class.return_value = mock_connector
            mock_session_class.return_value = mock_session

            await self.manager.startup()

            assert self.manager._startup_complete is True
            assert self.manager._connector == mock_connector
            assert self.manager._http_session == mock_session
            assert self.manager._connection_stats["sessions_created"] == 1
            assert self.manager._connection_stats["startup_time"] is not None

            # Verify monitor was called
            self.monitor.log_connection_pool_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_already_started(self):
        """Test startup when already started."""
        self.manager._startup_complete = True

        with patch("aiohttp.TCPConnector"), patch("aiohttp.ClientSession"):
            await self.manager.startup()

            # Should not create new connector/session
            assert self.manager._connector is None
            assert self.manager._http_session is None

    @pytest.mark.asyncio
    async def test_startup_failure(self):
        """Test ConnectionManager startup failure handling."""
        with patch("aiohttp.TCPConnector", side_effect=Exception("Connector failed")):
            with pytest.raises(ConnectionManagerError, match="Startup failed"):
                await self.manager.startup()

            assert self.manager._startup_complete is False
            assert self.manager._connector is None
            assert self.manager._http_session is None

    @pytest.mark.asyncio
    async def test_shutdown_success(self):
        """Test successful ConnectionManager shutdown."""
        # Set up as if started
        mock_session = AsyncMock()
        mock_connector = AsyncMock()
        self.manager._http_session = mock_session
        self.manager._connector = mock_connector
        self.manager._startup_complete = True

        await self.manager.shutdown()

        assert self.manager._shutdown_initiated is True
        assert self.manager._startup_complete is False
        assert self.manager._http_session is None
        assert self.manager._connector is None

        mock_session.close.assert_called_once()
        mock_connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_already_shutdown(self):
        """Test shutdown when already shutdown."""
        self.manager._shutdown_initiated = True
        mock_session = AsyncMock()
        self.manager._http_session = mock_session

        await self.manager.shutdown()

        # Should not call close again
        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_with_errors(self):
        """Test shutdown handles errors gracefully."""
        mock_session = AsyncMock()
        mock_session.close.side_effect = Exception("Close failed")
        self.manager._http_session = mock_session

        # Should not raise exception
        await self.manager.shutdown()

        assert self.manager._shutdown_initiated is True

    @pytest.mark.asyncio
    async def test_get_http_session_success(self):
        """Test successful HTTP session acquisition."""
        mock_session = AsyncMock()
        self.manager._http_session = mock_session
        self.manager._startup_complete = True

        session = await self.manager.get_http_session()

        assert session == mock_session
        assert self.manager._connection_stats["connections_acquired"] == 1

        # Verify monitor was called
        self.monitor.log_connection_acquisition.assert_called_once_with(
            wait_time=pytest.approx(0.0, abs=0.1),
            success=True,
            component="connection_manager",
        )

    @pytest.mark.asyncio
    async def test_get_http_session_not_ready(self):
        """Test HTTP session acquisition when not ready."""
        with pytest.raises(ConnectionManagerError, match="ConnectionManager not ready"):
            await self.manager.get_http_session()

    @pytest.mark.asyncio
    async def test_get_http_session_shutdown(self):
        """Test HTTP session acquisition when shutdown."""
        self.manager._startup_complete = True
        self.manager._shutdown_initiated = True

        with pytest.raises(ConnectionManagerError, match="ConnectionManager not ready"):
            await self.manager.get_http_session()

    @pytest.mark.asyncio
    async def test_get_http_session_no_session(self):
        """Test HTTP session acquisition when session is None."""
        self.manager._startup_complete = True
        self.manager._http_session = None

        with pytest.raises(ConnectionManagerError, match="HTTP session not available"):
            await self.manager.get_http_session()

    @pytest.mark.asyncio
    async def test_release_connection(self):
        """Test connection release."""
        await self.manager.release_connection()

        assert self.manager._connection_stats["connections_released"] == 1
        self.monitor.log_connection_release.assert_called_once_with(
            component="connection_manager",
        )

    def test_get_connection_stats_not_started(self):
        """Test connection stats when not started."""
        stats = self.manager.get_connection_stats()

        assert stats["status"] == "not_started"
        assert "error" in stats

    def test_get_connection_stats_active(self):
        """Test connection stats when active."""
        self.manager._startup_complete = True
        mock_connector = Mock()
        mock_connector._limit = 20
        mock_connector._limit_per_host = 15
        self.manager._connector = mock_connector
        self.manager._http_session = Mock()

        stats = self.manager.get_connection_stats()

        assert stats["status"] == "active"
        assert stats["startup_complete"] is True
        assert stats["max_connections"] == 20
        assert stats["max_connections_per_host"] == 15
        assert stats["session_available"] is True
        assert "statistics" in stats
        assert "connector" in stats

    def test_get_connection_stats_shutdown(self):
        """Test connection stats when shutdown."""
        self.manager._startup_complete = True
        self.manager._shutdown_initiated = True

        stats = self.manager.get_connection_stats()

        assert stats["status"] == "shutdown"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when everything is healthy."""
        self.manager._startup_complete = True
        mock_session = Mock()
        mock_session.closed = False
        self.manager._http_session = mock_session
        self.manager._connector = Mock()

        health = await self.manager.health_check()

        assert health["overall_healthy"] is True
        assert health["startup_complete"] is True
        assert health["session_available"] is True
        assert health["connector_available"] is True
        assert health["shutdown_initiated"] is False
        assert len(health["issues"]) == 0
        assert self.manager._connection_stats["last_health_check"] is not None

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_no_session(self):
        """Test health check when session is unavailable."""
        self.manager._startup_complete = True
        self.manager._http_session = None

        health = await self.manager.health_check()

        assert health["overall_healthy"] is False
        assert "HTTP session not available" in health["issues"]

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_closed_session(self):
        """Test health check when session is closed."""
        self.manager._startup_complete = True
        mock_session = Mock()
        mock_session.closed = True
        self.manager._http_session = mock_session
        self.manager._connector = Mock()

        health = await self.manager.health_check()

        assert health["overall_healthy"] is False
        assert "HTTP session is closed" in health["issues"]

    @pytest.mark.asyncio
    async def test_health_check_high_failure_rate(self):
        """Test health check with high failure rate."""
        self.manager._startup_complete = True
        self.manager._http_session = Mock()
        self.manager._http_session.closed = False
        self.manager._connector = Mock()

        # Set high failure rate
        self.manager._connection_stats["connections_acquired"] = 100
        self.manager._connection_stats["failed_acquisitions"] = 20  # 20% failure rate

        health = await self.manager.health_check()

        assert health["overall_healthy"] is False
        assert any("High failure rate" in issue for issue in health["issues"])

    @pytest.mark.asyncio
    async def test_close_all_connections(self):
        """Test close_all_connections is alias for shutdown."""
        with patch.object(self.manager, "shutdown", new_callable=AsyncMock) as mock_shutdown:
            await self.manager.close_all_connections()
            mock_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self):
        """Test cleanup on error during startup."""
        mock_session = AsyncMock()
        mock_connector = AsyncMock()
        self.manager._http_session = mock_session
        self.manager._connector = mock_connector

        await self.manager._cleanup_on_error()

        mock_session.close.assert_called_once()
        mock_connector.close.assert_called_once()
        assert self.manager._http_session is None
        assert self.manager._connector is None

    @pytest.mark.asyncio
    async def test_cleanup_on_error_with_exception(self):
        """Test cleanup on error handles exceptions."""
        mock_session = AsyncMock()
        mock_session.close.side_effect = Exception("Close failed")
        self.manager._http_session = mock_session

        # Should not raise exception
        await self.manager._cleanup_on_error()


class TestConnectionManagerGlobal:
    """Test global connection manager functions."""

    def teardown_method(self):
        """Clean up after tests."""
        reset_connection_manager()

    def test_get_connection_manager_singleton(self):
        """Test that get_connection_manager returns singleton."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

    def test_get_connection_manager_with_config(self):
        """Test get_connection_manager with custom config."""
        config = OptimizationConfig(max_connections=100)
        monitor = Mock(spec=Phase2AMonitor)

        manager = get_connection_manager(config, monitor)

        assert manager.config == config
        assert manager.monitor == monitor

    def test_reset_connection_manager(self):
        """Test reset_connection_manager."""
        manager1 = get_connection_manager()
        reset_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is not manager2


class TestConnectionManagerIntegration:
    """Integration tests for ConnectionManager with real aiohttp components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(
            max_connections=5,
            max_connections_per_host=3,
            connection_ttl=60,
        )
        self.monitor = Mock(spec=Phase2AMonitor)
        self.manager = ConnectionManager(self.config, self.monitor)

    async def cleanup_manager(self):
        """Helper to clean up manager."""
        if self.manager._startup_complete:
            await self.manager.shutdown()

    @pytest.mark.asyncio
    async def test_full_lifecycle_integration(self):
        """Test full ConnectionManager lifecycle with real aiohttp components."""
        try:
            # Startup
            await self.manager.startup()
            assert self.manager._startup_complete is True
            assert isinstance(self.manager._connector, aiohttp.TCPConnector)
            assert isinstance(self.manager._http_session, aiohttp.ClientSession)

            # Get session
            session = await self.manager.get_http_session()
            assert session is self.manager._http_session

            # Health check
            health = await self.manager.health_check()
            assert health["overall_healthy"] is True

            # Connection stats
            stats = self.manager.get_connection_stats()
            assert stats["status"] == "active"
            assert stats["session_available"] is True

        finally:
            await self.cleanup_manager()

    @pytest.mark.asyncio
    async def test_connector_configuration(self):
        """Test that TCPConnector is configured correctly."""
        try:
            await self.manager.startup()

            connector = self.manager._connector
            assert connector is not None
            assert getattr(connector, "_limit", None) == 5  # From config (under conservative limit)
            assert (
                getattr(connector, "_limit_per_host", None) == 3
            )  # From config (under conservative limit)
            assert getattr(connector, "_use_dns_cache", None) is True
            # Check that connector has expected type and basic functionality
            assert isinstance(connector, aiohttp.TCPConnector)

        finally:
            await self.cleanup_manager()

    @pytest.mark.asyncio
    async def test_session_timeout_configuration(self):
        """Test that ClientSession timeout is configured correctly."""
        try:
            await self.manager.startup()

            session = self.manager._http_session
            assert session is not None
            timeout = getattr(session, "timeout", None)
            if timeout:
                assert timeout.total == 30.0
                assert timeout.connect == 10.0

        finally:
            await self.cleanup_manager()

    @pytest.mark.asyncio
    async def test_multiple_session_acquisitions(self):
        """Test multiple session acquisitions return same session."""
        try:
            await self.manager.startup()

            session1 = await self.manager.get_http_session()
            session2 = await self.manager.get_http_session()

            assert session1 is session2
            assert self.manager._connection_stats["connections_acquired"] == 2

        finally:
            await self.cleanup_manager()

    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """Test integration with Phase2AMonitor."""
        try:
            await self.manager.startup()
            await self.manager.get_http_session()
            await self.manager.release_connection()
            await self.manager.health_check()

            # Verify monitor calls
            assert self.monitor.log_connection_pool_status.call_count >= 2
            self.monitor.log_connection_acquisition.assert_called()
            self.monitor.log_connection_release.assert_called()

        finally:
            await self.cleanup_manager()
