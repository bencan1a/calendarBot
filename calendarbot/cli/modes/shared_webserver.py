"""Shared webserver utility for Calendar Bot CLI modes.

This module provides a reusable webserver implementation that can be used
by multiple CLI modes (web mode, epaper mode) to ensure consistent HTML
rendering and reduce code duplication.
"""

import logging
import socket
from http.server import HTTPServer
from threading import Thread
from typing import Any, Optional

from ...layout.registry import LayoutRegistry
from ...layout.resource_manager import ResourceManager
from ...settings.service import SettingsService
from ...utils.process import auto_cleanup_before_start
from ...web.server import WebServer

logger = logging.getLogger(__name__)


class SharedWebServer:
    """Shared webserver utility for multiple CLI modes.

    This class provides a simplified interface to the WebServer class
    with additional functionality for port management and error handling.
    It can be used by both web mode and epaper mode to ensure consistent
    HTML rendering.
    """

    def __init__(
        self,
        settings: Any,
        display_manager: Any,
        cache_manager: Any,
        navigation_state: Optional[Any] = None,
        layout_registry: Optional[LayoutRegistry] = None,
        resource_manager: Optional[ResourceManager] = None,
    ) -> None:
        """Initialize shared webserver with required components.

        Args:
            settings: Application settings object containing web server configuration
            display_manager: Display manager instance for rendering calendar content
            cache_manager: Cache manager instance for event data
            navigation_state: Optional navigation state for interactive mode
            layout_registry: Optional layout registry for dynamic layout discovery
            resource_manager: Optional resource manager for dynamic CSS/JS loading

        Raises:
            RuntimeError: If initialization fails
        """
        self.settings = settings
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.navigation_state = navigation_state

        # Initialize layout management system
        if layout_registry is not None:
            logger.debug("SharedWebServer: Using provided LayoutRegistry instance")
            self.layout_registry = layout_registry
        else:
            logger.debug(
                "SharedWebServer: Creating new LayoutRegistry instance - POTENTIAL DUPLICATE!"
            )
            self.layout_registry = LayoutRegistry()

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
        self.host = getattr(settings, "web_host", "127.0.0.1")
        self.port = getattr(settings, "web_port", 8080)
        self.layout = getattr(settings, "web_layout", "whats-next-view")

        # Server instance
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[Thread] = None
        self.running = False
        self.web_server: Optional[WebServer] = None

        logger.info(f"SharedWebServer initialized with configuration: {self.host}:{self.port}")

    def start(self, auto_find_port: bool = True, max_port_attempts: int = 10) -> bool:
        """Start the webserver with automatic port conflict resolution.

        Args:
            auto_find_port: If True, automatically find an available port if the
                           configured port is in use
            max_port_attempts: Maximum number of ports to try if auto_find_port is True

        Returns:
            True if server started successfully, False otherwise
        """
        if self.running:
            logger.warning("Webserver already running")
            return True

        # Create WebServer instance
        try:
            self.web_server = WebServer(
                settings=self.settings,
                display_manager=self.display_manager,
                cache_manager=self.cache_manager,
                navigation_state=self.navigation_state,
                layout_registry=self.layout_registry,
                resource_manager=self.resource_manager,
            )
            logger.debug("WebServer instance created successfully")
        except Exception:
            logger.exception("Failed to create WebServer instance")
            return False

        # Try to start the server with port conflict resolution
        original_port = self.port
        port_attempts = 0

        while port_attempts < max_port_attempts:
            try:
                # Automatically clean up any conflicting processes before starting
                if getattr(self.settings, "auto_kill_existing", False):
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

                # Start the WebServer
                if self.web_server:
                    # Update port in case it changed during conflict resolution
                    if hasattr(self.web_server, "port"):
                        self.web_server.port = self.port

                    self.web_server.start()
                    self.running = True
                    logger.info(f"Webserver started successfully on http://{self.host}:{self.port}")

                    # Update settings with actual port used
                    if hasattr(self.settings, "web_port"):
                        self.settings.web_port = self.port

                    return True
                logger.error("WebServer instance is None, cannot start")
                return False

            except OSError:  # noqa: PERF203
                if auto_find_port and port_attempts < max_port_attempts - 1:
                    # Try the next port
                    self.port += 1
                    port_attempts += 1
                    logger.warning(
                        f"Port {self.port - 1} is in use, trying port {self.port} (attempt {port_attempts + 1}/{max_port_attempts})"
                    )
                else:
                    logger.exception(
                        f"Failed to start webserver after {port_attempts + 1} attempts"
                    )
                    # Reset port to original value
                    self.port = original_port
                    return False
            except Exception:
                logger.exception("Failed to start webserver")
                # Reset port to original value
                self.port = original_port
                return False

        # If we get here, we've exhausted all port attempts
        logger.error(f"Failed to find available port after {max_port_attempts} attempts")
        # Reset port to original value
        self.port = original_port
        return False

    def stop(self) -> bool:
        """Stop the webserver.

        Returns:
            True if server stopped successfully, False otherwise
        """
        if not self.running:
            logger.debug("Webserver already stopped or not running")
            return True

        try:
            if self.web_server:
                logger.debug("Stopping webserver...")
                self.web_server.stop()
                logger.info("Webserver stopped successfully")
                self.running = False
                return True
            logger.warning("WebServer instance is None, cannot stop")
            self.running = False
            return False
        except Exception:
            logger.exception("Error stopping webserver")
            # Set running to False even if there was an error
            self.running = False
            return False

    def get_calendar_html(self, days: int = 1, debug_time: Optional[Any] = None) -> str:
        """Get calendar HTML content from the webserver.

        Args:
            days: Number of days to fetch events for
            debug_time: Optional time override for debug mode

        Returns:
            HTML content as string

        Raises:
            RuntimeError: If webserver is not running or HTML generation fails
        """
        if not self.running or not self.web_server:
            error_msg = "Webserver is not running, cannot get calendar HTML"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            return self.web_server.get_calendar_html(days, debug_time)
        except Exception as e:
            error_msg = f"Failed to get calendar HTML: {e}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

    def get_status(self) -> dict[str, Any]:
        """Get server status information.

        Returns:
            Status information dictionary
        """
        if not self.web_server:
            return {
                "running": self.running,
                "host": self.host,
                "port": self.port,
                "layout": self.layout,
                "error": "WebServer instance is None",
            }

        try:
            return self.web_server.get_status()
        except Exception:
            logger.exception("Error getting server status")
            return {
                "running": self.running,
                "host": self.host,
                "port": self.port,
                "layout": self.layout,
                "error": "Error getting server status",
            }

    @property
    def url(self) -> str:
        """Get the server URL.

        Returns:
            Server URL as string
        """
        return f"http://{self.host}:{self.port}"


def find_available_port(start_port: int = 8080, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port.

    Args:
        start_port: Port to start checking from
        max_attempts: Maximum number of ports to check

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port is found after max_attempts
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                logger.debug(f"Found available port: {port}")
                return port
        except OSError:  # noqa: PERF203
            logger.debug(f"Port {port} is in use, trying next port")
            continue

    # If we get here, we've exhausted all port attempts
    error_msg = f"Failed to find available port after {max_attempts} attempts"
    logger.error(error_msg)
    raise RuntimeError(error_msg)
