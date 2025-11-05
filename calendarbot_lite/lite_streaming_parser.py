"""Memory-efficient streaming ICS parser for large calendar files - CalendarBot Lite.

This module handles streaming parsing of ICS files to minimize memory usage,
processing events incrementally as they are read from the source.
Extracted from lite_parser.py to improve modularity and testability.
"""

import codecs
import logging
import time
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from io import StringIO
from pathlib import Path
from typing import Any, BinaryIO, Optional, TextIO

from icalendar import Calendar

from .lite_attendee_parser import LiteAttendeeParser
from .lite_datetime_utils import LiteDateTimeParser
from .lite_event_parser import LiteEventComponentParser
from .lite_models import LiteCalendarEvent, LiteICSParseResult
from .lite_parser_telemetry import ParserTelemetry

logger = logging.getLogger(__name__)

# Size validation constants from design specification
MAX_ICS_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit
MAX_ICS_SIZE_WARNING = 10 * 1024 * 1024  # 10MB warning threshold

# Streaming parser constants
DEFAULT_CHUNK_SIZE = 8192  # 8KB chunks for streaming
STREAMING_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold for streaming vs traditional

# Streaming pipeline configuration constants
DEFAULT_READ_CHUNK_SIZE_BYTES = 8192  # 8KB chunks for stream reading
DEFAULT_MAX_LINE_LENGTH_BYTES = 32768  # 32KB max line length
DEFAULT_STREAM_DECODE_ERRORS = "replace"  # UTF-8 decode error handling

# DoS protection constants (CWE-835: Loop with Unreachable Exit Condition)
MAX_PARSER_ITERATIONS = 10000  # Maximum iterations to prevent infinite loops
MAX_PARSER_TIMEOUT_SECONDS = 30  # Maximum wall-clock time for parsing (30 seconds)


class LiteICSContentTooLargeError(Exception):
    """Raised when ICS content exceeds size limits."""


class LiteStreamingICSParser:
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

        # Additional configuration attributes
        self.read_chunk_size_bytes = DEFAULT_READ_CHUNK_SIZE_BYTES
        self.max_line_length_bytes = DEFAULT_MAX_LINE_LENGTH_BYTES
        self.stream_decode_errors = DEFAULT_STREAM_DECODE_ERRORS

    def parse_stream(
        self,
        file_source: str | BinaryIO | TextIO,
    ) -> Generator[dict[str, Any], None, None]:
        """Parse ICS content from file stream, yielding events as they are found.

        Args:
            file_source: File path, file object, or ICS content string

        Yields:
            Dictionary containing parsed event data and metadata

        Raises:
            LiteICSContentTooLargeError: If content exceeds size limits
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
        file_obj: BinaryIO | TextIO,
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

    async def parse_from_bytes_iter(
        self,
        byte_stream: AsyncIterator[bytes],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Parse ICS content from async byte stream, yielding events as they are found.

        This method implements the streaming pipeline for parsing bytes directly from
        HTTP responses, using incremental UTF-8 decoding to handle chunk boundaries
        properly.

        Args:
            byte_stream: Async iterator yielding byte chunks

        Yields:
            Dictionary containing parsed event data and metadata

        Raises:
            LiteICSContentTooLargeError: If content exceeds size limits
        """
        try:
            # Initialize incremental UTF-8 decoder
            decoder = codecs.getincrementaldecoder("utf-8")(errors=self.stream_decode_errors)
            total_bytes_processed = 0

            logger.debug("Starting streaming parser with incremental UTF-8 decoder")

            async for chunk in byte_stream:
                if not chunk:
                    continue

                # Track total bytes for size validation
                total_bytes_processed += len(chunk)
                if total_bytes_processed > MAX_ICS_SIZE_BYTES:
                    logger.error(
                        f"Streaming content too large: {total_bytes_processed} bytes exceeds {MAX_ICS_SIZE_BYTES} limit"
                    )
                    raise LiteICSContentTooLargeError(
                        f"Streaming content too large: {total_bytes_processed} bytes exceeds {MAX_ICS_SIZE_BYTES} limit"
                    )

                # Warn about large content
                if total_bytes_processed > MAX_ICS_SIZE_WARNING:
                    logger.warning(
                        f"Large streaming content detected: {total_bytes_processed} bytes "
                        f"(threshold: {MAX_ICS_SIZE_WARNING})"
                    )

                # Decode bytes to text incrementally
                text_chunk = decoder.decode(chunk, final=False)

                if text_chunk:
                    # Process the decoded text chunk and yield events
                    for item in self._process_chunk(text_chunk):
                        yield item

            # Finalize the decoder to handle any remaining bytes
            final_text = decoder.decode(b"", final=True)
            if final_text:
                for item in self._process_chunk(final_text):
                    yield item

            # Process any remaining buffered content
            for item in self._finalize_parsing():
                yield item

            logger.debug(f"Streaming parser completed, processed {total_bytes_processed} bytes")

        except Exception as e:
            logger.exception("Failed to parse ICS stream")
            yield {"type": "error", "error": str(e), "metadata": self._calendar_metadata.copy()}

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
            event_ics += "PRODID:CalendarBot-Lite-Streaming\n"
            event_ics += "\n".join(self._current_event_lines) + "\n"
            event_ics += "END:VCALENDAR\n"

            # Parse using icalendar library
            calendar = Calendar.from_ical(event_ics)

            for component in calendar.walk():
                if component.name == "VEVENT":
                    # DEBUG: log raw VEVENT fields to validate streaming/folding behavior
                    try:
                        raw_summary = component.get("SUMMARY")
                        raw_description = component.get("DESCRIPTION")
                        raw_attendees = component.get("ATTENDEE")
                        # Normalize debug-friendly representations
                        attendees_repr = (
                            [str(raw_attendees)]
                            if not getattr(raw_attendees, "__iter__", None)
                            else [str(a) for a in raw_attendees]
                        )
                        logger.debug(
                            "Streaming parsed VEVENT raw fields - "
                            f"SUMMARY={raw_summary!r}, DESCRIPTION_present={bool(raw_description)}, "
                            f"ATTENDEE={attendees_repr}"
                        )
                    except Exception:
                        logger.debug(
                            "Streaming parsed VEVENT - failed to extract raw fields", exc_info=True
                        )

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


async def parse_ics_stream(
    stream: AsyncIterator[bytes],
    source_url: Optional[str] = None,
    read_chunk_size_bytes: int = DEFAULT_READ_CHUNK_SIZE_BYTES,
    max_line_length_bytes: int = DEFAULT_MAX_LINE_LENGTH_BYTES,
    stream_decode_errors: str = DEFAULT_STREAM_DECODE_ERRORS,
) -> LiteICSParseResult:
    """Parse ICS content from async byte stream, returning structured result.

    This is the main entry point for streaming ICS parsing that accepts AsyncIterator[bytes]
    from HTTP responses and handles chunk boundaries with incremental UTF-8 decoding.

    Args:
        stream: Async iterator yielding byte chunks from HTTP response
        source_url: Optional source URL for audit trail
        read_chunk_size_bytes: Size of chunks for stream reading
        max_line_length_bytes: Maximum line length to prevent memory issues
        stream_decode_errors: UTF-8 decode error handling ('strict' or 'replace')

    Returns:
        LiteICSParseResult with parsed events and metadata

    Raises:
        LiteICSContentTooLargeError: If content exceeds size limits
    """
    try:
        logger.debug("Starting streaming ICS parse from byte stream")

        # Create streaming parser instance with configuration
        parser = LiteStreamingICSParser(
            chunk_size=read_chunk_size_bytes,
        )
        # Set additional configuration
        parser.read_chunk_size_bytes = read_chunk_size_bytes
        parser.max_line_length_bytes = max_line_length_bytes
        parser.stream_decode_errors = stream_decode_errors

        # Create event component parser for converting raw components to LiteCalendarEvent
        # Use a minimal settings object for event parsing
        class _MinimalSettings:
            enable_rrule_expansion = True
            rrule_expansion_days = 14
            rrule_max_occurrences = 1000

        datetime_parser = LiteDateTimeParser()
        attendee_parser = LiteAttendeeParser()
        event_parser = LiteEventComponentParser(
            datetime_parser,
            attendee_parser,
            _MinimalSettings(),
        )

        # Process the stream and collect results
        events: list[LiteCalendarEvent] = []
        warnings: list[str] = []
        errors: list[str] = []
        total_components = 0
        event_count = 0
        recurring_event_count = 0
        calendar_metadata: dict[str, str] = {}

        # Parse stream with memory-bounded processing
        max_stored_events = 1000  # Increased to handle calendars with many recurring events

        # Initialize telemetry for progress tracking and circuit breaker
        telemetry = ParserTelemetry(source_url=source_url)

        # DoS protection: Track iterations and wall-clock time (CWE-835)
        iteration_count = 0
        parse_start_time = time.monotonic()

        async for item in parser.parse_from_bytes_iter(stream):
            # Check iteration limit (protects against infinite loop from malformed calendars)
            iteration_count += 1
            if iteration_count > MAX_PARSER_ITERATIONS:
                error_msg = (
                    f"Parser iteration limit exceeded ({MAX_PARSER_ITERATIONS} iterations). "
                    f"This may indicate a malformed or malicious ICS file. "
                    f"Processed {event_count} events before termination."
                )
                logger.error(
                    "SECURITY: Parser iteration limit exceeded - source_url=%s, iterations=%d, "
                    "events_parsed=%d, elapsed_time=%.2fs",
                    source_url,
                    iteration_count,
                    event_count,
                    time.monotonic() - parse_start_time,
                )
                return LiteICSParseResult(
                    success=False,
                    error_message=error_msg,
                    warnings=warnings,
                    source_url=source_url,
                    event_count=event_count,
                    recurring_event_count=recurring_event_count,
                    total_components=total_components,
                )

            # Check wall-clock timeout (protects against slow infinite loops)
            elapsed_time = time.monotonic() - parse_start_time
            if elapsed_time > MAX_PARSER_TIMEOUT_SECONDS:
                error_msg = (
                    f"Parser timeout exceeded ({MAX_PARSER_TIMEOUT_SECONDS}s elapsed). "
                    f"This may indicate a malformed or malicious ICS file. "
                    f"Processed {event_count} events in {iteration_count} iterations before timeout."
                )
                logger.error(
                    "SECURITY: Parser timeout exceeded - source_url=%s, elapsed_time=%.2fs, "
                    "iterations=%d, events_parsed=%d",
                    source_url,
                    elapsed_time,
                    iteration_count,
                    event_count,
                )
                return LiteICSParseResult(
                    success=False,
                    error_message=error_msg,
                    warnings=warnings,
                    source_url=source_url,
                    event_count=event_count,
                    recurring_event_count=recurring_event_count,
                    total_components=total_components,
                )

            telemetry.record_item()

            if item["type"] == "event":
                event = None  # Initialize to None for cleanup safety
                try:
                    # Convert raw component to LiteCalendarEvent using existing parser logic
                    component = item["component"]
                    calendar_metadata.update(item["metadata"])

                    # Check for duplicate event processing (indicates network corruption)
                    # NOTE: Events with RECURRENCE-ID share the same UID as their master event,
                    # so we need to include RECURRENCE-ID in the uniqueness check
                    event_uid = str(component.get("UID", f"no-uid-{telemetry.event_items}"))
                    recurrence_id = component.get("RECURRENCE-ID")
                    if recurrence_id:
                        # Modified instance - create unique key with UID + RECURRENCE-ID
                        if hasattr(recurrence_id, "to_ical"):
                            recurrence_id_str = recurrence_id.to_ical().decode("utf-8")
                        else:
                            recurrence_id_str = str(recurrence_id)
                    else:
                        recurrence_id_str = None

                    # Record event and check for duplicates
                    is_duplicate = telemetry.record_event(event_uid, recurrence_id_str)
                    if is_duplicate:
                        # Duplicate detected, skip processing
                        continue

                    # Parse event component using event parser
                    event = event_parser.parse_event_component(
                        component,
                        calendar_metadata.get("X-WR-TIMEZONE"),
                    )

                    if event:
                        event_count += 1
                        total_components += 1

                        if event.is_recurring:
                            recurring_event_count += 1

                        # Apply filtering and bounds
                        if event.is_busy_status and not event.is_cancelled:
                            if len(events) < max_stored_events:
                                events.append(event)
                            elif len(events) == max_stored_events:
                                telemetry.record_warning()
                                warning = (
                                    f"Event limit reached ({max_stored_events}), truncating results"
                                )
                                warnings.append(warning)

                                # Log event limit warning with telemetry data
                                telemetry.log_event_limit_reached(max_stored_events, len(events))

                                # Circuit breaker: if we're seeing repeated warnings, terminate parsing
                                if telemetry.should_break():
                                    # Return failure when corruption is detected to trigger fallback logic
                                    logger.error(
                                        "Corruption mitigation: Returning failure to preserve %d events collected before corruption",
                                        len(events),
                                    )
                                    return LiteICSParseResult(
                                        success=False,
                                        error_message=telemetry.get_circuit_breaker_error_message(),
                                        warnings=warnings,
                                        source_url=source_url,
                                        event_count=event_count,
                                        recurring_event_count=recurring_event_count,
                                        total_components=total_components,
                                    )

                except Exception as e:
                    warning = f"Failed to parse streamed event: {e}"
                    warnings.append(warning)
                    logger.warning(warning)
                finally:
                    # Ensure event object is released in all code paths to prevent memory leaks
                    # This is critical for long-running processes on memory-constrained devices (e.g., Raspberry Pi)
                    if event is not None:
                        del event

            elif item["type"] == "error":
                errors.append(item["error"])

        # Return failure if errors occurred during streaming
        if errors:
            return LiteICSParseResult(
                success=False,
                error_message="; ".join(errors),
                warnings=warnings,
                source_url=source_url,
            )

        # Log comprehensive parsing telemetry at completion
        telemetry.log_completion(len(events), len(warnings))

        return LiteICSParseResult(
            success=True,
            events=events,
            calendar_name=calendar_metadata.get("X-WR-CALNAME"),
            calendar_description=calendar_metadata.get("X-WR-CALDESC"),
            timezone=calendar_metadata.get("X-WR-TIMEZONE"),
            total_components=total_components,
            event_count=event_count,
            recurring_event_count=recurring_event_count,
            warnings=warnings,
            ics_version=calendar_metadata.get("VERSION"),
            prodid=calendar_metadata.get("PRODID"),
            raw_content=None,  # Don't store raw content for streaming
            source_url=source_url,
        )

    except Exception as e:
        logger.exception("Failed to parse ICS stream")
        return LiteICSParseResult(
            success=False,
            error_message=str(e),
            source_url=source_url,
        )
