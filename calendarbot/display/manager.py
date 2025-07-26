"""Display manager coordinating between data and rendering."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

from ..cache.models import CachedEvent
from ..layout.exceptions import LayoutNotFoundError
from ..layout.registry import LayoutRegistry
from ..utils.helpers import secure_clear_screen
from .console_renderer import ConsoleRenderer
from .renderer_factory import RendererFactory
from .renderer_interface import RendererInterface
from .renderer_protocol import ConsoleRendererProtocol, RendererProtocol

logger = logging.getLogger(__name__)


class DisplayManager:
    """Manages display output and coordination between data and renderers with layout/renderer separation."""

    def __init__(
        self, settings: Any, renderer_type: Optional[str] = None, layout_name: Optional[str] = None
    ) -> None:
        """Initialize display manager with separate layout and renderer concerns.

        Args:
            settings: Application settings
            renderer_type: Optional explicit renderer type override
            layout_name: Optional layout name override
        """
        self.settings = settings
        self.renderer: Optional[
            Union[RendererProtocol, ConsoleRendererProtocol, RendererInterface]
        ] = None
        self._current_layout_name: Optional[str] = layout_name
        self._current_renderer_type: Optional[str] = renderer_type

        # Initialize layout registry for dynamic layout discovery
        try:
            self.layout_registry: Optional[LayoutRegistry] = LayoutRegistry()
            # Ensure layout registry is properly initialized by checking available layouts
            available_layouts = self.layout_registry.get_available_layouts()
            logger.debug(f"Layout registry initialized with {len(available_layouts)} layouts")

            # Validate current layout and fallback to default if invalid
            current_layout = getattr(settings, "web_layout", None)
            if current_layout and not self.layout_registry.validate_layout(current_layout):
                default_layout = self.layout_registry.get_default_layout()
                logger.info(
                    f"Invalid layout '{current_layout}', falling back to '{default_layout}'"
                )
                settings.web_layout = default_layout
                if hasattr(settings, "layout_name"):
                    settings.layout_name = default_layout

        except Exception as e:
            logger.warning(f"Failed to initialize layout registry: {e}, using fallback behavior")
            self.layout_registry = None

        # Initialize renderer factory and expose it for tests
        self.renderer_factory = RendererFactory()

        # Initialize renderer using factory with automatic device detection
        # Handle both old and new factory call patterns for compatibility
        effective_renderer_type = renderer_type or getattr(settings, "display_type", "html")

        # Special handling for whats-next-view layout: use WhatsNextRenderer or EInkWhatsNextRenderer
        current_layout = layout_name or getattr(settings, "web_layout", None)
        if current_layout == "whats-next-view":
            # Auto-detect if e-Paper renderer should be used
            available_renderers = self.renderer_factory.get_available_renderers()
            if "eink-whats-next" in available_renderers and self._should_use_epaper_renderer():
                logger.info(
                    "Detected whats-next-view layout with e-Paper support, using EInkWhatsNextRenderer"
                )
                effective_renderer_type = "eink-whats-next"
            else:
                logger.info("Detected whats-next-view layout, using WhatsNextRenderer")
                effective_renderer_type = "whats-next"

        try:
            # Try old signature first for backward compatibility with tests
            self.renderer = self.renderer_factory.create_renderer(effective_renderer_type, settings)
        except TypeError:
            # Fallback to new signature
            self.renderer = self.renderer_factory.create_renderer(
                settings=settings, renderer_type=effective_renderer_type, layout_name=layout_name
            )
        except Exception as e:
            # Handle renderer factory failures gracefully
            logger.error(f"Failed to create renderer: {e}")
            self.renderer = None

        if self.renderer:
            logger.info(f"Display manager initialized with {self.renderer.__class__.__name__}")
        else:
            logger.warning("Display manager initialized without renderer")
        logger.info(
            f"Layout: {getattr(settings, 'layout_name', 'default')}, "
            f"Renderer: {self._current_renderer_type or 'auto-detected'}"
        )

    def _should_use_epaper_renderer(self) -> bool:
        """Determine if e-Paper renderer should be used based on device detection.

        Returns:
            True if e-Paper renderer should be used, False otherwise
        """
        try:
            # Use the same device detection logic as RendererFactory
            device_type = self.renderer_factory.detect_device_type()
            # Use e-Paper for compact devices or if explicitly configured
            return device_type == "compact" or getattr(self.settings, "force_epaper", False)
        except Exception as e:
            logger.debug(f"E-Paper device detection failed: {e}")
            return False

    def set_display_type(self, display_type: str, layout_name: Optional[str] = None) -> bool:
        """Change the display type at runtime with layout/renderer separation.

        Args:
            display_type: New display type/renderer type
            layout_name: Optional layout name to use with the renderer

        Returns:
            True if display type was changed successfully
        """
        # Validate using Layout Registry if available
        if self.layout_registry is not None and layout_name is not None:
            layout_info = self.layout_registry.get_layout_info(layout_name)
            if layout_info is None:
                logger.warning(f"Layout '{layout_name}' not found in registry")
                return False
            logger.debug(f"Layout '{layout_name}' found in registry")

        # Validate renderer type
        available_renderers = RendererFactory.get_available_renderers()
        if display_type not in available_renderers:
            logger.warning(f"Invalid renderer type: {display_type}")
            return False

        if display_type == getattr(self.settings, "display_type", None) and layout_name == getattr(
            self.settings, "layout_name", None
        ):
            logger.debug(f"Display type and layout already set to: {display_type}, {layout_name}")
            return True

        try:
            # Create new renderer using factory
            old_display_type = getattr(self.settings, "display_type", "unknown")
            old_layout_name = getattr(self.settings, "layout_name", "unknown")

            # Special handling for whats-next-view layout: use WhatsNextRenderer
            effective_renderer_type = display_type
            if layout_name == "whats-next-view":
                logger.info("Switching to whats-next-view layout, using WhatsNextRenderer")
                effective_renderer_type = "whats-next"

            new_renderer = RendererFactory.create_renderer(
                settings=self.settings,
                renderer_type=effective_renderer_type,
                layout_name=layout_name,
            )

            # Update current state
            self.settings.display_type = display_type
            if layout_name is not None:
                self.settings.web_layout = layout_name
                self.settings.layout_name = layout_name
            self.renderer = new_renderer
            self._current_renderer_type = display_type
            self._current_layout_name = layout_name

            logger.info(
                f"Display changed from {old_display_type}/{old_layout_name} "
                f"to {display_type}/{layout_name or 'default'}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to change display type to {display_type}: {e}")
            return False

    def get_display_type(self) -> str:
        """Get the current display type.

        Returns:
            Current renderer type name
        """
        # Return the actual renderer type, not a layout-based mapping
        current_type = getattr(self.settings, "display_type", "console")
        logger.debug(
            f"DIAGNOSTIC LOG: get_display_type() returning renderer type: '{current_type}'"
        )
        return str(current_type)

    def get_available_display_types(self) -> List[str]:
        """Get list of available display types.

        Returns:
            List of available display type names
        """
        if self.layout_registry is not None:
            try:
                # Get dynamic list from Layout Registry
                available_layouts = self.layout_registry.get_available_layouts()
                logger.debug(
                    f"Layout Registry found {len(available_layouts)} layouts: {available_layouts}"
                )
                return available_layouts
            except Exception as e:
                logger.warning(f"Failed to get layouts from registry: {e}, using fallback")

        # Fallback to hardcoded list for compatibility
        logger.debug("Using fallback layout list")
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

            # Render events - handle both RendererProtocol and RendererInterface
            if hasattr(self.renderer, "render_events"):
                # RendererProtocol interface
                content = cast(RendererProtocol, self.renderer).render_events(
                    events, display_status
                )
            elif hasattr(self.renderer, "render"):
                # RendererInterface - need to create view model
                from .whats_next_logic import WhatsNextLogic

                logic = WhatsNextLogic(self.settings)
                view_model = logic.create_view_model(events, display_status)
                # Assert type to satisfy static type checker without redundant cast
                assert isinstance(self.renderer, RendererInterface)
                content = self.renderer.render(view_model)
            else:
                logger.error("Renderer does not support any known rendering interface")
                return False

            # Display content
            if clear_screen and hasattr(self.renderer, "display_with_clear"):
                cast(ConsoleRendererProtocol, self.renderer).display_with_clear(content)
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

            # Display content - handle both new RendererInterface and legacy methods
            if clear_screen and hasattr(self.renderer, "update_display"):
                # New RendererInterface method for e-Paper displays
                cast(RendererInterface, self.renderer).update_display(content)
            elif clear_screen and hasattr(self.renderer, "display_with_clear"):
                # Legacy renderer method
                cast(ConsoleRendererProtocol, self.renderer).display_with_clear(content)
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
                cast(ConsoleRendererProtocol, self.renderer).display_with_clear(content)
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
                cast(ConsoleRendererProtocol, self.renderer).display_with_clear(content)
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
                cast(ConsoleRendererProtocol, self.renderer).clear_screen()
                return True
            else:
                return secure_clear_screen()

        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
            return False

    def get_renderer_info(self) -> Dict[str, Any]:
        """Get information about the current renderer and layout.

        Returns:
            Dictionary with renderer and layout information
        """
        return {
            "type": getattr(self.settings, "display_type", "unknown"),
            "enabled": getattr(self.settings, "display_enabled", False),
            "renderer_class": self.renderer.__class__.__name__ if self.renderer else None,
        }

    def set_layout(self, layout_name: str) -> bool:
        """Change the layout and recreate renderer if necessary.

        Args:
            layout_name: New layout name to use

        Returns:
            True if layout was changed successfully
        """
        # Validate layout using registry if available
        if self.layout_registry is not None:
            try:
                if not self.layout_registry.validate_layout(layout_name):
                    logger.warning(f"Invalid layout: {layout_name}")
                    return False
            except Exception as e:
                logger.warning(f"Layout validation failed: {e}")
                return False

        # Check if we need to recreate the renderer for whats-next-view layout
        current_renderer_type = getattr(self.settings, "display_type", "html")

        try:
            # Special handling for whats-next-view layout: use WhatsNextRenderer
            if layout_name == "whats-next-view":
                logger.info("Switching to whats-next-view layout, using WhatsNextRenderer")
                effective_renderer_type = "whats-next"

                # Create new WhatsNextRenderer using factory
                new_renderer = self.renderer_factory.create_renderer(
                    settings=self.settings,
                    renderer_type=effective_renderer_type,
                    layout_name=layout_name,
                )
                self.renderer = new_renderer
                logger.info(f"Created {new_renderer.__class__.__name__} for whats-next-view layout")

            else:
                # For other layouts, check if we're switching from whats-next-view back to regular layout
                current_layout = getattr(self.settings, "layout_name", None)
                if current_layout == "whats-next-view" and layout_name != "whats-next-view":
                    logger.info(
                        f"Switching from whats-next-view to {layout_name}, recreating renderer"
                    )

                    # Recreate regular renderer (HTML renderer for most cases)
                    new_renderer = self.renderer_factory.create_renderer(
                        settings=self.settings,
                        renderer_type=current_renderer_type,
                        layout_name=layout_name,
                    )
                    self.renderer = new_renderer
                    logger.info(
                        f"Created {new_renderer.__class__.__name__} for {layout_name} layout"
                    )

                else:
                    # For regular layout changes, just update renderer's layout attribute if it has one
                    if self.renderer and hasattr(self.renderer, "layout"):
                        cast(Any, self.renderer).layout = layout_name

            # Update settings
            self.settings.layout_name = layout_name
            if hasattr(self.settings, "web_layout"):
                self.settings.web_layout = layout_name

            logger.debug(f"Layout changed to: {layout_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to change layout to {layout_name}: {e}")
            return False

    def get_current_layout(self) -> Optional[str]:
        """Get the current layout name.

        Returns:
            Current layout name or None if not set
        """
        return getattr(self.settings, "layout_name", None)

    def get_current_renderer_type(self) -> Optional[str]:
        """Get the current renderer type.

        Returns:
            Current renderer type or None if not set
        """
        return getattr(self.settings, "display_type", None)

    def get_available_layouts(self) -> List[str]:
        """Get list of available layouts.

        Returns:
            List of available layout names
        """
        return self.get_available_display_types()

    def get_layout(self) -> str:
        """Get the current layout name.

        Returns:
            Current layout name
        """
        # Try layout_name first, then web_layout, then default
        layout_name = getattr(self.settings, "layout_name", None)
        if layout_name and isinstance(layout_name, str):
            return str(layout_name)

        web_layout = getattr(self.settings, "web_layout", None)
        if web_layout and isinstance(web_layout, str):
            return str(web_layout)

        return "4x8"  # Default fallback

    def set_renderer_type(self, renderer_type: str) -> bool:
        """Set the renderer type while keeping the same layout.

        Args:
            renderer_type: New renderer type to use

        Returns:
            True if renderer type was changed successfully
        """
        current_layout = self.get_layout()
        return self.set_display_type(renderer_type, current_layout)

    def get_renderer_type(self) -> str:
        """Get the current renderer type.

        Returns:
            Current renderer type name
        """
        return getattr(self.settings, "display_type", "console")
