"""
Central logging configuration for calendarbot_lite.

Provides optimized logging configuration for Pi Zero 2W deployment by suppressing
verbose debug logs from third-party libraries while maintaining important diagnostic
information.
"""

import logging
import os
from typing import Optional


def configure_lite_logging(debug_mode: bool = False, force_debug: Optional[bool] = None) -> None:
    """
    Configure logging levels for calendarbot_lite optimized for Pi Zero 2W performance.

    This function suppresses verbose DEBUG logs from noisy third-party libraries
    while keeping WARNING/ERROR/INFO logs for diagnostics. Debug mode can be
    overridden via environment variable for troubleshooting.

    Args:
        debug_mode: Whether to enable debug logging for calendarbot_lite modules
        force_debug: Override debug mode setting (None to use env var detection)

    Environment Variables:
        CALENDARBOT_DEBUG: Set to '1', 'true', 'yes' to force debug logging
        CALENDARBOT_LOG_LEVEL: Override root log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Check for debug override from environment
    env_debug = os.getenv("CALENDARBOT_DEBUG", "").lower() in ("1", "true", "yes")
    env_log_level = os.getenv("CALENDARBOT_LOG_LEVEL", "").upper()

    # Determine final debug mode
    if force_debug is not None:
        final_debug = force_debug
    elif env_debug:
        final_debug = True
    else:
        final_debug = debug_mode

    # Set root logger level
    root_level = logging.DEBUG if final_debug else logging.INFO
    if env_log_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
        root_level = getattr(logging, env_log_level)

    # Configure root logger - don't use force=True to preserve colorful formatters
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)

    # Only add basic config if no handlers exist (preserve colorful setup from __init__.py)
    if not root_logger.handlers:
        logging.basicConfig(
            level=root_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Logger level configuration for Pi Zero 2W optimization
    logger_config: dict[str, int] = {
        # Third-party libraries that generate excessive debug logs
        "aiohttp.access": logging.WARNING,  # HTTP access logs
        "aiohttp.server": logging.WARNING,  # Server debug logs
        "aiohttp.web": logging.INFO,  # Keep basic web logs
        "aiohttp.web_log": logging.WARNING,  # Access log details
        "httpx": logging.WARNING,  # HTTP client debug logs
        "asyncio": logging.WARNING,  # Event loop debug logs
        "urllib3.connectionpool": logging.WARNING,  # Connection pool logs
        "requests.packages.urllib3": logging.WARNING,  # Requests urllib3 logs
        # Common noisy libraries that might be used
        "charset_normalizer": logging.WARNING,
        "multipart": logging.WARNING,
        "icalendar": logging.INFO,  # Keep some ICS parsing info
    }

    # Configure calendarbot_lite module loggers based on debug mode
    calendarbot_lite_level = logging.DEBUG if final_debug else logging.INFO
    lite_modules = [
        "calendarbot_lite",
        "calendarbot_lite.server",
        "calendarbot_lite.lite_parser",
        "calendarbot_lite.lite_fetcher",
        "calendarbot_lite.lite_rrule_expander",
        "calendarbot_lite.lite_models",
        "calendarbot_lite.skipped_store",
    ]

    for module in lite_modules:
        logger_config[module] = calendarbot_lite_level

    # Apply logger configurations
    for logger_name, level in logger_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

    # Log the configuration that was applied
    root_logger = logging.getLogger()
    if final_debug:
        root_logger.info(
            "Debug logging enabled for calendarbot_lite modules. "
            "Third-party debug logs suppressed for Pi Zero 2W performance."
        )
    else:
        root_logger.info(
            "Production logging configuration applied. "
            "Debug logs suppressed for performance optimization."
        )


def reset_logging_to_debug() -> None:
    """
    Reset all loggers to DEBUG level for troubleshooting.

    This is a utility function to temporarily enable verbose logging
    for all modules when diagnosing issues.
    """
    logging.getLogger().setLevel(logging.DEBUG)

    # Reset specific loggers that were suppressed
    suppressed_loggers = [
        "aiohttp.access",
        "aiohttp.server",
        "aiohttp.web_log",
        "httpx",
        "asyncio",
        "urllib3.connectionpool",
        "requests.packages.urllib3",
        "charset_normalizer",
        "multipart",
    ]

    for logger_name in suppressed_loggers:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

    logging.getLogger().info("All loggers reset to DEBUG level for troubleshooting")


def get_logging_status() -> dict[str, str]:
    """
    Get current logging configuration status.

    Returns:
        Dictionary mapping logger names to their current levels
    """
    status = {}

    # Check root logger
    root_logger = logging.getLogger()
    status["root"] = logging.getLevelName(root_logger.level)

    # Check key loggers
    key_loggers = ["calendarbot_lite", "aiohttp.access", "aiohttp.server", "httpx", "asyncio"]

    for logger_name in key_loggers:
        logger = logging.getLogger(logger_name)
        status[logger_name] = logging.getLevelName(logger.level)

    return status
