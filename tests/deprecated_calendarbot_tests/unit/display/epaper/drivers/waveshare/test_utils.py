"""Tests for Waveshare e-Paper display utility functions."""

from unittest.mock import MagicMock, patch

from calendarbot.display.epaper.drivers.waveshare.utils import (
    bytes_to_list,
    delay_ms,
    extract_region_buffer,
    list_to_bytes,
    split_color_buffer,
    validate_buffer_size,
)


class TestDelayMs:
    """Test cases for delay_ms function."""

    @patch("calendarbot.display.epaper.drivers.waveshare.utils.time.sleep")
    def test_delay_ms_when_called_then_sleeps_correct_duration(self, mock_sleep: MagicMock) -> None:
        """Test delay_ms calls time.sleep with correct duration."""
        # Test with various millisecond values
        test_cases = [0, 10, 100, 1000]

        for ms in test_cases:
            delay_ms(ms)
            mock_sleep.assert_called_with(ms / 1000.0)
            mock_sleep.reset_mock()


class TestBytesToList:
    """Test cases for bytes_to_list function."""

    def test_bytes_to_list_when_empty_bytes_then_returns_empty_list(self) -> None:
        """Test bytes_to_list with empty bytes returns empty list."""
        result = bytes_to_list(b"")
        assert result == []
        assert isinstance(result, list)

    def test_bytes_to_list_when_single_byte_then_returns_correct_list(self) -> None:
        """Test bytes_to_list with single byte returns correct list."""
        result = bytes_to_list(b"\x01")
        assert result == [1]
        assert isinstance(result, list)

    def test_bytes_to_list_when_multiple_bytes_then_returns_correct_list(self) -> None:
        """Test bytes_to_list with multiple bytes returns correct list."""
        result = bytes_to_list(b"\x01\x02\x03\xff")
        assert result == [1, 2, 3, 255]
        assert isinstance(result, list)


class TestListToBytes:
    """Test cases for list_to_bytes function."""

    def test_list_to_bytes_when_empty_list_then_returns_empty_bytes(self) -> None:
        """Test list_to_bytes with empty list returns empty bytes."""
        result = list_to_bytes([])
        assert result == b""
        assert isinstance(result, bytes)

    def test_list_to_bytes_when_single_item_then_returns_correct_bytes(self) -> None:
        """Test list_to_bytes with single item returns correct bytes."""
        result = list_to_bytes([1])
        assert result == b"\x01"
        assert isinstance(result, bytes)

    def test_list_to_bytes_when_multiple_items_then_returns_correct_bytes(self) -> None:
        """Test list_to_bytes with multiple items returns correct bytes."""
        result = list_to_bytes([1, 2, 3, 255])
        assert result == b"\x01\x02\x03\xff"
        assert isinstance(result, bytes)


class TestValidateBufferSize:
    """Test cases for validate_buffer_size function."""

    def test_validate_buffer_size_when_correct_size_then_returns_true(self) -> None:
        """Test validate_buffer_size returns True when buffer has expected size."""
        buffer = b"\x00\x01\x02"
        expected_size = 3

        result = validate_buffer_size(buffer, expected_size)

        assert result is True

    def test_validate_buffer_size_when_incorrect_size_then_returns_false(self) -> None:
        """Test validate_buffer_size returns False when buffer has incorrect size."""
        buffer = b"\x00\x01\x02"
        expected_size = 4

        result = validate_buffer_size(buffer, expected_size)

        assert result is False

    def test_validate_buffer_size_when_empty_buffer_expected_then_returns_true(self) -> None:
        """Test validate_buffer_size with empty buffer and expected size 0."""
        buffer = b""
        expected_size = 0

        result = validate_buffer_size(buffer, expected_size)

        assert result is True

    @patch("calendarbot.display.epaper.drivers.waveshare.utils.logger")
    def test_validate_buffer_size_when_incorrect_size_then_logs_error(
        self, mock_logger: MagicMock
    ) -> None:
        """Test validate_buffer_size logs error when buffer has incorrect size."""
        buffer = b"\x00\x01\x02"
        expected_size = 4

        validate_buffer_size(buffer, expected_size)

        mock_logger.error.assert_called_once()
        assert "Invalid buffer size" in mock_logger.error.call_args[0][0]
        assert "expected 4" in mock_logger.error.call_args[0][0]
        assert "3, expected 4" in mock_logger.error.call_args[0][0]


class TestSplitColorBuffer:
    """Test cases for split_color_buffer function."""

    def test_split_color_buffer_when_valid_buffer_then_returns_correct_parts(self) -> None:
        """Test split_color_buffer returns correct black and red parts."""
        black_part = b"\x01\x02\x03"
        red_part = b"\x04\x05\x06"
        buffer = black_part + red_part
        buffer_size = 3

        result = split_color_buffer(buffer, buffer_size)

        assert result is not None
        assert result[0] == black_part
        assert result[1] == red_part

    def test_split_color_buffer_when_invalid_size_then_returns_none(self) -> None:
        """Test split_color_buffer returns None when buffer size is invalid."""
        buffer = b"\x01\x02\x03\x04\x05"  # 5 bytes, not 2*buffer_size
        buffer_size = 3

        result = split_color_buffer(buffer, buffer_size)

        assert result is None

    def test_split_color_buffer_when_empty_buffer_then_returns_empty_parts(self) -> None:
        """Test split_color_buffer with empty buffer returns empty parts."""
        buffer = b""
        buffer_size = 0

        result = split_color_buffer(buffer, buffer_size)

        assert result is not None
        assert result[0] == b""
        assert result[1] == b""

    @patch("calendarbot.display.epaper.drivers.waveshare.utils.logger")
    def test_split_color_buffer_when_invalid_size_then_logs_error(
        self, mock_logger: MagicMock
    ) -> None:
        """Test split_color_buffer logs error when buffer size is invalid."""
        buffer = b"\x01\x02\x03\x04\x05"  # 5 bytes, not 2*buffer_size
        buffer_size = 3

        split_color_buffer(buffer, buffer_size)

        mock_logger.error.assert_called_once()
        assert "Invalid buffer size" in mock_logger.error.call_args[0][0]


class TestExtractRegionBuffer:
    """Test cases for extract_region_buffer function."""

    def test_extract_region_buffer_when_valid_region_then_returns_correct_buffer(self) -> None:
        """Test extract_region_buffer returns correct region buffer."""
        # Create a 16x8 display buffer (16 pixels width, 8 pixels height)
        # Each byte represents 8 pixels horizontally
        display_width = 16
        buffer = bytes(
            [
                0b10101010,
                0b11001100,  # Row 0
                0b01010101,
                0b00110011,  # Row 1
                0b11111111,
                0b00000000,  # Row 2
                0b00000000,
                0b11111111,  # Row 3
                0b10101010,
                0b11001100,  # Row 4
                0b01010101,
                0b00110011,  # Row 5
                0b11111111,
                0b00000000,  # Row 6
                0b00000000,
                0b11111111,  # Row 7
            ]
        )

        # Extract a 8x4 region from (0,2) to (7,5)
        region_x = 0
        region_y = 2
        region_width = 8
        region_height = 4

        result = extract_region_buffer(
            buffer, display_width, region_x, region_y, region_width, region_height
        )

        assert result is not None
        # Expected result: 4 bytes (8x4 pixels, 1 byte per 8 pixels)
        expected = bytes(
            [
                0b11111111,  # Row 0 (original row 2)
                0b00000000,  # Row 1 (original row 3)
                0b10101010,  # Row 2 (original row 4)
                0b01010101,  # Row 3 (original row 5)
            ]
        )
        assert result == expected

    def test_extract_region_buffer_when_region_outside_buffer_then_returns_none(self) -> None:
        """Test extract_region_buffer returns None when region is outside buffer."""
        display_width = 16
        buffer = bytes([0] * 16)  # 16x8 display buffer (16 bytes)

        # Region outside buffer
        region_x = 20
        region_y = 10
        region_width = 8
        region_height = 4

        result = extract_region_buffer(
            buffer, display_width, region_x, region_y, region_width, region_height
        )

        # Should return empty buffer, not None, as the function handles out-of-bounds
        assert result is not None
        assert len(result) == region_width * region_height // 8

    def test_extract_region_buffer_when_error_occurs_then_returns_none(self) -> None:
        """Test extract_region_buffer returns None when error occurs."""
        display_width = 16
        buffer = bytes([0] * 16)  # 16x8 display buffer (16 bytes)

        # Invalid region (negative width)
        region_x = 0
        region_y = 0
        region_width = -8  # Invalid
        region_height = 4

        # This should cause an exception inside the function
        result = extract_region_buffer(
            buffer, display_width, region_x, region_y, region_width, region_height
        )

        assert result is None

    @patch("calendarbot.display.epaper.drivers.waveshare.utils.logger")
    def test_extract_region_buffer_when_error_occurs_then_logs_error(
        self, mock_logger: MagicMock
    ) -> None:
        """Test extract_region_buffer logs error when error occurs."""
        display_width = 16
        buffer = bytes([0] * 16)  # 16x8 display buffer (16 bytes)

        # Invalid region (negative width)
        region_x = 0
        region_y = 0
        region_width = -8  # Invalid
        region_height = 4

        extract_region_buffer(
            buffer, display_width, region_x, region_y, region_width, region_height
        )

        mock_logger.error.assert_called_once()
        assert "Failed to extract region buffer" in mock_logger.error.call_args[0][0]

    def test_extract_region_buffer_when_region_partially_outside_then_extracts_valid_part(
        self,
    ) -> None:
        """Test extract_region_buffer extracts valid part when region is partially outside."""
        # Create a 16x8 display buffer
        display_width = 16
        buffer = bytes(
            [
                0b10101010,
                0b11001100,  # Row 0
                0b01010101,
                0b00110011,  # Row 1
                0b11111111,
                0b00000000,  # Row 2
                0b00000000,
                0b11111111,  # Row 3
                0b10101010,
                0b11001100,  # Row 4
                0b01010101,
                0b00110011,  # Row 5
                0b11111111,
                0b00000000,  # Row 6
                0b00000000,
                0b11111111,  # Row 7
            ]
        )

        # Extract a region that extends beyond the buffer
        region_x = 8
        region_y = 6
        region_width = 16  # Extends beyond buffer width
        region_height = 4  # Extends beyond buffer height

        result = extract_region_buffer(
            buffer, display_width, region_x, region_y, region_width, region_height
        )

        # Should return a buffer with the valid part
        assert result is not None
        # Expected: 2 rows (6,7) x 8 pixels (1 byte) from x=8
        assert len(result) == 8  # 8 bytes for the region
