"""Shared data model for What's Next view that both web and e-Paper renderers can consume."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..cache.models import CachedEvent

logger = logging.getLogger(__name__)


@dataclass
class EventData:
    """Standardized event data structure for rendering."""

    subject: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_current: bool = False
    is_upcoming: bool = False
    time_until_minutes: Optional[int] = None
    duration_minutes: Optional[int] = None
    formatted_time_range: str = ""
    organizer: Optional[str] = None
    attendees: List[str] = field(default_factory=list)

    @classmethod
    def from_cached_event(cls, event: CachedEvent, current_time: datetime) -> "EventData":
        """Create EventData from CachedEvent.

        Args:
            event: Source cached event
            current_time: Current time reference

        Returns:
            EventData instance
        """
        # Calculate time until start in minutes
        time_until = None
        if event.start_dt > current_time:
            time_until = int((event.start_dt - current_time).total_seconds() / 60)

        # Calculate duration in minutes
        duration = int((event.end_dt - event.start_dt).total_seconds() / 60)

        # Determine if event is current or upcoming
        is_current = event.is_current()
        is_upcoming = event.is_upcoming()

        # Filter out "Microsoft Teams Meeting" from location
        location = None
        if (
            event.location_display_name
            and "Microsoft Teams Meeting" not in event.location_display_name
        ):
            location = event.location_display_name

        # Handle potential format_time_range() errors
        try:
            formatted_time_range = event.format_time_range()
        except Exception as e:
            logger.warning(f"Failed to format time range for event '{event.subject}': {e}")
            formatted_time_range = ""

        return cls(
            subject=event.subject,
            start_time=event.start_dt,
            end_time=event.end_dt,
            location=location,
            is_current=is_current,
            is_upcoming=is_upcoming,
            time_until_minutes=time_until,
            duration_minutes=duration,
            formatted_time_range=formatted_time_range,
            organizer=getattr(event, "organizer", None),
            attendees=getattr(event, "attendees", []),
        )


@dataclass
class StatusInfo:
    """Status information for display."""

    last_update: datetime
    is_cached: bool = False
    connection_status: Optional[str] = None
    relative_description: Optional[str] = None
    interactive_mode: bool = False
    selected_date: Optional[str] = None


@dataclass
class WeatherData:
    """Weather information for display."""

    temperature: Optional[float] = None
    condition: Optional[str] = None
    icon: Optional[str] = None
    forecast: Optional[List[Dict[str, Any]]] = None


@dataclass
class SettingsData:
    """Settings panel data for display."""

    theme: str = "default"
    layout: str = "4x8"
    refresh_interval: int = 300
    display_type: str = "html"
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WhatsNextViewModel:
    """Comprehensive shared data model for What's Next view that both renderers can consume."""

    current_time: datetime
    display_date: str
    next_events: List[EventData] = field(default_factory=list)
    current_events: List[EventData] = field(default_factory=list)
    later_events: List[EventData] = field(default_factory=list)
    status_info: StatusInfo = field(default_factory=lambda: StatusInfo(last_update=datetime.now()))
    weather_info: Optional[WeatherData] = None
    settings_data: Optional[SettingsData] = None

    @classmethod
    def from_cached_events(
        cls,
        events: List[CachedEvent],
        current_time: Optional[datetime] = None,
        status_info: Optional[Dict[str, Any]] = None,
    ) -> "WhatsNextViewModel":
        """Create WhatsNextViewModel from a list of cached events.

        Args:
            events: List of cached events
            current_time: Current time reference (uses now if None)
            status_info: Additional status information

        Returns:
            WhatsNextViewModel instance
        """
        if current_time is None:
            from ..utils.helpers import get_timezone_aware_now

            current_time = get_timezone_aware_now()

        # Convert status info
        status = StatusInfo(
            last_update=datetime.now(),
            is_cached=status_info.get("is_cached", False) if status_info else False,
            connection_status=status_info.get("connection_status") if status_info else None,
            relative_description=status_info.get("relative_description") if status_info else None,
            interactive_mode=status_info.get("interactive_mode", False) if status_info else False,
            selected_date=status_info.get("selected_date") if status_info else None,
        )

        # Format display date
        if status.selected_date:
            display_date = status.selected_date
        else:
            display_date = current_time.strftime("%A, %B %d")

        # Group and convert events
        current_event_data = []
        next_event_data = []
        later_event_data = []

        # Find current events
        current_events = [e for e in events if e.is_current()]
        for event in current_events[:1]:  # Show only one current event
            current_event_data.append(EventData.from_cached_event(event, current_time))

        # Find upcoming events
        upcoming_events = [e for e in events if e.is_upcoming()]
        upcoming_events.sort(key=lambda e: e.start_dt)  # Sort by start time

        # Next up events (first 3)
        for event in upcoming_events[:3]:
            next_event_data.append(EventData.from_cached_event(event, current_time))

        # Later events (next 5 after the first 3)
        for event in upcoming_events[3:8]:
            later_event_data.append(EventData.from_cached_event(event, current_time))

        return cls(
            current_time=current_time,
            display_date=display_date,
            next_events=next_event_data,
            current_events=current_event_data,
            later_events=later_event_data,
            status_info=status,
        )

    def has_events(self) -> bool:
        """Check if there are any events to display.

        Returns:
            True if there are any events, False otherwise
        """
        return bool(self.next_events or self.current_events or self.later_events)

    def get_next_event(self) -> Optional[EventData]:
        """Get the next upcoming event if available.

        Returns:
            Next event or None if no upcoming events
        """
        return self.next_events[0] if self.next_events else None

    def get_current_event(self) -> Optional[EventData]:
        """Get the current event if available.

        Returns:
            Current event or None if no current event
        """
        return self.current_events[0] if self.current_events else None

    def get_time_until_next_event(self) -> Optional[int]:
        """Get time until next event in minutes.

        Returns:
            Minutes until next event or None if no upcoming events
        """
        next_event = self.get_next_event()
        return next_event.time_until_minutes if next_event else None

    def get_time_remaining_current_event(self) -> Optional[int]:
        """Get time remaining for current event in minutes.

        Returns:
            Minutes remaining for current event or None if no current event
        """
        current_event = self.get_current_event()
        if not current_event:
            return None

        remaining = int((current_event.end_time - self.current_time).total_seconds() / 60)
        return max(0, remaining)
