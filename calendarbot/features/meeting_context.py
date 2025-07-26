"""Meeting context preparation and analysis features."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from ..ics.models import CalendarEvent, EventStatus
from ..utils.logging import get_logger
from ..utils.helpers import get_timezone_aware_now

logger = get_logger(__name__)


class MeetingContextAnalyzer:
    """Analyzes calendar events to provide meeting context and preparation insights."""

    def __init__(self, preparation_buffer_minutes: int = 15) -> None:
        """
        Initialize meeting context analyzer.

        Args:
            preparation_buffer_minutes: Minutes before meeting to consider for preparation
        """
        self.preparation_buffer = timedelta(minutes=preparation_buffer_minutes)
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        logger.info(
            f"Meeting context analyzer initialized with {preparation_buffer_minutes}min buffer"
        )

    def analyze_upcoming_meetings(
        self, events: List[CalendarEvent], current_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze upcoming meetings and provide context insights.

        Args:
            events: List of calendar events to analyze
            current_time: Current time for analysis (defaults to now)

        Returns:
            List of meeting context insights with preparation recommendations

        Raises:
            ValueError: If events list is empty or contains invalid data
        """
        if not events:
            raise ValueError("Events list cannot be empty")

        if current_time is None:
            current_time = get_timezone_aware_now()
            logger.debug(
                f"Using timezone-aware current time: {current_time} (tz: {current_time.tzinfo})"
            )

        try:
            upcoming_meetings = self._filter_upcoming_meetings(events, current_time)
            context_insights = []

            for meeting in upcoming_meetings:
                insight = self._generate_meeting_insight(meeting, current_time)
                if insight:
                    context_insights.append(insight)

            logger.info(f"Generated {len(context_insights)} meeting insights")
            return context_insights

        except Exception as e:
            logger.error(f"Error analyzing meetings: {e}")
            raise

    def _filter_upcoming_meetings(
        self, events: List[CalendarEvent], current_time: datetime
    ) -> List[CalendarEvent]:
        """
        Filter events to only upcoming meetings within preparation window.

        Args:
            events: All calendar events
            current_time: Current timestamp

        Returns:
            Filtered list of upcoming meetings requiring preparation
        """
        cutoff_time = current_time + timedelta(hours=24)  # Look ahead 24 hours
        upcoming = []

        for event in events:
            if (
                event.start.date_time > current_time
                and event.start.date_time <= cutoff_time
                and event.is_busy_status
                and not event.is_cancelled
            ):
                upcoming.append(event)

        # Sort by start time
        upcoming.sort(key=lambda e: e.start.date_time)
        return upcoming

    def _generate_meeting_insight(
        self, meeting: CalendarEvent, current_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Generate context insight for a specific meeting.

        Args:
            meeting: Calendar event to analyze
            current_time: Current timestamp

        Returns:
            Meeting insight dictionary or None if not applicable
        """
        try:
            time_until_meeting = meeting.start.date_time - current_time

            # Skip if meeting is too far in future for immediate context
            if time_until_meeting > timedelta(hours=4):
                return None

            preparation_needed = time_until_meeting <= self.preparation_buffer

            insight = {
                "meeting_id": meeting.id,
                "subject": meeting.subject,
                "start_time": meeting.start.date_time.isoformat(),
                "time_until_meeting_minutes": int(time_until_meeting.total_seconds() / 60),
                "preparation_needed": preparation_needed,
                "meeting_type": self._classify_meeting_type(meeting),
                "attendee_count": len(meeting.attendees) if meeting.attendees else 0,
                "has_location": meeting.location is not None,
                "is_online": meeting.is_online_meeting,
                "preparation_recommendations": self._generate_preparation_recommendations(meeting),
            }

            return insight

        except Exception as e:
            logger.warning(f"Could not generate insight for meeting {meeting.id}: {e}")
            return None

    def _classify_meeting_type(self, meeting: CalendarEvent) -> str:
        """
        Classify meeting type based on event characteristics.

        Args:
            meeting: Calendar event to classify

        Returns:
            Meeting type classification string
        """
        subject_lower = meeting.subject.lower()

        # Check for common meeting patterns
        if any(word in subject_lower for word in ["1:1", "one-on-one", "sync"]):
            return "one_on_one"
        elif any(word in subject_lower for word in ["standup", "daily", "scrum"]):
            return "standup"
        elif any(word in subject_lower for word in ["review", "retrospective", "demo"]):
            return "review"
        elif any(word in subject_lower for word in ["interview", "candidate"]):
            return "interview"
        elif meeting.attendees and len(meeting.attendees) > 5:
            return "large_group"
        elif meeting.is_online_meeting:
            return "virtual"
        else:
            return "standard"

    def _generate_preparation_recommendations(self, meeting: CalendarEvent) -> List[str]:
        """
        Generate preparation recommendations based on meeting characteristics.

        Args:
            meeting: Calendar event to analyze

        Returns:
            List of preparation recommendation strings
        """
        recommendations = []

        meeting_type = self._classify_meeting_type(meeting)

        if meeting_type == "interview":
            recommendations.extend(
                [
                    "Review candidate resume and background",
                    "Prepare interview questions",
                    "Test video conference setup",
                ]
            )
        elif meeting_type == "review":
            recommendations.extend(
                [
                    "Gather status updates and metrics",
                    "Prepare presentation materials",
                    "Review previous action items",
                ]
            )
        elif meeting_type == "one_on_one":
            recommendations.extend(
                [
                    "Review recent team updates",
                    "Prepare discussion topics",
                    "Check for any blockers to discuss",
                ]
            )
        elif meeting_type == "standup":
            recommendations.extend(
                ["Prepare status update", "Identify any blockers", "Review sprint progress"]
            )

        # Universal recommendations
        if meeting.is_online_meeting:
            recommendations.append("Test audio/video setup")

        if meeting.location and not meeting.is_online_meeting:
            recommendations.append("Check travel time to location")

        if meeting.attendees and len(meeting.attendees) > 3:
            recommendations.append("Review attendee list and roles")

        return recommendations


async def get_meeting_context_for_timeframe(
    events: List[CalendarEvent], hours_ahead: int = 4
) -> Dict[str, Any]:
    """
    Get comprehensive meeting context for a specified timeframe.

    Args:
        events: List of calendar events to analyze
        hours_ahead: Hours to look ahead for meeting analysis

    Returns:
        Dictionary containing meeting context summary and insights

    Raises:
        ValueError: If hours_ahead is negative or events is empty
    """
    if hours_ahead < 0:
        raise ValueError("hours_ahead must be non-negative")

    if not events:
        raise ValueError("Events list cannot be empty")

    try:
        current_time = get_timezone_aware_now()
        logger.debug(
            f"Using timezone-aware current time for context analysis: {current_time} (tz: {current_time.tzinfo})"
        )
        analyzer = MeetingContextAnalyzer()

        # Filter events within timeframe
        cutoff_time = current_time + timedelta(hours=hours_ahead)
        relevant_events = [
            event
            for event in events
            if (current_time <= event.start.date_time <= cutoff_time and not event.is_cancelled)
        ]

        insights = analyzer.analyze_upcoming_meetings(relevant_events, current_time)

        # Generate summary statistics
        total_meetings = len(insights)
        meetings_needing_prep = len([i for i in insights if i["preparation_needed"]])
        online_meetings = len([i for i in insights if i["is_online"]])

        context_summary = {
            "timeframe_hours": hours_ahead,
            "analysis_time": current_time.isoformat(),
            "total_meetings": total_meetings,
            "meetings_needing_preparation": meetings_needing_prep,
            "online_meetings": online_meetings,
            "meeting_insights": insights,
            "next_meeting": insights[0] if insights else None,
        }

        logger.info(
            f"Generated meeting context for {total_meetings} meetings in next {hours_ahead}h"
        )
        return context_summary

    except Exception as e:
        logger.error(f"Error generating meeting context: {e}")
        raise


def calculate_preparation_time_needed(meeting_type: str, attendee_count: int) -> int:
    """
    Calculate recommended preparation time in minutes based on meeting characteristics.

    Args:
        meeting_type: Type of meeting (from _classify_meeting_type)
        attendee_count: Number of attendees

    Returns:
        Recommended preparation time in minutes

    Raises:
        ValueError: If attendee_count is negative
    """
    if attendee_count < 0:
        raise ValueError("Attendee count cannot be negative")

    # Base preparation time by meeting type
    base_times = {
        "interview": 30,
        "review": 20,
        "one_on_one": 5,
        "standup": 2,
        "large_group": 15,
        "virtual": 10,
        "standard": 10,
    }

    base_time = base_times.get(meeting_type, 10)

    # Add time based on attendee count
    if attendee_count > 5:
        base_time += min(attendee_count - 5, 10)  # Max 10 extra minutes

    return base_time
