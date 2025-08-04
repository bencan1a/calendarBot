"""E-Paper mode handler for Calendar Bot CLI.

This module provides the e-paper display mode functionality for Calendar Bot,
including hardware detection, rendering, and PNG fallback capabilities.
E-paper is a CORE feature with automatic hardware detection and PNG emulation.
"""

import asyncio
import logging
import signal
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn, Optional, Union

from calendarbot.config.settings import settings
from calendarbot.display.epaper.drivers.waveshare import EPD4in2bV2
from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.main import CalendarBot
from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging

from ..config import apply_cli_overrides

logger = logging.getLogger(__name__)


class EpaperModeContext:
    """Context object to hold e-paper mode state and components."""

    def __init__(self) -> None:
        self.app: Optional[CalendarBot] = None
        self.epaper_renderer: Optional[EInkWhatsNextRenderer] = None
        self.hardware_available: bool = False
        self.fetch_task: Optional[asyncio.Task] = None
        self.shutdown_event: asyncio.Event = asyncio.Event()


async def _initialize_epaper_components(args: Any) -> tuple[EpaperModeContext, Any]:
    """Initialize e-paper mode components and settings.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (context object, updated settings)

    Raises:
        Exception: If initialization fails
    """
    logger.info("Starting Calendar Bot e-paper mode initialization...")

    # Apply command-line logging overrides with priority system
    updated_settings = apply_command_line_overrides(settings, args)

    # Apply CLI-specific overrides
    updated_settings = apply_cli_overrides(updated_settings, args)

    # Apply e-paper mode overrides
    updated_settings = apply_epaper_mode_overrides(updated_settings, args)

    # Set up enhanced logging for e-paper mode
    setup_enhanced_logging(updated_settings, interactive_mode=False)
    logger.info("Enhanced logging initialized for e-paper mode")

    logger.info("Initializing Calendar Bot components...")

    # Create context and Calendar Bot instance
    context = EpaperModeContext()
    context.app = CalendarBot()
    logger.debug("Created CalendarBot instance")

    # Initialize components
    if not await context.app.initialize():
        logger.error("Failed to initialize Calendar Bot")
        print("Failed to initialize Calendar Bot")
        raise RuntimeError("Failed to initialize Calendar Bot")

    logger.info("Calendar Bot components initialized successfully")

    # Initialize e-paper renderer with hardware detection
    logger.info("Initializing e-paper renderer with hardware detection...")

    # Detect hardware and set up display mode
    context.hardware_available = detect_epaper_hardware()

    # Force HTML-to-PNG conversion for emulation mode
    if not context.hardware_available:
        # Ensure html2image is available
        try:
            from calendarbot.display.epaper.utils.html_to_png import is_html2image_available
            html2image_available = is_html2image_available()
            if not html2image_available:
                logger.warning("html2image is not available. Install with: pip install html2image")
                print("Warning: html2image is not available. Install with: pip install html2image")
                print("Falling back to PIL rendering for emulation mode")
        except ImportError:
            html2image_available = False
            logger.warning("Failed to import html2image module")

    # Create the renderer
    context.epaper_renderer = EInkWhatsNextRenderer(updated_settings)

    if context.hardware_available:
        logger.info("E-paper hardware detected - using physical display")
        print("E-paper hardware detected - rendering to physical display")
    else:
        logger.info("No e-paper hardware detected - using PNG emulation mode")
        print("No e-paper hardware detected - using PNG emulation (output saved to files)")

        # Ensure HTML-to-PNG conversion is used for emulation mode
        if context.epaper_renderer.html_converter is None:
            logger.warning("HTML-to-PNG converter not initialized, forcing initialization for emulation mode")
            try:
                import tempfile
                from pathlib import Path

                from calendarbot.display.epaper.utils.html_to_png import create_converter
                from calendarbot.display.shared_styling import get_layout_for_renderer

                # Get layout dimensions
                layout = get_layout_for_renderer("epaper")
                width, height = int(layout["width"]), int(layout["height"])

                # Create temporary directory for output files
                temp_dir_path = tempfile.mkdtemp(prefix="calendarbot_epaper_")
                context.epaper_renderer.temp_dir = Path(temp_dir_path)

                # Ensure the directory exists
                context.epaper_renderer.temp_dir.mkdir(exist_ok=True, parents=True)
                logger.info(f"Created temporary directory: {context.epaper_renderer.temp_dir}")

                # Initialize converter with e-paper dimensions
                context.epaper_renderer.html_converter = create_converter(
                    size=(width, height),
                    output_path=str(context.epaper_renderer.temp_dir),
                )
                logger.info(f"HTML-to-PNG converter initialized with size {width}x{height}")
            except Exception as e:
                logger.warning(f"Failed to initialize HTML-to-PNG converter: {e}")

    return context, updated_settings


async def _handle_render_error(
    context: EpaperModeContext, error: Exception, events: list[Any], render_count: int
) -> None:
    """Handle rendering errors by displaying error on e-paper display.

    Args:
        context: E-paper mode context
        error: The exception that occurred
        events: Current events list for context
        render_count: Current render cycle number
    """
    logger.exception("Error in e-paper render cycle")

    if not context.epaper_renderer:
        logger.error("E-paper renderer not initialized, cannot display error")
        return

    try:
        error_image = context.epaper_renderer.render_error(str(error), events)
        if context.hardware_available:
            context.epaper_renderer.update_display(error_image)
        else:
            error_path = save_png_emulation(error_image, f"error_{render_count + 1}")
            print(f"Error display saved to: {error_path}")
    except Exception:
        logger.exception("Failed to render error display")


async def _run_epaper_main_loop(context: EpaperModeContext) -> None:
    """Run the main e-paper rendering loop.

    Args:
        context: E-paper mode context with initialized components
    """
    if not context.app or not context.epaper_renderer:
        raise RuntimeError("E-paper components not properly initialized")

    print("Starting Calendar Bot e-paper mode")
    print("Press Ctrl+C to stop")
    logger.debug("E-paper mode ready, entering main loop")

    # Main rendering loop
    render_count = 0
    while not context.shutdown_event.is_set():
        events = []  # Initialize events for error handling scope
        try:
            logger.debug(f"Starting render cycle {render_count + 1}")

            # Get fresh calendar data using correct cache manager method
            events = await context.app.cache_manager.get_todays_cached_events()
            logger.debug(f"Retrieved {len(events)} events for rendering")

            # Create status info using correct cache manager methods
            cache_status = await context.app.cache_manager.get_cache_status()
            status_info = {
                "is_cached": True,  # Using cached data from app
                "last_update": (
                    getattr(cache_status, "last_update", None) if cache_status else None
                ),
            }

            # Render to e-paper format
            rendered_image = context.epaper_renderer.render_from_events(events, status_info)
            logger.debug("Successfully rendered calendar to e-paper format")

            # Update display (hardware or PNG file)
            if context.hardware_available:
                success = context.epaper_renderer.update_display(rendered_image)
                if success:
                    logger.info(f"Successfully updated e-paper display (cycle {render_count + 1})")
                else:
                    logger.warning(f"Failed to update e-paper display (cycle {render_count + 1})")
            else:
                # Save as PNG for emulation mode
                output_path = save_png_emulation(rendered_image, render_count + 1)
                logger.info(f"Saved PNG emulation to: {output_path}")
                print(f"Calendar rendered to: {output_path}")

            render_count += 1

            # Wait before next update (e-paper displays don't need frequent updates)
            logger.debug("Waiting for next render cycle...")
            for _ in range(300):  # 5 minutes in 1-second intervals for responsive shutdown
                if context.shutdown_event.is_set():
                    break
                await asyncio.sleep(1)

        except Exception as e:
            await _handle_render_error(context, e, events, render_count)
            # Wait before retry
            await asyncio.sleep(30)


async def _cleanup_epaper_resources(context: EpaperModeContext) -> None:
    """Clean up e-paper mode resources gracefully.

    Args:
        context: E-paper mode context with resources to clean up
    """
    logger.debug("Entering cleanup phase...")

    # Stop background fetching
    if context.fetch_task:
        logger.debug("Cancelling background fetch task...")
        context.fetch_task.cancel()

        logger.debug("Waiting for background fetch task to complete...")
        try:
            await asyncio.wait_for(context.fetch_task, timeout=10.0)
            logger.debug("Background fetch task completed normally")
        except asyncio.CancelledError:
            logger.debug("Background fetch task cancelled successfully")
        except asyncio.TimeoutError:
            logger.warning("Background fetch task did not cancel within 10 seconds")
        except Exception:
            logger.exception("Unexpected error during background fetch task cancellation")

    # Cleanup app
    if context.app:
        try:
            logger.debug("Running application cleanup...")
            await asyncio.wait_for(context.app.cleanup(), timeout=10.0)
            logger.info("Application cleanup completed")
        except asyncio.TimeoutError:
            logger.warning("Application cleanup timed out after 10 seconds")
        except Exception:
            logger.exception("Error during application cleanup")


def _raise_app_not_initialized() -> NoReturn:
    """Raise RuntimeError for uninitialized app."""
    raise RuntimeError("CalendarBot app is not initialized")


async def run_epaper_mode(args: Any) -> int:
    """Run Calendar Bot in e-paper display mode.

    Provides hardware detection with automatic PNG fallback when physical
    hardware is unavailable. Ensures identical visual output in both scenarios.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """

    def signal_handler(signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        if "context" in locals():
            context.shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize components
        context, updated_settings = await _initialize_epaper_components(args)

        # Start background data fetching
        if not context.app:
            _raise_app_not_initialized()

        logger.debug("Starting background data fetching task...")
        if context.app is not None:
            context.fetch_task = asyncio.create_task(context.app.run_background_fetch())
            logger.debug("Background data fetching task started")
        else:
            logger.error("CalendarBot app is not initialized; cannot start background fetch task.")
            _raise_app_not_initialized()

        try:
            # Run main loop
            await _run_epaper_main_loop(context)
            logger.info("Shutdown signal received, beginning graceful shutdown...")

        finally:
            # Always cleanup resources
            await _cleanup_epaper_resources(context)

        logger.info("E-paper mode completed successfully")
        return 0

    except Exception as e:
        # Use print instead of logger since logger might not be initialized yet
        print(f"E-paper mode error: {e}")
        # Print traceback for debugging
        traceback.print_exc()
        return 1


def detect_epaper_hardware() -> bool:
    """Detect if physical e-paper hardware is available.

    Performs hardware detection to determine if a physical e-paper display
    is connected and accessible. Returns False for mock drivers to ensure
    PNG fallback is used when no physical hardware is present.

    Returns:
        True if real e-paper hardware is detected and accessible, False otherwise
    """
    try:
        # First check if the driver module is using real GPIO/SPI
        try:
            import calendarbot.display.epaper.drivers.waveshare.epd4in2b_v2 as epd_module
            has_real_gpio = getattr(epd_module, '_HAS_REAL_GPIO', False)

            logger.debug(f"Hardware detection: _HAS_REAL_GPIO = {has_real_gpio}")

            if not has_real_gpio:
                logger.info(
                    "E-paper hardware detection: FAILED - Using mock GPIO/SPI drivers, no physical hardware"
                )
                return False

        except ImportError:
            logger.debug("Waveshare drivers not available")
            return False

        # Check for physical hardware indicators
        from pathlib import Path

        # Check for SPI device files
        spi_devices = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev1.0", "/dev/spidev1.1"]
        spi_found = any(Path(device).exists() for device in spi_devices)

        # Check for GPIO filesystem
        gpio_base = Path("/sys/class/gpio")
        gpio_available = gpio_base.exists()

        logger.debug(f"Hardware detection: SPI devices found = {spi_found}, GPIO filesystem = {gpio_available}")

        if not spi_found or not gpio_available:
            logger.info(
                f"E-paper hardware detection: FAILED - Missing hardware interfaces (SPI: {spi_found}, GPIO: {gpio_available})"
            )
            return False

        # Try to initialize the driver with real hardware
        try:
            test_driver = EPD4in2bV2()
            if test_driver.initialize():
                logger.info(
                    "E-paper hardware detection: SUCCESS - Physical Waveshare display detected and initialized"
                )
                return True
            logger.info("E-paper hardware detection: FAILED - Driver initialization failed")
            return False
        except Exception as e:
            logger.info(f"E-paper hardware detection: FAILED - Driver initialization error: {e}")
            return False

    except Exception as e:
        logger.info(f"E-paper hardware detection: FAILED - Detection error: {e}")
        return False


def save_png_emulation(image: Any, cycle_number: Union[int, str]) -> Path:
    """Save rendered image as PNG for emulation mode.

    Args:
        image: PIL Image to save
        cycle_number: Render cycle number for filename (int or str)

    Returns:
        Path to saved PNG file
    """
    # Create output directory if it doesn't exist
    output_dir = Path("epaper_output")
    output_dir.mkdir(exist_ok=True)

    # Generate filename with timestamp and cycle number
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if isinstance(cycle_number, str):
        filename = f"calendar_epaper_{timestamp}_{cycle_number}.png"
    else:
        filename = f"calendar_epaper_{timestamp}_cycle{cycle_number:03d}.png"

    output_path = output_dir / filename

    # Save the image
    image.save(output_path, "PNG")
    logger.debug(f"Saved PNG emulation: {output_path}")

    return output_path


def apply_epaper_mode_overrides(settings: Any, _args: Any) -> Any:
    """Apply e-paper mode specific setting overrides.

    Args:
        settings: Application settings object
        args: Parsed command line arguments

    Returns:
        Updated settings object with e-paper optimizations
    """
    # Configure settings for optimal e-paper rendering
    settings.display_type = "epaper"

    # Set layout appropriate for e-paper display
    settings.web_layout = "whats-next-view"  # Use WhatsNext layout for e-paper

    # E-paper specific optimizations
    settings.epaper.refresh_interval = 300  # 5 minutes - e-paper doesn't need frequent updates
    settings.cache_ttl = 600  # 10 minutes cache duration

    logger.debug("Applied e-paper mode setting overrides")
    return settings


__all__ = [
    "apply_epaper_mode_overrides",
    "detect_epaper_hardware",
    "run_epaper_mode",
    "save_png_emulation",
]
