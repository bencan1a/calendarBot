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
# ruff: noqa: PLR0915

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import signal
from typing import Any

logger = logging.getLogger(__name__)
logger.debug("calendarbot_lite.server module loaded")


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
    import os  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

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

    return cfg


def _create_skipped_store_if_available() -> object | None:
    """Attempt to create a SkippedStore instance from calendarbot_lite.skipped_store.

    Returns the instance if available and constructable, otherwise None.
    """
    try:
        from .skipped_store import SkippedStore  # type: ignore  # noqa: PLC0415
    except Exception:
        return None
    try:
        return SkippedStore()
    except Exception as exc:
        logger.warning("Failed to create SkippedStore: %s", exc)
        return None


# Internal type for an event stored in the in-memory window.
EventDict = dict[str, Any]


def _now_utc() -> datetime.datetime:
    """Return current UTC time with tzinfo."""
    return datetime.datetime.now(datetime.timezone.utc)


def _get_config_value(config: Any, key: str, default: Any = None) -> Any:
    """Support dict or dataclass-like config access."""
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


def _serialize_iso(dt: datetime.datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


async def _refresh_once(  # noqa: PLR0912
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[EventDict, ...]],
    window_lock: asyncio.Lock,
) -> None:
    """Perform a single refresh: fetch sources, parse/expand events and update window.

    This function performs lazy imports of the calendarbot parsing/fetching modules
    and is resilient if those modules are not present yet.
    """
    logger.debug("Starting refresh_once")
    try:
        # Lazy imports of parsing/fetching modules from the main repo.
        from calendarbot.ics import (  # noqa: PLC0415
            parser as ics_parser,  # type: ignore
            rrule_expander,  # type: ignore
        )
        from calendarbot.sources import (  # noqa: PLC0415
            ics_source as ics_source_module,  # type: ignore
        )
    except Exception as exc:  # pragma: no cover - runtime may not have these modules
        logger.warning("Calendarbot parser/fetcher not available: %s", exc)
        return

    # Collect sources configuration
    sources_cfg = _get_config_value(config, "ics_sources", []) or []
    parsed_events: list[EventDict] = []

    # How many days to expand recurrences
    rrule_days = int(_get_config_value(config, "rrule_expansion_days", 14))
    logger.debug(
        "Refresh configuration: rrule_expansion_days=%d, sources_count=%d",
        rrule_days,
        len(sources_cfg),
    )

    for src_cfg in sources_cfg:
        logger.debug("Processing source configuration: %r", src_cfg)
        try:
            # Try constructing an IcsSource from configuration.
            # Attempt to find a constructor for a source object. Prefer calendarbot.sources.ics_source.IcsSource
            # but fall back to calendarbot.ics.models.ICSSource (Pydantic model) if present.
            ics_source_ctor = getattr(ics_source_module, "IcsSource", None)
            if ics_source_ctor is None:
                try:
                    from calendarbot.ics import (  # noqa: PLC0415
                        models as ics_models,  # type: ignore
                    )

                    ics_source_ctor = getattr(ics_models, "ICSSource", None)
                    if ics_source_ctor is not None:
                        logger.debug(
                            "Using ICSSource model from calendarbot.ics.models as source constructor"
                        )
                except Exception:
                    ics_source_ctor = None

            if ics_source_ctor is None:
                logger.debug(
                    "IcsSource class not found in calendarbot.sources.ics_source or calendarbot.ics.models"
                )
                continue

            # Normalize configured source into a calendarbot.ics.models.ICSSource and
            # use the shared ICSFetcher as the primary fetch path (simpler and predictable).
            raw_ics = None
            try:
                from calendarbot.ics import models as ics_models  # type: ignore  # noqa: PLC0415
                from calendarbot.ics.fetcher import ICSFetcher  # type: ignore  # noqa: PLC0415
            except Exception as e:
                logger.warning("Calendarbot ICS models/fetcher not available: %s", e)
                continue

            icssrc_model = getattr(ics_models, "ICSSource", None)
            if icssrc_model is None:
                logger.debug(
                    "ICSSource model not present in calendarbot.ics.models; skipping source %r",
                    src_cfg,
                )
                continue

            # Build a proper ICSSource instance from supported input shapes.
            try:
                if isinstance(src_cfg, icssrc_model):
                    icssrc = src_cfg
                elif isinstance(src_cfg, dict):
                    icssrc = icssrc_model(**src_cfg)
                elif isinstance(src_cfg, str):
                    icssrc = icssrc_model(name=str(src_cfg), url=str(src_cfg))
                else:
                    # Try mapping attributes if given an object
                    icssrc = icssrc_model(
                        name=getattr(src_cfg, "name", str(src_cfg)),
                        url=getattr(src_cfg, "url", str(src_cfg)),
                    )
            except Exception as e:
                logger.warning("Failed to construct ICSSource for %r: %s", src_cfg, e)
                continue

            logger.debug("Using ICSFetcher to fetch URL=%s", getattr(icssrc, "url", None))
            try:

                class _Settings:
                    # Minimal settings surface required by ICSFetcher.
                    # Provide sensible defaults but allow override from config.
                    request_timeout = int(_get_config_value(config, "request_timeout", 30))
                    max_retries = int(_get_config_value(config, "max_retries", 3))
                    retry_backoff_factor = float(
                        _get_config_value(config, "retry_backoff_factor", 1.5)
                    )

                fetcher_client = ICSFetcher(_Settings())
                async with fetcher_client as client:
                    response = await client.fetch_ics(icssrc, conditional_headers=None)

                # Diagnostic logging for response
                try:
                    logger.debug(
                        "ICSFetcher response: success=%s status=%s error=%r",
                        getattr(response, "success", None),
                        getattr(response, "status_code", None),
                        getattr(response, "error_message", None),
                    )
                    hdrs = getattr(response, "headers", None)
                    if hdrs:
                        logger.debug("ICSFetcher response headers: %s", hdrs)
                except Exception:
                    logger.debug("Failed to log ICSFetcher response diagnostics", exc_info=True)

                if (
                    response
                    and getattr(response, "success", False)
                    and getattr(response, "content", None)
                ):
                    raw_ics = response.content
                else:
                    logger.debug("ICSFetcher did not return content for %r", src_cfg)
                    raw_ics = None

            except Exception as e:
                logger.warning("Error fetching ICS for %r using ICSFetcher: %s", src_cfg, e)
                raw_ics = None

            if not raw_ics:
                logger.debug("No ICS data from source %r", src_cfg)
                continue

            # Parse calendar content into events.
            # Try module-level parsing functions first, otherwise instantiate ICSParser.
            parse_fn = None
            for name in ("parse_ics", "parse_calendar", "parse"):
                parse_fn = getattr(ics_parser, name, None)
                if callable(parse_fn):
                    break

            parsed = None
            if callable(parse_fn):
                try:
                    parsed = parse_fn(raw_ics)
                except Exception as e:
                    logger.warning(
                        "Parser function %s failed for source %r: %s",
                        getattr(parse_fn, "__name__", "<callable>"),
                        src_cfg,
                        e,
                    )
                    parsed = None
            else:
                # Fall back to ICSParser class if available
                parser_class = getattr(ics_parser, "ICSParser", None)
                if callable(parser_class):
                    try:
                        # Minimal settings object for parser instance
                        class _ParserSettings:
                            rrule_expansion_days = int(
                                _get_config_value(config, "rrule_expansion_days", 14)
                            )
                            enable_rrule_expansion = bool(
                                _get_config_value(config, "enable_rrule_expansion", True)
                            )
                            rrule_max_occurrences = int(
                                _get_config_value(config, "rrule_max_occurrences", 1000)
                            )

                        # Annotate parser_instance as Any so static type checkers won't
                        # complain about dynamic parse method attributes that may vary
                        # between parser implementations.
                        parser_instance: Any = parser_class(_ParserSettings())
                        if hasattr(parser_instance, "parse_ics_content_optimized"):
                            parsed = parser_instance.parse_ics_content_optimized(
                                raw_ics, source_url=getattr(icssrc, "url", None)
                            )
                        elif hasattr(parser_instance, "parse_ics_content"):
                            parsed = parser_instance.parse_ics_content(
                                raw_ics, source_url=getattr(icssrc, "url", None)
                            )
                        else:
                            logger.debug("ICSParser instance has no supported parse method")
                            parsed = None
                    except Exception as e:
                        logger.warning("ICSParser class failed for source %r: %s", src_cfg, e)
                        parsed = None
                else:
                    logger.debug(
                        "No parser found in calendarbot.ics.parser and no ICSParser class available"
                    )
                    parsed = None

            if not parsed:
                logger.debug("Parsing produced no result for source %r", src_cfg)
                continue

            # Emit concise parse diagnostics so the lite server logs show parsing activity.
            try:
                parsed_event_count = (
                    len(parsed)
                    if isinstance(parsed, list)
                    else getattr(parsed, "event_count", None)
                )
            except Exception:
                parsed_event_count = None
            try:
                calendar_name = (
                    None if isinstance(parsed, list) else getattr(parsed, "calendar_name", None)
                )
            except Exception:
                calendar_name = None
            try:
                parsed_source_url = getattr(parsed, "source_url", None) or getattr(
                    icssrc, "url", str(src_cfg)
                )
            except Exception:
                parsed_source_url = str(src_cfg)

            logger.debug(
                "Parsed ICS summary: events=%s calendar=%s source=%s",
                parsed_event_count,
                calendar_name,
                parsed_source_url,
            )

            # Ensure events_list is typed as a list to satisfy static checkers.
            events_list: list[EventDict] = (
                parsed if isinstance(parsed, list) else getattr(parsed, "events", []) or []
            )

            # Expand recurring events using rrule_expander if available.
            expand_fn = getattr(rrule_expander, "expand", None) or getattr(
                rrule_expander, "expand_events", None
            )
            if callable(expand_fn):
                try:
                    expanded = expand_fn(events_list, days=rrule_days)
                    if expanded is None:
                        # keep original events_list
                        pass
                    else:
                        # Convert any iterable/generator to a concrete list to satisfy static checkers.
                        try:
                            events_list = list(expanded)  # type: ignore[arg-type]
                        except Exception:
                            # If conversion fails, fall back to original list.
                            logger.debug(
                                "Failed to coerce expanded events to list; keeping original events_list",
                                exc_info=True,
                            )
                except Exception as e:
                    logger.warning("RRule expansion failed: %s", e)

            # Normalize events into our lightweight EventDict shape.
            for ev in events_list:
                # ev may be a dict-like or object with attributes.
                def _get(o, *names, default=None):
                    """Safely retrieve attribute/key from object or dict.

                    Usage: _get(obj, "attr1", "attr2", default=None)
                    """
                    for n in names:
                        # Skip any non-string name defensively
                        if not isinstance(n, str):
                            continue
                        if isinstance(o, dict) and n in o:
                            return o[n]
                        if hasattr(o, n):
                            return getattr(o, n)
                    return default

                start = _get(ev, "start", "dtstart")
                end = _get(ev, "end", "dtend")
                duration = _get(ev, "duration")
                uid = _get(ev, "uid", "id", "uid")
                summary = _get(ev, "summary", "subject", "title", "name")
                location = _get(ev, "location", "place")
                # Resolve raw_source robustly (handle dict-like or object event representations).
                if isinstance(ev, dict):
                    raw_source = ev.get("raw") or str(src_cfg)
                else:
                    raw_source = getattr(ev, "raw", None) or str(src_cfg)

                # Normalize start/end/duration to datetimes/seconds.
                start_dt = None
                end_dt = None
                duration_seconds = 0
                try:
                    # Resolve start to a datetime if possible
                    if isinstance(start, dict):
                        s = start.get("date_time") or start.get("dtstart") or start.get("dt")
                        start_dt = datetime.datetime.fromisoformat(s) if isinstance(s, str) else s
                    elif hasattr(start, "date_time"):
                        # Some parser objects expose `date_time` but static type checkers
                        # may not know the attribute. Use getattr and silence attribute
                        # checking to keep runtime behavior while avoiding type errors.
                        start_dt = getattr(start, "date_time", None)  # type: ignore[attr-defined]
                    elif isinstance(start, str):
                        start_dt = datetime.datetime.fromisoformat(start)
                    else:
                        start_dt = start

                    # Resolve end to a datetime if possible
                    if isinstance(end, dict):
                        e = end.get("date_time") or end.get("dtend") or end.get("dt")
                        end_dt = datetime.datetime.fromisoformat(e) if isinstance(e, str) else e
                    elif hasattr(end, "date_time"):
                        end_dt = getattr(end, "date_time", None)  # type: ignore[attr-defined]
                    elif isinstance(end, str):
                        end_dt = datetime.datetime.fromisoformat(end)
                    else:
                        end_dt = end

                    # Prefer computing duration from start/end when available
                    if start_dt is not None and end_dt is not None:
                        try:
                            duration_seconds = int((end_dt - start_dt).total_seconds())
                        except Exception:
                            duration_seconds = 0
                    elif duration is not None:
                        if hasattr(duration, "total_seconds"):
                            try:
                                duration_seconds = int(duration.total_seconds())
                            except Exception:
                                duration_seconds = 0
                        else:
                            try:
                                duration_seconds = int(duration)
                            except Exception:
                                duration_seconds = 0
                except Exception:
                    start_dt = None
                    duration_seconds = 0

                if start_dt is None:
                    continue

                meeting_id = (
                    str(uid) if uid is not None else f"{raw_source}:{_serialize_iso(start_dt)}"
                )

                parsed_events.append(
                    {
                        "meeting_id": meeting_id,
                        "subject": str(summary) if summary is not None else "",
                        "description": str(_get(ev, "description", "body", "body_preview") or ""),
                        "participants": _get(ev, "attendees", "participants", "attendee_list")
                        or [],
                        "start": start_dt,
                        "duration_seconds": int(duration_seconds),
                        "location": str(location) if location is not None else "",
                        "raw_source": raw_source,
                    }
                )

        except Exception:
            logger.exception("Unexpected error while processing source %r", src_cfg)

    # Filter out past events and skipped ones, sort and trim window size.
    now = _now_utc()
    upcoming = [
        e
        for e in parsed_events
        if isinstance(e.get("start"), datetime.datetime) and e["start"] >= now
    ]

    if skipped_store is not None:
        is_skipped_fn = getattr(skipped_store, "is_skipped", None)
        if callable(is_skipped_fn):
            try:
                upcoming = [e for e in upcoming if not is_skipped_fn(e["meeting_id"])]
            except Exception as e:
                logger.warning("skipped_store.is_skipped raised: %s", e)

    upcoming.sort(key=lambda e: e["start"])

    window_size = int(_get_config_value(config, "event_window_size", 10))
    pruned = upcoming[:window_size]

    # Store atomically (replace the single reference inside event_window_ref list).
    async with window_lock:
        event_window_ref[0] = tuple(pruned)
    logger.debug("Refresh complete; stored %d events", len(pruned))


async def _refresh_loop(
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[EventDict, ...]],
    window_lock: asyncio.Lock,
    stop_event: asyncio.Event,
) -> None:
    """Background refresher: immediate refresh then periodic refreshes."""
    interval = int(_get_config_value(config, "refresh_interval_seconds", 60))
    # Perform an initial refresh immediately.
    await _refresh_once(config, skipped_store, event_window_ref, window_lock)
    while not stop_event.is_set():
        try:
            await asyncio.sleep(interval)
            if stop_event.is_set():
                break
            await _refresh_once(config, skipped_store, event_window_ref, window_lock)
        except Exception:
            logger.exception("Refresh loop unexpected error")


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


async def _make_app(
    _config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[EventDict, ...]],
    window_lock: asyncio.Lock,
    _stop_event: asyncio.Event,
):
    """Create aiohttp web application with routes wired to the in-memory window.

    aiohttp is imported lazily here so the module can be imported without aiohttp installed.
    """
    # Lazy import aiohttp.web
    try:
        from aiohttp import web  # type: ignore  # noqa: PLC0415
    except Exception:  # pragma: no cover - requires aiohttp at runtime
        logger.exception("aiohttp is required to run the server")
        raise
    else:
        logger.debug("aiohttp successfully imported; building web.Application")

    app = web.Application()

    async def whats_next(_request):
        now = _now_utc()
        # Read window with lock to be consistent.
        async with window_lock:
            window = tuple(event_window_ref[0])

        # Find first non-skipped upcoming meeting and compute seconds_until_start now.
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
                    logger.warning("skipped_store.is_skipped raised during api call: %s", e)
            model = _event_to_api_model(ev)
            model["seconds_until_start"] = seconds_until
            return web.json_response({"meeting": model}, status=200)

        return web.json_response({"meeting": None}, status=200)

    async def post_skip(request):
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

    async def delete_skip(_request):
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

    async def whats_next_page(_request):
        """Serve a simple HTML page that calls the server /api/whats-next endpoint and refreshes every 5 minutes."""
        html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>What's Next</title>
  <style>
    body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; padding: 1rem; }
    pre { background:#f6f8fa; padding:1rem; border-radius:6px; overflow:auto; }
    #status { margin-bottom: 0.5rem; font-weight:600; }
  </style>
</head>
<body>
  <h1>What's Next</h1>
  <div id="status">Loading…</div>
  <pre id="event" aria-live="polite"></pre>

  <script>
    const API = '/api/whats-next';
    async function fetchAndRender() {
      const statusEl = document.getElementById('status');
      const eventEl = document.getElementById('event');
      try {
        const res = await fetch(API, { cache: 'no-store' });
        if (!res.ok) {
          statusEl.textContent = 'API error: ' + res.status;
          eventEl.textContent = '';
          return;
        }
        const data = await res.json();
        if (data && data.meeting) {
          const m = data.meeting;
          statusEl.textContent = m.subject ? (`Next: ${m.subject} — in ${m.seconds_until_start}s`) : (`Next meeting in ${m.seconds_until_start}s`);
          eventEl.textContent = JSON.stringify(m, null, 2);
        } else {
          statusEl.textContent = 'No upcoming meetings';
          eventEl.textContent = '';
        }
      } catch (err) {
        statusEl.textContent = 'Fetch error';
        eventEl.textContent = String(err);
      }
    }

    // Initial load and periodic refresh every 5 minutes.
    fetchAndRender();
    setInterval(fetchAndRender, 5 * 60 * 1000);
  </script>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    # Page route that displays whats-next and auto-refreshes by calling the API.
    app.router.add_get("/", whats_next_page)
    app.router.add_get("/api/whats-next", whats_next)
    app.router.add_post("/api/skip", post_skip)
    app.router.add_delete("/api/skip", delete_skip)
    logger.debug(
        "API routes wired: /api/whats-next GET, /api/skip POST and DELETE; root '/' serves whats-next page"
    )

    # Provide a stop handler to allow external shutdown if needed.
    async def _shutdown(_app):
        logger.info("Application shutdown requested")

    app.on_shutdown.append(_shutdown)
    return app


async def _serve(config: Any, skipped_store: object | None) -> None:
    """Internal coroutine to run server and background tasks until signalled to stop."""
    # Event window stored as single-element list for atomic replacement semantics.
    event_window_ref: list[tuple[EventDict, ...]] = [()]
    window_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    # Create web app (may raise if aiohttp not available).
    try:
        # Log the environment and incoming config to diagnose missing source entries.
        import os as _os  # noqa: PLC0415

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
            cfg_preview = str(config)
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
    app = await _make_app(config, skipped_store, event_window_ref, window_lock, stop_event)
    logger.debug("Web application created")

    # Setup runner and TCP site
    from aiohttp import web  # type: ignore  # noqa: PLC0415

    runner = web.AppRunner(app)
    await runner.setup()

    host = _get_config_value(config, "server_bind", "0.0.0.0")  # nosec: B104 - default bind for dev; allow override via config/env
    port = int(_get_config_value(config, "server_port", 8080))
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logger.info("Server started on %s:%d", host, port)

    # Start background refresher task
    refresher = asyncio.create_task(
        _refresh_loop(config, skipped_store, event_window_ref, window_lock, stop_event)
    )

    # Wire signals for graceful shutdown
    loop = asyncio.get_running_loop()

    def _on_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _on_signal)

    # Wait until stop_event is set (by signal) then cleanup.
    await stop_event.wait()
    logger.info("Stop event received, shutting down")

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
        skipped_store: optional object implementing:
            - is_skipped(meeting_id) -> bool
            - add_skip(meeting_id) -> Optional[datetime|str]
            - clear_all() -> int
            These methods may be coroutine functions.

    This function blocks the calling thread and runs until a SIGINT/SIGTERM is received.
    aiohttp is required at runtime; imports are performed lazily so importing this module
    does not require aiohttp to be installed.
    """
    try:
        logger.debug("Running asyncio event loop for server")
        asyncio.run(_serve(config, skipped_store))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception:
        logger.exception("Server terminated unexpectedly")
