"""Static file serving routes for calendarbot_lite."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def register_static_routes(app: Any, package_dir: Path) -> None:
    """Register static file serving routes.

    Args:
        app: aiohttp web application
        package_dir: Path to calendarbot_lite package directory
    """
    from aiohttp import web

    async def serve_static_html(_request: Any) -> Any:
        """Serve the static whatsnext.html file."""
        html_file = package_dir / "whatsnext.html"
        if not html_file.exists():
            logger.error("Static HTML file not found: %s", html_file)
            return web.Response(text="Static HTML file not found", status=404)

        return web.FileResponse(html_file)

    async def serve_static_css(_request: Any) -> Any:
        """Serve the static whatsnext.css file."""
        css_file = package_dir / "whatsnext.css"
        if not css_file.exists():
            logger.error("Static CSS file not found: %s", css_file)
            return web.Response(text="CSS file not found", status=404)

        return web.FileResponse(css_file)

    async def serve_static_js(_request: Any) -> Any:
        """Serve the static whatsnext.js file."""
        js_file = package_dir / "whatsnext.js"
        if not js_file.exists():
            logger.error("Static JS file not found: %s", js_file)
            return web.Response(text="JS file not found", status=404)

        return web.FileResponse(js_file)

    # Register routes
    app.router.add_get("/", serve_static_html)
    app.router.add_get("/whatsnext.css", serve_static_css)
    app.router.add_get("/whatsnext.js", serve_static_js)

    logger.debug("Static routes registered")
