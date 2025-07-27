"""Display abstraction layer interfaces for e-Paper displays."""

from typing import Any, Protocol

from .capabilities import DisplayCapabilities


class DisplayAbstractionLayer(Protocol):
    """Protocol defining the interface for display hardware abstraction."""

    def initialize(self) -> bool:
        """Initialize the display hardware.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        ...

    def render(self, content: Any) -> bool:
        """Render content to the display.

        Args:
            content: Content to render (format depends on implementation)

        Returns:
            bool: True if rendering successful, False otherwise
        """
        ...

    def clear(self) -> bool:
        """Clear the display.

        Returns:
            bool: True if clearing successful, False otherwise
        """
        ...

    def shutdown(self) -> bool:
        """Shutdown the display hardware.

        Returns:
            bool: True if shutdown successful, False otherwise
        """
        ...

    def get_capabilities(self) -> DisplayCapabilities:
        """Get display capabilities.

        Returns:
            DisplayCapabilities: Object containing display capabilities
        """
        ...
