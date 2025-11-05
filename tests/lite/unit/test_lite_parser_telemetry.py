"""Unit tests for lite_parser_telemetry module."""

import pytest

from calendarbot_lite.calendar.lite_parser_telemetry import ParserTelemetry

pytestmark = pytest.mark.unit


class TestParserTelemetry:
    """Tests for ParserTelemetry class."""

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        telemetry = ParserTelemetry()

        assert telemetry.source_url == "unknown"
        assert telemetry.max_warnings == 50
        assert telemetry.duplicate_ratio_threshold == 10.0
        assert telemetry.progress_log_interval == 10
        assert telemetry.total_items == 0
        assert telemetry.event_items == 0
        assert len(telemetry.duplicate_ids) == 0
        assert telemetry.warnings == 0

    def test_initialization_custom_values(self):
        """Test initialization with custom values."""
        telemetry = ParserTelemetry(
            source_url="https://example.com/calendar.ics",
            max_warnings=100,
            duplicate_ratio_threshold=20.0,
            progress_log_interval=5,
        )

        assert telemetry.source_url == "https://example.com/calendar.ics"
        assert telemetry.max_warnings == 100
        assert telemetry.duplicate_ratio_threshold == 20.0
        assert telemetry.progress_log_interval == 5

    def test_record_item(self):
        """Test recording items increments counter."""
        telemetry = ParserTelemetry()

        telemetry.record_item()
        assert telemetry.total_items == 1

        telemetry.record_item()
        assert telemetry.total_items == 2

    def test_record_event_unique(self):
        """Test recording unique events."""
        telemetry = ParserTelemetry()

        is_duplicate = telemetry.record_event("event1")
        assert is_duplicate is False
        assert telemetry.event_items == 1
        assert "event1" in telemetry.duplicate_ids

        is_duplicate = telemetry.record_event("event2")
        assert is_duplicate is False
        assert telemetry.event_items == 2
        assert len(telemetry.duplicate_ids) == 2

    def test_record_event_duplicate(self):
        """Test recording duplicate events."""
        telemetry = ParserTelemetry()

        # First occurrence
        telemetry.record_event("event1")
        assert telemetry.warnings == 0

        # Duplicate
        is_duplicate = telemetry.record_event("event1")
        assert is_duplicate is True
        assert telemetry.event_items == 2
        assert telemetry.warnings == 1
        assert len(telemetry.duplicate_ids) == 1  # Still only one unique ID

    def test_record_event_with_recurrence_id(self):
        """Test recording events with RECURRENCE-ID."""
        telemetry = ParserTelemetry()

        # Master event
        telemetry.record_event("event1")
        assert len(telemetry.duplicate_ids) == 1

        # Modified instance with RECURRENCE-ID (different from master)
        is_duplicate = telemetry.record_event("event1", "20251028T143000")
        assert is_duplicate is False
        assert len(telemetry.duplicate_ids) == 2  # Master + modified instance

        # Same modified instance again (duplicate)
        is_duplicate = telemetry.record_event("event1", "20251028T143000")
        assert is_duplicate is True
        assert len(telemetry.duplicate_ids) == 2  # Still 2 unique

    def test_record_warning(self):
        """Test recording warnings."""
        telemetry = ParserTelemetry()

        telemetry.record_warning()
        assert telemetry.warnings == 1

        telemetry.record_warning()
        assert telemetry.warnings == 2

    def test_get_duplicate_ratio_zero_items(self):
        """Test duplicate ratio with zero items."""
        telemetry = ParserTelemetry()
        assert telemetry.get_duplicate_ratio() == 0.0

    def test_get_duplicate_ratio_no_duplicates(self):
        """Test duplicate ratio with no duplicates."""
        telemetry = ParserTelemetry()

        telemetry.record_item()
        telemetry.record_event("event1")

        assert telemetry.get_duplicate_ratio() == 0.0

    def test_get_duplicate_ratio_with_duplicates(self):
        """Test duplicate ratio with duplicates."""
        telemetry = ParserTelemetry()

        # 3 total items, 1 unique event (2 duplicates)
        telemetry.record_item()
        telemetry.record_event("event1")

        telemetry.record_item()
        telemetry.record_event("event1")  # Duplicate

        telemetry.record_item()
        telemetry.record_event("event1")  # Another duplicate

        # Duplicate ratio = (3 - 1) / 3 * 100 = 66.67%
        assert telemetry.get_duplicate_ratio() == pytest.approx(66.67, rel=0.01)

    def test_get_duplicate_count(self):
        """Test getting duplicate count."""
        telemetry = ParserTelemetry()

        telemetry.record_item()
        telemetry.record_event("event1")

        telemetry.record_item()
        telemetry.record_event("event1")  # Duplicate

        assert telemetry.get_duplicate_count() == 1

    def test_get_unique_event_count(self):
        """Test getting unique event count."""
        telemetry = ParserTelemetry()

        telemetry.record_event("event1")
        telemetry.record_event("event2")
        telemetry.record_event("event1")  # Duplicate

        assert telemetry.get_unique_event_count() == 2

    def test_get_content_size_estimate(self):
        """Test content size estimation."""
        telemetry = ParserTelemetry()

        telemetry.record_item()
        telemetry.record_item()
        telemetry.record_item()

        # 3 items * 100 bytes = 300 bytes
        assert telemetry.get_content_size_estimate() == 300

    def test_should_break_no_warnings(self):
        """Test circuit breaker doesn't trigger with no warnings."""
        telemetry = ParserTelemetry(max_warnings=50)

        assert telemetry.should_break() is False

    def test_should_break_warnings_but_low_duplicate_ratio(self):
        """Test circuit breaker doesn't trigger with warnings but low duplicate ratio."""
        telemetry = ParserTelemetry(max_warnings=50, duplicate_ratio_threshold=10.0)

        # Generate many warnings but low duplicate ratio
        for i in range(60):
            telemetry.record_item()
            telemetry.record_warning()
            telemetry.record_event(f"event{i}")  # All unique

        assert telemetry.warnings == 60
        assert telemetry.get_duplicate_ratio() < 10.0
        assert telemetry.should_break() is False

    def test_should_break_high_warnings_and_duplicates(self):
        """Test circuit breaker triggers with high warnings and duplicate ratio."""
        telemetry = ParserTelemetry(max_warnings=50, duplicate_ratio_threshold=10.0)

        # Generate items with high duplicate ratio
        telemetry.record_item()
        telemetry.record_event("event1")

        # Many duplicates
        for _ in range(100):
            telemetry.record_item()
            telemetry.record_warning()
            telemetry.record_event("event1")  # All duplicates

        assert telemetry.warnings > 50
        assert telemetry.get_duplicate_ratio() > 10.0
        assert telemetry.should_break() is True

    def test_circuit_breaker_exactly_at_threshold(self):
        """Test circuit breaker at exact threshold."""
        telemetry = ParserTelemetry(max_warnings=50, duplicate_ratio_threshold=10.0)

        # Generate exactly 50 warnings (not exceeding)
        for _ in range(50):
            telemetry.record_warning()

        # High duplicate ratio but warnings not exceeded yet
        assert telemetry.warnings == 50
        assert telemetry.should_break() is False  # Must exceed threshold

        # One more warning pushes over threshold
        telemetry.record_warning()

        # Need high duplicate ratio too
        telemetry.record_item()
        telemetry.record_event("event1")
        for _ in range(20):
            telemetry.record_item()
            telemetry.record_event("event1")  # Duplicates will add warnings

        assert telemetry.get_duplicate_ratio() > 10.0
        assert telemetry.should_break() is True

    def test_get_circuit_breaker_error_message(self):
        """Test circuit breaker error message formatting."""
        telemetry = ParserTelemetry(source_url="https://example.com/cal.ics")

        # Set up some warnings  manually
        for _ in range(55):
            telemetry.record_warning()

        # Add some items and duplicates for ratio
        telemetry.record_item()
        telemetry.record_event("event1")
        for _ in range(10):
            telemetry.record_item()
            telemetry.record_event("event1")  # Duplicates

        message = telemetry.get_circuit_breaker_error_message()

        assert "Circuit breaker" in message
        assert "warnings" in message
        assert "duplicates" in message
        assert str(telemetry.warnings) in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
