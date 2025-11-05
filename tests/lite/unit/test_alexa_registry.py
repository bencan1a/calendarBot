"""Tests for Alexa handler registry."""

from __future__ import annotations

import pytest

from calendarbot_lite.alexa.alexa_handlers import (
    DoneForDayHandler,
    LaunchSummaryHandler,
    MorningSummaryHandler,
    NextMeetingHandler,
    TimeUntilHandler,
)
from calendarbot_lite.alexa.alexa_registry import (
    AlexaHandlerRegistry,
    HandlerInfo,
    get_handler_info_summary,
)

pytestmark = pytest.mark.unit


class TestAlexaHandlerRegistry:
    """Test Alexa handler registry functionality."""

    @pytest.mark.smoke  # Critical path: Alexa handler registry validation
    def test_handlers_are_registered(self):
        """Test that all handlers are registered."""
        handlers = AlexaHandlerRegistry.get_handlers()

        # Verify all 5 handlers are registered
        assert len(handlers) >= 5

        # Verify specific handlers
        assert "GetNextMeetingIntent" in handlers
        assert "GetTimeUntilNextMeetingIntent" in handlers
        assert "GetDoneForDayIntent" in handlers
        assert "LaunchIntent" in handlers
        assert "GetMorningSummaryIntent" in handlers

    def test_handler_info_structure(self):
        """Test HandlerInfo contains expected fields."""
        handler = AlexaHandlerRegistry.get_handler("GetNextMeetingIntent")
        assert handler is not None
        assert isinstance(handler, HandlerInfo)

        # Check required fields
        assert handler.intent == "GetNextMeetingIntent"
        assert handler.route == "/api/alexa/next-meeting"
        assert handler.handler_class == NextMeetingHandler
        assert isinstance(handler.description, str)
        assert len(handler.description) > 0

        # Check boolean flags
        assert isinstance(handler.ssml_enabled, bool)
        assert isinstance(handler.cache_enabled, bool)
        assert isinstance(handler.precompute_enabled, bool)

    def test_next_meeting_handler_registration(self):
        """Test NextMeetingHandler registration details."""
        handler = AlexaHandlerRegistry.get_handler("GetNextMeetingIntent")
        assert handler is not None
        assert handler.route == "/api/alexa/next-meeting"
        assert handler.handler_class == NextMeetingHandler
        assert handler.ssml_enabled is True
        assert handler.cache_enabled is True
        assert handler.precompute_enabled is True

    def test_time_until_handler_registration(self):
        """Test TimeUntilHandler registration details."""
        handler = AlexaHandlerRegistry.get_handler("GetTimeUntilNextMeetingIntent")
        assert handler is not None
        assert handler.route == "/api/alexa/time-until-next"
        assert handler.handler_class == TimeUntilHandler
        assert handler.ssml_enabled is True
        assert handler.precompute_enabled is True

    def test_done_for_day_handler_registration(self):
        """Test DoneForDayHandler registration details."""
        handler = AlexaHandlerRegistry.get_handler("GetDoneForDayIntent")
        assert handler is not None
        assert handler.route == "/api/alexa/done-for-day"
        assert handler.handler_class == DoneForDayHandler
        assert handler.ssml_enabled is True
        assert handler.precompute_enabled is True

    def test_launch_summary_handler_registration(self):
        """Test LaunchSummaryHandler registration details."""
        handler = AlexaHandlerRegistry.get_handler("LaunchIntent")
        assert handler is not None
        assert handler.route == "/api/alexa/launch-summary"
        assert handler.handler_class == LaunchSummaryHandler
        assert handler.ssml_enabled is True
        assert handler.precompute_enabled is False  # Combines multiple sources

    def test_morning_summary_handler_registration(self):
        """Test MorningSummaryHandler registration details."""
        handler = AlexaHandlerRegistry.get_handler("GetMorningSummaryIntent")
        assert handler is not None
        assert handler.route == "/api/alexa/morning-summary"
        assert handler.handler_class == MorningSummaryHandler
        assert handler.ssml_enabled is True
        assert handler.precompute_enabled is False  # Has complex parameters

    def test_get_routes(self):
        """Test getting routes dictionary."""
        routes = AlexaHandlerRegistry.get_routes()
        assert isinstance(routes, dict)
        assert len(routes) >= 5

        # Check specific routes
        assert "/api/alexa/next-meeting" in routes
        assert "/api/alexa/time-until-next" in routes
        assert "/api/alexa/done-for-day" in routes
        assert "/api/alexa/launch-summary" in routes
        assert "/api/alexa/morning-summary" in routes

    def test_list_intents(self):
        """Test listing all intent names."""
        intents = AlexaHandlerRegistry.list_intents()
        assert isinstance(intents, list)
        assert len(intents) >= 5

        # Verify expected intents
        assert "GetNextMeetingIntent" in intents
        assert "GetTimeUntilNextMeetingIntent" in intents
        assert "GetDoneForDayIntent" in intents
        assert "LaunchIntent" in intents
        assert "GetMorningSummaryIntent" in intents

    def test_list_routes(self):
        """Test listing all route paths."""
        routes = AlexaHandlerRegistry.list_routes()
        assert isinstance(routes, list)
        assert len(routes) >= 5

        # Verify expected routes
        assert "/api/alexa/next-meeting" in routes
        assert "/api/alexa/time-until-next" in routes
        assert "/api/alexa/done-for-day" in routes
        assert "/api/alexa/launch-summary" in routes
        assert "/api/alexa/morning-summary" in routes

    def test_get_nonexistent_handler(self):
        """Test getting a handler that doesn't exist."""
        handler = AlexaHandlerRegistry.get_handler("NonexistentIntent")
        assert handler is None

    def test_get_handler_info_summary(self):
        """Test generating handler info summary."""
        summary = get_handler_info_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

        # Should contain handler information
        assert "GetNextMeetingIntent" in summary
        assert "/api/alexa/next-meeting" in summary
        assert "SSML" in summary or "ssml" in summary.lower()

    def test_route_uniqueness(self):
        """Test that all routes are unique."""
        routes = AlexaHandlerRegistry.list_routes()
        assert len(routes) == len(set(routes)), "Duplicate routes found!"

    def test_intent_uniqueness(self):
        """Test that all intents are unique."""
        intents = AlexaHandlerRegistry.list_intents()
        assert len(intents) == len(set(intents)), "Duplicate intents found!"

    def test_all_handlers_have_valid_classes(self):
        """Test that all registered handlers have valid handler classes."""
        handlers = AlexaHandlerRegistry.get_handlers()
        for intent, info in handlers.items():
            # Each handler class should be a class (not an instance)
            assert isinstance(info.handler_class, type)
            # Should have the handle method (from AlexaEndpointBase)
            assert hasattr(info.handler_class, "handle")

    def test_routes_follow_convention(self):
        """Test that routes follow the /api/alexa/* convention."""
        routes = AlexaHandlerRegistry.list_routes()
        for route in routes:
            assert route.startswith("/api/alexa/"), f"Route {route} doesn't follow convention"
