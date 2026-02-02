"""Timezone detection and conversion utilities for calendarbot_lite."""

from __future__ import annotations

import datetime
import logging
import os
import time
from functools import lru_cache
from typing import ClassVar

logger = logging.getLogger(__name__)

# Default fallback timezone for all timezone operations
DEFAULT_SERVER_TIMEZONE = "America/Los_Angeles"  # Pacific timezone


class TimezoneDetector:
    """Detects server timezone using multiple fallback strategies."""

    # Timezone abbreviation to IANA identifier mapping
    TZ_ABBREV_MAP: ClassVar[dict[str, str]] = {
        "PST": "America/Los_Angeles",
        "PDT": "America/Los_Angeles",
        "EST": "America/New_York",
        "EDT": "America/New_York",
        "CST": "America/Chicago",
        "CDT": "America/Chicago",
        "MST": "America/Denver",
        "MDT": "America/Denver",
    }

    # Windows timezone names to IANA identifier mapping
    # Common Windows timezones used in ICS files from Outlook/Exchange
    # https://docs.microsoft.com/en-us/windows-hardware/manufacture/desktop/default-time-zones
    WINDOWS_TZ_MAP: ClassVar[dict[str, str]] = {
        # US Timezones
        "Pacific Standard Time": "America/Los_Angeles",
        "Mountain Standard Time": "America/Denver",
        "Central Standard Time": "America/Chicago",
        "Eastern Standard Time": "America/New_York",
        "Alaskan Standard Time": "America/Anchorage",
        "Hawaiian Standard Time": "Pacific/Honolulu",
        "Arizona Standard Time": "America/Phoenix",
        "US Mountain Standard Time": "America/Phoenix",  # Arizona (no DST)
        "Atlantic Standard Time": "America/Halifax",
        "Newfoundland Standard Time": "America/St_Johns",
        "Saskatchewan Standard Time": "America/Regina",
        # Europe
        "GMT Standard Time": "Europe/London",
        "Central European Standard Time": "Europe/Paris",
        "W. Europe Standard Time": "Europe/Berlin",
        "E. Europe Standard Time": "Europe/Bucharest",
        "FLE Standard Time": "Europe/Helsinki",  # Finland, Latvia, Estonia
        "GTB Standard Time": "Europe/Athens",  # Greece, Turkey, Bulgaria
        "Romance Standard Time": "Europe/Brussels",
        "Central Europe Standard Time": "Europe/Budapest",
        "W. Central Africa Standard Time": "Africa/Lagos",
        "Russian Standard Time": "Europe/Moscow",
        # Asia
        "China Standard Time": "Asia/Shanghai",
        "Tokyo Standard Time": "Asia/Tokyo",
        "Korea Standard Time": "Asia/Seoul",
        "Singapore Standard Time": "Asia/Singapore",
        "Taipei Standard Time": "Asia/Taipei",
        "India Standard Time": "Asia/Kolkata",
        "Sri Lanka Standard Time": "Asia/Colombo",
        "Myanmar Standard Time": "Asia/Yangon",
        "SE Asia Standard Time": "Asia/Bangkok",
        "N. Central Asia Standard Time": "Asia/Novosibirsk",
        "West Asia Standard Time": "Asia/Karachi",
        "Central Asia Standard Time": "Asia/Almaty",
        "Afghanistan Standard Time": "Asia/Kabul",
        "Pakistan Standard Time": "Asia/Karachi",
        "Iran Standard Time": "Asia/Tehran",
        "Arabian Standard Time": "Asia/Dubai",
        "Arabic Standard Time": "Asia/Baghdad",
        "Israel Standard Time": "Asia/Jerusalem",
        "Jordan Standard Time": "Asia/Amman",
        "Syria Standard Time": "Asia/Damascus",
        # Australia & Pacific
        "AUS Eastern Standard Time": "Australia/Sydney",
        "AUS Central Standard Time": "Australia/Darwin",
        "Cen. Australia Standard Time": "Australia/Adelaide",
        "E. Australia Standard Time": "Australia/Brisbane",
        "Tasmania Standard Time": "Australia/Hobart",
        "W. Australia Standard Time": "Australia/Perth",
        "New Zealand Standard Time": "Pacific/Auckland",
        "Fiji Standard Time": "Pacific/Fiji",
        # Americas (South America)
        "Pacific SA Standard Time": "America/Santiago",
        "SA Pacific Standard Time": "America/Bogota",
        "SA Western Standard Time": "America/La_Paz",
        "SA Eastern Standard Time": "America/Cayenne",
        "Argentina Standard Time": "America/Buenos_Aires",
        "E. South America Standard Time": "America/Sao_Paulo",
        "Greenland Standard Time": "America/Nuuk",
        # Africa & Middle East
        "South Africa Standard Time": "Africa/Johannesburg",
        "Egypt Standard Time": "Africa/Cairo",
        "Libya Standard Time": "Africa/Tripoli",
        "Namibia Standard Time": "Africa/Windhoek",
        "Morocco Standard Time": "Africa/Casablanca",
    }

    # Timezone aliases mapping (obsolete/deprecated IANA names to current names)
    # These are common aliases found in older ICS files or legacy systems
    TZ_ALIAS_MAP: ClassVar[dict[str, str]] = {
        # US aliases (obsolete)
        "US/Pacific": "America/Los_Angeles",
        "US/Mountain": "America/Denver",
        "US/Central": "America/Chicago",
        "US/Eastern": "America/New_York",
        "US/Alaska": "America/Anchorage",
        "US/Hawaii": "Pacific/Honolulu",
        "US/Arizona": "America/Phoenix",
        # Other common aliases
        "UTC": "UTC",  # Identity mapping for clarity
        "GMT": "UTC",
        "Etc/UTC": "UTC",
        "Etc/GMT": "UTC",
        "Etc/Universal": "UTC",
        "Universal": "UTC",
        "Zulu": "UTC",
        # Legacy names
        "PST8PDT": "America/Los_Angeles",
        "MST7MDT": "America/Denver",
        "CST6CDT": "America/Chicago",
        "EST5EDT": "America/New_York",
        # Deprecated IANA names (for backward compatibility)
        "Asia/Rangoon": "Asia/Yangon",  # Myanmar
        "America/Godthab": "America/Nuuk",  # Greenland
    }

    # UTC offset (hours) to IANA identifier mapping
    OFFSET_TO_TZ_MAP: ClassVar[dict[int, str]] = {
        -8: "America/Los_Angeles",  # PST
        -7: "America/Los_Angeles",  # PDT
        -6: "America/Chicago",  # CST
        -5: "America/New_York",  # EST (prioritize over Chicago for -5)
        -4: "America/New_York",  # EDT
        0: "UTC",  # Only UTC if actually at UTC offset
    }

    def get_server_timezone(self) -> str:
        """Get the server's local timezone as an IANA timezone identifier.

        This function provides centralized timezone detection for calendarbot_lite.
        It NEVER falls back to UTC - always falls back to Pacific time as specified.

        Returns:
            IANA timezone string (e.g., "America/Los_Angeles", "America/New_York")
            Falls back to "America/Los_Angeles" (Pacific) if detection fails.
        """
        try:
            import zoneinfo

            # Strategy 1: Try system timezone name mapping
            local_tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]

            if local_tz_name in self.TZ_ABBREV_MAP:
                iana_tz = self.TZ_ABBREV_MAP[local_tz_name]
                # Validate it's a real timezone
                zoneinfo.ZoneInfo(iana_tz)
                return iana_tz

            # Strategy 2: Try UTC offset detection
            now_local = datetime.datetime.now()
            now_utc = datetime.datetime.now(datetime.UTC)
            offset = now_local - now_utc.replace(tzinfo=None)

            offset_hours = round(offset.total_seconds() / 3600)

            if offset_hours in self.OFFSET_TO_TZ_MAP:
                detected_tz = self.OFFSET_TO_TZ_MAP[offset_hours]
                # Validate the timezone works
                zoneinfo.ZoneInfo(detected_tz)
                return detected_tz

            logger.warning(
                "Could not detect server timezone, offset=%dh, falling back to Pacific",
                offset_hours,
            )
            return DEFAULT_SERVER_TIMEZONE

        except Exception as e:
            logger.warning("Failed to detect server timezone: %s, falling back to Pacific", e)
            return DEFAULT_SERVER_TIMEZONE

    def get_fallback_timezone(self) -> str:
        """Get the centralized fallback timezone for calendarbot_lite.

        This function provides a single source of truth for timezone fallbacks.
        Used when timezone detection or conversion fails anywhere in the application.

        Returns:
            Always returns "America/Los_Angeles" (Pacific timezone)
        """
        return DEFAULT_SERVER_TIMEZONE


class TimeProvider:
    """Provides current time with test time override support."""

    def __init__(self, detector: TimezoneDetector):
        """Initialize time provider.

        Args:
            detector: TimezoneDetector instance for timezone operations
        """
        self.detector = detector

    def now_utc(self) -> datetime.datetime:
        """Return current UTC time with tzinfo.

        Can be overridden for testing via CALENDARBOT_TEST_TIME environment variable.
        Format: ISO 8601 datetime string (e.g., "2025-10-27T08:20:00-07:00")

        Enhanced with DST detection: If a Pacific timezone offset is provided that doesn't
        match the actual DST status for that date, it will be automatically corrected.

        Returns:
            Current time in UTC with timezone info
        """
        test_time = os.environ.get("CALENDARBOT_TEST_TIME")
        if test_time:
            try:
                # Parse the test time and convert to UTC
                from dateutil import parser as date_parser

                dt = date_parser.isoparse(test_time)

                # Enhance with DST detection for Pacific timezone
                dt = self._enhance_datetime_with_dst_detection(dt, test_time)

                # Convert to UTC
                if dt.tzinfo is not None:
                    return dt.astimezone(datetime.UTC)
                # Assume naive datetime is already UTC
                return dt.replace(tzinfo=datetime.UTC)

            except Exception as e:
                logger.warning("Failed to parse CALENDARBOT_TEST_TIME=%r: %s", test_time, e)
                # Fall through to real time

        return datetime.datetime.now(datetime.UTC)

    def _enhance_datetime_with_dst_detection(
        self,
        dt: datetime.datetime,
        original_test_time: str,
    ) -> datetime.datetime:
        """Enhance datetime with DST detection for Pacific timezone.

        If the provided timezone offset doesn't match the actual DST status for that date,
        automatically correct it to the proper DST/PST timezone.

        Args:
            dt: Parsed datetime with timezone info
            original_test_time: Original test time string for logging

        Returns:
            Datetime with corrected timezone if applicable
        """
        try:
            # Check if this looks like a Pacific timezone (common offsets)
            if dt.tzinfo is not None:
                utc_offset = dt.utcoffset()
                if utc_offset is None:
                    return dt

                offset_seconds = utc_offset.total_seconds()
                offset_hours = offset_seconds / 3600

                # Pacific timezone offsets: PST = -8, PDT = -7
                if offset_hours in (-8, -7):
                    import zoneinfo

                    pacific_tz = zoneinfo.ZoneInfo("America/Los_Angeles")

                    # Create a naive datetime and localize it to Pacific timezone
                    naive_dt = dt.replace(tzinfo=None)
                    pacific_dt = naive_dt.replace(tzinfo=pacific_tz)

                    # Get the actual offset that Pacific timezone should have on this date
                    actual_utc_offset = pacific_dt.utcoffset()
                    if actual_utc_offset is None:
                        return dt

                    actual_offset_seconds = actual_utc_offset.total_seconds()
                    actual_offset_hours = actual_offset_seconds / 3600

                    # Check if the provided offset differs from the actual DST status
                    if offset_hours != actual_offset_hours:
                        dst_status = "PDT" if actual_offset_hours == -7 else "PST"
                        provided_status = "PDT" if offset_hours == -7 else "PST"

                        logger.debug(
                            "DST Auto-correction: %s uses %s but %s should be %s. "
                            "Correcting %+.0f:00 → %+.0f:00",
                            original_test_time,
                            provided_status,
                            dt.date(),
                            dst_status,
                            offset_hours,
                            actual_offset_hours,
                        )

                        # Return the corrected datetime with proper Pacific timezone
                        return pacific_dt

                    # Offset is correct, but still convert to proper Pacific timezone object
                    # for consistency (in case it was using a simple UTC offset)
                    return pacific_dt

        except Exception as e:
            logger.warning("DST detection failed for %s: %s", original_test_time, e)
            # Fall back to original datetime

        return dt


# Singleton instances for global use
_detector = TimezoneDetector()
_time_provider = TimeProvider(_detector)


def get_server_timezone() -> str:
    """Get the server's local timezone (convenience function).

    Returns:
        IANA timezone string
    """
    return _detector.get_server_timezone()


def get_fallback_timezone() -> str:
    """Get the fallback timezone (convenience function).

    Returns:
        Default fallback timezone string
    """
    return _detector.get_fallback_timezone()


def get_default_timezone(fallback: str = DEFAULT_SERVER_TIMEZONE) -> str:
    """Get default timezone from environment with validation.

    This is the canonical implementation for getting the configured default timezone.
    It checks the CALENDARBOT_DEFAULT_TIMEZONE environment variable first,
    then falls back to the provided fallback timezone.

    Args:
        fallback: Fallback timezone if not configured or invalid
                  (default: America/Los_Angeles)

    Returns:
        Valid IANA timezone string

    Note:
        This function validates the timezone using zoneinfo.ZoneInfo and falls back
        to the provided fallback timezone if the configured timezone is invalid.
    """
    import zoneinfo

    # Get timezone from environment
    timezone = os.environ.get("CALENDARBOT_DEFAULT_TIMEZONE", fallback)

    # Validate timezone
    try:
        zoneinfo.ZoneInfo(timezone)
        return timezone
    except Exception:
        logger.warning(
            "Invalid timezone %r, falling back to %r", timezone, fallback, exc_info=True
        )
        return fallback


def now_utc() -> datetime.datetime:
    """Get current UTC time (convenience function).

    Returns:
        Current time in UTC
    """
    return _time_provider.now_utc()


def windows_tz_to_iana(windows_tz: str) -> str | None:
    """Convert Windows timezone name to IANA timezone identifier.

    Args:
        windows_tz: Windows timezone name (e.g., "Mountain Standard Time")

    Returns:
        IANA timezone identifier (e.g., "America/Denver") or None if not found
    """
    return _detector.WINDOWS_TZ_MAP.get(windows_tz)


def resolve_timezone_alias(tz_name: str) -> str:
    """Resolve timezone alias to canonical IANA timezone identifier.

    Handles obsolete timezone names (e.g., US/Pacific -> America/Los_Angeles)
    and common aliases. If the timezone is not an alias, returns it unchanged.

    Args:
        tz_name: Timezone name or alias (e.g., "US/Pacific", "America/Los_Angeles")

    Returns:
        Canonical IANA timezone identifier

    Examples:
        >>> resolve_timezone_alias("US/Pacific")
        'America/Los_Angeles'
        >>> resolve_timezone_alias("America/Los_Angeles")
        'America/Los_Angeles'
        >>> resolve_timezone_alias("GMT")
        'UTC'
    """
    return _detector.TZ_ALIAS_MAP.get(tz_name, tz_name)


def normalize_timezone_name(tz_str: str) -> str | None:
    """Normalize timezone string to canonical IANA timezone identifier.

    This function provides comprehensive timezone name resolution:
    1. Checks if it's a Windows timezone name
    2. Checks if it's a timezone alias
    3. Validates the timezone with zoneinfo
    4. Returns None if the timezone cannot be resolved

    Args:
        tz_str: Timezone string (Windows name, alias, or IANA identifier)

    Returns:
        Canonical IANA timezone identifier or None if invalid

    Examples:
        >>> normalize_timezone_name("Pacific Standard Time")
        'America/Los_Angeles'
        >>> normalize_timezone_name("US/Pacific")
        'America/Los_Angeles'
        >>> normalize_timezone_name("America/Los_Angeles")
        'America/Los_Angeles'
        >>> normalize_timezone_name("Invalid/Timezone")
        None
    """
    if not tz_str:
        return None

    import zoneinfo

    # Try Windows timezone conversion first
    try:
        windows_tz = windows_tz_to_iana(tz_str)
        if windows_tz:
            # Validate the mapped timezone
            zoneinfo.ZoneInfo(windows_tz)
            return windows_tz
    except Exception:
        logger.warning("Failed during Windows timezone conversion for: %r", tz_str)

    # Try timezone alias resolution
    try:
        resolved_tz = resolve_timezone_alias(tz_str)
        # Validate the resolved timezone
        zoneinfo.ZoneInfo(resolved_tz)
        return resolved_tz
    except Exception:
        logger.warning("Failed during alias resolution or zoneinfo validation for: %r", tz_str)
        return None


def convert_to_server_tz(dt: datetime.datetime) -> datetime.datetime:
    """Convert a datetime to the server's local timezone.

    This is a convenience function for the common pattern of converting
    UTC or other timezone datetimes to the server's local timezone.

    Args:
        dt: Datetime to convert (should be timezone-aware)

    Returns:
        Datetime in server's local timezone

    Examples:
        >>> import datetime
        >>> from zoneinfo import ZoneInfo
        >>> utc_time = datetime.datetime(2025, 11, 1, 20, 0, tzinfo=datetime.UTC)
        >>> local_time = convert_to_server_tz(utc_time)
        >>> # Returns time converted to server's timezone (e.g., Pacific)
    """
    import zoneinfo

    server_tz_str = get_server_timezone()
    server_tz = zoneinfo.ZoneInfo(server_tz_str)
    return dt.astimezone(server_tz)


def convert_to_timezone(dt: datetime.datetime, tz_str: str) -> datetime.datetime:
    """Convert a datetime to a specific timezone.

    Args:
        dt: Datetime to convert (should be timezone-aware)
        tz_str: IANA timezone identifier (e.g., "America/Los_Angeles")

    Returns:
        Datetime in the specified timezone

    Raises:
        zoneinfo.ZoneInfoNotFoundError: If timezone identifier is invalid

    Examples:
        >>> import datetime
        >>> from zoneinfo import ZoneInfo
        >>> utc_time = datetime.datetime(2025, 11, 1, 20, 0, tzinfo=datetime.UTC)
        >>> ny_time = convert_to_timezone(utc_time, "America/New_York")
    """
    import zoneinfo

    target_tz = zoneinfo.ZoneInfo(tz_str)
    return dt.astimezone(target_tz)


@lru_cache(maxsize=20)
def parse_request_timezone(tz_str: str | None) -> datetime.tzinfo:
    """Parse timezone string from request, with fallback to UTC.

    This utility consolidates the common pattern in Alexa handlers where a timezone
    string is parsed from a request parameter and needs fallback handling.

    Args:
        tz_str: Optional IANA timezone identifier (e.g., "America/Los_Angeles")
                If None or invalid, falls back to UTC

    Returns:
        Timezone info object (either ZoneInfo or datetime.UTC)

    Examples:
        >>> tz = parse_request_timezone("America/New_York")
        >>> tz = parse_request_timezone(None)  # Returns UTC
        >>> tz = parse_request_timezone("Invalid/Timezone")  # Returns UTC with warning
    """
    if not tz_str:
        return datetime.UTC

    try:
        import zoneinfo

        return zoneinfo.ZoneInfo(tz_str)
    except Exception:
        logger.warning("Invalid timezone %r, falling back to UTC", tz_str)
        return datetime.UTC
