from unittest.mock import MagicMock

from calendarbot import monitoring
from calendarbot.monitoring import performance


def test_get_performance_logger_returns_noop_when_disabled(monkeypatch):
    """When monitoring is disabled via the monitoring gate, a NoOp logger is returned."""
    # Force the monitoring gate to report disabled
    monkeypatch.setattr(monitoring, "_is_monitoring_enabled", lambda: False)
    # Reset any existing global instance to ensure fresh creation
    monkeypatch.setattr(performance, "_performance_logger", None)
    logger = performance.get_performance_logger()
    assert isinstance(logger, monitoring.NoOpPerformanceLogger)


def test_sampling_interval_respected():
    """PerformanceLogger should pick up sampling interval from provided settings."""

    class FakeMonitoring:
        enabled = True
        sampling_interval_seconds = 10
        slow_write_threshold = 1024

    class FakeOptimization:
        small_device = False

    class FakeSettings:
        monitoring = FakeMonitoring()
        optimization = FakeOptimization()

    logger = performance.PerformanceLogger(FakeSettings())
    # Ensure configured sampling interval is applied to the logger instance
    assert logger._sampling_interval == 10


def test_metrics_buffering_and_flush(monkeypatch):
    """Metrics should be buffered and flushed only when flush threshold is reached."""

    class FakeMonitoring:
        enabled = True
        sampling_interval_seconds = 1
        slow_write_threshold = 1024

    class FakeOptimization:
        small_device = False

    class FakeSettings:
        monitoring = FakeMonitoring()
        optimization = FakeOptimization()

    logger = performance.PerformanceLogger(FakeSettings())

    # Replace metrics_logger with a mock to capture writes
    mock_metrics_logger = MagicMock()
    logger.metrics_logger = mock_metrics_logger

    # Set a small flush threshold for testing
    logger._flush_count = 3
    logger._write_buffer.clear()

    # Log fewer than _flush_count metrics -> should not flush yet
    for i in range(2):
        m = performance.PerformanceMetric(
            name=f"buffer_test_{i}",
            metric_type=performance.MetricType.GAUGE,
            value=1,
        )
        logger.log_metric(m)

    assert mock_metrics_logger.info.call_count == 0

    # Logging the third metric should trigger a flush
    m = performance.PerformanceMetric(
        name="buffer_test_trigger",
        metric_type=performance.MetricType.GAUGE,
        value=1,
    )
    logger.log_metric(m)

    # After flush, the metrics logger should have been called for each buffered metric
    assert mock_metrics_logger.info.call_count >= 3
