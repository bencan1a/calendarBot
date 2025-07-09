"""Unit tests for Cache Manager functionality."""

from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cache.manager import CacheManager
from calendarbot.cache.models import CachedEvent, CacheMetadata
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus


class TestCacheManagerInitialization:
    """Test CacheManager initialization and setup."""

    def test_init_creates_database_manager(self, test_settings):
        """Test that CacheManager.__init__ creates DatabaseManager correctly."""
        with patch("calendarbot.cache.manager.DatabaseManager") as mock_db:
            cache_manager = CacheManager(test_settings)

            assert cache_manager.settings == test_settings
            mock_db.assert_called_once_with(test_settings.database_file)
            assert cache_manager.db == mock_db.return_value

    @pytest.mark.asyncio
    async def test_initialize_success(self, test_settings):
        """Test successful cache manager initialization."""
        with patch("calendarbot.cache.manager.DatabaseManager") as mock_db:
            mock_db_instance = mock_db.return_value
            mock_db_instance.initialize = AsyncMock(return_value=True)

            cache_manager = CacheManager(test_settings)
            cache_manager.cleanup_old_events = AsyncMock(return_value=5)

            result = await cache_manager.initialize()

            assert result is True
            mock_db_instance.initialize.assert_called_once()
            cache_manager.cleanup_old_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_database_failure(self, test_settings):
        """Test initialization failure when database setup fails."""
        with patch("calendarbot.cache.manager.DatabaseManager") as mock_db:
            mock_db_instance = mock_db.return_value
            mock_db_instance.initialize = AsyncMock(return_value=False)

            cache_manager = CacheManager(test_settings)

            result = await cache_manager.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_exception_handling(self, test_settings):
        """Test exception handling during initialization."""
        with patch("calendarbot.cache.manager.DatabaseManager") as mock_db:
            mock_db_instance = mock_db.return_value
            mock_db_instance.initialize.side_effect = Exception("Database connection failed")

            cache_manager = CacheManager(test_settings)

            result = await cache_manager.initialize()

            assert result is False


class TestCacheManagerEventConversion:
    """Test CacheManager._convert_api_event_to_cached() method."""

    @pytest.fixture
    def cache_manager(self, test_settings):
        """Create CacheManager instance for testing."""
        with patch("calendarbot.cache.manager.DatabaseManager"):
            return CacheManager(test_settings)

    def test_convert_ics_event_to_cached(self, cache_manager, sample_events):
        """Test conversion of ICS CalendarEvent to CachedEvent."""
        api_event = sample_events[0]  # From conftest.py fixture

        cached_event = cache_manager._convert_api_event_to_cached(api_event)

        # Verify basic conversion
        assert cached_event.graph_id == api_event.id
        assert cached_event.subject == api_event.subject
        assert cached_event.body_preview == api_event.body_preview
        assert cached_event.is_all_day == api_event.is_all_day
        assert cached_event.is_cancelled == api_event.is_cancelled
        assert cached_event.is_organizer == api_event.is_organizer

        # Verify datetime conversion
        assert cached_event.start_datetime == api_event.start.date_time.isoformat()
        assert cached_event.end_datetime == api_event.end.date_time.isoformat()
        assert cached_event.start_timezone == api_event.start.time_zone
        assert cached_event.end_timezone == api_event.end.time_zone

        # Verify show_as handling for ICS events (string format)
        assert cached_event.show_as == str(api_event.show_as)

        # Verify cached metadata
        assert cached_event.cached_at is not None
        assert cached_event.id.startswith("cached_")

    def test_convert_graph_api_event_to_cached(self, cache_manager):
        """Test conversion of Microsoft Graph API event to CachedEvent."""
        # Create mock Graph API event with .value attribute
        now = datetime.now()
        mock_show_as = MagicMock()
        mock_show_as.value = "busy"

        mock_location = MagicMock()
        mock_location.address = "123 Test St"

        api_event = MagicMock()
        api_event.id = "graph_event_123"
        api_event.subject = "Graph API Meeting"
        api_event.body_preview = "Graph API event body"
        api_event.start.date_time = now
        api_event.end.date_time = now + timedelta(hours=1)
        api_event.start.time_zone = "UTC"
        api_event.end.time_zone = "UTC"
        api_event.is_all_day = False
        api_event.show_as = mock_show_as
        api_event.is_cancelled = False
        api_event.is_organizer = True
        api_event.location = mock_location
        api_event.is_online_meeting = False
        api_event.online_meeting_url = None
        api_event.is_recurring = False
        api_event.last_modified_date_time = now
        api_event.location_display = "Test Location"
        api_event.web_link = "https://example.com/event"
        api_event.series_master_id = None

        cached_event = cache_manager._convert_api_event_to_cached(api_event)

        # Verify Graph API specific conversions
        assert cached_event.show_as == "busy"  # .value extracted
        assert cached_event.location_display_name == "Test Location"
        assert cached_event.location_address == "123 Test St"
        assert cached_event.web_link == "https://example.com/event"
        assert cached_event.series_master_id is None

    def test_convert_event_with_minimal_data(self, cache_manager):
        """Test conversion of event with minimal required data."""
        now = datetime.now()

        # Create minimal event
        api_event = MagicMock()
        api_event.id = "minimal_event"
        api_event.subject = "Minimal Event"
        api_event.body_preview = "Minimal body"
        api_event.start.date_time = now
        api_event.end.date_time = now + timedelta(hours=1)
        api_event.start.time_zone = "UTC"
        api_event.end.time_zone = "UTC"
        api_event.is_all_day = False
        api_event.show_as = "free"  # String format (ICS style)
        api_event.is_cancelled = False
        api_event.is_organizer = False
        api_event.location = None
        api_event.is_online_meeting = False
        api_event.online_meeting_url = None
        api_event.is_recurring = False
        api_event.last_modified_date_time = None

        cached_event = cache_manager._convert_api_event_to_cached(api_event)

        # Verify minimal data handling
        assert cached_event.graph_id == "minimal_event"
        assert cached_event.subject == "Minimal Event"
        assert cached_event.location_display_name is None
        assert cached_event.location_address is None
        assert cached_event.web_link is None
        assert cached_event.last_modified is None


class TestCacheManagerCacheEvents:
    """Test CacheManager.cache_events() method."""

    @pytest.fixture
    def cache_manager_with_mocks(self, test_settings):
        """Create CacheManager with mocked database."""
        with patch("calendarbot.cache.manager.DatabaseManager") as mock_db:
            cache_manager = CacheManager(test_settings)
            cache_manager.db = AsyncMock()
            cache_manager._update_fetch_metadata = AsyncMock()
            return cache_manager

    @pytest.mark.asyncio
    async def test_cache_events_success(self, cache_manager_with_mocks, sample_events):
        """Test successful event caching."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.store_events.return_value = True

        result = await cache_manager.cache_events(sample_events)

        assert result is True
        cache_manager.db.store_events.assert_called_once()

        # Verify events were converted to cached events
        call_args = cache_manager.db.store_events.call_args[0][0]
        assert len(call_args) == len(sample_events)
        assert all(hasattr(event, "cached_at") for event in call_args)

        # Verify metadata update
        cache_manager._update_fetch_metadata.assert_called_once_with(success=True, error=None)

    @pytest.mark.asyncio
    async def test_cache_events_empty_list(self, cache_manager_with_mocks):
        """Test caching empty event list."""
        cache_manager = cache_manager_with_mocks

        result = await cache_manager.cache_events([])

        assert result is True
        cache_manager.db.store_events.assert_not_called()
        cache_manager._update_fetch_metadata.assert_called_once_with(success=True, error=None)

    @pytest.mark.asyncio
    async def test_cache_events_none_input(self, cache_manager_with_mocks):
        """Test caching None input."""
        cache_manager = cache_manager_with_mocks

        result = await cache_manager.cache_events(None)

        assert result is True
        cache_manager.db.store_events.assert_not_called()
        cache_manager._update_fetch_metadata.assert_called_once_with(success=True, error=None)

    @pytest.mark.asyncio
    async def test_cache_events_database_failure(self, cache_manager_with_mocks, sample_events):
        """Test handling of database storage failure."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.store_events.return_value = False

        result = await cache_manager.cache_events(sample_events)

        assert result is False
        cache_manager._update_fetch_metadata.assert_called_once_with(
            success=False, error="Database storage failed"
        )

    @pytest.mark.asyncio
    async def test_cache_events_exception_handling(self, cache_manager_with_mocks, sample_events):
        """Test exception handling during event caching."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.store_events.side_effect = Exception("Connection timeout")

        result = await cache_manager.cache_events(sample_events)

        assert result is False
        cache_manager._update_fetch_metadata.assert_called_once_with(
            success=False, error="Connection timeout"
        )


class TestCacheManagerRetrieveEvents:
    """Test CacheManager event retrieval methods."""

    @pytest.fixture
    def cache_manager_with_mocks(self, test_settings):
        """Create CacheManager with mocked database."""
        with patch("calendarbot.cache.manager.DatabaseManager"):
            cache_manager = CacheManager(test_settings)
            cache_manager.db = AsyncMock()
            return cache_manager

    @pytest.mark.asyncio
    async def test_get_cached_events_success(self, cache_manager_with_mocks):
        """Test successful retrieval of cached events by date range."""
        cache_manager = cache_manager_with_mocks

        # Mock database response
        mock_events = [
            MagicMock(id="cached_event1", subject="Event 1"),
            MagicMock(id="cached_event2", subject="Event 2"),
        ]
        cache_manager.db.get_events_by_date_range.return_value = mock_events

        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        result = await cache_manager.get_cached_events(start_date, end_date)

        assert result == mock_events
        cache_manager.db.get_events_by_date_range.assert_called_once_with(start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_cached_events_exception(self, cache_manager_with_mocks):
        """Test exception handling during event retrieval."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.get_events_by_date_range.side_effect = Exception("Database error")

        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        result = await cache_manager.get_cached_events(start_date, end_date)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_todays_cached_events_success(self, cache_manager_with_mocks):
        """Test successful retrieval of today's cached events."""
        cache_manager = cache_manager_with_mocks

        mock_events = [MagicMock(id="today_event", subject="Today's Event")]
        cache_manager.db.get_todays_events.return_value = mock_events

        result = await cache_manager.get_todays_cached_events()

        assert result == mock_events
        cache_manager.db.get_todays_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_todays_cached_events_exception(self, cache_manager_with_mocks):
        """Test exception handling during today's events retrieval."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.get_todays_events.side_effect = Exception("Database error")

        result = await cache_manager.get_todays_cached_events()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_alias(self, cache_manager_with_mocks):
        """Test that get_events_by_date_range is an alias for get_cached_events."""
        cache_manager = cache_manager_with_mocks

        mock_events = [MagicMock(id="range_event")]
        cache_manager.db.get_events_by_date_range.return_value = mock_events

        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        result = await cache_manager.get_events_by_date_range(start_date, end_date)

        assert result == mock_events
        cache_manager.db.get_events_by_date_range.assert_called_once_with(start_date, end_date)


class TestCacheManagerFreshness:
    """Test CacheManager cache freshness and status methods."""

    @pytest.fixture
    def cache_manager_with_mocks(self, test_settings):
        """Create CacheManager with mocked database."""
        with patch("calendarbot.cache.manager.DatabaseManager"):
            cache_manager = CacheManager(test_settings)
            cache_manager.db = AsyncMock()
            return cache_manager

    @pytest.mark.asyncio
    async def test_is_cache_fresh_with_fresh_cache(self, cache_manager_with_mocks):
        """Test cache freshness check with fresh cache."""
        cache_manager = cache_manager_with_mocks

        # Mock fresh metadata
        mock_metadata = MagicMock()
        mock_metadata.last_successful_fetch_dt = datetime.now() - timedelta(minutes=30)
        mock_metadata.is_cache_expired.return_value = False
        cache_manager.db.get_cache_metadata.return_value = mock_metadata

        result = await cache_manager.is_cache_fresh()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_cache_fresh_with_stale_cache(self, cache_manager_with_mocks):
        """Test cache freshness check with stale cache."""
        cache_manager = cache_manager_with_mocks

        # Mock stale metadata
        mock_metadata = MagicMock()
        mock_metadata.last_successful_fetch_dt = datetime.now() - timedelta(hours=2)
        mock_metadata.is_cache_expired.return_value = True
        cache_manager.db.get_cache_metadata.return_value = mock_metadata

        result = await cache_manager.is_cache_fresh()

        assert result is False

    @pytest.mark.asyncio
    async def test_is_cache_fresh_no_successful_fetch(self, cache_manager_with_mocks):
        """Test cache freshness check with no successful fetch recorded."""
        cache_manager = cache_manager_with_mocks

        # Mock metadata with no successful fetch
        mock_metadata = MagicMock()
        mock_metadata.last_successful_fetch_dt = None
        cache_manager.db.get_cache_metadata.return_value = mock_metadata

        result = await cache_manager.is_cache_fresh()

        assert result is False

    @pytest.mark.asyncio
    async def test_is_cache_fresh_exception(self, cache_manager_with_mocks):
        """Test cache freshness check with exception."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.get_cache_metadata.side_effect = Exception("Database error")

        result = await cache_manager.is_cache_fresh()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cache_status_success(self, cache_manager_with_mocks, test_settings):
        """Test successful cache status retrieval."""
        cache_manager = cache_manager_with_mocks

        # Mock metadata
        mock_metadata = MagicMock()
        mock_metadata.last_update = datetime.now()
        cache_manager.db.get_cache_metadata.return_value = mock_metadata
        cache_manager.is_cache_fresh = AsyncMock(return_value=True)

        result = await cache_manager.get_cache_status()

        assert result == mock_metadata
        assert result.is_stale is False
        assert result.cache_ttl_seconds == test_settings.cache_ttl

    @pytest.mark.asyncio
    async def test_get_cache_status_exception(self, cache_manager_with_mocks):
        """Test cache status retrieval with exception."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.get_cache_metadata.side_effect = Exception("Database error")

        result = await cache_manager.get_cache_status()

        # Should return default CacheMetadata object
        assert isinstance(result, CacheMetadata)


class TestCacheManagerCleanupAndMaintenance:
    """Test CacheManager cleanup and maintenance methods."""

    @pytest.fixture
    def cache_manager_with_mocks(self, test_settings):
        """Create CacheManager with mocked database."""
        with patch("calendarbot.cache.manager.DatabaseManager"):
            cache_manager = CacheManager(test_settings)
            cache_manager.db = AsyncMock()
            return cache_manager

    @pytest.mark.asyncio
    async def test_cleanup_old_events_success(self, cache_manager_with_mocks):
        """Test successful cleanup of old events."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.cleanup_old_events.return_value = 15

        result = await cache_manager.cleanup_old_events(days_old=7)

        assert result == 15
        cache_manager.db.cleanup_old_events.assert_called_once_with(7)

    @pytest.mark.asyncio
    async def test_cleanup_old_events_custom_days(self, cache_manager_with_mocks):
        """Test cleanup with custom days parameter."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.cleanup_old_events.return_value = 5

        result = await cache_manager.cleanup_old_events(days_old=14)

        assert result == 5
        cache_manager.db.cleanup_old_events.assert_called_once_with(14)

    @pytest.mark.asyncio
    async def test_cleanup_old_events_exception(self, cache_manager_with_mocks):
        """Test cleanup exception handling."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.cleanup_old_events.side_effect = Exception("Database error")

        result = await cache_manager.cleanup_old_events()

        assert result == 0

    @pytest.mark.asyncio
    async def test_clear_cache_success(self, cache_manager_with_mocks):
        """Test successful cache clearing."""
        cache_manager = cache_manager_with_mocks
        cache_manager.cleanup_old_events = AsyncMock(return_value=10)
        cache_manager.db.update_cache_metadata.return_value = None

        result = await cache_manager.clear_cache()

        assert result is True
        cache_manager.cleanup_old_events.assert_called_once_with(days_old=0)
        cache_manager.db.update_cache_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_exception(self, cache_manager_with_mocks):
        """Test cache clearing with exception."""
        cache_manager = cache_manager_with_mocks
        cache_manager.cleanup_old_events = AsyncMock(side_effect=Exception("Database error"))

        result = await cache_manager.clear_cache()

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_method(self, cache_manager_with_mocks):
        """Test the cleanup method for resource cleanup."""
        cache_manager = cache_manager_with_mocks
        cache_manager.cleanup_old_events = AsyncMock(return_value=3)

        result = await cache_manager.cleanup()

        assert result is True
        cache_manager.cleanup_old_events.assert_called_once()


class TestCacheManagerMetadata:
    """Test CacheManager metadata management methods."""

    @pytest.fixture
    def cache_manager_with_mocks(self, test_settings):
        """Create CacheManager with mocked database."""
        with patch("calendarbot.cache.manager.DatabaseManager"):
            cache_manager = CacheManager(test_settings)
            cache_manager.db = AsyncMock()
            return cache_manager

    @pytest.mark.asyncio
    async def test_update_fetch_metadata_success(self, cache_manager_with_mocks):
        """Test updating metadata after successful fetch."""
        cache_manager = cache_manager_with_mocks

        await cache_manager._update_fetch_metadata(success=True)

        cache_manager.db.update_cache_metadata.assert_called_once()
        call_kwargs = cache_manager.db.update_cache_metadata.call_args.kwargs

        assert call_kwargs["consecutive_failures"] == 0
        assert call_kwargs["last_error"] is None
        assert call_kwargs["last_error_time"] is None
        assert call_kwargs["last_update"] is not None
        assert call_kwargs["last_successful_fetch"] is not None

    @pytest.mark.asyncio
    async def test_update_fetch_metadata_failure(self, cache_manager_with_mocks):
        """Test updating metadata after failed fetch."""
        cache_manager = cache_manager_with_mocks

        # Mock existing metadata
        mock_metadata = MagicMock()
        mock_metadata.consecutive_failures = 2
        cache_manager.db.get_cache_metadata.return_value = mock_metadata

        await cache_manager._update_fetch_metadata(success=False, error="Network timeout")

        # Should increment failure count
        cache_manager.db.update_cache_metadata.assert_called_once()
        call_kwargs = cache_manager.db.update_cache_metadata.call_args.kwargs

        assert call_kwargs["consecutive_failures"] == 3
        assert call_kwargs["last_error"] == "Network timeout"
        assert call_kwargs["last_error_time"] is not None

    @pytest.mark.asyncio
    async def test_update_fetch_metadata_exception(self, cache_manager_with_mocks):
        """Test metadata update exception handling."""
        cache_manager = cache_manager_with_mocks
        cache_manager.db.update_cache_metadata.side_effect = Exception("Database error")

        # Should not raise exception
        await cache_manager._update_fetch_metadata(success=True)

        cache_manager.db.update_cache_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_summary_success(self, cache_manager_with_mocks):
        """Test successful cache summary retrieval."""
        cache_manager = cache_manager_with_mocks

        # Mock cache status
        mock_status = MagicMock()
        mock_status.total_events = 10
        mock_status.is_stale = False
        mock_status.last_update = datetime.now()
        mock_status.consecutive_failures = 1
        mock_status.cache_ttl_seconds = 3600
        mock_status.last_update_dt = datetime.now() - timedelta(minutes=30)
        mock_status.time_since_last_update.return_value = 30.5

        cache_manager.get_cache_status = AsyncMock(return_value=mock_status)

        # Mock database info
        mock_db_info = {"file_size_bytes": 1024 * 1024, "journal_mode": "WAL"}  # 1MB
        cache_manager.db.get_database_info.return_value = mock_db_info

        result = await cache_manager.get_cache_summary()

        assert result["total_events"] == 10
        assert result["is_fresh"] is True
        assert result["consecutive_failures"] == 1
        assert result["cache_ttl_hours"] == 1.0
        assert result["database_size_mb"] == 1.0
        assert result["journal_mode"] == "WAL"
        assert result["minutes_since_update"] == 30.5

    @pytest.mark.asyncio
    async def test_get_cache_summary_exception(self, cache_manager_with_mocks):
        """Test cache summary with exception."""
        cache_manager = cache_manager_with_mocks
        cache_manager.get_cache_status = AsyncMock(side_effect=Exception("Database error"))

        result = await cache_manager.get_cache_summary()

        assert result == {}


@pytest.mark.asyncio
async def test_cache_manager_integration_flow(test_settings, sample_events):
    """Integration test of CacheManager workflow."""
    with patch("calendarbot.cache.manager.DatabaseManager") as mock_db:
        mock_db_instance = mock_db.return_value
        mock_db_instance.initialize = AsyncMock(return_value=True)
        mock_db_instance.store_events = AsyncMock(return_value=True)
        mock_db_instance.get_todays_events = AsyncMock(return_value=[])
        mock_metadata = CacheMetadata()
        mock_db_instance.get_cache_metadata = AsyncMock(return_value=mock_metadata)
        mock_db_instance.update_cache_metadata = AsyncMock()

        cache_manager = CacheManager(test_settings)
        cache_manager.cleanup_old_events = AsyncMock(return_value=0)

        # Test complete workflow
        assert await cache_manager.initialize() is True
        assert await cache_manager.cache_events(sample_events) is True

        cached_events = await cache_manager.get_todays_cached_events()
        assert isinstance(cached_events, list)

        is_fresh = await cache_manager.is_cache_fresh()
        assert isinstance(is_fresh, bool)

        status = await cache_manager.get_cache_status()
        assert isinstance(status, CacheMetadata)

        cleanup_count = await cache_manager.cleanup_old_events()
        assert isinstance(cleanup_count, int)
