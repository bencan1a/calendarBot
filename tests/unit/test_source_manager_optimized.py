"""Optimized source manager tests for core functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.sources.manager import SourceManager


@pytest.mark.unit
@pytest.mark.critical_path
class TestSourceManagerCore:
    """Core source manager functionality tests."""

    @pytest.fixture
    def source_manager(self, test_settings, mock_cache_manager):
        """Create source manager with mocked cache."""
        return SourceManager(test_settings, mock_cache_manager)

    @pytest.mark.asyncio
    async def test_source_manager_initialization(
        self, source_manager, test_settings, mock_cache_manager
    ):
        """Test source manager initializes correctly."""
        assert source_manager.settings == test_settings
        assert source_manager.cache_manager == mock_cache_manager
        assert source_manager._sources == {}
        assert source_manager._source_configs == {}

    @pytest.mark.asyncio
    async def test_initialize_with_ics_url(self, source_manager, test_settings):
        """Test initialization with ICS URL configured."""
        test_settings.ics_url = "https://example.com/calendar.ics"

        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health = MagicMock()
            mock_health.is_healthy = True
            mock_handler.test_connection.return_value = mock_health
            mock_handler_class.return_value = mock_handler

            success = await source_manager.initialize()

            assert success is True
            assert "primary" in source_manager._sources

    @pytest.mark.asyncio
    async def test_initialize_without_ics_url(self, source_manager, test_settings):
        """Test initialization without ICS URL."""
        test_settings.ics_url = None

        success = await source_manager.initialize()

        assert success is False

    @pytest.mark.asyncio
    async def test_add_ics_source_success(self, source_manager):
        """Test successfully adding ICS source."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health = MagicMock()
            mock_health.is_healthy = True
            mock_handler.test_connection.return_value = mock_health
            mock_handler_class.return_value = mock_handler

            success = await source_manager.add_ics_source(
                name="test_source", url="https://example.com/calendar.ics"
            )

            assert success is True
            assert "test_source" in source_manager._sources
            assert "test_source" in source_manager._source_configs

    @pytest.mark.asyncio
    async def test_add_ics_source_connection_failure(self, source_manager):
        """Test adding ICS source with connection failure."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health = MagicMock()
            mock_health.is_healthy = False
            mock_health.error_message = "Connection failed"
            mock_handler.test_connection.return_value = mock_health
            mock_handler_class.return_value = mock_handler

            success = await source_manager.add_ics_source(
                name="test_source", url="https://example.com/calendar.ics"
            )

            assert success is False
            assert "test_source" not in source_manager._sources

    @pytest.mark.asyncio
    async def test_add_ics_source_with_basic_auth(self, source_manager):
        """Test adding ICS source with basic authentication."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health = MagicMock()
            mock_health.is_healthy = True
            mock_handler.test_connection.return_value = mock_health
            mock_handler_class.return_value = mock_handler

            success = await source_manager.add_ics_source(
                name="auth_source",
                url="https://example.com/calendar.ics",
                auth_type="basic",
                username="user",
                password="pass",
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_add_ics_source_with_bearer_auth(self, source_manager):
        """Test adding ICS source with bearer authentication."""
        with patch("calendarbot.sources.manager.ICSSourceHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_health = MagicMock()
            mock_health.is_healthy = True
            mock_handler.test_connection.return_value = mock_health
            mock_handler_class.return_value = mock_handler

            success = await source_manager.add_ics_source(
                name="bearer_source",
                url="https://example.com/calendar.ics",
                auth_type="bearer",
                bearer_token="token123",
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_remove_source_success(self, source_manager):
        """Test successfully removing source."""
        # Add a source first
        source_manager._sources["test_source"] = MagicMock()
        source_manager._source_configs["test_source"] = MagicMock()

        success = await source_manager.remove_source("test_source")

        assert success is True
        assert "test_source" not in source_manager._sources
        assert "test_source" not in source_manager._source_configs

    @pytest.mark.asyncio
    async def test_remove_source_not_found(self, source_manager):
        """Test removing non-existent source."""
        success = await source_manager.remove_source("nonexistent")

        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_success(self, source_manager, sample_events):
        """Test successful event fetching and caching."""
        # Mock source
        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.fetch_events.return_value = sample_events
        source_manager._sources["test_source"] = mock_handler

        success = await source_manager.fetch_and_cache_events()

        assert success is True
        assert source_manager._last_successful_update is not None
        assert source_manager._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_no_sources(self, source_manager):
        """Test fetching with no sources configured."""
        success = await source_manager.fetch_and_cache_events()

        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_unhealthy_source(self, source_manager):
        """Test fetching with unhealthy source."""
        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = False
        source_manager._sources["unhealthy_source"] = mock_handler

        success = await source_manager.fetch_and_cache_events()

        assert success is False

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_source_exception(self, source_manager):
        """Test fetching with source exception."""
        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.fetch_events.side_effect = Exception("Fetch error")
        source_manager._sources["error_source"] = mock_handler

        success = await source_manager.fetch_and_cache_events()

        assert success is False
        assert source_manager._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_cache_failure(self, source_manager, sample_events):
        """Test fetching with cache failure."""
        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.fetch_events.return_value = sample_events
        source_manager._sources["test_source"] = mock_handler

        # Mock cache failure
        source_manager.cache_manager.cache_events.return_value = False

        success = await source_manager.fetch_and_cache_events()

        assert success is False
        assert source_manager._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_and_cache_events_no_cache_manager(self, test_settings, sample_events):
        """Test fetching without cache manager."""
        source_manager = SourceManager(test_settings, None)

        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.fetch_events.return_value = sample_events
        source_manager._sources["test_source"] = mock_handler

        success = await source_manager.fetch_and_cache_events()

        assert success is True

    @pytest.mark.asyncio
    async def test_get_todays_events(self, source_manager, sample_events):
        """Test getting today's events."""
        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.get_todays_events.return_value = sample_events
        source_manager._sources["test_source"] = mock_handler

        events = await source_manager.get_todays_events()

        assert len(events) == len(sample_events)

    @pytest.mark.asyncio
    async def test_get_todays_events_with_duplicates(self, source_manager, sample_events):
        """Test getting today's events with duplicate removal."""
        # Create duplicate events with same ID
        duplicate_events = sample_events + [sample_events[0]]

        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.get_todays_events.return_value = duplicate_events
        source_manager._sources["test_source"] = mock_handler

        events = await source_manager.get_todays_events()

        # Should remove duplicates
        assert len(events) == len(sample_events)

    @pytest.mark.asyncio
    async def test_get_events_for_date_range(self, source_manager, sample_events):
        """Test getting events for date range."""
        start_date = datetime.now()
        end_date = datetime.now()

        mock_handler = AsyncMock()
        mock_handler.is_healthy.return_value = True
        mock_handler.get_events_for_date_range.return_value = sample_events
        source_manager._sources["test_source"] = mock_handler

        events = await source_manager.get_events_for_date_range(start_date, end_date)

        assert len(events) == len(sample_events)

    @pytest.mark.asyncio
    async def test_test_all_sources(self, source_manager):
        """Test testing all sources."""
        mock_handler = AsyncMock()
        mock_health = MagicMock()
        mock_health.is_healthy = True
        mock_health.status = "healthy"
        mock_health.response_time_ms = 100
        mock_health.error_message = None
        mock_health.events_fetched = 5
        mock_handler.test_connection.return_value = mock_health
        source_manager._sources["test_source"] = mock_handler

        results = await source_manager.test_all_sources()

        assert "test_source" in results
        assert results["test_source"]["healthy"] is True

    def test_get_source_status(self, source_manager):
        """Test getting source status."""
        mock_handler = MagicMock()
        mock_handler.get_status.return_value = {"status": "healthy"}
        source_manager._sources["test_source"] = mock_handler

        status = source_manager.get_source_status()

        assert "test_source" in status

    @pytest.mark.asyncio
    async def test_get_source_info_primary(self, source_manager):
        """Test getting primary source info."""
        mock_handler = MagicMock()
        mock_handler.is_healthy.return_value = True
        mock_config = MagicMock()
        mock_config.url = "https://example.com/calendar.ics"

        source_manager._sources["primary"] = mock_handler
        source_manager._source_configs["primary"] = mock_config

        info = await source_manager.get_source_info()

        assert info.status == "healthy"
        assert info.url == "https://example.com/calendar.ics"
        assert info.is_configured is True

    @pytest.mark.asyncio
    async def test_get_source_info_not_configured(self, source_manager):
        """Test getting source info when not configured."""
        info = await source_manager.get_source_info()

        assert info.status == "not_configured"
        assert info.url == ""
        assert info.is_configured is False

    def test_is_healthy_with_sources(self, source_manager):
        """Test health check with sources."""
        mock_handler = MagicMock()
        mock_handler.is_healthy.return_value = True
        source_manager._sources["test_source"] = mock_handler

        is_healthy = source_manager.is_healthy()

        assert is_healthy is True

    def test_is_healthy_no_sources(self, source_manager):
        """Test health check with no sources."""
        is_healthy = source_manager.is_healthy()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, source_manager):
        """Test health check when all sources healthy."""
        mock_handler = MagicMock()
        mock_handler.is_healthy.return_value = True
        source_manager._sources["test_source"] = mock_handler

        health = await source_manager.health_check()

        assert health.is_healthy is True
        assert "healthy" in health.status_message

    @pytest.mark.asyncio
    async def test_health_check_no_sources(self, source_manager):
        """Test health check with no sources."""
        health = await source_manager.health_check()

        assert health.is_healthy is False
        assert "No sources configured" in health.status_message

    @pytest.mark.asyncio
    async def test_health_check_mixed_health(self, source_manager):
        """Test health check with mixed source health."""
        healthy_handler = MagicMock()
        healthy_handler.is_healthy.return_value = True

        unhealthy_handler = MagicMock()
        unhealthy_handler.is_healthy.return_value = False

        source_manager._sources["healthy"] = healthy_handler
        source_manager._sources["unhealthy"] = unhealthy_handler

        health = await source_manager.health_check()

        assert health.is_healthy is True  # Some sources healthy
        assert "1/2" in health.status_message

    def test_get_summary_status(self, source_manager):
        """Test getting summary status."""
        mock_handler = MagicMock()
        mock_handler.is_healthy.return_value = True
        source_manager._sources["test_source"] = mock_handler

        summary = source_manager.get_summary_status()

        assert summary["total_sources"] == 1
        assert summary["healthy_sources"] == 1
        assert summary["is_healthy"] is True
        assert "test_source" in summary["source_names"]

    @pytest.mark.asyncio
    async def test_cleanup(self, source_manager):
        """Test cleanup process."""
        # Should not raise exception
        await source_manager.cleanup()


@pytest.mark.unit
class TestSourceManagerUtils:
    """Utility function tests for source manager."""

    @pytest.fixture
    def source_manager(self, test_settings, mock_cache_manager):
        """Create source manager."""
        return SourceManager(test_settings, mock_cache_manager)

    def test_deduplicate_events(self, source_manager, sample_events):
        """Test event deduplication."""
        # Create events with duplicate IDs
        duplicate_events = sample_events + [sample_events[0]]

        unique_events = source_manager._deduplicate_events(duplicate_events)

        assert len(unique_events) == len(sample_events)

        # Verify all unique IDs
        ids = [event.id for event in unique_events]
        assert len(ids) == len(set(ids))

    def test_deduplicate_events_empty_list(self, source_manager):
        """Test deduplication with empty list."""
        unique_events = source_manager._deduplicate_events([])

        assert unique_events == []

    @pytest.mark.asyncio
    async def test_refresh_source_configs(self, source_manager):
        """Test refreshing source configurations."""
        # Should not raise exception
        await source_manager.refresh_source_configs()
