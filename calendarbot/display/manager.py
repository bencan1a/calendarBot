"""Display manager coordinating between data and rendering."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..cache.models import CachedEvent
from ..utils.helpers import secure_clear_screen
from .compact_eink_renderer import CompactEInkRenderer
from .console_renderer import ConsoleRenderer
from .html_renderer import HTMLRenderer
from .renderer_protocol import RendererProtocol
from .rpi_html_renderer import RaspberryPiHTMLRenderer

logger = logging.getLogger(__name__)


class DisplayManager:
    """Manages display output and coordination between data and renderers."""

    def __init__(self, settings: Any) -> None:
        """Initialize display manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.renderer: Optional[RendererProtocol] = None

        # Initialize appropriate renderer based on settings
        logger.info(f"DIAGNOSTIC: display_type = '{settings.display_type}'")
        if settings.display_type == "console":
            self.renderer = ConsoleRenderer(settings)
            logger.info("DIAGNOSTIC: Using ConsoleRenderer")
        elif settings.display_type == "html":
            self.renderer = HTMLRenderer(settings)
            logger.info("DIAGNOSTIC: Using HTMLRenderer")
        elif settings.display_type == "rpi" or settings.display_type == "rpi-html":
            self.renderer = RaspberryPiHTMLRenderer(settings)
            logger.info("DIAGNOSTIC: Using RaspberryPiHTMLRenderer")
        elif settings.display_type == "3x4":
            self.renderer = CompactEInkRenderer(settings)
            logger.info("DIAGNOSTIC: Using CompactEInkRenderer for 300x400 e-ink display")
        else:
            logger.warning(f"Unknown display type: {settings.display_type}, defaulting to console")
            self.renderer = ConsoleRenderer(settings)

        logger.info(f"Display manager initialized with {settings.display_type} renderer")

    def set_display_type(self, display_type: str) -> bool:
        """Change the display type at runtime.

        Args:
            display_type: New display type (4x8, 3x4)

        Returns:
            True if display type was changed successfully
        """
        # Map display types to settings display_type values
        type_mapping = {
            "4x8": "html",
            "3x4": "3x4",
        }

        mapped_type = type_mapping.get(display_type, display_type)
        valid_types = ["html", "rpi", "3x4", "console"]

        if mapped_type not in valid_types:
            logger.warning(f"Invalid display type: {display_type}")
            return False

        if mapped_type == self.settings.display_type:
            logger.debug(f"Display type already set to: {display_type}")
            return True

        try:
            # Create new renderer based on mapped type
            old_display_type = self.settings.display_type

            new_renderer: RendererProtocol
            if mapped_type == "console":
                new_renderer = ConsoleRenderer(self.settings)
            elif mapped_type == "html":
                new_renderer = HTMLRenderer(self.settings)
            elif mapped_type == "rpi" or mapped_type == "rpi-html":
                new_renderer = RaspberryPiHTMLRenderer(self.settings)
            elif mapped_type == "3x4":
                new_renderer = CompactEInkRenderer(self.settings)
            else:
                logger.warning(f"Unknown mapped display type: {mapped_type}, defaulting to console")
                new_renderer = ConsoleRenderer(self.settings)

            # Update current state
            self.settings.display_type = mapped_type
            self.renderer = new_renderer

            logger.info(
                f"Display type changed from {old_display_type} to {mapped_type} (requested: {display_type})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to change display type to {display_type}: {e}")
            return False

    def get_display_type(self) -> str:
        """Get the current display type.

        Returns:
            Current display type name (mapped to user-friendly names)
        """
        # Map internal types back to user-friendly names
        type_mapping = {
            "html": "4x8",
            "3x4": "3x4",
            "console": "console",
        }
        mapped_type = type_mapping.get(self.settings.display_type, self.settings.display_type)
        logger.debug(
            f"DIAGNOSTIC LOG: get_display_type() - internal: '{self.settings.display_type}' → mapped: '{mapped_type}'"
        )
        return str(mapped_type)

    def get_available_display_types(self) -> List[str]:
        """Get list of available display types.

        Returns:
            List of available display type names
        """
        return ["4x8", "3x4"]

    @property
    def current_display_type(self) -> str:
        """Get the current display type (for compatibility).

        Returns:
            Current display type name
        """
        return self.get_display_type()

    async def display_events(
        self,
        events: List[CachedEvent],
        status_info: Optional[Dict[str, Any]] = None,
        clear_screen: bool = True,
    ) -> bool:
        """Display calendar events using the configured renderer.

        Args:
            events: List of cached events to display
            status_info: Additional status information
            clear_screen: Whether to clear screen before displaying

        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True

            # Prepare status information
            display_status = status_info or {}
            display_status["last_update"] = datetime.now().isoformat()

            # Render events
            if self.renderer is None:
                logger.error("No renderer available")
                return False

            content = self.renderer.render_events(events, display_status)

            # Display content
            if clear_screen and hasattr(self.renderer, "display_with_clear"):
                self.renderer.display_with_clear(content)
            else:
                print(content)

            logger.debug(f"Displayed {len(events)} events successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to display events: {e}")
            return False

    async def display_error(
        self,
        error_message: str,
        cached_events: Optional[List[CachedEvent]] = None,
        clear_screen: bool = True,
    ) -> bool:
        """Display error message with optional cached events.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show
            clear_screen: Whether to clear screen before displaying

        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True

            if self.renderer is None:
                logger.error("No renderer available")
                return False

            content = self.renderer.render_error(error_message, cached_events)

            # Display content
            if clear_screen and hasattr(self.renderer, "display_with_clear"):
                self.renderer.display_with_clear(content)
            else:
                print(content)

            logger.debug("Displayed error message successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to display error: {e}")
            return False

    async def display_authentication_prompt(
        self, verification_uri: str, user_code: str, clear_screen: bool = True
    ) -> bool:
        """Display authentication prompt for device code flow.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter
            clear_screen: Whether to clear screen before displaying

        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True

            if self.renderer is None:
                logger.error("No renderer available")
                return False

            content = self.renderer.render_authentication_prompt(verification_uri, user_code)

            # Display content
            if clear_screen and hasattr(self.renderer, "display_with_clear"):
                self.renderer.display_with_clear(content)
            else:
                print(content)

            logger.debug("Displayed authentication prompt successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to display authentication prompt: {e}")
            return False

    async def display_status(self, status_info: Dict[str, Any], clear_screen: bool = True) -> bool:
        """Display system status information.

        Args:
            status_info: Status information to display
            clear_screen: Whether to clear screen before displaying

        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True

            lines = []
            lines.append("=" * 60)
            lines.append("📊 CALENDAR BOT STATUS")
            lines.append("=" * 60)
            lines.append("")

            for key, value in status_info.items():
                # Format key for display
                display_key = key.replace("_", " ").title()
                lines.append(f"{display_key}: {value}")

            lines.append("")
            lines.append("=" * 60)

            content = "\n".join(lines)

            # Display content
            if (
                clear_screen
                and self.renderer is not None
                and hasattr(self.renderer, "display_with_clear")
            ):
                self.renderer.display_with_clear(content)
            else:
                print(content)

            logger.debug("Displayed status information successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to display status: {e}")
            return False

    def clear_display(self) -> bool:
        """Clear the display securely.

        Returns:
            True if display was cleared successfully, False otherwise
        """
        try:
            if self.renderer is not None and hasattr(self.renderer, "clear_screen"):
                self.renderer.clear_screen()
                return True
            else:
                return secure_clear_screen()

        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
            return False

    def get_renderer_info(self) -> Dict[str, Any]:
        """Get information about the current renderer.

        Returns:
            Dictionary with renderer information
        """
        return {
            "type": self.settings.display_type,
            "enabled": self.settings.display_enabled,
            "renderer_class": self.renderer.__class__.__name__ if self.renderer else None,
        }
