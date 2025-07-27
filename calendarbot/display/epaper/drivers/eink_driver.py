"""E-Ink display driver interface for e-Paper displays."""

from typing import Protocol

from ..abstraction import DisplayAbstractionLayer
from ..region import Region


class EInkDisplayDriver(DisplayAbstractionLayer, Protocol):
    """Protocol defining the interface for e-ink display drivers."""

    def partial_update(self, region: Region, buffer: bytes) -> bool:
        """Perform a partial update of the display.

        Args:
            region: Region to update
            buffer: Buffer containing pixel data

        Returns:
            bool: True if update successful, False otherwise
        """
        ...

    def full_update(self, buffer: bytes) -> bool:
        """Perform a full update of the display.

        Args:
            buffer: Buffer containing pixel data

        Returns:
            bool: True if update successful, False otherwise
        """
        ...

    def sleep(self) -> bool:
        """Put the display in sleep mode.

        Returns:
            bool: True if sleep mode entered successfully, False otherwise
        """
        ...

    def wake(self) -> bool:
        """Wake the display from sleep mode.

        Returns:
            bool: True if wake successful, False otherwise
        """
        ...
