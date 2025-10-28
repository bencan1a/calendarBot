"""Tests for streaming ICS parser functionality."""

from io import StringIO
from unittest.mock import Mock, patch

import pytest

from calendarbot.ics.models import CalendarEvent, ICSParseResult
from calendarbot.ics.parser import (
    DEFAULT_CHUNK_SIZE,
    STREAMING_THRESHOLD,
    ICSParser,
    StreamingICSParser,
)


class TestStreamingICSParser:
    """Test the StreamingICSParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = StreamingICSParser(chunk_size=64)  # Small chunks for testing

    def test_streaming_parser_initialization(self):
        """Test streaming parser initialization."""
        parser = StreamingICSParser()
        assert parser.chunk_size == DEFAULT_CHUNK_SIZE
        assert parser._line_buffer == ""
        assert parser._current_event_lines == []
        assert parser._in_event is False
        assert parser._calendar_metadata == {}

    def test_streaming_parser_custom_chunk_size(self):
        """Test streaming parser with custom chunk size."""
        parser = StreamingICSParser(chunk_size=1024)
        assert parser.chunk_size == 1024

    def test_parse_simple_ics_content_stream(self):
        """Test parsing simple ICS content as stream."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
X-WR-CALNAME:Test Calendar
BEGIN:VEVENT
UID:test-event-1
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        events = list(self.parser.parse_stream(ics_content))

        # Should get one event result
        event_items = [item for item in events if item["type"] == "event"]
        assert len(event_items) == 1

        event_item = event_items[0]
        assert event_item["type"] == "event"
        assert "component" in event_item
        assert "metadata" in event_item
        assert event_item["metadata"]["X-WR-CALNAME"] == "Test Calendar"

    def test_parse_multiple_events_stream(self):
        """Test parsing multiple events in stream."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:event-1
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Event 1
END:VEVENT
BEGIN:VEVENT
UID:event-2
DTSTART:20241201T120000Z
DTEND:20241201T130000Z
SUMMARY:Event 2
END:VEVENT
END:VCALENDAR"""

        events = list(self.parser.parse_stream(ics_content))
        event_items = [item for item in events if item["type"] == "event"]
        assert len(event_items) == 2

    def test_chunk_boundary_handling(self):
        """Test that events spanning chunk boundaries are handled correctly."""
        # Create content where event spans multiple small chunks
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:long-event-uid-that-spans-chunks
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:This is a very long event summary that will definitely span multiple chunks when using small chunk sizes for testing purposes
DESCRIPTION:This is an even longer description that contains multiple lines and lots of text to ensure that the event data spans across multiple processing chunks and tests the boundary handling logic properly
END:VEVENT
END:VCALENDAR"""

        # Use very small chunks to force boundary crossing
        small_parser = StreamingICSParser(chunk_size=32)
        events = list(small_parser.parse_stream(ics_content))

        event_items = [item for item in events if item["type"] == "event"]
        assert len(event_items) == 1

        # Verify the event was parsed correctly despite chunk boundaries
        component = event_items[0]["component"]
        assert str(component.get("UID")) == "long-event-uid-that-spans-chunks"
        assert "very long event summary" in str(component.get("SUMMARY"))

    def test_line_folding_across_chunks(self):
        """Test ICS line folding (RFC 5545) across chunk boundaries."""
        # Create content with folded lines that span chunks
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:folded-line-event
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:This is a folded
 line that continues
 on multiple lines
DESCRIPTION:Another folded
 line with more
 content
END:VEVENT
END:VCALENDAR"""

        # Use small chunks to ensure folding spans boundaries
        small_parser = StreamingICSParser(chunk_size=40)
        events = list(small_parser.parse_stream(ics_content))

        event_items = [item for item in events if item["type"] == "event"]
        assert len(event_items) == 1

        component = event_items[0]["component"]
        summary = str(component.get("SUMMARY"))
        description = str(component.get("DESCRIPTION"))

        # Verify folded lines were properly joined
        assert "This is a folded line that continues on multiple lines" in summary
        assert "Another folded line with more content" in description

    def test_incomplete_event_at_end(self):
        """Test handling of incomplete event at end of file."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:incomplete-event
DTSTART:20241201T100000Z
SUMMARY:Incomplete Event"""
        # Note: missing END:VEVENT and END:VCALENDAR

        events = list(self.parser.parse_stream(ics_content))

        # Should get an error for incomplete event
        error_items = [item for item in events if item["type"] == "error"]
        assert len(error_items) >= 1
        assert any("Incomplete event" in item["error"] for item in error_items)

    def test_calendar_metadata_extraction(self):
        """Test extraction of calendar-level metadata."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Microsoft Corporation//Outlook 16.0 MIMEDIR//EN
X-WR-CALNAME:Work Calendar
X-WR-CALDESC:My work calendar
X-WR-TIMEZONE:America/New_York
BEGIN:VEVENT
UID:test-event
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        events = list(self.parser.parse_stream(ics_content))
        event_items = [item for item in events if item["type"] == "event"]

        assert len(event_items) == 1
        metadata = event_items[0]["metadata"]

        assert metadata["VERSION"] == "2.0"
        assert "Microsoft Corporation" in metadata["PRODID"]
        assert metadata["X-WR-CALNAME"] == "Work Calendar"
        assert metadata["X-WR-CALDESC"] == "My work calendar"
        assert metadata["X-WR-TIMEZONE"] == "America/New_York"

    def test_parse_file_stream_binary(self):
        """Test parsing from binary file stream."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-binary
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Binary Test
END:VEVENT
END:VCALENDAR"""

        # Simulate binary file stream
        binary_stream = StringIO(ics_content)

        # Mock binary reading
        with patch.object(binary_stream, "read") as mock_read:
            mock_read.side_effect = [
                ics_content[:64].encode("utf-8"),
                ics_content[64:128].encode("utf-8"),
                ics_content[128:].encode("utf-8"),
                b"",  # End of file
            ]

            events = list(self.parser._parse_file_stream(binary_stream))
            event_items = [item for item in events if item["type"] == "event"]
            assert len(event_items) == 1

    def test_parsing_error_handling(self):
        """Test handling of parsing errors."""
        # Invalid ICS content
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
INVALID_COMPONENT
BEGIN:VEVENT
UID:test-event
INVALID_PROPERTY_FORMAT
END:VEVENT
END:VCALENDAR"""

        events = list(self.parser.parse_stream(ics_content))

        # Should still process valid parts and report errors for invalid parts
        event_items = [item for item in events if item["type"] == "event"]
        error_items = [item for item in events if item["type"] == "error"]

        # May get some events and some errors
        assert len(events) > 0  # Should get some results

    def test_empty_content_stream(self):
        """Test parsing empty content."""
        events = list(self.parser.parse_stream(""))
        assert len(events) == 0

    def test_content_vs_file_path_detection(self):
        """Test detection between ICS content and file path."""
        # Test ICS content detection
        ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        with patch.object(self.parser, "_parse_content_stream") as mock_content:
            mock_content.return_value = iter([])
            list(self.parser.parse_stream(ics_content))
            mock_content.assert_called_once()

        # Test file path detection (would need actual file handling in real implementation)
        file_path = "/path/to/calendar.ics"
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileNotFoundError("File not found")
            events = list(self.parser.parse_stream(file_path))
            # Should get error for file not found
            error_items = [item for item in events if item["type"] == "error"]
            assert len(error_items) > 0


class TestICSParserIntegration:
    """Test integration of streaming parser with main ICS parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Mock()
        self.parser = ICSParser(self.settings)

    def test_should_use_streaming_threshold(self):
        """Test file size threshold logic for streaming."""
        # Small content - should not use streaming
        small_content = "A" * 1000  # 1KB
        assert not self.parser._should_use_streaming(small_content)

        # Large content - should use streaming
        large_content = "A" * (STREAMING_THRESHOLD + 1000)  # >10MB
        assert self.parser._should_use_streaming(large_content)

    def test_should_use_streaming_empty_content(self):
        """Test streaming threshold with empty content."""
        assert not self.parser._should_use_streaming("")
        # Note: _should_use_streaming expects str, but handles empty case
        with pytest.raises((TypeError, AttributeError)):
            # This would fail type checking, test defensive programming
            self.parser._should_use_streaming(None)  # type: ignore

    def test_parse_ics_content_auto_selection_small(self):
        """Test automatic selection of traditional parser for small files."""
        small_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:small-event
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Small Event
END:VEVENT
END:VCALENDAR"""

        # Should use traditional parser
        with patch.object(self.parser, "_should_use_streaming", return_value=False):
            with patch.object(self.parser, "_validate_ics_size"):
                with patch("icalendar.Calendar.from_ical") as mock_from_ical:
                    mock_calendar = Mock()
                    mock_calendar.walk.return_value = []
                    mock_from_ical.return_value = mock_calendar

                    result = self.parser.parse_ics_content(small_ics)
                    mock_from_ical.assert_called_once()

    def test_parse_ics_content_auto_selection_large(self):
        """Test automatic selection of streaming parser for large files."""
        large_ics = "A" * (STREAMING_THRESHOLD + 1000)  # Force streaming

        # Mock streaming parser to return valid result
        with patch.object(self.parser, "_should_use_streaming", return_value=True):
            with patch.object(self.parser, "_parse_with_streaming") as mock_streaming:
                mock_result = ICSParseResult(success=True, events=[])
                mock_streaming.return_value = mock_result

                result = self.parser.parse_ics_content(large_ics)

                mock_streaming.assert_called_once_with(large_ics, None)
                assert result.success is True

    def test_parse_with_streaming_integration(self):
        """Test the streaming parser integration method."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
X-WR-CALNAME:Test Calendar
BEGIN:VEVENT
UID:streaming-test
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Streaming Test Event
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        # Mock the event parsing to return a valid event
        with patch.object(self.parser, "_parse_event_component") as mock_parse_event:
            mock_event = Mock(spec=CalendarEvent)
            mock_event.is_busy_status = True
            mock_event.is_cancelled = False
            mock_event.is_recurring = False
            mock_parse_event.return_value = mock_event

            result = self.parser._parse_with_streaming(ics_content, "test-source")

            assert result.success is True
            assert len(result.events) == 1
            assert result.calendar_name == "Test Calendar"
            assert result.source_url == "test-source"
            assert result.raw_content is None  # Should not store raw content for large files

    def test_parse_with_streaming_error_handling(self):
        """Test error handling in streaming parser integration."""
        invalid_ics = "INVALID ICS CONTENT"

        result = self.parser._parse_with_streaming(invalid_ics, "test-source")

        assert result.success is False
        assert result.error_message is not None
        assert result.source_url == "test-source"

    def test_parse_with_streaming_event_filtering(self):
        """Test that streaming parser applies same filtering as traditional parser."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:busy-event
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Busy Event
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
UID:free-event
DTSTART:20241201T120000Z
DTEND:20241201T130000Z
SUMMARY:Free Event
TRANSP:TRANSPARENT
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""

        with patch.object(self.parser, "_parse_event_component") as mock_parse_event:
            # First event - busy
            busy_event = Mock(spec=CalendarEvent)
            busy_event.is_busy_status = True
            busy_event.is_cancelled = False
            busy_event.is_recurring = False

            # Second event - free/cancelled
            free_event = Mock(spec=CalendarEvent)
            free_event.is_busy_status = False
            free_event.is_cancelled = True
            free_event.is_recurring = False

            mock_parse_event.side_effect = [busy_event, free_event]

            result = self.parser._parse_with_streaming(ics_content)

            # Should only include the busy event, filtering out free/cancelled
            assert result.success is True
            assert len(result.events) == 1  # Only busy event included

    def test_parse_ics_content_optimized_method(self):
        """Test the new optimized parse method."""
        test_content = "A" * 1000  # Small content

        with patch.object(self.parser, "parse_ics_content") as mock_traditional:
            mock_result = ICSParseResult(success=True, events=[])
            mock_traditional.return_value = mock_result

            result = self.parser.parse_ics_content_optimized(test_content, "test-url")

            mock_traditional.assert_called_once_with(test_content, "test-url")
            assert result.success is True

    def test_empty_content_handling(self):
        """Test handling of empty content in main parser."""
        result = self.parser.parse_ics_content("")
        assert result.success is False
        assert result.error_message is not None
        assert "Empty ICS content" in result.error_message

        result = self.parser.parse_ics_content("   ")
        assert result.success is False
        assert result.error_message is not None
        assert "Empty ICS content" in result.error_message


class TestStreamingPerformance:
    """Test performance characteristics of streaming parser."""

    def test_memory_efficiency_large_file(self):
        """Test that streaming parser doesn't load entire file into memory."""
        # Create a large ICS file content
        large_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
"""

        # Add many events to make it large
        for i in range(1000):
            large_ics += f"""BEGIN:VEVENT
UID:event-{i}
DTSTART:20241201T{i:06d}Z
DTEND:20241201T{i:06d}Z
SUMMARY:Event {i} with some description text to increase size
DESCRIPTION:This is event number {i} with a longer description to make the file larger and test memory efficiency of the streaming parser implementation
END:VEVENT
"""

        large_ics += "END:VCALENDAR"

        # Test that streaming parser can handle it without errors
        parser = StreamingICSParser(chunk_size=8192)
        events = list(parser.parse_stream(large_ics))

        event_items = [item for item in events if item["type"] == "event"]
        assert len(event_items) == 1000  # Should process all events

    def test_chunk_size_impact(self):
        """Test that different chunk sizes produce same results."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:chunk-test
DTSTART:20241201T100000Z
DTEND:20241201T110000Z
SUMMARY:Chunk Size Test Event
END:VEVENT
END:VCALENDAR"""

        # Test with different chunk sizes
        chunk_sizes = [32, 64, 128, 256, 1024]
        results = []

        for chunk_size in chunk_sizes:
            parser = StreamingICSParser(chunk_size=chunk_size)
            events = list(parser.parse_stream(ics_content))
            event_items = [item for item in events if item["type"] == "event"]
            results.append(len(event_items))

        # All chunk sizes should produce the same number of events
        assert all(count == 1 for count in results)


if __name__ == "__main__":
    pytest.main([__file__])
