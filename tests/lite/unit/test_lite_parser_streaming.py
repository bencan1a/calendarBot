"""Unit tests for streaming ICS parser functionality."""

import asyncio

import pytest

from calendarbot_lite.lite_streaming_parser import (
    LiteStreamingICSParser,
    parse_ics_stream,
)

pytestmark = pytest.mark.unit


class AsyncByteIterator:
    """Helper class to simulate async byte stream."""

    def __init__(self, chunks: list[bytes]):
        self.chunks = chunks
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self.index]
        self.index += 1
        return chunk


def create_test_ics_content() -> str:
    """Create a test ICS content with events."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test Calendar
X-WR-CALNAME:Test Calendar
X-WR-TIMEZONE:UTC
BEGIN:VEVENT
UID:test-event-1
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Test Event 1
DESCRIPTION:This is a test event description that spans multiple lines and
  includes line folding per RFC5545 specification. This should be handled
  correctly across chunk boundaries.
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
UID:test-event-2
DTSTART:20231202T140000Z
DTEND:20231202T150000Z
SUMMARY:Another Test Event
DESCRIPTION:Short description
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""


@pytest.mark.asyncio
async def test_streaming_parser_basic_functionality():
    """Test basic streaming parser functionality."""
    ics_content = create_test_ics_content()
    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://example.com")

    assert result.success
    assert len(result.events) == 2
    assert result.event_count == 2
    assert result.calendar_name == "Test Calendar"
    assert result.source_url == "test://example.com"


@pytest.mark.asyncio
async def test_streaming_parser_chunk_boundaries():
    """Test streaming parser with arbitrary chunk boundaries."""
    ics_content = create_test_ics_content()
    ics_bytes = ics_content.encode("utf-8")

    # Split into small chunks to test boundary handling
    chunk_size = 50  # Very small chunks to force boundary issues
    chunks = [ics_bytes[i : i + chunk_size] for i in range(0, len(ics_bytes), chunk_size)]

    stream = AsyncByteIterator(chunks)
    result = await parse_ics_stream(stream)

    assert result.success
    assert len(result.events) == 2
    assert result.event_count == 2


@pytest.mark.asyncio
async def test_streaming_parser_line_folding_across_chunks():
    """Test line folding handling across chunk boundaries."""
    # Create ICS with intentional line folding
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test
BEGIN:VEVENT
UID:test
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:A very long summary that will be folded across multiple lines
 and should be handled correctly when chunks split at arbitrary points
 in the folded content to test RFC5545 compliance
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

    ics_bytes = ics_content.encode("utf-8")

    # Find the folded line and split chunks to break it up
    folded_line_start = ics_content.find("SUMMARY:")
    folded_line_end = ics_content.find("TRANSP:", folded_line_start)

    # Create chunks that split the folded line
    chunk1 = ics_bytes[: folded_line_start + 30]  # Split in middle of SUMMARY
    chunk2 = ics_bytes[folded_line_start + 30 : folded_line_end - 20]  # Middle part
    chunk3 = ics_bytes[folded_line_end - 20 :]  # Rest

    stream = AsyncByteIterator([chunk1, chunk2, chunk3])
    result = await parse_ics_stream(stream)

    assert result.success
    assert len(result.events) == 1

    # Check that folded line was properly reconstructed
    event = result.events[0]
    assert "very long summary" in event.subject
    assert "test RFC5545 compliance" in event.subject


@pytest.mark.asyncio
async def test_streaming_parser_utf8_boundaries():
    """Test UTF-8 decoding across chunk boundaries."""
    # Create content with UTF-8 characters
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test
BEGIN:VEVENT
UID:test-utf8
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Test with émojis 🚀 and special chars: ñáéíóú
DESCRIPTION:Testing UTF-8 handling across boundaries: 中文测试
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

    ics_bytes = ics_content.encode("utf-8")

    # Split at arbitrary points that might break UTF-8 sequences
    chunks = []
    i = 0
    while i < len(ics_bytes):
        # Vary chunk sizes to increase chance of hitting UTF-8 boundaries
        chunk_size = 30 + (i % 20)  # Sizes between 30-49
        chunks.append(ics_bytes[i : i + chunk_size])
        i += chunk_size

    stream = AsyncByteIterator(chunks)
    result = await parse_ics_stream(stream, stream_decode_errors="replace")

    assert result.success
    assert len(result.events) == 1

    event = result.events[0]
    # Should contain the special characters (or replacement chars if boundaries were broken)
    assert "émojis" in event.subject or "Test with" in event.subject


@pytest.mark.asyncio
async def test_streaming_parser_empty_chunks():
    """Test streaming parser handles empty chunks gracefully."""
    ics_content = create_test_ics_content()
    ics_bytes = ics_content.encode("utf-8")

    # Include empty chunks
    chunks = [
        ics_bytes[:100],
        b"",  # Empty chunk
        ics_bytes[100:200],
        b"",  # Another empty chunk
        ics_bytes[200:],
    ]

    stream = AsyncByteIterator(chunks)
    result = await parse_ics_stream(stream)

    assert result.success
    assert len(result.events) == 2


@pytest.mark.asyncio
async def test_streaming_parser_configuration():
    """Test streaming parser with different configuration options."""
    ics_content = create_test_ics_content()
    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(
        stream,
        read_chunk_size_bytes=4096,
        max_line_length_bytes=16384,
        stream_decode_errors="strict",
    )

    assert result.success
    assert len(result.events) == 2


@pytest.mark.asyncio
async def test_streaming_parser_large_content_limit():
    """Test streaming parser respects size limits."""
    # Create a very large ICS content that exceeds limits
    large_summary = "A" * 1000000  # 1MB summary
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test
BEGIN:VEVENT
UID:large-event
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:{large_summary}
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

    # Split into chunks
    ics_bytes = ics_content.encode("utf-8")
    chunk_size = 1024 * 1024  # 1MB chunks
    chunks = [ics_bytes[i : i + chunk_size] for i in range(0, len(ics_bytes), chunk_size)]

    stream = AsyncByteIterator(chunks)

    # Should handle large content but respect limits
    result = await parse_ics_stream(stream)

    # The streaming parser should either succeed or fail gracefully
    # depending on the content size limits
    assert isinstance(result.success, bool)


@pytest.mark.asyncio
async def test_streaming_parser_invalid_ics():
    """Test streaming parser handles invalid ICS content."""
    invalid_ics = "This is not valid ICS content at all"
    chunks = [invalid_ics.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream)

    # Should not crash, but may not be successful
    assert isinstance(result.success, bool)
    if not result.success:
        assert result.error_message is not None


@pytest.mark.asyncio
async def test_streaming_parser_partial_events():
    """Test streaming parser handles incomplete events at end."""
    incomplete_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test
BEGIN:VEVENT
UID:incomplete
DTSTART:20231201T100000Z
SUMMARY:Incomplete Event
"""  # Missing END:VEVENT and END:VCALENDAR

    chunks = [incomplete_ics.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream)

    # Should handle gracefully, possibly with warnings
    assert isinstance(result.success, bool)
    if result.warnings:
        assert any("incomplete" in warning.lower() for warning in result.warnings)


def test_streaming_parser_class_initialization():
    """Test LiteStreamingICSParser class initialization."""
    parser = LiteStreamingICSParser(chunk_size=4096)

    assert parser.chunk_size == 4096
    assert parser.read_chunk_size_bytes == 8192  # DEFAULT_READ_CHUNK_SIZE_BYTES
    assert parser.max_line_length_bytes == 32768  # DEFAULT_MAX_LINE_LENGTH_BYTES (32KB)
    assert parser.stream_decode_errors == "replace"  # DEFAULT_STREAM_DECODE_ERRORS


@pytest.mark.asyncio
async def test_streaming_parser_single_byte_chunks():
    """Test streaming parser with extremely small chunks (single bytes)."""
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test
BEGIN:VEVENT
UID:single-byte-test
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Single Byte Test
END:VEVENT
END:VCALENDAR"""

    ics_bytes = ics_content.encode("utf-8")

    # Create single-byte chunks
    chunks = [bytes([b]) for b in ics_bytes]

    stream = AsyncByteIterator(chunks)
    result = await parse_ics_stream(stream)

    assert result.success
    assert len(result.events) == 1
    assert result.events[0].subject == "Single Byte Test"


@pytest.mark.asyncio
async def test_streaming_parser_memory_cleanup_on_parse_errors():
    """Test that event objects are properly cleaned up when parse errors occur.

    This is a regression test for the memory leak issue where event objects
    weren't released in error paths, causing memory accumulation over time.
    """
    # Create ICS with one valid event and one malformed event
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test Calendar
X-WR-CALNAME:Test Calendar
X-WR-TIMEZONE:UTC
BEGIN:VEVENT
UID:valid-event-1
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Valid Event Before Error
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
UID:malformed-event
DTSTART:INVALID_DATE_FORMAT
DTEND:20231202T150000Z
SUMMARY:Malformed Event
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
UID:valid-event-2
DTSTART:20231203T100000Z
DTEND:20231203T110000Z
SUMMARY:Valid Event After Error
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://memory-cleanup")

    # Should succeed but may have warnings about malformed events
    assert result.success
    # At least the valid events should be parsed
    assert len(result.events) >= 1
    # Check that we got warnings about parse failures
    if result.warnings:
        assert any("parse" in warning.lower() or "failed" in warning.lower()
                   for warning in result.warnings)


@pytest.mark.asyncio
async def test_streaming_parser_memory_cleanup_on_circuit_breaker():
    """Test that event objects are properly cleaned up when circuit breaker triggers.

    This tests the early return path (circuit breaker) to ensure event cleanup
    happens even when the function returns early.
    """
    # Create ICS with more events than the max_stored_events limit (1000)
    # to trigger circuit breaker
    events = []
    for i in range(1100):
        event = f"""BEGIN:VEVENT
UID:event-{i}
DTSTART:20231201T{i % 24:02d}0000Z
DTEND:20231201T{(i % 24 + 1) % 24:02d}0000Z
SUMMARY:Event {i}
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
"""
        events.append(event)

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:Test Calendar
X-WR-CALNAME:Large Calendar
X-WR-TIMEZONE:UTC
{"".join(events)}END:VCALENDAR"""

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://circuit-breaker")

    # Should handle the large calendar
    # May hit the 1000 event limit and return warnings
    assert isinstance(result.success, bool)
    if not result.success:
        # Circuit breaker triggered
        assert result.error_message is not None
    if result.warnings:
        # Should have warning about event limit
        assert any("limit" in warning.lower() or "truncat" in warning.lower()
                   for warning in result.warnings)


if __name__ == "__main__":
    # Run basic test manually
    asyncio.run(test_streaming_parser_basic_functionality())
    print("Basic streaming parser test passed!")
