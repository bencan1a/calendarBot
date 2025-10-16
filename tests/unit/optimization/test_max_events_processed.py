import asyncio
from datetime import datetime, timedelta
from threading import Thread
from types import SimpleNamespace

import pytest

from calendarbot.config.settings import get_settings, reset_settings
from calendarbot.optimization.event_cache import CacheableEvent, EventCache
from calendarbot.web.server import WebServer


@pytest.mark.asyncio
async def test_event_cache_respects_max_events_processed() -> None:
    """EventCache.get_events should respect optimization.max_events_processed when set."""
    # Ensure clean settings state for test
    reset_settings()
    try:
        settings = get_settings()
        settings.optimization.max_events_processed = 5

        # Prepare 10 cacheable events and mock cache_manager.get to return their dicts
        now = datetime.now()
        events = [
            CacheableEvent(
                uid=f"evt-{i}",
                title=f"Event {i}",
                start_time=now + timedelta(minutes=i),
                end_time=now + timedelta(minutes=i + 30),
            )
            for i in range(10)
        ]

        class DummyCacheManager:
            async def get(self, key, prefix):
                await asyncio.sleep(0)  # simulate async
                return [e.to_dict() for e in events]

        cache_mgr = DummyCacheManager()
        ec = EventCache(cache_manager=cache_mgr)

        result = await ec.get_events("source-key")
        assert isinstance(result, list)
        # Should be capped to 5
        assert len(result) == 5
    finally:
        reset_settings()


def _start_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def test_webserver_defensive_slice() -> None:
    """WebServer should defensively slice events received from cache according to settings."""
    # Clean settings and set cap to 3
    reset_settings()
    try:
        settings = get_settings()
        settings.optimization.prebuild_asset_cache = False
        settings.optimization.max_events_processed = 3
        settings.web_host = "127.0.0.1"
        settings.web_port = 8080
        settings.web_layout = "whats-next-view"
        settings.auto_kill_existing = False

        # Create dummy display manager that captures events passed to renderer
        class DummyRenderer:
            def __init__(self):
                self.received_events = None

            def render_events(self, events, status_info, debug_time=None):
                # Capture for assertions
                self.received_events = list(events)
                return "<html>ok</html>"

        class DummyDisplayManager:
            def __init__(self):
                self.renderer = DummyRenderer()

            def set_layout(self, layout):
                return True

        # Create 10 dummy event-like objects (simple namespace)
        now = datetime.now()
        dummy_events = [
            SimpleNamespace(graph_id=f"id-{i}", start=now, end=now, show_as=None) for i in range(10)
        ]

        async def async_get_events(start, end):
            await asyncio.sleep(0)
            return dummy_events

        # Dummy cache manager exposing the async method used by WebServer
        cache_mgr = SimpleNamespace(get_events_by_date_range=async_get_events)

        display_manager = DummyDisplayManager()

        web = WebServer(settings, display_manager, cache_mgr)
        # Provide no settings_service to avoid filtering branch
        web.settings_service = None

        # Start a background loop in a thread so run_coroutine_threadsafe works
        loop = asyncio.new_event_loop()
        t = Thread(target=_start_loop, args=(loop,), daemon=True)
        t.start()
        web._background_loop = loop

        try:
            html = web.get_calendar_html(days=1)
            assert isinstance(html, str)
            # The renderer should have received at most 3 events due to defensive slicing
            received = display_manager.renderer.received_events
            assert received is not None
            assert len(received) == 3
        finally:
            # Stop background loop and join thread
            loop.call_soon_threadsafe(loop.stop)
            t.join(timeout=2.0)
    finally:
        reset_settings()


@pytest.mark.asyncio
async def test_null_setting_returns_all_events() -> None:
    """When max_events_processed is None, EventCache should return full list."""
    reset_settings()
    try:
        settings = get_settings()
        settings.optimization.max_events_processed = None

        now = datetime.now()
        events = [
            CacheableEvent(
                uid=f"evt-{i}",
                title=f"Event {i}",
                start_time=now + timedelta(minutes=i),
                end_time=now + timedelta(minutes=i + 30),
            )
            for i in range(10)
        ]

        class DummyCacheManager:
            async def get(self, key, prefix):
                await asyncio.sleep(0)
                return [e.to_dict() for e in events]

        cache_mgr = DummyCacheManager()
        ec = EventCache(cache_manager=cache_mgr)

        result = await ec.get_events("source-key")
        assert isinstance(result, list)
        # No cap applied; should return all 10
        assert len(result) == 10
    finally:
        reset_settings()
