"""UI integration for calendarbot_lite.

Provides adapters to run framebuffer_ui with the calendarbot_lite backend.
Supports both embedded backend (local) and remote backend connection modes,
plus windowed vs fullscreen display options.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import platform
import signal
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Classes
# ============================================================================


class UIError(Exception):
    """Base exception for UI integration errors."""



class BackendConnectionError(UIError):
    """Raised when cannot connect to backend."""



class DisplayInitError(UIError):
    """Raised when display initialization fails."""



# ============================================================================
# SDL Display Configuration
# ============================================================================


def configure_display_mode(mode: str) -> None:
    """Configure SDL environment variables for display mode.

    Args:
        mode: Display mode - either 'window' or 'fullscreen'

    Raises:
        ValueError: If mode is not 'window' or 'fullscreen'
    """
    if mode not in ("window", "fullscreen"):
        raise ValueError(f"Invalid display mode: {mode}. Must be 'window' or 'fullscreen'")

    system = platform.system()

    if mode == "window":
        # Windowed mode (for testing on Mac/Linux)
        if system != "Darwin":
            # Linux/other: Use x11 for windowed mode
            os.environ["SDL_VIDEODRIVER"] = "x11"
            logger.debug("Set SDL_VIDEODRIVER=x11 for windowed mode on %s", system)
        else:
            # Mac: Don't set SDL_VIDEODRIVER - let pygame auto-detect Cocoa
            logger.debug("Using default SDL driver for windowed mode on macOS")

        # Show mouse cursor in windowed mode
        os.environ["SDL_NOMOUSE"] = "0"
        logger.info("Configured SDL for windowed mode")

    else:  # fullscreen
        # Fullscreen mode (production on Raspberry Pi)
        if "SDL_VIDEODRIVER" not in os.environ:
            if system == "Linux":
                # Use kmsdrm for direct framebuffer access on Linux
                os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
                logger.debug("Set SDL_VIDEODRIVER=kmsdrm for fullscreen mode on Linux")
            else:
                logger.debug("Using default SDL driver for fullscreen mode on %s", system)

        # Hide mouse cursor in fullscreen mode
        if "SDL_NOMOUSE" not in os.environ:
            os.environ["SDL_NOMOUSE"] = "1"
            logger.debug("Set SDL_NOMOUSE=1 to hide cursor")

        logger.info("Configured SDL for fullscreen mode")


# ============================================================================
# Backend Integration
# ============================================================================


async def _start_local_backend(config: dict[str, Any]) -> None:
    """Start calendarbot_lite backend server in background.

    This function runs the backend server using the same _serve() function
    that the standalone backend uses. It's designed to run as a background
    asyncio task.

    Args:
        config: Backend configuration dictionary containing server settings
                (e.g., server_port, server_bind, ics sources, etc.)

    Raises:
        ImportError: If calendarbot_lite.api.server module is not available
    """
    try:
        from calendarbot_lite.api.server import _create_skipped_store_if_available, _serve
    except ImportError:
        logger.exception("Cannot import calendarbot_lite.api.server")
        raise

    # Create skipped event store (returns None if not available)
    skipped_store = _create_skipped_store_if_available()

    logger.info("Starting local backend server on port %s", config.get("server_port", 8080))

    # Run the server (this is a blocking coroutine)
    await _serve(config, skipped_store)


async def _wait_for_backend_ready(
    backend_url: str, max_wait_seconds: int = 30, check_interval: float = 0.5
) -> None:
    """Wait for backend to be ready by polling the health endpoint.

    Polls the /api/health endpoint until the backend signals it's ready
    to serve requests (initial refresh complete and event window initialized).

    Args:
        backend_url: Base URL of the backend (e.g., "http://localhost:8080")
        max_wait_seconds: Maximum time to wait before timing out (default: 30)
        check_interval: Initial interval between health checks in seconds (default: 0.5)

    Raises:
        BackendConnectionError: If backend doesn't become ready within timeout
        BackendConnectionError: If health endpoint is unreachable

    Example:
        await _wait_for_backend_ready("http://localhost:8080")
    """
    import aiohttp

    health_url = f"{backend_url}/api/health"
    start_time = asyncio.get_event_loop().time()
    attempts = 0
    current_interval = check_interval

    logger.info("Waiting for backend to be ready at %s", health_url)
    logger.debug("Max wait time: %ds, initial check interval: %.1fs", max_wait_seconds, check_interval)

    async with aiohttp.ClientSession() as session:
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_seconds:
                raise BackendConnectionError(
                    f"Backend did not become ready within {max_wait_seconds} seconds. "
                    f"Attempted {attempts} health checks. "
                    "Check backend logs for initialization errors."
                )

            attempts += 1

            try:
                # Try to fetch health endpoint
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in {200, 503}:
                        # Both 200 (ok) and 503 (degraded) are acceptable
                        # We just need the data_status fields
                        data = await response.json()

                        # Check if backend is ready
                        data_status = data.get("data_status", {})
                        initial_refresh_complete = data_status.get("initial_refresh_complete", False)

                        if initial_refresh_complete:
                            event_count = data_status.get("event_count", 0)
                            logger.info(
                                "Backend is ready! Initial refresh complete, event count: %d (waited %.1fs, %d attempts)",
                                event_count,
                                elapsed,
                                attempts,
                            )
                            return

                        # Backend started but not ready yet
                        logger.debug(
                            "Backend started but initial refresh not complete yet (attempt %d, elapsed %.1fs)",
                            attempts,
                            elapsed,
                        )

            except (TimeoutError, aiohttp.ClientError) as exc:
                # Backend not reachable yet, will retry
                logger.debug(
                    "Backend health check failed (attempt %d, elapsed %.1fs): %s",
                    attempts,
                    elapsed,
                    exc.__class__.__name__,
                )

            except Exception as exc:
                # Unexpected error
                logger.warning(
                    "Unexpected error during health check (attempt %d): %s",
                    attempts,
                    exc,
                )

            # Wait before next check with exponential backoff
            await asyncio.sleep(current_interval)

            # Exponential backoff: 0.5s → 1s → 2s (max)
            current_interval = min(current_interval * 2, 2.0)


# ============================================================================
# Main UI Integration Function
# ============================================================================


async def run_with_framebuffer_ui(
    backend_mode: str,
    display_mode: str,
    backend_url: Optional[str] = None,
    backend_config: Optional[dict[str, Any]] = None,
) -> None:
    """Run calendarbot_lite with framebuffer UI.

    This is the main integration function that coordinates the backend
    and frontend components. It can run in two modes:

    1. Local mode: Starts the backend server in a background task and
       connects the UI to localhost
    2. Remote mode: Connects the UI to an existing backend server

    Args:
        backend_mode: Either 'local' (start embedded backend) or 'remote'
                     (connect to existing backend)
        display_mode: Either 'window' (for testing) or 'fullscreen'
                     (for production deployment)
        backend_url: URL for remote backend. Required if backend_mode='remote'.
                    Example: "http://192.168.1.100:8080"
        backend_config: Configuration dict for local backend. Required if
                       backend_mode='local'. Contains server settings like
                       server_port, server_bind, ICS sources, etc.

    Raises:
        ValueError: If invalid backend_mode or missing required arguments
        BackendConnectionError: If cannot connect to backend
        DisplayInitError: If display initialization fails
        ImportError: If framebuffer_ui module is not available

    Example:
        # Local backend with windowed display
        await run_with_framebuffer_ui(
            backend_mode="local",
            display_mode="window",
            backend_config={"server_port": 8080}
        )

        # Remote backend with fullscreen display
        await run_with_framebuffer_ui(
            backend_mode="remote",
            display_mode="fullscreen",
            backend_url="http://192.168.1.100:8080"
        )
    """
    # Validate arguments
    if backend_mode not in ("local", "remote"):
        raise ValueError(f"Invalid backend_mode: {backend_mode}. Must be 'local' or 'remote'")

    if backend_mode == "remote" and backend_url is None:
        raise ValueError("backend_url is required when backend_mode='remote'")

    if backend_mode == "local" and backend_config is None:
        raise ValueError("backend_config is required when backend_mode='local'")

    # Step 1: Configure SDL display mode
    logger.info("Configuring display mode: %s", display_mode)
    try:
        configure_display_mode(display_mode)
    except Exception as exc:
        raise DisplayInitError(f"Failed to configure display mode: {exc}") from exc

    # Step 2: Start backend or determine backend URL
    backend_task: Optional[asyncio.Task[None]] = None
    effective_url: str

    if backend_mode == "local":
        # Start local backend in background task
        logger.info("Starting local backend server...")

        if backend_config is None:
            raise ValueError("backend_config must be provided when backend_mode='local'")
        backend_task = asyncio.create_task(_start_local_backend(backend_config))

        # Construct localhost URL
        host = backend_config.get("server_bind", "0.0.0.0")  # nosec B104 - intentional default for server bind
        port = backend_config.get("server_port", 8080)

        # If server binds to 0.0.0.0, client should connect to localhost
        if host == "0.0.0.0":  # nosec B104 - intentional check for all-interfaces bind
            host = "localhost"

        effective_url = f"http://{host}:{port}"

        # Wait for backend to be ready (polls health endpoint until initialized)
        # Use longer timeout for local backend on resource-constrained devices
        # (initial ICS refresh can take 60+ seconds on Pi Zero 2)
        logger.info("Waiting for backend initialization at %s", effective_url)
        await _wait_for_backend_ready(effective_url, max_wait_seconds=120)
        logger.info("Backend is ready and initialized")

    else:  # remote mode
        # Use provided backend URL
        if backend_url is None:
            raise ValueError("backend_url must be provided when backend_mode='remote'")
        effective_url = backend_url
        logger.info("Connecting to remote backend: %s", effective_url)

        # Wait for remote backend to be ready
        # Use moderate timeout for remote backend (may need initial refresh)
        logger.info("Waiting for remote backend to be ready")
        await _wait_for_backend_ready(effective_url, max_wait_seconds=60)
        logger.info("Remote backend is ready")

    # Step 3: Configure framebuffer UI to use the backend
    os.environ["CALENDARBOT_BACKEND_URL"] = effective_url

    # Import framebuffer_ui components
    try:
        from framebuffer_ui.config import Config as UIConfig
        from framebuffer_ui.main import CalendarKioskApp
    except ImportError as exc:
        # Clean up backend if it was started
        if backend_task is not None:
            backend_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await backend_task

        raise ImportError(
            f"framebuffer_ui module not available: {exc}. "
            "Install with: pip install pygame"
        ) from exc

    # Create UI configuration from environment
    ui_config = UIConfig.from_env()

    logger.info("Starting framebuffer UI")
    logger.info("  Backend URL: %s", effective_url)
    logger.info("  Display mode: %s", display_mode)
    logger.info("  Refresh interval: %ds", ui_config.refresh_interval)

    # Step 4: Create and run the UI application
    app = CalendarKioskApp(ui_config)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig: int) -> None:
        logger.info("Received signal: %s", sig)
        app.running = False  # Immediately stop the loop

    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda s: signal_handler(s), sig)

    try:
        # Run the UI main loop (blocking until quit)
        await app.run()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")

    except Exception:
        logger.exception("UI terminated with error")
        raise

    finally:
        # Step 5: Graceful shutdown
        logger.info("Shutting down UI...")

        # Shutdown the UI app (stops loop, closes API client)
        try:
            await app.shutdown()
        except Exception:
            logger.exception("Error during UI shutdown")

        # Clean up pygame (must be done AFTER run() exits)
        try:
            app.renderer.cleanup()
            logger.debug("Renderer cleaned up")
        except Exception:
            logger.exception("Error during renderer cleanup")

        # Stop local backend if running
        if backend_task is not None:
            logger.info("Stopping local backend...")
            backend_task.cancel()

            # Wait for backend to stop
            try:
                await backend_task
            except asyncio.CancelledError:
                logger.debug("Backend task cancelled successfully")
            except Exception:
                logger.exception("Error during backend shutdown")

        logger.info("Shutdown complete")


__all__ = [
    "BackendConnectionError",
    "DisplayInitError",
    "UIError",
    "configure_display_mode",
    "run_with_framebuffer_ui",
]
