"""Shared utilities for Alexa handlers.

This module provides shared computation functions that can be used across multiple
Alexa handlers, eliminating the need for handlers to instantiate other handlers
just to access their computation logic.
"""

import datetime
import logging
from collections.abc import Callable
from typing import Any, Optional

from .alexa_types import AlexaDoneForDayInfo
from .lite_models import LiteCalendarEvent
from .timezone_utils import parse_request_timezone

logger = logging.getLogger(__name__)


async def compute_done_for_day_info(
    events: tuple[LiteCalendarEvent, ...],
    request_tz: Optional[str],
    now: datetime.datetime,
    filter_events_fn: Callable,
) -> dict[str, Any]:
    """Compute done-for-day information from event window.

    This function calculates whether the user has meetings today and when
    their last meeting ends, using pipeline-based event filtering.

    Args:
        events: Tuple of LiteCalendarEvent objects to analyze
        request_tz: Optional timezone string (IANA format) for date comparison
        now: Current UTC time
        filter_events_fn: Async function to filter events (e.g., _filter_events_with_pipeline)

    Returns:
        Dictionary with:
        - has_meetings_today (bool): Whether user has meetings today
        - last_meeting_start_utc (datetime | None): Start time of last meeting
        - last_meeting_end_utc (datetime | None): End time of last meeting
        - meetings_count (int): Number of meetings found today
    """
    # Parse timezone or fallback to UTC
    tz = parse_request_timezone(request_tz)

    # Get today's time window in the target timezone
    today_start = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + datetime.timedelta(days=1)

    # Use pipeline stages to filter events for today (with skipped events removed)
    filtered_events = await filter_events_fn(
        events=events,
        window_start=today_start,
        window_end=today_end,
        apply_skipped_filter=True,
        apply_time_window_filter=True,
    )

    # Find the latest end time from filtered events
    latest_end_utc = None
    latest_start_utc = None
    meetings_found = len(filtered_events)

    for ev in filtered_events:
        try:
            # Get event start and end times
            start = ev.start.date_time
            end_utc = ev.end.date_time

            # Handle both datetime and date objects (for all-day events)
            if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
                # All-day event: convert date to datetime at start of day in local timezone, then to UTC
                local_start = datetime.datetime.combine(start, datetime.time.min, tzinfo=tz)
                start = local_start.astimezone(datetime.timezone.utc)
            elif not isinstance(start, datetime.datetime):
                continue

            if isinstance(end_utc, datetime.date) and not isinstance(end_utc, datetime.datetime):
                # All-day event: convert date to datetime at start of day in local timezone, then to UTC
                local_end = datetime.datetime.combine(end_utc, datetime.time.min, tzinfo=tz)
                end_utc = local_end.astimezone(datetime.timezone.utc)
            elif not isinstance(end_utc, datetime.datetime):
                continue

            # Track latest end time
            if latest_end_utc is None or end_utc > latest_end_utc:
                latest_end_utc = end_utc
                latest_start_utc = start

        except (AttributeError, TypeError, ValueError) as e:
            logger.warning("Error processing event for done-for-day: %s", e)
            continue
        except Exception as e:
            logger.error("Unexpected error processing event: %s", e, exc_info=True)
            continue

    # Return raw data (handlers will format as needed)
    return {
        "has_meetings_today": meetings_found > 0,
        "last_meeting_start_utc": latest_start_utc,
        "last_meeting_end_utc": latest_end_utc,
        "meetings_count": meetings_found,
        "timezone": tz,
    }


def format_done_for_day_result(
    computation_result: dict[str, Any],
    iso_serializer: Optional[Callable] = None,
) -> AlexaDoneForDayInfo:
    """Format done-for-day computation result for Alexa response.

    Args:
        computation_result: Result from compute_done_for_day_info()
        iso_serializer: Optional function to serialize datetime to ISO string

    Returns:
        Formatted AlexaDoneForDayInfo with ISO strings suitable for Alexa response.
    """
    latest_start_utc = computation_result["last_meeting_start_utc"]
    latest_end_utc = computation_result["last_meeting_end_utc"]
    tz = computation_result["timezone"]

    result: AlexaDoneForDayInfo = {
        "has_meetings_today": computation_result["has_meetings_today"],
        "last_meeting_start_iso": (
            iso_serializer(latest_start_utc)
            if iso_serializer and latest_start_utc
            else (latest_start_utc.isoformat() + "Z" if latest_start_utc else None)
        ),
        "last_meeting_end_iso": (
            iso_serializer(latest_end_utc)
            if iso_serializer and latest_end_utc
            else (latest_end_utc.isoformat() + "Z" if latest_end_utc else None)
        ),
        "last_meeting_end_local_iso": (
            latest_end_utc.astimezone(tz).isoformat() if latest_end_utc else None
        ),
        "note": None,
    }

    return result


async def compute_last_meeting_end(
    events: tuple[LiteCalendarEvent, ...],
    request_tz: Optional[str],
    now: datetime.datetime,
    filter_events_fn: Callable,
) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    """Compute the last meeting end time for today.

    Simplified version that returns just the end times (UTC and local).

    Args:
        events: Tuple of LiteCalendarEvent objects to analyze
        request_tz: Optional timezone string for date comparison
        now: Current UTC time
        filter_events_fn: Async function to filter events

    Returns:
        Tuple of (last_meeting_end_utc, last_meeting_end_local)
    """
    result = await compute_done_for_day_info(events, request_tz, now, filter_events_fn)

    latest_end_utc = result["last_meeting_end_utc"]
    tz = result["timezone"]

    if latest_end_utc:
        latest_end_local = latest_end_utc.astimezone(tz)
        return (latest_end_utc, latest_end_local)

    return (None, None)
