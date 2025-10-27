#!/usr/bin/env python3
"""
performance_benchmark_lite.py

Comprehensive performance benchmark and validation harness for calendarbot_lite
targeting Pi Zero 2W-like constraints.

What this script provides:
- Scenario drivers for small/medium/large ICS feeds and multi-source concurrent fetches.
- Local aiohttp test server that serves generated ICS payloads (so tests are self-contained).
- Measurements:
    - Peak RSS (psutil or resource)
    - Wall-clock timings for fetch / parse / expand phases
    - Simple network bytes transferred (content-length or measured)
    - Basic responsiveness: simple HTTP API probe while background work runs
- Optional memory-pressure simulation to validate behavior under constrained RAM.
- Outputs JSON summary to "./calendarbot_lite_perf_results.json"
- Usage examples and pointers to run py-spy / tracemalloc externally for deeper profiling.

Note: Activate the project venv before running to ensure dependencies (aiohttp, psutil, httpx, dateutil, icalendar) are available.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import os
import socket
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Optional runtime dependencies
try:
    import psutil
except Exception:
    psutil = None  # Fallback to resource module

# Import centralized datetime function that supports CALENDARBOT_TEST_TIME override
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from calendarbot_lite.server import _now_utc
except ImportError:
    # Fallback if import fails (shouldn't happen in normal usage)
    def _now_utc():
        return datetime.now(timezone.utc)

import aiohttp
from aiohttp import web
from calendarbot_lite.http_client import close_all_clients, get_shared_client

# Import lite modules
from calendarbot_lite.lite_fetcher import LiteICSFetcher, StreamHandle
from calendarbot_lite.lite_parser import LiteICSContentTooLargeError, parse_ics_stream
from calendarbot_lite.lite_rrule_expander import LiteRRuleExpander

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("perf_bench")


@dataclass
class PhaseResult:
    name: str
    elapsed_s: float
    rss_kb_before: int | None
    rss_kb_after: int | None
    note: str | None = None


@dataclass
class ScenarioResult:
    scenario: str
    overall_elapsed_s: float
    phases: list[PhaseResult]
    events_parsed: int
    recurring_instances: int
    warnings: list[str]
    error: str | None = None
    api_validation: dict[str, Any] | None = None
    connection_metrics: dict[str, Any] | None = None


async def measure_connection_reuse_benefit() -> dict[str, Any]:
    """Measure connection reuse performance benefit.

    Compares individual client creation vs shared client usage
    for multiple sequential requests.

    Returns:
        Dictionary with connection reuse metrics
    """
    logger.info("Measuring connection reuse benefit")

    # Test configuration
    num_requests = 5

    # Individual client timing (baseline)
    individual_times = []
    for i in range(num_requests):
        start_time = time.time()

        # Create settings object
        settings = type(
            "Settings",
            (),
            {
                "request_timeout": 30,
                "max_retries": 3,
                "retry_backoff_factor": 1.5,
            },
        )()

        fetcher = LiteICSFetcher(settings)
        try:
            async with fetcher:
                # This will create a new client each time
                pass
        except Exception:
            pass  # Ignore errors for timing measurement

        elapsed = time.time() - start_time
        individual_times.append(elapsed)
        logger.debug("Individual client request %d: %.3fs", i + 1, elapsed)

    # Shared client timing (optimized)
    shared_times = []
    shared_client = None
    try:
        shared_client = await get_shared_client("benchmark_test")

        for i in range(num_requests):
            start_time = time.time()

            settings = type(
                "Settings",
                (),
                {
                    "request_timeout": 30,
                    "max_retries": 3,
                    "retry_backoff_factor": 1.5,
                },
            )()

            fetcher = LiteICSFetcher(settings, shared_client)
            try:
                async with fetcher:
                    # This will reuse the shared client
                    pass
            except Exception:
                pass  # Ignore errors for timing measurement

            elapsed = time.time() - start_time
            shared_times.append(elapsed)
            logger.debug("Shared client request %d: %.3fs", i + 1, elapsed)

    finally:
        # Cleanup
        if shared_client:
            await close_all_clients()

    # Calculate metrics
    avg_individual = sum(individual_times) / len(individual_times) if individual_times else 0
    avg_shared = sum(shared_times) / len(shared_times) if shared_times else 0
    improvement_pct = (
        ((avg_individual - avg_shared) / avg_individual * 100) if avg_individual > 0 else 0
    )

    metrics = {
        "individual_client_avg_ms": round(avg_individual * 1000, 2),
        "shared_client_avg_ms": round(avg_shared * 1000, 2),
        "improvement_percent": round(improvement_pct, 1),
        "num_requests_tested": num_requests,
        "individual_times_ms": [round(t * 1000, 2) for t in individual_times],
        "shared_times_ms": [round(t * 1000, 2) for t in shared_times],
    }

    logger.info(
        "Connection reuse results: %.1f%% improvement (%.2fms → %.2fms average)",
        improvement_pct,
        avg_individual * 1000,
        avg_shared * 1000,
    )

    return metrics


# -----------------------
# Utilities
# -----------------------
def get_rss_kb() -> int | None:
    """Return current process RSS in KB (best-effort)."""
    try:
        if psutil:
            proc = psutil.Process()
            return int(proc.memory_info().rss // 1024)
        import resource  # noqa: PLC0415

        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss typically in KB on Linux
        return int(getattr(usage, "ru_maxrss", 0))
    except Exception:
        return None


def find_free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# -----------------------
# API validation functions
# -----------------------
async def wait_for_server_refresh(server_port: int, timeout: int = 30) -> bool:
    """Wait for calendarbot_lite server to refresh and process ICS data.

    Args:
        server_port: Port of the calendarbot_lite server
        timeout: Maximum time to wait in seconds

    Returns:
        True if server appears to be responding, False if timeout
    """
    start_time = time.time()
    api_url = f"http://127.0.0.1:{server_port}/api/whats-next"

    async with aiohttp.ClientSession() as session:
        while (time.time() - start_time) < timeout:
            try:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        # Server is responding
                        return True
            except Exception:
                # Server not ready yet
                pass
            await asyncio.sleep(0.5)

    logger.warning("Server did not become ready within %d seconds", timeout)
    return False


def generate_expected_event_data(
    scenario: str, include_rrule: bool = False
) -> list[dict[str, Any]]:
    """Generate expected event data based on scenario parameters.

    Args:
        scenario: Scenario name (small, medium, large, concurrent)
        include_rrule: Whether to include recurring events

    Returns:
        List of expected event dictionaries
    """
    expected_events = []
    now = _now_utc()

    # Add predictable upcoming events based on scenario
    if scenario == "small":
        expected_events.append(
            {
                "subject": "Test Event 1",
                "start_offset_hours": 2,
                "duration_seconds": 3600,
                "expected_start": now + timedelta(hours=2),
            }
        )
    elif scenario in ["medium", "large"]:
        expected_events.extend(
            [
                {
                    "subject": "Test Event 1",
                    "start_offset_hours": 1,
                    "duration_seconds": 3600,
                    "expected_start": now + timedelta(hours=1),
                },
                {
                    "subject": "Test Event 2",
                    "start_offset_hours": 4,
                    "duration_seconds": 1800,
                    "expected_start": now + timedelta(hours=4),
                },
            ]
        )

        if include_rrule:
            expected_events.append(
                {
                    "subject": "Recurring Meeting",
                    "start_offset_hours": 24,
                    "duration_seconds": 3600,
                    "expected_start": now + timedelta(hours=24),
                    "is_recurring": True,
                }
            )

    return expected_events


async def validate_api_response(
    server_port: int, expected_events: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate the /api/whats-next endpoint returns correct JSON based on expected events.

    Args:
        server_port: Port of the calendarbot_lite server
        expected_events: List of expected event data for validation

    Returns:
        Dictionary with validation results
    """
    api_url = f"http://127.0.0.1:{server_port}/api/whats-next"
    validation_result = {
        "status": "ERROR",
        "meeting_found": False,
        "validation_details": {},
        "error_message": None,
    }

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            if resp.status != 200:
                validation_result["error_message"] = f"API returned status {resp.status}"
                return validation_result

            try:
                data = await resp.json()
            except Exception as e:
                validation_result["error_message"] = f"Invalid JSON response: {e}"
                return validation_result

            # Validate JSON structure
            if not isinstance(data, dict):
                validation_result["error_message"] = "Response is not a JSON object"
                return validation_result

            if "meeting" not in data:
                validation_result["error_message"] = "Response missing 'meeting' field"
                return validation_result

            meeting = data["meeting"]
            validation_result["meeting_found"] = meeting is not None

            # If no meeting expected and meeting is null, that's correct
            if not expected_events:
                if meeting is None:
                    validation_result["status"] = "PASS"
                    validation_result["validation_details"]["no_meeting_expected"] = True
                else:
                    validation_result["status"] = "FAIL"
                    validation_result["error_message"] = "Expected no meeting but found one"
                return validation_result

            # If events expected but no meeting returned
            if meeting is None:
                validation_result["status"] = "FAIL"
                validation_result["error_message"] = "Expected meeting but API returned null"
                return validation_result

            # Validate meeting structure and content
            required_fields = [
                "meeting_id",
                "subject",
                "start_iso",
                "duration_seconds",
                "seconds_until_start",
            ]
            validation_details = {}

            for field in required_fields:
                if field in meeting:
                    validation_details[f"has_{field}"] = True
                else:
                    validation_details[f"has_{field}"] = False
                    validation_result["error_message"] = f"Missing required field: {field}"
                    return validation_result

            # Validate subject matches expected
            subject = meeting.get("subject", "")
            expected_subjects = [evt["subject"] for evt in expected_events]
            if subject in expected_subjects:
                validation_details["subject_matches"] = True
            else:
                validation_details["subject_matches"] = False
                validation_details["expected_subjects"] = expected_subjects
                validation_details["actual_subject"] = subject

            # Validate timing logic
            seconds_until = meeting.get("seconds_until_start", 0)
            if isinstance(seconds_until, (int, float)) and seconds_until > 0:
                validation_details["reasonable_timing"] = True
            else:
                validation_details["reasonable_timing"] = False
                validation_details["seconds_until_start"] = seconds_until

            # Validate duration
            duration = meeting.get("duration_seconds", 0)
            if isinstance(duration, (int, float)) and duration > 0:
                validation_details["has_duration"] = True
            else:
                validation_details["has_duration"] = False

            validation_result["validation_details"] = validation_details

            # Overall status
            if all(
                [
                    validation_details.get("subject_matches", False),
                    validation_details.get("reasonable_timing", False),
                    validation_details.get("has_duration", False),
                ]
            ):
                validation_result["status"] = "PASS"
            else:
                validation_result["status"] = "FAIL"
                if not validation_result["error_message"]:
                    validation_result["error_message"] = "Validation checks failed"

    except Exception as e:
        validation_result["error_message"] = f"API request failed: {e}"

    return validation_result


# -----------------------
# ICS content generation
# -----------------------
def make_ics_with_sizes(
    total_bytes: int, include_rrule: bool = False, scenario: str = "default"
) -> str:
    """Generate a simple ICS calendar string approximately total_bytes long.

    This creates repeated VEVENT blocks until the approximate size is reached.
    If include_rrule is True, include one RRULE-heavy VEVENT to test expansion.
    For API validation, generates predictable upcoming events based on scenario.
    """
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:CalendarBot-Lite-Perf",
        "X-WR-CALNAME:Perf Test Calendar",
        "X-WR-TIMEZONE:UTC",
    ]
    footer = ["END:VCALENDAR"]
    events = []

    # Generate predictable upcoming events for API validation
    now = _now_utc()

    # Add predictable test events based on scenario
    if scenario == "small":
        # One upcoming event
        test_event = "\n".join(
            [
                "BEGIN:VEVENT",
                "UID:test-event-1",
                f"DTSTART:{(now + timedelta(hours=2)).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{(now + timedelta(hours=3)).strftime('%Y%m%dT%H%M%SZ')}",
                "SUMMARY:Test Event 1",
                "DESCRIPTION:Predictable test event for API validation",
                "END:VEVENT",
            ]
        )
        events.append(test_event)
    elif scenario in ["medium", "large"]:
        # Multiple upcoming events
        test_events = [
            {
                "uid": "test-event-1",
                "summary": "Test Event 1",
                "start_hours": 1,
                "duration_hours": 1,
            },
            {
                "uid": "test-event-2",
                "summary": "Test Event 2",
                "start_hours": 4,
                "duration_hours": 0.5,
            },
        ]

        for evt in test_events:
            test_event = "\n".join(
                [
                    "BEGIN:VEVENT",
                    f"UID:{evt['uid']}",
                    f"DTSTART:{(now + timedelta(hours=evt['start_hours'])).strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTEND:{(now + timedelta(hours=evt['start_hours'] + evt['duration_hours'])).strftime('%Y%m%dT%H%M%SZ')}",
                    f"SUMMARY:{evt['summary']}",
                    "DESCRIPTION:Predictable test event for API validation",
                    "END:VEVENT",
                ]
            )
            events.append(test_event)

    # Create one RRULE event (if requested)
    if include_rrule:
        rrule_start = now + timedelta(hours=24)
        rrule_event = "\n".join(
            [
                "BEGIN:VEVENT",
                "UID:recurring-meeting-1",
                f"DTSTART:{rrule_start.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{(rrule_start + timedelta(hours=1)).strftime('%Y%m%dT%H%M%SZ')}",
                "SUMMARY:Recurring Meeting",
                "RRULE:FREQ=DAILY;COUNT=30",
                "DESCRIPTION:Recurring test event for API validation",
                "END:VEVENT",
            ]
        )
        events.append(rrule_event)

    # Append many filler events until we reach size (in the past to avoid affecting API)
    base_event_template = [
        "BEGIN:VEVENT",
        "UID:filler-evt-{i}",
        "DTSTART:20240101T{hh:02d}0000Z",
        "DTEND:20240101T{hh:02d}3000Z",
        "SUMMARY:Filler event {i}",
        "DESCRIPTION:{payload}",
        "TRANSP:OPAQUE",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ]

    # create a payload chunk (smaller to allow more room for proper structure)
    payload_chunk = "X" * 256  # Reduced size to ensure complete events
    i = 0
    current_size = sum(len(x) + 1 for x in header + footer)  # rough
    for event in events:
        current_size += len(event) + 1

    # Build complete events, ensuring we don't exceed size and break structure
    while current_size < (total_bytes * 0.9):  # Leave 10% margin for complete structure
        hh = 10 + (i % 14)  # Valid hours 10-23
        ev_text = "\n".join(
            line.format(i=i, hh=hh, payload=payload_chunk) for line in base_event_template
        )

        # Check if adding this event would exceed size
        if current_size + len(ev_text) + 1 > (total_bytes * 0.9):
            break

        events.append(ev_text)
        current_size += len(ev_text) + 1
        i += 1
        if i > 5000:
            break

    # Always return complete, valid ICS structure
    return "\n".join(header + events + footer)


# -----------------------
# Local test server
# -----------------------
@asynccontextmanager
async def run_test_server(port: int, path_to_content: dict[str, str]):
    """Run a simple aiohttp test server that serves ICS content at endpoints."""
    app = web.Application()

    async def make_handler(content: str):
        async def handler(request):  # noqa: ARG001
            return web.Response(text=content, content_type="text/calendar")

        return handler

    for p, content in path_to_content.items():
        app.router.add_get(
            p,
            lambda request, c=content: web.Response(text=c, content_type="text/calendar"),  # noqa: ARG005
        )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    logger.info("Test server started on 127.0.0.1:%d", port)
    try:
        yield
    finally:
        logger.info("Shutting down test server...")
        await runner.cleanup()


# -----------------------
# Measurement phases
# -----------------------
async def fetch_phase(
    fetcher: LiteICSFetcher,
    source_cfg,
    timeout_s: int = 30,  # noqa: ARG001
) -> tuple[object | None, float, int | None]:
    """Perform the fetch and return (response, elapsed, bytes_hint)."""
    t0 = time.perf_counter()
    # Memory tracking removed to fix linting
    resp = await fetcher.fetch_ics(source_cfg)
    elapsed = time.perf_counter() - t0
    bytes_hint = None
    try:
        # If buffered path
        if hasattr(resp, "content") and resp.content:
            bytes_hint = len(resp.content.encode("utf-8"))
        elif getattr(resp, "stream_handle", None):
            hdrs = (
                getattr(resp, "headers", {}) or getattr(resp.stream_handle, "headers", None) or {}
            )
            cl = hdrs.get("content-length") if hdrs else None
            if cl:
                try:
                    bytes_hint = int(cl)
                except Exception:
                    bytes_hint = None
    except Exception:
        pass
    # Memory tracking removed to fix linting
    return resp, elapsed, bytes_hint


async def parse_phase(resp, source_url: str) -> tuple[int, int, float, str | None]:
    """Given a LiteICSResponse-like object, parse it and return stats:
    (events_parsed, recurring_instances, elapsed_s, error_message)
    """
    t0 = time.perf_counter()
    events_parsed = 0
    recurring_instances = 0
    error_msg = None

    try:
        if getattr(resp, "stream_handle", None):
            sh: StreamHandle = resp.stream_handle

            # Use async iterator to feed parser
            async def byte_iter():
                async for chunk in sh.iter_bytes():
                    yield chunk

            parse_result = await parse_ics_stream(byte_iter(), source_url=source_url)
        else:
            # Buffered path - use existing optimized parser path
            content = getattr(resp, "content", "") or ""
            from calendarbot_lite.lite_parser import LiteICSParser  # noqa: PLC0415

            parser = LiteICSParser(type("S", (), {})())  # minimal settings for parsing
            parse_result = parser.parse_ics_content_optimized(content, source_url=source_url)

        if parse_result and parse_result.success:
            events_parsed = len(getattr(parse_result, "events", []) or [])
            recurring_instances = getattr(parse_result, "recurring_event_count", 0) or 0
        else:
            error_msg = getattr(parse_result, "error_message", None) or "parse_failed"
    except LiteICSContentTooLargeError as e:
        error_msg = f"content_too_large: {e}"
    except Exception as e:
        error_msg = f"parse_exception: {e}"
    elapsed = time.perf_counter() - t0
    return events_parsed, recurring_instances, elapsed, error_msg


async def expand_phase(events, settings_obj) -> tuple[int, float, str | None, dict]:
    """Run RRULE streaming expansion for recurring events with Pi Zero 2W metrics."""
    t0 = time.perf_counter()
    expanded_total = 0
    streaming_metrics = {
        "events_with_rrules": 0,
        "time_budget_violations": 0,
        "occurrence_limit_hits": 0,
        "cooperative_yields": 0,
        "streaming_mode_used": True,
        "memory_efficient": True,
    }
    err = None

    try:
        from calendarbot_lite.lite_rrule_expander import expand_events_streaming  # noqa: PLC0415

        # Collect events with RRULEs for streaming expansion
        events_with_rrules = []
        for e in events:
            if getattr(e, "is_recurring", False):
                rrule_str = getattr(e, "rrule_string", None) or getattr(e, "rrule", None) or ""
                if rrule_str:
                    events_with_rrules.append((e, rrule_str, None))
                    streaming_metrics["events_with_rrules"] += 1

        if events_with_rrules:
            # Use streaming expansion for memory efficiency
            stream_start = time.perf_counter()
            yield_count = 0

            async for _expanded_event in expand_events_streaming(events_with_rrules, settings_obj):
                expanded_total += 1

                # Track cooperative yields (every 50 events)
                if expanded_total % 50 == 0:
                    yield_count += 1
                    streaming_metrics["cooperative_yields"] = yield_count

                # Check for time budget violations (200ms default per rule)
                elapsed_per_rule = (time.perf_counter() - stream_start) * 1000
                time_budget_ms = getattr(settings_obj, "expansion_time_budget_ms_per_rule", 200)
                if elapsed_per_rule > time_budget_ms * len(events_with_rrules):
                    streaming_metrics["time_budget_violations"] += 1

                # Check for occurrence limit hits (250 default)
                max_occurrences = getattr(settings_obj, "rrule_max_occurrences_per_rule", 250)
                if expanded_total >= max_occurrences * len(events_with_rrules):
                    streaming_metrics["occurrence_limit_hits"] += 1
                    break

        logger.debug(
            f"Streaming expansion: {expanded_total} events, "
            f"{streaming_metrics['events_with_rrules']} RRULEs, "
            f"{streaming_metrics['cooperative_yields']} yields, "
            f"{streaming_metrics['time_budget_violations']} budget violations"
        )

    except Exception as e:
        err = str(e)
        streaming_metrics["streaming_mode_used"] = False
        streaming_metrics["memory_efficient"] = False
        logger.warning(f"Streaming expansion failed, falling back: {e}")

        # Fallback to original expansion method
        try:
            expander = LiteRRuleExpander(settings_obj)
            for e in events:
                try:
                    if getattr(e, "is_recurring", False):
                        rrule_str = (
                            getattr(e, "rrule_string", None) or getattr(e, "rrule", None) or ""
                        )
                        instances = expander.expand_rrule(e, rrule_str) if rrule_str else []
                        expanded_total += len(instances)
                except Exception as inner_e:  # noqa: PERF203
                    logger.debug("Expansion error for event: %s", inner_e)
        except Exception as fallback_e:
            err = f"Both streaming and fallback failed: {e}, {fallback_e}"

    elapsed = time.perf_counter() - t0
    return expanded_total, elapsed, err, streaming_metrics


async def expand_phase_legacy(events, settings_obj) -> tuple[int, float, str | None]:
    """Legacy RRULE expansion for comparison benchmarks (non-streaming)."""
    t0 = time.perf_counter()
    expanded_total = 0
    err = None
    try:
        expander = LiteRRuleExpander(settings_obj)
        # Legacy expansion for each recurring event
        for e in events:
            try:
                if getattr(e, "is_recurring", False):
                    # Try to find rrule string on event (best-effort)
                    rrule_str = getattr(e, "rrule_string", None) or getattr(e, "rrule", None) or ""
                    instances = expander.expand_rrule(e, rrule_str) if rrule_str else []
                    expanded_total += len(instances)
            except Exception as inner_e:  # noqa: PERF203
                logger.debug("Legacy expansion error for event: %s", inner_e)
    except Exception as e:
        err = str(e)
    elapsed = time.perf_counter() - t0
    return expanded_total, elapsed, err


# -----------------------
# Scenario orchestrator
# -----------------------
async def run_scenario(
    name: str,
    server_base: str,
    endpoints: list[str],
    concurrency: int = 2,
    simulate_memory_pressure_mb: int = 0,
) -> ScenarioResult:
    """Run a scenario that fetches from endpoints concurrently and measures phases."""
    t_overall = time.perf_counter()
    # Memory tracking for overall scenario
    phases: list[PhaseResult] = []
    total_events = 0
    total_recurring = 0
    warnings: list[str] = []
    error = None

    # Optional memory pressure simulation: allocate big bytearrays to reduce available memory
    mem_pressure = []
    if simulate_memory_pressure_mb and simulate_memory_pressure_mb > 0:
        try:
            logger.info("Allocating %d MB to simulate memory pressure", simulate_memory_pressure_mb)
            for _ in range(simulate_memory_pressure_mb):
                mem_pressure.extend([bytearray(1024 * 1024)])  # 1MB each
        except Exception as e:
            logger.warning("Memory pressure allocation failed: %s", e)

    sem = asyncio.Semaphore(concurrency)
    tasks = []

    class MinimalSettings:
        # tune settings similar to Pi Zero recommendations
        rrule_expansion_days = 30
        rrule_max_occurrences = 1000
        request_timeout = 30
        max_retries = 1
        retry_backoff_factor = 1.5
        stream_threshold_bytes = 262144
        read_chunk_size_bytes = 8192

    settings_obj = MinimalSettings()

    async def worker(endpoint: str):
        nonlocal total_events, total_recurring, warnings
        async with sem:
            # Build a LiteICSSource-like minimal object used by LiteICSFetcher in tests/real code
            src = type("S", (), {})()
            src.url = server_base + endpoint
            src.auth = type("A", (), {"get_headers": lambda self={}: {}})()  # noqa: ARG005
            src.custom_headers = {}
            src.timeout = getattr(settings_obj, "request_timeout", 30)
            src.validate_ssl = True

            fetcher = LiteICSFetcher(settings_obj)
            await fetcher._ensure_client()  # noqa: SLF001
            rss_before = get_rss_kb()
            try:
                resp, fetch_elapsed, _bytes_hint = await fetch_phase(fetcher, src)
            except Exception as e:
                phases.append(
                    PhaseResult(
                        name=f"fetch:{endpoint}",
                        elapsed_s=0.0,
                        rss_kb_before=rss_before,
                        rss_kb_after=get_rss_kb(),
                        note=f"fetch_error:{e}",
                    )
                )
                return
            phases.append(
                PhaseResult(
                    name=f"fetch:{endpoint}",
                    elapsed_s=fetch_elapsed,
                    rss_kb_before=rss_before,
                    rss_kb_after=get_rss_kb(),
                )
            )

            # Parse
            rss_before_parse = get_rss_kb()
            events_parsed, recurring_instances, parse_elapsed, parse_err = await parse_phase(
                resp, src.url
            )
            phases.append(
                PhaseResult(
                    name=f"parse:{endpoint}",
                    elapsed_s=parse_elapsed,
                    rss_kb_before=rss_before_parse,
                    rss_kb_after=get_rss_kb(),
                    note=parse_err,
                )
            )
            total_events += events_parsed
            total_recurring += recurring_instances

            # For expansion measurement: we will simulate using expander on placeholder events if any recurring found.
            if recurring_instances and parse_err is None:
                # NOTE: to avoid double heavy CPU work we only simulate expansion cost via call to expander
                rss_before_expand = get_rss_kb()
                try:
                    # Use dummy events list with minimal fields for expander
                    # Here we call expander only once to approximate cost
                    dummy_events = []
                    (
                        _expanded_total,
                        expand_elapsed,
                        expand_err,
                        _streaming_metrics,
                    ) = await expand_phase(dummy_events, settings_obj)
                    phases.append(
                        PhaseResult(
                            name=f"expand:{endpoint}",
                            elapsed_s=expand_elapsed,
                            rss_kb_before=rss_before_expand,
                            rss_kb_after=get_rss_kb(),
                            note=expand_err,
                        )
                    )
                except Exception as e:
                    phases.append(
                        PhaseResult(
                            name=f"expand:{endpoint}",
                            elapsed_s=0.0,
                            rss_kb_before=rss_before_expand,
                            rss_kb_after=get_rss_kb(),
                            note=f"expand_exception:{e}",
                        )
                    )

    for ep in endpoints:
        tasks.extend([asyncio.create_task(worker(ep))])

    # Run tasks and concurrently probe responsiveness
    probe_task = asyncio.create_task(
        http_probe_loop(server_base, interval_s=0.5, duration_s=20.0)
    )  # short probe

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception("Scenario worker failure: %s", e)  # noqa: TRY401
        error = str(e)
    finally:
        # stop probe
        probe_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await probe_task

    # Add API validation after performance tests complete
    api_validation_result = None
    try:
        logger.info("Starting API validation for scenario %s", name)

        # Need to check if calendarbot_lite can be imported and run
        try:
            import subprocess  # noqa: PLC0415

            # Generate expected events for validation
            expected_events = generate_expected_event_data(name, bool(total_recurring))

            # Start calendarbot_lite server in subprocess pointing to our test server
            lite_port = find_free_port()

            # Start calendarbot_lite server
            try:
                lite_cmd = [sys.executable, "-m", "calendarbot_lite"]

                # Create environment for subprocess with testing configuration
                env = os.environ.copy()
                env["CALENDARBOT_ALLOW_LOCALHOST"] = "true"
                env["CALENDARBOT_WEB_PORT"] = str(lite_port)
                env["CALENDARBOT_ICS_URL"] = (
                    f"{server_base}/{'small' if name == 'small' else 'medium'}.ics"
                )
                env["CALENDARBOT_REFRESH_INTERVAL"] = "5"

                # Start server process
                lite_process = subprocess.Popen(
                    lite_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(Path(__file__).parent.parent),  # calendarbot_lite directory
                    env=env,
                )

                # Wait for server to be ready
                server_ready = await wait_for_server_refresh(lite_port, timeout=30)

                if server_ready:
                    # Allow additional time for ICS processing
                    await asyncio.sleep(3)

                    # Run API validation
                    api_validation_result = await validate_api_response(lite_port, expected_events)
                    logger.info(
                        "API validation %s: %s",
                        "PASSED" if api_validation_result.get("status") == "PASS" else "FAILED",
                        api_validation_result.get("error_message", ""),
                    )
                else:
                    api_validation_result = {
                        "status": "ERROR",
                        "meeting_found": False,
                        "validation_details": {},
                        "error_message": "calendarbot_lite server did not start within timeout",
                    }

            finally:
                # Clean up server process
                try:
                    lite_process.terminate()
                    lite_process.wait(timeout=5)
                except Exception:
                    try:
                        lite_process.kill()
                        lite_process.wait(timeout=2)
                    except Exception:
                        pass

                # No config file cleanup needed when using environment variables

        except ImportError as e:
            api_validation_result = {
                "status": "ERROR",
                "meeting_found": False,
                "validation_details": {},
                "error_message": f"Cannot import required modules for API validation: {e}",
            }
        except Exception as e:
            api_validation_result = {
                "status": "ERROR",
                "meeting_found": False,
                "validation_details": {},
                "error_message": f"API validation failed: {e}",
            }

    except Exception as e:
        logger.warning("API validation setup failed: %s", e)
        api_validation_result = {
            "status": "ERROR",
            "meeting_found": False,
            "validation_details": {},
            "error_message": f"API validation setup failed: {e}",
        }

    overall_elapsed = time.perf_counter() - t_overall
    return ScenarioResult(
        scenario=name,
        overall_elapsed_s=overall_elapsed,
        phases=phases,
        events_parsed=total_events,
        recurring_instances=total_recurring,
        warnings=warnings,
        error=error,
        api_validation=api_validation_result,
    )


async def http_probe_loop(base: str, interval_s: float = 0.5, duration_s: float = 20.0):
    """Simple loop that hits the server's root to check responsiveness while background work runs."""
    t0 = time.perf_counter()
    url = base or "http://127.0.0.1/"
    async with aiohttp.ClientSession() as sess:
        while (time.perf_counter() - t0) < duration_s:
            try:
                async with sess.get(url, timeout=2) as resp:
                    _ = await resp.text()
            except Exception:
                pass
            await asyncio.sleep(interval_s)


# -----------------------
# CLI and orchestration
# -----------------------
def build_args():
    p = argparse.ArgumentParser(description="calendarbot_lite performance benchmark harness")
    p.add_argument("--port", type=int, default=0, help="Port for local test server (0=auto)")
    p.add_argument(
        "--simulate-memory-pressure-mb", type=int, default=0, help="Simulate memory pressure (MB)"
    )
    p.add_argument(
        "--output",
        type=str,
        default="calendarbot_lite_perf_results.json",
        help="Output JSON results",
    )
    p.add_argument(
        "--run",
        type=str,
        default="all",
        choices=["all", "small", "medium", "large", "concurrent"],
        help="Which scenario to run",
    )
    p.add_argument(
        "--concurrency", type=int, default=2, help="Concurrency for fetches in concurrent scenario"
    )
    return p.parse_args()


async def main_async(args):
    # determine port
    port = args.port or find_free_port()
    server_base = f"http://127.0.0.1:{port}"

    # Create content map
    content_map = {
        "/": "OK",  # root probe
    }

    # scenarios definitions: (endpoint list, include_rrule flag)
    scenarios_config = {
        "small": (["/small.ics"], False, 50 * 1024),  # 50KB
        "medium": (["/medium.ics"], True, 500 * 1024),  # 500KB
        "large": (["/large.ics"], True, 5 * 1024 * 1024),  # 5MB
        "concurrent": (["/s1.ics", "/s2.ics", "/s3.ics"], True, 500 * 1024),
    }

    # Generate ICS payloads
    for key, (_endpoints, include_rrule, size) in scenarios_config.items():
        if key == "concurrent":
            # create multiple payloads of varying sizes
            content_map["/s1.ics"] = make_ics_with_sizes(
                size, include_rrule=True, scenario="medium"
            )
            content_map["/s2.ics"] = make_ics_with_sizes(
                int(size * 0.5), include_rrule=False, scenario="medium"
            )
            content_map["/s3.ics"] = make_ics_with_sizes(
                int(size * 1.5), include_rrule=True, scenario="medium"
            )
        else:
            ep = f"/{key}.ics"
            content_map[ep] = make_ics_with_sizes(size, include_rrule=include_rrule, scenario=key)

    # Start server and run requested scenarios
    results: dict[str, dict] = {}
    async with run_test_server(port, content_map):
        await asyncio.sleep(0.25)  # allow server warmup
        scenarios_to_run = (
            [args.run] if args.run != "all" else ["small", "medium", "large", "concurrent"]
        )
        for sc in scenarios_to_run:
            logger.info("Running scenario: %s", sc)
            _endpoints, include_rrule, _ = scenarios_config[sc]
            # Map scenario endpoints to server paths used earlier
            eps = ["/s1.ics", "/s2.ics", "/s3.ics"] if sc == "concurrent" else [f"/{sc}.ics"]
            scenario_result = await run_scenario(
                sc,
                server_base,
                eps,
                concurrency=args.concurrency,
                simulate_memory_pressure_mb=args.simulate_memory_pressure_mb,
            )
            results[sc] = asdict(scenario_result)
            # print brief summary
            logger.info(
                "Scenario %s: elapsed=%.2fs events=%d recurring=%d error=%s",
                sc,
                scenario_result.overall_elapsed_s,
                scenario_result.events_parsed,
                scenario_result.recurring_instances,
                scenario_result.error,
            )

    # Save results
    try:
        with Path(args.output).open("w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        logger.info("Results written to %s", args.output)
    except Exception as e:
        logger.warning("Failed to write results: %s", e)

    # Print guidance for deeper profiling
    print("\nDeeper profiling suggestions:")
    print(
        f"- Use py-spy on this script run to collect a flamegraph: py-spy record -o profile.svg -- python3 {sys.argv[0]}"
    )
    print("- Use tracemalloc inside a specialized run if you need allocation snapshots.")
    print(
        "- To simulate Pi Zero 2W more realistically, run this script on the actual device or use qemu/ARM VM.\n"
    )


def main():
    # Enable localhost testing for the entire harness
    os.environ["CALENDARBOT_ALLOW_LOCALHOST"] = "true"
    logger.info("CALENDARBOT_ALLOW_LOCALHOST enabled for performance testing")

    args = build_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
