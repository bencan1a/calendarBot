"""
Timezone package for CalendarBot.

Provides centralized timezone handling with a clean public API.
Uses zoneinfo + pytz fallback strategy for robust timezone operations.

Example usage:
    >>> from calendarbot.timezone import convert_to_server_timezone, now_server_timezone
    >>> from datetime import datetime
    >>>
    >>> # Get current time in server timezone
    >>> current_time = now_server_timezone()
    >>>
    >>> # Convert a datetime to server timezone
    >>> dt = datetime(2023, 12, 25, 10, 0, 0)
    >>> server_dt = convert_to_server_timezone(dt)
    >>>
    >>> # Ensure timezone awareness
    >>> naive_dt = datetime.now()
    >>> aware_dt = ensure_timezone_aware(naive_dt)
"""

from .service import (
    TimezoneError,
    TimezoneService,
    convert_to_server_timezone,
    ensure_timezone_aware,
    get_server_timezone,
    get_timezone_service,
    now_server_timezone,
    parse_datetime_with_timezone,
)

__all__ = [
    "TimezoneError",
    "TimezoneService",
    "convert_to_server_timezone",
    "ensure_timezone_aware",
    "get_server_timezone",
    "get_timezone_service",
    "now_server_timezone",
    "parse_datetime_with_timezone",
]
