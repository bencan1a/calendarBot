"""Database migration utilities for calendar cache schema updates."""

import logging
from pathlib import Path
from typing import Any, cast

import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handles database schema migrations for calendar cache."""

    def __init__(self, database_path: Path):
        """Initialize migration handler.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path

    async def get_current_version(self) -> int:
        """Get current database schema version.

        Returns:
            Current version number, 0 if not set
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                cursor = await db.execute("PRAGMA user_version")
                row = await cursor.fetchone()
                if row:
                    # Cast to int to satisfy mypy - PRAGMA user_version always returns integer
                    return cast(int, row[0])
                return 0
        except Exception:
            logger.exception("Failed to get database version")
            return 0

    async def set_version(self, version: int) -> bool:
        """Set database schema version.

        Args:
            version: Version number to set

        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                await db.execute(f"PRAGMA user_version = {version}")
                await db.commit()
                logger.info(f"Set database version to {version}")
                return True
        except Exception:
            logger.exception("Failed to set database version")
            return False

    async def apply_migration_v1_to_v2(self) -> bool:
        """Apply migration from v1 to v2: Add time awareness fields.

        Adds the following fields to cached_events table:
        - time_remaining_minutes: Calculated minutes until event start
        - confidence_score: User confidence in event accuracy (0.0-1.0)
        - focus_protection_level: Protection level (0=none, 1=minimal, 2=moderate, 3=strict)
        - last_time_calculation: When time remaining was last calculated
        - is_time_sensitive: Whether event should trigger time awareness alerts

        Returns:
            True if migration successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                logger.info("Applying database migration v1 -> v2: Adding time awareness fields")

                # Add new columns for time awareness
                migration_sql = [
                    """ALTER TABLE cached_events
                       ADD COLUMN time_remaining_minutes INTEGER DEFAULT NULL""",
                    """ALTER TABLE cached_events
                       ADD COLUMN confidence_score REAL DEFAULT 0.8""",
                    """ALTER TABLE cached_events
                       ADD COLUMN focus_protection_level INTEGER DEFAULT 1""",
                    """ALTER TABLE cached_events
                       ADD COLUMN last_time_calculation TEXT DEFAULT NULL""",
                    """ALTER TABLE cached_events
                       ADD COLUMN is_time_sensitive INTEGER DEFAULT 1""",
                ]

                for sql in migration_sql:
                    await db.execute(sql)

                # Create index for efficient time-based queries
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_time_remaining
                    ON cached_events(time_remaining_minutes, is_time_sensitive)
                """
                )

                # Create index for confidence scoring queries
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_confidence
                    ON cached_events(confidence_score, last_time_calculation)
                """
                )

                await db.commit()
                logger.info("Successfully applied migration v1 -> v2")
                return True

        except Exception:
            logger.exception("Failed to apply migration v1 -> v2")
            return False

    async def create_focus_sessions_table(self) -> bool:
        """Create focus_sessions table for tracking focus protection state.

        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS focus_sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT DEFAULT 'default',
                        session_start TEXT NOT NULL,
                        session_end TEXT,
                        protection_level INTEGER NOT NULL DEFAULT 2,
                        interrupted_count INTEGER DEFAULT 0,
                        last_interruption TEXT,
                        session_type TEXT DEFAULT 'manual',
                        associated_event_id TEXT,
                        is_active INTEGER DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (associated_event_id) REFERENCES cached_events(id)
                    )
                """
                )

                # Create indexes for efficient querying
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_focus_sessions_active
                    ON focus_sessions(is_active, session_start, session_end)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_focus_sessions_event
                    ON focus_sessions(associated_event_id)
                """
                )

                await db.commit()
                logger.info("Created focus_sessions table")
                return True

        except Exception:
            logger.exception("Failed to create focus_sessions table")
            return False

    async def create_sync_reliability_table(self) -> bool:
        """Create sync_reliability table for monitoring calendar sync health.

        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sync_reliability (
                        id TEXT PRIMARY KEY,
                        source_name TEXT NOT NULL,
                        check_timestamp TEXT NOT NULL,
                        sync_status TEXT NOT NULL,
                        response_time_ms REAL,
                        events_synced INTEGER DEFAULT 0,
                        error_message TEXT,
                        error_category TEXT,
                        consecutive_failures INTEGER DEFAULT 0,
                        data_corruption_detected INTEGER DEFAULT 0,
                        reliability_score REAL DEFAULT 1.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for performance
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sync_reliability_source
                    ON sync_reliability(source_name, check_timestamp DESC)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sync_reliability_status
                    ON sync_reliability(sync_status, reliability_score)
                """
                )

                await db.commit()
                logger.info("Created sync_reliability table")
                return True

        except Exception:
            logger.exception("Failed to create sync_reliability table")
            return False

    async def migrate_to_latest(self) -> bool:
        """Apply all pending migrations to bring database to latest version.

        Returns:
            True if all migrations successful, False otherwise
        """
        current_version = await self.get_current_version()
        target_version = 2  # Latest version

        logger.info(f"Current database version: {current_version}, target: {target_version}")

        if current_version >= target_version:
            logger.info("Database already at latest version")
            return True

        # Apply migrations sequentially
        migration_success = True

        if current_version < 1:
            # Version 0 -> 1: Initial schema (handled by DatabaseManager.initialize)
            await self.set_version(1)
            current_version = 1

        if current_version < 2:
            # Version 1 -> 2: Add time awareness fields
            if await self.apply_migration_v1_to_v2():
                await self.create_focus_sessions_table()
                await self.create_sync_reliability_table()
                await self.set_version(2)
                logger.info("Successfully migrated to version 2")
            else:
                logger.error("Failed to migrate to version 2")
                migration_success = False

        return migration_success

    async def get_migration_status(self) -> dict[str, Any]:
        """Get current migration status and table information.

        Returns:
            Dictionary with migration status information
        """
        try:
            async with aiosqlite.connect(str(self.database_path)) as db:
                db.row_factory = aiosqlite.Row

                # Get current version
                current_version = await self.get_current_version()

                # Check if new tables exist
                cursor = await db.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN ('focus_sessions', 'sync_reliability')
                """
                )
                existing_tables = [row["name"] for row in await cursor.fetchall()]

                # Check if new columns exist in cached_events
                cursor = await db.execute("PRAGMA table_info(cached_events)")
                columns = [row["name"] for row in await cursor.fetchall()]

                time_awareness_columns = [
                    "time_remaining_minutes",
                    "confidence_score",
                    "focus_protection_level",
                    "last_time_calculation",
                    "is_time_sensitive",
                ]

                has_time_awareness = all(col in columns for col in time_awareness_columns)

                return {
                    "current_version": current_version,
                    "target_version": 2,
                    "has_focus_sessions_table": "focus_sessions" in existing_tables,
                    "has_sync_reliability_table": "sync_reliability" in existing_tables,
                    "has_time_awareness_columns": has_time_awareness,
                    "needs_migration": current_version < 2 or not has_time_awareness,
                }

        except Exception as e:
            logger.exception("Failed to get migration status")
            return {"error": str(e)}
