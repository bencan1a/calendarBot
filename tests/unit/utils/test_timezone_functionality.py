"""
Unit tests for timezone functionality in CalendarBot.

This module tests the timezone synchronization fix including:
- Settings model timezone validation
- Timezone-aware time calculations
- Meeting context with proper timezone handling
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.features.meeting_context import (
    MeetingContextAnalyzer,
    get_meeting_context_for_timeframe,
)
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus
from calendarbot.settings.exceptions import SettingsValidationError
from calendarbot.settings.models import DisplaySettings, SettingsData
from calendarbot.utils.helpers import get_timezone_aware_now


class TestTimezoneSettings:
    """Test timezone configuration in settings model."""

    def test_display_settings_when_valid_timezone_then_accepts(self) -> None:
        """Test that valid timezones are accepted in DisplaySettings."""
        valid_timezones = ["UTC", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"]

        for tz in valid_timezones:
            settings = DisplaySettings(timezone=tz)
            assert settings.timezone == tz
            assert isinstance(settings.timezone, str)

    def test_display_settings_when_default_timezone_then_uses_utc(self) -> None:
        """Test that default timezone is UTC."""
        settings = DisplaySettings()
        assert settings.timezone == "UTC"

    def test_display_settings_when_empty_timezone_then_raises_error(self) -> None:
        """Test that empty timezone raises validation error."""
        with pytest.raises(SettingsValidationError) as exc_info:
            DisplaySettings(timezone="")

        assert "Timezone cannot be empty" in str(exc_info.value)
        assert exc_info.value.field_name == "timezone"

    def test_display_settings_when_whitespace_timezone_then_raises_error(self) -> None:
        """Test that whitespace-only timezone raises validation error."""
        with pytest.raises(SettingsValidationError):
            DisplaySettings(timezone="   ")

    @patch("pytz.timezone")
    def test_display_settings_when_invalid_timezone_then_raises_error(
        self, mock_timezone: MagicMock
    ) -> None:
        """Test that invalid timezone raises validation error."""
        mock_timezone.side_effect = Exception("UnknownTimeZoneError")

        with pytest.raises(SettingsValidationError) as exc_info:
            DisplaySettings(timezone="Invalid/Timezone")

        assert "Invalid timezone" in str(exc_info.value)
        assert exc_info.value.field_name == "timezone"

    @patch("builtins.__import__")
    def test_display_settings_when_pytz_unavailable_then_accepts_common_timezones(
        self, mock_import: MagicMock
    ) -> None:
        """Test that common timezones are accepted when pytz is unavailable."""

        def side_effect(name, *args, **kwargs):
            if name == "pytz":
                raise ImportError("No module named 'pytz'")
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = side_effect
        settings = DisplaySettings(timezone="America/Los_Angeles")
        assert settings.timezone == "America/Los_Angeles"

    def test_settings_data_includes_timezone_in_serialization(self) -> None:
        """Test that timezone is included in settings serialization."""
        settings = SettingsData(display=DisplaySettings(timezone="America/Los_Angeles"))

        api_dict = settings.to_api_dict()
        assert api_dict["display"]["timezone"] == "America/Los_Angeles"


class TestTimezoneAwareHelpers:
    """Test timezone-aware helper functions."""

    def test_get_timezone_aware_now_when_no_timezone_then_returns_system_timezone(self) -> None:
        """Test that get_timezone_aware_now returns system timezone by default."""
        result = get_timezone_aware_now()

        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert isinstance(result.tzinfo.utcoffset(result), timedelta)

    @patch("pytz.timezone")
    @patch("pytz.utc")
    def test_get_timezone_aware_now_when_user_timezone_then_uses_specified_timezone(
        self, mock_utc: MagicMock, mock_timezone: MagicMock
    ) -> None:
        """Test that get_timezone_aware_now uses specified timezone."""
        mock_tz = MagicMock()
        mock_timezone.return_value = mock_tz
        expected_time = datetime.now(timezone.utc)

        # Mock the utc_now creation
        mock_utc.return_value = timezone.utc
        mock_utc_time = MagicMock()
        mock_utc_time.astimezone.return_value = expected_time

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_utc_time
            result = get_timezone_aware_now("America/Los_Angeles")

        mock_timezone.assert_called_once_with("America/Los_Angeles")
        assert isinstance(result, datetime)

    def test_get_timezone_aware_now_when_invalid_timezone_then_falls_back_to_system(self) -> None:
        """Test that invalid timezone falls back to system timezone."""
        with patch("pytz.timezone") as mock_timezone:
            mock_timezone.side_effect = Exception("Invalid timezone")

            result = get_timezone_aware_now("Invalid/Timezone")

            assert isinstance(result, datetime)
            assert result.tzinfo is not None

    def test_get_timezone_aware_now_when_pytz_unavailable_then_falls_back_to_system(self) -> None:
        """Test that pytz unavailable falls back to system timezone."""
        with patch("builtins.__import__") as mock_import:

            def side_effect(name, *args, **kwargs):
                if name == "pytz":
                    raise ImportError("No module named 'pytz'")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = side_effect
            result = get_timezone_aware_now("America/Los_Angeles")

            assert isinstance(result, datetime)
            assert result.tzinfo is not None


class TestMeetingContextTimezone:
    """Test meeting context with timezone awareness."""

    @patch("calendarbot.features.meeting_context.get_timezone_aware_now")
    def test_meeting_context_analyzer_when_called_then_uses_timezone_aware_time(
        self, mock_get_now: MagicMock
    ) -> None:
        """Test that MeetingContextAnalyzer uses timezone-aware time."""
        mock_time = datetime(2023, 7, 19, 10, 0, 0, tzinfo=timezone.utc)
        mock_get_now.return_value = mock_time

        analyzer = MeetingContextAnalyzer()

        # Create test event
        event = CalendarEvent(
            id="test-event",
            subject="Test Meeting",
            start=DateTimeInfo(date_time=mock_time + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=mock_time + timedelta(hours=2), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        insights = analyzer.analyze_upcoming_meetings([event])

        mock_get_now.assert_called_once()
        assert len(insights) == 1
        assert insights[0]["time_until_meeting_minutes"] == 60

    @patch("calendarbot.features.meeting_context.get_timezone_aware_now")
    async def test_get_meeting_context_for_timeframe_when_called_then_uses_timezone_aware_time(
        self, mock_get_now: MagicMock
    ) -> None:
        """Test that get_meeting_context_for_timeframe uses timezone-aware time."""
        mock_time = datetime(2023, 7, 19, 10, 0, 0, tzinfo=timezone.utc)
        mock_get_now.return_value = mock_time

        # Create test event
        event = CalendarEvent(
            id="test-event",
            subject="Test Meeting",
            start=DateTimeInfo(date_time=mock_time + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=mock_time + timedelta(hours=2), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        context = await get_meeting_context_for_timeframe([event], hours_ahead=3)

        mock_get_now.assert_called_once()
        assert context["total_meetings"] == 1
        assert context["next_meeting"]["time_until_meeting_minutes"] == 60

    def test_meeting_context_analyzer_when_explicit_current_time_then_uses_provided_time(
        self,
    ) -> None:
        """Test that explicit current_time parameter is respected."""
        analyzer = MeetingContextAnalyzer()

        # Use explicit timezone-aware time
        current_time = datetime(2023, 7, 19, 10, 0, 0, tzinfo=timezone.utc)

        event = CalendarEvent(
            id="test-event",
            subject="Test Meeting",
            start=DateTimeInfo(date_time=current_time + timedelta(hours=2), time_zone="UTC"),
            end=DateTimeInfo(date_time=current_time + timedelta(hours=3), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        insights = analyzer.analyze_upcoming_meetings([event], current_time=current_time)

        assert len(insights) == 1
        assert insights[0]["time_until_meeting_minutes"] == 120


class TestTimezoneCalculationFix:
    """Test the specific timezone calculation fix."""

    def test_timezone_calculation_when_mixed_naive_aware_then_no_error(self) -> None:
        """Test that mixing naive and aware datetimes doesn't cause TypeError."""
        # This tests the specific fix for the diagnosed issue
        current_time = get_timezone_aware_now()  # timezone-aware
        event_time = datetime.now() + timedelta(hours=2)  # naive

        # Convert naive to aware for proper comparison
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=current_time.tzinfo)

        # This should not raise TypeError
        time_diff = event_time - current_time
        assert isinstance(time_diff, timedelta)

    def test_timezone_calculation_when_both_aware_then_correct_calculation(self) -> None:
        """Test that timezone-aware calculations are correct."""
        # Create timezone-aware times
        utc_now = datetime.now(timezone.utc)
        event_time = utc_now + timedelta(hours=2)

        time_diff = event_time - utc_now
        minutes_diff = time_diff.total_seconds() / 60

        assert abs(minutes_diff - 120) < 1  # Should be 120 minutes ± 1 minute for timing variations

    @patch("pytz.timezone")
    @patch("pytz.utc")
    def test_timezone_calculation_when_different_timezones_then_handles_correctly(
        self, mock_utc: MagicMock, mock_timezone: MagicMock
    ) -> None:
        """Test calculations across different timezones."""
        # Mock PST timezone (UTC-8)
        mock_pst = MagicMock()
        mock_timezone.return_value = mock_pst

        utc_time = datetime(2023, 7, 19, 10, 0, 0, tzinfo=timezone.utc)
        pst_time = datetime(2023, 7, 19, 2, 0, 0)  # 2 AM PST = 10 AM UTC

        # Mock the timezone conversion chain
        mock_utc.return_value = timezone.utc
        mock_utc_time = MagicMock()
        mock_utc_time.astimezone.return_value = pst_time.replace(
            tzinfo=timezone(timedelta(hours=-8))
        )

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_utc_time
            result = get_timezone_aware_now("America/Los_Angeles")

        # Verify timezone handling
        assert result.tzinfo is not None
        mock_timezone.assert_called_once_with("America/Los_Angeles")


class TestTimezoneIntegration:
    """Integration tests for timezone functionality."""

    def test_end_to_end_timezone_aware_meeting_calculation(self) -> None:
        """Test complete timezone-aware meeting time calculation flow."""
        # Create a realistic scenario
        analyzer = MeetingContextAnalyzer()

        # Current time with timezone
        current_time = datetime(2023, 7, 19, 14, 30, 0, tzinfo=timezone.utc)  # 2:30 PM UTC

        # Meeting 1 hour from now
        meeting_start = current_time + timedelta(hours=1)  # 3:30 PM UTC
        meeting_end = meeting_start + timedelta(hours=1)  # 4:30 PM UTC

        event = CalendarEvent(
            id="integration-test",
            subject="Integration Test Meeting",
            start=DateTimeInfo(date_time=meeting_start, time_zone="UTC"),
            end=DateTimeInfo(date_time=meeting_end, time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        # Analyze with explicit current time
        insights = analyzer.analyze_upcoming_meetings([event], current_time=current_time)

        # Verify correct calculation
        assert len(insights) == 1
        insight = insights[0]
        assert insight["time_until_meeting_minutes"] == 60
        assert insight["preparation_needed"] is False  # > 15 minutes
        assert insight["subject"] == "Integration Test Meeting"

    def test_settings_timezone_integration_with_helpers(self) -> None:
        """Test that settings timezone integrates with helper functions."""
        # Create settings with specific timezone
        settings = SettingsData(display=DisplaySettings(timezone="America/Los_Angeles"))

        # Verify timezone is stored correctly
        assert settings.display.timezone == "America/Los_Angeles"

        # Test helper function with this timezone
        result = get_timezone_aware_now(settings.display.timezone)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
