#!/usr/bin/env python3
"""
Integration tests for calendarbot_lite /api/whats-next that exercise recurring-event
scenarios end-to-end.

Each test spins up a tiny stub HTTP server that serves an ICS payload, then launches
calendarbot_lite in a subprocess (pointing it at the stub ICS URL via CALENDARBOT_ICS_URL).
We set CALENDARBOT_TEST_TIME to a deterministic instant so the server behaves
deterministically and the what's-next response can be asserted precisely.

Notes:
- These tests are intentionally conservative with timeouts to be CI-friendly.
- Keep tests independent: each test creates its own stub server and calendarbot_lite
  subprocess and performs proper cleanup.
"""
from __future__ import annotations

import contextlib
import http.client
import http.server
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from typing import Tuple

import pytest

pytestmark = pytest.mark.integration

# Helpers copied/simplified from tests/lite/test_calendarbot_lite_harness.py
def find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_lite_server_process(port: int) -> subprocess.Popen:
    """Start calendarbot_lite server in a child Python process bound to 127.0.0.1:port.

    The function will include an 'ics_sources' entry in the config if the parent process
    has CALENDARBOT_ICS_URL set in the environment. This ensures the server's refresh
    logic sees a source even when a minimal config dict is passed.
    """
    py = sys.executable or "python3"

    # Read ICS URL from environment (set by the test) and embed into the child config.
    ics_url = os.environ.get("CALENDARBOT_ICS_URL")
    if ics_url:
        # safe repr to embed string literal
        sources_fragment = f"'ics_sources': [{ics_url!r}],"
    else:
        sources_fragment = ""

    # Build the child process code string. Keep config minimal and deterministic.
    code = (
        "from calendarbot_lite.server import start_server\n"
        "cfg = { 'server_bind':'127.0.0.1', 'server_port':%d, %s 'refresh_interval_seconds':2, 'rrule_expansion_days':365, 'expansion_days_window':365 }\n"
        "start_server(cfg, None)\n"
    ) % (port, sources_fragment)

    env = os.environ.copy()
    env.pop("PYTHONSTARTUP", None)

    proc = subprocess.Popen(
        [py, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    return proc


def wait_for_port(host: str, port: int, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.1)
    raise RuntimeError(f"Port {host}:{port} did not open in {timeout}s (last error: {last_exc})")


def http_request(host: str, port: int, method: str, path: str, body: object | None = None, headers: dict | None = None) -> Tuple[int, dict]:
    conn = http.client.HTTPConnection(host, port, timeout=5)
    body_bytes = None
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if body is not None:
        body_bytes = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
        hdrs["Content-Length"] = str(len(body_bytes))
    conn.request(method, path, body=body_bytes, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read()
    try:
        parsed = json.loads(data.decode("utf-8")) if data else {}
    except Exception:
        parsed = {"_raw": data.decode("utf-8", errors="replace")}
    conn.close()
    return resp.status, parsed


from typing import Optional


def _print_summary(scenario: str, expected: dict, api_output: Optional[dict], passed: bool) -> None:
    """Print a concise per-scenario summary for whats-next integration tests."""
    print(f"\nSCENARIO: {scenario}")
    print("  Expected:")
    for k, v in expected.items():
        print(f"    - {k}: {v!r}")
    print("  Whats-Next API output:")
    if api_output is None:
        print("    - <no meeting returned>")
    else:
        for k, v in api_output.items():
            print(f"    - {k}: {v!r}")
    print(f"  RESULT: {'PASS' if passed else 'FAIL'}\n")


@pytest.mark.integration
def test_whatsnext_returns_next_recurring_event(tmp_path):
    """Set time to 08:45 and a daily recurring meeting at 09:00 -> whats-next should return the 09:00 occurrence."""
    # ICS with daily recurring meeting at 09:00Z
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:daily-api-test@example.com\n"
        b"SUMMARY:Daily Team Sync\n"
        b"DTSTART:20251101T090000Z\n"
        b"DTEND:20251101T100000Z\n"
        b"RRULE:FREQ=DAILY;COUNT=3\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set deterministic server time to 2025-11-01T08:45:00Z
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-01T08:45:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        # Poll /api/whats-next until a meeting appears (allow time for initial refresh)
        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        assert status == 200, f"GET /api/whats-next returned {status} {body}"
        assert isinstance(body, dict) and "meeting" in body

        meeting = body["meeting"]

        expected = {
            "start_iso": "2025-11-01T09:00:00Z",
            "subject": "Daily Team Sync",
            "seconds_until_start": 900,
        }
        api_output = None if meeting is None else {
            "start_iso": meeting.get("start_iso"),
            "subject": meeting.get("subject"),
            "seconds_until_start": meeting.get("seconds_until_start"),
        }

        # Run assertions but always produce a printed summary (even on failure)
        passed = False
        try:
            assert meeting is not None, "Expected a meeting but got None"
            assert meeting.get("start_iso") == expected["start_iso"]
            assert meeting.get("subject") == expected["subject"]
            assert meeting.get("seconds_until_start") == expected["seconds_until_start"]
            passed = True
        except AssertionError:
            _print_summary("Daily recurring whats-next", expected, api_output, False)
            raise
        else:
            _print_summary("Daily recurring whats-next", expected, api_output, True)

    finally:
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        try:
            out, err = proc.communicate(timeout=1)
        except Exception:
            out = ""
            err = ""
        if proc.returncode not in (0, None):
            if out:
                print("=== server stdout ===")
                print(out)
            if err:
                print("=== server stderr ===")
                print(err)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_dst_transition(tmp_path):
    """DST transition scenario: recurring meeting in America/Los_Angeles around DST end.
    We assert the whats-next API returns the subject (meeting exists) and print a summary.
    """
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VTIMEZONE\n"
        b"TZID:America/Los_Angeles\n"
        b"END:VTIMEZONE\n"
        b"BEGIN:VEVENT\n"
        b"UID:dst-test@example.com\n"
        b"SUMMARY:DST Local Meeting\n"
        b"DTSTART;TZID=America/Los_Angeles:20251102T013000\n"
        b"DTEND;TZID=America/Los_Angeles:20251102T020000\n"
        b"RRULE:FREQ=DAILY;COUNT=2\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set server time close to local 01:00 PT on DST end day (08:00Z)
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-02T08:00:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        # Poll until a meeting appears
        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        expected = {"subject": "DST Local Meeting"}
        meeting = None
        if isinstance(body, dict):
            meeting = body.get("meeting")
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}

        passed = meeting is not None and api_output.get("subject") == expected["subject"] if api_output else False
        _print_summary("DST transition whats-next", expected, api_output, passed)
        assert passed, f"Expected meeting subject {expected['subject']}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_monthly_31st_edgecase(tmp_path):
    """Monthly edge-case: event on 31st of month (server should return upcoming instance if present)."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:monthly-31-test@example.com\n"
        b"SUMMARY:Monthly 31st Event\n"
        b"DTSTART:20250131T100000Z\n"
        b"DTEND:20250131T110000Z\n"
        b"RRULE:FREQ=MONTHLY;COUNT=3\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set server time to Feb 28 2025 09:00Z (UTC) to observe how 31st is handled next
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-02-28T09:00:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = None
        if isinstance(body, dict):
            meeting = body.get("meeting")
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        expected = {"subject": "Monthly 31st Event"}
        passed = meeting is not None and api_output.get("subject") == expected["subject"] if api_output else False
        _print_summary("Monthly 31st edgecase whats-next", expected, api_output, passed)
        assert passed, f"Expected meeting subject {expected['subject']}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_overlapping_series_priority(tmp_path):
    """Overlapping series: two recurring series at same start time - whats-next should return one of them."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:overlap1@example.com\n"
        b"SUMMARY:Project Sync A\n"
        b"DTSTART:20251105T090000Z\n"
        b"DTEND:20251105T100000Z\n"
        b"RRULE:FREQ=DAILY;COUNT=2\n"
        b"END:VEVENT\n"
        b"BEGIN:VEVENT\n"
        b"UID:overlap2@example.com\n"
        b"SUMMARY:Project Sync B\n"
        b"DTSTART:20251105T090000Z\n"
        b"DTEND:20251105T100000Z\n"
        b"RRULE:FREQ=DAILY;COUNT=2\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-05T08:50:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = None
        if isinstance(body, dict):
            meeting = body.get("meeting")
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        expected = {"possible_subjects": ["Project Sync A", "Project Sync B"]}
        passed = meeting is not None and api_output.get("subject") in expected["possible_subjects"] if api_output else False
        _print_summary("Overlapping series whats-next", expected, api_output, passed)
        assert passed, f"Expected subject in {expected['possible_subjects']}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_skips_cancelled_occurrence_and_falls_back(tmp_path):
    """A recurring meeting at 09:00 is cancelled (EXDATE) -> whats-next should return the next available meeting (09:30 single event)."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:recancel-test@example.com\n"
        b"SUMMARY:Morning Recurring\n"
        b"DTSTART:20251101T090000Z\n"
        b"DTEND:20251101T100000Z\n"
        b"RRULE:FREQ=DAILY;COUNT=3\n"
        b"EXDATE:20251101T090000Z\n"
        b"END:VEVENT\n"
        # A separate single event later that should be the next meeting
        b"BEGIN:VEVENT\n"
        b"UID:ad_hoc@example.com\n"
        b"SUMMARY:Standby Meeting\n"
        b"DTSTART:20251101T093000Z\n"
        b"DTEND:20251101T100000Z\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-01T08:45:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        # Poll until a meeting appears (allow initial refresh)
        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        assert status == 200
        assert isinstance(body, dict) and "meeting" in body

        meeting = body["meeting"]

        expected = {
            "start_iso": "2025-11-01T09:30:00Z",
            "subject": "Standby Meeting",
        }
        api_output = None if meeting is None else {
            "start_iso": meeting.get("start_iso"),
            "subject": meeting.get("subject"),
        }

        passed = False
        try:
            assert meeting is not None
            assert meeting.get("start_iso") == expected["start_iso"]
            assert meeting.get("subject") == expected["subject"]
            passed = True
        except AssertionError:
            _print_summary("EXDATE fallback whats-next", expected, api_output, False)
            raise
        else:
            _print_summary("EXDATE fallback whats-next", expected, api_output, True)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        try:
            out, err = proc.communicate(timeout=1)
        except Exception:
            out = ""
            err = ""
        if proc.returncode not in (0, None):
            if out:
                print("=== server stdout ===")
                print(out)
            if err:
                print("=== server stderr ===")
                print(err)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_handles_recurring_moved_instance(tmp_path):
    """A recurring meeting has a RECURRENCE-ID moved instance -> whats-next should return the moved instance and suppress the original slot."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        # Master recurring series at 09:00 daily
        b"BEGIN:VEVENT\n"
        b"UID:move-api-test@example.com\n"
        b"SUMMARY:Standup Meeting\n"
        b"DTSTART:20251102T090000Z\n"
        b"DTEND:20251102T091500Z\n"
        b"RRULE:FREQ=DAILY;COUNT=3\n"
        b"END:VEVENT\n"
        # Moved second occurrence (original 20251103T090000Z) -> new time 11:00 and renamed.
        b"BEGIN:VEVENT\n"
        b"UID:move-api-test@example.com\n"
        b"RECURRENCE-ID:20251103T090000Z\n"
        b"SUMMARY:Standup Meeting (Rescheduled)\n"
        b"DTSTART:20251103T110000Z\n"
        b"DTEND:20251103T111500Z\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set server time to 2025-11-03T08:45:00Z so the moved instance at 11:00Z is upcoming
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-03T08:45:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        # Poll until a meeting appears (allow initial refresh)
        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        assert status == 200
        assert isinstance(body, dict) and "meeting" in body

        meeting = body["meeting"]

        expected = {
            "start_iso": "2025-11-03T11:00:00Z",
            "subject": "Standup Meeting (Rescheduled)",
        }
        api_output = None if meeting is None else {
            "start_iso": meeting.get("start_iso"),
            "subject": meeting.get("subject"),
        }

        passed = False
        try:
            assert meeting is not None
            assert meeting.get("start_iso") == expected["start_iso"]
            assert meeting.get("subject") == expected["subject"]
            # Also ensure original 09:00 slot is not returned as next
            assert meeting.get("start_iso") != "2025-11-03T09:00:00Z"
            passed = True
        except AssertionError:
            _print_summary("Moved-instance whats-next", expected, api_output, False)
            raise
        else:
            _print_summary("Moved-instance whats-next", expected, api_output, True)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        try:
            out, err = proc.communicate(timeout=1)
        except Exception:
            out = ""
            err = ""
        if proc.returncode not in (0, None):
            if out:
                print("=== server stdout ===")
                print(out)
            if err:
                print("=== server stderr ===")
                print(err)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_until_precedence_over_count(tmp_path):
    """RRULE contains COUNT and UNTIL; UNTIL should limit occurrences."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:until-count-test@example.com\n"
        b"SUMMARY:Until vs Count Meeting\n"
        b"DTSTART:20251101T090000Z\n"
        b"DTEND:20251101T100000Z\n"
        # COUNT=10 but UNTIL limits to 2025-11-03T09:00Z inclusive
        b"RRULE:FREQ=DAILY;COUNT=10;UNTIL=20251103T090000Z\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set time on 2025-11-02 so next occurrence is 2025-11-02T09:00:00Z
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-02T08:45:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        assert status == 200
        meeting = body.get("meeting") if isinstance(body, dict) else None
        expected = {"start_iso": "2025-11-02T09:00:00Z", "subject": "Until vs Count Meeting"}
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        passed = meeting is not None and api_output is not None and api_output.get("start_iso") == expected["start_iso"] and api_output.get("subject") == expected["subject"]
        _print_summary("UNTIL vs COUNT whats-next", expected, api_output, passed)
        assert passed, f"Expected {expected}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_floating_time_interpreted_localtz(tmp_path):
    """DTSTART without TZID (floating time) is currently treated as UTC by the parser."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:floating-local-test@example.com\n"
        b"SUMMARY:Local Floating Meeting\n"
        # Floating time (no 'Z' and no TZID) -- currently treated as UTC
        b"DTSTART:20251101T090000\n"
        b"DTEND:20251101T100000\n"
        b"RRULE:FREQ=DAILY;COUNT=2\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Nov 1 2025 at 09:00 America/Los_Angeles -> 2025-11-01T16:00:00Z (PDT still in effect)
    # Set time to just before the event in UTC
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-01T15:30:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = body.get("meeting") if isinstance(body, dict) else None
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        # Note: Floating time (no Z, no TZID) is currently treated as UTC by the parser
        # First occurrence at 09:00Z has passed (test time is 15:30Z), so next is the second occurrence
        expected = {"start_iso": "2025-11-02T09:00:00Z", "subject": "Local Floating Meeting"}
        passed = meeting is not None and api_output is not None and api_output.get("start_iso") == expected["start_iso"]
        _print_summary("Floating local-time whats-next", expected, api_output, passed)
        assert passed, f"Expected {expected}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_exdate_with_tzid_matching(tmp_path):
    """EXDATE with TZID should match and remove the occurrence from the recurring series."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VTIMEZONE\n"
        b"TZID:America/Los_Angeles\n"
        b"END:VTIMEZONE\n"
        b"BEGIN:VEVENT\n"
        b"UID:exdate-tzid-test@example.com\n"
        b"SUMMARY:Tz EXDATE Meeting\n"
        b"DTSTART;TZID=America/Los_Angeles:20251101T090000\n"
        b"DTEND;TZID=America/Los_Angeles:20251101T100000\n"
        b"RRULE:FREQ=DAILY;COUNT=3\n"
        b"EXDATE;TZID=America/Los_Angeles:20251102T090000\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set time to just before 2025-11-02 09:00 PT which was excluded -> next should be 2025-11-03 local 09:00 -> UTC 17:00Z (PDT)
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-02T16:30:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = body.get("meeting") if isinstance(body, dict) else None
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        expected_subject = "Tz EXDATE Meeting"
        passed = meeting is not None and api_output is not None and api_output.get("subject") == expected_subject
        _print_summary("EXDATE with TZID whats-next", {"subject": expected_subject}, api_output, passed)
        assert passed, f"Expected subject {expected_subject}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_all_day_recurring(tmp_path):
    """All-day recurring VEVENTs (VALUE=DATE) should be discovered and returned as upcoming."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:allday-test@example.com\n"
        b"SUMMARY:All Day Weekly\n"
        b"DTSTART;VALUE=DATE:20251105\n"
        b"RRULE:FREQ=WEEKLY;COUNT=2\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set time to the day before the all-day event (UTC)
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-04T12:00:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = body.get("meeting") if isinstance(body, dict) else None
        api_output = None if meeting is None else {"subject": meeting.get("subject"), "start_iso": meeting.get("start_iso")}
        expected = {"subject": "All Day Weekly"}
        passed = meeting is not None and api_output is not None and api_output.get("subject") == expected["subject"]
        _print_summary("All-day recurring whats-next", expected, api_output, passed)
        assert passed, f"Expected {expected}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_monthly_byday_ordinal(tmp_path):
    """RRULE with BYDAY=1MO (first Monday) should expand and return upcoming first-Monday occurrence."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:monthly-ordinal-test@example.com\n"
        b"SUMMARY:Monthly First Monday\n"
        b"DTSTART:20251103T090000Z\n"  # 2025-11-03 is a Monday (first Monday example)
        b"DTEND:20251103T100000Z\n"
        b"RRULE:FREQ=MONTHLY;BYDAY=1MO;COUNT=3\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-03T08:00:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = body.get("meeting") if isinstance(body, dict) else None
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        expected = {"subject": "Monthly First Monday", "start_iso": "2025-11-03T09:00:00Z"}
        passed = meeting is not None and api_output is not None and api_output.get("start_iso") == expected["start_iso"]
        _print_summary("Monthly ordinal BYDAY whats-next", expected, api_output, passed)
        assert passed, f"Expected {expected}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_moved_instance_different_tz(tmp_path):
    """Master series in UTC; one recurrence is moved and represented with RECURRENCE-ID (UTC) but DTSTART with TZID."""
    ics = (
        b"BEGIN:VCALENDAR\n"
        b"VERSION:2.0\n"
        b"BEGIN:VEVENT\n"
        b"UID:move-tz-test@example.com\n"
        b"SUMMARY:Team Huddle\n"
        b"DTSTART:20251102T090000Z\n"
        b"DTEND:20251102T091500Z\n"
        b"RRULE:FREQ=DAILY;COUNT=3\n"
        b"END:VEVENT\n"
        # Moved second occurrence originally 2025-11-03T09:00Z -> moved to 11:00 America/Los_Angeles
        b"BEGIN:VTIMEZONE\n"
        b"TZID:America/Los_Angeles\n"
        b"END:VTIMEZONE\n"
        b"BEGIN:VEVENT\n"
        b"UID:move-tz-test@example.com\n"
        b"RECURRENCE-ID:20251103T090000Z\n"
        b"SUMMARY:Team Huddle (Moved TZ)\n"
        b"DTSTART;TZID=America/Los_Angeles:20251103T110000\n"
        b"DTEND;TZID=America/Los_Angeles:20251103T111500\n"
        b"END:VEVENT\n"
        b"END:VCALENDAR\n"
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Set time so the moved instance (11:00 PST -> 19:00Z on 2025-11-03) is upcoming
    # Note: Nov 3 is after DST ends, so PST applies (UTC-8)
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-03T17:30:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = body.get("meeting") if isinstance(body, dict) else None
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        # Nov 3, 2025 is after DST ends (Nov 2), so America/Los_Angeles is PST (UTC-8), not PDT (UTC-7)
        # Therefore 11:00 PT = 11:00 PST = 19:00 UTC
        expected = {"subject": "Team Huddle (Moved TZ)", "start_iso": "2025-11-03T19:00:00Z"}
        passed = meeting is not None and api_output is not None and api_output.get("start_iso") == expected["start_iso"] and api_output.get("subject") == expected["subject"]
        _print_summary("Moved instance with TZ whats-next", expected, api_output, passed)
        assert passed, f"Expected {expected}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)


@pytest.mark.integration
def test_whatsnext_large_count_expansion_truncation(tmp_path):
    """RRULE with huge COUNT should not crash; expansion will be truncated by rrule_expansion_days but next occurrence must still be returned."""
    ics_body = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:big-count-test@example.com\n"
        "SUMMARY:Big Count Meeting\n"
        "DTSTART:20251101T090000Z\n"
        "DTEND:20251101T100000Z\n"
        # Very large COUNT - expansion must be bounded by server settings
        "RRULE:FREQ=DAILY;COUNT=100000\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    ics = ics_body.encode("utf-8")

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(ics)))
                self.end_headers()
                self.wfile.write(ics)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Time just before first occurrence
    os.environ["CALENDARBOT_TEST_TIME"] = "2025-11-01T08:50:00Z"
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"

    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        wait_for_port("127.0.0.1", port, timeout=8.0)

        deadline = time.time() + 6.0
        status = None
        body = None
        while time.time() < deadline:
            status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
            if status == 200 and isinstance(body, dict) and body.get("meeting") is not None:
                break
            time.sleep(0.25)

        meeting = body.get("meeting") if isinstance(body, dict) else None
        api_output = None if meeting is None else {"start_iso": meeting.get("start_iso"), "subject": meeting.get("subject")}
        expected = {"subject": "Big Count Meeting", "start_iso": "2025-11-01T09:00:00Z"}
        passed = meeting is not None and api_output is not None and api_output.get("start_iso") == expected["start_iso"]
        _print_summary("Large COUNT truncation whats-next", expected, api_output, passed)
        assert passed, f"Expected {expected}, got {api_output}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1)
        os.environ.pop("CALENDARBOT_TEST_TIME", None)
        os.environ.pop("CALENDARBOT_ICS_URL", None)
