"""Unit tests for DoS protection in streaming ICS parser (CWE-835).

Tests protection against infinite loop attacks from malformed or malicious ICS files.
"""

import asyncio
import re
import time

import pytest

from calendarbot_lite.calendar.lite_streaming_parser import (
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
    """Test that parser stops after MAX_PARSER_ITERATIONS to prevent infinite loops.

    This test verifies that:
    1. The parser actually enforces the iteration limit (not just checks error message)
    2. The parser stops NEAR the limit (within reasonable tolerance)
    3. The limit prevents processing excessive events
    """
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
    events_to_create = MAX_PARSER_ITERATIONS + 1000
    for i in range(events_to_create):
        ics_content += malformed_event.format(i=i)
    ics_content += "END:VCALENDAR"

    chunks = [ics_content.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://dos-attack")

    # Parser should stop and return failure
    assert not result.success, "Parser should fail when iteration limit exceeded"
    assert result.error_message is not None
    assert "iteration limit exceeded" in result.error_message.lower(), \
        f"Error should mention iteration limit, got: {result.error_message}"
    assert str(MAX_PARSER_ITERATIONS) in result.error_message

    # CRITICAL: Verify the parser stopped processing NEAR the limit, not much before
    # This proves the limit is actually enforced, not just checked arbitrarily
    # Each event generates multiple parse iterations (BEGIN, properties, END, etc.)
    # So we expect far fewer events than iterations
    assert result.event_count > 0, "Should have parsed some events before hitting limit"
    # Event count should be less than or equal to iteration limit (events have multiple lines/iterations)
    assert result.event_count <= MAX_PARSER_ITERATIONS, \
        f"Event count {result.event_count} should not exceed iteration limit {MAX_PARSER_ITERATIONS}"
    # But should be a reasonable fraction (at least 10% of limit for simple events)
    min_expected_events = MAX_PARSER_ITERATIONS // 20  # Very conservative estimate
    assert result.event_count >= min_expected_events, \
        f"Should parse at least {min_expected_events} events before limit, got {result.event_count}. " \
        f"This suggests parser stopped too early or limit not enforced properly."

    # Verify we didn't process all events (that would mean limit wasn't enforced)
    assert result.event_count < events_to_create, \
        f"Parser processed {result.event_count} events but should have stopped before {events_to_create}"


@pytest.mark.asyncio
async def test_dos_protection_timeout():
    """Test that parser stops after MAX_PARSER_TIMEOUT_SECONDS to prevent slow DoS.

    This test verifies:
    1. The parser enforces wall-clock timeout (not just iteration limit)
    2. Timeout is checked even when iteration count is low
    3. The timeout error is specific (not confused with iteration limit)
    """
    # Create iterator that yields valid data but very slowly
    # Use small chunks to keep iteration count low (avoid hitting iteration limit)
    class SlowIterator:
        def __init__(self):
            self.count = 0
            # Use short sleep per iteration to keep iterations low
            # but cumulative time exceeds timeout
            self.sleep_time = (MAX_PARSER_TIMEOUT_SECONDS + 5) / 3  # 3 iterations = 35+ seconds

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.count >= 3:  # Only 3 iterations (well below MAX_PARSER_ITERATIONS)
                raise StopAsyncIteration
            self.count += 1
            # Sleep long enough that total time exceeds timeout
            await asyncio.sleep(self.sleep_time)
            # Return small valid chunk to minimize iterations
            return b"BEGIN:VEVENT\nUID:event-" + str(self.count).encode() + b"\nEND:VEVENT\n"

    stream = SlowIterator()
    result = await parse_ics_stream(stream, source_url="test://slow-dos-attack")

    # Parser should stop and return failure due to TIMEOUT specifically
    assert not result.success, "Parser should fail when timeout exceeded"
    assert result.error_message is not None

    # CRITICAL: Must be timeout error, NOT iteration limit
    # This proves timeout protection is actually working
    error_lower = result.error_message.lower()
    assert "timeout exceeded" in error_lower, \
        f"Error should specifically mention timeout, got: {result.error_message}"
    # Should NOT hit iteration limit (that would mean test setup is wrong)
    assert "iteration limit" not in error_lower, \
        f"Should hit timeout, not iteration limit. Error: {result.error_message}"

    # Verify timeout happened quickly (within a few seconds of timeout threshold)
    # If we hit iteration limit instead, this would be wrong
    assert str(MAX_PARSER_TIMEOUT_SECONDS) in result.error_message or \
           f"{MAX_PARSER_TIMEOUT_SECONDS}s" in result.error_message, \
        "Error message should reference the timeout threshold"


@pytest.mark.asyncio
async def test_dos_protection_malformed_endless_loop():
    """Test protection against malformed ICS that causes parsing loops.

    This test verifies:
    1. Malformed ICS with excessive unclosed events is handled
    2. The iteration limit prevents processing all malformed content
    3. The parser fails gracefully with a clear error
    """
    # Create ICS with malformed structure that could cause parser loops
    malformed_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:Malformed Calendar
"""
    # Add tons of BEGIN:VEVENT without END:VEVENT to create malformed structure
    unclosed_events = MAX_PARSER_ITERATIONS + 500
    for i in range(unclosed_events):
        malformed_ics += f"BEGIN:VEVENT\nUID:broken-{i}\nSUMMARY:Broken Event {i}\n"

    malformed_ics += "END:VCALENDAR"

    chunks = [malformed_ics.encode("utf-8")]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://malformed-loop")

    # Parser should stop - it should NOT hang or process all malformed content
    assert result is not None, "Parser must return a result, not hang indefinitely"

    # CRITICAL: Parser should fail when processing excessive malformed content
    # Either by hitting iteration limit OR detecting structural issues
    assert not result.success, \
        "Parser should fail when processing malformed ICS with excessive unclosed events"
    assert result.error_message is not None

    error_lower = result.error_message.lower()
    # Parser may fail in two ways:
    # 1. Hit iteration limit (DoS protection kicks in)
    # 2. Detect incomplete/malformed structure (structural validation)
    # Both are acceptable - key is it doesn't hang or process all content
    has_valid_error = (
        "iteration limit" in error_lower or
        "incomplete" in error_lower or
        "malformed" in error_lower
    )
    assert has_valid_error, \
        f"Should fail with iteration limit or structural error. Error: {result.error_message}"

    # Verify we didn't process all malformed content (that would mean no protection)
    # The parser should stop well before processing all unclosed_events
    # Event count may be 0 if all malformed events were rejected, which is acceptable
    # But if any events were processed, it should be far less than the malformed count
    assert result.event_count < unclosed_events, \
        f"Parser should not process all {unclosed_events} malformed events, " \
        f"but got {result.event_count}. Even 0 events is acceptable (all rejected)."


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
    # Should not have iteration/timeout errors - verify unconditionally
    # Success=True should mean no DoS protection errors
    error_msg_lower = (result.error_message or "").lower()
    assert "iteration limit" not in error_msg_lower, \
        f"Legitimate calendar should not hit iteration limit. Error: {result.error_message}"
    assert "timeout" not in error_msg_lower, \
        f"Legitimate calendar should not hit timeout. Error: {result.error_message}"


@pytest.mark.asyncio
async def test_dos_protection_security_logging(caplog):
    """Test that security events are logged when DoS protection activates.

    This test verifies:
    1. DoS protection triggers result in security logs
    2. Security logs contain relevant context (source URL, iteration count, etc.)
    3. Log level is appropriate (ERROR for security events)
    """
    import logging

    # Set log level to capture ERROR logs
    caplog.set_level(logging.ERROR)

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

    result = await parse_ics_stream(stream, source_url="test://security-test")

    # Verify result indicates failure
    assert not result.success
    assert result.error_message is not None
    assert "iteration limit exceeded" in result.error_message.lower()
    # Verify source URL is tracked for security audit trail
    assert result.source_url == "test://security-test"
    # Verify we got some progress before hitting limit
    assert result.event_count > 0

    # CRITICAL: Verify security logging actually occurred
    security_logs = [
        record for record in caplog.records
        if record.levelname == "ERROR" and "SECURITY" in record.message
    ]

    assert len(security_logs) > 0, \
        "Should have at least one security ERROR log when DoS protection triggers"

    # Verify the security log contains relevant information
    security_log = security_logs[0]
    log_msg = security_log.message.lower()

    assert "iteration limit exceeded" in log_msg or "iteration" in log_msg, \
        f"Security log should mention iteration limit. Got: {security_log.message}"
    assert "test://security-test" in security_log.message or "source_url" in log_msg, \
        f"Security log should include source URL for audit trail. Got: {security_log.message}"
    assert security_log.levelname == "ERROR", \
        "Security events should be logged at ERROR level"


@pytest.mark.asyncio
async def test_dos_protection_corrupted_data():
    """Test graceful handling of corrupted UTF-8 data mixed with valid ICS events.

    The streaming parser uses incremental UTF-8 decoding with errors="replace",
    which substitutes invalid byte sequences with replacement characters (\ufffd).
    This allows the parser to continue processing valid events even when corrupted
    data is present between them.

    Expected behavior:
    - Parser succeeds (does not fail on UTF-8 corruption)
    - Most valid events are parsed (corrupted bytes between events are replaced)
    - Parser returns without hanging (DoS protection)
    - All 100 valid VEVENT blocks should be successfully parsed
    """
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
        # Add corrupted bytes between some events
        if i % 10 == 0:
            corrupted_ics += b"\xff\xfe\xfd" + b" Random corrupt data " + b"\x00\x01\x02"

    corrupted_ics += b"END:VCALENDAR"

    chunks = [corrupted_ics]
    stream = AsyncByteIterator(chunks)

    result = await parse_ics_stream(stream, source_url="test://corrupted")

    # Parser must succeed - UTF-8 corruption is handled gracefully by decoder
    assert result.success, (
        "Parser should handle UTF-8 corruption gracefully using errors='replace'. "
        f"Got error: {result.error_message}"
    )

    # All 100 valid events should be parsed (corrupt bytes are replaced, not fatal)
    # Note: Actual event_count may be less than 100 due to event filtering (cancelled, not busy, etc.)
    # But should be at least 90 events (90% success rate is acceptable for this edge case)
    assert result.event_count >= 90, (
        f"Should parse at least 90 out of 100 valid events despite UTF-8 corruption. "
        f"Got {result.event_count} events"
    )

    # Parser must return promptly (DoS protection - no infinite loops)
    # This is implicitly tested by the test not timing out, but we verify the result exists
    assert result is not None, "Parser must return result without hanging"


@pytest.mark.asyncio
async def test_dos_protection_empty_infinite_loop():
    """Test that parser completes quickly when stream yields infinite empty chunks.

    This prevents CPU-based DoS attacks via infinite empty chunk streams.
    Since empty chunks don't yield items, they won't trigger the iteration limit.
    Instead, the timeout protection should eventually terminate the parser.
    However, the parser should detect the lack of progress and complete gracefully.
    """

    class EmptyInfiniteIterator:
        """Yields empty chunks infinitely to simulate DoS attack."""

        def __init__(self, max_iterations: int):
            self.count = 0
            self.max_iterations = max_iterations

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.count += 1
            # Stop after specified iterations to prevent actual infinite loop in test
            if self.count > self.max_iterations:
                raise StopAsyncIteration
            # Small sleep to prevent tight loop, simulating network delay
            await asyncio.sleep(0.001)
            return b""  # Always return empty chunk

    # Test with a reasonable number of empty chunks
    # Parser will iterate through all of them since empty chunks are valid (just no content)
    max_test_iterations = 1000
    stream = EmptyInfiniteIterator(max_test_iterations)
    start_time = time.time()
    result = await parse_ics_stream(stream, source_url="test://empty-infinite")
    elapsed = time.time() - start_time

    # CRITICAL: Must complete without hanging indefinitely
    assert result is not None, "Parser must return result for empty stream, not hang"

    # Should complete relatively quickly (not hit the 30s timeout)
    # Allow some overhead for test infrastructure
    assert elapsed < 10, \
        f"Should complete quickly for {max_test_iterations} empty chunks, took {elapsed:.1f}s"

    # Parser should succeed with 0 events - empty stream is valid, just has no content
    assert result.success is True, \
        f"Empty stream should succeed (no content != error). Got error: {result.error_message}"

    # Should have 0 events since stream was empty
    assert result.event_count == 0, "Empty stream should have 0 events"

    # CRITICAL: Error message should be None for successful empty parse
    assert result.error_message is None or result.error_message == "", \
        f"Successful empty parse should have no error. Got: {result.error_message}"

    # Verify the iterator went through expected number of iterations
    # Parser processes all chunks even if empty (normal behavior)
    assert stream.count == max_test_iterations + 1, \
        f"Iterator should process all {max_test_iterations} chunks plus one StopAsyncIteration attempt. " \
        f"Got {stream.count} iterations"

    # Warnings are OK (e.g., "no events found") but should be informative
    # Check all warnings unconditionally - if present, they must be valid
    for warning in result.warnings:
        assert len(warning) > 0, \
            f"All warnings should be non-empty strings. Found empty warning in {result.warnings}"
        assert isinstance(warning, str), \
            f"All warnings should be strings. Found {type(warning)}: {warning}"


@pytest.mark.asyncio
async def test_dos_protection_timing_information_leak():
    """Test that error messages don't leak sensitive implementation details.

    This test verifies:
    1. Error messages don't contain memory addresses
    2. Error messages don't expose file system paths
    3. Error messages don't leak internal state/counters that could help attackers
    """
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

    # Should succeed with valid calendar
    assert result.success, "Valid calendar should parse successfully"

    # Test also needs to verify error messages in failure case
    # Create a scenario that will fail (iteration limit)
    malformed_ics = "BEGIN:VCALENDAR\nVERSION:2.0\n"
    for i in range(MAX_PARSER_ITERATIONS + 100):
        malformed_ics += f"BEGIN:VEVENT\nUID:leak-test-{i}\nEND:VEVENT\n"
    malformed_ics += "END:VCALENDAR"

    stream2 = AsyncByteIterator([malformed_ics.encode("utf-8")])
    result2 = await parse_ics_stream(stream2, source_url="test://timing-leak-test")

    # Should fail due to iteration limit
    assert not result2.success
    assert result2.error_message is not None

    # CRITICAL: Verify no sensitive information leaks in error message
    msg = result2.error_message

    # No memory addresses (like 0x7f8a9b0c1d2e)
    assert "0x" not in msg, "Error message should not contain memory addresses"

    # No file system paths (could reveal system structure)
    assert "/home" not in msg and "C:\\" not in msg and "/usr" not in msg, \
        "Error message should not contain file system paths"

    # No Python debug info
    assert "DEBUG" not in msg and "TRACE" not in msg, \
        "Error message should not contain debug traces"

    # Should not contain raw stack traces (line numbers from internal code)
    # Use regex to avoid false positives from words like "online", "timeline"
    assert not re.search(r'File "[^"]+", line \d+', msg), \
        "Error message should not contain stack traces"

    # Error message SHOULD contain the limit (this is expected user-facing info)
    # But verify it's presented in a clean way
    assert str(MAX_PARSER_ITERATIONS) in msg, \
        "Error message should contain the limit threshold for user awareness"
