"""Event component parsing for ICS calendar processing - CalendarBot Lite.

This module provides parsing of VEVENT components from iCalendar files.
Extracted from lite_parser.py to improve modularity and testability.
"""

import logging
import re
import uuid
from datetime import timedelta
from typing import Any, Optional

from icalendar import Event as ICalEvent

from calendarbot_lite.calendar.lite_attendee_parser import LiteAttendeeParser
from calendarbot_lite.calendar.lite_datetime_utils import LiteDateTimeParser
from calendarbot_lite.calendar.lite_models import (
    LiteCalendarEvent,
    LiteDateTimeInfo,
    LiteEventStatus,
    LiteLocation,
)
from calendarbot_lite.core.config_manager import (
    MAX_EVENT_DESCRIPTION_LENGTH,
    MAX_EVENT_LOCATION_LENGTH,
    MAX_EVENT_SUBJECT_LENGTH,
)

logger = logging.getLogger(__name__)


class LiteEventComponentParser:
    """Parser for iCalendar VEVENT components into LiteCalendarEvent objects."""

    def __init__(
        self,
        datetime_parser: LiteDateTimeParser,
        attendee_parser: LiteAttendeeParser,
        settings: Any = None,
    ):
        """Initialize event component parser.

        Args:
            datetime_parser: Parser for datetime properties
            attendee_parser: Parser for attendee properties
            settings: Optional application settings
        """
        self.datetime_parser = datetime_parser
        self.attendee_parser = attendee_parser
        self.settings = settings

    def parse_event_component(
        self,
        component: ICalEvent,
        default_timezone: Optional[str] = None,
    ) -> Optional[LiteCalendarEvent]:
        """Parse a single VEVENT component into LiteCalendarEvent.

        Args:
            component: iCalendar VEVENT component
            default_timezone: Default timezone for the calendar

        Returns:
            Parsed LiteCalendarEvent or None if parsing fails
        """
        try:
            # Extract basic properties
            basic_props = self._extract_basic_properties(component)

            # Parse event times
            try:
                start_info, end_info = self._parse_event_times(component, default_timezone)
            except ValueError as e:
                logger.warning("Event %s %s, skipping", basic_props["uid"], e)
                return None

            # Event status and visibility
            status = self._parse_status(component.get("STATUS"))
            transp = component.get("TRANSP", "OPAQUE")
            show_as = self._map_transparency_to_status(transp, status, component)

            # Extract attendee info
            attendee_info = self._extract_attendee_info(component)

            # Extract recurrence info
            recurrence_info = self._extract_recurrence_info(component)

            # Additional metadata
            created = self.datetime_parser.parse_datetime_optional(component.get("CREATED"))
            last_modified = self.datetime_parser.parse_datetime_optional(
                component.get("LAST-MODIFIED")
            )

            # Online meeting detection (Microsoft-specific)
            is_online_meeting, online_meeting_url = self._detect_online_meeting(
                basic_props["description"]
            )

            # Create LiteCalendarEvent
            calendar_event = LiteCalendarEvent(
                id=basic_props["uid"],
                subject=basic_props["summary"],
                body_preview=basic_props["body_preview"],
                start=start_info,
                end=end_info,
                is_all_day=basic_props["is_all_day"],
                show_as=show_as,
                is_cancelled=status == "CANCELLED",
                is_organizer=attendee_info["is_organizer"],
                location=basic_props["location"],
                attendees=attendee_info["attendees"],
                is_recurring=recurrence_info["is_recurring"],
                recurrence_id=recurrence_info["recurrence_id"],
                created_date_time=created,
                last_modified_date_time=last_modified,
                is_online_meeting=is_online_meeting,
                online_meeting_url=online_meeting_url,
            )

            # Attach RRULE and EXDATE metadata onto the parsed event so downstream
            # helpers (debug scripts and expanders) can discover RRULEs directly
            # from the parsed event object. This is defensive and preserves the
            # existing expansion flow which may use raw components in other codepaths.
            self._attach_rrule_metadata(
                calendar_event,
                recurrence_info["rrule_prop"],
                recurrence_info["exdate_props"],
            )

        except Exception:
            logger.exception("Failed to parse event component")
            return None
        else:
            return calendar_event

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
        self,
        transparency: str,
        status: Optional[str],
        component: Any,
    ) -> LiteEventStatus:
        """Map iCalendar transparency and status to LiteEventStatus using priority-based rules.

        This function evaluates status mapping rules in priority order (highest to lowest):
        1. Microsoft deletion markers (X-OUTLOOK-DELETED)
        2. Microsoft busy status override (X-MICROSOFT-CDO-BUSYSTATUS=FREE)
        3. Standard iCalendar STATUS property (CANCELLED, TENTATIVE)
        4. TRANSP property (TRANSPARENT)
        5. Special meeting types (Following meetings)
        6. Default fallback

        Args:
            transparency: TRANSP property value
            status: STATUS property value
            component: Raw iCalendar component for vendor-specific marker access

        Returns:
            LiteEventStatus enum value

        See Also:
            docs/ALGORITHMS.md - Status Mapping Algorithm documentation
        """
        # Extract context once for all rules
        context = {
            "transparency": transparency,
            "status": status,
            "ms_deleted": self._is_microsoft_deleted(component),
            "ms_busystatus": self._get_microsoft_busystatus(component),
            "is_following": self._is_following_meeting(component),
        }

        # Define priority-ordered rules (first match wins)
        rules = [
            # Rule 1: Microsoft deletion markers (highest precedence)
            (
                lambda ctx: ctx["ms_deleted"],
                LiteEventStatus.FREE,
                "Microsoft deleted marker",
            ),
            # Rule 2: Microsoft busy status = FREE
            (
                lambda ctx: ctx["ms_busystatus"] == "FREE" and not ctx["is_following"],
                LiteEventStatus.FREE,
                "Microsoft FREE busystatus",
            ),
            # Rule 3: Microsoft busy status = FREE + Following meeting
            (
                lambda ctx: ctx["ms_busystatus"] == "FREE" and ctx["is_following"],
                LiteEventStatus.TENTATIVE,
                "Microsoft FREE busystatus + Following",
            ),
            # Rule 4: Cancelled events
            (
                lambda ctx: ctx["status"] == "CANCELLED",
                LiteEventStatus.FREE,
                "STATUS=CANCELLED",
            ),
            # Rule 5: Tentative events
            (
                lambda ctx: ctx["status"] == "TENTATIVE",
                LiteEventStatus.TENTATIVE,
                "STATUS=TENTATIVE",
            ),
            # Rule 6: Transparent + Confirmed (special case)
            (
                lambda ctx: ctx["transparency"] == "TRANSPARENT" and ctx["status"] == "CONFIRMED",
                LiteEventStatus.TENTATIVE,
                "TRANSPARENT + CONFIRMED",
            ),
            # Rule 7: Transparent events
            (
                lambda ctx: ctx["transparency"] == "TRANSPARENT",
                LiteEventStatus.FREE,
                "TRANSPARENT",
            ),
            # Rule 8: Following meetings
            (
                lambda ctx: ctx["is_following"],
                LiteEventStatus.TENTATIVE,
                "Following meeting",
            ),
        ]

        # Evaluate rules in priority order
        for condition, result, rule_name in rules:
            if condition(context):
                logger.debug("Status mapping: %s → %s", rule_name, result)
                return result

        # Default: BUSY (opaque, confirmed, or no specific status)
        logger.debug("Status mapping: Default → BUSY")
        return LiteEventStatus.BUSY

    def _is_microsoft_deleted(self, component: Any) -> bool:
        """Check if event is marked as deleted by Microsoft Outlook.

        Args:
            component: iCalendar component

        Returns:
            True if event is marked as deleted
        """
        ms_deleted = component.get("X-OUTLOOK-DELETED")
        return ms_deleted is not None and str(ms_deleted).upper() == "TRUE"

    def _get_microsoft_busystatus(self, component: Any) -> Optional[str]:
        """Get Microsoft busy status if present.

        Args:
            component: iCalendar component

        Returns:
            Uppercase busy status string or None
        """
        ms_busystatus = component.get("X-MICROSOFT-CDO-BUSYSTATUS")
        return str(ms_busystatus).upper() if ms_busystatus else None

    def _is_following_meeting(self, component: Any) -> bool:
        """Check if this is a 'Following:' meeting.

        Args:
            component: iCalendar component

        Returns:
            True if summary contains 'Following:'
        """
        summary = component.get("SUMMARY")
        return summary is not None and "Following:" in str(summary)

    def _collect_exdate_props(self, component: ICalEvent) -> list[Any]:
        """Robustly collect EXDATE properties from an icalendar VEVENT component.

        The icalendar library exposes EXDATE in a few different ways depending on
        version and how the calendar was authored:
        - component.getall("EXDATE")
        - component["EXDATE"]
        - multiple property entries accessible via component.property_items() or items()

        This helper normalizes all those patterns into a list of property objects
        (the raw objects returned by the icalendar parser) so callers can convert
        them into strings/timestamps while preserving any TZID params.
        """
        exdate_props: list[Any] = []

        # Preferred: getall() (returns list of matching props)
        try:
            props = component.getall("EXDATE")  # type: ignore
            if props:
                exdate_props.extend(props)
        except Exception:
            pass  # nosec B110 - graceful degradation for different calendar formats

        # Fallback: dict-like access component["EXDATE"]
        if not exdate_props and "EXDATE" in component:
            try:
                val = component["EXDATE"]
                # component["EXDATE"] may be a single prop or a list-like structure
                if isinstance(val, list):
                    exdate_props.extend(val)
                else:
                    exdate_props.append(val)
            except Exception:
                pass  # nosec B110 - graceful degradation for different calendar formats

        # Last resort: scan property items for keys equal to EXDATE (case-insensitive)
        if not exdate_props:
            try:
                for key, val in getattr(component, "property_items", list)():
                    if str(key).upper() == "EXDATE":
                        if isinstance(val, list):
                            exdate_props.extend(val)
                        else:
                            exdate_props.append(val)
            except Exception:
                # property_items may not exist on some icalendar types; try items()
                try:
                    for key, val in component.items():
                        if str(key).upper() == "EXDATE":
                            if isinstance(val, list):
                                exdate_props.extend(val)
                            else:
                                exdate_props.append(val)
                except Exception:
                    pass  # nosec B110 - graceful degradation for different calendar formats

        return exdate_props

    def _detect_online_meeting(self, description: Any) -> tuple[bool, Optional[str]]:
        """Detect if event is an online meeting and extract meeting URL.

        Args:
            description: Event description text

        Returns:
            Tuple of (is_online_meeting, online_meeting_url)
        """
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
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, str(description))
                if urls:
                    online_meeting_url = urls[0]

        return is_online_meeting, online_meeting_url

    def _attach_rrule_metadata(
        self,
        calendar_event: LiteCalendarEvent,
        rrule_prop: Any,
        exdate_props: list[Any],
    ) -> None:
        """Attach RRULE and EXDATE metadata to parsed event.

        This allows downstream helpers (debug scripts and expanders) to discover
        RRULEs directly from the parsed event object.

        Args:
            calendar_event: Parsed calendar event to attach metadata to
            rrule_prop: RRULE property from component
            exdate_props: List of EXDATE properties
        """
        try:
            rrule_string = None
            if rrule_prop:
                if hasattr(rrule_prop, "to_ical"):
                    rrule_string = rrule_prop.to_ical().decode("utf-8")
                else:
                    rrule_string = str(rrule_prop)

            exdates_list: list[str] = []
            if exdate_props:
                if not isinstance(exdate_props, list):
                    exdate_props = [exdate_props]
                for exdate in exdate_props:
                    try:
                        if hasattr(exdate, "to_ical"):
                            exdate_str = exdate.to_ical().decode("utf-8")
                            tzid = None
                            if hasattr(exdate, "params") and "TZID" in exdate.params:
                                tzid = exdate.params["TZID"]

                            parts = [p.strip() for p in exdate_str.split(",") if p.strip()]
                            for p in parts:
                                if tzid:
                                    exdates_list.append(f"TZID={tzid}:{p}")
                                else:
                                    exdates_list.append(p)
                        else:
                            exdate_str = str(exdate)
                            exdates_list.extend(
                                [q.strip() for q in exdate_str.split(",") if q.strip()]
                            )
                    except Exception as e:
                        logger.debug("Failed to parse EXDATE entry: %s", e)
                        continue

            # Attach metadata to the underlying model dict so we don't trigger
            # Pydantic unknown-field errors when assigning to a BaseModel.
            try:
                calendar_event.__dict__["rrule_string"] = rrule_string
                calendar_event.__dict__["exdates"] = exdates_list if exdates_list else None
            except Exception as e:
                # As a final fallback, create a lightweight metadata map on the object
                logger.debug("Failed to set rrule metadata on __dict__, trying setattr: %s", e)
                try:
                    object.__setattr__(
                        calendar_event,
                        "_metadata",
                        {
                            "rrule_string": rrule_string,
                            "exdates": (exdates_list if exdates_list else None),
                        },
                    )
                except Exception as setattr_error:
                    logger.debug("Failed to set metadata attribute: %s", setattr_error)
        except Exception:
            # Non-fatal: expansion code will fall back to raw component mapping if needed
            logger.debug("Failed to attach rrule/exdate metadata to parsed event", exc_info=True)

    def _extract_basic_properties(self, component: ICalEvent) -> dict[str, Any]:
        """Extract basic event properties from component.

        Args:
            component: iCalendar VEVENT component

        Returns:
            Dictionary with basic properties: uid, summary, description, body_preview,
            location, is_all_day
        """
        uid = str(component.get("UID", str(uuid.uuid4())))
        summary_raw = str(component.get("SUMMARY", "No Title"))
        # Truncate subject to maximum length (validation will strip whitespace)
        summary = (
            summary_raw[:MAX_EVENT_SUBJECT_LENGTH]
            if len(summary_raw) > MAX_EVENT_SUBJECT_LENGTH
            else summary_raw
        )

        # Description
        description = component.get("DESCRIPTION")
        body_preview = None
        if description:
            # Truncate description to maximum length (validation allows 500 chars)
            desc_str = str(description)
            body_preview = (
                desc_str[:MAX_EVENT_DESCRIPTION_LENGTH]
                if len(desc_str) > MAX_EVENT_DESCRIPTION_LENGTH
                else desc_str
            )

        # Location
        location = None
        location_str = component.get("LOCATION")
        if location_str:
            # Truncate location to maximum length
            loc_str = str(location_str)
            loc_truncated = (
                loc_str[:MAX_EVENT_LOCATION_LENGTH]
                if len(loc_str) > MAX_EVENT_LOCATION_LENGTH
                else loc_str
            )
            if loc_truncated.strip():  # Only create location if non-empty after truncation
                location = LiteLocation(display_name=loc_truncated)

        # All-day events
        dtstart = component.get("DTSTART")
        is_all_day = False
        if dtstart:
            is_all_day = not hasattr(dtstart.dt, "hour")

        return {
            "uid": uid,
            "summary": summary,
            "description": description,
            "body_preview": body_preview,
            "location": location,
            "is_all_day": is_all_day,
        }

    def _parse_event_times(
        self,
        component: ICalEvent,
        default_timezone: Optional[str],
    ) -> tuple[LiteDateTimeInfo, LiteDateTimeInfo]:
        """Parse event start and end times from component.

        Args:
            component: iCalendar VEVENT component
            default_timezone: Default timezone for the calendar

        Returns:
            Tuple of (start_info, end_info) as LiteDateTimeInfo objects

        Raises:
            ValueError: If DTSTART is missing
        """
        # Time information
        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")

        if not dtstart:
            raise ValueError("Event missing DTSTART")

        # Parse start time
        start_dt = self.datetime_parser.parse_datetime(dtstart, default_timezone)
        start_info = LiteDateTimeInfo(
            date_time=start_dt,
            time_zone=str(start_dt.tzinfo) if start_dt.tzinfo else "UTC",
        )

        # Parse end time
        if dtend:
            end_dt = self.datetime_parser.parse_datetime(dtend, default_timezone)
        else:
            # Use duration if available, otherwise default to 1 hour
            duration = component.get("DURATION")
            if duration and hasattr(duration, "dt"):
                end_dt = start_dt + duration.dt
            else:
                end_dt = start_dt + timedelta(hours=1)

        end_info = LiteDateTimeInfo(
            date_time=end_dt,
            time_zone=str(end_dt.tzinfo) if end_dt.tzinfo else "UTC",
        )

        return start_info, end_info

    def _extract_attendee_info(self, component: ICalEvent) -> dict[str, Any]:
        """Extract attendee and organizer information from component.

        Args:
            component: iCalendar VEVENT component

        Returns:
            Dictionary with attendee info: is_organizer, attendees
        """
        # Organizer and attendees
        organizer = component.get("ORGANIZER")
        is_organizer = False

        if organizer and hasattr(self.settings, "user_email"):
            # Enhanced organizer detection - check if organizer email matches user
            organizer_str = str(organizer).replace("mailto:", "").strip().lower()
            user_email = str(self.settings.user_email).strip().lower()
            is_organizer = organizer_str == user_email
        elif organizer:
            # Fallback: if no user_email in settings, assume not organizer
            # (more conservative than always True)
            is_organizer = False

        # Parse attendees using the dedicated parser
        attendees = self.attendee_parser.parse_attendees(component)

        return {
            "is_organizer": is_organizer,
            "attendees": attendees if attendees else None,
        }

    def _extract_recurrence_info(self, component: ICalEvent) -> dict[str, Any]:
        """Extract recurrence information from component.

        Args:
            component: iCalendar VEVENT component

        Returns:
            Dictionary with recurrence info: is_recurring, recurrence_id, exdate_props
        """
        # Recurrence
        rrule_prop = component.get("RRULE")
        is_recurring = rrule_prop is not None

        # RFC 5545 RECURRENCE-ID detection for Microsoft ICS bug
        # When a recurring instance is moved, the original slot should be excluded
        recurrence_id_raw = component.get("RECURRENCE-ID")

        # Convert RECURRENCE-ID to string properly, preserving TZID parameter
        # Fix for issue #43: TZID must be preserved for correct EXDATE comparison
        if recurrence_id_raw is None:
            recurrence_id = None
        else:
            recurrence_id = self._format_recurrence_id(recurrence_id_raw)

        # Check if this event should be excluded due to EXDATE
        # Use the defensive collector to handle getall(), dict-like access, and param-preserving props
        exdate_props = self._collect_exdate_props(component)
        # Ensure exdate_props is always a list
        if exdate_props is None:
            exdate_props = []
        elif not isinstance(exdate_props, list):
            exdate_props = [exdate_props]

        return {
            "is_recurring": is_recurring,
            "recurrence_id": recurrence_id,
            "rrule_prop": rrule_prop,
            "exdate_props": exdate_props,
        }

    def _format_recurrence_id(self, recurrence_id_raw: Any) -> str:
        """Format a recurrence ID, preserving TZID if present, for consistent comparison.

        Args:
            recurrence_id_raw: The raw RECURRENCE-ID property from the component

        Returns:
            Formatted recurrence ID string, with TZID prefix if applicable
        """
        if hasattr(recurrence_id_raw, "to_ical"):
            recurrence_id_str = recurrence_id_raw.to_ical().decode("utf-8")
            tzid = (
                recurrence_id_raw.params["TZID"]
                if hasattr(recurrence_id_raw, "params") and "TZID" in recurrence_id_raw.params
                else None
            )
            if tzid:
                return f"TZID={tzid}:{recurrence_id_str}"
            return recurrence_id_str
        return str(recurrence_id_raw)
