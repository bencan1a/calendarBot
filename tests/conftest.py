"""Optimized test configuration with lightweight fixtures for fast execution."""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest


# Fast, lightweight test settings fixture
@pytest.fixture
def test_settings():
    """Create lightweight test settings without file I/O."""

    class MockSettings:
        def __init__(self):
            # Core settings
            self.ics_url = "http://example.com/test.ics"
            self.ics_timeout = 10
            self.ics_refresh_interval = 300
            self.cache_ttl = 3600
            self.refresh_interval = 60
            self.max_retries = 2
            self.retry_backoff_factor = 1.0
            self.request_timeout = 5
            self.app_name = "CalendarBot-Test"

            # Temporary paths for isolation
            self.data_dir = Path(tempfile.mkdtemp())
            self.config_dir = self.data_dir / "config"
            self.cache_dir = self.data_dir / "cache"

            # Database file path
            self.database_file = self.data_dir / "test_cache.db"

            # Test optimizations
            self.auto_kill_existing = False
            self.display_enabled = False

            # Logging
            self.log_level = "INFO"
            self.log_file = None

            # Display settings
            self.display_type = "console"

            # Web settings
            self.web_host = "127.0.0.1"
            self.web_port = 8998
            self.web_theme = "4x8"

    return MockSettings()


# Lightweight event fixtures for testing
@pytest.fixture
def sample_events():
    """Create minimal test events without heavy processing."""
    from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus

    now = datetime.now()

    return [
        CalendarEvent(
            id="test_event_1",
            subject="Test Meeting",
            body_preview="Test meeting body",
            start=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=2), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
        ),
        CalendarEvent(
            id="test_event_2",
            subject="All Day Event",
            body_preview="All day test",
            start=DateTimeInfo(date_time=now.replace(hour=0), time_zone="UTC"),
            end=DateTimeInfo(date_time=now.replace(hour=23), time_zone="UTC"),
            is_all_day=True,
            show_as=EventStatus.FREE,
            is_cancelled=False,
            is_organizer=False,
        ),
    ]


# Lightweight cache manager mock
@pytest.fixture
def mock_cache_manager():
    """Create lightweight cache manager mock."""
    mock = AsyncMock()
    mock.initialize.return_value = True
    mock.is_cache_fresh.return_value = True
    mock.get_todays_cached_events.return_value = []
    mock.cache_events.return_value = True
    mock.cleanup_old_events.return_value = 0

    # Mock cache status
    mock_status = MagicMock()
    mock_status.last_update = datetime.now()
    mock_status.is_stale = False
    mock.get_cache_status.return_value = mock_status

    # Mock cache summary
    mock.get_cache_summary.return_value = {"total_events": 5, "is_fresh": True}

    return mock


# Real cache manager fixture for integration tests
@pytest.fixture
def cache_manager(test_settings, event_loop):
    """Create real CacheManager instance for testing."""
    from calendarbot.cache.manager import CacheManager

    cache_mgr = CacheManager(test_settings)

    # Initialize synchronously using event loop
    event_loop.run_until_complete(cache_mgr.initialize())

    yield cache_mgr

    # Cleanup
    try:
        event_loop.run_until_complete(cache_mgr.clear_cache())
        if hasattr(cache_mgr, "db") and cache_mgr.db:
            event_loop.run_until_complete(cache_mgr.db.close())
    except Exception:
        pass  # Ignore cleanup errors


# Alias for existing sample_events fixture
@pytest.fixture
def sample_calendar_events(sample_events):
    """Alias for sample_events to match test expectations."""
    return sample_events


# Test database with populated data
@pytest.fixture
def populated_test_database(test_settings, sample_events, event_loop):
    """Create test database with sample data."""
    from calendarbot.cache.manager import CacheManager

    # Create cache manager with test database
    cache_mgr = CacheManager(test_settings)
    event_loop.run_until_complete(cache_mgr.initialize())

    # Populate with sample data
    event_loop.run_until_complete(cache_mgr.cache_events(sample_events))

    # Create mock database object for compatibility
    class MockTestDatabase:
        def __init__(self, settings, db, cache_manager):
            self.settings = settings
            self.db = db
            self.cache_manager = cache_manager

    test_db = MockTestDatabase(test_settings, cache_mgr.db, cache_mgr)

    yield test_db

    # Cleanup
    try:
        event_loop.run_until_complete(cache_mgr.clear_cache())
        event_loop.run_until_complete(cache_mgr.db.close())
    except Exception:
        pass


# Stale cache database for freshness testing
@pytest.fixture
def stale_cache_database(test_settings, sample_events, event_loop):
    """Create test database with stale data."""
    from calendarbot.cache.manager import CacheManager

    # Create cache manager with test database
    cache_mgr = CacheManager(test_settings)
    event_loop.run_until_complete(cache_mgr.initialize())

    # Populate with sample data and record metadata
    event_loop.run_until_complete(cache_mgr.cache_events(sample_events))
    event_loop.run_until_complete(cache_mgr._update_fetch_metadata(success=True))

    # Manually update database to make cache stale
    old_timestamp = datetime.now() - timedelta(hours=25)  # Older than cache_ttl (24 hours)
    stale_timestamp_str = old_timestamp.isoformat()

    # Update cache metadata to make cache stale
    async def make_stale():
        # Use the correct API method and metadata field for cache freshness
        await cache_mgr.db.update_cache_metadata(last_successful_fetch=stale_timestamp_str)

    event_loop.run_until_complete(make_stale())

    # Create mock database object for compatibility
    class MockStaleDatabase:
        def __init__(self, settings, db, cache_manager):
            self.settings = settings
            self.db = db
            self.cache_manager = cache_manager

    stale_db = MockStaleDatabase(test_settings, cache_mgr.db, cache_mgr)

    yield stale_db

    # Cleanup
    try:
        event_loop.run_until_complete(cache_mgr.clear_cache())
        event_loop.run_until_complete(cache_mgr.db.close())
    except Exception:
        pass


# Performance test database
@pytest.fixture
def performance_test_database(test_settings, event_loop):
    """Create test database optimized for performance testing."""
    from calendarbot.cache.manager import CacheManager
    from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus

    # Create cache manager
    cache_mgr = CacheManager(test_settings)
    event_loop.run_until_complete(cache_mgr.initialize())

    # Create large dataset for performance testing
    now = datetime.now()
    large_events = []

    for i in range(100):  # Create 100 test events
        event = CalendarEvent(
            id=f"perf_event_{i}",
            subject=f"Performance Test Event {i}",
            body_preview=f"Event {i} for performance testing",
            start=DateTimeInfo(date_time=now + timedelta(hours=i), time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=i + 1), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=None,
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=False,
            last_modified_date_time=now,
        )
        large_events.append(event)

    # Populate database
    event_loop.run_until_complete(cache_mgr.cache_events(large_events))

    # Create mock database object
    class MockPerformanceDatabase:
        def __init__(self, settings, db, cache_manager):
            self.settings = settings
            self.db = db
            self.cache_manager = cache_manager

    perf_db = MockPerformanceDatabase(test_settings, cache_mgr.db, cache_mgr)

    yield perf_db

    # Cleanup
    try:
        event_loop.run_until_complete(cache_mgr.clear_cache())
        event_loop.run_until_complete(cache_mgr.db.close())
    except Exception:
        pass


# Lightweight source manager mock
@pytest.fixture
def mock_source_manager():
    """Create lightweight source manager mock."""
    mock = AsyncMock()
    mock.initialize.return_value = True
    mock.fetch_and_cache_events.return_value = True
    mock.is_healthy.return_value = True

    # Mock health check
    mock_health = MagicMock()
    mock_health.is_healthy = True
    mock_health.status_message = "All sources healthy"
    mock.health_check.return_value = mock_health

    # Mock source info
    mock_info = MagicMock()
    mock_info.status = "healthy"
    mock_info.url = "http://example.com/test.ics"
    mock_info.is_configured = True
    mock.get_source_info.return_value = mock_info

    return mock


# Real source manager fixture for integration tests
@pytest.fixture
def source_manager(test_settings, event_loop):
    """Create real SourceManager instance for testing."""
    from calendarbot.sources.manager import SourceManager

    # Create source manager without cache manager for basic tests
    source_mgr = SourceManager(test_settings, None)

    yield source_mgr

    # Cleanup
    try:
        event_loop.run_until_complete(source_mgr.cleanup())
    except Exception:
        pass  # Ignore cleanup errors


# Lightweight display manager mock
@pytest.fixture
def mock_display_manager():
    """Create lightweight display manager mock."""
    mock = MagicMock()
    # Use AsyncMock for async methods that are awaited in CalendarBot
    mock.display_events = AsyncMock(return_value=True)
    mock.display_error = AsyncMock(return_value=True)
    return mock


# In-memory database for cache tests
@pytest.fixture
def memory_db_path():
    """Return in-memory SQLite database path."""
    return ":memory:"


# Simple ICS content for parser tests
@pytest.fixture
def sample_ics_content():
    """Create minimal valid ICS content."""
    now = datetime.now()
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test Calendar//EN
BEGIN:VEVENT
UID:test-event-1@example.com
DTSTART:{now.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{(now + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Test Event
DESCRIPTION:Test event description
END:VEVENT
END:VCALENDAR"""


# Mock HTTP responses for fetcher tests
@pytest.fixture
def mock_http_response():
    """Create mock HTTP response."""
    mock = MagicMock()
    mock.status_code = 200
    mock.text = "Mock ICS content"
    mock.headers = {"content-type": "text/calendar"}
    mock.raise_for_status = MagicMock()
    return mock


# Performance testing utilities
@pytest.fixture
def performance_tracker():
    """Simple performance tracking for test optimization."""

    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}

        def start_timer(self, name: str):
            import time

            self.metrics[name] = {"start": time.time()}

        def end_timer(self, name: str):
            import time

            if name in self.metrics:
                self.metrics[name]["duration"] = time.time() - self.metrics[name]["start"]

        def get_duration(self, name: str) -> float:
            return self.metrics.get(name, {}).get("duration", 0.0)

        def assert_performance(self, name: str, max_duration: float):
            duration = self.get_duration(name)
            assert (
                duration <= max_duration
            ), f"{name} took {duration:.3f}s, expected <= {max_duration}s"

    return PerformanceTracker()


# Configure pytest for optimized async testing
def pytest_configure(config):
    """Configure pytest with optimized markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests")
    config.addinivalue_line("markers", "critical_path: Core functionality tests")
    config.addinivalue_line("markers", "smoke: Basic smoke tests")


# Ensure clean test isolation
@pytest.fixture(autouse=True)
def clean_test_environment():
    """Ensure clean test environment for each test."""
    # Reset any global state if needed
    yield
    # Cleanup after test
    pass
