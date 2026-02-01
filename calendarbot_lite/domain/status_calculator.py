"""Status message calculation for meeting displays.

This module provides a single source of truth for calculating the status
message shown in the bottom section of both the HTML and framebuffer UIs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StatusInfo:
    """Status information for meeting display."""

    message: str
    is_urgent: bool
    is_critical: bool


def calculate_status(seconds_until_start: int, duration_seconds: int) -> StatusInfo:
    """Calculate status message based on time until meeting.

    This is the single source of truth for status message logic used by
    both the HTML interface and framebuffer UI.

    Args:
        seconds_until_start: Seconds until meeting starts (negative if started)
        duration_seconds: Meeting duration in seconds

    Returns:
        StatusInfo with message and urgency flags
    """
    minutes_until = seconds_until_start // 60

    if seconds_until_start <= 0:
        # Meeting is happening now or has started
        seconds_since_start = abs(seconds_until_start)

        if seconds_since_start < duration_seconds:
            # Meeting in progress
            return StatusInfo(
                message="Meeting in progress",
                is_urgent=True,
                is_critical=False,
            )
        # Meeting ended
        return StatusInfo(
            message="Meeting ended",
            is_urgent=False,
            is_critical=False,
        )

    if minutes_until <= 2:
        # Starting very soon
        return StatusInfo(
            message="Starting very soon",
            is_urgent=True,
            is_critical=True,
        )

    if minutes_until <= 15:
        # Starting soon
        return StatusInfo(
            message="Starting soon",
            is_urgent=True,
            is_critical=False,
        )

    if minutes_until <= 60:
        # Starting within the hour
        return StatusInfo(
            message="Starting within the hour",
            is_urgent=False,
            is_critical=False,
        )

    # Plenty of time (more than 60 minutes away)
    return StatusInfo(
        message="Plenty of time",
        is_urgent=False,
        is_critical=False,
    )
