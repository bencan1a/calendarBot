"""Database fixtures and utilities for testing."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite
import pytest


class DatabaseTestManager:
    """Manages test database creation and population."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def create_tables(self) -> None:
        """Create the required database tables."""
        async with aiosqlite.connect(self.db_path) as db:
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

    async def insert_test_events(self, events: list[dict[str, Any]]) -> None:
        """Insert test events into the database."""
        async with aiosqlite.connect(self.db_path) as db:
            for event in events:
                placeholders = ", ".join(["?" for _ in event.values()])
                columns = ", ".join(event.keys())

                await db.execute(
                    f"INSERT OR REPLACE INTO cached_events ({columns}) VALUES ({placeholders})",
                    list(event.values()),
                )

            await db.commit()

    async def insert_cache_metadata(self, metadata: dict[str, Any]) -> None:
        """Insert cache metadata into the database as key-value pairs."""
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in metadata.items():
                if value is not None:  # Only insert non-None values
                    await db.execute(
                        """INSERT OR REPLACE INTO cache_metadata (key, value, updated_at)
                           VALUES (?, ?, CURRENT_TIMESTAMP)""",
                        (key, str(value)),
                    )
            await db.commit()

    async def get_event_count(self) -> int:
        """Get the total number of events in the database."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM cached_events")
            result = await cursor.fetchone()
            return int(result[0]) if result and result[0] is not None else 0

    async def get_events_by_date(self, target_date: datetime) -> list[dict[str, Any]]:
        """Get events for a specific date."""
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT * FROM cached_events
                   WHERE start_datetime >= ? AND start_datetime < ?
                   ORDER BY start_datetime""",
                (start_of_day.isoformat(), end_of_day.isoformat()),
            )

            columns = [description[0] for description in cursor.description]
            events = []

            async for row in cursor:
                events.append(dict(zip(columns, row)))

            return events

    async def clear_all_data(self) -> None:
        """Clear all data from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cached_events")
            await db.execute("DELETE FROM cache_metadata")
            await db.commit()

    async def simulate_database_corruption(self) -> None:
        """Simulate database corruption for error testing."""
        # Create an invalid SQL operation to test error handling
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("INVALID SQL STATEMENT")
            except Exception:
                pass  # Expected to fail

    async def get_database_info(self) -> dict[str, Any]:
        """Get information about the database."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get file size
            file_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            # Get table info
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in await cursor.fetchall()]

            # Get journal mode
            cursor = await db.execute("PRAGMA journal_mode")
            journal_mode_result = await cursor.fetchone()
            journal_mode = journal_mode_result[0] if journal_mode_result else "UNKNOWN"

            return {"file_size_bytes": file_size, "tables": tables, "journal_mode": journal_mode}


class DatabaseScenarios:
    """Common database test scenarios."""

    @staticmethod
    def fresh_cache_scenario() -> dict[str, Any]:
        """Scenario: Fresh cache with recent successful fetch."""
        now = datetime.now()
        return {
            "metadata": {
                "last_update": now.isoformat(),
                "last_successful_fetch": now.isoformat(),
                "consecutive_failures": 0,
                "last_error": None,
                "last_error_time": None,
            },
            "events": [
                {
                    "id": "cached_fresh_1",
                    "graph_id": "fresh_1",
                    "subject": "Fresh Event 1",
                    "body_preview": "Recently cached event",
                    "start_datetime": (now + timedelta(hours=1)).isoformat(),
                    "end_datetime": (now + timedelta(hours=2)).isoformat(),
                    "start_timezone": "UTC",
                    "end_timezone": "UTC",
                    "is_all_day": False,
                    "show_as": "busy",
                    "is_cancelled": False,
                    "is_organizer": True,
                    "location_display_name": "Fresh Location",
                    "location_address": None,
                    "is_online_meeting": False,
                    "online_meeting_url": None,
                    "web_link": None,
                    "is_recurring": False,
                    "series_master_id": None,
                    "cached_at": now.isoformat(),
                    "last_modified": now.isoformat(),
                }
            ],
        }

    @staticmethod
    def stale_cache_scenario() -> dict[str, Any]:
        """Scenario: Stale cache that needs refresh."""
        now = datetime.now()
        old_time = now - timedelta(hours=2)  # 2 hours old

        return {
            "metadata": {
                "last_update": old_time.isoformat(),
                "last_successful_fetch": old_time.isoformat(),
                "consecutive_failures": 0,
                "last_error": None,
                "last_error_time": None,
            },
            "events": [
                {
                    "id": "cached_stale_1",
                    "graph_id": "stale_1",
                    "subject": "Stale Event 1",
                    "body_preview": "This event is from stale cache",
                    "start_datetime": (now + timedelta(hours=1)).isoformat(),
                    "end_datetime": (now + timedelta(hours=2)).isoformat(),
                    "start_timezone": "UTC",
                    "end_timezone": "UTC",
                    "is_all_day": False,
                    "show_as": "busy",
                    "is_cancelled": False,
                    "is_organizer": True,
                    "location_display_name": "Stale Location",
                    "location_address": None,
                    "is_online_meeting": False,
                    "online_meeting_url": None,
                    "web_link": None,
                    "is_recurring": False,
                    "series_master_id": None,
                    "cached_at": old_time.isoformat(),
                    "last_modified": old_time.isoformat(),
                }
            ],
        }

    @staticmethod
    def failed_cache_scenario() -> dict[str, Any]:
        """Scenario: Cache with recent failures."""
        now = datetime.now()
        error_time = now - timedelta(minutes=30)

        return {
            "metadata": {
                "last_update": error_time.isoformat(),
                "last_successful_fetch": (now - timedelta(hours=3)).isoformat(),
                "consecutive_failures": 3,
                "last_error": "Network timeout",
                "last_error_time": error_time.isoformat(),
            },
            "events": [],  # No recent events due to failures
        }

    @staticmethod
    def empty_cache_scenario() -> dict[str, Any]:
        """Scenario: Empty cache (first run)."""
        return {
            "metadata": {
                "last_update": None,
                "last_successful_fetch": None,
                "consecutive_failures": 0,
                "last_error": None,
                "last_error_time": None,
            },
            "events": [],
        }

    @staticmethod
    def performance_test_scenario(event_count: int = 1000) -> dict[str, Any]:
        """Scenario: Large number of events for performance testing."""
        now = datetime.now()
        events = []

        for i in range(event_count):
            # Spread events across multiple days
            event_start = now + timedelta(days=i // 50, hours=(i % 24))
            event_end = event_start + timedelta(hours=1)

            events.append(
                {
                    "id": f"cached_perf_{i}",
                    "graph_id": f"perf_{i}",
                    "subject": f"Performance Test Event {i}",
                    "body_preview": f"Event {i} for performance testing with detailed content",
                    "start_datetime": event_start.isoformat(),
                    "end_datetime": event_end.isoformat(),
                    "start_timezone": "UTC",
                    "end_timezone": "UTC",
                    "is_all_day": False,
                    "show_as": "busy",
                    "is_cancelled": False,
                    "is_organizer": True,
                    "location_display_name": f"Location {i}",
                    "location_address": None,
                    "is_online_meeting": i % 10 == 0,  # Every 10th event is online
                    "online_meeting_url": (
                        f"https://meeting.example.com/{i}" if i % 10 == 0 else None
                    ),
                    "web_link": None,
                    "is_recurring": i % 20 == 0,  # Every 20th event is recurring
                    "series_master_id": None,
                    "cached_at": now.isoformat(),
                    "last_modified": now.isoformat(),
                }
            )

        return {
            "metadata": {
                "last_update": now.isoformat(),
                "last_successful_fetch": now.isoformat(),
                "consecutive_failures": 0,
                "last_error": None,
                "last_error_time": None,
            },
            "events": events,
        }


@pytest.fixture
async def test_database_manager(temp_database: Path) -> AsyncGenerator[DatabaseTestManager, None]:
    """Create a test database manager."""
    manager = DatabaseTestManager(temp_database)
    await manager.create_tables()
    yield manager
    await manager.clear_all_data()


@pytest.fixture
async def populated_test_database(
    test_database_manager: DatabaseTestManager,
) -> DatabaseTestManager:
    """Create a test database populated with sample data."""
    scenario = DatabaseScenarios.fresh_cache_scenario()

    await test_database_manager.insert_cache_metadata(scenario["metadata"])
    await test_database_manager.insert_test_events(scenario["events"])

    return test_database_manager


@pytest.fixture
async def stale_cache_database(test_database_manager: DatabaseTestManager) -> DatabaseTestManager:
    """Create a test database with stale cache data."""
    scenario = DatabaseScenarios.stale_cache_scenario()

    await test_database_manager.insert_cache_metadata(scenario["metadata"])
    await test_database_manager.insert_test_events(scenario["events"])

    return test_database_manager


@pytest.fixture
async def performance_test_database(
    test_database_manager: DatabaseTestManager,
) -> DatabaseTestManager:
    """Create a test database with large amount of data for performance testing."""
    scenario = DatabaseScenarios.performance_test_scenario(500)  # 500 events for testing

    await test_database_manager.insert_cache_metadata(scenario["metadata"])
    await test_database_manager.insert_test_events(scenario["events"])

    return test_database_manager
