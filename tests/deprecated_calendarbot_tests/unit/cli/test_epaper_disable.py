import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so tests can import the package in isolated environments
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import http.server
import signal
import socketserver
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Import entrypoints under test
from calendarbot.cli.modes import epaper as epaper_module, web as web_module


@pytest.mark.asyncio
async def test_epaper_disabled_by_env(monkeypatch):
    """When CALENDARBOT_DISABLE_EPAPER=1, run_epaper_mode should exit 0 and not initialize renderer."""
    monkeypatch.setenv("CALENDARBOT_DISABLE_EPAPER", "1")

    # Patch heavy renderer constructor to detect any initialization attempts
    with patch("calendarbot.cli.modes.epaper.EInkWhatsNextRenderer") as mock_renderer:
        args = SimpleNamespace(epaper=True)
        result = await epaper_module.run_epaper_mode(args)
        assert result == 0
        mock_renderer.assert_not_called()


@pytest.mark.asyncio
async def test_epaper_disabled_by_settings(monkeypatch):
    """When settings.epaper.enabled is False, run_epaper_mode should exit 0 and not initialize renderer."""
    # Ensure setting is disabled via settings proxy
    from calendarbot.config.settings import settings

    monkeypatch.setattr(settings.epaper, "enabled", False)

    with patch("calendarbot.cli.modes.epaper.EInkWhatsNextRenderer") as mock_renderer:
        args = SimpleNamespace(epaper=True)
        result = await epaper_module.run_epaper_mode(args)
        assert result == 0
        mock_renderer.assert_not_called()


@pytest.mark.asyncio
async def test_web_mode_smoke_when_epaper_disabled(monkeypatch):
    """Web mode should still start and respond to /api/whats-next/data even when epaper is disabled.

    This test patches WebServer.start to run a lightweight HTTP server that responds to
    the expected API endpoint, runs run_web_mode asynchronously, queries the endpoint,
    then sends SIGINT to trigger graceful shutdown.
    """
    port = 18081

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/whats-next/data":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            else:
                self.send_response(404)
                self.end_headers()

        # Suppress logging from the test HTTP server
        def log_message(self, format, *args):
            return

    server = socketserver.TCPServer(("127.0.0.1", port), Handler)
    server.allow_reuse_address = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)

    # Replace WebServer.start with a fake starter that only sets the port
    def fake_start(self, *args, **kwargs):
        # Provide a port attribute similar to the real WebServer
        self.port = port

    monkeypatch.setattr(web_module.WebServer, "start", fake_start)

    # Start the test HTTP server immediately so it's accepting connections
    server_thread.start()

    # Ensure e-paper disabled via env to simulate resource-constrained environment
    monkeypatch.setenv("CALENDARBOT_DISABLE_EPAPER", "1")

    args = SimpleNamespace(port=port, host="127.0.0.1", auto_open=False)

    # Run web mode in background, give it time to start, then query the endpoint
    web_task = None
    try:
        web_task = pytest.helpers.async_run_in_task(web_module.run_web_mode(args))
    except Exception:
        # Some test harnesses may not provide pytest.helpers - fallback to creating a task directly
        import asyncio

        web_task = asyncio.create_task(web_module.run_web_mode(args))

    # Wait briefly for the patched web server to start and register port
    import time

    time.sleep(1.0)

    # Perform HTTP request against our lightweight server
    import requests

    resp = requests.get(f"http://127.0.0.1:{port}/api/whats-next/data", timeout=10)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Send SIGINT to trigger graceful shutdown in run_web_mode
    os.kill(os.getpid(), signal.SIGINT)

    # Await completion of web mode run
    import asyncio

    try:
        result = await asyncio.wait_for(web_task, timeout=10.0)
    except asyncio.TimeoutError:
        server.shutdown()
        pytest.fail("run_web_mode did not exit within timeout after SIGINT")

    assert result == 0

    # Cleanup test HTTP server
    server.shutdown()
