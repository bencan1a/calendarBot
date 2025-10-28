import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from calendarbot.web.server import WebRequestHandler, WebServer


class DummySettings:
    def __init__(self):
        self.web_host = "127.0.0.1"
        self.web_port = 0
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


class SlowCacheManager:
    async def get_events_by_date_range(self, start, end):
        # small async delay to exercise bridging under concurrency
        await __import__("asyncio").sleep(0.01)
        return [{"id": "evt-1", "start": start, "end": end}]


def test_no_new_event_loop_per_request_under_load():
    """Simulate many concurrent synchronous calls into the async bridge and ensure only one background thread exists."""
    settings = DummySettings()
    display = DummyDisplayManager()
    cache = SlowCacheManager()

    server = WebServer(settings, display, cache)
    server.start()

    # allow background loop to spin up
    time.sleep(0.05)

    handler = WebRequestHandler(web_server=server)

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(hours=1)

    # Compute expected via direct asyncio.run
    expected = __import__("asyncio").run(cache.get_events_by_date_range(start_dt, end_dt))

    # Run many concurrent sync calls that use the bridge
    results = []
    with ThreadPoolExecutor(max_workers=20) as exe:
        futures = [exe.submit(handler._get_events_async_safe, start_dt, end_dt) for _ in range(50)]
        for f in futures:
            results.append(f.result(timeout=2.0))

    # All results should match expected
    assert all(r == expected for r in results)

    # Exactly one background thread with name "WebBackgroundLoop" should exist while server was running
    bg_threads = [t for t in threading.enumerate() if t.name == "WebBackgroundLoop"]
    assert len(bg_threads) == 1

    # Stop server and ensure cleanup
    server.stop()
    time.sleep(0.05)

    # background loop reference should be cleared
    assert getattr(server, "_background_loop", None) is None
    # background thread should not be alive (or reference cleared)
    if getattr(server, "_background_thread", None) is not None:
        assert not server._background_thread.is_alive()
