"""
Lightweight debug helpers for calendar diagnostics (CalendarBot Lite).

Provides:
- .read_env to read minimal env keys from a .env file
- .fetch_ics_stream to yield bytes from an ICS HTTP(S) source
- .parse_stream_via_parser to call lite_parser.parse_ics_stream and return the parse result
- .event_summary to produce a small serializable summary of LiteCalendarEvent objects
- .collect_rrule_candidates to extract (event, rrule_string, exdates) tuples for expansion

These helpers are intentionally small and dependency-light so debug scripts can import them
without requiring changes to core library behavior.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from typing import Any, Optional

import httpx

from .lite_models import LiteCalendarEvent
from .lite_rrule_expander import expand_events_async
from .lite_streaming_parser import parse_ics_stream

logger = logging.getLogger(__name__)


def read_env(env_path: str | Path) -> dict[str, Optional[str]]:
    """Read a minimal .env-style file and return selected keys.

    Supported keys (preferred):
      - CALENDARBOT_ICS_URL (url or file path)
      - DATETIME_OVERRIDE
      - CALENDARBOT_DEBUG

    Backwards compatibility:
      - If a legacy ICS_SOURCE key is present in .env, it will be mapped to CALENDARBOT_ICS_URL.

    This is intentionally not a full dotenv implementation (keeps deps low).
    """
    env: dict[str, Optional[str]] = {
        "CALENDARBOT_ICS_URL": None,
        "DATETIME_OVERRIDE": None,
        "CALENDARBOT_DEBUG": None,
    }
    p = Path(env_path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        # Accept both the new primary key and the legacy ICS_SOURCE for backwards compatibility
        if k in {"ICS_SOURCE", "CALENDARBOT_ICS_URL"}:
            env["CALENDARBOT_ICS_URL"] = v
        elif k in env:
            env[k] = v
    return env


async def fetch_ics_stream(url: str, timeout: int = 30) -> AsyncIterator[bytes]:
    """Async generator yielding byte chunks for an ICS URL using httpx.

    Yields bytes suitable for consumption by parse_ics_stream (AsyncIterator[bytes]).
    """
    async with (
        httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client,
        client.stream("GET", url) as resp,
    ):
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes():
            if not chunk:
                continue
            yield chunk


async def parse_stream_via_parser(
    byte_stream: AsyncIterator[bytes],
    source_url: Optional[str] = None,
) -> Any:
    """Call calendarbot_lite.lite_parser.parse_ics_stream and return its result.

    Returns the LiteICSParseResult instance produced by the parser.
    """
    return await parse_ics_stream(byte_stream, source_url=source_url)


def event_summary(ev: LiteCalendarEvent) -> dict[str, Any]:
    """Return a small serializable summary of a LiteCalendarEvent."""
    try:
        start_dt = getattr(ev.start, "date_time", None)
        end_dt = getattr(ev.end, "date_time", None)
        tz = getattr(ev.start, "time_zone", None) or getattr(ev, "time_zone", None) or None
    except Exception:
        start_dt = None
        end_dt = None
        tz = None

    return {
        "id": getattr(ev, "id", None),
        "subject": getattr(ev, "subject", None),
        "start": getattr(start_dt, "isoformat", lambda: str(start_dt))()
        if start_dt is not None
        else None,
        "end": getattr(end_dt, "isoformat", lambda: str(end_dt))() if end_dt is not None else None,
        "time_zone": tz,
        "is_recurring": getattr(ev, "is_recurring", False),
        "rrule": getattr(ev, "rrule_string", None) or getattr(ev, "rrule", None),
        "exdates": getattr(ev, "exdates", None) or getattr(ev, "exdate", None),
        "is_cancelled": getattr(ev, "is_cancelled", False),
    }


def collect_rrule_candidates(
    parsed_events: Iterable[Any],
) -> list[tuple[Any, str, Optional[list[str]]]]:
    """From parsed events, build a list of (event, rrule_string, exdates) tuples.

    The parsed events may be LiteCalendarEvent instances or dict-like objects produced
    by the parser. This helper defensive-checks common attribute names.
    """
    candidates: list[tuple[Any, str, Optional[list[str]]]] = []
    for ev in parsed_events:
        # support both model instances and dicts
        rrule_str = None
        exdates = None
        try:
            rrule_str = getattr(ev, "rrule_string", None) or getattr(ev, "rrule", None)
            exdates = getattr(ev, "exdates", None) or getattr(ev, "exdate", None)
        except Exception:
            # dict-like
            if isinstance(ev, dict):
                rrule_str = ev.get("rrule_string") or ev.get("rrule")
                exdates = ev.get("exdates") or ev.get("exdate")
        if rrule_str:
            candidates.append((ev, str(rrule_str), list(exdates) if exdates else None))
    return candidates


async def expand_candidates_to_trace(
    candidates: list[tuple[Any, str, Optional[list[str]]]],
    settings: Any,
    limit_per_rule: Optional[int] = None,
) -> dict[str, list[dict[str, Any]]]:
    """Expand rrule candidates and return a mapping uid -> list of occurrence summaries.

    limit_per_rule: optional hard cap on the number of occurrences returned per rule
    """
    trace: dict[str, list[dict[str, Any]]] = {}
    # Use expand_events_async which returns flattened list (async)
    # Build events_with_rrules in expected shape: (event, rrule_string, exdates)
    try:
        expanded = await expand_events_async(candidates, settings)
    except Exception:
        logger.exception("Failed to expand events")
        expanded = []

    for inst in expanded:
        try:
            master = getattr(inst, "rrule_master_uid", None) or getattr(inst, "id", "unknown")
            lst = trace.setdefault(str(master), [])
            if limit_per_rule is not None and len(lst) >= limit_per_rule:
                continue
            lst.append(event_summary(inst))
        except Exception:
            # best-effort conversion
            lst = trace.setdefault("unknown", [])
            lst.append({"error": "failed to summarize instance"})
    return trace
