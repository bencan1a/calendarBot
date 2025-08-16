"""Mock implementation of RPi.GPIO for development environments."""

import logging
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# GPIO modes
BCM = 11
BOARD = 10

# GPIO directions
OUT = 0
IN = 1

# GPIO values
HIGH = 1
LOW = 0

# GPIO pull-up/down
PUD_OFF = 0
PUD_DOWN = 1
PUD_UP = 2

# GPIO edge detection
RISING = 1
FALLING = 2
BOTH = 3


# Create a class to mimic the RPi.GPIO module
class GPIO:
    """Mock GPIO module for development environments."""

    @staticmethod
    def setmode(mode: int) -> None:
        """Mock setting the GPIO mode."""
        logger.debug(f"Mock GPIO: setmode({mode})")

    @staticmethod
    def setwarnings(state: bool) -> None:
        """Mock setting warnings."""
        logger.debug(f"Mock GPIO: setwarnings({state})")

    @staticmethod
    def setup(
        channel: int, direction: int, pull_up_down: int = PUD_OFF, initial: Optional[int] = None
    ) -> None:
        """Mock setup of a GPIO channel."""
        logger.debug(f"Mock GPIO: setup({channel}, {direction}, {pull_up_down}, {initial})")

    @staticmethod
    def output(channel: int, value: bool | list[bool] | tuple[bool, ...] | Literal[0, 1]) -> None:
        """Mock output to a GPIO channel."""
        logger.debug(f"Mock GPIO: output({channel}, {value})")

    @staticmethod
    def input(channel: int) -> int:
        """Mock input from a GPIO channel."""
        logger.debug(f"Mock GPIO: input({channel})")
        return HIGH  # Always return HIGH to avoid blocking in wait_until_idle

    @staticmethod
    def cleanup(channel: Optional[list[int]] = None) -> None:
        """Mock cleanup of GPIO channels."""
        logger.debug(f"Mock GPIO: cleanup({channel})")

    @staticmethod
    def add_event_detect(
        channel: int, edge: int, callback: Optional[Any] = None, bouncetime: Optional[int] = None
    ) -> None:
        """Mock adding event detection."""
        logger.debug(f"Mock GPIO: add_event_detect({channel}, {edge}, {callback}, {bouncetime})")

    @staticmethod
    def add_event_callback(channel: int, callback: Any) -> None:
        """Mock adding an event callback."""
        logger.debug(f"Mock GPIO: add_event_callback({channel}, {callback})")

    @staticmethod
    def remove_event_detect(channel: int) -> None:
        """Mock removing event detection."""
        logger.debug(f"Mock GPIO: remove_event_detect({channel})")

    @staticmethod
    def event_detected(channel: int) -> bool:
        """Mock event detection."""
        logger.debug(f"Mock GPIO: event_detected({channel})")
        return False

    @staticmethod
    def wait_for_edge(channel: int, edge: int, timeout: Optional[int] = None) -> Optional[int]:
        """Mock waiting for an edge."""
        logger.debug(f"Mock GPIO: wait_for_edge({channel}, {edge}, {timeout})")
        return None


# Export the GPIO class as the module
setmode = GPIO.setmode
setwarnings = GPIO.setwarnings
setup = GPIO.setup
output = GPIO.output
input = GPIO.input
cleanup = GPIO.cleanup
add_event_detect = GPIO.add_event_detect
add_event_callback = GPIO.add_event_callback
remove_event_detect = GPIO.remove_event_detect
event_detected = GPIO.event_detected
wait_for_edge = GPIO.wait_for_edge
