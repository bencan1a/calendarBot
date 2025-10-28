import asyncio
import time

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
        # Simulate async work and return deterministic result
        await asyncio.sleep(0)
        return [{"id": "evt-1"}, {"id": "evt-2"}]


def test_run_coroutine_threadsafe_bridge_same_result():
    """Verify _get_events_async_safe (which uses the background loop) returns same result as awaiting directly."""
    settings = DummySettings()
    display = DummyDisplayManager()
    cache = SlowCacheManager()

    server = WebServer(settings, display, cache)
    server.start()

    # give background loop time to spin up
    time.sleep(0.05)

    handler = WebRequestHandler(web_server=server)

    # Use direct asyncio.run to get expected value
    expected = asyncio.run(cache.get_events_by_date_range(None, None))

    # Call the sync bridge which should schedule on the background loop
    result = handler._get_events_async_safe(None, None)

    assert result == expected

    server.stop()
