"""Shared fixtures for sources tests."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.sources.ics_source import ICSSourceHandler
from calendarbot.sources.models import SourceConfig, SourceHealthCheck, SourceMetrics


# Create an async context manager mock for the fetcher
class AsyncContextManagerMock(Mock):
    """Mock that supports async context manager protocol."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_settings() -> Mock:
    """Create mock settings for testing."""
    settings = Mock()
    settings.sources = {"ics": {"timeout": 30}}
    settings.max_retries = 3
    settings.retry_backoff_factor = 1.5
    return settings


@pytest.fixture
def source_config() -> SourceConfig:
    """Create a source configuration for testing."""
    return SourceConfig(
        name="Test Source",
        type="ics",
        url="https://example.com/calendar.ics",
        enabled=True,
    )


@pytest.fixture
def mock_fetcher() -> AsyncContextManagerMock:
    """Create a mock ICSFetcher that supports async context manager."""
    fetcher = AsyncContextManagerMock()
    fetcher.fetch_ics = AsyncMock()
    fetcher.test_connection = AsyncMock()
    fetcher.get_conditional_headers = Mock()
    return fetcher


@pytest.fixture
def mock_parser() -> Mock:
    """Create a mock ICSParser."""
    parser = Mock()
    parser.parse_ics_content = Mock()
    return parser


@pytest.fixture
def mock_ics_handler(
    source_config: SourceConfig,
    mock_settings: Mock,
    mock_fetcher: AsyncContextManagerMock,
    mock_parser: Mock,
) -> ICSSourceHandler:
    """Create an optimized ICSSourceHandler for testing."""
    with (
        patch("calendarbot.sources.ics_source.ICSFetcher", return_value=mock_fetcher),
        patch("calendarbot.sources.ics_source.ICSParser", return_value=mock_parser),
        patch.object(ICSSourceHandler, "_create_ics_source"),
        patch("calendarbot.sources.ics_source.logger"),  # Suppress logging
    ):
        handler = ICSSourceHandler(source_config, mock_settings)

        # Set mocks directly and reset to clear initialization calls
        handler.fetcher = mock_fetcher
        handler.parser = mock_parser
        mock_fetcher.reset_mock()
        mock_parser.reset_mock()

        return handler


@pytest.fixture
def mock_health_metrics() -> tuple[SourceHealthCheck, SourceMetrics]:
    """Create mock health check and metrics objects."""
    health = Mock(spec=SourceHealthCheck)
    health.status = "healthy"

    # Create a metrics object with pre-set values for testing
    metrics = SourceMetrics(
        consecutive_failures=0,
        last_event_count=10,
        last_error=None,
        total_requests=100,
        successful_requests=95,
    )
    metrics.last_successful_fetch = datetime(2023, 1, 1)

    return health, metrics
