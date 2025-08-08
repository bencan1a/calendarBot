"""Unit tests for WhatsNextLogic hidden events filtering."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytz

from calendarbot.cache.models import CachedEvent
from calendarbot.display.whats_next_logic import WhatsNextLogic
from calendarbot.settings.models import EventFilterSettings


def create_test_event(
    event_id: str, graph_id: str, subject: str, start_offset: int = 0, end_offset: int = 60
) -> CachedEvent:
    """Create a test event with the given parameters.

    Args:
        event_id: Event ID
        graph_id: Graph ID
        subject: Event subject
        start_offset: Minutes from now for start time (negative for past)
        end_offset: Minutes from now for end time

    Returns:
        CachedEvent instance
    """
    now = datetime.now(pytz.UTC)
    start = now + timedelta(minutes=start_offset)
    end = now + timedelta(minutes=end_offset)

    return CachedEvent(
        id=event_id,
        graph_id=graph_id,
        subject=subject,
        start_datetime=start.isoformat(),
        end_datetime=end.isoformat(),
        start_timezone="UTC",
        end_timezone="UTC",
        cached_at=now.isoformat(),
    )


def test_whats_next_logic_filters_hidden_events():
    """Test that WhatsNextLogic filters out hidden events."""
    # Create mock settings with hidden events
    mock_settings = MagicMock()
    mock_settings.event_filters = EventFilterSettings()
    mock_settings.event_filters.hidden_events = {"graph-id-2", "graph-id-4"}

    # Create test events
    events = [
        create_test_event("event-1", "graph-id-1", "Visible current event", -30, 30),
        create_test_event("event-2", "graph-id-2", "Hidden current event", -30, 30),
        create_test_event("event-3", "graph-id-3", "Visible upcoming event", 60, 120),
        create_test_event("event-4", "graph-id-4", "Hidden upcoming event", 90, 150),
        create_test_event("event-5", "graph-id-5", "Visible later event", 180, 240),
    ]

    # Initialize WhatsNextLogic with mock settings
    logic = WhatsNextLogic(mock_settings)

    # Set a fixed current time for testing
    current_time = datetime.now(pytz.UTC)

    # Group events
    current_events, upcoming_events, later_events = logic._group_events(events, current_time)

    # Verify hidden events are filtered out
    assert len(current_events) == 1
    assert current_events[0].graph_id == "graph-id-1"

    assert len(upcoming_events) == 2
    assert "graph-id-2" not in [e.graph_id for e in upcoming_events]
    assert "graph-id-4" not in [e.graph_id for e in upcoming_events]

    # Verify visible events are included
    assert "graph-id-1" in [e.graph_id for e in current_events]
    assert "graph-id-3" in [e.graph_id for e in upcoming_events]
    assert "graph-id-5" in [e.graph_id for e in upcoming_events]


def test_whats_next_logic_handles_missing_settings():
    """Test that WhatsNextLogic handles missing settings gracefully."""
    # Create mock settings without event_filters
    mock_settings = MagicMock()
    mock_settings.event_filters = None

    # Create test events
    events = [
        create_test_event("event-1", "graph-id-1", "Event 1", -30, 30),
        create_test_event("event-2", "graph-id-2", "Event 2", 60, 120),
    ]

    # Initialize WhatsNextLogic with mock settings
    logic = WhatsNextLogic(mock_settings)

    # Set a fixed current time for testing
    current_time = datetime.now(pytz.UTC)

    # Group events - should not raise an exception
    current_events, upcoming_events, later_events = logic._group_events(events, current_time)

    # Verify all events are included (no filtering)
    assert len(current_events) == 1
    assert len(upcoming_events) == 1
    assert current_events[0].graph_id == "graph-id-1"
    assert upcoming_events[0].graph_id == "graph-id-2"


def test_whats_next_logic_handles_missing_hidden_events():
    """Test that WhatsNextLogic handles missing hidden_events attribute gracefully."""
    # Create mock settings with event_filters but no hidden_events
    mock_settings = MagicMock()
    mock_settings.event_filters = MagicMock()
    # Intentionally not setting hidden_events

    # Create test events
    events = [
        create_test_event("event-1", "graph-id-1", "Event 1", -30, 30),
        create_test_event("event-2", "graph-id-2", "Event 2", 60, 120),
    ]

    # Initialize WhatsNextLogic with mock settings
    logic = WhatsNextLogic(mock_settings)

    # Set a fixed current time for testing
    current_time = datetime.now(pytz.UTC)

    # Group events - should not raise an exception
    current_events, upcoming_events, later_events = logic._group_events(events, current_time)

    # Verify all events are included (no filtering)
    assert len(current_events) == 1
    assert len(upcoming_events) == 1
    assert current_events[0].graph_id == "graph-id-1"
    assert upcoming_events[0].graph_id == "graph-id-2"
