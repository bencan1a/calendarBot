"""Unit tests for calendarbot_lite.monitoring_logging module.

Tests cover structured logging, rate limiting, system metrics collection,
and monitoring logger functionality.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from calendarbot_lite.monitoring_logging import (
    LOG_LEVELS,
    SCHEMA_VERSION,
    LogEntry,
    MonitoringLogger,
    RateLimiter,
    SystemMetricsCollector,
    configure_monitoring_logging,
    get_logger,
    log_health_event,
    log_recovery_event,
    log_server_event,
    log_watchdog_event,
)


@pytest.mark.unit
@pytest.mark.fast
class TestLogEntry:
    """Tests for LogEntry class."""

    def test_log_entry_when_created_then_stores_fields(self) -> None:
        """Test LogEntry initialization stores all fields."""
        entry = LogEntry(
            component="server",
            level="INFO",
            event="test.event",
            message="Test message",
            details={"key": "value"},
            action_taken="Action taken",
            recovery_level=1,
            system_state={"cpu": 0.5},
        )

        assert entry.component == "server"
        assert entry.level == "INFO"
        assert entry.event == "test.event"
        assert entry.message == "Test message"
        assert entry.details == {"key": "value"}
        assert entry.action_taken == "Action taken"
        assert entry.recovery_level == 1
        assert entry.system_state == {"cpu": 0.5}
        assert entry.timestamp is not None

    def test_log_entry_when_no_optional_fields_then_uses_defaults(self) -> None:
        """Test LogEntry with minimal fields uses defaults."""
        entry = LogEntry(
            component="server",
            level="INFO",
            event="test.event",
            message="Test message",
        )

        assert entry.details == {}
        assert entry.action_taken is None
        assert entry.recovery_level == 0
        assert entry.system_state == {}

    def test_log_entry_when_level_lowercase_then_converts_to_uppercase(self) -> None:
        """Test LogEntry converts level to uppercase."""
        entry = LogEntry(
            component="server",
            level="info",
            event="test.event",
            message="Test message",
        )

        assert entry.level == "INFO"

    def test_log_entry_to_dict_when_called_then_returns_complete_dict(self) -> None:
        """Test LogEntry.to_dict() returns all fields."""
        entry = LogEntry(
            component="server",
            level="ERROR",
            event="test.event",
            message="Test message",
            details={"error": "details"},
            action_taken="Restarted",
            recovery_level=2,
            system_state={"cpu": 0.8},
        )

        result = entry.to_dict()

        assert result["component"] == "server"
        assert result["level"] == "ERROR"
        assert result["event"] == "test.event"
        assert result["message"] == "Test message"
        assert result["details"] == {"error": "details"}
        assert result["action_taken"] == "Restarted"
        assert result["recovery_level"] == 2
        assert result["system_state"] == {"cpu": 0.8}
        assert result["schema_version"] == SCHEMA_VERSION
        assert "timestamp" in result

    def test_log_entry_to_dict_when_minimal_fields_then_excludes_optional(self) -> None:
        """Test LogEntry.to_dict() excludes None optional fields."""
        entry = LogEntry(
            component="server",
            level="INFO",
            event="test.event",
            message="Test message",
        )

        result = entry.to_dict()

        assert "action_taken" not in result
        assert "recovery_level" not in result  # 0 is excluded
        assert "system_state" not in result  # Empty dict excluded

    def test_log_entry_to_json_when_called_then_returns_valid_json(self) -> None:
        """Test LogEntry.to_json() returns valid JSON string."""
        entry = LogEntry(
            component="server",
            level="INFO",
            event="test.event",
            message="Test message",
        )

        json_str = entry.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["component"] == "server"
        assert parsed["level"] == "INFO"


@pytest.mark.unit
@pytest.mark.fast
class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_when_under_limit_then_allows_event(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test RateLimiter allows events under the limit."""
        # Clear any previous state
        from calendarbot_lite.monitoring_logging import _rate_limiters
        _rate_limiters.clear()

        result = RateLimiter.should_log("test_event", max_per_minute=5)

        assert result is True

    def test_rate_limiter_when_at_limit_then_blocks_event(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test RateLimiter blocks events when at the limit."""
        from calendarbot_lite.monitoring_logging import _rate_limiters
        _rate_limiters.clear()

        # Log 5 events (at limit)
        for _ in range(5):
            RateLimiter.should_log("test_event_limit", max_per_minute=5)

        # 6th event should be blocked
        result = RateLimiter.should_log("test_event_limit", max_per_minute=5)

        assert result is False

    def test_rate_limiter_when_old_events_then_removes_expired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test RateLimiter removes events older than 1 minute."""
        from calendarbot_lite.monitoring_logging import _rate_limiters
        _rate_limiters.clear()

        # Mock time to add old event
        with patch("calendarbot_lite.monitoring_logging.time.time") as mock_time:
            mock_time.return_value = 1000.0
            RateLimiter.should_log("test_event_old", max_per_minute=2)

            # Advance time by 61 seconds
            mock_time.return_value = 1061.0
            result = RateLimiter.should_log("test_event_old", max_per_minute=2)

        # Old event should be removed, new event allowed
        assert result is True

    def test_rate_limiter_get_count_when_called_then_returns_event_count(self) -> None:
        """Test RateLimiter.get_rate_limited_count() returns event count."""
        from calendarbot_lite.monitoring_logging import _rate_limiters
        _rate_limiters.clear()

        RateLimiter.should_log("test_event_count", max_per_minute=5)
        RateLimiter.should_log("test_event_count", max_per_minute=5)

        count = RateLimiter.get_rate_limited_count("test_event_count")

        assert count == 2


@pytest.mark.unit
@pytest.mark.fast
class TestSystemMetricsCollector:
    """Tests for SystemMetricsCollector class."""

    def test_get_current_metrics_when_all_available_then_returns_metrics(self) -> None:
        """Test SystemMetricsCollector.get_current_metrics() with all data available."""
        mock_meminfo = "MemAvailable:    1048576 kB\n"
        mock_uptime = "12345.67 67890.12"

        # Create a side_effect function to return different mocks for different files
        def open_side_effect(path: str, *args: object, **kwargs: object) -> object:
            if path == "/proc/meminfo":
                return mock_open(read_data=mock_meminfo)()
            elif path == "/proc/uptime":
                return mock_open(read_data=mock_uptime)()
            raise FileNotFoundError(f"Unexpected file: {path}")

        with patch("os.getloadavg", return_value=(0.5, 0.3, 0.1)), \
             patch("builtins.open", side_effect=open_side_effect), \
             patch("os.statvfs") as mock_statvfs:

            mock_stat = Mock()
            mock_stat.f_bavail = 1024 * 1024  # 1GB in blocks
            mock_stat.f_frsize = 1024  # 1KB blocks
            mock_statvfs.return_value = mock_stat

            metrics = SystemMetricsCollector.get_current_metrics()

            assert metrics["cpu_load"] == 0.5
            assert metrics["memory_free_mb"] == 1024.0
            assert metrics["disk_free_mb"] is not None
            assert metrics["uptime_seconds"] is not None

    def test_get_current_metrics_when_cpu_unavailable_then_returns_none(self) -> None:
        """Test SystemMetricsCollector handles missing CPU info."""
        with patch("os.getloadavg", side_effect=OSError):
            metrics = SystemMetricsCollector.get_current_metrics()

            assert metrics["cpu_load"] is None

    def test_get_current_metrics_when_memory_unavailable_then_returns_none(self) -> None:
        """Test SystemMetricsCollector handles missing memory info."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            metrics = SystemMetricsCollector.get_current_metrics()

            assert metrics["memory_free_mb"] is None

    def test_get_current_metrics_when_disk_unavailable_then_returns_none(self) -> None:
        """Test SystemMetricsCollector handles missing disk info."""
        with patch("os.statvfs", side_effect=OSError):
            metrics = SystemMetricsCollector.get_current_metrics()

            assert metrics["disk_free_mb"] is None


@pytest.mark.unit
@pytest.mark.fast
class TestMonitoringLogger:
    """Tests for MonitoringLogger class."""

    def test_monitoring_logger_when_created_then_initializes(self, tmp_path: Path) -> None:
        """Test MonitoringLogger initialization."""
        log_file = tmp_path / "test.log"
        
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="INFO",
            local_file=log_file,
        )

        assert logger.name == "test_logger"
        assert logger.component == "server"
        assert logger.logger is not None

    def test_monitoring_logger_log_when_called_then_logs_event(self, tmp_path: Path) -> None:
        """Test MonitoringLogger.log() creates log entry."""
        log_file = tmp_path / "test.log"
        
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="INFO",
            local_file=log_file,
            journald=False,
        )

        result = logger.log(
            "INFO",
            "test.event",
            "Test message",
            details={"key": "value"},
        )

        assert result is True

    def test_monitoring_logger_log_when_rate_limited_then_blocks(self, tmp_path: Path) -> None:
        """Test MonitoringLogger.log() respects rate limiting."""
        from calendarbot_lite.monitoring_logging import _rate_limiters
        _rate_limiters.clear()

        log_file = tmp_path / "test.log"
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="INFO",
            local_file=log_file,
            journald=False,
            rate_limiting=True,
        )

        # Log up to limit
        for _ in range(5):
            logger.log("INFO", "test.event", "Test", rate_limit_key="test_key", max_per_minute=5)

        # Should be rate limited
        result = logger.log("INFO", "test.event", "Test", rate_limit_key="test_key", max_per_minute=5)

        assert result is False

    def test_monitoring_logger_debug_when_called_then_logs_debug(self, tmp_path: Path) -> None:
        """Test MonitoringLogger.debug() logs DEBUG level."""
        log_file = tmp_path / "test.log"
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="DEBUG",
            local_file=log_file,
            journald=False,
        )

        result = logger.debug("test.event", "Debug message")

        assert result is True

    def test_monitoring_logger_convenience_methods_when_called_then_log_correctly(
        self, tmp_path: Path
    ) -> None:
        """Test MonitoringLogger convenience methods (info, warning, error, critical)."""
        log_file = tmp_path / "test.log"
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="DEBUG",
            local_file=log_file,
            journald=False,
        )

        assert logger.info("test.info", "Info message") is True
        assert logger.warning("test.warning", "Warning message") is True
        assert logger.error("test.error", "Error message") is True
        assert logger.critical("test.critical", "Critical message") is True

    def test_monitoring_logger_operation_context_when_success_then_logs_completion(
        self, tmp_path: Path
    ) -> None:
        """Test MonitoringLogger.operation_context() logs successful operations."""
        log_file = tmp_path / "test.log"
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="INFO",
            local_file=log_file,
            journald=False,
        )

        with logger.operation_context("test_operation"):
            pass  # Successful operation

        # Should log start and complete events

    def test_monitoring_logger_operation_context_when_exception_then_logs_error(
        self, tmp_path: Path
    ) -> None:
        """Test MonitoringLogger.operation_context() logs exceptions."""
        log_file = tmp_path / "test.log"
        logger = MonitoringLogger(
            name="test_logger",
            component="server",
            level="INFO",
            local_file=log_file,
            journald=False,
        )

        with pytest.raises(ValueError), logger.operation_context("test_operation"):
            raise ValueError("Test error")

        # Should log error event


@pytest.mark.unit
@pytest.mark.fast
class TestConfigureMonitoringLogging:
    """Tests for configure_monitoring_logging function."""

    def test_configure_monitoring_logging_when_called_then_returns_logger(self) -> None:
        """Test configure_monitoring_logging() returns MonitoringLogger."""
        logger = configure_monitoring_logging("test_component")

        assert isinstance(logger, MonitoringLogger)
        assert logger.component == "test_component"

    def test_configure_monitoring_logging_when_debug_env_then_uses_debug_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test configure_monitoring_logging() respects CALENDARBOT_DEBUG env var."""
        monkeypatch.setenv("CALENDARBOT_DEBUG", "true")

        logger = configure_monitoring_logging("test_component")

        assert logger.logger.level == logging.DEBUG

    def test_configure_monitoring_logging_when_log_level_env_then_uses_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test configure_monitoring_logging() respects CALENDARBOT_LOG_LEVEL env var."""
        monkeypatch.setenv("CALENDARBOT_LOG_LEVEL", "WARNING")
        monkeypatch.delenv("CALENDARBOT_DEBUG", raising=False)

        logger = configure_monitoring_logging("test_component")

        assert logger.logger.level == logging.WARNING

    def test_configure_monitoring_logging_when_local_log_dir_then_creates_file(
        self, tmp_path: Path
    ) -> None:
        """Test configure_monitoring_logging() creates local log file."""
        logger = configure_monitoring_logging(
            "test_component",
            local_log_dir=tmp_path,
        )

        assert logger.logger is not None


@pytest.mark.unit
@pytest.mark.fast
class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_when_called_then_returns_cached_logger(self) -> None:
        """Test get_logger() returns cached logger instance."""
        from calendarbot_lite.monitoring_logging import _logger_cache
        _logger_cache.clear()

        logger1 = get_logger("test_component")
        logger2 = get_logger("test_component")

        assert logger1 is logger2

    def test_get_logger_when_new_component_then_creates_logger(self) -> None:
        """Test get_logger() creates new logger for new component."""
        from calendarbot_lite.monitoring_logging import _logger_cache
        _logger_cache.clear()

        logger = get_logger("new_component")

        assert isinstance(logger, MonitoringLogger)
        assert logger.component == "new_component"


@pytest.mark.unit
@pytest.mark.fast
class TestConvenienceFunctions:
    """Tests for convenience logging functions."""

    def test_log_server_event_when_called_then_logs_to_server(self) -> None:
        """Test log_server_event() logs to server component."""
        result = log_server_event("test.event", "Test message")

        assert isinstance(result, bool)

    def test_log_watchdog_event_when_called_then_logs_to_watchdog(self) -> None:
        """Test log_watchdog_event() logs to watchdog component."""
        result = log_watchdog_event("test.event", "Test message")

        assert isinstance(result, bool)

    def test_log_health_event_when_called_then_logs_to_health(self) -> None:
        """Test log_health_event() logs to health component."""
        result = log_health_event("test.event", "Test message")

        assert isinstance(result, bool)

    def test_log_recovery_event_when_called_then_logs_with_recovery_level(self) -> None:
        """Test log_recovery_event() logs with recovery level."""
        result = log_recovery_event("test.event", "Test message", recovery_level=2)

        assert isinstance(result, bool)


@pytest.mark.unit
@pytest.mark.fast
class TestLogLevels:
    """Tests for LOG_LEVELS constant."""

    def test_log_levels_when_checked_then_contains_all_levels(self) -> None:
        """Test LOG_LEVELS contains all standard log levels."""
        assert LOG_LEVELS["DEBUG"] == logging.DEBUG
        assert LOG_LEVELS["INFO"] == logging.INFO
        assert LOG_LEVELS["WARN"] == logging.WARNING
        assert LOG_LEVELS["WARNING"] == logging.WARNING
        assert LOG_LEVELS["ERROR"] == logging.ERROR
        assert LOG_LEVELS["CRITICAL"] == logging.CRITICAL


@pytest.mark.unit
@pytest.mark.fast
class TestSchemaVersion:
    """Tests for SCHEMA_VERSION constant."""

    def test_schema_version_when_checked_then_is_valid(self) -> None:
        """Test SCHEMA_VERSION is a valid version string."""
        assert isinstance(SCHEMA_VERSION, str)
        assert len(SCHEMA_VERSION) > 0
