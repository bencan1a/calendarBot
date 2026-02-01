"""Layout engine for transforming API data into visual layout.

This module converts the /api/whats-next JSON response into a structured
layout format suitable for rendering by the pygame renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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
            # Use status from API if available, otherwise create default
            status_data = api_data.get("status", {})
            status = StatusDisplay(
                message=status_data.get("message", "No meetings scheduled"),
                is_urgent=status_data.get("is_urgent", False),
                is_critical=status_data.get("is_critical", False),
            )
            return self._create_no_meeting_layout(status)

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
        meeting = MeetingDisplay(title=subject, time=meeting_time, location=location)

        # Use status from API response (single source of truth)
        status_data = api_data.get("status", {})
        status = StatusDisplay(
            message=status_data.get("message", "Next meeting"),
            is_urgent=status_data.get("is_urgent", False),
            is_critical=status_data.get("is_critical", False),
        )

        return LayoutData(countdown=countdown, meeting=meeting, status=status, has_data=True)

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

    def _format_meeting_time(self, start_iso: str | None, duration_seconds: int) -> str:
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
            end_time = start_time + timedelta(seconds=duration_seconds)

            # Convert to local system timezone
            start_local = start_time.astimezone()
            end_local = end_time.astimezone()

            # Format as 12-hour time with AM/PM
            start_str = start_local.strftime("%I:%M %p").lstrip("0")
            end_str = end_local.strftime("%I:%M %p").lstrip("0")

            return f"{start_str} - {end_str}"
        except (ValueError, AttributeError):
            return ""

    def _create_no_meeting_layout(self, status: StatusDisplay | None = None) -> LayoutData:
        """Create layout for when there are no meetings.

        Args:
            status: Optional status from API response

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

        meeting = MeetingDisplay(title="No upcoming meetings", time="", location="")

        if status is None:
            status = StatusDisplay(
                message="No meetings scheduled", is_urgent=False, is_critical=False
            )

        return LayoutData(countdown=countdown, meeting=meeting, status=status, has_data=False)
