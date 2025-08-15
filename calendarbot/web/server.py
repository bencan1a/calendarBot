"""Simple HTTP server for web interface."""

import asyncio
import hashlib
import json
import logging
import mimetypes
import sqlite3
from collections import OrderedDict
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Optional, Union
from urllib.parse import parse_qs, urlparse

from ..config.build import (
    get_asset_exclusion_info,
    is_debug_asset,
    is_production_mode,
    should_exclude_asset,
)
from ..display.whats_next_data_model import EventData, WhatsNextViewModel
from ..layout.lazy_registry import LazyLayoutRegistry
from ..layout.registry import LayoutRegistry
from ..layout.resource_manager import ResourceManager
from ..optimization.connection_manager import get_connection_manager
from ..optimization.static_asset_cache import StaticAssetCache
from ..security.logging import SecurityEventLogger
from ..settings.exceptions import SettingsError, SettingsValidationError
from ..settings.service import SettingsService
from ..utils.process import auto_cleanup_before_start
from ..utils.thread_pool import run_in_thread_pool

logger = logging.getLogger(__name__)


class WebServerError(Exception):
    """Custom exception for web server errors."""


class StaticFileCache:
    """LRU cache for static file content with size limit (~10MB)."""

    def __init__(self, max_size_bytes: int = 10 * 1024 * 1024) -> None:
        """Initialize cache with maximum size in bytes.

        Args:
            max_size_bytes: Maximum cache size in bytes (default: 10MB)
        """
        self.max_size_bytes = max_size_bytes
        self.current_size = 0
        self.cache: OrderedDict[str, tuple[bytes, int, str]] = (
            OrderedDict()
        )  # path -> (content, size, etag)

    def _evict_lru(self) -> None:
        """Remove least recently used items until cache size is acceptable."""
        while self.current_size > self.max_size_bytes and self.cache:
            _, (_, size, _) = self.cache.popitem(last=False)
            self.current_size -= size

    def get(self, file_path: str) -> Optional[tuple[bytes, str]]:
        """Get cached file content and ETag.

        Args:
            file_path: File path to retrieve

        Returns:
            Tuple of (content, etag) if found, None otherwise
        """
        if file_path in self.cache:
            # Move to end (mark as recently used)
            content, size, etag = self.cache.pop(file_path)
            self.cache[file_path] = (content, size, etag)
            return content, etag
        return None

    def put(self, file_path: str, content: bytes, etag: str) -> None:
        """Store file content in cache.

        Args:
            file_path: File path to store
            content: File content bytes
            etag: ETag for cache validation
        """
        content_size = len(content)

        # Don't cache files larger than half the cache size
        if content_size > self.max_size_bytes // 2:
            return

        # Remove existing entry if present
        if file_path in self.cache:
            _, old_size, _ = self.cache.pop(file_path)
            self.current_size -= old_size

        # Add new entry
        self.cache[file_path] = (content, content_size, etag)
        self.current_size += content_size

        # Evict LRU items if needed
        self._evict_lru()

    def clear(self) -> None:
        """Clear all cached content."""
        self.cache.clear()
        self.current_size = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size_bytes": self.current_size,
            "max_size_bytes": self.max_size_bytes,
            "cached_files": len(self.cache),
            "cache_utilization": self.current_size / self.max_size_bytes
            if self.max_size_bytes > 0
            else 0,
        }


class WebRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for calendar web interface."""

    def __init__(self, *args: Any, web_server: Optional["WebServer"] = None, **kwargs: Any) -> None:
        """Initialize WebRequestHandler for both production and test contexts.

        Args:
            *args: Variable arguments passed by HTTP server (request, client_address, server)
                  When called by HTTP server, contains 3 required arguments.
                  When called directly in tests, may be empty.
            web_server: Optional WebServer instance for accessing application services
            **kwargs: Additional keyword arguments

        Note:
            This constructor handles both production HTTP server instantiation and
            direct test instantiation. The parent BaseHTTPRequestHandler.__init__
            is only called when the required HTTP server arguments are present.
        """
        self.web_server = web_server
        self.security_logger = SecurityEventLogger()

        # Only call parent constructor if we have the required HTTP server arguments
        # BaseHTTPRequestHandler requires: request, client_address, server
        if len(args) >= 3:
            # Production context: called by HTTP server with required arguments
            super().__init__(*args, **kwargs)
        else:
            # Test context: called directly without HTTP server arguments
            # Initialize required attributes that parent constructor would set
            self.request = None
            self.client_address = None  # type: ignore[assignment]
            self.server = None  # type: ignore[assignment]
            self.rfile = None  # type: ignore[assignment]
            self.wfile = None  # type: ignore[assignment]
            self.headers = None  # type: ignore[assignment]
            self.command = None  # type: ignore[assignment]
            self.path = None  # type: ignore[assignment]
            self.version = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            if path in {"/", "/calendar"}:
                self._serve_calendar_page(query_params)
            elif path == "/database-viewer":
                self._serve_database_viewer()
            elif path == "/health":
                self._handle_health_check()
            elif path == "/favicon.ico":
                self._serve_static_file("/static/favicon.ico")
            elif path.startswith("/api/"):
                self._handle_api_request(path, query_params)
            elif path.startswith("/static/"):
                self._serve_static_file(path)
            else:
                self._send_404()

        except Exception as e:
            logger.exception("Error handling GET request")
            self._send_500(str(e))

    def do_POST(self) -> None:
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
            logger.exception("Error handling POST request")
            self._send_500(str(e))

    def do_PUT(self) -> None:
        """Handle PUT requests."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path

            if path.startswith("/api/"):
                content_length = int(self.headers.get("Content-Length", 0))
                put_data = self.rfile.read(content_length)

                try:
                    data = json.loads(put_data.decode("utf-8")) if put_data else {}
                except json.JSONDecodeError:
                    data = {}

                self._handle_api_request(path, data)
            else:
                self._send_404()

        except Exception as e:
            logger.exception("Error handling PUT request")
            self._send_500(str(e))

    def _serve_calendar_page(self, query_params: dict[str, list[str]]) -> None:
        """Serve the main calendar page."""
        try:
            if not self.web_server:
                self._send_500("Web server not available")
                return

            # Get calendar HTML content
            current_layout = self.web_server.get_current_layout()
            days = 7 if current_layout == "whats-next-view" else 1
            html_content = self.web_server.get_calendar_html(days)

            self._send_response(200, html_content, "text/html")

        except Exception as e:
            logger.exception("Error serving calendar page")
            self._send_500(str(e))

    def _serve_database_viewer(self) -> None:
        """Serve the database viewer page."""
        try:
            # Get the path to the database viewer HTML file
            static_dir = Path(__file__).parent / "static"
            viewer_path = static_dir / "database-viewer.html"

            if not viewer_path.exists():
                self._send_404()
                return

            # Read and serve the HTML content
            html_content = viewer_path.read_text(encoding="utf-8")
            self._send_response(200, html_content, "text/html")

        except Exception as e:
            logger.exception("Error serving database viewer page")
            self._send_500(str(e))

    def _handle_api_request(
        self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle API requests."""
        try:
            logger.debug(f"API request routing: path='{path}', method={self.command}")

            if not self.web_server:
                self._send_json_response(500, {"error": "Web server not available"})
                return

            if path == "/api/navigate":
                logger.debug("Routing to navigation API")
                self._handle_navigation_api(params)
            elif path == "/api/layout":
                logger.debug("Routing to layout API")
                self._handle_layout_api(params)
            elif path == "/api/theme":
                logger.debug("Routing to theme API (redirect to layout)")
                # Backward compatibility - redirect to layout API
                self._handle_layout_api(params)
            elif path == "/api/refresh":
                logger.debug("Routing to refresh API")
                self._handle_refresh_api(params)
            elif path == "/api/whats-next/data":
                logger.debug("Routing to whats-next data API")
                self._handle_whats_next_data_api(params)
            elif path == "/api/status":
                logger.debug("Routing to status API")
                self._handle_status_api()
            elif path.startswith("/api/settings"):
                logger.debug("Routing to settings API")
                self._handle_settings_api(path, params)
            elif path.startswith("/api/events"):
                logger.debug("Routing events API to settings handler")
                self._handle_settings_api(path, params)
            elif path.startswith("/api/database"):
                logger.debug("Routing to database API")
                self._handle_database_api(path, params)
            else:
                logger.warning(f"No route found for API path: {path}")
                self._send_json_response(404, {"error": "API endpoint not found"})

        except Exception as e:
            logger.exception("Error handling API request")
            self._send_json_response(500, {"error": str(e)})

    def _handle_navigation_api(self, params: Union[dict[str, list[str]], dict[str, Any]]) -> None:
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

        if self.web_server:
            success = self.web_server.handle_navigation(action)

            if success:
                # Get updated HTML content
                current_layout = self.web_server.get_current_layout()
                days = 7 if current_layout == "whats-next-view" else 1
                html_content = self.web_server.get_calendar_html(days)
                self._send_json_response(200, {"success": True, "html": html_content})
            else:
                self._send_json_response(400, {"error": "Invalid navigation action"})
        else:
            self._send_json_response(500, {"error": "Web server not available"})

    def _handle_layout_api(self, params: Union[dict[str, list[str]], dict[str, Any]]) -> None:
        """Handle layout switching API requests."""
        if isinstance(params, dict) and "layout" in params:
            layout_value = params["layout"]
            # If it's a list (query params), take first element; if string (JSON), use directly
            layout = layout_value[0] if isinstance(layout_value, list) else layout_value
        else:
            layout = ""

        if not self.web_server:
            self._send_json_response(500, {"error": "Web server not available"})
            return

        if layout:
            success = self.web_server.set_layout(str(layout))
            if success:
                # Get updated HTML content with new layout
                days = 7 if layout == "whats-next-view" else 1
                html_content = self.web_server.get_calendar_html(days)
                self._send_json_response(
                    200, {"success": True, "layout": layout, "html": html_content}
                )
            else:
                self._send_json_response(400, {"error": "Invalid layout type"})
        else:
            # Cycle through layouts
            new_layout = self.web_server.cycle_layout()
            # Get updated HTML content with new layout
            days = 7 if new_layout == "whats-next-view" else 1
            html_content = self.web_server.get_calendar_html(days)
            self._send_json_response(
                200, {"success": True, "layout": new_layout, "html": html_content}
            )

    def _handle_refresh_api(
        self, params: Optional[Union[dict[str, list[str]], dict[str, Any]]] = None
    ) -> None:
        """Handle refresh API requests with optional debug time override."""
        if not self.web_server:
            self._send_json_response(500, {"error": "Web server not available"})
            return

        # Extract debug_time if provided (only for whats-next-view layout)
        debug_time = None
        current_layout = self.web_server.get_current_layout()

        if (
            current_layout == "whats-next-view"
            and params
            and isinstance(params, dict)
            and "debug_time" in params
        ):
            debug_time_value = params["debug_time"]
            debug_time_str = (
                debug_time_value[0] if isinstance(debug_time_value, list) else str(debug_time_value)
            )

            try:
                # Parse ISO format debug time
                debug_time = datetime.fromisoformat(debug_time_str.replace("Z", "+00:00"))
                logger.info(f"Debug mode: Using override time {debug_time.isoformat()}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid debug_time format '{debug_time_str}': {e}")
                debug_time = None

        success = self.web_server.refresh_data()
        days = 7 if current_layout == "whats-next-view" else 1
        html_content = self.web_server.get_calendar_html(days, debug_time=debug_time)
        self._send_json_response(200, {"success": success, "html": html_content})

    def _handle_whats_next_data_api(
        self, params: Optional[Union[dict[str, list[str]], dict[str, Any]]] = None
    ) -> None:
        """Handle What's Next data API requests.

        Args:
            params: Request parameters, including optional debug_time
        """
        if not self.web_server:
            self._send_json_response(500, {"error": "Web server not available"})
            return

        try:
            # Extract debug time and get current layout
            debug_time = self._extract_debug_time(params)
            current_layout = self.web_server.get_current_layout()

            # Get events and status info
            events, status_info = self._get_events_for_api(current_layout)

            # Filter out hidden events
            filtered_events = self._filter_events(events)

            # Create view model and return response
            self._create_and_send_view_model(filtered_events, status_info, debug_time)

        except Exception as e:
            logger.exception("Error handling What's Next data API request")
            self._send_json_response(500, {"error": str(e)})

    def _extract_debug_time(
        self, params: Optional[Union[dict[str, list[str]], dict[str, Any]]]
    ) -> Optional[datetime]:
        """Extract and parse debug_time from request parameters."""
        if not self.web_server:
            return None

        current_layout = self.web_server.get_current_layout()

        if (
            current_layout == "whats-next-view"
            and params
            and isinstance(params, dict)
            and "debug_time" in params
        ):
            debug_time_value = params["debug_time"]
            debug_time_str = (
                debug_time_value[0] if isinstance(debug_time_value, list) else str(debug_time_value)
            )

            try:
                # Parse ISO format debug time
                debug_time = datetime.fromisoformat(debug_time_str.replace("Z", "+00:00"))
                logger.info(f"Debug mode: Using override time {debug_time.isoformat()}")
                return debug_time
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid debug_time format '{debug_time_str}': {e}")

        return None

    def _get_events_for_api(self, current_layout: str) -> tuple[list[Any], dict[str, Any]]:
        """Get events and status info based on current layout and navigation state."""
        if not self.web_server:
            return [], {}

        days = 7 if current_layout == "whats-next-view" else 1

        if self.web_server.navigation_state:
            return self._get_interactive_mode_events(days)
        return self._get_non_interactive_mode_events(days)

    def _get_interactive_mode_events(self, days: int) -> tuple[list[Any], dict[str, Any]]:
        """Get events for interactive mode (navigation state available)."""
        if not self.web_server or not self.web_server.navigation_state:
            return [], {}

        selected_date = self.web_server.navigation_state.selected_date
        start_datetime = datetime.combine(selected_date, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=days)

        logger.debug(
            f"Interactive mode - getting events for {selected_date} ({start_datetime} to {end_datetime}) [days: {days}]"
        )

        events = self._get_events_async_safe(start_datetime, end_datetime)
        logger.debug(f"Retrieved {len(events)} events for selected date")

        # Build status info for interactive mode
        from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

        # Get cache status if cache manager is available
        is_cached = False
        if hasattr(self.web_server, "cache_manager") and self.web_server.cache_manager:
            # For now, just check if cache manager exists - a more complete implementation
            # would need to make this method async to properly check cache status
            is_cached = True

        status_info = {
            "selected_date": self.web_server.navigation_state.get_display_date(),
            "is_today": self.web_server.navigation_state.is_today(),
            "interactive_mode": True,
            "last_update": get_timezone_aware_now().isoformat(),
            "is_cached": is_cached,
        }

        return events, status_info

    def _get_non_interactive_mode_events(self, days: int) -> tuple[list[Any], dict[str, Any]]:
        """Get events for non-interactive mode (static web display)."""
        today = date.today()
        start_datetime = datetime.combine(today, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=days)

        logger.debug(
            f"Non-interactive mode - getting events for today {today} ({start_datetime} to {end_datetime}) [days: {days}]"
        )

        events = self._get_events_async_safe(start_datetime, end_datetime)
        logger.debug(f"Retrieved {len(events)} events for today")

        # Static web display mode - no navigation buttons
        from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

        status_info = {
            "last_update": get_timezone_aware_now().isoformat(),
            "is_cached": False,
            "interactive_mode": False,
        }

        return events, status_info

    def _get_events_async_safe(self, start_datetime: datetime, end_datetime: datetime) -> list[Any]:
        """Safely handle async event fetching from sync context."""
        if not self.web_server or not hasattr(self.web_server, "cache_manager"):
            logger.error("Web server or cache manager not available")
            return []

        web_server = self.web_server  # Store for type narrowing

        try:
            # Try to get the running event loop
            asyncio.get_running_loop()

            # If we're in an event loop, we can't use asyncio.run()
            def run_async_in_thread() -> Any:
                import asyncio  # noqa: PLC0415

                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        web_server.cache_manager.get_events_by_date_range(
                            start_datetime, end_datetime
                        )
                    )
                finally:
                    new_loop.close()

            return run_in_thread_pool(run_async_in_thread, timeout=5.0)

        except RuntimeError:
            # No running event loop, safe to use asyncio.run()
            return asyncio.run(
                web_server.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
            )

    def _filter_events(self, events: list[Any]) -> list[Any]:
        """Filter out hidden events based on settings."""
        if self.web_server and self.web_server.settings_service:
            filter_settings = self.web_server.settings_service.get_filter_settings()
            return [
                event for event in events if not filter_settings.is_event_hidden(event.graph_id)
            ]
        # Fallback if settings service not available
        return events

    def _create_and_send_view_model(
        self,
        filtered_events: list[Any],
        status_info: dict[str, Any],
        debug_time: Optional[datetime],
    ) -> None:
        """Create view model and send JSON response."""
        if not self.web_server:
            self._send_json_response(500, {"error": "Web server not available"})
            return

        # Use WhatsNextLogic to create the view model
        from ..display.whats_next_logic import WhatsNextLogic  # noqa: PLC0415

        whats_next_logic = WhatsNextLogic(self.web_server.settings)
        if debug_time:
            whats_next_logic.set_debug_time(debug_time)

        view_model = whats_next_logic.create_view_model(filtered_events, status_info)

        # Convert view model to dictionary for JSON serialization
        result = self._view_model_to_dict(view_model)

        # Return the data as JSON
        self._send_json_response(200, result)

    def _view_model_to_dict(self, view_model: "WhatsNextViewModel") -> dict[str, Any]:
        """Convert WhatsNextViewModel to dictionary for JSON serialization.

        Args:
            view_model: The view model to convert

        Returns:
            Dictionary representation of the view model
        """

        # Helper function to convert datetime to ISO format string with timezone info
        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            # Ensure timezone awareness - if naive, use system timezone
            if dt.tzinfo is None:
                from ..utils.helpers import ensure_timezone_aware  # noqa: PLC0415

                dt = ensure_timezone_aware(dt)
            return dt.isoformat()

        # Convert EventData objects to dictionaries
        def event_to_dict(event: "EventData") -> dict[str, Any]:
            return {
                "graph_id": event.graph_id,
                "title": event.subject,  # Frontend expects 'title' field
                "start_time": format_datetime(event.start_time),
                "end_time": format_datetime(event.end_time),
                "location": event.location,
                "is_current": event.is_current,
                "is_upcoming": event.is_upcoming,
                "time_until_minutes": event.time_until_minutes,
                "duration_minutes": event.duration_minutes,
                "formatted_time_range": event.formatted_time_range,
                "organizer": event.organizer,
                "attendees": event.attendees,
                # Include hidden status from settings
                "is_hidden": False,  # Simplified for now - can be enhanced later
            }

        # Convert StatusInfo to dictionary
        status_dict = {
            "last_update": format_datetime(view_model.status_info.last_update),
            "is_cached": view_model.status_info.is_cached,
            "connection_status": view_model.status_info.connection_status,
            "relative_description": view_model.status_info.relative_description,
            "interactive_mode": view_model.status_info.interactive_mode,
            "selected_date": view_model.status_info.selected_date,
        }

        # Build the complete result dictionary
        current_events_list = [event_to_dict(event) for event in view_model.current_events]
        next_events_list = [event_to_dict(event) for event in view_model.next_events]
        later_events_list = [event_to_dict(event) for event in view_model.later_events]

        result = {
            "layout_name": (
                self.web_server.get_current_layout()
                if self.web_server and hasattr(self.web_server, "get_current_layout")
                else "unknown"
            ),
            "current_time": format_datetime(view_model.current_time),
            "display_date": view_model.display_date,
            "current_events": current_events_list,
            "next_events": next_events_list,
            "later_events": later_events_list,
            # Flattened events array for frontend compatibility
            "events": current_events_list + next_events_list + later_events_list,
            "status_info": status_dict,
            "layout_config": {
                "show_hidden_events": False,  # Default value, could be made configurable
                "max_events": 8,  # Default value based on current implementation
                "time_format": "12h",  # Default value, could be made configurable
            },
        }

        # Add weather info if available
        if view_model.weather_info:
            result["weather_info"] = {
                "temperature": view_model.weather_info.temperature,
                "condition": view_model.weather_info.condition,
                "icon": view_model.weather_info.icon,
                "forecast": view_model.weather_info.forecast,
            }

        # Add settings data if available
        if view_model.settings_data:
            result["settings_data"] = {
                "theme": view_model.settings_data.theme,
                "layout": view_model.settings_data.layout,
                "refresh_interval": view_model.settings_data.refresh_interval,
                "display_type": view_model.settings_data.display_type,
                "custom_settings": view_model.settings_data.custom_settings,
            }

        return result

    def _get_updated_whats_next_data(self) -> dict[str, Any]:
        """Get updated whats-next data after event hiding/unhiding operations.

        Returns:
            Dictionary containing the updated event data in same format as /api/whats-next/data

        Raises:
            Exception: If unable to retrieve updated data
        """
        if not self.web_server:
            raise WebServerError("Web server not available")

        # Get the current layout to determine data retrieval approach
        current_layout = self.web_server.get_current_layout()

        # Calculate date range - use 7 days for whats-next-view, 1 day for others
        days = 7 if current_layout == "whats-next-view" else 1

        # Get events for the specified time period
        if self.web_server.navigation_state:
            # Interactive mode - get events for selected date
            selected_date = self.web_server.navigation_state.selected_date
            start_datetime = datetime.combine(selected_date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=days)

            # Build status info for interactive mode
            from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

            status_info = {
                "selected_date": self.web_server.navigation_state.get_display_date(),
                "is_today": self.web_server.navigation_state.is_today(),
                "interactive_mode": True,
                "last_update": get_timezone_aware_now().isoformat(),
                "is_cached": False,
            }
        else:
            # Non-interactive mode - get today's events
            today = date.today()
            start_datetime = datetime.combine(today, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=days)

            # Static web display mode - no navigation buttons
            from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

            status_info = {
                "last_update": get_timezone_aware_now().isoformat(),
                "is_cached": False,
                "interactive_mode": False,
            }

        # Check if web_server is available
        if not self.web_server or not hasattr(self.web_server, "cache_manager"):
            logger.error("Web server or cache manager not available")
            events = []
        else:
            web_server = self.web_server  # Store for type narrowing
            # Get events using async call handling
            try:
                # Try to get the running event loop
                loop = asyncio.get_running_loop()  # noqa: F841

                # If we're in an event loop, we can't use asyncio.run()
                def run_async_in_thread() -> Any:
                    import asyncio  # noqa: PLC0415

                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            web_server.cache_manager.get_events_by_date_range(
                                start_datetime, end_datetime
                            )
                        )
                    finally:
                        new_loop.close()

                events = run_in_thread_pool(run_async_in_thread, timeout=5.0)

            except RuntimeError:
                # No running event loop, safe to use asyncio.run()
                events = asyncio.run(
                    web_server.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
                )

        # DIAGNOSTIC: Track TENTATIVE events through web server pipeline
        tentative_before_settings = len(
            [e for e in events if hasattr(e, "show_as") and str(e.show_as).upper() == "TENTATIVE"]
        )
        logger.info(
            f"DEBUG WEB SERVER: TENTATIVE events received from cache: {tentative_before_settings}"
        )
        logger.info(f"DEBUG WEB SERVER: Total events received from cache: {len(events)}")

        # Filter out hidden events before creating view model
        if self.web_server and self.web_server.settings_service:
            filter_settings = self.web_server.settings_service.get_filter_settings()
            filtered_events = [
                event for event in events if not filter_settings.is_event_hidden(event.graph_id)
            ]
            tentative_after_settings = len(
                [
                    e
                    for e in filtered_events
                    if hasattr(e, "show_as") and str(e.show_as).upper() == "TENTATIVE"
                ]
            )
            logger.info(
                f"DEBUG WEB SERVER: TENTATIVE events after settings filtering: {tentative_after_settings}"
            )
            logger.info(
                f"DEBUG WEB SERVER: Total events after settings filtering: {len(filtered_events)}"
            )
        else:
            # Fallback if settings service not available
            filtered_events = events
            logger.info("DEBUG WEB SERVER: No settings service - using all events")

        # Use WhatsNextLogic to create the view model
        from ..display.whats_next_logic import WhatsNextLogic  # noqa: PLC0415

        whats_next_logic = WhatsNextLogic(self.web_server.settings)
        view_model = whats_next_logic.create_view_model(filtered_events, status_info)

        # Convert view model to dictionary for JSON serialization
        return self._view_model_to_dict(view_model)

    def _handle_health_check(self) -> None:
        """Handle health check requests for monitoring and smoke tests."""
        try:
            # Simple health check - if we can respond, we're healthy
            health_data = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "service": "calendarbot-web",
            }
            self._send_json_response(200, health_data)
        except Exception as e:
            logger.exception("Error handling health check")
            self._send_json_response(500, {"status": "error", "error": str(e)})

    def _handle_status_api(self) -> None:
        """Handle status API requests."""
        if not self.web_server:
            self._send_json_response(500, {"error": "Web server not available"})
            return

        status = self.web_server.get_status()
        self._send_json_response(200, status)

    def _handle_settings_api(
        self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle settings API requests with comprehensive endpoint support.

        Args:
            path: API endpoint path
            params: Request parameters (query params for GET, JSON data for POST/PUT)
        """
        try:
            if not self.web_server or not self.web_server.settings_service:
                self._send_json_response(
                    503,
                    {
                        "error": "Settings service not available",
                        "message": "Settings functionality is currently unavailable",
                    },
                )
                return

            settings_service = self.web_server.settings_service
            method = self.command

            # Settings API routing table
            route_handlers = {
                "/api/settings": {
                    "GET": lambda: self._handle_get_settings(settings_service),
                    "PUT": lambda: self._handle_update_settings(settings_service, params),
                },
                "/api/settings/filters": {
                    "GET": lambda: self._handle_get_filter_settings(settings_service),
                    "PUT": lambda: self._handle_update_filter_settings(settings_service, params),
                },
                "/api/settings/display": {
                    "GET": lambda: self._handle_get_display_settings(settings_service),
                    "PUT": lambda: self._handle_update_display_settings(settings_service, params),
                },
                "/api/settings/conflicts": {
                    "GET": lambda: self._handle_get_conflict_settings(settings_service),
                    "PUT": lambda: self._handle_update_conflict_settings(settings_service, params),
                },
                "/api/settings/validate": {
                    "POST": lambda: self._handle_validate_settings(settings_service, params),
                },
                "/api/settings/export": {
                    "GET": lambda: self._handle_export_settings(settings_service),
                },
                "/api/settings/import": {
                    "POST": lambda: self._handle_import_settings(settings_service, params),
                },
                "/api/settings/reset": {
                    "POST": lambda: self._handle_reset_settings(settings_service),
                },
                "/api/settings/info": {
                    "GET": lambda: self._handle_get_settings_info(settings_service),
                },
                "/api/settings/filters/patterns": {
                    "POST": lambda: self._handle_add_filter_pattern(settings_service, params),
                    "DELETE": lambda: self._handle_remove_filter_pattern(settings_service, params),
                },
                "/api/events/hide": {
                    "POST": lambda: self._handle_hide_event(settings_service, params),
                },
                "/api/events/unhide": {
                    "POST": lambda: self._handle_unhide_event(settings_service, params),
                },
                "/api/events/hidden": {
                    "GET": lambda: self._handle_get_hidden_events(settings_service),
                },
            }

            # Route request using lookup table
            if path in route_handlers and method in route_handlers[path]:
                route_handlers[path][method]()
            elif path in route_handlers:
                self._send_json_response(405, {"error": "Method not allowed"})
            else:
                self._send_json_response(404, {"error": "Settings API endpoint not found"})

        except Exception as e:
            logger.exception("Error handling settings API request")
            self._send_json_response(500, {"error": str(e)})

    def _handle_get_settings(self, settings_service: SettingsService) -> None:
        """Handle GET /api/settings - get complete settings."""
        try:
            settings = settings_service.get_settings()
            self._send_json_response(200, {"success": True, "data": settings.to_api_dict()})
        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to get settings", "message": str(e)})

    def _handle_update_settings(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle PUT /api/settings - update complete settings."""
        try:
            # Validate that params is a dictionary and not empty
            if not params or not isinstance(params, dict):
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            from ..settings.models import SettingsData  # noqa: PLC0415

            # For PUT requests, params comes from JSON data, so it should be Dict[str, Any]
            json_params = cast(dict[str, Any], params)
            settings = SettingsData(**json_params)
            updated_settings = settings_service.update_settings(settings)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Settings updated successfully",
                    "data": updated_settings.to_api_dict(),
                },
            )
        except SettingsValidationError as e:
            self._send_json_response(
                400,
                {
                    "error": "Settings validation failed",
                    "message": str(e),
                    "validation_errors": e.validation_errors,
                },
            )
        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to update settings", "message": str(e)})

    def _handle_get_filter_settings(self, settings_service: SettingsService) -> None:
        """Handle GET /api/settings/filters - get filter settings."""
        try:
            filters = settings_service.get_filter_settings()
            self._send_json_response(200, {"success": True, "data": filters.model_dump()})
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to get filter settings", "message": str(e)}
            )

    def _handle_update_filter_settings(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle PUT /api/settings/filters - update filter settings."""
        try:
            # params is always a dict due to Union[Dict[str, List[str]], Dict[str, Any]]
            # Validate that params contains the expected structure for filter settings update
            if not params:
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            from ..settings.models import EventFilterSettings  # noqa: PLC0415

            # For PUT requests, params comes from JSON data, so it should be Dict[str, Any]
            json_params = cast(dict[str, Any], params)
            filter_settings = EventFilterSettings(**json_params)
            updated_filters = settings_service.update_filter_settings(filter_settings)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Filter settings updated successfully",
                    "data": updated_filters.model_dump(),
                },
            )
        except SettingsValidationError as e:
            self._send_json_response(
                400, {"error": "Filter settings validation failed", "message": str(e)}
            )
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to update filter settings", "message": str(e)}
            )

    def _handle_get_display_settings(self, settings_service: SettingsService) -> None:
        """Handle GET /api/settings/display - get display settings."""
        try:
            display = settings_service.get_display_settings()
            self._send_json_response(200, {"success": True, "data": display.model_dump()})
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to get display settings", "message": str(e)}
            )

    def _handle_update_display_settings(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle PUT /api/settings/display - update display settings."""
        try:
            # params is always a dict due to Union[Dict[str, List[str]], Dict[str, Any]]
            # Validate that params contains the expected structure for display settings update
            if not params:
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            from ..settings.models import DisplaySettings  # noqa: PLC0415

            # For PUT requests, params comes from JSON data, so it should be Dict[str, Any]
            json_params = cast(dict[str, Any], params)
            display_settings = DisplaySettings(**json_params)
            updated_display = settings_service.update_display_settings(display_settings)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Display settings updated successfully",
                    "data": updated_display.model_dump(),
                },
            )
        except SettingsValidationError as e:
            self._send_json_response(
                400, {"error": "Display settings validation failed", "message": str(e)}
            )
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to update display settings", "message": str(e)}
            )

    def _handle_get_conflict_settings(self, settings_service: SettingsService) -> None:
        """Handle GET /api/settings/conflicts - get conflict resolution settings."""
        try:
            conflicts = settings_service.get_conflict_settings()
            self._send_json_response(200, {"success": True, "data": conflicts.model_dump()})
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to get conflict settings", "message": str(e)}
            )

    def _handle_update_conflict_settings(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle PUT /api/settings/conflicts - update conflict resolution settings."""
        try:
            # params is always a dict due to Union[Dict[str, List[str]], Dict[str, Any]]
            # Validate that params contains the expected structure for conflict settings update
            if not params:
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            from ..settings.models import ConflictResolutionSettings  # noqa: PLC0415

            # For PUT requests, params comes from JSON data, so it should be Dict[str, Any]
            json_params = cast(dict[str, Any], params)
            conflict_settings = ConflictResolutionSettings(**json_params)
            updated_conflicts = settings_service.update_conflict_settings(conflict_settings)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Conflict settings updated successfully",
                    "data": updated_conflicts.model_dump(),
                },
            )
        except SettingsValidationError as e:
            self._send_json_response(
                400, {"error": "Conflict settings validation failed", "message": str(e)}
            )
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to update conflict settings", "message": str(e)}
            )

    def _handle_validate_settings(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle POST /api/settings/validate - validate settings data."""
        try:
            # Validate that params is a dictionary and not empty
            if not params or not isinstance(params, dict):
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            from ..settings.models import SettingsData  # noqa: PLC0415

            # For POST requests, params comes from JSON data, so it should be Dict[str, Any]
            json_params = cast(dict[str, Any], params)
            settings = SettingsData(**json_params)
            validation_errors = settings_service.validate_settings(settings)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "valid": len(validation_errors) == 0,
                    "validation_errors": validation_errors,
                },
            )
        except Exception as e:
            self._send_json_response(
                400, {"error": "Settings validation failed", "message": str(e)}
            )

    def _handle_export_settings(self, settings_service: SettingsService) -> None:
        """Handle GET /api/settings/export - export settings."""
        try:
            settings = settings_service.get_settings()

            # Return settings as downloadable JSON
            json_content = json.dumps(settings.to_api_dict(), indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header(
                "Content-Disposition", "attachment; filename=calendarbot_settings.json"
            )
            self.send_header("Content-Length", str(len(json_content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(json_content.encode("utf-8"))

        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to export settings", "message": str(e)})

    def _handle_import_settings(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle POST /api/settings/import - import settings."""
        try:
            # Validate that params is a dictionary and not empty
            if not params or not isinstance(params, dict):
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            from ..settings.models import SettingsData  # noqa: PLC0415

            # For POST requests, params comes from JSON data, so it should be Dict[str, Any]
            json_params = cast(dict[str, Any], params)
            settings = SettingsData(**json_params)
            imported_settings = settings_service.update_settings(settings)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Settings imported successfully",
                    "data": imported_settings.to_api_dict(),
                },
            )
        except SettingsValidationError as e:
            self._send_json_response(
                400, {"error": "Settings import validation failed", "message": str(e)}
            )
        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to import settings", "message": str(e)})

    def _handle_reset_settings(self, settings_service: SettingsService) -> None:
        """Handle POST /api/settings/reset - reset settings to defaults."""
        try:
            reset_settings = settings_service.reset_to_defaults()

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Settings reset to defaults successfully",
                    "data": reset_settings.to_api_dict(),
                },
            )
        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to reset settings", "message": str(e)})

    def _handle_get_settings_info(self, settings_service: SettingsService) -> None:
        """Handle GET /api/settings/info - get settings information and statistics."""
        try:
            info = settings_service.get_settings_info()

            self._send_json_response(200, {"success": True, "data": info})
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to get settings info", "message": str(e)}
            )

    def _handle_add_filter_pattern(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle POST /api/settings/filters/patterns - add a new filter pattern."""
        try:
            # Validate that params is a dictionary and not empty
            if not params or not isinstance(params, dict):
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            pattern = params.get("pattern", "")
            is_regex = params.get("is_regex", False)
            case_sensitive = params.get("case_sensitive", False)
            description = params.get("description")

            if not pattern:
                self._send_json_response(400, {"error": "Pattern is required"})
                return

            # Ensure proper types for add_filter_pattern call
            pattern_str = str(pattern) if pattern else ""
            is_regex_bool = bool(is_regex)
            case_sensitive_bool = bool(case_sensitive)
            description_str = str(description) if description else None

            filter_pattern = settings_service.add_filter_pattern(
                pattern_str, is_regex_bool, case_sensitive_bool, description_str
            )

            self._send_json_response(
                200,
                {
                    "success": True,
                    "message": "Filter pattern added successfully",
                    "data": filter_pattern.model_dump(),
                },
            )
        except SettingsValidationError as e:
            self._send_json_response(
                400, {"error": "Filter pattern validation failed", "message": str(e)}
            )
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to add filter pattern", "message": str(e)}
            )

    def _handle_remove_filter_pattern(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle DELETE /api/settings/filters/patterns - remove a filter pattern."""
        try:
            # For DELETE requests, params might be in query string format
            if isinstance(params, dict) and "pattern" in params:
                pattern_value = params["pattern"]
                pattern = (
                    pattern_value[0] if isinstance(pattern_value, list) else str(pattern_value)
                )

                is_regex_value = params.get("is_regex", ["false"])
                is_regex = (
                    is_regex_value[0] if isinstance(is_regex_value, list) else str(is_regex_value)
                ).lower() == "true"
            else:
                self._send_json_response(400, {"error": "Pattern parameter is required"})
                return

            success = settings_service.remove_filter_pattern(pattern, is_regex)

            if success:
                self._send_json_response(
                    200, {"success": True, "message": "Filter pattern removed successfully"}
                )
            else:
                self._send_json_response(404, {"error": "Filter pattern not found"})
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to remove filter pattern", "message": str(e)}
            )

    def _handle_hide_event(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle POST /api/events/hide - hide a specific event."""
        try:
            # Check for missing graph_id first, before validating params structure
            graph_id = params.get("graph_id", "") if isinstance(params, dict) else ""
            if not graph_id:
                self._send_json_response(400, {"error": "Missing graph_id"})
                return

            # Get current filter settings
            filter_settings = settings_service.get_filter_settings()
            logger.debug(f"Before hiding - hidden_events: {list(filter_settings.hidden_events)}")

            # Hide the event
            filter_settings.hide_event(str(graph_id))
            logger.debug(
                f"After hide_event() - hidden_events: {list(filter_settings.hidden_events)}"
            )

            # Update filter settings
            updated_settings = settings_service.update_filter_settings(filter_settings)
            logger.debug(
                f"After update_filter_settings() - hidden_events: {list(updated_settings.hidden_events)}"
            )

            # Get updated count
            hidden_count = len(filter_settings.hidden_events)
            logger.info(
                f"Event {graph_id} hidden successfully. Total hidden events: {hidden_count}"
            )

            # Get updated event data after hiding
            try:
                updated_data = self._get_updated_whats_next_data()
                response_data = {
                    "success": True,
                    "message": "Event hidden successfully",
                    "count": hidden_count,
                    "data": updated_data,
                }
            except Exception as data_error:
                logger.warning(f"Failed to get updated data after hiding event: {data_error}")
                # Fallback to original response format
                response_data = {
                    "success": True,
                    "message": "Event hidden successfully",
                    "count": hidden_count,
                    "data": {"graph_id": str(graph_id), "hidden": True},
                }

            self._send_json_response(200, response_data)
        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to hide event", "message": str(e)})

    def _handle_unhide_event(
        self, settings_service: SettingsService, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle POST /api/events/unhide - unhide a specific event."""
        try:
            # Check for missing graph_id first, before validating params structure
            graph_id = params.get("graph_id", "") if isinstance(params, dict) else ""
            if not graph_id:
                self._send_json_response(400, {"error": "Missing graph_id"})
                return

            # Get current filter settings
            filter_settings = settings_service.get_filter_settings()

            # Unhide the event
            was_hidden = filter_settings.unhide_event(str(graph_id))

            # Update filter settings
            settings_service.update_filter_settings(filter_settings)

            # Get updated count
            hidden_count = len(filter_settings.hidden_events)

            # Get updated event data after unhiding
            try:
                updated_data = self._get_updated_whats_next_data()
                response_data = {
                    "success": True,
                    "message": "Event unhidden successfully"
                    if was_hidden
                    else "Event was not hidden",
                    "count": hidden_count,
                    "data": updated_data,
                }
            except Exception as data_error:
                logger.warning(f"Failed to get updated data after unhiding event: {data_error}")
                # Fallback to original response format
                response_data = {
                    "success": True,
                    "message": "Event unhidden successfully"
                    if was_hidden
                    else "Event was not hidden",
                    "count": hidden_count,
                    "data": {"graph_id": str(graph_id), "hidden": False, "was_hidden": was_hidden},
                }

            self._send_json_response(200, response_data)
        except SettingsError as e:
            self._send_json_response(500, {"error": "Failed to unhide event", "message": str(e)})

    def _handle_get_hidden_events(self, settings_service: SettingsService) -> None:
        """Handle GET /api/events/hidden - get list of hidden events."""
        try:
            filter_settings = settings_service.get_filter_settings()
            hidden_events = list(filter_settings.hidden_events)

            self._send_json_response(
                200,
                {"success": True, "hidden_events": hidden_events, "count": len(hidden_events)},
            )
        except SettingsError as e:
            self._send_json_response(
                500, {"error": "Failed to get hidden events", "message": str(e)}
            )

    def _handle_database_api(
        self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle database API requests with comprehensive endpoint support.

        Args:
            path: API endpoint path
            params: Request parameters (query params for GET, JSON data for POST)
        """
        try:
            if not self.web_server or not hasattr(self.web_server, "cache_manager"):
                self._send_json_response(
                    503,
                    {
                        "error": "Database service not available",
                        "message": "Database functionality is currently unavailable",
                    },
                )
                return

            method = self.command

            # Database API routing table
            route_handlers = {
                "/api/database/query": {
                    "POST": lambda: self._handle_database_query(params),
                },
                "/api/database/schema": {
                    "GET": lambda: self._handle_database_schema(),
                },
                "/api/database/tables": {
                    "GET": lambda: self._handle_database_tables(),
                },
                "/api/database/info": {
                    "GET": lambda: self._handle_database_info(),
                },
            }

            # Route request using lookup table
            if path in route_handlers and method in route_handlers[path]:
                route_handlers[path][method]()
            elif path in route_handlers:
                self._send_json_response(405, {"error": "Method not allowed"})
            else:
                self._send_json_response(404, {"error": "Database API endpoint not found"})

        except Exception as e:
            logger.exception("Error handling database API request")
            self._send_json_response(500, {"error": str(e)})

    def _handle_database_query(self, params: Union[dict[str, list[str]], dict[str, Any]]) -> None:
        """Handle POST /api/database/query - execute SQL query safely."""
        try:
            # Validate that params is a dictionary and contains query
            if not params or not isinstance(params, dict):
                self._send_json_response(400, {"error": "Invalid request data"})
                return

            from typing import cast  # noqa: PLC0415

            # For POST requests, params comes from JSON data
            json_params = cast(dict[str, Any], params)
            query = json_params.get("query", "").strip()

            if not query:
                self._send_json_response(400, {"error": "Query parameter is required"})
                return

            # Security validation - only allow SELECT statements and schema queries
            if not self._is_safe_query(query):
                self.security_logger.log_input_validation_failure(
                    input_type="sql_query",
                    validation_error="Unsafe SQL query attempted",
                    details={
                        "source_ip": self.client_address[0] if self.client_address else "unknown",
                        "query": query[:100],  # Log first 100 chars for debugging
                        "endpoint": "/api/database/query",
                    },
                )
                self._send_json_response(
                    403,
                    {
                        "error": "Query not allowed",
                        "message": "Only SELECT and schema queries are permitted",
                    },
                )
                return

            # Execute query using database manager
            results = self._execute_safe_query(query)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "data": results,
                    "query": query,
                },
            )

        except Exception as e:
            logger.exception("Error executing database query")
            self._send_json_response(500, {"error": f"Query execution failed: {e!s}"})

    def _is_safe_query(self, query: str) -> bool:
        """Validate that the SQL query is safe to execute.

        Args:
            query: SQL query string to validate

        Returns:
            True if query is safe, False otherwise
        """
        query_upper = query.upper().strip()

        # Allow only specific safe operations
        safe_prefixes = [
            "SELECT",
            "PRAGMA TABLE_INFO",
            "PRAGMA TABLE_LIST",
            "PRAGMA INDEX_LIST",
            "PRAGMA FOREIGN_KEY_LIST",
            ".SCHEMA",
            ".TABLES",
        ]

        # Check if query starts with safe prefix
        for prefix in safe_prefixes:
            if query_upper.startswith(prefix):
                break
        else:
            return False

        # Block dangerous keywords
        dangerous_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "REPLACE",
            "EXEC",
            "EXECUTE",
            "DECLARE",
            "SCRIPT",
            "SHUTDOWN",
            "BACKUP",
            "RESTORE",
        ]

        return all(keyword not in query_upper for keyword in dangerous_keywords)

    def _execute_safe_query(self, query: str) -> dict[str, Any]:
        """Execute a validated SQL query safely.

        Args:
            query: Validated SQL query string

        Returns:
            Dictionary containing query results
        """
        if not self.web_server or not hasattr(self.web_server, "cache_manager"):
            raise WebServerError("Database manager not available")

        # Get database path from cache manager
        db_manager = self.web_server.cache_manager.db
        db_path = db_manager.database_path

        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)

                # Fetch results
                rows = cursor.fetchall()

                # Convert to list of dictionaries
                results = [dict(row) for row in rows]

                return {
                    "rows": results,
                    "count": len(results),
                    "columns": [desc[0] for desc in cursor.description]
                    if cursor.description
                    else [],
                }

        except sqlite3.Error as e:
            raise WebServerError(f"Database query failed: {e!s}") from e

    def _handle_database_schema(self) -> None:
        """Handle GET /api/database/schema - get database schema information."""
        try:
            schema_query = """
                SELECT
                    name,
                    type,
                    sql
                FROM sqlite_master
                WHERE type IN ('table', 'index', 'view')
                ORDER BY type, name
            """

            results = self._execute_safe_query(schema_query)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "data": results,
                },
            )

        except Exception as e:
            logger.exception("Error getting database schema")
            self._send_json_response(500, {"error": f"Failed to get schema: {e!s}"})

    def _handle_database_tables(self) -> None:
        """Handle GET /api/database/tables - get list of database tables."""
        try:
            tables_query = """
                SELECT
                    name,
                    type,
                    sql
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
            """

            results = self._execute_safe_query(tables_query)

            self._send_json_response(
                200,
                {
                    "success": True,
                    "data": results,
                },
            )

        except Exception as e:
            logger.exception("Error getting database tables")
            self._send_json_response(500, {"error": f"Failed to get tables: {e!s}"})

    def _handle_database_info(self) -> None:
        """Handle GET /api/database/info - get database information and statistics."""
        try:
            if not self.web_server or not hasattr(self.web_server, "cache_manager"):
                self._send_json_response(500, {"error": "Database manager not available"})
                return

            # Get database info from cache manager
            db_manager = self.web_server.cache_manager.db

            # Use async call handling similar to other methods
            try:
                # Try to get the running event loop
                asyncio.get_running_loop()

                def run_async_in_thread() -> Any:
                    import asyncio  # noqa: PLC0415

                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(db_manager.get_database_info())
                    finally:
                        new_loop.close()

                db_info = run_in_thread_pool(run_async_in_thread, timeout=5.0)

            except RuntimeError:
                # No running event loop, safe to use asyncio.run()
                db_info = asyncio.run(db_manager.get_database_info())

            self._send_json_response(
                200,
                {
                    "success": True,
                    "data": db_info,
                },
            )

        except Exception as e:
            logger.exception("Error getting database info")
            self._send_json_response(500, {"error": f"Failed to get database info: {e!s}"})

    def _generate_etag(self, file_path: Path) -> str:
        """Generate ETag for file based on path and modification time.

        Args:
            file_path: Path to the file

        Returns:
            ETag string for cache validation
        """
        try:
            stat_info = file_path.stat()
            etag_data = f"{file_path}{stat_info.st_mtime}{stat_info.st_size}"
            return hashlib.md5(
                etag_data.encode(), usedforsecurity=False
            ).hexdigest()  # Used for ETag generation, not security
        except Exception:
            # Fallback to path-only hash if stat fails
            return hashlib.md5(
                str(file_path).encode(), usedforsecurity=False
            ).hexdigest()  # Used for ETag generation, not security

    def _serve_static_file(self, path: str) -> None:  # noqa: PLR0912, PLR0915
        """Serve static files (CSS, JS, etc.)."""
        try:
            # Remove /static/ prefix
            file_path = path[8:]  # Remove '/static/'

            # Production asset filtering - check if asset should be excluded
            if should_exclude_asset(file_path):
                # DEBUG: Add comprehensive logging for asset exclusion diagnosis
                prod_mode = is_production_mode()
                is_debug = is_debug_asset(file_path)
                exclusion_info = get_asset_exclusion_info()

                logger.warning(f"ASSET_EXCLUSION: Blocking {file_path}")
                logger.warning(f"ASSET_EXCLUSION: Production mode = {prod_mode}")
                logger.warning(f"ASSET_EXCLUSION: Is debug asset = {is_debug}")
                logger.warning(f"ASSET_EXCLUSION: Environment = {exclusion_info['environment']}")
                logger.warning(
                    "ASSET_EXCLUSION: This may be incorrectly excluding essential files!"
                )

                self._send_404()
                return

            # Use static asset cache for O(1) path resolution (eliminates triple filesystem lookup)
            full_path = None

            # DEBUG: Add comprehensive path tracing
            logger.debug(f"STATIC_FILE_DEBUG: Processing request for file_path='{file_path}'")

            if (
                self.web_server
                and hasattr(self.web_server, "asset_cache")
                and self.web_server.asset_cache.is_cache_built()
            ):
                # Extract layout context if this is a layout-specific request
                layout_name = None
                cache_file_path = file_path  # Preserve original for fallback

                logger.debug("STATIC_FILE_DEBUG: Asset cache is available and built")

                if file_path.startswith("layouts/") and "/" in file_path[8:]:
                    # Extract layout name from "layouts/whats-next-view/whats-next-view.css" -> layout_name="whats-next-view"
                    layout_path_parts = file_path[8:].split("/", 1)
                    logger.debug(
                        f"STATIC_FILE_DEBUG: Layout path parsing - file_path[8:]='{file_path[8:]}', parts={layout_path_parts}"
                    )
                    if len(layout_path_parts) >= 2:
                        layout_name = layout_path_parts[0]
                        cache_file_path = layout_path_parts[1]  # Use the actual filename for cache
                        logger.debug(
                            f"STATIC_FILE_DEBUG: Extracted layout_name='{layout_name}', cache_file_path='{cache_file_path}'"
                        )

                # Resolve asset path using cache (O(1) operation)
                full_path = self.web_server.asset_cache.resolve_asset_path(
                    cache_file_path, layout_name
                )

                logger.debug(f"STATIC_FILE_DEBUG: Asset cache result - full_path={full_path}")

                if full_path:
                    # Security validation - ensure resolved path is within allowed directories
                    resolved_str = str(full_path.resolve())
                    layouts_dir = Path(__file__).parent.parent / "layouts"
                    static_dir = Path(__file__).parent / "static"

                    allowed_dirs = [str(layouts_dir.resolve()), str(static_dir.resolve())]
                    logger.debug(
                        f"STATIC_FILE_DEBUG: Security check - resolved_str='{resolved_str}', allowed_dirs={allowed_dirs}"
                    )
                    if not any(
                        resolved_str.startswith(allowed_dir) for allowed_dir in allowed_dirs
                    ):
                        logger.warning(
                            f"Asset cache returned path outside allowed directories: {full_path}"
                        )
                        full_path = None
                    else:
                        logger.debug(
                            f"STATIC_FILE_DEBUG: Security check passed, serving cached file: {full_path}"
                        )
                else:
                    logger.debug(
                        f"STATIC_FILE_DEBUG: Asset cache returned None for cache_file_path='{cache_file_path}', layout_name='{layout_name}'"
                    )
            else:
                logger.warning("Asset cache not built, falling back to filesystem lookup")
                # Fallback to original triple lookup pattern if cache failed to build
                # First check if this is a layout directory path (e.g., layouts/4x8/4x8.css)
                if file_path.startswith("layouts/"):
                    # Handle layout directory paths directly
                    layouts_dir = Path(__file__).parent.parent / "layouts"
                    layout_file_path = file_path[8:]  # Remove 'layouts/' prefix
                    layout_path = layouts_dir / layout_file_path

                    # Security check - ensure file exists, is a file, and is within layouts directory
                    if (
                        layout_path.exists()
                        and layout_path.is_file()
                        and str(layout_path.resolve()).startswith(str(layouts_dir.resolve()))
                    ):
                        full_path = layout_path

                # If not found in layouts, try the legacy static directory (web/static)
                if not full_path:
                    static_dir = Path(__file__).parent / "static"
                    legacy_path = static_dir / file_path

                    # Security check - ensure file exists, is a file, and is within static directory
                    if (
                        legacy_path.exists()
                        and legacy_path.is_file()
                        and str(legacy_path.resolve()).startswith(str(static_dir.resolve()))
                    ):
                        full_path = legacy_path

                # If not found in legacy, try the layout directories with filename matching
                if not full_path:
                    layouts_dir = Path(__file__).parent / "static" / "layouts"

                    # Check if file matches layout pattern (e.g., "4x8.css" -> "layouts/4x8/4x8.css")
                    if "." in file_path:
                        name_part = file_path.split(".")[0]  # e.g., "4x8" from "4x8.css"
                        layout_path = layouts_dir / name_part / file_path

                        # Security check - ensure file exists, is a file, and is within layouts directory
                        if (
                            layout_path.exists()
                            and layout_path.is_file()
                            and str(layout_path.resolve()).startswith(str(layouts_dir.resolve()))
                        ):
                            full_path = layout_path

            if full_path and full_path.exists() and full_path.is_file():
                # Determine content type
                content_type, _ = mimetypes.guess_type(str(full_path))
                if not content_type:
                    content_type = "text/plain"

                # Read and serve file
                with full_path.open("rb") as f:
                    content = f.read()

                # Send binary response directly
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "max-age=3600, public")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                logger.warning(f"STATIC_FILE_REQUEST: File not found: {file_path}")
                self._send_404()

        except Exception as e:
            logger.exception(f"Error serving static file {path}")
            self._send_500(str(e))

    def _send_response(
        self, status_code: int, content: Union[str, bytes], content_type: str, _binary: bool = False
    ) -> None:
        """Send HTTP response."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "max-age=3600, public")

        content_bytes = content.encode("utf-8") if isinstance(content, str) else content

        self.send_header("Content-Length", str(len(content_bytes)))
        self.end_headers()

        self.wfile.write(content_bytes)

    def _send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        """Send JSON response."""
        json_content = json.dumps(data, indent=2)
        self._send_response(status_code, json_content, "application/json")

    def _send_404(self) -> None:
        """Send 404 Not Found response."""
        self._send_response(404, "404 Not Found", "text/plain")

    def _send_500(self, error_message: str) -> None:
        """Send 500 Internal Server Error response."""
        self._send_response(500, f"500 Internal Server Error: {error_message}", "text/plain")

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger."""
        logger.debug(f"HTTP {format % args}")


class WebServer:
    """Simple web server for calendar HTML interface."""

    def __init__(
        self,
        settings: Any,
        display_manager: Any,
        cache_manager: Any,
        navigation_state: Optional[Any] = None,
        layout_registry: Optional[LayoutRegistry] = None,
        resource_manager: Optional[ResourceManager] = None,
    ) -> None:
        """Initialize web server with all required components and configuration.

        Sets up the HTTP server for serving the calendar web interface, configures
        request handlers, and establishes connections to display and cache management
        systems. The web server supports both interactive and static display modes.

        Args:
            settings: Application settings object containing web server configuration.
                     Must include web_host (str), web_port (int), web_theme (str),
                     and auto_kill_existing (bool) attributes for proper operation.
            display_manager: Display manager instance responsible for rendering calendar
                           content into HTML. Must implement get_calendar_html() and
                           set_display_type() methods for layout switching functionality.
            cache_manager: Cache manager instance for event data storage and retrieval.
                          Must implement async get_events_by_date_range() method for
                          fetching cached events within specified datetime ranges.
            navigation_state: Optional navigation state manager for interactive mode.
                            When provided, enables date navigation controls and maintains
                            selected_date state. Required for interactive calendar browsing.
            layout_registry: Optional layout registry for dynamic layout discovery.
                           If not provided, a default registry will be created automatically.
            resource_manager: Optional resource manager for dynamic CSS/JS loading.
                            If not provided, a manager will be created using the layout registry.

        Raises:
            AttributeError: If required settings attributes are missing
            TypeError: If managers don't implement required interface methods

        Note:
            The server is not started automatically. Call start() method after
            initialization to begin accepting HTTP requests.
        """
        self.settings = settings
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.navigation_state = navigation_state

        # Initialize layout management system - use lazy loading for performance
        self.layout_registry = layout_registry or LazyLayoutRegistry()
        self.resource_manager = resource_manager or ResourceManager(
            self.layout_registry, settings=self.settings
        )

        # Initialize settings service
        try:
            self.settings_service: Optional[SettingsService] = SettingsService(settings)
            logger.debug("Settings service initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize settings service: {e}")
            self.settings_service = None

        # Server configuration
        self.host = settings.web_host
        self.port = settings.web_port
        self.layout = settings.web_layout

        # Server instance
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[Thread] = None
        self.running = False

        logger.info(f"Web server initialized on {self.host}:{self.port}")
        logger.debug(
            f"Layout registry initialized with {len(self.layout_registry.get_available_layouts())} available layouts"
        )
        # Initialize static file cache for performance optimization
        self.static_cache = StaticFileCache()

        # Initialize static asset cache to eliminate triple filesystem lookups
        static_dirs = [Path(__file__).parent / "static"]  # Legacy web/static directory
        layouts_dir = Path(__file__).parent / "static" / "layouts"  # Correct path to layout files
        self.asset_cache = StaticAssetCache(static_dirs, layouts_dir)

        # Build cache at startup for O(1) path resolution
        logger.info("Building static asset cache for performance optimization...")
        self.asset_cache.build_cache()

        # Initialize connection manager for HTTP client pooling
        self.connection_manager = None
        logger.debug("ConnectionManager will be initialized during server startup")

    def start(self) -> None:
        """Start the web server."""
        if self.running:
            logger.warning("Web server already running")
            return

        try:
            # Automatically clean up any conflicting processes before starting (if configured)
            if self.settings.auto_kill_existing:
                logger.debug(
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
            def handler(*args: Any, **kwargs: Any) -> WebRequestHandler:
                return WebRequestHandler(*args, web_server=self, **kwargs)

            # Create and start server with improved configuration
            self.server = HTTPServer((self.host, self.port), handler)

            # Configure server for faster shutdown
            self.server.timeout = 1.0  # Shorter timeout for request handling

            # Use non-daemon thread to avoid abrupt termination issues
            self.server_thread = Thread(target=self._serve_with_cleanup, daemon=False)
            self.server_thread.start()

            # Initialize connection manager for HTTP client pooling
            try:
                self.connection_manager = get_connection_manager()
                logger.info("ConnectionManager initialized for HTTP client pooling")
            except Exception as e:
                logger.warning(f"Failed to initialize ConnectionManager: {e}")
                self.connection_manager = None

            self.running = True
            logger.info(f"Web server started on http://{self.host}:{self.port}")

        except Exception:
            logger.exception("Failed to start web server")
            raise

    def _serve_with_cleanup(self) -> None:
        """Serve requests with proper cleanup handling."""
        try:
            logger.debug("Server thread started, beginning serve_forever()")
            if self.server:
                self.server.serve_forever()
            logger.debug("serve_forever() completed normally")
        except Exception as e:
            if self.running:  # Only log if we didn't expect this
                logger.warning(f"Server thread ended with exception: {e}")
        finally:
            logger.debug("Server thread cleanup completed")

    def stop(self) -> None:  # noqa
        """Stop the web server with proper shutdown sequence and improved error handling."""
        if not self.running:
            logger.debug("Web server already stopped or not running")
            return

        logger.info("Starting web server shutdown process...")
        self.running = False  # Set this early to prevent new operations

        # Cleanup connection manager first
        if self.connection_manager:
            try:
                logger.debug("Shutting down ConnectionManager...")
                # ConnectionManager cleanup is handled by reset_connection_manager()
                from ..optimization.connection_manager import (  # noqa
                    reset_connection_manager,
                )

                reset_connection_manager()
                self.connection_manager = None
                logger.debug("ConnectionManager shutdown completed")
            except Exception as e:
                logger.warning(f"Error during ConnectionManager shutdown: {e}")

        try:
            if self.server:
                # CRITICAL FIX: Close the server socket FIRST to stop accepting new connections
                logger.debug("Calling server.server_close() first to release socket...")
                try:
                    self.server.server_close()
                    logger.debug("server.server_close() completed successfully")
                except Exception as e:
                    logger.warning(f"Error during server_close(): {e}")

                # Then shutdown the request handling with improved timeout
                logger.debug("Calling server.shutdown()...")
                import threading  # noqa: PLC0415

                shutdown_complete = threading.Event()
                shutdown_error = None

                def shutdown_server() -> None:
                    nonlocal shutdown_error
                    try:
                        if self.server:
                            self.server.shutdown()
                        shutdown_complete.set()
                    except Exception as e:
                        shutdown_error = e
                        shutdown_complete.set()

                shutdown_thread = threading.Thread(
                    target=shutdown_server, daemon=True, name="ServerShutdown"
                )
                shutdown_thread.start()

                # Wait for shutdown with increased timeout (10 seconds)
                if shutdown_complete.wait(timeout=10.0):
                    if shutdown_error:
                        logger.warning(f"Server shutdown completed with error: {shutdown_error}")
                    else:
                        logger.debug("server.shutdown() completed successfully")
                else:
                    logger.warning(
                        "server.shutdown() timed out after 10 seconds - continuing with cleanup"
                    )

            if self.server_thread and self.server_thread.is_alive():
                logger.debug("Waiting for server thread to join (timeout=10s)...")
                self.server_thread.join(timeout=10)
                if self.server_thread.is_alive():
                    logger.warning(
                        "Server thread did not terminate within 10 seconds - marking as daemon for cleanup"
                    )
                    # Mark as daemon to allow process to exit
                    self.server_thread.daemon = True
                else:
                    logger.debug("Server thread joined successfully")

            # Clean up server reference
            self.server = None

        except Exception:
            logger.exception("Error during web server shutdown")

            # Emergency cleanup
            try:
                if self.server:
                    logger.debug("Emergency cleanup: attempting server_close()")
                    self.server.server_close()
            except Exception:
                pass  # Ignore errors during emergency cleanup

            self.server = None

        # Always ensure running is False and server is cleaned up
        self.running = False

    def get_calendar_html(self, days: int = 1, debug_time: Optional[datetime] = None) -> str:
        """Get current calendar HTML content.

        Args:
            days: Number of days to fetch events for (default: 1)
            debug_time: Optional time override for debug mode (whats-next-view only)
        """
        try:
            logger.debug(f"Navigation state available: {self.navigation_state is not None}")

            # Get current events
            if self.navigation_state:
                # Interactive mode - get events for selected date
                selected_date = self.navigation_state.selected_date
                start_datetime = datetime.combine(selected_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=days)

                logger.debug(
                    f"Interactive mode - getting events for {selected_date} ({start_datetime} to {end_datetime}) [days: {days}]"
                )

                # Handle async call from sync context properly
                try:
                    # Try to get the running event loop
                    loop = asyncio.get_running_loop()

                    # If we're in an event loop, we can't use asyncio.run()
                    # Create a task and run it synchronously (this is for web server context)
                    # Run the async function in a separate thread to avoid event loop conflicts
                    def run_async_in_thread() -> Any:
                        import asyncio  # noqa: PLC0415

                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                self.cache_manager.get_events_by_date_range(
                                    start_datetime, end_datetime
                                )
                            )
                        finally:
                            new_loop.close()

                    events = run_in_thread_pool(run_async_in_thread, timeout=5.0)

                except RuntimeError:
                    # No running event loop, safe to use asyncio.run()
                    events = asyncio.run(
                        self.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
                    )

                logger.debug(f"Retrieved {len(events)} events for selected date")

                # Build status info for interactive mode
                from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

                status_info = {
                    "selected_date": self.navigation_state.get_display_date(),
                    "is_today": self.navigation_state.is_today(),
                    "interactive_mode": True,
                    "last_update": get_timezone_aware_now().isoformat(),
                    "is_cached": bool(events),  # If we got events, assume cached
                }
            else:
                # Non-interactive mode - get today's events
                today = date.today()
                start_datetime = datetime.combine(today, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=days)

                logger.debug(
                    f"Non-interactive mode - getting events for today {today} ({start_datetime} to {end_datetime}) [days: {days}]"
                )

                # Handle async call from sync context properly
                try:
                    # Try to get the running event loop
                    loop = asyncio.get_running_loop()  # noqa: F841

                    # If we're in an event loop, we can't use asyncio.run()
                    # Run the async function in a separate thread to avoid event loop conflicts
                    def run_async_in_thread() -> Any:
                        import asyncio  # noqa: PLC0415

                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                self.cache_manager.get_events_by_date_range(
                                    start_datetime, end_datetime
                                )
                            )
                        finally:
                            new_loop.close()

                    events = run_in_thread_pool(run_async_in_thread, timeout=5.0)

                except RuntimeError:
                    # No running event loop, safe to use asyncio.run()
                    events = asyncio.run(
                        self.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
                    )

                logger.debug(f"Retrieved {len(events)} events for today")

                # Static web display mode - no navigation buttons
                from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

                status_info = {
                    "last_update": get_timezone_aware_now().isoformat(),
                    "is_cached": False,
                    "interactive_mode": False,
                }

            logger.debug(f"Display manager renderer type: {type(self.display_manager.renderer)}")
            logger.debug(
                f"Renderer has render_events method: {hasattr(self.display_manager.renderer, 'render_events')}"
            )

            # Generate HTML using display manager
            if hasattr(self.display_manager.renderer, "render_events"):
                # Pass debug_time to renderer if it's a WhatsNextRenderer and debug_time is provided
                if debug_time and hasattr(
                    self.display_manager.renderer, "_find_next_upcoming_event"
                ):
                    # For WhatsNextRenderer, we need to pass debug_time
                    logger.debug(
                        f"Passing debug_time {debug_time.isoformat()} to WhatsNextRenderer"
                    )
                    html_result = self.display_manager.renderer.render_events(
                        events, status_info, debug_time=debug_time
                    )
                else:
                    html_result = self.display_manager.renderer.render_events(events, status_info)
                logger.debug(f"Generated HTML length: {len(html_result)} characters")
                return str(html_result)
            logger.error("HTML renderer does not have render_events method")
            return "<html><body><h1>Error: HTML renderer not available</h1></body></html>"

        except Exception as e:
            logger.exception("Error getting calendar HTML")
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

        except Exception:
            logger.exception(f"Error handling navigation action '{action}'")
            return False

    def toggle_layout(self) -> str:
        """Toggle between layouts (alias for cycle_layout for backward compatibility).

        Returns:
            New layout name
        """
        return self.cycle_layout()

    def set_layout(self, layout: str) -> bool:
        """Set the display layout type.

        Args:
            layout: Layout type (dynamically discovered from registry)

        Returns:
            True if layout was set successfully
        """
        # Validate layout using registry
        if self.layout_registry.validate_layout(layout):
            # Call display_manager.set_layout to change just the layout
            success = self.display_manager.set_layout(layout)
            if success:
                # Update layout property
                self.layout = layout
                logger.info(f"Layout changed to: {layout}")
                return True
            logger.warning(f"Failed to set layout: {layout}")
            return False
        available_layouts = self.layout_registry.get_available_layouts()
        logger.warning(f"Unknown layout: {layout}. Available layouts: {available_layouts}")
        return False

    def cycle_layout(self) -> str:
        """Cycle through available layouts.

        Returns:
            New layout name
        """
        # Get current layout from display manager
        current_layout = self.get_current_layout()
        logger.debug(f"cycle_layout current_layout='{current_layout}'")

        # Get available layouts from registry and cycle through them
        available_layouts = self.layout_registry.get_available_layouts()
        if not available_layouts:
            logger.warning("No layouts available for cycling")
            return current_layout

        try:
            current_index = available_layouts.index(current_layout)
            # Cycle to next layout, wrapping around to 0 if at end
            next_index = (current_index + 1) % len(available_layouts)
            new_layout = available_layouts[next_index]
            logger.debug(
                f"Cycling {current_layout} -> {new_layout} (index {current_index} -> {next_index})"
            )
        except ValueError:
            # Current layout not in available layouts, start with first
            logger.debug(
                f"Current layout '{current_layout}' not in available layouts, using first available"
            )
            new_layout = available_layouts[0]

        logger.debug(f"cycle_layout calling set_layout('{new_layout}')")
        self.set_layout(new_layout)
        return new_layout

    def get_current_layout(self) -> str:
        """Get the current layout type.

        Returns:
            Current layout name
        """
        # Use the web server's layout property which correctly tracks layout names
        # The display manager tracks renderer type ('html') not layout name ('3x4', '4x8')
        current_layout = self.layout

        logger.debug(
            f"get_current_layout() returning '{current_layout}' from web server layout property"
        )
        return str(current_layout)

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
        except Exception:
            logger.exception("Error refreshing data")
            return False

    def get_status(self) -> dict[str, Any]:
        """Get server status information.

        Returns:
            Status information dictionary
        """
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "layout": self.get_current_layout(),
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
