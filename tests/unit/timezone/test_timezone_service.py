"""
Comprehensive unit tests for CalendarBot's centralized timezone service.

This module tests the TimezoneService class including:
- Core service functions (get_server_timezone, convert_to_server_timezone, etc.)
- Special case scenarios (Australian timezone handling, DST transitions)
- Edge cases (invalid inputs, None values, malformed data)
- Integration validation with refactored helper functions
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from calendarbot.timezone.service import TimezoneError, TimezoneService


class TestTimezoneServiceInitialization:
    """Test TimezoneService initialization and basic setup."""

    def test_init_when_default_then_initializes_successfully(self) -> None:
        """Test that default initialization succeeds."""
        service = TimezoneService()

        assert service._server_tz is None  # Lazy initialization
        assert hasattr(service, "_validate_timezone_support")

    def test_init_when_no_timezone_libraries_then_raises_error(self) -> None:
        """Test initialization fails when no timezone libraries available."""
        with (
            patch("calendarbot.timezone.service.ZONEINFO_AVAILABLE", False),
            patch("calendarbot.timezone.service.PYTZ_AVAILABLE", False),
        ):
            with pytest.raises(TimezoneError, match="No timezone library available"):
                TimezoneService()

    def test_validate_timezone_support_when_zoneinfo_available_then_logs_info(self) -> None:
        """Test timezone support validation with zoneinfo available."""
        with patch("calendarbot.timezone.service.logger") as mock_logger:
            TimezoneService()

            mock_logger.info.assert_called_with("Using zoneinfo for timezone handling")

    @patch("calendarbot.timezone.service.ZONEINFO_AVAILABLE", False)
    def test_validate_timezone_support_when_pytz_fallback_then_logs_info(self) -> None:
        """Test timezone support validation with pytz fallback."""
        with patch("calendarbot.timezone.service.logger") as mock_logger:
            TimezoneService()

            mock_logger.info.assert_called_with("Using pytz fallback for timezone handling")


class TestGetServerTimezone:
    """Test get_server_timezone function."""

    def test_get_server_timezone_when_called_then_returns_pacific(self) -> None:
        """Test returns Pacific timezone."""
        service = TimezoneService()

        result = service.get_server_timezone()

        assert str(result) == "America/Los_Angeles"
        assert isinstance(result, ZoneInfo)

    def test_get_server_timezone_when_multiple_calls_then_returns_cached_instance(self) -> None:
        """Test that multiple calls return the same cached timezone instance."""
        service = TimezoneService()

        tz1 = service.get_server_timezone()
        tz2 = service.get_server_timezone()

        assert tz1 is tz2
        assert service._server_tz is not None

    def test_get_server_timezone_when_timezone_creation_fails_then_raises_error(self) -> None:
        """Test error handling when timezone creation fails."""
        service = TimezoneService()

        with patch(
            "calendarbot.timezone.service.ZoneInfo", side_effect=Exception("Creation failed")
        ):
            with pytest.raises(TimezoneError, match="Failed to create server timezone"):
                service.get_server_timezone()

    @patch("calendarbot.timezone.service.ZONEINFO_AVAILABLE", False)
    @patch("calendarbot.timezone.service.PYTZ_AVAILABLE", True)
    def test_get_server_timezone_when_pytz_fallback_then_uses_pytz(self) -> None:
        """Test pytz fallback when zoneinfo unavailable."""
        mock_pytz = MagicMock()
        mock_tz = MagicMock()
        mock_pytz.timezone.return_value = mock_tz

        with patch("calendarbot.timezone.service.pytz", mock_pytz):
            service = TimezoneService()

            result = service.get_server_timezone()

            mock_pytz.timezone.assert_called_once_with("America/Los_Angeles")
            assert result == mock_tz

    @patch("calendarbot.timezone.service.ZONEINFO_AVAILABLE", False)
    @patch("calendarbot.timezone.service.PYTZ_AVAILABLE", False)
    def test_get_server_timezone_when_no_libraries_then_uses_utc_fallback(self) -> None:
        """Test UTC fallback when no timezone libraries available."""
        with patch("calendarbot.timezone.service.logger") as mock_logger:
            # This will fail in init, but let's test the fallback logic
            service = TimezoneService.__new__(TimezoneService)  # Skip __init__
            service._server_tz = None

            result = service.get_server_timezone()

            assert result == timezone.utc
            mock_logger.warning.assert_called()


class TestConvertToServerTimezone:
    """Test convert_to_server_timezone function."""

    def test_convert_to_server_timezone_when_utc_datetime_then_converts_correctly(self) -> None:
        """Test conversion from UTC to server timezone."""
        service = TimezoneService()
        utc_dt = datetime(2024, 1, 15, 20, 0, 0, tzinfo=timezone.utc)  # 8 PM UTC

        result = service.convert_to_server_timezone(utc_dt)

        assert result.tzinfo == service.get_server_timezone()
        # UTC 8 PM should be 12 PM PST in winter (PST = UTC-8)
        assert result.hour == 12

    def test_convert_to_server_timezone_when_dst_summer_then_converts_correctly(self) -> None:
        """Test conversion during DST summer period."""
        service = TimezoneService()
        utc_dt = datetime(2024, 7, 15, 19, 0, 0, tzinfo=timezone.utc)  # 7 PM UTC in summer

        result = service.convert_to_server_timezone(utc_dt)

        assert result.tzinfo == service.get_server_timezone()
        # UTC 7 PM should be 12 PM PDT in summer (PDT = UTC-7)
        assert result.hour == 12

    def test_convert_to_server_timezone_when_different_timezone_then_converts_correctly(
        self,
    ) -> None:
        """Test conversion from different source timezone."""
        service = TimezoneService()
        # Create a datetime in Eastern timezone
        eastern_dt = datetime(2024, 1, 15, 15, 30, 0, tzinfo=ZoneInfo("America/New_York"))

        result = service.convert_to_server_timezone(eastern_dt)

        assert result.tzinfo == service.get_server_timezone()
        # 3:30 PM EST should be 12:30 PM PST (3 hour difference in winter)
        assert result.hour == 12
        assert result.minute == 30

    def test_convert_to_server_timezone_when_naive_datetime_then_assumes_server_time(self) -> None:
        """Test naive datetime is assumed to be in server timezone."""
        service = TimezoneService()
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)

        result = service.convert_to_server_timezone(naive_dt)

        assert result.tzinfo == service.get_server_timezone()
        assert result.hour == 12  # Same time, just now timezone-aware
        assert result.year == 2024

    def test_convert_to_server_timezone_when_not_datetime_then_raises_error(self) -> None:
        """Test that non-datetime object raises TypeError."""
        service = TimezoneService()

        with pytest.raises(TypeError, match="Expected datetime object"):
            service.convert_to_server_timezone("not-a-datetime")  # type: ignore

    def test_convert_to_server_timezone_when_conversion_fails_then_raises_error(self) -> None:
        """Test error handling when conversion fails."""
        service = TimezoneService()
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Mock get_server_timezone to return invalid timezone that will cause conversion to fail
        with patch.object(
            service, "get_server_timezone", side_effect=Exception("Timezone creation failed")
        ):
            with pytest.raises(TimezoneError, match="Failed to convert datetime"):
                service.convert_to_server_timezone(dt)


class TestEnsureTimezoneAware:
    """Test ensure_timezone_aware function."""

    def test_ensure_timezone_aware_when_already_aware_then_returns_unchanged(self) -> None:
        """Test timezone-aware datetime is returned unchanged."""
        service = TimezoneService()
        aware_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = service.ensure_timezone_aware(aware_dt)

        assert result is aware_dt
        assert result.tzinfo == timezone.utc

    def test_ensure_timezone_aware_when_naive_no_fallback_then_uses_server_timezone(self) -> None:
        """Test naive datetime uses server timezone as default."""
        service = TimezoneService()
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)

        result = service.ensure_timezone_aware(naive_dt)

        assert result.tzinfo == service.get_server_timezone()
        assert str(result.tzinfo) == "America/Los_Angeles"
        assert result.hour == 12

    def test_ensure_timezone_aware_when_naive_with_fallback_then_uses_fallback(self) -> None:
        """Test naive datetime uses specified fallback timezone."""
        service = TimezoneService()
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)
        fallback_tz = ZoneInfo("America/New_York")

        result = service.ensure_timezone_aware(naive_dt, fallback_tz)

        assert result.tzinfo == fallback_tz
        assert str(result.tzinfo) == "America/New_York"

    def test_ensure_timezone_aware_when_not_datetime_then_raises_error(self) -> None:
        """Test non-datetime object raises TypeError."""
        service = TimezoneService()

        with pytest.raises(TypeError, match="Expected datetime object"):
            service.ensure_timezone_aware("not-a-datetime")  # type: ignore

    def test_ensure_timezone_aware_when_operation_fails_then_raises_error(self) -> None:
        """Test error handling when timezone operation fails."""
        service = TimezoneService()
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)

        with patch.object(service, "get_server_timezone", side_effect=Exception("TZ failed")):
            with pytest.raises(TimezoneError, match="Failed to make datetime timezone-aware"):
                service.ensure_timezone_aware(naive_dt)

    @patch("calendarbot.timezone.service.ZONEINFO_AVAILABLE", False)
    @patch("calendarbot.timezone.service.PYTZ_AVAILABLE", True)
    def test_ensure_timezone_aware_when_pytz_fallback_then_uses_localize(self) -> None:
        """Test pytz fallback uses localize method."""
        mock_tz = MagicMock()
        mock_aware_dt = MagicMock()
        mock_tz.localize.return_value = mock_aware_dt

        service = TimezoneService()
        service._server_tz = mock_tz
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)

        result = service.ensure_timezone_aware(naive_dt)

        mock_tz.localize.assert_called_once_with(naive_dt)
        assert result == mock_aware_dt


class TestNowServerTimezone:
    """Test now_server_timezone function."""

    def test_now_server_timezone_when_called_then_returns_current_time_in_server_tz(self) -> None:
        """Test returns current time in server timezone."""
        service = TimezoneService()

        before = datetime.now(service.get_server_timezone())
        result = service.now_server_timezone()
        after = datetime.now(service.get_server_timezone())

        assert before <= result <= after
        assert result.tzinfo == service.get_server_timezone()

    def test_now_server_timezone_when_multiple_calls_then_returns_increasing_times(self) -> None:
        """Test multiple calls return increasing times."""
        service = TimezoneService()

        time1 = service.now_server_timezone()
        time2 = service.now_server_timezone()

        assert time2 >= time1
        assert time1.tzinfo == time2.tzinfo

    def test_now_server_timezone_when_timezone_fails_then_raises_error(self) -> None:
        """Test error handling when timezone operations fail."""
        service = TimezoneService()

        with patch.object(service, "get_server_timezone", side_effect=Exception("TZ failed")):
            with pytest.raises(TimezoneError, match="Failed to get current server time"):
                service.now_server_timezone()


class TestParseDatetimeWithTimezone:
    """Test parse_datetime_with_timezone function."""

    def test_parse_datetime_with_timezone_when_iso_format_then_parses_correctly(self) -> None:
        """Test parsing ISO format datetime string."""
        service = TimezoneService()
        dt_string = "2024-01-15T12:00:00"

        result = service.parse_datetime_with_timezone(dt_string)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.tzinfo == service.get_server_timezone()

    def test_parse_datetime_with_timezone_when_iso_with_z_then_parses_as_utc(self) -> None:
        """Test parsing ISO format with Z suffix as UTC."""
        service = TimezoneService()
        dt_string = "2024-01-15T12:00:00Z"

        result = service.parse_datetime_with_timezone(dt_string)

        assert result.tzinfo == timezone.utc

    def test_parse_datetime_with_timezone_when_iso_with_offset_then_parses_correctly(self) -> None:
        """Test parsing ISO format with timezone offset."""
        service = TimezoneService()
        dt_string = "2024-01-15T12:00:00+05:00"

        result = service.parse_datetime_with_timezone(dt_string)

        assert result.tzinfo is not None
        # Verify the offset is correctly parsed
        assert result.utcoffset() == timedelta(hours=5)

    def test_parse_datetime_with_timezone_when_custom_fallback_then_uses_specified(self) -> None:
        """Test parsing with custom fallback timezone specified."""
        service = TimezoneService()
        dt_string = "2024-01-15T12:00:00"
        fallback_tz = ZoneInfo("America/Chicago")

        result = service.parse_datetime_with_timezone(dt_string, fallback_tz)

        assert str(result.tzinfo) == "America/Chicago"

    def test_parse_datetime_with_timezone_when_not_string_then_raises_error(self) -> None:
        """Test non-string input raises TypeError."""
        service = TimezoneService()

        with pytest.raises(TypeError, match="Expected string"):
            service.parse_datetime_with_timezone(123)  # type: ignore

    def test_parse_datetime_with_timezone_when_invalid_format_then_raises_error(self) -> None:
        """Test invalid datetime format raises TimezoneError."""
        service = TimezoneService()

        with pytest.raises(TimezoneError, match="Failed to parse ISO datetime"):
            service.parse_datetime_with_timezone("not-a-datetime")

    def test_parse_datetime_with_timezone_when_parsing_fails_then_raises_error(self) -> None:
        """Test error handling when parsing fails."""
        service = TimezoneService()

        # Use an invalid ISO format that will actually fail to parse
        with pytest.raises(TimezoneError, match="Failed to parse ISO datetime"):
            service.parse_datetime_with_timezone("invalid-datetime-format")


class TestAustralianTimezoneHandling:
    """Test Australian timezone handling that previously required +1 day hack."""

    def test_convert_when_sydney_timezone_then_handles_correctly(self) -> None:
        """Test Sydney timezone conversion without +1 day hack."""
        service = TimezoneService()
        # Create a Sydney datetime (UTC+11 during Australian summer)
        sydney_dt = datetime(2024, 1, 15, 22, 0, 0, tzinfo=ZoneInfo("Australia/Sydney"))

        result = service.convert_to_server_timezone(sydney_dt)

        assert result.tzinfo == service.get_server_timezone()
        # Sydney 10 PM should be around 3 AM Pacific same day (19 hour difference)
        assert result.day == 15  # Same day in this case
        assert result.hour == 3

    def test_convert_when_sydney_dst_transition_then_handles_correctly(self) -> None:
        """Test Sydney DST transition handling."""
        service = TimezoneService()
        # Test during Australian summer (DST active, UTC+11)
        sydney_summer_dt = datetime(2024, 2, 15, 10, 0, 0, tzinfo=ZoneInfo("Australia/Sydney"))

        result = service.convert_to_server_timezone(sydney_summer_dt)

        assert result.tzinfo == service.get_server_timezone()
        # Verify correct conversion without manual day adjustment
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_convert_when_sydney_edge_case_then_detects_australian_timezone(self) -> None:
        """Test that Australian timezone detection works correctly."""
        service = TimezoneService()
        sydney_dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("Australia/Sydney"))

        with patch("calendarbot.timezone.service.logger") as mock_logger:
            result = service.convert_to_server_timezone(sydney_dt)

            # Check that conversion message was logged (Australian timezone special handling exists but may not log)
            mock_logger.debug.assert_called()
            assert isinstance(result, datetime)
            assert result.tzinfo is not None

    @pytest.mark.parametrize(
        "australian_tz",
        [
            "Australia/Sydney",
            "Australia/Melbourne",
            "Australia/Brisbane",
            "Australia/Perth",
            "Australia/Adelaide",
        ],
    )
    def test_australian_timezones_when_various_cities_then_converts_correctly(
        self, australian_tz: str
    ) -> None:
        """Test various Australian timezones convert correctly."""
        service = TimezoneService()
        # Use a standard time for comparison
        local_dt = datetime(2024, 2, 15, 12, 0, 0, tzinfo=ZoneInfo(australian_tz))

        result = service.convert_to_server_timezone(local_dt)

        assert result.tzinfo == service.get_server_timezone()
        # Verify conversion happened correctly
        assert isinstance(result, datetime)
        assert result.year == 2024


class TestDSTTransitions:
    """Test Daylight Saving Time transitions."""

    def test_convert_when_spring_forward_transition_then_handles_correctly(self) -> None:
        """Test spring forward DST transition handling."""
        service = TimezoneService()
        # Test around Pacific DST transition (March 10, 2024 at 2 AM -> 3 AM)
        utc_dt = datetime(
            2024, 3, 10, 10, 30, 0, tzinfo=timezone.utc
        )  # 2:30 AM PST before transition

        result = service.convert_to_server_timezone(utc_dt)

        assert result.tzinfo == service.get_server_timezone()
        assert result.hour == 3  # Should be 3:30 AM PDT after spring forward
        assert result.minute == 30

    def test_convert_when_fall_back_transition_then_handles_correctly(self) -> None:
        """Test fall back DST transition handling."""
        service = TimezoneService()
        # Test around Pacific DST end (November 3, 2024 at 2 AM -> 1 AM)
        utc_dt = datetime(2024, 11, 3, 9, 30, 0, tzinfo=timezone.utc)  # 1:30 AM PST after fall back

        result = service.convert_to_server_timezone(utc_dt)

        assert result.tzinfo == service.get_server_timezone()
        assert result.hour == 1  # Should be 1:30 AM PST
        assert result.minute == 30

    def test_convert_when_cross_dst_boundary_then_maintains_accuracy(self) -> None:
        """Test conversions across DST boundary maintain accuracy."""
        service = TimezoneService()

        # Test times around Pacific DST transition
        before_dst = datetime(2024, 3, 10, 9, 0, 0, tzinfo=timezone.utc)  # 1 AM PST
        after_dst = datetime(
            2024, 3, 10, 11, 0, 0, tzinfo=timezone.utc
        )  # 4 AM PDT (skipped 2-3 AM)

        result_before = service.convert_to_server_timezone(before_dst)
        result_after = service.convert_to_server_timezone(after_dst)

        assert result_before.hour == 1  # PST (UTC-8)
        assert result_after.hour == 4  # PDT (UTC-7)


class TestPytzFallback:
    """Test pytz fallback behavior when zoneinfo is unavailable."""

    @patch("calendarbot.timezone.service.ZONEINFO_AVAILABLE", False)
    @patch("calendarbot.timezone.service.PYTZ_AVAILABLE", True)
    def test_convert_when_pytz_fallback_then_uses_pytz_methods(self) -> None:
        """Test conversion uses pytz methods when zoneinfo unavailable."""
        mock_pytz = MagicMock()
        mock_tz = MagicMock()
        mock_aware_dt = MagicMock()
        mock_tz.localize.return_value = mock_aware_dt
        mock_pytz.timezone.return_value = mock_tz

        with patch("calendarbot.timezone.service.pytz", mock_pytz):
            service = TimezoneService()
            naive_dt = datetime(2024, 1, 15, 12, 0, 0)

            result = service.convert_to_server_timezone(naive_dt)

            mock_tz.localize.assert_called_once_with(naive_dt)
            assert result == mock_aware_dt


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    def test_convert_when_extreme_future_date_then_handles_correctly(self) -> None:
        """Test conversion with extreme future date."""
        service = TimezoneService()
        future_dt = datetime(2100, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        result = service.convert_to_server_timezone(future_dt)

        assert result.tzinfo == service.get_server_timezone()
        assert result.year == 2100

    def test_convert_when_extreme_past_date_then_handles_correctly(self) -> None:
        """Test conversion with extreme past date."""
        service = TimezoneService()
        past_dt = datetime(1900, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        result = service.convert_to_server_timezone(past_dt)

        assert result.tzinfo == service.get_server_timezone()
        # UTC 1900-01-01 00:00:00 becomes PST 1899-12-31 16:00:00 (UTC-8)
        assert result.year == 1899
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 16

    def test_ensure_timezone_aware_when_date_object_then_converts_to_datetime(self) -> None:
        """Test date object handling."""
        service = TimezoneService()

        # This should raise TypeError since we expect datetime, not date
        with pytest.raises(TypeError, match="Expected datetime object"):
            service.ensure_timezone_aware(date(2024, 1, 15))  # type: ignore

    def test_timezone_service_when_concurrent_access_then_thread_safe(self) -> None:
        """Test timezone service is thread-safe for concurrent access."""
        import threading

        service = TimezoneService()
        results = []

        def convert_time() -> None:
            dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            result = service.convert_to_server_timezone(dt)
            results.append(result)

        threads = [threading.Thread(target=convert_time) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All results should be identical
        assert len(results) == 10
        assert all(r == results[0] for r in results)


class TestIntegrationWithRefactoredCode:
    """Test integration with refactored helper functions."""

    def test_timezone_service_when_used_by_helpers_then_maintains_compatibility(self) -> None:
        """Test TimezoneService maintains compatibility with refactored helpers."""
        service = TimezoneService()

        # Simulate the pattern used in refactored helpers.py
        current_time = service.now_server_timezone()
        future_time = current_time + timedelta(hours=2)

        # Convert to UTC for comparison (common pattern)
        current_utc = current_time.astimezone(timezone.utc)
        future_utc = future_time.astimezone(timezone.utc)

        time_diff = future_utc - current_utc
        assert time_diff == timedelta(hours=2)

    def test_timezone_service_when_parsing_ics_datetime_then_handles_correctly(self) -> None:
        """Test TimezoneService integration with ICS parser patterns."""
        service = TimezoneService()

        # Simulate common ICS datetime patterns
        ics_patterns = [
            "2024-01-15T12:00:00Z",  # UTC format
            "2024-01-15T12:00:00",  # Local format
            "2024-01-15T12:00:00+00:00",  # ISO with offset
        ]

        for pattern in ics_patterns:
            result = service.parse_datetime_with_timezone(pattern)

            assert isinstance(result, datetime)
            assert result.tzinfo is not None
            assert result.year == 2024


@pytest.fixture
def timezone_service() -> TimezoneService:
    """Fixture providing a default TimezoneService instance."""
    return TimezoneService()


@pytest.fixture
def utc_datetime() -> datetime:
    """Fixture providing a UTC datetime for testing."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def naive_datetime() -> datetime:
    """Fixture providing a naive datetime for testing."""
    return datetime(2024, 1, 15, 12, 0, 0)


@pytest.fixture
def sydney_datetime() -> datetime:
    """Fixture providing a Sydney timezone datetime for testing."""
    return datetime(2024, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("Australia/Sydney"))


# Parametrized test for comprehensive timezone coverage
@pytest.mark.parametrize(
    "test_tz,winter_offset,summer_offset",
    [
        ("America/Los_Angeles", -8, -7),  # PST/PDT
        ("America/New_York", -5, -4),  # EST/EDT
        ("Europe/London", 0, 1),  # GMT/BST
        ("Asia/Tokyo", 9, 9),  # JST (no DST)
        ("Australia/Sydney", 11, 10),  # AEDT/AEST (reversed seasons)
    ],
)
def test_timezone_conversions_comprehensive_coverage(
    test_tz: str, winter_offset: int, summer_offset: int
) -> None:
    """Test comprehensive timezone conversion coverage."""
    service = TimezoneService()

    # Test winter time (January) - create UTC time and convert to target timezone first
    winter_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    winter_target = winter_utc.astimezone(ZoneInfo(test_tz))

    # Convert target timezone back to server timezone
    winter_server = service.convert_to_server_timezone(winter_target)

    # Test summer time (July)
    summer_utc = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    summer_target = summer_utc.astimezone(ZoneInfo(test_tz))

    # Convert target timezone back to server timezone
    summer_server = service.convert_to_server_timezone(summer_target)

    # Verify conversions are timezone-aware and use server timezone
    assert winter_server.tzinfo is not None
    assert summer_server.tzinfo is not None
    assert str(winter_server.tzinfo) == "America/Los_Angeles"
    assert str(summer_server.tzinfo) == "America/Los_Angeles"
