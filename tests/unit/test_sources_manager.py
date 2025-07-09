"""Comprehensive test suite for Sources Manager.

This module tests the Sources Manager which coordinates calendar data
fetching and caching across multiple sources.

Test Coverage:
- Source manager initialization and configuration
- ICS source addition with various authentication types  
- Source removal and lifecycle management
- Event fetching and caching operations
- Today's events and date range filtering
- Health checks and status monitoring
- Error handling and recovery scenarios
- Source information and metrics tracking
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from calendarbot.cache.manager import CacheManager
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, Location
from calendarbot.sources.exceptions import SourceConnectionError, SourceError
from calendarbot.sources.ics_source import ICSSourceHandler
from calendarbot.sources.manager import SourceManager
from calendarbot.sources.models import (
    SourceConfig,
    SourceHealthCheck,
    SourceInfo,
    SourceMetrics,
    SourceStatus,
    SourceType,
)


class TestSourceManagerInitialization:
    """Test source manager initialization and basic setup."""

    def test_source_manager_init_basic(self) -> None:
        """Test basic source manager initialization."""
        # Create mock settings
        settings = Mock()
        settings.max_retries = 3
        settings.retry_backoff_factor = 1.5

        # Initialize source manager
        manager = SourceManager(settings)

        # Verify initialization
        assert manager.settings is settings
        assert manager.cache_manager is None
        assert len(manager._sources) == 0
        assert len(manager._source_configs) == 0
        assert manager._last_successful_update is None
        assert manager._consecutive_failures == 0

    def test_source_manager_init_with_cache_manager(self) -> None:
        """Test source manager initialization with cache manager."""
        # Create mock objects
        settings = Mock()
        cache_manager = Mock(spec=CacheManager)

        # Initialize source manager
        manager = SourceManager(settings, cache_manager)

        # Verify initialization
        assert manager.settings is settings
        assert manager.cache_manager is cache_manager
        assert len(manager._sources) == 0
        assert len(manager._source_configs) == 0

    @pytest.mark.asyncio
    async def test_initialize_success_with_ics_url(self) -> None:
        """Test successful initialization with ICS URL in settings."""
        # Create mock settings with ICS configuration
        settings = Mock()
        settings.ics_url = "https://example.com/calendar.ics"
        settings.ics_auth_type = "none"
        settings.ics_username = None
        settings.ics_password = None
        settings.ics_bearer_token = None
        settings.ics_refresh_interval = 300
        settings.ics_timeout = 10
        settings.max_retries = 3
        settings.retry_backoff_factor = 1.5

        manager = SourceManager(settings)

        # Mock the add_ics_source method
        with patch.object(manager, "add_ics_source", return_value=True) as mock_add:
            result = await manager.initialize()

            # Verify success
            assert result is True
            mock_add.assert_called_once_with(
                name="primary",
                url="https://example.com/calendar.ics",
                auth_type="none",
                username=None,
                password=None,
                bearer_token=None,
                refresh_interval=300,
                timeout=10,
            )

    @pytest.mark.asyncio
    async def test_initialize_failure_no_ics_url(self) -> None:
        """Test initialization failure when no ICS URL configured."""
        # Create mock settings without ICS URL
        settings = Mock()
        settings.ics_url = None

        manager = SourceManager(settings)

        # Test initialization
        result = await manager.initialize()

        # Verify failure
        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_exception_handling(self) -> None:
        """Test initialization exception handling."""
        # Create mock settings that will cause exception
        settings = Mock()
        settings.ics_url = "https://example.com/calendar.ics"

        manager = SourceManager(settings)

        # Mock add_ics_source to raise exception
        with patch.object(manager, "add_ics_source", side_effect=Exception("Test error")):
            result = await manager.initialize()

            # Verify failure handling
            assert result is False


class TestSourceManagerAddICSSource:
    """Test ICS source addition with various configurations."""

    @pytest.fixture
    def source_manager(self) -> Any:
        """Create source manager for testing."""
        settings = Mock()
        settings.max_retries = 3
        settings.retry_backoff_factor = 1.5
        return SourceManager(settings)

    @pytest.mark.asyncio
    async def test_add_ics_source_basic_success(self, source_manager: Any) -> None:
        """Test successful addition of basic ICS source."""
        # Mock ICS source handler
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_health_check = Mock()
        mock_health_check.is_healthy = True
        mock_handler.test_connection.return_value = mock_health_check

        with patch("calendarbot.sources.manager.ICSSourceHandler", return_value=mock_handler):
            result = await source_manager.add_ics_source(
                name="test_source", url="https://example.com/calendar.ics"
            )

            # Verify success
            assert result is True
            assert "test_source" in source_manager._sources
            assert "test_source" in source_manager._source_configs
            assert source_manager._sources["test_source"] is mock_handler

    @pytest.mark.asyncio
    async def test_add_ics_source_basic_auth(self, source_manager: Any) -> None:
        """Test adding ICS source with basic authentication."""
        # Mock ICS source handler
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_health_check = Mock()
        mock_health_check.is_healthy = True
        mock_handler.test_connection.return_value = mock_health_check

        with patch("calendarbot.sources.manager.ICSSourceHandler", return_value=mock_handler):
            result = await source_manager.add_ics_source(
                name="auth_source",
                url="https://example.com/calendar.ics",
                auth_type="basic",
                username="testuser",
                password="testpass",
            )

            # Verify success and auth config
            assert result is True
            config = source_manager._source_configs["auth_source"]
            assert config.auth_type == "basic"
            assert config.auth_config == {"username": "testuser", "password": "testpass"}

    @pytest.mark.asyncio
    async def test_add_ics_source_bearer_auth(self, source_manager: Any) -> None:
        """Test adding ICS source with bearer token authentication."""
        # Mock ICS source handler
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_health_check = Mock()
        mock_health_check.is_healthy = True
        mock_handler.test_connection.return_value = mock_health_check

        with patch("calendarbot.sources.manager.ICSSourceHandler", return_value=mock_handler):
            result = await source_manager.add_ics_source(
                name="bearer_source",
                url="https://example.com/calendar.ics",
                auth_type="bearer",
                bearer_token="abc123token",
            )

            # Verify success and auth config
            assert result is True
            config = source_manager._source_configs["bearer_source"]
            assert config.auth_type == "bearer"
            assert config.auth_config == {"token": "abc123token"}

    @pytest.mark.asyncio
    async def test_add_ics_source_connection_test_failure(self, source_manager: Any) -> None:
        """Test ICS source addition failure due to connection test."""
        # Mock ICS source handler with failed health check
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_health_check = Mock()
        mock_health_check.is_healthy = False
        mock_health_check.error_message = "Connection failed"
        mock_handler.test_connection.return_value = mock_health_check

        with patch("calendarbot.sources.manager.ICSSourceHandler", return_value=mock_handler):
            result = await source_manager.add_ics_source(
                name="failed_source", url="https://invalid.example.com/calendar.ics"
            )

            # Verify failure
            assert result is False
            assert "failed_source" not in source_manager._sources

    @pytest.mark.asyncio
    async def test_add_ics_source_exception_handling(self, source_manager: Any) -> None:
        """Test ICS source addition exception handling."""
        # Mock ICS source handler creation to raise exception
        with patch(
            "calendarbot.sources.manager.ICSSourceHandler",
            side_effect=Exception("Handler creation failed"),
        ):
            result = await source_manager.add_ics_source(
                name="exception_source", url="https://example.com/calendar.ics"
            )

            # Verify failure handling
            assert result is False
            assert "exception_source" not in source_manager._sources

    @pytest.mark.asyncio
    async def test_add_ics_source_custom_options(self, source_manager: Any) -> None:
        """Test adding ICS source with custom options."""
        # Mock ICS source handler
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_health_check = Mock()
        mock_health_check.is_healthy = True
        mock_handler.test_connection.return_value = mock_health_check

        with patch("calendarbot.sources.manager.ICSSourceHandler", return_value=mock_handler):
            result = await source_manager.add_ics_source(
                name="custom_source",
                url="https://example.com/calendar.ics",
                refresh_interval=600,
                timeout=60,
                custom_setting="value",
            )

            # Verify success and custom configuration
            assert result is True
            config = source_manager._source_configs["custom_source"]
            assert config.refresh_interval == 600
            assert config.timeout == 60


class TestSourceManagerSourceLifecycle:
    """Test source removal and lifecycle management."""

    @pytest.fixture
    def source_manager_with_source(self) -> Any:
        """Create source manager with a test source."""
        settings = Mock()
        settings.max_retries = 3
        settings.retry_backoff_factor = 1.5
        manager = SourceManager(settings)

        # Add a mock source
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_config = Mock(spec=SourceConfig)
        mock_config.name = "test_source"

        manager._sources["test_source"] = mock_handler
        manager._source_configs["test_source"] = mock_config

        return manager

    @pytest.mark.asyncio
    async def test_remove_source_success(self, source_manager_with_source: Any) -> None:
        """Test successful source removal."""
        manager = source_manager_with_source

        # Verify source exists
        assert "test_source" in manager._sources
        assert "test_source" in manager._source_configs

        # Remove source
        result = await manager.remove_source("test_source")

        # Verify removal
        assert result is True
        assert "test_source" not in manager._sources
        assert "test_source" not in manager._source_configs

    @pytest.mark.asyncio
    async def test_remove_source_not_found(self, source_manager_with_source: Any) -> None:
        """Test removal of non-existent source."""
        manager = source_manager_with_source

        # Try to remove non-existent source
        result = await manager.remove_source("nonexistent_source")

        # Verify failure
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_source_exception_handling(self, source_manager_with_source: Any) -> None:
        """Test source removal exception handling."""
        manager = source_manager_with_source

        # Add a source that exists
        manager._sources["test_source"] = Mock()
        manager._source_configs["test_source"] = Mock()

        # Mock logger to raise exception during removal
        with patch("calendarbot.sources.manager.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Logging failed")

            result = await manager.remove_source("test_source")

            # Should return False due to exception
            assert result is False


class TestSourceManagerEventFetching:
    """Test event fetching and caching operations."""

    @pytest.fixture
    def source_manager_with_sources(self) -> Any:
        """Create source manager with multiple test sources."""
        settings = Mock()
        cache_manager = Mock(spec=CacheManager)
        manager = SourceManager(settings, cache_manager)

        # Create sample events
        event1 = CalendarEvent(
            id="event1",
            subject="Event 1",
            start=DateTimeInfo(date_time=datetime.now()),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1)),
        )
        event2 = CalendarEvent(
            id="event2",
            subject="Event 2",
            start=DateTimeInfo(date_time=datetime.now() + timedelta(hours=2)),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=3)),
        )

        # Mock source handlers
        mock_handler1 = Mock(spec=ICSSourceHandler)
        mock_handler1.is_healthy.return_value = True
        mock_handler1.fetch_events.return_value = [event1]

        mock_handler2 = Mock(spec=ICSSourceHandler)
        mock_handler2.is_healthy.return_value = True
        mock_handler2.fetch_events.return_value = [event2]

        manager._sources = {"source1": mock_handler1, "source2": mock_handler2}

        return manager, [event1, event2]

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, source_manager_with_sources):
        """Test successful event fetching and caching."""
        manager, expected_events = source_manager_with_sources

        # Mock cache manager success
        manager.cache_manager.cache_events = AsyncMock(return_value=True)

        # Fetch and cache events
        with patch("calendarbot.sources.manager.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = await manager.fetch_and_cache_events()

            # Verify success
            assert result is True
            assert manager._last_successful_update == mock_now
            assert manager._consecutive_failures == 0

            # Verify cache manager called with all events
            manager.cache_manager.cache_events.assert_called_once()
            cached_events = manager.cache_manager.cache_events.call_args[0][0]
            assert len(cached_events) == 2

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_no_sources(self):
        """Test event fetching with no sources configured."""
        settings = Mock()
        manager = SourceManager(settings)

        # Fetch events with no sources
        result = await manager.fetch_and_cache_events()

        # Verify failure
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_unhealthy_sources(self, source_manager_with_sources):
        """Test event fetching with unhealthy sources."""
        manager, _ = source_manager_with_sources

        # Make all sources unhealthy
        for handler in manager._sources.values():
            handler.is_healthy.return_value = False

        # Fetch events
        result = await manager.fetch_and_cache_events()

        # Verify failure due to no healthy sources
        assert result is False
        assert manager._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_source_exception(self, source_manager_with_sources):
        """Test event fetching with source exceptions."""
        manager, expected_events = source_manager_with_sources

        # Make one source raise exception
        manager._sources["source1"].fetch_events.side_effect = Exception("Fetch failed")

        # Mock successful caching
        manager.cache_manager.cache_events = AsyncMock(return_value=True)

        # Fetch events
        with patch("calendarbot.sources.manager.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = await manager.fetch_and_cache_events()

            # Should still succeed with events from healthy source
            assert result is True

            # Verify only events from source2 cached
            cached_events = manager.cache_manager.cache_events.call_args[0][0]
            assert len(cached_events) == 1
            assert cached_events[0].id == "event2"

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_cache_failure(self, source_manager_with_sources):
        """Test event fetching with cache failure."""
        manager, _ = source_manager_with_sources

        # Mock cache failure
        manager.cache_manager.cache_events.return_value = False

        # Fetch events
        result = await manager.fetch_and_cache_events()

        # Verify failure handling
        assert result is False
        assert manager._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_no_cache_manager(self, source_manager_with_sources):
        """Test event fetching without cache manager."""
        manager, expected_events = source_manager_with_sources
        manager.cache_manager = None

        # Fetch events
        with patch("calendarbot.sources.manager.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = await manager.fetch_and_cache_events()

            # Should succeed without caching
            assert result is True
            assert manager._last_successful_update == mock_now
            assert manager._consecutive_failures == 0


class TestSourceManagerEventQueries:
    """Test today's events and date range queries."""

    @pytest.fixture
    def source_manager_with_events(self):
        """Create source manager with test events."""
        settings = Mock()
        manager = SourceManager(settings)

        # Create test events for different dates
        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        todays_event = CalendarEvent(
            id="today_event",
            subject="Today's Event",
            start=DateTimeInfo(date_time=today),
            end=DateTimeInfo(date_time=today + timedelta(hours=1)),
        )

        tomorrows_event = CalendarEvent(
            id="tomorrow_event",
            subject="Tomorrow's Event",
            start=DateTimeInfo(date_time=tomorrow),
            end=DateTimeInfo(date_time=tomorrow + timedelta(hours=1)),
        )

        # Mock source handler
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_handler.is_healthy.return_value = True
        mock_handler.get_todays_events.return_value = [todays_event]
        mock_handler.get_events_for_date_range.return_value = [todays_event, tomorrows_event]

        manager._sources = {"test_source": mock_handler}

        return manager, todays_event, tomorrows_event

    @pytest.mark.asyncio
    async def test_get_todays_events_success(self, source_manager_with_events):
        """Test successful retrieval of today's events."""
        manager, todays_event, _ = source_manager_with_events

        # Mock deduplication method
        with patch.object(manager, "_deduplicate_events", side_effect=lambda x: x):
            events = await manager.get_todays_events()

            # Verify results
            assert len(events) == 1
            assert events[0].id == "today_event"

    @pytest.mark.asyncio
    async def test_get_todays_events_with_timezone(self, source_manager_with_events):
        """Test today's events with specific timezone."""
        manager, todays_event, _ = source_manager_with_events

        # Mock deduplication method
        with patch.object(manager, "_deduplicate_events", side_effect=lambda x: x):
            events = await manager.get_todays_events("America/New_York")

            # Verify timezone passed to handler
            manager._sources["test_source"].get_todays_events.assert_called_with("America/New_York")
            assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_todays_events_unhealthy_source(self, source_manager_with_events):
        """Test today's events with unhealthy source."""
        manager, _, _ = source_manager_with_events

        # Make source unhealthy
        manager._sources["test_source"].is_healthy.return_value = False

        # Mock deduplication method
        with patch.object(manager, "_deduplicate_events", side_effect=lambda x: x):
            events = await manager.get_todays_events()

            # Should return empty list
            assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_todays_events_source_exception(self, source_manager_with_events):
        """Test today's events with source exception."""
        manager, _, _ = source_manager_with_events

        # Make source raise exception
        manager._sources["test_source"].get_todays_events.side_effect = Exception("Source error")

        # Mock deduplication method
        with patch.object(manager, "_deduplicate_events", side_effect=lambda x: x):
            events = await manager.get_todays_events()

            # Should return empty list despite exception
            assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_events_for_date_range_success(self, source_manager_with_events):
        """Test successful date range event retrieval."""
        manager, todays_event, tomorrows_event = source_manager_with_events

        start_date = datetime.now()
        end_date = start_date + timedelta(days=2)

        # Mock deduplication and sorting
        def mock_deduplicate(events):
            return events

        with patch.object(manager, "_deduplicate_events", side_effect=mock_deduplicate):
            events = await manager.get_events_for_date_range(start_date, end_date)

            # Verify results
            assert len(events) == 2
            # Verify sorting by start time (events should be in original order as mock returns them)
            assert events[0].id in ["today_event", "tomorrow_event"]
            assert events[1].id in ["today_event", "tomorrow_event"]

    @pytest.mark.asyncio
    async def test_fetch_todays_events_alias(self, source_manager_with_events):
        """Test fetch_todays_events method as alias."""
        manager, todays_event, _ = source_manager_with_events

        # Mock deduplication method
        with patch.object(manager, "_deduplicate_events", side_effect=lambda x: x):
            events = await manager.fetch_todays_events("UTC")

            # Should call get_todays_events
            assert len(events) == 1
            assert events[0].id == "today_event"


class TestSourceManagerDeduplication:
    """Test event deduplication logic."""

    @pytest.fixture
    def source_manager(self):
        """Create source manager for testing."""
        settings = Mock()
        return SourceManager(settings)

    def test_deduplicate_events_no_duplicates(self, source_manager):
        """Test deduplication with no duplicate events."""
        # Create unique events
        event1 = CalendarEvent(
            id="event1",
            subject="Event 1",
            start=DateTimeInfo(date_time=datetime.now()),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1)),
        )
        event2 = CalendarEvent(
            id="event2",
            subject="Event 2",
            start=DateTimeInfo(date_time=datetime.now()),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1)),
        )

        events = [event1, event2]
        result = source_manager._deduplicate_events(events)

        # Should return all events
        assert len(result) == 2
        assert result[0].id == "event1"
        assert result[1].id == "event2"

    def test_deduplicate_events_with_duplicates(self, source_manager):
        """Test deduplication with duplicate events."""
        # Create events with same ID
        event1 = CalendarEvent(
            id="duplicate_event",
            subject="Event 1",
            start=DateTimeInfo(date_time=datetime.now()),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1)),
        )
        event2 = CalendarEvent(
            id="duplicate_event",
            subject="Event 2",  # Different title but same ID
            start=DateTimeInfo(date_time=datetime.now()),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1)),
        )
        event3 = CalendarEvent(
            id="unique_event",
            subject="Event 3",
            start=DateTimeInfo(date_time=datetime.now()),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1)),
        )

        events = [event1, event2, event3]
        result = source_manager._deduplicate_events(events)

        # Should return only unique events (first occurrence kept)
        assert len(result) == 2
        assert result[0].id == "duplicate_event"
        assert result[0].subject == "Event 1"  # First occurrence kept
        assert result[1].id == "unique_event"

    def test_deduplicate_events_empty_list(self, source_manager):
        """Test deduplication with empty event list."""
        events: List[CalendarEvent] = []
        result = source_manager._deduplicate_events(events)

        # Should return empty list
        assert len(result) == 0


class TestSourceManagerHealthAndStatus:
    """Test health checks and status monitoring."""

    @pytest.fixture
    def source_manager_with_mixed_sources(self):
        """Create source manager with healthy and unhealthy sources."""
        settings = Mock()
        manager = SourceManager(settings)

        # Create healthy source
        healthy_handler = Mock(spec=ICSSourceHandler)
        healthy_handler.is_healthy.return_value = True
        healthy_handler.test_connection.return_value = Mock(
            is_healthy=True,
            status=SourceStatus.HEALTHY,
            response_time_ms=100,
            error_message=None,
            events_fetched=5,
        )
        healthy_handler.get_status.return_value = {
            "name": "healthy_source",
            "health_status": SourceStatus.HEALTHY,
        }

        # Create unhealthy source
        unhealthy_handler = Mock(spec=ICSSourceHandler)
        unhealthy_handler.is_healthy.return_value = False
        unhealthy_handler.test_connection.return_value = Mock(
            is_healthy=False,
            status=SourceStatus.ERROR,
            response_time_ms=None,
            error_message="Connection failed",
            events_fetched=0,
        )
        unhealthy_handler.get_status.return_value = {
            "name": "unhealthy_source",
            "health_status": SourceStatus.ERROR,
        }

        manager._sources = {
            "healthy_source": healthy_handler,
            "unhealthy_source": unhealthy_handler,
        }

        return manager

    @pytest.mark.asyncio
    async def test_test_all_sources_success(self, source_manager_with_mixed_sources):
        """Test testing all sources with mixed results."""
        manager = source_manager_with_mixed_sources

        results = await manager.test_all_sources()

        # Verify results structure
        assert len(results) == 2
        assert "healthy_source" in results
        assert "unhealthy_source" in results

        # Verify healthy source result
        healthy_result = results["healthy_source"]
        assert healthy_result["healthy"] is True
        assert healthy_result["status"] == SourceStatus.HEALTHY
        assert healthy_result["response_time_ms"] == 100
        assert healthy_result["events_fetched"] == 5

        # Verify unhealthy source result
        unhealthy_result = results["unhealthy_source"]
        assert unhealthy_result["healthy"] is False
        assert unhealthy_result["status"] == SourceStatus.ERROR
        assert unhealthy_result["error_message"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_test_all_sources_exception_handling(self, source_manager_with_mixed_sources):
        """Test testing all sources with exceptions."""
        manager = source_manager_with_mixed_sources

        # Make one source raise exception during test
        manager._sources["healthy_source"].test_connection.side_effect = Exception("Test failed")

        results = await manager.test_all_sources()

        # Verify exception handling
        assert len(results) == 2
        healthy_result = results["healthy_source"]
        assert healthy_result["healthy"] is False
        assert healthy_result["status"] == SourceStatus.ERROR
        assert "Test failed" in healthy_result["error_message"]

    def test_get_source_status(self, source_manager_with_mixed_sources):
        """Test getting status of all sources."""
        manager = source_manager_with_mixed_sources

        status = manager.get_source_status()

        # Verify status retrieval
        assert len(status) == 2
        assert "healthy_source" in status
        assert "unhealthy_source" in status
        assert status["healthy_source"]["name"] == "healthy_source"
        assert status["unhealthy_source"]["name"] == "unhealthy_source"

    def test_is_healthy_with_healthy_sources(self, source_manager_with_mixed_sources):
        """Test manager health check with some healthy sources."""
        manager = source_manager_with_mixed_sources

        # Should be healthy if at least one source is healthy
        assert manager.is_healthy() is True

    def test_is_healthy_no_sources(self):
        """Test manager health check with no sources."""
        settings = Mock()
        manager = SourceManager(settings)

        # Should be unhealthy with no sources
        assert manager.is_healthy() is False

    def test_is_healthy_all_unhealthy(self):
        """Test manager health check with all sources unhealthy."""
        settings = Mock()
        manager = SourceManager(settings)

        # Add unhealthy source
        unhealthy_handler = Mock(spec=ICSSourceHandler)
        unhealthy_handler.is_healthy.return_value = False
        manager._sources = {"unhealthy_source": unhealthy_handler}

        # Should be unhealthy
        assert manager.is_healthy() is False

    @pytest.mark.asyncio
    async def test_health_check_no_sources(self):
        """Test health check with no sources configured."""
        settings = Mock()
        manager = SourceManager(settings)

        result = await manager.health_check()

        assert result.is_healthy is False
        assert result.status_message == "No sources configured"

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, source_manager_with_mixed_sources):
        """Test health check with all sources healthy."""
        manager = source_manager_with_mixed_sources

        # Make all sources healthy
        for handler in manager._sources.values():
            handler.is_healthy.return_value = True

        result = await manager.health_check()

        assert result.is_healthy is True
        assert "All 2 sources are healthy" in result.status_message

    @pytest.mark.asyncio
    async def test_health_check_mixed_health(self, source_manager_with_mixed_sources):
        """Test health check with mixed source health."""
        manager = source_manager_with_mixed_sources

        result = await manager.health_check()

        assert result.is_healthy is True  # At least one healthy
        assert "1/2 sources healthy" in result.status_message

    @pytest.mark.asyncio
    async def test_health_check_all_unhealthy(self, source_manager_with_mixed_sources):
        """Test health check with all sources unhealthy."""
        manager = source_manager_with_mixed_sources

        # Make all sources unhealthy
        for handler in manager._sources.values():
            handler.is_healthy.return_value = False

        result = await manager.health_check()

        assert result.is_healthy is False
        assert "All 2 sources are unhealthy" in result.status_message

    def test_get_summary_status(self, source_manager_with_mixed_sources):
        """Test getting summary status."""
        manager = source_manager_with_mixed_sources

        # Set some tracking data
        test_time = datetime(2024, 1, 15, 10, 0, 0)
        manager._last_successful_update = test_time
        manager._consecutive_failures = 2

        summary = manager.get_summary_status()

        # Verify summary data
        assert summary["total_sources"] == 2
        assert summary["healthy_sources"] == 1  # Only one healthy
        assert summary["last_successful_update"] == test_time
        assert summary["consecutive_failures"] == 2
        assert summary["is_healthy"] is True  # At least one healthy
        assert set(summary["source_names"]) == {"healthy_source", "unhealthy_source"}


class TestSourceManagerSourceInfo:
    """Test source information retrieval."""

    @pytest.fixture
    def source_manager_with_info(self):
        """Create source manager with detailed source info."""
        settings = Mock()
        cache_manager = Mock(spec=CacheManager)
        manager = SourceManager(settings, cache_manager)

        # Create mock handler and config
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_handler.is_healthy.return_value = True
        mock_handler.get_health_check.return_value = Mock()
        mock_handler.get_metrics.return_value = Mock()

        mock_config = Mock(spec=SourceConfig)
        mock_config.name = "test_source"
        mock_config.url = "https://example.com/calendar.ics"

        manager._sources = {"test_source": mock_handler}
        manager._source_configs = {"test_source": mock_config}

        return manager

    @pytest.mark.asyncio
    async def test_get_source_info_primary_default(self, source_manager_with_info):
        """Test getting source info for primary source (default)."""
        manager = source_manager_with_info

        # Add primary source
        manager._sources["primary"] = manager._sources["test_source"]
        manager._source_configs["primary"] = manager._source_configs["test_source"]
        manager._source_configs["primary"].url = "https://primary.example.com/calendar.ics"

        info = await manager.get_source_info()

        # Should default to primary source
        assert info.status == "healthy"
        assert info.url == "https://primary.example.com/calendar.ics"
        assert info.is_configured is True

    @pytest.mark.asyncio
    async def test_get_source_info_specific_source(self, source_manager_with_info):
        """Test getting source info for specific source."""
        manager = source_manager_with_info

        info = await manager.get_source_info("test_source")

        assert info.status == "healthy"
        assert info.url == "https://example.com/calendar.ics"
        assert info.is_configured is True

    @pytest.mark.asyncio
    async def test_get_source_info_nonexistent_source(self, source_manager_with_info):
        """Test getting source info for non-existent source."""
        manager = source_manager_with_info

        info = await manager.get_source_info("nonexistent")

        assert info.status == "not_configured"
        assert info.url == ""
        assert info.is_configured is False

    @pytest.mark.asyncio
    async def test_get_source_info_unhealthy_source(self, source_manager_with_info):
        """Test getting source info for unhealthy source."""
        manager = source_manager_with_info

        # Make source unhealthy
        manager._sources["test_source"].is_healthy.return_value = False

        info = await manager.get_source_info("test_source")

        assert info.status == "unhealthy"
        assert info.is_configured is True

    def test_get_detailed_source_info_success(self, source_manager_with_info):
        """Test getting detailed source information."""
        manager = source_manager_with_info

        # Mock the handler methods to return proper model instances
        mock_handler = manager._sources["test_source"]
        mock_handler.get_health_check.return_value = SourceHealthCheck(
            timestamp=datetime.now(), status=SourceStatus.HEALTHY, error_message=None
        )
        mock_handler.get_metrics.return_value = SourceMetrics(
            total_requests=10,
            successful_requests=9,
            failed_requests=1,
            avg_response_time_ms=500.0,
            last_fetch_time=datetime.now(),
        )

        info = manager.get_detailed_source_info("test_source")

        assert info is not None
        assert info.config is manager._source_configs["test_source"]
        assert info.cached_events_count == 0  # Default when no cache data
        assert info.last_cache_update is None

    def test_get_detailed_source_info_not_found(self, source_manager_with_info):
        """Test getting detailed info for non-existent source."""
        manager = source_manager_with_info

        info = manager.get_detailed_source_info("nonexistent")

        assert info is None


class TestSourceManagerConfigurationAndCleanup:
    """Test configuration refresh and cleanup operations."""

    @pytest.fixture
    def source_manager_with_primary(self):
        """Create source manager with primary source."""
        settings = Mock()
        settings.ics_url = "https://example.com/calendar.ics"
        manager = SourceManager(settings)

        # Add primary source with config
        mock_handler = Mock(spec=ICSSourceHandler)
        mock_config = Mock(spec=SourceConfig)
        mock_config.url = "https://example.com/calendar.ics"

        manager._sources = {"primary": mock_handler}
        manager._source_configs = {"primary": mock_config}

        return manager

    @pytest.mark.asyncio
    async def test_refresh_source_configs_no_changes(self, source_manager_with_primary):
        """Test configuration refresh with no changes."""
        manager = source_manager_with_primary

        # URL matches current config
        await manager.refresh_source_configs()

        # Should complete without error (just logs refresh request)
        assert "primary" in manager._sources

    @pytest.mark.asyncio
    async def test_refresh_source_configs_url_changed(self, source_manager_with_primary):
        """Test configuration refresh with URL change."""
        manager = source_manager_with_primary

        # Change settings URL
        manager.settings.ics_url = "https://newurl.example.com/calendar.ics"

        await manager.refresh_source_configs()

        # Should detect URL change and log it
        # In full implementation would update the configuration
        assert "primary" in manager._sources

    @pytest.mark.asyncio
    async def test_refresh_source_configs_no_primary(self):
        """Test configuration refresh without primary source."""
        settings = Mock()
        settings.ics_url = "https://example.com/calendar.ics"
        manager = SourceManager(settings)

        # No primary source configured
        await manager.refresh_source_configs()

        # Should complete without error
        assert len(manager._sources) == 0

    @pytest.mark.asyncio
    async def test_refresh_source_configs_exception_handling(self, source_manager_with_primary):
        """Test configuration refresh exception handling."""
        manager = source_manager_with_primary

        # Remove settings attribute to cause exception
        delattr(manager.settings, "ics_url")

        # Should handle exception gracefully
        await manager.refresh_source_configs()

        # Manager should still be functional
        assert "primary" in manager._sources

    @pytest.mark.asyncio
    async def test_cleanup_success(self, source_manager_with_primary):
        """Test successful cleanup operation."""
        manager = source_manager_with_primary

        # Cleanup should complete without error
        await manager.cleanup()

        # Sources should still exist (cleanup doesn't remove them)
        assert "primary" in manager._sources

    @pytest.mark.asyncio
    async def test_cleanup_exception_handling(self, source_manager_with_primary):
        """Test cleanup exception handling."""
        manager = source_manager_with_primary

        # Mock logger to raise exception during cleanup
        with patch("calendarbot.sources.manager.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Logging failed")

            # Should handle exception gracefully
            await manager.cleanup()

            # Verify error was logged
            mock_logger.error.assert_called()

            # Manager should still be functional
            assert "primary" in manager._sources
