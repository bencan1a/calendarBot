"""Tests for Alexa request parameter validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from calendarbot_lite.alexa_models import (
    AlexaRequestParams,
    DoneForDayRequestParams,
    LaunchSummaryRequestParams,
    MorningSummaryRequestParams,
    NextMeetingRequestParams,
    TimeUntilRequestParams,
)


class TestAlexaRequestParams:
    """Test base request parameter validation."""

    def test_valid_timezone(self):
        """Test valid timezone validation."""
        params = AlexaRequestParams(tz="America/Los_Angeles")
        assert params.tz == "America/Los_Angeles"

    def test_valid_utc_timezone(self):
        """Test UTC timezone validation."""
        params = AlexaRequestParams(tz="UTC")
        assert params.tz == "UTC"

    def test_none_timezone(self):
        """Test None timezone is allowed."""
        params = AlexaRequestParams(tz=None)
        assert params.tz is None

    def test_missing_timezone(self):
        """Test missing timezone defaults to None."""
        params = AlexaRequestParams()  # type: ignore[call-arg]
        assert params.tz is None

    def test_invalid_timezone(self):
        """Test invalid timezone raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AlexaRequestParams(tz="Invalid/Timezone")
        assert "Invalid timezone" in str(exc_info.value)

    def test_empty_string_timezone(self):
        """Test empty string timezone raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AlexaRequestParams(tz="")
        # Empty string will fail ZoneInfo lookup
        # Error message varies based on Python version
        error_msg = str(exc_info.value).lower()
        assert "tz" in error_msg or "zoneinfo" in error_msg


class TestMorningSummaryRequestParams:
    """Test morning summary request parameter validation."""

    def test_valid_params(self):
        """Test valid morning summary parameters."""
        params = MorningSummaryRequestParams(
            date="2025-11-03",
            timezone="America/New_York",
            detail_level="detailed",
            prefer_ssml=True,
            max_events=75,
        )
        assert params.date == "2025-11-03"
        assert params.timezone == "America/New_York"
        assert params.detail_level == "detailed"
        assert params.prefer_ssml is True
        assert params.max_events == 75

    def test_defaults(self):
        """Test default parameter values."""
        params = MorningSummaryRequestParams()  # type: ignore[call-arg]
        assert params.date is None
        assert params.timezone == "UTC"
        assert params.detail_level == "normal"
        assert params.prefer_ssml is False
        assert params.max_events == 50

    def test_invalid_date_format(self):
        """Test invalid date format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(date="11/03/2025")  # type: ignore[call-arg]
        assert "date" in str(exc_info.value).lower()

    def test_invalid_date_value(self):
        """Test invalid date value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(date="2025-13-45")  # type: ignore[call-arg]
        assert "Invalid date format" in str(exc_info.value)

    def test_invalid_timezone(self):
        """Test invalid timezone raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(timezone="Invalid/TZ")  # type: ignore[call-arg]
        assert "Invalid timezone" in str(exc_info.value)

    def test_invalid_detail_level(self):
        """Test invalid detail level raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(detail_level="extreme")  # type: ignore[call-arg]
        # Pydantic will reject non-literal values
        assert "detail_level" in str(exc_info.value).lower()

    def test_max_events_too_low(self):
        """Test max_events < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(max_events=0)  # type: ignore[call-arg]
        assert "max_events" in str(exc_info.value).lower()

    def test_max_events_too_high(self):
        """Test max_events > 100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(max_events=101)  # type: ignore[call-arg]
        assert "max_events" in str(exc_info.value).lower()

    def test_prefer_ssml_string_true(self):
        """Test prefer_ssml string 'true' is converted to boolean."""
        params = MorningSummaryRequestParams(prefer_ssml="true")  # type: ignore[call-arg]
        assert params.prefer_ssml is True

    def test_prefer_ssml_string_false(self):
        """Test prefer_ssml string 'false' is converted to boolean."""
        params = MorningSummaryRequestParams(prefer_ssml="false")  # type: ignore[call-arg]
        assert params.prefer_ssml is False

    def test_prefer_ssml_string_other(self):
        """Test prefer_ssml string other than 'true' is false."""
        params = MorningSummaryRequestParams(prefer_ssml="yes")  # type: ignore[call-arg]
        assert params.prefer_ssml is False

    def test_max_events_string_conversion(self):
        """Test max_events string is converted to int."""
        params = MorningSummaryRequestParams(max_events="75")  # type: ignore[call-arg]
        assert params.max_events == 75
        assert isinstance(params.max_events, int)

    def test_max_events_invalid_string(self):
        """Test max_events invalid string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MorningSummaryRequestParams(max_events="not_a_number")  # type: ignore[call-arg]
        assert "max_events" in str(exc_info.value).lower()


class TestNextMeetingRequestParams:
    """Test next meeting request parameter validation."""

    def test_inherits_from_base(self):
        """Test NextMeetingRequestParams inherits base validation."""
        params = NextMeetingRequestParams(tz="Europe/London")
        assert params.tz == "Europe/London"

    def test_invalid_timezone_inherited(self):
        """Test invalid timezone validation is inherited."""
        with pytest.raises(ValidationError):
            NextMeetingRequestParams(tz="Bad/TZ")


class TestTimeUntilRequestParams:
    """Test time until request parameter validation."""

    def test_inherits_from_base(self):
        """Test TimeUntilRequestParams inherits base validation."""
        params = TimeUntilRequestParams(tz="Asia/Tokyo")
        assert params.tz == "Asia/Tokyo"


class TestDoneForDayRequestParams:
    """Test done for day request parameter validation."""

    def test_inherits_from_base(self):
        """Test DoneForDayRequestParams inherits base validation."""
        params = DoneForDayRequestParams(tz="Australia/Sydney")
        assert params.tz == "Australia/Sydney"


class TestLaunchSummaryRequestParams:
    """Test launch summary request parameter validation."""

    def test_inherits_from_base(self):
        """Test LaunchSummaryRequestParams inherits base validation."""
        params = LaunchSummaryRequestParams(tz="America/Chicago")
        assert params.tz == "America/Chicago"
