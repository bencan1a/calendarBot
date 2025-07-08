"""Unit tests for Pydantic V2 serialization fixes."""

import json
from datetime import datetime

import pytest

from calendarbot.cache.models import CalendarEvent
from calendarbot.ics.models import CalendarEvent as ICSCalendarEvent
from calendarbot.ics.models import DateTimeInfo


class TestDateTimeInfoSerialization:
    """Test DateTimeInfo serialization with field_serializer."""

    def test_datetime_serialization(self):
        """Test that datetime fields are properly serialized to ISO format."""
        # Arrange
        test_datetime = datetime(2023, 12, 25, 10, 30, 0)
        datetime_info = DateTimeInfo(date_time=test_datetime, time_zone="US/Pacific")

        # Act
        serialized = datetime_info.model_dump(mode="json")

        # Assert
        assert serialized["date_time"] == test_datetime.isoformat()
        assert serialized["time_zone"] == "US/Pacific"

    def test_json_dump_works(self):
        """Test that the model can be properly JSON serialized."""
        # Arrange
        test_datetime = datetime(2023, 12, 25, 10, 30, 0)
        datetime_info = DateTimeInfo(date_time=test_datetime, time_zone="UTC")

        # Act
        json_str = json.dumps(datetime_info.model_dump(mode="json"))

        # Assert
        assert test_datetime.isoformat() in json_str
        assert "UTC" in json_str


class TestCalendarEventSerialization:
    """Test CalendarEvent serialization with field_serializer."""

    def test_datetime_fields_serialization(self):
        """Test that datetime fields are properly serialized."""
        # Arrange
        start_time = datetime(2023, 12, 25, 10, 0, 0)
        end_time = datetime(2023, 12, 25, 11, 0, 0)
        last_modified = datetime(2023, 12, 24, 15, 30, 0)

        event = CalendarEvent(
            id="test-123",
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            last_modified=last_modified,
        )

        # Act
        serialized = event.model_dump(mode="json")

        # Assert
        assert serialized["start_time"] == start_time.isoformat()
        assert serialized["end_time"] == end_time.isoformat()
        assert serialized["last_modified"] == last_modified.isoformat()

    def test_none_datetime_serialization(self):
        """Test that None datetime fields are handled correctly."""
        # Arrange
        start_time = datetime(2023, 12, 25, 10, 0, 0)
        end_time = datetime(2023, 12, 25, 11, 0, 0)

        event = CalendarEvent(
            id="test-123",
            title="Test Event",
            start_time=start_time,
            end_time=end_time,
            last_modified=None,  # Test None value
        )

        # Act
        serialized = event.model_dump(mode="json")

        # Assert
        assert serialized["start_time"] == start_time.isoformat()
        assert serialized["end_time"] == end_time.isoformat()
        assert serialized["last_modified"] is None

    def test_json_dump_works(self):
        """Test that the model can be properly JSON serialized."""
        # Arrange
        start_time = datetime(2023, 12, 25, 10, 0, 0)
        end_time = datetime(2023, 12, 25, 11, 0, 0)

        event = CalendarEvent(
            id="test-123", title="Test Event", start_time=start_time, end_time=end_time
        )

        # Act
        json_str = json.dumps(event.model_dump(mode="json"))

        # Assert
        assert start_time.isoformat() in json_str
        assert end_time.isoformat() in json_str
        assert "test-123" in json_str


class TestICSCalendarEventSerialization:
    """Test ICS CalendarEvent serialization with field_serializer."""

    def test_datetime_fields_serialization(self):
        """Test that datetime fields are properly serialized."""
        # Arrange
        start_datetime = datetime(2023, 12, 25, 10, 0, 0)
        end_datetime = datetime(2023, 12, 25, 11, 0, 0)
        created_datetime = datetime(2023, 12, 24, 15, 30, 0)
        last_modified_datetime = datetime(2023, 12, 24, 16, 0, 0)

        start_info = DateTimeInfo(date_time=start_datetime, time_zone="UTC")
        end_info = DateTimeInfo(date_time=end_datetime, time_zone="UTC")

        event = ICSCalendarEvent(
            id="test-ics-123",
            subject="Test ICS Event",
            start=start_info,
            end=end_info,
            created_date_time=created_datetime,
            last_modified_date_time=last_modified_datetime,
        )

        # Act
        serialized = event.model_dump(mode="json")

        # Assert
        assert serialized["created_date_time"] == created_datetime.isoformat()
        assert serialized["last_modified_date_time"] == last_modified_datetime.isoformat()

    def test_none_datetime_fields_serialization(self):
        """Test that None datetime fields are handled correctly."""
        # Arrange
        start_datetime = datetime(2023, 12, 25, 10, 0, 0)
        end_datetime = datetime(2023, 12, 25, 11, 0, 0)

        start_info = DateTimeInfo(date_time=start_datetime, time_zone="UTC")
        end_info = DateTimeInfo(date_time=end_datetime, time_zone="UTC")

        event = ICSCalendarEvent(
            id="test-ics-123",
            subject="Test ICS Event",
            start=start_info,
            end=end_info,
            created_date_time=None,
            last_modified_date_time=None,
        )

        # Act
        serialized = event.model_dump(mode="json")

        # Assert
        assert serialized["created_date_time"] is None
        assert serialized["last_modified_date_time"] is None

    def test_json_dump_works(self):
        """Test that the model can be properly JSON serialized."""
        # Arrange
        start_datetime = datetime(2023, 12, 25, 10, 0, 0)
        end_datetime = datetime(2023, 12, 25, 11, 0, 0)

        start_info = DateTimeInfo(date_time=start_datetime, time_zone="UTC")
        end_info = DateTimeInfo(date_time=end_datetime, time_zone="UTC")

        event = ICSCalendarEvent(
            id="test-ics-123", subject="Test ICS Event", start=start_info, end=end_info
        )

        # Act
        json_str = json.dumps(event.model_dump(mode="json"))

        # Assert
        assert "test-ics-123" in json_str
        assert "Test ICS Event" in json_str
        # DateTimeInfo should be serialized with its field_serializer
        assert start_datetime.isoformat() in json_str


class TestBackwardsCompatibility:
    """Test that the changes maintain backwards compatibility."""

    def test_model_dump_produces_same_output_as_before(self):
        """Test that model_dump produces the same output as the old json_encoders."""
        # Arrange
        test_datetime = datetime(2023, 12, 25, 10, 30, 45, 123456)
        datetime_info = DateTimeInfo(date_time=test_datetime, time_zone="US/Eastern")

        # Act
        serialized = datetime_info.model_dump(mode="json")

        # Assert - should match what json_encoders would have produced
        expected_datetime_str = test_datetime.isoformat()
        assert serialized["date_time"] == expected_datetime_str
        assert isinstance(serialized["date_time"], str)

    def test_serialization_handles_microseconds(self):
        """Test that datetime serialization correctly handles microseconds."""
        # Arrange
        test_datetime = datetime(2023, 12, 25, 10, 30, 45, 123456)
        event = CalendarEvent(
            id="test-microseconds",
            title="Test Microseconds",
            start_time=test_datetime,
            end_time=test_datetime,
        )

        # Act
        serialized = event.model_dump(mode="json")

        # Assert
        expected_str = test_datetime.isoformat()
        assert serialized["start_time"] == expected_str
        assert ".123456" in serialized["start_time"]  # Microseconds preserved
