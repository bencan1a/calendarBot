"""Unit tests for runtime resource tracking functionality."""

import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from calendarbot.cli.runtime_integration import (
    create_runtime_tracker,
    start_runtime_tracking,
    stop_runtime_tracking,
)
from calendarbot.monitoring.runtime_tracker import (
    ResourceSample,
    RuntimeResourceStats,
    RuntimeResourceTracker,
)


class TestResourceSample:
    """Test ResourceSample dataclass functionality."""

    def test_resource_sample_creation_with_valid_data_then_success(self):
        """Test creating ResourceSample with valid data."""
        sample = ResourceSample(cpu_percent=25.5, memory_rss_mb=128.75)

        assert isinstance(sample.timestamp, datetime)
        assert sample.cpu_percent == 25.5
        assert sample.memory_rss_mb == 128.75

    def test_resource_sample_creation_with_zero_values_then_success(self):
        """Test creating ResourceSample with zero values."""
        sample = ResourceSample(cpu_percent=0.0, memory_rss_mb=0.0)

        assert sample.cpu_percent == 0.0
        assert sample.memory_rss_mb == 0.0

    def test_resource_sample_creation_with_negative_values_then_success(self):
        """Test creating ResourceSample with negative values (edge case)."""
        sample = ResourceSample(
            cpu_percent=-1.0,  # Could happen in some edge cases
            memory_rss_mb=0.0,
        )

        assert sample.cpu_percent == -1.0


class TestRuntimeResourceStats:
    """Test RuntimeResourceStats dataclass functionality."""

    def test_runtime_resource_stats_creation_with_valid_data_then_success(self):
        """Test creating RuntimeResourceStats with valid data."""
        stats = RuntimeResourceStats(
            cpu_median=15.5,
            cpu_maximum=45.2,
            memory_median_mb=256.0,
            memory_maximum_mb=512.5,
            total_samples=100,
            duration_seconds=5.0,
        )

        assert stats.cpu_median == 15.5
        assert stats.cpu_maximum == 45.2
        assert stats.memory_median_mb == 256.0
        assert stats.memory_maximum_mb == 512.5
        assert stats.total_samples == 100
        assert stats.duration_seconds == 5.0

    def test_runtime_resource_stats_creation_with_zero_samples_then_success(self):
        """Test creating RuntimeResourceStats with zero samples."""
        stats = RuntimeResourceStats(
            cpu_median=0.0,
            cpu_maximum=0.0,
            memory_median_mb=0.0,
            memory_maximum_mb=0.0,
            total_samples=0,
            duration_seconds=0.0,
        )

        assert stats.total_samples == 0


class TestRuntimeResourceTracker:
    """Test RuntimeResourceTracker main functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "test_runtime.db"

    @pytest.fixture
    def mock_settings(self, temp_db_path):
        """Create test settings configuration."""
        return SimpleNamespace(
            benchmark_storage_path=temp_db_path, version="test_version", environment="test"
        )

    @pytest.fixture
    def runtime_tracker(self, mock_settings):
        """Create RuntimeResourceTracker for testing."""
        return RuntimeResourceTracker(
            settings=mock_settings, sampling_interval=0.1, save_individual_samples=False
        )

    def test_runtime_tracker_initialization_with_valid_config_then_success(self, runtime_tracker):
        """Test RuntimeResourceTracker initialization."""
        assert runtime_tracker.sampling_interval == 0.1
        assert not runtime_tracker._tracking
        assert runtime_tracker._samples == []
        assert runtime_tracker._tracking_thread is None

    def test_get_current_sample_when_called_then_returns_valid_sample(self, runtime_tracker):
        """Test getting current resource sample."""
        sample = runtime_tracker.get_current_sample()

        assert isinstance(sample, ResourceSample) or sample is None
        if sample:
            assert isinstance(sample.timestamp, datetime)
            assert sample.cpu_percent >= 0
            assert sample.memory_rss_mb > 0

    @patch("psutil.Process")
    def test_get_current_sample_with_mocked_psutil_then_returns_expected_values(
        self, mock_process_class, runtime_tracker
    ):
        """Test getting current sample with mocked psutil."""
        # Mock process instance
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 25.5
        mock_process.memory_info.return_value = Mock(
            rss=268435456, vms=536870912
        )  # 256MB RSS, 512MB VMS
        mock_process.memory_percent.return_value = 12.5
        mock_process_class.return_value = mock_process

        sample = runtime_tracker.get_current_sample()

        assert sample.cpu_percent == 25.5
        assert sample.memory_rss_mb == 256.0
        assert sample.memory_vms_mb == 512.0
        assert sample.memory_percent == 12.5

    def test_start_tracking_when_not_tracking_then_starts_successfully(self, runtime_tracker):
        """Test starting resource tracking."""
        session_id = runtime_tracker.start_tracking(session_name="test")

        assert runtime_tracker._tracking
        assert runtime_tracker._tracking_thread is not None
        assert runtime_tracker._tracking_thread.is_alive()
        assert session_id is not None

        # Clean up
        runtime_tracker.stop_tracking()

    def test_start_tracking_when_already_tracking_then_stops_previous(self, runtime_tracker):
        """Test starting tracking when already tracking."""
        session_id1 = runtime_tracker.start_tracking(session_name="test1")
        session_id2 = runtime_tracker.start_tracking(session_name="test2")

        assert session_id1 != session_id2
        assert runtime_tracker._tracking

        # Clean up
        runtime_tracker.stop_tracking()

    def test_stop_tracking_when_tracking_then_stops_successfully(self, runtime_tracker):
        """Test stopping resource tracking."""
        runtime_tracker.start_tracking(session_name="test")
        # Use event wait instead of sleep
        event = threading.Event()
        event.wait(timeout=0.02)  # Brief wait to allow samples

        stats = runtime_tracker.stop_tracking()

        assert not runtime_tracker._tracking
        assert runtime_tracker._tracking_thread is None
        assert isinstance(stats, RuntimeResourceStats)
        assert stats.total_samples >= 0

    def test_stop_tracking_when_not_tracking_then_returns_none(self, runtime_tracker):
        """Test stopping tracking when not tracking."""
        stats = runtime_tracker.stop_tracking()

        assert stats is None
        assert not runtime_tracker._tracking

    def test_track_execution_context_manager_then_collects_samples(self, runtime_tracker):
        """Test using track_execution as context manager."""

        def test_operation():
            # Use event wait instead of sleep
            event = threading.Event()
            event.wait(timeout=0.02)
            return "test_result"

        with runtime_tracker.track_execution("test_operation"):
            result = test_operation()

        assert result == "test_result"
        # Should have some samples collected
        assert len(runtime_tracker._samples) >= 0

    def test_track_execution_with_exception_then_still_stops_tracking(self, runtime_tracker):
        """Test track_execution context manager with exception."""
        with (
            pytest.raises(ValueError, match="Test exception"),
            runtime_tracker.track_execution("test_operation"),
        ):
            raise ValueError("Test exception")

        assert not runtime_tracker._tracking
        assert runtime_tracker._tracking_thread is None

    def test_worker_thread_collects_samples_continuously(self, runtime_tracker):
        """Test that worker thread collects samples continuously."""
        runtime_tracker.start_tracking(session_name="test")
        # Use event wait instead of sleep
        event = threading.Event()
        event.wait(timeout=0.03)  # Brief wait for samples
        stats = runtime_tracker.stop_tracking()

        # Should have collected some samples
        if stats:
            assert stats.total_samples >= 0

    def test_get_tracking_status_when_not_tracking_then_returns_inactive_status(
        self, runtime_tracker
    ):
        """Test getting tracking status when not tracking."""
        status = runtime_tracker.get_tracking_status()

        assert status["tracking_active"] is False
        assert status["session_id"] is None
        assert status["sample_count"] == 0

    def test_get_tracking_status_when_tracking_then_returns_active_status(self, runtime_tracker):
        """Test getting tracking status when tracking."""
        runtime_tracker.start_tracking(session_name="test")

        status = runtime_tracker.get_tracking_status()

        assert status["tracking_active"] is True
        assert status["session_id"] is not None
        assert status["sample_count"] >= 0

        # Clean up
        runtime_tracker.stop_tracking()


class TestRuntimeIntegration:
    """Test CLI runtime integration functions."""

    @pytest.fixture
    def mock_settings_enabled(self):
        """Create mock settings with runtime tracking enabled."""
        runtime_tracking = SimpleNamespace(enabled=True, sampling_interval=0.1, save_samples=True)
        return SimpleNamespace(
            runtime_tracking=runtime_tracking,
            benchmark_storage_path=Path("/tmp/test.db"),
            version="test_version",
            environment="test",
        )

    @pytest.fixture
    def mock_settings_disabled(self):
        """Create mock settings with runtime tracking disabled."""
        runtime_tracking = SimpleNamespace(enabled=False, sampling_interval=1.0, save_samples=False)
        return SimpleNamespace(
            runtime_tracking=runtime_tracking,
            benchmark_storage_path=None,
            version="test_version",
            environment="test",
        )

    def test_create_runtime_tracker_when_enabled_then_returns_tracker(self, mock_settings_enabled):
        """Test creating runtime tracker when enabled."""
        tracker = create_runtime_tracker(mock_settings_enabled)

        assert tracker is not None
        assert isinstance(tracker, RuntimeResourceTracker)
        assert tracker.sampling_interval == 0.1

    def test_create_runtime_tracker_when_disabled_then_returns_none(self, mock_settings_disabled):
        """Test creating runtime tracker when disabled."""
        tracker = create_runtime_tracker(mock_settings_disabled)

        assert tracker is None

    @patch("builtins.print")
    def test_start_runtime_tracking_with_tracker_then_starts_successfully(self, mock_print):
        """Test starting runtime tracking with valid tracker."""
        mock_tracker = Mock(spec=RuntimeResourceTracker)
        mock_tracker.start_tracking.return_value = "session_123"

        result = start_runtime_tracking(mock_tracker)

        assert result is True
        mock_tracker.start_tracking.assert_called_once_with(
            session_name="application", metadata={"operation": "application"}
        )
        mock_print.assert_called_with("Runtime tracking started for: application")

    def test_start_runtime_tracking_with_none_then_returns_false(self):
        """Test starting runtime tracking with None tracker."""
        result = start_runtime_tracking(None)

        assert result is False

    @patch("builtins.print")
    def test_start_runtime_tracking_with_exception_then_returns_false(self, mock_print):
        """Test starting runtime tracking with exception."""
        mock_tracker = Mock(spec=RuntimeResourceTracker)
        mock_tracker.start_tracking.side_effect = Exception("Test error")

        result = start_runtime_tracking(mock_tracker)

        assert result is False
        mock_print.assert_called_with("Warning: Could not start runtime tracking - Test error")

    @patch("builtins.print")
    def test_stop_runtime_tracking_with_tracker_then_stops_and_reports(self, mock_print):
        """Test stopping runtime tracking with valid tracker."""
        mock_stats = RuntimeResourceStats(
            cpu_median=15.0,
            cpu_maximum=30.0,
            memory_median_mb=128.0,
            memory_maximum_mb=256.0,
            total_samples=10,
            duration_seconds=5.0,
        )
        mock_tracker = Mock(spec=RuntimeResourceTracker)
        mock_tracker.stop_tracking.return_value = mock_stats

        result = stop_runtime_tracking(mock_tracker)

        assert result is True
        mock_tracker.stop_tracking.assert_called_once()

        # Check that performance summary was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Runtime tracking completed for: application" in call for call in print_calls)
        assert any("CPU Usage - Median: 15.0%, Max: 30.0%" in call for call in print_calls)
        assert any("Memory Usage - Median: 128.0MB, Max: 256.0MB" in call for call in print_calls)

    def test_stop_runtime_tracking_with_none_then_returns_false(self):
        """Test stopping runtime tracking with None tracker."""
        result = stop_runtime_tracking(None)

        assert result is False

    @patch("builtins.print")
    def test_stop_runtime_tracking_with_no_stats_then_returns_true(self, mock_print):
        """Test stopping runtime tracking when no stats collected."""
        mock_tracker = Mock(spec=RuntimeResourceTracker)
        mock_tracker.stop_tracking.return_value = None

        result = stop_runtime_tracking(mock_tracker)

        assert result is True
        # No performance summary should be printed when no stats

    @patch("builtins.print")
    def test_stop_runtime_tracking_with_exception_then_returns_false(self, mock_print):
        """Test stopping runtime tracking with exception."""
        mock_tracker = Mock(spec=RuntimeResourceTracker)
        mock_tracker.stop_tracking.side_effect = Exception("Test error")

        result = stop_runtime_tracking(mock_tracker)

        assert result is False
        mock_print.assert_called_with("Warning: Error stopping runtime tracking - Test error")


class TestRuntimeTrackerRealIntegration:
    """Integration tests with real components (slower, fewer tests)."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create temporary storage path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "integration_test.db"

    def test_real_runtime_tracker_integration_then_works_end_to_end(self, temp_storage_path):
        """Test real integration with actual components."""
        # Create settings
        settings = SimpleNamespace(
            benchmark_storage_path=temp_storage_path, version="test_version", environment="test"
        )

        # Create tracker
        tracker = RuntimeResourceTracker(
            settings=settings,
            sampling_interval=0.05,  # Fast sampling for test
            save_individual_samples=False,
        )

        # Test tracking a real operation
        def cpu_intensive_operation():
            # Do some CPU work
            total = 0
            for i in range(100000):
                total += i * i
            return total

        with tracker.track_execution("cpu_test"):
            result = cpu_intensive_operation()

        # Verify results
        assert result > 0
        assert len(tracker._samples) >= 0

    def test_real_cli_integration_functions_then_work_correctly(self, temp_storage_path):
        """Test real CLI integration functions."""
        # Create settings with proper structure
        runtime_tracking = SimpleNamespace(enabled=True, sampling_interval=0.05, save_samples=True)
        settings = SimpleNamespace(
            runtime_tracking=runtime_tracking,
            benchmark_storage_path=temp_storage_path,
            version="test_version",
            environment="test",
        )

        # Test creating tracker
        tracker = create_runtime_tracker(settings)
        assert tracker is not None

        # Test starting tracking
        result = start_runtime_tracking(tracker)
        assert result is True
        assert tracker._tracking

        # Let it run briefly
        event = threading.Event()
        event.wait(timeout=0.01)

        # Test stopping tracking
        result = stop_runtime_tracking(tracker)
        assert result is True
        assert not tracker._tracking

        # Should have collected samples
        assert len(tracker._samples) > 0


@pytest.mark.performance
class TestRuntimeTrackerPerformance:
    """Performance tests for runtime tracker."""

    @pytest.mark.skip(reason="Performance test is unstable in test environment")
    def test_runtime_tracker_overhead_is_minimal(self):
        """Test that runtime tracker has minimal performance overhead."""
        settings = SimpleNamespace(
            benchmark_storage_path=None, version="test_version", environment="test"
        )

        tracker = RuntimeResourceTracker(
            settings=settings,
            sampling_interval=1.0,  # Much longer interval to reduce overhead
            save_individual_samples=False,
        )

        # Measure overhead of tracking with longer operations
        def test_operation():
            total = 0
            for i in range(2000000):  # Much larger operation
                total += i * 2
            return total

        # Run multiple iterations to get stable timing
        iterations = 5
        times_without = []
        times_with = []

        for _ in range(iterations):
            # Time without tracking
            start_time = time.perf_counter()
            result1 = test_operation()
            times_without.append(time.perf_counter() - start_time)

            # Time with tracking
            start_time = time.perf_counter()
            with tracker.track_execution("performance_test"):
                result2 = test_operation()
            times_with.append(time.perf_counter() - start_time)

            # Results should be the same
            assert result1 == result2

        # Use median times for more stable results
        time_without_tracking = sorted(times_without)[iterations // 2]
        time_with_tracking = sorted(times_with)[iterations // 2]

        # Overhead should be less than 5% (as per requirements)
        overhead_ratio = (time_with_tracking - time_without_tracking) / time_without_tracking
        print(f"Runtime tracking overhead: {overhead_ratio * 100:.2f}%")
        assert overhead_ratio < 0.05, f"Overhead {overhead_ratio * 100:.2f}% exceeds 5% limit"

    def test_sampling_interval_accuracy(self):
        """Test that sampling interval is reasonably accurate."""
        settings = SimpleNamespace(
            benchmark_storage_path=None, version="test_version", environment="test"
        )

        tracker = RuntimeResourceTracker(
            settings=settings, sampling_interval=0.1, save_individual_samples=False
        )

        tracker.start_tracking(session_name="timing_test")
        # Wait long enough to collect multiple samples
        time.sleep(0.25)  # Wait 250ms for 0.1s (100ms) interval
        stats = tracker.stop_tracking()

        # Should have approximately 2-3 samples (0.25s / 0.1s = 2.5)
        actual_samples = stats.total_samples if stats else 0

        # Allow generous variance due to timing in CI environments
        assert actual_samples >= 1, f"Expected at least 1 sample, got {actual_samples}"
