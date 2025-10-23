"""Shared data model for What's Next view that both web and e-Paper renderers can consume."""

# The EventData.from_cached_event factory is intentionally large/defensive to normalize
# many upstream event shapes. It contains many defensive branches to handle varied
# upstream event shapes; keeping it as-is avoids risky refactors during pre-commit.
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

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
    description: Optional[str] = None
    organizer: Optional[str] = None
    attendees: list[str] = field(default_factory=list)
    graph_id: Optional[str] = None  # Microsoft Graph ID for event hiding functionality

    @classmethod
    def from_cached_event(cls, event: CachedEvent, current_time: datetime) -> "EventData":  # noqa: PLR0912, PLR0915
        """Create EventData from CachedEvent with defensive normalization.

        This method is intentionally permissive about the source event's attribute
        names because different sources/caches may use alternate names for the
        same concept (e.g., 'title' vs 'subject', 'body_preview' vs 'description').

        Args:
            event: Source cached event
            current_time: Current time reference

        Returns:
            EventData instance
        """
        # Calculate time until start in minutes
        time_until = None
        try:
            if event.start_dt > current_time:
                time_until = int((event.start_dt - current_time).total_seconds() / 60)
        except Exception:
            time_until = None

        # Calculate duration in minutes (robust against malformed datetimes)
        try:
            duration = int((event.end_dt - event.start_dt).total_seconds() / 60)
        except Exception:
            duration = None

        # Determine if event is current or upcoming (safe calls)
        try:
            is_current = event.is_current()
        except Exception:
            is_current = False
        try:
            is_upcoming = event.is_upcoming()
        except Exception:
            is_upcoming = False

        # Filter out "Microsoft Teams Meeting" from location
        location = None
        try:
            loc_attr = getattr(event, "location_display_name", None)
            if loc_attr and "Microsoft Teams Meeting" not in str(loc_attr):
                location = str(loc_attr)
        except Exception:
            location = None

        # Handle potential format_time_range() errors
        try:
            formatted_time_range = event.format_time_range()
        except Exception as e:
            logger.warning(
                f"Failed to format time range for event '{getattr(event, 'subject', None)}': {e}"
            )
            formatted_time_range = ""

        # DEBUG: Check if CachedEvent has graph_id and what its value is
        graph_id = getattr(event, "graph_id", None)

        # Subject/title extraction - accept multiple attribute names
        subject = None
        # Collect candidate values for improved debug visibility
        candidate_values = {}
        for attr in ("subject", "title", "summary", "name"):
            try:
                val = getattr(event, attr, None)
                candidate_values[attr] = val
                if val:
                    subject = str(val)
                    break
            except Exception:
                candidate_values[attr] = None
                continue
        if not subject:
            # As a last resort, try to extract from body_preview first line
            try:
                bp = getattr(event, "body_preview", None) or getattr(event, "description", None)
                candidate_values["body_preview"] = bp
                if bp and isinstance(bp, str):
                    first_line = bp.strip().splitlines()[0]
                    subject = first_line if first_line else "Untitled Event"
                else:
                    subject = "Untitled Event"
            except Exception:
                subject = "Untitled Event"
        # DEBUG: Log resolved subject and candidate attribute values to aid diagnostics
        try:
            logger.debug(
                "EventData.from_cached_event - resolved subject=%r; candidates=%s",
                subject,
                {k: (v if v is not None else None) for k, v in candidate_values.items()},
            )
        except Exception:
            # Ensure we never raise from debug logging
            logger.debug(
                "EventData.from_cached_event - resolved subject (logging failed to serialize candidates)"
            )

        # Description extraction (support many possible attribute names)
        description = None
        for desc_attr in ("body_preview", "description", "body", "notes", "event_description"):
            try:
                desc_val = getattr(event, desc_attr, None)
                if desc_val:
                    # Convert non-string to string safely
                    if isinstance(desc_val, bytes):
                        description = desc_val.decode("utf-8", errors="replace")
                    else:
                        description = str(desc_val)
                    break
            except Exception:
                continue

        # Organizer extraction - be permissive with field names used across sources
        organizer = None
        for org_attr in ("organizer", "organizer_name", "organizer_email", "creator"):
            try:
                org_val = getattr(event, org_attr, None)
                if org_val:
                    organizer = str(org_val)
                    break
            except Exception:
                continue

        # Attendees extraction - normalize to list[str] where possible
        raw_attendees = None
        # Common attribute names to try
        for att_attr in (
            "attendees",
            "attendee_list",
            "attendee",
            "participants",
            "attendees_list",
        ):
            if raw_attendees:
                break
            try:
                raw_attendees = getattr(event, att_attr, None)
            except Exception:
                raw_attendees = None

        normalized_attendees: list[str] = []
        try:
            if raw_attendees:
                # If it's a single string, split by common separators
                if isinstance(raw_attendees, str):
                    parts = [
                        p.strip() for p in raw_attendees.replace(";", ",").split(",") if p.strip()
                    ]
                    normalized_attendees.extend(parts)
                else:
                    # Assume iterable (list of strings or objects)
                    for a in raw_attendees:
                        try:
                            if a is None:
                                continue
                            if isinstance(a, str):
                                normalized_attendees.append(a)
                                continue
                            if isinstance(a, dict):
                                name = a.get("name") or a.get("email") or str(a)
                                normalized_attendees.append(name)
                                continue
                            # Try common attributes
                            name = getattr(a, "name", None)
                            email = getattr(a, "email", None)
                            cn = getattr(a, "common_name", None)
                            if name:
                                normalized_attendees.append(str(name))
                            elif email:
                                normalized_attendees.append(str(email))
                            elif cn:
                                normalized_attendees.append(str(cn))
                            else:
                                normalized_attendees.append(str(a))
                        except Exception:
                            continue
        except Exception:
            normalized_attendees = []

        # Final construction using normalized and defensive values
        return cls(
            subject=subject,
            start_time=getattr(event, "start_dt", current_time),
            end_time=getattr(event, "end_dt", current_time),
            location=location,
            is_current=is_current,
            is_upcoming=is_upcoming,
            time_until_minutes=time_until,
            duration_minutes=duration,
            formatted_time_range=formatted_time_range,
            description=description,
            organizer=organizer,
            attendees=normalized_attendees,
            graph_id=graph_id,  # Microsoft Graph ID for event hiding
        )


@dataclass
class StatusInfo:
    """Status information for display."""

    last_update: datetime
    is_cached: bool = False
    connection_status: Optional[str] = None
    relative_description: Optional[str] = None
    selected_date: Optional[str] = None


@dataclass
class WeatherData:
    """Weather information for display."""

    temperature: Optional[float] = None
    condition: Optional[str] = None
    icon: Optional[str] = None
    forecast: Optional[list[dict[str, Any]]] = None


@dataclass
class SettingsData:
    """Settings panel data for display."""

    theme: str = "default"
    layout: str = "4x8"
    refresh_interval: int = 300
    display_type: str = "html"
    custom_settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class WhatsNextViewModel:
    """Comprehensive shared data model for What's Next view that both renderers can consume."""

    current_time: datetime
    display_date: str
    next_events: list[EventData] = field(default_factory=list)
    current_events: list[EventData] = field(default_factory=list)
    later_events: list[EventData] = field(default_factory=list)
    status_info: StatusInfo = field(default_factory=lambda: StatusInfo(last_update=datetime.now()))
    weather_info: Optional[WeatherData] = None
    settings_data: Optional[SettingsData] = None

    @classmethod
    def from_cached_events(
        cls,
        events: list[CachedEvent],
        current_time: Optional[datetime] = None,
        status_info: Optional[dict[str, Any]] = None,
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
            from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

            current_time = get_timezone_aware_now()

        # Convert status info
        status = StatusInfo(
            last_update=datetime.now(),
            is_cached=status_info.get("is_cached", False) if status_info else False,
            connection_status=status_info.get("connection_status") if status_info else None,
            relative_description=status_info.get("relative_description") if status_info else None,
            selected_date=status_info.get("selected_date") if status_info else None,
        )

        # Format display date
        display_date = status.selected_date or current_time.strftime("%A, %B %d")

        # Group and convert events
        current_event_data = []
        next_event_data = []
        later_event_data = []

        # Find current events
        current_events = [e for e in events if e.is_current()]
        # Show only one current event
        current_event_data = [
            EventData.from_cached_event(event, current_time) for event in current_events[:1]
        ]

        # Find upcoming events
        upcoming_events = [e for e in events if e.is_upcoming()]
        upcoming_events.sort(key=lambda e: e.start_dt)  # Sort by start time

        # Next up events (first 3)
        next_event_data = [
            EventData.from_cached_event(event, current_time) for event in upcoming_events[:3]
        ]

        # Later events (next 5 after the first 3)
        later_event_data = [
            EventData.from_cached_event(event, current_time) for event in upcoming_events[3:8]
        ]

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
