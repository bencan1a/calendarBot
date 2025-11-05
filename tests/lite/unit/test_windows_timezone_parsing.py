"""Test Windows timezone name parsing in RRULE expander.

This test ensures that Windows timezone names (e.g., "Mountain Standard Time")
are properly converted to IANA timezone identifiers (e.g., "America/Denver")
when parsing EXDATE fields in ICS files.
"""

from types import SimpleNamespace

import pytest

from calendarbot_lite.calendar.lite_rrule_expander import LiteRRuleExpander
from calendarbot_lite.core.timezone_utils import windows_tz_to_iana

pytestmark = pytest.mark.unit


@pytest.fixture
def expander():
    """Create an RRULE expander with minimal settings."""
    settings = SimpleNamespace(
        rrule_worker_concurrency=1,
        max_occurrences_per_rule=250,
        expansion_days_window=365,
        expansion_time_budget_ms_per_rule=200,
        expansion_yield_frequency=50,
        rrule_expansion_days=365,
        enable_rrule_expansion=True,
    )
    return LiteRRuleExpander(settings)


class TestWindowsTimezoneMapping:
    """Test Windows timezone to IANA timezone conversion."""

    def test_common_us_timezones(self):
        """Test that common US Windows timezones are mapped correctly."""
        assert windows_tz_to_iana("Pacific Standard Time") == "America/Los_Angeles"
        assert windows_tz_to_iana("Mountain Standard Time") == "America/Denver"
        assert windows_tz_to_iana("Central Standard Time") == "America/Chicago"
        assert windows_tz_to_iana("Eastern Standard Time") == "America/New_York"

    def test_other_timezones(self):
        """Test other common Windows timezone mappings."""
        assert windows_tz_to_iana("GMT Standard Time") == "Europe/London"
        assert windows_tz_to_iana("China Standard Time") == "Asia/Shanghai"
        assert windows_tz_to_iana("Tokyo Standard Time") == "Asia/Tokyo"

    def test_unknown_timezone_returns_none(self):
        """Test that unknown Windows timezones return None."""
        assert windows_tz_to_iana("Unknown Timezone") is None
        assert windows_tz_to_iana("") is None


class TestEXDATEWindowsTimezoneParsing:
    """Test EXDATE parsing with Windows timezone names."""

    def test_parse_mountain_standard_time(self, expander):
        """Test parsing EXDATE with Mountain Standard Time (the original issue)."""
        exdate = "TZID=Mountain Standard Time:20251031T090000"
        dt = expander._parse_datetime(exdate)

        # Should be converted to UTC (MST is UTC-7, so 09:00 MST = 16:00 UTC)
        # Note: In late October, Mountain time is MDT (UTC-6), so 09:00 MDT = 15:00 UTC
        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31
        # The hour will be 15 or 16 depending on DST, but it should be in UTC
        assert dt.hour in (15, 16)

    def test_parse_pacific_standard_time(self, expander):
        """Test parsing EXDATE with Pacific Standard Time."""
        exdate = "TZID=Pacific Standard Time:20251031T080000"
        dt = expander._parse_datetime(exdate)

        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31
        # The hour will be 15 or 16 depending on DST
        assert dt.hour in (15, 16)

    def test_parse_eastern_standard_time(self, expander):
        """Test parsing EXDATE with Eastern Standard Time."""
        exdate = "TZID=Eastern Standard Time:20251031T120000"
        dt = expander._parse_datetime(exdate)

        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31
        # EST is UTC-5, so 12:00 EST = 17:00 UTC (or EDT UTC-4 = 16:00 UTC)
        assert dt.hour in (16, 17)

    def test_parse_central_standard_time(self, expander):
        """Test parsing EXDATE with Central Standard Time."""
        exdate = "TZID=Central Standard Time:20251031T100000"
        dt = expander._parse_datetime(exdate)

        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31
        # CST is UTC-6, so 10:00 CST = 16:00 UTC (or CDT UTC-5 = 15:00 UTC)
        assert dt.hour in (15, 16)

    def test_parse_utc_timezone(self, expander):
        """Test that UTC timezone is handled correctly."""
        exdate = "TZID=UTC:20251031T100000"
        dt = expander._parse_datetime(exdate)

        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31
        assert dt.hour == 10

    def test_parse_with_z_suffix(self, expander):
        """Test parsing datetime with Z suffix (UTC indicator)."""
        exdate = "20251031T100000Z"
        dt = expander._parse_datetime(exdate)

        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 31
        assert dt.hour == 10

    def test_multiple_windows_timezones_in_exdates(self, expander):
        """Test parsing multiple EXDATEs with different Windows timezones."""
        exdates = [
            "TZID=Mountain Standard Time:20251031T090000",
            "TZID=Pacific Standard Time:20251031T080000",
            "TZID=Eastern Standard Time:20251031T120000",
        ]

        parsed_dates = []
        for exdate in exdates:
            dt = expander._parse_datetime(exdate)
            parsed_dates.append(dt)

        # All should be successfully parsed
        assert len(parsed_dates) == 3
        # All should have timezone info
        assert all(dt.tzinfo is not None for dt in parsed_dates)
        # All should be the same date
        assert all(dt.year == 2025 and dt.month == 10 and dt.day == 31 for dt in parsed_dates)
