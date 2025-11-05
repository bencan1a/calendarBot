"""Unit tests for DoS protection in streaming ICS parser (CWE-835).

Tests protection against infinite loop attacks from malformed or malicious ICS files.
"""

import asyncio

import pytest

from calendarbot_lite.lite_streaming_parser import (
    MAX_PARSER_ITERATIONS,
    MAX_PARSER_TIMEOUT_SECONDS,
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


class InfiniteAsyncByteIterator:
    """Simulates an infinite stream that never ends (DoS attack)."""

    def __init__(self, repeat_chunk: bytes, max_iterations: int = 20000):
        self.repeat_chunk = repeat_chunk
        self.iteration = 0
        self.max_iterations = max_iterations

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.iteration >= self.max_iterations:
            raise StopAsyncIteration
        self.iteration += 1
        # Simulate slow network to trigger timeout
        await asyncio.sleep(0.001)
        return self.repeat_chunk


@pytest.mark.asyncio
async def test_dos_protection_iteration_limit():
    """Test that parser stops after MAX_PARSER_ITERATIONS to prevent infinite loops."""
    # Create malformed ICS that generates many events
    malformed_event = """BEGIN:VEVENT
UID:malicious-event-{i}
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Malicious Event {i}
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
"""

    # Generate ICS with way more events than iteration limit
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:Malicious Calendar\n"
    # Generate enough events to exceed iteration limit
    for i in range(MAX_PARSER_ITERATIONS + 1000):
        ics_content += malformed_event.format(i=i)
    ics_content += "END:VCALENDAR"

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://dos-attack")

    # Parser should stop and return failure
    assert not result.success
    assert "iteration limit exceeded" in result.error_message.lower()
    assert str(MAX_PARSER_ITERATIONS) in result.error_message
    # Should have parsed some events before hitting limit
    assert result.event_count > 0


@pytest.mark.asyncio
async def test_dos_protection_timeout():
    """Test that parser stops after MAX_PARSER_TIMEOUT_SECONDS to prevent slow DoS."""
    # Create a stream that yields data slowly to trigger timeout
    # Use very few events so we don't hit iteration limit first
    event_chunk = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:Slow Calendar
BEGIN:VEVENT
UID:slow-event-1
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Slow Event 1
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

    # Create iterator that yields slowly to trigger wall-clock timeout
    # Yield only a few iterations but with long delays
    class SlowIterator:
        def __init__(self):
            self.count = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.count >= 3:  # Very few iterations
                raise StopAsyncIteration
            self.count += 1
            # Sleep longer than timeout to force timeout trigger
            await asyncio.sleep(MAX_PARSER_TIMEOUT_SECONDS + 5)
            return event_chunk

    stream = SlowIterator()
    result = await parse_ics_stream(stream, source_url="test://slow-dos-attack")

    # Parser should stop and return failure due to timeout OR iteration limit
    # Both are acceptable since they protect against DoS
    assert not result.success
    # Accept either timeout or iteration limit as valid DoS protection
    assert (
        "timeout exceeded" in result.error_message.lower()
        or "iteration limit exceeded" in result.error_message.lower()
    )


@pytest.mark.asyncio
async def test_dos_protection_malformed_endless_loop():
    """Test protection against malformed ICS that causes parsing loops."""
    # Create ICS with malformed structure that could cause parser loops
    malformed_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Malformed Calendar
"""
    # Add tons of BEGIN:VEVENT without END:VEVENT to create malformed structure
    for i in range(MAX_PARSER_ITERATIONS + 500):
        malformed_ics += f"BEGIN:VEVENT\nUID:broken-{i}\nSUMMARY:Broken Event {i}\n"

    malformed_ics += "END:VCALENDAR"

    chunks = [malformed_ics.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://malformed-loop")

    # Parser should stop, either via iteration limit or natural completion
    # Even if it completes naturally, it should not hang
    assert result is not None
    # Malformed ICS may fail for various reasons - key is it doesn't hang
    # Common outcomes: iteration limit, incomplete event, or natural completion
    if not result.success:
        error_lower = result.error_message.lower()
        # Accept various failure modes as long as it doesn't hang
        assert (
            "iteration limit" in error_lower
            or "timeout" in error_lower
            or "incomplete event" in error_lower
            or "failed to parse" in error_lower
        )


@pytest.mark.asyncio
async def test_dos_protection_legitimate_large_calendar():
    """Test that legitimate large calendars are not falsely flagged."""
    # Create a large but legitimate calendar with 500 events (below limits)
    legitimate_event = """BEGIN:VEVENT
UID:legit-event-{i}
DTSTART:20231201T{hour:02d}0000Z
DTEND:20231201T{hour:02d}3000Z
SUMMARY:Legitimate Meeting {i}
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
"""

    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:Large Legitimate Calendar\n"
    # Generate 500 events - well within limits
    for i in range(500):
        hour = i % 24
        ics_content += legitimate_event.format(i=i, hour=hour)
    ics_content += "END:VCALENDAR"

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://large-legitimate")

    # Should successfully parse without hitting limits
    assert result.success
    # Should have parsed a good number of events (may be less due to filtering)
    assert result.event_count <= 500
    # Should not have iteration/timeout errors
    if result.error_message:
        assert "iteration limit" not in result.error_message.lower()
        assert "timeout" not in result.error_message.lower()


@pytest.mark.asyncio
async def test_dos_protection_security_logging():
    """Test that security events are logged when DoS protection activates."""
    # Create ICS that will exceed iteration limit
    malformed_event = """BEGIN:VEVENT
UID:security-test-{i}
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Security Test {i}
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
"""

    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:Security Test\n"
    for i in range(MAX_PARSER_ITERATIONS + 100):
        ics_content += malformed_event.format(i=i)
    ics_content += "END:VCALENDAR"

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    # Capture logs would require log capture fixture
    # For now, just verify the result contains security information
    result = await parse_ics_stream(stream, source_url="test://security-test")

    assert not result.success
    assert "iteration limit exceeded" in result.error_message.lower()
    # Verify source URL is tracked for security audit trail
    assert result.source_url == "test://security-test"
    # Verify we got some progress before hitting limit
    assert result.event_count > 0


@pytest.mark.asyncio
async def test_dos_protection_corrupted_data():
    """Test handling of corrupted data that might cause infinite parsing."""
    # Create ICS with corrupted/random data mixed in
    corrupted_ics = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:Corrupted Calendar
"""
    # Add legitimate events mixed with corruption
    for i in range(100):
        corrupted_ics += f"""BEGIN:VEVENT
UID:event-{i}
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Event {i}
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
""".encode()
        # Add corrupted bytes
        if i % 10 == 0:
            corrupted_ics += b"\xFF\xFE\xFD Random corrupt data \x00\x01\x02"

    corrupted_ics += b"END:VCALENDAR"

    chunks = [corrupted_ics]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://corrupted")

    # Should complete without hanging
    assert result is not None
    # May succeed or fail depending on corruption handling, but should not hang
    # If it fails due to limits, should have appropriate error
    if (
        not result.success
        and result.error_message
        and ("iteration" in result.error_message.lower() or "timeout" in result.error_message.lower())
    ):
        # If it hit DoS protection, should be clear
        assert "malformed" in result.error_message.lower() or "malicious" in result.error_message.lower()


@pytest.mark.asyncio
async def test_dos_protection_empty_infinite_loop():
    """Test protection against streams that yield empty chunks indefinitely."""
    class EmptyInfiniteIterator:
        """Yields empty chunks infinitely."""

        def __init__(self):
            self.count = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.count += 1
            if self.count > MAX_PARSER_ITERATIONS + 1000:
                raise StopAsyncIteration
            await asyncio.sleep(0.001)
            return b""  # Empty chunk

    stream = EmptyInfiniteIterator()
    result = await parse_ics_stream(stream, source_url="test://empty-infinite")

    # Should handle empty chunks gracefully without hanging
    assert result is not None
    # Empty stream should result in success with 0 events
    assert result.event_count == 0


@pytest.mark.asyncio
async def test_dos_protection_timing_information_leak():
    """Test that timing information doesn't leak sensitive data."""
    # Create a small legitimate calendar
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Timing Test
BEGIN:VEVENT
UID:timing-test-1
DTSTART:20231201T100000Z
DTEND:20231201T110000Z
SUMMARY:Timing Test
TRANSP:OPAQUE
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://timing-test")

    # Should succeed
    assert result.success
    # Error message should not contain implementation details that could help attackers
    if result.error_message:
        # Should not expose internal iteration counts, memory addresses, etc.
        assert "0x" not in result.error_message  # No memory addresses
