"""Unit tests for health_tracker module."""

import time

from calendarbot_lite.health_tracker import HealthStatus, HealthTracker


class TestHealthTracker:
    """Tests for HealthTracker class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a fresh instance for each test
        self.tracker = HealthTracker()
        # Reset start time for consistent testing
        self.tracker._start_time = time.time()

    def test_initial_state(self):
        """Should have correct initial state."""
        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        assert status.status == "degraded"  # No refresh success yet
        assert status.uptime_seconds >= 0
        assert status.event_count == 0
        assert status.last_refresh_success_age_seconds is None

    def test_record_refresh_attempt(self):
        """Should record refresh attempts."""
        # Implementation stores timestamp, not counter
        self.tracker.record_refresh_attempt()

        assert self.tracker._last_refresh_attempt is not None

    def test_record_refresh_success(self):
        """Should record successful refresh with event count."""
        self.tracker.record_refresh_success(25)

        assert self.tracker._last_refresh_success is not None
        assert self.tracker.get_event_count() == 25

    def test_record_background_heartbeat(self):
        """Should record background task heartbeat."""
        self.tracker.record_background_heartbeat()

        assert self.tracker._background_task_heartbeat is not None

    def test_get_health_status_ok(self):
        """Should return 'ok' status when recently refreshed."""
        # Record a successful refresh
        self.tracker.record_refresh_success(10)

        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        assert status.status == "ok"
        assert status.event_count == 10
        assert status.last_refresh_success_age_seconds is not None
        assert status.last_refresh_success_age_seconds < 60  # Should be very recent

    def test_get_health_status_degraded_no_refresh(self):
        """Should return 'degraded' when never refreshed."""
        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        assert status.status == "degraded"
        assert status.last_refresh_success_age_seconds is None

    def test_get_health_status_degraded_old_refresh(self):
        """Should return 'degraded' when refresh is too old."""
        # Record a successful refresh
        self.tracker.record_refresh_success(10)

        # Mock the last refresh to be 20 minutes ago
        self.tracker._last_refresh_success = time.time() - (20 * 60)

        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        assert status.status == "degraded"
        assert status.last_refresh_success_age_seconds > 900  # More than 15 minutes

    def test_get_health_status_background_tasks(self):
        """Should include background task status."""
        # Record a heartbeat
        self.tracker.record_background_heartbeat()

        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        assert len(status.background_tasks) == 1
        task_info = status.background_tasks[0]
        assert task_info["name"] == "refresher_task"
        assert task_info["status"] == "running"
        assert task_info["last_heartbeat_age_s"] < 60

    def test_get_health_status_stale_background_task(self):
        """Should mark background task as stale when heartbeat is old."""
        # Record a heartbeat 15 minutes ago
        self.tracker.record_background_heartbeat()
        self.tracker._background_task_heartbeat = time.time() - (15 * 60)

        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        task_info = status.background_tasks[0]
        assert task_info["status"] == "stale"
        assert task_info["last_heartbeat_age_s"] > 600  # More than 10 minutes

    def test_get_health_status_uptime(self):
        """Should calculate uptime correctly."""
        # Set start time to 5 minutes ago
        self.tracker._start_time = time.time() - (5 * 60)

        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        # Should be approximately 5 minutes (300 seconds)
        assert 290 <= status.uptime_seconds <= 310

    def test_thread_safety_concurrent_updates(self):
        """Should handle concurrent updates safely."""
        import threading

        def update_tracker():
            for i in range(100):
                self.tracker.record_refresh_attempt()
                self.tracker.record_refresh_success(i + 1)
                self.tracker.record_background_heartbeat()

        threads = [threading.Thread(target=update_tracker) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have timestamps set (implementation doesn't count attempts)
        assert self.tracker._last_refresh_attempt is not None
        assert self.tracker._last_refresh_success is not None
        assert self.tracker._background_task_heartbeat is not None

    def test_health_status_dataclass_fields(self):
        """Should have all expected fields in HealthStatus."""
        self.tracker.record_refresh_success(15)
        self.tracker.record_background_heartbeat()

        current_time = time.time()
        current_iso = f"{int(current_time)}"

        status = self.tracker.get_health_status(current_iso)

        # Check all expected fields exist
        assert hasattr(status, "status")
        assert hasattr(status, "server_time_iso")
        assert hasattr(status, "uptime_seconds")
        assert hasattr(status, "pid")
        assert hasattr(status, "event_count")
        assert hasattr(status, "last_refresh_success_age_seconds")
        assert hasattr(status, "background_tasks")

    def test_singleton_behavior(self):
        """Should behave like a singleton within same process."""
        # Note: The HealthTracker is designed to be used as a single instance
        # but isn't enforced as a singleton pattern. This test just validates
        # that multiple instances don't interfere with each other.

        tracker1 = HealthTracker()
        tracker2 = HealthTracker()

        tracker1.record_refresh_success(10)
        tracker2.record_refresh_success(20)

        # Each instance maintains its own state
        assert tracker1.get_event_count() == 10
        assert tracker2.get_event_count() == 20
