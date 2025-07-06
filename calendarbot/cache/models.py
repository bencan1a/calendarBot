"""Database models for caching calendar events."""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
import pytz


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
    
    class Config:
        # Allow datetime objects
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
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
        from ..utils.helpers import get_timezone_aware_now
        now = get_timezone_aware_now()
        return self.start_time <= now <= self.end_time
    
    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        from ..utils.helpers import get_timezone_aware_now
        now = get_timezone_aware_now()
        return self.start_time > now
    
    def format_time_range(self, format_str: str = "%I:%M %p") -> str:
        """Format the event time range as a string in Pacific Time (GMT-8/PDT)."""
        # Convert to Pacific timezone (handles PST/PDT automatically)
        pacific_tz = pytz.timezone('US/Pacific')
        
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
    
    class Config:
        # Allow field names with underscores for database columns
        allow_population_by_field_name = True
    
    @property
    def start_dt(self) -> datetime:
        """Get start datetime as datetime object."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"DEBUG: Parsing start_datetime: '{self.start_datetime}'")
            result = datetime.fromisoformat(self.start_datetime.replace('Z', '+00:00'))
            logger.info(f"DEBUG: Parsed to: {result}")
            return result
        except Exception as e:
            logger.error(f"DEBUG: Failed to parse start_datetime '{self.start_datetime}': {e}")
            raise
    
    @property
    def end_dt(self) -> datetime:
        """Get end datetime as datetime object."""
        return datetime.fromisoformat(self.end_datetime.replace('Z', '+00:00'))
    
    @property
    def cached_dt(self) -> datetime:
        """Get cached datetime as datetime object."""
        return datetime.fromisoformat(self.cached_at.replace('Z', '+00:00'))
    
    def is_current(self) -> bool:
        """Check if event is currently happening."""
        from ..utils.helpers import get_timezone_aware_now
        now = get_timezone_aware_now()
        return self.start_dt <= now <= self.end_dt
    
    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        from ..utils.helpers import get_timezone_aware_now
        now = get_timezone_aware_now()
        return self.start_dt > now
    
    def format_time_range(self, format_str: str = "%I:%M %p") -> str:
        """Format the event time range as a string in Pacific Time (GMT-8/PDT)."""
        # Convert to Pacific timezone (handles PST/PDT automatically)
        pacific_tz = pytz.timezone('US/Pacific')
        
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
        
        from ..utils.helpers import get_timezone_aware_now
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
            return datetime.fromisoformat(self.last_update.replace('Z', '+00:00'))
        return None
    
    @property
    def last_successful_fetch_dt(self) -> Optional[datetime]:
        """Get last successful fetch as datetime object."""
        if self.last_successful_fetch:
            return datetime.fromisoformat(self.last_successful_fetch.replace('Z', '+00:00'))
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