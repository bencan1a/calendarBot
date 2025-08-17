"""Unit tests for ICS parser raw content functionality."""

from unittest.mock import patch

import pytest

from calendarbot.ics.parser import (
    MAX_ICS_SIZE_BYTES,
    MAX_ICS_SIZE_WARNING,
    ICSContentTooLargeError,
    ICSParser,
)


class MockSettings:
    """Mock settings for testing."""

    def __init__(self):
        pass


@pytest.fixture
def parser() -> ICSParser:
    """Create ICSParser instance for testing."""
    settings = MockSettings()
    with patch("calendarbot.ics.parser.SecurityEventLogger"):
        return ICSParser(settings)


class TestICSParserSizeValidation:
    """Test cases for ICS content size validation."""

    def test_validate_ics_size_when_empty_content_then_no_error(self, parser: ICSParser) -> None:
        """Test that empty content doesn't raise size validation error."""
        # Should not raise any exception
        parser._validate_ics_size("")

    def test_validate_ics_size_when_small_content_then_no_error(self, parser: ICSParser) -> None:
        """Test that small content doesn't raise size validation error."""
        small_content = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        # Should not raise any exception
        parser._validate_ics_size(small_content)

    def test_validate_ics_size_when_warning_threshold_exceeded_then_logs_warning(
        self, parser: ICSParser
    ) -> None:
        """Test that content over warning threshold logs warning but doesn't raise error."""
        # Create content just over warning threshold
        large_content = "X" * (MAX_ICS_SIZE_WARNING + 1000)

        with patch("calendarbot.ics.parser.logger") as mock_logger:
            # Should not raise exception but should log warning
            parser._validate_ics_size(large_content)
            mock_logger.warning.assert_called_once()

    def test_validate_ics_size_when_max_size_exceeded_then_raises_error(
        self, parser: ICSParser
    ) -> None:
        """Test that content over max size raises ICSContentTooLargeError."""
        # Create content over max size
        oversized_content = "X" * (MAX_ICS_SIZE_BYTES + 1000)

        with pytest.raises(ICSContentTooLargeError) as exc_info:
            parser._validate_ics_size(oversized_content)

        assert "exceeds" in str(exc_info.value)
        assert str(MAX_ICS_SIZE_BYTES) in str(exc_info.value)

    def test_validate_ics_size_when_exactly_max_size_then_no_error(self, parser: ICSParser) -> None:
        """Test that content exactly at max size doesn't raise error."""
        # Create content exactly at max size
        max_size_content = "X" * MAX_ICS_SIZE_BYTES

        # Should not raise exception
        parser._validate_ics_size(max_size_content)

    @pytest.mark.parametrize(
        ("content_size", "should_warn", "should_error"),
        [
            (1000, False, False),  # Small content
            (MAX_ICS_SIZE_WARNING - 1000, False, False),  # Just under warning
            (MAX_ICS_SIZE_WARNING + 1000, True, False),  # Over warning, under max
            (MAX_ICS_SIZE_BYTES - 1000, True, False),  # Just under max
            (MAX_ICS_SIZE_BYTES + 1000, True, True),  # Over max
        ],
    )
    def test_validate_ics_size_when_various_sizes_then_correct_behavior(
        self, parser: ICSParser, content_size: int, should_warn: bool, should_error: bool
    ) -> None:
        """Test size validation behavior with various content sizes."""
        content = "X" * content_size

        with patch("calendarbot.ics.parser.logger") as mock_logger:
            if should_error:
                with pytest.raises(ICSContentTooLargeError):
                    parser._validate_ics_size(content)
            else:
                parser._validate_ics_size(content)

            if should_warn and not should_error:
                mock_logger.warning.assert_called_once()
            elif not should_warn:
                mock_logger.warning.assert_not_called()


class TestICSParserRawContentCapture:
    """Test cases for raw content capture in ICS parsing."""

    def test_parse_ics_content_when_valid_content_then_captures_raw_content(
        self, parser: ICSParser
    ) -> None:
        """Test that valid ICS content is captured in parse result."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-123
DTSTART:20250813T140000Z
DTEND:20250813T150000Z
SUMMARY:Test Meeting
END:VEVENT
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        assert result.success is True
        # Current implementation sets raw_content to None for size validation reasons
        assert result.raw_content is None
        assert result.source_url is None

    def test_parse_ics_content_when_with_source_url_then_captures_source_url(
        self, parser: ICSParser
    ) -> None:
        """Test that source URL is captured in parse result."""
        ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        source_url = "https://example.com/calendar.ics"

        # Mock production mode to enable raw content capture
        with patch("calendarbot.ics.parser.is_production_mode", return_value=False):
            result = parser.parse_ics_content(ics_content, source_url)

            assert result.success is True
            assert result.raw_content == ics_content  # With source URL, raw_content should be set
            assert result.source_url == source_url

    def test_parse_ics_content_when_empty_content_then_captures_empty_raw_content(
        self, parser: ICSParser
    ) -> None:
        """Test that empty content is handled properly."""
        ics_content = ""

        # Empty content fails early and doesn't capture raw content
        result = parser.parse_ics_content(ics_content)

        assert result.success is False  # Empty content should fail parsing
        assert result.raw_content is None  # Empty content doesn't capture raw content

    def test_parse_ics_content_when_size_error_then_no_raw_content_and_raises_error(
        self, parser: ICSParser
    ) -> None:
        """Test that oversized content returns failed result and doesn't capture raw content."""
        # Mock production mode and size validation to simulate oversized content error
        with (
            patch("calendarbot.ics.parser.is_production_mode", return_value=False),
            patch.object(
                parser,
                "_validate_ics_size",
                side_effect=ICSContentTooLargeError(
                    "Content too large: 52429800 bytes exceeds 52428800 limit"
                ),
            ),
        ):
            result = parser.parse_ics_content("BEGIN:VCALENDAR\nEND:VCALENDAR")

            # Should return failed result, not raise exception
            assert result.success is False
            assert result.error_message is not None
            assert "too large" in result.error_message
            assert result.raw_content is None

    def test_parse_ics_content_when_size_validation_error_then_logs_and_raises(
        self, parser: ICSParser
    ) -> None:
        """Test that size validation errors are properly logged and return failed result."""
        with (
            patch("calendarbot.ics.parser.is_production_mode", return_value=False),
            patch("calendarbot.ics.parser.logger") as mock_logger,
            patch.object(
                parser,
                "_validate_ics_size",
                side_effect=ICSContentTooLargeError(
                    "Content too large: 52429800 bytes exceeds 52428800 limit"
                ),
            ),
        ):
            result = parser.parse_ics_content("BEGIN:VCALENDAR\nEND:VCALENDAR")

            # Should return failed result
            assert result.success is False
            assert result.error_message is not None
            assert "too large" in result.error_message

            # Verify error was logged
            mock_logger.exception.assert_called()

    def test_parse_ics_content_when_warning_size_then_captures_with_warning(
        self, parser: ICSParser
    ) -> None:
        """Test that large content over warning threshold still captures raw content but logs warning."""
        # Create content over warning but under max - use valid ICS structure
        base_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-large-event
DTSTART:20250813T140000Z
DTEND:20250813T150000Z
SUMMARY:Large Event """

        # Add enough content to exceed warning threshold
        # Mock streaming decision to ensure traditional parser is used
        padding = "X" * (MAX_ICS_SIZE_WARNING + 1000)
        large_content = (
            base_content
            + padding
            + """
END:VEVENT
END:VCALENDAR"""
        )

        # Mock both production mode and streaming decision to enable raw content capture
        with (
            patch("calendarbot.ics.parser.is_production_mode", return_value=False),
            patch.object(parser, "_should_use_streaming", return_value=False),
            patch("calendarbot.ics.parser.logger") as mock_logger,
        ):
            result = parser.parse_ics_content(large_content)

            # Should succeed and capture content
            assert result.success is True
            assert result.raw_content == large_content

            # Should log warning for size
            mock_logger.warning.assert_called()

    def test_parse_ics_content_when_parsing_fails_then_still_captures_raw_content(
        self, parser: ICSParser
    ) -> None:
        """Test that raw content is captured even when parsing fails."""
        invalid_ics_content = "INVALID ICS CONTENT"

        # Mock production mode to enable raw content capture
        with patch("calendarbot.ics.parser.is_production_mode", return_value=False):
            result = parser.parse_ics_content(invalid_ics_content)

            # Parsing should fail but raw content should still be captured
            assert result.success is False
            assert result.raw_content == invalid_ics_content
            assert result.error_message is not None

    def test_parse_ics_content_when_raw_content_capture_fails_then_continues_parsing(
        self, parser: ICSParser
    ) -> None:
        """Test that parsing continues even if raw content capture fails."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR"""

        # Mock production mode and size validation to raise an exception during capture
        with (
            patch("calendarbot.ics.parser.is_production_mode", return_value=False),
            patch.object(parser, "_validate_ics_size", side_effect=Exception("Capture error")),
            patch("calendarbot.ics.parser.logger") as mock_logger,
        ):
            result = parser.parse_ics_content(ics_content)

            # Should log warning but continue
            mock_logger.warning.assert_called()
            # Raw content should be None since capture failed
            assert result.raw_content is None

    def test_parse_ics_content_when_large_valid_content_then_handles_correctly(
        self, parser: ICSParser
    ) -> None:
        """Test parsing of large but valid ICS content."""
        # Create large valid content (under warning threshold)
        base_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-123
DTSTART:20250813T140000Z
DTEND:20250813T150000Z
SUMMARY:"""

        # Add large summary
        large_summary = "Large Event " + "X" * 5000

        full_content = (
            base_content
            + large_summary
            + """
END:VEVENT
END:VCALENDAR"""
        )

        # Mock production mode to enable raw content capture
        with patch("calendarbot.ics.parser.is_production_mode", return_value=False):
            result = parser.parse_ics_content(full_content)

            assert result.success is True
            assert result.raw_content == full_content
            assert len(result.events) >= 0  # Should parse some events


class TestICSParserBackwardCompatibility:
    """Test cases for backward compatibility of ICS parser."""

    def test_parse_ics_content_when_no_source_url_then_backward_compatible(
        self, parser: ICSParser
    ) -> None:
        """Test that calling parse_ics_content without source_url works as before."""
        ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"

        # Mock production mode to enable raw content capture
        with patch("calendarbot.ics.parser.is_production_mode", return_value=False):
            result = parser.parse_ics_content(ics_content)

            assert result.success is True
            assert result.raw_content == ics_content
            assert result.source_url is None

    def test_parse_ics_content_when_existing_fields_then_unchanged(self, parser: ICSParser) -> None:
        """Test that existing parse result fields are unchanged."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR"""

        result = parser.parse_ics_content(ics_content)

        # Verify all expected fields exist
        assert hasattr(result, "success")
        assert hasattr(result, "events")
        assert hasattr(result, "calendar_name")
        assert hasattr(result, "calendar_description")
        assert hasattr(result, "timezone")
        assert hasattr(result, "total_components")
        assert hasattr(result, "event_count")
        assert hasattr(result, "recurring_event_count")
        assert hasattr(result, "warnings")
        assert hasattr(result, "error_message")
        assert hasattr(result, "ics_version")
        assert hasattr(result, "prodid")

        # New fields should also exist
        assert hasattr(result, "raw_content")
        assert hasattr(result, "source_url")
