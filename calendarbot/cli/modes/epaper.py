"""E-Paper mode handler for Calendar Bot CLI.

This module provides the e-paper display mode functionality for Calendar Bot,
including hardware detection, rendering, and PNG fallback capabilities.
E-paper is a CORE feature with automatic hardware detection and PNG emulation.
"""

import asyncio
import logging
import signal
from pathlib import Path
from typing import Any, Union

logger = logging.getLogger(__name__)


async def run_epaper_mode(args: Any) -> int:
    """Run Calendar Bot in e-paper display mode.

    Provides hardware detection with automatic PNG fallback when physical
    hardware is unavailable. Ensures identical visual output in both scenarios.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        from calendarbot.config.settings import settings
        from calendarbot.display.epaper.integration.eink_whats_next_renderer import (
            EInkWhatsNextRenderer,
        )
        from calendarbot.main import CalendarBot
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging

        from ..config import apply_cli_overrides

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

        # Create Calendar Bot instance
        app = CalendarBot()
        logger.debug("Created CalendarBot instance")

        # Initialize components
        if not await app.initialize():
            logger.error("Failed to initialize Calendar Bot")
            print("Failed to initialize Calendar Bot")
            return 1
        logger.info("Calendar Bot components initialized successfully")

        # Initialize e-paper renderer with hardware detection
        logger.info("Initializing e-paper renderer with hardware detection...")
        epaper_renderer = EInkWhatsNextRenderer(updated_settings)

        # Detect hardware and set up display mode
        hardware_available = detect_epaper_hardware()
        if hardware_available:
            logger.info("E-paper hardware detected - using physical display")
            print("E-paper hardware detected - rendering to physical display")
        else:
            logger.info("No e-paper hardware detected - using PNG emulation mode")
            print("No e-paper hardware detected - using PNG emulation (output saved to files)")

        # Start background data fetching
        logger.debug("Starting background data fetching task...")
        fetch_task = asyncio.create_task(app.run_background_fetch())
        logger.debug("Background data fetching task started")

        try:
            print("Starting Calendar Bot e-paper mode")
            print("Press Ctrl+C to stop")
            logger.debug("E-paper mode ready, entering main loop")

            # Main rendering loop
            render_count = 0
            while not shutdown_event.is_set():
                events = []  # Initialize events for error handling scope
                try:
                    logger.debug(f"Starting render cycle {render_count + 1}")

                    # Get fresh calendar data using correct cache manager method
                    events = await app.cache_manager.get_todays_cached_events()
                    logger.debug(f"Retrieved {len(events)} events for rendering")

                    # Create status info using correct cache manager methods
                    cache_status = await app.cache_manager.get_cache_status()
                    status_info = {
                        "is_cached": True,  # Using cached data from app
                        "last_update": (
                            getattr(cache_status, "last_update", None) if cache_status else None
                        ),
                    }

                    # Render to e-paper format
                    rendered_image = epaper_renderer.render_from_events(events, status_info)
                    logger.debug("Successfully rendered calendar to e-paper format")

                    # Update display (hardware or PNG file)
                    if hardware_available:
                        success = epaper_renderer.update_display(rendered_image)
                        if success:
                            logger.info(
                                f"Successfully updated e-paper display (cycle {render_count + 1})"
                            )
                        else:
                            logger.warning(
                                f"Failed to update e-paper display (cycle {render_count + 1})"
                            )
                    else:
                        # Save as PNG for emulation mode
                        output_path = save_png_emulation(rendered_image, render_count + 1)
                        logger.info(f"Saved PNG emulation to: {output_path}")
                        print(f"Calendar rendered to: {output_path}")

                    render_count += 1

                    # Wait before next update (e-paper displays don't need frequent updates)
                    logger.debug("Waiting for next render cycle...")
                    for _ in range(300):  # 5 minutes in 1-second intervals for responsive shutdown
                        if shutdown_event.is_set():
                            break
                        await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error in e-paper render cycle: {e}")
                    # Try to render error to display
                    try:
                        cached_events = events if "events" in locals() and events else []
                        error_image = epaper_renderer.render_error(str(e), cached_events)
                        if hardware_available:
                            epaper_renderer.update_display(error_image)
                        else:
                            error_path = save_png_emulation(
                                error_image, f"error_{render_count + 1}"
                            )
                            print(f"Error display saved to: {error_path}")
                    except Exception as render_error:
                        logger.error(f"Failed to render error display: {render_error}")

                    # Wait before retry
                    await asyncio.sleep(30)

            logger.info("Shutdown signal received, beginning graceful shutdown...")

        finally:
            logger.debug("Entering cleanup phase...")

            # Stop background fetching
            logger.debug("Cancelling background fetch task...")
            fetch_task.cancel()

            logger.debug("Waiting for background fetch task to complete...")
            try:
                await asyncio.wait_for(fetch_task, timeout=10.0)
                logger.debug("Background fetch task completed normally")
            except asyncio.CancelledError:
                logger.debug("Background fetch task cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Background fetch task did not cancel within 10 seconds")
            except Exception as e:
                logger.error(f"Unexpected error during background fetch task cancellation: {e}")

            # Cleanup
            try:
                logger.debug("Running application cleanup...")
                await asyncio.wait_for(app.cleanup(), timeout=10.0)
                logger.info("Application cleanup completed")
            except asyncio.TimeoutError:
                logger.warning("Application cleanup timed out after 10 seconds")
            except Exception as e:
                logger.error(f"Error during application cleanup: {e}")

        logger.info("E-paper mode completed successfully")
        return 0

    except Exception as e:
        # Use print instead of logger since logger might not be initialized yet
        print(f"E-paper mode error: {e}")
        import traceback

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
        # First try to detect real hardware drivers (Waveshare, etc.)
        try:
            from calendarbot.display.epaper.drivers.waveshare import EPD4in2bV2

            # Try to initialize real hardware
            test_driver = EPD4in2bV2()
            if test_driver.initialize():
                logger.info(
                    "E-paper hardware detection: SUCCESS - Physical Waveshare display detected"
                )
                return True
            logger.info("E-paper hardware detection: Physical driver failed to initialize")
        except ImportError:
            logger.debug("Waveshare drivers not available or hardware not connected")
        except Exception as e:
            logger.debug(f"Real hardware initialization failed: {e}")

        # If we reach here, no real hardware was detected
        logger.info(
            "E-paper hardware detection: FAILED - No physical hardware detected, using PNG fallback"
        )
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
    from datetime import datetime

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


def apply_epaper_mode_overrides(settings: Any, args: Any) -> Any:
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
