"""Tests for source models."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from calendarbot.sources.models import (
    SourceConfig,
    SourceHealthCheck,
    SourceInfo,
    SourceMetrics,
    SourceStatus,
    SourceType,
)


class TestSourceType:
    """Test suite for SourceType enum."""

    def test_source_type_has_expected_values(self) -> None:
        """Test SourceType enum has expected values."""
        # Assert
        assert SourceType.ICS.value == "ics"
        assert SourceType.CALDAV.value == "caldav"
        assert SourceType.OUTLOOK.value == "outlook"

    def test_source_type_can_be_used_as_string(self) -> None:
        """Test SourceType enum can be used as string."""
        # Arrange
        source_type = SourceType.ICS

        # Act & Assert
        # Use the value property to get the string representation
        assert f"Type: {source_type.value}" == "Type: ics"


class TestSourceStatus:
    """Test suite for SourceStatus enum."""

    def test_source_status_has_expected_values(self) -> None:
        """Test SourceStatus enum has expected values."""
        # Assert
        assert SourceStatus.HEALTHY.value == "healthy"
        assert SourceStatus.ERROR.value == "error"
        assert SourceStatus.UNKNOWN.value == "unknown"
        assert SourceStatus.WARNING.value == "warning"
        assert SourceStatus.DISABLED.value == "disabled"

    def test_source_status_can_be_used_as_string(self) -> None:
        """Test SourceStatus enum can be used as string."""
        # Arrange
        status = SourceStatus.HEALTHY

        # Act & Assert
        # Use the value property to get the string representation
        assert f"Status: {status.value}" == "Status: healthy"


class TestSourceConfig:
    """Test suite for SourceConfig model."""

    def test_source_config_when_required_fields_then_creates_instance(self) -> None:
        """Test SourceConfig creates instance with required fields."""
        # Arrange & Act
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
        )

        # Assert
        assert config.name == "Test Source"
        assert config.type == "ics"
        assert config.url == "https://example.com/calendar.ics"
        assert config.enabled is True  # Default value
        assert config.timeout == 30  # Default value
        assert config.refresh_interval == 300  # Default value

    def test_source_config_when_all_fields_then_creates_instance(self) -> None:
        """Test SourceConfig creates instance with all fields."""
        # Arrange & Act
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=False,
            timeout=60,
            refresh_interval=600,
            auth_type="basic",
            auth_config={"username": "user", "password": "pass"},
            custom_headers={"User-Agent": "Test"},
            validate_ssl=False,
            max_retries=5,
            retry_backoff=2.0,
        )

        # Assert
        assert config.name == "Test Source"
        assert config.type == "ics"
        assert config.url == "https://example.com/calendar.ics"
        assert config.enabled is False
        assert config.timeout == 60
        assert config.refresh_interval == 600
        assert config.auth_type == "basic"
        assert config.auth_config == {"username": "user", "password": "pass"}
        assert config.custom_headers == {"User-Agent": "Test"}
        assert config.validate_ssl is False
        assert config.max_retries == 5
        assert config.retry_backoff == 2.0

    def test_source_config_when_missing_required_fields_then_raises_error(self) -> None:
        """Test SourceConfig raises error when missing required fields."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError):
            SourceConfig()  # type: ignore

        with pytest.raises(ValueError):
            SourceConfig(name="Test Source")  # type: ignore

        with pytest.raises(ValueError):
            SourceConfig(name="Test Source", type="ics")  # type: ignore

    def test_source_config_when_enum_as_string_then_accepts_value(self) -> None:
        """Test SourceConfig accepts enum value as string."""
        # Arrange & Act
        config = SourceConfig(
            name="Test Source",
            type=SourceType.ICS.value,
            url="https://example.com/calendar.ics",
        )

        # Assert
        assert config.type == "ics"


class TestSourceHealthCheck:
    """Test suite for SourceHealthCheck model."""

    def test_source_health_check_when_default_values_then_creates_instance(self) -> None:
        """Test SourceHealthCheck creates instance with default values."""
        # Arrange & Act
        health = SourceHealthCheck()

        # Assert
        assert health.status == SourceStatus.UNKNOWN
        assert health.response_time_ms is None
        assert health.http_status is None
        assert health.content_size is None
        assert health.content_type is None
        assert health.error_message is None
        assert health.error_count == 0
        assert health.last_successful_fetch is None
        assert health.events_fetched == 0

    def test_source_health_check_when_custom_values_then_creates_instance(self) -> None:
        """Test SourceHealthCheck creates instance with custom values."""
        # Arrange
        now = datetime.now()

        # Act
        health = SourceHealthCheck(
            timestamp=now,
            status=SourceStatus.HEALTHY,
            response_time_ms=150.5,
            http_status=200,
            content_size=1024,
            content_type="text/calendar",
            error_message=None,
            error_count=0,
            last_successful_fetch=now,
            events_fetched=42,
        )

        # Assert
        assert health.timestamp == now
        assert health.status == SourceStatus.HEALTHY
        assert health.response_time_ms == 150.5
        assert health.http_status == 200
        assert health.content_size == 1024
        assert health.content_type == "text/calendar"
        assert health.error_message is None
        assert health.error_count == 0
        assert health.last_successful_fetch == now
        assert health.events_fetched == 42

    def test_is_healthy_when_status_healthy_then_returns_true(self) -> None:
        """Test is_healthy returns True when status is HEALTHY."""
        # Arrange
        health = SourceHealthCheck(status=SourceStatus.HEALTHY)

        # Act & Assert
        assert health.is_healthy is True

    def test_is_healthy_when_status_not_healthy_then_returns_false(self) -> None:
        """Test is_healthy returns False when status is not HEALTHY."""
        # Arrange
        health_error = SourceHealthCheck(status=SourceStatus.ERROR)
        health_unknown = SourceHealthCheck(status=SourceStatus.UNKNOWN)

        # Act & Assert
        assert health_error.is_healthy is False
        assert health_unknown.is_healthy is False

    def test_has_errors_when_status_error_then_returns_true(self) -> None:
        """Test has_errors returns True when status is ERROR."""
        # Arrange
        health = SourceHealthCheck(status=SourceStatus.ERROR)

        # Act & Assert
        assert health.has_errors is True

    def test_has_errors_when_status_not_error_then_returns_false(self) -> None:
        """Test has_errors returns False when status is not ERROR."""
        # Arrange
        health_healthy = SourceHealthCheck(status=SourceStatus.HEALTHY)
        health_unknown = SourceHealthCheck(status=SourceStatus.UNKNOWN)

        # Act & Assert
        assert health_healthy.has_errors is False
        assert health_unknown.has_errors is False

    def test_update_success_when_called_then_updates_fields(self) -> None:
        """Test update_success updates fields correctly."""
        # Arrange
        health = SourceHealthCheck()

        # Act
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now

            health.update_success(150.5, 42)

            # Assert
            assert health.status == SourceStatus.HEALTHY
            assert health.response_time_ms == 150.5
            assert health.last_successful_fetch == mock_now
            assert health.events_fetched == 42
            assert health.error_message is None

    def test_update_error_when_called_then_updates_fields(self) -> None:
        """Test update_error updates fields correctly."""
        # Arrange
        health = SourceHealthCheck()

        # Act
        health.update_error("Test error", 500)

        # Assert
        assert health.status == SourceStatus.ERROR
        assert health.error_message == "Test error"
        assert health.http_status == 500
        assert health.error_count == 1


class TestSourceMetrics:
    """Test suite for SourceMetrics model."""

    def test_source_metrics_when_default_values_then_creates_instance(self) -> None:
        """Test SourceMetrics creates instance with default values."""
        # Arrange & Act
        metrics = SourceMetrics()

        # Assert
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.avg_response_time_ms == 0.0
        assert metrics.min_response_time_ms == 0.0
        assert metrics.max_response_time_ms == 0.0
        assert metrics.total_events_fetched == 0
        assert metrics.last_event_count == 0
        assert metrics.consecutive_failures == 0
        assert metrics.last_error is None
        assert metrics.last_error_time is None
        assert metrics.first_fetch_time is None
        assert metrics.last_fetch_time is None
        assert metrics.last_successful_fetch is None

    def test_source_metrics_when_custom_values_then_creates_instance(self) -> None:
        """Test SourceMetrics creates instance with custom values."""
        # Arrange
        now = datetime.now()

        # Act
        metrics = SourceMetrics(
            total_requests=10,
            successful_requests=8,
            failed_requests=2,
            avg_response_time_ms=150.5,
            min_response_time_ms=100.0,
            max_response_time_ms=200.0,
            total_events_fetched=100,
            last_event_count=20,
            consecutive_failures=0,
            last_error="Test error",
            last_error_time=now - timedelta(days=1),
            first_fetch_time=now - timedelta(days=7),
            last_fetch_time=now,
            last_successful_fetch=now,
        )

        # Assert
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 8
        assert metrics.failed_requests == 2
        assert metrics.avg_response_time_ms == 150.5
        assert metrics.min_response_time_ms == 100.0
        assert metrics.max_response_time_ms == 200.0
        assert metrics.total_events_fetched == 100
        assert metrics.last_event_count == 20
        assert metrics.consecutive_failures == 0
        assert metrics.last_error == "Test error"
        assert metrics.last_error_time == now - timedelta(days=1)
        assert metrics.first_fetch_time == now - timedelta(days=7)
        assert metrics.last_fetch_time == now
        assert metrics.last_successful_fetch == now

    def test_success_rate_when_no_requests_then_returns_zero(self) -> None:
        """Test success_rate returns 0 when no requests."""
        # Arrange
        metrics = SourceMetrics()

        # Act & Assert
        assert metrics.success_rate == 0.0

    def test_success_rate_when_has_requests_then_calculates_percentage(self) -> None:
        """Test success_rate calculates percentage correctly."""
        # Arrange
        metrics = SourceMetrics(total_requests=10, successful_requests=8)

        # Act & Assert
        assert metrics.success_rate == 80.0

    def test_is_recently_successful_when_no_success_then_returns_false(self) -> None:
        """Test is_recently_successful returns False when no successful fetch."""
        # Arrange
        metrics = SourceMetrics()

        # Act & Assert
        assert metrics.is_recently_successful is False

    def test_is_recently_successful_when_recent_success_then_returns_true(self) -> None:
        """Test is_recently_successful returns True for recent success."""
        # Arrange
        now = datetime.now()
        metrics = SourceMetrics(last_successful_fetch=now)

        # Act & Assert
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(minutes=5)
            assert metrics.is_recently_successful is True

    def test_is_recently_successful_when_old_success_then_returns_false(self) -> None:
        """Test is_recently_successful returns False for old success."""
        # Arrange
        now = datetime.now()
        metrics = SourceMetrics(last_successful_fetch=now)

        # Act & Assert
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(hours=25)
            assert metrics.is_recently_successful is False

    def test_record_success_when_first_success_then_initializes_metrics(self) -> None:
        """Test record_success initializes metrics on first success."""
        # Arrange
        metrics = SourceMetrics()

        # Act
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now

            metrics.record_success(150.5, 42)

            # Assert
            assert metrics.total_requests == 1
            assert metrics.successful_requests == 1
            assert metrics.failed_requests == 0
            assert metrics.avg_response_time_ms == 150.5
            assert metrics.min_response_time_ms == 150.5
            assert metrics.max_response_time_ms == 150.5
            assert metrics.total_events_fetched == 42
            assert metrics.last_event_count == 42
            assert metrics.consecutive_failures == 0
            assert metrics.first_fetch_time == mock_now
            assert metrics.last_fetch_time == mock_now
            assert metrics.last_successful_fetch == mock_now

    def test_record_success_when_subsequent_success_then_updates_metrics(self) -> None:
        """Test record_success updates metrics on subsequent success."""
        # Arrange
        now = datetime.now()
        metrics = SourceMetrics(
            total_requests=5,
            successful_requests=4,
            failed_requests=1,
            avg_response_time_ms=100.0,
            min_response_time_ms=80.0,
            max_response_time_ms=120.0,
            total_events_fetched=100,
            last_event_count=20,
            consecutive_failures=1,
            first_fetch_time=now - timedelta(days=7),
            last_fetch_time=now - timedelta(hours=1),
            last_successful_fetch=now - timedelta(hours=1),
        )

        # Act
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_now = now
            mock_datetime.now.return_value = mock_now

            metrics.record_success(150.5, 42)

            # Assert
            assert metrics.total_requests == 6
            assert metrics.successful_requests == 5
            assert metrics.failed_requests == 1
            assert metrics.min_response_time_ms == 80.0
            assert metrics.max_response_time_ms == 150.5
            assert metrics.total_events_fetched == 142
            assert metrics.last_event_count == 42
            assert metrics.consecutive_failures == 0
            assert metrics.first_fetch_time == now - timedelta(days=7)
            assert metrics.last_fetch_time == mock_now
            assert metrics.last_successful_fetch == mock_now

    def test_record_failure_when_first_failure_then_initializes_metrics(self) -> None:
        """Test record_failure initializes metrics on first failure."""
        # Arrange
        metrics = SourceMetrics()

        # Act
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now

            metrics.record_failure("Test error")

            # Assert
            assert metrics.total_requests == 1
            assert metrics.successful_requests == 0
            assert metrics.failed_requests == 1
            assert metrics.consecutive_failures == 1
            assert metrics.last_error == "Test error"
            assert metrics.last_error_time == mock_now
            assert metrics.first_fetch_time == mock_now
            assert metrics.last_fetch_time == mock_now
            assert metrics.last_successful_fetch is None

    def test_record_failure_when_subsequent_failure_then_updates_metrics(self) -> None:
        """Test record_failure updates metrics on subsequent failure."""
        # Arrange
        now = datetime.now()
        metrics = SourceMetrics(
            total_requests=5,
            successful_requests=4,
            failed_requests=1,
            avg_response_time_ms=100.0,
            min_response_time_ms=80.0,
            max_response_time_ms=120.0,
            total_events_fetched=100,
            last_event_count=20,
            consecutive_failures=1,
            last_error="Previous error",
            last_error_time=now - timedelta(hours=1),
            first_fetch_time=now - timedelta(days=7),
            last_fetch_time=now - timedelta(hours=1),
            last_successful_fetch=now - timedelta(hours=2),
        )

        # Act
        with patch("calendarbot.sources.models.datetime") as mock_datetime:
            mock_now = now
            mock_datetime.now.return_value = mock_now

            metrics.record_failure("New error")

            # Assert
            assert metrics.total_requests == 6
            assert metrics.successful_requests == 4
            assert metrics.failed_requests == 2
            assert metrics.consecutive_failures == 2
            assert metrics.last_error == "New error"
            assert metrics.last_error_time == mock_now
            assert metrics.first_fetch_time == now - timedelta(days=7)
            assert metrics.last_fetch_time == mock_now
            assert metrics.last_successful_fetch == now - timedelta(hours=2)


class TestSourceInfo:
    """Test suite for SourceInfo model."""

    def test_source_info_when_required_fields_then_creates_instance(self) -> None:
        """Test SourceInfo creates instance with required fields."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
        )
        health = SourceHealthCheck()
        metrics = SourceMetrics()

        # Act
        info = SourceInfo(
            config=config,
            health=health,
            metrics=metrics,
        )

        # Assert
        assert info.config == config
        assert info.health == health
        assert info.metrics == metrics
        assert info.last_cache_update is None
        assert info.cached_events_count == 0

    def test_source_info_when_all_fields_then_creates_instance(self) -> None:
        """Test SourceInfo creates instance with all fields."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
        )
        health = SourceHealthCheck()
        metrics = SourceMetrics()
        now = datetime.now()

        # Act
        info = SourceInfo(
            config=config,
            health=health,
            metrics=metrics,
            last_cache_update=now,
            cached_events_count=42,
        )

        # Assert
        assert info.config == config
        assert info.health == health
        assert info.metrics == metrics
        assert info.last_cache_update == now
        assert info.cached_events_count == 42

    def test_display_name_when_called_then_returns_config_name(self) -> None:
        """Test display_name returns config name."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
        )
        info = SourceInfo(
            config=config,
            health=SourceHealthCheck(),
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.display_name == "Test Source"

    def test_is_operational_when_enabled_and_healthy_then_returns_true(self) -> None:
        """Test is_operational returns True when enabled and healthy."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )
        health = SourceHealthCheck(status=SourceStatus.HEALTHY)
        info = SourceInfo(
            config=config,
            health=health,
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.is_operational is True

    def test_is_operational_when_disabled_then_returns_false(self) -> None:
        """Test is_operational returns False when disabled."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=False,
        )
        health = SourceHealthCheck(status=SourceStatus.HEALTHY)
        info = SourceInfo(
            config=config,
            health=health,
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.is_operational is False

    def test_is_operational_when_unhealthy_then_returns_false(self) -> None:
        """Test is_operational returns False when unhealthy."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )
        health = SourceHealthCheck(status=SourceStatus.ERROR)
        info = SourceInfo(
            config=config,
            health=health,
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.is_operational is False

    def test_status_summary_when_disabled_then_returns_disabled(self) -> None:
        """Test status_summary returns 'Disabled' when disabled."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=False,
        )
        info = SourceInfo(
            config=config,
            health=SourceHealthCheck(),
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.status_summary == "Disabled"

    def test_status_summary_when_healthy_then_returns_healthy_with_count(self) -> None:
        """Test status_summary returns 'Healthy' with event count when healthy."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )
        metrics = SourceMetrics(last_event_count=42)
        health = SourceHealthCheck(status=SourceStatus.HEALTHY)
        info = SourceInfo(
            config=config,
            health=health,
            metrics=metrics,
        )

        # Act & Assert
        assert info.status_summary == "Healthy (42 events)"

    def test_status_summary_when_error_then_returns_error_with_message(self) -> None:
        """Test status_summary returns 'Error' with message when error."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )
        health = SourceHealthCheck(
            status=SourceStatus.ERROR,
            error_message="Connection failed",
        )
        info = SourceInfo(
            config=config,
            health=health,
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.status_summary == "Error: Connection failed"

    def test_status_summary_when_unknown_then_returns_unknown(self) -> None:
        """Test status_summary returns 'Unknown' when unknown status."""
        # Arrange
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )
        health = SourceHealthCheck(status=SourceStatus.UNKNOWN)
        info = SourceInfo(
            config=config,
            health=health,
            metrics=SourceMetrics(),
        )

        # Act & Assert
        assert info.status_summary == "Unknown"

    def test_get_status_dict_when_called_then_returns_status_dict(self) -> None:
        """Test get_status_dict returns status dictionary with expected fields."""
        # Arrange
        now = datetime.now()
        config = SourceConfig(
            name="Test Source",
            type="ics",
            url="https://example.com/calendar.ics",
            enabled=True,
        )
        health = SourceHealthCheck(
            status=SourceStatus.HEALTHY,
            error_message=None,
        )
        # Create metrics with the values needed to calculate success_rate
        metrics = SourceMetrics(
            total_requests=100,
            successful_requests=90,
            last_successful_fetch=now,
            consecutive_failures=0,
            last_event_count=42,
        )
        info = SourceInfo(
            config=config,
            health=health,
            metrics=metrics,
            cached_events_count=42,
        )

        # Act
        status_dict = info.get_status_dict()

        # Assert
        assert status_dict["name"] == "Test Source"
        assert status_dict["type"] == "ics"
        assert status_dict["enabled"] is True
        assert status_dict["status"] == "healthy"
        assert status_dict["last_successful_fetch"] == now
        assert status_dict["success_rate"] == 90.0
        assert status_dict["consecutive_failures"] == 0
        assert status_dict["last_event_count"] == 42
        assert status_dict["cached_events_count"] == 42
        assert status_dict["error_message"] is None
