"""Tests for LiteCalendarEvent and LiteLocation input length validation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from calendarbot_lite.config_manager import (
    MAX_EVENT_DESCRIPTION_LENGTH,
    MAX_EVENT_LOCATION_LENGTH,
    MAX_EVENT_SUBJECT_LENGTH,
)
from calendarbot_lite.lite_models import (
    LiteCalendarEvent,
    LiteDateTimeInfo,
    LiteEventStatus,
    LiteLocation,
)

pytestmark = pytest.mark.unit


class TestLiteLocationValidation:
    """Test location display_name validation."""

    def test_valid_location_display_name(self):
        """Test valid location display name."""
        location = LiteLocation(display_name="Conference Room A")
        assert location.display_name == "Conference Room A"

    def test_location_at_max_length(self):
        """Test location display name at exact maximum length."""
        display_name = "A" * MAX_EVENT_LOCATION_LENGTH
        location = LiteLocation(display_name=display_name)
        assert location.display_name == display_name
        assert len(location.display_name) == MAX_EVENT_LOCATION_LENGTH

    def test_location_exceeds_max_length(self):
        """Test location display name exceeding maximum length raises ValidationError."""
        display_name = "A" * (MAX_EVENT_LOCATION_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            LiteLocation(display_name=display_name)
        error_msg = str(exc_info.value).lower()
        assert "display_name" in error_msg
        assert "max_length" in error_msg or "maximum" in error_msg or str(MAX_EVENT_LOCATION_LENGTH) in error_msg

    def test_location_strips_whitespace(self):
        """Test location display name strips leading/trailing whitespace."""
        location = LiteLocation(display_name="  Conference Room B  ")
        assert location.display_name == "Conference Room B"

    def test_location_empty_string_after_strip(self):
        """Test location with whitespace-only display name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiteLocation(display_name="   ")
        assert "display_name" in str(exc_info.value).lower()
        assert "empty" in str(exc_info.value).lower()

    def test_location_empty_string(self):
        """Test location with empty display name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiteLocation(display_name="")
        assert "display_name" in str(exc_info.value).lower()

    def test_location_none_display_name(self):
        """Test location with None display name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiteLocation(display_name=None)  # type: ignore[arg-type]
        assert "display_name" in str(exc_info.value).lower()

    def test_location_unicode_characters(self):
        """Test location display name with unicode characters."""
        display_name = "会議室 東京"  # Japanese: "Conference Room Tokyo"
        location = LiteLocation(display_name=display_name)
        assert location.display_name == display_name

    def test_location_emoji_characters(self):
        """Test location display name with emoji (multi-byte characters)."""
        display_name = "Room 🏢 Building 🌆"
        location = LiteLocation(display_name=display_name)
        assert location.display_name == display_name

    def test_location_max_length_with_unicode(self):
        """Test location at max length with unicode characters."""
        # Unicode characters may be multiple bytes but count as single characters
        # for max_length validation
        display_name = "東" * MAX_EVENT_LOCATION_LENGTH  # Japanese character
        location = LiteLocation(display_name=display_name)
        assert len(location.display_name) == MAX_EVENT_LOCATION_LENGTH


class TestLiteCalendarEventSubjectValidation:
    """Test event subject validation."""

    def _make_event(self, subject: str, **kwargs) -> LiteCalendarEvent:
        """Helper to create a minimal event with a subject."""
        now = datetime.now(timezone.utc)
        return LiteCalendarEvent(
            id="test-event-1",
            subject=subject,
            start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            end=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            **kwargs,
        )

    def test_valid_subject(self):
        """Test valid event subject."""
        event = self._make_event("Team Standup")
        assert event.subject == "Team Standup"

    def test_subject_at_max_length(self):
        """Test event subject at exact maximum length."""
        subject = "A" * MAX_EVENT_SUBJECT_LENGTH
        event = self._make_event(subject)
        assert event.subject == subject
        assert len(event.subject) == MAX_EVENT_SUBJECT_LENGTH

    def test_subject_exceeds_max_length(self):
        """Test event subject exceeding maximum length raises ValidationError."""
        subject = "A" * (MAX_EVENT_SUBJECT_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            self._make_event(subject)
        error_msg = str(exc_info.value).lower()
        assert "subject" in error_msg
        assert "max_length" in error_msg or "maximum" in error_msg or str(MAX_EVENT_SUBJECT_LENGTH) in error_msg

    def test_subject_strips_whitespace(self):
        """Test event subject strips leading/trailing whitespace."""
        event = self._make_event("  Project Planning  ")
        assert event.subject == "Project Planning"

    def test_subject_empty_after_strip(self):
        """Test event with whitespace-only subject raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self._make_event("   ")
        error_msg = str(exc_info.value).lower()
        assert "subject" in error_msg
        assert "empty" in error_msg

    def test_subject_empty_string(self):
        """Test event with empty subject raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self._make_event("")
        assert "subject" in str(exc_info.value).lower()

    def test_subject_min_length_satisfied(self):
        """Test event subject minimum length (1 character) is satisfied."""
        event = self._make_event("A")
        assert event.subject == "A"

    def test_subject_unicode_characters(self):
        """Test event subject with unicode characters."""
        subject = "チームミーティング"  # Japanese: "Team Meeting"
        event = self._make_event(subject)
        assert event.subject == subject

    def test_subject_emoji_characters(self):
        """Test event subject with emoji (multi-byte characters)."""
        subject = "🎉 Celebration Party 🎊"
        event = self._make_event(subject)
        assert event.subject == subject

    def test_subject_max_length_with_unicode(self):
        """Test event subject at max length with unicode characters."""
        subject = "会" * MAX_EVENT_SUBJECT_LENGTH  # Japanese character
        event = self._make_event(subject)
        assert len(event.subject) == MAX_EVENT_SUBJECT_LENGTH


class TestLiteCalendarEventBodyPreviewValidation:
    """Test event body_preview validation."""

    def _make_event(self, body_preview: str | None, **kwargs) -> LiteCalendarEvent:
        """Helper to create a minimal event with a body preview."""
        now = datetime.now(timezone.utc)
        return LiteCalendarEvent(
            id="test-event-1",
            subject="Test Event",
            body_preview=body_preview,
            start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            end=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            **kwargs,
        )

    def test_valid_body_preview(self):
        """Test valid event body preview."""
        event = self._make_event("Discussion topics: Q4 planning, budget review")
        assert event.body_preview == "Discussion topics: Q4 planning, budget review"

    def test_body_preview_none(self):
        """Test event with None body_preview is valid."""
        event = self._make_event(None)
        assert event.body_preview is None

    def test_body_preview_at_max_length(self):
        """Test event body_preview at exact maximum length."""
        body_preview = "A" * MAX_EVENT_DESCRIPTION_LENGTH
        event = self._make_event(body_preview)
        assert event.body_preview == body_preview
        assert event.body_preview is not None
        assert len(event.body_preview) == MAX_EVENT_DESCRIPTION_LENGTH

    def test_body_preview_exceeds_max_length(self):
        """Test event body_preview exceeding maximum length raises ValidationError."""
        body_preview = "A" * (MAX_EVENT_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            self._make_event(body_preview)
        error_msg = str(exc_info.value).lower()
        assert "body_preview" in error_msg
        assert "max_length" in error_msg or "maximum" in error_msg or str(MAX_EVENT_DESCRIPTION_LENGTH) in error_msg

    def test_body_preview_strips_whitespace(self):
        """Test event body_preview strips leading/trailing whitespace."""
        event = self._make_event("  Meeting notes here  ")
        assert event.body_preview == "Meeting notes here"

    def test_body_preview_empty_after_strip_becomes_none(self):
        """Test event with whitespace-only body_preview becomes None."""
        event = self._make_event("   ")
        assert event.body_preview is None

    def test_body_preview_empty_string_becomes_none(self):
        """Test event with empty body_preview becomes None."""
        event = self._make_event("")
        assert event.body_preview is None

    def test_body_preview_unicode_characters(self):
        """Test event body_preview with unicode characters."""
        body_preview = "議題：第四四半期の計画"  # Japanese: "Topics: Q4 planning"
        event = self._make_event(body_preview)
        assert event.body_preview == body_preview

    def test_body_preview_emoji_characters(self):
        """Test event body_preview with emoji (multi-byte characters)."""
        body_preview = "📋 Agenda: Review project status 📊"
        event = self._make_event(body_preview)
        assert event.body_preview == body_preview

    def test_body_preview_max_length_with_unicode(self):
        """Test event body_preview at max length with unicode characters."""
        body_preview = "議" * MAX_EVENT_DESCRIPTION_LENGTH  # Japanese character
        event = self._make_event(body_preview)
        assert event.body_preview is not None
        assert len(event.body_preview) == MAX_EVENT_DESCRIPTION_LENGTH


class TestLiteCalendarEventCompleteValidation:
    """Test complete event validation with all fields."""

    def test_event_with_location_and_body_at_limits(self):
        """Test event with subject, location, and body all at maximum length."""
        now = datetime.now(timezone.utc)
        subject = "S" * MAX_EVENT_SUBJECT_LENGTH
        body_preview = "B" * MAX_EVENT_DESCRIPTION_LENGTH
        location = LiteLocation(display_name="L" * MAX_EVENT_LOCATION_LENGTH)

        event = LiteCalendarEvent(
            id="test-event-1",
            subject=subject,
            body_preview=body_preview,
            location=location,
            start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            end=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
        )

        assert len(event.subject) == MAX_EVENT_SUBJECT_LENGTH
        assert event.body_preview is not None
        assert len(event.body_preview) == MAX_EVENT_DESCRIPTION_LENGTH
        assert event.location is not None
        assert len(event.location.display_name) == MAX_EVENT_LOCATION_LENGTH

    def test_event_with_oversized_subject_fails(self):
        """Test event with oversized subject fails validation."""
        now = datetime.now(timezone.utc)
        subject = "S" * (MAX_EVENT_SUBJECT_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            LiteCalendarEvent(
                id="test-event-1",
                subject=subject,
                start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
                end=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            )
        assert "subject" in str(exc_info.value).lower()

    def test_event_with_oversized_location_fails(self):
        """Test event with oversized location fails validation."""
        now = datetime.now(timezone.utc)
        location_name = "L" * (MAX_EVENT_LOCATION_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            LiteCalendarEvent(
                id="test-event-1",
                subject="Valid Subject",
                location=LiteLocation(display_name=location_name),
                start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
                end=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            )
        # Error should mention display_name (from LiteLocation)
        error_msg = str(exc_info.value).lower()
        assert "display_name" in error_msg or "location" in error_msg

    def test_event_with_oversized_body_preview_fails(self):
        """Test event with oversized body_preview fails validation."""
        now = datetime.now(timezone.utc)
        body_preview = "B" * (MAX_EVENT_DESCRIPTION_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            LiteCalendarEvent(
                id="test-event-1",
                subject="Valid Subject",
                body_preview=body_preview,
                start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
                end=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
            )
        assert "body_preview" in str(exc_info.value).lower()
