"""TypedDict definitions for Alexa response structures.

This module provides type-safe dictionary structures for Alexa endpoint responses,
replacing generic dicts and eliminating the need for # type: ignore comments.
"""

from typing import Optional, TypedDict

# Meeting Information Types

class AlexaMeetingInfo(TypedDict, total=False):
    """Information about a single meeting for Alexa responses.

    Attributes:
        subject: Meeting title/subject
        start_iso: ISO 8601 formatted start time
        seconds_until_start: Seconds from now until meeting starts
        duration_spoken: Human-readable duration string (e.g., "in 5 minutes")
        location: Meeting location or join URL
        is_online_meeting: Whether this is an online/virtual meeting
        speech_text: Pre-formatted speech text for this meeting
        ssml: Optional SSML markup for enhanced speech
    """

    subject: str
    start_iso: str
    seconds_until_start: int
    duration_spoken: str
    location: str
    is_online_meeting: bool
    speech_text: str
    ssml: Optional[str]


# Response Types

class AlexaNextMeetingResponse(TypedDict, total=False):
    """Response structure for /api/alexa/next-meeting endpoint.

    Attributes:
        meeting: Meeting information (None if no upcoming meetings)
        speech_text: Plain text response for Alexa
        ssml: Optional SSML markup
        card: Optional Alexa card data
    """

    meeting: Optional[AlexaMeetingInfo]
    speech_text: str
    ssml: Optional[str]
    card: Optional[dict[str, str]]


class AlexaTimeUntilResponse(TypedDict, total=False):
    """Response structure for /api/alexa/time-until-next endpoint.

    Attributes:
        seconds_until_start: Seconds until next meeting (None if no meetings)
        duration_spoken: Human-readable duration
        speech_text: Plain text response for Alexa
        ssml: Optional SSML markup
    """

    seconds_until_start: Optional[int]
    duration_spoken: str
    speech_text: str
    ssml: Optional[str]


class _AlexaDoneForDayInfoRequired(TypedDict):
    """Required fields for AlexaDoneForDayInfo."""
    has_meetings_today: bool
    last_meeting_start_iso: Optional[str]
    last_meeting_end_iso: Optional[str]
    last_meeting_end_local_iso: Optional[str]


class AlexaDoneForDayInfo(_AlexaDoneForDayInfoRequired, total=False):
    """Done-for-day calculation results.

    Attributes:
        has_meetings_today: Whether user has any meetings today
        last_meeting_start_iso: ISO time of last meeting start (None if no meetings)
        last_meeting_end_iso: ISO time of last meeting end (None if no meetings)
        last_meeting_end_local_iso: Local timezone ISO time of last meeting end
        note: Optional notes or warnings
    """
    note: Optional[str]


class AlexaDoneForDayResponse(TypedDict, total=False):
    """Response structure for /api/alexa/done-for-day endpoint.

    Attributes:
        now_iso: Current time in ISO format
        tz: Timezone used for calculations
        has_meetings_today: Whether user has meetings today
        last_meeting_start_iso: Start time of last meeting
        last_meeting_end_iso: End time of last meeting
        last_meeting_end_local_iso: Local time for last meeting end
        speech_text: Plain text response
        ssml: Optional SSML markup
        card: Optional Alexa card data
        note: Optional notes
    """

    now_iso: str
    tz: Optional[str]
    has_meetings_today: bool
    last_meeting_start_iso: Optional[str]
    last_meeting_end_iso: Optional[str]
    last_meeting_end_local_iso: Optional[str]
    speech_text: str
    ssml: Optional[str]
    card: Optional[dict[str, str]]
    note: Optional[str]


class AlexaLaunchSummaryResponse(TypedDict, total=False):
    """Response structure for /api/alexa/launch-summary endpoint.

    Attributes:
        speech_text: Plain text response
        has_meetings_today: Whether user has meetings today
        next_meeting: Information about next meeting (None if no meetings)
        done_for_day: Done-for-day calculation results
        ssml: Optional SSML markup
    """

    speech_text: str
    has_meetings_today: bool
    next_meeting: Optional[AlexaMeetingInfo]
    done_for_day: AlexaDoneForDayInfo
    ssml: Optional[str]


class AlexaMorningSummaryMetadata(TypedDict, total=False):
    """Metadata for morning summary response.

    Attributes:
        preview_for: What the summary is for (e.g., "tomorrow_morning")
        total_meetings_equivalent: Total equivalent meeting time
        early_start_flag: Whether day starts early
        density: Meeting density indicator
        back_to_back_count: Number of back-to-back meetings
        timeframe_start: Start of analyzed timeframe
        timeframe_end: End of analyzed timeframe
        wake_up_recommendation: Recommended wake-up time (None if not applicable)
    """

    preview_for: str
    total_meetings_equivalent: float
    early_start_flag: bool
    density: str
    back_to_back_count: int
    timeframe_start: str
    timeframe_end: str
    wake_up_recommendation: Optional[str]


class AlexaMorningSummaryResponse(TypedDict, total=False):
    """Response structure for /api/alexa/morning-summary endpoint.

    Attributes:
        speech_text: Plain text summary
        summary: Summary metadata
        ssml: Optional SSML markup
        error: Optional error message
    """

    speech_text: str
    summary: AlexaMorningSummaryMetadata
    ssml: Optional[str]
    error: Optional[str]
