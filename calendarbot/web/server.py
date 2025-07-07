"""Simple HTTP server for web interface."""

import asyncio
import json
import logging
import mimetypes
import os
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from ..security.logging import SecurityEventLogger
from ..utils.process import auto_cleanup_before_start

logger = logging.getLogger(__name__)


class WebRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for calendar web interface."""

    def __init__(self, *args, web_server=None, **kwargs):
        self.web_server = web_server
        self.security_logger = SecurityEventLogger()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            if path == "/" or path == "/calendar":
                self._serve_calendar_page(query_params)
            elif path.startswith("/api/"):
                self._handle_api_request(path, query_params)
            elif path.startswith("/static/"):
                self._serve_static_file(path)
            else:
                self._send_404()

        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self._send_500(str(e))

    def do_POST(self):
        """Handle POST requests."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path

            if path.startswith("/api/"):
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)

                try:
                    data = json.loads(post_data.decode("utf-8")) if post_data else {}
                except json.JSONDecodeError:
                    data = {}

                self._handle_api_request(path, data)
            else:
                self._send_404()

        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self._send_500(str(e))

    def _serve_calendar_page(self, query_params: Dict):
        """Serve the main calendar page."""
        try:
            if not self.web_server:
                self._send_500("Web server not available")
                return

            # Get calendar HTML content
            html_content = self.web_server.get_calendar_html()

            self._send_response(200, html_content, "text/html")

        except Exception as e:
            logger.error(f"Error serving calendar page: {e}")
            self._send_500(str(e))

    def _handle_api_request(self, path: str, params):
        """Handle API requests."""
        try:
            if not self.web_server:
                self._send_json_response(500, {"error": "Web server not available"})
                return

            if path == "/api/navigate":
                self._handle_navigation_api(params)
            elif path == "/api/theme":
                self._handle_theme_api(params)
            elif path == "/api/refresh":
                self._handle_refresh_api()
            elif path == "/api/status":
                self._handle_status_api()
            else:
                self._send_json_response(404, {"error": "API endpoint not found"})

        except Exception as e:
            logger.error(f"Error handling API request: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _handle_navigation_api(self, params):
        """Handle navigation API requests."""
        logger.debug(f"Navigation API params type: {type(params)}")
        logger.debug(f"Navigation API params content: {params}")

        # Handle both JSON format {"action": "value"} and query format {"action": ["value"]}
        if isinstance(params, dict) and "action" in params:
            action_value = params["action"]
            # If it's a list (query params), take first element; if string (JSON), use directly
            action = action_value[0] if isinstance(action_value, list) else action_value
        else:
            action = params.get("action", "") if hasattr(params, "get") else ""

        logger.debug(f"Extracted navigation action: '{action}'")

        # Validate navigation action input
        valid_actions = ["prev", "next", "today", "week-start", "week-end"]
        if not action:
            self.security_logger.log_input_validation_failure(
                input_type="navigation_action",
                validation_error="Missing action parameter",
                details={
                    "source_ip": self.client_address[0],
                    "input_value": "",
                    "endpoint": "/api/navigate",
                },
            )
            logger.warning("Missing action parameter in navigation request")
            self._send_json_response(400, {"error": "Missing action parameter"})
            return

        if action not in valid_actions:
            self.security_logger.log_input_validation_failure(
                input_type="navigation_action",
                validation_error=f"Invalid navigation action: {action}",
                details={
                    "source_ip": self.client_address[0],
                    "input_value": action,
                    "valid_actions": valid_actions,
                    "endpoint": "/api/navigate",
                },
            )
            logger.warning(f"Invalid navigation action: {action}")
            self._send_json_response(400, {"error": "Invalid navigation action"})
            return

        # No logging for successful validation - only security violations are logged
        logger.debug(f"Valid navigation action: {action}")

        success = self.web_server.handle_navigation(action)

        if success:
            # Get updated HTML content
            html_content = self.web_server.get_calendar_html()
            self._send_json_response(200, {"success": True, "html": html_content})
        else:
            self._send_json_response(400, {"error": "Invalid navigation action"})

    def _handle_theme_api(self, params):
        """Handle theme switching API requests."""
        theme = (
            params.get("theme", [""])[0]
            if isinstance(params, dict) and "theme" in params
            else params.get("theme", "")
        )

        if theme:
            success = self.web_server.set_theme(theme)
            self._send_json_response(200, {"success": success, "theme": theme})
        else:
            # Toggle theme
            new_theme = self.web_server.toggle_theme()
            self._send_json_response(200, {"success": True, "theme": new_theme})

    def _handle_refresh_api(self):
        """Handle refresh API requests."""
        success = self.web_server.refresh_data()
        html_content = self.web_server.get_calendar_html()
        self._send_json_response(200, {"success": success, "html": html_content})

    def _handle_status_api(self):
        """Handle status API requests."""
        status = self.web_server.get_status()
        self._send_json_response(200, status)

    def _serve_static_file(self, path: str):
        """Serve static files (CSS, JS, etc.)."""
        try:
            # Remove /static/ prefix
            file_path = path[8:]  # Remove '/static/'

            # Get the static directory path
            static_dir = Path(__file__).parent / "static"
            full_path = static_dir / file_path

            # Security check - ensure file is within static directory
            if not str(full_path.resolve()).startswith(str(static_dir.resolve())):
                self._send_404()
                return

            if full_path.exists() and full_path.is_file():
                # Determine content type
                content_type, _ = mimetypes.guess_type(str(full_path))
                if not content_type:
                    content_type = "text/plain"

                # Read and serve file
                with open(full_path, "rb") as f:
                    content = f.read()

                self._send_response(200, content, content_type, binary=True)
            else:
                self._send_404()

        except Exception as e:
            logger.error(f"Error serving static file {path}: {e}")
            self._send_500(str(e))

    def _send_response(
        self, status_code: int, content: str | bytes, content_type: str, binary: bool = False
    ):
        """Send HTTP response."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")

        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        self.send_header("Content-Length", str(len(content_bytes)))
        self.end_headers()

        self.wfile.write(content_bytes)

    def _send_json_response(self, status_code: int, data: Dict):
        """Send JSON response."""
        json_content = json.dumps(data, indent=2)
        self._send_response(status_code, json_content, "application/json")

    def _send_404(self):
        """Send 404 Not Found response."""
        self._send_response(404, "404 Not Found", "text/plain")

    def _send_500(self, error_message: str):
        """Send 500 Internal Server Error response."""
        self._send_response(500, f"500 Internal Server Error: {error_message}", "text/plain")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"HTTP {format % args}")


class WebServer:
    """Simple web server for calendar HTML interface."""

    def __init__(self, settings, display_manager, cache_manager, navigation_state=None):
        """Initialize web server.

        Args:
            settings: Application settings
            display_manager: Display manager for rendering
            cache_manager: Cache manager for data
            navigation_state: Optional navigation state for interactive mode
        """
        self.settings = settings
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.navigation_state = navigation_state

        # Server configuration
        self.host = settings.web_host
        self.port = settings.web_port
        self.theme = settings.web_theme

        # Server instance
        self.server = None
        self.server_thread = None
        self.running = False

        logger.info(f"Web server initialized on {self.host}:{self.port}")

    def start(self):
        """Start the web server."""
        if self.running:
            logger.warning("Web server already running")
            return

        try:
            # Automatically clean up any conflicting processes before starting (if configured)
            if self.settings.auto_kill_existing:
                logger.info(
                    f"Checking for existing processes before starting web server on {self.host}:{self.port}"
                )
                cleanup_success = auto_cleanup_before_start(self.host, self.port, force=True)

                if not cleanup_success:
                    logger.warning(
                        f"Port {self.port} may still be in use, attempting to start anyway"
                    )
            else:
                logger.debug("Auto-cleanup of existing processes disabled in configuration")

            # Create custom request handler with web server reference
            def handler(*args, **kwargs):
                return WebRequestHandler(*args, web_server=self, **kwargs)

            # Create and start server
            self.server = HTTPServer((self.host, self.port), handler)
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

            self.running = True
            logger.info(f"Web server started on http://{self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise

    def stop(self):
        """Stop the web server."""
        if not self.running:
            return

        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()

            if self.server_thread:
                self.server_thread.join(timeout=5)

            self.running = False
            logger.info("Web server stopped")

        except Exception as e:
            logger.error(f"Error stopping web server: {e}")

    def get_calendar_html(self) -> str:
        """Get current calendar HTML content."""
        try:
            logger.debug(f"Navigation state available: {self.navigation_state is not None}")

            # Get current events
            if self.navigation_state:
                # Interactive mode - get events for selected date
                selected_date = self.navigation_state.selected_date
                start_datetime = datetime.combine(selected_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=1)

                logger.debug(
                    f"Interactive mode - getting events for {selected_date} ({start_datetime} to {end_datetime})"
                )

                # This should be async, but we're in sync context
                # In a real implementation, we'd need to handle this properly
                events = asyncio.run(
                    self.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
                )

                logger.debug(f"Retrieved {len(events)} events for selected date")

                # Build status info for interactive mode
                status_info = {
                    "selected_date": self.navigation_state.get_display_date(),
                    "is_today": self.navigation_state.is_today(),
                    "relative_description": self.navigation_state.get_relative_description(),
                    "interactive_mode": True,
                    "last_update": datetime.now().isoformat(),
                    "is_cached": False,  # TODO: Get actual cache status
                    "connection_status": "Online",
                }
            else:
                # Non-interactive mode - get today's events
                today = date.today()
                start_datetime = datetime.combine(today, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=1)

                logger.debug(
                    f"Non-interactive mode - getting events for today {today} ({start_datetime} to {end_datetime})"
                )

                events = asyncio.run(
                    self.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
                )

                logger.debug(f"Retrieved {len(events)} events for today")

                # Static web display mode - no navigation buttons
                status_info = {
                    "last_update": datetime.now().isoformat(),
                    "is_cached": False,
                    "connection_status": "Online",
                    "interactive_mode": False,
                }

            logger.debug(f"Display manager renderer type: {type(self.display_manager.renderer)}")
            logger.debug(
                f"Renderer has render_events method: {hasattr(self.display_manager.renderer, 'render_events')}"
            )

            # Generate HTML using display manager
            if hasattr(self.display_manager.renderer, "render_events"):
                html_result = self.display_manager.renderer.render_events(events, status_info)
                logger.debug(f"Generated HTML length: {len(html_result)} characters")
                return html_result
            else:
                logger.error("HTML renderer does not have render_events method")
                return "<html><body><h1>Error: HTML renderer not available</h1></body></html>"

        except Exception as e:
            logger.error(f"Error getting calendar HTML: {e}")
            return f"<html><body><h1>Error</h1><p>{e}</p></body></html>"

    def handle_navigation(self, action: str) -> bool:
        """Handle navigation action.

        Args:
            action: Navigation action (prev, next, today, etc.)

        Returns:
            True if action was successful
        """
        if not self.navigation_state:
            logger.warning("Navigation not available - no navigation state")
            return False

        try:
            if action == "prev":
                self.navigation_state.navigate_backward()
            elif action == "next":
                self.navigation_state.navigate_forward()
            elif action == "today":
                self.navigation_state.jump_to_today()
            elif action == "week-start":
                self.navigation_state.jump_to_start_of_week()
            elif action == "week-end":
                self.navigation_state.jump_to_end_of_week()
            else:
                logger.warning(f"Unknown navigation action: {action}")
                return False

            logger.debug(f"Navigation action '{action}' completed")
            return True

        except Exception as e:
            logger.error(f"Error handling navigation action '{action}': {e}")
            return False

    def set_theme(self, theme: str) -> bool:
        """Set the display theme.

        Args:
            theme: Theme name (eink, standard, eink-rpi)

        Returns:
            True if theme was set successfully
        """
        if theme in ["eink", "standard", "eink-rpi"]:
            self.theme = theme
            if hasattr(self.display_manager.renderer, "theme"):
                self.display_manager.renderer.theme = theme
            logger.debug(f"Theme set to: {theme}")
            return True
        else:
            logger.warning(f"Unknown theme: {theme}")
            return False

    def toggle_theme(self) -> str:
        """Toggle between themes.

        Returns:
            New theme name
        """
        # Cycle through available themes: eink -> standard -> eink-rpi -> eink
        if self.theme == "eink":
            new_theme = "standard"
        elif self.theme == "standard":
            new_theme = "eink-rpi"
        else:  # eink-rpi or any other
            new_theme = "eink"

        self.set_theme(new_theme)
        return new_theme

    def refresh_data(self) -> bool:
        """Trigger data refresh.

        Returns:
            True if refresh was triggered successfully
        """
        try:
            # In a real implementation, this would trigger a data refresh
            # For now, we'll just return success
            logger.debug("Data refresh requested")
            return True
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get server status information.

        Returns:
            Status information dictionary
        """
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "theme": self.theme,
            "interactive_mode": self.navigation_state is not None,
            "current_date": (
                self.navigation_state.selected_date.isoformat()
                if self.navigation_state
                else date.today().isoformat()
            ),
        }

    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"
