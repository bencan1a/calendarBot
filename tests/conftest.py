"""Test configuration and shared fixtures for CalendarBot test suite."""

import asyncio
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import httpx
import pytest
import pytest_asyncio

from calendarbot.cache import CachedEvent, CacheManager, CacheMetadata
from calendarbot.ics.fetcher import ICSFetcher
from calendarbot.ics.models import CalendarEvent, ICSAuth, ICSSource
from calendarbot.main import CalendarBot
from calendarbot.sources.manager import SourceManager

# Import CalendarBot components
from config.settings import CalendarBotSettings


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> CalendarBotSettings:
    """Create test settings with temporary file paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a test settings instance with temporary directories
        # We need to override the default directory factory functions
        settings = CalendarBotSettings(
            # ICS settings (required)
            ics_url="http://localhost:8999/test.ics",
            ics_timeout=10,
            ics_refresh_interval=300,
            # Cache settings
            cache_ttl=3600,  # 1 hour
            # Web settings
            web_host="127.0.0.1",
            web_port=8998,
            web_theme="standard",
            # Application settings
            app_name="CalendarBot-Test",
            refresh_interval=60,
            max_retries=2,
            retry_backoff_factor=1.0,
            request_timeout=5,
            # Test-specific settings
            auto_kill_existing=False,
            display_enabled=False,
        )

        # Override the directory properties after initialization
        # Use object.__setattr__ to bypass Pydantic's field validation
        object.__setattr__(settings, "data_dir", temp_path)
        object.__setattr__(settings, "config_dir", temp_path)
        object.__setattr__(settings, "cache_dir", temp_path)

        # Configure logging for tests
        settings.logging.console_level = "DEBUG"
        settings.logging.file_enabled = False  # Disable file logging in tests

        yield settings


@pytest_asyncio.fixture
async def temp_database() -> AsyncGenerator[Path, None]:
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        db_path = Path(temp_file.name)

    try:
        # Initialize the database
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS cached_events (
                    id TEXT PRIMARY KEY,
                    graph_id TEXT UNIQUE,
                    subject TEXT,
                    body_preview TEXT,
                    start_datetime TEXT,
                    end_datetime TEXT,
                    start_timezone TEXT,
                    end_timezone TEXT,
                    is_all_day BOOLEAN,
                    show_as TEXT,
                    is_cancelled BOOLEAN,
                    is_organizer BOOLEAN,
                    location_display_name TEXT,
                    location_address TEXT,
                    is_online_meeting BOOLEAN,
                    online_meeting_url TEXT,
                    web_link TEXT,
                    is_recurring BOOLEAN,
                    series_master_id TEXT,
                    cached_at TEXT,
                    last_modified TEXT
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            await db.commit()

        yield db_path
    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()


@pytest_asyncio.fixture
async def cache_manager(
    test_settings: CalendarBotSettings, temp_database: Path
) -> AsyncGenerator[CacheManager, None]:
    """Create a test cache manager with temporary database."""
    # Create a test settings copy with modified database path
    from unittest.mock import patch

    # Since database_file is a property that depends on data_dir,
    # we need to patch data_dir to point to the temp database's directory
    temp_data_dir = temp_database.parent

    with patch.object(test_settings, "data_dir", temp_data_dir):
        # Copy the temp database to the expected name in the temp directory
        expected_db_path = temp_data_dir / "calendar_cache.db"
        if expected_db_path != temp_database:
            import shutil

            shutil.copy2(temp_database, expected_db_path)

        cache_mgr = CacheManager(test_settings)

        await cache_mgr.initialize()
        yield cache_mgr

        # Cleanup
        await cache_mgr.cleanup_old_events(days_old=0)


@pytest_asyncio.fixture
async def source_manager(
    test_settings: CalendarBotSettings, cache_manager: CacheManager
) -> AsyncGenerator[SourceManager, None]:
    """Create a test source manager."""
    source_mgr = SourceManager(test_settings, cache_manager)
    yield source_mgr

    # Cleanup
    await source_mgr.cleanup()


@pytest_asyncio.fixture
async def calendar_bot(test_settings: CalendarBotSettings) -> AsyncGenerator[CalendarBot, None]:
    """Create a test CalendarBot instance."""
    # Override settings for test instance
    original_settings = test_settings

    bot = CalendarBot()
    bot.settings = test_settings

    # Replace components with test versions
    bot.cache_manager = CacheManager(test_settings)
    bot.source_manager = SourceManager(test_settings, bot.cache_manager)

    yield bot

    # Cleanup
    await bot.cleanup()


# Mock data fixtures
@pytest.fixture
def sample_calendar_events() -> List[CalendarEvent]:
    """Create sample calendar events for testing."""
    from calendarbot.ics.models import DateTimeInfo, EventStatus, Location

    now = datetime.now()

    events = [
        CalendarEvent(
            id="event_1",
            subject="Test Meeting 1",
            body_preview="First test meeting",
            start=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=2), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=Location(display_name="Conference Room A", address="123 Test St"),
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=False,
            last_modified_date_time=now,
        ),
        CalendarEvent(
            id="event_2",
            subject="All Day Event",
            body_preview="Test all day event",
            start=DateTimeInfo(
                date_time=now.replace(hour=0, minute=0, second=0, microsecond=0), time_zone="UTC"
            ),
            end=DateTimeInfo(
                date_time=now.replace(hour=23, minute=59, second=59, microsecond=0), time_zone="UTC"
            ),
            is_all_day=True,
            show_as=EventStatus.FREE,
            is_cancelled=False,
            is_organizer=False,
            location=None,
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=False,
            last_modified_date_time=now,
        ),
        CalendarEvent(
            id="event_3",
            subject="Online Meeting",
            body_preview="Test online meeting with video",
            start=DateTimeInfo(date_time=now + timedelta(hours=3), time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=4), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=None,
            is_online_meeting=True,
            online_meeting_url="https://teams.microsoft.com/l/meetup/test",
            is_recurring=True,
            last_modified_date_time=now,
        ),
    ]

    return events


@pytest.fixture
def sample_ics_content() -> str:
    """Create sample ICS content for testing."""
    now = datetime.now()
    event_date = now.strftime("%Y%m%dT%H%M%SZ")

    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:test-event-1@example.com
DTSTART:{event_date}
DTEND:{now.strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Test ICS Event
DESCRIPTION:This is a test event from ICS
LOCATION:Test Location
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
BEGIN:VEVENT
UID:test-event-2@example.com
DTSTART;VALUE=DATE:{now.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{(now + timedelta(days=1)).strftime("%Y%m%d")}
SUMMARY:Test All-Day Event
DESCRIPTION:This is a test all-day event
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""


# Mock server fixtures
class MockICSServer:
    """Mock HTTP server for ICS testing."""

    def __init__(self, host: str = "localhost", port: int = 8999):
        self.host = host
        self.port = port
        self.responses: Dict[str, Any] = {}
        self.request_count = 0
        self.server_thread = None
        self.running = False

    def set_response(
        self, path: str, content: str, status_code: int = 200, headers: Dict[str, str] = None
    ):
        """Set response for a specific path."""
        self.responses[path] = {
            "content": content,
            "status_code": status_code,
            "headers": headers or {"Content-Type": "text/calendar"},
        }

    def start(self):
        """Start the mock server."""
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class MockHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                nonlocal self
                self.request_count += 1

                path = handler_self.path
                if path in self.responses:
                    response = self.responses[path]
                    handler_self.send_response(response["status_code"])

                    for header, value in response["headers"].items():
                        handler_self.send_header(header, value)
                    handler_self.end_headers()

                    handler_self.wfile.write(response["content"].encode())
                else:
                    handler_self.send_response(404)
                    handler_self.end_headers()
                    handler_self.wfile.write(b"Not Found")

            def log_message(handler_self, format, *args):
                # Suppress logging
                pass

        self.server = HTTPServer((self.host, self.port), MockHandler)
        self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
        self.running = True
        self.server_thread.start()

        # Wait for server to start
        time.sleep(0.1)

    def stop(self):
        """Stop the mock server."""
        if self.running and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False


@pytest_asyncio.fixture
async def mock_ics_server(sample_ics_content: str) -> AsyncGenerator[MockICSServer, None]:
    """Create a mock ICS server for testing."""
    server = MockICSServer()
    server.set_response("/test.ics", sample_ics_content)
    server.start()

    yield server

    server.stop()


@pytest.fixture
def mock_ics_source(test_settings: CalendarBotSettings) -> ICSSource:
    """Create a mock ICS source for testing."""
    return ICSSource(
        name="test_source",
        url="http://localhost:8999/test.ics",
        auth=ICSAuth(),
        timeout=10,
        validate_ssl=True,
        custom_headers={},
    )


# HTTP mocking fixtures
@pytest_asyncio.fixture
async def mock_http_client() -> AsyncGenerator[AsyncMock, None]:
    """Create a mock HTTP client for testing."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Configure default responses
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "Mock ICS content"
    mock_response.headers = {"content-type": "text/calendar"}
    mock_response.raise_for_status = AsyncMock()

    mock_client.get.return_value = mock_response
    mock_client.head.return_value = mock_response
    mock_client.is_closed = False
    mock_client.aclose = AsyncMock()

    yield mock_client


# Database fixtures for different scenarios
@pytest_asyncio.fixture
async def populated_test_database(test_settings: CalendarBotSettings, temp_database: Path):
    """Create a database populated with test data."""
    from calendarbot.cache.database import DatabaseManager
    from calendarbot.cache.models import CachedEvent

    class TestDatabase:
        def __init__(self, settings, db):
            self.settings = settings
            self.db = db

    # Patch data_dir instead of database_file
    temp_data_dir = temp_database.parent
    expected_db_path = temp_data_dir / "calendar_cache.db"

    with patch.object(test_settings, "data_dir", temp_data_dir):
        # Copy the temp database to the expected name
        if expected_db_path != temp_database:
            import shutil

            shutil.copy2(temp_database, expected_db_path)

        db = DatabaseManager(expected_db_path)
        await db.initialize()

        # Add some test events
        now = datetime.now()
        test_events = [
            CachedEvent(
                id="test_event_1",
                graph_id="graph_1",
                subject="Test Event 1",
                body_preview="Test event body",
                start_datetime=(now + timedelta(hours=1)).isoformat(),
                end_datetime=(now + timedelta(hours=2)).isoformat(),
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                cached_at=now.isoformat(),
            ),
            CachedEvent(
                id="test_event_2",
                graph_id="graph_2",
                subject="Test Event 2",
                body_preview="Another test event",
                start_datetime=(now + timedelta(hours=3)).isoformat(),
                end_datetime=(now + timedelta(hours=4)).isoformat(),
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="free",
                is_cancelled=False,
                is_organizer=False,
                cached_at=now.isoformat(),
            ),
        ]

        await db.store_events(test_events)

        yield TestDatabase(test_settings, db)


@pytest_asyncio.fixture
async def stale_cache_database(test_settings: CalendarBotSettings, temp_database: Path):
    """Create a database with stale cache metadata."""
    from calendarbot.cache.database import DatabaseManager

    class TestDatabase:
        def __init__(self, settings, db):
            self.settings = settings
            self.db = db

    # Patch data_dir instead of database_file
    temp_data_dir = temp_database.parent
    expected_db_path = temp_data_dir / "calendar_cache.db"

    with patch.object(test_settings, "data_dir", temp_data_dir):
        # Copy the temp database to the expected name
        if expected_db_path != temp_database:
            import shutil

            shutil.copy2(temp_database, expected_db_path)

        db = DatabaseManager(expected_db_path)
        await db.initialize()

        # Set stale metadata (older than cache TTL)
        stale_time = datetime.now() - timedelta(seconds=test_settings.cache_ttl + 1000)
        await db.update_cache_metadata(
            last_update=stale_time.isoformat(),
            last_successful_fetch=stale_time.isoformat(),
            consecutive_failures=0,
        )

        yield TestDatabase(test_settings, db)


@pytest_asyncio.fixture
async def performance_test_database(test_settings: CalendarBotSettings, temp_database: Path):
    """Create a database with large amount of test data for performance testing."""
    from calendarbot.cache.database import DatabaseManager
    from calendarbot.cache.models import CachedEvent

    class TestDatabase:
        def __init__(self, settings, db):
            self.settings = settings
            self.db = db

    # Patch data_dir instead of database_file
    temp_data_dir = temp_database.parent
    expected_db_path = temp_data_dir / "calendar_cache.db"

    with patch.object(test_settings, "data_dir", temp_data_dir):
        # Copy the temp database to the expected name
        if expected_db_path != temp_database:
            import shutil

            shutil.copy2(temp_database, expected_db_path)

        db = DatabaseManager(expected_db_path)
        await db.initialize()

        # Add many test events for performance testing
        now = datetime.now()
        test_events = []
        for i in range(500):  # 500 events for performance testing
            test_events.append(
                CachedEvent(
                    id=f"perf_event_{i}",
                    graph_id=f"graph_{i}",
                    subject=f"Performance Test Event {i}",
                    body_preview=f"Performance test event {i}",
                    start_datetime=(now + timedelta(hours=i)).isoformat(),
                    end_datetime=(now + timedelta(hours=i + 1)).isoformat(),
                    start_timezone="UTC",
                    end_timezone="UTC",
                    is_all_day=False,
                    show_as="busy",
                    is_cancelled=False,
                    is_organizer=True,
                    cached_at=now.isoformat(),
                )
            )

        await db.store_events(test_events)

        yield TestDatabase(test_settings, db)


# Performance testing utilities
@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests."""

    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}

        def start_timer(self, name: str):
            self.metrics[name] = {"start": time.time()}

        def end_timer(self, name: str):
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


# Test markers and parametrization
pytest_plugins = ["pytest_asyncio"]


# Ensure async tests work properly
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "browser: mark test as a browser automation test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security-focused")
    config.addinivalue_line("markers", "critical_path: mark test as critical path functionality")
