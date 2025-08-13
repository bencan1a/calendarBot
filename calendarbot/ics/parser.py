"""iCalendar parser with Microsoft Outlook compatibility."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional, cast

from icalendar import Calendar, Event as ICalEvent

from ..security.logging import SecurityEventLogger  # type: ignore
from ..timezone import (
    ensure_timezone_aware,
)
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

# Size validation constants from design specification
MAX_ICS_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit
MAX_ICS_SIZE_WARNING = 10 * 1024 * 1024  # 10MB warning threshold


class ICSContentTooLargeError(Exception):
    """Raised when ICS content exceeds size limits."""


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

    def _validate_ics_size(self, ics_content: str) -> None:
        """Validate ICS content size before processing.

        Args:
            ics_content: Raw ICS content to validate

        Raises:
            ICSContentTooLargeError: If content exceeds maximum size limit
        """
        if not ics_content:
            return

        size_bytes = len(ics_content.encode("utf-8"))

        if size_bytes > MAX_ICS_SIZE_BYTES:
            logger.error(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit"
            )
            raise ICSContentTooLargeError(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit"
            )

        if size_bytes > MAX_ICS_SIZE_WARNING:
            logger.warning(
                f"Large ICS content detected: {size_bytes} bytes "
                f"(threshold: {MAX_ICS_SIZE_WARNING})"
            )

    def parse_ics_content(
        self, ics_content: str, source_url: Optional[str] = None
    ) -> ICSParseResult:
        """Parse ICS content into structured calendar events.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with events and metadata including raw content
        """
        # Initialize variables that might be used in error handling
        raw_content = None

        try:
            logger.debug("Starting ICS content parsing")

            # Capture raw content and validate size (with error handling)
            try:
                self._validate_ics_size(ics_content)
                raw_content = ics_content
                logger.debug(f"Raw ICS content captured: {len(ics_content)} bytes")
            except ICSContentTooLargeError:
                logger.exception("ICS content too large, skipping raw content storage")
                raise  # Re-raise to stop processing
            except Exception as e:
                logger.warning(f"Failed to capture raw ICS content: {e}")
                # Continue parsing without raw content

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
            raw_components = []  # Store raw components for phantom filtering
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
                            raw_components.append(component)  # Store raw component
                            event_count += 1

                            if event.is_recurring:
                                recurring_event_count += 1

                    except Exception as e:
                        warning = f"Failed to parse event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

            # Filter to only busy/tentative events (same as Graph API behavior)
            # TODO: This should respect the filter_busy_only configuration setting
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
                raw_content=raw_content,
                source_url=source_url,
            )

        except Exception as e:
            logger.exception("Failed to parse ICS content")
            return ICSParseResult(
                success=False,
                error_message=str(e),
                raw_content=raw_content,
                source_url=source_url,
            )

    def parse_ics_content_unfiltered(
        self, ics_content: str, source_url: Optional[str] = None
    ) -> ICSParseResult:
        """Parse ICS content into ALL events without filtering for raw event storage.

        This method returns ALL parsed events without any filtering, specifically
        for raw event storage to enable comparison with cached events.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with ALL events and metadata including raw content
        """
        # Initialize variables that might be used in error handling
        raw_content = None

        try:
            logger.debug("Starting unfiltered ICS content parsing for raw events")

            # Capture raw content and validate size (with error handling)
            try:
                self._validate_ics_size(ics_content)
                raw_content = ics_content
                logger.debug(f"Raw ICS content captured: {len(ics_content)} bytes")
            except ICSContentTooLargeError:
                logger.exception("ICS content too large, skipping raw content storage")
                raise  # Re-raise to stop processing
            except Exception as e:
                logger.warning(f"Failed to capture raw ICS content: {e}")
                # Continue parsing without raw content

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

            # Parse events and capture individual event raw content
            events = []
            event_raw_content_map = {}  # Map event ID to individual raw ICS content
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

                            # Extract individual event ICS content using component.to_ical()
                            try:
                                individual_ics = component.to_ical().decode("utf-8")
                                event_raw_content_map[event.id] = individual_ics
                                logger.debug(
                                    f"Captured raw ICS for event {event.id}: {len(individual_ics)} bytes"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to extract raw ICS for event {event.id}: {e}"
                                )
                                # Fallback to basic event identifier
                                event_raw_content_map[event.id] = (
                                    f"# Event {event.id} - Raw ICS extraction failed"
                                )

                            if event.is_recurring:
                                recurring_event_count += 1

                    except Exception as e:
                        warning = f"Failed to parse event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

            # NO FILTERING - return ALL events for raw storage
            logger.debug(
                f"Parsed {len(events)} unfiltered events from ICS content "
                f"({event_count} total events, no filtering applied)"
            )

            # Create enhanced result with individual event raw content mapping
            result = ICSParseResult(
                success=True,
                events=events,  # Return ALL events without filtering
                calendar_name=calendar_name,
                calendar_description=calendar_description,
                timezone=timezone_str,
                total_components=total_components,
                event_count=event_count,
                recurring_event_count=recurring_event_count,
                warnings=warnings,
                ics_version=version,
                prodid=prodid,
                raw_content=raw_content,
                source_url=source_url,
            )

            # Store individual event raw content in the result for access by cache manager
            result.event_raw_content_map = event_raw_content_map

            return result

        except Exception as e:
            logger.exception("Failed to parse ICS content")
            return ICSParseResult(
                success=False,
                error_message=str(e),
                raw_content=raw_content,
                source_url=source_url,
            )

    def _parse_event_component(  # noqa
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
                end_dt = start_dt + duration.dt if duration else start_dt + timedelta(hours=1)

            end_info = DateTimeInfo(
                date_time=end_dt, time_zone=str(end_dt.tzinfo) if end_dt.tzinfo else "UTC"
            )

            # Event status and visibility
            status = self._parse_status(component.get("STATUS"))
            transp = component.get("TRANSP", "OPAQUE")

            show_as = self._map_transparency_to_status(transp, status, component)

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
                attendee_list = (
                    attendee_prop if isinstance(attendee_prop, list) else [attendee_prop]
                )

                for att in attendee_list:
                    attendee = self._parse_attendee(att)
                    if attendee:
                        attendees.append(attendee)

            # Recurrence
            rrule_prop = component.get("RRULE")
            is_recurring = rrule_prop is not None

            # RFC 5545 RECURRENCE-ID detection for Microsoft ICS bug
            # When a recurring instance is moved, the original slot should be excluded
            recurrence_id = component.get("RECURRENCE-ID")
            is_moved_instance = recurrence_id is not None  # noqa

            # Check if this event should be excluded due to EXDATE
            exdate_props = component.get("EXDATE", [])
            if not isinstance(exdate_props, list):
                exdate_props = [exdate_props] if exdate_props else []

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
                    import re  # noqa: PLC0415

                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                    urls = re.findall(url_pattern, str(description))
                    if urls:
                        online_meeting_url = urls[0]

            # Create CalendarEvent
            calendar_event = CalendarEvent(
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

        except Exception:
            logger.exception("Failed to parse event component")
            return None
        else:
            return calendar_event

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
                # No timezone specified, use centralized service for timezone handling
                if default_timezone:
                    try:
                        # Use centralized timezone service to handle timezone conversion
                        # This replaces the manual Australian timezone hack with proper service handling
                        dt = ensure_timezone_aware(dt)
                        # If a specific timezone was requested, convert to that timezone
                        # For now, we'll use the server timezone as the base since that's our standard
                        logger.debug(
                            f"Parsed naive datetime {dt} with default timezone: {default_timezone}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply timezone via service {default_timezone}: {e}"
                        )
                        dt = ensure_timezone_aware(dt)  # Fallback to server timezone
                else:
                    # Use centralized service for standard timezone awareness
                    dt = ensure_timezone_aware(dt)
            else:
                # Already has timezone info, ensure it's properly handled
                dt = ensure_timezone_aware(dt)
            return dt
        # Date object - convert to datetime at midnight with proper timezone
        return ensure_timezone_aware(datetime.combine(dt, datetime.min.time()))

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

    def _map_transparency_to_status(
        self, transparency: str, status: Optional[str], component: Any
    ) -> EventStatus:
        """Map iCalendar transparency and status to EventStatus with Microsoft phantom event filtering.

        Args:
            transparency: TRANSP property value
            status: STATUS property value
            component: Raw iCalendar component for Microsoft marker access

        Returns:
            EventStatus enum value
        """
        # Check Microsoft deletion markers for phantom event filtering
        ms_deleted = component.get("X-OUTLOOK-DELETED")
        ms_busystatus = component.get("X-MICROSOFT-CDO-BUSYSTATUS")

        # Filter out Microsoft phantom deleted events
        if ms_deleted and str(ms_deleted).upper() == "TRUE":
            return EventStatus.FREE  # Will be filtered out by busy status check

        # Check if this is a "Following:" meeting by parsing the event title
        summary = component.get("SUMMARY")
        is_following_meeting = summary and "Following:" in str(summary)

        # Use Microsoft busy status override if available
        if ms_busystatus:
            ms_status = str(ms_busystatus).upper()
            if ms_status == "FREE":
                # Special case: "Following:" meetings should be TENTATIVE, not FREE
                if is_following_meeting:
                    return EventStatus.TENTATIVE
                # All other FREE busy status events should be filtered out
                return EventStatus.FREE

        if status == "CANCELLED":
            mapped_status = EventStatus.FREE
        elif status == "TENTATIVE":
            mapped_status = EventStatus.TENTATIVE
        elif transparency == "TRANSPARENT":
            # Special handling for transparent + confirmed meetings (e.g., "Following" meetings)
            # These should appear on calendar but with different visual treatment
            mapped_status = EventStatus.TENTATIVE if status == "CONFIRMED" else EventStatus.FREE
        elif is_following_meeting:
            # "Following:" meetings should appear on calendar regardless of other properties
            mapped_status = EventStatus.TENTATIVE
            logger.info(f"  → APPLIED FOLLOWING LOGIC: {mapped_status}")
        else:
            # OPAQUE or default
            mapped_status = EventStatus.BUSY

        return mapped_status

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

    def filter_phantom_recurring_events_conservative(  # noqa
        self, events: list[CalendarEvent], raw_components: list
    ) -> list[CalendarEvent]:
        """Conservative filter for phantom recurring events caused by Microsoft ICS RFC 5545 bug.

        Only removes events with explicit evidence of the Microsoft bug:
        - Event must be recurring with no RECURRENCE-ID (original pattern slot)
        - Must have a moved instance (RECURRENCE-ID) within the same UID series
        - Original slot must lack proper EXDATE exclusion

        Args:
            events: Parsed calendar events
            raw_components: Raw iCalendar VEVENT components for RFC 5545 field access

        Returns:
            Filtered events with confirmed phantom recurring instances removed
        """
        if len(events) != len(raw_components):
            logger.warning("Event/component count mismatch, skipping phantom filter")
            return events

        # Build UID-based mapping for precise targeting
        uid_to_events = {}  # UID -> list of (event, component) tuples

        for event, component in zip(events, raw_components):
            uid = str(component.get("UID", ""))
            if uid not in uid_to_events:
                uid_to_events[uid] = []
            uid_to_events[uid].append((event, component))

        filtered_events = []
        phantom_count = 0

        # Process each UID series independently
        for event_component_pairs in uid_to_events.values():
            # Separate original patterns from moved instances within this UID series
            original_patterns = []
            moved_instances = []
            exdate_times = []

            for event, component in event_component_pairs:
                if component.get("RECURRENCE-ID"):
                    # This is a moved instance
                    moved_instances.append((event, component))
                elif event.is_recurring:
                    # This is an original recurring pattern
                    original_patterns.append((event, component))

                # Collect EXDATE times for this UID
                exdate_props = component.get("EXDATE", [])
                if exdate_props:
                    if not isinstance(exdate_props, list):
                        exdate_props = [exdate_props]
                    for exdate in exdate_props:
                        try:
                            # Use the event's timezone for proper parsing
                            timezone_str = (
                                event.start.time_zone
                                if hasattr(event.start, "time_zone")
                                else "UTC"
                            )
                            excluded_time = self._parse_datetime(exdate, timezone_str)
                            exdate_times.append(excluded_time)
                        except Exception:  # noqa: PERF203
                            continue

            # Only check for phantoms if we have both moved instances AND original patterns
            if moved_instances and original_patterns:
                # Check each original pattern for phantom status
                for event, component in original_patterns:  # noqa
                    is_phantom = False
                    event_start = event.start.date_time

                    # Check if this pattern slot has a corresponding moved instance
                    for moved_event, moved_component in moved_instances:
                        recurrence_id = moved_component.get("RECURRENCE-ID")
                        if recurrence_id:
                            try:
                                # Parse using the moved event's timezone
                                moved_timezone = (
                                    moved_event.start.time_zone
                                    if hasattr(moved_event.start, "time_zone")
                                    else "UTC"
                                )
                                original_time = self._parse_datetime(recurrence_id, moved_timezone)

                                # Check if this pattern matches the moved instance's original time
                                if (
                                    abs((event_start - original_time).total_seconds()) < 300
                                ):  # 5 minute tolerance
                                    # Found a moved instance - check if EXDATE properly excludes this slot
                                    is_properly_excluded = any(
                                        abs((event_start - ex_time).total_seconds()) < 300
                                        for ex_time in exdate_times
                                    )

                                    if not is_properly_excluded:
                                        # This is a phantom - moved instance exists but no EXDATE exclusion
                                        logger.debug(
                                            f"🚨 Found phantom recurring event: {event.subject} at {event_start}"
                                        )
                                        logger.debug(
                                            f"   - Moved instance exists with RECURRENCE-ID: {recurrence_id}"
                                        )
                                        logger.debug("   - No proper EXDATE exclusion found")
                                        is_phantom = True
                                        phantom_count += 1
                                        break
                            except Exception as e:
                                logger.warning(f"Error parsing RECURRENCE-ID {recurrence_id}: {e}")
                                continue

                    if not is_phantom:
                        filtered_events.append(event)

                # Always include moved instances (they're the real meetings)
                for moved_event, _ in moved_instances:
                    filtered_events.append(moved_event)
            else:
                # No moved instances, include all events for this UID
                for event, _ in event_component_pairs:
                    filtered_events.append(event)

        if phantom_count > 0:
            logger.info(
                f"🎯 Conservative phantom filter: removed {phantom_count} confirmed phantom events"
            )
        else:
            logger.info("✅ Conservative phantom filter: no phantom events detected")

        return filtered_events

    def filter_busy_events(self, events: list[CalendarEvent]) -> list[CalendarEvent]:
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
