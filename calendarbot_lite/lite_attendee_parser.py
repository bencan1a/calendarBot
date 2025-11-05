"""Attendee parsing utilities for ICS calendar processing - CalendarBot Lite.

This module provides parsing of ATTENDEE properties from iCalendar components.
Extracted from lite_parser.py to improve modularity and testability.
"""

import logging
from typing import Any, Optional

from .lite_models import LiteAttendee, LiteAttendeeType, LiteResponseStatus

logger = logging.getLogger(__name__)


class LiteAttendeeParser:
    """Parser for iCalendar ATTENDEE properties."""

    def parse_attendee(self, attendee_prop: Any) -> Optional[LiteAttendee]:
        """Parse attendee from iCalendar property.

        Args:
            attendee_prop: iCalendar ATTENDEE property

        Returns:
            Parsed LiteAttendee or None
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
            attendee_type = LiteAttendeeType.REQUIRED
            if role == "OPT-PARTICIPANT":
                attendee_type = LiteAttendeeType.OPTIONAL
            elif role == "NON-PARTICIPANT":
                attendee_type = LiteAttendeeType.RESOURCE

            # Response status
            partstat = params.get("PARTSTAT", "NEEDS-ACTION")
            response_status = LiteResponseStatus.NOT_RESPONDED

            status_map = {
                "ACCEPTED": LiteResponseStatus.ACCEPTED,
                "DECLINED": LiteResponseStatus.DECLINED,
                "TENTATIVE": LiteResponseStatus.TENTATIVELY_ACCEPTED,
                "DELEGATED": LiteResponseStatus.NOT_RESPONDED,
                "NEEDS-ACTION": LiteResponseStatus.NOT_RESPONDED,
            }

            response_status = status_map.get(partstat, LiteResponseStatus.NOT_RESPONDED)

            return LiteAttendee(
                name=name,
                email=email,
                type=attendee_type,
                response_status=response_status,
            )

        except Exception as e:
            logger.debug("Failed to parse attendee: %s", e)
            return None

    def parse_attendees(self, component: Any) -> list[LiteAttendee]:
        """Parse all attendees from an iCalendar component.

        Args:
            component: iCalendar component (e.g., VEVENT)

        Returns:
            List of parsed LiteAttendee objects
        """
        attendees = []

        # Parse attendees
        attendee_props = component.get("ATTENDEE", [])

        # Ensure attendee_props is a list
        if not isinstance(attendee_props, list):
            attendee_props = [attendee_props] if attendee_props else []

        for attendee_prop in attendee_props:
            # Handle nested lists (some ICS formats have this)
            attendee_list = attendee_prop if isinstance(attendee_prop, list) else [attendee_prop]

            for att in attendee_list:
                attendee = self.parse_attendee(att)
                if attendee:
                    attendees.append(attendee)

        return attendees
