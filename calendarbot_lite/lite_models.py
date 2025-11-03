"""Data models for ICS calendar processing - CalendarBot Lite version."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

# Import the central datetime override function from timezone_utils
from .timezone_utils import now_utc as _now_utc


class LiteAuthType(str, Enum):
    """Supported authentication types for ICS sources."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"


class LiteICSAuth(BaseModel):
    """Authentication configuration for ICS sources."""

    type: LiteAuthType = LiteAuthType.NONE
    username: Optional[str] = None
    password: Optional[str] = None
    bearer_token: Optional[str] = None

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for authentication."""
        headers = {}

        if self.type == LiteAuthType.BASIC and self.username and self.password:
            import base64

            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif self.type == LiteAuthType.BEARER and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        return headers


class LiteICSSource(BaseModel):
    """Configuration for an ICS calendar source."""

    name: str = Field(..., description="Human-readable name for this calendar source")
    url: str = Field(..., description="ICS calendar URL")
    auth: LiteICSAuth = Field(
        default_factory=LiteICSAuth, description="Authentication configuration"
    )

    # Refresh settings
    refresh_interval: int = Field(default=300, description="Refresh interval in seconds")
    timeout: int = Field(default=30, description="HTTP timeout in seconds")

    # Optional headers
    custom_headers: dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")

    # Validation settings
    validate_ssl: bool = Field(default=True, description="Validate SSL certificates")

    model_config = ConfigDict(use_enum_values=True)


class LiteICSResponse(BaseModel):
    """Response from ICS fetch operation.

    Notes:
        - New fields `stream_handle` and `stream_mode` support streaming responses.
        - Backwards compatibility is preserved: consumers may continue to use
          `content` for buffered responses. Use `get_content_or_stream()` to
          obtain the available variant in a defensive way.
    """

    success: bool
    content: Optional[str] = None
    status_code: Optional[int] = None
    headers: dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    fetch_time: datetime = Field(default_factory=_now_utc)

    # HTTP caching support
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    cache_control: Optional[str] = None

    # Streaming support (new)
    stream_handle: Optional[object] = None
    stream_mode: Optional[str] = None  # e.g. "bytes" (future: "lines", etc.)

    @property
    def is_not_modified(self) -> bool:
        """Check if response indicates content not modified (304)."""
        return self.status_code == 304

    @property
    def content_length(self) -> Optional[int]:
        """Get content length if available for buffered responses or from headers."""
        if self.content:
            return len(self.content.encode("utf-8"))
        # Fall back to headers if available
        if self.headers:
            cl = None
            for k, v in self.headers.items():
                if k.lower() == "content-length":
                    cl = v
                    break
            if cl is not None:
                try:
                    return int(cl)
                except Exception:
                    return None
        return None

    def get_content_or_stream(self) -> tuple[Optional[str], Optional[object]]:
        """Utility to obtain either buffered content or a stream handle.

        Returns:
            (content, stream_handle)
            - For buffered responses, `content` will be populated and `stream_handle` will be None.
            - For streaming responses, `content` will be None and `stream_handle` will be populated.
        """
        return self.content, self.stream_handle


class LiteICSParseResult(BaseModel):
    """Result of ICS parsing operation."""

    success: bool
    events: list[Any] = Field(default_factory=list, description="Parsed calendar events")
    raw_content: Optional[str] = Field(default=None, description="Raw ICS content for storage")
    source_url: Optional[str] = Field(default=None, description="Source URL for tracking")
    calendar_name: Optional[str] = None
    calendar_description: Optional[str] = None
    timezone: Optional[str] = None

    # Parse statistics
    total_components: int = 0
    event_count: int = 0
    recurring_event_count: int = 0

    # Error information
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)

    # Parsing metadata
    parse_time: datetime = Field(default_factory=_now_utc)
    ics_version: Optional[str] = None
    prodid: Optional[str] = None

    # Individual event raw content mapping (event_id -> raw_ics_content)
    event_raw_content_map: dict[str, str] = Field(
        default_factory=dict, description="Mapping of event IDs to individual raw ICS content"
    )


class LiteICSValidationResult(BaseModel):
    """Result of ICS source validation."""

    source_accessible: bool = False
    auth_valid: bool = False
    content_valid: bool = False
    parse_successful: bool = False

    # Detailed results
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    content_size: Optional[int] = None

    # Timing information
    response_time_ms: Optional[float] = None

    # Error details
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Sample events (for validation)
    sample_events: list[str] = Field(default_factory=list, description="Sample event titles")

    @property
    def is_valid(self) -> bool:
        """Check if validation passed all checks."""
        return (
            self.source_accessible
            and self.auth_valid
            and self.content_valid
            and self.parse_successful
        )

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


# Calendar Event Models (ICS-native equivalents to Azure API models)


class LiteEventStatus(str, Enum):
    """Event status/show-as values."""

    FREE = "free"
    TENTATIVE = "tentative"
    BUSY = "busy"
    OUT_OF_OFFICE = "oof"
    WORKING_ELSEWHERE = "workingElsewhere"


class LiteAttendeeType(str, Enum):
    """Attendee type enum."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    RESOURCE = "resource"


class LiteResponseStatus(str, Enum):
    """Response status enum."""

    NONE = "none"
    ORGANIZER = "organizer"
    TENTATIVELY_ACCEPTED = "tentativelyAccepted"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    NOT_RESPONDED = "notResponded"


class LiteDateTimeInfo(BaseModel):
    """Date and time information for calendar events."""

    date_time: datetime = Field(..., description="The date and time")
    time_zone: str = Field(default="UTC", description="Time zone")

    @field_serializer("date_time")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()


class LiteLocation(BaseModel):
    """Location information for calendar events."""

    display_name: str = Field(..., description="Display name of the location")
    address: Optional[str] = Field(default=None, description="Physical address")
    coordinates: Optional[dict[str, float]] = Field(default=None, description="GPS coordinates")


class LiteAttendee(BaseModel):
    """Calendar event attendee."""

    name: str = Field(..., description="Attendee name")
    email: str = Field(..., description="Attendee email address")
    type: LiteAttendeeType = Field(default=LiteAttendeeType.REQUIRED, description="Attendee type")
    response_status: LiteResponseStatus = Field(
        default=LiteResponseStatus.NOT_RESPONDED, description="Response status"
    )


class LiteCalendarEvent(BaseModel):
    """Calendar event model for ICS-based events."""

    # Core properties
    id: str = Field(..., description="Event ID")
    subject: str = Field(..., description="Event subject/title")
    body_preview: Optional[str] = Field(default=None, description="Event body preview")

    # Time information
    start: LiteDateTimeInfo = Field(..., description="Event start time")
    end: LiteDateTimeInfo = Field(..., description="Event end time")
    is_all_day: bool = Field(default=False, description="All-day event flag")

    # Status and visibility
    show_as: LiteEventStatus = Field(default=LiteEventStatus.BUSY, description="Show-as status")
    is_cancelled: bool = Field(default=False, description="Cancellation status")

    # Organizer and attendees
    is_organizer: bool = Field(default=False, description="Is current user the organizer")
    location: Optional[LiteLocation] = Field(default=None, description="Event location")
    attendees: Optional[list[LiteAttendee]] = Field(default=None, description="Event attendees")

    # Recurrence
    is_recurring: bool = Field(default=False, description="Recurring event flag")
    recurrence_id: Optional[str] = Field(
        default=None, description="RECURRENCE-ID for recurrence instances"
    )

    # RRULE expansion tracking
    is_expanded_instance: bool = Field(
        default=False, description="True if generated from RRULE expansion"
    )
    rrule_master_uid: Optional[str] = Field(
        default=None, description="UID of master recurring event for expanded instances"
    )

    # Metadata
    created_date_time: Optional[datetime] = Field(default=None, description="Creation time")
    last_modified_date_time: Optional[datetime] = Field(
        default=None, description="Last modification time"
    )

    # Online meeting
    is_online_meeting: bool = Field(default=False, description="Online meeting flag")
    online_meeting_url: Optional[str] = Field(default=None, description="Online meeting URL")

    @property
    def is_busy_status(self) -> bool:
        """Check if event has busy status (not free)."""
        return self.show_as in [
            LiteEventStatus.BUSY,
            LiteEventStatus.TENTATIVE,
            LiteEventStatus.OUT_OF_OFFICE,
            LiteEventStatus.WORKING_ELSEWHERE,
        ]

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("created_date_time", "last_modified_date_time", when_used="unless-none")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return dt.isoformat()
