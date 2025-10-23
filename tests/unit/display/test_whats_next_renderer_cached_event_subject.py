import logging
from datetime import datetime, timedelta
from types import SimpleNamespace

from calendarbot.display.whats_next_renderer import WhatsNextRenderer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_renderer_normalizes_cachedevent_subject():
    """Ensure WhatsNextRenderer normalizes CachedEvent to EventData and renders subject from body_preview."""
    now = datetime.now()
    start = now + timedelta(minutes=10)
    end = start + timedelta(hours=1)

    fake_cached = SimpleNamespace(
        subject=None,
        title="",
        summary=None,
        name=None,
        body_preview="Team Sync Meeting\nAgenda",
        description=None,
        start_dt=start,
        end_dt=end,
        location_display_name="Conference Room",
        graph_id="graph-xxx",
        attendees=None,
        is_current=lambda: False,
        is_upcoming=lambda: True,
        format_time_range=lambda: f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}",
    )

    class Settings:
        epaper = False

    renderer = WhatsNextRenderer(Settings())
    html = renderer._render_events_content([fake_cached])  # type: ignore
    assert "Team Sync Meeting" in html, (
        "Renderer should extract subject from body_preview and include it in HTML"
    )
