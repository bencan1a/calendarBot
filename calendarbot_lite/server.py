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

# Import models for type annotations
from .lite_models import LiteCalendarEvent

# Import timezone utilities (consolidated from duplicate implementations)
from .timezone_utils import (
    get_server_timezone as _get_server_timezone,
    now_utc as _now_utc,
)

# Import and configure logging early for Pi Zero 2W optimization
try:
    from .lite_logging import configure_lite_logging

    # Apply lite logging configuration on module import
    configure_lite_logging(debug_mode=False)
except ImportError:
    # Fallback if lite_logging module is not available
    logging.basicConfig(level=logging.INFO)

# Import enhanced monitoring logging
monitoring_logger: Any = (
    None  # Type: Optional[MonitoringLogger] but we use Any to avoid circular imports
)
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
        logger.log(log_level, "[%s] %s", event, message)


# Health tracking infrastructure - lightweight in-memory tracking for monitoring
import os
from typing import Optional

# Initialize health tracker (replaces global health variables)
from .health_tracker import HealthTracker

_health_tracker = HealthTracker()

# Global storage for precomputed Alexa responses (updated on each refresh)
_precomputed_responses: dict[str, Any] = {}

# Import SSML generation for Alexa endpoints
try:
    from .alexa_ssml import (
        render_done_for_day_ssml,
        render_meeting_ssml,
        render_morning_summary_ssml,
        render_time_until_ssml,
    )

    logger.debug("SSML module imported successfully")
except ImportError as e:
    logger.warning("SSML module not available: %s", e)
    render_meeting_ssml = None  # type: ignore[assignment]
    render_time_until_ssml = None  # type: ignore[assignment]
    render_done_for_day_ssml = None  # type: ignore[assignment]
    render_morning_summary_ssml = None  # type: ignore[assignment]


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

    # Rate limiting configuration
    rate_limit_per_ip = os.environ.get("CALENDARBOT_RATE_LIMIT_PER_IP")
    if rate_limit_per_ip:
        try:
            cfg["rate_limit_per_ip"] = int(rate_limit_per_ip)
        except Exception:
            logger.warning("Invalid CALENDARBOT_RATE_LIMIT_PER_IP=%r; ignoring", rate_limit_per_ip)

    rate_limit_per_token = os.environ.get("CALENDARBOT_RATE_LIMIT_PER_TOKEN")
    if rate_limit_per_token:
        try:
            cfg["rate_limit_per_token"] = int(rate_limit_per_token)
        except Exception:
            logger.warning(
                "Invalid CALENDARBOT_RATE_LIMIT_PER_TOKEN=%r; ignoring", rate_limit_per_token
            )

    rate_limit_burst = os.environ.get("CALENDARBOT_RATE_LIMIT_BURST")
    if rate_limit_burst:
        try:
            cfg["rate_limit_burst"] = int(rate_limit_burst)
        except Exception:
            logger.warning("Invalid CALENDARBOT_RATE_LIMIT_BURST=%r; ignoring", rate_limit_burst)

    rate_limit_burst_window = os.environ.get("CALENDARBOT_RATE_LIMIT_BURST_WINDOW")
    if rate_limit_burst_window:
        try:
            cfg["rate_limit_burst_window"] = int(rate_limit_burst_window)
        except Exception:
            logger.warning(
                "Invalid CALENDARBOT_RATE_LIMIT_BURST_WINDOW=%r; ignoring", rate_limit_burst_window
            )

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


def _is_focus_time_event(event: LiteCalendarEvent) -> bool:
    """Check if event is Focus Time and should be skipped from whats-next.

    Args:
        event: LiteCalendarEvent with 'subject' attribute

    Returns:
        True if event is focus time, False otherwise
    """
    subject = event.subject.lower()
    return any(keyword in subject for keyword in FOCUS_TIME_KEYWORDS)


# Timezone utility functions now imported from timezone_utils module (see imports at top)
# This eliminates ~186 lines of duplicate code that was previously defined here.
# Functions available: _get_server_timezone(), _get_fallback_timezone(), _now_utc()


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
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")


def _get_precomputed_response(cache_key: str) -> dict[str, Any] | None:
    """Get precomputed Alexa response if available.

    Args:
        cache_key: Key for the precomputed response (e.g., "NextMeetingHandler:UTC")

    Returns:
        Precomputed response dict or None if not available
    """
    return _precomputed_responses.get(cache_key)


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
            tz = datetime.UTC  # type: ignore[assignment]
    except Exception:
        logger.warning("Invalid timezone %r, falling back to UTC", request_tz)
        tz = datetime.UTC  # type: ignore[assignment]

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
) -> tuple[str, list[LiteCalendarEvent]] | list[Any]:
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
        List of parsed events as LiteCalendarEvent objects (not yet converted to EventDict)
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

            # Parse ICS content using EventProcessingPipeline
            # This is Pipeline 1 (per-source): processes each ICS source independently
            logger.info("=== Source Pipeline: Processing ICS from %r ===", source.name)
            logger.debug("ICS content size: %d bytes from %r", len(ics_content), source.url)

            from .pipeline import EventProcessingPipeline, ProcessingContext
            from .pipeline_stages import DeduplicationStage, ParseStage, SortStage

            # Create per-source processing pipeline (runs once per ICS source)
            # This pipeline handles: parsing raw ICS → expanding RRULEs → removing source-internal duplicates → sorting
            # Note: Filtering/windowing/limiting happen later in _refresh_once after all sources are combined
            parser = LiteICSParser(_Settings())
            pipeline = (
                EventProcessingPipeline()
                .add_stage(ParseStage(parser))  # Parse ICS + expand RRULEs
                .add_stage(DeduplicationStage())  # Remove source-internal duplicates
                .add_stage(SortStage())  # Sort by time
            )

            # Create processing context
            context = ProcessingContext(
                raw_content=ics_content,
                source_url=source.url,
                source_name=source.name,
                rrule_expansion_days=rrule_days,
                enable_streaming=True,
            )

            # Process through pipeline
            result = await pipeline.process(context)

            if not result.success:
                logger.warning(
                    "Pipeline processing failed for source %r: %s",
                    src_cfg,
                    "; ".join(result.errors) if result.errors else "Unknown error",
                )
                return []

            if not context.events:
                logger.debug("No events found in source %r", src_cfg)
                return []

            # Log pipeline statistics
            logger.debug(
                "Pipeline processed %d events from source %r (warnings: %d)",
                len(context.events),
                src_cfg,
                len(result.warnings),
            )

            # Return tuple of (source_name, events) to preserve source information
            # Conversion to EventDict happens later after all sources are processed and filtered
            logger.debug(
                "Successfully processed %d events from source %r", len(context.events), src_cfg
            )
            return (source.name, context.events)

        except ImportError:
            logger.exception("Required modules not available")
            return []
        except Exception:
            logger.exception("Unexpected error while processing source %r", src_cfg)
            return []


async def _refresh_once(
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[LiteCalendarEvent, ...]],
    window_lock: asyncio.Lock,
    shared_http_client: Any = None,
    response_cache: Any = None,
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
        response_cache: Optional ResponseCache to invalidate on window update
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

    # Import AsyncOrchestrator for centralized async patterns
    from .async_utils import get_global_orchestrator

    orchestrator = get_global_orchestrator()

    # Use bounded concurrency for fetching sources
    semaphore = asyncio.Semaphore(fetch_concurrency)
    fetch_tasks = [
        asyncio.create_task(
            _fetch_and_parse_source(semaphore, src_cfg, config, rrule_days, shared_http_client)
        )
        for src_cfg in sources_cfg
    ]

    # Execute all fetch tasks concurrently with timeout management
    # Use 120s timeout for fetching all sources (reasonable for multiple ICS fetches)
    fetch_results = await orchestrator.gather_with_timeout(
        *fetch_tasks, timeout=120.0, return_exceptions=True
    )

    # Process results and collect parsed LiteCalendarEvent objects
    from .lite_models import LiteCalendarEvent

    parsed_events: list[LiteCalendarEvent] = []
    event_source_map: dict[str, str] = {}  # event_id -> source_name

    for i, result in enumerate(fetch_results):
        if isinstance(result, Exception):
            logger.error("DEBUG: Source %r failed: %s", sources_cfg[i], result)
            continue
        if isinstance(result, tuple) and len(result) == 2:
            source_name, events = result
            logger.debug(" Source %r returned %d events", sources_cfg[i], len(events))
            for event in events:
                parsed_events.append(event)
                event_source_map[event.id] = source_name
        elif isinstance(result, list):
            # Fallback for old return format (should not happen in production)
            # Skip dict objects (EventDict) - only process LiteCalendarEvent objects
            logger.debug(
                " Source %r returned %d items (checking types)", sources_cfg[i], len(result)
            )
            for item in result:
                if isinstance(item, LiteCalendarEvent):
                    parsed_events.append(item)
                elif isinstance(item, dict):
                    # Skip EventDict objects - these are from old code paths
                    logger.warning(
                        "Skipping EventDict from source %r - not compatible with pipeline",
                        sources_cfg[i],
                    )
                    continue

    logger.debug(" Total parsed events from all sources: %d", len(parsed_events))

    # Get current time and window size for pipeline configuration
    now = _now_utc()
    window_size = int(_get_config_value(config, "event_window_size", 50))

    # Get skipped event IDs from store if available
    skipped_event_ids: set[str] = set()
    if skipped_store is not None:
        try:
            active_list_fn = getattr(skipped_store, "active_list", None)
            if callable(active_list_fn):
                active_skips = active_list_fn()
                if active_skips and hasattr(active_skips, "keys"):
                    skipped_event_ids = set(active_skips.keys())  # type: ignore[attr-defined]
                    logger.debug("Loaded %d skipped event IDs from store", len(skipped_event_ids))
        except Exception as e:
            logger.warning("Failed to get skipped event IDs: %s", e)

    # Pipeline 2 (multi-source post-processing): processes combined events from all sources
    logger.info(
        "=== Post-Processing Pipeline: Filtering and limiting %d combined events ===",
        len(parsed_events),
    )

    from .pipeline import EventProcessingPipeline, ProcessingContext
    from .pipeline_stages import EventLimitStage, SkippedEventsFilterStage, TimeWindowStage

    # Create multi-source post-processing pipeline (runs once after combining all sources)
    # This pipeline handles: filtering skipped events → applying time window → limiting to display size
    post_pipeline = (
        EventProcessingPipeline()
        .add_stage(SkippedEventsFilterStage())
        .add_stage(TimeWindowStage())
        .add_stage(EventLimitStage())
    )

    # Calculate window start to include past events from today
    # Go back 24 hours to ensure we capture events from "today" in any timezone
    # This is needed for done-for-day queries that need to see completed meetings
    import datetime

    window_start = now - datetime.timedelta(hours=24)

    # Create context for post-processing
    post_context = ProcessingContext(
        events=parsed_events,
        skipped_event_ids=skipped_event_ids,
        window_start=window_start,  # Start from 24 hours ago to include past events from today
        window_end=None,  # No end limit (TimeWindowStage will handle)
        event_window_size=window_size,
        now=now,
    )

    # Process through post-processing pipeline
    post_result = await post_pipeline.process(post_context)

    if not post_result.success:
        logger.warning(
            "Post-processing pipeline failed: %s",
            "; ".join(post_result.errors) if post_result.errors else "Unknown error",
        )
        # Fall back to using all parsed events if post-processing fails
        final_events = parsed_events
    else:
        final_events = post_context.events
        logger.debug(
            "Post-processing pipeline complete: %d → %d events (filtered: %d, warnings: %d)",
            post_result.events_in,
            post_result.events_out,
            post_result.events_in - post_result.events_out,
            len(post_result.warnings),
        )

    # Update the event window atomically with LiteCalendarEvent objects
    # NOTE: Changed from EventDict to LiteCalendarEvent for consistency across codebase
    async with window_lock:
        event_window_ref[0] = tuple(final_events)
        final_count = len(final_events)

    # Invalidate response cache since event window has changed
    if response_cache:
        response_cache.invalidate_all()
        logger.debug("Invalidated Alexa response cache after window update")

    # Run precomputation pipeline for Alexa responses (if enabled)
    try:
        from .alexa_precompute_stages import create_alexa_precompute_pipeline

        # Get default timezone for precomputation
        default_tz = _get_config_value(config, "default_timezone", "UTC")

        # Create precomputation pipeline
        precompute_pipeline = create_alexa_precompute_pipeline(
            skipped_store=skipped_store,  # type: ignore[arg-type]
            default_tz=default_tz,
            time_provider=_now_utc,
            duration_formatter=_format_duration_spoken,
            iso_serializer=_serialize_iso,  # type: ignore[arg-type]
            get_server_timezone=_get_server_timezone,  # type: ignore[arg-type]
        )

        # Run precomputation on the new events
        from .pipeline import ProcessingContext

        precompute_context = ProcessingContext(events=list(final_events))
        precompute_result = await precompute_pipeline.process(precompute_context)

        # Extract and store precomputed responses globally
        global _precomputed_responses
        _precomputed_responses = precompute_context.extra.get("precomputed_responses", {})

        if precompute_result.success:
            logger.debug(
                "Precomputed %d Alexa responses",
                len(_precomputed_responses),
            )
        else:
            logger.warning(
                "Precomputation completed with errors: %s",
                precompute_result.errors,
            )

    except ImportError:
        logger.debug("Alexa precomputation not available")
    except Exception as e:
        logger.warning("Failed to precompute Alexa responses: %s", e)

    updated = True  # We successfully updated the window
    message = f"Updated event window with {final_count} events"

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
            event.id,
            event.subject,
            event.start,
        )


async def _refresh_loop(
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[LiteCalendarEvent, ...]],
    window_lock: asyncio.Lock,
    stop_event: asyncio.Event,
    shared_http_client: Any = None,
    response_cache: Any = None,
) -> None:
    """Background refresher: immediate refresh then periodic refreshes."""
    interval = int(_get_config_value(config, "refresh_interval_seconds", 60))
    logger.debug(" _refresh_loop starting with interval %d seconds", interval)

    # Perform an initial refresh immediately.
    logger.debug(" Starting initial refresh")
    try:
        await _refresh_once(
            config, skipped_store, event_window_ref, window_lock, shared_http_client, response_cache
        )
        logger.debug(" Initial refresh completed")
    except Exception:
        logger.exception("DEBUG: Initial refresh failed")

    logger.debug(" Starting refresh loop")
    while not stop_event.is_set():
        try:
            logger.debug(" Sleeping for %d seconds until next refresh", interval)
            await asyncio.sleep(interval)
            if stop_event.is_set():
                break
            logger.debug(" Starting periodic refresh")
            await _refresh_once(
                config,
                skipped_store,
                event_window_ref,
                window_lock,
                shared_http_client,
                response_cache,
            )
            logger.debug(" Periodic refresh completed")
        except Exception:
            logger.exception("DEBUG: Refresh loop unexpected error")


def _event_to_api_model(ev: LiteCalendarEvent) -> dict[str, Any]:
    """Serialize LiteCalendarEvent to API response fields.

    Args:
        ev: LiteCalendarEvent object from event window

    Returns:
        Dictionary with API response fields
    """
    # Calculate duration in seconds
    duration_seconds = 0
    if ev.start.date_time and ev.end.date_time:
        duration_seconds = int((ev.end.date_time - ev.start.date_time).total_seconds())

    # Extract attendee emails/names
    attendees = []
    if ev.attendees:
        attendees = [
            attendee.email or attendee.name or "Unknown"
            for attendee in ev.attendees
            if attendee.email or attendee.name
        ]

    # Extract location display name
    location = ""
    if ev.location:
        location = ev.location.display_name

    return {
        "meeting_id": ev.id,
        "subject": ev.subject or "",
        "description": ev.body_preview or "",
        "attendees": attendees,
        "start_iso": _serialize_iso(ev.start.date_time),
        "duration_seconds": duration_seconds,
        "location": location,
        "raw_source": getattr(ev, "raw_source", None) or "",
    }


async def _make_app(  # type: ignore[no-untyped-def]
    _config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[LiteCalendarEvent, ...]],
    window_lock: asyncio.Lock,
    _stop_event: asyncio.Event,
    shared_http_client: Any = None,
    response_cache: Any = None,
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

    # Import correlation ID middleware
    from .middleware import correlation_id_middleware

    # Create app with correlation ID middleware
    app = web.Application(middlewares=[correlation_id_middleware])

    # Get the package directory for static file serving
    from pathlib import Path

    package_dir = Path(__file__).resolve().parent

    # Import route registration functions
    from .routes import register_alexa_routes, register_api_routes, register_static_routes

    # Register static file routes
    register_static_routes(app, package_dir)

    # Register API routes with all dependencies
    register_api_routes(
        app=app,
        config=_config,
        skipped_store=skipped_store,
        event_window_ref=event_window_ref,
        window_lock=window_lock,
        shared_http_client=shared_http_client,
        health_tracker=_health_tracker,
        time_provider=_now_utc,
        event_to_api_model=_event_to_api_model,
        is_focus_time_event=_is_focus_time_event,
        serialize_iso=_serialize_iso,
        get_system_diagnostics=_get_system_diagnostics,
        compute_last_meeting_end_for_today=_compute_last_meeting_end_for_today,
        get_server_timezone=_get_server_timezone,
    )

    # Get bearer token from config for Alexa endpoints
    alexa_bearer_token = _get_config_value(_config, "alexa_bearer_token")

    # Initialize rate limiter for Alexa endpoints
    rate_limiter = None
    try:
        from .rate_limiter import RateLimitConfig, RateLimiter

        # Get rate limit configuration from config or use defaults
        rate_limit_config = RateLimitConfig(
            per_ip_limit=int(_get_config_value(_config, "rate_limit_per_ip", 100)),
            per_token_limit=int(_get_config_value(_config, "rate_limit_per_token", 500)),
            burst_limit=int(_get_config_value(_config, "rate_limit_burst", 20)),
            burst_window_seconds=int(_get_config_value(_config, "rate_limit_burst_window", 10)),
        )

        rate_limiter = RateLimiter(rate_limit_config)
        logger.info("Initialized rate limiter for Alexa endpoints")
    except ImportError:
        logger.warning(
            "Rate limiter module not available, Alexa endpoints will run without rate limiting"
        )
    except Exception:
        logger.exception("Failed to initialize rate limiter")

    # Create SSML renderers dictionary for Alexa routes
    ssml_renderers = {
        "meeting": render_meeting_ssml,
        "time_until": render_time_until_ssml,
        "done_for_day": render_done_for_day_ssml,
        "morning_summary": render_morning_summary_ssml,
    }

    # Register Alexa routes
    register_alexa_routes(
        app=app,
        bearer_token=alexa_bearer_token,
        event_window_ref=event_window_ref,
        window_lock=window_lock,
        skipped_store=skipped_store,  # type: ignore[arg-type]
        time_provider=_now_utc,
        duration_formatter=_format_duration_spoken,
        iso_serializer=_serialize_iso,  # type: ignore[arg-type]
        ssml_renderers=ssml_renderers,  # type: ignore[arg-type]
        get_server_timezone=_get_server_timezone,
        response_cache=response_cache,
        precompute_getter=_get_precomputed_response,
        rate_limiter=rate_limiter,
    )

    # Store rate limiter in app for access by health endpoint
    if rate_limiter:
        app["rate_limiter"] = rate_limiter

    # Provide a stop handler to allow external shutdown if needed
    async def _shutdown(_app):  # type: ignore[no-untyped-def]
        logger.info("Application shutdown requested")
        # Stop rate limiter cleanup task
        if rate_limiter:
            await rate_limiter.stop()

    app.on_shutdown.append(_shutdown)
    return app


async def _serve(config: Any, skipped_store: object | None) -> None:
    """Internal coroutine to run server and background tasks until signalled to stop."""
    # Event window stored as single-element list for atomic replacement semantics.
    event_window_ref: list[tuple[LiteCalendarEvent, ...]] = [()]
    window_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    # Initialize Alexa response cache for improved performance
    response_cache = None
    try:
        from .alexa_response_cache import ResponseCache

        response_cache = ResponseCache(max_size=100)
        logger.info("Initialized Alexa response cache (max_size=100)")
    except ImportError:
        logger.debug("ResponseCache not available, caching disabled")

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
        config,
        skipped_store,
        event_window_ref,
        window_lock,
        stop_event,
        shared_http_client,
        response_cache,
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

        # Start rate limiter cleanup task if available
        if "rate_limiter" in app:
            await app["rate_limiter"].start()
            logger.debug("Rate limiter cleanup task started")

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
            config,
            skipped_store,
            event_window_ref,
            window_lock,
            stop_event,
            shared_http_client,
            response_cache,
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
