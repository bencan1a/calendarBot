"""Mock implementation of spidev for development environments."""

import logging
from typing import List

logger = logging.getLogger(__name__)


class SpiDev:
    """Mock SPI device class."""

    def __init__(self) -> None:
        """Initialize the mock SPI device."""
        self.max_speed_hz = 0
        self.mode = 0
        logger.debug("Mock SpiDev: initialized")

    def open(self, bus: int, device: int) -> None:
        """Mock opening the SPI device."""
        logger.debug(f"Mock SpiDev: open({bus}, {device})")

    def close(self) -> None:
        """Mock closing the SPI device."""
        logger.debug("Mock SpiDev: close()")

    def writebytes(self, data: List[int]) -> None:
        """Mock writing bytes to the SPI device."""
        if data and len(data) > 10:
            logger.debug(f"Mock SpiDev: writebytes({data[:10]}... [{len(data)} bytes])")
        else:
            logger.debug(f"Mock SpiDev: writebytes({data})")

    def readbytes(self, length: int) -> List[int]:
        """Mock reading bytes from the SPI device."""
        logger.debug(f"Mock SpiDev: readbytes({length})")
        return [0] * length

    def xfer(self, data: List[int]) -> List[int]:
        """Mock transferring data over SPI."""
        logger.debug(f"Mock SpiDev: xfer({data})")
        return [0] * len(data)

    def xfer2(self, data: List[int]) -> List[int]:
        """Mock transferring data over SPI with chip select held active between blocks."""
        logger.debug(f"Mock SpiDev: xfer2({data})")
        return [0] * len(data)


# Create a module-level variable to export
class _SpidevModule:
    """Module-level container for SpiDev."""

    SpiDev = SpiDev


# Export the module
spidev = _SpidevModule()
