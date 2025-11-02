"""Unit tests for lite_attendee_parser module."""

from unittest.mock import MagicMock

import pytest

from calendarbot_lite.lite_attendee_parser import LiteAttendeeParser
from calendarbot_lite.lite_models import LiteAttendeeType, LiteResponseStatus

pytestmark = pytest.mark.unit


class TestLiteAttendeeParser:
    """Tests for LiteAttendeeParser class."""

    def test_parse_attendee_basic(self):
        """Test parsing a basic attendee."""
        parser = LiteAttendeeParser()

        # Mock attendee property
        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:john.doe@example.com"
        attendee_prop.params = {
            "CN": "John Doe",
            "ROLE": "REQ-PARTICIPANT",
            "PARTSTAT": "ACCEPTED",
        }

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.name == "John Doe"
        assert result.email == "john.doe@example.com"
        assert result.type == LiteAttendeeType.REQUIRED
        assert result.response_status == LiteResponseStatus.ACCEPTED

    def test_parse_attendee_optional_participant(self):
        """Test parsing an optional attendee."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:jane.smith@example.com"
        attendee_prop.params = {
            "CN": "Jane Smith",
            "ROLE": "OPT-PARTICIPANT",
            "PARTSTAT": "NEEDS-ACTION",
        }

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.name == "Jane Smith"
        assert result.email == "jane.smith@example.com"
        assert result.type == LiteAttendeeType.OPTIONAL
        assert result.response_status == LiteResponseStatus.NOT_RESPONDED

    def test_parse_attendee_resource(self):
        """Test parsing a resource attendee."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:conference-room@example.com"
        attendee_prop.params = {
            "CN": "Conference Room A",
            "ROLE": "NON-PARTICIPANT",
            "PARTSTAT": "ACCEPTED",
        }

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.name == "Conference Room A"
        assert result.email == "conference-room@example.com"
        assert result.type == LiteAttendeeType.RESOURCE
        assert result.response_status == LiteResponseStatus.ACCEPTED

    def test_parse_attendee_declined(self):
        """Test parsing an attendee who declined."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:bob@example.com"
        attendee_prop.params = {
            "CN": "Bob",
            "ROLE": "REQ-PARTICIPANT",
            "PARTSTAT": "DECLINED",
        }

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.response_status == LiteResponseStatus.DECLINED

    def test_parse_attendee_tentative(self):
        """Test parsing an attendee who tentatively accepted."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:alice@example.com"
        attendee_prop.params = {
            "CN": "Alice",
            "ROLE": "REQ-PARTICIPANT",
            "PARTSTAT": "TENTATIVE",
        }

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.response_status == LiteResponseStatus.TENTATIVELY_ACCEPTED

    def test_parse_attendee_delegated(self):
        """Test parsing a delegated attendee."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:delegated@example.com"
        attendee_prop.params = {
            "CN": "Delegated User",
            "ROLE": "REQ-PARTICIPANT",
            "PARTSTAT": "DELEGATED",
        }

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.response_status == LiteResponseStatus.NOT_RESPONDED

    def test_parse_attendee_no_cn_uses_email_prefix(self):
        """Test parsing attendee without CN uses email prefix as name."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:noname@example.com"
        attendee_prop.params = {}

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.name == "noname"
        assert result.email == "noname@example.com"

    def test_parse_attendee_with_mailto_prefix(self):
        """Test parsing attendee with mailto: prefix."""
        parser = LiteAttendeeParser()

        attendee_prop = MagicMock()
        attendee_prop.__str__ = lambda self: "mailto:test@example.com"
        attendee_prop.params = {"CN": "Test User"}

        result = parser.parse_attendee(attendee_prop)

        assert result is not None
        assert result.email == "test@example.com"  # mailto: should be stripped

    def test_parse_attendee_invalid_returns_none(self):
        """Test parsing invalid attendee returns None."""
        parser = LiteAttendeeParser()

        # Mock property that raises exception
        attendee_prop = MagicMock()
        attendee_prop.__str__ = MagicMock(side_effect=Exception("Invalid"))
        attendee_prop.params = {}

        result = parser.parse_attendee(attendee_prop)

        assert result is None

    def test_parse_attendees_from_component(self):
        """Test parsing multiple attendees from component."""
        parser = LiteAttendeeParser()

        # Mock component with multiple attendees
        component = MagicMock()

        attendee1 = MagicMock()
        attendee1.__str__ = lambda self: "mailto:john@example.com"
        attendee1.params = {"CN": "John", "ROLE": "REQ-PARTICIPANT", "PARTSTAT": "ACCEPTED"}

        attendee2 = MagicMock()
        attendee2.__str__ = lambda self: "mailto:jane@example.com"
        attendee2.params = {"CN": "Jane", "ROLE": "OPT-PARTICIPANT", "PARTSTAT": "DECLINED"}

        component.get = MagicMock(return_value=[attendee1, attendee2])

        results = parser.parse_attendees(component)

        assert len(results) == 2
        assert results[0].name == "John"
        assert results[0].email == "john@example.com"
        assert results[1].name == "Jane"
        assert results[1].email == "jane@example.com"

    def test_parse_attendees_single_attendee(self):
        """Test parsing single attendee from component."""
        parser = LiteAttendeeParser()

        # Mock component with single attendee (not in list)
        component = MagicMock()

        attendee = MagicMock()
        attendee.__str__ = lambda self: "mailto:single@example.com"
        attendee.params = {"CN": "Single User"}

        component.get = MagicMock(return_value=attendee)

        results = parser.parse_attendees(component)

        assert len(results) == 1
        assert results[0].email == "single@example.com"

    def test_parse_attendees_no_attendees(self):
        """Test parsing component with no attendees."""
        parser = LiteAttendeeParser()

        # Mock component with no attendees
        component = MagicMock()
        component.get = MagicMock(return_value=[])

        results = parser.parse_attendees(component)

        assert len(results) == 0

    def test_parse_attendees_nested_list(self):
        """Test parsing attendees with nested list structure."""
        parser = LiteAttendeeParser()

        # Mock component with nested attendee lists
        component = MagicMock()

        attendee1 = MagicMock()
        attendee1.__str__ = lambda self: "mailto:user1@example.com"
        attendee1.params = {"CN": "User 1"}

        attendee2 = MagicMock()
        attendee2.__str__ = lambda self: "mailto:user2@example.com"
        attendee2.params = {"CN": "User 2"}

        # Nested list structure
        component.get = MagicMock(return_value=[[attendee1, attendee2]])

        results = parser.parse_attendees(component)

        assert len(results) == 2
        assert results[0].name == "User 1"
        assert results[1].name == "User 2"

    def test_parse_attendees_skips_invalid(self):
        """Test parsing attendees skips invalid entries."""
        parser = LiteAttendeeParser()

        # Mock component with mix of valid and invalid attendees
        component = MagicMock()

        valid_attendee = MagicMock()
        valid_attendee.__str__ = lambda self: "mailto:valid@example.com"
        valid_attendee.params = {"CN": "Valid User"}

        invalid_attendee = MagicMock()
        invalid_attendee.__str__ = MagicMock(side_effect=Exception("Invalid"))
        invalid_attendee.params = {}

        component.get = MagicMock(return_value=[valid_attendee, invalid_attendee])

        results = parser.parse_attendees(component)

        # Should only return the valid attendee
        assert len(results) == 1
        assert results[0].email == "valid@example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
