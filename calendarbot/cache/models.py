"""Database models for caching calendar events."""

import hashlib
from datetime import datetime, timedelta
from typing import Optional

import pytz
from pydantic import BaseModel, field_serializer

from ..utils.helpers import get_timezone_aware_now


class CalendarEvent(BaseModel):
    """Common calendar event model used across the system."""

    # Event identification
    id: str
    title: str
    description: Optional[str] = None

    # Time information
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    is_all_day: bool = False

    # Status and visibility
    status: str = "busy"  # busy, free, tentative, out_of_office
    is_cancelled: bool = False
    is_private: bool = False

    # Location
    location: Optional[str] = None
    location_address: Optional[str] = None

    # Meeting details
    is_online_meeting: bool = False
    online_meeting_url: Optional[str] = None
    web_link: Optional[str] = None

    # Organizer and attendees
    organizer_name: Optional[str] = None
    organizer_email: Optional[str] = None
    is_organizer: bool = False

    # Recurrence
    is_recurring: bool = False
    series_master_id: Optional[str] = None

    # Source metadata
    source_name: Optional[str] = None
    last_modified: Optional[datetime] = None

    @field_serializer("start_time", "end_time", "last_modified")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return dt.isoformat() if dt is not None else None

    @property
    def duration_minutes(self) -> int:
        """Get event duration in minutes."""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def is_busy_status(self) -> bool:
        """Check if event has a busy status."""
        return self.status.lower() in ["busy", "tentative", "out_of_office"]

    def is_current(self) -> bool:
        """Check if event is currently happening."""
        now = get_timezone_aware_now()
        return self.start_time <= now <= self.end_time

    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        now = get_timezone_aware_now()
        return self.start_time > now

    def format_time_range(self, format_str: str = "%I:%M %p") -> str:
        """Format the event time range as a string in Pacific Time (GMT-8/PDT)."""
        # Convert to Pacific timezone (handles PST/PDT automatically)
        pacific_tz = pytz.timezone("US/Pacific")

        # Ensure datetime objects are timezone-aware
        if self.start_time.tzinfo is None:
            start_utc = pytz.utc.localize(self.start_time)
        else:
            start_utc = self.start_time.astimezone(pytz.utc)

        if self.end_time.tzinfo is None:
            end_utc = pytz.utc.localize(self.end_time)
        else:
            end_utc = self.end_time.astimezone(pytz.utc)

        # Convert to Pacific time
        start_pacific = start_utc.astimezone(pacific_tz)
        end_pacific = end_utc.astimezone(pacific_tz)

        start_str = start_pacific.strftime(format_str)
        end_str = end_pacific.strftime(format_str)
        return f"{start_str} - {end_str}"


class CachedEvent(BaseModel):
    """Cached calendar event model for local storage."""

    # Primary key and Graph API reference
    id: str
    graph_id: str  # Original ID from Microsoft Graph

    # Event details
    subject: str
    body_preview: Optional[str] = None

    # Time information (stored as ISO strings for SQLite compatibility)
    start_datetime: str
    end_datetime: str
    start_timezone: str
    end_timezone: str
    is_all_day: bool = False

    # Status and visibility
    show_as: str = "busy"
    is_cancelled: bool = False
    is_organizer: bool = False

    # Location
    location_display_name: Optional[str] = None
    location_address: Optional[str] = None

    # Meeting details
    is_online_meeting: bool = False
    online_meeting_url: Optional[str] = None
    web_link: Optional[str] = None

    # Recurrence
    is_recurring: bool = False
    series_master_id: Optional[str] = None

    # Cache metadata
    cached_at: str  # When this was cached (ISO string)
    last_modified: Optional[str] = None  # Last modified from Graph API

    model_config = {"populate_by_name": True}

    @property
    def start_dt(self) -> datetime:
        """Get start datetime as datetime object."""
        return datetime.fromisoformat(self.start_datetime.replace("Z", "+00:00"))

    @property
    def end_dt(self) -> datetime:
        """Get end datetime as datetime object."""
        return datetime.fromisoformat(self.end_datetime.replace("Z", "+00:00"))

    @property
    def cached_dt(self) -> datetime:
        """Get cached datetime as datetime object."""
        return datetime.fromisoformat(self.cached_at.replace("Z", "+00:00"))

    def is_current(self) -> bool:
        """Check if event is currently happening."""
        now = get_timezone_aware_now()
        return self.start_dt <= now <= self.end_dt

    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        now = get_timezone_aware_now()
        return self.start_dt > now

    def format_time_range(self, format_str: str = "%I:%M %p") -> str:
        """Format the event time range as a string in Pacific Time (GMT-8/PDT)."""
        # Convert to Pacific timezone (handles PST/PDT automatically)
        pacific_tz = pytz.timezone("US/Pacific")

        # Ensure datetime objects are timezone-aware
        if self.start_dt.tzinfo is None:
            start_utc = pytz.utc.localize(self.start_dt)
        else:
            start_utc = self.start_dt.astimezone(pytz.utc)

        if self.end_dt.tzinfo is None:
            end_utc = pytz.utc.localize(self.end_dt)
        else:
            end_utc = self.end_dt.astimezone(pytz.utc)

        # Convert to Pacific time
        start_pacific = start_utc.astimezone(pacific_tz)
        end_pacific = end_utc.astimezone(pacific_tz)

        start_str = start_pacific.strftime(format_str)
        end_str = end_pacific.strftime(format_str)
        return f"{start_str} - {end_str}"

    def time_until_start(self) -> Optional[int]:
        """Get minutes until event starts.

        Returns:
            Minutes until event starts, or None if event has already started
        """
        if not self.is_upcoming():
            return None

        now = get_timezone_aware_now()
        delta = self.start_dt - now
        minutes = int(delta.total_seconds() / 60)
        return max(0, minutes)


class CacheMetadata(BaseModel):
    """Metadata about the cache state."""

    # Cache statistics
    total_events: int = 0
    last_update: Optional[str] = None
    last_successful_fetch: Optional[str] = None

    # Cache health
    is_stale: bool = False
    cache_ttl_seconds: int = 3600  # 1 hour default

    # Error tracking
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None

    @property
    def last_update_dt(self) -> Optional[datetime]:
        """Get last update as datetime object."""
        if self.last_update:
            return datetime.fromisoformat(self.last_update.replace("Z", "+00:00"))
        return None

    @property
    def last_successful_fetch_dt(self) -> Optional[datetime]:
        """Get last successful fetch as datetime object."""
        if self.last_successful_fetch:
            return datetime.fromisoformat(self.last_successful_fetch.replace("Z", "+00:00"))
        return None

    def is_cache_expired(self) -> bool:
        """Check if cache has expired based on TTL."""
        if not self.last_successful_fetch_dt:
            return True

        now = datetime.now()
        expiry_time = self.last_successful_fetch_dt + timedelta(seconds=self.cache_ttl_seconds)
        return now > expiry_time

    def time_since_last_update(self) -> Optional[int]:
        """Get minutes since last update."""
        if not self.last_update_dt:
            return None

        now = datetime.now()
        delta = now - self.last_update_dt
        return int(delta.total_seconds() / 60)


class RawEvent(BaseModel):
    """Raw ICS event model for storage alongside cached events.

    Contains same parsed event data as CachedEvent plus raw ICS content.
    """

    # Primary identification
    id: str  # Unique identifier
    graph_id: str  # Links to CachedEvent.graph_id

    # Event details (same as CachedEvent)
    subject: str
    body_preview: Optional[str] = None

    # Time information (stored as ISO strings for SQLite compatibility)
    start_datetime: str
    end_datetime: str
    start_timezone: str
    end_timezone: str
    is_all_day: bool = False

    # Status and visibility
    show_as: str = "busy"
    is_cancelled: bool = False
    is_organizer: bool = False

    # Location
    location_display_name: Optional[str] = None
    location_address: Optional[str] = None

    # Meeting details
    is_online_meeting: bool = False
    online_meeting_url: Optional[str] = None
    web_link: Optional[str] = None

    # Recurrence
    is_recurring: bool = False
    series_master_id: Optional[str] = None
    recurrence_id: Optional[str] = None  # RECURRENCE-ID value for instances
    is_instance: bool = False  # True if this is a recurrence instance, False if master pattern

    # Cache metadata
    last_modified: Optional[str] = None  # Last modified from Graph API

    # Source information
    source_url: Optional[str] = None  # ICS feed URL if available

    # Raw content
    raw_ics_content: str  # Complete raw ICS text
    content_hash: str  # SHA-256 for deduplication
    content_size_bytes: int  # Content size for monitoring

    # Timestamps
    cached_at: str  # When stored (ISO string)

    model_config = {"populate_by_name": True}

    @property
    def cached_dt(self) -> datetime:
        """Get cached datetime as datetime object."""
        return datetime.fromisoformat(self.cached_at.replace("Z", "+00:00"))

    @classmethod
    def create_from_cached_event(
        cls, cached_event: "CachedEvent", ics_content: str, source_url: Optional[str] = None
    ) -> "RawEvent":
        """Create RawEvent instance from CachedEvent and ICS content.

        Args:
            cached_event: CachedEvent to copy parsed data from
            ics_content: Raw ICS content to store
            source_url: Optional source URL for the ICS content

        Returns:
            New RawEvent instance with parsed data and raw content
        """
        content_hash = hashlib.sha256(ics_content.encode("utf-8")).hexdigest()

        # For debugging purposes, make each raw event ID unique to preserve duplicates
        import uuid  # noqa: PLC0415

        unique_suffix = str(uuid.uuid4())[:8]  # Short UUID for readability

        return cls(
            id=f"raw_{cached_event.graph_id}_{unique_suffix}",
            graph_id=cached_event.graph_id,
            subject=cached_event.subject,
            body_preview=cached_event.body_preview,
            start_datetime=cached_event.start_datetime,
            end_datetime=cached_event.end_datetime,
            start_timezone=cached_event.start_timezone,
            end_timezone=cached_event.end_timezone,
            is_all_day=cached_event.is_all_day,
            show_as=cached_event.show_as,
            is_cancelled=cached_event.is_cancelled,
            is_organizer=cached_event.is_organizer,
            location_display_name=cached_event.location_display_name,
            location_address=cached_event.location_address,
            is_online_meeting=cached_event.is_online_meeting,
            online_meeting_url=cached_event.online_meeting_url,
            web_link=cached_event.web_link,
            is_recurring=cached_event.is_recurring,
            series_master_id=cached_event.series_master_id,
            recurrence_id=None,  # Will be set by caller if this is an instance
            is_instance=False,  # Will be set by caller if this is an instance
            last_modified=cached_event.last_modified,
            source_url=source_url,
            raw_ics_content=ics_content,
            content_hash=content_hash,
            content_size_bytes=len(ics_content.encode("utf-8")),
            cached_at=datetime.now().isoformat(),
        )

    @classmethod
    def create_from_ics(
        cls,
        graph_id: str,
        subject: str,
        start_datetime: str,
        end_datetime: str,
        start_timezone: str,
        end_timezone: str,
        ics_content: str,
        source_url: Optional[str] = None,
        **kwargs,
    ) -> "RawEvent":
        """Create RawEvent instance from ICS content and minimal parsed data.

        Args:
            graph_id: Graph ID to link to cached event
            subject: Event subject/title
            start_datetime: Start datetime as ISO string
            end_datetime: End datetime as ISO string
            start_timezone: Start timezone
            end_timezone: End timezone
            ics_content: Raw ICS content to store
            source_url: Optional source URL for the ICS content
            **kwargs: Additional optional fields

        Returns:
            New RawEvent instance with computed hash and metadata
        """
        content_hash = hashlib.sha256(ics_content.encode("utf-8")).hexdigest()

        # For debugging purposes, make each raw event ID unique to preserve duplicates
        # Include microseconds to ensure uniqueness even for rapid insertions
        import uuid  # noqa: PLC0415

        unique_suffix = str(uuid.uuid4())[:8]  # Short UUID for readability

        # Set default values for new fields, allow override via kwargs
        recurrence_id = kwargs.pop("recurrence_id", None)
        is_instance = kwargs.pop("is_instance", False)

        return cls(
            id=f"raw_{graph_id}_{unique_suffix}",
            graph_id=graph_id,
            subject=subject,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            start_timezone=start_timezone,
            end_timezone=end_timezone,
            recurrence_id=recurrence_id,
            is_instance=is_instance,
            source_url=source_url,
            raw_ics_content=ics_content,
            content_hash=content_hash,
            content_size_bytes=len(ics_content.encode("utf-8")),
            cached_at=datetime.now().isoformat(),
            **kwargs,
        )
