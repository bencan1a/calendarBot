"""Unit tests for the performance monitoring module."""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.monitoring.performance import (
    MetricType,
    PerformanceLogger,
    PerformanceLoggerMixin,
    PerformanceMetric,
    cache_monitor,
    get_performance_logger,
    init_performance_logging,
    memory_monitor,
    performance_monitor,
    performance_timer,
)


class TestMetricType:
    """Tests for the MetricType enum."""

    def test_metric_type_values(self) -> None:
        """Test that MetricType enum has expected values."""
        assert MetricType.TIMER.value == "timer"
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.MEMORY.value == "memory"
        assert MetricType.CACHE.value == "cache"
        assert MetricType.REQUEST.value == "request"
        assert MetricType.DATABASE.value == "database"
        assert MetricType.SYSTEM.value == "system"


class TestPerformanceMetric:
    """Tests for the PerformanceMetric dataclass."""

    def test_performance_metric_initialization_with_defaults(self) -> None:
        """Test PerformanceMetric initialization with default values."""
        metric = PerformanceMetric()

        assert isinstance(metric.metric_id, str)
        assert metric.name == ""
        assert metric.metric_type == MetricType.GAUGE
        assert metric.value == 0
        assert metric.unit == ""
        assert isinstance(metric.timestamp, datetime)
        assert metric.component == ""
        assert metric.operation == ""
        assert metric.correlation_id is None
        assert metric.metadata == {}

    def test_performance_metric_initialization_with_custom_values(self) -> None:
        """Test PerformanceMetric initialization with custom values."""
        custom_id = "test-metric-123"
        custom_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        custom_metadata = {"key": "value"}

        metric = PerformanceMetric(
            metric_id=custom_id,
            name="test_metric",
            metric_type=MetricType.TIMER,
            value=1.23,
            unit="seconds",
            timestamp=custom_timestamp,
            component="test_component",
            operation="test_operation",
            correlation_id="test-correlation-id",
            metadata=custom_metadata,
        )

        assert metric.metric_id == custom_id
        assert metric.name == "test_metric"
        assert metric.metric_type == MetricType.TIMER
        assert metric.value == 1.23
        assert metric.unit == "seconds"
        assert metric.timestamp == custom_timestamp
        assert metric.component == "test_component"
        assert metric.operation == "test_operation"
        assert metric.correlation_id == "test-correlation-id"
        assert metric.metadata == custom_metadata

    def test_to_dict_method(self) -> None:
        """Test the to_dict method returns correct dictionary representation."""
        metric = PerformanceMetric(
            metric_id="test-id",
            name="test_metric",
            metric_type=MetricType.COUNTER,
            value=42,
            unit="count",
            component="test_component",
            operation="test_operation",
            correlation_id="test-correlation-id",
            metadata={"test_key": "test_value"},
        )

        result = metric.to_dict()

        assert result["metric_id"] == "test-id"
        assert result["name"] == "test_metric"
        assert result["type"] == "counter"
        assert result["value"] == 42
        assert result["unit"] == "count"
        assert isinstance(result["timestamp"], str)
        assert result["component"] == "test_component"
        assert result["operation"] == "test_operation"
        assert result["correlation_id"] == "test-correlation-id"
        assert result["metadata"] == {"test_key": "test_value"}


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def mock_metrics_logger() -> MagicMock:
    """Create a mock metrics logger for testing."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def performance_logger(mock_logger: MagicMock, mock_metrics_logger: MagicMock) -> PerformanceLogger:
    """Create a PerformanceLogger with mocked loggers for testing."""
    with patch("calendarbot.monitoring.performance.get_logger", return_value=mock_logger):
        logger = PerformanceLogger()
        logger.metrics_logger = mock_metrics_logger
        return logger


class TestPerformanceLogger:
    """Tests for the PerformanceLogger class."""

    def test_initialization(self) -> None:
        """Test PerformanceLogger initialization."""
        with patch("calendarbot.monitoring.performance.get_logger") as mock_get_logger:
            with patch.object(PerformanceLogger, "_setup_metrics_logger") as mock_setup:
                logger = PerformanceLogger()

                mock_get_logger.assert_called_once_with("performance")
                mock_setup.assert_called_once()
                assert logger._metrics_cache == []
                assert logger._operation_timers == {}
                assert logger.cache_size == 2000
                # Check that _lock is a lock object (not checking the exact type)
                assert hasattr(logger._lock, "acquire")
                assert hasattr(logger._lock, "release")
                assert isinstance(logger.thresholds, dict)

    def test_setup_metrics_logger_with_settings(self) -> None:
        """Test _setup_metrics_logger with settings."""
        mock_settings = MagicMock()
        mock_settings.data_dir = "/test/data/dir"

        with patch("calendarbot.monitoring.performance.logging"):
            with patch("calendarbot.monitoring.performance.Path") as mock_path:
                with patch("logging.handlers.RotatingFileHandler") as mock_handler:
                    # Setup the mock path
                    mock_path_instance = Mock()
                    mock_path.return_value = mock_path_instance

                    # Mock the / operator for Path objects
                    mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)
                    mock_path_instance.mkdir = Mock()

                    logger = PerformanceLogger(settings=mock_settings)

                    # Check that the correct path was created
                    mock_path.assert_called_with("/test/data/dir")
                    mock_path_instance.mkdir.assert_called_with(parents=True, exist_ok=True)

    def test_setup_metrics_logger_without_settings(self) -> None:
        """Test _setup_metrics_logger without settings."""
        with patch("calendarbot.monitoring.performance.logging"):
            with patch("calendarbot.monitoring.performance.Path") as mock_path:
                with patch("logging.handlers.RotatingFileHandler") as mock_handler:
                    # Setup the mock path
                    home_path = Mock()
                    mock_path.home.return_value = home_path
                    home_path.__truediv__ = Mock(return_value=home_path)
                    home_path.mkdir = Mock()

                    logger = PerformanceLogger()

                    # Check that the default path was created
                    mock_path.home.assert_called_once()
                    home_path.mkdir.assert_called_with(parents=True, exist_ok=True)

    def test_log_metric(
        self, performance_logger: PerformanceLogger, mock_metrics_logger: MagicMock
    ) -> None:
        """Test log_metric method."""
        metric = PerformanceMetric(
            name="test_metric", metric_type=MetricType.GAUGE, value=42, unit="count"
        )

        with patch.object(performance_logger, "_add_to_cache") as mock_add_to_cache:
            with patch.object(performance_logger, "_check_thresholds") as mock_check_thresholds:
                performance_logger.log_metric(metric)

                mock_add_to_cache.assert_called_once_with(metric)
                mock_metrics_logger.info.assert_called_once()
                mock_check_thresholds.assert_called_once_with(metric)

    def test_log_metric_exception(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test log_metric method with exception."""
        metric = PerformanceMetric(name="test_metric")

        with patch.object(performance_logger, "_add_to_cache", side_effect=Exception("Test error")):
            performance_logger.log_metric(metric)

            mock_logger.exception.assert_called_once_with("Failed to log performance metric")

    def test_start_timer(self, performance_logger: PerformanceLogger) -> None:
        """Test start_timer method."""
        with patch("calendarbot.monitoring.performance.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "12345678" * 2
            with patch("calendarbot.monitoring.performance.time.perf_counter", return_value=100.0):
                with patch.object(performance_logger, "log_metric") as mock_log_metric:
                    timer_id = performance_logger.start_timer(
                        "test_operation", "test_component", "test-correlation-id"
                    )

                    assert timer_id == "test_operation_12345678"
                    assert performance_logger._operation_timers[timer_id] == 100.0
                    mock_log_metric.assert_called_once()

                    # Check the metric that was logged
                    metric = mock_log_metric.call_args[0][0]
                    assert metric.name == "test_operation_start"
                    assert metric.metric_type == MetricType.TIMER
                    assert metric.value == 100.0
                    assert metric.component == "test_component"
                    assert metric.operation == "test_operation"
                    assert metric.correlation_id == "test-correlation-id"
                    assert metric.metadata["timer_id"] == timer_id
                    assert metric.metadata["action"] == "start"

    def test_stop_timer(self, performance_logger: PerformanceLogger) -> None:
        """Test stop_timer method."""
        # Setup a timer
        timer_id = "test_operation_12345678"
        performance_logger._operation_timers[timer_id] = 100.0

        with patch("calendarbot.monitoring.performance.time.perf_counter", return_value=105.5):
            with patch.object(performance_logger, "log_metric") as mock_log_metric:
                duration = performance_logger.stop_timer(
                    timer_id,
                    "test_component",
                    "test_operation",
                    "test-correlation-id",
                    {"extra": "metadata"},
                )

                assert duration == 5.5
                assert timer_id not in performance_logger._operation_timers
                mock_log_metric.assert_called_once()

                # Check the metric that was logged
                metric = mock_log_metric.call_args[0][0]
                assert metric.name == "test_operation_duration"
                assert metric.metric_type == MetricType.TIMER
                assert metric.value == 5.5
                assert metric.component == "test_component"
                assert metric.operation == "test_operation"
                assert metric.correlation_id == "test-correlation-id"
                assert metric.metadata["timer_id"] == timer_id
                assert metric.metadata["action"] == "complete"
                assert metric.metadata["start_time"] == 100.0
                assert metric.metadata["end_time"] == 105.5
                assert metric.metadata["extra"] == "metadata"

    def test_stop_timer_not_found(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test stop_timer method when timer_id is not found."""
        timer_id = "nonexistent_timer"

        duration = performance_logger.stop_timer(timer_id)

        assert duration == 0.0
        mock_logger.warning.assert_called_once_with(f"Timer {timer_id} not found")

    def test_log_request_performance(self, performance_logger: PerformanceLogger) -> None:
        """Test log_request_performance method."""
        with patch.object(performance_logger, "log_metric") as mock_log_metric:
            performance_logger.log_request_performance(
                method="GET",
                url="https://example.com/api",
                duration=0.75,
                status_code=200,
                component="test_component",
                correlation_id="test-correlation-id",
                metadata={"extra": "data"},
            )

            mock_log_metric.assert_called_once()

            # Check the metric that was logged
            metric = mock_log_metric.call_args[0][0]
            assert metric.name == "http_request_duration"
            assert metric.metric_type == MetricType.REQUEST
            assert metric.value == 0.75
            assert metric.unit == "seconds"
            assert metric.component == "test_component"
            assert metric.operation == "GET https://example.com/api"
            assert metric.correlation_id == "test-correlation-id"
            assert metric.metadata["method"] == "GET"
            assert metric.metadata["url"] == "https://example.com/api"
            assert metric.metadata["status_code"] == 200
            assert metric.metadata["success"] is True
            assert metric.metadata["extra"] == "data"

    def test_log_memory_usage(self, performance_logger: PerformanceLogger) -> None:
        """Test log_memory_usage method."""
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600  # 100 MB
        mock_memory_info.vms = 209715200  # 200 MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.pid = 12345

        mock_system_memory = MagicMock()
        mock_system_memory.total = 8589934592  # 8 GB
        mock_system_memory.available = 4294967296  # 4 GB
        mock_system_memory.used = 4294967296  # 4 GB
        mock_system_memory.percent = 50.0

        with patch("calendarbot.monitoring.performance.psutil.Process", return_value=mock_process):
            with patch(
                "calendarbot.monitoring.performance.psutil.virtual_memory",
                return_value=mock_system_memory,
            ):
                with patch.object(performance_logger, "log_metric") as mock_log_metric:
                    performance_logger.log_memory_usage(
                        component="test_component",
                        operation="test_operation",
                        correlation_id="test-correlation-id",
                    )

                    assert mock_log_metric.call_count == 2

                    # Check the first metric (RSS)
                    rss_metric = mock_log_metric.call_args_list[0][0][0]
                    assert rss_metric.name == "memory_rss"
                    assert rss_metric.metric_type == MetricType.MEMORY
                    assert rss_metric.value == 100.0  # 100 MB
                    assert rss_metric.unit == "MB"
                    assert rss_metric.component == "test_component"
                    assert rss_metric.operation == "test_operation"
                    assert rss_metric.correlation_id == "test-correlation-id"
                    assert rss_metric.metadata["memory_type"] == "rss"
                    assert rss_metric.metadata["vms"] == 200.0  # 200 MB
                    assert rss_metric.metadata["pid"] == 12345

                    # Check the second metric (System memory)
                    sys_metric = mock_log_metric.call_args_list[1][0][0]
                    assert sys_metric.name == "system_memory_usage"
                    assert sys_metric.metric_type == MetricType.SYSTEM
                    assert sys_metric.value == 50.0  # 50%
                    assert sys_metric.unit == "percent"
                    assert sys_metric.component == "test_component"
                    assert sys_metric.operation == "test_operation"
                    assert sys_metric.correlation_id == "test-correlation-id"
                    assert sys_metric.metadata["total_mb"] == 8192.0  # 8 GB
                    assert sys_metric.metadata["available_mb"] == 4096.0  # 4 GB
                    assert sys_metric.metadata["used_mb"] == 4096.0  # 4 GB

    def test_log_memory_usage_exception(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test log_memory_usage method with exception."""
        with patch(
            "calendarbot.monitoring.performance.psutil.Process", side_effect=Exception("Test error")
        ):
            performance_logger.log_memory_usage()

            mock_logger.exception.assert_called_once_with("Failed to log memory usage")

    def test_log_cache_performance(self, performance_logger: PerformanceLogger) -> None:
        """Test log_cache_performance method."""
        with patch.object(performance_logger, "log_metric") as mock_log_metric:
            performance_logger.log_cache_performance(
                cache_name="test_cache",
                hits=80,
                misses=20,
                total_requests=100,
                component="test_component",
                correlation_id="test-correlation-id",
            )

            mock_log_metric.assert_called_once()

            # Check the metric that was logged
            metric = mock_log_metric.call_args[0][0]
            assert metric.name == "test_cache_hit_rate"
            assert metric.metric_type == MetricType.CACHE
            assert metric.value == 0.8  # 80% hit rate
            assert metric.unit == "ratio"
            assert metric.component == "test_component"
            assert metric.operation == "cache_performance"
            assert metric.correlation_id == "test-correlation-id"
            assert metric.metadata["cache_name"] == "test_cache"
            assert metric.metadata["hits"] == 80
            assert metric.metadata["misses"] == 20
            assert metric.metadata["total_requests"] == 100
            assert metric.metadata["miss_rate"] == 0.2  # 20% miss rate

    def test_log_cache_performance_zero_requests(
        self, performance_logger: PerformanceLogger
    ) -> None:
        """Test log_cache_performance method with zero requests."""
        with patch.object(performance_logger, "log_metric") as mock_log_metric:
            performance_logger.log_cache_performance(
                cache_name="test_cache", hits=0, misses=0, total_requests=0
            )

            mock_log_metric.assert_called_once()

            # Check the metric that was logged
            metric = mock_log_metric.call_args[0][0]
            assert metric.value == 0  # 0% hit rate
            assert metric.metadata["miss_rate"] == 0  # 0% miss rate

    def test_log_database_performance(self, performance_logger: PerformanceLogger) -> None:
        """Test log_database_performance method."""
        with patch.object(performance_logger, "log_metric") as mock_log_metric:
            performance_logger.log_database_performance(
                query_type="SELECT",
                duration=0.05,
                rows_affected=10,
                component="test_component",
                correlation_id="test-correlation-id",
                metadata={"query": "SELECT * FROM test"},
            )

            mock_log_metric.assert_called_once()

            # Check the metric that was logged
            metric = mock_log_metric.call_args[0][0]
            assert metric.name == "database_query_duration"
            assert metric.metric_type == MetricType.DATABASE
            assert metric.value == 0.05
            assert metric.unit == "seconds"
            assert metric.component == "test_component"
            assert metric.operation == "SELECT"
            assert metric.correlation_id == "test-correlation-id"
            assert metric.metadata["query_type"] == "SELECT"
            assert metric.metadata["rows_affected"] == 10
            assert metric.metadata["query"] == "SELECT * FROM test"

    def test_check_thresholds_request_duration_error(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test _check_thresholds method with request duration error threshold."""
        performance_logger.thresholds["request_duration_error"] = 10.0

        metric = PerformanceMetric(
            name="http_request_duration", metric_type=MetricType.REQUEST, value=15.0
        )

        performance_logger._check_thresholds(metric)

        mock_logger.error.assert_called_once()
        assert (
            "Request duration critical: 15.00s exceeds 10.0s threshold"
            in mock_logger.error.call_args[0][0]
        )

    def test_check_thresholds_request_duration_warning(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test _check_thresholds method with request duration warning threshold."""
        performance_logger.thresholds["request_duration_warning"] = 5.0
        performance_logger.thresholds["request_duration_error"] = 10.0

        metric = PerformanceMetric(
            name="http_request_duration", metric_type=MetricType.REQUEST, value=7.5
        )

        performance_logger._check_thresholds(metric)

        mock_logger.warning.assert_called_once()
        assert (
            "Request duration high: 7.50s exceeds 5.0s threshold"
            in mock_logger.warning.call_args[0][0]
        )

    def test_check_thresholds_memory_usage_error(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test _check_thresholds method with memory usage error threshold."""
        performance_logger.thresholds["memory_usage_error"] = 1000

        metric = PerformanceMetric(name="memory_rss", metric_type=MetricType.MEMORY, value=1200)

        performance_logger._check_thresholds(metric)

        mock_logger.error.assert_called_once()
        assert (
            "Memory usage critical: 1200.0MB exceeds 1000MB threshold"
            in mock_logger.error.call_args[0][0]
        )

    def test_check_thresholds_memory_usage_warning(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test _check_thresholds method with memory usage warning threshold."""
        performance_logger.thresholds["memory_usage_warning"] = 500
        performance_logger.thresholds["memory_usage_error"] = 1000

        metric = PerformanceMetric(name="memory_rss", metric_type=MetricType.MEMORY, value=750)

        performance_logger._check_thresholds(metric)

        mock_logger.warning.assert_called_once()
        assert (
            "Memory usage high: 750.0MB exceeds 500MB threshold"
            in mock_logger.warning.call_args[0][0]
        )

    def test_check_thresholds_cache_miss_rate_error(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test _check_thresholds method with cache miss rate error threshold."""
        performance_logger.thresholds["cache_miss_rate_error"] = 0.6

        metric = PerformanceMetric(
            name="test_cache_hit_rate", metric_type=MetricType.CACHE, metadata={"miss_rate": 0.7}
        )

        performance_logger._check_thresholds(metric)

        mock_logger.error.assert_called_once()
        assert (
            "Cache miss rate critical: 70.0% exceeds 60.0% threshold"
            in mock_logger.error.call_args[0][0]
        )

    def test_check_thresholds_cache_miss_rate_warning(
        self, performance_logger: PerformanceLogger, mock_logger: MagicMock
    ) -> None:
        """Test _check_thresholds method with cache miss rate warning threshold."""
        performance_logger.thresholds["cache_miss_rate_warning"] = 0.3
        performance_logger.thresholds["cache_miss_rate_error"] = 0.6

        metric = PerformanceMetric(
            name="test_cache_hit_rate", metric_type=MetricType.CACHE, metadata={"miss_rate": 0.4}
        )

        performance_logger._check_thresholds(metric)

        mock_logger.warning.assert_called_once()
        assert (
            "Cache miss rate high: 40.0% exceeds 30.0% threshold"
            in mock_logger.warning.call_args[0][0]
        )

    def test_add_to_cache(self, performance_logger: PerformanceLogger) -> None:
        """Test _add_to_cache method."""
        metric = PerformanceMetric(name="test_metric")

        performance_logger._add_to_cache(metric)

        assert metric in performance_logger._metrics_cache
        assert len(performance_logger._metrics_cache) == 1

    def test_add_to_cache_limit(self, performance_logger: PerformanceLogger) -> None:
        """Test _add_to_cache method with cache size limit."""
        # Set a small cache size for testing
        performance_logger.cache_size = 3

        # Add metrics to fill the cache
        metrics = [PerformanceMetric(name=f"metric_{i}") for i in range(5)]

        for metric in metrics:
            performance_logger._add_to_cache(metric)

        # Check that only the most recent metrics are kept
        assert len(performance_logger._metrics_cache) == 3
        assert metrics[2] in performance_logger._metrics_cache
        assert metrics[3] in performance_logger._metrics_cache
        assert metrics[4] in performance_logger._metrics_cache
        assert metrics[0] not in performance_logger._metrics_cache
        assert metrics[1] not in performance_logger._metrics_cache

    def test_get_performance_summary(self, performance_logger: PerformanceLogger) -> None:
        """Test get_performance_summary method."""
        # Create metrics with different timestamps
        now = datetime.now(timezone.utc)

        # Recent metrics (within the last hour)
        recent_metrics = [
            PerformanceMetric(
                name="recent_metric_1",
                metric_type=MetricType.TIMER,
                value=1.0,
                timestamp=now - timedelta(minutes=30),
            ),
            PerformanceMetric(
                name="recent_metric_2",
                metric_type=MetricType.REQUEST,
                value=2.0,
                timestamp=now - timedelta(minutes=45),
            ),
        ]

        # Old metric (more than an hour ago)
        old_metric = PerformanceMetric(
            name="old_metric",
            metric_type=MetricType.GAUGE,
            value=3.0,
            timestamp=now - timedelta(hours=2),
        )

        # Add metrics to cache
        performance_logger._metrics_cache = recent_metrics + [old_metric]

        # Get summary for the last hour
        summary = performance_logger.get_performance_summary(hours=1)

        assert summary["total_metrics"] == 2
        assert summary["time_period_hours"] == 1
        assert "by_type" in summary
        assert "timer" in summary["by_type"]
        assert "request" in summary["by_type"]
        assert "gauge" not in summary["by_type"]
        assert summary["by_type"]["timer"]["count"] == 1
        assert summary["by_type"]["timer"]["avg_value"] == 1.0
        assert summary["by_type"]["request"]["count"] == 1
        assert summary["by_type"]["request"]["avg_value"] == 2.0
        assert summary["avg_request_duration"] == 2.0
        assert summary["oldest_metric"] == (now - timedelta(minutes=45)).isoformat()
        assert summary["newest_metric"] == (now - timedelta(minutes=30)).isoformat()

    def test_get_performance_summary_empty(self, performance_logger: PerformanceLogger) -> None:
        """Test get_performance_summary method with empty cache."""
        # Ensure cache is empty
        performance_logger._metrics_cache = []

        # Get summary
        summary = performance_logger.get_performance_summary()

        assert summary["total_metrics"] == 0
        assert summary["time_period_hours"] == 1
        assert "by_type" not in summary
        assert "avg_request_duration" not in summary
        assert "oldest_metric" not in summary
        assert "newest_metric" not in summary


class TestPerformanceLoggerMixin:
    """Tests for the PerformanceLoggerMixin class."""

    class TestClass(PerformanceLoggerMixin):
        """Test class that inherits from PerformanceLoggerMixin."""

    @pytest.fixture
    def mixin_instance(self) -> TestClass:
        """Create an instance of the test class with PerformanceLoggerMixin."""
        with patch("calendarbot.monitoring.performance.get_performance_logger") as mock_get_logger:
            instance = self.TestClass()
            return instance

    def test_initialization(self, mixin_instance: TestClass) -> None:
        """Test PerformanceLoggerMixin initialization."""
        assert hasattr(mixin_instance, "_perf_logger")

    def test_start_performance_timer(self, mixin_instance: TestClass) -> None:
        """Test start_performance_timer method."""
        mock_logger = MagicMock()
        mixin_instance._perf_logger = mock_logger
        mock_logger.start_timer.return_value = "timer-123"

        timer_id = mixin_instance.start_performance_timer("test_operation", "test-correlation-id")

        assert timer_id == "timer-123"
        mock_logger.start_timer.assert_called_once_with(
            "test_operation", "TestClass", "test-correlation-id"
        )

    def test_stop_performance_timer(self, mixin_instance: TestClass) -> None:
        """Test stop_performance_timer method."""
        mock_logger = MagicMock()
        mixin_instance._perf_logger = mock_logger
        mock_logger.stop_timer.return_value = 1.5

        duration = mixin_instance.stop_performance_timer(
            "timer-123", "test_operation", "test-correlation-id", {"extra": "metadata"}
        )

        assert duration == 1.5
        mock_logger.stop_timer.assert_called_once_with(
            "timer-123", "TestClass", "test_operation", "test-correlation-id", {"extra": "metadata"}
        )

    def test_log_performance_metric(self, mixin_instance: TestClass) -> None:
        """Test log_performance_metric method."""
        mock_logger = MagicMock()
        mixin_instance._perf_logger = mock_logger

        mixin_instance.log_performance_metric(
            name="test_metric",
            value=42,
            metric_type=MetricType.COUNTER,
            unit="count",
            operation="test_operation",
            correlation_id="test-correlation-id",
            metadata={"extra": "data"},
        )

        mock_logger.log_metric.assert_called_once()
        metric = mock_logger.log_metric.call_args[0][0]
        assert metric.name == "test_metric"
        assert metric.value == 42
        assert metric.metric_type == MetricType.COUNTER
        assert metric.unit == "count"
        assert metric.component == "TestClass"
        assert metric.operation == "test_operation"
        assert metric.correlation_id == "test-correlation-id"
        assert metric.metadata == {"extra": "data"}


class TestContextManagers:
    """Tests for the context managers in the performance module."""

    def test_performance_timer_context_manager(self) -> None:
        """Test performance_timer context manager."""
        mock_logger = MagicMock()
        mock_logger.start_timer.return_value = "timer-123"

        with performance_timer(
            operation="test_operation",
            component="test_component",
            correlation_id="test-correlation-id",
            logger=mock_logger,
        ) as timer_id:
            assert timer_id == "timer-123"
            mock_logger.start_timer.assert_called_once_with(
                "test_operation", "test_component", "test-correlation-id"
            )

        mock_logger.stop_timer.assert_called_once_with(
            "timer-123", "test_component", "test_operation", "test-correlation-id"
        )

    def test_performance_timer_with_exception(self) -> None:
        """Test performance_timer context manager with exception."""
        mock_logger = MagicMock()
        mock_logger.start_timer.return_value = "timer-123"

        try:
            with performance_timer("test_operation", logger=mock_logger):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Timer should still be stopped even if an exception occurs
        mock_logger.stop_timer.assert_called_once()

    def test_memory_monitor_context_manager(self) -> None:
        """Test memory_monitor context manager."""
        mock_logger = MagicMock()

        with memory_monitor(
            component="test_component",
            operation="test_operation",
            correlation_id="test-correlation-id",
            logger=mock_logger,
        ):
            # Check that memory usage was logged at the start
            mock_logger.log_memory_usage.assert_called_once_with(
                "test_component", "test_operation_start", "test-correlation-id"
            )
            mock_logger.log_memory_usage.reset_mock()

        # Check that memory usage was logged at the end
        mock_logger.log_memory_usage.assert_called_once_with(
            "test_component", "test_operation_end", "test-correlation-id"
        )

    def test_memory_monitor_with_exception(self) -> None:
        """Test memory_monitor context manager with exception."""
        mock_logger = MagicMock()

        try:
            with memory_monitor(logger=mock_logger):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Memory usage should still be logged at the end even if an exception occurs
        assert mock_logger.log_memory_usage.call_count == 2

    def test_cache_monitor_context_manager(self) -> None:
        """Test cache_monitor context manager."""
        mock_logger = MagicMock()

        with cache_monitor(
            cache_name="test_cache",
            component="test_component",
            correlation_id="test-correlation-id",
            logger=mock_logger,
        ) as monitor:
            # Record some hits and misses
            monitor.record_hit()
            monitor.record_hit()
            monitor.record_miss()

            # Check monitor state
            assert monitor.hits == 2
            assert monitor.misses == 1
            assert monitor.total_requests == 3

        # Check that cache performance was logged
        mock_logger.log_cache_performance.assert_called_once_with(
            "test_cache", 2, 1, 3, "test_component", "test-correlation-id"
        )

    def test_cache_monitor_with_no_requests(self) -> None:
        """Test cache_monitor context manager with no requests."""
        mock_logger = MagicMock()

        with cache_monitor("test_cache", logger=mock_logger) as monitor:
            # Don't record any hits or misses
            pass

        # No log should be made if there are no requests
        mock_logger.log_cache_performance.assert_not_called()

    def test_cache_monitor_with_exception(self) -> None:
        """Test cache_monitor context manager with exception."""
        mock_logger = MagicMock()

        try:
            with cache_monitor("test_cache", logger=mock_logger) as monitor:
                monitor.record_hit()
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Cache performance should still be logged even if an exception occurs
        mock_logger.log_cache_performance.assert_called_once()


class TestPerformanceMonitorDecorator:
    """Tests for the performance_monitor decorator."""

    def test_performance_monitor_basic(self) -> None:
        """Test performance_monitor decorator basic functionality."""
        mock_logger = MagicMock()

        with patch(
            "calendarbot.monitoring.performance.get_performance_logger", return_value=mock_logger
        ):

            @performance_monitor()
            def test_function():
                return "test_result"

            result = test_function()

            assert result == "test_result"
            assert mock_logger.log_memory_usage.call_count == 0  # No memory tracking by default

    def test_performance_monitor_with_custom_params(self) -> None:
        """Test performance_monitor decorator with custom parameters."""
        mock_logger = MagicMock()

        with patch(
            "calendarbot.monitoring.performance.get_performance_logger", return_value=mock_logger
        ):

            @performance_monitor(
                operation="custom_operation",
                component="custom_component",
                track_memory=True,
                correlation_id="test-correlation-id",
            )
            def test_function():
                return "test_result"

            result = test_function()

            assert result == "test_result"
            # Should track memory before and after
            assert mock_logger.log_memory_usage.call_count == 2
            # First call should be for start
            assert mock_logger.log_memory_usage.call_args_list[0][0][1] == "custom_operation_start"
            # Second call should be for end
            assert mock_logger.log_memory_usage.call_args_list[1][0][1] == "custom_operation_end"

    def test_performance_monitor_with_exception(self) -> None:
        """Test performance_monitor decorator with exception."""
        mock_logger = MagicMock()

        with patch(
            "calendarbot.monitoring.performance.get_performance_logger", return_value=mock_logger
        ):

            @performance_monitor(track_memory=True)
            def test_function():
                raise ValueError("Test exception")

            try:
                test_function()
            except ValueError:
                pass

            # Memory tracking should still happen at the start, but not at the end due to exception
            assert mock_logger.log_memory_usage.call_count == 1


class TestGlobalFunctions:
    """Tests for the global functions in the performance module."""

    def test_get_performance_logger_creates_new_instance(self) -> None:
        """Test get_performance_logger creates a new instance if none exists."""
        with patch("calendarbot.monitoring.performance._performance_logger", None):
            with patch("calendarbot.monitoring.performance.PerformanceLogger") as mock_logger_class:
                mock_logger = MagicMock()
                mock_logger_class.return_value = mock_logger

                logger = get_performance_logger()

                assert logger == mock_logger
                mock_logger_class.assert_called_once()

    def test_get_performance_logger_returns_existing_instance(self) -> None:
        """Test get_performance_logger returns existing instance if one exists."""
        mock_logger = MagicMock()

        with patch("calendarbot.monitoring.performance._performance_logger", mock_logger):
            logger = get_performance_logger()

            assert logger == mock_logger

    def test_init_performance_logging(self) -> None:
        """Test init_performance_logging function."""
        mock_settings = MagicMock()
        mock_logger = MagicMock()

        with patch(
            "calendarbot.monitoring.performance.PerformanceLogger", return_value=mock_logger
        ) as mock_logger_class:
            logger = init_performance_logging(mock_settings)

            assert logger == mock_logger
            mock_logger_class.assert_called_once_with(mock_settings)
