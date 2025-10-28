import logging
from pathlib import Path
from unittest.mock import Mock, patch

from calendarbot.web.server import WebRequestHandler, WebServer

logger = logging.getLogger(__name__)


def _make_basic_deps():
    mock_display_manager = Mock()
    mock_display_manager.renderer = Mock()
    mock_display_manager.renderer.render_events.return_value = "<html></html>"

    mock_cache_manager = Mock()

    async def _dummy_get_events(a, b):
        return []

    mock_cache_manager.get_events_by_date_range = _dummy_get_events

    mock_navigation_state = Mock()
    mock_navigation_state.selected_date = None

    return mock_display_manager, mock_cache_manager, mock_navigation_state


def test_webserver_prebuild_enabled_calls_build_cache():
    display_manager, cache_manager, nav_state = _make_basic_deps()

    settings = Mock()
    settings.web_host = "localhost"
    settings.web_port = 8080
    settings.web_layout = "4x8"
    settings.auto_kill_existing = False
    settings.optimization = Mock(prebuild_asset_cache=True)

    with patch("calendarbot.web.server.StaticAssetCache.build_cache") as mock_build:
        ws = WebServer(settings, display_manager, cache_manager, nav_state)
        mock_build.assert_called_once()


def test_webserver_prebuild_disabled_triggers_targeted_build_on_first_static_request():
    display_manager, cache_manager, nav_state = _make_basic_deps()

    settings = Mock()
    settings.web_host = "localhost"
    settings.web_port = 8080
    settings.web_layout = "4x8"
    settings.auto_kill_existing = False
    settings.optimization = Mock(prebuild_asset_cache=False)

    with patch("calendarbot.web.server.StaticAssetCache.build_cache") as mock_build:
        ws = WebServer(settings, display_manager, cache_manager, nav_state)
        mock_build.assert_not_called()

    # Ensure cache is empty
    asset_cache = ws.asset_cache
    asset_cache.clear_cache()
    assert not asset_cache.is_cache_built()

    # Prepare a repo file path to simulate existing static asset (fallback if not present)
    repo_path = Path(__file__).parent.parent / "calendarbot" / "web" / "static" / "favicon.ico"
    if not repo_path.exists():
        repo_path = (
            Path(__file__).parent.parent
            / "calendarbot"
            / "web"
            / "static"
            / "layouts"
            / "4x8"
            / "4x8.css"
        )

    # Mock ensure_built_for to simulate adding an entry to cache
    def ensure_side_effect(requested_path, layout_name=None):
        key = requested_path.replace("\\", "/").lstrip("/")
        asset_cache._asset_map[key] = Mock(absolute_path=repo_path)

    asset_cache.ensure_built_for = Mock(side_effect=ensure_side_effect)
    asset_cache.resolve_asset_path = Mock(return_value=None)

    # Create handler bypassing BaseHTTPRequestHandler.__init__
    with (
        patch("calendarbot.web.server.SecurityEventLogger"),
        patch.object(WebRequestHandler, "__init__", lambda *_args, **_kwargs: None),
    ):
        handler = WebRequestHandler()
        handler.web_server = ws
        handler.security_logger = Mock()
        handler.client_address = ("127.0.0.1", 12345)
        handler.path = "/static/favicon.ico"
        handler.command = "GET"
        handler.headers = {}
        handler.rfile = None
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler._serve_static_file("/static/favicon.ico")

    asset_cache.ensure_built_for.assert_called()
    # After ensure_side_effect, simulate resolve returning the file
    asset_cache.resolve_asset_path = Mock(return_value=repo_path)
    assert asset_cache.resolve_asset_path("favicon.ico") == repo_path
