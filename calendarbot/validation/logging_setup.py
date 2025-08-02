"""Enhanced logging setup for validation mode."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Optional


class ValidationFormatter(logging.Formatter):
    """Custom formatter for validation logging with component context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with enhanced information."""
        # Add timestamp with milliseconds - handle edge cases
        try:
            msecs = getattr(record, "msecs", 0)
            if msecs is None:
                msecs = 0
            record.msecs_formatted = f"{msecs:03.0f}"
        except (ValueError, TypeError):
            record.msecs_formatted = "000"

        # Extract component from logger name if possible - handle None names
        try:
            logger_name = getattr(record, "name", "") or ""
            logger_parts = logger_name.split(".")
            if len(logger_parts) >= 2 and logger_parts[0] == "calendarbot":
                record.component = logger_parts[1]
            else:
                record.component = "system"
        except (AttributeError, TypeError):
            record.component = "system"

        return super().format(record)


class ComponentFilter(logging.Filter):
    """Filter to only show logs from specific components."""

    def __init__(self, allowed_components: Optional[list[str]] = None):
        """Initialize component filter.

        Args:
            allowed_components: List of component names to allow, None for all
        """
        super().__init__()
        self.allowed_components = (
            set(allowed_components) if allowed_components is not None else None
        )

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on component."""
        if not self.allowed_components:
            return True

        # Extract component from logger name
        logger_parts = record.name.split(".")
        if len(logger_parts) >= 2 and logger_parts[0] == "calendarbot":
            component = logger_parts[1]
            return component in self.allowed_components

        # Allow system logs
        return "system" in self.allowed_components


def setup_validation_logging(
    verbose: bool = False, components: Optional[list[str]] = None, log_file: Optional[str] = None
) -> dict[str, logging.Logger]:
    """Set up enhanced logging for validation mode.

    Args:
        verbose: Enable verbose (DEBUG) logging
        components: List of components to log, None for all
        log_file: Optional log file path for detailed logging

    Returns:
        Dictionary of component-specific loggers
    """
    # Determine log level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create component-specific formatters
    console_formatter = ValidationFormatter(
        "%(asctime)s.%(msecs_formatted)s [%(component)8s] %(levelname)7s: %(message)s",
        datefmt="%H:%M:%S",
    )

    verbose_formatter = ValidationFormatter(
        "%(asctime)s.%(msecs_formatted)s [%(component)8s] %(levelname)7s %(funcName)s:%(lineno)d: %(message)s",
        datefmt="%H:%M:%S",
    )

    file_formatter = ValidationFormatter(
        "%(asctime)s.%(msecs_formatted)s [%(component)8s] %(levelname)7s %(name)s.%(funcName)s:%(lineno)d: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear existing handlers to avoid duplication
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(verbose_formatter if verbose else console_formatter)

    # Add component filter if specified
    if components:
        component_filter = ComponentFilter([*components, "system"])
        console_handler.addFilter(component_filter)

    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # Set up file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=3  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Create component-specific loggers
    component_loggers = {}
    component_names = ["sources", "cache", "display", "validation"]

    for component in component_names:
        logger = logging.getLogger(f"calendarbot.{component}")
        logger.setLevel(logging.DEBUG)
        component_loggers[component] = logger

    # Configure third-party library log levels to reduce noise
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("msal").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Create system logger for validation framework
    system_logger = logging.getLogger("calendarbot.validation.system")
    system_logger.setLevel(logging.DEBUG)
    component_loggers["system"] = system_logger

    # Log initialization
    system_logger.info("Validation logging initialized")
    if verbose:
        system_logger.debug("Verbose logging enabled")
    if components:
        system_logger.info(f"Component filter active: {', '.join(components)}")
    if log_file:
        system_logger.info(f"Detailed logging to: {log_file}")

    return component_loggers


def get_validation_logger(component: str) -> logging.Logger:
    """Get a validation logger for a specific component.

    Args:
        component: Component name (sources, cache, display, validation)

    Returns:
        Logger instance for the component
    """
    return logging.getLogger(f"calendarbot.{component}")


def log_validation_start(
    logger: logging.Logger, test_name: str, details: Optional[dict[str, Any]] = None
) -> None:
    """Log the start of a validation test.

    Args:
        logger: Logger to use
        test_name: Name of the test being started
        details: Optional test details
    """
    logger.info(f"Starting validation: {test_name}")
    if details:
        for key, value in details.items():
            logger.debug(f"  {key}: {value}")


def log_validation_result(
    logger: logging.Logger,
    test_name: str,
    success: bool,
    message: str,
    duration_ms: Optional[int] = None,
) -> None:
    """Log the result of a validation test.

    Args:
        logger: Logger to use
        test_name: Name of the test
        success: Whether the test succeeded
        message: Result message
        duration_ms: Optional test duration in milliseconds
    """
    level = logging.INFO if success else logging.ERROR
    duration_str = f" ({duration_ms}ms)" if duration_ms else ""
    status = "PASSED" if success else "FAILED"

    logger.log(level, f"Validation {status}: {test_name} - {message}{duration_str}")
