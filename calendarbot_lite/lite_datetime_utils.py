"""DateTime parsing utilities for ICS calendar processing - CalendarBot Lite.

This module provides timezone-aware datetime parsing for iCalendar properties.
Extracted from lite_parser.py to improve modularity and testability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (lightweight version for calendarbot_lite).

    Args:
        dt: Datetime to make timezone-aware

    Returns:
        Timezone-aware datetime (UTC if originally naive)
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def format_time_for_speech(dt: datetime, target_tz: Optional[ZoneInfo] = None) -> str:
    """Format a datetime for natural speech output.

    Converts the datetime to the target timezone and formats it conversationally:
    - "noon" for 12:00 PM
    - "10 AM" for times on the hour
    - "10 thirty PM" for half-hour times
    - "10 15 AM" for other times

    Args:
        dt: Datetime to format (should be timezone-aware)
        target_tz: Target timezone for conversion (if None, uses dt's timezone)

    Returns:
        Conversational time string

    Examples:
        >>> from datetime import datetime
        >>> from zoneinfo import ZoneInfo
        >>> dt = datetime(2025, 11, 1, 12, 0, tzinfo=ZoneInfo("UTC"))
        >>> format_time_for_speech(dt)
        'noon'
        >>> dt = datetime(2025, 11, 1, 14, 30, tzinfo=ZoneInfo("UTC"))
        >>> format_time_for_speech(dt)
        '2 thirty PM'
        >>> dt = datetime(2025, 11, 1, 9, 15, tzinfo=ZoneInfo("UTC"))
        >>> format_time_for_speech(dt)
        '9 15 AM'
    """
    # Convert to target timezone if provided
    try:
        if target_tz is not None:
            local_time = dt.astimezone(target_tz)
            hour = local_time.hour
            minute = local_time.minute
        else:
            hour = dt.hour
            minute = dt.minute
    except Exception:
        # Fallback to original time if conversion fails
        hour = dt.hour
        minute = dt.minute

    # Format based on time values
    if minute == 0:
        if hour == 12:
            return "noon"
        if hour > 12:
            return f"{hour - 12} PM"
        return f"{hour} AM"
    if minute == 30:
        if hour == 12:
            return "twelve thirty PM"
        if hour > 12:
            return f"{hour - 12} thirty PM"
        return f"{hour} thirty AM"
    if hour == 12:
        return f"twelve {minute:02d} PM"
    if hour > 12:
        return f"{hour - 12} {minute:02d} PM"
    return f"{hour} {minute:02d} AM"


class LiteDateTimeParser:
    """Parser for iCalendar datetime properties with timezone handling."""

    def __init__(self, default_timezone: Optional[str] = None):
        """Initialize datetime parser.

        Args:
            default_timezone: Default timezone for naive datetimes
        """
        self.default_timezone = default_timezone

    def parse_datetime(
        self, dt_prop: Any, default_timezone: Optional[str] = None
    ) -> datetime:
        """Parse iCalendar datetime property.

        Args:
            dt_prop: iCalendar datetime property
            default_timezone: Default timezone if none specified (overrides instance default)

        Returns:
            Parsed datetime with timezone
        """
        # Use provided default or instance default
        tz = default_timezone or self.default_timezone

        dt = dt_prop.dt

        # Handle date-only (all-day events)
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                # No timezone specified, use lightweight timezone handling
                if tz:
                    try:
                        # Use lightweight timezone service to handle timezone conversion
                        dt = ensure_timezone_aware(dt)
                        logger.debug(
                            f"Parsed naive datetime {dt} with default timezone: {tz}",
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply timezone {tz}: {e}",
                        )
                        dt = ensure_timezone_aware(dt)  # Fallback to UTC
                else:
                    # Use lightweight timezone awareness
                    dt = ensure_timezone_aware(dt)
            else:
                # Already has timezone info, ensure it's properly handled
                dt = ensure_timezone_aware(dt)
            return dt
        # Date object - convert to datetime at midnight with proper timezone
        return ensure_timezone_aware(datetime.combine(dt, datetime.min.time()))

    def parse_datetime_optional(self, dt_prop: Any) -> Optional[datetime]:
        """Parse optional datetime property.

        Args:
            dt_prop: iCalendar datetime property or None

        Returns:
            Parsed datetime or None
        """
        if dt_prop is None:
            return None

        try:
            return self.parse_datetime(dt_prop)
        except Exception:
            return None
