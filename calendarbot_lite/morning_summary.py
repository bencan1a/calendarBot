"""Morning summary logic service for CalendarBot's Alexa integration.

This module implements the core morning summary functionality for CalendarBot Lite,
providing analysis of tomorrow morning's calendar events (6 AM to 12 PM) with
natural language speech generation for Alexa delivery.

All user stories from the Morning Summary Feature specification are implemented:
- Basic Morning Summary Generation (Story 1)
- Early Start Detection and Wake-up Recommendations (Story 2)
- Free Time Block Analysis (Story 3)
- Morning Schedule Density Classification (Story 4)
- Natural Language Response Generation (Story 5)
- All-Day Event Handling (Story 6)
- No Meetings Scenario (Story 7)
- Performance and Reliability (Story 8)
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .lite_models import LiteCalendarEvent
from .server import _now_utc

logger = logging.getLogger(__name__)

# Performance constants (Story 8)
MAX_EVENTS_LIMIT = 50
PERFORMANCE_TARGET_SECONDS = 3.0
MEMORY_TARGET_MB = 100
CACHE_TTL_SECONDS = 300  # 5 minutes

# Morning window constants (Story 1)
MORNING_START_HOUR = 6
MORNING_END_HOUR = 12

# Early start thresholds (Story 2)
EARLY_START_THRESHOLD_HOUR = 8
VERY_EARLY_THRESHOLD_HOUR = 7
VERY_EARLY_THRESHOLD_MINUTE = 30
WAKE_UP_BUFFER_MINUTES = 90
MIN_WAKE_UP_HOUR = 6

# Free time analysis constants (Story 3)
MIN_FREE_BLOCK_MINUTES = 30
SIGNIFICANT_FREE_BLOCK_MINUTES = 45
BACK_TO_BACK_GAP_MINUTES = 15

# Focus Time keywords for detection (Stories 3&4)
FOCUS_TIME_KEYWORDS = ["focus time", "focus", "deep work", "thinking time", "planning time"]


class DensityLevel(str, Enum):
    """Morning schedule density classification (Story 4)."""

    LIGHT = "light"
    MODERATE = "moderate"
    BUSY = "busy"


class MorningSummaryRequest(BaseModel):
    """Request for morning summary generation."""

    date: Optional[str] = Field(
        default=None, description="ISO date for summary (defaults to tomorrow)"
    )
    timezone: str = Field(default="UTC", description="IANA timezone identifier")
    detail_level: str = Field(default="normal", description="Detail level: brief|normal|detailed")
    prefer_ssml: bool = Field(default=False, description="Prefer SSML response if available")
    max_events: int = Field(default=50, description="Maximum events to process")

    @field_validator("max_events")
    @classmethod
    def clamp_max_events(cls, v: int) -> int:
        """Clamp max_events to performance limit (Story 8)."""
        return min(v, MAX_EVENTS_LIMIT)

    model_config = ConfigDict(use_enum_values=True)


class FreeBlock(BaseModel):
    """Free time block information (Story 3)."""

    start_time: datetime = Field(..., description="Block start time")
    end_time: datetime = Field(..., description="Block end time")
    duration_minutes: int = Field(..., description="Duration in minutes")
    recommended_action: Optional[str] = Field(
        default=None, description="Suggested use for this time block"
    )

    @property
    def is_significant(self) -> bool:
        """Check if this is a significant free block (45+ minutes)."""
        return self.duration_minutes >= SIGNIFICANT_FREE_BLOCK_MINUTES

    def get_spoken_duration(self) -> str:
        """Get conversational duration text (Story 5)."""
        if self.duration_minutes < 60:
            return f"{self.duration_minutes}-minute"
        if self.duration_minutes == 60:
            return "one-hour"
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if minutes == 0:
            return f"{hours}-hour"
        return f"{hours}-hour {minutes}-minute"

    def get_spoken_start_time(self) -> str:
        """Get conversational start time (Story 5)."""
        hour = self.start_time.hour
        minute = self.start_time.minute

        if minute == 0:
            if hour == 12:
                return "noon"
            if hour > 12:
                return f"{hour - 12} PM"
            return f"{hour} AM"
        if minute == 30:
            if hour == 12:
                return "twelve thirty PM"
            if hour > 12:
                return f"{hour - 12} thirty PM"
            return f"{hour} thirty AM"
        if hour == 12:
            return f"twelve {minute:02d} PM"
        if hour > 12:
            return f"{hour - 12} {minute:02d} PM"
        return f"{hour} {minute:02d} AM"


class MeetingInsight(BaseModel):
    """Meeting insight information."""

    meeting_id: str = Field(..., description="Meeting identifier")
    subject: str = Field(..., description="Meeting subject")
    start_time: datetime = Field(..., description="Meeting start time")
    end_time: datetime = Field(..., description="Meeting end time")
    time_until_minutes: Optional[int] = Field(
        default=None, description="Minutes until meeting starts"
    )
    preparation_needed: bool = Field(default=False, description="Meeting needs preparation")
    is_online: bool = Field(default=False, description="Online meeting flag")
    attendees_count: Optional[int] = Field(default=None, description="Number of attendees")
    short_note: Optional[str] = Field(default=None, description="Brief meeting note")

    def get_short_subject(self) -> str:
        """Get shortened subject for speech (Story 5)."""
        words = self.subject.split()
        if len(words) <= 6:
            return self.subject
        return " ".join(words[:6])

    def get_spoken_start_time(self) -> str:
        """Get conversational start time (Story 5)."""
        hour = self.start_time.hour
        minute = self.start_time.minute

        if minute == 0:
            if hour == 12:
                return "noon"
            if hour > 12:
                return f"{hour - 12} PM"
            return f"{hour} AM"
        if minute == 30:
            if hour == 12:
                return "twelve thirty PM"
            if hour > 12:
                return f"{hour - 12} thirty PM"
            return f"{hour} thirty AM"
        if hour == 12:
            return f"twelve {minute:02d} PM"
        if hour > 12:
            return f"{hour - 12} {minute:02d} PM"
        return f"{hour} {minute:02d} AM"


class MorningSummaryResult(BaseModel):
    """Result of morning summary analysis."""

    # Time frame (Story 1)
    timeframe_start: datetime = Field(..., description="Summary window start (06:00 local)")
    timeframe_end: datetime = Field(..., description="Summary window end (12:00 local)")
    analysis_time: datetime = Field(default_factory=_now_utc, description="Analysis timestamp")

    # Core metrics (Stories 1&4)
    total_meetings_equivalent: float = Field(
        ..., description="Total meeting equivalents (all-day = 0.5)"
    )
    early_start_flag: bool = Field(..., description="Has meetings before 8:00 AM")
    density: DensityLevel = Field(..., description="Schedule density classification")

    # Analysis results (Stories 2&3)
    meeting_insights: list[MeetingInsight] = Field(
        default_factory=list, description="Meeting analysis details"
    )
    free_blocks: list[FreeBlock] = Field(default_factory=list, description="Free time blocks")
    back_to_back_count: int = Field(default=0, description="Number of back-to-back meetings")

    # Speech output (Story 5)
    speech_text: str = Field(..., description="Natural language summary for evening delivery")
    ssml: Optional[str] = Field(default=None, description="SSML formatted speech")

    # Metadata (Architecture requirement)
    metadata: dict[str, Any] = Field(
        default_factory=lambda: {
            "preview_for": "tomorrow_morning",
            "generation_context": {
                "delivery_time": "evening",
                "reference_day": "tomorrow",
            },
        },
        description="Summary metadata",
    )

    @property
    def wake_up_recommendation_time(self) -> Optional[datetime]:
        """Get recommended wake-up time (Story 2)."""
        if not self.early_start_flag or not self.meeting_insights:
            return None

        # Find earliest non-cancelled, non-all-day meeting
        earliest_meeting = None
        for meeting in self.meeting_insights:
            if earliest_meeting is None or meeting.start_time < earliest_meeting.start_time:
                earliest_meeting = meeting

        if earliest_meeting is None:
            return None

        # Calculate wake-up time (90 minutes before, minimum 6:00 AM)
        wake_up_time = earliest_meeting.start_time - timedelta(minutes=WAKE_UP_BUFFER_MINUTES)
        
        # Create minimum wake-up time for the same date as the meeting
        min_wake_up = earliest_meeting.start_time.replace(
            hour=MIN_WAKE_UP_HOUR, minute=0, second=0, microsecond=0
        )

        return max(wake_up_time, min_wake_up)

    @property
    def longest_free_block(self) -> Optional[FreeBlock]:
        """Get longest continuous free time block (Story 3)."""
        if not self.free_blocks:
            return None
        return max(self.free_blocks, key=lambda fb: fb.duration_minutes)

    model_config = ConfigDict(use_enum_values=True)


class MorningSummaryService:
    """Core morning summary generation service.

    Implements all user stories for morning summary functionality with
    performance optimization and caching (Story 8).
    """

    def __init__(self):
        """Initialize the service."""
        self._cache: dict[str, tuple[MorningSummaryResult, float]] = {}

    async def generate_summary(
        self,
        events: list[LiteCalendarEvent],
        request: MorningSummaryRequest,
    ) -> MorningSummaryResult:
        """Generate morning summary from calendar events.

        Args:
            events: List of calendar events to analyze
            request: Summary generation request parameters

        Returns:
            Complete morning summary analysis and speech text

        Raises:
            ValueError: If invalid request parameters
            Exception: If performance targets cannot be met (Story 8)
        """
        start_time = time.time()

        try:
            # Validate inputs
            if not isinstance(events, list):
                raise ValueError("Events must be a list")  # noqa: TRY004, TRY301

            # Performance check (Story 8)
            if len(events) > MAX_EVENTS_LIMIT:
                logger.warning(
                    f"Event count {len(events)} exceeds limit {MAX_EVENTS_LIMIT}, truncating"
                )
                events = events[:MAX_EVENTS_LIMIT]

            # Check cache
            cache_key = self._get_cache_key(events, request)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug("Returning cached morning summary")
                return cached_result

            # Generate tomorrow's date in target timezone
            tomorrow_date = await self._get_tomorrow_date(request.timezone)

            # Create time window (6 AM to 12 PM tomorrow) (Story 1)
            timeframe_start, timeframe_end = self._create_time_window(tomorrow_date, request.timezone)

            # Filter and process events
            filtered_events = self._filter_morning_events(events, timeframe_start, timeframe_end)

            # Generate analysis
            result = await self._analyze_morning_schedule(
                filtered_events, timeframe_start, timeframe_end, request
            )

            # Cache result
            self._cache_result(cache_key, result)

            # Performance validation (Story 8)
            elapsed_time = time.time() - start_time
            if elapsed_time > PERFORMANCE_TARGET_SECONDS:
                logger.warning(
                    f"Summary generation took {elapsed_time:.2f}s, exceeds target {PERFORMANCE_TARGET_SECONDS}s"
                )

            logger.info(f"Generated morning summary in {elapsed_time:.2f}s")
            return result

        except Exception:
            elapsed_time = time.time() - start_time
            logger.exception(f"Morning summary generation failed after {elapsed_time:.2f}s")
            raise

    async def _get_tomorrow_date(self, timezone_str: str) -> datetime:
        """Get tomorrow's date in the target timezone."""
        # Use the server's _now_utc for consistent time handling
        now_utc = _now_utc()

        # Convert to target timezone
        try:
            import zoneinfo  # noqa: PLC0415

            tz = zoneinfo.ZoneInfo(timezone_str)
            now_local = now_utc.astimezone(tz)
            tomorrow = now_local + timedelta(days=1)
            return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception as e:
            logger.warning(f"Timezone conversion failed for {timezone_str}: {e}, using UTC")
            tomorrow = now_utc + timedelta(days=1)
            return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)

    def _create_time_window(
        self, tomorrow_date: datetime, timezone_str: str
    ) -> tuple[datetime, datetime]:
        """Create 6 AM to 12 PM time window for tomorrow (Story 1)."""
        try:
            import zoneinfo  # noqa: PLC0415

            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            tz = timezone.utc

        timeframe_start = tomorrow_date.replace(hour=MORNING_START_HOUR, tzinfo=tz)
        timeframe_end = tomorrow_date.replace(hour=MORNING_END_HOUR, tzinfo=tz)

        return timeframe_start, timeframe_end

    def _filter_morning_events(
        self,
        events: list[LiteCalendarEvent],
        timeframe_start: datetime,
        timeframe_end: datetime,
    ) -> list[LiteCalendarEvent]:
        """Filter events to morning window and remove cancelled/hidden events (Story 2)."""
        filtered_events = []

        for event in events:
            # Skip cancelled events (Story 2)
            if event.is_cancelled:
                continue

            # Skip phantom/hidden events - check for common hidden patterns
            if self._is_hidden_event(event):
                continue

            # Check if event overlaps with morning window
            event_start = event.start.date_time
            event_end = event.end.date_time

            # Convert to UTC for comparison if needed
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)

            # Check overlap with morning window
            if event_start < timeframe_end and event_end > timeframe_start:
                filtered_events.append(event)

        return filtered_events

    def _is_hidden_event(self, event: LiteCalendarEvent) -> bool:
        """Check if event should be hidden from analysis."""
        subject_lower = event.subject.lower()

        # Common hidden event patterns
        hidden_patterns = [
            "busy",
            "free",
            "phantom",
            "hidden",
            "private",
            "personal",
            "birthday",
            "holiday",
            "vacation",
            "out of office",
        ]

        return any(pattern in subject_lower for pattern in hidden_patterns)

    def _is_focus_time(self, event: LiteCalendarEvent) -> bool:
        """Check if event is Focus Time (Stories 3&4)."""
        subject_lower = event.subject.lower()
        return any(keyword in subject_lower for keyword in FOCUS_TIME_KEYWORDS)

    async def _analyze_morning_schedule(
        self,
        events: list[LiteCalendarEvent],
        timeframe_start: datetime,
        timeframe_end: datetime,
        request: MorningSummaryRequest,
    ) -> MorningSummaryResult:
        """Analyze morning schedule and generate insights."""
        # Separate all-day and timed events (Story 6)
        all_day_events = [e for e in events if e.is_all_day]
        timed_events = [e for e in events if not e.is_all_day]

        # Calculate meeting equivalents (Story 4)
        # Focus Time doesn't count, all-day events = 0.5
        meeting_equivalents = 0.0
        actionable_all_day = []

        for event in all_day_events:
            if not self._is_actionable_all_day(event):
                continue
            actionable_all_day.append(event)
            meeting_equivalents += 0.5

        for event in timed_events:
            if not self._is_focus_time(event):
                meeting_equivalents += 1.0

        # Classify density (Story 4)
        density = self._classify_density(meeting_equivalents)

        # Detect early start (Story 2)
        early_start_flag = self._detect_early_start(timed_events, timeframe_start)

        # Analyze free blocks and back-to-back meetings (Story 3)
        free_blocks = self._analyze_free_blocks(timed_events, timeframe_start, timeframe_end)
        back_to_back_count = self._count_back_to_back_meetings(timed_events)

        # Create meeting insights
        meeting_insights = self._create_meeting_insights(timed_events, timeframe_start)

        # Generate speech text (Story 5)
        speech_text = self._generate_speech_text(
            meeting_insights=meeting_insights,
            all_day_events=actionable_all_day,
            density=density,
            early_start_flag=early_start_flag,
            free_blocks=free_blocks,
            back_to_back_count=back_to_back_count,
            total_meetings=meeting_equivalents,
            has_any_events=(len(events) > 0),  # Pass whether there are any events at all
        )

        return MorningSummaryResult(
            timeframe_start=timeframe_start,
            timeframe_end=timeframe_end,
            total_meetings_equivalent=meeting_equivalents,
            early_start_flag=early_start_flag,
            density=density,
            meeting_insights=meeting_insights,
            free_blocks=free_blocks,
            back_to_back_count=back_to_back_count,
            speech_text=speech_text,
        )

    def _is_actionable_all_day(self, event: LiteCalendarEvent) -> bool:
        """Check if all-day event is actionable (Story 6)."""
        subject_lower = event.subject.lower()

        # Skip holidays, birthdays, and non-actionable events
        non_actionable_patterns = [
            "birthday",
            "holiday",
            "vacation",
            "day off",
            "public holiday",
            "national holiday",
            "anniversary",
        ]

        return not any(pattern in subject_lower for pattern in non_actionable_patterns)

    def _classify_density(self, meeting_equivalents: float) -> DensityLevel:
        """Classify morning schedule density (Story 4)."""
        if meeting_equivalents <= 2:
            return DensityLevel.LIGHT
        if meeting_equivalents <= 4:
            return DensityLevel.MODERATE
        return DensityLevel.BUSY

    def _detect_early_start(
        self, timed_events: list[LiteCalendarEvent], timeframe_start: datetime
    ) -> bool:
        """Detect early start meetings before 8:00 AM (Story 2)."""
        early_threshold = timeframe_start.replace(hour=EARLY_START_THRESHOLD_HOUR)

        for event in timed_events:
            event_start = event.start.date_time
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)

            if event_start < early_threshold:
                return True

        return False

    def _analyze_free_blocks(
        self,
        timed_events: list[LiteCalendarEvent],
        timeframe_start: datetime,
        timeframe_end: datetime,
    ) -> list[FreeBlock]:
        """Analyze free time blocks (Story 3)."""
        if not timed_events:
            # Entire morning is free
            duration_minutes = int((timeframe_end - timeframe_start).total_seconds() / 60)
            return [
                FreeBlock(
                    start_time=timeframe_start,
                    end_time=timeframe_end,
                    duration_minutes=duration_minutes,
                    recommended_action="deep work or personal time",
                )
            ]

        # Sort events by start time
        sorted_events = sorted(timed_events, key=lambda e: e.start.date_time)

        free_blocks = []
        current_time = timeframe_start

        for event in sorted_events:
            event_start = event.start.date_time
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)

            # Skip events that start before current time
            if event_start <= current_time:
                event_end = event.end.date_time
                if event_end.tzinfo is None:
                    event_end = event_end.replace(tzinfo=timezone.utc)
                current_time = max(current_time, event_end)
                continue

            # Check for free block
            gap_minutes = int((event_start - current_time).total_seconds() / 60)
            if gap_minutes >= MIN_FREE_BLOCK_MINUTES:
                recommended_action = None
                if gap_minutes >= SIGNIFICANT_FREE_BLOCK_MINUTES:
                    if gap_minutes >= 120:  # 2+ hours
                        recommended_action = "deep work session"
                    elif gap_minutes >= 90:  # 1.5+ hours
                        recommended_action = "focused project work"
                    else:
                        recommended_action = "planning or preparation"

                free_blocks.append(
                    FreeBlock(
                        start_time=current_time,
                        end_time=event_start,
                        duration_minutes=gap_minutes,
                        recommended_action=recommended_action,
                    )
                )

            # Update current time to end of this event
            event_end = event.end.date_time
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)
            current_time = event_end

        # Check for free time after last event
        if current_time < timeframe_end:
            gap_minutes = int((timeframe_end - current_time).total_seconds() / 60)
            if gap_minutes >= MIN_FREE_BLOCK_MINUTES:
                free_blocks.append(
                    FreeBlock(
                        start_time=current_time,
                        end_time=timeframe_end,
                        duration_minutes=gap_minutes,
                        recommended_action="wrap-up or preparation for afternoon",
                    )
                )

        return free_blocks

    def _count_back_to_back_meetings(self, timed_events: list[LiteCalendarEvent]) -> int:
        """Count back-to-back meetings with less than 15 minutes gap (Story 3)."""
        if len(timed_events) < 2:
            return 0

        sorted_events = sorted(timed_events, key=lambda e: e.start.date_time)
        back_to_back_count = 0

        for i in range(len(sorted_events) - 1):
            current_end = sorted_events[i].end.date_time
            next_start = sorted_events[i + 1].start.date_time

            if current_end.tzinfo is None:
                current_end = current_end.replace(tzinfo=timezone.utc)
            if next_start.tzinfo is None:
                next_start = next_start.replace(tzinfo=timezone.utc)

            gap_minutes = (next_start - current_end).total_seconds() / 60
            if gap_minutes < BACK_TO_BACK_GAP_MINUTES:
                back_to_back_count += 1

        return back_to_back_count

    def _create_meeting_insights(
        self, timed_events: list[LiteCalendarEvent], timeframe_start: datetime
    ) -> list[MeetingInsight]:
        """Create meeting insights from timed events."""
        insights = []

        for event in timed_events:
            # Skip Focus Time events from meeting insights (Stories 3&4)
            if self._is_focus_time(event):
                continue
                
            event_start = event.start.date_time
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)

            # Calculate time until meeting
            time_until_minutes = None
            now = _now_utc()
            if event_start > now:
                time_until_minutes = int((event_start - now).total_seconds() / 60)

            insights.append(
                MeetingInsight(
                    meeting_id=event.id,
                    subject=event.subject,
                    start_time=event_start,
                    end_time=event.end.date_time,
                    time_until_minutes=time_until_minutes,
                    is_online=event.is_online_meeting,
                    attendees_count=len(event.attendees) if event.attendees else None,
                )
            )

        return sorted(insights, key=lambda m: m.start_time)

    def _generate_speech_text(
        self,
        meeting_insights: list[MeetingInsight],
        all_day_events: list[LiteCalendarEvent],
        density: DensityLevel,
        early_start_flag: bool,
        free_blocks: list[FreeBlock],
        back_to_back_count: int,
        total_meetings: float,
        has_any_events: bool = False,
    ) -> str:
        """Generate natural language speech text for evening delivery (Story 5)."""
        # Handle no meetings scenario (Story 7) - truly no events at all
        if not meeting_insights and not all_day_events and not has_any_events:
            return (
                "Good evening. You have a completely free morning tomorrow until noon. "
                "This is a great opportunity for deep work or personal time."
            )

        # Start with evening greeting
        parts = ["Good evening."]

        # Early start handling (Story 2)
        if early_start_flag and meeting_insights:
            earliest_meeting = min(meeting_insights, key=lambda m: m.start_time)
            start_time_spoken = earliest_meeting.get_spoken_start_time()

            if earliest_meeting.start_time.hour < VERY_EARLY_THRESHOLD_HOUR or (
                earliest_meeting.start_time.hour == VERY_EARLY_THRESHOLD_HOUR
                and earliest_meeting.start_time.minute < VERY_EARLY_THRESHOLD_MINUTE
            ):
                parts.append(f"You start very early tomorrow at {start_time_spoken}.")
            else:
                parts.append(f"You start early tomorrow at {start_time_spoken}.")

        # Meeting count and density (Stories 1&4)
        if meeting_insights or total_meetings > 0 or has_any_events:
            meeting_count = len(meeting_insights)
            if total_meetings != meeting_count:  # Include all-day events in count
                if total_meetings == int(total_meetings):
                    total_text = f"{int(total_meetings)} meeting equivalents"
                else:
                    total_text = f"{total_meetings:.1f} meeting equivalents"
            elif meeting_count == 1:
                total_text = "1 meeting"
            elif meeting_count > 1:
                total_text = f"{meeting_count} meetings"
            else:
                total_text = "0 meeting equivalents"

            parts.append(f"You have {total_text} before noon tomorrow.")

            # Add density-based encouragement (Story 4)
            if density == DensityLevel.BUSY:
                parts.append("It's a busy morning, but you've got this.")
            elif density == DensityLevel.LIGHT:
                parts.append("It's a light morning schedule.")

        # Free time and back-to-back information (Story 3)
        longest_block = None
        if free_blocks:
            longest_block = max(free_blocks, key=lambda fb: fb.duration_minutes)

        if back_to_back_count > 0:
            if back_to_back_count == 1:
                parts.append("You have one back-to-back meeting transition.")
            else:
                parts.append(f"You have {back_to_back_count} back-to-back meeting transitions.")

        if longest_block and longest_block.is_significant:
            duration_text = longest_block.get_spoken_duration()
            start_time_text = longest_block.get_spoken_start_time()
            parts.append(f"You have a {duration_text} window starting at {start_time_text}.")

        # First meeting details (if exists and not already mentioned in early start)
        if meeting_insights and not early_start_flag:
            first_meeting = meeting_insights[0]
            subject = first_meeting.get_short_subject()
            start_time = first_meeting.get_spoken_start_time()
            
            if first_meeting.start_time.hour >= MORNING_START_HOUR:
                parts.append(f"Your first meeting is {subject} at {start_time}.")

        # All-day events (Story 6)
        if all_day_events:
            if len(all_day_events) == 1:
                parts.append(f"You also have {all_day_events[0].subject} all day.")
            elif len(all_day_events) <= 3:
                subjects = [event.subject for event in all_day_events[:3]]
                parts.append(f"You also have {', '.join(subjects)} all day.")
            else:
                parts.append("You also have several all-day items.")

        return " ".join(parts)

    def _get_cache_key(self, events: list[LiteCalendarEvent], request: MorningSummaryRequest) -> str:
        """Generate cache key for result caching."""
        # Create a simple hash of event IDs and request parameters
        event_ids = sorted([e.id for e in events])
        key_parts = [
            str(hash(tuple(event_ids))),
            request.date or "tomorrow",
            request.timezone,
            request.detail_level,
        ]
        return "|".join(key_parts)

    def _get_cached_result(self, cache_key: str) -> Optional[MorningSummaryResult]:
        """Get cached result if still valid."""
        if cache_key not in self._cache:
            return None

        result, timestamp = self._cache[cache_key]
        if time.time() - timestamp > CACHE_TTL_SECONDS:
            del self._cache[cache_key]
            return None

        return result

    def _cache_result(self, cache_key: str, result: MorningSummaryResult) -> None:
        """Cache result with TTL."""
        self._cache[cache_key] = (result, time.time())

        # Simple cache cleanup - remove old entries
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > CACHE_TTL_SECONDS
        ]
        for key in expired_keys:
            del self._cache[key]


# Global service instance for use by other modules
_morning_summary_service: Optional[MorningSummaryService] = None


@lru_cache(maxsize=1)
def get_morning_summary_service() -> MorningSummaryService:
    """Get the global morning summary service instance."""
    global _morning_summary_service  # noqa: PLW0603
    if _morning_summary_service is None:
        _morning_summary_service = MorningSummaryService()
    return _morning_summary_service
