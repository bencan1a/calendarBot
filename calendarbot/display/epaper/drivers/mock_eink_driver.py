"""Mock e-Ink driver for testing without physical hardware."""

import logging
from typing import Any, Optional

from ..abstraction import DisplayAbstractionLayer
from ..capabilities import DisplayCapabilities

logger = logging.getLogger(__name__)


class MockEInkDriver(DisplayAbstractionLayer):
    """Mock e-Ink driver for testing and validation without physical hardware.

    This driver simulates the behavior of a real e-Paper display for development
    and testing purposes, following the same interface as hardware drivers.
    """

    def __init__(self, width: int = 300, height: int = 400, supports_red: bool = True) -> None:
        """Initialize mock e-Ink driver.

        Args:
            width: Display width in pixels (default: 300 for e-ink portrait)
            height: Display height in pixels (default: 400 for e-ink portrait)
            supports_red: Whether the mock display supports red color
        """
        self._width = width
        self._height = height
        self._supports_red = supports_red
        self._initialized = False
        self._last_rendered_content: Optional[bytes] = None

        logger.info(f"MockEInkDriver initialized {width}x{height}, red support: {supports_red}")

    def initialize(self) -> bool:
        """Initialize the mock display.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._initialized = True
            logger.info("MockEInkDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"MockEInkDriver initialization failed: {e}")
            return False

    def render(self, content: Any) -> bool:
        """Mock render content to the display.

        Args:
            content: Content to render (PIL Image or bytes)

        Returns:
            True if rendering successful, False otherwise
        """
        try:
            if not self._initialized:
                logger.warning("MockEInkDriver not initialized, auto-initializing")
                if not self.initialize():
                    return False

            # Simulate rendering by storing the content
            if hasattr(content, "tobytes"):
                # PIL Image
                self._last_rendered_content = content.tobytes()
                logger.debug(f"MockEInkDriver rendered PIL Image ({content.size})")
            elif isinstance(content, (bytes, bytearray)):
                # Raw bytes
                self._last_rendered_content = bytes(content)
                logger.debug(f"MockEInkDriver rendered {len(content)} bytes")
            else:
                # Convert to string representation
                content_str = str(content)
                self._last_rendered_content = content_str.encode("utf-8")
                logger.debug(f"MockEInkDriver rendered string content: {content_str[:50]}...")

            logger.info("MockEInkDriver render completed successfully")
            return True

        except Exception as e:
            logger.error(f"MockEInkDriver render failed: {e}")
            return False

    def clear(self) -> bool:
        """Clear the mock display.

        Returns:
            True if clearing successful, False otherwise
        """
        try:
            self._last_rendered_content = None
            logger.info("MockEInkDriver display cleared")
            return True
        except Exception as e:
            logger.error(f"MockEInkDriver clear failed: {e}")
            return False

    def shutdown(self) -> bool:
        """Shutdown the mock display.

        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            self._initialized = False
            self._last_rendered_content = None
            logger.info("MockEInkDriver shutdown completed")
            return True
        except Exception as e:
            logger.error(f"MockEInkDriver shutdown failed: {e}")
            return False

    def get_capabilities(self) -> DisplayCapabilities:
        """Get mock display capabilities.

        Returns:
            DisplayCapabilities object
        """
        return DisplayCapabilities(
            width=self._width,
            height=self._height,
            colors=3 if self._supports_red else 2,  # Black/white/red or black/white
            supports_partial_update=True,
            supports_grayscale=True,
            supports_red=self._supports_red,
        )

    def get_last_rendered_content(self) -> Optional[bytes]:
        """Get the last rendered content for testing purposes.

        Returns:
            Last rendered content as bytes, None if nothing rendered
        """
        return self._last_rendered_content

    def is_initialized(self) -> bool:
        """Check if driver is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized


# Alias for compatibility
EInkDriver = MockEInkDriver
