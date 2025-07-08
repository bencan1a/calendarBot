"""Data models for ICS calendar processing."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class AuthType(str, Enum):
    """Supported authentication types for ICS sources."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"


class ICSAuth(BaseModel):
    """Authentication configuration for ICS sources."""

    type: AuthType = AuthType.NONE
    username: Optional[str] = None
    password: Optional[str] = None
    bearer_token: Optional[str] = None

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for authentication."""
        headers = {}

        if self.type == AuthType.BASIC and self.username and self.password:
            import base64

            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif self.type == AuthType.BEARER and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        return headers


class ICSSource(BaseModel):
    """Configuration for an ICS calendar source."""

    name: str = Field(..., description="Human-readable name for this calendar source")
    url: str = Field(..., description="ICS calendar URL")
    auth: ICSAuth = Field(default_factory=ICSAuth, description="Authentication configuration")

    # Refresh settings
    refresh_interval: int = Field(default=300, description="Refresh interval in seconds")
    timeout: int = Field(default=30, description="HTTP timeout in seconds")

    # Optional headers
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")

    # Validation settings
    validate_ssl: bool = Field(default=True, description="Validate SSL certificates")

    model_config = ConfigDict(use_enum_values=True)


class ICSResponse(BaseModel):
    """Response from ICS fetch operation."""

    success: bool
    content: Optional[str] = None
    status_code: Optional[int] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    fetch_time: datetime = Field(default_factory=datetime.now)

    # HTTP caching support
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    cache_control: Optional[str] = None

    @property
    def is_not_modified(self) -> bool:
        """Check if response indicates content not modified (304)."""
        return self.status_code == 304

    @property
    def content_length(self) -> Optional[int]:
        """Get content length if available."""
        if self.content:
            return len(self.content.encode("utf-8"))
        return None


class ICSParseResult(BaseModel):
    """Result of ICS parsing operation."""

    success: bool
    events: List[Any] = Field(default_factory=list, description="Parsed calendar events")
    calendar_name: Optional[str] = None
    calendar_description: Optional[str] = None
    timezone: Optional[str] = None

    # Parse statistics
    total_components: int = 0
    event_count: int = 0
    recurring_event_count: int = 0

    # Error information
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    # Parsing metadata
    parse_time: datetime = Field(default_factory=datetime.now)
    ics_version: Optional[str] = None
    prodid: Optional[str] = None


class ICSValidationResult(BaseModel):
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
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Sample events (for validation)
    sample_events: List[str] = Field(default_factory=list, description="Sample event titles")

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


class EventStatus(str, Enum):
    """Event status/show-as values."""

    FREE = "free"
    TENTATIVE = "tentative"
    BUSY = "busy"
    OUT_OF_OFFICE = "oof"
    WORKING_ELSEWHERE = "workingElsewhere"


class AttendeeType(str, Enum):
    """Attendee type enum."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    RESOURCE = "resource"


class ResponseStatus(str, Enum):
    """Response status enum."""

    NONE = "none"
    ORGANIZER = "organizer"
    TENTATIVELY_ACCEPTED = "tentativelyAccepted"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    NOT_RESPONDED = "notResponded"


class DateTimeInfo(BaseModel):
    """Date and time information for calendar events."""

    date_time: datetime = Field(..., description="The date and time")
    time_zone: str = Field(default="UTC", description="Time zone")

    @field_serializer("date_time")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()


class Location(BaseModel):
    """Location information for calendar events."""

    display_name: str = Field(..., description="Display name of the location")
    address: Optional[str] = Field(default=None, description="Physical address")
    coordinates: Optional[Dict[str, float]] = Field(default=None, description="GPS coordinates")


class Attendee(BaseModel):
    """Calendar event attendee."""

    name: str = Field(..., description="Attendee name")
    email: str = Field(..., description="Attendee email address")
    type: AttendeeType = Field(default=AttendeeType.REQUIRED, description="Attendee type")
    response_status: ResponseStatus = Field(
        default=ResponseStatus.NOT_RESPONDED, description="Response status"
    )


class CalendarEvent(BaseModel):
    """Calendar event model for ICS-based events."""

    # Core properties
    id: str = Field(..., description="Event ID")
    subject: str = Field(..., description="Event subject/title")
    body_preview: Optional[str] = Field(default=None, description="Event body preview")

    # Time information
    start: DateTimeInfo = Field(..., description="Event start time")
    end: DateTimeInfo = Field(..., description="Event end time")
    is_all_day: bool = Field(default=False, description="All-day event flag")

    # Status and visibility
    show_as: EventStatus = Field(default=EventStatus.BUSY, description="Show-as status")
    is_cancelled: bool = Field(default=False, description="Cancellation status")

    # Organizer and attendees
    is_organizer: bool = Field(default=False, description="Is current user the organizer")
    location: Optional[Location] = Field(default=None, description="Event location")
    attendees: Optional[List[Attendee]] = Field(default=None, description="Event attendees")

    # Recurrence
    is_recurring: bool = Field(default=False, description="Recurring event flag")

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
            EventStatus.BUSY,
            EventStatus.TENTATIVE,
            EventStatus.OUT_OF_OFFICE,
            EventStatus.WORKING_ELSEWHERE,
        ]

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("created_date_time", "last_modified_date_time", when_used="unless-none")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return dt.isoformat()
