#!/usr/bin/env python3
"""
Integration test harness for calendarbot_lite.

This test:
- Finds an available port on localhost
- Spawns a background python process that imports calendarbot_lite.server and calls
  start_server(...) with a small config bound to 127.0.0.1 and the chosen port.
- Waits for the server to accept TCP connections.
- Calls:
    GET  /api/whats-next   -> expect 200, {"meeting": None} (no sources configured)
    POST /api/skip          -> expect 501 (skip-store not available)
    DELETE /api/skip        -> expect 501 (skip-store not available)
- Gracefully stops the subprocess and reports failures.

Uses only stdlib modules so it can run in minimal CI environments.
"""

from __future__ import annotations

import contextlib
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import threading
import http.server
import socketserver
from typing import Tuple
import pytest

from tests.fixtures.mock_ics_data import ICSDataFactory

pytestmark = pytest.mark.integration


def find_free_port() -> int:
    """Bind to port 0 to obtain a free ephemeral port."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_lite_server_process(port: int) -> subprocess.Popen:
    """Start a separate Python process that runs calendarbot_lite.server.start_server.

    We call Python with -c to avoid relying on CLI entrypoints that print friendly
    messages and exit when the implementation is missing.

    This enhanced launcher will attempt to include an ICS source if one is configured
    in the environment (CALENDARBOT_ICS_URL) or the repository .env file so the server
    can fetch real events during integration testing.
    """
    py = sys.executable or "python3"

    # Only read ICS URL from the explicit environment to avoid .env auto-discovery
    # which can introduce non-determinism in CI environments.
    ics_url = os.environ.get("CALENDARBOT_ICS_URL")

    # Build the child process code string, embedding the discovered ICS URL if present.
    if ics_url:
        # Use repr so the URL is safely quoted in the generated code.
        sources_fragment = f"'ics_sources': [{ics_url!r}],"
    else:
        sources_fragment = ""

    code = (
        "import sys\n"
        "from calendarbot_lite.server import start_server\n"
        "cfg = { 'server_bind':'127.0.0.1', 'server_port':%d, %s 'refresh_interval_seconds':2 }\n"
        "start_server(cfg, None)\n"
    ) % (port, sources_fragment)

    # Use an isolated environment copy so tests do not accidentally inherit unrelated env vars
    env = os.environ.copy()
    # Ensure Python doesn't run in sitecustomize that could interfere in certain CI setups
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
    """Wait until a TCP connection to (host, port) succeeds or timeout elapses.
 
    Timeout is intentionally conservative (<= 8s) so CI feedback is quick while
    still giving the process time to initialize.
    """
    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            # Use short per-attempt timeout so failures are retried quickly.
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.1)
    raise RuntimeError(
        f"Port {host}:{port} did not open in {timeout}s (last error: {last_exc})"
    )


def http_request(
    host: str,
    port: int,
    method: str,
    path: str,
    body: object | None = None,
    headers: dict | None = None,
) -> Tuple[int, dict]:
    """Make a simple HTTP request and return (status, json-decoded-body).
 
    Connection timeout is kept small to fail fast in CI when the service is not
    responding.
    """
    conn = http.client.HTTPConnection(host, port, timeout=3)
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


@pytest.mark.integration
def test_calendarbot_lite_apis_work_locally(tmp_path):
    """Integration test: launch server and hit its APIs.
 
    Hardened:
    - No .env auto-discovery (only explicit CALENDARBOT_ICS_URL)
    - Uses a local stub HTTP server to serve deterministic ICS content
      from tests/fixtures/mock_ics_data.py
    - Conservative timeouts and robust cleanup of subprocess and server
      resources.
    """
    # Prepare deterministic ICS content and start a local stub server to serve it.
    ics_content = ICSDataFactory.create_basic_ics(event_count=2)
    content_bytes = ics_content.encode("utf-8")
 
    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # type: ignore[override]
            if self.path in ("/", "/calendar.ics"):
                self.send_response(200)
                self.send_header("Content-Type", "text/calendar")
                self.send_header("Content-Length", str(len(content_bytes)))
                self.end_headers()
                self.wfile.write(content_bytes)
            else:
                self.send_response(404)
                self.end_headers()
 
        def log_message(self, format: str, *args: object) -> None:  # silence logs
            return
 
    # Bind to an ephemeral port on localhost
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    # Allow quick reuse in case CI reuses ports rapidly
    httpd.allow_reuse_address = True
    stub_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
 
    # Ensure child process picks up the stub ICS URL; avoid .env discovery.
    os.environ["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{stub_port}/calendar.ics"
    port = find_free_port()
    proc = start_lite_server_process(port)
 
    try:
        # Wait for the server to start accepting connections.
        try:
            wait_for_port("127.0.0.1", port, timeout=8.0)
        except Exception as e:
            # If the process exited early, capture remaining output for diagnostics.
            if proc.poll() is not None:
                try:
                    out, err = proc.communicate(timeout=1)
                except Exception:
                    out = ""
                    err = ""
                raise RuntimeError(
                    f"Server process exited prematurely. stdout:\n{out}\n\nstderr:\n{err}"
                ) from e
            raise
 
        # GET /api/whats-next -> 200 and {"meeting": ...} should contain deterministic data
        status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
        assert status == 200, f"GET /api/whats-next returned status {status}, body={body}"
        assert isinstance(body, dict) and "meeting" in body, (
            f"Unexpected body for whats-next: {body}"
        )
        # When an ICS source is provided the meeting key may be present; at minimum
        # verify that the response is JSON and contains expected shape.
 
        # POST /api/skip -> skip-store not available -> 501
        status, body = http_request(
            "127.0.0.1", port, "POST", "/api/skip", body={"meeting_id": "x"}
        )
        assert status == 501, (
            f"POST /api/skip expected 501 when skip-store missing, got {status} body={body}"
        )
 
        # DELETE /api/skip -> skip-store not available -> 501
        status, body = http_request("127.0.0.1", port, "DELETE", "/api/skip")
        assert status == 501, (
            f"DELETE /api/skip expected 501 when skip-store missing, got {status} body={body}"
        )
 
    finally:
        # First, cleanup the child process.
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        # Drain any remaining output non-blocking-friendly.
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
        # Then shutdown the stub HTTP server and join its thread.
        try:
            httpd.shutdown()
            httpd.server_close()
        finally:
            # thread is daemon; but join briefly for cleanliness.
            thread.join(timeout=1)
