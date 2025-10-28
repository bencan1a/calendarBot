"""Lightweight smoke test for calendarbot_lite startup.

Uses in-process aiohttp TestServer if available, otherwise falls back to
a minimal subprocess-based startup. Test is fast (<10s) and asserts no
ERROR logs emitted during server initialization.
"""
# pyright: reportGeneralTypeIssues=false, reportMissingImports=false
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, cast
from contextlib import suppress
import socket
from tests.fixtures.mock_ics_data import ICSDataFactory  # type: ignore

import pytest

aiohttp = pytest.importorskip("aiohttp")

from calendarbot_lite import server as cb_server

# Prefer using the existing lightweight fixture when available
# simple_settings is defined in tests/lite/conftest.py and is imported by name


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_lite_smoke_boot_inprocess_no_errors(caplog: Any) -> None:
    """Start calendarbot_lite in-process with aiohttp TestServer and assert no ERROR.

    This exercise uses the server._make_app factory (if present) to create a
    runnable aiohttp application. It performs a single GET to /api/whats-next
    to verify the app responds and captures logs to ensure no ERROR-level
    messages appeared during startup.
    """
    caplog.set_level(logging.INFO)

    make_app = getattr(cb_server, "_make_app", None)
    if not callable(make_app):
        pytest.skip("_make_app factory not available in calendarbot_lite.server")

    # Serve a local test ICS so the app executes the full fetch+parse path in-process.
    ics_content = ICSDataFactory.create_basic_ics(event_count=2).encode("utf-8")

    class _ICSHandlerForInProcess(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar")
            self.send_header("Content-Length", str(len(ics_content)))
            self.end_headers()
            self.wfile.write(ics_content)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: D401
            return

    httpd_in = HTTPServer(("127.0.0.1", 0), _ICSHandlerForInProcess)
    port_in = httpd_in.server_port
    thread_in = threading.Thread(target=httpd_in.serve_forever, daemon=True)
    thread_in.start()

    # Minimal deterministic config: point to local ICS and short refresh interval
    config: dict[str, Any] = {
        "ics_sources": [f"http://127.0.0.1:{port_in}/calendar.ics"],
        "refresh_interval_seconds": 3600,
    }

    skipped_store = None
    event_window_ref: list[Any] = [[]]
    window_lock = asyncio.Lock()
    stop_event = asyncio.Event()
    shared_http_client = None

    # _make_app may be implemented synchronously (returns an aiohttp.Application)
    # or asynchronously (returns an awaitable). Support both to satisfy static
    # type checkers and runtime variations across environments.
    _maybe_app = make_app(
        config, skipped_store, event_window_ref, window_lock, stop_event, shared_http_client
    )
    if asyncio.iscoroutine(_maybe_app) or asyncio.isfuture(_maybe_app):
        app = await _maybe_app  # type: ignore[assignment]
    else:
        app = _maybe_app

    from aiohttp.test_utils import TestClient, TestServer
 
    # Cast to Any for static checkers so TestServer accepts the value in all
    # environments (the actual object is a valid aiohttp Application at runtime).
    app = cast(Any, app)
    test_server = TestServer(app)
    await test_server.start_server()
    client = TestClient(test_server)
    await client.start_server()
    try:
        resp = await client.get("/api/whats-next")
        assert resp.status == 200
    finally:
        await client.close()
        await test_server.close()
        # Shutdown the in-process ICS server used for fetching/parsing
        try:
            httpd_in.shutdown()
        except Exception:
            pass
        thread_in.join(timeout=1)

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, f"ERROR logs found during startup: {errors}"


@pytest.mark.smoke
def test_lite_smoke_boot_subprocess_no_errors(tmp_path: Path) -> None:
    """Fallback smoke test using a minimal local ICS HTTP server and subprocess.

    This is a fast, minimal subprocess check that avoids external network
    dependencies by serving a tiny ICS from localhost. It captures stderr and
    asserts no ERROR-level messages were emitted during startup.
    """
    # Serve a realistic test ICS so the server executes the full fetch/parse path.
    # Use the project's ICS test factory to produce deterministic ICS content.
    ics_content = ICSDataFactory.create_basic_ics(event_count=3).encode("utf-8")

    class _ICSHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar")
            self.send_header("Content-Length", str(len(ics_content)))
            self.end_headers()
            self.wfile.write(ics_content)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: D401
            # Suppress default logging to keep test output clean
            return

    httpd = HTTPServer(("127.0.0.1", 0), _ICSHandler)
    # Use httpd.server_port for robust port extraction (works for IPv4/IPv6)
    port = httpd.server_port
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    env = os.environ.copy()
    # Ensure deterministic config and avoid repository .env loading surprises
    env.pop("CALENDARBOT_TEST_TIME", None)
    env.pop("CALENDARBOT_REFRESH_INTERVAL", None)
    env.pop("CALENDARBOT_REFRESH_INTERVAL_SECONDS", None)
    env["CALENDARBOT_ICS_URL"] = f"http://127.0.0.1:{port}/calendar.ics"
    # Choose a free ephemeral port for the subprocess server to avoid collisions.
    # We bind a temporary socket to get an available port and immediately close it.
    # This reduces the chance of the server prompting on port conflicts in CI/dev.
    import socket  # local import to avoid top-level dependency
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _sock:
        _sock.bind(("127.0.0.1", 0))
        free_port = _sock.getsockname()[1]
    env["CALENDARBOT_WEB_PORT"] = str(free_port)
    env["CALENDARBOT_SERVER_PORT"] = str(free_port)
 
    proc = subprocess.Popen(
        [sys.executable, "-m", "calendarbot_lite"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )

    try:
        # Wait briefly for startup (should be fast)
        time.sleep(1.5)
        # Collect stderr without blocking indefinitely by using communicate with a timeout.
        # If the subprocess is still running after the short timeout, terminate it
        # gracefully and collect whatever output it produced so far.
        try:
            _, stderr_bytes = proc.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                _, stderr_bytes = proc.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                _, stderr_bytes = proc.communicate(timeout=2.0)
        stderr = (stderr_bytes or b"").decode("utf-8", errors="ignore")
        assert "ERROR" not in stderr, f"ERROR found in stderr: {stderr}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        httpd.shutdown()
        thread.join(timeout=1)
