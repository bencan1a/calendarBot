"""DateTime parsing utilities for ICS calendar processing - CalendarBot Lite.

This module provides timezone-aware datetime parsing for iCalendar properties.
Extracted from lite_parser.py to improve modularity and testability.
"""

import logging
from datetime import UTC, datetime
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
        return dt.replace(tzinfo=UTC)
    return dt


def serialize_datetime_utc(dt: datetime) -> str:
    """Serialize datetime to ISO 8601 UTC string with Z suffix.

    This function replaces manual string concatenation (dt.isoformat() + "Z")
    with proper datetime handling that validates timezone awareness and ensures
    consistent UTC serialization.

    Args:
        dt: Datetime to serialize (timezone-aware or naive)

    Returns:
        ISO 8601 string with Z suffix (e.g., "2024-11-04T16:30:00Z")

    Raises:
        ValueError: If datetime is None

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=timezone.utc)
        >>> serialize_datetime_utc(dt)
        '2024-11-04T16:30:00Z'
        >>> dt_naive = datetime(2024, 11, 4, 16, 30, 0)
        >>> serialize_datetime_utc(dt_naive)
        '2024-11-04T16:30:00Z'
    """
    if dt is None:
        raise ValueError("Cannot serialize None datetime")

    # Convert to UTC if timezone-aware, assume UTC if naive
    dt_utc = dt.astimezone(UTC) if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    # Use proper ISO format with Z suffix
    return dt_utc.isoformat().replace("+00:00", "Z")


def serialize_datetime_optional(dt: Optional[datetime]) -> Optional[str]:
    """Serialize optional datetime to ISO 8601 UTC string, returning None if input is None.

    This is a convenience wrapper around serialize_datetime_utc() for handling
    optional datetimes without explicit null checks in calling code.

    Args:
        dt: Optional datetime to serialize (timezone-aware, naive, or None)

    Returns:
        ISO 8601 string with Z suffix if dt is not None, otherwise None

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=timezone.utc)
        >>> serialize_datetime_optional(dt)
        '2024-11-04T16:30:00Z'
        >>> serialize_datetime_optional(None)
        None
    """
    return serialize_datetime_utc(dt) if dt is not None else None


def format_time_cross_platform(dt: datetime, suffix: str = "") -> str:
    """Format time in 12-hour format without leading zeros (cross-platform).

    This function provides cross-platform compatible time formatting that works
    on both Unix/Linux and Windows systems. The Unix-specific strftime format
    code %-I is not supported on Windows, causing runtime errors.

    Args:
        dt: Datetime to format
        suffix: Optional suffix to append (e.g., " UTC")

    Returns:
        Time string in format "H:MM AM/PM" without leading zeros on hour
        Examples: "9:30 am", "12:45 pm", "10:00 am utc"

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 11, 4, 9, 30)
        >>> format_time_cross_platform(dt)
        '9:30 am'
        >>> dt = datetime(2025, 11, 4, 14, 45)
        >>> format_time_cross_platform(dt)
        '2:45 pm'
        >>> dt = datetime(2025, 11, 4, 9, 30)
        >>> format_time_cross_platform(dt, " UTC")
        '9:30 am utc'
    """
    # Convert to 12-hour format
    hour = dt.hour % 12 or 12  # Convert 0 to 12, keep 1-12 as is
    minute = dt.minute
    am_pm = "am" if dt.hour < 12 else "pm"

    # Format without leading zeros
    time_str = f"{hour}:{minute:02d} {am_pm}"

    # Add suffix if provided
    if suffix:
        time_str += suffix.lower()

    return time_str


def format_time_for_speech(
    dt: datetime, target_tz: Optional[ZoneInfo] = None, use_ssml: bool = False
) -> str:
    """Format a datetime for natural speech output.

    Converts the datetime to the target timezone and formats it for speech.
    Can return either plain text (for non-SSML responses) or SSML with <say-as> tag
    (for SSML responses where Alexa will handle natural pronunciation).

    Args:
        dt: Datetime to format (should be timezone-aware)
        target_tz: Target timezone for conversion (if None, uses dt's timezone)
        use_ssml: If True, wrap time in SSML <say-as> tag; if False, return plain text

    Returns:
        Time string formatted for speech (plain text or SSML depending on use_ssml)

    Examples:
        >>> from datetime import datetime
        >>> from zoneinfo import ZoneInfo
        >>> dt = datetime(2025, 11, 1, 12, 0, tzinfo=ZoneInfo("UTC"))
        >>> format_time_for_speech(dt)
        'noon'
        >>> format_time_for_speech(dt, use_ssml=True)
        'noon'
        >>> dt = datetime(2025, 11, 1, 14, 30, tzinfo=ZoneInfo("UTC"))
        >>> format_time_for_speech(dt)
        '2:30 pm'
        >>> format_time_for_speech(dt, use_ssml=True)
        '<say-as interpret-as="time">2:30pm</say-as>'
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

    # Special case for noon - natural in both formats
    if hour == 12 and minute == 0:
        return "noon"

    # Convert to 12-hour format
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12

    # Use lowercase am/pm
    period = "am" if hour < 12 else "pm"

    if use_ssml:
        # SSML format: no space before am/pm per Alexa SSML spec
        time_str = f"{display_hour}:{minute:02d}{period}"
        return f'<say-as interpret-as="time">{time_str}</say-as>'
    # Plain text format: space before am/pm for readability
    return f"{display_hour}:{minute:02d} {period}"


class TimezoneParser:
    """Parse datetime strings with timezone handling.

    Handles TZID formats like: TZID=Pacific Standard Time:20251031T090000
    Supports Windows timezone names with automatic conversion to IANA format.
    """

    def parse_datetime_with_tzid(self, datetime_str: str) -> datetime:
        """Parse datetime string with TZID prefix.

        Args:
            datetime_str: String in format "TZID=<timezone>:<datetime>"
                         Example: "TZID=Pacific Standard Time:20251031T090000"

        Returns:
            Datetime in UTC

        Raises:
            ValueError: If parsing fails
        """
        if not datetime_str.startswith("TZID="):
            raise ValueError(f"Expected TZID prefix, got: {datetime_str}")

        try:
            # Extract TZID and datetime parts
            # Format: TZID=<timezone>:<datetime>
            # Find the colon before the datetime (datetime starts with year: 20XX)
            colon_idx = datetime_str.rfind(":", 0, datetime_str.find(":2"))
            if colon_idx == -1:
                # Fallback: simple split
                tzid_part, dt_part = datetime_str.split(":", 1)
            else:
                tzid_part = datetime_str[:colon_idx]
                dt_part = datetime_str[colon_idx + 1 :]

            # Extract timezone ID
            tzid = tzid_part.replace("TZID=", "").strip()

            # Parse datetime part (remove Z suffix if present)
            dt_str_clean = dt_part.rstrip("Z")

            # Try multiple datetime formats for robustness
            dt_naive = None
            for fmt in [
                "%Y%m%dT%H%M%S",  # Standard: 20251031T090000
                "%Y%m%dT%H%M",  # Without seconds: 20251031T0900
                "%Y-%m-%dT%H:%M:%S",  # ISO format: 2025-10-31T09:00:00
                "%Y-%m-%d %H:%M:%S",  # Space separated: 2025-10-31 09:00:00
            ]:
                try:
                    dt_naive = datetime.strptime(dt_str_clean, fmt)
                    break
                except ValueError:
                    continue

            if dt_naive is None:
                raise ValueError(f"Unable to parse datetime format: {dt_str_clean}")

            # Handle UTC explicitly
            if tzid == "UTC" or dt_part.endswith("Z"):
                return dt_naive.replace(tzinfo=UTC)

            # Use comprehensive timezone normalization (handles Windows TZ, aliases, etc.)
            from calendarbot_lite.core.timezone_utils import normalize_timezone_name

            iana_tz = normalize_timezone_name(tzid)
            if iana_tz is None:
                # Log warning but fallback gracefully
                logger.warning("Unknown timezone %r in %r, assuming UTC", tzid, datetime_str)
                return dt_naive.replace(tzinfo=UTC)

            # Apply timezone using zoneinfo (Python 3.12+ standard library)
            tz = ZoneInfo(iana_tz)
            dt_with_tz = dt_naive.replace(tzinfo=tz)
            return dt_with_tz.astimezone(UTC)

        except Exception as e:
            # Fallback to UTC if timezone parsing fails
            logger.warning("Failed to parse TZID datetime %s: %s, assuming UTC", datetime_str, e)
            # Try to extract just the datetime part
            try:
                dt_str = datetime_str.split(":")[-1].rstrip("Z")
                dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
                return dt.replace(tzinfo=UTC)
            except Exception:
                raise ValueError(f"Unable to parse datetime: {datetime_str}") from e

    def parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string in various formats.

        Handles:
        - TZID format: TZID=Pacific Standard Time:20251031T090000
        - ISO format: 2025-06-23T08:30:00Z
        - RRULE format: 20250623T083000

        Args:
            datetime_str: Datetime string in supported format

        Returns:
            Parsed datetime (UTC if timezone specified)

        Raises:
            ValueError: If format is invalid
        """
        # Handle TZID format
        if datetime_str.startswith("TZID="):
            return self.parse_datetime_with_tzid(datetime_str)

        # Handle standard formats
        dt_str = datetime_str.rstrip("Z")
        has_utc_marker = datetime_str.endswith("Z")

        # Try common datetime formats
        for fmt in [
            "%Y%m%dT%H%M%S",  # 20250623T083000
            "%Y-%m-%dT%H:%M:%S",  # 2025-06-23T08:30:00
            "%Y%m%d",  # 20250623
            "%Y-%m-%d",  # 2025-06-23
        ]:
            try:
                dt = datetime.strptime(dt_str, fmt)
                if has_utc_marker:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:
                continue

        raise ValueError(f"Unable to parse datetime: {datetime_str}")


class LiteDateTimeParser:
    """Parser for iCalendar datetime properties with timezone handling."""

    def __init__(self, default_timezone: Optional[str] = None):
        """Initialize datetime parser.

        Args:
            default_timezone: Default timezone for naive datetimes
        """
        self.default_timezone = default_timezone

    def parse_datetime(self, dt_prop: Any, default_timezone: Optional[str] = None) -> datetime:
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
                        logger.debug("Parsed naive datetime %s with default timezone: %s", dt, tz)
                    except Exception as e:
                        logger.warning("Failed to apply timezone %s: %s", tz, e)
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
