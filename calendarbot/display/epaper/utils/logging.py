"""Logging utilities for e-Paper displays."""

import logging
import sys
from pathlib import Path
from typing import Optional

# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LEVEL = logging.INFO


def setup_logger(
    name: str,
    level: int | str = DEFAULT_LEVEL,
    log_format: str = DEFAULT_FORMAT,
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """Set up a logger with the specified configuration.

    Args:
        name: Name of the logger
        level: Logging level (default: INFO)
        log_format: Log message format
        log_file: Path to log file (optional)
        console: Whether to log to console

    Returns:
        Configured logger
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Add file handler if log_file is specified
    if log_file:
        # Create directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add console handler if console is True
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Name of the logger

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_level(logger: logging.Logger, level: int | str) -> None:
    """Set the log level for the specified logger.

    Args:
        logger: Logger to modify
        level: New log level
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(level)


def configure_package_logging(
    level: int | str = DEFAULT_LEVEL,
    log_format: str = DEFAULT_FORMAT,
    log_file: Optional[str] = None,
    console: bool = True,
) -> dict[str, logging.Logger]:
    """Configure logging for the entire package.

    Args:
        level: Logging level (default: INFO)
        log_format: Log message format
        log_file: Path to log file (optional)
        console: Whether to log to console

    Returns:
        Dictionary of configured loggers
    """
    # Configure root logger for the package
    root_logger = setup_logger(
        "calendarbot.display.epaper",
        level=level,
        log_format=log_format,
        log_file=log_file,
        console=console,
    )

    # Configure loggers for each module
    return {
        "root": root_logger,
        "display": setup_logger("calendarbot.display.epaper.display", level, log_format),
        "drivers": setup_logger("calendarbot.display.epaper.drivers", level, log_format),
        "drivers.waveshare": setup_logger(
            "calendarbot.display.epaper.drivers.waveshare", level, log_format
        ),
        "rendering": setup_logger("calendarbot.display.epaper.rendering", level, log_format),
        "utils": setup_logger("calendarbot.display.epaper.utils", level, log_format),
    }
