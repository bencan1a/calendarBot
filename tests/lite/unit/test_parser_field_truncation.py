"""Tests for parser handling of oversized event fields."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from calendarbot_lite.config_manager import (
    MAX_EVENT_DESCRIPTION_LENGTH,
    MAX_EVENT_LOCATION_LENGTH,
    MAX_EVENT_SUBJECT_LENGTH,
)
from calendarbot_lite.lite_attendee_parser import LiteAttendeeParser
from calendarbot_lite.lite_datetime_utils import LiteDateTimeParser
from calendarbot_lite.lite_event_parser import LiteEventComponentParser

pytestmark = pytest.mark.unit


class TestParserFieldTruncation:
    """Test that parser properly truncates oversized fields."""

    def _make_parser(self) -> LiteEventComponentParser:
        """Create a parser instance for testing."""
        datetime_parser = LiteDateTimeParser()
        attendee_parser = LiteAttendeeParser()
        return LiteEventComponentParser(datetime_parser, attendee_parser)

    def _make_mock_component(
        self,
        uid: str = "test-1",
        summary: str = "Test Event",
        description: str | None = None,
        location: str | None = None,
    ) -> MagicMock:
        """Create a mock iCalendar component."""
        component = MagicMock()
        component.get = MagicMock(
            side_effect=lambda key, default=None: {
                "UID": uid,
                "SUMMARY": summary,
                "DESCRIPTION": description,
                "LOCATION": location,
                "DTSTART": self._make_mock_dtstart(),
                "DTEND": self._make_mock_dtend(),
            }.get(key, default)
        )
        component.getall = MagicMock(return_value=None)
        component.__contains__ = MagicMock(return_value=False)
        return component

    def _make_mock_dtstart(self) -> MagicMock:
        """Create a mock DTSTART property."""
        mock_dtstart = MagicMock()
        mock_dtstart.dt = datetime(2025, 11, 5, 10, 0, 0, tzinfo=timezone.utc)
        return mock_dtstart

    def _make_mock_dtend(self) -> MagicMock:
        """Create a mock DTEND property."""
        mock_dtend = MagicMock()
        mock_dtend.dt = datetime(2025, 11, 5, 11, 0, 0, tzinfo=timezone.utc)
        return mock_dtend

    def test_parser_truncates_oversized_subject(self):
        """Test parser truncates subject exceeding maximum length."""
        parser = self._make_parser()
        oversized_subject = "A" * (MAX_EVENT_SUBJECT_LENGTH + 50)
        component = self._make_mock_component(summary=oversized_subject)

        event = parser.parse_event_component(component)

        assert event is not None
        assert len(event.subject) == MAX_EVENT_SUBJECT_LENGTH
        assert event.subject == "A" * MAX_EVENT_SUBJECT_LENGTH

    def test_parser_accepts_subject_at_max_length(self):
        """Test parser accepts subject at exact maximum length."""
        parser = self._make_parser()
        max_subject = "B" * MAX_EVENT_SUBJECT_LENGTH
        component = self._make_mock_component(summary=max_subject)

        event = parser.parse_event_component(component)

        assert event is not None
        assert len(event.subject) == MAX_EVENT_SUBJECT_LENGTH
        assert event.subject == max_subject

    def test_parser_truncates_oversized_description(self):
        """Test parser truncates description exceeding maximum length."""
        parser = self._make_parser()
        oversized_desc = "D" * (MAX_EVENT_DESCRIPTION_LENGTH + 100)
        component = self._make_mock_component(description=oversized_desc)

        event = parser.parse_event_component(component)

        assert event is not None
        assert event.body_preview is not None
        assert len(event.body_preview) == MAX_EVENT_DESCRIPTION_LENGTH
        assert event.body_preview == "D" * MAX_EVENT_DESCRIPTION_LENGTH

    def test_parser_accepts_description_at_max_length(self):
        """Test parser accepts description at exact maximum length."""
        parser = self._make_parser()
        max_desc = "E" * MAX_EVENT_DESCRIPTION_LENGTH
        component = self._make_mock_component(description=max_desc)

        event = parser.parse_event_component(component)

        assert event is not None
        assert event.body_preview is not None
        assert len(event.body_preview) == MAX_EVENT_DESCRIPTION_LENGTH
        assert event.body_preview == max_desc

    def test_parser_truncates_oversized_location(self):
        """Test parser truncates location exceeding maximum length."""
        parser = self._make_parser()
        oversized_location = "L" * (MAX_EVENT_LOCATION_LENGTH + 30)
        component = self._make_mock_component(location=oversized_location)

        event = parser.parse_event_component(component)

        assert event is not None
        assert event.location is not None
        assert len(event.location.display_name) == MAX_EVENT_LOCATION_LENGTH
        assert event.location.display_name == "L" * MAX_EVENT_LOCATION_LENGTH

    def test_parser_accepts_location_at_max_length(self):
        """Test parser accepts location at exact maximum length."""
        parser = self._make_parser()
        max_location = "M" * MAX_EVENT_LOCATION_LENGTH
        component = self._make_mock_component(location=max_location)

        event = parser.parse_event_component(component)

        assert event is not None
        assert event.location is not None
        assert len(event.location.display_name) == MAX_EVENT_LOCATION_LENGTH
        assert event.location.display_name == max_location

    def test_parser_handles_all_oversized_fields(self):
        """Test parser truncates all oversized fields simultaneously."""
        parser = self._make_parser()
        oversized_subject = "S" * (MAX_EVENT_SUBJECT_LENGTH + 10)
        oversized_desc = "D" * (MAX_EVENT_DESCRIPTION_LENGTH + 20)
        oversized_location = "L" * (MAX_EVENT_LOCATION_LENGTH + 5)

        component = self._make_mock_component(
            summary=oversized_subject,
            description=oversized_desc,
            location=oversized_location,
        )

        event = parser.parse_event_component(component)

        assert event is not None
        assert len(event.subject) == MAX_EVENT_SUBJECT_LENGTH
        assert event.body_preview is not None
        assert len(event.body_preview) == MAX_EVENT_DESCRIPTION_LENGTH
        assert event.location is not None
        assert len(event.location.display_name) == MAX_EVENT_LOCATION_LENGTH

    def test_parser_handles_empty_location_after_truncation(self):
        """Test parser handles location that becomes empty after truncation and stripping."""
        parser = self._make_parser()
        # Location with only whitespace should be set to None
        component = self._make_mock_component(location="   ")

        event = parser.parse_event_component(component)

        assert event is not None
        assert event.location is None  # Empty location should be None

    def test_parser_preserves_unicode_in_truncated_fields(self):
        """Test parser preserves unicode characters in truncated fields."""
        parser = self._make_parser()
        # Unicode characters (Japanese)
        oversized_subject = "会議" * (MAX_EVENT_SUBJECT_LENGTH // 2 + 10)
        component = self._make_mock_component(summary=oversized_subject)

        event = parser.parse_event_component(component)

        assert event is not None
        assert len(event.subject) <= MAX_EVENT_SUBJECT_LENGTH
        # Verify unicode is preserved (subject should contain Japanese characters)
        assert "会議" in event.subject
