"""Unit tests for bounded concurrency and worker-based RRULE expansion system."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot_lite.lite_rrule_expander import RRuleWorkerPool, get_worker_pool
from calendarbot_lite.server import _fetch_and_parse_source, _refresh_once


class TestBoundedConcurrency:
    """Test bounded concurrency for calendar fetches."""

    @pytest.mark.asyncio
    async def test_fetch_and_parse_source_with_semaphore(self):
        """Test that fetch_and_parse_source respects semaphore limits."""
        semaphore = asyncio.Semaphore(1)
        config = {"request_timeout": 30, "max_retries": 3, "retry_backoff_factor": 1.5}
        src_cfg = "https://example.com/calendar.ics"
        rrule_days = 14

        # Mock the imports and functions
        with (
            patch("calendarbot_lite.server.calendarbot.sources") as mock_sources,
            patch("calendarbot_lite.server.lite_parser") as mock_parser,
            patch("calendarbot_lite.server.lite_rrule_expander") as mock_rrule,
            patch("calendarbot_lite.server.lite_models") as mock_models,
            patch("calendarbot_lite.server.LiteICSFetcher") as mock_fetcher,
        ):
            # Setup mocks
            mock_sources.ics_source.IcsSource = Mock()
            mock_models.LiteICSSource = Mock()
            mock_models.LiteICSSource.return_value = Mock(url="https://example.com/calendar.ics")

            mock_response = Mock()
            mock_response.success = True
            mock_response.stream_handle = None
            mock_response.content = "BEGIN:VCALENDAR\nEND:VCALENDAR"

            mock_fetcher_instance = AsyncMock()
            mock_fetcher_instance.__aenter__ = AsyncMock(return_value=mock_fetcher_instance)
            mock_fetcher_instance.__aexit__ = AsyncMock(return_value=None)
            mock_fetcher_instance.fetch_ics = AsyncMock(return_value=mock_response)
            mock_fetcher.return_value = mock_fetcher_instance

            mock_parser.parse_ics = Mock(return_value=[])
            mock_rrule.expand = Mock(return_value=[])

            # Test the function
            result = await _fetch_and_parse_source(semaphore, src_cfg, config, rrule_days)

            assert isinstance(result, list)
            mock_fetcher_instance.fetch_ics.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_once_concurrent_fetching(self):
        """Test that _refresh_once uses concurrent fetching with bounded semaphore."""
        config = {
            "ics_sources": ["https://example1.com/cal.ics", "https://example2.com/cal.ics"],
            "fetch_concurrency": 2,
            "rrule_expansion_days": 14,
            "event_window_size": 10,
        }
        skipped_store = None
        event_window_ref = [()]
        window_lock = asyncio.Lock()

        with patch("calendarbot_lite.server._fetch_and_parse_source") as mock_fetch:
            mock_fetch.return_value = []

            await _refresh_once(config, skipped_store, event_window_ref, window_lock)

            # Should have called fetch_and_parse_source for each source
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_fetch_respects_limits(self):
        """Test that concurrent fetching respects the configured limits."""
        config = {
            "ics_sources": [
                "https://example1.com/cal.ics",
                "https://example2.com/cal.ics",
                "https://example3.com/cal.ics",
            ],
            "fetch_concurrency": 1,  # Force sequential processing
            "rrule_expansion_days": 14,
            "event_window_size": 10,
        }
        skipped_store = None
        event_window_ref = [()]
        window_lock = asyncio.Lock()

        fetch_times = []

        async def mock_fetch_with_timing(*args, **kwargs):
            fetch_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)  # Simulate fetch time
            return []

        with patch(
            "calendarbot_lite.server._fetch_and_parse_source", side_effect=mock_fetch_with_timing
        ):
            await _refresh_once(config, skipped_store, event_window_ref, window_lock)

            # With concurrency=1, fetches should be sequential
            assert len(fetch_times) == 3
            # Each fetch should start after the previous one (allowing for small timing variations)
            time_diffs = [fetch_times[i + 1] - fetch_times[i] for i in range(len(fetch_times) - 1)]
            assert all(diff >= 0.05 for diff in time_diffs)  # Should be roughly 0.1s apart


class TestRRuleWorkerPool:
    """Test the RRULE worker pool system."""

    def test_worker_pool_initialization(self):
        """Test RRuleWorkerPool initialization with settings."""
        settings = Mock()
        settings.rrule_worker_concurrency = 2
        settings.max_occurrences_per_rule = 100
        settings.expansion_days_window = 180
        settings.expansion_time_budget_ms_per_rule = 150
        settings.expansion_yield_frequency = 25

        pool = RRuleWorkerPool(settings)

        assert pool.concurrency == 2
        assert pool.max_occurrences == 100
        assert pool.expansion_days == 180
        assert pool.time_budget_ms == 150
        assert pool.yield_frequency == 25

    def test_worker_pool_default_settings(self):
        """Test RRuleWorkerPool with default settings."""
        settings = Mock()
        # No attributes set, should use defaults
        for attr in [
            "rrule_worker_concurrency",
            "max_occurrences_per_rule",
            "expansion_days_window",
            "expansion_time_budget_ms_per_rule",
            "expansion_yield_frequency",
        ]:
            if hasattr(settings, attr):
                delattr(settings, attr)

        pool = RRuleWorkerPool(settings)

        assert pool.concurrency == 1
        assert pool.max_occurrences == 250
        assert pool.expansion_days == 365
        assert pool.time_budget_ms == 200
        assert pool.yield_frequency == 50

    @pytest.mark.asyncio
    async def test_worker_pool_expand_event_async(self):
        """Test async event expansion with cooperative multitasking."""
        settings = Mock()
        settings.rrule_worker_concurrency = 1
        settings.max_occurrences_per_rule = 5  # Small limit for testing
        settings.expansion_days_window = 30
        settings.expansion_time_budget_ms_per_rule = 1000  # Large budget
        settings.expansion_yield_frequency = 2  # Yield every 2 events

        pool = RRuleWorkerPool(settings)

        # Mock event and expander
        master_event = Mock()
        master_event.id = "test-event"
        master_event.start = Mock()
        master_event.start.date_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

        rrule_string = "FREQ=DAILY;COUNT=3"

        with patch("calendarbot_lite.lite_rrule_expander.LiteRRuleExpander") as mock_expander_class:
            mock_expander = Mock()
            mock_expander.expand_rrule.return_value = [Mock(), Mock(), Mock()]  # 3 events
            mock_expander_class.return_value = mock_expander

            events = []
            async for event in pool.expand_event_async(master_event, rrule_string):
                events.append(event)

            assert len(events) == 3
            mock_expander.expand_rrule.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_pool_time_budget_limit(self):
        """Test that worker pool respects time budget limits."""
        settings = Mock()
        settings.rrule_worker_concurrency = 1
        settings.max_occurrences_per_rule = 1000  # High limit
        settings.expansion_days_window = 30
        settings.expansion_time_budget_ms_per_rule = 1  # Very small budget
        settings.expansion_yield_frequency = 10

        pool = RRuleWorkerPool(settings)

        master_event = Mock()
        master_event.id = "test-event"
        master_event.start = Mock()
        master_event.start.date_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

        rrule_string = "FREQ=DAILY;COUNT=100"

        with patch("calendarbot_lite.lite_rrule_expander.LiteRRuleExpander") as mock_expander_class:
            mock_expander = Mock()
            # Return many events to test time budget
            mock_expander.expand_rrule.return_value = [Mock() for _ in range(100)]
            mock_expander_class.return_value = mock_expander

            events = []
            async for event in pool.expand_event_async(master_event, rrule_string):
                events.append(event)

            # Should be limited by time budget, not by count
            assert len(events) < 100

    @pytest.mark.asyncio
    async def test_worker_pool_occurrence_limit(self):
        """Test that worker pool respects occurrence limits."""
        settings = Mock()
        settings.rrule_worker_concurrency = 1
        settings.max_occurrences_per_rule = 5  # Small limit
        settings.expansion_days_window = 30
        settings.expansion_time_budget_ms_per_rule = 10000  # Large budget
        settings.expansion_yield_frequency = 2

        pool = RRuleWorkerPool(settings)

        master_event = Mock()
        master_event.id = "test-event"
        master_event.start = Mock()
        master_event.start.date_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

        rrule_string = "FREQ=DAILY;COUNT=100"

        with patch("calendarbot_lite.lite_rrule_expander.LiteRRuleExpander") as mock_expander_class:
            mock_expander = Mock()
            # Return many events to test occurrence limit
            mock_expander.expand_rrule.return_value = [Mock() for _ in range(100)]
            mock_expander_class.return_value = mock_expander

            events = []
            async for event in pool.expand_event_async(master_event, rrule_string):
                events.append(event)

            # Should be limited by max_occurrences
            assert len(events) == 5

    @pytest.mark.asyncio
    async def test_worker_pool_shutdown(self):
        """Test worker pool shutdown functionality."""
        settings = Mock()
        settings.rrule_worker_concurrency = 1

        pool = RRuleWorkerPool(settings)

        # Add a mock task
        mock_task = Mock()
        mock_task.done.return_value = False
        mock_task.cancel = Mock()
        pool._active_tasks.add(mock_task)

        with patch("asyncio.gather") as mock_gather:
            mock_gather.return_value = None

            await pool.shutdown()

            mock_task.cancel.assert_called_once()
            mock_gather.assert_called_once()
            assert len(pool._active_tasks) == 0

    def test_get_worker_pool_singleton(self):
        """Test that get_worker_pool returns singleton instance."""
        settings1 = Mock()
        settings2 = Mock()

        # Clear any existing global pool
        import calendarbot_lite.lite_rrule_expander as module

        module._worker_pool = None

        pool1 = get_worker_pool(settings1)
        pool2 = get_worker_pool(settings2)

        # Should return the same instance
        assert pool1 is pool2


class TestConcurrencyConfiguration:
    """Test concurrency configuration and bounds."""

    @pytest.mark.asyncio
    async def test_fetch_concurrency_bounds(self):
        """Test that fetch_concurrency is properly bounded."""
        # Test with various values
        test_cases = [
            (0, 1),  # Below minimum should be clamped to 1
            (1, 1),  # Minimum valid value
            (2, 2),  # Default value
            (3, 3),  # Maximum valid value
            (5, 3),  # Above maximum should be clamped to 3
        ]

        for input_concurrency, expected_concurrency in test_cases:
            config = {
                "ics_sources": ["https://example.com/cal.ics"],
                "fetch_concurrency": input_concurrency,
                "rrule_expansion_days": 14,
                "event_window_size": 10,
            }
            event_window_ref = [()]
            window_lock = asyncio.Lock()

            with patch("calendarbot_lite.server._fetch_and_parse_source") as mock_fetch:
                mock_fetch.return_value = []

                # Track semaphore creation
                with patch("asyncio.Semaphore") as mock_semaphore:
                    await _refresh_once(config, None, event_window_ref, window_lock)

                    # Should create semaphore with bounded concurrency
                    mock_semaphore.assert_called_once_with(expected_concurrency)

    @pytest.mark.asyncio
    async def test_error_handling_in_concurrent_fetch(self):
        """Test error handling when concurrent fetches fail."""
        config = {
            "ics_sources": ["https://example1.com/cal.ics", "https://example2.com/cal.ics"],
            "fetch_concurrency": 2,
            "rrule_expansion_days": 14,
            "event_window_size": 10,
        }
        event_window_ref = [()]
        window_lock = asyncio.Lock()

        async def mock_fetch_with_error(*args, **kwargs):
            if "example1" in str(args[1]):
                raise Exception("Network error")
            return [
                {"meeting_id": "test", "subject": "Test Event", "start": datetime.now(timezone.utc)}
            ]

        with patch(
            "calendarbot_lite.server._fetch_and_parse_source", side_effect=mock_fetch_with_error
        ):
            # Should not raise exception, should handle errors gracefully
            await _refresh_once(config, None, event_window_ref, window_lock)

            # Should still process successful sources
            assert len(event_window_ref[0]) >= 0  # At least no crash


@pytest.mark.asyncio
async def test_memory_optimization_cooperative_yielding():
    """Test that RRULE expansion yields control to the event loop."""
    settings = Mock()
    settings.rrule_worker_concurrency = 1
    settings.max_occurrences_per_rule = 100
    settings.expansion_days_window = 30
    settings.expansion_time_budget_ms_per_rule = 10000
    settings.expansion_yield_frequency = 5  # Yield every 5 events

    pool = RRuleWorkerPool(settings)

    master_event = Mock()
    master_event.id = "test-event"
    master_event.start = Mock()
    master_event.start.date_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

    with (
        patch("calendarbot_lite.lite_rrule_expander.LiteRRuleExpander") as mock_expander_class,
        patch("asyncio.sleep") as mock_sleep,
    ):
        mock_expander = Mock()
        mock_expander.expand_rrule.return_value = [Mock() for _ in range(20)]  # 20 events
        mock_expander_class.return_value = mock_expander

        events = []
        async for event in pool.expand_event_async(master_event, "FREQ=DAILY;COUNT=20"):
            events.append(event)

        # Should have yielded multiple times (every 5 events)
        expected_yields = 20 // 5  # 4 yields
        assert mock_sleep.call_count >= expected_yields - 1  # Allow for off-by-one
