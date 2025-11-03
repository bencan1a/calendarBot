"""Protocol definitions for Alexa handler dependencies.

This module defines Protocol types for better type safety in Alexa handlers,
replacing generic 'Any' type hints with explicit interface contracts.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional, Protocol


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

    def __call__(self) -> datetime.tzinfo:
        """Get server timezone.

        Returns:
            Server timezone info
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
        self, meeting_data: dict[str, Any]
    ) -> tuple[str, Optional[str]]:
        """Format next meeting data for speech.

        Args:
            meeting_data: Meeting data dict with subject, time, etc.

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
        self, done_info: dict[str, Any]
    ) -> tuple[str, Optional[str]]:
        """Format done-for-day information for speech.

        Args:
            done_info: Done-for-day data with has_meetings_today, etc.

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...

    def format_morning_summary(
        self, summary_data: dict[str, Any]
    ) -> tuple[str, Optional[str]]:
        """Format morning summary for speech.

        Args:
            summary_data: Morning summary data

        Returns:
            Tuple of (speech_text, optional_ssml)
        """
        ...
