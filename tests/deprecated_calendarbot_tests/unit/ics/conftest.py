"""Shared fixtures for ICS module tests.

This module provides common fixtures to reduce duplication across ICS test files
and improve test performance through fixture reuse.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ics.models import (
    AuthType,
    CalendarEvent,
    DateTimeInfo,
    ICSAuth,
    ICSParseResult,
    ICSResponse,
    ICSSource,
)
from calendarbot.sources.models import SourceConfig, SourceType

# ============================================================================
# Settings and Configuration Fixtures
# ============================================================================


@pytest.fixture
def test_settings():
    """Create mock settings object with common defaults."""
    settings = Mock()
    settings.app_name = "CalendarBot Test"
    settings.app_version = "1.0.0"
    settings.max_retries = 3
    settings.retry_backoff_factor = 1.5
    settings.cache_ttl = 3600
    settings.ics_enable_caching = True
    settings.ics_filter_busy_only = True
    settings.ics_expand_recurring = False
    settings.ics_refresh_interval = 300
    settings.ics_timeout = 30
    settings.ics_validate_ssl = True
    settings.enable_rrule_expansion = True
    settings.rrule_expansion_days = 365
    settings.rrule_max_occurrences = 1000
    return settings


@pytest.fixture
def basic_source_config():
    """Create basic ICS source configuration."""
    return SourceConfig(
        name="test_source",
        type=SourceType.ICS,
        url="https://example.com/calendar.ics",
        timeout=30,
        refresh_interval=300,
        enabled=True,
    )


@pytest.fixture
def auth_source_config():
    """Create ICS source configuration with authentication."""
    return SourceConfig(
        name="auth_source",
        type=SourceType.ICS,
        url="https://example.com/calendar.ics",
        auth_type="basic",
        auth_config={"username": "testuser", "password": "testpass"},
        timeout=30,
        refresh_interval=300,
        enabled=True,
    )


# ============================================================================
# ICS Model Fixtures
# ============================================================================


@pytest.fixture
def basic_ics_auth():
    """Create basic ICS authentication object."""
    return ICSAuth(type=AuthType.BASIC, username="testuser", password="testpass")


@pytest.fixture
def bearer_ics_auth():
    """Create bearer token ICS authentication object."""
    return ICSAuth(type=AuthType.BEARER, bearer_token="abc123token")


@pytest.fixture
def no_auth():
    """Create no authentication ICS auth object."""
    return ICSAuth(type=AuthType.NONE)


@pytest.fixture
def sample_ics_source(no_auth):
    """Create sample ICS source for testing."""
    return ICSSource(
        name="Test Source",
        url="https://example.com/calendar.ics",
        auth=no_auth,
        timeout=30,
        validate_ssl=True,
    )


@pytest.fixture
def sample_ics_content():
    """Provide sample ICS content for testing."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Company//Test Product//EN
BEGIN:VEVENT
UID:test-event-123
DTSTART:20250817T140000Z
DTEND:20250817T150000Z
SUMMARY:Test Meeting
DESCRIPTION:This is a test meeting description
LOCATION:Conference Room A
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""


# ============================================================================
# Calendar Event Fixtures
# ============================================================================


@pytest.fixture
def sample_events():
    """Create sample calendar events."""
    now = datetime.now()
    return [
        CalendarEvent(
            id="event1",
            subject="Test Event 1",
            start=DateTimeInfo(date_time=now),
            end=DateTimeInfo(date_time=now + timedelta(hours=1)),
        ),
        CalendarEvent(
            id="event2",
            subject="Test Event 2",
            start=DateTimeInfo(date_time=now + timedelta(hours=2)),
            end=DateTimeInfo(date_time=now + timedelta(hours=3)),
        ),
    ]


@pytest.fixture
def sample_parse_result(sample_events):
    """Create sample ICS parse result."""
    result = Mock(spec=ICSParseResult)
    result.success = True
    result.events = sample_events
    result.calendar_name = "Test Calendar"
    result.event_count = len(sample_events)
    result.total_components = len(sample_events)
    result.recurring_event_count = 0
    result.warnings = []
    result.error_message = None
    return result


# ============================================================================
# Mock Response Fixtures
# ============================================================================


@pytest.fixture
def successful_ics_response(sample_ics_content):
    """Create successful ICS response mock."""
    response = Mock(spec=ICSResponse)
    response.success = True
    response.is_not_modified = False
    response.content = sample_ics_content
    response.status_code = 200
    response.etag = '"test123"'
    response.last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"
    response.headers = {"content-type": "text/calendar"}
    return response


@pytest.fixture
def not_modified_response():
    """Create 304 Not Modified response mock."""
    response = Mock(spec=ICSResponse)
    response.success = True
    response.is_not_modified = True
    response.status_code = 304
    response.content = None
    response.etag = '"cached123"'
    response.last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"
    response.headers = {}
    return response


@pytest.fixture
def failed_ics_response():
    """Create failed ICS response mock."""
    response = Mock()
    response.success = False
    response.is_not_modified = False
    response.error_message = "Network timeout"
    response.status_code = None
    response.content = None
    response.etag = None
    response.last_modified = None
    response.headers = {}
    return response


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_ics_fetcher(successful_ics_response):
    """Create optimized ICS fetcher mock."""
    fetcher = AsyncMock()

    # Pre-configure common async context manager behavior
    fetcher.__aenter__.return_value = fetcher
    fetcher.__aexit__.return_value = None
    fetcher.is_closed = False

    # Pre-configure common methods with successful response
    fetcher.fetch_ics = AsyncMock(return_value=successful_ics_response)
    fetcher.get_conditional_headers = Mock(return_value={})
    fetcher.test_connection = AsyncMock(return_value=True)

    return fetcher


@pytest.fixture
def mock_ics_parser():
    """Create optimized ICS parser mock."""
    parser = Mock()

    # Pre-configure common methods
    parser.validate_ics_content = Mock(return_value=True)
    parser.filter_busy_events = Mock(side_effect=lambda events: events)

    return parser


@pytest.fixture
def mock_fetcher_class(mock_ics_fetcher):
    """Create mock fetcher class that returns configured fetcher."""
    with patch("calendarbot.sources.ics_source.ICSFetcher") as mock_class:
        mock_class.return_value = mock_ics_fetcher
        yield mock_class


@pytest.fixture
def mock_parser_class(mock_ics_parser):
    """Create mock parser class that returns configured parser."""
    with patch("calendarbot.sources.ics_source.ICSParser") as mock_class:
        mock_class.return_value = mock_ics_parser
        yield mock_class


# ============================================================================
# Combined Service Fixtures
# ============================================================================


@pytest.fixture
def ics_service_mocks(mock_fetcher_class, mock_parser_class, mock_ics_fetcher, mock_ics_parser):
    """Provide all ICS service mocks in one fixture."""
    return {
        "fetcher_class": mock_fetcher_class,
        "parser_class": mock_parser_class,
        "fetcher": mock_ics_fetcher,
        "parser": mock_ics_parser,
    }


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def mock_time():
    """Mock time.time() to return consistent value."""
    with patch("time.time", return_value=1000.0):
        yield


@pytest.fixture
def mock_asyncio_sleep():
    """Mock asyncio.sleep to speed up tests."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield


@pytest.fixture
def suppress_logging():
    """Suppress log output during tests for cleaner output."""
    with (
        patch("calendarbot.ics.parser.logger"),
        patch("calendarbot.ics.fetcher.logger"),
        patch("calendarbot.sources.ics_source.logger"),
    ):
        yield


@pytest.fixture
def security_logger_mock():
    """Mock security event logger."""
    with (
        patch("calendarbot.ics.parser.SecurityEventLogger") as mock_logger,
        patch("calendarbot.ics.fetcher.SecurityEventLogger"),
    ):
        yield mock_logger


# ============================================================================
# ICS Fetcher Instance Fixtures
# ============================================================================


@pytest.fixture
def fetcher_instance(test_settings):
    """Create a real ICS fetcher instance for testing."""
    from calendarbot.ics.fetcher import ICSFetcher

    return ICSFetcher(test_settings)


@pytest.fixture
def fetcher(test_settings):
    """Create a real ICS fetcher instance for SSRF and validation tests."""
    from calendarbot.ics.fetcher import ICSFetcher

    return ICSFetcher(test_settings)


@pytest.fixture
def fetcher_with_mock_client(test_settings, mock_http_response):
    """Create ICS fetcher with mocked HTTP client."""
    from calendarbot.ics.fetcher import ICSFetcher

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_http_response

        fetcher = ICSFetcher(test_settings)
        return fetcher
        yield mock_logger
