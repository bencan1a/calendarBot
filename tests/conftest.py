"""Optimized test configuration with lightweight fixtures for fast execution."""

import asyncio
import contextlib
import gc
import logging
import shutil
import sys
import tempfile
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psutil
import pytest

from calendarbot.cache.manager import CacheManager
from calendarbot.config.settings import EpaperConfiguration
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus
from calendarbot.settings.models import (
    ConflictResolutionSettings,
    DisplaySettings,
    EventFilterSettings,
    FilterPattern,
    SettingsData,
)
from calendarbot.sources.manager import SourceManager

# Global resource tracking for cleanup - using weak references to avoid memory leaks
_test_resources: list[Any] = []
_temp_directories: list[Path] = []
_active_mocks: list[Any] = []


# Fast, lightweight test settings fixture
@pytest.fixture
def test_settings() -> Any:
    """Create lightweight test settings without file I/O."""

    class MockSettings:
        def __init__(self) -> None:
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

            # Temporary paths for isolation - use memory paths when possible
            self.data_dir = Path(tempfile.mkdtemp(prefix="test_"))
            self.config_dir = self.data_dir / "config"
            self.cache_dir = self.data_dir / "cache"

            # Database file path - use in-memory for tests
            self.database_file = ":memory:"

            # Test optimizations
            self.auto_kill_existing = False
            self.display_enabled = False

            # Logging
            self.log_level = "ERROR"  # Reduce log noise
            self.log_file = None

            # Display settings
            self.display_type = "console"

            # Missing display dimensions that tests expect
            self.compact_display_width = 800
            self.compact_display_height = 480
            self.display_width = 1024
            self.display_height = 768

            # E-Paper configuration (matches CalendarBotSettings structure)
            self.epaper = EpaperConfiguration()

            # Web settings
            self.web_host = "127.0.0.1"
            self.web_port = 8998
            self.web_layout = "4x8"

        def cleanup(self) -> None:
            """Clean up temporary resources."""
            try:
                if (
                    hasattr(self, "data_dir")
                    and self.data_dir != Path(":memory:")
                    and self.data_dir.exists()
                ):
                    shutil.rmtree(self.data_dir, ignore_errors=True)
            except Exception:
                pass

    settings = MockSettings()
    register_test_resource(settings.cleanup)
    register_temp_directory(settings.data_dir)
    return settings


# Lightweight event fixtures for testing
@pytest.fixture
def sample_events() -> list[Any]:
    """Create minimal test events without heavy processing."""
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
def mock_cache_manager() -> AsyncMock:
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

    # Register for cleanup
    register_mock_for_cleanup(mock)
    return mock


# Real cache manager fixture for integration tests
@pytest.fixture
async def cache_manager(test_settings: Any) -> AsyncGenerator[Any, None]:
    """Create real CacheManager instance for testing."""
    cache_mgr = CacheManager(test_settings)

    try:
        # Initialize asynchronously
        await cache_mgr.initialize()

        yield cache_mgr

    finally:
        # Cleanup - ensure this always runs
        try:
            if hasattr(cache_mgr, "clear_cache"):
                await cache_mgr.clear_cache()
            if hasattr(cache_mgr, "db") and cache_mgr.db and hasattr(cache_mgr.db, "close"):
                await cache_mgr.db.close()
            # Clear any remaining references
            if hasattr(cache_mgr, "_db"):
                cache_mgr._db = None
        except Exception as e:
            logging.debug(f"Cache cleanup failed: {e}")


# Alias for existing sample_events fixture
@pytest.fixture
def sample_calendar_events(sample_events: list[Any]) -> list[Any]:
    """Alias for sample_events to match test expectations."""
    return sample_events


# Test database with populated data
@pytest.fixture
async def populated_test_database(
    test_settings: Any, sample_events: list[Any]
) -> AsyncGenerator[Any, None]:
    """Create test database with sample data."""
    cache_mgr = None
    try:
        # Create cache manager with test database
        cache_mgr = CacheManager(test_settings)
        await cache_mgr.initialize()

        # Populate with sample data
        await cache_mgr.cache_events(sample_events)

        # Create mock database object for compatibility
        class MockTestDatabase:
            def __init__(self, settings: Any, db: Any, cache_manager: Any) -> None:
                self.settings = settings
                self.db = db
                self.cache_manager = cache_manager

            def cleanup(self) -> None:
                """Cleanup method for resource tracking."""
                self.settings = None
                self.db = None
                self.cache_manager = None

        test_db = MockTestDatabase(test_settings, cache_mgr.db, cache_mgr)
        register_test_resource(test_db.cleanup)

        yield test_db

    finally:
        # Cleanup
        if cache_mgr:
            try:
                await cache_mgr.clear_cache()
                if hasattr(cache_mgr, "db") and cache_mgr.db and hasattr(cache_mgr.db, "close"):
                    await cache_mgr.db.close()
            except Exception as e:
                logging.debug(f"Test database cleanup failed: {e}")


# Stale cache database for freshness testing
@pytest.fixture
async def stale_cache_database(
    test_settings: Any, sample_events: list[Any]
) -> AsyncGenerator[Any, None]:
    """Create test database with stale data."""
    cache_mgr = None
    try:
        # Create cache manager with test database
        cache_mgr = CacheManager(test_settings)
        await cache_mgr.initialize()

        # Populate with sample data and record metadata
        await cache_mgr.cache_events(sample_events)
        await cache_mgr._update_fetch_metadata(success=True)

        # Manually update database to make cache stale
        old_timestamp = datetime.now() - timedelta(hours=25)  # Older than cache_ttl (24 hours)
        stale_timestamp_str = old_timestamp.isoformat()

        # Update cache metadata to make cache stale
        async def make_stale() -> None:
            # Use the correct API method and metadata field for cache freshness
            await cache_mgr.db.update_cache_metadata(last_successful_fetch=stale_timestamp_str)

        await make_stale()

        # Create mock database object for compatibility
        class MockStaleDatabase:
            def __init__(self, settings: Any, db: Any, cache_manager: Any) -> None:
                self.settings = settings
                self.db = db
                self.cache_manager = cache_manager

            def cleanup(self) -> None:
                """Cleanup method for resource tracking."""
                self.settings = None
                self.db = None
                self.cache_manager = None

        stale_db = MockStaleDatabase(test_settings, cache_mgr.db, cache_mgr)
        register_test_resource(stale_db.cleanup)

        yield stale_db

    finally:
        # Cleanup
        if cache_mgr:
            try:
                await cache_mgr.clear_cache()
                if hasattr(cache_mgr, "db") and cache_mgr.db and hasattr(cache_mgr.db, "close"):
                    await cache_mgr.db.close()
            except Exception as e:
                logging.debug(f"Stale database cleanup failed: {e}")


# Performance test database
@pytest.fixture
async def performance_test_database(test_settings: Any) -> AsyncGenerator[Any, None]:
    """Create test database optimized for performance testing."""
    cache_mgr = None
    try:
        # Create cache manager
        cache_mgr = CacheManager(test_settings)
        await cache_mgr.initialize()

        # Create smaller dataset for performance testing to reduce memory usage
        now = datetime.now()
        large_events = []

        for i in range(20):  # Reduced from 100 to 20 events
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
        await cache_mgr.cache_events(large_events)

        # Create mock database object
        class MockPerformanceDatabase:
            def __init__(self, settings: Any, db: Any, cache_manager: Any) -> None:
                self.settings = settings
                self.db = db
                self.cache_manager = cache_manager

            def cleanup(self) -> None:
                """Cleanup method for resource tracking."""
                self.settings = None
                self.db = None
                self.cache_manager = None

        perf_db = MockPerformanceDatabase(test_settings, cache_mgr.db, cache_mgr)
        register_test_resource(perf_db.cleanup)

        yield perf_db

    finally:
        # Cleanup
        if cache_mgr:
            try:
                await cache_mgr.clear_cache()
                if hasattr(cache_mgr, "db") and cache_mgr.db and hasattr(cache_mgr.db, "close"):
                    await cache_mgr.db.close()
            except Exception as e:
                logging.debug(f"Performance database cleanup failed: {e}")


# Lightweight source manager mock
@pytest.fixture
def mock_source_manager() -> AsyncMock:
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

    # Register all mocks for cleanup
    register_mock_for_cleanup(mock)
    register_mock_for_cleanup(mock_health)
    register_mock_for_cleanup(mock_info)

    return mock


# Real source manager fixture for integration tests
@pytest.fixture
async def source_manager(test_settings: Any) -> AsyncGenerator[Any, None]:
    """Create real SourceManager instance for testing."""
    source_mgr = None
    try:
        # Create source manager without cache manager for basic tests
        source_mgr = SourceManager(test_settings, None)

        yield source_mgr

    finally:
        # Cleanup
        if source_mgr:
            try:
                await source_mgr.cleanup()
                # Clear any remaining references
                if hasattr(source_mgr, "_sources"):
                    source_mgr._sources = None
            except Exception as e:
                logging.debug(f"Source manager cleanup failed: {e}")


# Lightweight display manager mock
@pytest.fixture
def mock_display_manager() -> MagicMock:
    """Create lightweight display manager mock."""
    mock = MagicMock()
    # Use AsyncMock for async methods that are awaited in CalendarBot
    mock.display_events = AsyncMock(return_value=True)
    mock.display_error = AsyncMock(return_value=True)

    # Register for cleanup
    register_mock_for_cleanup(mock)
    return mock


# In-memory database for cache tests
@pytest.fixture
def memory_db_path() -> str:
    """Return in-memory SQLite database path."""
    return ":memory:"


# Simple ICS content for parser tests
@pytest.fixture
def sample_ics_content() -> str:
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
def mock_http_response() -> MagicMock:
    """Create mock HTTP response."""
    mock = MagicMock()
    mock.status_code = 200
    mock.text = "Mock ICS content"
    mock.headers = {"content-type": "text/calendar"}
    mock.raise_for_status = MagicMock()
    return mock


# Performance testing utilities
@pytest.fixture
def performance_tracker() -> Any:
    """Simple performance tracking for test optimization."""

    class PerformanceTracker:
        def __init__(self) -> None:
            self.metrics: dict[str, dict[str, float]] = {}

        def start_timer(self, name: str) -> None:
            self.metrics[name] = {"start": time.time()}

        def end_timer(self, name: str) -> None:
            if name in self.metrics:
                self.metrics[name]["duration"] = time.time() - self.metrics[name]["start"]

        def get_duration(self, name: str) -> float:
            duration = self.metrics.get(name, {}).get("duration", 0.0)
            return float(duration)

        def assert_performance(self, name: str, max_duration: float) -> None:
            duration = self.get_duration(name)
            if duration > max_duration:
                pytest.fail(f"{name} took {duration:.3f}s, expected <= {max_duration}s")

    return PerformanceTracker()


# Configure pytest for optimized async testing
def pytest_configure(config: Any) -> None:
    """Configure pytest with optimized markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests")
    config.addinivalue_line("markers", "critical_path: Core functionality tests")
    config.addinivalue_line("markers", "smoke: Basic smoke tests")


# Settings model fixtures for API tests
@pytest.fixture
def sample_settings_data() -> Any:
    """Create sample SettingsData for testing."""
    return SettingsData(
        event_filters=EventFilterSettings(
            enabled=True,
            hide_all_day_events=False,
            title_patterns=[],
        ),
        display=DisplaySettings(
            default_layout="whats-next-view",
            display_density="normal",
            timezone="UTC",
        ),
        conflict_resolution=ConflictResolutionSettings(
            priority_by_acceptance=True,
            conflict_display_mode="primary",
        ),
    )


@pytest.fixture
def sample_event_filter_settings() -> Any:
    """Create sample EventFilterSettings for testing."""
    return EventFilterSettings(
        enabled=True,
        hide_all_day_events=False,
        title_patterns=[],
    )


@pytest.fixture
def sample_display_settings() -> Any:
    """Create sample DisplaySettings for testing."""
    return DisplaySettings(
        default_layout="whats-next-view",
        display_density="normal",
        timezone="UTC",
    )


@pytest.fixture
def sample_conflict_resolution_settings() -> Any:
    """Create sample ConflictResolutionSettings for testing."""
    return ConflictResolutionSettings(
        priority_by_acceptance=True,
        conflict_display_mode="primary",
    )


@pytest.fixture
def sample_filter_pattern() -> Any:
    """Create sample FilterPattern for testing."""
    return FilterPattern(
        pattern="test_pattern",
        is_regex=False,
        case_sensitive=False,
        description="Test pattern for filtering",
    )


# Enhanced resource management and cleanup
@pytest.fixture(autouse=True)
def aggressive_cleanup():
    """Aggressive resource cleanup to prevent memory exhaustion."""
    # Pre-test cleanup
    _cleanup_all_resources()
    gc.collect()  # Force garbage collection before each test

    yield  # Run the test

    # Post-test cleanup
    _cleanup_all_resources()


def register_test_resource(resource: Any) -> None:
    """Register a resource for cleanup after test completion."""
    _test_resources.append(resource)


def register_temp_directory(temp_dir: Path) -> None:
    """Register a temporary directory for cleanup after test completion."""
    _temp_directories.append(temp_dir)


def register_mock_for_cleanup(mock_obj: Any) -> None:
    """Register a mock object for cleanup after test completion."""
    _active_mocks.append(mock_obj)


def _cleanup_all_resources() -> None:  # noqa: PLR0912, PLR0915
    """Comprehensive cleanup of all test resources."""

    # Clean up tracked resources
    # Pre-categorize resources to avoid exceptions in the loop
    close_resources = []
    cleanup_resources = []
    callable_resources = []
    failed_resources = []

    for resource in _test_resources[:]:
        if hasattr(resource, "close"):
            close_resources.append(resource)
        elif hasattr(resource, "cleanup"):
            cleanup_resources.append(resource)
        elif callable(resource):
            callable_resources.append(resource)
        else:
            failed_resources.append(resource)

    # Process resources without exception handling in loops
    for resource in close_resources:
        resource.close()
    for resource in cleanup_resources:
        resource.cleanup()
    for resource in callable_resources:
        resource()

    # Log failed resources outside the main processing
    if failed_resources:
        logging.debug(
            f"Failed to cleanup {len(failed_resources)} resources: no valid cleanup method"
        )

    # Clean up temporary directories
    # Pre-filter valid directories to avoid exceptions in the loop
    valid_temp_dirs = []
    invalid_temp_dirs = []

    for temp_dir in _temp_directories[:]:
        if temp_dir != Path(":memory:") and temp_dir.exists():
            valid_temp_dirs.append(temp_dir)
        else:
            invalid_temp_dirs.append(temp_dir)

    # Process valid directories without exception handling in the loop
    for temp_dir in valid_temp_dirs:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Log invalid directories if any
    if invalid_temp_dirs:
        logging.debug(
            f"Skipped {len(invalid_temp_dirs)} temp directories: memory paths or non-existent"
        )

    # Reset all mocks to prevent memory accumulation
    # Pre-filter valid mocks to avoid exceptions in the loop
    valid_mocks = []
    failed_mocks = []

    for mock_obj in _active_mocks[:]:
        if hasattr(mock_obj, "reset_mock"):
            valid_mocks.append(mock_obj)
        else:
            failed_mocks.append(mock_obj)

    # Process valid mocks without exception handling in the loop
    for mock_obj in valid_mocks:
        mock_obj.reset_mock()
        # Clear internal mock storage safely
        if hasattr(mock_obj, "_mock_children"):
            mock_obj._mock_children.clear()
        if hasattr(mock_obj, "call_args_list"):
            mock_obj.call_args_list.clear()

    # Log failed mocks outside the main processing loop
    if failed_mocks:
        logging.debug(f"Failed to reset {len(failed_mocks)} mocks: missing reset_mock method")

    # Clear tracking lists
    _test_resources.clear()
    _temp_directories.clear()
    _active_mocks.clear()

    # Clean up any remaining asyncio tasks
    try:
        try:
            loop = asyncio.get_event_loop()
            pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending_tasks:
                # Cancel all tasks first without exception handling in the loop
                for task in pending_tasks:
                    if not task.done():
                        task.cancel()

                # Wait for all cancellations with single exception handler
                if pending_tasks:
                    with contextlib.suppress(
                        asyncio.TimeoutError, asyncio.CancelledError, asyncio.InvalidStateError
                    ):
                        # Use asyncio.wait with timeout for efficient batch processing
                        loop.run_until_complete(
                            asyncio.wait(
                                pending_tasks, timeout=0.1, return_when=asyncio.ALL_COMPLETED
                            )
                        )
        except RuntimeError:
            pass  # No event loop running
    except Exception:
        pass

    # Clear type cache and force garbage collection
    try:
        if hasattr(sys, "_clear_type_cache"):
            sys._clear_type_cache()
    except Exception:
        pass

    # Force multiple garbage collection passes
    for _ in range(3):
        gc.collect()


# Memory pressure monitoring
@pytest.fixture(autouse=True)
def memory_pressure_monitor():
    """Monitor memory pressure and force cleanup when needed."""
    try:
        process = psutil.Process()

        # Check memory before test
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)

        # If memory usage is high, force aggressive cleanup
        if memory_mb > 200:  # Lowered threshold to 200MB
            logging.warning(f"High memory usage detected: {memory_mb:.1f}MB - forcing cleanup")
            _cleanup_all_resources()

            # Additional cleanup measures
            try:
                if hasattr(sys, "_clear_type_cache"):
                    sys._clear_type_cache()

                # Clear import cache for test modules
                modules_to_clear = [mod for mod in sys.modules if mod.startswith("tests.")]
                for mod in modules_to_clear:
                    if mod in sys.modules:
                        del sys.modules[mod]

            except Exception:
                pass

            # Force multiple GC passes
            for _ in range(5):
                gc.collect()

    except ImportError:
        pass  # psutil not available
    except Exception as e:
        logging.debug(f"Memory monitoring error: {e}")

    yield

    # Post-test memory check
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)

        # Force cleanup if memory grew significantly
        if memory_mb > 300:
            _cleanup_all_resources()
            for _ in range(3):
                gc.collect()

    except Exception:
        pass


# Ensure clean test isolation with enhanced cleanup
@pytest.fixture(autouse=True)
def clean_test_environment() -> Any:
    """Ensure clean test environment for each test."""
    # Reset any global state if needed
    return
    # Cleanup is handled by aggressive_cleanup fixture
