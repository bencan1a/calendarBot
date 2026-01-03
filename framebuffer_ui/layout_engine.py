"""Layout engine for transforming API data into visual layout.

This module converts the /api/whats-next JSON response into a structured
layout format suitable for rendering by the pygame renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


@dataclass
class CountdownDisplay:
    """Countdown section display data (Zone 1)."""

    label: str  # "STARTS IN"
    value: int  # Main number to display
    primary_unit: str  # "HOURS" or "MINUTES"
    secondary: str  # Secondary unit text (e.g., "58 MINUTES")
    state: Literal["normal", "warning", "critical"]  # Visual state


@dataclass
class MeetingDisplay:
    """Meeting card display data (Zone 2)."""

    title: str  # Meeting subject
    time: str  # Formatted time range (e.g., "07:00 AM - 08:00 AM")
    location: str  # Meeting location (empty string if none)


@dataclass
class StatusDisplay:
    """Bottom status display data (Zone 3)."""

    message: str  # Status message
    is_urgent: bool  # Whether to apply urgent styling
    is_critical: bool  # Whether to apply critical styling


@dataclass
class LayoutData:
    """Complete layout data for all zones."""

    countdown: CountdownDisplay | None
    meeting: MeetingDisplay | None
    status: StatusDisplay | None
    has_data: bool  # Whether we have valid meeting data


class LayoutEngine:
    """Convert API response data to visual layout.

    Transforms the JSON response from /api/whats-next into structured
    display data for each of the 3 zones.
    """

    def process(self, api_data: dict[str, Any]) -> LayoutData:
        """Process API response into layout data.

        Args:
            api_data: JSON response from /api/whats-next endpoint

        Returns:
            LayoutData with display data for all zones
        """
        # Check if we have meeting data
        meeting_data = api_data.get("meeting")

        if not meeting_data:
            return self._create_no_meeting_layout()

        # Extract meeting fields
        subject = meeting_data.get("subject", "No meeting")
        start_iso = meeting_data.get("start_iso")
        duration_seconds = meeting_data.get("duration_seconds", 0)
        location = meeting_data.get("location", "")
        seconds_until_start = meeting_data.get("seconds_until_start", 0)

        # Calculate countdown display
        countdown = self._calculate_countdown(seconds_until_start)

        # Format meeting time range
        meeting_time = self._format_meeting_time(start_iso, duration_seconds)

        # Create meeting display
        meeting = MeetingDisplay(
            title=subject, time=meeting_time, location=location
        )

        # Calculate status display
        status = self._calculate_status(seconds_until_start, duration_seconds)

        return LayoutData(
            countdown=countdown, meeting=meeting, status=status, has_data=True
        )

    def _calculate_countdown(self, seconds_until: int) -> CountdownDisplay:
        """Calculate countdown display from seconds until start.

        Args:
            seconds_until: Seconds until meeting starts

        Returns:
            CountdownDisplay with formatted countdown data
        """
        hours = seconds_until // 3600
        minutes = (seconds_until % 3600) // 60

        # Determine primary value and unit
        if hours > 0:
            value = hours
            primary_unit = "HOURS"
            secondary = f"{minutes} MINUTES" if minutes > 0 else ""
        else:
            value = max(0, minutes)  # Never show negative minutes
            primary_unit = "MINUTES"
            secondary = ""

        # Determine visual state
        if seconds_until < 300:  # Less than 5 minutes
            state = "critical"
        elif seconds_until < 900:  # Less than 15 minutes
            state = "warning"
        else:
            state = "normal"

        return CountdownDisplay(
            label="STARTS IN",
            value=value,
            primary_unit=primary_unit,
            secondary=secondary,
            state=state,
        )

    def _format_meeting_time(
        self, start_iso: str | None, duration_seconds: int
    ) -> str:
        """Format meeting time range.

        Args:
            start_iso: ISO 8601 start time
            duration_seconds: Meeting duration in seconds

        Returns:
            Formatted time range (e.g., "07:00 AM - 08:00 AM")
        """
        if not start_iso:
            return ""

        try:
            start_time = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            end_time = start_time.replace(
                second=start_time.second + duration_seconds
            )

            # Format as 12-hour time with AM/PM
            start_str = start_time.strftime("%I:%M %p").lstrip("0")
            end_str = end_time.strftime("%I:%M %p").lstrip("0")

            return f"{start_str} - {end_str}"
        except (ValueError, AttributeError):
            return ""

    def _calculate_status(
        self, seconds_until: int, duration_seconds: int
    ) -> StatusDisplay:
        """Calculate bottom status display.

        Args:
            seconds_until: Seconds until meeting starts
            duration_seconds: Meeting duration in seconds

        Returns:
            StatusDisplay with message and urgency flags
        """
        minutes_until = seconds_until // 60

        # Determine message and urgency based on time
        if seconds_until <= 0:
            # Meeting is happening now or has started
            seconds_since_start = abs(seconds_until)

            if seconds_since_start < duration_seconds:
                # Meeting in progress
                remaining_seconds = duration_seconds - seconds_since_start
                remaining_minutes = remaining_seconds // 60

                if remaining_minutes > 0:
                    message = f"Meeting in progress - {remaining_minutes}m remaining"
                else:
                    message = "Meeting in progress - ending soon"

                return StatusDisplay(
                    message=message, is_urgent=True, is_critical=False
                )
            else:
                # Meeting ended
                return StatusDisplay(
                    message="Meeting ended", is_urgent=False, is_critical=False
                )

        elif minutes_until <= 2:
            # Starting very soon
            return StatusDisplay(
                message=f"Starting very soon - {minutes_until}m",
                is_urgent=True,
                is_critical=True,
            )

        elif minutes_until <= 15:
            # Starting soon
            return StatusDisplay(
                message=f"Starting soon - {minutes_until}m",
                is_urgent=True,
                is_critical=False,
            )

        elif minutes_until <= 60:
            # Starting within the hour
            return StatusDisplay(
                message=f"Starting within the hour - {minutes_until}m",
                is_urgent=False,
                is_critical=False,
            )

        else:
            # Plenty of time
            hours = minutes_until // 60
            remaining_minutes = minutes_until % 60

            if hours < 24:
                if remaining_minutes == 0:
                    message = f"Plenty of time - {hours}h"
                else:
                    message = f"Plenty of time - {hours}h {remaining_minutes}m"
            else:
                days = hours // 24
                message = f"Next meeting in {days}d"

            return StatusDisplay(
                message=message, is_urgent=False, is_critical=False
            )

    def _create_no_meeting_layout(self) -> LayoutData:
        """Create layout for when there are no meetings.

        Returns:
            LayoutData for no-meeting state
        """
        countdown = CountdownDisplay(
            label="MEETINGS",
            value=0,
            primary_unit="SCHEDULED",
            secondary="",
            state="normal",
        )

        meeting = MeetingDisplay(
            title="No upcoming meetings", time="", location=""
        )

        status = StatusDisplay(
            message="No meetings scheduled", is_urgent=False, is_critical=False
        )

        return LayoutData(
            countdown=countdown, meeting=meeting, status=status, has_data=False
        )
