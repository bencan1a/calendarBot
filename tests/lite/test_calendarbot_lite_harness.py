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
from typing import Tuple

import pytest


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

    # Try to discover ICS URL from the current environment first, then fall back to .env
    ics_url = os.environ.get("CALENDARBOT_ICS_URL")
    if not ics_url:
        from pathlib import Path as _Path

        env_path = _Path.cwd() / ".env"
        if env_path.exists():
            for ln in env_path.read_text().splitlines():
                ln_stripped = ln.strip()
                if ln_stripped.startswith("CALENDARBOT_ICS_URL="):
                    ics_url = ln_stripped.split("=", 1)[1].strip()
                    # strip surrounding quotes if present
                    if ics_url and (
                        (ics_url[0] == '"' and ics_url[-1] == '"')
                        or (ics_url[0] == "'" and ics_url[-1] == "'")
                    ):
                        ics_url = ics_url[1:-1]
                    break

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


def wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    """Wait until a TCP connection to (host, port) succeeds or timeout elapses."""
    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.1)
    raise RuntimeError(f"Port {host}:{port} did not open in {timeout}s (last error: {last_exc})")


def http_request(
    host: str,
    port: int,
    method: str,
    path: str,
    body: object | None = None,
    headers: dict | None = None,
) -> Tuple[int, dict]:
    """Make a simple HTTP request and return (status, json-decoded-body)."""
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


@pytest.mark.integration
def test_calendarbot_lite_apis_work_locally():
    """Integration test: launch server and hit its APIs.

    This test intentionally keeps expectations conservative:
    - When no ICS sources and no skip-store are configured, the server should
      return meeting: None for whats-next and 501 for skip endpoints.
    """
    port = find_free_port()
    proc = start_lite_server_process(port)

    try:
        # Wait for the server to start accepting connections.
        try:
            wait_for_port("127.0.0.1", port, timeout=10.0)
        except Exception as e:
            # If the process exited early, capture stderr for diagnostics.
            if proc.poll() is not None:
                stderr = (proc.stderr.read() or "").strip()
                stdout = (proc.stdout.read() or "").strip()
                raise RuntimeError(
                    f"Server process exited prematurely. stdout:\n{stdout}\n\nstderr:\n{stderr}"
                ) from e
            raise

        # GET /api/whats-next -> 200 and {"meeting": None}
        status, body = http_request("127.0.0.1", port, "GET", "/api/whats-next")
        assert status == 200, f"GET /api/whats-next returned status {status}, body={body}"
        assert isinstance(body, dict) and "meeting" in body, (
            f"Unexpected body for whats-next: {body}"
        )
        # With no sources configured, expect null meeting
        assert body["meeting"] is None, f"Expected meeting None but got: {body['meeting']}"

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
        # Attempt graceful shutdown by sending SIGTERM
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

        # For visibility in CI logs, surface a truncated stderr/stdout if the test fails.
        if proc.returncode not in (0, None):
            stderr = (proc.stderr.read() or "").strip()
            stdout = (proc.stdout.read() or "").strip()
            # Attach to assertion so test frameworks surface logs.
            if stderr or stdout:
                print("=== server stdout ===")
                print(stdout)
                print("=== server stderr ===")
                print(stderr)
