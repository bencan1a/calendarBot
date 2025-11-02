"""Unit tests for lite_event_parser module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from calendarbot_lite.lite_attendee_parser import LiteAttendeeParser
from calendarbot_lite.lite_datetime_utils import LiteDateTimeParser
from calendarbot_lite.lite_event_parser import LiteEventComponentParser
from calendarbot_lite.lite_models import LiteEventStatus

pytestmark = pytest.mark.unit


class TestLiteEventComponentParser:
    """Tests for LiteEventComponentParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.datetime_parser = LiteDateTimeParser()
        self.attendee_parser = LiteAttendeeParser()
        self.parser = LiteEventComponentParser(
            self.datetime_parser, self.attendee_parser
        )

    def test_parse_status_with_none(self):
        """Test parsing None status returns None."""
        result = self.parser._parse_status(None)
        assert result is None

    def test_parse_status_with_confirmed(self):
        """Test parsing CONFIRMED status."""
        status_prop = MagicMock()
        status_prop.__str__ = lambda self: "CONFIRMED"

        result = self.parser._parse_status(status_prop)
        assert result == "CONFIRMED"

    def test_parse_status_with_lowercase(self):
        """Test parsing status converts to uppercase."""
        status_prop = MagicMock()
        status_prop.__str__ = lambda self: "tentative"

        result = self.parser._parse_status(status_prop)
        assert result == "TENTATIVE"

    def test_map_transparency_cancelled_status(self):
        """Test mapping cancelled status."""
        component = MagicMock()
        component.get = MagicMock(return_value=None)

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "CANCELLED", component
        )

        assert result == LiteEventStatus.FREE

    def test_map_transparency_tentative_status(self):
        """Test mapping tentative status."""
        component = MagicMock()
        component.get = MagicMock(return_value=None)

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "TENTATIVE", component
        )

        assert result == LiteEventStatus.TENTATIVE

    def test_map_transparency_transparent(self):
        """Test mapping transparent events."""
        component = MagicMock()
        component.get = MagicMock(return_value=None)

        result = self.parser._map_transparency_to_status(
            "TRANSPARENT", None, component
        )

        assert result == LiteEventStatus.FREE

    def test_map_transparency_transparent_confirmed(self):
        """Test mapping transparent + confirmed events."""
        component = MagicMock()
        component.get = MagicMock(return_value=None)

        result = self.parser._map_transparency_to_status(
            "TRANSPARENT", "CONFIRMED", component
        )

        assert result == LiteEventStatus.TENTATIVE

    def test_map_transparency_opaque_default(self):
        """Test mapping opaque events default to BUSY."""
        component = MagicMock()
        component.get = MagicMock(return_value=None)

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "CONFIRMED", component
        )

        assert result == LiteEventStatus.BUSY

    def test_map_transparency_microsoft_deleted(self):
        """Test Microsoft phantom deleted events."""
        component = MagicMock()
        component.get = MagicMock(side_effect=lambda key: "TRUE" if key == "X-OUTLOOK-DELETED" else None)

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "CONFIRMED", component
        )

        assert result == LiteEventStatus.FREE

    def test_map_transparency_microsoft_busystatus_free(self):
        """Test Microsoft busy status FREE."""
        component = MagicMock()
        component.get = MagicMock(
            side_effect=lambda key: "FREE" if key == "X-MICROSOFT-CDO-BUSYSTATUS" else None
        )

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "CONFIRMED", component
        )

        assert result == LiteEventStatus.FREE

    def test_map_transparency_following_meeting(self):
        """Test Following: meeting special case."""
        component = MagicMock()
        component.get = MagicMock(side_effect=lambda key: "Following: Team Meeting" if key == "SUMMARY" else None)

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "CONFIRMED", component
        )

        assert result == LiteEventStatus.TENTATIVE

    def test_map_transparency_following_meeting_overrides_free(self):
        """Test Following: meeting overrides FREE busy status."""
        component = MagicMock()
        component.get = MagicMock(
            side_effect=lambda key: (
                "Following: Team Meeting" if key == "SUMMARY"
                else "FREE" if key == "X-MICROSOFT-CDO-BUSYSTATUS"
                else None
            )
        )

        result = self.parser._map_transparency_to_status(
            "OPAQUE", "CONFIRMED", component
        )

        assert result == LiteEventStatus.TENTATIVE

    def test_detect_online_meeting_teams(self):
        """Test detection of Microsoft Teams meeting."""
        description = "Join us on Microsoft Teams: https://teams.microsoft.com/l/meetup/..."

        is_online, url = self.parser._detect_online_meeting(description)

        assert is_online is True
        assert url is not None
        assert "teams.microsoft.com" in url

    def test_detect_online_meeting_zoom(self):
        """Test detection of Zoom meeting."""
        description = "Zoom meeting: https://zoom.us/j/123456789"

        is_online, url = self.parser._detect_online_meeting(description)

        assert is_online is True
        assert url is not None
        assert "zoom.us" in url

    def test_detect_online_meeting_google_meet(self):
        """Test detection of Google Meet meeting."""
        description = "Join on Google Meet: https://meet.google.com/abc-defg-hij"

        is_online, url = self.parser._detect_online_meeting(description)

        assert is_online is True
        assert url is not None
        assert "meet.google.com" in url

    def test_detect_online_meeting_none(self):
        """Test no online meeting detected."""
        description = "Regular in-person meeting in Conference Room A"

        is_online, url = self.parser._detect_online_meeting(description)

        assert is_online is False
        assert url is None

    def test_detect_online_meeting_empty(self):
        """Test empty description."""
        is_online, url = self.parser._detect_online_meeting(None)

        assert is_online is False
        assert url is None

    def test_collect_exdate_props_using_getall(self):
        """Test collecting EXDATE using getall()."""
        component = MagicMock()
        exdate1 = MagicMock()
        exdate2 = MagicMock()
        component.getall = MagicMock(return_value=[exdate1, exdate2])

        result = self.parser._collect_exdate_props(component)

        assert len(result) == 2
        assert exdate1 in result
        assert exdate2 in result

    def test_collect_exdate_props_using_dict_access_single(self):
        """Test collecting EXDATE using dict access (single value)."""
        component = MagicMock()
        exdate = MagicMock()
        component.getall = MagicMock(side_effect=Exception("Not supported"))
        component.__contains__ = MagicMock(return_value=True)
        component.__getitem__ = MagicMock(return_value=exdate)

        result = self.parser._collect_exdate_props(component)

        assert len(result) == 1
        assert exdate in result

    def test_collect_exdate_props_using_dict_access_list(self):
        """Test collecting EXDATE using dict access (list value)."""
        component = MagicMock()
        exdate1, exdate2 = MagicMock(), MagicMock()
        component.getall = MagicMock(side_effect=Exception("Not supported"))
        component.__contains__ = MagicMock(return_value=True)
        component.__getitem__ = MagicMock(return_value=[exdate1, exdate2])

        result = self.parser._collect_exdate_props(component)

        assert len(result) == 2

    def test_collect_exdate_props_empty(self):
        """Test collecting EXDATE when none present."""
        component = MagicMock()
        component.getall = MagicMock(side_effect=Exception("Not supported"))
        component.__contains__ = MagicMock(return_value=False)
        component.property_items = MagicMock(return_value=[])

        result = self.parser._collect_exdate_props(component)

        assert len(result) == 0

    def test_parse_event_component_missing_dtstart(self):
        """Test parsing event without DTSTART returns None."""
        component = MagicMock()
        component.get = MagicMock(side_effect=lambda key: None if key == "DTSTART" else "test-uid")

        result = self.parser.parse_event_component(component)

        assert result is None

    def test_parse_event_component_basic_event(self):
        """Test parsing basic event."""
        component = MagicMock()

        # Setup component properties
        uid = "test-event-123"
        summary = "Test Event"

        # Mock DTSTART
        dtstart = MagicMock()
        dtstart.dt = datetime(2023, 12, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Mock DTEND
        dtend = MagicMock()
        dtend.dt = datetime(2023, 12, 1, 11, 0, 0, tzinfo=timezone.utc)

        component.get = MagicMock(side_effect=lambda key, default=None: {
            "UID": uid,
            "SUMMARY": summary,
            "DTSTART": dtstart,
            "DTEND": dtend,
            "TRANSP": "OPAQUE",
            "STATUS": None,
            "DESCRIPTION": None,
            "LOCATION": None,
            "ORGANIZER": None,
            "ATTENDEE": [],
            "RRULE": None,
            "RECURRENCE-ID": None,
            "CREATED": None,
            "LAST-MODIFIED": None,
        }.get(key, default))

        result = self.parser.parse_event_component(component)

        assert result is not None
        assert result.id == uid
        assert result.subject == summary
        assert result.start.date_time == dtstart.dt
        assert result.end.date_time == dtend.dt
        assert result.is_all_day is False
        assert result.show_as == LiteEventStatus.BUSY

    def test_parse_event_component_all_day(self):
        """Test parsing all-day event."""
        from datetime import date

        component = MagicMock()

        # Mock DTSTART as date (not datetime)
        dtstart = MagicMock()
        dtstart.dt = date(2023, 12, 1)

        component.get = MagicMock(side_effect=lambda key, default=None: {
            "UID": "all-day-event",
            "SUMMARY": "All Day Event",
            "DTSTART": dtstart,
            "DTEND": None,
            "TRANSP": "OPAQUE",
        }.get(key, default))

        result = self.parser.parse_event_component(component)

        assert result is not None
        assert result.is_all_day is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
