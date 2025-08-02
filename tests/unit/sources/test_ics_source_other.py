"""Tests for ICS source handler."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from icalendar import Calendar, Event

from calendarbot.sources.exceptions import SourceConnectionError, SourceDataError
from calendarbot.sources.ics_source import ICSSourceHandler
from calendarbot.sources.models import SourceConfig, SourceHealthCheck, SourceMetrics


# Create an async context manager mock for the fetcher
class AsyncContextManagerMock(Mock):
    """Mock that supports async context manager protocol."""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestICSSourceHandler:
    """Test suite for ICSSourceHandler."""

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings for testing."""
        settings = Mock()
        settings.sources = {"ics": {"timeout": 30}}
        return settings

    @pytest.fixture
    def source_config(self) -> SourceConfig:
        """Create a source configuration for testing."""
        return SourceConfig(
            name="Test Calendar",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )

    @pytest.fixture
    def mock_fetcher(self) -> AsyncContextManagerMock:
        """Create a mock ICSFetcher that supports async context manager."""
        fetcher = AsyncContextManagerMock()
        fetcher.fetch_ics = AsyncMock()
        fetcher.test_connection = AsyncMock()
        fetcher.get_conditional_headers = Mock()
        return fetcher

    @pytest.fixture
    def mock_parser(self) -> Mock:
        """Create a mock ICSParser."""
        parser = Mock()
        parser.parse_ics_content = Mock()
        return parser

    @pytest.fixture
    def handler(self, source_config: SourceConfig, mock_settings: Mock, 
                mock_fetcher: AsyncContextManagerMock, mock_parser: Mock) -> ICSSourceHandler:
        """Create an ICSSourceHandler for testing."""
        with patch("calendarbot.sources.ics_source.ICSFetcher", return_value=mock_fetcher), \
             patch("calendarbot.sources.ics_source.ICSParser", return_value=mock_parser), \
             patch.object(ICSSourceHandler, "_create_ics_source"):
            
            handler = ICSSourceHandler(source_config, mock_settings)
            
            # Set mocks directly
            handler.fetcher = mock_fetcher
            handler.parser = mock_parser
            
            # Reset mocks to clear initialization calls
            mock_fetcher.reset_mock()
            mock_parser.reset_mock()
            
            return handler

    def test_init_when_called_then_initializes_properties(self, source_config: SourceConfig, mock_settings: Mock) -> None:
        """Test initialization sets up properties correctly."""
        # Act
        with patch("calendarbot.sources.ics_source.ICSFetcher"), \
             patch("calendarbot.sources.ics_source.ICSParser"), \
             patch.object(ICSSourceHandler, "_create_ics_source"):
            
            handler = ICSSourceHandler(source_config, mock_settings)
            
            # Assert
            assert handler.config == source_config
            assert handler.settings == mock_settings
            assert handler._last_etag is None
            assert handler._last_modified is None
            assert isinstance(handler.health, SourceHealthCheck)
            assert isinstance(handler.metrics, SourceMetrics)

    def test_create_ics_source_when_called_then_creates_source_with_correct_parameters(self) -> None:
        """Test _create_ics_source creates ICS source with correct parameters."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
        )
        settings = Mock()
        
        # Act
        with patch("calendarbot.sources.ics_source.ICSSource") as mock_ics_source_cls, \
             patch("calendarbot.sources.ics_source.ICSAuth") as mock_ics_auth_cls, \
             patch("calendarbot.sources.ics_source.AuthType") as mock_auth_type:
            
            mock_auth_type.NONE = "none"
            mock_auth = Mock()
            mock_ics_auth_cls.return_value = mock_auth
            
            # Create a new handler directly to test _create_ics_source
            handler = ICSSourceHandler.__new__(ICSSourceHandler)
            handler.config = config
            handler.settings = settings
            
            # Call the method directly
            result = handler._create_ics_source()
            
            # Assert
            mock_ics_source_cls.assert_called_once()
            mock_ics_auth_cls.assert_called_once()
            assert result is mock_ics_source_cls.return_value

    @pytest.mark.asyncio
    async def test_fetch_events_when_connection_error_then_raises_source_connection_error(self, handler: ICSSourceHandler) -> None:
        """Test fetch_events raises SourceConnectionError on connection error."""
        # Arrange
        from calendarbot.ics.exceptions import ICSNetworkError
        handler.fetcher.fetch_ics.side_effect = ICSNetworkError("Connection failed")
        
        # Act & Assert
        with pytest.raises(SourceConnectionError) as excinfo:
            await handler.fetch_events()
        
        # Verify error message format
        assert "Network error: Connection failed" in str(excinfo.value)
        handler.fetcher.fetch_ics.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_events_when_parsing_error_then_raises_source_data_error(self, handler: ICSSourceHandler) -> None:
        """Test fetch_events raises SourceDataError on parsing error."""
        # Arrange
        from calendarbot.ics.exceptions import ICSParseError
        
        # Create a successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.is_not_modified = False
        mock_response.content = "ics content"
        handler.fetcher.fetch_ics.return_value = mock_response
        
        # Make the parser raise a parse error
        handler.parser.parse_ics_content.side_effect = ICSParseError("Parse error")
        
        # Act & Assert
        with pytest.raises(SourceDataError) as excinfo:
            await handler.fetch_events()
        
        # Verify error message format
        assert "Parse error: Parse error" in str(excinfo.value)
        handler.fetcher.fetch_ics.assert_called_once()
        handler.parser.parse_ics_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_when_successful_then_returns_healthy_check(self, handler: ICSSourceHandler) -> None:
        """Test test_connection returns healthy check on successful connection."""
        # Arrange
        handler.fetcher.test_connection.return_value = True
        
        # Act
        with patch.object(handler, "fetch_events", return_value=[{"event": "data"}]), \
             patch("calendarbot.sources.ics_source.time.time", side_effect=[0, 0.1, 0.2, 0.3]):
            
            # Create a new health check with the status set to healthy
            handler.health = SourceHealthCheck(status="healthy")
            
            result = await handler.test_connection()
        
        # Assert
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_test_connection_when_error_then_returns_unhealthy_check(self, handler: ICSSourceHandler) -> None:
        """Test test_connection returns unhealthy check on error."""
        # Arrange
        # Make the test_connection method raise an exception
        handler.fetcher.test_connection.side_effect = Exception("Connection failed")
        
        # Act
        result = await handler.test_connection()
        
        # Assert
        assert result.is_healthy is False
        assert result.status == "error"  # Check status instead of object identity

    def test_record_success_when_called_then_updates_metrics_and_health(self, handler: ICSSourceHandler) -> None:
        """Test _record_success updates metrics and health."""
        # Arrange
        handler.metrics = Mock(spec=SourceMetrics)
        handler.health = Mock(spec=SourceHealthCheck)
        
        # Act
        handler._record_success(150.5, 10)
        
        # Assert
        handler.metrics.record_success.assert_called_once_with(150.5, 10)
        handler.health.update_success.assert_called_once_with(150.5, 10)

    def test_record_failure_when_called_then_updates_metrics_and_health(self, handler: ICSSourceHandler) -> None:
        """Test _record_failure updates metrics and health."""
        # Arrange
        handler.metrics = Mock(spec=SourceMetrics)
        handler.health = Mock(spec=SourceHealthCheck)
        
        # Act
        handler._record_failure("Test error")
        
        # Assert
        handler.metrics.record_failure.assert_called_once_with("Test error")
        handler.health.update_error.assert_called_once_with("Test error")

    def test_raise_connection_error_when_called_then_records_failure_and_raises(self, handler: ICSSourceHandler) -> None:
        """Test _raise_connection_error records failure and raises error."""
        # Arrange
        handler._record_failure = Mock()
        
        # Act & Assert
        with pytest.raises(SourceConnectionError) as excinfo:
            handler._raise_connection_error(f"Connection error for {handler.config.name}")
        
        # Verify error message and source name
        assert handler.config.name in str(excinfo.value)
        handler._record_failure.assert_called_once()

    def test_raise_data_error_when_called_then_records_failure_and_raises(self, handler: ICSSourceHandler) -> None:
        """Test _raise_data_error records failure and raises error."""
        # Arrange
        handler._record_failure = Mock()
        
        # Act & Assert
        with pytest.raises(SourceDataError) as excinfo:
            handler._raise_data_error(f"Data error for {handler.config.name}")
        
        # Verify error message and source name
        assert handler.config.name in str(excinfo.value)
        handler._record_failure.assert_called_once()

    def test_get_status_when_called_then_returns_status_dict(self, handler: ICSSourceHandler) -> None:
        """Test get_status returns status dictionary with expected fields."""
        # Arrange - use direct attribute access for read-only properties
        handler.health.status = "healthy"
        handler._last_etag = "test-etag"
        handler._last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"
        
        # Create a datetime for last_successful_fetch
        last_fetch = datetime(2023, 1, 1)
        
        # Create a new metrics object with the desired values
        metrics = SourceMetrics(
            consecutive_failures=0,
            last_event_count=10,
            last_error=None,
            # Set the values needed to calculate success_rate
            total_requests=100,
            successful_requests=95
        )
        # Set the datetime directly
        metrics.last_successful_fetch = last_fetch
        handler.metrics = metrics
        
        # Act
        result = handler.get_status()
        
        # Assert
        assert result["name"] == "Test Calendar"
        assert result["type"] == "ics"
        assert result["enabled"] is True
        assert result["url"] == "https://example.com/calendar.ics"
        assert result["health_status"] == "healthy"
        assert result["last_successful_fetch"] == last_fetch
        assert result["success_rate"] == 95.0
        assert result["consecutive_failures"] == 0
        assert result["last_event_count"] == 10
        assert result["last_error"] is None
        assert result["cache_headers"]["etag"] == "test-etag"
        assert result["cache_headers"]["last_modified"] == "Wed, 21 Oct 2015 07:28:00 GMT"

    def test_clear_cache_headers_when_called_then_resets_headers(self, handler: ICSSourceHandler) -> None:
        """Test clear_cache_headers resets cache headers."""
        # Arrange
        handler._last_etag = "test-etag"
        handler._last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"
        
        # Act
        handler.clear_cache_headers()
        
        # Assert
        assert handler._last_etag is None
        assert handler._last_modified is None

    def test_update_config_when_called_then_updates_config_and_source(self, handler: ICSSourceHandler) -> None:
        """Test update_config updates configuration and recreates source."""
        # Arrange
        new_config = SourceConfig(
            name="Updated Source",
            type="ics",
            url="https://updated.example.com/calendar.ics",
        )
        
        # Act
        with patch.object(handler, "_create_ics_source") as mock_create_source:
            handler.update_config(new_config)
            
            # Assert
            assert handler.config is new_config
            mock_create_source.assert_called_once()

    def test_is_healthy_when_healthy_and_enabled_then_returns_true(self, handler: ICSSourceHandler) -> None:
        """Test is_healthy returns True when source is healthy and enabled."""
        # Arrange
        handler.health.status = "healthy"  # Set the underlying status attribute
        handler.config.enabled = True
        
        # Act & Assert
        assert handler.is_healthy() is True

    def test_is_healthy_when_healthy_but_disabled_then_returns_false(self, handler: ICSSourceHandler) -> None:
        """Test is_healthy returns False when source is healthy but disabled."""
        # Arrange
        handler.health.status = "healthy"  # Set the underlying status attribute
        handler.config.enabled = False
        
        # Act & Assert
        assert handler.is_healthy() is False

    def test_get_health_check_when_called_then_returns_health(self, handler: ICSSourceHandler) -> None:
        """Test get_health_check returns health object."""
        # Act
        result = handler.get_health_check()
        
        # Assert
        assert result is handler.health

    def test_get_metrics_when_called_then_returns_metrics(self, handler: ICSSourceHandler) -> None:
        """Test get_metrics returns metrics object."""
        # Act
        result = handler.get_metrics()
        
        # Assert
        assert result is handler.metrics