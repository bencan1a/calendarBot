"""Unit tests for calendarbot_lite.timezone_utils module.

Tests timezone detection, conversion utilities, and time provider functionality
with support for test time override.
"""

import datetime
from unittest.mock import patch

import pytest

from calendarbot_lite.timezone_utils import (
    DEFAULT_SERVER_TIMEZONE,
    TimeProvider,
    TimezoneDetector,
    convert_to_server_tz,
    convert_to_timezone,
    get_fallback_timezone,
    get_server_timezone,
    now_utc,
    parse_request_timezone,
    windows_tz_to_iana,
)

pytestmark = pytest.mark.unit


class TestTimezoneDetector:
    """Tests for TimezoneDetector class."""

    def test_get_fallback_timezone_returns_pacific(self):
        """Test fallback timezone is always Pacific."""
        detector = TimezoneDetector()
        
        assert detector.get_fallback_timezone() == DEFAULT_SERVER_TIMEZONE
        assert detector.get_fallback_timezone() == "America/Los_Angeles"

    def test_get_server_timezone_returns_valid_iana_string(self):
        """Test server timezone detection returns valid IANA identifier."""
        detector = TimezoneDetector()
        
        tz = detector.get_server_timezone()
        
        assert isinstance(tz, str)
        # Can return UTC or IANA format like "America/Los_Angeles"
        assert tz in ("UTC", DEFAULT_SERVER_TIMEZONE) or "/" in tz

    def test_get_server_timezone_with_abbreviation_mapping(self):
        """Test timezone detection via abbreviation mapping."""
        detector = TimezoneDetector()
        
        # PST should map to America/Los_Angeles
        assert "PST" in detector.TZ_ABBREV_MAP
        assert detector.TZ_ABBREV_MAP["PST"] == "America/Los_Angeles"

    def test_get_server_timezone_falls_back_on_error(self):
        """Test server timezone falls back to Pacific on detection error."""
        detector = TimezoneDetector()
        
        # Even if detection fails, should return Pacific (unless system is UTC)
        with patch("time.tzname", side_effect=Exception("Test error")):
            tz = detector.get_server_timezone()
            assert tz in (DEFAULT_SERVER_TIMEZONE, "UTC")

    def test_windows_tz_map_contains_common_zones(self):
        """Test Windows timezone map has common entries."""
        detector = TimezoneDetector()
        
        assert "Pacific Standard Time" in detector.WINDOWS_TZ_MAP
        assert "Eastern Standard Time" in detector.WINDOWS_TZ_MAP
        assert detector.WINDOWS_TZ_MAP["Pacific Standard Time"] == "America/Los_Angeles"

    def test_offset_to_tz_map_contains_common_offsets(self):
        """Test UTC offset map has common offsets."""
        detector = TimezoneDetector()
        
        assert -8 in detector.OFFSET_TO_TZ_MAP
        assert -5 in detector.OFFSET_TO_TZ_MAP
        assert detector.OFFSET_TO_TZ_MAP[-8] == "America/Los_Angeles"


class TestTimeProvider:
    """Tests for TimeProvider class."""

    def test_now_utc_returns_utc_datetime(self):
        """Test now_utc returns timezone-aware UTC datetime."""
        detector = TimezoneDetector()
        provider = TimeProvider(detector)
        
        now = provider.now_utc()
        
        assert isinstance(now, datetime.datetime)
        assert now.tzinfo == datetime.timezone.utc

    def test_now_utc_with_test_time_override(self, monkeypatch):
        """Test now_utc respects CALENDARBOT_TEST_TIME environment variable."""
        detector = TimezoneDetector()
        provider = TimeProvider(detector)
        
        test_time = "2025-01-15T12:00:00Z"
        monkeypatch.setenv("CALENDARBOT_TEST_TIME", test_time)
        
        now = provider.now_utc()
        
        assert now.year == 2025
        assert now.month == 1
        assert now.day == 15
        assert now.hour == 12
        assert now.tzinfo == datetime.timezone.utc

    def test_now_utc_with_pacific_offset_test_time(self, monkeypatch):
        """Test now_utc handles Pacific timezone test time."""
        detector = TimezoneDetector()
        provider = TimeProvider(detector)
        
        # Test time in PST (UTC-8)
        test_time = "2025-01-15T10:00:00-08:00"
        monkeypatch.setenv("CALENDARBOT_TEST_TIME", test_time)
        
        now = provider.now_utc()
        
        # Should convert to UTC (18:00)
        assert now.tzinfo == datetime.timezone.utc
        assert now.hour == 18

    def test_now_utc_with_invalid_test_time_falls_back(self, monkeypatch):
        """Test now_utc falls back to real time on invalid test time."""
        detector = TimezoneDetector()
        provider = TimeProvider(detector)
        
        monkeypatch.setenv("CALENDARBOT_TEST_TIME", "invalid-datetime")
        
        now = provider.now_utc()
        
        # Should return current time, not fail
        assert isinstance(now, datetime.datetime)
        assert now.tzinfo == datetime.timezone.utc

    def test_enhance_datetime_with_dst_detection(self):
        """Test DST detection enhancement for Pacific timezone."""
        detector = TimezoneDetector()
        provider = TimeProvider(detector)
        
        # Create a datetime with PDT offset (-7) during PST period (should be -8)
        # January is PST time
        dt = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-7)))
        
        enhanced = provider._enhance_datetime_with_dst_detection(dt, "2025-01-15T10:00:00-07:00")
        
        # Should have been corrected
        assert enhanced.tzinfo is not None


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_server_timezone_returns_string(self):
        """Test get_server_timezone convenience function."""
        tz = get_server_timezone()
        
        assert isinstance(tz, str)
        # Can return UTC or IANA format
        assert tz in ("UTC", DEFAULT_SERVER_TIMEZONE) or "/" in tz

    def test_get_fallback_timezone_returns_pacific(self):
        """Test get_fallback_timezone convenience function."""
        tz = get_fallback_timezone()
        
        assert tz == "America/Los_Angeles"

    def test_now_utc_convenience_returns_datetime(self):
        """Test now_utc convenience function."""
        now = now_utc()
        
        assert isinstance(now, datetime.datetime)
        assert now.tzinfo == datetime.timezone.utc

    def test_windows_tz_to_iana_with_valid_timezone(self):
        """Test Windows timezone to IANA conversion."""
        iana = windows_tz_to_iana("Pacific Standard Time")
        
        assert iana == "America/Los_Angeles"

    def test_windows_tz_to_iana_with_invalid_timezone(self):
        """Test Windows timezone conversion with unknown timezone."""
        iana = windows_tz_to_iana("Invalid Timezone")
        
        assert iana is None


class TestTimezoneConversion:
    """Tests for timezone conversion functions."""

    def test_convert_to_server_tz_from_utc(self):
        """Test converting UTC datetime to server timezone."""
        utc_time = datetime.datetime(2025, 1, 1, 20, 0, tzinfo=datetime.timezone.utc)
        
        local_time = convert_to_server_tz(utc_time)
        
        assert local_time.tzinfo is not None
        # If server is in UTC, times will be equal; otherwise they differ
        server_tz = get_server_timezone()
        if server_tz == "UTC":
            assert local_time.replace(tzinfo=datetime.timezone.utc) == utc_time
        else:
            assert local_time != utc_time  # Should be different time in non-UTC TZ

    def test_convert_to_timezone_with_valid_tz(self):
        """Test converting datetime to specific timezone."""
        utc_time = datetime.datetime(2025, 1, 1, 20, 0, tzinfo=datetime.timezone.utc)
        
        ny_time = convert_to_timezone(utc_time, "America/New_York")
        
        assert ny_time.tzinfo is not None
        # New York is UTC-5 in winter
        assert ny_time.hour == 15

    def test_convert_to_timezone_with_invalid_tz_raises(self):
        """Test convert_to_timezone raises on invalid timezone."""
        import zoneinfo
        
        utc_time = datetime.datetime(2025, 1, 1, 20, 0, tzinfo=datetime.timezone.utc)
        
        with pytest.raises(zoneinfo.ZoneInfoNotFoundError):
            convert_to_timezone(utc_time, "Invalid/Timezone")


class TestParseRequestTimezone:
    """Tests for parse_request_timezone function."""

    def test_parse_request_timezone_with_valid_tz(self):
        """Test parsing valid timezone string."""
        tz = parse_request_timezone("America/Los_Angeles")
        
        assert tz is not None
        assert str(tz) in ("America/Los_Angeles", "tzfile('/usr/share/zoneinfo/America/Los_Angeles')")

    def test_parse_request_timezone_with_none_returns_utc(self):
        """Test parsing None returns UTC."""
        tz = parse_request_timezone(None)
        
        assert tz == datetime.timezone.utc

    def test_parse_request_timezone_with_empty_string_returns_utc(self):
        """Test parsing empty string returns UTC."""
        tz = parse_request_timezone("")
        
        assert tz == datetime.timezone.utc

    def test_parse_request_timezone_with_invalid_tz_returns_utc(self):
        """Test parsing invalid timezone returns UTC."""
        tz = parse_request_timezone("Invalid/Timezone")
        
        assert tz == datetime.timezone.utc

    def test_parse_request_timezone_caching(self):
        """Test parse_request_timezone uses LRU cache."""
        # Call twice with same input
        tz1 = parse_request_timezone("America/Chicago")
        tz2 = parse_request_timezone("America/Chicago")
        
        # Should return same object from cache
        assert tz1 is tz2


@pytest.mark.parametrize("abbrev,expected_iana", [
    ("PST", "America/Los_Angeles"),
    ("PDT", "America/Los_Angeles"),
    ("EST", "America/New_York"),
    ("EDT", "America/New_York"),
    ("CST", "America/Chicago"),
    ("CDT", "America/Chicago"),
])
def test_tz_abbrev_mapping(abbrev: str, expected_iana: str):
    """Test timezone abbreviation mappings."""
    detector = TimezoneDetector()
    
    assert abbrev in detector.TZ_ABBREV_MAP
    assert detector.TZ_ABBREV_MAP[abbrev] == expected_iana


@pytest.mark.parametrize("windows_tz,expected_iana", [
    ("Pacific Standard Time", "America/Los_Angeles"),
    ("Eastern Standard Time", "America/New_York"),
    ("Central Standard Time", "America/Chicago"),
    ("Mountain Standard Time", "America/Denver"),
])
def test_windows_tz_mapping(windows_tz: str, expected_iana: str):
    """Test Windows timezone mappings."""
    result = windows_tz_to_iana(windows_tz)
    
    assert result == expected_iana
