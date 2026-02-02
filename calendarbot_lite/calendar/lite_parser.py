"""iCalendar parser with Microsoft Outlook compatibility - CalendarBot Lite version."""

import logging
from datetime import datetime
from typing import Any, Optional, cast

from icalendar import Calendar, Event as ICalEvent

from calendarbot_lite.calendar.lite_attendee_parser import LiteAttendeeParser
from calendarbot_lite.calendar.lite_datetime_utils import LiteDateTimeParser
from calendarbot_lite.calendar.lite_event_merger import LiteEventMerger
from calendarbot_lite.calendar.lite_event_parser import LiteEventComponentParser
from calendarbot_lite.calendar.lite_models import (
    DateTimeWrapper,
    LiteAttendee,
    LiteCalendarEvent,
    LiteICSParseResult,
    SimpleEvent,
)

# Backward compatibility aliases (these classes were previously defined here with underscore prefix)
_SimpleEvent = SimpleEvent
_DateTimeWrapper = DateTimeWrapper
from calendarbot_lite.calendar.lite_rrule_expander import LiteRRuleExpander
from calendarbot_lite.calendar.lite_streaming_parser import (
    MAX_ICS_SIZE_BYTES,
    MAX_ICS_SIZE_WARNING,
    STREAMING_THRESHOLD,
    LiteICSContentTooLargeError,
    LiteStreamingICSParser,
)

logger = logging.getLogger(__name__)

# NOTE: LiteStreamingICSParser has been moved to lite_streaming_parser module
# and is now imported at the top of this file

# NOTE: _ensure_timezone_aware has been moved to lite_datetime_utils module
# and is now imported at the top of this file


def _is_production_mode() -> bool:
    """Simple production mode check for calendarbot_lite."""
    import os

    return os.environ.get("CALENDARBOT_PRODUCTION", "false").lower() in ("true", "1")


class LiteICSParser:
    """iCalendar parser with Microsoft Outlook compatibility - CalendarBot Lite version."""

    def __init__(self, settings: Any) -> None:
        """Initialize ICS parser.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.rrule_expander = LiteRRuleExpander(settings)
        self._streaming_parser = LiteStreamingICSParser()
        self._datetime_parser = LiteDateTimeParser()
        self._attendee_parser = LiteAttendeeParser()
        self._event_parser = LiteEventComponentParser(
            self._datetime_parser, self._attendee_parser, settings
        )
        self._event_merger = LiteEventMerger()

        # Initialize RRULE orchestrator for centralized expansion logic
        from calendarbot_lite.calendar.lite_rrule_expander import RRuleOrchestrator

        self._rrule_orchestrator = RRuleOrchestrator(settings, self._event_parser)

        logger.debug("Lite ICS parser initialized")

    # NOTE: Previously, this class contained several methods for RRULE expansion logic
    # that have been refactored and moved to RRuleOrchestrator for better separation of
    # concerns. The _expand_recurring_events() method now delegates to RRuleOrchestrator.

    def _should_use_streaming(self, ics_content: str) -> bool:
        """Determine if streaming parser should be used based on content size.

        Args:
            ics_content: ICS content to check

        Returns:
            True if streaming should be used, False otherwise

        Raises:
            TypeError: If content is None
            AttributeError: If content doesn't have required string methods
        """
        if ics_content is None:
            raise TypeError("ICS content cannot be None")

        if not hasattr(ics_content, "encode"):
            raise AttributeError("ICS content must be a string with encode method")

        if not ics_content:
            return False

        content_size = len(ics_content.encode("utf-8"))
        return content_size >= STREAMING_THRESHOLD

    def parse_ics_content_optimized(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> LiteICSParseResult:
        """Parse ICS content using optimal method based on size.

        Automatically chooses between streaming (for large files) and
        traditional parsing (for small files) to optimize memory usage.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with events and metadata
        """
        if self._should_use_streaming(ics_content):
            logger.debug(
                "Using streaming parser for large ICS content (%d bytes)", len(ics_content)
            )
            return self._parse_with_streaming(ics_content, source_url)

        logger.debug("Using traditional parser for small ICS content (%d bytes)", len(ics_content))
        return self.parse_ics_content(ics_content, source_url)

    def _parse_with_streaming(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> LiteICSParseResult:
        """Parse ICS content using streaming parser with memory-bounded processing."""
        try:
            # Initialize result tracking - NO event accumulation
            filtered_events: list[LiteCalendarEvent] = []  # Only store final filtered results
            raw_components: list[Any] = []  # Store raw components for RRULE expansion

            # Issue #49: Bounded memory for component superset
            # Track masters (recurring) and non-masters (single events) separately with hard limits
            try:
                max_superset = getattr(self.settings, "raw_components_superset_limit", 1500)
            except Exception:
                max_superset = 1500

            # Split limit: 70% for masters (recurring events), 30% for non-masters (single events)
            # This prioritizes recurring events for RRULE expansion while preventing unbounded growth
            masters_limit = int(max_superset * 0.7)
            nonmasters_limit = int(max_superset * 0.3)

            raw_components_masters: list[Any] = []  # Bounded list of recurring events
            raw_components_nonmasters: list[Any] = []  # Bounded list of non-recurring events

            warnings = []
            errors = []
            total_components = 0
            event_count = 0
            recurring_event_count = 0
            calendar_metadata = {}

            # Memory-bounded processing: limit stored events for typical calendar view usage
            max_stored_events = 1000  # Increased to handle calendars with many recurring events

            # Process stream with immediate filtering to prevent memory accumulation
            for item in self._streaming_parser.parse_stream(ics_content):
                if item["type"] == "event":
                    try:
                        # Parse the iCalendar component using existing logic
                        component = item["component"]
                        calendar_metadata.update(item["metadata"])

                        # Issue #49: Add component to appropriate bounded list
                        # This prevents unbounded memory growth by enforcing hard limits on BOTH
                        # recurring and non-recurring events
                        if bool(component.get("RRULE")):
                            # Recurring event (master with RRULE)
                            raw_components_masters.append(component)
                            # Enforce limit: keep only the most recent masters_limit items
                            if len(raw_components_masters) > masters_limit:
                                # Remove oldest items (FIFO) to stay within limit
                                raw_components_masters = raw_components_masters[-masters_limit:]
                        else:
                            # Non-recurring event (single occurrence)
                            raw_components_nonmasters.append(component)
                            # Enforce limit: keep only the most recent nonmasters_limit items
                            if len(raw_components_nonmasters) > nonmasters_limit:
                                # Remove oldest items (FIFO) to stay within limit
                                raw_components_nonmasters = raw_components_nonmasters[
                                    -nonmasters_limit:
                                ]

                        # DEBUG: log raw component fields prior to mapping to LiteCalendarEvent
                        try:
                            raw_summary = component.get("SUMMARY")
                            raw_description = component.get("DESCRIPTION")
                            raw_attendees = component.get("ATTENDEE")
                            logger.debug(
                                "Streaming parser received component - SUMMARY=%r, DESCRIPTION_present=%s, ATTENDEE=%s",
                                raw_summary,
                                bool(raw_description),
                                raw_attendees,
                            )
                        except Exception:
                            logger.debug(
                                "Streaming parser - failed to read raw component fields",
                                exc_info=True,
                            )

                        # Use existing event parsing logic
                        event = self._parse_event_component(
                            cast("ICalEvent", component),
                            calendar_metadata.get("X-WR-TIMEZONE"),
                        )

                        # DEBUG: log mapped event fields for validation
                        if event:
                            try:
                                attendees_len = len(event.attendees) if event.attendees else 0
                            except Exception:
                                attendees_len = -1
                            logger.debug(
                                "Streaming parser mapped event - subject=%r, body_preview_present=%s, attendees_count=%s",
                                getattr(event, "subject", None),
                                bool(getattr(event, "body_preview", None)),
                                attendees_len,
                            )

                        if event:
                            event_count += 1
                            total_components += 1

                            if event.is_recurring:
                                recurring_event_count += 1

                            # Apply filtering immediately to prevent memory accumulation
                            if event.is_busy_status and not event.is_cancelled:
                                # Only store filtered events, and cap the total
                                if len(filtered_events) < max_stored_events:
                                    filtered_events.append(event)
                                    # Store raw component for RRULE expansion (needed for recurring events)
                                    raw_components.append(component)
                                elif len(filtered_events) == max_stored_events:
                                    warning = f"Event limit reached ({max_stored_events}), truncating results"
                                    warnings.append(warning)
                                    logger.warning(warning)

                            # Explicitly release event object for garbage collection
                            del event

                    except Exception as e:
                        warning = f"Failed to parse streamed event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

                elif item["type"] == "error":
                    errors.append(item["error"])

            # If there were errors during streaming, return failure
            if errors:
                return LiteICSParseResult(
                    success=False,
                    error_message="; ".join(errors),
                    warnings=warnings,
                    source_url=source_url,
                )

            logger.debug(
                "Streaming parser processed %s events (%s total events, %s busy/tentative)",
                len(filtered_events),
                event_count,
                len(filtered_events),
            )

            # IMPORTANT: Expand recurring events (RRULE) to generate instances
            # This was missing from the streaming parser, causing recurring events
            # to not show their future occurrences
            expanded_events = []
            if recurring_event_count > 0:
                try:
                    # Combine bounded masters and non-masters for RRULE expansion
                    # This ensures RRULE masters are available while maintaining memory bounds
                    raw_components_superset = raw_components_masters + raw_components_nonmasters
                    expanded_events = self._expand_recurring_events(
                        filtered_events, raw_components_superset
                    )
                    if expanded_events:
                        # Merge expanded events with original events and deduplicate
                        filtered_events = self._merge_expanded_events(
                            filtered_events, expanded_events
                        )
                        logger.debug(
                            "Streaming parser: Added %s expanded recurring event instances",
                            len(expanded_events),
                        )
                except Exception as e:
                    logger.warning("Failed to expand recurring events in streaming parser: %s", e)
                    # Continue with unexpanded events

            return LiteICSParseResult(
                success=True,
                events=filtered_events,
                calendar_name=calendar_metadata.get("X-WR-CALNAME"),
                calendar_description=calendar_metadata.get("X-WR-CALDESC"),
                timezone=calendar_metadata.get("X-WR-TIMEZONE"),
                total_components=total_components,
                event_count=event_count,
                recurring_event_count=recurring_event_count,
                warnings=warnings,
                ics_version=calendar_metadata.get("VERSION"),
                prodid=calendar_metadata.get("PRODID"),
                raw_content=None,  # Don't store raw content for large files
                source_url=source_url,
            )

        except Exception as e:
            logger.exception("Failed to parse ICS content with streaming parser")
            return LiteICSParseResult(
                success=False,
                error_message=str(e),
                source_url=source_url,
            )

    def _validate_ics_size(self, ics_content: str) -> None:
        """Validate ICS content size before processing.

        Args:
            ics_content: Raw ICS content to validate

        Raises:
            LiteICSContentTooLargeError: If content exceeds maximum size limit
        """
        if not ics_content:
            return

        size_bytes = len(ics_content.encode("utf-8"))

        if size_bytes > MAX_ICS_SIZE_BYTES:
            logger.error(
                "ICS content too large: %s bytes exceeds %s limit",
                size_bytes,
                MAX_ICS_SIZE_BYTES,
            )
            raise LiteICSContentTooLargeError(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit",
            )

        if size_bytes > MAX_ICS_SIZE_WARNING:
            logger.warning(
                "Large ICS content detected: %s bytes (threshold: %s)",
                size_bytes,
                MAX_ICS_SIZE_WARNING,
            )

    def parse_ics_content(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> LiteICSParseResult:
        """Parse ICS content into structured calendar events.

        Automatically chooses optimal parsing method based on content size.
        For large files (>10MB), uses streaming parser to reduce memory usage.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with events and metadata including raw content
        """
        if not ics_content or not ics_content.strip():
            logger.warning("Empty ICS content provided")
            return LiteICSParseResult(
                success=False,
                error_message="Empty ICS content",
                source_url=source_url,
            )

        # Use optimized parsing method that automatically selects strategy
        if self._should_use_streaming(ics_content):
            logger.debug(
                "Using streaming parser for large ICS content (%d bytes)", len(ics_content)
            )
            return self._parse_with_streaming(ics_content, source_url)

        # Initialize variables that might be used in error handling
        raw_content = None

        try:
            logger.debug("Starting traditional ICS content parsing")

            # Capture raw content and validate size (with error handling)
            # Only store full raw ICS content in development environment
            if not _is_production_mode():
                try:
                    self._validate_ics_size(ics_content)
                    raw_content = ics_content
                    logger.debug("Raw ICS content captured: %d bytes", len(ics_content))
                except LiteICSContentTooLargeError:
                    logger.exception("ICS content too large, skipping raw content storage")
                    raise  # Re-raise to stop processing
                except Exception as e:
                    logger.warning("Failed to capture raw ICS content: %s", e)
                    # Continue parsing without raw content

            # Parse the calendar
            calendar = Calendar.from_ical(ics_content)

            # Extract calendar metadata
            calendar_name = self._get_calendar_property(cast("Calendar", calendar), "X-WR-CALNAME")
            calendar_description = self._get_calendar_property(
                cast("Calendar", calendar),
                "X-WR-CALDESC",
            )
            timezone_str = self._get_calendar_property(cast("Calendar", calendar), "X-WR-TIMEZONE")
            prodid = self._get_calendar_property(cast("Calendar", calendar), "PRODID")
            version = self._get_calendar_property(cast("Calendar", calendar), "VERSION")

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
                            cast("ICalEvent", component),
                            timezone_str,
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

            # Apply RRULE expansion if enabled
            expanded_events = []
            if getattr(self.settings, "enable_rrule_expansion", True):
                try:
                    expanded_events = self._expand_recurring_events(events, raw_components)
                    if expanded_events:
                        # Merge expanded events with original events and deduplicate
                        events = self._merge_expanded_events(events, expanded_events)
                        events = self._deduplicate_events(events)
                        logger.debug(
                            "Added %s expanded recurring event instances", len(expanded_events)
                        )
                except Exception as e:
                    logger.warning("RRULE expansion failed, continuing without expansion: %s", e)
                    # Continue with original events only

            # Filter to only busy/tentative events (same as Graph API behavior)
            # TODO: This should respect the filter_busy_only configuration setting
            filtered_events = [e for e in events if e.is_busy_status and not e.is_cancelled]

            logger.debug(
                "Parsed %s events from ICS content (%s total events, %s busy/tentative)",
                len(filtered_events),
                event_count,
                len(filtered_events),
            )

            return LiteICSParseResult(
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
            return LiteICSParseResult(
                success=False,
                error_message=str(e),
                raw_content=raw_content,
                source_url=source_url,
            )

    def _parse_event_component(
        self,
        component: ICalEvent,
        default_timezone: Optional[str] = None,
    ) -> Optional[LiteCalendarEvent]:
        """Parse a single VEVENT component into LiteCalendarEvent.

        Delegates to LiteEventComponentParser for actual parsing logic.

        Args:
            component: iCalendar VEVENT component
            default_timezone: Default timezone for the calendar

        Returns:
            Parsed LiteCalendarEvent or None if parsing fails
        """
        return self._event_parser.parse_event_component(component, default_timezone)

    def _parse_datetime(self, dt_prop: Any, default_timezone: Optional[str] = None) -> datetime:
        """Parse iCalendar datetime property.

        Delegates to LiteDateTimeParser for actual parsing logic.

        Args:
            dt_prop: iCalendar datetime property
            default_timezone: Default timezone if none specified

        Returns:
            Parsed datetime with timezone
        """
        return self._datetime_parser.parse_datetime(dt_prop, default_timezone)

    def _parse_datetime_optional(self, dt_prop: Any) -> Optional[datetime]:
        """Parse optional datetime property.

        Delegates to LiteDateTimeParser for actual parsing logic.

        Args:
            dt_prop: iCalendar datetime property or None

        Returns:
            Parsed datetime or None
        """
        return self._datetime_parser.parse_datetime_optional(dt_prop)

    # NOTE: _parse_status has been moved to LiteEventComponentParser in lite_event_parser.py
    # NOTE: _map_transparency_to_status has been moved to LiteEventComponentParser in lite_event_parser.py

    def _parse_attendee(self, attendee_prop: Any) -> Optional[LiteAttendee]:
        """Parse attendee from iCalendar property.

        Delegates to LiteAttendeeParser for actual parsing logic.

        Args:
            attendee_prop: iCalendar ATTENDEE property

        Returns:
            Parsed LiteAttendee or None
        """
        return self._attendee_parser.parse_attendee(attendee_prop)

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

    def filter_busy_events(self, events: list[LiteCalendarEvent]) -> list[LiteCalendarEvent]:
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
                logger.debug("Empty ICS content provided for validation")
                return False

            # Check for required ICS markers
            if "BEGIN:VCALENDAR" not in ics_content:
                logger.debug("Missing BEGIN:VCALENDAR marker")
                return False

            if "END:VCALENDAR" not in ics_content:
                logger.debug("Missing END:VCALENDAR marker")
                return False

            # Try to parse with icalendar
            Calendar.from_ical(ics_content)

            logger.debug("Valid ICS content parsed successfully: %d bytes", len(ics_content))
            return True

        except Exception as e:
            logger.debug("ICS validation failed: %s", e)
            return False

    # NOTE: _collect_exdate_props has been moved to LiteEventComponentParser in lite_event_parser.py

    def _expand_recurring_events(
        self,
        events: list[LiteCalendarEvent],
        raw_components: list[ICalEvent],
    ) -> list[LiteCalendarEvent]:
        """Expand recurring events using RRuleOrchestrator.

        This method now delegates all RRULE expansion logic to the centralized
        RRuleOrchestrator, which handles:
        1. Building component and event maps
        2. Collecting expansion candidates
        3. Executing async RRULE expansion

        Args:
            events: List of parsed calendar events
            raw_components: List of raw iCalendar components for RRULE extraction

        Returns:
            List of expanded event instances
        """
        # Delegate to RRuleOrchestrator for centralized RRULE expansion
        return self._rrule_orchestrator.expand_recurring_events(events, raw_components)

    def _merge_expanded_events(
        self,
        original_events: list[LiteCalendarEvent],
        expanded_events: list[LiteCalendarEvent],
    ) -> list[LiteCalendarEvent]:
        """Merge expanded events with original events.

        Delegates to LiteEventMerger for actual merging logic.

        Args:
            original_events: Original parsed events
            expanded_events: Expanded recurring event instances

        Returns:
            Combined list of events
        """
        return self._event_merger.merge_expanded_events(original_events, expanded_events)

    def _deduplicate_events(self, events: list[LiteCalendarEvent]) -> list[LiteCalendarEvent]:
        """Remove duplicate events based on UID and start time.

        Delegates to LiteEventMerger for actual deduplication logic.

        Args:
            events: List of calendar events to deduplicate

        Returns:
            Deduplicated list of events
        """
        return self._event_merger.deduplicate_events(events)
