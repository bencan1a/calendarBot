"""calendarbot_lite - lightweight isolated app skeleton for CalendarBot.

This package provides a minimal entrypoint and stubs. It intentionally keeps imports
light so the package can be inspected without pulling in heavy runtime dependencies.
"""

__version__ = "0.1.0"

from typing import Optional


def _init_logging(level_name: Optional[str]) -> None:
    """Initialize root logging to stream to console.

    This sets a sensible default formatter and level so that import-time errors
    and early startup messages are visible on the console. Callers may adjust
    the level later (e.g. from config).

    For diagnostics this function will also honor the CALENDARBOT_DEBUG environment
    variable (truthy values: "1", "true", "yes") which forces DEBUG verbosity to
    surface parser/fetcher debug logs during troubleshooting without changing code.
    """
    import logging
    import os
    import sys

    # If CALENDARBOT_DEBUG is set to a truthy value, override the requested level.
    debug_env = os.environ.get("CALENDARBOT_DEBUG", "")
    if isinstance(debug_env, str) and debug_env.strip().lower() in ("1", "true", "yes", "on"):
        level_name = "DEBUG"

    root = logging.getLogger()
    # Only configure basic handler if no handlers are present to avoid duplicate output.
    if not root.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        # Prefer the lightweight external colorlog formatter when available for nicer console output.
        try:
            from colorlog import ColoredFormatter  # type: ignore[import-not-found]

            # Readable colorized format:
            # HH:MM:SS  LEVEL   logger.name: message
            # - Only the level is colorized to avoid all-green output.
            # - Level is left-aligned to 7 chars for column alignment.
            fmt = "%(asctime)s %(log_color)s%(levelname)-7s%(reset)s %(name)s: %(message)s"
            # Adjust level colors for better readability (INFO is intentionally neutral)
            log_colors = {
                "DEBUG": "cyan",
                "INFO": "green",
                "VERBOSE": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
            formatter = ColoredFormatter(fmt, datefmt="%H:%M:%S", log_colors=log_colors)
        except Exception:
            # Fall back to plain logging if colorlog isn't installed.
            fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
            formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")

        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Coerce provided level name (case-insensitive) to a logging level.
    level = logging.INFO
    if isinstance(level_name, str):
        try:
            # Use public attribute lookup instead of private _nameToLevel
            level = getattr(logging, level_name.upper(), logging.INFO)
        except Exception:
            level = logging.INFO
    root.setLevel(level)
    logging.getLogger(__name__).debug(
        "Logging initialized at level %s", logging.getLevelName(level)
    )


def run_server(args: Optional[object] = None) -> None:
    """Start the calendarbot_lite server (with optional UI).

    This function attempts to import the runtime server implementation using
    importlib so we can capture and report import-time errors more clearly when
    running `python -m calendarbot_lite`. If the server module is present and
    provides the expected entrypoint ``start_server``, we delegate to it.

    Args:
        args: Optional command line arguments namespace containing --port, --ui, and other options

    Behavior:
    - Initialize console logging early using CALENDARBOT_LOG_LEVEL (env) if present.
    - After loading any environment/config defaults from the server helper, update
      the log level from cfg['log_level'] when available.
    - Apply command line argument overrides to configuration.
    - If args.ui == 'framebuffer': Run with framebuffer UI integration
    - Otherwise: Run backend-only (delegate to server's start_server(cfg, skipped))
    """
    # Initialize early logging so import-time / startup messages are visible.
    import asyncio
    import os
    import sys

    _init_logging(os.environ.get("CALENDARBOT_LOG_LEVEL"))

    import importlib
    import logging
    import traceback

    logger = logging.getLogger(__name__)

    try:
        server = importlib.import_module("calendarbot_lite.api.server")
    except Exception as exc:
        # Provide a useful developer-facing error that includes the underlying traceback.
        tb = "".join(traceback.format_exception(exc.__class__, exc, exc.__traceback__))
        logger.exception("Failed to import calendarbot_lite.api.server")
        raise NotImplementedError(
            "calendarbot_lite server not available. To continue development:\n"
            "  - Implement `calendarbot_lite.server` and expose `start_server()`.\n"
            "  - Run the package in dev mode with: python -m calendarbot_lite\n\n"
            f"Underlying import error:\n{tb}"
        ) from exc

    # Try to use server helpers to build defaults but continue if missing.
    cfg: dict = {}
    try:
        builder = getattr(server, "_build_default_config_from_env", None)
        if callable(builder):
            maybe_cfg = builder()
            if isinstance(maybe_cfg, dict):
                cfg = maybe_cfg
    except Exception:
        cfg = {}

    # Apply command line argument overrides to configuration
    if args is not None:
        port = getattr(args, "port", None)
        if port is not None:
            try:
                port_int = int(port)
                cfg["server_port"] = port_int
                logger.debug("Applied command line port override: %d", port_int)
            except (ValueError, TypeError) as e:
                logger.warning("Invalid port value from command line '%s': %s", port, e)

    # If config includes a log_level, ensure logging level matches it.
    try:
        cfg_level = None
        if isinstance(cfg, dict):
            cfg_level = cfg.get("log_level")
        if isinstance(cfg_level, str):
            logger.info("Applying configured log_level=%s", cfg_level)
            root = logging.getLogger()
            root.setLevel(getattr(logging, cfg_level.upper(), logging.INFO))
    except Exception:
        # Do not fail startup due to logging configuration issues.
        logger.debug("Failed to apply configured log level", exc_info=True)

    # Extract UI parameters from args
    ui_mode = getattr(args, "ui", "none")
    backend_mode = getattr(args, "backend", "local")
    display_mode = getattr(args, "display_mode", "fullscreen")
    backend_url = getattr(args, "backend_url", None)

    # Branch on UI mode
    if ui_mode == "framebuffer":
        # Run with framebuffer UI integration
        logger.info("Starting calendarbot_lite with framebuffer UI")

        # Import UI integration
        try:
            from calendarbot_lite.ui import run_with_framebuffer_ui
        except ImportError as exc:
            logger.error("framebuffer_ui module not available: %s", exc)
            print("\nError: framebuffer_ui dependencies not installed.", file=sys.stderr)
            print("Install with: pip install pygame", file=sys.stderr)
            sys.exit(1)

        # Validate arguments
        if backend_mode == "remote" and backend_url is None:
            logger.error("--backend-url required when --backend remote")
            print("\nError: --backend-url is required when using --backend remote", file=sys.stderr)
            sys.exit(1)

        # Run with UI (blocking)
        try:
            asyncio.run(
                run_with_framebuffer_ui(
                    backend_mode=backend_mode,
                    display_mode=display_mode,
                    backend_url=backend_url,
                    backend_config=cfg if backend_mode == "local" else None,
                )
            )
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            sys.exit(130)  # Standard exit code for SIGINT (128 + 2)
        except Exception:
            logger.exception("UI terminated unexpectedly")
            sys.exit(1)

    else:
        # Run backend-only (preserve existing behavior)
        logger.info("Starting calendarbot_lite backend (no UI)")

        skipped = None
        try:
            creator = getattr(server, "_create_skipped_store_if_available", None)
            if callable(creator):
                skipped = creator()
        except Exception:
            skipped = None

        start_fn = getattr(server, "start_server", None)
        if not callable(start_fn):
            raise NotImplementedError("calendarbot_lite server implementation missing start_server().")

        # Diagnostic startup information to help developers verify config/logging at launch.
        try:
            root_logger = logging.getLogger()
            logger.debug(
                "Effective root log level: %s", logging.getLevelName(root_logger.getEffectiveLevel())
            )
            # Only surface a small set of config keys to avoid leaking secrets into logs.
            if isinstance(cfg, dict):
                diagnostic_cfg = {
                    k: cfg.get(k) for k in ("sources", "log_level", "server_bind", "server_port")
                }
            else:
                diagnostic_cfg = str(cfg)
            logger.debug("Resolved configuration (diagnostic): %s", diagnostic_cfg)
        except Exception:
            logger.debug("Failed to emit startup diagnostics", exc_info=True)

        # Delegate and block until shutdown. Any exceptions will propagate to the caller.
        start_fn(cfg, skipped)
