"""Enhanced logging configuration and setup utilities."""

import logging
import logging.handlers
import os
import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, List, Optional, Union

# Lazy imports moved to function level to avoid circular dependencies

if TYPE_CHECKING:
    from config.settings import CalendarBotSettings

    from ..display.manager import DisplayManager

# Custom log level between INFO(20) and DEBUG(10)
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")


def verbose(self: logging.Logger, message: Any, *args: Any, **kwargs: Any) -> None:
    """Add verbose() method to Logger class for detailed diagnostic logging.

    This method extends the standard logging.Logger class with a custom VERBOSE
    level (15) that provides more detailed output than INFO but less than DEBUG.
    Useful for operational visibility without debug-level verbosity.

    Args:
        self (logging.Logger): Logger instance (automatically provided)
        message (Any): Log message or format string
        *args (Any): Arguments for string formatting
        **kwargs (Any): Additional keyword arguments for logging

    Example:
        >>> logger = logging.getLogger(__name__)
        >>> logger.verbose("Detailed operation info: %s", operation_details)
        >>> logger.verbose("Processing %d items", item_count, extra={'operation': 'batch'})
    """
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kwargs)


# Add verbose method to all Logger instances
logging.Logger.verbose = verbose  # type: ignore[attr-defined]


def get_log_level(level_name: str) -> int:
    """Get numeric log level from string name, including custom VERBOSE level.

    Converts string log level names to their numeric equivalents, with support
    for the custom VERBOSE level (15) in addition to standard Python logging levels.

    Args:
        level_name (str): Log level name (DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        int: Numeric log level value for use with logging methods

    Raises:
        AttributeError: If level name is not recognized or invalid

    Example:
        >>> level = get_log_level("VERBOSE")
        >>> print(level)  # 15
        >>>
        >>> level = get_log_level("INFO")
        >>> print(level)  # 20
        >>>
        >>> # Case insensitive
        >>> level = get_log_level("debug")
        >>> print(level)  # 10
    """
    level_name = level_name.upper()
    if level_name == "VERBOSE":
        return VERBOSE
    level: int = getattr(logging, level_name)
    return level


class AutoColoredFormatter(logging.Formatter):
    """Formatter that auto-detects terminal color support."""

    # Color schemes for different terminal types
    COLORS = {
        "ERROR": {"truecolor": "\033[91m", "basic": "\033[31m", "none": ""},
        "INFO": {"truecolor": "\033[94m", "basic": "\033[34m", "none": ""},
        "VERBOSE": {"truecolor": "\033[92m", "basic": "\033[32m", "none": ""},
        "WARNING": {"truecolor": "\033[93m", "basic": "\033[33m", "none": ""},
        "DEBUG": {"truecolor": "\033[95m", "basic": "\033[35m", "none": ""},
        "CRITICAL": {"truecolor": "\033[91m\033[1m", "basic": "\033[31m\033[1m", "none": ""},
        "RESET": {"truecolor": "\033[0m", "basic": "\033[0m", "none": ""},
    }

    def __init__(self, *args: Any, enable_colors: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.enable_colors = enable_colors
        self.color_mode = self._detect_color_support() if enable_colors else "none"

    def _detect_color_support(self) -> str:
        """Auto-detect terminal color capabilities."""
        # Check if output is not a TTY
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return "none"

        # Check environment variables
        term = os.environ.get("TERM", "").lower()
        colorterm = os.environ.get("COLORTERM", "").lower()

        # Check for dumb terminal first (highest priority)
        if term == "dumb":
            return "none"

        # Check for truecolor support
        if colorterm in ("truecolor", "24bit") or "256color" in term:
            return "truecolor"

        # Check for basic color support
        if term and "color" in term:
            return "basic"

        # Windows Terminal detection
        if os.name == "nt" and "WT_SESSION" in os.environ:
            return "truecolor"

        return "none"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors if supported."""
        # Get base formatted message
        formatted = super().format(record)

        if self.color_mode == "none":
            return formatted

        # Apply colors to level name
        level_name = record.levelname
        if level_name in self.COLORS:
            color_start = self.COLORS[level_name][self.color_mode]
            color_end = self.COLORS["RESET"][self.color_mode]

            # Replace level name with colored version
            colored_level = f"{color_start}{level_name}{color_end}"
            formatted = formatted.replace(level_name, colored_level, 1)

        return formatted


class TimestampedFileHandler(logging.FileHandler):
    """Handler that creates timestamped log files per execution."""

    def __init__(
        self, log_dir: Union[str, Path], prefix: str = "calendarbot", max_files: int = 5
    ) -> None:
        self.log_dir = Path(log_dir)
        self.prefix = prefix
        self.max_files = max_files

        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.log"
        log_path = self.log_dir / filename

        # Ensure directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize parent FileHandler
        super().__init__(str(log_path), encoding="utf-8")

        # Clean up old files
        self.cleanup_old_files()

    def cleanup_old_files(self) -> None:
        """Remove log files beyond max_files limit, keeping most recent."""
        pattern = f"{self.prefix}_*.log"
        log_files = list(self.log_dir.glob(pattern))

        if len(log_files) > self.max_files:
            # Sort by modification time (most recent first)
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Remove oldest files
            for old_file in log_files[self.max_files :]:
                try:
                    old_file.unlink()
                except OSError:
                    pass  # Ignore cleanup errors


class SplitDisplayHandler(logging.Handler):
    """Handler that maintains a reserved log area in interactive mode."""

    def __init__(self, display_manager: "DisplayManager", max_log_lines: int = 5) -> None:
        super().__init__()
        self.display_manager = display_manager
        self.max_log_lines = max_log_lines
        self.log_buffer: Deque[str] = deque(maxlen=max_log_lines)

    def emit(self, record: logging.LogRecord) -> None:
        """Add log record to buffer and trigger display update."""
        try:
            formatted_msg = self.format(record)
            self.log_buffer.append(formatted_msg)

            # Update display manager's log area
            if self.display_manager.renderer is not None and hasattr(
                self.display_manager.renderer, "update_log_area"
            ):
                self.display_manager.renderer.update_log_area(list(self.log_buffer))
        except Exception:
            # Don't let logging errors break the application
            pass


def setup_enhanced_logging(
    settings: "CalendarBotSettings",
    interactive_mode: bool = False,
    display_manager: Optional["DisplayManager"] = None,
) -> logging.Logger:
    """Set up enhanced logging system with all features including security, performance, structured logging, and production optimization."""

    # Lazy imports to avoid circular dependencies
    from ..monitoring import PerformanceLogger, init_performance_logging
    from ..optimization import LoggingOptimizer, ProductionLogFilter
    from ..security import SecurityEventLogger, init_security_logging
    from ..structured import StructuredLogger, init_structured_logging

    # Create main logger
    logger = logging.getLogger("calendarbot")
    logger.setLevel(logging.DEBUG)  # Allow all levels, handlers will filter

    # Clear existing handlers
    logger.handlers.clear()

    # 1. Initialize New Logging Infrastructure
    # Initialize security logging
    security_logger = init_security_logging(settings)
    logger.info("Security event logging initialized")

    # Initialize performance monitoring
    performance_monitor = init_performance_logging(settings)
    logger.info("Performance monitoring initialized")

    # Initialize structured logging
    structured_logger = init_structured_logging(settings)
    logger.info("Structured logging initialized")

    # Initialize production optimization
    optimizer = LoggingOptimizer(settings)
    logger.info("Production log optimization initialized")

    # 2. Console Handler (if enabled)
    if settings.logging.console_enabled:
        console_level = get_log_level(settings.logging.console_level)

        # Auto-detecting color formatter
        console_formatter = AutoColoredFormatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
            enable_colors=settings.logging.console_colors,
        )

        # Add split display handler for interactive mode
        if interactive_mode and settings.logging.interactive_split_display and display_manager:
            split_handler = SplitDisplayHandler(
                display_manager, max_log_lines=settings.logging.interactive_log_lines
            )
            split_handler.setLevel(console_level)
            split_handler.setFormatter(console_formatter)

            # Apply production optimization filters to console
            from ..optimization import ProductionLogFilter

            production_filter = ProductionLogFilter(optimizer.rules, settings)
            split_handler.addFilter(production_filter)

            logger.addHandler(split_handler)
        else:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(console_level)
            console_handler.setFormatter(console_formatter)

            # Apply production optimization filters to console - but allow INFO+ through
            from ..optimization import ProductionLogFilter

            # Create console-friendly filter rules (suppress only DEBUG, allow INFO+)
            console_rules = [
                rule
                for rule in optimizer.rules
                if not rule.suppress or rule.level_threshold != logging.DEBUG
            ]
            production_filter = ProductionLogFilter(console_rules, settings)
            console_handler.addFilter(production_filter)

            logger.addHandler(console_handler)

            # Ensure console shows INFO level for development visibility
            if console_level > logging.INFO:
                console_handler.setLevel(logging.INFO)
                logger.info("Console logging enabled at INFO level for development visibility")

    # 3. File Handler (if enabled)
    if settings.logging.file_enabled:
        # Determine log directory
        if settings.logging.file_directory:
            log_dir = Path(settings.logging.file_directory)
        else:
            log_dir = settings.data_dir / "logs"

        # Timestamped file handler
        file_handler = TimestampedFileHandler(
            log_dir=log_dir,
            prefix=settings.logging.file_prefix,
            max_files=settings.logging.max_log_files,
        )

        file_level = get_log_level(settings.logging.file_level)
        file_handler.setLevel(file_level)

        # Use structured formatter for file logs if enabled
        if hasattr(settings.logging, "structured_format") and settings.logging.structured_format:
            from ..structured.logging import StructuredFormatter

            file_formatter: logging.Formatter = StructuredFormatter(
                format_type="json", include_context=True, include_source=True
            )
        else:
            # Detailed file formatter
            if settings.logging.include_function_names:
                file_format = (
                    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
                )
            else:
                file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

            file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")

        file_handler.setFormatter(file_formatter)

        # Apply production optimization filters to file handler
        from ..optimization import ProductionLogFilter

        production_filter = ProductionLogFilter(optimizer.rules, settings)
        file_handler.addFilter(production_filter)

        logger.addHandler(file_handler)

        logger.info(f"Enhanced logging to file: {file_handler.baseFilename}")

    # 4. Configure third-party library levels
    third_party_level = get_log_level(settings.logging.third_party_level)
    for lib in ["aiohttp", "urllib3", "msal", "asyncio"]:
        logging.getLogger(lib).setLevel(third_party_level)

    # 5. Store references for access by other modules
    # Type ignore because we're dynamically adding attributes to logger
    logger._security_logger = security_logger  # type: ignore[attr-defined]
    logger._performance_monitor = performance_monitor  # type: ignore[attr-defined]
    logger._structured_logger = structured_logger  # type: ignore[attr-defined]
    logger._optimizer = optimizer  # type: ignore[attr-defined]

    logger.info(
        "Enhanced logging system with security, performance, structured logging, and optimization initialized"
    )
    return logger


def setup_logging(
    log_level: str = "INFO", log_file: Optional[str] = None, log_dir: Optional[Path] = None
) -> logging.Logger:
    """Set up application logging with console and optional file output.

    Legacy function maintained for backward compatibility.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name
        log_dir: Optional log directory path

    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("calendarbot")
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    console_formatter = AutoColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / log_file
        else:
            log_path = Path(log_file)

        # Use rotating file handler to prevent large log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)  # File logs everything
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_path}")

    # Set third-party library log levels to reduce noise
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("msal").setLevel(logging.WARNING)

    logger.info(f"Logging initialized at {log_level} level")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module with CalendarBot namespace.

    Creates a properly namespaced logger instance for use within CalendarBot modules.
    All loggers are prefixed with 'calendarbot.' to maintain consistent logging
    hierarchy and enable proper filtering and configuration.

    Args:
        name (str): Logger name, typically the module's __name__ value

    Returns:
        logging.Logger: Configured logger instance with CalendarBot namespace

    Example:
        >>> # In a module file
        >>> logger = get_logger(__name__)
        >>> logger.info("Module operation completed")
        >>>
        >>> # Or with explicit name
        >>> cache_logger = get_logger("cache.manager")
        >>> cache_logger.debug("Cache operation details")
    """
    return logging.getLogger(f"calendarbot.{name}")


def apply_command_line_overrides(
    settings: "CalendarBotSettings", args: Any
) -> "CalendarBotSettings":
    """Apply command-line argument overrides to logging settings.

    Processes command-line arguments and applies them to the logging configuration,
    following priority order: Command-line > Environment > YAML > Defaults.
    Modifies the settings object in-place and returns it for convenience.

    Args:
        settings (CalendarBotSettings): Current settings object to modify
        args (Any): Parsed command-line arguments from argparse

    Returns:
        CalendarBotSettings: Settings object with command-line overrides applied

    Example:
        >>> # Apply verbose logging from command line
        >>> settings = apply_command_line_overrides(settings, args)
        >>> if args.verbose:
        ...     print(f"Console level: {settings.logging.console_level}")  # "VERBOSE"
        >>>
        >>> # Apply quiet mode
        >>> if args.quiet:
        ...     print(f"Console level: {settings.logging.console_level}")  # "ERROR"
    """
    # Priority: Command-line > Environment > YAML > Defaults

    if hasattr(args, "log_level") and args.log_level:
        settings.logging.console_level = args.log_level
        settings.logging.file_level = args.log_level

    if hasattr(args, "verbose") and args.verbose:
        settings.logging.console_level = "VERBOSE"
        settings.logging.file_level = "VERBOSE"

    if hasattr(args, "quiet") and args.quiet:
        settings.logging.console_level = "ERROR"

    if hasattr(args, "log_dir") and args.log_dir:
        settings.logging.file_directory = args.log_dir

    if hasattr(args, "no_log_colors") and args.no_log_colors:
        settings.logging.console_colors = False

    if hasattr(args, "max_log_files") and args.max_log_files:
        settings.logging.max_log_files = args.max_log_files

    return settings
