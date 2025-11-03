#!/usr/bin/env python3
"""
CI Performance Benchmark Runner for CalendarBot GitHub Actions workflows.

Lightweight performance benchmark harness for calendarbot_lite that uses aiohttp 
to serve generated ICS payloads, fetches them with aiohttp client, and feeds the 
bytes into calendarbot_lite.lite_streaming_parser.parse_ics_stream for parsing/measurement.

Features:
- Scenarios: small, medium, large, concurrent, fifty (configurable event counts)
- Measures: fetch elapsed, parse elapsed, and RSS (psutil) before/after parse
- Outputs JSON results to the specified file

Usage:
  . venv/bin/activate && python tests/ci_performance_benchmark.py --run fifty --output calendarbot_lite_perf_results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp
from aiohttp import web

# Try optional psutil for RSS measurement
try:
    import psutil
except Exception:
    psutil = None

# Import parser from calendarbot_lite
try:
    from calendarbot_lite.lite_streaming_parser import parse_ics_stream
except Exception as e:
    raise RuntimeError("Failed to import parse_ics_stream from calendarbot_lite.lite_streaming_parser") from e

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ci_perf_benchmark")


@dataclass
class PhaseResult:
    name: str
    elapsed_s: float
    rss_kb_before: Optional[int]
    rss_kb_after: Optional[int]
    note: Optional[str] = None


@dataclass
class ScenarioResult:
    scenario: str
    overall_elapsed_s: float
    phases: list[PhaseResult]
    events_parsed: int
    recurring_instances: int
    warnings: list[str]
    error: Optional[str] = None


def get_rss_kb() -> Optional[int]:
    if psutil is None:
        return None
    try:
        p = psutil.Process()
        return int(p.memory_info().rss // 1024)
    except Exception:
        return None


def make_ics_with_n_events(n: int, start_dt: datetime) -> str:
    """Generate a simple ICS feed with n VEVENT entries starting at start_dt."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//calendarbot//ci-perf//EN",
    ]
    for i in range(n):
        s = start_dt + timedelta(minutes=30 * i)
        e = s + timedelta(minutes=25)
        uid = f"evt-{i}@example.local"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{s.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{e.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:CI Test Event {i}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


from contextlib import asynccontextmanager


@asynccontextmanager
async def run_test_server(port: int, path_to_content: dict[str, str]):
    app = web.Application()

    for p, content in path_to_content.items():
        async def handler(_request, c=content):  # capture, request unused but required by aiohttp
            return web.Response(text=c, content_type="text/calendar")
        app.router.add_get(p, handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    logger.info("CI test server started on 127.0.0.1:%d", port)
    try:
        yield
    finally:
        logger.info("Shutting down CI test server...")
        await runner.cleanup()


async def byte_iter_from_text(text: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
    b = text.encode("utf-8")
    for i in range(0, len(b), chunk_size):
        yield b[i : i + chunk_size]


async def fetch_and_parse(url: str, session: aiohttp.ClientSession) -> dict[str, Any]:
    result: dict[str, Any] = {"url": url, "fetch_elapsed": 0.0, "parse_elapsed": 0.0, "events": 0}
    t0 = time.perf_counter()
    timeout_obj = aiohttp.ClientTimeout(total=30)
    async with session.get(url, timeout=timeout_obj) as resp:
        content = await resp.text()
    fetch_elapsed = time.perf_counter() - t0
    result["fetch_elapsed"] = fetch_elapsed

    rss_before = get_rss_kb()
    t1 = time.perf_counter()
    # parse_ics_stream expects an async iterator of bytes
    async def ai():
        async for chunk in byte_iter_from_text(content, 16384):
            yield chunk

    parse_result = await parse_ics_stream(ai())
    parse_elapsed = time.perf_counter() - t1
    rss_after = get_rss_kb()

    result["parse_elapsed"] = parse_elapsed
    result["rss_before_kb"] = rss_before
    result["rss_after_kb"] = rss_after
    if parse_result and getattr(parse_result, "success", False):
        events = len(getattr(parse_result, "events", []) or [])
        recurring = getattr(parse_result, "recurring_event_count", 0) or 0
        result["events"] = events
        result["recurring_instances"] = recurring
    else:
        result["error"] = getattr(parse_result, "error_message", "parse_failed")
    return result


async def run_scenario(scenario: str, server_base: str, endpoints: list[str]) -> ScenarioResult:
    phases: list[PhaseResult] = []
    total_events = 0
    total_recurring = 0
    warnings: list[str] = []
    error = None
    t0 = time.perf_counter()
    async with aiohttp.ClientSession() as sess:
        for ep in endpoints:
            url = f"{server_base}{ep}"
            try:
                phase_name = f"fetch_and_parse:{ep}"
                rss_before = get_rss_kb()
                start = time.perf_counter()
                detail = await fetch_and_parse(url, sess)
                elapsed = time.perf_counter() - start
                rss_after = get_rss_kb()
                phases.append(PhaseResult(phase_name, elapsed, rss_before, rss_after, detail.get("error")))
                if "error" in detail:
                    warnings.append(f"{ep}: {detail['error']}")
                total_events += int(detail.get("events", 0))
                total_recurring += int(detail.get("recurring_instances", 0))
            except Exception as e:
                logger.exception("Error in CI scenario endpoint %s", ep)
                warnings.append(f"{ep}: exception {e}")
    overall_elapsed = time.perf_counter() - t0
    return ScenarioResult(
        scenario=scenario,
        overall_elapsed_s=overall_elapsed,
        phases=phases,
        events_parsed=total_events,
        recurring_instances=total_recurring,
        warnings=warnings,
        error=error,
    )


def build_args():
    p = argparse.ArgumentParser(description="CalendarBot CI Performance Benchmark")
    p.add_argument("--port", type=int, default=0)
    # Added "fifty" option to run a dedicated 50-event scenario
    p.add_argument(
        "--run",
        type=str,
        default="all",
        choices=["all", "small", "medium", "large", "concurrent", "fifty"],
    )
    p.add_argument("--output", type=str, default="calendarbot_lite_perf_results.json")
    return p.parse_args()


def generate_content_map():
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # Define event counts roughly matching small/medium/large intent
    cm = {}
    cm["/small.ics"] = make_ics_with_n_events(10, now)
    cm["/medium.ics"] = make_ics_with_n_events(200, now)
    cm["/large.ics"] = make_ics_with_n_events(1200, now)
    # dedicated 50-event scenario for CI acceptance testing
    cm["/fifty.ics"] = make_ics_with_n_events(50, now)
    # concurrent endpoints
    cm["/s1.ics"] = make_ics_with_n_events(200, now)
    cm["/s2.ics"] = make_ics_with_n_events(100, now)
    cm["/s3.ics"] = make_ics_with_n_events(300, now)
    cm["/"] = "OK"
    return cm


async def main_async(args):
    port = args.port or 0
    # find free port
    import socket

    if port == 0:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

    server_base = f"http://127.0.0.1:{port}"
    content_map = generate_content_map()

    results: dict[str, Any] = {}
    # run server
    # Use the asynccontextmanager run_test_server directly
    async with run_test_server(port, content_map):
        await asyncio.sleep(0.25)  # warmup
        scenarios = ["small", "medium", "large", "concurrent"] if args.run == "all" else [args.run]
        for sc in scenarios:
            logger.info("Running CI scenario: %s", sc)
            eps = ["/s1.ics", "/s2.ics", "/s3.ics"] if sc == "concurrent" else [f"/{sc}.ics"]
            res = await run_scenario(sc, server_base, eps)
            results[sc] = asdict(res)
            logger.info(
                "CI Scenario %s: elapsed=%.2fs events=%d recurring=%d warnings=%d",
                sc,
                res.overall_elapsed_s,
                res.events_parsed,
                res.recurring_instances,
                len(res.warnings),
            )

    # Write output
    try:
        with Path(args.output).open("w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        logger.info("CI performance results written to %s", args.output)
    except Exception as e:
        logger.warning("Failed to write CI performance results: %s", e)


def main():
    args = build_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("CI Performance benchmark interrupted")


if __name__ == "__main__":
    main()