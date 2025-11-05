"""Parser telemetry and circuit breaker for ICS calendar processing - CalendarBot Lite.

This module handles progress tracking, duplicate detection, and circuit breaker
logic to prevent infinite loops from corrupted/malformed ICS feeds.
Extracted from lite_parser.py to improve modularity and testability.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ParserTelemetry:
    """Tracks parsing progress, detects duplicates, and triggers circuit breaker.

    This class monitors ICS parsing to detect network corruption or malformed
    feeds that could cause infinite loops or excessive memory usage.
    """

    def __init__(
        self,
        source_url: Optional[str] = None,
        max_warnings: int = 50,
        duplicate_ratio_threshold: float = 10.0,
        progress_log_interval: int = 10,
    ):
        """Initialize parser telemetry.

        Args:
            source_url: Source URL for logging context
            max_warnings: Maximum warnings before circuit breaker triggers
            duplicate_ratio_threshold: Duplicate percentage threshold for circuit breaker
            progress_log_interval: Log progress every N events
        """
        self.source_url = source_url or "unknown"
        self.max_warnings = max_warnings
        self.duplicate_ratio_threshold = duplicate_ratio_threshold
        self.progress_log_interval = progress_log_interval

        # Tracking state
        self.total_items = 0
        self.event_items = 0
        self.duplicate_ids: set[str] = set()
        self.warnings = 0

    def record_item(self) -> None:
        """Record that an item was processed."""
        self.total_items += 1

    def record_event(self, event_uid: str, recurrence_id: Optional[str] = None) -> bool:
        """Record an event and check for duplicates.

        Args:
            event_uid: Event UID
            recurrence_id: Optional RECURRENCE-ID for modified instances

        Returns:
            True if this is a duplicate event, False otherwise
        """
        self.event_items += 1

        # Create unique key for this event
        unique_event_key = f"{event_uid}::{recurrence_id}" if recurrence_id else event_uid

        # Check for duplicate
        if unique_event_key in self.duplicate_ids:
            self._log_duplicate(event_uid)
            self.warnings += 1
            return True
        self.duplicate_ids.add(unique_event_key)
        self._log_progress_if_needed()
        return False

    def record_warning(self) -> None:
        """Record a warning."""
        self.warnings += 1

    def should_break(self) -> bool:
        """Check if circuit breaker should activate.

        Circuit breaker triggers when:
        - Warning count exceeds threshold AND
        - Duplicate ratio exceeds threshold

        This prevents infinite loops from corrupted/malformed feeds.

        Returns:
            True if circuit breaker should activate
        """
        if self.warnings <= self.max_warnings:
            return False

        duplicate_ratio = self.get_duplicate_ratio()
        if duplicate_ratio <= self.duplicate_ratio_threshold:
            return False

        # Circuit breaker activation
        self._log_circuit_breaker(duplicate_ratio)
        return True

    def get_duplicate_ratio(self) -> float:
        """Calculate duplicate ratio as percentage.

        Returns:
            Duplicate percentage (0-100)
        """
        if self.total_items == 0:
            return 0.0

        duplicate_count = self.total_items - len(self.duplicate_ids)
        return (duplicate_count / self.total_items) * 100

    def get_duplicate_count(self) -> int:
        """Get number of duplicate items detected.

        Returns:
            Duplicate count
        """
        return self.total_items - len(self.duplicate_ids)

    def get_unique_event_count(self) -> int:
        """Get number of unique events.

        Returns:
            Unique event count
        """
        return len(self.duplicate_ids)

    def get_content_size_estimate(self) -> int:
        """Estimate content size in bytes.

        Returns:
            Rough estimate of content size (total_items * 100 bytes)
        """
        return self.total_items * 100

    def _log_duplicate(self, event_uid: str) -> None:
        """Log duplicate event detection with context."""
        logger.warning(
            "Duplicate event UID detected during streaming parse - uid=%s, source_url=%s, "
            "content_size_est=%sbytes, total_items=%s, events_processed=%s, "
            "unique_uids=%s, duplicate_count=%s",
            event_uid,
            self.source_url,
            self.get_content_size_estimate(),
            self.total_items,
            self.event_items,
            len(self.duplicate_ids),
            self.get_duplicate_count(),
        )

    def _log_progress_if_needed(self) -> None:
        """Log progress every N events."""
        if self.event_items % self.progress_log_interval == 0:
            logger.debug(
                "Streaming parse progress - source_url=%s, events_processed=%d, "
                "unique_uids=%d, duplicate_ratio=%.2f%%",
                self.source_url,
                self.event_items,
                len(self.duplicate_ids),
                self.get_duplicate_ratio(),
            )

    def _log_circuit_breaker(self, duplicate_ratio: float) -> None:
        """Log circuit breaker activation with diagnostic data."""
        corruption_severity = "HIGH" if duplicate_ratio > 50 else "MEDIUM"

        logger.error(
            "CIRCUIT BREAKER ACTIVATED - Network corruption detected during streaming parse. "
            "source_url=%s, severity=%s, warning_count=%d, content_size_est=%dbytes, "
            "total_items=%d, unique_events=%d, processed_events=%d, duplicate_ratio=%.2f%%. "
            "TERMINATING PARSING TO PREVENT INFINITE LOOP.",
            self.source_url,
            corruption_severity,
            self.warnings,
            self.get_content_size_estimate(),
            self.total_items,
            len(self.duplicate_ids),
            self.event_items,
            duplicate_ratio,
        )

    def log_event_limit_reached(self, max_events: int, events_collected: int) -> None:
        """Log when event limit is reached.

        Args:
            max_events: Maximum events allowed
            events_collected: Number of events collected so far
        """
        duplicate_ratio = self.get_duplicate_ratio()

        logger.warning(
            "Event limit warning - source_url=%s, limit=%d, warning_count=%d, "
            "total_items=%d, events_processed=%d, unique_uids=%d, duplicate_ratio=%.2f%%",
            self.source_url,
            max_events,
            self.warnings,
            self.total_items,
            self.event_items,
            len(self.duplicate_ids),
            duplicate_ratio,
        )

    def log_completion(self, final_events: int, warning_count: int) -> None:
        """Log completion with comprehensive telemetry.

        Args:
            final_events: Number of events in final result
            warning_count: Total warnings encountered
        """
        duplicate_count = self.get_duplicate_count()
        duplicate_ratio = self.get_duplicate_ratio()
        content_size_estimate = self.get_content_size_estimate()

        logger.debug(
            "Streaming parse completed successfully - source_url=%s, content_size_est=%dbytes, "
            "total_items=%d, events_processed=%d, unique_uids=%d, duplicate_count=%d, "
            "duplicate_ratio=%.2f%%, final_events=%d, warnings=%d",
            self.source_url,
            content_size_estimate,
            self.total_items,
            self.event_items,
            len(self.duplicate_ids),
            duplicate_count,
            duplicate_ratio,
            final_events,
            warning_count,
        )

    def get_circuit_breaker_error_message(self) -> str:
        """Get error message for circuit breaker activation.

        Returns:
            Error message describing circuit breaker trigger
        """
        return (
            f"Circuit breaker: Network corruption detected "
            f"({self.warnings} warnings, {self.get_duplicate_ratio():.1f}% duplicates)"
        )
