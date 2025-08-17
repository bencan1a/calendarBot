"""SQLite database operations for calendar event caching."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Union

import aiosqlite

from .models import CachedEvent, CacheMetadata, RawEvent

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for calendar event caching."""

    def __init__(self, database_path: Union[Path, str]):
        """Initialize database manager.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = (
            Path(database_path) if isinstance(database_path, str) else database_path
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        self._initialization_lock = None

        logger.info(f"Database manager initialized (lazy): {database_path}")

    async def _ensure_initialized(self) -> bool:
        """Ensure database is initialized before operations.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.debug(f"Database already initialized for {self.database_path}")
            return True

        # Use a lock to prevent concurrent initialization
        if self._initialization_lock is None:
            self._initialization_lock = asyncio.Lock()

        async with self._initialization_lock:
            # Double-check after acquiring lock
            if self._initialized:
                return True

            try:
                success = await self._initialize_database()
                self._initialized = success
                return success
            except Exception:
                logger.exception("Failed to initialize database")
                return False

    async def _initialize_database(self) -> bool:
        """Internal database initialization.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                # Enable WAL mode for better concurrent access and less SD card wear
                await db.execute("PRAGMA journal_mode=WAL")

                # Set synchronous mode to NORMAL for better performance
                await db.execute("PRAGMA synchronous=NORMAL")

                # Enable foreign key constraints
                await db.execute("PRAGMA foreign_keys=ON")

                # Create events table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cached_events (
                        id TEXT PRIMARY KEY,
                        graph_id TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        body_preview TEXT,
                        start_datetime TEXT NOT NULL,
                        end_datetime TEXT NOT NULL,
                        start_timezone TEXT NOT NULL,
                        end_timezone TEXT NOT NULL,
                        is_all_day INTEGER NOT NULL DEFAULT 0,
                        show_as TEXT NOT NULL DEFAULT 'busy',
                        is_cancelled INTEGER NOT NULL DEFAULT 0,
                        is_organizer INTEGER NOT NULL DEFAULT 0,
                        location_display_name TEXT,
                        location_address TEXT,
                        is_online_meeting INTEGER NOT NULL DEFAULT 0,
                        online_meeting_url TEXT,
                        web_link TEXT,
                        is_recurring INTEGER NOT NULL DEFAULT 0,
                        series_master_id TEXT,
                        cached_at TEXT NOT NULL,
                        last_modified TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create index for efficient querying by date range
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_datetime
                    ON cached_events(start_datetime, end_datetime)
                """
                )

                # Create index for Graph ID lookups
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_graph_id
                    ON cached_events(graph_id)
                """
                )

                # Create metadata table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create trigger to update updated_at timestamp
                await db.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS update_events_timestamp
                    AFTER UPDATE ON cached_events
                    BEGIN
                        UPDATE cached_events SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END
                """
                )

                # Drop and recreate raw_events table to ensure correct schema
                await db.execute("DROP TABLE IF EXISTS raw_events")

                # Create raw_events table for storing raw ICS content with parsed event data
                await db.execute(
                    """
                    CREATE TABLE raw_events (
                        id TEXT PRIMARY KEY,
                        graph_id TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        body_preview TEXT,
                        start_datetime TEXT NOT NULL,
                        end_datetime TEXT NOT NULL,
                        start_timezone TEXT NOT NULL,
                        end_timezone TEXT NOT NULL,
                        is_all_day INTEGER NOT NULL DEFAULT 0,
                        show_as TEXT NOT NULL DEFAULT 'busy',
                        is_cancelled INTEGER NOT NULL DEFAULT 0,
                        is_organizer INTEGER NOT NULL DEFAULT 0,
                        location_display_name TEXT,
                        location_address TEXT,
                        is_online_meeting INTEGER NOT NULL DEFAULT 0,
                        online_meeting_url TEXT,
                        web_link TEXT,
                        is_recurring INTEGER NOT NULL DEFAULT 0,
                        series_master_id TEXT,
                        recurrence_id TEXT,
                        is_instance INTEGER NOT NULL DEFAULT 0,
                        last_modified TEXT,
                        source_url TEXT,
                        raw_ics_content TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        content_size_bytes INTEGER NOT NULL,
                        cached_at TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (graph_id) REFERENCES cached_events(graph_id) ON DELETE CASCADE
                    )
                """
                )

                # Create indexes for raw_events table
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_raw_events_graph_id
                    ON raw_events(graph_id)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_raw_events_recurrence_id
                    ON raw_events(recurrence_id)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_raw_events_is_instance
                    ON raw_events(is_instance)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_raw_events_content_hash
                    ON raw_events(content_hash)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_raw_events_cached_at
                    ON raw_events(cached_at)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_raw_events_size_cached
                    ON raw_events(content_size_bytes, cached_at)
                """
                )

                # Create trigger to update updated_at timestamp for raw_events
                await db.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS update_raw_events_timestamp
                    AFTER UPDATE ON raw_events
                    BEGIN
                        UPDATE raw_events SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END
                """
                )

                await db.commit()

                logger.info("Database schema initialized successfully")
                return True

        except Exception:
            logger.exception("Failed to initialize database")
            return False

    async def _create_schema_in_connection(self, db) -> None:
        """Create database schema in an existing connection.

        This is used for in-memory databases where each connection
        needs its own copy of the schema.

        Args:
            db: Active database connection
        """
        # Enable WAL mode for better concurrent access and less SD card wear
        await db.execute("PRAGMA journal_mode=WAL")

        # Set synchronous mode to NORMAL for better performance
        await db.execute("PRAGMA synchronous=NORMAL")

        # Enable foreign key constraints
        await db.execute("PRAGMA foreign_keys=ON")

        # Create events table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cached_events (
                id TEXT PRIMARY KEY,
                graph_id TEXT UNIQUE,
                subject TEXT NOT NULL,
                body_preview TEXT,
                start_datetime TEXT NOT NULL,
                start_timezone TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                end_timezone TEXT NOT NULL,
                is_all_day INTEGER NOT NULL DEFAULT 0,
                show_as TEXT NOT NULL DEFAULT 'busy',
                is_cancelled INTEGER NOT NULL DEFAULT 0,
                is_organizer INTEGER NOT NULL DEFAULT 0,
                location_display_name TEXT,
                location_address TEXT,
                is_online_meeting INTEGER NOT NULL DEFAULT 0,
                online_meeting_url TEXT,
                web_link TEXT,
                is_recurring INTEGER NOT NULL DEFAULT 0,
                series_master_id TEXT,
                recurrence_id TEXT,
                is_instance INTEGER NOT NULL DEFAULT 0,
                last_modified TEXT,
                source_url TEXT,
                cached_at TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create metadata table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create raw_events table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                graph_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_content TEXT,
                body_content_type TEXT,
                start_datetime TEXT NOT NULL,
                start_timezone TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                end_timezone TEXT NOT NULL,
                is_all_day INTEGER NOT NULL DEFAULT 0,
                show_as TEXT NOT NULL DEFAULT 'busy',
                is_cancelled INTEGER NOT NULL DEFAULT 0,
                is_organizer INTEGER NOT NULL DEFAULT 0,
                location_display_name TEXT,
                location_address TEXT,
                is_online_meeting INTEGER NOT NULL DEFAULT 0,
                online_meeting_url TEXT,
                web_link TEXT,
                is_recurring INTEGER NOT NULL DEFAULT 0,
                series_master_id TEXT,
                recurrence_id TEXT,
                is_instance INTEGER NOT NULL DEFAULT 0,
                last_modified TEXT,
                source_url TEXT,
                raw_ics_content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content_size_bytes INTEGER NOT NULL,
                cached_at TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (graph_id) REFERENCES cached_events(graph_id) ON DELETE CASCADE
            )
        """
        )

        # Create indexes for cached_events table
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cached_events_start_datetime
            ON cached_events(start_datetime)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cached_events_end_datetime
            ON cached_events(end_datetime)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cached_events_graph_id
            ON cached_events(graph_id)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cached_events_recurrence_id
            ON cached_events(recurrence_id)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cached_events_series_master_id
            ON cached_events(series_master_id)
        """
        )

        # Create indexes for raw_events table
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_events_graph_id
            ON raw_events(graph_id)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_events_recurrence_id
            ON raw_events(recurrence_id)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_events_hash_cached
            ON raw_events(content_hash, cached_at)
        """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_events_size_cached
            ON raw_events(content_size_bytes, cached_at)
        """
        )

        # Create trigger to update updated_at timestamp for cached_events
        await db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS update_cached_events_timestamp
            AFTER UPDATE ON cached_events
            BEGIN
                UPDATE cached_events SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """
        )

        # Create trigger to update updated_at timestamp for raw_events
        await db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS update_raw_events_timestamp
            AFTER UPDATE ON raw_events
            BEGIN
                UPDATE raw_events SET updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END
        """
        )

        await db.commit()

    async def initialize(self) -> bool:
        """Initialize database schema and settings (now lazy).

        Returns:
            True if initialization was successful, False otherwise
        """
        # Just return True immediately - actual initialization is deferred
        logger.info("Database initialization deferred for faster startup")
        return True

    async def store_events(self, events: list[CachedEvent]) -> bool:
        """Store calendar events in cache.

        Args:
            events: list of cached events to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            if not await self._ensure_initialized():
                return False

            if not events:
                logger.debug("No events to store")
                return True

            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                # Insert or replace events
                await db.executemany(
                    """
                    INSERT OR REPLACE INTO cached_events (
                        id, graph_id, subject, body_preview,
                        start_datetime, end_datetime, start_timezone, end_timezone,
                        is_all_day, show_as, is_cancelled, is_organizer,
                        location_display_name, location_address,
                        is_online_meeting, online_meeting_url, web_link,
                        is_recurring, series_master_id, cached_at, last_modified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    [
                        (
                            event.id,
                            event.graph_id,
                            event.subject,
                            event.body_preview,
                            event.start_datetime,
                            event.end_datetime,
                            event.start_timezone,
                            event.end_timezone,
                            event.is_all_day,
                            event.show_as,
                            event.is_cancelled,
                            event.is_organizer,
                            event.location_display_name,
                            event.location_address,
                            event.is_online_meeting,
                            event.online_meeting_url,
                            event.web_link,
                            event.is_recurring,
                            event.series_master_id,
                            event.cached_at,
                            event.last_modified,
                        )
                        for event in events
                    ],
                )

                # Commit the transaction
                await db.commit()

                logger.debug(f"Stored {len(events)} events in cache")
                return True

        except Exception:
            logger.exception("Failed to store events")
            return False

    async def get_events_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[CachedEvent]:
        """Get cached events within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            list of cached events
        """
        try:
            if not await self._ensure_initialized():
                return []

            start_str = start_date.isoformat()
            end_str = end_date.isoformat()

            logger.debug(f"Database query - start_str={start_str}, end_str={end_str}")
            logger.debug(
                f"Query logic - events WHERE start_datetime <= {end_str} AND end_datetime >= {start_str}"
            )

            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                db.row_factory = aiosqlite.Row

                # First check total events in database
                total_cursor = await db.execute("SELECT COUNT(*) as count FROM cached_events")
                total_row = await total_cursor.fetchone()
                total_count = total_row["count"] if total_row else 0
                logger.debug(f"Total events in database: {total_count}")

                cursor = await db.execute(
                    """
                    SELECT * FROM cached_events
                    WHERE start_datetime <= ? AND end_datetime >= ?
                    AND is_cancelled = 0
                    ORDER BY start_datetime ASC
                """,
                    (end_str, start_str),
                )

                rows = await cursor.fetchall()
                row_count = len(list(rows)) if rows else 0

                logger.debug(f"Query returned {row_count} rows")

                # DIAGNOSTIC: Check show_as distribution in retrieved events
                if rows:
                    show_as_counts = {}
                    for row in rows:
                        show_as = row["show_as"]
                        show_as_counts[show_as] = show_as_counts.get(show_as, 0) + 1

                # Convert rows to CachedEvent objects
                events = []
                for row in rows:
                    event_data = dict(row)
                    # Convert boolean fields from INTEGER to bool
                    event_data["is_all_day"] = bool(event_data["is_all_day"])
                    event_data["is_cancelled"] = bool(event_data["is_cancelled"])
                    event_data["is_organizer"] = bool(event_data["is_organizer"])
                    event_data["is_online_meeting"] = bool(event_data["is_online_meeting"])
                    event_data["is_recurring"] = bool(event_data["is_recurring"])

                    events.append(CachedEvent(**event_data))

                logger.debug(f"Retrieved {len(events)} events from cache")
                return events

        except Exception:
            logger.exception("Failed to get events by date range")
            return []

    async def get_todays_events(self) -> list[CachedEvent]:
        """Get today's cached events.

        Returns:
            list of today's cached events
        """
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.get_events_by_date_range(start_of_day, end_of_day)

    async def cleanup_old_events(self, days_old: int = 7) -> int:
        """Remove events older than specified days.

        Args:
            days_old: Number of days after which to remove events

        Returns:
            Number of events removed
        """
        try:
            await self._ensure_initialized()
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()

            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                cursor = await db.execute(
                    """
                    DELETE FROM cached_events
                    WHERE end_datetime < ?
                """,
                    (cutoff_str,),
                )

                deleted_count = cursor.rowcount
                await db.commit()

                logger.debug(f"Cleaned up {deleted_count} old events (older than {days_old} days)")
                return deleted_count

        except Exception:
            logger.exception("Failed to cleanup old events")
            return 0

    async def clear_all_events(self) -> int:
        """Clear all events from the database.

        Returns:
            Number of events removed
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                cursor = await db.execute("DELETE FROM cached_events")
                deleted_count = cursor.rowcount
                await db.commit()

                logger.debug(f"Cleared all {deleted_count} events from database")
                return deleted_count

        except Exception:
            logger.exception("Failed to clear all events")
            return 0

    async def get_cache_metadata(self) -> CacheMetadata:
        """Get cache metadata and statistics.

        Returns:
            Cache metadata object
        """
        try:
            await self._ensure_initialized()
            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                db.row_factory = aiosqlite.Row

                # Get event count
                cursor = await db.execute("SELECT COUNT(*) as count FROM cached_events")
                count_row = await cursor.fetchone()
                total_events = count_row["count"] if count_row else 0

                # Get metadata values
                metadata_dict = {}
                cursor = await db.execute("SELECT key, value FROM cache_metadata")
                rows = await cursor.fetchall()
                for row in rows:
                    metadata_dict[row["key"]] = row["value"]

                # Create metadata object
                return CacheMetadata(
                    total_events=total_events,
                    last_update=metadata_dict.get("last_update"),
                    last_successful_fetch=metadata_dict.get("last_successful_fetch"),
                    consecutive_failures=int(metadata_dict.get("consecutive_failures", 0)),
                    last_error=metadata_dict.get("last_error"),
                    last_error_time=metadata_dict.get("last_error_time"),
                )

        except Exception:
            logger.exception("Failed to get cache metadata")
            return CacheMetadata()

    async def update_cache_metadata(self, **kwargs: Any) -> bool:
        """Update cache metadata.

        Args:
            **kwargs: Metadata key-value pairs to update

        Returns:
            True if update was successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                for key, value in kwargs.items():
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO cache_metadata (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                        (key, str(value)),
                    )

                await db.commit()

                logger.debug(f"Updated cache metadata: {kwargs}")
                return True

        except Exception:
            logger.exception("Failed to update cache metadata")
            return False

    async def get_database_info(self) -> dict[str, Any]:
        """Get database information and statistics.

        Returns:
            dictionary with database information
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                # For in-memory databases, ensure schema exists in this connection
                if str(self.database_path) == ":memory:":
                    await self._create_schema_in_connection(db)
                db.row_factory = aiosqlite.Row

                info: dict[str, Any] = {}

                # Database file size
                if self.database_path.exists():
                    info["file_size_bytes"] = self.database_path.stat().st_size

                # Event count by date
                cursor = await db.execute(
                    """
                    SELECT DATE(start_datetime) as event_date, COUNT(*) as count
                    FROM cached_events
                    GROUP BY DATE(start_datetime)
                    ORDER BY event_date DESC
                    LIMIT 7
                """
                )
                rows = await cursor.fetchall()
                events_by_date: list[dict[str, Any]] = [dict(row) for row in rows]
                info["events_by_date"] = events_by_date

                # Database version info
                cursor = await db.execute("PRAGMA user_version")
                version_row = await cursor.fetchone()
                info["user_version"] = version_row[0] if version_row else 0

                # Journal mode
                cursor = await db.execute("PRAGMA journal_mode")
                journal_row = await cursor.fetchone()
                info["journal_mode"] = journal_row[0] if journal_row else "unknown"

                return info

        except Exception:
            logger.exception("Failed to get database info")
            return {}

    async def store_raw_events(self, raw_events: list[RawEvent]) -> bool:
        """Store raw ICS events in database.

        Args:
            raw_events: List of raw events to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            if not raw_events:
                logger.debug("No raw events to store")
                return True

            async with aiosqlite.connect(str(self.database_path)) as db:
                await db.executemany(
                    """
                    INSERT OR REPLACE INTO raw_events (
                        id, graph_id, subject, body_preview,
                        start_datetime, end_datetime, start_timezone, end_timezone,
                        is_all_day, show_as, is_cancelled, is_organizer,
                        location_display_name, location_address,
                        is_online_meeting, online_meeting_url, web_link,
                        is_recurring, series_master_id, recurrence_id, is_instance,
                        last_modified, source_url, raw_ics_content, content_hash,
                        content_size_bytes, cached_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            event.id,
                            event.graph_id,
                            event.subject,
                            event.body_preview,
                            event.start_datetime,
                            event.end_datetime,
                            event.start_timezone,
                            event.end_timezone,
                            event.is_all_day,
                            event.show_as,
                            event.is_cancelled,
                            event.is_organizer,
                            event.location_display_name,
                            event.location_address,
                            event.is_online_meeting,
                            event.online_meeting_url,
                            event.web_link,
                            event.is_recurring,
                            event.series_master_id,
                            event.recurrence_id,
                            event.is_instance,
                            event.last_modified,
                            event.source_url,
                            event.raw_ics_content,
                            event.content_hash,
                            event.content_size_bytes,
                            event.cached_at,
                        )
                        for event in raw_events
                    ],
                )

                await db.commit()
                logger.debug(f"Stored {len(raw_events)} raw events")
                return True

        except Exception:
            logger.exception("Failed to store raw events")
            return False

    async def cleanup_raw_events(self, days_old: int = 7) -> int:
        """Remove raw events older than specified days.

        Args:
            days_old: Number of days after which to remove raw events

        Returns:
            Number of raw events removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()

            async with aiosqlite.connect(str(self.database_path)) as db:
                cursor = await db.execute(
                    """
                    DELETE FROM raw_events
                    WHERE cached_at < ?
                    """,
                    (cutoff_str,),
                )

                deleted_count = cursor.rowcount
                await db.commit()

                logger.debug(
                    f"Cleaned up {deleted_count} old raw events (older than {days_old} days)"
                )
                return deleted_count

        except Exception:
            logger.exception("Failed to cleanup old raw events")
            return 0

    async def clear_raw_events(self) -> bool:
        """Clear all raw events from database.

        Returns:
            True if clearing was successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                cursor = await db.execute("DELETE FROM raw_events")
                deleted_count = cursor.rowcount
                await db.commit()

                logger.debug(f"Cleared all {deleted_count} raw events")
                return True

        except Exception:
            logger.exception("Failed to clear all raw events")
            return False

    async def get_raw_event_by_id(self, event_id: str) -> RawEvent | None:
        """Get raw event by ID.

        Args:
            event_id: Raw event ID to retrieve

        Returns:
            RawEvent if found, None otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                db.row_factory = aiosqlite.Row

                cursor = await db.execute(
                    """
                    SELECT * FROM raw_events
                    WHERE id = ?
                    """,
                    (event_id,),
                )

                row = await cursor.fetchone()
                if row:
                    return RawEvent(**dict(row))
                return None

        except Exception:
            logger.exception(f"Failed to get raw event by ID: {event_id}")
            return None
