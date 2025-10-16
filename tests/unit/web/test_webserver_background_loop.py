import threading
import time

from calendarbot.web.server import WebServer


class DummySettings:
    def __init__(self):
        self.web_host = "127.0.0.1"
        self.web_port = 0  # let OS pick a free port
        self.web_layout = "4x8"
        self.auto_kill_existing = False

        class Opt:
            prebuild_asset_cache = False

        self.optimization = Opt()


class DummyDisplayManager:
    def get_calendar_html(self, days=1):
        return "<html></html>"

    def set_display_type(self, *args, **kwargs):
        return None


class DummyCacheManager:
    async def get_events_by_date_range(self, start, end):
        return []


def test_webserver_background_loop_start_stop():
    """Start WebServer and ensure a single background asyncio loop/thread is created and cleaned up."""
    settings = DummySettings()
    display = DummyDisplayManager()
    cache = DummyCacheManager()

    server = WebServer(settings, display, cache)

    # Start server (should create server thread and background loop thread)
    server.start()

    # Give threads a short moment to start
    time.sleep(0.1)

    # Background loop and thread should be set
    assert getattr(server, "_background_loop", None) is not None
    assert getattr(server, "_background_thread", None) is not None
    assert isinstance(server._background_thread, threading.Thread)
    assert server._background_thread.is_alive()

    # Stop server (should stop background loop and join thread)
    server.stop()

    # Allow a short time for graceful shutdown
    time.sleep(0.1)

    assert getattr(server, "_background_loop", None) is None
    # Background thread reference should be cleared or not alive
    if getattr(server, "_background_thread", None) is not None:
        assert not server._background_thread.is_alive()
