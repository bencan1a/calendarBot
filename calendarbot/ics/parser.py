"""iCalendar parser with Microsoft Outlook compatibility."""

import logging
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, BinaryIO, Optional, TextIO, Union, cast

from icalendar import Calendar, Event as ICalEvent

from ..config.build import is_production_mode
from ..security.logging import SecurityEventLogger  # type: ignore
from ..timezone import ensure_timezone_aware
from .models import (
    Attendee,
    AttendeeType,
    CalendarEvent,
    DateTimeInfo,
    EventStatus,
    ICSParseResult,
    Location,
    ResponseStatus,
)
from .rrule_expander import RRuleExpander

logger = logging.getLogger(__name__)

# Size validation constants from design specification
MAX_ICS_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit
MAX_ICS_SIZE_WARNING = 10 * 1024 * 1024  # 10MB warning threshold

# Streaming parser constants
DEFAULT_CHUNK_SIZE = 8192  # 8KB chunks for streaming
STREAMING_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold for streaming vs traditional


class ICSContentTooLargeError(Exception):
    """Raised when ICS content exceeds size limits."""


class StreamingICSParser:
    """Memory-efficient streaming ICS parser for large files.

    Processes ICS files in chunks to minimize memory usage, handling
    event boundaries and line folding across chunk boundaries.
    """

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        """Initialize streaming parser.

        Args:
            chunk_size: Size of chunks to read in bytes
        """
        self.chunk_size = chunk_size
        self._line_buffer = ""  # Buffer for incomplete lines
        self._current_event_lines: list[str] = []  # Buffer for current event
        self._in_event = False  # Track if we're inside a VEVENT
        self._calendar_metadata: dict[str, str] = {}  # Store calendar properties
        self._pending_folded_line = ""  # Buffer for incomplete folded lines across chunks

    def parse_stream(
        self,
        file_source: Union[str, BinaryIO, TextIO],
    ) -> Generator[dict[str, Any], None, None]:
        """Parse ICS content from file stream, yielding events as they are found.

        Args:
            file_source: File path, file object, or ICS content string

        Yields:
            Dictionary containing parsed event data and metadata

        Raises:
            ICSContentTooLargeError: If content exceeds size limits
        """
        try:
            # Handle different input types
            if isinstance(file_source, str):
                if not file_source or not file_source.strip():
                    # Empty content - no events to yield
                    return
                elif file_source.startswith(("BEGIN:VCALENDAR", "BEGIN:VEVENT")):
                    # It's ICS content, not a file path
                    yield from self._parse_content_stream(file_source)
                else:
                    # It's a file path
                    with Path(file_source).open(encoding="utf-8") as f:
                        yield from self._parse_file_stream(f)
            else:
                # It's a file object
                yield from self._parse_file_stream(file_source)

        except Exception as e:
            logger.exception("Failed to parse ICS stream")
            yield {"type": "error", "error": str(e), "metadata": self._calendar_metadata.copy()}

    def _parse_content_stream(self, content: str) -> Generator[dict[str, Any], None, None]:
        """Parse ICS content string in chunks."""
        content_io = StringIO(content)
        yield from self._parse_file_stream(content_io)

    def _parse_file_stream(
        self,
        file_obj: Union[BinaryIO, TextIO],
    ) -> Generator[dict[str, Any], None, None]:
        """Parse ICS file stream in chunks."""
        while True:
            chunk = file_obj.read(self.chunk_size)
            if not chunk:
                break

            # Convert bytes to string if needed
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="replace")

            # Process chunk and yield any complete events
            yield from self._process_chunk(chunk)

        # Process any remaining buffered content
        yield from self._finalize_parsing()

    def _process_chunk(self, chunk: str) -> Generator[dict[str, Any], None, None]:
        """Process a chunk of ICS data, handling line and event boundaries."""
        # Combine with buffered incomplete line
        content = self._line_buffer + chunk
        lines = content.split("\n")

        # Keep last line in buffer if chunk doesn't end with newline
        if not chunk.endswith("\n"):
            self._line_buffer = lines[-1]
            lines = lines[:-1]
        else:
            self._line_buffer = ""

        # Process complete lines
        yield from self._process_lines(lines)

    def _process_lines(self, lines: list[str]) -> Generator[dict[str, Any], None, None]:
        """Process ICS lines, handling line folding and event boundaries across chunks."""
        for raw_line in lines:
            line = raw_line.rstrip("\r")

            # Handle pending folded line from previous chunk
            if self._pending_folded_line:
                if line.startswith((" ", "\t")):
                    # This is a continuation line - add to pending
                    self._pending_folded_line += (
                        " " + line[1:]
                    )  # Remove leading whitespace, add space
                    continue
                else:
                    # Pending line is complete, process it
                    yield from self._process_line(self._pending_folded_line)
                    self._pending_folded_line = ""
                    # Fall through to process current line

            # Check if this line starts a folded sequence that might span chunks
            if line and not line.startswith((" ", "\t")):
                # This is a potential start of a folded line
                self._pending_folded_line = line
            elif line.startswith((" ", "\t")) and self._pending_folded_line:
                # This is a continuation of an existing folded line
                self._pending_folded_line += " " + line[1:]  # Add continuation
                # If no pending line, this is an orphaned continuation (shouldn't happen in valid ICS)

    def _process_line(self, line: str) -> Generator[dict[str, Any], None, None]:
        """Process a single complete ICS line."""
        line = line.strip()
        if not line:
            return

        # Handle calendar metadata
        if not self._in_event and ":" in line:
            prop, value = line.split(":", 1)
            prop = prop.upper()

            if prop in ("X-WR-CALNAME", "X-WR-CALDESC", "X-WR-TIMEZONE", "PRODID", "VERSION"):
                self._calendar_metadata[prop] = value

        # Handle event boundaries
        if line == "BEGIN:VEVENT":
            self._in_event = True
            self._current_event_lines = [line]
        elif line == "END:VEVENT":
            if self._in_event:
                self._current_event_lines.append(line)
                yield from self._parse_complete_event()
                self._current_event_lines = []
            self._in_event = False
        elif self._in_event:
            self._current_event_lines.append(line)

    def _parse_complete_event(self) -> Generator[dict[str, Any], None, None]:
        """Parse a complete event from buffered lines."""
        try:
            # Create minimal ICS content for this event
            event_ics = "BEGIN:VCALENDAR\n"
            event_ics += "VERSION:2.0\n"
            event_ics += "PRODID:CalendarBot-Streaming\n"
            event_ics += "\n".join(self._current_event_lines) + "\n"
            event_ics += "END:VCALENDAR\n"

            # Parse using icalendar library
            calendar = Calendar.from_ical(event_ics)

            for component in calendar.walk():
                if component.name == "VEVENT":
                    yield {
                        "type": "event",
                        "component": component,
                        "metadata": self._calendar_metadata.copy(),
                    }
                    break

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            yield {
                "type": "error",
                "error": f"Failed to parse event: {e}",
                "raw_lines": self._current_event_lines.copy(),
                "metadata": self._calendar_metadata.copy(),
            }

    def _finalize_parsing(self) -> Generator[dict[str, Any], None, None]:
        """Process any remaining buffered content at end of file."""
        # Process any pending folded line from cross-chunk folding
        if self._pending_folded_line:
            yield from self._process_line(self._pending_folded_line)
            self._pending_folded_line = ""

        # Process any remaining line buffer
        if self._line_buffer.strip():
            yield from self._process_line(self._line_buffer)

        # Process any incomplete event
        if self._in_event and self._current_event_lines:
            logger.warning("Incomplete event at end of file")
            yield {
                "type": "error",
                "error": "Incomplete event at end of file",
                "raw_lines": self._current_event_lines.copy(),
                "metadata": self._calendar_metadata.copy(),
            }


class ICSParser:
    """iCalendar parser with Microsoft Outlook compatibility."""

    def __init__(self, settings: Any) -> None:
        """Initialize ICS parser.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.security_logger = SecurityEventLogger()
        self.rrule_expander = RRuleExpander(settings)
        self._streaming_parser = StreamingICSParser()
        logger.debug("ICS parser initialized")

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
    ) -> ICSParseResult:
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
            logger.info(f"Using streaming parser for large ICS content ({len(ics_content)} bytes)")
            return self._parse_with_streaming(ics_content, source_url)

        logger.debug(f"Using traditional parser for small ICS content ({len(ics_content)} bytes)")
        return self.parse_ics_content(ics_content, source_url)

    def _parse_with_streaming(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> ICSParseResult:
        """Parse ICS content using streaming parser with memory-bounded processing."""
        try:
            # Initialize result tracking - NO event accumulation
            filtered_events: list[CalendarEvent] = []  # Only store final filtered results
            warnings = []
            errors = []
            total_components = 0
            event_count = 0
            recurring_event_count = 0
            calendar_metadata = {}

            # Memory-bounded processing: limit stored events for typical calendar view usage
            max_stored_events = (
                50  # Cap at 50 events - sufficient for typical 1-20 event calendar views
            )

            # Process stream with immediate filtering to prevent memory accumulation
            for item in self._streaming_parser.parse_stream(ics_content):
                if item["type"] == "event":
                    try:
                        # Parse the iCalendar component using existing logic
                        component = item["component"]
                        calendar_metadata.update(item["metadata"])

                        # Use existing event parsing logic
                        event = self._parse_event_component(
                            cast("ICalEvent", component),
                            calendar_metadata.get("X-WR-TIMEZONE"),
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
                return ICSParseResult(
                    success=False,
                    error_message="; ".join(errors),
                    warnings=warnings,
                    source_url=source_url,
                )

            logger.debug(
                f"Streaming parser processed {len(filtered_events)} events "
                f"({event_count} total events, {len(filtered_events)} busy/tentative)",
            )

            return ICSParseResult(
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
            return ICSParseResult(
                success=False,
                error_message=str(e),
                source_url=source_url,
            )

    def _validate_ics_size(self, ics_content: str) -> None:
        """Validate ICS content size before processing.

        Args:
            ics_content: Raw ICS content to validate

        Raises:
            ICSContentTooLargeError: If content exceeds maximum size limit
        """
        if not ics_content:
            return

        size_bytes = len(ics_content.encode("utf-8"))

        if size_bytes > MAX_ICS_SIZE_BYTES:
            logger.error(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit",
            )
            raise ICSContentTooLargeError(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit",
            )

        if size_bytes > MAX_ICS_SIZE_WARNING:
            logger.warning(
                f"Large ICS content detected: {size_bytes} bytes "
                f"(threshold: {MAX_ICS_SIZE_WARNING})",
            )

    def parse_ics_content(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> ICSParseResult:
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
            return ICSParseResult(
                success=False,
                error_message="Empty ICS content",
                source_url=source_url,
            )

        # Use optimized parsing method that automatically selects strategy
        if self._should_use_streaming(ics_content):
            logger.info(f"Using streaming parser for large ICS content ({len(ics_content)} bytes)")
            return self._parse_with_streaming(ics_content, source_url)

        # Initialize variables that might be used in error handling
        raw_content = None

        try:
            logger.debug("Starting traditional ICS content parsing")

            # Capture raw content and validate size (with error handling)
            # Only store full raw ICS content in development environment
            if not is_production_mode():
                try:
                    self._validate_ics_size(ics_content)
                    raw_content = ics_content
                    logger.debug(f"Raw ICS content captured: {len(ics_content)} bytes")
                except ICSContentTooLargeError:
                    logger.exception("ICS content too large, skipping raw content storage")
                    raise  # Re-raise to stop processing
                except Exception as e:
                    logger.warning(f"Failed to capture raw ICS content: {e}")
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
                            f"Added {len(expanded_events)} expanded recurring event instances"
                        )
                except Exception as e:
                    logger.warning(f"RRULE expansion failed, continuing without expansion: {e}")
                    # Continue with original events only

            # Filter to only busy/tentative events (same as Graph API behavior)
            # TODO: This should respect the filter_busy_only configuration setting
            filtered_events = [e for e in events if e.is_busy_status and not e.is_cancelled]

            logger.debug(
                f"Parsed {len(filtered_events)} events from ICS content "
                f"({event_count} total events, {len(filtered_events)} busy/tentative)",
            )

            return ICSParseResult(
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
            return ICSParseResult(
                success=False,
                error_message=str(e),
                raw_content=raw_content,
                source_url=source_url,
            )

    def parse_ics_content_unfiltered(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> ICSParseResult:
        """Parse ICS content into ALL events without filtering for raw event storage.

        This method returns ALL parsed events without any filtering, specifically
        for raw event storage to enable comparison with cached events.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with ALL events and metadata including raw content
        """
        # Initialize variables that might be used in error handling
        raw_content = None

        try:
            logger.debug("Starting unfiltered ICS content parsing for raw events")

            # Capture raw content and validate size (with error handling)
            # Only store full raw ICS content in development environment
            if not is_production_mode():
                try:
                    self._validate_ics_size(ics_content)
                    raw_content = ics_content
                    logger.debug(f"Raw ICS content captured: {len(ics_content)} bytes")
                except ICSContentTooLargeError:
                    logger.exception("ICS content too large, skipping raw content storage")
                    raise  # Re-raise to stop processing
                except Exception as e:
                    logger.warning(f"Failed to capture raw ICS content: {e}")
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

            # Parse events and capture individual event raw content
            events = []
            event_raw_content_map = {}  # Map event ID to individual raw ICS content
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
                            event_count += 1

                            # Extract individual event ICS content using component.to_ical()
                            # Only store raw ICS content in development environment
                            if not is_production_mode():
                                try:
                                    individual_ics = component.to_ical().decode("utf-8")
                                    event_raw_content_map[event.id] = individual_ics
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to extract raw ICS for event {event.id}: {e}",
                                    )
                                    # Fallback to basic event identifier
                                    event_raw_content_map[event.id] = (
                                        f"# Event {event.id} - Raw ICS extraction failed"
                                    )

                            if event.is_recurring:
                                recurring_event_count += 1

                    except Exception as e:
                        warning = f"Failed to parse event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

            # NO FILTERING - return ALL events (raw storage only in development)
            logger.debug(
                f"Parsed {len(events)} unfiltered events from ICS content "
                f"({event_count} total events, no filtering applied)",
            )

            # Create enhanced result with individual event raw content mapping
            result = ICSParseResult(
                success=True,
                events=events,  # Return ALL events without filtering
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

            # Store individual event raw content in the result for access by cache manager
            result.event_raw_content_map = event_raw_content_map

            return result

        except Exception as e:
            logger.exception("Failed to parse ICS content")
            return ICSParseResult(
                success=False,
                error_message=str(e),
                raw_content=raw_content,
                source_url=source_url,
            )

    def _parse_event_component(  # noqa: PLR0912, PLR0915
        self,
        component: ICalEvent,
        default_timezone: Optional[str] = None,
    ) -> Optional[CalendarEvent]:
        """Parse a single VEVENT component into CalendarEvent.

        Args:
            component: iCalendar VEVENT component
            default_timezone: Default timezone for the calendar

        Returns:
            Parsed CalendarEvent or None if parsing fails
        """
        try:
            # Required properties
            uid = str(component.get("UID", str(uuid.uuid4())))
            summary = str(component.get("SUMMARY", "No Title"))

            # Time information
            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")

            if not dtstart:
                logger.warning(f"Event {uid} missing DTSTART, skipping")
                return None

            # Parse start time
            start_dt = self._parse_datetime(dtstart, default_timezone)
            start_info = DateTimeInfo(
                date_time=start_dt,
                time_zone=str(start_dt.tzinfo) if start_dt.tzinfo else "UTC",
            )

            # Parse end time
            if dtend:
                end_dt = self._parse_datetime(dtend, default_timezone)
            else:
                # Use duration if available, otherwise default to 1 hour
                duration = component.get("DURATION")
                end_dt = start_dt + duration.dt if duration else start_dt + timedelta(hours=1)

            end_info = DateTimeInfo(
                date_time=end_dt,
                time_zone=str(end_dt.tzinfo) if end_dt.tzinfo else "UTC",
            )

            # Event status and visibility
            status = self._parse_status(component.get("STATUS"))
            transp = component.get("TRANSP", "OPAQUE")

            show_as = self._map_transparency_to_status(transp, status, component)

            # All-day events
            is_all_day = not hasattr(dtstart.dt, "hour")

            # Description
            description = component.get("DESCRIPTION")
            body_preview = None
            if description:
                body_preview = str(description)[:200]  # Truncate for preview

            # Location
            location = None
            location_str = component.get("LOCATION")
            if location_str:
                location = Location(display_name=str(location_str))

            # Organizer and attendees
            organizer = component.get("ORGANIZER")
            is_organizer = False
            attendees = []

            if organizer:
                # Simple organizer detection (could be enhanced)
                is_organizer = True

            # Parse attendees
            for attendee_prop in component.get("ATTENDEE", []):
                attendee_list = (
                    attendee_prop if isinstance(attendee_prop, list) else [attendee_prop]
                )

                for att in attendee_list:
                    attendee = self._parse_attendee(att)
                    if attendee:
                        attendees.append(attendee)

            # Recurrence
            rrule_prop = component.get("RRULE")
            is_recurring = rrule_prop is not None

            # RFC 5545 RECURRENCE-ID detection for Microsoft ICS bug
            # When a recurring instance is moved, the original slot should be excluded
            recurrence_id_raw = component.get("RECURRENCE-ID")
            is_moved_instance = recurrence_id_raw is not None  # noqa

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
            exdate_props = component.get("EXDATE", [])
            if not isinstance(exdate_props, list):
                exdate_props = [exdate_props] if exdate_props else []

            # Additional metadata
            created = self._parse_datetime_optional(component.get("CREATED"))
            last_modified = self._parse_datetime_optional(component.get("LAST-MODIFIED"))

            # Online meeting detection (Microsoft-specific)
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
                    import re  # noqa: PLC0415

                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                    urls = re.findall(url_pattern, str(description))
                    if urls:
                        online_meeting_url = urls[0]

            # Create CalendarEvent
            calendar_event = CalendarEvent(
                id=uid,
                subject=summary,
                body_preview=body_preview,
                start=start_info,
                end=end_info,
                is_all_day=is_all_day,
                show_as=show_as,
                is_cancelled=status == "CANCELLED",
                is_organizer=is_organizer,
                location=location,
                attendees=attendees if attendees else None,
                is_recurring=is_recurring,
                recurrence_id=recurrence_id,
                created_date_time=created,
                last_modified_date_time=last_modified,
                is_online_meeting=is_online_meeting,
                online_meeting_url=online_meeting_url,
            )

        except Exception:
            logger.exception("Failed to parse event component")
            return None
        else:
            return calendar_event

    def _parse_datetime(self, dt_prop: Any, default_timezone: Optional[str] = None) -> datetime:
        """Parse iCalendar datetime property.

        Args:
            dt_prop: iCalendar datetime property
            default_timezone: Default timezone if none specified

        Returns:
            Parsed datetime with timezone
        """
        dt = dt_prop.dt

        # Handle date-only (all-day events)
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                # No timezone specified, use centralized service for timezone handling
                if default_timezone:
                    try:
                        # Use centralized timezone service to handle timezone conversion
                        # This replaces the manual Australian timezone hack with proper service handling
                        dt = ensure_timezone_aware(dt)
                        # If a specific timezone was requested, convert to that timezone
                        # For now, we'll use the server timezone as the base since that's our standard
                        logger.debug(
                            f"Parsed naive datetime {dt} with default timezone: {default_timezone}",
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply timezone via service {default_timezone}: {e}",
                        )
                        dt = ensure_timezone_aware(dt)  # Fallback to server timezone
                else:
                    # Use centralized service for standard timezone awareness
                    dt = ensure_timezone_aware(dt)
            else:
                # Already has timezone info, ensure it's properly handled
                dt = ensure_timezone_aware(dt)
            return dt
        # Date object - convert to datetime at midnight with proper timezone
        return ensure_timezone_aware(datetime.combine(dt, datetime.min.time()))

    def _parse_datetime_optional(self, dt_prop: Any) -> Optional[datetime]:
        """Parse optional datetime property.

        Args:
            dt_prop: iCalendar datetime property or None

        Returns:
            Parsed datetime or None
        """
        if dt_prop is None:
            return None

        try:
            return self._parse_datetime(dt_prop)
        except Exception:
            return None

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
    ) -> EventStatus:
        """Map iCalendar transparency and status to EventStatus with Microsoft phantom event filtering.

        Args:
            transparency: TRANSP property value
            status: STATUS property value
            component: Raw iCalendar component for Microsoft marker access

        Returns:
            EventStatus enum value
        """
        # Check Microsoft deletion markers for phantom event filtering
        ms_deleted = component.get("X-OUTLOOK-DELETED")
        ms_busystatus = component.get("X-MICROSOFT-CDO-BUSYSTATUS")

        # Filter out Microsoft phantom deleted events
        if ms_deleted and str(ms_deleted).upper() == "TRUE":
            return EventStatus.FREE  # Will be filtered out by busy status check

        # Check if this is a "Following:" meeting by parsing the event title
        summary = component.get("SUMMARY")
        is_following_meeting = summary and "Following:" in str(summary)

        # Use Microsoft busy status override if available
        if ms_busystatus:
            ms_status = str(ms_busystatus).upper()
            if ms_status == "FREE":
                # Special case: "Following:" meetings should be TENTATIVE, not FREE
                if is_following_meeting:
                    return EventStatus.TENTATIVE
                # All other FREE busy status events should be filtered out
                return EventStatus.FREE

        if status == "CANCELLED":
            mapped_status = EventStatus.FREE
        elif status == "TENTATIVE":
            mapped_status = EventStatus.TENTATIVE
        elif transparency == "TRANSPARENT":
            # Special handling for transparent + confirmed meetings (e.g., "Following" meetings)
            # These should appear on calendar but with different visual treatment
            mapped_status = EventStatus.TENTATIVE if status == "CONFIRMED" else EventStatus.FREE
        elif is_following_meeting:
            # "Following:" meetings should appear on calendar regardless of other properties
            mapped_status = EventStatus.TENTATIVE
            logger.info(f"  → APPLIED FOLLOWING LOGIC: {mapped_status}")
        else:
            # OPAQUE or default
            mapped_status = EventStatus.BUSY

        return mapped_status

    def _parse_attendee(self, attendee_prop: Any) -> Optional[Attendee]:
        """Parse attendee from iCalendar property.

        Args:
            attendee_prop: iCalendar ATTENDEE property

        Returns:
            Parsed Attendee or None
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
            attendee_type = AttendeeType.REQUIRED
            if role == "OPT-PARTICIPANT":
                attendee_type = AttendeeType.OPTIONAL
            elif role == "NON-PARTICIPANT":
                attendee_type = AttendeeType.RESOURCE

            # Response status
            partstat = params.get("PARTSTAT", "NEEDS-ACTION")
            response_status = ResponseStatus.NOT_RESPONDED

            status_map = {
                "ACCEPTED": ResponseStatus.ACCEPTED,
                "DECLINED": ResponseStatus.DECLINED,
                "TENTATIVE": ResponseStatus.TENTATIVELY_ACCEPTED,
                "DELEGATED": ResponseStatus.NOT_RESPONDED,
                "NEEDS-ACTION": ResponseStatus.NOT_RESPONDED,
            }

            response_status = status_map.get(partstat, ResponseStatus.NOT_RESPONDED)

            return Attendee(
                name=name,
                email=email,
                type=attendee_type,
                response_status=response_status,
            )

        except Exception as e:
            logger.debug(f"Failed to parse attendee: {e}")
            return None

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

    def filter_phantom_recurring_events_conservative(  # noqa: PLR0912
        self,
        events: list[CalendarEvent],
        raw_components: list,
    ) -> list[CalendarEvent]:
        """Conservative filter for phantom recurring events caused by Microsoft ICS RFC 5545 bug.

        Only removes events with explicit evidence of the Microsoft bug:
        - Event must be recurring with no RECURRENCE-ID (original pattern slot)
        - Must have a moved instance (RECURRENCE-ID) within the same UID series
        - Original slot must lack proper EXDATE exclusion

        Args:
            events: Parsed calendar events
            raw_components: Raw iCalendar VEVENT components for RFC 5545 field access

        Returns:
            Filtered events with confirmed phantom recurring instances removed
        """
        if len(events) != len(raw_components):
            logger.warning("Event/component count mismatch, skipping phantom filter")
            return events

        # Build UID-based mapping for precise targeting
        uid_to_events: dict[str, list] = {}  # UID -> list of (event, component) tuples

        for event, component in zip(events, raw_components):
            uid = str(component.get("UID", ""))
            if uid not in uid_to_events:
                uid_to_events[uid] = []
            uid_to_events[uid].append((event, component))

        filtered_events = []
        phantom_count = 0

        # Process each UID series independently
        for event_component_pairs in uid_to_events.values():
            # Separate original patterns from moved instances within this UID series
            original_patterns = []
            moved_instances = []
            exdate_times = []

            for event, component in event_component_pairs:
                if component.get("RECURRENCE-ID"):
                    # This is a moved instance
                    moved_instances.append((event, component))
                elif event.is_recurring:
                    # This is an original recurring pattern
                    original_patterns.append((event, component))

                # Collect EXDATE times for this UID
                exdate_props = component.get("EXDATE", [])
                if exdate_props:
                    if not isinstance(exdate_props, list):
                        exdate_props = [exdate_props]
                    for exdate in exdate_props:
                        try:
                            # Use the event's timezone for proper parsing
                            timezone_str = (
                                event.start.time_zone
                                if hasattr(event.start, "time_zone")
                                else "UTC"
                            )
                            excluded_time = self._parse_datetime(exdate, timezone_str)
                            exdate_times.append(excluded_time)
                        except Exception:  # noqa: PERF203
                            continue

            # Only check for phantoms if we have both moved instances AND original patterns
            if moved_instances and original_patterns:
                # Check each original pattern for phantom status
                for event, component in original_patterns:  # noqa
                    is_phantom = False
                    event_start = event.start.date_time

                    # Check if this pattern slot has a corresponding moved instance
                    for moved_event, moved_component in moved_instances:
                        recurrence_id = moved_component.get("RECURRENCE-ID")
                        if recurrence_id:
                            try:
                                # Parse using the moved event's timezone
                                moved_timezone = (
                                    moved_event.start.time_zone
                                    if hasattr(moved_event.start, "time_zone")
                                    else "UTC"
                                )
                                original_time = self._parse_datetime(recurrence_id, moved_timezone)

                                # Check if this pattern matches the moved instance's original time
                                if (
                                    abs((event_start - original_time).total_seconds()) < 300
                                ):  # 5 minute tolerance
                                    # Found a moved instance - check if EXDATE properly excludes this slot
                                    is_properly_excluded = any(
                                        abs((event_start - ex_time).total_seconds()) < 300
                                        for ex_time in exdate_times
                                    )

                                    if not is_properly_excluded:
                                        # This is a phantom - moved instance exists but no EXDATE exclusion
                                        logger.debug(
                                            f"🚨 Found phantom recurring event: {event.subject} at {event_start}",
                                        )
                                        logger.debug(
                                            f"   - Moved instance exists with RECURRENCE-ID: {recurrence_id}",
                                        )
                                        logger.debug("   - No proper EXDATE exclusion found")
                                        is_phantom = True
                                        phantom_count += 1
                                        break
                            except Exception as e:
                                logger.warning(f"Error parsing RECURRENCE-ID {recurrence_id}: {e}")
                                continue

                    if not is_phantom:
                        filtered_events.append(event)

                # Always include moved instances (they're the real meetings)
                for moved_event, _ in moved_instances:
                    filtered_events.append(moved_event)
            else:
                # No moved instances, include all events for this UID
                for event, _ in event_component_pairs:
                    filtered_events.append(event)

        if phantom_count > 0:
            logger.info(
                f"🎯 Conservative phantom filter: removed {phantom_count} confirmed phantom events",
            )
        else:
            logger.info("✅ Conservative phantom filter: no phantom events detected")

        return filtered_events

    def filter_busy_events(self, events: list[CalendarEvent]) -> list[CalendarEvent]:
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
                self.security_logger.log_input_validation_failure(
                    input_type="ics_content",
                    validation_error="Empty ICS content provided",
                    details={
                        "source_ip": "internal",
                        "input_value": "<empty>",
                        "content_length": 0,
                    },
                )
                return False

            # Check for required ICS markers
            if "BEGIN:VCALENDAR" not in ics_content:
                self.security_logger.log_input_validation_failure(
                    input_type="ics_content",
                    validation_error="Missing BEGIN:VCALENDAR marker",
                    details={
                        "source_ip": "internal",
                        "content_length": len(ics_content),
                        "input_preview": (
                            ics_content[:100] + "..." if len(ics_content) > 100 else ics_content
                        ),
                    },
                )
                return False

            if "END:VCALENDAR" not in ics_content:
                self.security_logger.log_input_validation_failure(
                    input_type="ics_content",
                    validation_error="Missing END:VCALENDAR marker",
                    details={
                        "source_ip": "internal",
                        "content_length": len(ics_content),
                        "input_preview": (
                            ics_content[:100] + "..." if len(ics_content) > 100 else ics_content
                        ),
                    },
                )
                return False

            # Try to parse with icalendar
            Calendar.from_ical(ics_content)

            # No logging for successful validation - only security violations are logged
            logger.debug(f"Valid ICS content parsed successfully: {len(ics_content)} bytes")
            return True

        except Exception as e:
            self.security_logger.log_input_validation_failure(
                input_type="ics_content",
                validation_error=f"ICS parsing failed: {e}",
                details={
                    "source_ip": "internal",
                    "content_length": len(ics_content) if ics_content else 0,
                    "input_preview": (
                        ics_content[:100] + "..."
                        if ics_content and len(ics_content) > 100
                        else ics_content or "<empty>"
                    ),
                    "exception_type": type(e).__name__,
                },
            )
            logger.debug(f"ICS validation failed: {e}")
            return False

    def _expand_recurring_events(  # noqa: PLR0912
        self,
        events: list[CalendarEvent],
        raw_components: list[ICalEvent],
    ) -> list[CalendarEvent]:
        """Expand recurring events using RRuleExpander.

        Args:
            events: List of parsed calendar events
            raw_components: List of raw iCalendar components for RRULE extraction

        Returns:
            List of expanded event instances
        """
        expanded_events = []

        # Create a mapping of event UIDs to their raw components
        component_map = {}
        for i, component in enumerate(raw_components):
            if i < len(events):
                uid = events[i].id
                component_map[uid] = component

        for event in events:
            if not event.is_recurring:
                continue

            # Get the raw component for this event
            component = component_map.get(event.id)
            if not component:
                logger.warning(f"No raw component found for recurring event {event.id}")
                continue

            # Extract RRULE and EXDATE
            rrule_prop = component.get("RRULE")
            exdate_props = component.get("EXDATE", [])

            if rrule_prop:
                try:
                    # Convert RRULE to proper iCalendar format
                    if hasattr(rrule_prop, "to_ical"):
                        rrule_string = rrule_prop.to_ical().decode("utf-8")
                    else:
                        rrule_string = str(rrule_prop)

                    # Convert EXDATE to list of strings
                    exdates: list[str] = []
                    if exdate_props:
                        if not isinstance(exdate_props, list):
                            exdate_props = [exdate_props]
                        for exdate in exdate_props:
                            if hasattr(exdate, "to_ical"):
                                exdate_str = exdate.to_ical().decode("utf-8")

                                # Preserve timezone information if present
                                if hasattr(exdate, "params") and "TZID" in exdate.params:
                                    tzid = exdate.params["TZID"]

                                    # Handle comma-separated EXDATE values with timezone
                                    if "," in exdate_str:
                                        # Apply timezone to each comma-separated value in one extend for performance
                                        exdates.extend(
                                            f"TZID={tzid}:{single_exdate.strip()}"
                                            for single_exdate in exdate_str.split(",")
                                        )
                                    else:
                                        # Single EXDATE with timezone
                                        exdates.append(f"TZID={tzid}:{exdate_str}")
                                else:  # noqa: PLR5501 - separate branch for non-timezone EXDATE formats
                                    # No timezone - handle comma separation normally
                                    if "," in exdate_str:
                                        exdates.extend(
                                            single_exdate.strip()
                                            for single_exdate in exdate_str.split(",")
                                        )
                                    else:
                                        exdates.append(exdate_str)
                            else:
                                exdate_str = str(exdate)
                                # Handle comma-separated EXDATE values
                                if "," in exdate_str:
                                    exdates.extend(
                                        single_exdate.strip()
                                        for single_exdate in exdate_str.split(",")
                                    )
                                else:
                                    exdates.append(exdate_str)

                    # Expand using RRuleExpander
                    instances = self.rrule_expander.expand_rrule(
                        event,
                        rrule_string,
                        exdates=exdates if exdates else None,
                    )

                    expanded_events.extend(instances)

                except Exception as e:
                    logger.warning(f"Failed to expand RRULE for event {event.id}: {e}")
                    continue

        return expanded_events

    def _merge_expanded_events(
        self,
        original_events: list[CalendarEvent],
        expanded_events: list[CalendarEvent],
    ) -> list[CalendarEvent]:
        """Merge expanded events with original events.

        Args:
            original_events: Original parsed events
            expanded_events: Expanded recurring event instances

        Returns:
            Combined list of events
        """
        # Start with all expanded events
        merged_events = expanded_events.copy()

        # Create a set of master UIDs that were successfully expanded
        expanded_master_uids = {
            getattr(event, "rrule_master_uid", None)
            for event in expanded_events
            if getattr(event, "rrule_master_uid", None)
        }

        # Add original events, but skip recurring masters that were successfully expanded
        for event in original_events:
            if event.is_recurring:
                # Keep recurring masters that weren't expanded (e.g., due to unsupported RRULE)
                if event.id not in expanded_master_uids:
                    merged_events.append(event)
            else:
                # Always keep non-recurring events
                merged_events.append(event)

        logger.debug(
            f"Merged {len(original_events)} original + {len(expanded_events)} expanded = {len(merged_events)} total events"
        )
        return merged_events

    def _deduplicate_events(self, events: list[CalendarEvent]) -> list[CalendarEvent]:
        """Remove duplicate events based on UID and start time.

        Args:
            events: List of calendar events to deduplicate

        Returns:
            Deduplicated list of events
        """
        seen = set()
        deduplicated = []

        for event in events:
            # Create a unique key based on subject, start time, and basic properties
            # Use start time as string to avoid timezone comparison issues
            key = (
                event.subject,
                event.start.date_time.isoformat(),
                event.end.date_time.isoformat(),
                event.is_all_day,
            )

            if key not in seen:
                seen.add(key)
                deduplicated.append(event)

        if len(events) != len(deduplicated):
            logger.debug(f"Removed {len(events) - len(deduplicated)} duplicate events")

        return deduplicated
