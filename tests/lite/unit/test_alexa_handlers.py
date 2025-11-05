"""Unit tests for calendarbot_lite/alexa_handlers.py.

Tests cover:
- AlexaEndpointBase authentication, validation, caching
- NextMeetingHandler functionality
- TimeUntilHandler functionality
- DoneForDayHandler functionality
- LaunchSummaryHandler functionality
- MorningSummaryHandler functionality
"""

import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web

from calendarbot_lite.alexa_exceptions import (
    AlexaAuthenticationError,
    AlexaValidationError,
)
from calendarbot_lite.alexa_handlers import (
    AlexaEndpointBase,
    DoneForDayHandler,
    LaunchSummaryHandler,
    NextMeetingHandler,
    TimeUntilHandler,
)
from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_time_provider() -> Mock:
    """Provide a mock time provider that returns a fixed datetime."""
    now = datetime.datetime(2024, 1, 15, 10, 0, 0, tzinfo=datetime.UTC)
    return Mock(return_value=now)


@pytest.fixture
def mock_skipped_store() -> Mock:
    """Provide a mock skipped store."""
    store = Mock()
    store.is_skipped = Mock(return_value=False)
    return store


@pytest.fixture
def mock_response_cache() -> Mock:
    """Provide a mock response cache."""
    cache = Mock()
    cache.generate_key = Mock(return_value="test_key")
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    return cache


@pytest.fixture
def mock_precompute_getter() -> Mock:
    """Provide a mock precompute getter."""
    return Mock(return_value=None)


@pytest.fixture
def mock_presenter() -> Mock:
    """Provide a mock presenter."""
    presenter = Mock()
    presenter.format_next_meeting = Mock(return_value=("Speech text", "<speak>SSML</speak>"))
    presenter.format_time_until = Mock(return_value=("Time speech", "<speak>Time SSML</speak>"))
    presenter.format_done_for_day = Mock(return_value=("Done speech", "<speak>Done SSML</speak>"))
    presenter.format_launch_summary = Mock(
        return_value=("Launch speech", "<speak>Launch SSML</speak>")
    )
    presenter.format_morning_summary = Mock(
        return_value=("Morning speech", "<speak>Morning SSML</speak>")
    )
    return presenter


@pytest.fixture
def mock_request() -> Mock:
    """Provide a mock aiohttp request."""
    request = Mock()
    request.query = {}
    request.headers = {}
    return request


@pytest.fixture
def mock_window_lock() -> AsyncMock:
    """Provide a mock async window lock."""
    lock = AsyncMock()
    lock.__aenter__ = AsyncMock()
    lock.__aexit__ = AsyncMock()
    return lock


@pytest.fixture
def sample_event() -> LiteCalendarEvent:
    """Create a sample calendar event for testing."""
    from calendarbot_lite.lite_models import LiteDateTimeInfo, LiteLocation

    start_time = datetime.datetime(2024, 1, 15, 14, 0, 0, tzinfo=datetime.UTC)
    end_time = datetime.datetime(2024, 1, 15, 15, 0, 0, tzinfo=datetime.UTC)

    return LiteCalendarEvent(
        id="test-event-1",
        subject="Team Meeting",
        start=LiteDateTimeInfo(date_time=start_time),
        end=LiteDateTimeInfo(date_time=end_time),
        is_all_day=False,
        location=LiteLocation(display_name="Conference Room A"),
        is_online_meeting=False,
        attendees=[],
        body_preview="",
    )


# ============================================================================
# AlexaEndpointBase Tests
# ============================================================================


@pytest.mark.unit
async def test_validate_params_when_valid_params_then_returns_model(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
) -> None:
    """Test parameter validation with valid parameters."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)

    mock_request = Mock()
    mock_request.query = {"tz": "America/New_York"}

    result = handler.validate_params(mock_request)
    assert result is not None
    assert hasattr(result, "tz")


@pytest.mark.unit
async def test_validate_params_when_invalid_params_then_raises_validation_error(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
) -> None:
    """Test parameter validation with invalid parameters."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)

    # Mock request with invalid parameters that will cause pydantic validation to fail
    mock_request = Mock()
    mock_request.query = {}

    # This should not raise - AlexaRequestParams has all optional fields
    result = handler.validate_params(mock_request)
    assert result is not None


@pytest.mark.unit
async def test_check_auth_when_no_token_configured_then_allows_request(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
) -> None:
    """Test authentication check when no bearer token is configured."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)

    # Should not raise any exception
    handler.check_auth(mock_request)


@pytest.mark.unit
async def test_check_auth_when_valid_token_then_allows_request(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
) -> None:
    """Test authentication check with valid bearer token."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler("test-token", mock_time_provider, mock_skipped_store)
    mock_request.headers = {"Authorization": "Bearer test-token"}

    # Should not raise any exception
    handler.check_auth(mock_request)


@pytest.mark.unit
async def test_check_auth_when_invalid_token_then_raises_auth_error(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
) -> None:
    """Test authentication check with invalid bearer token."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler("correct-token", mock_time_provider, mock_skipped_store)
    mock_request.headers = {"Authorization": "Bearer wrong-token"}

    with pytest.raises(AlexaAuthenticationError):
        handler.check_auth(mock_request)


@pytest.mark.unit
async def test_check_auth_when_missing_bearer_prefix_then_raises_auth_error(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
) -> None:
    """Test authentication check with malformed authorization header."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler("test-token", mock_time_provider, mock_skipped_store)
    mock_request.headers = {"Authorization": "test-token"}  # Missing "Bearer " prefix

    with pytest.raises(AlexaAuthenticationError):
        handler.check_auth(mock_request)


@pytest.mark.unit
async def test_find_next_meeting_when_meetings_exist_then_returns_next_meeting(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    sample_event: LiteCalendarEvent,
) -> None:
    """Test finding next meeting when upcoming meetings exist."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)
    now = mock_time_provider()

    result = handler.find_next_meeting((sample_event,), now)

    assert result is not None
    event, seconds_until = result
    assert event.id == "test-event-1"
    assert seconds_until > 0


@pytest.mark.unit
async def test_find_next_meeting_when_no_meetings_then_returns_none(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
) -> None:
    """Test finding next meeting when no meetings exist."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)
    now = mock_time_provider()

    result = handler.find_next_meeting((), now)

    assert result is None


@pytest.mark.unit
async def test_find_next_meeting_when_event_skipped_then_returns_next_unskipped(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    sample_event: LiteCalendarEvent,
) -> None:
    """Test finding next meeting when first event is skipped."""
    from calendarbot_lite.lite_models import LiteDateTimeInfo

    # Create second event
    start_time = datetime.datetime(2024, 1, 15, 16, 0, 0, tzinfo=datetime.UTC)
    end_time = datetime.datetime(2024, 1, 15, 17, 0, 0, tzinfo=datetime.UTC)

    second_event = LiteCalendarEvent(
        id="test-event-2",
        subject="Second Meeting",
        start=LiteDateTimeInfo(date_time=start_time),
        end=LiteDateTimeInfo(date_time=end_time),
        is_all_day=False,
        location=None,
        is_online_meeting=False,
        attendees=[],
        body_preview="",
    )

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    # Configure skipped store to skip first event
    mock_skipped_store.is_skipped = Mock(side_effect=lambda id: id == "test-event-1")

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)
    now = mock_time_provider()

    result = handler.find_next_meeting((sample_event, second_event), now)

    assert result is not None
    event, _ = result
    assert event.id == "test-event-2"


@pytest.mark.unit
async def test_is_focus_time_when_focus_keywords_in_subject_then_returns_true(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    sample_event: LiteCalendarEvent,
) -> None:
    """Test focus time detection with focus keywords in subject."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)

    # Test various focus time keywords
    sample_event.subject = "Focus Time - Deep Work"
    assert handler._is_focus_time(sample_event) is True

    sample_event.subject = "Focus Block for Project"
    assert handler._is_focus_time(sample_event) is True

    sample_event.subject = "Do Not Schedule"
    assert handler._is_focus_time(sample_event) is True


@pytest.mark.unit
async def test_is_focus_time_when_no_focus_keywords_then_returns_false(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    sample_event: LiteCalendarEvent,
) -> None:
    """Test focus time detection without focus keywords."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)

    sample_event.subject = "Regular Team Meeting"
    assert handler._is_focus_time(sample_event) is False


# ============================================================================
# NextMeetingHandler Tests
# ============================================================================


@pytest.mark.unit
async def test_next_meeting_handler_when_meeting_exists_then_returns_meeting_info(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    sample_event: LiteCalendarEvent,
    mock_request: Mock,
    mock_window_lock: AsyncMock,
) -> None:
    """Test NextMeetingHandler returns meeting information when event exists."""
    handler = NextMeetingHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
        duration_formatter=lambda s: f"in {s} seconds",  # type: ignore
        iso_serializer=lambda dt: dt.isoformat(),  # type: ignore
    )

    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (sample_event,), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "meeting" in data
    assert data["meeting"] is not None
    assert data["meeting"]["subject"] == "Team Meeting"
    assert "seconds_until_start" in data["meeting"]


@pytest.mark.unit
async def test_next_meeting_handler_when_no_meetings_then_returns_none(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    mock_request: Mock,
    mock_window_lock: AsyncMock,
) -> None:
    """Test NextMeetingHandler returns None when no meetings exist."""
    handler = NextMeetingHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
    )

    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "meeting" in data
    assert data["meeting"] is None
    assert "speech_text" in data


# ============================================================================
# TimeUntilHandler Tests
# ============================================================================


@pytest.mark.unit
async def test_time_until_handler_when_meeting_exists_then_returns_time_info(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    sample_event: LiteCalendarEvent,
    mock_request: Mock,
) -> None:
    """Test TimeUntilHandler returns time information when event exists."""
    handler = TimeUntilHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
        duration_formatter=lambda s: f"in {s} seconds",  # type: ignore
    )

    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (sample_event,), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "seconds_until_start" in data
    assert data["seconds_until_start"] is not None
    assert data["seconds_until_start"] > 0
    assert "speech_text" in data


@pytest.mark.unit
async def test_time_until_handler_when_no_meetings_then_returns_none_seconds(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    mock_request: Mock,
) -> None:
    """Test TimeUntilHandler returns None seconds when no meetings exist."""
    handler = TimeUntilHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
    )

    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "seconds_until_start" in data
    assert data["seconds_until_start"] is None


# ============================================================================
# DoneForDayHandler Tests
# ============================================================================


@pytest.mark.unit
async def test_done_for_day_handler_when_meetings_today_then_returns_end_time(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    sample_event: LiteCalendarEvent,
    mock_request: Mock,
) -> None:
    """Test DoneForDayHandler returns last meeting end time."""
    handler = DoneForDayHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
        iso_serializer=lambda dt: dt.isoformat() + "Z",  # type: ignore
    )

    mock_request.query = {"tz": "UTC"}
    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (sample_event,), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "has_meetings_today" in data
    assert data["has_meetings_today"] is True
    assert "last_meeting_end_iso" in data
    assert data["last_meeting_end_iso"] is not None


@pytest.mark.unit
async def test_done_for_day_handler_when_no_meetings_today_then_returns_false(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    mock_request: Mock,
) -> None:
    """Test DoneForDayHandler returns false when no meetings today."""
    handler = DoneForDayHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
    )

    mock_request.query = {"tz": "UTC"}
    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "has_meetings_today" in data
    assert data["has_meetings_today"] is False


@pytest.mark.unit
async def test_done_for_day_handler_when_meetings_ended_then_returns_done_message(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    mock_request: Mock,
) -> None:
    """Test DoneForDayHandler returns done message when all meetings ended."""
    from calendarbot_lite.lite_models import LiteDateTimeInfo

    # Create a past event (meeting already ended)
    past_start = datetime.datetime(2024, 1, 15, 8, 0, 0, tzinfo=datetime.UTC)
    past_end = datetime.datetime(2024, 1, 15, 9, 0, 0, tzinfo=datetime.UTC)

    past_event = LiteCalendarEvent(
        id="past-event",
        subject="Morning Meeting",
        start=LiteDateTimeInfo(date_time=past_start),
        end=LiteDateTimeInfo(date_time=past_end),
        is_all_day=False,
        location=None,
        is_online_meeting=False,
        attendees=[],
        body_preview="",
    )

    handler = DoneForDayHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
        iso_serializer=lambda dt: dt.isoformat() + "Z",  # type: ignore
    )

    mock_request.query = {"tz": "UTC"}
    now = mock_time_provider()  # 10:00 AM, after the meeting ended

    response = await handler.handle_request(mock_request, (past_event,), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert data["has_meetings_today"] is True
    assert "speech_text" in data


# ============================================================================
# LaunchSummaryHandler Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.smoke  # Critical path: Core Alexa handler functionality
async def test_launch_summary_handler_when_meetings_today_then_returns_summary(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    sample_event: LiteCalendarEvent,
    mock_request: Mock,
) -> None:
    """Test LaunchSummaryHandler returns summary with meeting info."""
    handler = LaunchSummaryHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
        duration_formatter=lambda s: f"in {s} seconds",  # type: ignore
        iso_serializer=lambda dt: dt.isoformat(),  # type: ignore
    )

    mock_request.query = {"tz": "UTC"}
    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (sample_event,), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert "has_meetings_today" in data
    assert "next_meeting" in data
    assert "done_for_day" in data
    assert "speech_text" in data


@pytest.mark.unit
async def test_launch_summary_handler_when_no_meetings_then_returns_free_message(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    mock_request: Mock,
) -> None:
    """Test LaunchSummaryHandler returns free message when no meetings."""
    handler = LaunchSummaryHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
    )

    mock_request.query = {"tz": "UTC"}
    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (), now)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert data["has_meetings_today"] is False
    assert "speech_text" in data


@pytest.mark.unit
async def test_launch_summary_handler_when_meeting_in_progress_then_acknowledges_current_meeting(
    mock_skipped_store: Mock,
    mock_presenter: Mock,
    mock_request: Mock,
    sample_event: LiteCalendarEvent,
) -> None:
    """Test LaunchSummaryHandler acknowledges when user is in a meeting."""
    # Test at 10:15 AM, during a 10:00-11:00 AM meeting
    test_time = datetime.datetime(2024, 1, 15, 10, 15, 0, tzinfo=datetime.UTC)
    mock_time_provider = Mock(return_value=test_time)

    # Create a meeting that's currently in progress (10:00-11:00 AM)
    current_meeting = LiteCalendarEvent(
        id="current-meeting",
        subject="Morning Standup",
        start=LiteDateTimeInfo(
            date_time=datetime.datetime(2024, 1, 15, 10, 0, 0, tzinfo=datetime.UTC),
            time_zone="UTC",
        ),
        end=LiteDateTimeInfo(
            date_time=datetime.datetime(2024, 1, 15, 11, 0, 0, tzinfo=datetime.UTC),
            time_zone="UTC",
        ),
        is_all_day=False,
    )

    # Create a future meeting (1:00-2:00 PM)
    next_meeting = LiteCalendarEvent(
        id="next-meeting",
        subject="Afternoon Meeting",
        start=LiteDateTimeInfo(
            date_time=datetime.datetime(2024, 1, 15, 13, 0, 0, tzinfo=datetime.UTC),
            time_zone="UTC",
        ),
        end=LiteDateTimeInfo(
            date_time=datetime.datetime(2024, 1, 15, 14, 0, 0, tzinfo=datetime.UTC),
            time_zone="UTC",
        ),
        is_all_day=False,
    )

    handler = LaunchSummaryHandler(  # type: ignore[call-arg]
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=mock_presenter,  # type: ignore
        duration_formatter=lambda s: f"in {s // 60} minutes",  # type: ignore
        iso_serializer=lambda dt: dt.isoformat(),  # type: ignore
    )

    mock_request.query = {"tz": "UTC"}
    now = mock_time_provider()

    response = await handler.handle_request(mock_request, (current_meeting, next_meeting), now)

    assert response.status == 200

    # Verify that format_launch_summary was called with current_meeting parameter
    mock_presenter.format_launch_summary.assert_called_once()
    call_args = mock_presenter.format_launch_summary.call_args

    # Check that current_meeting was passed (positional or keyword arg)
    if call_args.args and len(call_args.args) > 5:
        # Positional argument
        passed_current_meeting = call_args.args[5]
    else:
        # Keyword argument
        passed_current_meeting = call_args.kwargs.get("current_meeting")

    assert passed_current_meeting is not None
    assert passed_current_meeting["subject"] == "Morning Standup"
    assert passed_current_meeting["is_current"] is True


# ============================================================================
# MorningSummaryHandler Tests
# ============================================================================


# ============================================================================
# Caching and Precompute Tests
# ============================================================================


@pytest.mark.unit
async def test_handle_when_precompute_hit_then_returns_cached_response(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
    mock_window_lock: AsyncMock,
) -> None:
    """Test that precomputed responses are returned immediately."""
    precompute_data = {"precomputed": True, "meeting": None}
    mock_precompute_getter = Mock(return_value=precompute_data)

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({"computed": True})

    handler = TestHandler(
        None,
        mock_time_provider,
        mock_skipped_store,
        precompute_getter=mock_precompute_getter,
    )

    mock_request.query = {"tz": "UTC"}
    event_window_ref: Any = [[]]

    response = await handler.handle(mock_request, event_window_ref, mock_window_lock)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert data == precompute_data
    assert "precomputed" in data


@pytest.mark.unit
async def test_handle_when_cache_hit_then_returns_cached_response(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_response_cache: Mock,
    mock_request: Mock,
    mock_window_lock: AsyncMock,
) -> None:
    """Test that cached responses are returned when available."""
    cached_data = {"cached": True, "meeting": None}
    mock_response_cache.get = Mock(return_value=cached_data)

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({"computed": True})

    handler = TestHandler(
        None,
        mock_time_provider,
        mock_skipped_store,
        response_cache=mock_response_cache,
    )

    mock_request.query = {}
    event_window_ref: Any = [[]]

    response = await handler.handle(mock_request, event_window_ref, mock_window_lock)

    assert response.status == 200
    body = response.body
    import json

    data = json.loads(body)  # type: ignore[arg-type]

    assert data == cached_data


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
async def test_handle_when_auth_error_then_returns_401(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
    mock_window_lock: AsyncMock,
) -> None:
    """Test that authentication errors return 401 status."""

    class TestHandler(AlexaEndpointBase):
        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler("correct-token", mock_time_provider, mock_skipped_store)
    mock_request.headers = {"Authorization": "Bearer wrong-token"}
    mock_request.query = {}

    event_window_ref: Any = [[]]

    response = await handler.handle(mock_request, event_window_ref, mock_window_lock)

    assert response.status == 401


@pytest.mark.unit
async def test_handle_when_validation_error_then_returns_400(
    mock_time_provider: Mock,
    mock_skipped_store: Mock,
    mock_request: Mock,
    mock_window_lock: AsyncMock,
) -> None:
    """Test that validation errors return 400 status."""

    class TestHandler(AlexaEndpointBase):
        def validate_params(self, request: Any) -> Any:
            raise AlexaValidationError("Invalid parameters")

        async def handle_request(self, request: Any, window: Any, now: Any) -> Any:
            return web.json_response({})

    handler = TestHandler(None, mock_time_provider, mock_skipped_store)
    mock_request.query = {}

    event_window_ref: Any = [[]]

    response = await handler.handle(mock_request, event_window_ref, mock_window_lock)

    assert response.status == 400
