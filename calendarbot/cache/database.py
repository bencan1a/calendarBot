"""SQLite database operations for calendar event caching."""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from .models import CachedEvent, CacheMetadata

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for calendar event caching."""

    def __init__(self, database_path: Path):
        """Initialize database manager.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Database manager initialized: {database_path}")

    async def initialize(self) -> bool:
        """Initialize database schema and settings.

        Returns:
            True if initialization was successful, False otherwise
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
                        graph_id TEXT UNIQUE NOT NULL,
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

                await db.commit()

                logger.info("Database schema initialized successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    async def store_events(self, events: List[CachedEvent]) -> bool:
        """Store calendar events in cache.

        Args:
            events: List of cached events to store

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            if not events:
                logger.debug("No events to store")
                return True

            async with aiosqlite.connect(str(self.database_path)) as db:
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

                await db.commit()

                logger.info(f"Stored {len(events)} events in cache")
                return True

        except Exception as e:
            logger.error(f"Failed to store events: {e}")
            return False

    async def get_events_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[CachedEvent]:
        """Get cached events within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of cached events
        """
        try:
            start_str = start_date.isoformat()
            end_str = end_date.isoformat()

            logger.info(f"DEBUG: Database query - start_str={start_str}, end_str={end_str}")
            logger.info(
                f"DEBUG: Query logic - events WHERE start_datetime <= {end_str} AND end_datetime >= {start_str}"
            )

            async with aiosqlite.connect(str(self.database_path)) as db:
                db.row_factory = aiosqlite.Row

                # First check total events in database
                total_cursor = await db.execute("SELECT COUNT(*) as count FROM cached_events")
                total_row = await total_cursor.fetchone()
                total_count = total_row["count"] if total_row else 0
                logger.info(f"DEBUG: Total events in database: {total_count}")

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

                logger.info(f"DEBUG: Query returned {row_count} rows")

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

        except Exception as e:
            logger.error(f"Failed to get events by date range: {e}")
            return []

    async def get_todays_events(self) -> List[CachedEvent]:
        """Get today's cached events.

        Returns:
            List of today's cached events
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
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()

            async with aiosqlite.connect(str(self.database_path)) as db:
                cursor = await db.execute(
                    """
                    DELETE FROM cached_events
                    WHERE end_datetime < ?
                """,
                    (cutoff_str,),
                )

                deleted_count = cursor.rowcount
                await db.commit()

                logger.info(f"Cleaned up {deleted_count} old events (older than {days_old} days)")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0

    async def get_cache_metadata(self) -> CacheMetadata:
        """Get cache metadata and statistics.

        Returns:
            Cache metadata object
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
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
                metadata = CacheMetadata(
                    total_events=total_events,
                    last_update=metadata_dict.get("last_update"),
                    last_successful_fetch=metadata_dict.get("last_successful_fetch"),
                    consecutive_failures=int(metadata_dict.get("consecutive_failures", 0)),
                    last_error=metadata_dict.get("last_error"),
                    last_error_time=metadata_dict.get("last_error_time"),
                )

                return metadata

        except Exception as e:
            logger.error(f"Failed to get cache metadata: {e}")
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

        except Exception as e:
            logger.error(f"Failed to update cache metadata: {e}")
            return False

    async def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics.

        Returns:
            Dictionary with database information
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                db.row_factory = aiosqlite.Row

                info: Dict[str, Any] = {}

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
                events_by_date: List[Dict[str, Any]] = [dict(row) for row in rows]
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

        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
