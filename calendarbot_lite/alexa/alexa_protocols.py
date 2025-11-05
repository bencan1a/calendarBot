"""Protocol definitions for Alexa handler dependencies.

This module defines Protocol types for better type safety in Alexa handlers,
replacing generic 'Any' type hints with explicit interface contracts.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Optional, Protocol

if TYPE_CHECKING:
    from calendarbot_lite.alexa.alexa_types import AlexaDoneForDayInfo


class TimeProvider(Protocol):
    """Protocol for time provider callables."""

    def __call__(self) -> datetime.datetime:
        """Return current UTC time.

        Returns:
            Current UTC datetime
        """
        ...


class SkippedStore(Protocol):
    """Protocol for skipped events storage."""

    def is_skipped(self, event_id: str) -> bool:
        """Check if an event is marked as skipped.

        Args:
            event_id: Event identifier

        Returns:
            True if event is skipped, False otherwise
        """
        ...


class DurationFormatter(Protocol):
    """Protocol for duration formatting callables."""

    def __call__(self, seconds: int) -> str:
        """Format duration in seconds to human-readable speech.

        Args:
            seconds: Duration in seconds

        Returns:
            Human-readable duration string (e.g., "in 2 hours")
        """
        ...


class ISOSerializer(Protocol):
    """Protocol for datetime ISO serialization."""

    def __call__(self, dt: datetime.datetime) -> str:
        """Serialize datetime to ISO string format.

        Args:
            dt: Datetime to serialize

        Returns:
            ISO 8601 formatted string
        """
        ...


class TimezoneGetter(Protocol):
    """Protocol for getting server timezone."""

    def __call__(self) -> str:
        """Get server timezone.

        Returns:
            Server timezone string (IANA format)
        """
        ...


class PrecomputeGetter(Protocol):
    """Protocol for getting precomputed responses."""

    def __call__(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Get precomputed response by cache key.

        Args:
            cache_key: Cache key for the precomputed response

        Returns:
            Precomputed response dict or None if not available
        """
        ...


class AlexaPresenter(Protocol):
    """Protocol for Alexa response presenters.

    Presenters format data for Alexa responses, separating
    business logic from presentation concerns.
    """

    def format_next_meeting(
        self, meeting_data: Optional[dict[str, Any]]
    ) -> tuple[str, Optional[str]]:
        """Format next meeting data for speech.

        Args:
            meeting_data: Meeting data dict with subject, time, etc. (None if no meetings)

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...

    def format_time_until(
        self, seconds_until: int, meeting_data: Optional[dict[str, Any]]
    ) -> tuple[str, Optional[str]]:
        """Format time until meeting for speech.

        Args:
            seconds_until: Seconds until next meeting (0 if none)
            meeting_data: Optional meeting data dict

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...

    def format_done_for_day(
        self, has_meetings_today: bool, speech_text: str
    ) -> tuple[str, Optional[str]]:
        """Format done-for-day information for speech.

        Args:
            has_meetings_today: Whether user has meetings today
            speech_text: Pre-generated speech text

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...

    def format_launch_summary(
        self,
        done_info: AlexaDoneForDayInfo,
        primary_meeting: Optional[dict[str, Any]],
        tz: Optional[datetime.tzinfo] = None,
        request_tz: Optional[str] = None,
        now: Optional[datetime.datetime] = None,
        current_meeting: Optional[dict[str, Any]] = None,
    ) -> tuple[str, Optional[str]]:
        """Format launch summary into speech and optional SSML.

        Args:
            done_info: Done-for-day information
            primary_meeting: Next upcoming meeting (or None)
            tz: Timezone object
            request_tz: Timezone string from request
            now: Current datetime
            current_meeting: Currently in-progress meeting (or None)

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...

    def format_morning_summary(self, summary_result: Any) -> tuple[str, Optional[str]]:
        """Format morning summary into speech and optional SSML.

        Args:
            summary_result: MorningSummaryResult object

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...
