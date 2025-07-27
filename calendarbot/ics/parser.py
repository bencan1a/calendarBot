"""iCalendar parser with Microsoft Outlook compatibility."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, cast

from dateutil import tz
from dateutil.rrule import rrule, rrulestr
from icalendar import Calendar
from icalendar import Event as ICalEvent
from icalendar.cal import Component

from ..security.logging import SecurityEventLogger
from .exceptions import ICSContentError, ICSParseError
from .models import (
    Attendee,
    AttendeeType,
    CalendarEvent,
    DateTimeInfo,
    EventStatus,
    ICSParseResult,
    Location,
    ResponseStatus,
)

logger = logging.getLogger(__name__)


class ICSParser:
    """iCalendar parser with Microsoft Outlook compatibility."""

    def __init__(self, settings: Any) -> None:
        """Initialize ICS parser.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.security_logger = SecurityEventLogger()
        logger.debug("ICS parser initialized")

    def parse_ics_content(self, ics_content: str) -> ICSParseResult:
        """Parse ICS content into structured calendar events.

        Args:
            ics_content: Raw ICS file content

        Returns:
            Parse result with events and metadata
        """
        try:
            logger.debug("Starting ICS content parsing")

            # Parse the calendar
            calendar = Calendar.from_ical(ics_content)

            # Extract calendar metadata
            calendar_name = self._get_calendar_property(cast(Calendar, calendar), "X-WR-CALNAME")
            calendar_description = self._get_calendar_property(
                cast(Calendar, calendar), "X-WR-CALDESC"
            )
            timezone_str = self._get_calendar_property(cast(Calendar, calendar), "X-WR-TIMEZONE")
            prodid = self._get_calendar_property(cast(Calendar, calendar), "PRODID")
            version = self._get_calendar_property(cast(Calendar, calendar), "VERSION")

            # Parse events
            events = []
            total_components = 0
            event_count = 0
            recurring_event_count = 0
            warnings = []

            for component in calendar.walk():
                total_components += 1

                if component.name == "VEVENT":
                    try:
                        event = self._parse_event_component(
                            cast(ICalEvent, component), timezone_str
                        )
                        if event:
                            events.append(event)
                            event_count += 1

                            if event.is_recurring:
                                recurring_event_count += 1

                    except Exception as e:
                        warning = f"Failed to parse event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

            # Filter to only busy/tentative events (same as Graph API behavior)
            filtered_events = [e for e in events if e.is_busy_status and not e.is_cancelled]

            logger.debug(
                f"Parsed {len(filtered_events)} events from ICS content "
                f"({event_count} total events, {len(filtered_events)} busy/tentative)"
            )

            return ICSParseResult(
                success=True,
                events=filtered_events,
                calendar_name=calendar_name,
                calendar_description=calendar_description,
                timezone=timezone_str,
                total_components=total_components,
                event_count=event_count,
                recurring_event_count=recurring_event_count,
                warnings=warnings,
                ics_version=version,
                prodid=prodid,
            )

        except Exception as e:
            logger.error(f"Failed to parse ICS content: {e}")
            return ICSParseResult(success=False, error_message=str(e))

    def _parse_event_component(
        self, component: ICalEvent, default_timezone: Optional[str] = None
    ) -> Optional[CalendarEvent]:
        """Parse a single VEVENT component into CalendarEvent.

        Args:
            component: iCalendar VEVENT component
            default_timezone: Default timezone for the calendar

        Returns:
            Parsed CalendarEvent or None if parsing fails
        """
        try:
            # Required properties
            uid = str(component.get("UID", str(uuid.uuid4())))
            summary = str(component.get("SUMMARY", "No Title"))

            # Time information
            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")

            if not dtstart:
                logger.warning(f"Event {uid} missing DTSTART, skipping")
                return None

            # Parse start time
            start_dt = self._parse_datetime(dtstart, default_timezone)
            start_info = DateTimeInfo(
                date_time=start_dt, time_zone=str(start_dt.tzinfo) if start_dt.tzinfo else "UTC"
            )

            # Parse end time
            if dtend:
                end_dt = self._parse_datetime(dtend, default_timezone)
            else:
                # Use duration if available, otherwise default to 1 hour
                duration = component.get("DURATION")
                if duration:
                    end_dt = start_dt + duration.dt
                else:
                    end_dt = start_dt + timedelta(hours=1)

            end_info = DateTimeInfo(
                date_time=end_dt, time_zone=str(end_dt.tzinfo) if end_dt.tzinfo else "UTC"
            )

            # Event status and visibility
            status = self._parse_status(component.get("STATUS"))
            transp = component.get("TRANSP", "OPAQUE")
            show_as = self._map_transparency_to_status(transp, status)

            # All-day events
            is_all_day = not hasattr(dtstart.dt, "hour")

            # Description
            description = component.get("DESCRIPTION")
            body_preview = None
            if description:
                body_preview = str(description)[:200]  # Truncate for preview

            # Location
            location = None
            location_str = component.get("LOCATION")
            if location_str:
                location = Location(display_name=str(location_str))

            # Organizer and attendees
            organizer = component.get("ORGANIZER")
            is_organizer = False
            attendees = []

            if organizer:
                # Simple organizer detection (could be enhanced)
                is_organizer = True

            # Parse attendees
            for attendee_prop in component.get("ATTENDEE", []):
                if not isinstance(attendee_prop, list):
                    attendee_prop = [attendee_prop]

                for att in attendee_prop:
                    try:
                        attendee = self._parse_attendee(att)
                        if attendee:
                            attendees.append(attendee)
                    except Exception as e:
                        logger.debug(f"Failed to parse attendee: {e}")

            # Recurrence
            rrule_prop = component.get("RRULE")
            is_recurring = rrule_prop is not None

            # Additional metadata
            created = self._parse_datetime_optional(component.get("CREATED"))
            last_modified = self._parse_datetime_optional(component.get("LAST-MODIFIED"))

            # Online meeting detection (Microsoft-specific)
            is_online_meeting = False
            online_meeting_url = None

            # Check for Microsoft Teams or other online meeting indicators
            if description:
                desc_str = str(description).lower()
                if any(
                    indicator in desc_str
                    for indicator in ["teams.microsoft.com", "zoom.us", "meet.google.com"]
                ):
                    is_online_meeting = True
                    # Try to extract URL (basic implementation)
                    import re

                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                    urls = re.findall(url_pattern, str(description))
                    if urls:
                        online_meeting_url = urls[0]

            # Create CalendarEvent
            event = CalendarEvent(
                id=uid,
                subject=summary,
                body_preview=body_preview,
                start=start_info,
                end=end_info,
                is_all_day=is_all_day,
                show_as=show_as,
                is_cancelled=status == "CANCELLED",
                is_organizer=is_organizer,
                location=location,
                attendees=attendees if attendees else None,
                is_recurring=is_recurring,
                created_date_time=created,
                last_modified_date_time=last_modified,
                is_online_meeting=is_online_meeting,
                online_meeting_url=online_meeting_url,
            )

            return event

        except Exception as e:
            logger.error(f"Failed to parse event component: {e}")
            return None

    def _parse_datetime(self, dt_prop: Any, default_timezone: Optional[str] = None) -> datetime:
        """Parse iCalendar datetime property.

        Args:
            dt_prop: iCalendar datetime property
            default_timezone: Default timezone if none specified

        Returns:
            Parsed datetime with timezone
        """
        dt = dt_prop.dt

        # Handle date-only (all-day events)
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                # No timezone specified, use default or UTC
                if default_timezone:
                    try:
                        tz_obj = tz.gettz(default_timezone)
                        dt = dt.replace(tzinfo=tz_obj)
                    except Exception:
                        dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.replace(tzinfo=timezone.utc)
            return dt
        else:
            # Date object - convert to datetime at midnight
            return datetime.combine(dt, datetime.min.time()).replace(tzinfo=timezone.utc)

    def _parse_datetime_optional(self, dt_prop: Any) -> Optional[datetime]:
        """Parse optional datetime property.

        Args:
            dt_prop: iCalendar datetime property or None

        Returns:
            Parsed datetime or None
        """
        if dt_prop is None:
            return None

        try:
            return self._parse_datetime(dt_prop)
        except Exception:
            return None

    def _parse_status(self, status_prop: Any) -> Optional[str]:
        """Parse event status.

        Args:
            status_prop: iCalendar STATUS property

        Returns:
            Status string or None
        """
        if status_prop is None:
            return None

        return str(status_prop).upper()

    def _map_transparency_to_status(self, transparency: str, status: Optional[str]) -> EventStatus:
        """Map iCalendar transparency and status to EventStatus.

        Args:
            transparency: TRANSP property value
            status: STATUS property value

        Returns:
            EventStatus enum value
        """
        if status == "CANCELLED":
            return EventStatus.FREE

        if status == "TENTATIVE":
            return EventStatus.TENTATIVE

        # Map transparency
        if transparency == "TRANSPARENT":
            return EventStatus.FREE
        else:  # OPAQUE or default
            return EventStatus.BUSY

    def _parse_attendee(self, attendee_prop: Any) -> Optional[Attendee]:
        """Parse attendee from iCalendar property.

        Args:
            attendee_prop: iCalendar ATTENDEE property

        Returns:
            Parsed Attendee or None
        """
        try:
            # Extract email from the property
            email = str(attendee_prop).replace("mailto:", "")

            # Get parameters
            params = getattr(attendee_prop, "params", {})

            # Name
            name = params.get("CN", email.split("@")[0])

            # Role/Type
            role = params.get("ROLE", "REQ-PARTICIPANT")
            attendee_type = AttendeeType.REQUIRED
            if role == "OPT-PARTICIPANT":
                attendee_type = AttendeeType.OPTIONAL
            elif role == "NON-PARTICIPANT":
                attendee_type = AttendeeType.RESOURCE

            # Response status
            partstat = params.get("PARTSTAT", "NEEDS-ACTION")
            response_status = ResponseStatus.NOT_RESPONDED

            status_map = {
                "ACCEPTED": ResponseStatus.ACCEPTED,
                "DECLINED": ResponseStatus.DECLINED,
                "TENTATIVE": ResponseStatus.TENTATIVELY_ACCEPTED,
                "DELEGATED": ResponseStatus.NOT_RESPONDED,
                "NEEDS-ACTION": ResponseStatus.NOT_RESPONDED,
            }

            response_status = status_map.get(partstat, ResponseStatus.NOT_RESPONDED)

            return Attendee(
                name=name, email=email, type=attendee_type, response_status=response_status
            )

        except Exception as e:
            logger.debug(f"Failed to parse attendee: {e}")
            return None

    def _get_calendar_property(self, calendar: Calendar, prop_name: str) -> Optional[str]:
        """Get calendar-level property.

        Args:
            calendar: iCalendar Calendar object
            prop_name: Property name to get

        Returns:
            Property value as string or None
        """
        try:
            prop = calendar.get(prop_name)
            return str(prop) if prop else None
        except Exception:
            return None

    def expand_recurring_events(
        self, events: List[CalendarEvent], start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Expand recurring events within date range.

        **IMPLEMENTATION STATUS: PLACEHOLDER - NOT YET IMPLEMENTED**

        This method is currently a placeholder that returns events unchanged.
        Full recurrence expansion will be implemented in a future release.

        **Planned Implementation:**

        The full implementation will handle:

        1. **RRULE Processing**: Parse RRULE properties using dateutil.rrule
        2. **Occurrence Generation**: Create individual CalendarEvent instances for each occurrence
        3. **Exception Handling**: Process EXDATE (excluded dates) and RDATE (additional dates)
        4. **Recurrence Modifications**: Handle modified occurrences (RECURRENCE-ID)
        5. **Performance Optimization**: Limit expansion to the requested date range
        6. **Timezone Handling**: Proper timezone conversion for recurring events

        **Implementation Timeline:** Targeted for version 2.0

        **Current Behavior:** Returns original events list unchanged

        Args:
            events (List[CalendarEvent]): List of calendar events, including recurring events
            start_date (datetime): Start of expansion date range
            end_date (datetime): End of expansion date range

        Returns:
            List[CalendarEvent]: List with recurring events expanded (currently unchanged)

        Note:
            Current implementation is a placeholder. Recurring events are currently
            handled by showing only the master event. For proper recurrence support,
            use a fully-featured calendar library or wait for the full implementation.

        Example:
            >>> parser = ICSParser(settings)
            >>> events = [recurring_event, single_event]
            >>> expanded = parser.expand_recurring_events(
            ...     events,
            ...     datetime(2024, 1, 1),
            ...     datetime(2024, 1, 31)
            ... )
            >>> # Currently returns original events unchanged
        """
        # TODO: Implement full recurrence expansion using dateutil.rrule
        # TODO: Add support for EXDATE and RDATE processing
        # TODO: Handle RECURRENCE-ID for modified occurrences
        # TODO: Add timezone-aware recurrence handling
        # TODO: Optimize performance for large date ranges

        logger.debug("Recurrence expansion not yet implemented, returning original events")
        logger.info(
            f"Placeholder: Would expand {len([e for e in events if e.is_recurring])} recurring events from {start_date} to {end_date}"
        )
        return events

    def filter_busy_events(self, events: List[CalendarEvent]) -> List[CalendarEvent]:
        """Filter to only show busy/tentative events.

        Args:
            events: List of calendar events

        Returns:
            Filtered list of events
        """
        return [event for event in events if event.is_busy_status and not event.is_cancelled]

    def validate_ics_content(self, ics_content: str) -> bool:
        """Validate that content is valid ICS format.

        Args:
            ics_content: ICS content to validate

        Returns:
            True if valid ICS format, False otherwise
        """
        try:
            if not ics_content or not ics_content.strip():
                self.security_logger.log_input_validation_failure(
                    input_type="ics_content",
                    validation_error="Empty ICS content provided",
                    details={
                        "source_ip": "internal",
                        "input_value": "<empty>",
                        "content_length": 0,
                    },
                )
                return False

            # Check for required ICS markers
            if "BEGIN:VCALENDAR" not in ics_content:
                self.security_logger.log_input_validation_failure(
                    input_type="ics_content",
                    validation_error="Missing BEGIN:VCALENDAR marker",
                    details={
                        "source_ip": "internal",
                        "content_length": len(ics_content),
                        "input_preview": (
                            ics_content[:100] + "..." if len(ics_content) > 100 else ics_content
                        ),
                    },
                )
                return False

            if "END:VCALENDAR" not in ics_content:
                self.security_logger.log_input_validation_failure(
                    input_type="ics_content",
                    validation_error="Missing END:VCALENDAR marker",
                    details={
                        "source_ip": "internal",
                        "content_length": len(ics_content),
                        "input_preview": (
                            ics_content[:100] + "..." if len(ics_content) > 100 else ics_content
                        ),
                    },
                )
                return False

            # Try to parse with icalendar
            Calendar.from_ical(ics_content)

            # No logging for successful validation - only security violations are logged
            logger.debug(f"Valid ICS content parsed successfully: {len(ics_content)} bytes")
            return True

        except Exception as e:
            self.security_logger.log_input_validation_failure(
                input_type="ics_content",
                validation_error=f"ICS parsing failed: {e}",
                details={
                    "source_ip": "internal",
                    "content_length": len(ics_content) if ics_content else 0,
                    "input_preview": (
                        ics_content[:100] + "..."
                        if ics_content and len(ics_content) > 100
                        else ics_content or "<empty>"
                    ),
                    "exception_type": type(e).__name__,
                },
            )
            logger.debug(f"ICS validation failed: {e}")
            return False
