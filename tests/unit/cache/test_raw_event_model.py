"""Unit tests for RawEvent model functionality."""

import hashlib
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from calendarbot.cache.models import RawEvent


class TestRawEventModel:
    """Test cases for RawEvent model creation and validation."""

    def test_create_from_ics_when_valid_content_then_creates_model(self) -> None:
        """Test that create_from_ics creates a valid RawEvent with proper fields."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-123
DTSTART:20250813T140000Z
DTEND:20250813T150000Z
SUMMARY:Test Meeting
END:VEVENT
END:VCALENDAR"""

        graph_id = "graph_123"
        source_url = "https://example.com/calendar.ics"

        with patch("calendarbot.cache.models.datetime") as mock_datetime:
            mock_now = datetime(2025, 8, 13, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            raw_event = RawEvent.create_from_ics(
                graph_id=graph_id,
                subject="Test Meeting",
                start_datetime="2025-08-13T14:00:00Z",
                end_datetime="2025-08-13T15:00:00Z",
                start_timezone="UTC",
                end_timezone="UTC",
                ics_content=ics_content,
                source_url=source_url,
            )

        # Verify basic fields
        assert raw_event.id.startswith(f"raw_{graph_id}_")
        assert raw_event.graph_id == graph_id
        assert raw_event.source_url == source_url
        assert raw_event.raw_ics_content == ics_content
        assert raw_event.subject == "Test Meeting"

        # Verify computed fields
        expected_hash = hashlib.sha256(ics_content.encode("utf-8")).hexdigest()
        assert raw_event.content_hash == expected_hash
        assert raw_event.content_size_bytes == len(ics_content.encode("utf-8"))
        assert raw_event.cached_at == mock_now.isoformat()

    def test_create_from_ics_when_no_source_url_then_creates_model_with_none(self) -> None:
        """Test that create_from_ics works without source_url."""
        ics_content = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        graph_id = "graph_456"

        raw_event = RawEvent.create_from_ics(
            graph_id=graph_id,
            subject="Test Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=ics_content,
        )

        assert raw_event.source_url is None
        assert raw_event.graph_id == graph_id
        assert raw_event.raw_ics_content == ics_content
        assert raw_event.subject == "Test Event"

    def test_create_from_ics_when_empty_content_then_creates_model(self) -> None:
        """Test that create_from_ics handles empty content."""
        ics_content = ""
        graph_id = "graph_empty"

        raw_event = RawEvent.create_from_ics(
            graph_id=graph_id,
            subject="Empty Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=ics_content,
        )

        assert raw_event.raw_ics_content == ""
        assert raw_event.content_size_bytes == 0
        assert raw_event.content_hash == hashlib.sha256(b"").hexdigest()
        assert raw_event.subject == "Empty Event"

    @pytest.mark.parametrize(
        ("content", "expected_size"),
        [
            ("Hello", 5),
            ("Hello 世界", 12),  # UTF-8 encoding test
            ("", 0),
            ("🎉🎊🎈", 12),  # Emoji test
        ],
    )
    def test_create_from_ics_when_various_content_then_calculates_correct_size(
        self, content: str, expected_size: int
    ) -> None:
        """Test that content size calculation handles various character encodings."""
        raw_event = RawEvent.create_from_ics(
            graph_id="test",
            subject="Test Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=content,
        )

        assert raw_event.content_size_bytes == expected_size

    def test_create_from_ics_when_large_content_then_handles_correctly(self) -> None:
        """Test that create_from_ics handles large content."""
        # Create large content (1MB)
        large_content = "X" * (1024 * 1024)
        graph_id = "large_event"

        raw_event = RawEvent.create_from_ics(
            graph_id=graph_id,
            subject="Large Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=large_content,
        )

        assert raw_event.content_size_bytes == 1024 * 1024
        assert len(raw_event.content_hash) == 64  # SHA-256 hex length
        assert raw_event.raw_ics_content == large_content

    def test_content_hash_when_same_content_then_produces_same_hash(self) -> None:
        """Test that identical content produces identical hashes."""
        content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"

        event1 = RawEvent.create_from_ics(
            graph_id="id1",
            subject="Event 1",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=content,
        )
        event2 = RawEvent.create_from_ics(
            graph_id="id2",
            subject="Event 2",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=content,
        )

        assert event1.content_hash == event2.content_hash

    def test_content_hash_when_different_content_then_produces_different_hash(self) -> None:
        """Test that different content produces different hashes."""
        content1 = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        content2 = "BEGIN:VCALENDAR\nVERSION:2.1\nEND:VCALENDAR"

        event1 = RawEvent.create_from_ics(
            graph_id="id1",
            subject="Event 1",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=content1,
        )
        event2 = RawEvent.create_from_ics(
            graph_id="id2",
            subject="Event 2",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            ics_content=content2,
        )

        assert event1.content_hash != event2.content_hash

    def test_cached_dt_property_when_iso_format_then_returns_datetime(self) -> None:
        """Test that cached_dt property correctly parses ISO format datetime."""
        # Create a raw event with specific ISO timestamp
        raw_event = RawEvent(
            id="test",
            graph_id="graph_test",
            subject="Test Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            raw_ics_content="content",
            content_hash="hash",
            content_size_bytes=7,
            cached_at="2025-08-13T15:30:45",
        )

        expected_dt = datetime(2025, 8, 13, 15, 30, 45)
        assert raw_event.cached_dt == expected_dt

    def test_cached_dt_property_when_z_suffix_then_handles_correctly(self) -> None:
        """Test that cached_dt property handles Z suffix in timestamp."""
        # Create a raw event with Z suffix timestamp
        raw_event = RawEvent(
            id="test",
            graph_id="graph_test",
            subject="Test Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            raw_ics_content="content",
            content_hash="hash",
            content_size_bytes=7,
            cached_at="2025-08-13T15:30:45Z",
        )

        # Z suffix creates UTC timezone-aware datetime
        expected_dt = datetime(2025, 8, 13, 15, 30, 45, tzinfo=timezone.utc)
        assert raw_event.cached_dt == expected_dt

    def test_model_validation_when_required_fields_missing_then_raises_error(self) -> None:
        """Test that model validation fails when required fields are missing."""
        with pytest.raises(ValueError, match="validation error"):
            RawEvent()  # type: ignore

    def test_model_validation_when_all_fields_provided_then_creates_successfully(self) -> None:
        """Test that model validation passes with all required fields."""
        raw_event = RawEvent(
            id="test_id",
            graph_id="graph_id",
            subject="Test Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            raw_ics_content="content",
            content_hash="abcd1234",
            content_size_bytes=7,
            cached_at="2025-08-13T12:00:00",
        )

        assert raw_event.id == "test_id"
        assert raw_event.graph_id == "graph_id"
        assert raw_event.subject == "Test Event"
        assert raw_event.raw_ics_content == "content"
        assert raw_event.content_hash == "abcd1234"
        assert raw_event.content_size_bytes == 7
        assert raw_event.source_url is None

    def test_model_serialization_when_to_dict_then_includes_all_fields(self) -> None:
        """Test that model can be serialized to dictionary."""
        raw_event = RawEvent(
            id="test_id",
            graph_id="graph_id",
            subject="Test Event",
            start_datetime="2025-08-13T14:00:00Z",
            end_datetime="2025-08-13T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            source_url="https://example.com",
            raw_ics_content="content",
            content_hash="abcd1234",
            content_size_bytes=7,
            cached_at="2025-08-13T12:00:00",
        )

        data = raw_event.model_dump()

        assert data["id"] == "test_id"
        assert data["graph_id"] == "graph_id"
        assert data["subject"] == "Test Event"
        assert data["source_url"] == "https://example.com"
        assert data["raw_ics_content"] == "content"
        assert data["content_hash"] == "abcd1234"
        assert data["content_size_bytes"] == 7
        assert data["cached_at"] == "2025-08-13T12:00:00"
