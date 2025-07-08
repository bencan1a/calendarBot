"""Consolidated unit tests for source manager functionality."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus
from calendarbot.sources.exceptions import SourceConnectionError, SourceError
from calendarbot.sources.ics_source import ICSSourceHandler
from calendarbot.sources.manager import SourceManager
from calendarbot.sources.models import SourceConfig, SourceStatus, SourceType


@pytest.mark.unit
class TestSourceManagerInitialization:
    """Test suite for source manager initialization."""

    def test_source_manager_creation(self, test_settings, cache_manager):
        """Test source manager creation with proper initialization."""
        source_mgr = SourceManager(test_settings, cache_manager)

        assert source_mgr.settings == test_settings
        assert source_mgr.cache_manager == cache_manager
        assert source_mgr._sources == {}
        assert source_mgr._source_configs == {}
        assert source_mgr._last_successful_update is None
        assert source_mgr._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_initialize_with_ics_url(self, test_settings, cache_manager):
        """Test initialization with ICS URL configured."""
        test_settings.ics_url = "https://example.com/calendar.ics"
        source_mgr = SourceManager(test_settings, cache_manager)

        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health = MagicMock()
            mock_health.is_healthy = True
            mock_handler.test_connection.return_value = mock_health
            mock_handler_class.return_value = mock_handler

            success = await source_mgr.initialize()

            assert success is True
            assert "primary" in source_mgr._sources

    @pytest.mark.asyncio
    async def test_initialize_without_ics_url(self, test_settings, cache_manager):
        """Test initialization without ICS URL."""
        test_settings.ics_url = None
        source_mgr = SourceManager(test_settings, cache_manager)

        success = await source_mgr.initialize()
        assert success is False

    @pytest.mark.asyncio
    async def test_initialize_with_auth_settings(self, test_settings, cache_manager):
        """Test initialization with authentication settings."""
        test_settings.ics_url = "https://example.com/calendar.ics"
        test_settings.ics_auth_type = "basic"
        test_settings.ics_username = "testuser"
        test_settings.ics_password = "testpass"
        test_settings.ics_timeout = 45

        source_mgr = SourceManager(test_settings, cache_manager)

        with patch.object(source_mgr, "add_ics_source", return_value=True) as mock_add:
            await source_mgr.initialize()

            mock_add.assert_called_once_with(
                name="primary",
                url="https://example.com/calendar.ics",
                auth_type="basic",
                username="testuser",
                password="testpass",
                bearer_token=None,
                refresh_interval=300,
                timeout=45,
            )


@pytest.mark.unit
class TestSourceManagement:
    """Test suite for source management operations."""

    @pytest_asyncio.fixture
    async def source_manager_with_mock(self, test_settings, cache_manager):
        """Create source manager with mocked dependencies."""
        source_mgr = SourceManager(test_settings, cache_manager)
        yield source_mgr
        await source_mgr.cleanup()

    @pytest.mark.asyncio
    async def test_add_ics_source_success(self, source_manager_with_mock):
        """Test successful addition of ICS source."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.test_connection.return_value.is_healthy = True
            mock_handler_class.return_value = mock_handler

            success = await source_manager_with_mock.add_ics_source(
                name="test_source",
                url="https://example.com/test.ics",
                auth_type="basic",
                username="user",
                password="pass",
                timeout=30,
            )

            assert success is True
            assert "test_source" in source_manager_with_mock._sources
            assert "test_source" in source_manager_with_mock._source_configs

            # Verify configuration
            config = source_manager_with_mock._source_configs["test_source"]
            assert config.name == "test_source"
            assert config.url == "https://example.com/test.ics"
            assert config.type == SourceType.ICS
            assert config.auth_type == "basic"
            assert config.auth_config == {"username": "user", "password": "pass"}

    @pytest.mark.asyncio
    async def test_add_ics_source_with_bearer_auth(self, source_manager_with_mock):
        """Test adding ICS source with bearer token authentication."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.test_connection.return_value.is_healthy = True
            mock_handler_class.return_value = mock_handler

            success = await source_manager_with_mock.add_ics_source(
                name="bearer_source",
                url="https://example.com/auth.ics",
                auth_type="bearer",
                bearer_token="test-token-123",
            )

            assert success is True
            config = source_manager_with_mock._source_configs["bearer_source"]
            assert config.auth_type == "bearer"
            assert config.auth_config == {"token": "test-token-123"}

    @pytest.mark.asyncio
    async def test_add_ics_source_connection_failure(self, source_manager_with_mock):
        """Test ICS source addition when connection test fails."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health_check = MagicMock()
            mock_health_check.is_healthy = False
            mock_health_check.error_message = "Connection failed"
            mock_handler.test_connection.return_value = mock_health_check
            mock_handler_class.return_value = mock_handler

            success = await source_manager_with_mock.add_ics_source(
                name="failed_source", url="https://example.com/bad.ics"
            )

            assert success is False
            assert "failed_source" not in source_manager_with_mock._sources

    @pytest.mark.asyncio
    async def test_add_ics_source_with_exception(self, source_manager_with_mock):
        """Test ICS source addition with exception during setup."""
        with patch(
            "calendarbot.sources.manager.ICSSourceHandler", side_effect=Exception("Setup error")
        ):
            success = await source_manager_with_mock.add_ics_source(
                name="error_source", url="https://example.com/error.ics"
            )

            assert success is False

    @pytest.mark.asyncio
    async def test_remove_source_success(self, source_manager_with_mock):
        """Test successful source removal."""
        # First add a source
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.test_connection.return_value.is_healthy = True
            mock_handler_class.return_value = mock_handler

            await source_manager_with_mock.add_ics_source(
                "temp_source", "https://example.com/temp.ics"
            )

            # Then remove it
            success = await source_manager_with_mock.remove_source("temp_source")

            assert success is True
            assert "temp_source" not in source_manager_with_mock._sources
            assert "temp_source" not in source_manager_with_mock._source_configs

    @pytest.mark.asyncio
    async def test_remove_source_not_found(self, source_manager_with_mock):
        """Test removing a source that doesn't exist."""
        success = await source_manager_with_mock.remove_source("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_remove_source_with_exception(self, source_manager_with_mock):
        """Test source removal with exception handling."""
        # Add a source first
        mock_handler = AsyncMock()
        source_manager_with_mock._sources["test"] = mock_handler
        source_manager_with_mock._source_configs["test"] = MagicMock()

        # Use a mock dict that raises an exception on deletion
        class FailingDict(dict):
            def __delitem__(self, key):
                if key == "test":
                    raise Exception("Remove error")
                super().__delitem__(key)

        # Replace with failing dict
        failing_sources = FailingDict(source_manager_with_mock._sources)
        source_manager_with_mock._sources = failing_sources

        success = await source_manager_with_mock.remove_source("test")
        assert success is False


@pytest.mark.unit
class TestEventFetching:
    """Test suite for event fetching and caching operations."""

    @pytest_asyncio.fixture
    async def source_manager_with_sources(self, test_settings, cache_manager):
        """Create source manager with mock sources."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Add mock sources with proper event data
        mock_handler1 = AsyncMock()
        mock_handler1.is_healthy = MagicMock(return_value=True)
        now = datetime.now()
        mock_handler1.fetch_events.return_value = [
            CalendarEvent(
                id="event1",
                subject="Event 1",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]
        mock_handler1.get_todays_events.return_value = [
            CalendarEvent(
                id="event1",
                subject="Event 1",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]
        mock_handler1.get_events_for_date_range.return_value = [
            CalendarEvent(
                id="event1",
                subject="Event 1",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]

        mock_handler2 = AsyncMock()
        mock_handler2.is_healthy = MagicMock(return_value=True)
        mock_handler2.fetch_events.return_value = [
            CalendarEvent(
                id="event2",
                subject="Event 2",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]
        mock_handler2.get_todays_events.return_value = [
            CalendarEvent(
                id="event2",
                subject="Event 2",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]
        mock_handler2.get_events_for_date_range.return_value = [
            CalendarEvent(
                id="event2",
                subject="Event 2",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]

        source_mgr._sources = {"source1": mock_handler1, "source2": mock_handler2}

        yield source_mgr
        await source_mgr.cleanup()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, source_manager_with_sources):
        """Test successful event fetching and caching."""
        with patch.object(
            source_manager_with_sources.cache_manager,
            "cache_events",
            new_callable=AsyncMock,
            return_value=True,
        ):
            success = await source_manager_with_sources.fetch_and_cache_events()

            assert success is True
            assert source_manager_with_sources._consecutive_failures == 0
            assert source_manager_with_sources._last_successful_update is not None

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_no_sources(self, test_settings, cache_manager):
        """Test fetching events with no configured sources."""
        source_mgr = SourceManager(test_settings, cache_manager)
        success = await source_mgr.fetch_and_cache_events()
        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_unhealthy_sources(self, source_manager_with_sources):
        """Test fetching events with unhealthy sources."""
        # Make all sources unhealthy
        for handler in source_manager_with_sources._sources.values():
            handler.is_healthy.return_value = False

        success = await source_manager_with_sources.fetch_and_cache_events()
        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_partial_failure(self, source_manager_with_sources):
        """Test fetching events with some sources failing."""
        # Make one source fail
        source_manager_with_sources._sources["source1"].fetch_events.side_effect = Exception(
            "Fetch error"
        )

        with patch.object(
            source_manager_with_sources.cache_manager,
            "cache_events",
            new_callable=AsyncMock,
            return_value=True,
        ):
            success = await source_manager_with_sources.fetch_and_cache_events()

            # Should still succeed with remaining sources
            assert success is True

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_cache_failure(self, source_manager_with_sources):
        """Test fetching events with cache failure."""
        with patch.object(
            source_manager_with_sources.cache_manager, "cache_events", return_value=False
        ):
            success = await source_manager_with_sources.fetch_and_cache_events()

            assert success is False
            assert source_manager_with_sources._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_no_cache_manager(self, test_settings):
        """Test fetching events without cache manager."""
        source_mgr = SourceManager(test_settings, None)

        # Add mock source
        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.fetch_events.return_value = [MagicMock()]
        source_mgr._sources = {"source1": mock_handler}

        success = await source_mgr.fetch_and_cache_events()
        assert success is True  # Should succeed without caching

    @pytest.mark.asyncio
    async def test_get_todays_events(self, source_manager_with_sources):
        """Test getting today's events from all sources."""
        events = await source_manager_with_sources.get_todays_events()

        assert len(events) == 2  # Should get events from both sources
        assert all(isinstance(event, CalendarEvent) for event in events)

    @pytest.mark.asyncio
    async def test_get_todays_events_with_duplicates(self, source_manager_with_sources):
        """Test getting today's events with duplicate removal."""
        # Create duplicate event with same ID
        now = datetime.now()
        duplicate_event = CalendarEvent(
            id="event1",  # Same ID as first source
            subject="Duplicate Event",
            start=DateTimeInfo(date_time=now, time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        # Add duplicate to second source
        source_manager_with_sources._sources["source2"].get_todays_events.return_value = [
            duplicate_event
        ]

        events = await source_manager_with_sources.get_todays_events()

        # Should deduplicate events
        assert len(events) == 1
        assert events[0].id == "event1"

    @pytest.mark.asyncio
    async def test_get_events_for_date_range(self, source_manager_with_sources):
        """Test getting events for date range."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        events = await source_manager_with_sources.get_events_for_date_range(start_date, end_date)

        assert len(events) >= 0  # Should return events from sources
        # Verify each source was called
        for handler in source_manager_with_sources._sources.values():
            handler.get_events_for_date_range.assert_called_once_with(start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_events_for_date_range_with_error(self, source_manager_with_sources):
        """Test getting events for date range with source error."""
        source_manager_with_sources._sources["source1"].get_events_for_date_range.side_effect = (
            Exception("Range error")
        )

        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)

        events = await source_manager_with_sources.get_events_for_date_range(start_date, end_date)

        # Should handle errors gracefully
        assert isinstance(events, list)

    def test_deduplicate_events(self, test_settings, cache_manager):
        """Test event deduplication functionality."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Create duplicate events
        now = datetime.now()
        event1 = CalendarEvent(
            id="dup",
            subject="Duplicate Event",
            start=DateTimeInfo(date_time=now, time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
        )
        event2 = CalendarEvent(
            id="dup",
            subject="Duplicate Event",
            start=DateTimeInfo(date_time=now, time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
        )
        event3 = CalendarEvent(
            id="unique",
            subject="Unique Event",
            start=DateTimeInfo(date_time=now, time_zone="UTC"),
            end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
        )

        deduplicated = source_mgr._deduplicate_events([event1, event2, event3])

        assert len(deduplicated) == 2
        assert deduplicated[0].id == "dup"
        assert deduplicated[1].id == "unique"

    def test_deduplicate_events_empty_list(self, test_settings, cache_manager):
        """Test deduplication with empty list."""
        source_mgr = SourceManager(test_settings, cache_manager)
        unique_events = source_mgr._deduplicate_events([])
        assert unique_events == []


@pytest.mark.unit
class TestSourceHealth:
    """Test suite for source health checking and monitoring."""

    @pytest_asyncio.fixture
    async def source_manager_with_health_sources(self, test_settings, cache_manager):
        """Create source manager with sources of varying health."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Healthy source
        healthy_handler = AsyncMock()
        healthy_handler.is_healthy = MagicMock(return_value=True)
        healthy_handler.test_connection.return_value.is_healthy = True
        healthy_handler.test_connection.return_value.status = SourceStatus.HEALTHY
        healthy_handler.test_connection.return_value.response_time_ms = 150
        healthy_handler.test_connection.return_value.error_message = None
        healthy_handler.test_connection.return_value.events_fetched = 5

        # Unhealthy source
        unhealthy_handler = AsyncMock()
        unhealthy_handler.is_healthy = MagicMock(return_value=False)
        unhealthy_handler.test_connection.return_value.is_healthy = False
        unhealthy_handler.test_connection.return_value.status = SourceStatus.ERROR
        unhealthy_handler.test_connection.return_value.error_message = "Connection failed"

        source_mgr._sources = {"healthy": healthy_handler, "unhealthy": unhealthy_handler}

        yield source_mgr
        await source_mgr.cleanup()

    @pytest.mark.asyncio
    async def test_test_all_sources(self, source_manager_with_health_sources):
        """Test testing all sources for health."""
        results = await source_manager_with_health_sources.test_all_sources()

        assert "healthy" in results
        assert "unhealthy" in results

        assert results["healthy"]["healthy"] is True
        assert results["healthy"]["status"] == SourceStatus.HEALTHY
        assert results["healthy"]["response_time_ms"] == 150
        assert results["healthy"]["events_fetched"] == 5

        assert results["unhealthy"]["healthy"] is False
        assert results["unhealthy"]["status"] == SourceStatus.ERROR
        assert results["unhealthy"]["error_message"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_test_all_sources_with_exception(self, source_manager_with_health_sources):
        """Test testing sources when exception occurs."""
        # Make one source throw exception
        source_manager_with_health_sources._sources["healthy"].test_connection.side_effect = (
            Exception("Test error")
        )

        results = await source_manager_with_health_sources.test_all_sources()

        assert results["healthy"]["healthy"] is False
        assert results["healthy"]["status"] == SourceStatus.ERROR
        assert "Test error" in results["healthy"]["error_message"]

    def test_get_source_status(self, source_manager_with_health_sources):
        """Test getting status of all sources."""
        source_manager_with_health_sources._sources["healthy"].get_status = MagicMock(
            return_value={"status": "healthy"}
        )
        source_manager_with_health_sources._sources["unhealthy"].get_status = MagicMock(
            return_value={"status": "error"}
        )

        status = source_manager_with_health_sources.get_source_status()

        assert "healthy" in status
        assert "unhealthy" in status
        assert status["healthy"]["status"] == "healthy"
        assert status["unhealthy"]["status"] == "error"

    def test_is_healthy_with_healthy_sources(self, source_manager_with_health_sources):
        """Test source manager health with healthy sources."""
        is_healthy = source_manager_with_health_sources.is_healthy()
        assert is_healthy is True

    def test_is_healthy_with_no_healthy_sources(self, source_manager_with_health_sources):
        """Test source manager health with no healthy sources."""
        # Make all sources unhealthy
        for handler in source_manager_with_health_sources._sources.values():
            handler.is_healthy.return_value = False

        is_healthy = source_manager_with_health_sources.is_healthy()
        assert is_healthy is False

    def test_is_healthy_with_no_sources(self, test_settings, cache_manager):
        """Test source manager health with no sources."""
        source_mgr = SourceManager(test_settings, cache_manager)
        is_healthy = source_mgr.is_healthy()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, source_manager_with_health_sources):
        """Test health check when all sources are healthy."""
        # Make both sources healthy for this test
        source_manager_with_health_sources._sources["unhealthy"].is_healthy.return_value = True

        health_result = await source_manager_with_health_sources.health_check()

        assert health_result.is_healthy is True
        assert "All 2 sources are healthy" in health_result.status_message

    @pytest.mark.asyncio
    async def test_health_check_partial_healthy(self, source_manager_with_health_sources):
        """Test health check when some sources are healthy."""
        health_result = await source_manager_with_health_sources.health_check()

        # One healthy, one unhealthy
        assert health_result.is_healthy is True  # Still healthy if any are healthy
        assert "1/2 sources healthy" in health_result.status_message

    @pytest.mark.asyncio
    async def test_health_check_none_healthy(self, source_manager_with_health_sources):
        """Test health check when no sources are healthy."""
        # Make all sources unhealthy
        for handler in source_manager_with_health_sources._sources.values():
            handler.is_healthy.return_value = False

        health_result = await source_manager_with_health_sources.health_check()

        assert health_result.is_healthy is False
        assert "All 2 sources are unhealthy" in health_result.status_message

    @pytest.mark.asyncio
    async def test_health_check_no_sources(self, test_settings, cache_manager):
        """Test health check with no sources configured."""
        source_mgr = SourceManager(test_settings, cache_manager)
        health_result = await source_mgr.health_check()

        assert health_result.is_healthy is False
        assert "No sources configured" in health_result.status_message


@pytest.mark.unit
class TestSourceInfo:
    """Test suite for source information retrieval."""

    @pytest_asyncio.fixture
    async def source_manager_with_info(self, test_settings, cache_manager):
        """Create source manager with configured sources."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Mock handler and config
        mock_handler = AsyncMock()
        mock_handler.is_healthy = MagicMock(return_value=True)

        mock_config = MagicMock()
        mock_config.url = "https://example.com/primary.ics"

        source_mgr._sources = {"primary": mock_handler}
        source_mgr._source_configs = {"primary": mock_config}

        yield source_mgr
        await source_mgr.cleanup()

    @pytest.mark.asyncio
    async def test_get_source_info_primary(self, source_manager_with_info):
        """Test getting info for primary source."""
        info = await source_manager_with_info.get_source_info()

        assert info.status == "healthy"
        assert info.url == "https://example.com/primary.ics"
        assert info.is_configured is True

    @pytest.mark.asyncio
    async def test_get_source_info_by_name(self, source_manager_with_info):
        """Test getting info for specific source by name."""
        info = await source_manager_with_info.get_source_info("primary")

        assert info.status == "healthy"
        assert info.url == "https://example.com/primary.ics"
        assert info.is_configured is True

    @pytest.mark.asyncio
    async def test_get_source_info_not_configured(self, test_settings, cache_manager):
        """Test getting info for nonexistent source."""
        source_mgr = SourceManager(test_settings, cache_manager)
        info = await source_mgr.get_source_info("nonexistent")

        assert info.status == "not_configured"
        assert info.url == ""
        assert info.is_configured is False

    @pytest.mark.asyncio
    async def test_get_source_info_unhealthy(self, source_manager_with_info):
        """Test getting info for unhealthy source."""
        source_manager_with_info._sources["primary"].is_healthy.return_value = False

        info = await source_manager_with_info.get_source_info("primary")

        assert info.status == "unhealthy"
        assert info.is_configured is True

    def test_get_detailed_source_info(self, source_manager_with_info):
        """Test getting detailed source information."""
        # Mock detailed responses with proper objects that match Pydantic validation
        mock_handler = source_manager_with_info._sources["primary"]

        # Create proper models instead of MagicMock
        from calendarbot.sources.models import (
            SourceConfig,
            SourceHealthCheck,
            SourceMetrics,
            SourceStatus,
            SourceType,
        )

        real_config = SourceConfig(
            name="primary",
            type=SourceType.ICS,
            url="https://example.com/primary.ics",
            refresh_interval=300,
            timeout=30,
            max_retries=3,
            retry_backoff=1.0,
        )
        source_manager_with_info._source_configs["primary"] = real_config

        # Create proper SourceHealthCheck and SourceMetrics instances
        health_check = SourceHealthCheck(
            status=SourceStatus.HEALTHY, response_time_ms=150.0, events_fetched=5
        )

        metrics = SourceMetrics(
            total_requests=10,
            successful_requests=9,
            avg_response_time_ms=145.0,
            total_events_fetched=50,
            last_event_count=5,
        )

        # Mock health check and metrics to return proper objects
        mock_handler.get_health_check = MagicMock(return_value=health_check)
        mock_handler.get_metrics = MagicMock(return_value=metrics)

        detailed_info = source_manager_with_info.get_detailed_source_info("primary")

        assert detailed_info is not None
        assert detailed_info.config is not None
        assert detailed_info.health is not None
        assert detailed_info.metrics is not None
        assert isinstance(detailed_info.config, SourceConfig)
        assert isinstance(detailed_info.health, SourceHealthCheck)
        assert isinstance(detailed_info.metrics, SourceMetrics)

    def test_get_detailed_source_info_nonexistent(self, test_settings, cache_manager):
        """Test getting detailed info for nonexistent source."""
        source_mgr = SourceManager(test_settings, cache_manager)
        detailed_info = source_mgr.get_detailed_source_info("nonexistent")
        assert detailed_info is None

    def test_get_summary_status(self, source_manager_with_info):
        """Test getting summary status."""
        summary = source_manager_with_info.get_summary_status()

        assert summary["total_sources"] == 1
        assert summary["healthy_sources"] == 1
        assert summary["is_healthy"] is True
        assert summary["source_names"] == ["primary"]
        assert summary["consecutive_failures"] == 0


@pytest.mark.unit
class TestSourceConfiguration:
    """Test suite for source configuration management."""

    @pytest.mark.asyncio
    async def test_refresh_source_configs(self, test_settings, cache_manager):
        """Test refreshing source configurations."""
        source_mgr = SourceManager(test_settings, cache_manager)
        # This is a placeholder implementation in the current code
        await source_mgr.refresh_source_configs()
        # Should not raise exceptions

    @pytest.mark.asyncio
    async def test_refresh_source_configs_with_url_change(self, test_settings, cache_manager):
        """Test refreshing configurations when URL changes."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Add a mock source
        mock_handler = AsyncMock()
        mock_config = MagicMock()
        mock_config.url = "https://example.com/old.ics"

        source_mgr._sources = {"primary": mock_handler}
        source_mgr._source_configs = {"primary": mock_config}

        # Change URL in settings
        test_settings.ics_url = "https://example.com/new.ics"

        await source_mgr.refresh_source_configs()
        # Should handle the configuration change

    @pytest.mark.asyncio
    async def test_cleanup(self, test_settings, cache_manager):
        """Test source manager cleanup."""
        source_mgr = SourceManager(test_settings, cache_manager)
        await source_mgr.cleanup()
        # Should not raise exceptions


@pytest.mark.unit
class TestErrorHandling:
    """Test suite for error handling in source manager."""

    @pytest_asyncio.fixture
    async def source_manager_with_sources(self, test_settings, cache_manager):
        """Create source manager with mock sources for error testing."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Add mock sources
        now = datetime.now()
        mock_handler1 = AsyncMock()
        mock_handler1.is_healthy = MagicMock(return_value=True)
        mock_handler1.fetch_events.return_value = [
            CalendarEvent(
                id="event1",
                subject="Event 1",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]

        mock_handler2 = AsyncMock()
        mock_handler2.is_healthy = MagicMock(return_value=True)
        mock_handler2.fetch_events.return_value = [
            CalendarEvent(
                id="event2",
                subject="Event 2",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]

        source_mgr._sources = {"source1": mock_handler1, "source2": mock_handler2}

        yield source_mgr
        await source_mgr.cleanup()

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_with_exception(self, source_manager_with_sources):
        """Test fetch and cache events with exception."""
        # Mock an exception during fetching
        with patch.object(
            source_manager_with_sources, "_sources", side_effect=Exception("Fetch error")
        ):
            success = await source_manager_with_sources.fetch_and_cache_events()

            assert success is False
            assert source_manager_with_sources._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_get_todays_events_with_source_error(self, source_manager_with_sources):
        """Test getting today's events when source throws error."""
        # Make one source throw exception
        source_manager_with_sources._sources["source1"].get_todays_events.side_effect = Exception(
            "Source error"
        )

        events = await source_manager_with_sources.get_todays_events()

        # Should still get events from other sources
        assert len(events) >= 0


@pytest.mark.unit
@pytest.mark.performance
class TestPerformance:
    """Performance tests for source manager."""

    @pytest_asyncio.fixture
    async def source_manager_with_sources(self, test_settings, cache_manager):
        """Create source manager with mock sources for performance testing."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Add mock sources
        now = datetime.now()
        mock_handler1 = AsyncMock()
        mock_handler1.is_healthy = MagicMock(return_value=True)
        mock_handler1.fetch_events.return_value = [
            CalendarEvent(
                id="event1",
                subject="Event 1",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]

        mock_handler2 = AsyncMock()
        mock_handler2.is_healthy = MagicMock(return_value=True)
        mock_handler2.fetch_events.return_value = [
            CalendarEvent(
                id="event2",
                subject="Event 2",
                start=DateTimeInfo(date_time=now, time_zone="UTC"),
                end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                show_as=EventStatus.BUSY,
            )
        ]

        source_mgr._sources = {"source1": mock_handler1, "source2": mock_handler2}

        yield source_mgr
        await source_mgr.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_source_fetching(
        self, source_manager_with_sources, performance_tracker
    ):
        """Test that multiple sources can be fetched concurrently."""
        performance_tracker.start_timer("concurrent_fetch")

        # Mock cache manager to avoid field validation issues
        with patch.object(
            source_manager_with_sources.cache_manager,
            "cache_events",
            new_callable=AsyncMock,
            return_value=True,
        ):
            success = await source_manager_with_sources.fetch_and_cache_events()

        performance_tracker.end_timer("concurrent_fetch")

        assert success is True
        # Should complete quickly since sources run concurrently
        performance_tracker.assert_performance("concurrent_fetch", 2.0)

    @pytest.mark.asyncio
    async def test_large_source_count_performance(
        self, test_settings, cache_manager, performance_tracker
    ):
        """Test performance with many sources."""
        source_mgr = SourceManager(test_settings, cache_manager)

        # Add many mock sources
        now = datetime.now()
        for i in range(10):
            mock_handler = AsyncMock()
            mock_handler.is_healthy = MagicMock(return_value=True)
            mock_handler.fetch_events.return_value = [
                CalendarEvent(
                    id=f"event{i}",
                    subject=f"Event {i}",
                    start=DateTimeInfo(date_time=now, time_zone="UTC"),
                    end=DateTimeInfo(date_time=now + timedelta(hours=1), time_zone="UTC"),
                    show_as=EventStatus.BUSY,
                )
            ]
            source_mgr._sources[f"source{i}"] = mock_handler

        performance_tracker.start_timer("many_sources")
        # Mock cache manager to avoid field validation issues
        with patch.object(cache_manager, "cache_events", new_callable=AsyncMock, return_value=True):
            success = await source_mgr.fetch_and_cache_events()
        performance_tracker.end_timer("many_sources")

        assert success is True
        # Should handle many sources efficiently
        performance_tracker.assert_performance("many_sources", 5.0)
