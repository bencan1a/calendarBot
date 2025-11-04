"""Enhanced monitoring logging module for CalendarBot_Lite.

Provides centralized structured JSON logging with consistent field schema,
rate limiting, context managers, and multi-destination output support.
Optimized for Pi Zero 2W with minimal resource usage.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from collections import defaultdict, deque
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

# Global rate limiting state
_rate_limiters: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
_rate_limit_lock = threading.Lock()

# Global logger cache
_logger_cache: dict[str, MonitoringLogger] = {}

# Default log schema version
SCHEMA_VERSION = "1.0"

# Log levels mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class LogEntry:
    """Structured log entry with consistent schema."""

    def __init__(
        self,
        component: str,
        level: str,
        event: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        action_taken: Optional[str] = None,
        recovery_level: int = 0,
        system_state: Optional[dict[str, Any]] = None,
    ):
        """Initialize log entry.

        Args:
            component: Component name (server|watchdog|health|recovery)
            level: Log level (DEBUG|INFO|WARN|ERROR|CRITICAL)
            event: Short event code (e.g., "health.endpoint.check")
            message: Human readable description
            details: Additional context data
            action_taken: Description of any action taken
            recovery_level: Recovery escalation level (0-4)
            system_state: Current system metrics
        """
        self.timestamp = datetime.now(UTC)
        self.component = component
        self.level = level.upper()
        self.event = event
        self.message = message
        self.details = details or {}
        self.action_taken = action_taken
        self.recovery_level = recovery_level
        self.system_state = system_state or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary following the standard schema."""
        entry: dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "level": self.level,
            "event": self.event,
            "message": self.message,
            "details": self.details,
            "schema_version": SCHEMA_VERSION,
        }

        if self.action_taken:
            entry["action_taken"] = self.action_taken

        if self.recovery_level > 0:
            entry["recovery_level"] = self.recovery_level

        if self.system_state:
            entry["system_state"] = self.system_state

        return entry

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


class RateLimiter:
    """Rate limiting for repeated error messages."""

    @staticmethod
    def should_log(event_key: str, max_per_minute: int = 5) -> bool:
        """Check if event should be logged based on rate limits.

        Args:
            event_key: Unique key for the event type
            max_per_minute: Maximum events per minute

        Returns:
            True if event should be logged, False if rate limited
        """
        with _rate_limit_lock:
            now = time.time()
            events = _rate_limiters[event_key]

            # Remove events older than 1 minute
            while events and now - events[0] > 60:
                events.popleft()

            # Check if under rate limit
            if len(events) < max_per_minute:
                events.append(now)
                return True

            return False

    @staticmethod
    def get_rate_limited_count(event_key: str) -> int:
        """Get count of rate limited events for the key."""
        with _rate_limit_lock:
            return len(_rate_limiters[event_key])


class SystemMetricsCollector:
    """Lightweight system metrics collection for Pi Zero 2W."""

    @staticmethod
    def get_current_metrics() -> dict[str, Any]:
        """Get current system metrics with fallbacks for missing data."""
        metrics: dict[str, Any] = {
            "cpu_load": None,
            "memory_free_mb": None,
            "disk_free_mb": None,
            "uptime_seconds": None,
        }

        # CPU load average (1 minute)
        try:
            load_avg = os.getloadavg()
            metrics["cpu_load"] = round(load_avg[0], 2)
        except (OSError, AttributeError):
            pass

        # Memory info
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        metrics["memory_free_mb"] = round(kb / 1024, 1)
                        break
        except (FileNotFoundError, ValueError, IndexError):
            pass

        # Disk space for root partition
        try:
            stat = os.statvfs("/")
            free_bytes = stat.f_bavail * stat.f_frsize
            metrics["disk_free_mb"] = round(free_bytes / (1024 * 1024), 1)
        except OSError:
            pass

        # System uptime
        try:
            with open("/proc/uptime", encoding="utf-8") as f:
                uptime = float(f.read().split()[0])
                metrics["uptime_seconds"] = int(uptime)
        except (FileNotFoundError, ValueError, IndexError):
            pass

        return metrics


class MonitoringLogger:
    """Enhanced monitoring logger with structured JSON output.

    IMPORTANT - Exception Handling:
        This logger does NOT have an exception() method. When logging errors
        within exception handlers, use the standard Python logger for traceback
        capture, then use MonitoringLogger.error() for structured event logging:

        Example:
            try:
                risky_operation()
            except Exception as e:
                logger.exception("Operation failed")  # Captures full traceback
                monitoring_logger.error(  # Structured event data only
                    "operation.failed",
                    "Operation encountered error",
                    details={"error_type": type(e).__name__, "error": str(e)}
                )

        This separation of concerns ensures:
        - Full exception tracebacks are logged to standard logs
        - Structured event data is logged for monitoring/alerting
        - MonitoringLogger maintains a clean, structured format
    """

    def __init__(
        self,
        name: str,
        component: str,
        level: str = "INFO",
        local_file: Optional[Path] = None,
        journald: bool = True,
        rate_limiting: bool = True,
        max_file_size_mb: int = 2,
        backup_count: int = 5,
    ):
        """Initialize monitoring logger.

        Args:
            name: Logger name
            component: Component identifier (server|watchdog|health|recovery)
            level: Default log level
            local_file: Optional local file path for structured logs
            journald: Enable journald output
            rate_limiting: Enable rate limiting for repeated messages
            max_file_size_mb: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.name = name
        self.component = component
        self.rate_limiting = rate_limiting

        # Create Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))

        # Avoid duplicate handlers if logger already exists
        if not self.logger.handlers:
            self._setup_handlers(local_file, journald, max_file_size_mb, backup_count)

    def _setup_handlers(
        self,
        local_file: Optional[Path],
        journald: bool,
        max_file_size_mb: int,
        backup_count: int,
    ) -> None:
        """Setup log handlers."""
        # Console handler for journald (systemd captures stdout)
        if journald:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.logger.level)
            console_handler.setFormatter(
                logging.Formatter("%(message)s")  # Raw JSON for journald
            )
            self.logger.addHandler(console_handler)

        # Local file handler with rotation
        if local_file:
            try:
                local_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.handlers.RotatingFileHandler(
                    local_file,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
                file_handler.setLevel(self.logger.level)
                file_handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
                )
                self.logger.addHandler(file_handler)
            except Exception as e:
                # Fallback to console logging if file setup fails
                self.logger.warning(f"Failed to setup file logging: {e}")

    def log(
        self,
        level: str,
        event: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        action_taken: Optional[str] = None,
        recovery_level: int = 0,
        include_system_state: bool = False,
        rate_limit_key: Optional[str] = None,
        max_per_minute: int = 5,
    ) -> bool:
        """Log a structured monitoring event.

        Args:
            level: Log level (DEBUG|INFO|WARN|ERROR|CRITICAL)
            event: Event code (e.g., "health.endpoint.fail")
            message: Human readable message
            details: Additional event details
            action_taken: Description of any action taken
            recovery_level: Recovery escalation level (0-4)
            include_system_state: Include current system metrics
            rate_limit_key: Optional rate limiting key
            max_per_minute: Rate limit threshold

        Returns:
            True if logged, False if rate limited
        """
        # Check rate limiting
        if (
            self.rate_limiting
            and rate_limit_key
            and not RateLimiter.should_log(rate_limit_key, max_per_minute)
        ):
            return False

        # Collect system state if requested
        system_state = None
        if include_system_state:
            system_state = SystemMetricsCollector.get_current_metrics()

        # Create log entry
        entry = LogEntry(
            component=self.component,
            level=level,
            event=event,
            message=message,
            details=details,
            action_taken=action_taken,
            recovery_level=recovery_level,
            system_state=system_state,
        )

        # Log to Python logger
        log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
        self.logger.log(log_level, entry.to_json())

        return True

    def debug(self, event: str, message: str, **kwargs: Any) -> bool:
        """Log debug event."""
        return self.log("DEBUG", event, message, **kwargs)

    def info(self, event: str, message: str, **kwargs: Any) -> bool:
        """Log info event."""
        return self.log("INFO", event, message, **kwargs)

    def warning(self, event: str, message: str, **kwargs: Any) -> bool:
        """Log warning event."""
        return self.log("WARN", event, message, **kwargs)

    def error(self, event: str, message: str, **kwargs: Any) -> bool:
        """Log error event."""
        return self.log("ERROR", event, message, **kwargs)

    def critical(self, event: str, message: str, **kwargs: Any) -> bool:
        """Log critical event."""
        return self.log("CRITICAL", event, message, **kwargs)

    @contextmanager
    def operation_context(
        self,
        operation: str,
        details: Optional[dict[str, Any]] = None,
        log_success: bool = True,
        log_failure: bool = True,
        include_duration: bool = True,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager for logging operation start/end.

        Args:
            operation: Operation name (e.g., "browser.restart")
            details: Additional context
            log_success: Log successful completion
            log_failure: Log failures/exceptions
            include_duration: Include operation duration in logs

        Yields:
            Context dictionary for operation tracking
        """
        start_time = time.time()
        context = {"operation": operation, "start_time": start_time}

        # Log operation start
        self.info(
            f"{operation}.start",
            f"Starting {operation}",
            details=details,
            include_system_state=True,
        )

        try:
            yield context

            # Log successful completion
            if log_success:
                duration_ms = int((time.time() - start_time) * 1000)
                success_details = {"duration_ms": duration_ms} if include_duration else {}
                if details:
                    success_details.update(details)

                self.info(
                    f"{operation}.complete",
                    f"Completed {operation} successfully",
                    details=success_details,
                )

        except Exception as e:
            # Log operation failure
            if log_failure:
                duration_ms = int((time.time() - start_time) * 1000)
                error_details: dict[str, Any] = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                if include_duration:
                    error_details["duration_ms"] = duration_ms
                if details:
                    error_details.update(details)

                self.error(
                    f"{operation}.error",
                    f"Failed {operation}: {e}",
                    details=error_details,
                    include_system_state=True,
                )

            raise


def configure_monitoring_logging(
    component: str,
    level: Optional[str] = None,
    local_log_dir: Optional[str | Path] = None,
    journald: bool = True,
    rate_limiting: bool = True,
) -> MonitoringLogger:
    """Configure monitoring logging for a component.

    Args:
        component: Component name (server|watchdog|health|recovery)
        level: Log level override from environment or config
        local_log_dir: Directory for local log files
        journald: Enable journald integration
        rate_limiting: Enable rate limiting

    Returns:
        Configured MonitoringLogger instance
    """
    # Determine log level with environment override
    log_level = level or os.environ.get("CALENDARBOT_LOG_LEVEL", "INFO")
    assert log_level is not None  # Guaranteed by the or expression with default
    if os.environ.get("CALENDARBOT_DEBUG", "").lower() in ("true", "1", "yes"):
        log_level = "DEBUG"

    # Setup local file path if directory provided
    local_file = None
    if local_log_dir:
        log_dir = Path(local_log_dir)
        local_file = log_dir / f"{component}.log"

    # Create logger
    logger_name = f"calendarbot.{component}"
    return MonitoringLogger(
        name=logger_name,
        component=component,
        level=log_level,
        local_file=local_file,
        journald=journald,
        rate_limiting=rate_limiting,
    )


def get_logger(component: str) -> MonitoringLogger:
    """Get or create a monitoring logger for a component.

    Args:
        component: Component name

    Returns:
        MonitoringLogger instance
    """
    # Check cache first
    if component in _logger_cache:
        return _logger_cache[component]

    # Create new monitoring logger and cache it
    monitoring_logger = configure_monitoring_logging(component)
    _logger_cache[component] = monitoring_logger

    return monitoring_logger


# Convenience functions for common usage patterns
def log_server_event(event: str, message: str, level: str = "INFO", **kwargs: Any) -> bool:
    """Log a server component event."""
    logger = get_logger("server")
    return logger.log(level, event, message, **kwargs)


def log_watchdog_event(event: str, message: str, level: str = "INFO", **kwargs: Any) -> bool:
    """Log a watchdog component event."""
    logger = get_logger("watchdog")
    return logger.log(level, event, message, **kwargs)


def log_health_event(event: str, message: str, level: str = "INFO", **kwargs: Any) -> bool:
    """Log a health check component event."""
    logger = get_logger("health")
    return logger.log(level, event, message, **kwargs)


def log_recovery_event(
    event: str, message: str, level: str = "INFO", recovery_level: int = 0, **kwargs: Any
) -> bool:
    """Log a recovery component event."""
    logger = get_logger("recovery")
    return logger.log(level, event, message, recovery_level=recovery_level, **kwargs)
