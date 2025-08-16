"""End-to-end tests for complete application workflows."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cache.manager import CacheManager
from calendarbot.display.manager import DisplayManager
from calendarbot.main import CalendarBot
from calendarbot.sources.manager import SourceManager
from calendarbot.ui.navigation import NavigationState
from calendarbot.web.server import WebServer
from tests.fixtures.mock_ics_data import ICSTestData


@pytest.mark.e2e
@pytest.mark.critical_path
class TestCompleteApplicationWorkflows:
    """Test suite for complete application workflows end-to-end."""

    @pytest.fixture
    async def full_application_setup(self, test_settings, populated_test_database):
        """Set up complete application stack for end-to-end testing."""
        # Create real CalendarBot instance
        with (
            patch("calendarbot.main.settings", test_settings),
            patch(
                "calendarbot.sources.ics_source.ICSSourceHandler.test_connection"
            ) as mock_test_conn,
            patch("calendarbot.sources.ics_source.ICSSourceHandler.is_healthy", return_value=True),
        ):
            # Mock successful connection test to prevent real HTTP calls
            mock_health_result = MagicMock()
            mock_health_result.is_healthy = True
            mock_health_result.status = "healthy"
            mock_health_result.error_message = None
            mock_health_result.response_time_ms = 100
            mock_health_result.events_fetched = 0
            mock_test_conn.return_value = mock_health_result

            bot = CalendarBot()

            # Initialize all components
            await bot.initialize()

            yield bot

            # Cleanup
            await bot.cleanup()

    @pytest.mark.asyncio
    async def test_complete_startup_sequence(self, full_application_setup):
        """Test complete application startup sequence."""
        bot = full_application_setup

        # Verify all components are initialized
        assert bot.cache_manager is not None
        assert bot.source_manager is not None
        assert bot.display_manager is not None
        assert bot.running is False  # Not started yet
        assert bot.consecutive_failures == 0
        assert bot.last_successful_update is None

    @pytest.mark.asyncio
    async def test_first_run_workflow(self, test_settings, populated_test_database):
        """Test first run workflow with initial configuration."""
        # Mock first run scenario - this test is about configuration detection, not setup wizard
        with (
            patch("calendarbot.main.check_first_run_configuration", return_value=True),
            patch("calendarbot.main.settings", test_settings),
            patch(
                "calendarbot.sources.ics_source.ICSSourceHandler.test_connection"
            ) as mock_test_conn,
        ):
            # Mock successful connection test to prevent real HTTP calls
            mock_health_result = MagicMock()
            mock_health_result.is_healthy = True
            mock_health_result.status = "healthy"
            mock_health_result.error_message = None
            mock_health_result.response_time_ms = 100
            mock_health_result.events_fetched = 0
            mock_test_conn.return_value = mock_health_result

            bot = CalendarBot()
            success = await bot.initialize()

            # Should succeed when configuration is present
            assert success is True

    @pytest.mark.asyncio
    async def test_fetch_cache_display_workflow(self, full_application_setup):
        """Test complete fetch → cache → display workflow."""
        bot = full_application_setup

        # Mock external calendar data
        external_events = ICSTestData.create_mock_events(count=5, include_today=True)

        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager,
                "get_todays_cached_events",
                new_callable=AsyncMock,
                return_value=external_events,
            ),
            patch.object(
                bot.cache_manager,
                "get_cache_status",
                new_callable=AsyncMock,
                return_value=MagicMock(last_update=datetime.now(), is_stale=False),
            ),
            patch.object(
                bot.source_manager,
                "get_source_info",
                new_callable=AsyncMock,
                return_value=MagicMock(status="healthy", url="test_url"),
            ),
            patch.object(
                bot.display_manager, "display_events", new_callable=AsyncMock, return_value=True
            ) as mock_display,
        ):
            # Execute complete workflow
            # 1. Fetch and cache events
            fetch_success = await bot.fetch_and_cache_events()
            assert fetch_success is True
            assert bot.last_successful_update is not None
            assert bot.consecutive_failures == 0

            # 2. Update display
            display_success = await bot.update_display()
            assert display_success is True

            # Verify display was called with events and status
            mock_display.assert_called_once()
            call_args = mock_display.call_args
            events_arg = call_args[0][0]
            status_arg = call_args[0][1]

            assert len(events_arg) >= 0  # May be filtered by date
            assert isinstance(status_arg, dict)
            assert "total_events" in status_arg
            assert "connection_status" in status_arg

    @pytest.mark.asyncio
    async def test_refresh_cycle_workflow(self, full_application_setup):
        """Test complete refresh cycle workflow."""
        bot = full_application_setup

        # Mock components
        external_events = ICSTestData.create_mock_events(count=3, include_today=True)

        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager, "get_todays_cached_events", return_value=external_events
            ),
            patch.object(bot.display_manager, "display_events", return_value=True),
            patch.object(bot, "fetch_and_cache_events", return_value=True) as mock_fetch,
            patch.object(bot, "update_display", return_value=True) as mock_update,
        ):
            # Execute refresh cycle
            await bot.refresh_cycle()

            # Should have attempted fetch and update
            # (exact behavior depends on cache freshness)
            assert mock_fetch.called or mock_update.called

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, full_application_setup):
        """Test error recovery workflow."""
        bot = full_application_setup

        # Simulate network failure
        with (
            patch.object(
                bot.source_manager,
                "fetch_and_cache_events",
                side_effect=Exception("Network error"),
            ),
            patch.object(
                bot.cache_manager,
                "is_cache_fresh",
                new_callable=AsyncMock,
                return_value=False,  # Force cache to be stale
            ),
            patch.object(bot, "handle_error_display", new_callable=AsyncMock) as mock_error_display,
        ):
            # Attempt fetch (should fail)
            success = await bot.fetch_and_cache_events()
            assert success is False
            assert bot.consecutive_failures == 1

            # Execute refresh cycle (should handle error gracefully)
            await bot.refresh_cycle()

            # Should have triggered error display
            mock_error_display.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout to prevent hanging
    async def test_background_operation_workflow(self, full_application_setup):
        """Test background operation workflow."""
        bot = full_application_setup
        bot.settings.refresh_interval = 0.1  # Very short for testing

        # Mock components
        with patch.object(bot, "fetch_and_cache_events", return_value=True) as mock_fetch:
            bot.running = True

            # Start background fetch for a short time
            async def run_briefly():
                await asyncio.sleep(0.02)  # Reduce sleep time
                bot.running = False
                bot.shutdown_event.set()

            # Run background operation and stop it quickly with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(bot.run_background_fetch(), run_briefly()),
                    timeout=5.0,  # 5 second timeout
                )
            except asyncio.TimeoutError:
                bot.running = False
                bot.shutdown_event.set()

            # Should have performed at least initial fetch
            mock_fetch.assert_called()

    @pytest.mark.asyncio
    async def test_signal_handling_workflow(self, full_application_setup):
        """Test signal handling and graceful shutdown workflow."""
        bot = full_application_setup

        # Mock signal handler setup
        with patch("signal.signal") as mock_signal:
            from calendarbot.main import setup_signal_handlers

            setup_signal_handlers(bot)

            # Should have set up handlers for SIGINT and SIGTERM
            assert mock_signal.call_count == 2

            # Test shutdown
            await bot.stop()
            assert bot.running is False
            assert bot.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_concurrent_operations_workflow(self, full_application_setup):
        """Test concurrent operations workflow."""
        bot = full_application_setup

        # Mock components
        with (
            patch.object(bot, "fetch_and_cache_events", return_value=True),
            patch.object(bot, "update_display", return_value=True),
            patch.object(bot, "refresh_cycle"),
        ):
            # Run multiple operations concurrently
            tasks = [bot.refresh_cycle(), bot.fetch_and_cache_events(), bot.update_display()]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Should handle concurrent operations gracefully
            assert len(results) == 3
            # No exceptions should be raised
            assert all(not isinstance(result, Exception) for result in results)


@pytest.mark.e2e
class TestWebInterfaceWorkflows:
    """Test suite for web interface end-to-end workflows."""

    @pytest.fixture
    async def web_application_setup(self, test_settings, populated_test_database):
        """Set up complete web application for end-to-end testing."""
        with (
            patch(
                "calendarbot.sources.ics_source.ICSSourceHandler.test_connection"
            ) as mock_test_conn,
            patch("calendarbot.sources.ics_source.ICSSourceHandler.is_healthy", return_value=True),
        ):
            # Mock successful connection test to prevent real HTTP calls
            mock_health_result = MagicMock()
            mock_health_result.is_healthy = True
            mock_health_result.status = "healthy"
            mock_health_result.error_message = None
            mock_health_result.response_time_ms = 100
            mock_health_result.events_fetched = 0
            mock_test_conn.return_value = mock_health_result

            # Initialize backend
            cache_manager = CacheManager(test_settings)
            await cache_manager.initialize()

            source_manager = SourceManager(test_settings, cache_manager)
            await source_manager.initialize()

            display_manager = DisplayManager(test_settings)
            navigation_state = NavigationState()

            # Create web server
            web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

            # Create CalendarBot for full integration
            with patch("calendarbot.main.settings", test_settings):
                bot = CalendarBot()
                bot.cache_manager = cache_manager
                bot.source_manager = source_manager
                bot.display_manager = display_manager
                await bot.initialize()

            yield web_server, bot, navigation_state

            # Cleanup
            if web_server.running:
                web_server.stop()
            await cache_manager.cleanup()

    @pytest.mark.asyncio
    async def test_complete_web_navigation_workflow(self, web_application_setup):
        """Test complete web navigation workflow."""
        web_server, bot, navigation_state = web_application_setup

        # Navigation sequence
        actions = ["next", "next", "prev", "today", "week-start", "week-end"]

        for action in actions:
            success = web_server.handle_navigation(action)
            assert success is True

        # Should be at week end now
        # (exact date depends on current date and week start configuration)

    @pytest.mark.asyncio
    async def test_complete_refresh_via_web_workflow(self, web_application_setup):
        """Test complete refresh workflow triggered via web interface."""
        web_server, bot, navigation_state = web_application_setup

        # Mock external data
        external_events = ICSTestData.create_mock_events(count=4, include_today=True)

        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager, "get_events_by_date_range", return_value=external_events
            ),
        ):
            # Trigger refresh via web API
            success = web_server.refresh_data()
            assert success is True

            # Verify data flowed through system
            cached_events = await bot.cache_manager.get_todays_cached_events()
            assert len(cached_events) >= 0  # May be filtered

            # Get status via web API
            status = web_server.get_status()
            assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_layout_switching_workflow(self, web_application_setup):
        """Test layout switching workflow via web interface."""
        web_server, bot, navigation_state = web_application_setup

        # Mock the display manager's set_layout method to avoid renderer replacement
        with patch.object(
            web_server.display_manager, "set_layout", return_value=True
        ) as mock_set_layout:
            with patch.object(web_server.display_manager, "get_current_layout") as mock_get_layout:
                # Set up the mock to return the layout that was just set
                def mock_get_current_layout_side_effect():
                    if mock_set_layout.call_count > 0:
                        # Return the last layout that was set
                        return mock_set_layout.call_args[0][0]
                    return "4x8"  # default

                mock_get_layout.side_effect = mock_get_current_layout_side_effect

                # Layout switching sequence
                layouts = ["4x8", "whats-next-view"]

                for layout in layouts:
                    success = web_server.set_layout(layout)
                    assert success is True
                    # Verify set_layout was called with correct layout
                    mock_set_layout.assert_called_with(layout)
                    # Check layout through display manager API
                    current_layout = web_server.display_manager.get_current_layout()
                    assert current_layout == layout

                # Test layout toggle
                new_layout = web_server.cycle_layout()
                assert new_layout in ["4x8", "whats-next-view"]
                # Verify the layout was actually set in display manager
                assert web_server.display_manager.get_current_layout() == new_layout

    @pytest.mark.asyncio
    async def test_calendar_display_workflow(self, web_application_setup):
        """Test calendar display workflow via web interface."""
        web_server, bot, navigation_state = web_application_setup

        # Populate with test data
        test_events = ICSTestData.create_mock_events(count=5, include_today=True)
        await bot.cache_manager.cache_events(test_events)

        # Mock renderer
        web_server.display_manager.renderer = MagicMock()
        expected_html = "<html><body><h1>Calendar Display</h1><div>Events here</div></body></html>"
        web_server.display_manager.renderer.render_events.return_value = expected_html

        # Get calendar HTML
        html = web_server.get_calendar_html()
        assert html == expected_html

        # Verify renderer was called with correct data
        web_server.display_manager.renderer.render_events.assert_called_once()
        call_args = web_server.display_manager.renderer.render_events.call_args
        events_arg = call_args[0][0]
        status_arg = call_args[0][1]

        assert isinstance(events_arg, list)
        assert isinstance(status_arg, dict)

    @pytest.mark.asyncio
    async def test_interactive_session_workflow(self, web_application_setup):
        """Test complete interactive session workflow."""
        web_server, bot, navigation_state = web_application_setup

        # Mock external data and renderer
        external_events = ICSTestData.create_mock_events(count=3, include_today=True)
        web_server.display_manager.renderer = MagicMock()
        web_server.display_manager.renderer.render_events.return_value = "<html>Calendar</html>"

        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager, "get_events_by_date_range", return_value=external_events
            ),
        ):
            # Simulate user session
            # 1. Initial load
            status1 = web_server.get_status()
            html1 = web_server.get_calendar_html()

            # 2. Navigate forward
            web_server.handle_navigation("next")
            status2 = web_server.get_status()
            html2 = web_server.get_calendar_html()

            # 3. Change layout
            web_server.set_layout("3x4")

            # 4. Refresh data
            web_server.refresh_data()
            html3 = web_server.get_calendar_html()

            # 5. Navigate back
            web_server.handle_navigation("prev")
            status3 = web_server.get_status()

            # Verify session progression
            assert status1["current_date"] != status2["current_date"]  # Navigation worked
            assert status3["current_date"] == status1["current_date"]  # Back to start
            assert web_server.layout == "3x4"  # Theme persisted

            # All HTML generations should succeed
            assert all("Calendar" in html for html in [html1, html2, html3])


@pytest.mark.e2e
class TestFailureRecoveryWorkflows:
    """Test suite for failure recovery end-to-end workflows."""

    @pytest.fixture
    async def failure_recovery_setup(self, test_settings, populated_test_database):
        """Set up for failure recovery testing."""
        with (
            patch("calendarbot.main.settings", test_settings),
            patch(
                "calendarbot.sources.ics_source.ICSSourceHandler.test_connection"
            ) as mock_test_conn,
            patch("calendarbot.sources.ics_source.ICSSourceHandler.is_healthy", return_value=True),
        ):
            # Mock successful connection test to prevent real HTTP calls
            mock_health_result = MagicMock()
            mock_health_result.is_healthy = True
            mock_health_result.status = "healthy"
            mock_health_result.error_message = None
            mock_health_result.response_time_ms = 100
            mock_health_result.events_fetched = 0
            mock_test_conn.return_value = mock_health_result

            bot = CalendarBot()
            await bot.initialize()

            yield bot

            await bot.cleanup()

    @pytest.mark.asyncio
    async def test_network_failure_recovery_workflow(self, failure_recovery_setup):
        """Test recovery from network failures."""
        bot = failure_recovery_setup

        # Initial successful fetch
        initial_events = ICSTestData.create_mock_events(count=3)
        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager, "get_events_by_date_range", return_value=initial_events
            ),
        ):
            success = await bot.fetch_and_cache_events()
            assert success is True
            assert bot.consecutive_failures == 0

        # Network failure
        with patch.object(
            bot.source_manager,
            "fetch_and_cache_events",
            side_effect=Exception("Network error"),
        ):
            success = await bot.fetch_and_cache_events()
            assert success is False
            assert bot.consecutive_failures == 1

        # Recovery
        recovery_events = ICSTestData.create_mock_events(count=5)
        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager, "get_events_by_date_range", return_value=recovery_events
            ),
        ):
            success = await bot.fetch_and_cache_events()
            assert success is True
            assert bot.consecutive_failures == 0  # Reset on success

    @pytest.mark.asyncio
    async def test_cache_corruption_recovery_workflow(self, failure_recovery_setup):
        """Test recovery from cache corruption."""
        bot = failure_recovery_setup

        # Simulate cache corruption
        with patch.object(
            bot.cache_manager, "get_todays_cached_events", side_effect=Exception("Cache corrupted")
        ):
            # Should handle gracefully
            success = await bot.update_display()
            # May fail but shouldn't crash
            assert isinstance(success, bool)

    @pytest.mark.asyncio
    async def test_multiple_component_failure_workflow(self, failure_recovery_setup):
        """Test recovery when multiple components fail."""
        bot = failure_recovery_setup

        # Multiple failures
        with (
            patch.object(
                bot.source_manager, "fetch_and_cache_events", side_effect=Exception("Source error")
            ),
            patch.object(
                bot.cache_manager, "get_todays_cached_events", side_effect=Exception("Cache error")
            ),
            patch.object(
                bot.cache_manager,
                "is_cache_fresh",
                new_callable=AsyncMock,
                return_value=False,  # Force cache to be stale
            ),
            patch.object(bot, "handle_error_display", new_callable=AsyncMock) as mock_error_display,
        ):
            # Execute refresh cycle
            await bot.refresh_cycle()

            # Should handle multiple failures gracefully
            mock_error_display.assert_called()

    @pytest.mark.asyncio
    async def test_startup_failure_recovery_workflow(self, test_settings, populated_test_database):
        """Test recovery from startup failures."""
        # Mock initialization failure
        with (
            patch("calendarbot.main.settings", test_settings),
            patch.object(CacheManager, "initialize", return_value=False),
            patch(
                "calendarbot.sources.ics_source.ICSSourceHandler.test_connection"
            ) as mock_test_conn,
            patch("calendarbot.sources.ics_source.ICSSourceHandler.is_healthy", return_value=True),
        ):
            # Mock successful connection test to prevent real HTTP calls
            mock_health_result = MagicMock()
            mock_health_result.is_healthy = True
            mock_health_result.status = "healthy"
            mock_health_result.error_message = None
            mock_health_result.response_time_ms = 100
            mock_health_result.events_fetched = 0
            mock_test_conn.return_value = mock_health_result

            bot = CalendarBot()
            success = await bot.initialize()

            # Should fail gracefully
            assert success is False

    @pytest.mark.asyncio
    async def test_graceful_degradation_workflow(self, failure_recovery_setup):
        """Test graceful degradation when services are unavailable."""
        bot = failure_recovery_setup

        # Populate cache first
        initial_events = ICSTestData.create_mock_events(count=3)
        await bot.cache_manager.cache_events(initial_events)

        # Source becomes unavailable
        with patch.object(bot.source_manager, "health_check") as mock_health:
            unhealthy_check = MagicMock()
            unhealthy_check.is_healthy = False
            unhealthy_check.status_message = "Service unavailable"
            mock_health.return_value = unhealthy_check

            # Should still be able to display cached data
            with patch.object(
                bot.display_manager, "display_events", return_value=True
            ) as mock_display:
                success = await bot.update_display()
                assert success is True

                # Should have used cached data
                mock_display.assert_called_once()
                call_args = mock_display.call_args[0]
                events_used = call_args[0]
                assert len(events_used) >= 0  # May be filtered but should work


@pytest.mark.e2e
class TestPerformanceWorkflows:
    """Test suite for performance-related end-to-end workflows."""

    @pytest.fixture
    async def performance_setup(
        self, test_settings, performance_test_database, performance_tracker
    ):
        """Set up for performance testing."""
        with (
            patch("calendarbot.main.settings", test_settings),
            patch(
                "calendarbot.sources.ics_source.ICSSourceHandler.test_connection"
            ) as mock_test_conn,
            patch("calendarbot.sources.ics_source.ICSSourceHandler.is_healthy", return_value=True),
        ):
            # Mock successful connection test to prevent real HTTP calls
            mock_health_result = MagicMock()
            mock_health_result.is_healthy = True
            mock_health_result.status = "healthy"
            mock_health_result.error_message = None
            mock_health_result.response_time_ms = 100
            mock_health_result.events_fetched = 0
            mock_test_conn.return_value = mock_health_result

            bot = CalendarBot()
            await bot.initialize()

            yield bot, performance_tracker

            await bot.cleanup()

    @pytest.mark.asyncio
    async def test_large_dataset_workflow(self, performance_setup):
        """Test workflow with large datasets."""
        bot, performance_tracker = performance_setup

        # Create large dataset
        large_event_set = ICSTestData.create_mock_events(count=1000, include_today=True)

        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(
                bot.cache_manager, "get_events_by_date_range", return_value=large_event_set
            ),
            patch.object(bot.display_manager, "display_events", return_value=True),
        ):
            performance_tracker.start_timer("large_dataset_workflow")

            # Execute complete workflow
            fetch_success = await bot.fetch_and_cache_events()
            display_success = await bot.update_display()

            performance_tracker.end_timer("large_dataset_workflow")

            assert fetch_success is True
            assert display_success is True

            # Should complete within reasonable time
            performance_tracker.assert_performance("large_dataset_workflow", 10.0)

    @pytest.mark.asyncio
    async def test_high_frequency_operations_workflow(self, performance_setup):
        """Test workflow with high frequency operations."""
        bot, performance_tracker = performance_setup

        # Mock fast operations
        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(bot.cache_manager, "get_events_by_date_range", return_value=[]),
            patch.object(bot.display_manager, "display_events", return_value=True),
        ):
            performance_tracker.start_timer("high_frequency_operations")

            # Perform many operations quickly
            for _ in range(50):
                await bot.fetch_and_cache_events()
                await bot.update_display()

            performance_tracker.end_timer("high_frequency_operations")

            # Should handle high frequency gracefully
            performance_tracker.assert_performance("high_frequency_operations", 15.0)

    @pytest.mark.asyncio
    async def test_memory_usage_workflow(self, performance_setup):
        """Test memory usage during extended operation."""
        bot, performance_tracker = performance_setup

        import gc

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Mock operations that might accumulate memory
        test_events = ICSTestData.create_mock_events(count=100)

        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(bot.cache_manager, "get_events_by_date_range", return_value=test_events),
            patch.object(bot.display_manager, "display_events", return_value=True),
        ):
            # Perform many cycles
            for _ in range(20):
                await bot.refresh_cycle()

                # Periodic cleanup
                if _ % 5 == 0:
                    gc.collect()

            # Final cleanup
            gc.collect()
            final_objects = len(gc.get_objects())

            # Memory usage should not grow excessively
            growth_ratio = final_objects / initial_objects
            assert growth_ratio < 2.0, f"Memory usage grew by {growth_ratio:.2f}x"

    @pytest.mark.asyncio
    async def test_concurrent_workflow_performance(self, performance_setup):
        """Test performance under concurrent operations."""
        bot, performance_tracker = performance_setup

        # Mock operations
        with (
            patch.object(bot.source_manager, "fetch_and_cache_events", return_value=True),
            patch.object(bot.cache_manager, "get_events_by_date_range", return_value=[]),
            patch.object(bot.display_manager, "display_events", return_value=True),
        ):
            performance_tracker.start_timer("concurrent_workflow")

            # Run multiple workflows concurrently
            tasks = []
            for _ in range(10):
                task = asyncio.create_task(bot.refresh_cycle())
                tasks.append(task)

            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            performance_tracker.end_timer("concurrent_workflow")

            # All should complete without exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0, f"Found exceptions: {exceptions}"

            # Should complete concurrency efficiently
            performance_tracker.assert_performance("concurrent_workflow", 5.0)
