from collections.abc import AsyncIterator, Generator
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import AsyncMock

import pytest

from calendarbot_lite.core.http_client import close_all_clients


@pytest.fixture
def simple_settings() -> SimpleNamespace:
    """Lightweight settings object used across lite tests.

    Provides a minimal, deterministic configuration used by multiple
    tests in tests/lite/. Keep this fixture small and fast.
    Fields:
      - request_timeout: HTTP read timeout in seconds
      - max_retries: retry attempts for HTTP fetches
      - retry_backoff_factor: multiplier for retry backoff delays
      - user_agent: default User-Agent header used in tests
    """
    return SimpleNamespace(
        request_timeout=30,
        max_retries=3,
        retry_backoff_factor=1.5,
        user_agent="calendarbot-lite-test/1.0",
    )


@pytest.fixture
def test_timezone() -> str:
    """Return a deterministic timezone identifier for tests.

    Using a fixed timezone string avoids host-local timezone differences
    which can make datetime-sensitive tests flaky.
    """
    return "America/Los_Angeles"


@pytest.fixture(autouse=True)
def reset_worker_pool() -> Generator[None, Any, None]:
    """Reset global worker pool between tests to prevent state pollution.

    The global _worker_pool singleton in lite_rrule_expander can carry state
    from one test to another. This fixture ensures each test gets a fresh
    worker pool by resetting it to None after each test.
    """
    yield
    # Reset global worker pool after each test
    import calendarbot_lite.lite_rrule_expander

    calendarbot_lite.lite_rrule_expander._worker_pool = None


@pytest.fixture(autouse=True)
def clean_test_environment(monkeypatch: Any) -> Generator[None, Any, None]:
    """Ensure test environment variables are cleaned between tests.

    Some tests set CALENDARBOT_TEST_TIME to freeze time for recurring event
    expansion. This fixture ensures the environment variable is cleared before
    and after each test to prevent pollution between tests.
    """
    # Clear any lingering test time before the test
    monkeypatch.delenv("CALENDARBOT_TEST_TIME", raising=False)
    yield
    # Clear again after the test
    monkeypatch.delenv("CALENDARBOT_TEST_TIME", raising=False)


@pytest.fixture(autouse=True)
async def cleanup_shared_http_clients() -> AsyncIterator[None]:
    """Autouse async fixture to clean up shared HTTP clients.

    Ensures calendarbot_lite.http_client.close_all_clients() is invoked
    after every test to prevent resource leaks from httpx clients.
    This fixture is intentionally lightweight (no setup) and only runs
    teardown logic after the test completes.
    """
    yield
    await close_all_clients()


# ==================== ICS Test Data Fixtures ====================


@pytest.fixture
def sample_ics_simple() -> str:
    """
    Return a simple ICS calendar string with a single event.

    Returns:
        RFC 5545 compliant ICS string with one event:
        - Event: "Team Meeting" on 2024-01-15 10:00-11:00 UTC
        - Includes DTSTART, DTEND, SUMMARY, LOCATION, DESCRIPTION
    """
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:test-event-001@calendarbot.test
DTSTART:20240115T100000Z
DTEND:20240115T110000Z
SUMMARY:Team Meeting
LOCATION:Conference Room A
DESCRIPTION:Weekly team sync meeting
DTSTAMP:20240115T090000Z
END:VEVENT
END:VCALENDAR"""


@pytest.fixture
def sample_ics_recurring() -> str:
    """
    Return an ICS string with a recurring event.

    Returns:
        RFC 5545 compliant ICS string with recurring event:
        - Event: "Daily Standup" recurring daily at 09:00-09:15 UTC
        - RRULE:FREQ=DAILY;COUNT=5 (5 occurrences)
    """
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:test-event-002@calendarbot.test
DTSTART:20240115T090000Z
DTEND:20240115T091500Z
SUMMARY:Daily Standup
LOCATION:Virtual
DESCRIPTION:Daily team standup meeting
RRULE:FREQ=DAILY;COUNT=5
DTSTAMP:20240115T080000Z
END:VEVENT
END:VCALENDAR"""


@pytest.fixture
def sample_ics_exdate() -> str:
    """
    Return an ICS string with EXDATE (cancelled occurrence).

    Returns:
        RFC 5545 compliant ICS string with EXDATE:
        - Event: "Weekly Review" on Mondays at 14:00-15:00 UTC
        - RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=4 (4 occurrences)
        - EXDATE for second occurrence (2024-01-22)
    """
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:test-event-003@calendarbot.test
DTSTART:20240115T140000Z
DTEND:20240115T150000Z
SUMMARY:Weekly Review
LOCATION:Board Room
DESCRIPTION:Weekly review meeting with stakeholders
RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=4
EXDATE:20240122T140000Z
DTSTAMP:20240115T130000Z
END:VEVENT
END:VCALENDAR"""


# ==================== Alexa Request Fixtures ====================


@pytest.fixture
def alexa_request_builder() -> Callable[[str, str | None, dict | None, dict | None], dict]:
    """
    Return a builder function for creating Alexa request payloads.

    Returns:
        Callable that builds Alexa request dicts with signature:
        builder(request_type, intent_name=None, slots=None, session_attrs=None) -> dict

        The builder creates properly formatted Alexa request dicts matching
        the alexa_models structure with request ID, timestamp, locale, and session data.
    """

    def builder(
        request_type: str,
        intent_name: str | None = None,
        slots: dict | None = None,
        session_attrs: dict | None = None,
    ) -> dict:
        """
        Build an Alexa request payload.

        Args:
            request_type: Type of request (e.g., "LaunchRequest", "IntentRequest")
            intent_name: Name of the intent (required for IntentRequest)
            slots: Optional dict of slot name -> slot value
            session_attrs: Optional session attributes dict

        Returns:
            Complete Alexa request payload dict
        """
        request_id = f"amzn1.echo-api.request.{request_type.lower()}-test-12345"
        timestamp = "2024-01-15T12:00:00Z"
        locale = "en-US"

        base_request = {
            "version": "1.0",
            "session": {
                "new": True,
                "sessionId": "amzn1.echo-api.session.test-session-12345",
                "application": {"applicationId": "amzn1.ask.skill.test-app-id"},
                "attributes": session_attrs or {},
                "user": {"userId": "amzn1.ask.account.test-user-id"},
            },
            "context": {
                "System": {
                    "application": {"applicationId": "amzn1.ask.skill.test-app-id"},
                    "user": {"userId": "amzn1.ask.account.test-user-id"},
                    "device": {
                        "deviceId": "amzn1.ask.device.test-device-id",
                        "supportedInterfaces": {},
                    },
                    "apiEndpoint": "https://api.amazonalexa.com",
                    "apiAccessToken": "test-access-token",
                }
            },
            "request": {
                "type": request_type,
                "requestId": request_id,
                "timestamp": timestamp,
                "locale": locale,
            },
        }

        # Add intent-specific fields for IntentRequest
        if request_type == "IntentRequest" and intent_name:
            formatted_slots = {}
            if slots:
                for slot_name, slot_value in slots.items():
                    formatted_slots[slot_name] = {
                        "name": slot_name,
                        "value": slot_value,
                        "confirmationStatus": "NONE",
                    }

            base_request["request"]["intent"] = {
                "name": intent_name,
                "confirmationStatus": "NONE",
                "slots": formatted_slots,
            }

        return base_request

    return builder


@pytest.fixture
def alexa_launch_request(alexa_request_builder: Callable) -> dict:
    """
    Return a sample Alexa LaunchRequest payload.

    Args:
        alexa_request_builder: Builder fixture for creating requests

    Returns:
        Complete Alexa LaunchRequest payload dict
    """
    return alexa_request_builder("LaunchRequest")


@pytest.fixture
def alexa_intent_request(alexa_request_builder: Callable) -> dict:
    """
    Return a sample Alexa WhatsNextIntent request payload.

    Args:
        alexa_request_builder: Builder fixture for creating requests

    Returns:
        Complete Alexa IntentRequest payload dict for WhatsNextIntent
    """
    return alexa_request_builder("IntentRequest", intent_name="WhatsNextIntent")


# ==================== Utility Fixtures ====================


@pytest.fixture
def freeze_time_fixture(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """
    Freeze time at a specific datetime for testing.

    Uses pytest's monkeypatch to override datetime.now() to return a fixed
    datetime value for consistent time-based testing.

    Args:
        monkeypatch: Pytest's monkeypatch fixture

    Returns:
        The frozen datetime object (2024-01-15 12:00:00 UTC)
    """
    frozen_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    class FrozenDatetime:
        @classmethod
        def now(cls, tz: timezone | None = None) -> datetime:
            if tz is None:
                return frozen_time
            return frozen_time.astimezone(tz)

        @classmethod
        def utcnow(cls) -> datetime:
            return frozen_time

        def __getattr__(self, name: str) -> Any:
            return getattr(datetime, name)

    monkeypatch.setattr("datetime.datetime", FrozenDatetime)
    return frozen_time


@pytest.fixture
def mock_aiohttp_session() -> AsyncMock:
    """
    Return a mock aiohttp ClientSession for testing.

    Returns:
        AsyncMock that simulates aiohttp.ClientSession with:
        - Mock get() method that returns AsyncMock
        - Response mock with text(), json(), and status attributes
    """
    session_mock = AsyncMock()

    # Create response mock
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.text = AsyncMock(return_value="Mock response text")
    response_mock.json = AsyncMock(return_value={"mock": "data"})
    response_mock.__aenter__ = AsyncMock(return_value=response_mock)
    response_mock.__aexit__ = AsyncMock(return_value=None)

    # Configure session.get() to return the response
    session_mock.get = AsyncMock(return_value=response_mock)
    session_mock.post = AsyncMock(return_value=response_mock)
    session_mock.close = AsyncMock()

    # Make session itself async context manager
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    return session_mock
