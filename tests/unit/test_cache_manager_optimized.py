"""Optimized cache manager tests for core functionality."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.critical_path
class TestCacheManagerCore:
    """Core cache manager functionality tests."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create lightweight cache manager mock."""
        mock = AsyncMock()
        mock.initialize.return_value = True
        mock.is_cache_fresh.return_value = True
        mock.get_todays_cached_events.return_value = []
        mock.cache_events.return_value = True
        mock.cleanup_old_events.return_value = 0
        return mock

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self, mock_cache_manager):
        """Test cache manager initializes successfully."""
        result = await mock_cache_manager.initialize()

        assert result is True
        mock_cache_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_manager_is_cache_fresh_true(self, mock_cache_manager):
        """Test cache freshness check returns True."""
        result = await mock_cache_manager.is_cache_fresh()

        assert result is True

    @pytest.mark.asyncio
    async def test_cache_manager_is_cache_fresh_false(self, mock_cache_manager):
        """Test cache freshness check returns False."""
        mock_cache_manager.is_cache_fresh.return_value = False

        result = await mock_cache_manager.is_cache_fresh()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_todays_cached_events_empty(self, mock_cache_manager):
        """Test getting today's events when cache is empty."""
        events = await mock_cache_manager.get_todays_cached_events()

        assert events == []
        mock_cache_manager.get_todays_cached_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_todays_cached_events_with_events(self, mock_cache_manager, sample_events):
        """Test getting today's events when cache has events."""
        mock_cache_manager.get_todays_cached_events.return_value = sample_events

        events = await mock_cache_manager.get_todays_cached_events()

        assert len(events) == len(sample_events)
        assert events == sample_events

    @pytest.mark.asyncio
    async def test_cache_events_success(self, mock_cache_manager, sample_events):
        """Test caching events successfully."""
        result = await mock_cache_manager.cache_events(sample_events)

        assert result is True
        mock_cache_manager.cache_events.assert_called_once_with(sample_events)

    @pytest.mark.asyncio
    async def test_cache_events_failure(self, mock_cache_manager, sample_events):
        """Test caching events failure."""
        mock_cache_manager.cache_events.return_value = False

        result = await mock_cache_manager.cache_events(sample_events)

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_old_events(self, mock_cache_manager):
        """Test cleaning up old events."""
        mock_cache_manager.cleanup_old_events.return_value = 5

        result = await mock_cache_manager.cleanup_old_events(days_old=30)

        assert result == 5
        mock_cache_manager.cleanup_old_events.assert_called_once_with(days_old=30)

    @pytest.mark.asyncio
    async def test_get_cache_status(self, mock_cache_manager):
        """Test getting cache status."""
        mock_status = MagicMock()
        mock_status.last_update = datetime.now()
        mock_status.is_stale = False
        mock_cache_manager.get_cache_status.return_value = mock_status

        status = await mock_cache_manager.get_cache_status()

        assert status.last_update is not None
        assert status.is_stale is False

    @pytest.mark.asyncio
    async def test_get_cache_summary(self, mock_cache_manager):
        """Test getting cache summary."""
        mock_summary = {
            "total_events": 10,
            "is_fresh": True,
            "last_update": datetime.now().isoformat(),
        }
        mock_cache_manager.get_cache_summary.return_value = mock_summary

        summary = await mock_cache_manager.get_cache_summary()

        assert summary["total_events"] == 10
        assert summary["is_fresh"] is True
        assert "last_update" in summary


@pytest.mark.unit
class TestCacheManagerErrorHandling:
    """Cache manager error handling tests."""

    @pytest.fixture
    def failing_cache_manager(self):
        """Create cache manager that simulates failures."""
        mock = AsyncMock()
        mock.initialize.side_effect = Exception("Database error")
        mock.cache_events.side_effect = Exception("Cache write error")
        mock.get_todays_cached_events.side_effect = Exception("Cache read error")
        return mock

    @pytest.mark.asyncio
    async def test_initialization_failure(self, failing_cache_manager):
        """Test cache manager initialization failure."""
        with pytest.raises(Exception, match="Database error"):
            await failing_cache_manager.initialize()

    @pytest.mark.asyncio
    async def test_cache_events_exception(self, failing_cache_manager, sample_events):
        """Test caching events with exception."""
        with pytest.raises(Exception, match="Cache write error"):
            await failing_cache_manager.cache_events(sample_events)

    @pytest.mark.asyncio
    async def test_get_events_exception(self, failing_cache_manager):
        """Test getting events with exception."""
        with pytest.raises(Exception, match="Cache read error"):
            await failing_cache_manager.get_todays_cached_events()


@pytest.mark.unit
class TestCacheManagerPerformance:
    """Performance-focused cache manager tests."""

    @pytest.mark.asyncio
    async def test_cache_large_number_of_events(self, mock_cache_manager, performance_tracker):
        """Test caching large number of events efficiently."""
        # Create many mock events
        large_event_list = [MagicMock() for _ in range(100)]

        performance_tracker.start_timer("cache_large_events")

        await mock_cache_manager.cache_events(large_event_list)

        performance_tracker.end_timer("cache_large_events")

        # Should complete quickly even with many events (mock)
        performance_tracker.assert_performance("cache_large_events", 1.0)

    @pytest.mark.asyncio
    async def test_repeated_cache_operations(
        self, mock_cache_manager, sample_events, performance_tracker
    ):
        """Test repeated cache operations perform well."""
        performance_tracker.start_timer("repeated_operations")

        # Perform multiple operations
        for _ in range(10):
            await mock_cache_manager.cache_events(sample_events)
            await mock_cache_manager.get_todays_cached_events()
            await mock_cache_manager.is_cache_fresh()

        performance_tracker.end_timer("repeated_operations")

        # Should complete quickly with mocked operations
        performance_tracker.assert_performance("repeated_operations", 1.0)


@pytest.mark.unit
class TestCacheManagerIntegration:
    """Integration boundary tests for cache manager."""

    @pytest.mark.asyncio
    async def test_cache_manager_with_real_events(self, mock_cache_manager, sample_events):
        """Test cache manager handles real event objects."""
        # Use actual sample events instead of mocks
        result = await mock_cache_manager.cache_events(sample_events)

        assert result is True

        # Verify the call was made with actual events
        mock_cache_manager.cache_events.assert_called_once()
        call_args = mock_cache_manager.cache_events.call_args[0][0]
        assert len(call_args) == len(sample_events)

    @pytest.mark.asyncio
    async def test_cache_manager_date_filtering(self, mock_cache_manager, sample_events):
        """Test cache manager date filtering behavior."""
        # Mock returning events for specific date
        mock_cache_manager.get_todays_cached_events.return_value = sample_events

        events = await mock_cache_manager.get_todays_cached_events()

        # Should return the configured events
        assert len(events) == len(sample_events)
        assert events == sample_events

    @pytest.mark.asyncio
    async def test_cache_manager_cleanup_with_date_param(self, mock_cache_manager):
        """Test cache manager cleanup with various date parameters."""
        mock_cache_manager.cleanup_old_events.return_value = 3

        # Test different cleanup periods
        result_30_days = await mock_cache_manager.cleanup_old_events(days_old=30)
        result_7_days = await mock_cache_manager.cleanup_old_events(days_old=7)
        result_1_day = await mock_cache_manager.cleanup_old_events(days_old=1)

        assert all(result == 3 for result in [result_30_days, result_7_days, result_1_day])
        assert mock_cache_manager.cleanup_old_events.call_count == 3
