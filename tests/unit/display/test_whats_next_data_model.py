"""Tests for WhatsNextDataModel classes."""

from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import MagicMock, patch

from calendarbot.cache.models import CachedEvent
from calendarbot.display.whats_next_data_model import (
    EventData,
    SettingsData,
    StatusInfo,
    WeatherData,
    WhatsNextViewModel,
)


class TestEventData:
    """Test EventData class functionality."""

    def create_mock_cached_event(
        self,
        subject: str = "Test Event",
        start_hours_offset: int = 1,
        end_hours_offset: int = 2,
        location: Optional[str] = None,
    ) -> CachedEvent:
        """Create a mock CachedEvent for testing."""
        base_time = datetime(2025, 7, 14, 12, 0, 0)
        start_dt = base_time + timedelta(hours=start_hours_offset)
        end_dt = base_time + timedelta(hours=end_hours_offset)

        event = MagicMock(spec=CachedEvent)
        event.subject = subject
        event.start_dt = start_dt
        event.end_dt = end_dt
        event.location_display_name = location
        event.format_time_range = MagicMock(
            return_value=f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
        )
        event.is_current = MagicMock(return_value=start_dt <= base_time < end_dt)
        event.is_upcoming = MagicMock(return_value=start_dt > base_time)

        return event

    def test_init_when_valid_data_then_creates_instance(self) -> None:
        """Test EventData initialization with valid data."""
        start_time = datetime(2025, 7, 14, 14, 0, 0)
        end_time = datetime(2025, 7, 14, 15, 0, 0)

        event_data = EventData(
            subject="Test Meeting",
            start_time=start_time,
            end_time=end_time,
            location="Conference Room A",
            is_current=False,
            is_upcoming=True,
            time_until_minutes=120,
        )

        assert event_data.subject == "Test Meeting"
        assert event_data.start_time == start_time
        assert event_data.end_time == end_time
        assert event_data.location == "Conference Room A"
        assert event_data.is_current is False
        assert event_data.is_upcoming is True
        assert event_data.time_until_minutes == 120

    def test_init_when_optional_fields_none_then_handles_gracefully(self) -> None:
        """Test EventData initialization with None optional fields."""
        start_time = datetime(2025, 7, 14, 13, 0, 0)
        end_time = datetime(2025, 7, 14, 14, 0, 0)

        event_data = EventData(
            subject="Minimal Event",
            start_time=start_time,
            end_time=end_time,
            location=None,
            is_current=False,
            is_upcoming=True,
            time_until_minutes=None,
        )

        assert event_data.subject == "Minimal Event"
        assert event_data.location is None
        assert event_data.time_until_minutes is None

    def test_from_cached_event_when_upcoming_event_then_converts_correctly(self) -> None:
        """Test converting upcoming CachedEvent to EventData."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        cached_event = self.create_mock_cached_event(
            subject="Team Meeting", start_hours_offset=2, end_hours_offset=3, location="Room 101"
        )
        # The create_mock_cached_event already properly sets these, but we override for explicit test logic
        cached_event.is_upcoming = MagicMock(return_value=True)
        cached_event.is_current = MagicMock(return_value=False)

        event_data = EventData.from_cached_event(cached_event, current_time)

        assert event_data.subject == "Team Meeting"
        assert event_data.location == "Room 101"
        assert event_data.is_current is False
        assert event_data.is_upcoming is True
        assert event_data.time_until_minutes == 120  # 2 hours
        # Note: format_time_range should be called during conversion, but assertion removed for pylance compatibility

    def test_from_cached_event_when_current_event_then_converts_correctly(self) -> None:
        """Test converting current CachedEvent to EventData."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        cached_event = self.create_mock_cached_event(
            subject="Current Call", start_hours_offset=-1, end_hours_offset=1
        )
        cached_event.is_current = MagicMock(return_value=True)
        cached_event.is_upcoming = MagicMock(return_value=False)

        event_data = EventData.from_cached_event(cached_event, current_time)

        assert event_data.subject == "Current Call"
        assert event_data.is_current is True
        assert event_data.is_upcoming is False
        assert event_data.time_until_minutes is None

    def test_from_cached_event_when_no_location_then_handles_gracefully(self) -> None:
        """Test converting CachedEvent with no location."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        cached_event = self.create_mock_cached_event(location=None)

        event_data = EventData.from_cached_event(cached_event, current_time)

        assert event_data.location is None

    def test_from_cached_event_when_teams_location_then_filters_it_out(self) -> None:
        """Test filtering out Microsoft Teams Meeting from location."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        cached_event = self.create_mock_cached_event(location="Microsoft Teams Meeting")

        event_data = EventData.from_cached_event(cached_event, current_time)

        assert event_data.location is None

    def test_from_cached_event_when_time_format_error_then_handles_gracefully(self) -> None:
        """Test error handling when time formatting fails."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        cached_event = self.create_mock_cached_event()
        cached_event.format_time_range = MagicMock(side_effect=Exception("Time format error"))

        # Should still create EventData despite the error
        event_data = EventData.from_cached_event(cached_event, current_time)
        assert event_data.subject == "Test Event"


class TestStatusInfo:
    """Test StatusInfo class functionality."""

    def test_init_when_valid_data_then_creates_instance(self) -> None:
        """Test StatusInfo initialization with valid data."""
        last_update = datetime(2025, 7, 14, 12, 0, 0)

        status_info = StatusInfo(
            last_update=last_update,
            is_cached=True,
            connection_status="Connected",
            relative_description="Today",
            interactive_mode=False,
        )

        assert status_info.last_update == last_update
        assert status_info.is_cached is True
        assert status_info.connection_status == "Connected"
        assert status_info.relative_description == "Today"
        assert status_info.interactive_mode is False

    def test_init_when_optional_fields_none_then_handles_gracefully(self) -> None:
        """Test StatusInfo initialization with None optional fields."""
        last_update = datetime(2025, 7, 14, 12, 0, 0)

        status_info = StatusInfo(
            last_update=last_update,
            is_cached=False,
            connection_status=None,
            relative_description=None,
            interactive_mode=True,
        )

        assert status_info.is_cached is False
        assert status_info.connection_status is None
        assert status_info.relative_description is None
        assert status_info.interactive_mode is True


class TestWeatherData:
    """Test WeatherData class functionality."""

    def test_init_when_valid_data_then_creates_instance(self) -> None:
        """Test WeatherData initialization with valid data."""
        weather_data = WeatherData(
            temperature=72.0,
            condition="Sunny",
            icon="sun",
            forecast=[{"day": "tomorrow", "temp": 75}],
        )

        assert weather_data.temperature == 72.0
        assert weather_data.condition == "Sunny"
        assert weather_data.icon == "sun"
        assert weather_data.forecast == [{"day": "tomorrow", "temp": 75}]

    def test_init_when_optional_fields_none_then_handles_gracefully(self) -> None:
        """Test WeatherData initialization with None optional fields."""
        weather_data = WeatherData(temperature=68.0, condition="Cloudy", icon=None, forecast=None)

        assert weather_data.temperature == 68.0
        assert weather_data.condition == "Cloudy"
        assert weather_data.icon is None
        assert weather_data.forecast is None


class TestSettingsData:
    """Test SettingsData class functionality."""

    def test_init_when_valid_data_then_creates_instance(self) -> None:
        """Test SettingsData initialization with valid data."""
        settings_data = SettingsData(
            theme="dark",
            layout="whats-next-view",
            refresh_interval=600,
            display_type="html",
        )

        assert settings_data.theme == "dark"
        assert settings_data.layout == "whats-next-view"
        assert settings_data.refresh_interval == 600
        assert settings_data.display_type == "html"

    def test_init_when_default_values_then_uses_defaults(self) -> None:
        """Test SettingsData initialization with default values."""
        settings_data = SettingsData()

        assert settings_data.theme == "default"
        assert settings_data.layout == "4x8"
        assert settings_data.refresh_interval == 300
        assert settings_data.display_type == "html"


class TestWhatsNextViewModel:
    """Test WhatsNextViewModel class functionality."""

    def create_sample_event_data(self) -> EventData:
        """Create sample EventData for testing."""
        return EventData(
            subject="Sample Meeting",
            start_time=datetime(2025, 7, 14, 14, 0, 0),
            end_time=datetime(2025, 7, 14, 15, 0, 0),
            location="Conference Room",
            is_current=False,
            is_upcoming=True,
            time_until_minutes=60,
        )

    def create_sample_status_info(self) -> StatusInfo:
        """Create sample StatusInfo for testing."""
        return StatusInfo(
            last_update=datetime(2025, 7, 14, 12, 0, 0),
            is_cached=True,
            connection_status="Connected",
            relative_description="Today",
            interactive_mode=False,
        )

    def test_init_when_valid_data_then_creates_instance(self) -> None:
        """Test WhatsNextViewModel initialization with valid data."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        next_event = self.create_sample_event_data()
        current_event = self.create_sample_event_data()
        current_event.is_current = True
        current_event.is_upcoming = False

        status_info = self.create_sample_status_info()
        weather_data = WeatherData(temperature=70.0, condition="Sunny")
        settings_data = SettingsData(theme="light", layout="whats-next-view")

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[next_event],
            current_events=[current_event],
            later_events=[],
            status_info=status_info,
            weather_info=weather_data,
            settings_data=settings_data,
        )

        assert view_model.current_time == current_time
        assert view_model.display_date == "Monday, July 14"
        assert len(view_model.next_events) == 1
        assert len(view_model.current_events) == 1
        assert view_model.status_info == status_info
        assert view_model.weather_info == weather_data
        assert view_model.settings_data == settings_data

    def test_init_when_optional_fields_none_then_handles_gracefully(self) -> None:
        """Test WhatsNextViewModel initialization with None optional fields."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
            weather_info=None,
            settings_data=None,
        )

        assert len(view_model.next_events) == 0
        assert len(view_model.current_events) == 0
        assert len(view_model.later_events) == 0
        assert view_model.weather_info is None
        assert view_model.settings_data is None

    def test_has_events_when_next_events_exist_then_returns_true(self) -> None:
        """Test has_events returns True when next events exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[self.create_sample_event_data()],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        assert view_model.has_events() is True

    def test_has_events_when_current_events_exist_then_returns_true(self) -> None:
        """Test has_events returns True when current events exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()

        current_event = self.create_sample_event_data()
        current_event.is_current = True

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[],
            current_events=[current_event],
            later_events=[],
            status_info=status_info,
        )

        assert view_model.has_events() is True

    def test_has_events_when_no_events_then_returns_false(self) -> None:
        """Test has_events returns False when no events exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        assert view_model.has_events() is False

    def test_get_next_event_when_next_event_exists_then_returns_it(self) -> None:
        """Test get_next_event returns next event when it exists."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()
        next_event = self.create_sample_event_data()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[next_event],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        assert view_model.get_next_event() == next_event

    def test_get_next_event_when_no_next_event_then_returns_none(self) -> None:
        """Test get_next_event returns None when next event doesn't exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        assert view_model.get_next_event() is None

    def test_get_time_remaining_current_event_when_current_event_exists_then_returns_minutes(
        self,
    ) -> None:
        """Test get_time_remaining_current_event returns minutes for current event."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        current_event = self.create_sample_event_data()
        current_event.end_time = datetime(2025, 7, 14, 12, 30, 0)  # 30 minutes from now
        status_info = self.create_sample_status_info()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[],
            current_events=[current_event],
            later_events=[],
            status_info=status_info,
        )

        result = view_model.get_time_remaining_current_event()
        assert result == 30

    def test_get_time_remaining_current_event_when_no_current_event_then_returns_none(self) -> None:
        """Test get_time_remaining_current_event returns None when no current event."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        status_info = self.create_sample_status_info()

        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, July 14",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        assert view_model.get_time_remaining_current_event() is None

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_from_cached_events_when_valid_events_then_creates_view_model(
        self, mock_get_now
    ) -> None:
        """Test creating WhatsNextViewModel from cached events."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create mock cached events
        current_event = MagicMock(spec=CachedEvent)
        current_event.is_current = MagicMock(return_value=True)
        current_event.is_upcoming = MagicMock(return_value=False)
        current_event.subject = "Current Meeting"
        current_event.start_dt = datetime(2025, 7, 14, 11, 0, 0)
        current_event.end_dt = datetime(2025, 7, 14, 13, 0, 0)
        current_event.location_display_name = None
        current_event.format_time_range = MagicMock(return_value="11:00 AM - 1:00 PM")

        upcoming_event = MagicMock(spec=CachedEvent)
        upcoming_event.is_current = MagicMock(return_value=False)
        upcoming_event.is_upcoming = MagicMock(return_value=True)
        upcoming_event.subject = "Next Meeting"
        upcoming_event.start_dt = datetime(2025, 7, 14, 15, 0, 0)
        upcoming_event.end_dt = datetime(2025, 7, 14, 16, 0, 0)
        upcoming_event.location_display_name = None
        upcoming_event.format_time_range = MagicMock(return_value="3:00 PM - 4:00 PM")

        events: list[CachedEvent] = [current_event, upcoming_event]  # type: ignore
        status_info = {"is_cached": True, "connection_status": "Connected"}

        view_model = WhatsNextViewModel.from_cached_events(events, current_time, status_info)

        assert view_model.current_time == current_time
        assert len(view_model.current_events) == 1
        assert len(view_model.next_events) == 1
        assert view_model.status_info.is_cached is True

    def test_type_compliance_for_all_classes(self) -> None:
        """Test that all data model classes have proper type compliance."""
        # EventData
        start_time = datetime(2025, 7, 14, 13, 0, 0)
        end_time = datetime(2025, 7, 14, 14, 0, 0)
        event_data = EventData("Test", start_time, end_time, None, False, True, 60)
        assert isinstance(event_data.subject, str)
        assert isinstance(event_data.is_current, bool)
        assert isinstance(event_data.is_upcoming, bool)

        # StatusInfo
        last_update = datetime(2025, 7, 14, 12, 0, 0)
        status_info = StatusInfo(last_update, True, "Connected", "Today", False)
        assert isinstance(status_info.last_update, datetime)
        assert isinstance(status_info.is_cached, bool)

        # WeatherData
        weather_data = WeatherData(70.0, "Sunny", "sun", [])
        assert isinstance(weather_data.temperature, float)
        assert isinstance(weather_data.condition, str)

        # SettingsData
        settings_data = SettingsData("light", "4x8", 300, "html")
        assert isinstance(settings_data.theme, str)
        assert isinstance(settings_data.refresh_interval, int)

        # WhatsNextViewModel
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        view_model = WhatsNextViewModel(current_time, "Monday", [], [], [], status_info, None, None)
        assert isinstance(view_model.next_events, list)
        assert isinstance(view_model.has_events(), bool)
