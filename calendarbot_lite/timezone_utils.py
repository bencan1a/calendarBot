"""Timezone detection and conversion utilities for calendarbot_lite."""

from __future__ import annotations

import datetime
import logging
import os
import time
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
    WINDOWS_TZ_MAP: ClassVar[dict[str, str]] = {
        "Pacific Standard Time": "America/Los_Angeles",
        "Mountain Standard Time": "America/Denver",
        "Central Standard Time": "America/Chicago",
        "Eastern Standard Time": "America/New_York",
        "Alaskan Standard Time": "America/Anchorage",
        "Hawaiian Standard Time": "Pacific/Honolulu",
        "Arizona Standard Time": "America/Phoenix",
        "GMT Standard Time": "Europe/London",
        "Central European Standard Time": "Europe/Paris",
        "W. Europe Standard Time": "Europe/Berlin",
        "China Standard Time": "Asia/Shanghai",
        "Tokyo Standard Time": "Asia/Tokyo",
        "India Standard Time": "Asia/Kolkata",
        "AUS Eastern Standard Time": "Australia/Sydney",
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
            now_utc = datetime.datetime.now(datetime.timezone.utc)
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
                    return dt.astimezone(datetime.timezone.utc)
                # Assume naive datetime is already UTC
                return dt.replace(tzinfo=datetime.timezone.utc)

            except Exception as e:
                logger.warning("Failed to parse CALENDARBOT_TEST_TIME=%r: %s", test_time, e)
                # Fall through to real time

        return datetime.datetime.now(datetime.timezone.utc)

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
