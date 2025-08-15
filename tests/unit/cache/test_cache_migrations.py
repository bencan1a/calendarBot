"""Unit tests for calendarbot.cache.migrations module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest

from calendarbot.cache import migrations


class TestDatabaseMigration:
    """Test cases for DatabaseMigration class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            yield Path(tmp.name)

    @pytest.fixture
    def migration_handler(self, temp_db_path):
        """Create a DatabaseMigration instance for testing."""
        return migrations.DatabaseMigration(temp_db_path)

    @pytest.mark.asyncio
    async def test_database_migration_initialization(self, temp_db_path):
        """Test DatabaseMigration initialization."""
        handler = migrations.DatabaseMigration(temp_db_path)
        assert handler.database_path == temp_db_path

    @pytest.mark.asyncio
    async def test_get_current_version_no_database(self, migration_handler):
        """Test getting version when database doesn't exist."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Database not found")

            version = await migration_handler.get_current_version()
            assert version == 0

    @pytest.mark.asyncio
    async def test_get_current_version_success(self, migration_handler):
        """Test successful version retrieval."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = [2]
            mock_db.execute.return_value = mock_cursor
            mock_connect.return_value.__aenter__.return_value = mock_db

            version = await migration_handler.get_current_version()
            assert version == 2
            mock_db.execute.assert_called_once_with("PRAGMA user_version")

    @pytest.mark.asyncio
    async def test_get_current_version_no_row(self, migration_handler):
        """Test version retrieval when no row is returned."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = None
            mock_db.execute.return_value = mock_cursor
            mock_connect.return_value.__aenter__.return_value = mock_db

            version = await migration_handler.get_current_version()
            assert version == 0

    @pytest.mark.asyncio
    async def test_set_version_success(self, migration_handler):
        """Test successful version setting."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await migration_handler.set_version(2)
            assert result is True
            mock_db.execute.assert_called_once_with("PRAGMA user_version = 2")
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_version_failure(self, migration_handler):
        """Test version setting failure."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Database error")

            result = await migration_handler.set_version(2)
            assert result is False

    @pytest.mark.asyncio
    async def test_apply_migration_v1_to_v2_success(self, migration_handler):
        """Test successful v1 to v2 migration."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await migration_handler.apply_migration_v1_to_v2()
            assert result is True

            # Verify all migration SQL statements were executed
            assert mock_db.execute.call_count >= 7  # 5 ALTER TABLE + 2 CREATE INDEX
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_migration_v1_to_v2_failure(self, migration_handler):
        """Test v1 to v2 migration failure."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Migration failed")

            result = await migration_handler.apply_migration_v1_to_v2()
            assert result is False

    @pytest.mark.asyncio
    async def test_create_focus_sessions_table_success(self, migration_handler):
        """Test successful focus_sessions table creation."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await migration_handler.create_focus_sessions_table()
            assert result is True

            # Verify table creation and index creation
            assert mock_db.execute.call_count == 3  # CREATE TABLE + 2 CREATE INDEX
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_focus_sessions_table_failure(self, migration_handler):
        """Test focus_sessions table creation failure."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Table creation failed")

            result = await migration_handler.create_focus_sessions_table()
            assert result is False

    @pytest.mark.asyncio
    async def test_create_sync_reliability_table_success(self, migration_handler):
        """Test successful sync_reliability table creation."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await migration_handler.create_sync_reliability_table()
            assert result is True

            # Verify table creation and index creation
            assert mock_db.execute.call_count == 3  # CREATE TABLE + 2 CREATE INDEX
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sync_reliability_table_failure(self, migration_handler):
        """Test sync_reliability table creation failure."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Table creation failed")

            result = await migration_handler.create_sync_reliability_table()
            assert result is False

    @pytest.mark.asyncio
    async def test_migrate_to_latest_already_current(self, migration_handler):
        """Test migration when database is already at latest version."""
        with patch.object(migration_handler, "get_current_version") as mock_get_version:
            mock_get_version.return_value = 2  # Already at target version

            result = await migration_handler.migrate_to_latest()
            assert result is True

    @pytest.mark.asyncio
    async def test_migrate_to_latest_from_v0(self, migration_handler):
        """Test migration from version 0 to latest."""
        with patch.object(migration_handler, "get_current_version") as mock_get_version:
            with patch.object(migration_handler, "set_version") as mock_set_version:
                with patch.object(migration_handler, "apply_migration_v1_to_v2") as mock_apply:
                    with patch.object(
                        migration_handler, "create_focus_sessions_table"
                    ) as mock_focus:
                        with patch.object(
                            migration_handler, "create_sync_reliability_table"
                        ) as mock_sync:
                            mock_get_version.return_value = 0
                            mock_apply.return_value = True
                            mock_focus.return_value = True
                            mock_sync.return_value = True

                            result = await migration_handler.migrate_to_latest()
                            assert result is True

                            # Verify migration steps
                            assert mock_set_version.call_count == 2  # Set to v1, then v2
                            mock_apply.assert_called_once()
                            mock_focus.assert_called_once()
                            mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_to_latest_migration_failure(self, migration_handler):
        """Test migration failure handling."""
        with patch.object(migration_handler, "get_current_version") as mock_get_version:
            with patch.object(migration_handler, "set_version") as mock_set_version:
                with patch.object(migration_handler, "apply_migration_v1_to_v2") as mock_apply:
                    mock_get_version.return_value = 1
                    mock_apply.return_value = False  # Migration fails

                    result = await migration_handler.migrate_to_latest()
                    assert result is False

    @pytest.mark.asyncio
    async def test_get_migration_status_success(self, migration_handler):
        """Test successful migration status retrieval."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_db.row_factory = aiosqlite.Row

            # Mock cursor for table queries
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [
                {"name": "focus_sessions"},
                {"name": "sync_reliability"},
            ]

            # Mock cursor for column queries
            mock_column_cursor = AsyncMock()
            mock_column_cursor.fetchall.return_value = [
                {"name": "id"},
                {"name": "time_remaining_minutes"},
                {"name": "confidence_score"},
                {"name": "focus_protection_level"},
                {"name": "last_time_calculation"},
                {"name": "is_time_sensitive"},
            ]

            mock_db.execute.side_effect = [mock_cursor, mock_column_cursor]
            mock_connect.return_value.__aenter__.return_value = mock_db

            with patch.object(migration_handler, "get_current_version") as mock_get_version:
                mock_get_version.return_value = 2

                status = await migration_handler.get_migration_status()

                assert status["current_version"] == 2
                assert status["target_version"] == 2
                assert status["has_focus_sessions_table"] is True
                assert status["has_sync_reliability_table"] is True
                assert status["has_time_awareness_columns"] is True
                assert status["needs_migration"] is False

    @pytest.mark.asyncio
    async def test_get_migration_status_failure(self, migration_handler):
        """Test migration status retrieval failure."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Database error")

            status = await migration_handler.get_migration_status()
            assert "error" in status
            assert status["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_get_migration_status_needs_migration(self, migration_handler):
        """Test migration status when migration is needed."""
        with patch("aiosqlite.connect") as mock_connect:
            mock_db = AsyncMock()
            mock_db.row_factory = aiosqlite.Row

            # Mock cursor for table queries (no new tables)
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = []

            # Mock cursor for column queries (missing time awareness columns)
            mock_column_cursor = AsyncMock()
            mock_column_cursor.fetchall.return_value = [
                {"name": "id"},
                {"name": "title"},  # Basic columns only
            ]

            mock_db.execute.side_effect = [mock_cursor, mock_column_cursor]
            mock_connect.return_value.__aenter__.return_value = mock_db

            with patch.object(migration_handler, "get_current_version") as mock_get_version:
                mock_get_version.return_value = 1

                status = await migration_handler.get_migration_status()

                assert status["current_version"] == 1
                assert status["target_version"] == 2
                assert status["has_focus_sessions_table"] is False
                assert status["has_sync_reliability_table"] is False
                assert status["has_time_awareness_columns"] is False
                assert status["needs_migration"] is True
