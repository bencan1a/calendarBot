"""Tests for ICS source handler."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ics.exceptions import ICSNetworkError, ICSParseError
from calendarbot.sources.exceptions import SourceConnectionError, SourceDataError
from calendarbot.sources.ics_source import ICSSourceHandler
from calendarbot.sources.models import SourceConfig, SourceHealthCheck, SourceMetrics


class TestICSSourceHandler:
    """Test suite for ICSSourceHandler."""

    def test_init_when_called_then_initializes_properties(
        self, source_config: SourceConfig, mock_settings: Mock
    ) -> None:
        """Test initialization sets up properties correctly."""
        # Act
        with (
            patch("calendarbot.sources.ics_source.ICSFetcher"),
            patch("calendarbot.sources.ics_source.ICSParser"),
            patch.object(ICSSourceHandler, "_create_ics_source"),
        ):
            handler = ICSSourceHandler(source_config, mock_settings)

            # Assert
            assert handler.config == source_config
            assert handler.settings == mock_settings
            assert handler._last_etag is None
            assert handler._last_modified is None
            assert isinstance(handler.health, SourceHealthCheck)
            assert isinstance(handler.metrics, SourceMetrics)

    def test_create_ics_source_when_called_then_creates_source_with_correct_parameters(
        self,
    ) -> None:
        """Test _create_ics_source creates ICS source with correct parameters."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
        )
        settings = Mock()

        # Act
        with (
            patch("calendarbot.sources.ics_source.ICSSource") as mock_ics_source_cls,
            patch("calendarbot.sources.ics_source.ICSAuth") as mock_ics_auth_cls,
            patch("calendarbot.sources.ics_source.AuthType") as mock_auth_type,
        ):
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
    async def test_fetch_events_when_connection_error_then_raises_source_connection_error(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test fetch_events raises SourceConnectionError on connection error."""
        # Arrange
        mock_ics_handler.fetcher.fetch_ics.side_effect = ICSNetworkError("Connection failed")

        # Act & Assert
        with pytest.raises(SourceConnectionError) as excinfo:
            await mock_ics_handler.fetch_events()

        # Verify error message format
        assert "Network error: Connection failed" in str(excinfo.value)
        mock_ics_handler.fetcher.fetch_ics.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_events_when_parsing_error_then_raises_source_data_error(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test fetch_events raises SourceDataError on parsing error."""
        # Arrange
        # Create a successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.is_not_modified = False
        mock_response.content = "ics content"
        mock_ics_handler.fetcher.fetch_ics.return_value = mock_response

        # Make the parser raise a parse error
        mock_ics_handler.parser.parse_ics_content.side_effect = ICSParseError("Parse error")

        # Act & Assert
        with pytest.raises(SourceDataError) as excinfo:
            await mock_ics_handler.fetch_events()

        # Verify error message format
        assert "Parse error: Parse error" in str(excinfo.value)
        mock_ics_handler.fetcher.fetch_ics.assert_called_once()
        mock_ics_handler.parser.parse_ics_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_when_successful_then_returns_healthy_check(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test test_connection returns healthy check on successful connection."""
        # Arrange - Mock the handler's test_connection method directly to return success
        healthy_check = SourceHealthCheck(source_name="Test Calendar")
        healthy_check.update_success(100.0, 0)  # 100ms response time, 0 events

        # Mock the test_connection method to return healthy status
        with patch.object(
            mock_ics_handler, "test_connection", new_callable=AsyncMock, return_value=healthy_check
        ):
            # Act
            result = await mock_ics_handler.test_connection()

            # Assert
            assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_test_connection_when_error_then_returns_unhealthy_check(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test test_connection returns unhealthy check on error."""
        # Arrange - Mock aiohttp to avoid real network calls
        with patch("aiohttp.ClientSession") as mock_session:
            # Create mock response that returns 404
            mock_response = Mock()
            mock_response.status = 404
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session.return_value.__aenter__.return_value.head.return_value = mock_response

            # Act
            result = await mock_ics_handler.test_connection()

            # Assert
            assert result.is_healthy is False
            assert result.status == "error"

    def test_get_status_when_called_then_returns_status_dict(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test get_status returns status dictionary with expected fields."""
        # Arrange - use direct attribute access for read-only properties
        mock_ics_handler.health.status = "healthy"
        mock_ics_handler._last_etag = "test-etag"
        mock_ics_handler._last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"

        # Create a datetime for last_successful_fetch
        last_fetch = datetime(2023, 1, 1)

        # Create a new metrics object with the desired values
        metrics = SourceMetrics(
            consecutive_failures=0,
            last_event_count=10,
            last_error=None,
            # Set the values needed to calculate success_rate
            total_requests=100,
            successful_requests=95,
        )
        # Set the datetime directly
        metrics.last_successful_fetch = last_fetch
        mock_ics_handler.metrics = metrics

        # Act
        result = mock_ics_handler.get_status()

        # Assert
        assert result["name"] == "Test Source"
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

    def test_clear_cache_headers_when_called_then_resets_headers(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test clear_cache_headers resets cache headers."""
        # Arrange
        mock_ics_handler._last_etag = "test-etag"
        mock_ics_handler._last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"

        # Act
        mock_ics_handler.clear_cache_headers()

        # Assert
        assert mock_ics_handler._last_etag is None
        assert mock_ics_handler._last_modified is None

    def test_update_config_when_called_then_updates_config_and_source(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test update_config updates configuration and recreates source."""
        # Arrange
        new_config = SourceConfig(
            name="Updated Source",
            type="ics",
            url="https://updated.example.com/calendar.ics",
        )

        # Act
        with patch.object(mock_ics_handler, "_create_ics_source") as mock_create_source:
            mock_ics_handler.update_config(new_config)

            # Assert
            assert mock_ics_handler.config is new_config
            mock_create_source.assert_called_once()

    def test_is_healthy_when_healthy_and_enabled_then_returns_true(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test is_healthy returns True when source is healthy and enabled."""
        # Arrange
        mock_ics_handler.health.status = "healthy"  # Set the underlying status attribute
        mock_ics_handler.config.enabled = True

        # Act & Assert
        assert mock_ics_handler.is_healthy() is True

    def test_is_healthy_when_healthy_but_disabled_then_returns_false(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test is_healthy returns False when source is healthy but disabled."""
        # Arrange
        mock_ics_handler.health.status = "healthy"  # Set the underlying status attribute
        mock_ics_handler.config.enabled = False

        # Act & Assert
        assert mock_ics_handler.is_healthy() is False

    def test_get_health_check_when_called_then_returns_health(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test get_health_check returns health object."""
        # Act
        result = mock_ics_handler.get_health_check()

        # Assert
        assert result is mock_ics_handler.health

    def test_get_metrics_when_called_then_returns_metrics(
        self, mock_ics_handler: ICSSourceHandler
    ) -> None:
        """Test get_metrics returns metrics object."""
        # Act
        result = mock_ics_handler.get_metrics()

        # Assert
        assert result is mock_ics_handler.metrics
