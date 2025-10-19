"""E-Paper mode handler for Calendar Bot CLI.

This module provides the e-paper display mode functionality for Calendar Bot,
including hardware detection, rendering, and PNG fallback capabilities.
E-paper is a CORE feature with automatic hardware detection and PNG emulation.

The module now includes webserver integration to ensure consistent rendering
between web mode and e-paper mode by fetching HTML from a local webserver
instead of generating it directly.
"""
# ruff: noqa

import asyncio
import logging
import os
import signal
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, Optional, Union

from calendarbot.config.settings import settings
from calendarbot.main import CalendarBot
from calendarbot.display.shared_styling import get_layout_for_renderer
from calendarbot.utils.logging import (
    apply_command_line_overrides,
    setup_enhanced_logging,
)
from calendarbot.cli.config import apply_cli_overrides

# Lazy-loaded heavy dependencies. These are intentionally initialized at runtime
# inside initialization functions to allow early exit when e-paper is disabled.
Image = None
EPD4in2bV2 = None
EInkWhatsNextRenderer = None
create_converter = None


# Default to a conservative false-returning callable until the real function is loaded
def is_html2image_available() -> bool:  # type: ignore
    return False


# Runtime-lazy placeholders for heavy classes. Mark as Any so static type-checkers
# (Pylance) understand these are runtime-assigned and avoid "None is not callable"
# diagnostics. Actual implementations are imported at runtime inside
# _initialize_epaper_components().
SharedWebServer: Any = None
HTTPClient: Any = None

# Type checking imports
if TYPE_CHECKING:
    from calendarbot.cli.modes.shared_webserver import SharedWebServer
    from calendarbot.utils.http_client import HTTPClient
    from calendarbot.display.epaper.integration.eink_whats_next_renderer import (
        EInkWhatsNextRenderer,
    )

logger = logging.getLogger(__name__)


class EpaperModeContext:
    """Context object to hold e-paper mode state and components."""

    def __init__(self) -> None:
        self.app: Optional[CalendarBot] = None
        # Use Any here to avoid static analysis issues for runtime-lazy imports
        self.epaper_renderer: Optional[Any] = None
        self.hardware_available: bool = False
        self.fetch_task: Optional[asyncio.Task] = None
        self.shutdown_event: asyncio.Event = asyncio.Event()

        # Webserver integration components (runtime-lazy; typed as Any to avoid import-time heavy deps)
        # Use Any for these attributes so static analysis won't attempt to resolve optional runtime
        # imports that are lazily loaded by this module.
        self.webserver: Any = None
        self.http_client: Any = None


async def _initialize_epaper_components(args: Any) -> tuple[EpaperModeContext, Any]:  # noqa: PLR0915
    """Initialize e-paper mode components and settings.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (context object, updated settings)

    Raises:
        Exception: If initialization fails
    """
    logger.info("Starting Calendar Bot e-paper mode initialization...")

    # Early disable guard: environment variable override or settings flag
    _disable_env = os.getenv("CALENDARBOT_DISABLE_EPAPER", "")
    if _disable_env and _disable_env.lower() in ("1", "true"):
        print(
            "e-paper mode disabled by CALENDARBOT_DISABLE_EPAPER=1 or settings.epaper.enabled=false — exiting"
        )
        ctx = EpaperModeContext()
        setattr(ctx, "disabled_by_config", True)
        return ctx, settings

    if not getattr(settings.epaper, "enabled", True):
        print(
            "e-paper mode disabled by CALENDARBOT_DISABLE_EPAPER=1 or settings.epaper.enabled=false — exiting"
        )
        ctx = EpaperModeContext()
        setattr(ctx, "disabled_by_config", True)
        return ctx, settings

    # Lazy import heavy dependencies here so importing this module does not pull in
    # renderer, hardware drivers, or html2image at import-time.
    global \
        Image, \
        EPD4in2bV2, \
        EInkWhatsNextRenderer, \
        create_converter, \
        is_html2image_available, \
        SharedWebServer, \
        HTTPClient
    try:
        from PIL import Image as _Image  # noqa: PLC0415

        Image = _Image
    except Exception:
        Image = None

    try:
        from calendarbot.display.epaper.drivers.waveshare import EPD4in2bV2 as _EPD  # noqa: PLC0415

        EPD4in2bV2 = _EPD
    except Exception:
        EPD4in2bV2 = None

    try:
        from calendarbot.display.epaper.integration.eink_whats_next_renderer import (  # noqa: PLC0415
            EInkWhatsNextRenderer as _EInk,
        )

        EInkWhatsNextRenderer = _EInk
    except Exception:
        EInkWhatsNextRenderer = None

    try:
        from calendarbot.display.epaper.utils.html_to_png import (  # noqa: PLC0415
            create_converter as _create_converter,
            is_html2image_available as _is_html2image_available,
        )

        create_converter = _create_converter
        is_html2image_available = _is_html2image_available
    except Exception:
        create_converter = None
        is_html2image_available = lambda: False  # type: ignore

    try:
        from calendarbot.cli.modes.shared_webserver import SharedWebServer as _SWS  # noqa: PLC0415

        SharedWebServer = _SWS
    except Exception:
        SharedWebServer = None

    try:
        from calendarbot.utils.http_client import HTTPClient as _HTTPClient  # noqa: PLC0415

        HTTPClient = _HTTPClient
    except Exception:
        HTTPClient = None

    # Apply command-line logging overrides with priority system
    updated_settings = apply_command_line_overrides(settings, args)

    # Apply CLI-specific overrides
    updated_settings = apply_cli_overrides(updated_settings, args)

    # Apply e-paper mode overrides
    updated_settings = apply_epaper_mode_overrides(updated_settings, args)

    # Set up enhanced logging for e-paper mode
    setup_enhanced_logging(updated_settings)
    logger.info("Enhanced logging initialized for e-paper mode")

    logger.debug("Initializing Calendar Bot components...")

    # Create context and Calendar Bot instance
    context = EpaperModeContext()
    context.app = CalendarBot()
    logger.debug("Created CalendarBot instance")

    # Initialize components
    init_ok = await context.app.initialize()
    if not init_ok:
        # Initialization failed due to missing/invalid configuration (common on clean installs).
        # Log a clear, user-facing message and return the partially-initialized context so
        # the caller can exit gracefully without raising an unhandled exception.
        logger.error(
            "Calendar Bot failed to initialize. This commonly indicates missing or invalid configuration (e.g. no ICS URL)."
        )
        print("\nCalendar Bot could not initialize due to missing or invalid configuration.")
        print("Quick fixes:")
        print("  1) Run the interactive setup:    calendarbot --setup")
        print("  2) Copy the example config and edit it:")
        print("       cp calendarbot/config/config.yaml.example calendarbot/config/config.yaml")
        print(
            "       Edit calendarbot/config/config.yaml and set your ICS URL or set CALENDARBOT_ICS_URL environment variable."
        )
        setattr(context, "init_failed", True)
        return context, updated_settings

    logger.info("Calendar Bot components initialized successfully")

    # Initialize e-paper renderer with hardware detection
    logger.info("Initializing e-paper renderer with hardware detection...")

    # Detect hardware and set up display mode
    context.hardware_available = detect_epaper_hardware()

    # Force HTML-to-PNG conversion for emulation mode
    if not context.hardware_available:
        # Ensure html2image is available
        try:
            html2image_available = is_html2image_available()
            if not html2image_available:
                logger.warning("html2image is not available. Install with: pip install html2image")
                print("Warning: html2image is not available. Install with: pip install html2image")
                print("Falling back to PIL rendering for emulation mode")
        except ImportError:
            html2image_available = False
            logger.warning("Failed to import html2image module")

    # Create the renderer (only if the renderer class was successfully imported)
    if EInkWhatsNextRenderer is not None:
        context.epaper_renderer = EInkWhatsNextRenderer(updated_settings)
    else:
        context.epaper_renderer = None
        logger.warning(
            "EInkWhatsNextRenderer not available; running in fallback emulation mode without renderer instance"
        )

    if context.hardware_available:
        logger.info("E-paper hardware detected - using physical display")
        print("E-paper hardware detected - rendering to physical display")
    else:
        logger.info("No e-paper hardware detected - using PNG emulation mode")
        print("No e-paper hardware detected - using PNG emulation (output saved to files)")

        # Ensure HTML-to-PNG conversion is used for emulation mode when we have a renderer instance
        if (
            context.epaper_renderer
            and getattr(context.epaper_renderer, "html_converter", None) is None
        ):
            logger.warning(
                "HTML-to-PNG converter not initialized on renderer instance, attempting initialization for emulation mode"
            )
            try:
                # Get layout dimensions
                layout = get_layout_for_renderer("epaper")
                width, height = int(layout["width"]), int(layout["height"])

                # Create temporary directory for output files
                temp_dir_path = tempfile.mkdtemp(prefix="calendarbot_epaper_")
                if context.epaper_renderer is not None:
                    context.epaper_renderer.temp_dir = Path(temp_dir_path)

                    # Ensure the directory exists
                    context.epaper_renderer.temp_dir.mkdir(exist_ok=True, parents=True)
                    logger.info(f"Created temporary directory: {context.epaper_renderer.temp_dir}")

                    # Initialize converter with e-paper dimensions if available
                    if create_converter is not None:
                        context.epaper_renderer.html_converter = create_converter(
                            size=(width, height),
                            output_path=str(context.epaper_renderer.temp_dir),
                        )
                        logger.info(f"HTML-to-PNG converter initialized with size {width}x{height}")
                    else:
                        logger.warning(
                            "create_converter is not available; cannot initialize html_converter"
                        )
                else:
                    logger.warning(
                        "No epaper_renderer instance; skipping html_converter initialization"
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize HTML-to-PNG converter: {e}")

    # Initialize webserver for HTML rendering
    try:
        logger.info("Initializing webserver for e-paper mode...")

        # Configure webserver port (use a different port than default web mode)
        webserver_enabled = getattr(updated_settings.epaper, "webserver_enabled", True)

        if not webserver_enabled:
            logger.info("Webserver is disabled in settings, skipping initialization")
            context.webserver = None
            context.http_client = None
            return context, updated_settings

        webserver_port = getattr(updated_settings.epaper, "webserver_port", 8081)

        # Set webserver port in settings
        updated_settings.web_port = webserver_port

        # Create and start webserver (only if SharedWebServer class is available)
        if SharedWebServer is not None:
            context.webserver = SharedWebServer(
                settings=updated_settings,
                display_manager=context.app.display_manager,
                cache_manager=context.app.cache_manager,
            )

            # Start webserver with automatic port conflict resolution
            webserver_started = False
            if context.webserver is not None and hasattr(context.webserver, "start"):
                webserver_started = context.webserver.start(
                    auto_find_port=True, max_port_attempts=10
                )

            if webserver_started:
                actual_port = getattr(context.webserver, "port", None)
                logger.info(f"Webserver started successfully on port {actual_port}")

                # Create HTTP client for fetching HTML (only if HTTPClient is available)
                # Use the IP address that we know works (192.168.1.45)
                host = "192.168.1.45"
                logger.debug(f"Using host {host} for HTTP client")
                if HTTPClient is not None:
                    if actual_port is not None:
                        context.http_client = HTTPClient(
                            base_url=f"http://{host}:{actual_port}",
                            timeout=5.0,
                            max_retries=3,
                        )
                        logger.info(
                            f"HTTP client initialized with base URL: {context.http_client.base_url}"
                        )
                    else:
                        context.http_client = None
                        logger.warning("Webserver port unknown; cannot initialize HTTP client")
                else:
                    context.http_client = None
                    logger.warning("HTTPClient class not available; cannot create HTTP client")
            else:
                logger.warning("Failed to start webserver, falling back to direct HTML generation")
                context.webserver = None
                context.http_client = None
        else:
            logger.warning("SharedWebServer not available; skipping webserver initialization")
            context.webserver = None
            context.http_client = None
    except Exception:
        logger.exception("Error initializing webserver")
        logger.warning("Falling back to direct HTML generation")
        context.webserver = None
        context.http_client = None

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
            png_path, processed_path = save_png_emulation(error_image, f"error_{render_count + 1}")
            print(f"Error display saved to: {png_path}")
            if processed_path:
                print(f"Processed e-paper visualization saved to: {processed_path}")
    except Exception:
        logger.exception("Failed to render error display")


async def _run_epaper_main_loop(context: EpaperModeContext) -> None:  # noqa: PLR0912, PLR0915
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
            if context.app.cache_manager is None:
                logger.error("Cache manager not available, skipping render cycle")
                await asyncio.sleep(300)  # Default 5 minute interval
                continue

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

            # Render to e-paper format - try using webserver if available
            rendered_image = None
            if context.webserver and context.http_client:
                try:
                    logger.debug("Rendering using webserver URL")

                    # Use HTML-to-PNG converter if available
                    if context.epaper_renderer.html_converter:
                        # Create a unique filename for the output image
                        output_filename = f"epaper_render_{os.urandom(4).hex()}.png"

                        # Get the webserver URL - use the base URL without any path
                        webserver_url = context.http_client.base_url
                        logger.info(f"Using webserver URL: {webserver_url}")

                        try:
                            # Use the new URL-based conversion method
                            logger.info("Using URL-based HTML-to-PNG conversion...")
                            png_path = context.epaper_renderer.html_converter.convert_url_to_png(
                                url=webserver_url, output_filename=output_filename
                            )

                            if png_path and Path(png_path).exists():
                                # Load the generated PNG as a PIL Image
                                if Image is not None:
                                    rendered_image = Image.open(png_path)
                                    logger.info(
                                        f"Webserver URL converted successfully to {png_path}"
                                    )
                                    logger.info(f"File size: {Path(png_path).stat().st_size} bytes")
                                else:
                                    logger.warning(
                                        "PIL Image is not available; cannot open generated PNG"
                                    )
                                    rendered_image = None
                            else:
                                # Direct fallback if PNG path doesn't exist
                                logger.warning(
                                    "URL-to-PNG conversion failed to produce a valid file, using direct fallback"
                                )
                                logger.warning(f"png_path = {png_path}")
                                rendered_image = None
                        except Exception as png_error:
                            logger.warning(f"URL-to-PNG conversion failed with error: {png_error}")
                            logger.warning("Using direct fallback rendering")
                            rendered_image = None
                except Exception as e:
                    logger.warning(f"Failed to render using webserver HTML: {e}")
                    logger.warning("Falling back to direct rendering")
                    rendered_image = None

            # Fall back to direct rendering if webserver rendering failed
            if rendered_image is None:
                rendered_image = context.epaper_renderer.render_from_events(events, status_info)
                logger.debug(
                    "Successfully rendered calendar to e-paper format using direct rendering"
                )

            # Update display (hardware or PNG file)
            if context.hardware_available:
                success = context.epaper_renderer.update_display(rendered_image)
                if success:
                    logger.info(f"Successfully updated e-paper display (cycle {render_count + 1})")
                else:
                    logger.warning(f"Failed to update e-paper display (cycle {render_count + 1})")
            else:
                # Save as PNG for emulation mode and also save processed visualization
                png_path, processed_path = save_png_emulation(rendered_image, render_count + 1)  # type: ignore[assignment]
                logger.info(f"Saved PNG emulation to: {png_path}")
                if processed_path:
                    logger.info(f"Saved processed e-paper visualization to: {processed_path}")
                print(f"Calendar rendered to: {png_path}")

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

    # Stop webserver if running
    if context.webserver:
        logger.debug("Stopping webserver...")
        try:
            context.webserver.stop()
            logger.info("Webserver stopped successfully")
        except Exception:
            logger.exception("Error stopping webserver")

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
        except TimeoutError:
            logger.warning("Background fetch task did not cancel within 10 seconds")
        except Exception:
            logger.exception("Unexpected error during background fetch task cancellation")

    # Cleanup app
    if context.app:
        try:
            logger.debug("Running application cleanup...")
            await asyncio.wait_for(context.app.cleanup(), timeout=10.0)
            logger.info("Application cleanup completed")
        except TimeoutError:
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

    # Early disable guard: environment variable override or settings flag
    _disable_env = os.getenv("CALENDARBOT_DISABLE_EPAPER", "")
    if _disable_env and _disable_env.lower() in ("1", "true"):
        print(
            "e-paper mode disabled by CALENDARBOT_DISABLE_EPAPER=1 or settings.epaper.enabled=false — exiting"
        )
        return 0

    if not getattr(settings.epaper, "enabled", True):
        print(
            "e-paper mode disabled by CALENDARBOT_DISABLE_EPAPER=1 or settings.epaper.enabled=false — exiting"
        )
        return 0

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
        context, _ = await _initialize_epaper_components(args)  # updated_settings unused

        # If initialization returned early because e-paper was disabled, exit cleanly
        if getattr(context, "disabled_by_config", False):
            return 0

        # Start background data fetching
        if not context.app:
            _raise_app_not_initialized()

        logger.debug("Starting background data fetching task...")
        context.fetch_task = asyncio.create_task(context.app.run_background_fetch())
        logger.debug("Background data fetching task started")

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
            import calendarbot.display.epaper.drivers.waveshare.epd4in2b_v2 as epd_module  # noqa: PLC0415

            has_real_gpio = getattr(epd_module, "_HAS_REAL_GPIO", False)

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
        # Check for SPI device files
        spi_devices = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev1.0", "/dev/spidev1.1"]
        spi_found = any(Path(device).exists() for device in spi_devices)

        # Check for GPIO filesystem
        gpio_base = Path("/sys/class/gpio")
        gpio_available = gpio_base.exists()

        logger.debug(
            f"Hardware detection: SPI devices found = {spi_found}, GPIO filesystem = {gpio_available}"
        )

        if not spi_found or not gpio_available:
            logger.info(
                f"E-paper hardware detection: FAILED - Missing hardware interfaces (SPI: {spi_found}, GPIO: {gpio_available})"
            )
            return False

        # Try to initialize the driver with real hardware
        try:
            if EPD4in2bV2 is None:
                logger.info("E-paper hardware detection: FAILED - EPD driver not available")
                return False
            test_driver = EPD4in2bV2()
            if hasattr(test_driver, "initialize") and test_driver.initialize():
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


def save_png_emulation(image: Any, cycle_number: Union[int, str]) -> tuple[Path, Optional[Path]]:
    """Save rendered image as PNG for emulation mode and also save a processed version
    showing how it would appear on the e-paper display.

    Args:
        image: PIL Image to save
        cycle_number: Render cycle number for filename (int or str)

    Returns:
        Tuple of (Path to saved PNG file, Path to saved processed BMP file)
    """
    # Create output directory if it doesn't exist
    output_dir = Path("epaper_output")
    output_dir.mkdir(exist_ok=True)

    # Generate filename with timestamp and cycle number
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if isinstance(cycle_number, str):
        base_filename = f"calendar_epaper_{timestamp}_{cycle_number}"
    else:
        base_filename = f"calendar_epaper_{timestamp}_cycle{cycle_number:03d}"

    png_filename = f"{base_filename}.png"
    processed_filename = f"{base_filename}_processed.bmp"

    png_path = output_dir / png_filename
    processed_path = output_dir / processed_filename

    # Save the original image
    image.save(png_path, "PNG")
    logger.debug(f"Saved PNG emulation: {png_path}")

    # Create and save the processed image
    from calendarbot.display.epaper.utils.image_processing import create_epaper_preview_image  # noqa: I001, PLC0415

    try:
        # Default thresholds for black/white/red conversion
        processed_image = create_epaper_preview_image(image, threshold=128, red_threshold=200)
        processed_image.save(processed_path, "BMP")
        logger.debug(f"Saved processed BMP emulation: {processed_path}")
    except Exception:
        logger.exception("Failed to create processed image")
        logger.debug(traceback.format_exc())
        # Return only the PNG path if processing fails
        return (png_path, None)

    return png_path, processed_path


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

    # Configure webserver for e-paper mode (different from web mode)
    # Use a different port to avoid conflicts with web mode
    settings.epaper.webserver_enabled = True
    settings.epaper.webserver_port = 8081

    # Note: Auto port conflict resolution is now controlled by --kill-duplicates flag
    # No longer forcing auto_kill_existing = True in epaper mode

    logger.debug("Applied e-paper mode setting overrides")
    return settings


__all__ = [
    "apply_epaper_mode_overrides",
    "detect_epaper_hardware",
    "run_epaper_mode",
    "save_png_emulation",
]
