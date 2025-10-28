"""
Unit tests for environment-based monitoring toggle functionality.

Tests conditional monitoring system that can be disabled in production to reduce
resource overhead by 25MB memory and 2-5ms CPU per operation.
"""

import os
from unittest.mock import MagicMock, patch

# Import monitoring components
from calendarbot.monitoring import (
    NoOpPerformanceLogger,
    NoOpRuntimeResourceTracker,
    _is_monitoring_enabled,
)
from calendarbot.monitoring.performance import (
    get_performance_logger,
    init_performance_logging,
)
from calendarbot.monitoring.runtime_tracker import (
    get_runtime_tracker,
    init_runtime_tracking,
)


class TestEnvironmentToggle:
    """Test environment variable control for monitoring system."""

    def test_is_monitoring_enabled_when_true(self):
        """Test monitoring is enabled when CALENDARBOT_MONITORING=true."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "true"}):
            assert _is_monitoring_enabled() is True

    def test_is_monitoring_enabled_when_false(self):
        """Test monitoring is disabled when CALENDARBOT_MONITORING=false."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            assert _is_monitoring_enabled() is False

    def test_is_monitoring_enabled_when_missing(self):
        """Test monitoring defaults to disabled when environment variable missing."""
        with patch.dict(os.environ, {}, clear=True):
            if "CALENDARBOT_MONITORING" in os.environ:
                del os.environ["CALENDARBOT_MONITORING"]
            assert _is_monitoring_enabled() is False

    def test_is_monitoring_enabled_case_insensitive(self):
        """Test environment variable is case insensitive."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "TRUE"}):
            assert _is_monitoring_enabled() is True

        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "FALSE"}):
            assert _is_monitoring_enabled() is False


class TestNoOpPerformanceLogger:
    """Test NoOpPerformanceLogger behaves as expected."""

    def test_noop_logger_initialization(self):
        """Test NoOpPerformanceLogger can be initialized."""
        logger = NoOpPerformanceLogger()
        assert logger is not None

    def test_noop_logger_methods_work(self):
        """Test all NoOpPerformanceLogger methods work without errors."""
        logger = NoOpPerformanceLogger()

        # Test timer methods
        timer_id = logger.start_timer("test_operation")
        assert timer_id == "noop-timer"

        duration = logger.stop_timer(timer_id)
        assert duration == 0.0

        # Test logging methods - should not raise exceptions
        logger.log_request_performance("GET", "/test", 1.0, 200)
        logger.log_memory_usage()
        logger.log_cache_performance("test_cache", 10, 5, 15)
        logger.log_database_performance("SELECT", 0.5)

        # Test summary method
        summary = logger.get_performance_summary()
        assert summary["monitoring_disabled"] is True
        assert summary["total_metrics"] == 0

    def test_noop_logger_no_side_effects(self):
        """Test NoOpPerformanceLogger has no observable side effects."""
        logger = NoOpPerformanceLogger()

        # Multiple calls should not raise exceptions
        for i in range(100):
            timer_id = logger.start_timer(f"operation_{i}")
            logger.stop_timer(timer_id)
            logger.log_memory_usage()


class TestNoOpRuntimeResourceTracker:
    """Test NoOpRuntimeResourceTracker behaves as expected."""

    def test_noop_tracker_initialization(self):
        """Test NoOpRuntimeResourceTracker can be initialized."""
        tracker = NoOpRuntimeResourceTracker()
        assert tracker is not None

    def test_noop_tracker_methods_work(self):
        """Test all NoOpRuntimeResourceTracker methods work without errors."""
        tracker = NoOpRuntimeResourceTracker()

        # Test tracking methods
        session_id = tracker.start_tracking("test_session")
        assert session_id == "noop-session"

        result = tracker.stop_tracking()
        assert result is None

        sample = tracker.get_current_sample()
        assert sample is None

        status = tracker.get_tracking_status()
        assert status["tracking_active"] is False
        assert status["session_id"] is None
        assert status["sample_count"] == 0

        # Test context manager
        with tracker.track_execution("test_operation") as session:
            assert session == "noop-session"

    def test_noop_tracker_no_side_effects(self):
        """Test NoOpRuntimeResourceTracker has no observable side effects."""
        tracker = NoOpRuntimeResourceTracker()

        # Multiple calls should not raise exceptions
        for i in range(50):
            session_id = tracker.start_tracking(f"session_{i}")
            tracker.get_current_sample()
            tracker.stop_tracking()


class TestConditionalPerformanceLogging:
    """Test conditional performance logging based on environment."""

    def test_get_performance_logger_when_enabled(self):
        """Test get_performance_logger returns real logger when monitoring enabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "true"}):
            # Mock the real PerformanceLogger to avoid actual initialization
            with patch("calendarbot.monitoring.performance.PerformanceLogger") as mock_logger:
                mock_instance = MagicMock()
                mock_logger.return_value = mock_instance

                # Clear any cached logger
                import calendarbot.monitoring.performance

                calendarbot.monitoring.performance._performance_logger = None

                logger = get_performance_logger()
                assert logger is mock_instance
                mock_logger.assert_called_once()

    def test_get_performance_logger_when_disabled(self):
        """Test get_performance_logger returns NoOpPerformanceLogger when monitoring disabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            # Clear any cached logger
            import calendarbot.monitoring.performance

            calendarbot.monitoring.performance._performance_logger = None

            logger = get_performance_logger()
            assert isinstance(logger, NoOpPerformanceLogger)

    def test_init_performance_logging_when_enabled(self):
        """Test init_performance_logging creates real logger when monitoring enabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "true"}):
            # Mock the real PerformanceLogger
            with patch("calendarbot.monitoring.performance.PerformanceLogger") as mock_logger:
                mock_instance = MagicMock()
                mock_logger.return_value = mock_instance

                mock_settings = {"log_file": "tests/fixtures/test.log"}
                logger = init_performance_logging(mock_settings)

                assert logger is mock_instance
                mock_logger.assert_called_once_with(mock_settings)

    def test_init_performance_logging_when_disabled(self):
        """Test init_performance_logging creates NoOpPerformanceLogger when monitoring disabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            mock_settings = {"log_file": "tests/fixtures/test.log"}
            logger = init_performance_logging(mock_settings)

            assert isinstance(logger, NoOpPerformanceLogger)


class TestConditionalRuntimeTracking:
    """Test conditional runtime tracking based on environment."""

    def test_get_runtime_tracker_when_enabled(self):
        """Test get_runtime_tracker returns real tracker when monitoring enabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "true"}):
            # Mock the real RuntimeResourceTracker
            with patch(
                "calendarbot.monitoring.runtime_tracker.RuntimeResourceTracker"
            ) as mock_tracker:
                mock_instance = MagicMock()
                mock_tracker.return_value = mock_instance

                # Clear any cached tracker
                import calendarbot.monitoring.runtime_tracker

                calendarbot.monitoring.runtime_tracker._runtime_tracker = None

                tracker = get_runtime_tracker()
                assert tracker is mock_instance
                mock_tracker.assert_called_once()

    def test_get_runtime_tracker_when_disabled(self):
        """Test get_runtime_tracker returns NoOpRuntimeResourceTracker when monitoring disabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            # Clear any cached tracker
            import calendarbot.monitoring.runtime_tracker

            calendarbot.monitoring.runtime_tracker._runtime_tracker = None

            tracker = get_runtime_tracker()
            assert isinstance(tracker, NoOpRuntimeResourceTracker)

    def test_init_runtime_tracking_when_enabled(self):
        """Test init_runtime_tracking creates real tracker when monitoring enabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "true"}):
            # Mock the real RuntimeResourceTracker
            with patch(
                "calendarbot.monitoring.runtime_tracker.RuntimeResourceTracker"
            ) as mock_tracker:
                mock_instance = MagicMock()
                mock_tracker.return_value = mock_instance

                mock_settings = {"polling_interval": 1.0}
                tracker = init_runtime_tracking(mock_settings)

                assert tracker is mock_instance
                mock_tracker.assert_called_once_with(mock_settings)

    def test_init_runtime_tracking_when_disabled(self):
        """Test init_runtime_tracking creates NoOpRuntimeResourceTracker when monitoring disabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            mock_settings = {"polling_interval": 1.0}
            tracker = init_runtime_tracking(mock_settings)

            assert isinstance(tracker, NoOpRuntimeResourceTracker)


class TestPerformanceImpact:
    """Test performance characteristics of no-op implementations."""

    def test_noop_logger_memory_efficiency(self):
        """Test NoOpPerformanceLogger doesn't accumulate memory."""
        import sys

        logger = NoOpPerformanceLogger()
        initial_size = sys.getsizeof(logger)

        # Perform many operations that would normally accumulate data
        for i in range(1000):
            timer_id = logger.start_timer(f"operation_{i}")
            logger.stop_timer(timer_id)
            logger.get_performance_summary()

        final_size = sys.getsizeof(logger)
        assert final_size == initial_size  # No memory growth

    def test_noop_tracker_memory_efficiency(self):
        """Test NoOpRuntimeResourceTracker doesn't accumulate memory."""
        import sys

        tracker = NoOpRuntimeResourceTracker()
        initial_size = sys.getsizeof(tracker)

        # Perform many operations that would normally accumulate data
        for i in range(1000):
            session_id = tracker.start_tracking(f"session_{i}")
            tracker.get_current_sample()
            tracker.stop_tracking()

        final_size = sys.getsizeof(tracker)
        assert final_size == initial_size  # No memory growth

    def test_noop_performance_overhead(self):
        """Test no-op implementations have minimal CPU overhead."""
        import time

        logger = NoOpPerformanceLogger()
        tracker = NoOpRuntimeResourceTracker()

        # Time many no-op operations
        start_time = time.perf_counter()
        for i in range(10000):
            timer_id = logger.start_timer(f"op_{i}")
            logger.stop_timer(timer_id)
            tracker.get_current_sample()
        end_time = time.perf_counter()

        elapsed = (end_time - start_time) * 1000  # Convert to milliseconds

        # Should complete 10k operations in under 10ms (very conservative)
        assert elapsed < 10.0, f"No-op operations took {elapsed:.2f}ms, expected < 10ms"


class TestBackwardCompatibility:
    """Test that conditional monitoring maintains API compatibility."""

    def test_api_compatibility_when_disabled(self):
        """Test all monitoring APIs work when monitoring is disabled."""
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            # Clear caches
            import calendarbot.monitoring.performance
            import calendarbot.monitoring.runtime_tracker

            calendarbot.monitoring.performance._performance_logger = None
            calendarbot.monitoring.runtime_tracker._runtime_tracker = None

            # Test that all APIs work without exceptions
            logger = get_performance_logger()
            tracker = get_runtime_tracker()

            # Test logger APIs
            timer_id = logger.start_timer("test")
            logger.stop_timer(timer_id)
            summary = logger.get_performance_summary()

            # Test tracker APIs
            session_id = tracker.start_tracking("test")
            current = tracker.get_current_sample()
            status = tracker.get_tracking_status()
            tracker.stop_tracking()

            # All calls should succeed
            assert summary is not None
            assert current is None
            assert status is not None

    def test_api_compatibility_initialization(self):
        """Test initialization APIs work in both modes."""
        # Test disabled mode
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "false"}):
            logger = init_performance_logging({"test": "settings"})
            tracker = init_runtime_tracking({"test": "settings"})

            assert isinstance(logger, NoOpPerformanceLogger)
            assert isinstance(tracker, NoOpRuntimeResourceTracker)

        # Test enabled mode (with mocking to avoid real initialization)
        with patch.dict(os.environ, {"CALENDARBOT_MONITORING": "true"}):
            with (
                patch("calendarbot.monitoring.performance.PerformanceLogger") as mock_logger,
                patch(
                    "calendarbot.monitoring.runtime_tracker.RuntimeResourceTracker"
                ) as mock_tracker,
            ):
                mock_logger_instance = MagicMock()
                mock_tracker_instance = MagicMock()
                mock_logger.return_value = mock_logger_instance
                mock_tracker.return_value = mock_tracker_instance

                logger = init_performance_logging({"test": "settings"})
                tracker = init_runtime_tracking({"test": "settings"})

                assert logger is mock_logger_instance
                assert tracker is mock_tracker_instance
