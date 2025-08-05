"""Renderer factory for automatic renderer selection based on device detection."""

import logging
import platform
import subprocess  # nosec
from pathlib import Path
from typing import Any, Optional, cast

from .console_renderer import ConsoleRenderer
from .html_renderer import HTMLRenderer
from .renderer_protocol import RendererProtocol
from .whats_next_renderer import WhatsNextRenderer

logger = logging.getLogger(__name__)

# Import e-Paper renderer with graceful fallback
try:
    from .epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer

    EPAPER_AVAILABLE = True
    EInkWhatsNextRenderer_TYPE: Optional[type[EInkWhatsNextRenderer]] = EInkWhatsNextRenderer
except ImportError:
    logger.info("calendarbot.display.epaper package not available - e-Paper rendering disabled")
    EInkWhatsNextRenderer_TYPE = None
    EPAPER_AVAILABLE = False


class RendererFactory:
    """Factory for automatic renderer selection based on device capabilities and settings."""

    @staticmethod
    def detect_device_type() -> str:
        """Detect the device type based on hardware characteristics.

        Returns:
            Device type string: 'rpi', 'compact', 'desktop', or 'unknown'

        Raises:
            No exceptions raised - detection failures return 'unknown'
        """
        try:
            system = platform.system().lower()
            machine = platform.machine().lower()

            logger.debug(f"Device detection: system={system}, machine={machine}")

            # Check for Raspberry Pi
            if _is_raspberry_pi():
                # Check for compact e-ink display (300x400)
                if _has_compact_display():
                    logger.info("Detected Raspberry Pi with compact e-ink display")
                    return "compact"
                logger.info("Detected standard Raspberry Pi")
                return "rpi"

            # Check for Linux ARM devices (other SBCs)
            if system == "linux" and "arm" in machine:
                logger.info("Detected ARM Linux device")
                return "rpi"  # Treat as rpi-compatible

            # Desktop/server systems
            if system in ["linux", "darwin", "windows"]:
                logger.info(f"Detected desktop system: {system}")
                return "desktop"

            logger.warning(f"Unknown device type: {system} {machine}")
            return "unknown"

        except Exception:
            logger.exception("Device detection failed")
            return "unknown"

    @staticmethod
    def create_renderer(
        settings_or_renderer_type: Optional[Any] = None,
        settings_or_unused: Optional[Any] = None,
        layout_name: Optional[str] = None,
        *,
        settings: Optional[Any] = None,
        renderer_type: Optional[str] = None,
    ) -> RendererProtocol:
        """Create appropriate renderer based on device detection or explicit type.

        Supports both old positional signature: create_renderer(renderer_type, settings)
        And new keyword signature: create_renderer(settings=..., renderer_type=..., layout_name=...)

        Args:
            settings_or_renderer_type: Either settings (new style) or renderer_type (old style)
            settings_or_unused: Either None (new style) or settings (old style)
            layout_name: Optional layout name to use with the renderer
            settings: Settings object (keyword-only, new style)
            renderer_type: Renderer type (keyword-only, new style)

        Returns:
            Configured renderer instance

        Raises:
            ValueError: If renderer_type is invalid
            RuntimeError: If renderer creation fails
        """
        # Handle both old and new calling conventions
        if settings is not None and renderer_type is not None:
            # New keyword style: create_renderer(settings=..., renderer_type=..., layout_name=...)
            actual_settings = settings
            actual_renderer_type: Optional[str] = renderer_type
        elif settings_or_unused is not None:
            # Old positional style: create_renderer(renderer_type, settings)
            actual_renderer_type = cast(Optional[str], settings_or_renderer_type)
            actual_settings = settings_or_unused
        elif settings_or_renderer_type is not None:
            # Mixed style: create_renderer(settings, renderer_type=..., layout_name=...)
            actual_settings = settings_or_renderer_type
            actual_renderer_type = renderer_type
        else:
            # All keyword style but missing required arguments
            raise ValueError(
                "Must provide either: (renderer_type, settings) or (settings=..., renderer_type=...)"
            )

        # Validate required parameters
        if actual_settings is None:
            raise ValueError("Settings object is required")
        # Determine renderer type
        if actual_renderer_type is None:
            device_type = RendererFactory.detect_device_type()
            actual_renderer_type = _map_device_to_renderer(device_type)
            logger.info(
                f"Auto-detected renderer type: {actual_renderer_type} for device: {device_type}"
            )
        else:
            logger.info(f"Using explicit renderer type: {actual_renderer_type}")

        # Update settings if layout_name is provided
        if layout_name is not None:
            actual_settings.web_layout = layout_name
            logger.debug(f"Updated settings with layout: {layout_name}")

        try:
            # Create renderer instance
            renderer = _create_renderer_instance(actual_renderer_type, actual_settings)
            logger.info(f"Created {renderer.__class__.__name__} successfully")
            return renderer

        except Exception:
            logger.exception("Renderer creation failed")
            logger.warning("Falling back to ConsoleRenderer")
            return ConsoleRenderer(actual_settings)

    @staticmethod
    def get_available_renderers() -> list[str]:
        """Get list of available renderer types.

        Returns:
            List of renderer type names
        """
        renderers = ["html", "console", "whats-next"]
        if EPAPER_AVAILABLE:
            renderers.append("epaper")
            renderers.append("eink-whats-next")  # Keep for backward compatibility
        return renderers

    @staticmethod
    def get_recommended_renderer() -> str:
        """Get recommended renderer type for current device.

        Returns:
            Recommended renderer type string
        """
        device_type = RendererFactory.detect_device_type()
        recommended = _map_device_to_renderer(device_type)
        logger.debug(f"Recommended renderer for device {device_type}: {recommended}")
        return recommended


def _is_raspberry_pi() -> bool:
    """Check if running on a Raspberry Pi.

    Returns:
        True if on Raspberry Pi, False otherwise
    """
    try:
        # Check /proc/cpuinfo for Raspberry Pi identifier
        cpuinfo_path = Path("/proc/cpuinfo")
        if cpuinfo_path.exists():
            cpuinfo_content = cpuinfo_path.read_text()
            if "Raspberry Pi" in cpuinfo_content or "BCM" in cpuinfo_content:
                return True

        # Check /proc/device-tree/model if available
        model_path = Path("/proc/device-tree/model")
        if model_path.exists():
            model_content = model_path.read_text(errors="ignore")
            if "Raspberry Pi" in model_content:
                return True

        return False

    except Exception as e:
        logger.debug(f"Raspberry Pi detection failed: {e}")
        return False


def _has_compact_display() -> bool:
    """Check if device has compact e-ink display (300x400).

    Returns:
        True if compact display detected, False otherwise
    """
    try:
        # Check for common e-ink display drivers/modules
        eink_indicators = [
            Path("/sys/class/graphics/fb1"),  # Secondary framebuffer
            Path("/dev/fb1"),  # Framebuffer device
            Path("/sys/module/fbtft"),  # FBTFT driver
        ]

        for indicator in eink_indicators:
            if indicator.exists():
                logger.debug(f"Found e-ink display indicator: {indicator}")
                return True

        # Check for SPI devices (common for e-ink displays)
        try:
            result = subprocess.run(  # nosec
                ["ls", "/dev/spi*"], check=False, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.debug("Found SPI devices, possible e-ink display")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    except Exception as e:
        logger.debug(f"Compact display detection failed: {e}")
        return False


def _map_device_to_renderer(device_type: str) -> str:
    """Map device type to appropriate renderer type.

    Args:
        device_type: Device type from detection

    Returns:
        Renderer type string
    """
    mapping = {
        "desktop": "html",
        "unknown": "console",
        "rpi": "whats-next",
        "compact": "epaper",  # Updated to use the new standardized "epaper" type
    }
    return mapping.get(device_type, "console")


def _create_renderer_instance(renderer_type: str, settings: Any) -> RendererProtocol:
    """Create renderer instance of specified type.

    Args:
        renderer_type: Type of renderer to create
        settings: Application settings

    Returns:
        Renderer instance

    Raises:
        ValueError: If renderer_type is invalid
    """
    renderer_classes = {
        "html": HTMLRenderer,
        "console": ConsoleRenderer,
        "whats-next": WhatsNextRenderer,
        # Legacy type mappings for backward compatibility
        "rpi": WhatsNextRenderer,
        "compact": EInkWhatsNextRenderer_TYPE
        if EPAPER_AVAILABLE and EInkWhatsNextRenderer_TYPE is not None
        else ConsoleRenderer,
    }

    # Add e-Paper renderer if available
    if EPAPER_AVAILABLE and EInkWhatsNextRenderer_TYPE is not None:
        renderer_classes["eink-whats-next"] = EInkWhatsNextRenderer_TYPE
        renderer_classes["epaper"] = (
            EInkWhatsNextRenderer_TYPE  # Add direct mapping for "epaper" display_type
        )

    renderer_class = renderer_classes.get(renderer_type)
    if renderer_class is None:
        available_types = list(renderer_classes.keys())
        raise ValueError(
            f"Unknown renderer type: {renderer_type}. Available types: {available_types}"
        )

    return cast(RendererProtocol, renderer_class(settings))
