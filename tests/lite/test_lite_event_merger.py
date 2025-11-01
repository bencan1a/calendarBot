"""Unit tests for lite_event_merger module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from calendarbot_lite.lite_event_merger import LiteEventMerger
from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo


class TestLiteEventMerger:
    """Tests for LiteEventMerger class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.merger = LiteEventMerger()

    def create_test_event(
        self,
        uid: str,
        subject: str,
        start: datetime,
        end: datetime,
        is_recurring: bool = False,
        recurrence_id: str = None,
    ) -> LiteCalendarEvent:
        """Create a test calendar event."""
        return LiteCalendarEvent(
            id=uid,
            subject=subject,
            start=LiteDateTimeInfo(date_time=start, time_zone="UTC"),
            end=LiteDateTimeInfo(date_time=end, time_zone="UTC"),
            is_recurring=is_recurring,
            recurrence_id=recurrence_id,
        )

    def test_extract_master_uid_with_double_colon(self):
        """Test extracting master UID with :: delimiter."""
        result = self.merger._extract_master_uid("event123::instance1")
        assert result == "event123"

    def test_extract_master_uid_with_underscore(self):
        """Test extracting master UID with _ delimiter."""
        result = self.merger._extract_master_uid("event123_instance1")
        assert result == "event123"

    def test_extract_master_uid_no_delimiter(self):
        """Test extracting master UID with no delimiter."""
        result = self.merger._extract_master_uid("event123")
        assert result == "event123"

    def test_parse_recurrence_id_with_tzid(self):
        """Test parsing RECURRENCE-ID with TZID."""
        result = self.merger._parse_recurrence_id_time(
            "TZID=Pacific Standard Time:20251028T143000"
        )
        assert result == "20251028T143000"

    def test_parse_recurrence_id_with_z_suffix(self):
        """Test parsing RECURRENCE-ID with Z suffix."""
        result = self.merger._parse_recurrence_id_time("20251028T143000Z")
        assert result == "20251028T143000"

    def test_parse_recurrence_id_simple(self):
        """Test parsing simple RECURRENCE-ID."""
        result = self.merger._parse_recurrence_id_time("20251028T143000")
        assert result == "20251028T143000"

    def test_parse_recurrence_id_invalid(self):
        """Test parsing invalid RECURRENCE-ID returns None."""
        result = self.merger._parse_recurrence_id_time("invalid")
        assert result is None

    def test_collect_recurrence_overrides_empty(self):
        """Test collecting overrides from empty list."""
        result = self.merger._collect_recurrence_overrides([])
        assert len(result) == 0

    def test_collect_recurrence_overrides_no_recurrence_id(self):
        """Test collecting overrides from events without RECURRENCE-ID."""
        event = self.create_test_event(
            "event1",
            "Test Event",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )

        result = self.merger._collect_recurrence_overrides([event])
        assert len(result) == 0

    def test_collect_recurrence_overrides_with_recurrence_id(self):
        """Test collecting overrides from events with RECURRENCE-ID."""
        event = self.create_test_event(
            "event1::moved",
            "Moved Meeting",
            datetime(2025, 10, 28, 15, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 16, 0, tzinfo=timezone.utc),
            recurrence_id="20251028T143000",
        )

        result = self.merger._collect_recurrence_overrides([event])
        assert len(result) == 1
        assert ("event1", "20251028T143000") in result
        assert result[("event1", "20251028T143000")] == event

    def test_filter_overridden_occurrences_no_overrides(self):
        """Test filtering with no overrides."""
        event = self.create_test_event(
            "event1",
            "Test Event",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        event.rrule_master_uid = "event1"  # type: ignore

        filtered, count = self.merger._filter_overridden_occurrences([event], {})
        assert len(filtered) == 1
        assert count == 0

    def test_filter_overridden_occurrences_with_override(self):
        """Test filtering suppresses overridden occurrence."""
        # Create expanded occurrence
        expanded_event = self.create_test_event(
            "event1::occurrence1",
            "Test Event",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        expanded_event.rrule_master_uid = "event1"  # type: ignore

        # Create override
        override_event = self.create_test_event(
            "event1::moved",
            "Test Event (Moved)",
            datetime(2025, 10, 28, 15, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 16, 0, tzinfo=timezone.utc),
            recurrence_id="20251028T143000",
        )

        overrides = {("event1", "20251028T143000"): override_event}

        filtered, count = self.merger._filter_overridden_occurrences(
            [expanded_event], overrides
        )
        assert len(filtered) == 0  # Occurrence was suppressed
        assert count == 1

    def test_deduplicate_events_no_duplicates(self):
        """Test deduplication with no duplicates."""
        event1 = self.create_test_event(
            "event1",
            "Event 1",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        event2 = self.create_test_event(
            "event2",
            "Event 2",
            datetime(2025, 10, 28, 16, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 17, 30, tzinfo=timezone.utc),
        )

        result = self.merger.deduplicate_events([event1, event2])
        assert len(result) == 2

    def test_deduplicate_events_with_duplicates(self):
        """Test deduplication removes duplicates."""
        event1 = self.create_test_event(
            "event1",
            "Test Event",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        event2 = self.create_test_event(
            "event1",  # Same UID
            "Test Event",  # Same subject
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),  # Same start
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),  # Same end
        )

        result = self.merger.deduplicate_events([event1, event2])
        assert len(result) == 1

    def test_deduplicate_events_different_uids(self):
        """Test deduplication keeps events with different UIDs."""
        event1 = self.create_test_event(
            "event1",
            "Test Event",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        event2 = self.create_test_event(
            "event2",  # Different UID
            "Test Event",  # Same subject
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),  # Same start
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),  # Same end
        )

        result = self.merger.deduplicate_events([event1, event2])
        assert len(result) == 2  # Both kept

    def test_merge_expanded_events_no_recurring(self):
        """Test merging with no recurring events."""
        original1 = self.create_test_event(
            "event1",
            "Event 1",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        original2 = self.create_test_event(
            "event2",
            "Event 2",
            datetime(2025, 10, 29, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 29, 15, 30, tzinfo=timezone.utc),
        )

        result = self.merger.merge_expanded_events([original1, original2], [])
        assert len(result) == 2

    def test_merge_expanded_events_with_recurring_master(self):
        """Test merging filters out expanded recurring master."""
        # Recurring master
        recurring_master = self.create_test_event(
            "recurring1",
            "Weekly Meeting",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
            is_recurring=True,
        )

        # Expanded occurrences
        occurrence1 = self.create_test_event(
            "recurring1::occ1",
            "Weekly Meeting",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
        )
        occurrence1.rrule_master_uid = "recurring1"  # type: ignore

        occurrence2 = self.create_test_event(
            "recurring1::occ2",
            "Weekly Meeting",
            datetime(2025, 11, 4, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 11, 4, 15, 30, tzinfo=timezone.utc),
        )
        occurrence2.rrule_master_uid = "recurring1"  # type: ignore

        result = self.merger.merge_expanded_events(
            [recurring_master], [occurrence1, occurrence2]
        )

        # Should have 2 expanded occurrences, master should be filtered out
        assert len(result) == 2
        assert all(
            event.id.startswith("recurring1::") for event in result
        )  # Only occurrences

    def test_merge_expanded_events_keeps_non_expanded_master(self):
        """Test merging keeps recurring master that wasn't expanded."""
        # Recurring master with unsupported RRULE
        recurring_master = self.create_test_event(
            "recurring1",
            "Complex Meeting",
            datetime(2025, 10, 28, 14, 30, tzinfo=timezone.utc),
            datetime(2025, 10, 28, 15, 30, tzinfo=timezone.utc),
            is_recurring=True,
        )

        # No expanded occurrences (e.g., unsupported RRULE)
        result = self.merger.merge_expanded_events([recurring_master], [])

        # Should keep the recurring master
        assert len(result) == 1
        assert result[0].id == "recurring1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
