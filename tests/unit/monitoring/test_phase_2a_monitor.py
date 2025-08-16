"""Unit tests for the connection pool monitoring module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.config.optimization import OptimizationConfig
from calendarbot.monitoring.connection_pool_monitor import (
    ConnectionPoolMetrics,
    RequestPipelineMetrics,
)


class TestConnectionPoolMetrics:
    """Tests for the ConnectionPoolMetrics dataclass."""

    def test_connection_pool_metrics_initialization_with_defaults(self) -> None:
        """Test ConnectionPoolMetrics initialization with default values."""
        metrics = ConnectionPoolMetrics()

        assert metrics.active_connections == 0
        assert metrics.idle_connections == 0
        assert metrics.total_connections == 0
        assert metrics.max_connections == 0
        assert metrics.pool_utilization == 0.0
        assert metrics.connection_acquisitions == 0
        assert metrics.connection_releases == 0
        assert metrics.acquisition_wait_time == 0.0
        assert metrics.failed_acquisitions == 0

    def test_utilization_percentage_calculation(self) -> None:
        """Test utilization_percentage property calculation."""
        metrics = ConnectionPoolMetrics()

        # Test with zero max connections
        metrics.total_connections = 5
        metrics.max_connections = 0
        assert metrics.utilization_percentage == 0.0

        # Test normal calculation
        metrics.max_connections = 10
        assert metrics.utilization_percentage == 50.0

        # Test full utilization
        metrics.total_connections = 10
        assert metrics.utilization_percentage == 100.0


class TestRequestPipelineMetrics:
    """Tests for the RequestPipelineMetrics dataclass."""

    def test_request_pipeline_metrics_initialization_with_defaults(self) -> None:
        """Test RequestPipelineMetrics initialization with default values."""
        metrics = RequestPipelineMetrics()

        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.total_requests == 0
        assert metrics.cached_request_duration == 0.0
        assert metrics.uncached_request_duration == 0.0
        assert metrics.batch_requests == 0
        assert metrics.single_requests == 0
        assert metrics.average_batch_size == 0.0
        assert metrics.ttl_expirations == 0

    def test_cache_hit_rate_calculation(self) -> None:
        """Test cache_hit_rate property calculation."""
        metrics = RequestPipelineMetrics()

        # Test with zero total requests
        assert metrics.cache_hit_rate == 0.0

        # Test normal calculation
        metrics.cache_hits = 80
        metrics.cache_misses = 20
        metrics.total_requests = 100
        assert metrics.cache_hit_rate == 0.8

    def test_cache_miss_rate_calculation(self) -> None:
        """Test cache_miss_rate property calculation."""
        metrics = RequestPipelineMetrics()

        # Test with zero total requests
        assert metrics.cache_miss_rate == 1.0

        # Test normal calculation
        metrics.cache_hits = 80
        metrics.cache_misses = 20
        metrics.total_requests = 100
        assert abs(metrics.cache_miss_rate - 0.2) < 1e-10

    def test_batch_efficiency_calculation(self) -> None:
        """Test batch_efficiency property calculation."""
        metrics = RequestPipelineMetrics()

        # Test with zero total requests
        assert metrics.batch_efficiency == 0.0

        # Test normal calculation
        metrics.batch_requests = 30
        metrics.single_requests = 70
        metrics.total_requests = 100
        assert metrics.batch_efficiency == 0.3


@pytest.fixture
def mock_optimization_config() -> OptimizationConfig:
    """Create a mock optimization config for testing."""
    config = OptimizationConfig()
    config.memory_warning_threshold_mb = 400
    config.latency_warning_threshold_ms = 200
    config.cache_hit_rate_warning = 0.5
    return config


@pytest.fixture
def mock_performance_logger() -> MagicMock:
    """Create a mock performance logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def connection_pool_monitor(
    mock_optimization_config: OptimizationConfig,
    mock_performance_logger: MagicMock,
    mock_logger: MagicMock,
) -> ConnectionPoolMonitor:
    """Create a ConnectionPoolMonitor with mocked dependencies for testing."""
    with patch(
        "calendarbot.monitoring.connection_pool_monitor.get_optimization_config",
        return_value=mock_optimization_config,
    ):
        with patch(
            "calendarbot.monitoring.connection_pool_monitor.get_performance_logger",
            return_value=mock_performance_logger,
        ):
            with patch(
                "calendarbot.monitoring.connection_pool_monitor.get_logger",
                return_value=mock_logger,
            ):
                monitor = ConnectionPoolMonitor()
                return monitor


class TestPhase2AMonitor:
    """Tests for the Phase2AMonitor class."""

    def test_initialization(self, mock_optimization_config: OptimizationConfig) -> None:
        """Test Phase2AMonitor initialization."""
        with patch(
            "calendarbot.monitoring.phase_2a_monitor.get_optimization_config",
            return_value=mock_optimization_config,
        ):
            with patch("calendarbot.monitoring.phase_2a_monitor.get_performance_logger"):
                with patch("calendarbot.monitoring.phase_2a_monitor.get_logger"):
                    with patch("time.time", return_value=100.0):
                        monitor = Phase2AMonitor()

                        assert monitor.config == mock_optimization_config
                        assert isinstance(monitor.connection_pool_metrics, ConnectionPoolMetrics)
                        assert isinstance(monitor.request_pipeline_metrics, RequestPipelineMetrics)
                        assert monitor._request_timers == {}
                        assert monitor._monitoring_start_time == 100.0
                        assert monitor.memory_warning_threshold == 400
                        assert monitor.latency_warning_threshold == 0.2  # Converted to seconds
                        assert monitor.cache_hit_rate_warning == 0.5

    def test_initialization_with_custom_config(self) -> None:
        """Test Phase2AMonitor initialization with custom config."""
        custom_config = OptimizationConfig()
        custom_config.memory_warning_threshold_mb = 512

        with patch("calendarbot.monitoring.phase_2a_monitor.get_performance_logger"):
            with patch("calendarbot.monitoring.phase_2a_monitor.get_logger"):
                monitor = Phase2AMonitor(custom_config)

                assert monitor.config == custom_config
                assert monitor.memory_warning_threshold == 512

    def test_log_connection_pool_status(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_connection_pool_status method."""
        phase_2a_monitor.log_connection_pool_status(
            active=8,
            idle=2,
            max_connections=20,
            component="test_pool",
            correlation_id="test-correlation-id",
        )

        # Check that metrics were updated
        assert phase_2a_monitor.connection_pool_metrics.active_connections == 8
        assert phase_2a_monitor.connection_pool_metrics.idle_connections == 2
        assert phase_2a_monitor.connection_pool_metrics.total_connections == 10
        assert phase_2a_monitor.connection_pool_metrics.max_connections == 20
        assert phase_2a_monitor.connection_pool_metrics.pool_utilization == 50.0

        # Check that performance logger was called for each metric
        assert mock_performance_logger.log_metric.call_count == 4

        # Check specific metrics logged
        logged_metrics = [call[0][0] for call in mock_performance_logger.log_metric.call_args_list]
        metric_names = [metric.name for metric in logged_metrics]

        assert "connection_pool_active" in metric_names
        assert "connection_pool_idle" in metric_names
        assert "connection_pool_total" in metric_names
        assert "connection_pool_utilization" in metric_names

    def test_log_connection_pool_status_high_utilization_warning(
        self, phase_2a_monitor: Phase2AMonitor, mock_logger: MagicMock
    ) -> None:
        """Test log_connection_pool_status with high utilization warning."""
        phase_2a_monitor.log_connection_pool_status(active=16, idle=0, max_connections=20)

        mock_logger.warning.assert_called_once()
        assert "Connection pool utilization high: 80.0%" in mock_logger.warning.call_args[0][0]

    def test_log_connection_pool_status_critical_utilization_error(
        self, phase_2a_monitor: Phase2AMonitor, mock_logger: MagicMock
    ) -> None:
        """Test log_connection_pool_status with critical utilization error."""
        phase_2a_monitor.log_connection_pool_status(active=19, idle=0, max_connections=20)

        mock_logger.error.assert_called_once()
        assert "Connection pool utilization critical: 95.0%" in mock_logger.error.call_args[0][0]

    def test_log_connection_acquisition_success(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_connection_acquisition method with successful acquisition."""
        phase_2a_monitor.log_connection_acquisition(
            wait_time=0.5,
            success=True,
            component="test_pool",
            correlation_id="test-correlation-id",
        )

        # Check that metrics were updated
        assert phase_2a_monitor.connection_pool_metrics.connection_acquisitions == 1
        assert phase_2a_monitor.connection_pool_metrics.acquisition_wait_time == 0.5
        assert phase_2a_monitor.connection_pool_metrics.failed_acquisitions == 0

        # Check that performance logger was called
        mock_performance_logger.log_metric.assert_called_once()

        metric = mock_performance_logger.log_metric.call_args[0][0]
        assert metric.name == "connection_acquisition"
        assert metric.value == 0.5
        assert metric.metadata["success"] is True

    def test_log_connection_acquisition_failure(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_connection_acquisition method with failed acquisition."""
        phase_2a_monitor.log_connection_acquisition(wait_time=2.0, success=False)

        # Check that metrics were updated
        assert phase_2a_monitor.connection_pool_metrics.connection_acquisitions == 0
        assert phase_2a_monitor.connection_pool_metrics.failed_acquisitions == 1

        # Check that performance logger was called
        mock_performance_logger.log_metric.assert_called_once()

        metric = mock_performance_logger.log_metric.call_args[0][0]
        assert metric.metadata["success"] is False

    def test_log_connection_acquisition_slow_warning(
        self, phase_2a_monitor: Phase2AMonitor, mock_logger: MagicMock
    ) -> None:
        """Test log_connection_acquisition with slow acquisition warning."""
        phase_2a_monitor.log_connection_acquisition(wait_time=1.5, success=True)

        mock_logger.warning.assert_called_once()
        assert "Connection acquisition slow: 1.50s" in mock_logger.warning.call_args[0][0]

    def test_log_connection_release(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_connection_release method."""
        phase_2a_monitor.log_connection_release(
            component="test_pool",
            correlation_id="test-correlation-id",
        )

        # Check that metrics were updated
        assert phase_2a_monitor.connection_pool_metrics.connection_releases == 1

        # Check that performance logger was called
        mock_performance_logger.log_metric.assert_called_once()

        metric = mock_performance_logger.log_metric.call_args[0][0]
        assert metric.name == "connection_release"
        assert metric.value == 1

    def test_start_request_timer(self, phase_2a_monitor: Phase2AMonitor) -> None:
        """Test start_request_timer method."""
        with patch("time.perf_counter", return_value=100.0):
            phase_2a_monitor.start_request_timer("test-request-123", is_cached=True)

            assert phase_2a_monitor._request_timers["test-request-123"] == 100.0

    def test_log_request_completion_cache_hit(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_request_completion method with cache hit."""
        # Setup timer
        phase_2a_monitor._request_timers["test-request-123"] = 100.0

        with patch("time.perf_counter", return_value=100.5):
            duration = phase_2a_monitor.log_request_completion(
                request_id="test-request-123",
                cache_hit=True,
                was_batched=False,
                batch_size=1,
                component="test_pipeline",
                correlation_id="test-correlation-id",
            )

            assert duration == 0.5
            assert "test-request-123" not in phase_2a_monitor._request_timers

            # Check that metrics were updated
            assert phase_2a_monitor.request_pipeline_metrics.total_requests == 1
            assert phase_2a_monitor.request_pipeline_metrics.cache_hits == 1
            assert phase_2a_monitor.request_pipeline_metrics.cache_misses == 0
            assert phase_2a_monitor.request_pipeline_metrics.cached_request_duration == 0.5
            assert phase_2a_monitor.request_pipeline_metrics.single_requests == 1
            assert phase_2a_monitor.request_pipeline_metrics.batch_requests == 0

            # Check that performance logger was called
            mock_performance_logger.log_metric.assert_called_once()

            metric = mock_performance_logger.log_metric.call_args[0][0]
            assert metric.name == "request_pipeline_duration"
            assert metric.value == 0.5
            assert metric.metadata["cache_hit"] is True
            assert metric.metadata["was_batched"] is False

    def test_log_request_completion_cache_miss_batched(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_request_completion method with cache miss and batched request."""
        # Setup timer
        phase_2a_monitor._request_timers["test-request-456"] = 50.0

        with patch("time.perf_counter", return_value=52.0):
            duration = phase_2a_monitor.log_request_completion(
                request_id="test-request-456",
                cache_hit=False,
                was_batched=True,
                batch_size=5,
            )

            assert duration == 2.0

            # Check that metrics were updated
            assert phase_2a_monitor.request_pipeline_metrics.total_requests == 1
            assert phase_2a_monitor.request_pipeline_metrics.cache_hits == 0
            assert phase_2a_monitor.request_pipeline_metrics.cache_misses == 1
            assert phase_2a_monitor.request_pipeline_metrics.uncached_request_duration == 2.0
            assert phase_2a_monitor.request_pipeline_metrics.batch_requests == 1
            assert phase_2a_monitor.request_pipeline_metrics.single_requests == 0
            assert phase_2a_monitor.request_pipeline_metrics.average_batch_size == 5.0

    def test_log_request_completion_timer_not_found(
        self, phase_2a_monitor: Phase2AMonitor, mock_logger: MagicMock
    ) -> None:
        """Test log_request_completion method when timer is not found."""
        duration = phase_2a_monitor.log_request_completion("nonexistent-request")

        assert duration == 0.0
        mock_logger.warning.assert_called_once()
        assert (
            "Request timer not found for nonexistent-request" in mock_logger.warning.call_args[0][0]
        )

    def test_log_request_completion_high_latency_warning(
        self, phase_2a_monitor: Phase2AMonitor, mock_logger: MagicMock
    ) -> None:
        """Test log_request_completion with high latency warning."""
        # Setup timer
        phase_2a_monitor._request_timers["slow-request"] = 100.0

        with patch("time.perf_counter", return_value=100.3):  # 300ms duration > 200ms threshold
            phase_2a_monitor.log_request_completion("slow-request")

            mock_logger.warning.assert_called_once()
            assert "Request latency high: 0.30s" in mock_logger.warning.call_args[0][0]

    def test_log_cache_performance(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_cache_performance method."""
        # Setup some requests first
        phase_2a_monitor.request_pipeline_metrics.total_requests = 100
        phase_2a_monitor.request_pipeline_metrics.cache_hits = 70
        phase_2a_monitor.request_pipeline_metrics.cache_misses = 30

        phase_2a_monitor.log_cache_performance(
            component="test_cache",
            correlation_id="test-correlation-id",
        )

        # Check that performance logger was called for each metric
        assert mock_performance_logger.log_metric.call_count == 4

        # Check specific metrics logged
        logged_metrics = [call[0][0] for call in mock_performance_logger.log_metric.call_args_list]
        metric_names = [metric.name for metric in logged_metrics]

        assert "cache_hit_rate" in metric_names
        assert "cache_miss_rate" in metric_names
        assert "cache_hits" in metric_names
        assert "cache_misses" in metric_names

    def test_log_cache_performance_no_requests(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_cache_performance method with no requests."""
        phase_2a_monitor.log_cache_performance()

        # Should not log anything if no requests
        mock_performance_logger.log_metric.assert_not_called()

    def test_log_cache_performance_low_hit_rate_warning(
        self, phase_2a_monitor: Phase2AMonitor, mock_logger: MagicMock
    ) -> None:
        """Test log_cache_performance with low hit rate warning."""
        # Setup low hit rate
        phase_2a_monitor.request_pipeline_metrics.total_requests = 100
        phase_2a_monitor.request_pipeline_metrics.cache_hits = 30  # 30% < 50% threshold
        phase_2a_monitor.request_pipeline_metrics.cache_misses = 70

        phase_2a_monitor.log_cache_performance()

        mock_logger.warning.assert_called_once()
        assert "Cache hit rate low: 30.0%" in mock_logger.warning.call_args[0][0]

    def test_log_ttl_expiration(
        self, phase_2a_monitor: Phase2AMonitor, mock_performance_logger: MagicMock
    ) -> None:
        """Test log_ttl_expiration method."""
        phase_2a_monitor.log_ttl_expiration(
            expired_items=5,
            component="test_cache",
            correlation_id="test-correlation-id",
        )

        # Check that metrics were updated
        assert phase_2a_monitor.request_pipeline_metrics.ttl_expirations == 5

        # Check that performance logger was called
        mock_performance_logger.log_metric.assert_called_once()

        metric = mock_performance_logger.log_metric.call_args[0][0]
        assert metric.name == "ttl_expiration"
        assert metric.value == 5

    def test_get_phase_2a_summary(self, phase_2a_monitor: Phase2AMonitor) -> None:
        """Test get_phase_2a_summary method."""
        # Setup some test data
        start_time = time.time()
        phase_2a_monitor._monitoring_start_time = start_time - 3600  # 1 hour ago

        # Connection pool metrics
        phase_2a_monitor.connection_pool_metrics.active_connections = 8
        phase_2a_monitor.connection_pool_metrics.idle_connections = 2
        phase_2a_monitor.connection_pool_metrics.total_connections = 10
        phase_2a_monitor.connection_pool_metrics.max_connections = 20
        phase_2a_monitor.connection_pool_metrics.connection_acquisitions = 100
        phase_2a_monitor.connection_pool_metrics.failed_acquisitions = 5
        phase_2a_monitor.connection_pool_metrics.connection_releases = 95
        phase_2a_monitor.connection_pool_metrics.acquisition_wait_time = 10.0

        # Request pipeline metrics
        phase_2a_monitor.request_pipeline_metrics.total_requests = 500
        phase_2a_monitor.request_pipeline_metrics.cache_hits = 350
        phase_2a_monitor.request_pipeline_metrics.cache_misses = 150
        phase_2a_monitor.request_pipeline_metrics.cached_request_duration = 35.0
        phase_2a_monitor.request_pipeline_metrics.uncached_request_duration = 300.0
        phase_2a_monitor.request_pipeline_metrics.batch_requests = 200
        phase_2a_monitor.request_pipeline_metrics.single_requests = 300
        phase_2a_monitor.request_pipeline_metrics.average_batch_size = 3.5
        phase_2a_monitor.request_pipeline_metrics.ttl_expirations = 25

        with patch("time.time", return_value=start_time):
            summary = phase_2a_monitor.get_phase_2a_summary()

            # Check basic structure
            assert "monitoring_uptime_seconds" in summary
            assert "connection_pool" in summary
            assert "request_pipeline" in summary
            assert "performance_assessment" in summary

            # Check connection pool summary
            pool_summary = summary["connection_pool"]
            assert pool_summary["active_connections"] == 8
            assert pool_summary["utilization_percentage"] == 50.0
            assert pool_summary["avg_acquisition_wait_time"] == 0.1  # 10.0 / 100

            # Check request pipeline summary
            pipeline_summary = summary["request_pipeline"]
            assert pipeline_summary["total_requests"] == 500
            assert pipeline_summary["cache_hit_rate"] == 0.7  # 350/500
            assert pipeline_summary["batch_efficiency"] == 0.4  # 200/500
            assert pipeline_summary["avg_cached_request_time"] == 0.1  # 35.0/350
            assert pipeline_summary["avg_uncached_request_time"] == 2.0  # 300.0/150
            assert pipeline_summary["cache_speedup_factor"] == 20.0  # 2.0/0.1

            # Check performance assessment
            assessment = summary["performance_assessment"]
            assert assessment["connection_pool_healthy"] is True  # 50% < 75%
            assert assessment["cache_performance_good"] is True  # 0.7 >= 0.5
            assert assessment["latency_acceptable"] is False  # 2.0 >= 0.2
            assert assessment["optimization_effective"] is True  # Good cache + pool

    def test_get_phase_2a_summary_with_zero_values(self, phase_2a_monitor: Phase2AMonitor) -> None:
        """Test get_phase_2a_summary method with zero values."""
        summary = phase_2a_monitor.get_phase_2a_summary()

        # Check that zero values are handled properly
        pipeline_summary = summary["request_pipeline"]
        assert pipeline_summary["avg_cached_request_time"] == 0.0
        assert pipeline_summary["avg_uncached_request_time"] == 0.0
        assert pipeline_summary["cache_speedup_factor"] == 1.0  # Default when no cached time


class TestGlobalFunctions:
    """Tests for global functions in the phase_2a_monitor module."""

    def test_get_phase_2a_monitor_creates_new_instance(self) -> None:
        """Test get_phase_2a_monitor creates a new instance if none exists."""
        # Reset global monitor to None
        reset_phase_2a_monitor()

        with patch("calendarbot.monitoring.phase_2a_monitor.Phase2AMonitor") as mock_monitor_class:
            mock_monitor = MagicMock()
            mock_monitor_class.return_value = mock_monitor

            monitor = get_phase_2a_monitor()

            assert monitor == mock_monitor
            mock_monitor_class.assert_called_once_with(None)

    def test_get_phase_2a_monitor_returns_existing_instance(self) -> None:
        """Test get_phase_2a_monitor returns existing instance if one exists."""
        # Create first instance
        with patch("calendarbot.monitoring.phase_2a_monitor.Phase2AMonitor"):
            monitor1 = get_phase_2a_monitor()
            # Get second instance
            monitor2 = get_phase_2a_monitor()

            # Should be the same instance
            assert monitor1 is monitor2

    def test_get_phase_2a_monitor_with_custom_config(self) -> None:
        """Test get_phase_2a_monitor with custom optimization config."""
        reset_phase_2a_monitor()

        custom_config = OptimizationConfig()
        custom_config.max_connections = 42

        with patch("calendarbot.monitoring.phase_2a_monitor.Phase2AMonitor") as mock_monitor_class:
            mock_monitor = MagicMock()
            mock_monitor_class.return_value = mock_monitor

            monitor = get_phase_2a_monitor(custom_config)

            assert monitor == mock_monitor
            mock_monitor_class.assert_called_once_with(custom_config)

    def test_reset_phase_2a_monitor(self) -> None:
        """Test reset_phase_2a_monitor clears the global instance."""
        # Create an instance
        with patch("calendarbot.monitoring.phase_2a_monitor.Phase2AMonitor"):
            monitor1 = get_phase_2a_monitor()
            assert monitor1 is not None

            # Reset and create new instance
            reset_phase_2a_monitor()
            monitor2 = get_phase_2a_monitor()

            # Should be different instances
            assert monitor1 is not monitor2
