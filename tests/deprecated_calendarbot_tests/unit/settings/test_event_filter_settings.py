"""Unit tests for EventFilterSettings with hidden events functionality."""

from calendarbot.settings.models import EventFilterSettings


def test_event_filter_settings_hidden_events_default_empty():
    """Test that hidden_events is empty by default."""
    settings = EventFilterSettings()
    assert isinstance(settings.hidden_events, set)
    assert len(settings.hidden_events) == 0


def test_event_filter_settings_hide_event():
    """Test hiding an event adds its graph_id to hidden_events."""
    settings = EventFilterSettings()
    graph_id = "AAMkADExample"

    # Hide the event
    settings.hide_event(graph_id)

    # Verify it's in the hidden events set
    assert graph_id in settings.hidden_events
    assert len(settings.hidden_events) == 1


def test_event_filter_settings_hide_event_empty_id():
    """Test hiding an event with empty graph_id does nothing."""
    settings = EventFilterSettings()

    # Try to hide an event with empty ID
    settings.hide_event("")

    # Verify nothing was added
    assert len(settings.hidden_events) == 0


def test_event_filter_settings_hide_event_duplicate():
    """Test hiding the same event twice only adds it once."""
    settings = EventFilterSettings()
    graph_id = "AAMkADExample"

    # Hide the event twice
    settings.hide_event(graph_id)
    settings.hide_event(graph_id)

    # Verify it's only in the set once
    assert graph_id in settings.hidden_events
    assert len(settings.hidden_events) == 1


def test_event_filter_settings_unhide_event():
    """Test unhiding an event removes its graph_id from hidden_events."""
    settings = EventFilterSettings()
    graph_id = "AAMkADExample"

    # Hide then unhide the event
    settings.hide_event(graph_id)
    result = settings.unhide_event(graph_id)

    # Verify it's removed and the result is True
    assert graph_id not in settings.hidden_events
    assert len(settings.hidden_events) == 0
    assert result is True


def test_event_filter_settings_unhide_nonexistent_event():
    """Test unhiding a non-existent event returns False."""
    settings = EventFilterSettings()
    graph_id = "AAMkADExample"

    # Unhide an event that wasn't hidden
    result = settings.unhide_event(graph_id)

    # Verify the result is False
    assert result is False


def test_event_filter_settings_unhide_event_empty_id():
    """Test unhiding an event with empty graph_id returns False."""
    settings = EventFilterSettings()

    # Try to unhide an event with empty ID
    result = settings.unhide_event("")

    # Verify the result is False
    assert result is False


def test_event_filter_settings_is_event_hidden():
    """Test is_event_hidden returns correct status."""
    settings = EventFilterSettings()
    graph_id = "AAMkADExample"
    other_id = "BBNlBDExample"

    # Hide one event
    settings.hide_event(graph_id)

    # Verify is_event_hidden returns correct values
    assert settings.is_event_hidden(graph_id) is True
    assert settings.is_event_hidden(other_id) is False
    assert settings.is_event_hidden("") is False


def test_event_filter_settings_serialization():
    """Test that hidden_events is properly serialized."""
    settings = EventFilterSettings()
    graph_id = "AAMkADExample"

    # Hide an event
    settings.hide_event(graph_id)

    # Serialize to dict
    data = settings.dict()

    # Verify hidden_events is in the dict
    assert "hidden_events" in data
    assert isinstance(data["hidden_events"], list)  # Sets are serialized to lists
    assert graph_id in data["hidden_events"]
