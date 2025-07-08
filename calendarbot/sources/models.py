"""Data models for calendar source management."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Supported calendar source types."""

    ICS = "ics"
    CALDAV = "caldav"  # For future extension
    OUTLOOK = "outlook"  # For future extension


class SourceStatus(str, Enum):
    """Source status values."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    DISABLED = "disabled"


class SourceConfig(BaseModel):
    """Configuration for a calendar source."""

    # Basic identification
    name: str = Field(..., description="Human-readable source name")
    type: SourceType = Field(..., description="Source type")
    enabled: bool = Field(default=True, description="Whether source is enabled")

    # Connection settings
    url: str = Field(..., description="Source URL")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    refresh_interval: int = Field(default=300, description="Refresh interval in seconds")

    # Authentication
    auth_type: Optional[str] = Field(default=None, description="Authentication type")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="Auth configuration")

    # Advanced settings
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")
    validate_ssl: bool = Field(default=True, description="Validate SSL certificates")

    # Retry and error handling
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff: float = Field(default=1.5, description="Retry backoff factor")

    model_config = ConfigDict(use_enum_values=True)


class SourceHealthCheck(BaseModel):
    """Health check result for a source."""

    timestamp: datetime = Field(default_factory=datetime.now)
    status: SourceStatus = SourceStatus.UNKNOWN
    response_time_ms: Optional[float] = None

    # Connection details
    http_status: Optional[int] = None
    content_size: Optional[int] = None
    content_type: Optional[str] = None

    # Error information
    error_message: Optional[str] = None
    error_count: int = 0

    # Success metrics
    last_successful_fetch: Optional[datetime] = None
    events_fetched: int = 0

    model_config = ConfigDict()

    @property
    def is_healthy(self) -> bool:
        """Check if source is healthy."""
        return self.status == SourceStatus.HEALTHY

    @property
    def has_errors(self) -> bool:
        """Check if source has errors."""
        return self.status == SourceStatus.ERROR

    def update_success(self, response_time: float, events_count: int = 0) -> None:
        """Update with successful fetch information."""
        self.status = SourceStatus.HEALTHY
        self.response_time_ms = response_time
        self.last_successful_fetch = datetime.now()
        self.events_fetched = events_count
        self.error_message = None

    def update_error(self, error_message: str, http_status: Optional[int] = None) -> None:
        """Update with error information."""
        self.status = SourceStatus.ERROR
        self.error_message = error_message
        self.http_status = http_status
        self.error_count += 1


class SourceMetrics(BaseModel):
    """Metrics and statistics for a source."""

    # Timing metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Response time metrics
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0

    # Data metrics
    total_events_fetched: int = 0
    last_event_count: int = 0

    # Error tracking
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    # Timing information
    first_fetch_time: Optional[datetime] = None
    last_fetch_time: Optional[datetime] = None
    last_successful_fetch: Optional[datetime] = None

    model_config = ConfigDict()

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def is_recently_successful(self) -> bool:
        """Check if source has been successful recently."""
        if not self.last_successful_fetch:
            return False

        # Consider successful if last success was within 24 hours
        time_diff = datetime.now() - self.last_successful_fetch
        return time_diff.total_seconds() < 86400  # 24 hours

    def record_success(self, response_time_ms: float, event_count: int) -> None:
        """Record a successful fetch."""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0

        # Update response time metrics
        self._update_response_times(response_time_ms)

        # Update event metrics
        self.total_events_fetched += event_count
        self.last_event_count = event_count

        # Update timing
        now = datetime.now()
        if not self.first_fetch_time:
            self.first_fetch_time = now
        self.last_fetch_time = now
        self.last_successful_fetch = now

    def record_failure(self, error_message: str) -> None:
        """Record a failed fetch."""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1

        # Update error tracking
        self.last_error = error_message
        self.last_error_time = datetime.now()

        # Update timing
        now = datetime.now()
        if not self.first_fetch_time:
            self.first_fetch_time = now
        self.last_fetch_time = now

    def _update_response_times(self, response_time_ms: float) -> None:
        """Update response time statistics."""
        if self.successful_requests == 1:
            # First successful request
            self.avg_response_time_ms = response_time_ms
            self.min_response_time_ms = response_time_ms
            self.max_response_time_ms = response_time_ms
        else:
            # Update running average
            total_time = self.avg_response_time_ms * (self.successful_requests - 1)
            self.avg_response_time_ms = (total_time + response_time_ms) / self.successful_requests

            # Update min/max
            self.min_response_time_ms = min(self.min_response_time_ms, response_time_ms)
            self.max_response_time_ms = max(self.max_response_time_ms, response_time_ms)


class SourceInfo(BaseModel):
    """Complete information about a calendar source."""

    config: SourceConfig
    health: SourceHealthCheck
    metrics: SourceMetrics

    # Cache information
    last_cache_update: Optional[datetime] = None
    cached_events_count: int = 0

    model_config = ConfigDict()

    @property
    def display_name(self) -> str:
        """Get display name for the source."""
        return self.config.name

    @property
    def is_operational(self) -> bool:
        """Check if source is operational (enabled and healthy)."""
        return self.config.enabled and self.health.is_healthy

    @property
    def status_summary(self) -> str:
        """Get a summary status string."""
        if not self.config.enabled:
            return "Disabled"
        elif self.health.is_healthy:
            return f"Healthy ({self.metrics.last_event_count} events)"
        elif self.health.has_errors:
            return f"Error: {self.health.error_message}"
        else:
            return "Unknown"

    def get_status_dict(self) -> Dict[str, Any]:
        """Get status information as dictionary."""
        return {
            "name": self.config.name,
            "type": self.config.type,
            "enabled": self.config.enabled,
            "status": self.health.status,
            "last_successful_fetch": self.metrics.last_successful_fetch,
            "success_rate": self.metrics.success_rate,
            "consecutive_failures": self.metrics.consecutive_failures,
            "last_event_count": self.metrics.last_event_count,
            "cached_events_count": self.cached_events_count,
            "error_message": self.health.error_message,
        }
