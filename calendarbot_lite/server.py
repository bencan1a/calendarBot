"""calendarbot_lite.server — minimal asyncio HTTP server for Pi Zero 2W.

This module provides a small server core that:
- runs an asyncio event loop and aiohttp web server (lazy-imported)
- runs a background refresher that fetches ICS sources, parses events and expands recurrences
- keeps a small in-memory window of upcoming events
- exposes a tiny JSON API: GET /api/whats-next, POST /api/skip, DELETE /api/skip

The implementation imports calendarbot parsing/fetching modules lazily so
the module can be imported even if the full application modules aren't present.
aiohttp is required to run the server (imported at startup).
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import signal
from typing import Any

# Import shared HTTP client for connection reuse optimization
from .http_client import close_all_clients, get_shared_client

# Import and configure logging early for Pi Zero 2W optimization
try:
    from .lite_logging import configure_lite_logging

    # Apply lite logging configuration on module import
    configure_lite_logging(debug_mode=False)
except ImportError:
    # Fallback if lite_logging module is not available
    logging.basicConfig(level=logging.INFO)

# Import enhanced monitoring logging
monitoring_logger: Any = None  # Type: Optional[MonitoringLogger] but we use Any to avoid circular imports
try:
    from .monitoring_logging import get_logger

    # Get monitoring logger for server component
    monitoring_logger = get_logger("server")
    logger = logging.getLogger(__name__)
    logger.debug("calendarbot_lite.server module loaded with monitoring logging")
except ImportError:
    # Fallback if monitoring_logging module is not available
    monitoring_logger = None
    logger = logging.getLogger(__name__)
    logger.debug("calendarbot_lite.server module loaded (monitoring logging not available)")


def log_monitoring_event(event: str, message: str, level: str = "INFO", **kwargs: Any) -> None:
    """Log monitoring event with fallback to standard logging."""
    if monitoring_logger:
        monitoring_logger.log(level, event, message, **kwargs)
    else:
        # Fallback to standard logging
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"[{event}] {message}")


# Health tracking infrastructure - lightweight in-memory tracking for monitoring
import os
from typing import Optional

# Initialize health tracker (replaces global health variables)
from .health_tracker import HealthTracker

_health_tracker = HealthTracker()

# Import SSML generation for Alexa endpoints
try:
    from .alexa_ssml import render_done_for_day_ssml, render_meeting_ssml, render_time_until_ssml

    logger.debug("SSML module imported successfully")
except ImportError as e:
    logger.warning("SSML module not available: %s", e)
    render_meeting_ssml = None  # type: ignore[assignment]
    render_time_until_ssml = None  # type: ignore[assignment]
    render_done_for_day_ssml = None  # type: ignore[assignment]


def _import_process_utilities() -> Any:  # type: ignore[misc]
    """Lazy import of process utilities to handle missing calendarbot module."""
    try:
        from calendarbot.utils.process import (  # type: ignore
            auto_cleanup_before_start,
            check_port_availability,
            find_process_using_port,
        )

        return check_port_availability, find_process_using_port, auto_cleanup_before_start
    except ImportError as e:
        logger.warning("Process utilities not available: %s", e)
        return None, None, None


class PortConflictError(Exception):
    """Raised when a port conflict cannot be resolved."""


def _get_system_diagnostics() -> dict[str, Any]:
    """Get lightweight system diagnostics for health monitoring.

    Returns:
        Dictionary with system metrics, using None for unavailable values.
    """
    diag: dict[str, Any] = {
        "server_load_1m": None,
        "free_mem_kb": None,
    }

    try:
        # Get 1-minute load average (Pi Zero 2W specific)
        load_avg = os.getloadavg()
        diag["server_load_1m"] = round(load_avg[0], 2)
    except (OSError, AttributeError):
        # getloadavg not available on all platforms
        pass

    try:
        # Get free memory in KB - lightweight approach
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    # Extract value in KB
                    parts = line.split()
                    if len(parts) >= 2:
                        diag["free_mem_kb"] = int(parts[1])
                    break
    except (FileNotFoundError, ValueError, IndexError):
        # /proc/meminfo not available or format unexpected
        pass

    return diag


def _update_health_tracking(
    *,
    refresh_attempt: bool = False,
    refresh_success: bool = False,
    event_count: Optional[int] = None,
    background_heartbeat: bool = False,
    render_probe_ok: Optional[bool] = None,
    render_probe_notes: Optional[str] = None,
) -> None:
    """Update health tracking (delegates to HealthTracker instance).

    Args:
        refresh_attempt: Mark a refresh attempt timestamp
        refresh_success: Mark a successful refresh timestamp
        event_count: Update current event count
        background_heartbeat: Update background task heartbeat
        render_probe_ok: Update render probe status
        render_probe_notes: Update render probe notes
    """
    _health_tracker.update(
        refresh_attempt=refresh_attempt,
        refresh_success=refresh_success,
        event_count=event_count,
        background_heartbeat=background_heartbeat,
        render_probe_ok=render_probe_ok,
        render_probe_notes=render_probe_notes,
    )


def _handle_port_conflict(host: str, port: int) -> bool:
    """Handle port conflicts by offering to terminate conflicting processes.

    In non-interactive mode (CALENDARBOT_NONINTERACTIVE=true), automatically attempts
    cleanup without user prompts for systemd/journald compatibility.

    Args:
        host: Host address to bind to
        port: Port number to bind to

    Returns:
        True if port is available or conflict was resolved, False otherwise
    """
    check_port_availability, find_process_using_port, auto_cleanup_before_start = (
        _import_process_utilities()
    )

    if not check_port_availability:
        logger.warning("Port conflict resolution not available - process utilities missing")
        return False

    # Check if port is available
    if check_port_availability(host, port):
        logger.debug("Port %d is available", port)
        return True

    logger.error("Port %d is already in use", port)

    # Find the process using the port
    port_process = None
    if find_process_using_port:
        port_process = find_process_using_port(port)
        if port_process:
            logger.warning(
                "Process using port %d: PID %d (%s)", port, port_process.pid, port_process.command
            )
        else:
            logger.warning("Port %d is occupied but could not identify the process", port)
    else:
        logger.warning("Port %d is occupied (process identification not available)", port)

    # Check for non-interactive mode
    noninteractive = os.environ.get("CALENDARBOT_NONINTERACTIVE", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if noninteractive:
        # Non-interactive mode: automatically attempt cleanup
        logger.info(
            "Non-interactive mode: automatically attempting to terminate conflicting process on port %d",
            port,
        )

        if auto_cleanup_before_start:
            success = auto_cleanup_before_start(host, port, force=True)
            if success:
                logger.info("Successfully terminated conflicting process and freed port %d", port)
                return True
            logger.error("Failed to terminate conflicting process on port %d", port)
            return False
        logger.error("Auto cleanup function not available")
        return False

    # Interactive mode: prompt user
    print(f"\nPort {port} is currently occupied.")
    if port_process:
        print(f"Process using the port: PID {port_process.pid} ({port_process.command})")

    response = (
        input("Would you like to attempt to terminate the process using this port? (y/N): ")
        .strip()
        .lower()
    )

    if response in ("y", "yes"):
        logger.info("User confirmed termination of process using port %d", port)
        print("Attempting to terminate the conflicting process...")

        if auto_cleanup_before_start:
            success = auto_cleanup_before_start(host, port, force=True)
            if success:
                logger.info("Successfully terminated conflicting process and freed port %d", port)
                print(f"✓ Port {port} is now available")
                return True
            logger.error("Failed to terminate conflicting process on port %d", port)
            print(f"✗ Failed to free port {port}")
            return False
        logger.error("Auto cleanup function not available")
        print("✗ Port cleanup functionality not available")
        return False
    logger.info("User declined to terminate process using port %d", port)
    print("Port conflict not resolved - server cannot start")
    return False


def _build_default_config_from_env() -> dict[str, Any]:
    """Build a default config dict from environment variables.

    Behavior:
      - If a repository-local ".env" file exists, attempt to load it (simple KEY=VALUE
        parsing) into os.environ *only if* the key is not already present. This is
        intentionally non-blocking and conservative so it won't override a user's
        environment or fail startup if the file is malformed.
      - Recognizes:
        - CALENDARBOT_ICS_URL -> sets 'ics_sources' to a single-item list
        - CALENDARBOT_REFRESH_INTERVAL -> refresh_interval_seconds (int)
        - CALENDARBOT_WEB_HOST or CALENDARBOT_SERVER_BIND -> server_bind
        - CALENDARBOT_WEB_PORT or CALENDARBOT_SERVER_PORT -> server_port
    Returns:
        Mapping compatible with start_server's expected config parameter.
    """
    import os
    from pathlib import Path

    # Best-effort: try to load .env from the repo root to help developers who keep
    # runtime values there. Do not fail on errors.
    try:
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            set_keys = []
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Only set if the variable is not already in the environment to avoid
                # surprising overrides.
                if key and key not in os.environ:
                    os.environ[key] = val
                    set_keys.append(key)
            if set_keys:
                # Show which keys were loaded from .env (keys only, values not printed).
                try:
                    logger.debug("Loaded .env defaults for keys: %s", ", ".join(set_keys))
                except Exception:
                    logger.debug("Loaded .env defaults (unable to format keys)", exc_info=True)
    except Exception:
        logger.debug(
            "Failed to read .env file for defaults (continuing): %s",
            str(Path.cwd() / ".env"),
            exc_info=True,
        )

    cfg: dict[str, Any] = {}

    ics_url = os.environ.get("CALENDARBOT_ICS_URL")
    if ics_url:
        # Accept a single URL string; server._refresh_once accepts string or dict.
        # Populate both 'ics_sources' (used by refresh logic) and 'sources' (diagnostic
        # key surfaced by startup logs) to make the startup diagnostics informative.
        cfg["ics_sources"] = [ics_url]
        with contextlib.suppress(Exception):
            cfg["sources"] = [ics_url]

    refresh = os.environ.get("CALENDARBOT_REFRESH_INTERVAL") or os.environ.get(
        "CALENDARBOT_REFRESH_INTERVAL_SECONDS"
    )
    if refresh:
        try:
            cfg["refresh_interval_seconds"] = int(refresh)
        except Exception:
            logger.warning("Invalid CALENDARBOT_REFRESH_INTERVAL=%r; ignoring", refresh)

    host = os.environ.get("CALENDARBOT_WEB_HOST") or os.environ.get("CALENDARBOT_SERVER_BIND")
    if host:
        cfg["server_bind"] = host

    port = os.environ.get("CALENDARBOT_WEB_PORT") or os.environ.get("CALENDARBOT_SERVER_PORT")
    if port:
        try:
            cfg["server_port"] = int(port)
        except Exception:
            logger.warning("Invalid CALENDARBOT_WEB_PORT=%r; ignoring", port)

    # Alexa bearer token for API authentication
    alexa_token = os.environ.get("CALENDARBOT_ALEXA_BEARER_TOKEN")
    if alexa_token:
        cfg["alexa_bearer_token"] = alexa_token

    return cfg


def _create_skipped_store_if_available() -> object | None:
    """Attempt to create a SkippedStore instance from calendarbot_lite.skipped_store.

    Returns the instance if available and constructable, otherwise None.
    """
    try:
        from .skipped_store import SkippedStore  # type: ignore
    except Exception:
        return None
    try:
        return SkippedStore()
    except Exception as exc:
        logger.warning("Failed to create SkippedStore: %s", exc)
        return None


# Internal type for an event stored in the in-memory window.
EventDict = dict[str, Any]


# Centralized timezone constants
DEFAULT_SERVER_TIMEZONE = "America/Los_Angeles"  # Pacific timezone as fallback

# Focus Time keywords for detection - used to skip focus time events from whats-next
FOCUS_TIME_KEYWORDS = ["focus time", "focus", "deep work", "thinking time", "planning time"]


def _is_focus_time_event(event: dict[str, Any]) -> bool:
    """Check if event is Focus Time and should be skipped from whats-next.

    Args:
        event: Event dictionary with 'subject' key

    Returns:
        True if event is focus time, False otherwise
    """
    subject = event.get("subject", "").lower()
    return any(keyword in subject for keyword in FOCUS_TIME_KEYWORDS)


def _get_server_timezone() -> str:
    """Get the server's local timezone as an IANA timezone identifier.

    This function provides centralized timezone detection for calendarbot_lite.
    It NEVER falls back to UTC - always falls back to Pacific time as specified.

    Returns:
        IANA timezone string (e.g., "America/Los_Angeles", "America/New_York")
        Falls back to "America/Los_Angeles" (Pacific) if detection fails.
    """
    try:
        import time
        import zoneinfo

        # Get local timezone name from system
        local_tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]

        # Map common timezone abbreviations to IANA identifiers
        tz_mapping = {
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "CST": "America/Chicago",
            "CDT": "America/Chicago",
            "MST": "America/Denver",
            "MDT": "America/Denver",
        }

        # Try mapped timezone first
        if local_tz_name in tz_mapping:
            iana_tz = tz_mapping[local_tz_name]
            # Validate it's a real timezone
            zoneinfo.ZoneInfo(iana_tz)
            return iana_tz

        # Fallback: try to use system timezone detection via datetime
        from datetime import datetime, timezone

        now_local = datetime.now()
        now_utc = datetime.now(timezone.utc)
        offset = now_local - now_utc.replace(tzinfo=None)

        # Map UTC offsets to common timezones (approximate)
        offset_hours = round(offset.total_seconds() / 3600)
        offset_mapping = {
            -8: "America/Los_Angeles",  # PST
            -7: "America/Los_Angeles",  # PDT
            -6: "America/Chicago",  # CST
            -5: "America/New_York",  # EST (prioritize over Chicago for -5)
            -4: "America/New_York",  # EDT
            0: "UTC",  # Only UTC if actually at UTC offset
        }

        if offset_hours in offset_mapping:
            detected_tz = offset_mapping[offset_hours]
            # Validate the timezone works
            zoneinfo.ZoneInfo(detected_tz)
            return detected_tz

        logger.warning(
            f"Could not detect server timezone, offset={offset_hours}h, falling back to Pacific"
        )
        return DEFAULT_SERVER_TIMEZONE

    except Exception as e:
        logger.warning(f"Failed to detect server timezone: {e}, falling back to Pacific")
        return DEFAULT_SERVER_TIMEZONE


def _get_fallback_timezone() -> str:
    """Get the centralized fallback timezone for calendarbot_lite.

    This function provides a single source of truth for timezone fallbacks.
    Used when timezone detection or conversion fails anywhere in the application.

    Returns:
        Always returns "America/Los_Angeles" (Pacific timezone)
    """
    return DEFAULT_SERVER_TIMEZONE


def _now_utc() -> datetime.datetime:
    """Return current UTC time with tzinfo.

    Can be overridden for testing via CALENDARBOT_TEST_TIME environment variable.
    Format: ISO 8601 datetime string (e.g., "2025-10-27T08:20:00-07:00")

    Enhanced with DST detection: If a Pacific timezone offset is provided that doesn't
    match the actual DST status for that date, it will be automatically corrected.
    """
    import os

    test_time = os.environ.get("CALENDARBOT_TEST_TIME")
    if test_time:
        try:
            # Parse the test time and convert to UTC
            from dateutil import parser as date_parser

            dt = date_parser.isoparse(test_time)
            if dt.tzinfo is None:
                # Assume UTC if no timezone specified
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            else:
                # Enhanced DST detection for Pacific timezone
                dt = _enhance_datetime_with_dst_detection(dt, test_time)
                # Convert to UTC
                dt = dt.astimezone(datetime.timezone.utc)
            return dt
        except Exception as e:
            import logging

            logging.warning(f"Invalid CALENDARBOT_TEST_TIME: {test_time}, error: {e}")

    return datetime.datetime.now(datetime.timezone.utc)


def _enhance_datetime_with_dst_detection(
    dt: datetime.datetime, original_test_time: str
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
                    import logging

                    dst_status = "PDT" if actual_offset_hours == -7 else "PST"
                    provided_status = "PDT" if offset_hours == -7 else "PST"

                    logging.debug(
                        f"DST Auto-correction: {original_test_time} uses {provided_status} "
                        f"but {dt.date()} should be {dst_status}. "
                        f"Correcting {offset_hours:+.0f}:00 → {actual_offset_hours:+.0f}:00"
                    )

                    # Return the corrected datetime with proper Pacific timezone
                    return pacific_dt
                # Offset is correct, but still convert to proper Pacific timezone object
                # for consistency (in case it was using a simple UTC offset)
                return pacific_dt

    except Exception as e:
        import logging

        logging.warning(f"DST detection failed for {original_test_time}: {e}")
        # Fall back to original datetime

    return dt


def _get_config_value(config: Any, key: str, default: Any = None) -> Any:
    """Support dict or dataclass-like config access."""
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


def _check_bearer_token(request: Any, required_token: str | None) -> bool:
    """Check if request has valid bearer token.

    Args:
        request: aiohttp request object
        required_token: Expected bearer token, or None to skip auth

    Returns:
        True if auth is valid or not required, False otherwise
    """
    if required_token is None:
        return True

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    provided_token = auth_header[7:]  # Remove "Bearer " prefix
    return provided_token == required_token  # type: ignore[no-any-return]


def _format_duration_spoken(seconds: int) -> str:
    """Format duration in seconds for natural speech.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string for speech
    """
    if seconds < 0:
        return "in the past"
    if seconds < 60:
        return f"in {seconds} seconds"
    if seconds < 3600:
        minutes = seconds // 60
        if minutes == 1:
            return "in 1 minute"
        return f"in {minutes} minutes"
    hours = seconds // 3600
    remaining_minutes = (seconds % 3600) // 60
    if hours == 1:
        if remaining_minutes == 0:
            return "in 1 hour"
        if remaining_minutes == 1:
            return "in 1 hour and 1 minute"
        return f"in 1 hour and {remaining_minutes} minutes"
    if remaining_minutes == 0:
        return f"in {hours} hours"
    if remaining_minutes == 1:
        return f"in {hours} hours and 1 minute"
    return f"in {hours} hours and {remaining_minutes} minutes"


def _serialize_iso(dt: datetime.datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _compute_last_meeting_end_for_today(
    request_tz: str | None,
    event_window: tuple[EventDict, ...],
    skipped_store: object | None,
) -> dict[str, Any]:
    """Compute the last meeting end time for today from the event window.

    Args:
        request_tz: Optional timezone string for date comparison (e.g., "America/Los_Angeles")
        event_window: Tuple of EventDict objects from the in-memory window
        skipped_store: Optional skipped store object for checking skipped meetings

    Returns:
        Dictionary with keys:
        - has_meetings_today: bool
        - last_meeting_start_iso: str | None
        - last_meeting_end_iso: str | None
        - last_meeting_end_local_iso: str | None
        - note: str | None (for any processing notes)
    """
    now_utc = _now_utc()

    # Parse timezone or fallback to UTC
    try:
        if request_tz:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(request_tz)
        else:
            tz = datetime.timezone.utc  # type: ignore[assignment]
    except Exception:
        logger.warning("Invalid timezone %r, falling back to UTC", request_tz)
        tz = datetime.timezone.utc  # type: ignore[assignment]

    # Get today's date in the target timezone
    today_date = now_utc.astimezone(tz).date()

    latest_end_utc = None
    latest_start_utc = None
    meetings_found = 0

    # Process events in the window
    for ev in event_window:
        try:
            # Get event start time
            start = ev.get("start")
            if not isinstance(start, datetime.datetime):
                continue

            # Convert to target timezone for date comparison
            start_local = start.astimezone(tz)
            if start_local.date() != today_date:
                continue  # Not today

            # Check if meeting is skipped
            if skipped_store is not None:
                meeting_id = ev.get("meeting_id")
                if meeting_id:
                    try:
                        is_skipped_fn = getattr(skipped_store, "is_skipped", None)
                        if callable(is_skipped_fn) and is_skipped_fn(meeting_id):
                            continue  # Skip this meeting
                    except Exception as e:
                        logger.warning("Error checking skipped status for %s: %s", meeting_id, e)
                        # Continue processing - don't let skipped store errors block us

            meetings_found += 1

            # Calculate event end time with 1-hour fallback
            duration_seconds = ev.get("duration_seconds")
            if not isinstance(duration_seconds, int) or duration_seconds <= 0:
                duration_seconds = 3600  # 1-hour fallback

            end_utc = start + datetime.timedelta(seconds=duration_seconds)

            # Track latest end time
            if latest_end_utc is None or end_utc > latest_end_utc:
                latest_end_utc = end_utc
                latest_start_utc = start

        except Exception as e:
            logger.warning("Error processing event for done-for-day: %s", e)
            continue

    # Build response
    result = {
        "has_meetings_today": meetings_found > 0,
        "last_meeting_start_iso": _serialize_iso(latest_start_utc),
        "last_meeting_end_iso": _serialize_iso(latest_end_utc),
        "last_meeting_end_local_iso": None,
        "note": None,
    }

    # Add local timezone version if we have an end time
    if latest_end_utc is not None:
        try:
            end_local = latest_end_utc.astimezone(tz)
            result["last_meeting_end_local_iso"] = end_local.isoformat()
        except Exception as e:
            logger.warning("Error converting end time to local timezone: %s", e)
            result["note"] = "Local timezone conversion failed"

    logger.debug(
        "Done-for-day computation: %d meetings today, latest end: %s",
        meetings_found,
        result["last_meeting_end_iso"],
    )

    return result


def _lite_event_to_dict(event: Any, source_name: str = "") -> EventDict:
    """Convert LiteCalendarEvent to EventDict format for server compatibility.

    Args:
        event: LiteCalendarEvent object from parser
        source_name: Source name for tracking origin

    Returns:
        EventDict with normalized fields
    """
    # Calculate duration in seconds
    duration_seconds = 0
    try:
        if hasattr(event, "start") and hasattr(event, "end"):
            start_dt = event.start.date_time if hasattr(event.start, "date_time") else event.start
            end_dt = event.end.date_time if hasattr(event.end, "date_time") else event.end
            if start_dt and end_dt:
                duration_seconds = int((end_dt - start_dt).total_seconds())
    except Exception as e:
        logger.debug("Failed to calculate duration for event %s: %s", getattr(event, "id", ""), e)
        duration_seconds = 3600  # Default to 1 hour

    # Extract start datetime
    start_dt = None
    if hasattr(event, "start"):
        start_dt = event.start.date_time if hasattr(event.start, "date_time") else event.start

    # Extract location
    location_value = ""
    if hasattr(event, "location") and event.location:
        if hasattr(event.location, "display_name"):
            location_value = str(event.location.display_name)
        else:
            location_value = str(event.location)

    # Extract attendees/participants
    participants = []
    if hasattr(event, "attendees") and event.attendees:
        participants = event.attendees

    return {
        "meeting_id": str(getattr(event, "id", "")),
        "subject": str(getattr(event, "subject", "")),
        "description": str(getattr(event, "body_preview", "") or ""),
        "participants": participants,
        "start": start_dt,
        "duration_seconds": duration_seconds,
        "location": location_value,
        "raw_source": source_name,
    }


async def _fetch_and_parse_source(
    semaphore: asyncio.Semaphore,
    src_cfg: Any,
    config: Any,
    rrule_days: int,
    shared_http_client: Any = None,
) -> list[EventDict]:
    """Fetch and parse a single source using existing lite_fetcher and lite_parser abstractions.

    This function uses the well-tested LiteICSFetcher and LiteICSParser modules instead of
    duplicating their logic. RRULE expansion is handled automatically by the parser.

    Args:
        semaphore: Semaphore to limit concurrent fetches
        src_cfg: Source configuration (string URL, dict, or LiteICSSource object)
        config: Application configuration
        rrule_days: Days to expand RRULE patterns (passed to parser settings)
        shared_http_client: Optional shared HTTP client for connection reuse

    Returns:
        List of parsed events in EventDict format
    """
    async with semaphore:
        logger.debug("Processing source configuration: %r", src_cfg)
        try:
            # Import required modules
            from .lite_fetcher import LiteICSFetcher
            from .lite_models import LiteICSSource
            from .lite_parser import LiteICSParser

            # Build source object from various input formats
            if isinstance(src_cfg, LiteICSSource):
                source = src_cfg
            elif isinstance(src_cfg, dict):
                source = LiteICSSource(**src_cfg)
            elif isinstance(src_cfg, str):
                source = LiteICSSource(name=src_cfg, url=src_cfg)
            else:
                # Handle objects with name/url attributes
                source = LiteICSSource(
                    name=getattr(src_cfg, "name", str(src_cfg)),
                    url=getattr(src_cfg, "url", str(src_cfg)),
                )

            # Create settings object for fetcher and parser
            class _Settings:
                request_timeout = int(_get_config_value(config, "request_timeout", 30))
                max_retries = int(_get_config_value(config, "max_retries", 3))
                retry_backoff_factor = float(_get_config_value(config, "retry_backoff_factor", 1.5))
                rrule_expansion_days = rrule_days
                enable_rrule_expansion = True

            # Fetch ICS data using LiteICSFetcher
            logger.debug("Fetching ICS data from source: %r", source.url)
            fetcher = LiteICSFetcher(_Settings(), shared_http_client)
            async with fetcher:
                response = await fetcher.fetch_ics(source, conditional_headers=None)

            if not response or not response.success:
                logger.warning("Fetch failed for source %r", src_cfg)
                return []

            # Get ICS content (handle both streaming and buffered responses)
            ics_content = None
            if hasattr(response, "stream_handle") and response.stream_handle:
                # For streaming responses, read all content
                logger.debug("Reading streaming content from source %r", source.url)
                try:
                    ics_content = await response.stream_handle.read_all()  # type: ignore[attr-defined]
                except Exception as e:
                    logger.warning("Failed to read streaming content: %s", e)
                    return []
            elif hasattr(response, "content") and response.content:
                ics_content = response.content
            else:
                logger.warning("No content in response from source %r", src_cfg)
                return []

            # Parse ICS content using LiteICSParser (includes automatic RRULE expansion)
            logger.debug("Parsing ICS content from source %r (%d bytes)", source.url, len(ics_content))
            parser = LiteICSParser(_Settings())
            parse_result = parser.parse_ics_content_optimized(ics_content, source_url=source.url)

            if not parse_result.success:
                logger.warning(
                    "Parse failed for source %r: %s", src_cfg, parse_result.error_message or "Unknown error"
                )
                return []

            if not parse_result.events:
                logger.debug("No events found in source %r", src_cfg)
                return []

            # Convert LiteCalendarEvent objects to EventDict format
            logger.debug(
                "Converting %d LiteCalendarEvent objects to EventDict format", len(parse_result.events)
            )
            normalized_events = [
                _lite_event_to_dict(event, source_name=source.name) for event in parse_result.events
            ]

            logger.debug("Successfully processed %d events from source %r", len(normalized_events), src_cfg)
            return normalized_events

        except ImportError:
            logger.exception("Required modules not available")
            return []
        except Exception:
            logger.exception("Unexpected error while processing source %r", src_cfg)
            return []


async def _refresh_once(
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[EventDict, ...]],
    window_lock: asyncio.Lock,
    shared_http_client: Any = None,
) -> None:
    """Perform a single refresh: fetch sources, parse/expand events and update window.

    This function performs lazy imports of the calendarbot parsing/fetching modules
    and is resilient if those modules are not present yet.

    Uses bounded concurrency for fetching sources.

    Args:
        config: Application configuration
        skipped_store: Optional store for skipped events
        event_window_ref: Reference to event window for atomic updates
        window_lock: Lock for thread-safe event window updates
        shared_http_client: Optional shared HTTP client for connection reuse
    """
    logger.debug("=== Starting refresh_once ===")

    # Track refresh attempt and log monitoring event
    _update_health_tracking(refresh_attempt=True, background_heartbeat=True)
    log_monitoring_event(
        "refresh.cycle.start",
        "Starting refresh cycle",
        "DEBUG",
        details={"sources_count": len(_get_config_value(config, "ics_sources", []) or [])},
    )

    # Collect sources configuration
    sources_cfg = _get_config_value(config, "ics_sources", []) or []

    # Get concurrency configuration
    fetch_concurrency = int(_get_config_value(config, "fetch_concurrency", 2))
    fetch_concurrency = max(1, min(fetch_concurrency, 3))  # Bound between 1-3 for Pi Zero 2W

    # How many days to expand recurrences
    rrule_days = int(_get_config_value(config, "rrule_expansion_days", 14))

    logger.debug(
        "Refresh configuration: rrule_expansion_days=%d, sources_count=%d, fetch_concurrency=%d",
        rrule_days,
        len(sources_cfg),
        fetch_concurrency,
    )
    logger.debug(" Sources configured: %r", sources_cfg)

    if not sources_cfg:
        logger.error("DEBUG: No sources configured, skipping refresh - THIS IS THE PROBLEM!")
        log_monitoring_event(
            "refresh.config.error",
            "No ICS sources configured - refresh skipped",
            "ERROR",
            details={"config_keys": list(config.keys()) if isinstance(config, dict) else []},
        )
        return

    # Use bounded concurrency for fetching sources
    semaphore = asyncio.Semaphore(fetch_concurrency)
    fetch_tasks = [
        asyncio.create_task(
            _fetch_and_parse_source(semaphore, src_cfg, config, rrule_days, shared_http_client)
        )
        for src_cfg in sources_cfg
    ]

    # Execute all fetch tasks concurrently and gather results
    fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    # Process results and collect parsed events
    parsed_events: list[EventDict] = []
    for i, result in enumerate(fetch_results):
        if isinstance(result, Exception):
            logger.error("DEBUG: Source %r failed: %s", sources_cfg[i], result)
            continue
        if isinstance(result, list):
            logger.debug(" Source %r returned %d events", sources_cfg[i], len(result))
            parsed_events.extend(result)

    logger.debug(" Total parsed events from all sources: %d", len(parsed_events))

    # Use event filter and window manager for smart filtering and fallback
    from .event_filter import EventFilter, EventWindowManager, SmartFallbackHandler

    # Initialize filter components
    fallback_handler = SmartFallbackHandler()
    event_filter = EventFilter(_get_server_timezone, _get_fallback_timezone)
    window_manager = EventWindowManager(event_filter, fallback_handler)

    # Get current time and window size
    now = _now_utc()
    window_size = int(_get_config_value(config, "event_window_size", 50))

    # Update window with smart fallback logic
    updated, final_count, message = await window_manager.update_window(
        event_window_ref,
        window_lock,
        parsed_events,
        now,
        skipped_store,
        window_size,
        len(sources_cfg),
    )

    # Log appropriate monitoring events based on outcome
    if not updated:
        # Window was preserved due to fallback logic
        if final_count > 0:
            log_monitoring_event(
                "refresh.sources.fallback",
                message,
                "WARNING",
                details={"existing_events": final_count, "sources_count": len(sources_cfg)},
                include_system_state=True,
            )
        else:
            log_monitoring_event(
                "refresh.sources.critical_failure",
                message,
                "CRITICAL",
                include_system_state=True,
            )
        return  # Exit early when using fallback

    # Track successful refresh and log monitoring event
    _update_health_tracking(refresh_success=True, event_count=final_count)

    logger.debug(" Refresh complete; stored %d events in window", final_count)

    # Log structured monitoring event for refresh success
    log_monitoring_event(
        "refresh.cycle.complete",
        f"Refresh cycle completed successfully - {final_count} events in window",
        "INFO",
        details={
            "events_parsed": len(parsed_events),
            "events_in_window": final_count,
            "sources_processed": len(_get_config_value(config, "ics_sources", []) or []),
        },
        include_system_state=True,
    )

    # INFO level log to confirm server is operational and data is available
    if parsed_events:
        logger.info(
            "ICS data successfully parsed and refreshed - %d upcoming events available for serving",
            final_count,
        )
    else:
        logger.info(
            "No events from sources - using fallback behavior (%d events in window)",
            final_count,
        )

    # Log event details for debugging (read window for logging)
    async with window_lock:
        window_for_logging = event_window_ref[0]

    for i, event in enumerate(window_for_logging[:3]):  # Log first 3 events
        logger.debug(
            " Event %d - ID: %r, Subject: %r, Start: %r",
            i,
            event.get("meeting_id"),
            event.get("subject"),
            event.get("start"),
        )


async def _refresh_loop(
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[EventDict, ...]],
    window_lock: asyncio.Lock,
    stop_event: asyncio.Event,
    shared_http_client: Any = None,
) -> None:
    """Background refresher: immediate refresh then periodic refreshes."""
    interval = int(_get_config_value(config, "refresh_interval_seconds", 60))
    logger.debug(" _refresh_loop starting with interval %d seconds", interval)

    # Perform an initial refresh immediately.
    logger.debug(" Starting initial refresh")
    try:
        await _refresh_once(
            config, skipped_store, event_window_ref, window_lock, shared_http_client
        )
        logger.debug(" Initial refresh completed")
    except Exception as e:
        logger.error("DEBUG: Initial refresh failed: %s", e, exc_info=True)

    logger.debug(" Starting refresh loop")
    while not stop_event.is_set():
        try:
            logger.debug(" Sleeping for %d seconds until next refresh", interval)
            await asyncio.sleep(interval)
            if stop_event.is_set():
                break
            logger.debug(" Starting periodic refresh")
            await _refresh_once(
                config, skipped_store, event_window_ref, window_lock, shared_http_client
            )
            logger.debug(" Periodic refresh completed")
        except Exception:
            logger.exception("DEBUG: Refresh loop unexpected error")


def _event_to_api_model(ev: EventDict) -> dict[str, Any]:
    """Serialize internal event dict to API response fields (start_iso computed later).

    Note: 'subject' is the canonical title field for events; 'title' alias removed.
    """
    return {
        "meeting_id": ev["meeting_id"],
        "subject": ev.get("subject") or ev.get("title") or "",
        "description": ev.get("description"),
        "attendees": ev.get("participants") or ev.get("attendees") or [],
        "start_iso": _serialize_iso(ev.get("start")),
        "duration_seconds": int(ev.get("duration_seconds") or 0),
        "location": ev.get("location"),
        "raw_source": ev.get("raw_source"),
    }


async def _make_app(  # type: ignore[no-untyped-def]
    _config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[EventDict, ...]],
    window_lock: asyncio.Lock,
    _stop_event: asyncio.Event,
    shared_http_client: Any = None,
):
    """Create aiohttp web application with routes wired to the in-memory window.

    aiohttp is imported lazily here so the module can be imported without aiohttp installed.
    """
    # Lazy import aiohttp.web
    try:
        from aiohttp import web  # type: ignore
    except Exception:  # pragma: no cover - requires aiohttp at runtime
        logger.exception("aiohttp is required to run the server")
        raise
    else:
        logger.debug("aiohttp successfully imported; building web.Application")

    app = web.Application()

    # Get the package directory for static file serving
    from pathlib import Path

    package_dir = Path(__file__).resolve().parent

    async def health_check(_request):  # type: ignore[no-untyped-def]
        """Health check endpoint for monitoring system status."""
        now = _now_utc()
        now_iso = now.isoformat() + "Z"

        # Server uptime calculation
        uptime_seconds = _health_tracker.get_uptime_seconds()

        # Last refresh delta calculation
        last_success_delta_s = _health_tracker.get_last_refresh_age_seconds()

        # Determine overall status
        status = _health_tracker.determine_overall_status()

        # Background task status
        background_tasks = [_health_tracker.get_background_task_status()]

        # Get system diagnostics
        diag = _get_system_diagnostics()

        # Build comprehensive health response
        last_refresh_success = _health_tracker.get_last_refresh_success_timestamp()
        last_refresh_attempt = _health_tracker.get_last_refresh_attempt_timestamp()
        last_render_probe = _health_tracker.get_last_render_probe_timestamp()

        health_data = {
            "status": status,
            "server_time_iso": now_iso,
            "server_status": {"uptime_s": uptime_seconds, "pid": os.getpid()},
            "last_refresh": {
                "last_success_iso": last_refresh_success
                and datetime.datetime.fromtimestamp(
                    last_refresh_success, tz=datetime.timezone.utc
                ).isoformat()
                + "Z",
                "last_attempt_iso": last_refresh_attempt
                and datetime.datetime.fromtimestamp(
                    last_refresh_attempt, tz=datetime.timezone.utc
                ).isoformat()
                + "Z",
                "last_success_delta_s": last_success_delta_s,
                "event_count": _health_tracker.get_event_count(),
            },
            "background_tasks": background_tasks,
            "display_probe": {
                "last_render_probe_iso": last_render_probe
                and datetime.datetime.fromtimestamp(
                    last_render_probe, tz=datetime.timezone.utc
                ).isoformat()
                + "Z",
                "last_probe_ok": _health_tracker.get_last_render_probe_ok(),
                "last_probe_notes": _health_tracker.get_last_render_probe_notes(),
            },
            "diag": diag,
        }

        # Return appropriate HTTP status based on health
        http_status = 200 if status == "ok" else 503
        return web.json_response(health_data, status=http_status)

    async def whats_next(_request):  # type: ignore[no-untyped-def]
        """Find the next upcoming event with smart prioritization logic."""
        from .event_prioritizer import EventPrioritizer

        now = _now_utc()

        # Read window with lock to be consistent
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug(" /api/whats-next called - window has %d events", len(window))

        # Use event prioritizer to find next event with business logic
        prioritizer = EventPrioritizer(_is_focus_time_event)
        result = prioritizer.find_next_event(window, now, skipped_store)

        if result is None:
            # No upcoming events found
            return web.json_response({"meeting": None}, status=200)

        # Unpack result and build response
        event, seconds_until = result
        model = _event_to_api_model(event)
        model["seconds_until_start"] = seconds_until

        return web.json_response({"meeting": model}, status=200)

    async def post_skip(request):  # type: ignore[no-untyped-def]
        if skipped_store is None:
            return web.json_response({"error": "skip-store not available"}, status=501)
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)
        meeting_id = data.get("meeting_id") if isinstance(data, dict) else None
        if not meeting_id or not isinstance(meeting_id, str):
            return web.json_response({"error": "missing or invalid meeting_id"}, status=400)
        add_skip = getattr(skipped_store, "add_skip", None)
        if not callable(add_skip):
            return web.json_response({"error": "skip-store missing add_skip"}, status=501)
        try:
            result = add_skip(meeting_id)
            if asyncio.iscoroutine(result):
                result = await result
        except Exception:
            logger.exception("skipped_store.add_skip failed")
            return web.json_response({"error": "failed to add skip"}, status=500)

        # Normalize result into ISO timestamp if possible.
        skipped_until_iso = None
        if isinstance(result, datetime.datetime):
            skipped_until_iso = _serialize_iso(result)
        elif isinstance(result, str):
            skipped_until_iso = result

        return web.json_response({"skipped_until": skipped_until_iso}, status=200)

    async def delete_skip(_request):  # type: ignore[no-untyped-def]
        if skipped_store is None:
            return web.json_response({"error": "skip-store not available"}, status=501)
        clear_all = getattr(skipped_store, "clear_all", None)
        if not callable(clear_all):
            return web.json_response({"error": "skip-store missing clear_all"}, status=501)
        try:
            res = clear_all()
            if asyncio.iscoroutine(res):
                res = await res
        except Exception:
            logger.exception("skipped_store.clear_all failed")
            return web.json_response({"error": "failed to clear skips"}, status=500)

        count = int(res) if isinstance(res, int) else 0
        return web.json_response({"cleared": True, "count": count}, status=200)

    async def clear_skips(_request):  # type: ignore[no-untyped-def]
        """Convenient GET endpoint to clear all skipped meetings."""
        if skipped_store is None:
            return web.json_response({"error": "skip-store not available"}, status=501)
        clear_all = getattr(skipped_store, "clear_all", None)
        if not callable(clear_all):
            return web.json_response({"error": "skip-store missing clear_all"}, status=501)

        try:
            res = clear_all()
            if asyncio.iscoroutine(res):
                res = await res
        except Exception:
            logger.exception("skipped_store.clear_all failed")
            return web.json_response({"error": "failed to clear skips"}, status=500)

        count = int(res) if isinstance(res, int) else 0

        # Force immediate cache refresh to restore previously skipped meetings
        try:
            await _refresh_once(
                _config, skipped_store, event_window_ref, window_lock, shared_http_client
            )
            logger.debug("Refreshed event cache after clearing %d skipped meetings", count)
        except Exception:
            logger.exception("Failed to refresh cache after clearing skips")
            return web.json_response(
                {"error": "cleared skips but failed to refresh cache"}, status=500
            )

        return web.json_response(
            {"cleared": True, "count": count, "message": f"Cleared {count} skipped meetings"},
            status=200,
        )

    async def serve_static_html(_request):  # type: ignore[no-untyped-def]
        """Serve the static whatsnext.html file."""
        html_file = package_dir / "whatsnext.html"
        if not html_file.exists():
            logger.error("Static HTML file not found: %s", html_file)
            return web.Response(text="Static HTML file not found", status=404)

        return web.FileResponse(html_file)

    async def serve_static_css(_request):  # type: ignore[no-untyped-def]
        """Serve the static whatsnext.css file."""
        css_file = package_dir / "whatsnext.css"
        if not css_file.exists():
            logger.error("Static CSS file not found: %s", css_file)
            return web.Response(text="CSS file not found", status=404)

        return web.FileResponse(css_file)

    async def serve_static_js(_request):  # type: ignore[no-untyped-def]
        """Serve the static whatsnext.js file."""
        js_file = package_dir / "whatsnext.js"
        if not js_file.exists():
            logger.error("Static JS file not found: %s", js_file)
            return web.Response(text="JS file not found", status=404)

        return web.FileResponse(js_file)

    # Static file routes
    app.router.add_get("/", serve_static_html)
    app.router.add_get("/whatsnext.css", serve_static_css)
    app.router.add_get("/whatsnext.js", serve_static_js)

    # Get bearer token from config for Alexa endpoints
    alexa_bearer_token = _get_config_value(_config, "alexa_bearer_token")

    async def alexa_next_meeting(request):  # type: ignore[no-untyped-def]
        """Alexa endpoint for getting next meeting with speech formatting."""
        if not _check_bearer_token(request, alexa_bearer_token):
            return web.json_response({"error": "Unauthorized"}, status=401)

        now = _now_utc()
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug("Alexa /api/alexa/next-meeting called - window has %d events", len(window))

        # Find first upcoming meeting
        for ev in window:
            start = ev.get("start")
            if not isinstance(start, datetime.datetime):
                continue
            seconds_until = int((start - now).total_seconds())
            if seconds_until < 0:
                continue
            if skipped_store is not None:
                is_skipped = getattr(skipped_store, "is_skipped", None)
                try:
                    if callable(is_skipped) and is_skipped(ev["meeting_id"]):
                        continue
                except Exception as e:
                    logger.warning("skipped_store.is_skipped raised during alexa call: %s", e)

            # Format meeting for speech
            subject = ev.get("subject", "Untitled meeting")
            duration_spoken = _format_duration_spoken(seconds_until)

            # Simple speech text for Alexa
            speech_text = f"Your next meeting is {subject} {duration_spoken}."

            # Generate SSML if available
            ssml_output = None
            if render_meeting_ssml:  # type: ignore[truthy-function]
                logger.debug("Attempting SSML generation for next-meeting")
                meeting_data = {
                    "subject": subject,
                    "seconds_until_start": seconds_until,
                    "duration_spoken": duration_spoken,
                    "location": ev.get("location", ""),
                    "is_online_meeting": ev.get("is_online_meeting", False),
                }
                try:
                    ssml_output = render_meeting_ssml(meeting_data)
                    if ssml_output:
                        logger.info("SSML generated successfully: %d characters", len(ssml_output))
                    else:
                        logger.warning(
                            "SSML generation returned None - validation failed or disabled"
                        )
                except Exception as e:
                    logger.error("SSML generation failed: %s", e, exc_info=True)
            else:  # type: ignore[unreachable]
                logger.warning("SSML generation not available - module not imported")

            response_data = {
                "meeting": {
                    "subject": subject,
                    "start_iso": _serialize_iso(start),
                    "seconds_until_start": seconds_until,
                    "speech_text": speech_text,
                    "duration_spoken": duration_spoken,
                }
            }

            # Add SSML to response if generated
            if ssml_output:
                response_data["meeting"]["ssml"] = ssml_output
                logger.debug(
                    "Added SSML to response: %s",
                    ssml_output[:100] + "..." if len(ssml_output) > 100 else ssml_output,
                )

            return web.json_response(response_data, status=200)

        # No upcoming meetings case
        speech_text = "You have no upcoming meetings."
        ssml_output = None

        # Generate SSML for no meetings case if available
        if render_meeting_ssml:  # type: ignore[truthy-function]
            logger.debug("Attempting SSML generation for no meetings case")
            try:
                # Create empty meeting dict for no meetings case
                empty_meeting = {"subject": "", "seconds_until_start": 0, "duration_spoken": ""}
                ssml_output = render_meeting_ssml(empty_meeting)
                if ssml_output:
                    logger.info("No-meetings SSML generated: %d characters", len(ssml_output))
                else:
                    logger.warning("No-meetings SSML generation returned None")
            except Exception as e:
                logger.error("No-meetings SSML generation failed: %s", e, exc_info=True)

        response_data = {"meeting": None, "speech_text": speech_text}  # type: ignore[dict-item]
        if ssml_output:
            response_data["ssml"] = ssml_output  # type: ignore[assignment]

        return web.json_response(response_data, status=200)

    async def alexa_time_until_next(request):  # type: ignore[no-untyped-def]
        """Alexa endpoint for getting time until next meeting."""
        if not _check_bearer_token(request, alexa_bearer_token):
            return web.json_response({"error": "Unauthorized"}, status=401)

        now = _now_utc()
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug("Alexa /api/alexa/time-until-next called - window has %d events", len(window))

        # Find first upcoming meeting
        for ev in window:
            start = ev.get("start")
            if not isinstance(start, datetime.datetime):
                continue
            seconds_until = int((start - now).total_seconds())
            if seconds_until < 0:
                continue
            if skipped_store is not None:
                is_skipped = getattr(skipped_store, "is_skipped", None)
                try:
                    if callable(is_skipped) and is_skipped(ev["meeting_id"]):
                        continue
                except Exception as e:
                    logger.warning("skipped_store.is_skipped raised during alexa call: %s", e)

            duration_spoken = _format_duration_spoken(seconds_until)
            speech_text = f"Your next meeting is {duration_spoken}."

            # Generate SSML for time-until response if available
            ssml_output = None
            if render_time_until_ssml:  # type: ignore[truthy-function]
                logger.debug("Attempting SSML generation for time-until-next")
                meeting_data = {
                    "subject": ev.get("subject", ""),
                    "duration_spoken": duration_spoken,
                }
                try:
                    ssml_output = render_time_until_ssml(seconds_until, meeting_data)
                    if ssml_output:
                        logger.info("Time-until SSML generated: %d characters", len(ssml_output))
                    else:
                        logger.warning("Time-until SSML generation returned None")
                except Exception as e:
                    logger.error("Time-until SSML generation failed: %s", e, exc_info=True)
            else:  # type: ignore[unreachable]
                logger.warning("Time-until SSML generation not available - module not imported")

            response_data = {
                "seconds_until_start": seconds_until,
                "duration_spoken": duration_spoken,
                "speech_text": speech_text,
            }

            # Add SSML to response if generated
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        # No upcoming meetings case for time-until
        speech_text = "You have no upcoming meetings."
        ssml_output = None

        # Generate SSML for no meetings case if available
        if render_time_until_ssml:  # type: ignore[truthy-function]
            logger.debug("Attempting SSML generation for time-until no meetings case")
            try:
                ssml_output = render_time_until_ssml(0, None)  # 0 seconds, no meeting
                if ssml_output:
                    logger.info(
                        "Time-until no-meetings SSML generated: %d characters", len(ssml_output)
                    )
            except Exception as e:
                logger.error("Time-until no-meetings SSML generation failed: %s", e, exc_info=True)

        response_data = {"seconds_until_start": None, "speech_text": speech_text}
        if ssml_output:
            response_data["ssml"] = ssml_output

        return web.json_response(response_data, status=200)

    async def done_for_day(request):  # type: ignore[no-untyped-def]
        """API endpoint for getting last meeting end time for today."""
        now = _now_utc()

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        # Read window with lock to be consistent
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug(
            "/api/done-for-day called - window has %d events, tz=%s", len(window), request_tz
        )

        # Compute last meeting end for today
        result = _compute_last_meeting_end_for_today(request_tz, window, skipped_store)

        # Build full response with current time and timezone info
        response = {
            "now_iso": _serialize_iso(now),
            "tz": request_tz,
            **result,
        }

        return web.json_response(response, status=200)

    async def alexa_done_for_day(request):  # type: ignore[no-untyped-def]
        """Alexa endpoint for getting done-for-day status with SSML."""
        if not _check_bearer_token(request, alexa_bearer_token):
            return web.json_response({"error": "Unauthorized"}, status=401)

        now = _now_utc()

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        # Read window with lock to be consistent
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug(
            "Alexa /api/alexa/done-for-day called - window has %d events, tz=%s",
            len(window),
            request_tz,
        )

        # Compute last meeting end for today
        result = _compute_last_meeting_end_for_today(request_tz, window, skipped_store)

        # Generate speech text based on results
        if result["has_meetings_today"]:
            if result["last_meeting_end_iso"]:
                # Parse the end time for speech formatting
                try:
                    import zoneinfo

                    end_utc = datetime.datetime.fromisoformat(
                        result["last_meeting_end_iso"].replace("Z", "+00:00")
                    )

                    # Convert to local time for speech
                    if request_tz:
                        try:
                            tz = zoneinfo.ZoneInfo(request_tz)
                            end_local = end_utc.astimezone(tz)
                            time_str = end_local.strftime("%-I:%M %p").lower()
                        except Exception:
                            time_str = end_utc.strftime("%-I:%M %p UTC").lower()
                    else:
                        time_str = end_utc.strftime("%-I:%M %p UTC").lower()

                    # Compare current time with last meeting end time
                    if now >= end_utc:
                        # All meetings for today have ended
                        speech_text = "You're all done for today!"
                    else:
                        # Still have meetings, will be done at end time
                        speech_text = f"You'll be done at {time_str}."

                except Exception as e:
                    logger.warning("Error formatting end time for speech: %s", e)
                    speech_text = (
                        "You have meetings today, but I couldn't determine when your last one ends."
                    )
            else:
                speech_text = (
                    "You have meetings today, but I couldn't determine when your last one ends."
                )
        else:
            speech_text = "You have no meetings today. Enjoy your free day!"

        # Generate SSML if available
        ssml_output = None
        if render_done_for_day_ssml:  # type: ignore[truthy-function]
            logger.debug("Attempting SSML generation for done-for-day")
            try:
                ssml_output = render_done_for_day_ssml(result["has_meetings_today"], speech_text)
                if ssml_output:
                    logger.info("Done-for-day SSML generated: %d characters", len(ssml_output))
                else:
                    logger.warning("Done-for-day SSML generation returned None")
            except Exception as e:
                logger.error("Done-for-day SSML generation failed: %s", e, exc_info=True)

        # Build response
        response_data = {
            "now_iso": _serialize_iso(now),
            "tz": request_tz,
            **result,
            "speech_text": speech_text,
        }

        # Add SSML and card data for Alexa if available
        if ssml_output:
            response_data["ssml"] = ssml_output
            response_data["card"] = {
                "title": "Done for the Day",
                "content": speech_text,
            }

        return web.json_response(response_data, status=200)

    # API routes
    app.router.add_get("/api/health", health_check)
    app.router.add_get("/api/whats-next", whats_next)
    app.router.add_post("/api/skip", post_skip)
    app.router.add_delete("/api/skip", delete_skip)
    app.router.add_get("/api/clear_skips", clear_skips)
    app.router.add_get("/api/done-for-day", done_for_day)

    async def alexa_launch_summary(request):  # type: ignore[no-untyped-def]
        """Alexa endpoint for launch intent - comprehensive summary with SSML."""
        if not _check_bearer_token(request, alexa_bearer_token):
            return web.json_response({"error": "Unauthorized"}, status=401)

        now = _now_utc()

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        # Read window with lock to be consistent
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug(
            "Alexa /api/alexa/launch-summary called - window has %d events, tz=%s",
            len(window),
            request_tz,
        )

        # Compute last meeting end for today to determine if done for day
        done_for_day_result = _compute_last_meeting_end_for_today(request_tz, window, skipped_store)

        # Parse timezone for date comparison
        try:
            if request_tz:
                import zoneinfo

                tz = zoneinfo.ZoneInfo(request_tz)
            else:
                tz = datetime.timezone.utc  # type: ignore[assignment]
        except Exception:
            tz = datetime.timezone.utc  # type: ignore[assignment]

        today_date = now.astimezone(tz).date()

        # Initialize meeting variables
        next_meeting_today = None
        future_meeting = None

        # Build speech response based on whether there are meetings today
        if not done_for_day_result["has_meetings_today"]:
            # No meetings today case
            # Find next future meeting beyond today
            future_meeting = None
            for ev in window:
                start = ev.get("start")
                if not isinstance(start, datetime.datetime):
                    continue

                start_local = start.astimezone(tz)
                if start_local.date() <= today_date:
                    continue  # Skip today's meetings and past meetings

                # This is a future meeting beyond today
                if skipped_store is not None:
                    is_skipped = getattr(skipped_store, "is_skipped", None)
                    try:
                        if callable(is_skipped) and is_skipped(ev["meeting_id"]):
                            continue
                    except Exception:
                        pass

                seconds_until = int((start - now).total_seconds())
                future_meeting = {
                    "event": ev,
                    "seconds_until": seconds_until,
                    "subject": ev.get("subject", "Untitled meeting"),
                    "duration_spoken": _format_duration_spoken(seconds_until),
                }
                break

            if future_meeting:
                speech_text = f"No meetings today, you're free until {future_meeting['subject']} {future_meeting['duration_spoken']}."
            else:
                speech_text = "No meetings today. You have no upcoming meetings scheduled."

        else:
            # Have meetings today case - find next meeting today
            next_meeting_today = None
            for ev in window:
                start = ev.get("start")
                if not isinstance(start, datetime.datetime):
                    continue

                start_local = start.astimezone(tz)
                if start_local.date() != today_date:
                    continue  # Skip non-today meetings

                seconds_until = int((start - now).total_seconds())
                if seconds_until < 0:
                    continue  # Skip past meetings

                if skipped_store is not None:
                    is_skipped = getattr(skipped_store, "is_skipped", None)
                    try:
                        if callable(is_skipped) and is_skipped(ev["meeting_id"]):
                            continue
                    except Exception as e:
                        logger.warning(
                            "skipped_store.is_skipped raised during alexa launch call: %s", e
                        )

                next_meeting_today = {
                    "event": ev,
                    "seconds_until": seconds_until,
                    "subject": ev.get("subject", "Untitled meeting"),
                    "duration_spoken": _format_duration_spoken(seconds_until),
                }
                break

            if next_meeting_today:
                speech_text = f"Your next meeting is {next_meeting_today['subject']} {next_meeting_today['duration_spoken']}."
            else:
                speech_text = "You have no more meetings today."

            # Add done-for-day information if we have meetings today
            if done_for_day_result["last_meeting_end_iso"]:
                try:
                    import zoneinfo

                    end_utc = datetime.datetime.fromisoformat(
                        done_for_day_result["last_meeting_end_iso"].replace("Z", "+00:00")
                    )

                    # Convert to local time for speech
                    if request_tz:
                        try:
                            tz = zoneinfo.ZoneInfo(request_tz)
                            end_local = end_utc.astimezone(tz)
                            time_str = end_local.strftime("%-I:%M %p").lower()
                        except Exception:
                            time_str = end_utc.strftime("%-I:%M %p UTC").lower()
                    else:
                        time_str = end_utc.strftime("%-I:%M %p UTC").lower()

                    if now >= end_utc:
                        speech_text += " You're all done for today!"
                    else:
                        speech_text += f" You'll be done for the day at {time_str}."

                except Exception as e:
                    logger.warning("Error formatting end time for launch summary: %s", e)
                    speech_text += " I couldn't determine when your last meeting ends today."

        # Determine which meeting to use for SSML and response building
        primary_meeting = None
        if done_for_day_result["has_meetings_today"] and next_meeting_today is not None:
            primary_meeting = next_meeting_today
        elif not done_for_day_result["has_meetings_today"] and future_meeting is not None:
            primary_meeting = future_meeting

        # Generate SSML if available - reuse existing SSML functions
        ssml_output = None
        if done_for_day_result["has_meetings_today"] and primary_meeting and render_meeting_ssml:  # type: ignore[truthy-function]
            # Meetings today case - use meeting SSML
            logger.debug("Attempting SSML generation for launch summary with meetings today")
            try:
                meeting_data = {
                    "subject": primary_meeting["subject"],
                    "seconds_until_start": primary_meeting["seconds_until"],
                    "duration_spoken": primary_meeting["duration_spoken"],
                    "location": primary_meeting["event"].get("location", ""),
                    "is_online_meeting": primary_meeting["event"].get("is_online_meeting", False),
                }
                # Use the meeting SSML renderer for meetings today
                base_ssml = render_meeting_ssml(meeting_data)
                if base_ssml:
                    ssml_output = base_ssml
                    logger.info(
                        "Launch summary (meetings today) SSML generated: %d characters",
                        len(ssml_output),
                    )
            except Exception as e:
                logger.error(
                    "Launch summary (meetings today) SSML generation failed: %s", e, exc_info=True
                )
        elif render_done_for_day_ssml:  # type: ignore[truthy-function]
            # No meetings today case - use done-for-day SSML (which handles the speech_text format)
            logger.debug("Attempting SSML generation for launch summary (no meetings today)")
            try:
                ssml_output = render_done_for_day_ssml(
                    done_for_day_result["has_meetings_today"], speech_text
                )
                if ssml_output:
                    logger.info(
                        "Launch summary (no meetings today) SSML generated: %d characters",
                        len(ssml_output),
                    )
            except Exception as e:
                logger.error(
                    "Launch summary (no meetings today) SSML generation failed: %s",
                    e,
                    exc_info=True,
                )

        # Build response
        response_data = {
            "speech_text": speech_text,
            "has_meetings_today": done_for_day_result["has_meetings_today"],
            "next_meeting": {
                "subject": primary_meeting["subject"],
                "start_iso": _serialize_iso(primary_meeting["event"].get("start")),
                "seconds_until_start": primary_meeting["seconds_until"],
                "duration_spoken": primary_meeting["duration_spoken"],
            }
            if primary_meeting
            else None,
            "done_for_day": done_for_day_result,
        }

        # Add SSML to response if generated
        if ssml_output:
            response_data["ssml"] = ssml_output

        return web.json_response(response_data, status=200)

    async def alexa_morning_summary(request):  # type: ignore[no-untyped-def]
        """Alexa endpoint for morning summary with intelligent context switching."""
        if not _check_bearer_token(request, alexa_bearer_token):
            return web.json_response({"error": "Unauthorized"}, status=401)

        try:
            # Parse request parameters
            target_date = request.query.get("date")  # ISO date for summary (defaults to tomorrow)
            timezone_str = request.query.get("timezone", _get_server_timezone())
            detail_level = request.query.get("detail_level", "normal")
            prefer_ssml = request.query.get("prefer_ssml", "false").lower() == "true"
            max_events = int(request.query.get("max_events", "50"))

            logger.debug(
                "Alexa morning summary called with tz=%s, prefer_ssml=%s", timezone_str, prefer_ssml
            )

            # Read window with lock to be consistent
            async with window_lock:
                window = tuple(event_window_ref[0])

            # Convert raw events to LiteCalendarEvent objects for morning summary service
            from .lite_models import (
                LiteCalendarEvent,
                LiteDateTimeInfo,
                LiteEventStatus,
                LiteLocation,
            )
            from .morning_summary import MorningSummaryRequest, MorningSummaryService

            lite_events = []
            for ev in window:
                try:
                    # Convert raw event dict to LiteCalendarEvent
                    start_dt = ev.get("start")
                    duration_seconds = ev.get("duration_seconds", 3600)  # Default 1 hour

                    if not isinstance(start_dt, datetime.datetime):
                        continue

                    end_dt = start_dt + datetime.timedelta(seconds=duration_seconds)

                    # Create location object if location exists
                    location_obj = None
                    if ev.get("location"):
                        location_obj = LiteLocation(display_name=ev.get("location", ""))

                    lite_event = LiteCalendarEvent(
                        id=ev.get("meeting_id", f"event_{id(ev)}"),  # Use meeting_id or fallback
                        subject=ev.get("subject", "Untitled meeting"),
                        start=LiteDateTimeInfo(date_time=start_dt),
                        end=LiteDateTimeInfo(date_time=end_dt),
                        location=location_obj,
                        is_online_meeting=ev.get("is_online_meeting", False),
                        is_cancelled=False,  # Assume not cancelled if in window
                        show_as=LiteEventStatus.BUSY,  # Default to busy
                    )
                    lite_events.append(lite_event)
                except Exception as e:
                    logger.warning("Failed to convert event to LiteCalendarEvent: %s", e)
                    continue

            # Create morning summary request
            summary_request = MorningSummaryRequest(
                date=target_date,
                timezone=timezone_str,
                detail_level=detail_level,
                prefer_ssml=prefer_ssml,
                max_events=max_events,
            )

            # Generate morning summary
            service = MorningSummaryService()
            summary_result = await service.generate_summary(lite_events, summary_request)

            # Generate SSML if requested and available
            ssml_output = None
            if prefer_ssml and summary_result.speech_text:
                try:
                    from .alexa_ssml import render_morning_summary_ssml

                    ssml_output = render_morning_summary_ssml(summary_result)
                    if ssml_output:
                        logger.info(
                            "Morning summary SSML generated: %d characters", len(ssml_output)
                        )
                except Exception as e:
                    logger.error("Morning summary SSML generation failed: %s", e, exc_info=True)

            # Build response following existing Alexa endpoint patterns
            response_data = {
                "speech_text": summary_result.speech_text,
                "summary": {
                    "preview_for": summary_result.metadata.get("preview_for", "tomorrow_morning"),
                    "total_meetings_equivalent": summary_result.total_meetings_equivalent,
                    "early_start_flag": summary_result.early_start_flag,
                    "density": summary_result.density,
                    "back_to_back_count": summary_result.back_to_back_count,
                    "timeframe_start": summary_result.timeframe_start.isoformat(),
                    "timeframe_end": summary_result.timeframe_end.isoformat(),
                    "wake_up_recommendation": summary_result.wake_up_recommendation_time.isoformat()
                    if summary_result.wake_up_recommendation_time
                    else None,
                },
            }

            # Add SSML to response if generated
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        except Exception as e:
            logger.error("Morning summary endpoint failed: %s", e, exc_info=True)
            return web.json_response(
                {
                    "error": "Internal server error",
                    "speech_text": "Sorry, I couldn't generate your morning summary right now. Please try again later.",
                },
                status=500,
            )

    async def morning_summary(request):  # type: ignore[no-untyped-def]
        """General API endpoint for morning summary with full structured data.

        Returns comprehensive morning summary data for programmatic consumption,
        excluding Alexa-specific fields like speech_text and ssml.

        Query Parameters:
            date (str, optional): ISO date for summary (defaults to tomorrow)
            timezone (str, optional): IANA timezone identifier (default: UTC)
            detail_level (str, optional): Detail level: brief|normal|detailed (default: normal)
            max_events (int, optional): Maximum events to process (default: 50)

        Returns:
            JSON response with complete summary structure including timeframe,
            meeting analysis, free blocks, density metrics, and metadata.
        """
        # No authentication required for general API endpoints

        try:
            # Parse request parameters - same as Alexa endpoint but no prefer_ssml
            target_date = request.query.get("date")  # ISO date for summary (defaults to tomorrow)
            timezone_str = request.query.get("timezone", _get_server_timezone())
            detail_level = request.query.get("detail_level", "normal")
            max_events = int(request.query.get("max_events", "50"))

            logger.debug(
                "Morning summary called with tz=%s, detail_level=%s", timezone_str, detail_level
            )

            # Read window with lock to be consistent
            async with window_lock:
                window = tuple(event_window_ref[0])

            # Convert raw events to LiteCalendarEvent objects for morning summary service
            from .lite_models import (
                LiteCalendarEvent,
                LiteDateTimeInfo,
                LiteEventStatus,
                LiteLocation,
            )
            from .morning_summary import MorningSummaryRequest, MorningSummaryService

            lite_events = []
            for ev in window:
                try:
                    # Convert raw event dict to LiteCalendarEvent
                    start_dt = ev.get("start")
                    duration_seconds = ev.get("duration_seconds", 3600)  # Default 1 hour

                    if not isinstance(start_dt, datetime.datetime):
                        continue

                    end_dt = start_dt + datetime.timedelta(seconds=duration_seconds)

                    # Create location object if location exists
                    location_obj = None
                    if ev.get("location"):
                        location_obj = LiteLocation(display_name=ev.get("location", ""))

                    lite_event = LiteCalendarEvent(
                        id=ev.get("meeting_id", f"event_{id(ev)}"),  # Use meeting_id or fallback
                        subject=ev.get("subject", "Untitled meeting"),
                        start=LiteDateTimeInfo(date_time=start_dt),
                        end=LiteDateTimeInfo(date_time=end_dt),
                        location=location_obj,
                        is_online_meeting=ev.get("is_online_meeting", False),
                        is_cancelled=False,  # Assume not cancelled if in window
                        show_as=LiteEventStatus.BUSY,  # Default to busy
                    )
                    lite_events.append(lite_event)
                except Exception as e:
                    logger.warning("Failed to convert event to LiteCalendarEvent: %s", e)
                    continue

            # Create morning summary request (no prefer_ssml for general API)
            summary_request = MorningSummaryRequest(
                date=target_date,
                timezone=timezone_str,
                detail_level=detail_level,
                prefer_ssml=False,  # General API doesn't need SSML
                max_events=max_events,
            )

            # Generate morning summary
            service = MorningSummaryService()
            summary_result = await service.generate_summary(lite_events, summary_request)

            # Build response with full structured data (exclude Alexa-specific fields)
            summary_data = {
                "timeframe_start": summary_result.timeframe_start.isoformat(),
                "timeframe_end": summary_result.timeframe_end.isoformat(),
                "analysis_time": summary_result.analysis_time.isoformat(),
                "total_meetings_equivalent": summary_result.total_meetings_equivalent,
                "early_start_flag": summary_result.early_start_flag,
                "density": summary_result.density,
                "back_to_back_count": summary_result.back_to_back_count,
                "meeting_insights": [
                    {
                        "meeting_id": insight.meeting_id,
                        "subject": insight.subject,
                        "start_time": insight.start_time.isoformat(),
                        "end_time": insight.end_time.isoformat(),
                        "time_until_minutes": insight.time_until_minutes,
                        "preparation_needed": insight.preparation_needed,
                        "is_online": insight.is_online,
                        "attendees_count": insight.attendees_count,
                        "short_note": insight.short_note,
                    }
                    for insight in summary_result.meeting_insights
                ],
                "free_blocks": [
                    {
                        "start_time": block.start_time.isoformat(),
                        "end_time": block.end_time.isoformat(),
                        "duration_minutes": block.duration_minutes,
                        "recommended_action": block.recommended_action,
                        "is_significant": block.is_significant,
                    }
                    for block in summary_result.free_blocks
                ],
                "metadata": summary_result.metadata,
            }

            # Add wake-up recommendation if available
            if summary_result.wake_up_recommendation_time:
                summary_data["wake_up_recommendation_time"] = (
                    summary_result.wake_up_recommendation_time.isoformat()
                )

            response_data = {"summary": summary_data}

            return web.json_response(response_data, status=200)

        except Exception as e:
            logger.error("Morning summary endpoint failed: %s", e, exc_info=True)
            return web.json_response(
                {
                    "error": "Internal server error",
                    "message": "Failed to generate morning summary. Please try again later.",
                },
                status=500,
            )

    # General API routes
    app.router.add_post("/api/morning-summary", morning_summary)

    # Alexa-specific API routes
    app.router.add_get("/api/alexa/next-meeting", alexa_next_meeting)
    app.router.add_get("/api/alexa/time-until-next", alexa_time_until_next)
    app.router.add_get("/api/alexa/done-for-day", alexa_done_for_day)
    app.router.add_get("/api/alexa/launch-summary", alexa_launch_summary)
    app.router.add_post("/api/alexa/morning-summary", alexa_morning_summary)

    logger.debug(
        "Routes wired: / (static HTML), /whatsnext.css, /whatsnext.js, /api/whats-next GET, /api/skip POST and DELETE, /api/clear_skips GET, /api/done-for-day GET, /api/alexa/next-meeting GET, /api/alexa/time-until-next GET, /api/alexa/done-for-day GET"
    )

    # Provide a stop handler to allow external shutdown if needed.
    async def _shutdown(_app):  # type: ignore[no-untyped-def]
        logger.info("Application shutdown requested")

    app.on_shutdown.append(_shutdown)
    return app


async def _serve(config: Any, skipped_store: object | None) -> None:
    """Internal coroutine to run server and background tasks until signalled to stop."""
    # Event window stored as single-element list for atomic replacement semantics.
    event_window_ref: list[tuple[EventDict, ...]] = [()]
    window_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    # Initialize shared HTTP client for connection reuse optimization
    shared_http_client = None
    try:
        shared_http_client = await get_shared_client("lite_server")
        logger.info("Initialized shared HTTP client for connection reuse")
    except Exception as e:
        logger.warning(
            "Failed to initialize shared HTTP client, falling back to individual clients: %s", e
        )

    # Create web app (may raise if aiohttp not available).
    try:
        # Log the environment and incoming config to diagnose missing source entries.
        import os as _os

        env_url = _os.environ.get("CALENDARBOT_ICS_URL")
        masked = env_url[:40] + ("..." if len(env_url) > 40 else "") if env_url else None
        logger.debug("Startup env CALENDARBOT_ICS_URL (masked): %s", masked)
    except Exception:
        logger.debug("Failed to read CALENDARBOT_ICS_URL from environment", exc_info=True)

    try:
        # Emit the raw config passed to _serve for debugging (non-sensitive keys).
        if isinstance(config, dict):
            cfg_preview = {
                k: config.get(k) for k in ("ics_sources", "sources", "server_bind", "server_port")
            }
        else:
            cfg_preview = str(config)  # type: ignore[assignment]
        logger.debug("Config passed to _serve (preview): %s", cfg_preview)
    except Exception:
        logger.debug("Failed to emit config preview", exc_info=True)

    logger.info(
        "Creating web application (aiohttp may be imported). Config summary: %s",
        ", ".join(
            f"{k}={v!r}"
            for k, v in (config.items() if isinstance(config, dict) else [("config", repr(config))])
        ),
    )
    app = await _make_app(
        config, skipped_store, event_window_ref, window_lock, stop_event, shared_http_client
    )
    logger.debug("Web application created")

    # Setup runner and TCP site
    from aiohttp import web  # type: ignore

    runner = web.AppRunner(app)
    await runner.setup()

    host = _get_config_value(config, "server_bind", "0.0.0.0")  # nosec: B104 - default bind for dev; allow override via config/env
    port = int(_get_config_value(config, "server_port", 8080))

    # Check for port conflicts and handle them
    if not _handle_port_conflict(host, port):
        logger.error("Failed to resolve port conflict on %s:%d - server cannot start", host, port)
        log_monitoring_event(
            "server.startup.port_conflict",
            f"Port conflict on {host}:{port} could not be resolved",
            "CRITICAL",
            details={"host": host, "port": port},
            include_system_state=True,
        )
        raise PortConflictError(f"Port {port} is occupied and could not be freed")

    site = web.TCPSite(runner, host=host, port=port)
    try:
        await site.start()
        logger.info("Server started successfully on %s:%d", host, port)
        log_monitoring_event(
            "server.startup.success",
            f"CalendarBot_Lite server started successfully on {host}:{port}",
            "INFO",
            details={"host": host, "port": port, "pid": os.getpid()},
            include_system_state=True,
        )
    except OSError as e:
        if "Address already in use" in str(e):
            logger.exception("Port %d is still occupied after conflict resolution", port)
            log_monitoring_event(
                "server.startup.port_still_occupied",
                f"Port {port} still occupied after conflict resolution",
                "CRITICAL",
                details={"host": host, "port": port, "error": str(e)},
                include_system_state=True,
            )
            raise RuntimeError(f"Port {port} is still occupied: {e}") from e
        logger.exception("Failed to start server on %s:%d", host, port)
        log_monitoring_event(
            "server.startup.failure",
            f"Failed to start server on {host}:{port}",
            "CRITICAL",
            details={"host": host, "port": port, "error": str(e)},
            include_system_state=True,
        )
        raise

    # Start background refresher task
    logger.debug(" Creating background refresher task")
    refresher = asyncio.create_task(
        _refresh_loop(
            config, skipped_store, event_window_ref, window_lock, stop_event, shared_http_client
        )
    )
    logger.debug(" Background refresher task created: %r", refresher)

    # Wire signals for graceful shutdown
    loop = asyncio.get_running_loop()

    def _on_signal() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _on_signal)

    # Wait until stop_event is set (by signal) then cleanup.
    await stop_event.wait()
    logger.info("Stop event received, shutting down")
    log_monitoring_event(
        "server.shutdown.start",
        "Server shutdown initiated",
        "INFO",
        details={"uptime_seconds": _health_tracker.get_uptime_seconds()},
    )

    # Cancel refresher and wait for it to finish
    refresher.cancel()
    try:
        await refresher
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning("Refresher task error during shutdown: %s", e)

    # Cleanup web runner
    await runner.cleanup()

    # Cleanup shared HTTP clients
    try:
        await close_all_clients()
        logger.debug("Shared HTTP clients cleaned up")
    except Exception as e:
        logger.warning("Error cleaning up shared HTTP clients: %s", e)

    logger.info("Server shutdown complete")


def start_server(config: Any, skipped_store: object | None = None) -> None:
    """Start the asyncio event loop and HTTP server.

    Args:
        config: dict or dataclass-like object with keys:
            - server_bind: host to bind (str)
            - server_port: port (int)
            - refresh_interval_seconds: seconds between refreshes
            - rrule_expansion_days: days to expand rrules
            - event_window_size: number of upcoming events to keep
            - ics_sources: iterable of source configurations (passed to IcsSource)
            - debug_logging: enable debug logging for calendarbot_lite (bool)

            # Bounded Concurrency Configuration (Pi Zero 2W optimized)
            - fetch_concurrency: number of concurrent fetches (int, default 2, range 1-3)
            - rrule_worker_concurrency: RRULE worker pool size (int, default 1)

            # RRULE Worker Limits and Performance Controls
            - max_occurrences_per_rule: max events per RRULE (int, default 250)
            - expansion_days_window: expansion time window in days (int, default 365)
            - expansion_time_budget_ms_per_rule: time budget per RRULE in ms (int, default 200)
            - expansion_yield_frequency: yield to event loop after N events (int, default 50)

            # HTTP Fetcher Configuration
            - request_timeout: HTTP request timeout in seconds (int, default 30)
            - max_retries: maximum HTTP retries (int, default 3)
            - retry_backoff_factor: retry backoff multiplier (float, default 1.5)

        skipped_store: optional object implementing:
            - is_skipped(meeting_id) -> bool
            - add_skip(meeting_id) -> Optional[datetime|str]
            - clear_all() -> int
            These methods may be coroutine functions.

    This function blocks the calling thread and runs until a SIGINT/SIGTERM is received.
    aiohttp is required at runtime; imports are performed lazily so importing this module
    does not require aiohttp to be installed.
    """
    # Allow runtime control of debug logging via config
    debug_mode = _get_config_value(config, "debug_logging", False)
    try:
        from .lite_logging import configure_lite_logging

        configure_lite_logging(debug_mode=debug_mode)
        logger.info("Logging configuration applied: debug_mode=%s", debug_mode)
    except ImportError:
        logger.warning("lite_logging module not available, using basic configuration")

    try:
        logger.debug("Running asyncio event loop for server")
        asyncio.run(_serve(config, skipped_store))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except PortConflictError as e:
        logger.exception("Server cannot start")
        print(f"\nServer startup aborted: {e}")
        print("Please resolve the port conflict and try again.")
    except Exception:
        logger.exception("Server terminated unexpectedly")
