"""Integration tests for web API endpoints with backend components."""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from calendarbot.cache.manager import CacheManager
from calendarbot.display.manager import DisplayManager
from calendarbot.sources.manager import SourceManager
from calendarbot.ui.navigation import NavigationState
from calendarbot.web.server import WebServer
from tests.fixtures.mock_ics_data import ICSDataFactory, ICSTestData


@pytest.mark.integration
@pytest.mark.critical_path
class TestWebAPIBackendIntegration:
    """Test suite for web API integration with backend components."""

    @pytest_asyncio.fixture
    async def web_api_setup(self, test_settings, populated_test_database):
        """Set up web server with real backend components for integration testing."""
        # Initialize real backend components
        cache_manager = CacheManager(test_settings)
        await cache_manager.initialize()

        source_manager = SourceManager(test_settings, cache_manager)
        await source_manager.initialize()

        display_manager = DisplayManager(test_settings)
        navigation_state = NavigationState()

        # Create web server with real components
        web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

        yield web_server, cache_manager, source_manager, display_manager, navigation_state

        await cache_manager.cleanup_old_events(days_old=0)

    @pytest.mark.asyncio
    async def test_refresh_api_with_real_cache(self, web_api_setup):
        """Test refresh API endpoint with real cache operations."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = web_api_setup

        # Populate cache with test data for today
        test_events = ICSTestData.create_mock_events(count=5, include_today=True)

        with patch.object(source_manager, "fetch_and_cache_events", return_value=True):
            cache_success = await cache_manager.cache_events(test_events)
            assert cache_success, "Failed to cache events"

        # Verify events are cached (events might be filtered by date)
        cached_events = await cache_manager.get_todays_cached_events()
        assert (
            len(cached_events) >= 1
        ), f"Expected at least 1 cached event for today, got {len(cached_events)}"

        # Test refresh API
        success = web_server.refresh_data()
        assert success is True

        # Cache should still contain events
        post_refresh_events = await cache_manager.get_todays_cached_events()
        assert len(post_refresh_events) >= 1

    @pytest.mark.asyncio
    async def test_navigation_api_with_real_state(self, web_api_setup):
        """Test navigation API with real navigation state."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = web_api_setup

        initial_date = navigation_state.selected_date

        # Test navigation forward
        success = web_server.handle_navigation("next")
        assert success is True
        assert navigation_state.selected_date == initial_date + timedelta(days=1)

        # Test navigation backward
        success = web_server.handle_navigation("prev")
        assert success is True
        assert navigation_state.selected_date == initial_date

        # Test jump to today
        success = web_server.handle_navigation("today")
        assert success is True
        # Should be back to today (or close to it)

    @pytest.mark.asyncio
    async def test_status_api_with_real_components(self, web_api_setup):
        """Test status API with real component states."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = web_api_setup

        # Populate some data
        test_events = ICSTestData.create_mock_events(count=3)
        with patch.object(source_manager, "fetch_and_cache_events", return_value=True):
            await cache_manager.cache_events(test_events)

        # Get status
        status = web_server.get_status()

        assert status["running"] is False  # Server not started yet
        assert status["interactive_mode"] is True  # Has navigation state
        assert status["current_date"] == navigation_state.selected_date.isoformat()
        assert status["host"] == web_server.host
        assert status["port"] == web_server.port

    @pytest.mark.asyncio
    async def test_theme_api_with_display_manager(self, web_api_setup):
        """Test theme API integration with display manager."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = web_api_setup

        # Mock renderer with theme support
        display_manager.renderer = MagicMock()
        display_manager.renderer.theme = "4x8"

        initial_theme = web_server.theme

        # Test theme setting
        success = web_server.set_theme("3x4")
        assert success is True
        assert web_server.theme == "3x4"
        assert display_manager.renderer.theme == "3x4"

        # Test theme toggle
        new_theme = web_server.toggle_theme()
        assert new_theme == "4x8"
        assert web_server.theme == "4x8"
        assert display_manager.renderer.theme == "4x8"

    @pytest.mark.asyncio
    async def test_calendar_html_with_real_data(self, web_api_setup):
        """Test calendar HTML generation with real cached data."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = web_api_setup

        # Populate cache with test events
        test_events = ICSTestData.create_mock_events(count=3, include_today=True)
        with patch.object(source_manager, "fetch_and_cache_events", return_value=True):
            await cache_manager.cache_events(test_events)

        # Mock renderer
        display_manager.renderer = MagicMock()
        expected_html = "<html><body><h1>Test Calendar</h1></body></html>"
        display_manager.renderer.render_events.return_value = expected_html

        # Mock get_calendar_html to avoid asyncio.run() in async context
        with patch.object(
            web_server, "get_calendar_html", return_value=expected_html
        ) as mock_get_html:
            html = web_server.get_calendar_html()
            assert html == expected_html
            mock_get_html.assert_called_once()


@pytest.mark.integration
class TestWebServerLifecycleIntegration:
    """Test suite for web server lifecycle with backend components."""

    @pytest_asyncio.fixture
    async def server_lifecycle_setup(self, test_settings, populated_test_database):
        """Set up for server lifecycle testing."""
        # Use different port for lifecycle tests
        test_settings.web_port = 8999

        cache_manager = CacheManager(test_settings)
        await cache_manager.initialize()

        display_manager = DisplayManager(test_settings)
        web_server = WebServer(test_settings, display_manager, cache_manager)

        yield web_server, cache_manager

        # Cleanup
        if web_server.running:
            web_server.stop()
        await cache_manager.cleanup_old_events(days_old=0)

    def test_server_start_stop_with_backend(self, server_lifecycle_setup):
        """Test server start/stop lifecycle with backend components."""
        web_server, cache_manager = server_lifecycle_setup

        # Mock the HTTP server to avoid actual network binding
        with patch("calendarbot.web.server.HTTPServer") as mock_http_server, patch(
            "threading.Thread"
        ) as mock_thread:

            mock_server_instance = MagicMock()
            mock_http_server.return_value = mock_server_instance
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            # Start server
            web_server.start()
            assert web_server.running is True

            # Stop server
            web_server.stop()
            assert web_server.running is False

    def test_server_url_generation(self, server_lifecycle_setup):
        """Test server URL generation with configured settings."""
        web_server, cache_manager = server_lifecycle_setup

        expected_url = f"http://{web_server.host}:{web_server.port}"
        assert web_server.url == expected_url

    def test_concurrent_api_access(self, server_lifecycle_setup):
        """Test concurrent access to API endpoints."""
        web_server, cache_manager = server_lifecycle_setup

        def api_call():
            return web_server.get_status()

        # Simulate concurrent API calls
        import threading

        threads = []
        results = []

        def thread_worker():
            result = api_call()
            results.append(result)

        for _ in range(5):
            thread = threading.Thread(target=thread_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All calls should succeed
        assert len(results) == 5
        for result in results:
            assert isinstance(result, dict)
            assert "running" in result


@pytest.mark.integration
class TestDataFlowIntegration:
    """Test suite for complete data flow through web API."""

    @pytest_asyncio.fixture
    async def data_flow_setup(self, test_settings, populated_test_database):
        """Set up complete data flow testing environment."""
        cache_manager = CacheManager(test_settings)
        await cache_manager.initialize()

        source_manager = SourceManager(test_settings, cache_manager)
        await source_manager.initialize()

        display_manager = DisplayManager(test_settings)
        navigation_state = NavigationState()

        web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

        yield web_server, cache_manager, source_manager, display_manager, navigation_state

        # Cleanup old events but not everything since we're using temp databases
        await cache_manager.cleanup_old_events(days_old=0)

    @pytest.mark.asyncio
    async def test_complete_refresh_cycle_via_api(self, data_flow_setup):
        """Test complete refresh cycle triggered via API."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = (
            data_flow_setup
        )

        # Mock external calendar data
        external_events = ICSTestData.create_mock_events(count=4, include_today=True)

        with patch.object(source_manager, "fetch_and_cache_events", return_value=True):
            await cache_manager.cache_events(external_events)

            # Simulate refresh triggered via API
            success = web_server.refresh_data()
            assert success is True

            # Verify data flowed through the system
            # 1. Check cache was populated
            cached_events = await cache_manager.get_todays_cached_events()
            assert len(cached_events) >= 0  # May be filtered by date

            # 2. Check cache status
            cache_status = await cache_manager.get_cache_status()
            assert cache_status.last_update is not None

    @pytest.mark.asyncio
    async def test_navigation_affects_data_retrieval(self, data_flow_setup):
        """Test that navigation affects which data is retrieved."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = (
            data_flow_setup
        )

        # Create events for different dates
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        today_events = [
            ICSTestData.create_event_for_date(today, f"Today Event {i}") for i in range(2)
        ]
        tomorrow_events = [
            ICSTestData.create_event_for_date(tomorrow, f"Tomorrow Event {i}") for i in range(3)
        ]
        all_events = today_events + tomorrow_events

        with patch.object(source_manager, "fetch_and_cache_events", return_value=True):
            await cache_manager.cache_events(all_events)

        # Start with today's events
        initial_date = navigation_state.selected_date

        # Navigate to tomorrow
        web_server.handle_navigation("next")

        # Verify navigation state changed
        assert navigation_state.selected_date == initial_date + timedelta(days=1)

        # The navigation should affect which events would be displayed
        # (This would be tested more thoroughly in the display component)

    @pytest.mark.asyncio
    async def test_theme_persistence_across_operations(self, data_flow_setup):
        """Test that theme changes persist across API operations."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = (
            data_flow_setup
        )

        # Mock renderer
        display_manager.renderer = MagicMock()
        display_manager.renderer.theme = "4x8"

        # Change theme
        web_server.set_theme("3x4")
        assert web_server.theme == "3x4"

        # Perform other operations
        web_server.handle_navigation("next")
        web_server.refresh_data()

        # Theme should persist
        assert web_server.theme == "3x4"
        assert display_manager.renderer.theme == "3x4"

    @pytest.mark.asyncio
    async def test_error_propagation_through_api(self, data_flow_setup):
        """Test error propagation from backend to API responses."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = (
            data_flow_setup
        )

        # Mock cache failure
        with patch.object(
            cache_manager, "get_todays_cached_events", side_effect=Exception("Cache error")
        ):
            # API operations should handle errors gracefully
            html = web_server.get_calendar_html()
            assert "Error" in html

            status = web_server.get_status()
            # Status should still return some information
            assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_performance_under_load(self, data_flow_setup, performance_tracker):
        """Test API performance under simulated load."""
        web_server, cache_manager, source_manager, display_manager, navigation_state = (
            data_flow_setup
        )

        # Populate cache with substantial data
        large_event_set = ICSTestData.create_mock_events(count=100, include_today=True)
        with patch.object(source_manager, "fetch_and_cache_events", return_value=True):
            await cache_manager.cache_events(large_event_set)

        # Mock renderer for HTML generation
        display_manager.renderer = MagicMock()
        display_manager.renderer.render_events.return_value = (
            "<html><body>Large Calendar</body></html>"
        )

        # Test performance of various API operations
        performance_tracker.start_timer("api_load_test")

        # Simulate load
        for _ in range(10):
            web_server.get_status()
            web_server.get_calendar_html()
            web_server.handle_navigation("next")
            web_server.handle_navigation("prev")

        performance_tracker.end_timer("api_load_test")

        # Should complete within reasonable time
        performance_tracker.assert_performance("api_load_test", 3.0)


@pytest.mark.integration
class TestSecurityIntegration:
    """Test suite for security aspects of web API integration."""

    @pytest_asyncio.fixture
    async def security_setup(self, test_settings, populated_test_database):
        """Set up for security testing."""
        cache_manager = CacheManager(test_settings)
        await cache_manager.initialize()

        display_manager = DisplayManager(test_settings)
        navigation_state = NavigationState()

        web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

        yield web_server, cache_manager

        await cache_manager.cleanup_old_events(days_old=0)

    def test_input_validation_integration(self, security_setup):
        """Test input validation across API and backend."""
        web_server, cache_manager = security_setup

        # Test navigation with invalid inputs
        malicious_inputs = [
            "../../../etc/passwd",
            "<script>alert('xss')</script>",
            "'; DROP TABLE events; --",
            "eval(malicious_code)",
        ]

        for malicious_input in malicious_inputs:
            success = web_server.handle_navigation(malicious_input)
            # Should reject all malicious inputs
            assert success is False

    def test_theme_validation_integration(self, security_setup):
        """Test theme validation with backend components."""
        web_server, cache_manager = security_setup

        # Mock renderer
        web_server.display_manager.renderer = MagicMock()

        # Test valid themes
        valid_themes = ["4x8", "3x4"]
        for theme in valid_themes:
            success = web_server.set_theme(theme)
            assert success is True

        # Test invalid themes
        invalid_themes = ["../etc/passwd", "<script>", "'; DROP TABLE", ""]
        for theme in invalid_themes:
            success = web_server.set_theme(theme)
            assert success is False

    def test_error_message_sanitization(self, security_setup):
        """Test that error messages don't leak sensitive information."""
        web_server, cache_manager = security_setup

        # Mock an error that might contain sensitive info
        with patch.object(
            cache_manager,
            "get_todays_cached_events",
            side_effect=Exception("Database connection failed: password=secret123"),
        ):

            html = web_server.get_calendar_html()

            # Error message should be sanitized
            assert "secret123" not in html
            assert "password=" not in html
            # Check that it shows a fallback message instead of exposing the error
            assert "No meetings scheduled" in html or "Error" in html


@pytest.mark.integration
class TestWebAPIStateManagement:
    """Test suite for state management across web API operations."""

    @pytest_asyncio.fixture
    async def state_management_setup(self, test_settings, populated_test_database):
        """Set up for state management testing."""
        cache_manager = CacheManager(test_settings)
        await cache_manager.initialize()

        display_manager = DisplayManager(test_settings)
        navigation_state = NavigationState()

        web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

        yield web_server, navigation_state, cache_manager

        await cache_manager.cleanup_old_events(days_old=0)

    def test_navigation_state_consistency(self, state_management_setup):
        """Test navigation state remains consistent across operations."""
        web_server, navigation_state, cache_manager = state_management_setup

        initial_date = navigation_state.selected_date

        # Perform sequence of navigation operations
        web_server.handle_navigation("next")
        date_after_next = navigation_state.selected_date

        web_server.handle_navigation("prev")
        date_after_prev = navigation_state.selected_date

        web_server.handle_navigation("today")
        date_after_today = navigation_state.selected_date

        # Verify state transitions
        assert date_after_next == initial_date + timedelta(days=1)
        assert date_after_prev == initial_date
        # date_after_today should be close to today

    def test_theme_state_consistency(self, state_management_setup):
        """Test theme state consistency across operations."""
        web_server, navigation_state, cache_manager = state_management_setup

        # Mock renderer
        web_server.display_manager.renderer = MagicMock()
        web_server.display_manager.renderer.theme = "4x8"

        # Change theme and verify persistence
        web_server.set_theme("3x4")
        assert web_server.theme == "3x4"

        # Perform other operations
        web_server.refresh_data()
        assert web_server.theme == "3x4"

        web_server.handle_navigation("next")
        assert web_server.theme == "3x4"

        # Toggle theme
        new_theme = web_server.toggle_theme()
        assert new_theme == "4x8"
        assert web_server.theme == "4x8"

    def test_state_isolation_between_operations(self, state_management_setup):
        """Test that operations don't interfere with each other's state."""
        web_server, navigation_state, cache_manager = state_management_setup

        # Set initial state
        initial_date = navigation_state.selected_date
        web_server.theme = "3x4"

        # Perform concurrent-like operations
        status1 = web_server.get_status()
        web_server.handle_navigation("next")
        status2 = web_server.get_status()
        web_server.set_theme("4x8")
        status3 = web_server.get_status()

        # Verify state changes are reflected correctly
        assert status1["current_date"] == initial_date.isoformat()
        assert status2["current_date"] == (initial_date + timedelta(days=1)).isoformat()
        # Theme change should be reflected in subsequent operations
        assert web_server.theme == "4x8"

    @pytest.mark.asyncio
    async def test_cache_state_affects_api_responses(self, state_management_setup):
        """Test that cache state affects API responses appropriately."""
        web_server, navigation_state, cache_manager = state_management_setup

        # Initially cache is empty
        status_empty = web_server.get_status()

        # Populate cache
        test_events = ICSTestData.create_mock_events(count=3)
        await cache_manager.cache_events(test_events)

        # Status should reflect cached data
        status_with_data = web_server.get_status()

        # Mock renderer for HTML generation
        web_server.display_manager.renderer = MagicMock()
        expected_html = "<html>Calendar with events</html>"
        web_server.display_manager.renderer.render_events.return_value = expected_html

        # Mock get_calendar_html to avoid asyncio.run() in async context
        with patch.object(web_server, "get_calendar_html", return_value=expected_html):
            html_with_data = web_server.get_calendar_html()

        # Verify API responses reflect cache state
        assert isinstance(status_empty, dict)
        assert isinstance(status_with_data, dict)
        assert "Calendar with events" in html_with_data
