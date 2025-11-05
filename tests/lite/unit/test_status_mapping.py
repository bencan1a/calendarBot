"""
Comprehensive tests for status mapping logic in LiteEventComponentParser.

Tests all combinations of:
- TRANSP (TRANSPARENT/OPAQUE)
- STATUS (CANCELLED/TENTATIVE/CONFIRMED/None)
- Microsoft markers (X-OUTLOOK-DELETED, X-MICROSOFT-CDO-BUSYSTATUS)
- Special cases ("Following:" meetings)

Covers the refactoring of _map_transparency_to_status method.
"""

from datetime import UTC, datetime

import pytest
from icalendar import Event as ICalEvent

from calendarbot_lite.calendar.lite_event_parser import LiteEventComponentParser
from calendarbot_lite.calendar.lite_models import LiteEventStatus

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class DummyDateTimeParser:
    """Mock datetime parser for testing."""

    def parse_datetime(self, value, default_timezone=None):
        return getattr(value, "dt", value)

    def parse_datetime_optional(self, value):
        if value is None:
            return None
        return getattr(value, "dt", value)


class DummyAttendeeParser:
    """Mock attendee parser for testing."""

    def parse_attendees(self, component):
        return []


class DummySettings:
    """Mock settings for testing."""

    def __init__(self):
        self.user_email = "test@example.com"


@pytest.fixture
def parser():
    """Create parser instance for testing."""
    return LiteEventComponentParser(
        DummyDateTimeParser(),  # type: ignore[arg-type]
        DummyAttendeeParser(),  # type: ignore[arg-type]
        DummySettings(),
    )


def make_event(
    summary: str = "Test Event",
    transp: str | None = "OPAQUE",
    status: str | None = None,
    ms_deleted: str | None = None,
    ms_busystatus: str | None = None,
) -> ICalEvent:
    """Helper to create iCalendar event with specified properties."""
    ev = ICalEvent()
    ev.add("UID", "test-uid")
    ev.add("SUMMARY", summary)
    ev.add("DTSTART", datetime(2025, 1, 10, 9, 0, tzinfo=UTC))
    if transp:
        ev.add("TRANSP", transp)
    if status:
        ev.add("STATUS", status)
    if ms_deleted is not None:
        ev.add("X-OUTLOOK-DELETED", ms_deleted)
    if ms_busystatus is not None:
        ev.add("X-MICROSOFT-CDO-BUSYSTATUS", ms_busystatus)
    return ev


# ===== Microsoft Deletion Markers =====


def test_ms_deleted_true_returns_free(parser):
    """Microsoft deleted events should map to FREE."""
    ev = make_event(ms_deleted="TRUE")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.FREE


def test_ms_deleted_false_follows_normal_logic(parser):
    """MS-deleted=FALSE should follow normal mapping logic."""
    ev = make_event(ms_deleted="FALSE")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.BUSY


# ===== Microsoft Busy Status Override =====


def test_ms_busystatus_free_returns_free(parser):
    """Microsoft FREE busystatus should map to FREE."""
    ev = make_event(ms_busystatus="FREE")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.FREE


def test_ms_busystatus_free_with_following_returns_tentative(parser):
    """Following meetings with MS FREE busystatus should be TENTATIVE."""
    ev = make_event(summary="Following: Team Sync", ms_busystatus="FREE")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.TENTATIVE


def test_ms_busystatus_busy_follows_normal_logic(parser):
    """MS-busystatus=BUSY should follow normal logic."""
    ev = make_event(ms_busystatus="BUSY")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.BUSY


# ===== Status Property Mapping =====


def test_status_cancelled_returns_free(parser):
    """Cancelled events should map to FREE."""
    ev = make_event(status="CANCELLED")
    result = parser._map_transparency_to_status("OPAQUE", "CANCELLED", ev)
    assert result == LiteEventStatus.FREE


def test_status_tentative_returns_tentative(parser):
    """Tentative events should map to TENTATIVE."""
    ev = make_event(status="TENTATIVE")
    result = parser._map_transparency_to_status("OPAQUE", "TENTATIVE", ev)
    assert result == LiteEventStatus.TENTATIVE


# ===== Transparency Property Mapping =====


def test_transparent_without_status_returns_free(parser):
    """Transparent events without status should map to FREE."""
    ev = make_event(transp="TRANSPARENT", status=None)
    result = parser._map_transparency_to_status("TRANSPARENT", None, ev)
    assert result == LiteEventStatus.FREE


def test_transparent_with_confirmed_returns_tentative(parser):
    """Transparent + confirmed events should map to TENTATIVE."""
    ev = make_event(transp="TRANSPARENT", status="CONFIRMED")
    result = parser._map_transparency_to_status("TRANSPARENT", "CONFIRMED", ev)
    assert result == LiteEventStatus.TENTATIVE


def test_transparent_with_non_confirmed_returns_free(parser):
    """Transparent events without confirmed status should map to FREE."""
    ev = make_event(transp="TRANSPARENT", status="UNKNOWN")
    result = parser._map_transparency_to_status("TRANSPARENT", "UNKNOWN", ev)
    assert result == LiteEventStatus.FREE


# ===== Following Meeting Logic =====


def test_following_meeting_returns_tentative(parser):
    """Events with 'Following:' prefix should map to TENTATIVE."""
    ev = make_event(summary="Following: Weekly Review")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.TENTATIVE


def test_following_meeting_transparent_returns_free(parser):
    """Transparent takes precedence over Following meetings (returns FREE)."""
    ev = make_event(summary="Following: Standup", transp="TRANSPARENT")
    result = parser._map_transparency_to_status("TRANSPARENT", None, ev)
    # TRANSPARENT is checked before Following logic, so returns FREE
    assert result == LiteEventStatus.FREE


def test_following_meeting_cancelled_still_free(parser):
    """Cancelled Following meetings should be FREE (cancelled takes precedence)."""
    ev = make_event(summary="Following: Cancelled Meeting", status="CANCELLED")
    result = parser._map_transparency_to_status("OPAQUE", "CANCELLED", ev)
    assert result == LiteEventStatus.FREE


# ===== Default Cases =====


def test_opaque_no_status_returns_busy(parser):
    """Default OPAQUE events without status should map to BUSY."""
    ev = make_event(transp="OPAQUE", status=None)
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.BUSY


def test_no_transp_no_status_returns_busy(parser):
    """Events with no transparency or status should default to BUSY."""
    ev = make_event(transp=None, status=None)
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.BUSY


# ===== Edge Cases and Combinations =====


def test_case_insensitive_ms_deleted(parser):
    """MS-deleted marker should be case insensitive."""
    ev = make_event(ms_deleted="true")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.FREE


def test_case_insensitive_ms_busystatus(parser):
    """MS-busystatus should be case insensitive."""
    ev = make_event(ms_busystatus="free")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.FREE


def test_following_case_sensitive(parser):
    """'Following:' detection should be case sensitive."""
    ev = make_event(summary="following: meeting")  # lowercase
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    # Should NOT trigger following logic, should be BUSY
    assert result == LiteEventStatus.BUSY


def test_partial_following_text(parser):
    """'Following:' detection is case-sensitive (exact 'Following:' required)."""
    ev = make_event(summary="Now following: guidelines")
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    # Does NOT trigger because it's lowercase "following:" not "Following:"
    # The detection is case-sensitive and requires exact "Following:" string
    assert result == LiteEventStatus.BUSY


def test_ms_deleted_overrides_all(parser):
    """MS-deleted should override all other conditions."""
    ev = make_event(
        summary="Following: Meeting",
        transp="OPAQUE",
        status="TENTATIVE",
        ms_deleted="TRUE",
    )
    result = parser._map_transparency_to_status("OPAQUE", "TENTATIVE", ev)
    assert result == LiteEventStatus.FREE


def test_ms_busystatus_overrides_status_property(parser):
    """MS-busystatus should override standard STATUS property."""
    ev = make_event(status="TENTATIVE", ms_busystatus="FREE")
    result = parser._map_transparency_to_status("OPAQUE", "TENTATIVE", ev)
    assert result == LiteEventStatus.FREE


def test_tentative_with_following_uses_tentative(parser):
    """Both TENTATIVE status and Following meeting should result in TENTATIVE."""
    ev = make_event(summary="Following: Review", status="TENTATIVE")
    result = parser._map_transparency_to_status("OPAQUE", "TENTATIVE", ev)
    assert result == LiteEventStatus.TENTATIVE


# ===== Complex Combinations =====


def test_transparent_tentative_returns_tentative(parser):
    """Transparent + tentative should map to TENTATIVE."""
    ev = make_event(transp="TRANSPARENT", status="TENTATIVE")
    result = parser._map_transparency_to_status("TRANSPARENT", "TENTATIVE", ev)
    # Status=TENTATIVE should be checked before transparency
    assert result == LiteEventStatus.TENTATIVE


def test_confirmed_opaque_returns_busy(parser):
    """Confirmed + opaque should map to BUSY."""
    ev = make_event(transp="OPAQUE", status="CONFIRMED")
    result = parser._map_transparency_to_status("OPAQUE", "CONFIRMED", ev)
    assert result == LiteEventStatus.BUSY


def test_none_summary_no_crash(parser):
    """Missing summary should not crash."""
    ev = ICalEvent()
    ev.add("UID", "test")
    ev.add("DTSTART", datetime(2025, 1, 10, 9, 0, tzinfo=UTC))
    # No SUMMARY added
    result = parser._map_transparency_to_status("OPAQUE", None, ev)
    assert result == LiteEventStatus.BUSY
