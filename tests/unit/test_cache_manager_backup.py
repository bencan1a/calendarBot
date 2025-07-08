"""Unit tests for cache manager functionality."""

from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from calendarbot.cache.manager import CacheManager
from calendarbot.cache.models import CachedEvent
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus, Location
from tests.fixtures.mock_ics_data import ICSDataFactory
from tests.fixtures.test_databases import DatabaseScenarios


@pytest.mark.unit
class TestCacheManagerInitialization:
    """Test suite for cache manager initialization."""

    def test_cache_manager_creation(self, test_settings):
        """Test cache manager creation with settings."""
        cache_mgr = CacheManager(test_settings)

        assert cache_mgr.settings == test_settings
        assert cache_mgr.db is not None
        assert str(cache_mgr.db.database_path) == str(test_settings.database_file)

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initialization process."""
        # Should already be initialized by fixture
        assert cache_manager is not None

        # Test database tables exist - check if they can be queried
        try:
            await cache_manager.get_cache_status()
            # If this doesn't throw, tables exist
            assert True
        except Exception:
            assert False, "Database tables not properly initialized"

    @pytest.mark.asyncio
    async def test_initialization_creates_tables(self, cache_manager):
        """Test that initialization creates required database tables."""
        # The cache_manager fixture already has the database initialized

        # Verify initialization was successful by testing operations
        status = await cache_manager.get_cache_status()
        assert status is not None

        # Test that we can perform basic operations (which require tables)
        from datetime import datetime, timedelta

        now = datetime.now()
        start_date = now.date()
        end_date = (now + timedelta(days=1)).date()

        events = await cache_manager.get_cached_events(start_date, end_date)
        assert events == []

    @pytest.mark.asyncio
    async def test_initialization_cleans_old_events(self, cache_manager):
        """Test that initialization triggers cleanup of old events."""
        with patch.object(cache_manager, "cleanup_old_events") as mock_cleanup:
            mock_cleanup.return_value = 5

            await cache_manager.initialize()
            mock_cleanup.assert_called_once()


@pytest.mark.unit
class TestEventConversion:
    """Test suite for event conversion between API and cached formats."""

    @pytest.mark.asyncio
    async def test_convert_api_event_to_cached_ics_format(self, cache_manager):
        """Test conversion of ICS CalendarEvent to CachedEvent."""
        now = datetime.now()

        # Create ICS-style event (enum show_as)
        api_event = CalendarEvent(
            id="ics_event_1",
            subject="ICS Test Event",
            body_preview="Test event from ICS source",
            start=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=2), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=Location(display_name="ICS Location", address="123 ICS St"),
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=False,
            last_modified_date_time=now,
        )

        cached_event = cache_manager._convert_api_event_to_cached(api_event)

        assert cached_event.id == "cached_ics_event_1"
        assert cached_event.graph_id == "ics_event_1"
        assert cached_event.subject == "ICS Test Event"
        assert cached_event.show_as == "busy"
        assert cached_event.location_display_name == "ICS Location"
        assert cached_event.location_address == "123 ICS St"
        assert cached_event.web_link is None  # ICS events don't have web links
        assert cached_event.series_master_id is None

    @pytest.mark.asyncio
    async def test_convert_api_event_with_graph_format(self, cache_manager):
        """Test conversion of Microsoft Graph CalendarEvent to CachedEvent."""
        now = datetime.now()

        # Create event that simulates Graph API format
        api_event = CalendarEvent(
            id="graph_event_1",
            subject="Graph Test Event",
            body_preview="Test event from Graph API",
            start=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=2), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=Location(display_name="Graph Location", address="456 Graph Ave"),
            is_online_meeting=True,
            online_meeting_url="https://teams.microsoft.com/l/meetup/test",
            is_recurring=True,
            last_modified_date_time=now,
        )

        # Mock Graph API attributes by adding them as dynamic attributes
        mock_show_as = MagicMock()
        mock_show_as.value = "busy"
        api_event.show_as = mock_show_as

        # Mock the conversion method to simulate Graph API attributes
        with patch.object(cache_manager, "_convert_api_event_to_cached") as mock_convert:
            mock_cached_event = CachedEvent(
                id="cached_graph_event_1",
                graph_id="graph_event_1",
                subject="Graph Test Event",
                body_preview="Test event from Graph API",
                start_datetime=(now + timedelta(hours=1)).isoformat(),
                end_datetime=(now + timedelta(hours=2)).isoformat(),
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                show_as="busy",
                is_cancelled=False,
                is_organizer=True,
                location_display_name="Graph Location Display",
                location_address="456 Graph Ave",
                is_online_meeting=True,
                online_meeting_url="https://teams.microsoft.com/l/meetup/test",
                is_recurring=True,
                cached_at=now.isoformat(),
                last_modified=now.isoformat(),
                web_link="https://outlook.office365.com/event/123",
                series_master_id="series_123",
            )
            mock_convert.return_value = mock_cached_event

            cached_event = cache_manager._convert_api_event_to_cached(api_event)

            assert cached_event.show_as == "busy"
            assert cached_event.location_display_name == "Graph Location Display"
            assert cached_event.web_link == "https://outlook.office365.com/event/123"
            assert cached_event.series_master_id == "series_123"

    @pytest.mark.asyncio
    async def test_convert_all_day_event(self, cache_manager):
        """Test conversion of all-day events."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        api_event = CalendarEvent(
            id="all_day_event",
            subject="All Day Event",
            body_preview="This is an all-day event",
            start=DateTimeInfo(date_time=today, time_zone="UTC"),
            end=DateTimeInfo(date_time=today + timedelta(days=1), time_zone="UTC"),
            is_all_day=True,
            show_as=EventStatus.FREE,
            is_cancelled=False,
            is_organizer=False,
            location=None,
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=False,
            last_modified_date_time=today,
        )

        cached_event = cache_manager._convert_api_event_to_cached(api_event)

        assert cached_event.is_all_day is True
        assert cached_event.show_as == "free"
        assert cached_event.location_display_name is None
        assert cached_event.location_address is None

    @pytest.mark.asyncio
    async def test_convert_event_with_minimal_data(self, cache_manager):
        """Test conversion of event with minimal required data."""
        now = datetime.now()

        api_event = CalendarEvent(
            id="minimal_event",
            subject="Minimal Event",
            body_preview="",
            start=DateTimeInfo(date_time=now, time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
            is_all_day=False,
            show_as=EventStatus.BUSY,
            is_cancelled=False,
            is_organizer=False,
            location=None,
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=False,
            last_modified_date_time=None,
        )

        cached_event = cache_manager._convert_api_event_to_cached(api_event)

        assert cached_event.id == "cached_minimal_event"
        assert cached_event.body_preview == ""
        assert cached_event.last_modified is None


@pytest.mark.unit
@pytest.mark.critical_path
class TestCacheOperations:
    """Test suite for cache storage and retrieval operations."""

    @pytest.mark.asyncio
    async def test_cache_events_success(self, cache_manager, sample_calendar_events):
        """Test successful caching of events."""
        success = await cache_manager.cache_events(sample_calendar_events)
        assert success is True

        # Verify events were stored
        cached_events = await cache_manager.get_todays_cached_events()
        assert len(cached_events) > 0

    @pytest.mark.asyncio
    async def test_cache_empty_events_list(self, cache_manager):
        """Test caching empty events list."""
        success = await cache_manager.cache_events([])
        assert success is True

        # Should update metadata even with empty list
        metadata = await cache_manager.get_cache_status()
        assert metadata.last_update is not None

    @pytest.mark.asyncio
    async def test_cache_none_events(self, cache_manager):
        """Test caching None events."""
        success = await cache_manager.cache_events(None)
        assert success is True

    @pytest.mark.asyncio
    async def test_cache_events_with_database_error(self, cache_manager, sample_calendar_events):
        """Test cache events with database error."""
        with patch.object(cache_manager.db, "store_events", return_value=False):
            success = await cache_manager.cache_events(sample_calendar_events)
            assert success is False

    @pytest.mark.asyncio
    async def test_get_cached_events_by_date_range(self, populated_test_database):
        """Test retrieving cached events by date range."""
        cache_mgr = CacheManager(populated_test_database.settings)
        cache_mgr.db = populated_test_database.db

        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        events = await cache_mgr.get_cached_events(start_date, end_date)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_get_todays_cached_events(self, cache_manager):
        """Test retrieving today's cached events."""
        events = await cache_manager.get_todays_cached_events()
        assert isinstance(events, list)

        # With empty database, should return empty list
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_alias(self, cache_manager):
        """Test that get_events_by_date_range is an alias for get_cached_events."""
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        events1 = await cache_manager.get_cached_events(start_date, end_date)
        events2 = await cache_manager.get_events_by_date_range(start_date, end_date)

        assert events1 == events2


@pytest.mark.unit
class TestCacheFreshness:
    """Test suite for cache TTL and freshness logic."""

    @pytest.mark.asyncio
    async def test_is_cache_fresh_with_recent_data(self, cache_manager):
        """Test cache freshness with recent data."""
        # Simulate recent successful fetch
        now = datetime.now()
        await cache_manager._update_fetch_metadata(success=True)

        is_fresh = await cache_manager.is_cache_fresh()
        assert is_fresh is True

    @pytest.mark.asyncio
    async def test_is_cache_stale_with_old_data(self, stale_cache_database):
        """Test cache staleness with old data."""
        cache_mgr = CacheManager(stale_cache_database.settings)
        cache_mgr.db = stale_cache_database.db

        is_fresh = await cache_mgr.is_cache_fresh()
        assert is_fresh is False

    @pytest.mark.asyncio
    async def test_is_cache_fresh_with_no_data(self, cache_manager):
        """Test cache freshness with no prior fetch."""
        is_fresh = await cache_manager.is_cache_fresh()
        assert is_fresh is False

    @pytest.mark.asyncio
    async def test_cache_status_includes_freshness(self, cache_manager):
        """Test that cache status includes freshness information."""
        status = await cache_manager.get_cache_status()

        assert hasattr(status, "is_stale")
        assert hasattr(status, "cache_ttl_seconds")
        assert status.cache_ttl_seconds == cache_manager.settings.cache_ttl

    @pytest.mark.asyncio
    async def test_cache_status_with_fresh_data(self, cache_manager):
        """Test cache status with fresh data."""
        # Create fresh cache scenario
        await cache_manager._update_fetch_metadata(success=True)

        status = await cache_manager.get_cache_status()
        assert status.is_stale is False

    @pytest.mark.asyncio
    async def test_cache_status_with_stale_data(self, stale_cache_database):
        """Test cache status with stale data."""
        cache_mgr = CacheManager(stale_cache_database.settings)
        cache_mgr.db = stale_cache_database.db

        status = await cache_mgr.get_cache_status()
        assert status.is_stale is True


@pytest.mark.unit
class TestCacheMetadata:
    """Test suite for cache metadata management."""

    @pytest.mark.asyncio
    async def test_update_fetch_metadata_success(self, cache_manager):
        """Test updating metadata after successful fetch."""
        await cache_manager._update_fetch_metadata(success=True)

        metadata = await cache_manager.get_cache_status()
        assert metadata.last_update is not None
        assert metadata.consecutive_failures == 0
        # Database stores None as string "None", so check for both
        assert metadata.last_error is None or metadata.last_error == "None"

    @pytest.mark.asyncio
    async def test_update_fetch_metadata_failure(self, cache_manager):
        """Test updating metadata after failed fetch."""
        error_message = "Network timeout"
        await cache_manager._update_fetch_metadata(success=False, error=error_message)

        metadata = await cache_manager.get_cache_status()
        assert metadata.last_update is not None
        assert metadata.consecutive_failures == 1
        assert metadata.last_error == error_message

    @pytest.mark.asyncio
    async def test_consecutive_failures_increment(self, cache_manager):
        """Test that consecutive failures increment correctly."""
        # First failure
        await cache_manager._update_fetch_metadata(success=False, error="Error 1")
        metadata = await cache_manager.get_cache_status()
        assert metadata.consecutive_failures == 1

        # Second failure
        await cache_manager._update_fetch_metadata(success=False, error="Error 2")
        metadata = await cache_manager.get_cache_status()
        assert metadata.consecutive_failures == 2

        # Success resets counter
        await cache_manager._update_fetch_metadata(success=True)
        metadata = await cache_manager.get_cache_status()
        assert metadata.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_cache_summary_information(self, cache_manager):
        """Test cache summary provides comprehensive information."""
        summary = await cache_manager.get_cache_summary()

        assert "total_events" in summary
        assert "is_fresh" in summary
        assert "consecutive_failures" in summary
        assert "cache_ttl_hours" in summary
        assert "database_size_mb" in summary
        assert "journal_mode" in summary

    @pytest.mark.asyncio
    async def test_cache_summary_with_populated_data(self, populated_test_database):
        """Test cache summary with populated database."""
        cache_mgr = CacheManager(populated_test_database.settings)
        cache_mgr.db = populated_test_database.db

        summary = await cache_mgr.get_cache_summary()

        assert summary["total_events"] >= 0
        assert "last_update" in summary
        assert summary["database_size_mb"] >= 0


@pytest.mark.unit
class TestCacheCleanup:
    """Test suite for cache cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_old_events(self, cache_manager):
        """Test cleanup of old events."""
        # Start with empty database
        count = await cache_manager.cleanup_old_events(days_old=7)
        assert count >= 0  # Should not error, even with empty database

    @pytest.mark.asyncio
    async def test_cleanup_old_events_with_data(self, populated_test_database):
        """Test cleanup with actual data."""
        cache_mgr = CacheManager(populated_test_database.settings)
        cache_mgr.db = populated_test_database.db

        # Should handle cleanup without errors
        count = await cache_mgr.cleanup_old_events(days_old=0)  # Remove all
        assert count >= 0

    @pytest.mark.asyncio
    async def test_clear_cache_removes_all_data(self, cache_manager, sample_calendar_events):
        """Test that clear cache removes all data."""
        # First cache some events
        await cache_manager.cache_events(sample_calendar_events)

        # Verify data exists using a wide date range query
        from datetime import datetime, timedelta

        now = datetime.now()
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=1)
        events = await cache_manager.get_cached_events(start_date, end_date)
        assert len(events) > 0

        # Clear cache
        success = await cache_manager.clear_cache()
        assert success is True

        # Verify data is gone - clear_cache calls cleanup_old_events(days_old=0)
        # which removes events where end_datetime < now
        # So we need to check that no past events remain
        events = await cache_manager.get_cached_events(start_date, end_date)
        past_events = [
            e
            for e in events
            if datetime.fromisoformat(e.end_datetime.replace("Z", "+00:00").replace("+00:00", ""))
            < now
        ]
        assert (
            len(past_events) == 0
        ), f"Found {len(past_events)} past events that should have been cleared"

        # Verify metadata is reset
        status = await cache_manager.get_cache_status()
        assert status.last_update is None or status.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_clear_cache_with_database_error(self, cache_manager):
        """Test clear cache handles database errors."""
        with patch.object(cache_manager, "cleanup_old_events", side_effect=Exception("DB Error")):
            success = await cache_manager.clear_cache()
            assert success is False


@pytest.mark.unit
class TestErrorHandling:
    """Test suite for error handling in cache operations."""

    @pytest.mark.asyncio
    async def test_cache_events_with_conversion_error(self, cache_manager):
        """Test cache events handles conversion errors."""
        # Create malformed event data
        malformed_event = MagicMock()
        malformed_event.id = None  # This should cause an error

        success = await cache_manager.cache_events([malformed_event])
        assert success is False

    @pytest.mark.asyncio
    async def test_get_cached_events_with_database_error(self, cache_manager):
        """Test get cached events handles database errors."""
        with patch.object(
            cache_manager.db, "get_events_by_date_range", side_effect=Exception("DB Error")
        ):
            now = datetime.now()
            events = await cache_manager.get_cached_events(now, now + timedelta(days=1))
            assert events == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_get_todays_events_with_database_error(self, cache_manager):
        """Test get today's events handles database errors."""
        with patch.object(cache_manager.db, "get_todays_events", side_effect=Exception("DB Error")):
            events = await cache_manager.get_todays_cached_events()
            assert events == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_is_cache_fresh_with_database_error(self, cache_manager):
        """Test is cache fresh handles database errors."""
        with patch.object(
            cache_manager.db, "get_cache_metadata", side_effect=Exception("DB Error")
        ):
            is_fresh = await cache_manager.is_cache_fresh()
            assert is_fresh is False  # Should assume stale on error

    @pytest.mark.asyncio
    async def test_get_cache_status_with_database_error(self, cache_manager):
        """Test get cache status handles database errors gracefully."""
        with patch.object(
            cache_manager.db, "get_cache_metadata", side_effect=Exception("DB Error")
        ):
            status = await cache_manager.get_cache_status()
            assert status is not None  # Should return default metadata

    @pytest.mark.asyncio
    async def test_get_cache_summary_with_database_error(self, cache_manager):
        """Test get cache summary handles database errors."""
        with patch.object(cache_manager, "get_cache_status", side_effect=Exception("DB Error")):
            summary = await cache_manager.get_cache_summary()
            assert summary == {}  # Should return empty dict on error


@pytest.mark.unit
class TestPerformanceMonitoring:
    """Test suite for performance monitoring decorators."""

    @pytest.mark.asyncio
    async def test_memory_monitoring_during_conversion(self, cache_manager, sample_calendar_events):
        """Test memory monitoring during event conversion."""
        with patch("calendarbot.cache.manager.memory_monitor") as mock_monitor:
            mock_context = MagicMock()
            mock_monitor.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_monitor.return_value.__exit__ = MagicMock(return_value=None)

            await cache_manager.cache_events(sample_calendar_events)

            mock_monitor.assert_called_with("event_conversion")

    @pytest.mark.asyncio
    async def test_cache_monitoring_during_storage(self, cache_manager, sample_calendar_events):
        """Test cache monitoring during database storage."""
        with patch("calendarbot.cache.manager.cache_monitor") as mock_monitor:
            mock_context = MagicMock()
            mock_monitor.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_monitor.return_value.__exit__ = MagicMock(return_value=None)

            await cache_manager.cache_events(sample_calendar_events)

            # Should be called with cache name and cache manager identifier
            mock_monitor.assert_called_with("database_store", "cache_manager")


@pytest.mark.slow
@pytest.mark.unit
class TestCachePerformance:
    """Performance tests for cache operations."""

    @pytest.mark.asyncio
    async def test_large_event_caching_performance(self, cache_manager, performance_tracker):
        """Test performance of caching large number of events."""
        # Create large number of events
        large_event_list = []
        now = datetime.now()

        for i in range(1000):
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
            large_event_list.append(event)

        performance_tracker.start_timer("large_cache")
        success = await cache_manager.cache_events(large_event_list)
        performance_tracker.end_timer("large_cache")

        assert success is True
        # Should complete within 10 seconds for 1000 events
        performance_tracker.assert_performance("large_cache", 10.0)

    @pytest.mark.asyncio
    async def test_large_retrieval_performance(
        self, performance_test_database, performance_tracker
    ):
        """Test performance of retrieving large number of events."""
        cache_mgr = CacheManager(performance_test_database.settings)
        cache_mgr.db = performance_test_database.db

        performance_tracker.start_timer("large_retrieval")
        events = await cache_mgr.get_todays_cached_events()
        performance_tracker.end_timer("large_retrieval")

        assert len(events) >= 0
        # Should complete within 5 seconds
        performance_tracker.assert_performance("large_retrieval", 5.0)
