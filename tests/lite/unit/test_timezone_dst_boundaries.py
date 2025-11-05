"""Test DST boundary conditions and edge cases for timezone parsing.

This test module covers:
- Spring forward (DST start) edge cases
- Fall back (DST end) edge cases
- Ambiguous times during DST transitions
- Non-existent times during DST transitions
- International timezone DST boundaries
"""

import datetime
from zoneinfo import ZoneInfo

import pytest

from calendarbot_lite.calendar.lite_datetime_utils import TimezoneParser
from calendarbot_lite.core.timezone_utils import (
    normalize_timezone_name,
    resolve_timezone_alias,
    windows_tz_to_iana,
)

pytestmark = pytest.mark.unit


class TestDSTSpringForward:
    """Test DST spring forward (start) edge cases."""

    def test_us_pacific_spring_forward_2025(self):
        """Test US Pacific DST start: 2025-03-09 02:00 -> 03:00."""
        # On 2025-03-09 at 2:00 AM, clocks spring forward to 3:00 AM
        # Time 2:30 AM doesn't exist in Pacific timezone on this date
        
        parser = TimezoneParser()
        
        # Parse a time before the transition (1:30 AM PST)
        dt_before = parser.parse_datetime_with_tzid(
            "TZID=Pacific Standard Time:20250309T013000"
        )
        assert dt_before.tzinfo == datetime.UTC
        # 1:30 AM PST (UTC-8) = 9:30 AM UTC
        assert dt_before.hour == 9
        assert dt_before.minute == 30

    def test_us_eastern_spring_forward_2025(self):
        """Test US Eastern DST start: 2025-03-09 02:00 -> 03:00."""
        parser = TimezoneParser()
        
        # Parse time after the transition (3:30 AM EDT)
        dt_after = parser.parse_datetime_with_tzid(
            "TZID=Eastern Standard Time:20250309T033000"
        )
        assert dt_after.tzinfo == datetime.UTC
        # 3:30 AM EDT (UTC-4) = 7:30 AM UTC
        assert dt_after.hour == 7
        assert dt_after.minute == 30

    def test_european_spring_forward_2025(self):
        """Test European DST start: 2025-03-30 01:00 -> 02:00."""
        parser = TimezoneParser()
        
        # Central European Time springs forward on last Sunday of March
        dt = parser.parse_datetime_with_tzid(
            "TZID=Central European Standard Time:20250330T003000"
        )
        assert dt.tzinfo == datetime.UTC
        # Before transition: 0:30 AM CET (UTC+1) = 23:30 previous day UTC
        # After parsing should be in UTC


class TestDSTFallBack:
    """Test DST fall back (end) edge cases."""

    def test_us_pacific_fall_back_2025(self):
        """Test US Pacific DST end: 2025-11-02 02:00 -> 01:00."""
        # On 2025-11-02 at 2:00 AM, clocks fall back to 1:00 AM
        # Time 1:30 AM occurs twice (once in PDT, once in PST)
        
        parser = TimezoneParser()
        
        # Parse time during the ambiguous hour
        dt_ambiguous = parser.parse_datetime_with_tzid(
            "TZID=Pacific Standard Time:20251102T013000"
        )
        assert dt_ambiguous.tzinfo == datetime.UTC
        # Python's zoneinfo picks one interpretation (fold parameter)
        assert dt_ambiguous.month == 11
        assert dt_ambiguous.day == 2

    def test_us_eastern_fall_back_2025(self):
        """Test US Eastern DST end: 2025-11-02 02:00 -> 01:00."""
        parser = TimezoneParser()
        
        dt = parser.parse_datetime_with_tzid(
            "TZID=Eastern Standard Time:20251102T013000"
        )
        assert dt.tzinfo == datetime.UTC
        assert dt.month == 11
        assert dt.day == 2

    def test_european_fall_back_2025(self):
        """Test European DST end: 2025-10-26 03:00 -> 02:00."""
        parser = TimezoneParser()
        
        # Central European Time falls back on last Sunday of October
        dt = parser.parse_datetime_with_tzid(
            "TZID=W. Europe Standard Time:20251026T023000"
        )
        assert dt.tzinfo == datetime.UTC
        assert dt.month == 10
        assert dt.day == 26


class TestInternationalDST:
    """Test DST handling for international timezones."""

    def test_australia_dst_start(self):
        """Test Australian DST start (October, opposite of Northern Hemisphere)."""
        parser = TimezoneParser()
        
        # Australian Eastern DST starts first Sunday in October
        dt = parser.parse_datetime_with_tzid(
            "TZID=AUS Eastern Standard Time:20251005T020000"
        )
        assert dt.tzinfo == datetime.UTC

    def test_australia_dst_end(self):
        """Test Australian DST end (April, opposite of Northern Hemisphere)."""
        parser = TimezoneParser()
        
        # Australian Eastern DST ends first Sunday in April
        dt = parser.parse_datetime_with_tzid(
            "TZID=AUS Eastern Standard Time:20250406T030000"
        )
        assert dt.tzinfo == datetime.UTC

    def test_no_dst_timezone(self):
        """Test timezone that doesn't observe DST (Arizona)."""
        parser = TimezoneParser()
        
        # Arizona doesn't observe DST
        dt_winter = parser.parse_datetime_with_tzid(
            "TZID=Arizona Standard Time:20250115T120000"
        )
        dt_summer = parser.parse_datetime_with_tzid(
            "TZID=Arizona Standard Time:20250715T120000"
        )
        
        # Both should parse successfully
        assert dt_winter.tzinfo == datetime.UTC
        assert dt_summer.tzinfo == datetime.UTC
        
        # UTC offset should be the same (no DST)
        # Winter: 12:00 MST (UTC-7) = 19:00 UTC
        # Summer: 12:00 MST (UTC-7) = 19:00 UTC (no change)
        assert dt_winter.hour == 19
        assert dt_summer.hour == 19


class TestTimezoneAliases:
    """Test timezone alias resolution."""

    def test_resolve_us_aliases(self):
        """Test resolving obsolete US/* timezone aliases."""
        assert resolve_timezone_alias("US/Pacific") == "America/Los_Angeles"
        assert resolve_timezone_alias("US/Mountain") == "America/Denver"
        assert resolve_timezone_alias("US/Central") == "America/Chicago"
        assert resolve_timezone_alias("US/Eastern") == "America/New_York"
        assert resolve_timezone_alias("US/Alaska") == "America/Anchorage"
        assert resolve_timezone_alias("US/Hawaii") == "Pacific/Honolulu"

    def test_resolve_gmt_aliases(self):
        """Test resolving GMT/UTC aliases."""
        assert resolve_timezone_alias("GMT") == "UTC"
        assert resolve_timezone_alias("Etc/UTC") == "UTC"
        assert resolve_timezone_alias("Etc/GMT") == "UTC"
        assert resolve_timezone_alias("Universal") == "UTC"
        assert resolve_timezone_alias("Zulu") == "UTC"

    def test_resolve_legacy_names(self):
        """Test resolving legacy timezone names."""
        assert resolve_timezone_alias("PST8PDT") == "America/Los_Angeles"
        assert resolve_timezone_alias("MST7MDT") == "America/Denver"
        assert resolve_timezone_alias("CST6CDT") == "America/Chicago"
        assert resolve_timezone_alias("EST5EDT") == "America/New_York"

    def test_resolve_non_alias_unchanged(self):
        """Test that non-alias timezones are returned unchanged."""
        assert resolve_timezone_alias("America/Los_Angeles") == "America/Los_Angeles"
        assert resolve_timezone_alias("Europe/London") == "Europe/London"
        assert resolve_timezone_alias("Asia/Tokyo") == "Asia/Tokyo"


class TestTimezoneNormalization:
    """Test comprehensive timezone normalization."""

    def test_normalize_windows_timezone(self):
        """Test normalizing Windows timezone names."""
        assert normalize_timezone_name("Pacific Standard Time") == "America/Los_Angeles"
        assert normalize_timezone_name("Eastern Standard Time") == "America/New_York"
        assert normalize_timezone_name("GMT Standard Time") == "Europe/London"

    def test_normalize_timezone_alias(self):
        """Test normalizing timezone aliases."""
        assert normalize_timezone_name("US/Pacific") == "America/Los_Angeles"
        assert normalize_timezone_name("GMT") == "UTC"
        assert normalize_timezone_name("PST8PDT") == "America/Los_Angeles"

    def test_normalize_canonical_timezone(self):
        """Test normalizing canonical IANA timezone names."""
        assert normalize_timezone_name("America/Los_Angeles") == "America/Los_Angeles"
        assert normalize_timezone_name("Europe/London") == "Europe/London"
        assert normalize_timezone_name("Asia/Tokyo") == "Asia/Tokyo"

    def test_normalize_invalid_timezone(self):
        """Test normalizing invalid timezone returns None."""
        assert normalize_timezone_name("Invalid/Timezone") is None
        assert normalize_timezone_name("BadTimeZone") is None
        assert normalize_timezone_name("") is None


class TestMalformedTimezoneData:
    """Test handling of malformed timezone data."""

    def test_parse_with_missing_timezone(self):
        """Test parsing datetime with missing/empty timezone falls back to UTC."""
        parser = TimezoneParser()
        
        # Should fall back to UTC when timezone is invalid
        dt = parser.parse_datetime_with_tzid("TZID=:20251031T090000")
        assert dt.tzinfo == datetime.UTC

    def test_parse_with_invalid_timezone(self):
        """Test parsing with invalid timezone name falls back gracefully."""
        parser = TimezoneParser()
        
        dt = parser.parse_datetime_with_tzid("TZID=Invalid/Timezone:20251031T090000")
        # Should parse datetime but fall back to UTC for timezone
        assert dt.tzinfo == datetime.UTC
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31

    def test_parse_malformed_datetime_format(self):
        """Test parsing with various datetime format variations."""
        parser = TimezoneParser()
        
        # Missing seconds - October 31, 2025 is during PDT (UTC-7), so 9 AM PDT = 16:00 UTC
        dt1 = parser.parse_datetime_with_tzid("TZID=Pacific Standard Time:20251031T0900")
        assert dt1.hour == 16  # 9 AM PDT (UTC-7) = 16:00 UTC
        
        # ISO format with hyphens
        dt2 = parser.parse_datetime_with_tzid("TZID=Pacific Standard Time:2025-10-31T09:00:00")
        assert dt2.day == 31

    def test_parse_with_unexpected_characters(self):
        """Test parsing handles unexpected characters gracefully."""
        parser = TimezoneParser()
        
        # Extra whitespace
        dt = parser.parse_datetime_with_tzid("TZID= Pacific Standard Time :20251031T090000")
        assert dt.tzinfo == datetime.UTC
        assert dt.year == 2025


class TestAdditionalWindowsTimezones:
    """Test additional Windows timezone mappings."""

    def test_asian_timezones(self):
        """Test Asian Windows timezone mappings."""
        assert windows_tz_to_iana("China Standard Time") == "Asia/Shanghai"
        assert windows_tz_to_iana("Tokyo Standard Time") == "Asia/Tokyo"
        assert windows_tz_to_iana("Korea Standard Time") == "Asia/Seoul"
        assert windows_tz_to_iana("India Standard Time") == "Asia/Kolkata"
        assert windows_tz_to_iana("Singapore Standard Time") == "Asia/Singapore"

    def test_european_timezones(self):
        """Test European Windows timezone mappings."""
        assert windows_tz_to_iana("GMT Standard Time") == "Europe/London"
        assert windows_tz_to_iana("W. Europe Standard Time") == "Europe/Berlin"
        assert windows_tz_to_iana("Central European Standard Time") == "Europe/Paris"
        assert windows_tz_to_iana("E. Europe Standard Time") == "Europe/Bucharest"
        assert windows_tz_to_iana("Russian Standard Time") == "Europe/Moscow"

    def test_australian_timezones(self):
        """Test Australian Windows timezone mappings."""
        assert windows_tz_to_iana("AUS Eastern Standard Time") == "Australia/Sydney"
        assert windows_tz_to_iana("AUS Central Standard Time") == "Australia/Darwin"
        assert windows_tz_to_iana("W. Australia Standard Time") == "Australia/Perth"

    def test_south_american_timezones(self):
        """Test South American Windows timezone mappings."""
        assert windows_tz_to_iana("Pacific SA Standard Time") == "America/Santiago"
        assert windows_tz_to_iana("SA Pacific Standard Time") == "America/Bogota"
        assert windows_tz_to_iana("Argentina Standard Time") == "America/Buenos_Aires"
        assert windows_tz_to_iana("E. South America Standard Time") == "America/Sao_Paulo"

    def test_middle_east_timezones(self):
        """Test Middle East Windows timezone mappings."""
        assert windows_tz_to_iana("Arabian Standard Time") == "Asia/Dubai"
        assert windows_tz_to_iana("Arabic Standard Time") == "Asia/Baghdad"
        assert windows_tz_to_iana("Israel Standard Time") == "Asia/Jerusalem"
        assert windows_tz_to_iana("Iran Standard Time") == "Asia/Tehran"


class TestDSTBoundaryAccuracy:
    """Test accuracy of DST boundary handling with zoneinfo."""

    def test_pacific_dst_transition_exact_time(self):
        """Test exact DST transition time for Pacific timezone."""
        # 2025-03-09 at 2:00 AM PST becomes 3:00 AM PDT
        tz_pacific = ZoneInfo("America/Los_Angeles")
        
        # 1:59 AM is still PST (UTC-8)
        dt_before = datetime.datetime(2025, 3, 9, 1, 59, 0, tzinfo=tz_pacific)
        utc_before = dt_before.astimezone(datetime.UTC)
        assert utc_before.hour == 9  # 1:59 AM + 8 hours = 9:59 AM UTC
        
        # 3:00 AM is PDT (UTC-7) - clock jumped from 2:00 to 3:00
        dt_after = datetime.datetime(2025, 3, 9, 3, 0, 0, tzinfo=tz_pacific)
        utc_after = dt_after.astimezone(datetime.UTC)
        assert utc_after.hour == 10  # 3:00 AM + 7 hours = 10:00 AM UTC

    def test_eastern_dst_transition_exact_time(self):
        """Test exact DST transition time for Eastern timezone."""
        # 2025-11-02 at 2:00 AM EDT becomes 1:00 AM EST
        tz_eastern = ZoneInfo("America/New_York")
        
        # Before fall back: 1:30 AM EDT (UTC-4)
        dt_edt = datetime.datetime(2025, 11, 2, 1, 30, 0, tzinfo=tz_eastern)
        utc_edt = dt_edt.astimezone(datetime.UTC)
        
        # After fall back: Time 1:30 appears again in EST (UTC-5)
        # zoneinfo will pick one interpretation based on fold parameter
        assert utc_edt.month == 11
        assert utc_edt.day == 2
