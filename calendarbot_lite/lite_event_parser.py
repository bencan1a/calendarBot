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

from .lite_attendee_parser import LiteAttendeeParser
from .lite_datetime_utils import LiteDateTimeParser
from .lite_models import (
    LiteCalendarEvent,
    LiteDateTimeInfo,
    LiteEventStatus,
    LiteLocation,
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
                logger.warning(f"Event {basic_props['uid']} {e}, skipping")
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
        """Map iCalendar transparency and status to LiteEventStatus with Microsoft phantom event filtering.

        Args:
            transparency: TRANSP property value
            status: STATUS property value
            component: Raw iCalendar component for Microsoft marker access

        Returns:
            LiteEventStatus enum value
        """
        # Check Microsoft deletion markers for phantom event filtering
        ms_deleted = component.get("X-OUTLOOK-DELETED")
        ms_busystatus = component.get("X-MICROSOFT-CDO-BUSYSTATUS")

        # Filter out Microsoft phantom deleted events
        if ms_deleted and str(ms_deleted).upper() == "TRUE":
            return LiteEventStatus.FREE  # Will be filtered out by busy status check

        # Check if this is a "Following:" meeting by parsing the event title
        summary = component.get("SUMMARY")
        is_following_meeting = summary and "Following:" in str(summary)

        # Use Microsoft busy status override if available
        if ms_busystatus:
            ms_status = str(ms_busystatus).upper()
            if ms_status == "FREE":
                # Special case: "Following:" meetings should be TENTATIVE, not FREE
                if is_following_meeting:
                    return LiteEventStatus.TENTATIVE
                # All other FREE busy status events should be filtered out
                return LiteEventStatus.FREE

        if status == "CANCELLED":
            mapped_status = LiteEventStatus.FREE
        elif status == "TENTATIVE":
            mapped_status = LiteEventStatus.TENTATIVE
        elif transparency == "TRANSPARENT":
            # Special handling for transparent + confirmed meetings (e.g., "Following" meetings)
            # These should appear on calendar but with different visual treatment
            mapped_status = (
                LiteEventStatus.TENTATIVE if status == "CONFIRMED" else LiteEventStatus.FREE
            )
        elif is_following_meeting:
            # "Following:" meetings should appear on calendar regardless of other properties
            mapped_status = LiteEventStatus.TENTATIVE
            logger.debug(f"  → APPLIED FOLLOWING LOGIC: {mapped_status}")
        else:
            # OPAQUE or default
            mapped_status = LiteEventStatus.BUSY

        return mapped_status

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
            pass

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
                pass

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
                    pass

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
                        logger.debug(f"Failed to parse EXDATE entry: {e}")
                        continue

            # Attach metadata to the underlying model dict so we don't trigger
            # Pydantic unknown-field errors when assigning to a BaseModel.
            try:
                calendar_event.__dict__["rrule_string"] = rrule_string
                calendar_event.__dict__["exdates"] = exdates_list if exdates_list else None
            except Exception as e:
                # As a final fallback, create a lightweight metadata map on the object
                logger.debug(f"Failed to set rrule metadata on __dict__, trying setattr: {e}")
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
                    logger.debug(f"Failed to set metadata attribute: {setattr_error}")
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
        summary = str(component.get("SUMMARY", "No Title"))

        # Description
        description = component.get("DESCRIPTION")
        body_preview = None
        if description:
            body_preview = str(description)[:200]  # Truncate for preview

        # Location
        location = None
        location_str = component.get("LOCATION")
        if location_str:
            location = LiteLocation(display_name=str(location_str))

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
            is_organizer = (organizer_str == user_email)
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

        # Convert RECURRENCE-ID to string properly (fix for icalendar object bug)
        if recurrence_id_raw is not None:
            if hasattr(recurrence_id_raw, "to_ical"):
                # icalendar object - convert to iCal format then decode
                recurrence_id = recurrence_id_raw.to_ical().decode("utf-8")
            else:
                # Already a string or other type - convert to string
                recurrence_id = str(recurrence_id_raw)
        else:
            recurrence_id = None

        # Check if this event should be excluded due to EXDATE
        # Use the defensive collector to handle getall(), dict-like access, and param-preserving props
        exdate_props = self._collect_exdate_props(component)
        if not isinstance(exdate_props, list):
            exdate_props = [exdate_props] if exdate_props else []

        return {
            "is_recurring": is_recurring,
            "recurrence_id": recurrence_id,
            "rrule_prop": rrule_prop,
            "exdate_props": exdate_props,
        }
