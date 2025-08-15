"""Driver for Waveshare 4.2inch e-Paper Module (B) v2."""

import logging
from typing import Optional

try:
    import spidev  # type: ignore[import]
    from RPi import GPIO  # type: ignore[import]

    _HAS_REAL_GPIO = True
except ImportError:
    # Use mock implementations for development/testing environments
    from . import (
        mock_gpio as GPIO,  # type: ignore[import]
        mock_spidev as spidev,  # type: ignore[import]
    )

    _HAS_REAL_GPIO = False

from ...capabilities import DisplayCapabilities
from ...region import Region
from ..eink_driver import EInkDisplayDriver
from .utils import (
    delay_ms,
    split_color_buffer,
)

logger = logging.getLogger(__name__)


class EPD4in2bV2(EInkDisplayDriver):
    """Driver for Waveshare 4.2inch e-Paper Module (B) v2."""

    # Pin definitions
    RST_PIN = 17
    DC_PIN = 25
    CS_PIN = 8
    BUSY_PIN = 24

    # Display constants
    WIDTH = 400
    HEIGHT = 300

    # Command constants
    PANEL_SETTING = 0x00
    POWER_SETTING = 0x01
    POWER_OFF = 0x02
    POWER_ON = 0x04
    BOOSTER_SOFT_START = 0x06
    DEEP_SLEEP = 0x07
    DATA_START_TRANSMISSION_1 = 0x10
    DATA_STOP = 0x11
    DISPLAY_REFRESH = 0x12
    DATA_START_TRANSMISSION_2 = 0x13
    PARTIAL_DATA_START_TRANSMISSION_1 = 0x14
    PARTIAL_DATA_START_TRANSMISSION_2 = 0x15
    PARTIAL_DISPLAY_REFRESH = 0x16
    LUT_FOR_VCOM = 0x20
    LUT_WHITE_TO_WHITE = 0x21
    LUT_BLACK_TO_WHITE = 0x22
    LUT_WHITE_TO_BLACK = 0x23
    LUT_BLACK_TO_BLACK = 0x24
    PLL_CONTROL = 0x30
    TEMPERATURE_SENSOR_COMMAND = 0x40
    TEMPERATURE_SENSOR_SELECTION = 0x41
    TEMPERATURE_SENSOR_WRITE = 0x42
    TEMPERATURE_SENSOR_READ = 0x43
    VCOM_AND_DATA_INTERVAL_SETTING = 0x50
    LOW_POWER_DETECTION = 0x51
    TCON_SETTING = 0x60
    RESOLUTION_SETTING = 0x61
    GSST_SETTING = 0x65
    GET_STATUS = 0x71
    AUTO_MEASUREMENT_VCOM = 0x80
    READ_VCOM_VALUE = 0x81
    VCM_DC_SETTING = 0x82
    PARTIAL_WINDOW = 0x90
    PARTIAL_IN = 0x91
    PARTIAL_OUT = 0x92
    PROGRAM_MODE = 0xA0
    ACTIVE_PROGRAM = 0xA1
    READ_OTP_DATA = 0xA2
    POWER_SAVING = 0xE3

    def __init__(self) -> None:
        """Initialize the Waveshare e-Paper driver."""
        self.width = self.WIDTH
        self.height = self.HEIGHT
        self.spi: Optional[spidev.SpiDev] = None
        self.initialized = False

    def _digital_write(self, pin: int, value: int) -> None:
        """Write digital value to GPIO pin.

        Args:
            pin: GPIO pin number
            value: Value to write (0 or 1)
        """
        GPIO.output(pin, value)

    def _digital_read(self, pin: int) -> int:
        """Read digital value from GPIO pin.

        Args:
            pin: GPIO pin number

        Returns:
            Value read from pin (0 or 1)
        """
        return GPIO.input(pin)  # type: ignore[no-any-return]

    def _spi_transfer(self, data: list[int]) -> None:
        """Transfer data over SPI.

        Args:
            data: Data to transfer
        """
        if self.spi:
            self.spi.writebytes(data)

    def _send_command(self, command: int) -> None:
        """Send command to display.

        Args:
            command: Command byte
        """
        self._digital_write(self.DC_PIN, 0)
        self._digital_write(self.CS_PIN, 0)
        self._spi_transfer([command])
        self._digital_write(self.CS_PIN, 1)

    def _send_data(self, data: int) -> None:
        """Send data to display.

        Args:
            data: Data byte
        """
        self._digital_write(self.DC_PIN, 1)
        self._digital_write(self.CS_PIN, 0)
        self._spi_transfer([data])
        self._digital_write(self.CS_PIN, 1)

    def _send_data_bulk(self, data: list[int]) -> None:
        """Send multiple data bytes to display.

        Args:
            data: List of data bytes
        """
        self._digital_write(self.DC_PIN, 1)
        self._digital_write(self.CS_PIN, 0)
        self._spi_transfer(data)
        self._digital_write(self.CS_PIN, 1)

    def _init_full(self) -> None:
        """Initialize display for full update mode."""
        self._send_command(self.POWER_SETTING)
        self._send_data(0x03)  # VDS_EN, VDG_EN
        self._send_data(0x00)  # VCOM_HV, VGHL_LV[1], VGHL_LV[0]
        self._send_data(0x2B)  # VDH
        self._send_data(0x2B)  # VDL
        self._send_data(0x09)  # VDHR

        self._send_command(self.BOOSTER_SOFT_START)
        self._send_data(0x07)
        self._send_data(0x07)
        self._send_data(0x17)

        # Power optimization
        self._send_command(0xF8)
        self._send_data(0x60)
        self._send_data(0xA5)

        # Power optimization
        self._send_command(0xF8)
        self._send_data(0x89)
        self._send_data(0xA5)

        # Power optimization
        self._send_command(0xF8)
        self._send_data(0x90)
        self._send_data(0x00)

        # Power optimization
        self._send_command(0xF8)
        self._send_data(0x93)
        self._send_data(0x2A)

        # Power optimization
        self._send_command(0xF8)
        self._send_data(0x73)
        self._send_data(0x41)

        self._send_command(self.PARTIAL_DISPLAY_REFRESH)
        self._send_data(0x00)

        self._send_command(self.POWER_ON)
        self._wait_until_idle()

        self._send_command(self.PANEL_SETTING)
        self._send_data(0xAF)  # KW-BF   KWR-AF    BWROTP 0f

        self._send_command(self.PLL_CONTROL)
        self._send_data(0x3A)  # 3A 100HZ   29 150Hz 39 200HZ    31 171HZ

        self._send_command(self.RESOLUTION_SETTING)
        self._send_data(0x01)  # width high byte
        self._send_data(0x90)  # width low byte
        self._send_data(0x01)  # height high byte
        self._send_data(0x2C)  # height low byte

        self._send_command(self.VCM_DC_SETTING)
        self._send_data(0x12)

        self._send_command(self.VCOM_AND_DATA_INTERVAL_SETTING)
        self._send_data(0x97)  # 97 white border 77 black border    97 white border 77 black border

    def _wait_until_idle(self) -> None:
        """Wait until display is idle (not busy)."""
        logger.debug("Waiting for display to be idle...")
        while self._digital_read(self.BUSY_PIN) == 0:
            delay_ms(100)
        logger.debug("Display is now idle")

    def initialize(self) -> bool:
        """Initialize the display hardware.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Initialize GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.RST_PIN, GPIO.OUT)
            GPIO.setup(self.DC_PIN, GPIO.OUT)
            GPIO.setup(self.CS_PIN, GPIO.OUT)
            GPIO.setup(self.BUSY_PIN, GPIO.IN)

            # Initialize SPI
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # type: ignore
            self.spi.max_speed_hz = 4000000  # type: ignore
            self.spi.mode = 0b00  # type: ignore

            # Reset display
            self._digital_write(self.RST_PIN, 1)
            delay_ms(200)
            self._digital_write(self.RST_PIN, 0)
            delay_ms(10)
            self._digital_write(self.RST_PIN, 1)
            delay_ms(200)

            # Initialize display
            self._init_full()

            # Clear display
            self.clear()

            self.initialized = True
            logger.info("Waveshare e-Paper display initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Waveshare e-Paper display: {e}")
            return False

    def render(self, content: bytes) -> bool:
        """Render content to the display.

        Args:
            content: Buffer containing pixel data

        Returns:
            bool: True if rendering successful, False otherwise
        """
        return self.full_update(content)

    def clear(self) -> bool:
        """Clear the display.

        Returns:
            bool: True if clearing successful, False otherwise
        """
        try:
            buffer_size = self.width * self.height // 8
            buffer = [0xFF] * buffer_size  # White

            self._send_command(self.DATA_START_TRANSMISSION_1)
            self._send_data_bulk(buffer)

            self._send_command(self.DATA_START_TRANSMISSION_2)
            self._send_data_bulk(buffer)

            self._send_command(self.DISPLAY_REFRESH)
            self._wait_until_idle()

            logger.info("Display cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
            return False

    def shutdown(self) -> bool:
        """Shutdown the display hardware.

        Returns:
            bool: True if shutdown successful, False otherwise
        """
        try:
            self._send_command(self.POWER_OFF)
            self._wait_until_idle()
            self._send_command(self.DEEP_SLEEP)
            self._send_data(0xA5)

            # Clean up GPIO and SPI
            if self.spi:
                self.spi.close()
                self.spi = None

            GPIO.cleanup([self.RST_PIN, self.DC_PIN, self.CS_PIN, self.BUSY_PIN])

            self.initialized = False
            logger.info("Display shutdown successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to shutdown display: {e}")
            return False

    def get_capabilities(self) -> DisplayCapabilities:
        """Get display capabilities.

        Returns:
            DisplayCapabilities: Object containing display capabilities
        """
        return DisplayCapabilities(
            width=self.width,
            height=self.height,
            colors=3,  # Black, white, red
            supports_partial_update=True,
            supports_grayscale=True,
            supports_red=True,
        )

    def partial_update(self, region: Region, buffer: bytes) -> bool:
        """Perform a partial update of the display.

        Args:
            region: Region to update
            buffer: Buffer containing pixel data

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Ensure region is within display bounds
            if (
                region.x < 0
                or region.y < 0
                or region.x + region.width > self.width
                or region.y + region.height > self.height
            ):
                logger.error("Region out of bounds")
                return False

            # Ensure region dimensions are multiples of 8
            if region.width % 8 != 0 or region.height % 8 != 0:
                logger.warning("Region dimensions should be multiples of 8 for optimal results")

            # Enter partial update mode
            self._send_command(self.PARTIAL_IN)

            # Set partial window
            self._send_command(self.PARTIAL_WINDOW)
            self._send_data(region.x >> 8)  # X start high byte
            self._send_data(region.x & 0xFF)  # X start low byte
            self._send_data((region.x + region.width - 1) >> 8)  # X end high byte
            self._send_data((region.x + region.width - 1) & 0xFF)  # X end low byte
            self._send_data(region.y >> 8)  # Y start high byte
            self._send_data(region.y & 0xFF)  # Y start low byte
            self._send_data((region.y + region.height - 1) >> 8)  # Y end high byte
            self._send_data((region.y + region.height - 1) & 0xFF)  # Y end low byte
            self._send_data(0x01)  # Gates scan both inside and outside of the partial window

            # Split buffer into black and red parts
            buffer_size = region.width * region.height // 8
            result = split_color_buffer(buffer, buffer_size)
            if result is None:
                logger.error("Failed to split color buffer")
                return False

            black_buffer, red_buffer = result

            # Send black buffer
            self._send_command(self.PARTIAL_DATA_START_TRANSMISSION_1)
            self._send_data_bulk(list(black_buffer))

            # Send red buffer
            self._send_command(self.PARTIAL_DATA_START_TRANSMISSION_2)
            self._send_data_bulk(list(red_buffer))

            # Refresh display
            self._send_command(self.PARTIAL_DISPLAY_REFRESH)
            self._wait_until_idle()

            # Exit partial update mode
            self._send_command(self.PARTIAL_OUT)

            logger.info(f"Partial update completed for region: {region}")
            return True

        except Exception as e:
            logger.error(f"Failed to perform partial update: {e}")
            return False

    def full_update(self, buffer: bytes) -> bool:
        """Perform a full update of the display.

        Args:
            buffer: Buffer containing pixel data

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Ensure buffer size is correct
            buffer_size = self.width * self.height // 8

            # Split buffer into black and red parts
            result = split_color_buffer(buffer, buffer_size)
            if result is None:
                logger.error("Failed to split color buffer")
                return False

            black_buffer, red_buffer = result

            # Send black buffer
            self._send_command(self.DATA_START_TRANSMISSION_1)
            self._send_data_bulk(list(black_buffer))

            # Send red buffer
            self._send_command(self.DATA_START_TRANSMISSION_2)
            self._send_data_bulk(list(red_buffer))

            # Refresh display
            self._send_command(self.DISPLAY_REFRESH)
            self._wait_until_idle()

            logger.info("Full update completed")
            return True

        except Exception as e:
            logger.error(f"Failed to perform full update: {e}")
            return False

    def sleep(self) -> bool:
        """Put the display in sleep mode.

        Returns:
            bool: True if sleep mode entered successfully, False otherwise
        """
        try:
            self._send_command(self.POWER_OFF)
            self._wait_until_idle()
            self._send_command(self.DEEP_SLEEP)
            self._send_data(0xA5)

            logger.info("Display entered sleep mode")
            return True

        except Exception as e:
            logger.error(f"Failed to enter sleep mode: {e}")
            return False

    def wake(self) -> bool:
        """Wake the display from sleep mode.

        Returns:
            bool: True if wake successful, False otherwise
        """
        try:
            # Reset display
            self._digital_write(self.RST_PIN, 0)
            delay_ms(10)
            self._digital_write(self.RST_PIN, 1)
            delay_ms(200)

            # Re-initialize display
            self._init_full()

            logger.info("Display woken from sleep mode")
            return True

        except Exception as e:
            logger.error(f"Failed to wake display: {e}")
            return False
