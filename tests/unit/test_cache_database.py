"""Unit tests for Cache Database error handling and edge cases."""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import aiosqlite
import pytest

from calendarbot.cache.database import DatabaseManager
from calendarbot.cache.models import CachedEvent, CacheMetadata


class TestDatabaseManagerErrorHandling:
    """Test DatabaseManager error handling scenarios."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create temporary database path for testing."""
        return tmp_path / "test_error_cache.db"

    @pytest.fixture
    def database_manager(self, temp_db_path: Path) -> DatabaseManager:
        """Create DatabaseManager instance for error testing."""
        return DatabaseManager(temp_db_path)

    @pytest.mark.asyncio
    async def test_initialize_when_database_connection_fails_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test initialization failure when database connection fails."""
        with patch("aiosqlite.connect", side_effect=sqlite3.Error("Connection failed")):
            result = await database_manager.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_when_permission_denied_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test initialization failure when database file permission denied."""
        with patch("aiosqlite.connect", side_effect=PermissionError("Permission denied")):
            result = await database_manager.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_when_pragma_execution_fails_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test initialization failure when PRAGMA commands fail."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = sqlite3.Error("PRAGMA failed")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_store_events_when_database_locked_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test store_events failure when database is locked."""
        sample_events = [
            CachedEvent(
                id="test_1",
                graph_id="graph_1",
                subject="Test Event",
                body_preview="Test body",
                start_datetime="2024-01-01T10:00:00",
                end_datetime="2024-01-01T11:00:00",
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                cached_at="2024-01-01T09:00:00",
            )
        ]

        with patch("aiosqlite.connect", side_effect=sqlite3.OperationalError("database is locked")):
            result = await database_manager.store_events(sample_events)

            assert result is False

    @pytest.mark.asyncio
    async def test_store_events_when_constraint_violation_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test store_events failure when constraint violation occurs."""
        sample_events = [
            CachedEvent(
                id="test_1",
                graph_id="graph_1",
                subject="Test Event",
                body_preview="Test body",
                start_datetime="2024-01-01T10:00:00",
                end_datetime="2024-01-01T11:00:00",
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                cached_at="2024-01-01T09:00:00",
            )
        ]

        mock_db = AsyncMock()
        mock_db.executemany.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.store_events(sample_events)

            assert result is False

    @pytest.mark.asyncio
    async def test_store_events_when_transaction_rollback_needed_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test store_events failure requiring transaction rollback."""
        sample_events = [
            CachedEvent(
                id="test_1",
                graph_id="graph_1",
                subject="Test Event",
                body_preview="Test body",
                start_datetime="2024-01-01T10:00:00",
                end_datetime="2024-01-01T11:00:00",
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                cached_at="2024-01-01T09:00:00",
            )
        ]

        mock_db = AsyncMock()
        mock_db.executemany.side_effect = Exception("Transaction failed")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.store_events(sample_events)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_when_connection_fails_then_returns_empty_list(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_events_by_date_range failure when connection fails."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        with patch("aiosqlite.connect", side_effect=sqlite3.Error("Connection failed")):
            result = await database_manager.get_events_by_date_range(start_date, end_date)

            assert result == []

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_when_query_execution_fails_then_returns_empty_list(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_events_by_date_range failure when query execution fails."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        mock_db = AsyncMock()
        mock_db.execute.side_effect = sqlite3.Error("Query failed")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.get_events_by_date_range(start_date, end_date)

            assert result == []

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_when_data_corruption_then_returns_empty_list(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_events_by_date_range failure when data corruption encountered."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        mock_db = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [{"corrupted": "data"}]  # Missing required fields
        mock_db.execute.return_value = mock_cursor
        mock_db.row_factory = aiosqlite.Row

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.get_events_by_date_range(start_date, end_date)

            assert result == []

    @pytest.mark.asyncio
    async def test_get_todays_events_when_database_error_then_returns_empty_list(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_todays_events failure when database error occurs."""
        with patch("aiosqlite.connect", side_effect=Exception("Database error")):
            result = await database_manager.get_todays_events()

            assert result == []

    @pytest.mark.asyncio
    async def test_cleanup_old_events_when_delete_fails_then_returns_zero(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test cleanup_old_events failure when delete operation fails."""
        with patch("aiosqlite.connect", side_effect=sqlite3.Error("Delete failed")):
            result = await database_manager.cleanup_old_events(days_old=7)

            assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_events_when_permission_error_then_returns_zero(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test cleanup_old_events failure when permission error occurs."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = PermissionError("Permission denied")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.cleanup_old_events(days_old=7)

            assert result == 0

    @pytest.mark.asyncio
    async def test_get_cache_metadata_when_connection_fails_then_returns_default(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_cache_metadata failure when connection fails."""
        with patch("aiosqlite.connect", side_effect=sqlite3.Error("Connection failed")):
            result = await database_manager.get_cache_metadata()

            # Should return default CacheMetadata object
            assert isinstance(result, CacheMetadata)
            assert result.total_events == 0
            assert result.last_update is None

    @pytest.mark.asyncio
    async def test_get_cache_metadata_when_table_corrupted_then_returns_default(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_cache_metadata failure when metadata table is corrupted."""
        mock_db = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.side_effect = sqlite3.DatabaseError("Table corrupted")
        mock_db.execute.return_value = mock_cursor

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.get_cache_metadata()

            assert isinstance(result, CacheMetadata)
            assert result.total_events == 0

    @pytest.mark.asyncio
    async def test_update_cache_metadata_when_update_fails_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test update_cache_metadata failure when update operation fails."""
        with patch("aiosqlite.connect", side_effect=sqlite3.Error("Update failed")):
            result = await database_manager.update_cache_metadata(
                last_update="2024-01-01T10:00:00", consecutive_failures=0
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_update_cache_metadata_when_constraint_violation_then_returns_false(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test update_cache_metadata failure when constraint violation occurs."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = sqlite3.IntegrityError("Constraint failed")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.update_cache_metadata(
                last_update="2024-01-01T10:00:00", consecutive_failures=0
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_get_database_info_when_pragma_fails_then_returns_empty_dict(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_database_info failure when PRAGMA commands fail."""
        with patch("aiosqlite.connect", side_effect=sqlite3.Error("PRAGMA failed")):
            result = await database_manager.get_database_info()

            assert result == {}

    @pytest.mark.asyncio
    async def test_get_database_info_when_file_stat_fails_then_handles_gracefully(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_database_info when file stat operation fails."""
        mock_db = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = [0]
        mock_db.execute.return_value = mock_cursor

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db
            # Mock pathlib.Path.exists method to return False
            with patch("pathlib.Path.exists", return_value=False):
                result = await database_manager.get_database_info()

                # Should not include file_size_bytes when file doesn't exist
                assert "file_size_bytes" not in result
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_database_info_when_query_timeout_then_returns_empty_dict(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test get_database_info failure when query times out."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = asyncio.TimeoutError("Query timeout")

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.get_database_info()

            assert result == {}

    @pytest.mark.parametrize(
        "error_type,expected_events",
        [
            (sqlite3.Error("General SQL error"), []),
            (PermissionError("Permission denied"), []),
            (sqlite3.OperationalError("Database locked"), []),
            (sqlite3.DatabaseError("Database corrupted"), []),
            (Exception("Unexpected error"), []),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_events_by_date_range_various_errors_then_returns_empty_list(
        self, database_manager: DatabaseManager, error_type: Exception, expected_events: List
    ) -> None:
        """Test get_events_by_date_range handles various error types gracefully."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        with patch("aiosqlite.connect", side_effect=error_type):
            result = await database_manager.get_events_by_date_range(start_date, end_date)

            assert result == expected_events

    @pytest.mark.parametrize(
        "metadata_updates,should_fail",
        [
            ({"last_update": "invalid_date"}, False),  # Should handle gracefully
            ({"consecutive_failures": "not_a_number"}, False),  # Should convert to string
            ({"very_long_key" * 100: "value"}, False),  # Should handle long keys
            ({}, False),  # Empty updates should succeed
        ],
    )
    @pytest.mark.asyncio
    async def test_update_cache_metadata_edge_cases_then_handles_gracefully(
        self, database_manager: DatabaseManager, metadata_updates: dict, should_fail: bool
    ) -> None:
        """Test update_cache_metadata handles edge cases gracefully."""
        mock_db = AsyncMock()
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_db

            result = await database_manager.update_cache_metadata(**metadata_updates)

            if should_fail:
                assert result is False
            else:
                assert result is True


class TestDatabaseManagerRecoveryScenarios:
    """Test DatabaseManager recovery and resilience scenarios."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create temporary database path for testing."""
        return tmp_path / "test_recovery_cache.db"

    @pytest.fixture
    def database_manager(self, temp_db_path: Path) -> DatabaseManager:
        """Create DatabaseManager instance for recovery testing."""
        return DatabaseManager(temp_db_path)

    @pytest.mark.asyncio
    async def test_store_events_recovery_after_temporary_failure(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test store_events can recover after temporary failures."""
        sample_events = [
            CachedEvent(
                id="test_1",
                graph_id="graph_1",
                subject="Test Event",
                body_preview="Test body",
                start_datetime="2024-01-01T10:00:00",
                end_datetime="2024-01-01T11:00:00",
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                cached_at="2024-01-01T09:00:00",
            )
        ]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("Temporary failure")
            # Second call should succeed
            mock_db = AsyncMock()
            mock_db.executemany.return_value = None
            mock_db.commit.return_value = None
            return mock_db.__aenter__.return_value

        with patch("aiosqlite.connect", side_effect=side_effect):
            # First call should fail
            result1 = await database_manager.store_events(sample_events)
            assert result1 is False

            # Second call should succeed (in real scenario after retry)
            result2 = await database_manager.store_events(sample_events)
            assert result2 is True  # Should succeed on recovery

    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion_recovery(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test recovery when database connection pool is exhausted."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        with patch("aiosqlite.connect", side_effect=sqlite3.Error("too many connections")):
            result = await database_manager.get_events_by_date_range(start_date, end_date)

            # Should return empty list and log error, allowing application to continue
            assert result == []

    @pytest.mark.asyncio
    async def test_concurrent_access_conflict_handling(
        self, database_manager: DatabaseManager
    ) -> None:
        """Test handling of concurrent access conflicts."""
        sample_events = [
            CachedEvent(
                id="concurrent_test",
                graph_id="concurrent_graph",
                subject="Concurrent Event",
                body_preview="Concurrent body",
                start_datetime="2024-01-01T10:00:00",
                end_datetime="2024-01-01T11:00:00",
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                cached_at="2024-01-01T09:00:00",
            )
        ]

        with patch("aiosqlite.connect", side_effect=sqlite3.OperationalError("database is locked")):
            result = await database_manager.store_events(sample_events)

            # Should fail gracefully without crashing
            assert result is False
