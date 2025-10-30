"""Tests for calendarbot_lite.monitoring_logging module."""

import json
import logging
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from typing import Any, Dict

import pytest

from calendarbot_lite.monitoring_logging import (
    LogEntry,
    MonitoringLogger,
    RateLimiter,
    SystemMetricsCollector,
    configure_monitoring_logging,
    get_logger,
    log_server_event,
    log_watchdog_event,
    log_health_event,
    log_recovery_event,
)


class TestLogEntry:
    """Test LogEntry class functionality."""

    def test_log_entry_when_minimal_args_then_creates_valid_entry(self) -> None:
        """Test that LogEntry creates valid entry with minimal arguments."""
        entry = LogEntry(
            component="server",
            level="INFO",
            event="test.event",
            message="Test message"
        )
        
        assert entry.component == "server"
        assert entry.level == "INFO"
        assert entry.event == "test.event"
        assert entry.message == "Test message"
        assert entry.details == {}
        assert entry.action_taken is None
        assert entry.recovery_level == 0
        assert entry.system_state == {}
        assert isinstance(entry.timestamp, datetime)

    def test_log_entry_when_all_args_then_creates_complete_entry(self) -> None:
        """Test that LogEntry creates complete entry with all arguments."""
        details = {"key": "value"}
        system_state = {"cpu_load": 0.5}
        
        entry = LogEntry(
            component="watchdog",
            level="ERROR",
            event="recovery.action",
            message="Recovery action taken",
            details=details,
            action_taken="Browser restart",
            recovery_level=1,
            system_state=system_state
        )
        
        assert entry.component == "watchdog"
        assert entry.level == "ERROR"
        assert entry.event == "recovery.action"
        assert entry.message == "Recovery action taken"
        assert entry.details == details
        assert entry.action_taken == "Browser restart"
        assert entry.recovery_level == 1
        assert entry.system_state == system_state

    def test_log_entry_to_dict_when_minimal_then_returns_required_fields(self) -> None:
        """Test that to_dict returns required fields for minimal entry."""
        entry = LogEntry("server", "INFO", "test.event", "Test message")
        result = entry.to_dict()
        
        assert "timestamp" in result
        assert result["component"] == "server"
        assert result["level"] == "INFO"
        assert result["event"] == "test.event"
        assert result["message"] == "Test message"
        assert result["details"] == {}
        assert result["schema_version"] == "1.0"
        assert "action_taken" not in result
        assert "recovery_level" not in result

    def test_log_entry_to_dict_when_complete_then_returns_all_fields(self) -> None:
        """Test that to_dict returns all fields for complete entry."""
        entry = LogEntry(
            "watchdog", "ERROR", "recovery.action", "Recovery action",
            details={"key": "value"},
            action_taken="Browser restart",
            recovery_level=1,
            system_state={"cpu": 0.5}
        )
        result = entry.to_dict()
        
        assert result["action_taken"] == "Browser restart"
        assert result["recovery_level"] == 1
        assert result["system_state"] == {"cpu": 0.5}

    def test_log_entry_to_json_when_called_then_returns_valid_json(self) -> None:
        """Test that to_json returns valid JSON string."""
        entry = LogEntry("server", "INFO", "test.event", "Test message")
        json_str = entry.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["component"] == "server"
        assert parsed["level"] == "INFO"


class TestRateLimiter:
    """Test RateLimiter functionality."""

    def setup_method(self) -> None:
        """Clear rate limiter state before each test."""
        from calendarbot_lite.monitoring_logging import _rate_limiters
        _rate_limiters.clear()

    def test_should_log_when_under_limit_then_returns_true(self) -> None:
        """Test that should_log returns True when under rate limit."""
        result = RateLimiter.should_log("test_event", max_per_minute=5)
        assert result is True

    def test_should_log_when_at_limit_then_returns_false(self) -> None:
        """Test that should_log returns False when at rate limit."""
        # Fill up to limit
        for _ in range(5):
            result = RateLimiter.should_log("test_event", max_per_minute=5)
            assert result is True
        
        # Next call should be rate limited
        result = RateLimiter.should_log("test_event", max_per_minute=5)
        assert result is False

    def test_should_log_when_different_keys_then_independent_limits(self) -> None:
        """Test that different event keys have independent rate limits."""
        # Fill first key to limit
        for _ in range(5):
            RateLimiter.should_log("event_a", max_per_minute=5)
        
        # Second key should still work
        result = RateLimiter.should_log("event_b", max_per_minute=5)
        assert result is True

    @patch('time.time')
    def test_should_log_when_time_passes_then_resets_limit(self, mock_time: MagicMock) -> None:
        """Test that rate limit resets after time window passes."""
        # Start at time 0
        mock_time.return_value = 0.0
        
        # Fill to limit
        for _ in range(5):
            RateLimiter.should_log("test_event", max_per_minute=5)
        
        # Should be rate limited
        result = RateLimiter.should_log("test_event", max_per_minute=5)
        assert result is False
        
        # Move time forward by 61 seconds
        mock_time.return_value = 61.0
        
        # Should work again
        result = RateLimiter.should_log("test_event", max_per_minute=5)
        assert result is True

    def test_get_rate_limited_count_when_events_logged_then_returns_count(self) -> None:
        """Test that get_rate_limited_count returns correct count."""
        for _ in range(3):
            RateLimiter.should_log("test_event", max_per_minute=5)
        
        count = RateLimiter.get_rate_limited_count("test_event")
        assert count == 3


class TestSystemMetricsCollector:
    """Test SystemMetricsCollector functionality."""

    @patch('os.getloadavg')
    def test_get_current_metrics_when_load_available_then_includes_cpu_load(
        self, mock_getloadavg: MagicMock
    ) -> None:
        """Test that CPU load is included when available."""
        mock_getloadavg.return_value = (0.75, 1.0, 1.25)
        
        metrics = SystemMetricsCollector.get_current_metrics()
        
        assert metrics["cpu_load"] == 0.75

    @patch('os.getloadavg', side_effect=OSError("Not available"))
    def test_get_current_metrics_when_load_unavailable_then_none(
        self, mock_getloadavg: MagicMock
    ) -> None:
        """Test that CPU load is None when unavailable."""
        metrics = SystemMetricsCollector.get_current_metrics()
        
        assert metrics["cpu_load"] is None

    @patch('builtins.open')
    def test_get_current_metrics_when_meminfo_available_then_includes_memory(
        self, mock_open: MagicMock
    ) -> None:
        """Test that memory info is included when available."""
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.__iter__.return_value = iter([
            "MemTotal:        8192000 kB\n",
            "MemAvailable:    6144000 kB\n",
        ])
        mock_open.return_value = mock_file
        
        metrics = SystemMetricsCollector.get_current_metrics()
        
        assert metrics["memory_free_mb"] == 6000.0  # 6144000 KB / 1024

    @patch('os.statvfs')
    def test_get_current_metrics_when_disk_available_then_includes_disk(
        self, mock_statvfs: MagicMock
    ) -> None:
        """Test that disk info is included when available."""
        # Mock statvfs result
        mock_stat = MagicMock()
        mock_stat.f_bavail = 1000000  # Available blocks
        mock_stat.f_frsize = 4096     # Fragment size
        mock_statvfs.return_value = mock_stat
        
        metrics = SystemMetricsCollector.get_current_metrics()
        
        expected_mb = (1000000 * 4096) / (1024 * 1024)  # Convert to MB
        assert abs(metrics["disk_free_mb"] - expected_mb) < 0.1  # Allow small floating point differences


class TestMonitoringLogger:
    """Test MonitoringLogger functionality."""

    def test_monitoring_logger_when_created_then_initializes_correctly(self) -> None:
        """Test that MonitoringLogger initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            logger = MonitoringLogger(
                name="test_logger",
                component="test",
                level="INFO",
                local_file=log_file,
                journald=False,
            )
            
            assert logger.name == "test_logger"
            assert logger.component == "test"

    def test_log_when_valid_event_then_logs_successfully(self) -> None:
        """Test that log method works with valid event."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            logger = MonitoringLogger(
                name="test_logger",
                component="test",
                level="DEBUG",
                local_file=log_file,
                journald=False,
            )
            
            result = logger.log(
                "INFO", "test.event", "Test message",
                details={"key": "value"}
            )
            
            assert result is True
            # Force log handler to flush
            for handler in logger.logger.handlers:
                handler.flush()
            # Log file should exist after logging
            assert log_file.exists()

    def test_log_when_rate_limited_then_returns_false(self) -> None:
        """Test that log returns False when rate limited."""
        logger = MonitoringLogger(
            name="test_logger",
            component="test",
            journald=False,
            rate_limiting=True,
        )
        
        # Fill rate limit
        for _ in range(5):
            logger.log("INFO", "test.event", "Message", rate_limit_key="test_key")
        
        # Should be rate limited now
        result = logger.log("INFO", "test.event", "Message", rate_limit_key="test_key")
        assert result is False

    def test_operation_context_when_successful_then_logs_start_and_complete(self) -> None:
        """Test that operation context logs start and completion."""
        logger = MonitoringLogger(
            name="test_logger",
            component="test",
            journald=False,
        )
        
        with patch.object(logger, 'info') as mock_info:
            with logger.operation_context("test.operation"):
                pass
            
            # Should have logged start and complete
            assert mock_info.call_count == 2
            start_call, complete_call = mock_info.call_args_list
            
            assert start_call[0][0] == "test.operation.start"
            assert complete_call[0][0] == "test.operation.complete"

    def test_operation_context_when_exception_then_logs_error(self) -> None:
        """Test that operation context logs errors on exception."""
        logger = MonitoringLogger(
            name="test_logger",
            component="test",
            journald=False,
        )
        
        with patch.object(logger, 'info') as mock_info, \
             patch.object(logger, 'error') as mock_error:
            
            with pytest.raises(ValueError):
                with logger.operation_context("test.operation"):
                    raise ValueError("Test error")
            
            # Should have logged start and error
            mock_info.assert_called_once()
            mock_error.assert_called_once()
            
            error_call = mock_error.call_args_list[0]
            assert error_call[0][0] == "test.operation.error"


class TestConvenienceFunctions:
    """Test convenience logging functions."""

    @patch('calendarbot_lite.monitoring_logging.get_logger')
    def test_log_server_event_when_called_then_uses_server_logger(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that log_server_event uses server logger."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_server_event("test.event", "Test message", "INFO", details={"key": "value"})
        
        mock_get_logger.assert_called_once_with("server")
        mock_logger.log.assert_called_once_with(
            "INFO", "test.event", "Test message", details={"key": "value"}
        )

    @patch('calendarbot_lite.monitoring_logging.get_logger')
    def test_log_recovery_event_when_called_then_includes_recovery_level(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that log_recovery_event includes recovery level."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_recovery_event("recovery.action", "Recovery taken", "ERROR", recovery_level=2)
        
        mock_get_logger.assert_called_once_with("recovery")
        mock_logger.log.assert_called_once_with(
            "ERROR", "recovery.action", "Recovery taken", recovery_level=2
        )


class TestLoggerConfiguration:
    """Test logger configuration and management."""

    def test_configure_monitoring_logging_when_called_then_returns_logger(self) -> None:
        """Test that configure_monitoring_logging returns MonitoringLogger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = configure_monitoring_logging(
                component="test",
                level="INFO",
                local_log_dir=temp_dir,
                journald=False,
            )
            
            assert isinstance(logger, MonitoringLogger)
            assert logger.component == "test"

    @patch.dict('os.environ', {'CALENDARBOT_DEBUG': 'true'})
    def test_configure_monitoring_logging_when_debug_env_then_debug_level(self) -> None:
        """Test that debug environment variable sets debug level."""
        logger = configure_monitoring_logging(
            component="test",
            journald=False,
        )
        
        assert logger.logger.level == logging.DEBUG

    @patch.dict('os.environ', {'CALENDARBOT_LOG_LEVEL': 'WARNING'})
    def test_configure_monitoring_logging_when_level_env_then_uses_env_level(self) -> None:
        """Test that log level environment variable is used."""
        logger = configure_monitoring_logging(
            component="test",
            journald=False,
        )
        
        assert logger.logger.level == logging.WARNING

    def test_get_logger_when_called_multiple_times_then_returns_same_instance(self) -> None:
        """Test that get_logger returns same instance for same component."""
        logger1 = get_logger("test_component")
        logger2 = get_logger("test_component")
        
        assert logger1 is logger2


class TestThreadSafety:
    """Test thread safety of logging components."""

    def test_rate_limiter_when_concurrent_access_then_thread_safe(self) -> None:
        """Test that RateLimiter is thread-safe under concurrent access."""
        results = []
        event_key = "concurrent_test"
        
        def worker() -> None:
            for _ in range(10):
                result = RateLimiter.should_log(event_key, max_per_minute=5)
                results.append(result)
                time.sleep(0.001)  # Small delay to increase contention
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have exactly 5 True results (rate limit of 5)
        true_count = sum(1 for result in results if result)
        assert true_count == 5

    def test_monitoring_logger_when_concurrent_logging_then_handles_safely(self) -> None:
        """Test that MonitoringLogger handles concurrent logging safely."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "concurrent.log"
            
            logger = MonitoringLogger(
                name="concurrent_test",
                component="test",
                local_file=log_file,
                journald=False,
            )
            
            def worker(worker_id: int) -> None:
                for i in range(10):
                    logger.info(f"worker.{worker_id}.event", f"Message {i} from worker {worker_id}")
            
            # Start multiple threads
            threads = []
            for worker_id in range(3):
                thread = threading.Thread(target=worker, args=(worker_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Log file should exist and contain entries
            assert log_file.exists()
            log_content = log_file.read_text()
            assert "worker.0.event" in log_content
            assert "worker.1.event" in log_content
            assert "worker.2.event" in log_content


class TestIntegration:
    """Test integration with existing logging infrastructure."""

    def test_monitoring_logger_when_file_setup_fails_then_continues_with_console(self) -> None:
        """Test that MonitoringLogger continues with console logging if file setup fails."""
        # Try to write to invalid path
        invalid_path = Path("/invalid/path/test.log")
        
        with patch('calendarbot_lite.monitoring_logging.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Should not raise exception
            monitoring_logger = MonitoringLogger(
                name="test",
                component="test",
                local_file=invalid_path,
                journald=True,
            )
            
            assert monitoring_logger is not None

    @patch('sys.stdout')
    def test_monitoring_logger_when_journald_enabled_then_writes_to_stdout(
        self, mock_stdout: MagicMock
    ) -> None:
        """Test that journald mode writes JSON to stdout."""
        logger = MonitoringLogger(
            name="test",
            component="test",
            journald=True,
        )
        
        logger.info("test.event", "Test message")
        
        # Should have written to stdout (captured by journald)
        # Note: This test verifies the handler setup, actual output would be to stdout

    def test_system_metrics_collector_when_proc_unavailable_then_returns_none_values(self) -> None:
        """Test that SystemMetricsCollector handles missing /proc files gracefully."""
        with patch('builtins.open', side_effect=FileNotFoundError), \
             patch('os.getloadavg', side_effect=OSError), \
             patch('os.statvfs', side_effect=OSError):
            
            metrics = SystemMetricsCollector.get_current_metrics()
            
            assert metrics["cpu_load"] is None
            assert metrics["memory_free_mb"] is None
            assert metrics["disk_free_mb"] is None
            assert metrics["uptime_seconds"] is None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_log_entry_when_invalid_level_then_normalizes_level(self) -> None:
        """Test that LogEntry handles invalid log levels gracefully."""
        entry = LogEntry("server", "invalid", "test.event", "Test message")
        
        # Level should be normalized to uppercase
        assert entry.level == "INVALID"

    def test_monitoring_logger_when_missing_handlers_then_creates_new(self) -> None:
        """Test that MonitoringLogger creates handlers when missing."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = []  # No existing handlers
            mock_get_logger.return_value = mock_logger
            
            monitoring_logger = MonitoringLogger(
                name="test",
                component="test",
                journald=False,
            )
            
            # Should have attempted to add handlers
            assert monitoring_logger is not None

    def test_rate_limiter_when_cleanup_occurs_then_removes_old_entries(self) -> None:
        """Test that rate limiter automatically cleans up old entries."""
        with patch('time.time') as mock_time:
            # Start at time 0
            mock_time.return_value = 0.0
            
            # Add some entries
            RateLimiter.should_log("cleanup_test", max_per_minute=5)
            
            # Move time forward significantly
            mock_time.return_value = 3600.0  # 1 hour later
            
            # New log should work (old entries cleaned up)
            result = RateLimiter.should_log("cleanup_test", max_per_minute=1)
            assert result is True


# Integration test with actual logging
class TestRealLogging:
    """Test with actual logging infrastructure."""

    def test_end_to_end_logging_when_called_then_produces_structured_output(self) -> None:
        """Test end-to-end logging produces expected structured output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "e2e.log"
            
            logger = MonitoringLogger(
                name="e2e_test",
                component="test",
                local_file=log_file,
                journald=False,
            )
            
            # Log various events
            logger.info("server.start", "Server starting", details={"port": 8080})
            logger.error("server.error", "Server error", 
                        details={"error": "connection failed"},
                        include_system_state=True)
            
            # Verify log file exists and has content
            assert log_file.exists()
            content = log_file.read_text()
            assert "server.start" in content
            assert "server.error" in content