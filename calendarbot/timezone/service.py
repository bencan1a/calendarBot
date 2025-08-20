"""Core timezone service for CalendarBot.

Provides centralized timezone handling with zoneinfo + pytz fallback strategy.
Eliminates hardcoded timezone strings and standardizes timezone operations.
"""

import importlib.util
import logging
from datetime import datetime, timezone as dt_timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Server timezone identifier (Pacific by default)
SERVER_TZ_NAME = "America/Los_Angeles"

# Check for timezone library availability
ZONEINFO_AVAILABLE = importlib.util.find_spec("zoneinfo") is not None
PYTZ_AVAILABLE = importlib.util.find_spec("pytz") is not None

# Import timezone libraries at top level if available
ZoneInfo = None
if ZONEINFO_AVAILABLE:
    from zoneinfo import ZoneInfo

pytz = None
if PYTZ_AVAILABLE:
    import pytz


class TimezoneError(Exception):
    """Raised when timezone operations fail."""


class TimezoneService:
    """Centralized timezone service for CalendarBot.

    Provides standardized timezone operations using zoneinfo with pytz fallback.
    All timezone operations should go through this service to ensure consistency.
    """

    def __init__(self) -> None:
        """Initialize timezone service."""
        self._server_tz: Optional[Any] = None
        self._validate_timezone_support()

    def _validate_timezone_support(self) -> None:
        """Validate that timezone libraries are available.

        Raises:
            TimezoneError: If no timezone library is available.
        """
        if not ZONEINFO_AVAILABLE and not PYTZ_AVAILABLE:
            raise TimezoneError(
                "No timezone library available. Install Python 3.9+ for zoneinfo "
                "or install pytz package."
            )

        if ZONEINFO_AVAILABLE:
            logger.info("Using zoneinfo for timezone handling")
        else:
            logger.info("Using pytz fallback for timezone handling")

    def get_server_timezone(self) -> Any:
        """Get server timezone object.

        Returns standardized server timezone (America/Los_Angeles) using
        the best available timezone library.

        Returns:
            Timezone object for server timezone.

        Raises:
            TimezoneError: If server timezone cannot be created.
        """
        if self._server_tz is not None:
            return self._server_tz

        try:
            if ZONEINFO_AVAILABLE and ZoneInfo is not None:
                self._server_tz = ZoneInfo(SERVER_TZ_NAME)
            elif PYTZ_AVAILABLE and pytz is not None:
                self._server_tz = pytz.timezone(SERVER_TZ_NAME)
            else:
                # Fallback to UTC offset (not ideal but functional)
                self._server_tz = dt_timezone.utc
                logger.warning(
                    "No timezone library available, using UTC. "
                    "Install zoneinfo or pytz for proper timezone support."
                )

            logger.debug(f"Created server timezone: {self._server_tz}")
            return self._server_tz

        except Exception as e:
            raise TimezoneError(f"Failed to create server timezone: {e}") from e

    def convert_to_server_timezone(self, dt: datetime) -> datetime:
        """Convert datetime to server timezone.

        Handles timezone-naive datetimes by assuming they are in server time.
        Properly converts timezone-aware datetimes from other timezones.

        Args:
            dt: Datetime to convert to server timezone.

        Returns:
            Datetime converted to server timezone.

        Raises:
            TimezoneError: If conversion fails.
            TypeError: If dt is not a datetime object.
        """
        if not isinstance(dt, datetime):
            raise TypeError(f"Expected datetime object, got {type(dt)}")

        try:
            server_tz = self.get_server_timezone()

            if dt.tzinfo is None:
                # Timezone-naive datetime - assume it's already in server time
                logger.debug(f"Converting timezone-naive datetime to server: {dt}")
                if ZONEINFO_AVAILABLE:
                    return dt.replace(tzinfo=server_tz)
                if PYTZ_AVAILABLE and hasattr(server_tz, "localize"):
                    return server_tz.localize(dt)
                return dt.replace(tzinfo=server_tz)

            # Timezone-aware datetime - convert to server timezone
            server_dt = dt.astimezone(server_tz)

            # Handle Australian timezone special case
            # Check if original timezone looks like Australian timezone
            if hasattr(dt.tzinfo, "zone") and "Australia/" in str(getattr(dt.tzinfo, "zone", "")):
                logger.debug("Detected Australian timezone, applying date correction logic")
                # The conversion itself handles the timezone math correctly
                # No additional +1 day correction needed with proper timezone libraries

            return server_dt

        except Exception as e:
            raise TimezoneError(f"Failed to convert datetime to server timezone: {e}") from e

    def ensure_timezone_aware(self, dt: datetime, fallback_tz: Optional[Any] = None) -> datetime:
        """Ensure datetime has timezone information.

        If datetime is timezone-naive, applies fallback timezone (server by default).
        If datetime is timezone-aware, returns it unchanged.

        Args:
            dt: Datetime to ensure has timezone information.
            fallback_tz: Timezone to apply if dt is naive. Defaults to server timezone.

        Returns:
            Timezone-aware datetime.

        Raises:
            TimezoneError: If timezone operation fails.
            TypeError: If dt is not a datetime object.
        """
        if not isinstance(dt, datetime):
            raise TypeError(f"Expected datetime object, got {type(dt)}")

        if dt.tzinfo is not None:
            return dt

        try:
            tz = fallback_tz or self.get_server_timezone()

            if ZONEINFO_AVAILABLE:
                return dt.replace(tzinfo=tz)
            if PYTZ_AVAILABLE and hasattr(tz, "localize"):
                return tz.localize(dt)
            return dt.replace(tzinfo=tz)

        except Exception as e:
            raise TimezoneError(f"Failed to make datetime timezone-aware: {e}") from e

    def now_server_timezone(self) -> datetime:
        """Get current time in server timezone.

        Returns:
            Current datetime in server timezone.

        Raises:
            TimezoneError: If server timezone cannot be determined.
        """
        try:
            server_tz = self.get_server_timezone()
            return datetime.now(server_tz)

        except Exception as e:
            raise TimezoneError(f"Failed to get current server time: {e}") from e

    def parse_datetime_with_timezone(
        self, iso_string: str, fallback_tz: Optional[Any] = None
    ) -> datetime:
        """Parse ISO datetime string with timezone handling.

        Parses ISO 8601 datetime strings and ensures timezone awareness.
        If the string contains timezone info, uses it. Otherwise applies fallback timezone.

        Args:
            iso_string: ISO 8601 datetime string to parse.
            fallback_tz: Timezone to apply if string has no timezone info.
                        Defaults to server timezone.

        Returns:
            Parsed timezone-aware datetime.

        Raises:
            TimezoneError: If parsing or timezone operations fail.
            TypeError: If iso_string is not a valid datetime string.
        """
        if not isinstance(iso_string, str):
            raise TypeError(f"Expected string, got {type(iso_string)}")

        try:
            # Try parsing with built-in fromisoformat (Python 3.7+)
            try:
                dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
                logger.debug(f"Parsed ISO datetime: {iso_string} -> {dt}")
            except ValueError:
                # Fallback to manual parsing for edge cases
                # Remove 'Z' suffix and add UTC timezone
                if iso_string.endswith("Z"):
                    iso_string = iso_string[:-1] + "+00:00"
                dt = datetime.fromisoformat(iso_string)

            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = self.ensure_timezone_aware(dt, fallback_tz)

            return dt

        except Exception as e:
            raise TimezoneError(f"Failed to parse ISO datetime '{iso_string}': {e}") from e


# Global service instance (using module-level variable instead of global statement)
_timezone_service: Optional[TimezoneService] = None


def get_timezone_service() -> TimezoneService:
    """Get global timezone service instance.

    Returns:
        Singleton TimezoneService instance.
    """
    # Use module-level variable access instead of global statement
    if "_timezone_service" not in globals() or globals()["_timezone_service"] is None:
        globals()["_timezone_service"] = TimezoneService()
    return globals()["_timezone_service"]


# Convenience functions for direct use
def get_server_timezone() -> Any:
    """Get server timezone object."""
    return get_timezone_service().get_server_timezone()


def convert_to_server_timezone(dt: datetime) -> datetime:
    """Convert datetime to server timezone."""
    return get_timezone_service().convert_to_server_timezone(dt)


def ensure_timezone_aware(dt: datetime, fallback_tz: Optional[Any] = None) -> datetime:
    """Ensure datetime has timezone information."""
    return get_timezone_service().ensure_timezone_aware(dt, fallback_tz)


def now_server_timezone() -> datetime:
    """Get current time in server timezone."""
    return get_timezone_service().now_server_timezone()


def parse_datetime_with_timezone(iso_string: str, fallback_tz: Optional[Any] = None) -> datetime:
    """Parse ISO datetime string with timezone handling."""
    return get_timezone_service().parse_datetime_with_timezone(iso_string, fallback_tz)
