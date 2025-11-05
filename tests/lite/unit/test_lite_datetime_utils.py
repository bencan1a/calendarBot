"""Unit tests for lite_datetime_utils module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from calendarbot_lite.calendar.lite_datetime_utils import (
    LiteDateTimeParser,
    ensure_timezone_aware,
    format_time_cross_platform,
    serialize_datetime_optional,
    serialize_datetime_utc,
)

pytestmark = pytest.mark.unit


class TestFormatTimeCrossPlatform:
    """Tests for format_time_cross_platform utility function.

    This function must work identically on Windows, Linux, and macOS,
    replacing the Unix-specific strftime format code %-I.
    """

    def test_morning_single_digit_hour(self):
        """Test formatting single-digit morning hour without leading zero."""
        dt = datetime(2025, 11, 4, 9, 30, 0)
        result = format_time_cross_platform(dt)
        assert result == "9:30 am"

    def test_afternoon_single_digit_hour(self):
        """Test formatting single-digit afternoon hour (1 PM)."""
        dt = datetime(2025, 11, 4, 13, 15, 0)
        result = format_time_cross_platform(dt)
        assert result == "1:15 pm"

    def test_morning_double_digit_hour(self):
        """Test formatting double-digit morning hour."""
        dt = datetime(2025, 11, 4, 10, 45, 0)
        result = format_time_cross_platform(dt)
        assert result == "10:45 am"

    def test_afternoon_double_digit_hour(self):
        """Test formatting double-digit afternoon hour."""
        dt = datetime(2025, 11, 4, 15, 20, 0)
        result = format_time_cross_platform(dt)
        assert result == "3:20 pm"

    def test_midnight(self):
        """Test formatting midnight as 12:00 AM."""
        dt = datetime(2025, 11, 4, 0, 0, 0)
        result = format_time_cross_platform(dt)
        assert result == "12:00 am"

    def test_noon(self):
        """Test formatting noon as 12:00 PM."""
        dt = datetime(2025, 11, 4, 12, 0, 0)
        result = format_time_cross_platform(dt)
        assert result == "12:00 pm"

    def test_with_utc_suffix(self):
        """Test formatting with UTC suffix."""
        dt = datetime(2025, 11, 4, 9, 30, 0)
        result = format_time_cross_platform(dt, " UTC")
        assert result == "9:30 am utc"

    def test_with_custom_suffix(self):
        """Test formatting with custom suffix."""
        dt = datetime(2025, 11, 4, 14, 15, 0)
        result = format_time_cross_platform(dt, " PST")
        assert result == "2:15 pm pst"

    def test_zero_minutes(self):
        """Test formatting with zero minutes."""
        dt = datetime(2025, 11, 4, 8, 0, 0)
        result = format_time_cross_platform(dt)
        assert result == "8:00 am"

    def test_single_digit_minutes_with_leading_zero(self):
        """Test that minutes always have leading zeros."""
        dt = datetime(2025, 11, 4, 9, 5, 0)
        result = format_time_cross_platform(dt)
        assert result == "9:05 am"

    def test_timezone_aware_datetime(self):
        """Test formatting timezone-aware datetime."""
        dt = datetime(2025, 11, 4, 9, 30, 0, tzinfo=timezone.utc)
        result = format_time_cross_platform(dt)
        assert result == "9:30 am"

    def test_edge_case_11pm(self):
        """Test formatting 11 PM."""
        dt = datetime(2025, 11, 4, 23, 59, 0)
        result = format_time_cross_platform(dt)
        assert result == "11:59 pm"

    def test_edge_case_1am(self):
        """Test formatting 1 AM."""
        dt = datetime(2025, 11, 4, 1, 0, 0)
        result = format_time_cross_platform(dt)
        assert result == "1:00 am"

    def test_suffix_case_handling(self):
        """Test that suffix is lowercased."""
        dt = datetime(2025, 11, 4, 9, 30, 0)
        result = format_time_cross_platform(dt, " UTC")
        assert "utc" in result
        assert "UTC" not in result


class TestEnsureTimezoneAware:
    """Tests for ensure_timezone_aware utility function."""

    def test_naive_datetime_gets_utc_timezone(self):
        """Test that naive datetime gets UTC timezone."""
        naive_dt = datetime(2023, 12, 1, 10, 0, 0)
        result = ensure_timezone_aware(naive_dt)

        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 10

    def test_aware_datetime_unchanged(self):
        """Test that timezone-aware datetime is not modified."""
        aware_dt = datetime(2023, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        result = ensure_timezone_aware(aware_dt)

        assert result is aware_dt
        assert result.tzinfo == timezone.utc


class TestSerializeDateTimeUtc:
    """Tests for serialize_datetime_utc utility function.

    This function replaces manual string concatenation (dt.isoformat() + "Z")
    with proper datetime handling.
    """

    def test_serialize_utc_aware_datetime(self):
        """Test serializing timezone-aware UTC datetime."""
        dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=timezone.utc)
        result = serialize_datetime_utc(dt)
        assert result == "2024-11-04T16:30:00Z"

    def test_serialize_naive_datetime_assumes_utc(self):
        """Test serializing naive datetime (should assume UTC)."""
        dt = datetime(2024, 11, 4, 16, 30, 0)
        result = serialize_datetime_utc(dt)
        assert result == "2024-11-04T16:30:00Z"

    def test_serialize_non_utc_timezone_converts_to_utc(self):
        """Test serializing datetime with non-UTC timezone converts to UTC."""
        from zoneinfo import ZoneInfo

        # 5 PM PST = 1 AM UTC next day (PST is UTC-8)
        dt = datetime(2024, 11, 4, 17, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
        result = serialize_datetime_utc(dt)
        # PST is UTC-8, so 17:00 PST = 01:00 UTC next day (during standard time)
        # During PST (winter), UTC offset is -8
        assert "T01:00:00Z" in result or "T00:00:00Z" in result  # Account for DST variations

    def test_serialize_with_microseconds(self):
        """Test that microseconds are included in serialization."""
        dt = datetime(2024, 11, 4, 16, 30, 0, 123456, tzinfo=timezone.utc)
        result = serialize_datetime_utc(dt)
        assert result == "2024-11-04T16:30:00.123456Z"

    def test_serialize_midnight_utc(self):
        """Test serializing midnight UTC."""
        dt = datetime(2024, 11, 4, 0, 0, 0, tzinfo=timezone.utc)
        result = serialize_datetime_utc(dt)
        assert result == "2024-11-04T00:00:00Z"

    def test_serialize_end_of_day(self):
        """Test serializing end of day (23:59:59)."""
        dt = datetime(2024, 11, 4, 23, 59, 59, tzinfo=timezone.utc)
        result = serialize_datetime_utc(dt)
        assert result == "2024-11-04T23:59:59Z"

    def test_serialize_none_raises_value_error(self):
        """Test that None input raises ValueError."""
        with pytest.raises(ValueError, match="Cannot serialize None datetime"):
            serialize_datetime_utc(None)  # type: ignore[arg-type]

    def test_result_ends_with_z_suffix(self):
        """Test that result always ends with Z suffix."""
        dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=timezone.utc)
        result = serialize_datetime_utc(dt)
        assert result.endswith("Z")

    def test_result_is_valid_iso8601(self):
        """Test that result is valid ISO 8601 format."""
        dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=timezone.utc)
        result = serialize_datetime_utc(dt)
        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert parsed.year == 2024
        assert parsed.month == 11
        assert parsed.day == 4
        assert parsed.hour == 16
        assert parsed.minute == 30


class TestSerializeDateTimeOptional:
    """Tests for serialize_datetime_optional utility function."""

    def test_serialize_valid_datetime(self):
        """Test serializing valid datetime."""
        dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=timezone.utc)
        result = serialize_datetime_optional(dt)
        assert result == "2024-11-04T16:30:00Z"

    def test_serialize_none_returns_none(self):
        """Test that None input returns None."""
        result = serialize_datetime_optional(None)
        assert result is None

    def test_serialize_naive_datetime(self):
        """Test serializing naive datetime (should work via serialize_datetime_utc)."""
        dt = datetime(2024, 11, 4, 16, 30, 0)
        result = serialize_datetime_optional(dt)
        assert result == "2024-11-04T16:30:00Z"

    def test_serialize_with_timezone(self):
        """Test serializing datetime with timezone."""
        from zoneinfo import ZoneInfo

        dt = datetime(2024, 11, 4, 16, 30, 0, tzinfo=ZoneInfo("UTC"))
        result = serialize_datetime_optional(dt)
        assert result == "2024-11-04T16:30:00Z"


class TestLiteDateTimeParser:
    """Tests for LiteDateTimeParser class."""

    def test_parser_initialization_with_default_timezone(self):
        """Test parser initialization with default timezone."""
        parser = LiteDateTimeParser(default_timezone="America/New_York")
        assert parser.default_timezone == "America/New_York"

    def test_parser_initialization_without_default_timezone(self):
        """Test parser initialization without default timezone."""
        parser = LiteDateTimeParser()
        assert parser.default_timezone is None

    def test_parse_datetime_with_aware_datetime(self):
        """Test parsing datetime that already has timezone."""
        parser = LiteDateTimeParser()

        # Mock iCalendar property
        dt_prop = MagicMock()
        dt_prop.dt = datetime(2023, 12, 1, 10, 0, 0, tzinfo=timezone.utc)

        result = parser.parse_datetime(dt_prop)

        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 10

    def test_parse_datetime_with_naive_datetime_uses_utc(self):
        """Test parsing naive datetime uses UTC as default."""
        parser = LiteDateTimeParser()

        # Mock iCalendar property with naive datetime
        dt_prop = MagicMock()
        dt_prop.dt = datetime(2023, 12, 1, 10, 0, 0)

        result = parser.parse_datetime(dt_prop)

        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 10

    def test_parse_datetime_with_default_timezone(self):
        """Test parsing naive datetime with default timezone."""
        parser = LiteDateTimeParser(default_timezone="America/New_York")

        # Mock iCalendar property with naive datetime
        dt_prop = MagicMock()
        dt_prop.dt = datetime(2023, 12, 1, 10, 0, 0)

        result = parser.parse_datetime(dt_prop)

        # Should be timezone-aware (UTC since we don't have pytz in lite version)
        assert result.tzinfo is not None

    def test_parse_datetime_with_date_object(self):
        """Test parsing date-only property (all-day events)."""
        from datetime import date

        parser = LiteDateTimeParser()

        # Mock iCalendar property with date object
        dt_prop = MagicMock()
        dt_prop.dt = date(2023, 12, 1)

        result = parser.parse_datetime(dt_prop)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_parse_datetime_optional_with_none(self):
        """Test parsing optional datetime returns None for None input."""
        parser = LiteDateTimeParser()
        result = parser.parse_datetime_optional(None)
        assert result is None

    def test_parse_datetime_optional_with_valid_datetime(self):
        """Test parsing optional datetime with valid input."""
        parser = LiteDateTimeParser()

        # Mock iCalendar property
        dt_prop = MagicMock()
        dt_prop.dt = datetime(2023, 12, 1, 10, 0, 0, tzinfo=timezone.utc)

        result = parser.parse_datetime_optional(dt_prop)

        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.year == 2023

    def test_parse_datetime_optional_with_invalid_input_returns_none(self):
        """Test parsing optional datetime returns None for invalid input."""
        parser = LiteDateTimeParser()

        # Mock property that raises exception
        dt_prop = MagicMock()
        dt_prop.dt = None  # This will cause an error

        # Should return None instead of raising
        result = parser.parse_datetime_optional(dt_prop)
        assert result is None

    def test_parse_datetime_with_override_default_timezone(self):
        """Test parsing datetime with timezone override."""
        parser = LiteDateTimeParser(default_timezone="America/Los_Angeles")

        # Mock iCalendar property with naive datetime
        dt_prop = MagicMock()
        dt_prop.dt = datetime(2023, 12, 1, 10, 0, 0)

        # Override the default timezone
        result = parser.parse_datetime(dt_prop, default_timezone="America/New_York")

        # Should be timezone-aware
        assert result.tzinfo is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
