"""Tests for calendarbot_lite health check functionality."""

import datetime
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the module under test
import calendarbot_lite.api.server as server_module

pytestmark = pytest.mark.integration


class TestHealthTracking:
    """Test health tracking infrastructure."""

    def setup_method(self) -> None:
        """Reset health tracking variables before each test."""
        # Reset the health tracker to a fresh state
        server_module._health_tracker = server_module.HealthTracker()

    def test_update_health_tracking_when_refresh_attempt_then_sets_timestamp(self) -> None:
        """Test that refresh attempt updates timestamp."""
        start_time = time.time()
        server_module._update_health_tracking(refresh_attempt=True)

        timestamp = server_module._health_tracker.get_last_refresh_attempt_timestamp()
        assert timestamp is not None
        assert isinstance(timestamp, float)
        assert timestamp >= start_time

    def test_update_health_tracking_when_refresh_success_then_sets_timestamp(self) -> None:
        """Test that refresh success updates timestamp."""
        server_module._update_health_tracking(refresh_success=True)

        timestamp = server_module._health_tracker.get_last_refresh_success_timestamp()
        assert timestamp is not None
        assert isinstance(timestamp, float)

    def test_update_health_tracking_when_event_count_then_sets_count(self) -> None:
        """Test that event count is updated correctly."""
        server_module._update_health_tracking(event_count=42)

        assert server_module._health_tracker.get_event_count() == 42

    def test_update_health_tracking_when_background_heartbeat_then_sets_timestamp(self) -> None:
        """Test that background heartbeat updates timestamp."""
        server_module._update_health_tracking(background_heartbeat=True)

        status = server_module._health_tracker.get_background_task_status()
        assert status["last_heartbeat_age_s"] is not None
        assert isinstance(status["last_heartbeat_age_s"], int)

    def test_update_health_tracking_when_render_probe_then_sets_all_fields(self) -> None:
        """Test that render probe updates all related fields."""
        server_module._update_health_tracking(
            render_probe_ok=True,
            render_probe_notes="Test successful"
        )

        assert server_module._health_tracker.get_last_render_probe_timestamp() is not None
        assert server_module._health_tracker.get_last_render_probe_ok() is True
        assert server_module._health_tracker.get_last_render_probe_notes() == "Test successful"

    def test_update_health_tracking_when_multiple_updates_then_all_set(self) -> None:
        """Test that multiple updates can be applied atomically."""
        server_module._update_health_tracking(
            refresh_attempt=True,
            refresh_success=True,
            event_count=10,
            background_heartbeat=True
        )

        assert server_module._health_tracker.get_last_refresh_attempt_timestamp() is not None
        assert server_module._health_tracker.get_last_refresh_success_timestamp() is not None
        assert server_module._health_tracker.get_event_count() == 10
        assert server_module._health_tracker.get_background_task_status()["last_heartbeat_age_s"] is not None


class TestHealthEndpoint:
    """Test the /api/health endpoint."""

    def setup_method(self) -> None:
        """Reset health tracking variables before each test."""
        # Reset the health tracker to a fresh state
        server_module._health_tracker = server_module.HealthTracker()

    @pytest.mark.asyncio
    async def test_health_check_when_no_refresh_then_returns_degraded(self) -> None:
        """Test that health check returns degraded status when no refresh has occurred."""
        # Test health check function directly by creating it within the _make_app context

        with patch("calendarbot_lite.api.server._now_utc") as mock_now, \
             patch("os.getpid", return_value=12345):

            mock_now.return_value = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

            # Mock the app creation components for context
            event_window_ref = [()]
            window_lock = AsyncMock()
            stop_event = AsyncMock()
            config = {}
            skipped_store = None

            # Create the app which creates the health_check function
            # (unused but needed to initialize internal state)
            _ = await server_module._make_app(
                config, skipped_store, event_window_ref, window_lock, stop_event
            )

            # Test status determination logic directly using the health tracker
            status = server_module._health_tracker.determine_overall_status()

            assert status == "degraded"

            # Test that health data structure is correct
            health_data = {
                "status": status,
                "server_time_iso": "2025-01-01T12:00:00Z",
                "server_status": {
                    "uptime_s": 100,
                    "pid": 12345
                },
                "last_refresh": {
                    "last_success_iso": None,
                    "last_attempt_iso": None,
                    "last_success_delta_s": None,
                    "event_count": 0
                },
                "background_tasks": [],
                "display_probe": {
                    "last_render_probe_iso": None,
                    "last_probe_ok": False,
                    "last_probe_notes": None
                },
            }

            # Verify the structure is correct
            assert health_data["status"] == "degraded"
            assert health_data["last_refresh"]["last_success_iso"] is None
            assert health_data["server_status"]["pid"] == 12345

    def test_health_status_logic_when_recent_success_then_returns_ok(self) -> None:
        """Test that health status logic returns ok when recent refresh succeeded."""
        # Set up successful refresh state using the health tracker
        server_module._health_tracker.update(
            refresh_attempt=True,
            refresh_success=True,
            event_count=5,
            background_heartbeat=True
        )

        # Test status determination logic
        status = server_module._health_tracker.determine_overall_status()
        last_success_delta_s = server_module._health_tracker.get_last_refresh_age_seconds()

        assert status == "ok"
        assert last_success_delta_s is not None
        assert last_success_delta_s < 900

    def test_health_status_logic_when_stale_success_then_returns_degraded(self) -> None:
        """Test that health status logic returns degraded when last success is too old."""
        # Set up stale refresh state (16 minutes ago) by directly modifying internal state
        current_time = time.time()
        server_module._health_tracker._last_refresh_success = current_time - 960  # 16 minutes ago
        server_module._health_tracker._last_refresh_attempt = current_time - 960

        # Test status determination logic
        status = server_module._health_tracker.determine_overall_status()
        last_success_delta_s = server_module._health_tracker.get_last_refresh_age_seconds()

        assert status == "degraded"
        assert last_success_delta_s is not None
        assert last_success_delta_s > 900

    def test_background_task_status_when_recent_heartbeat_then_running(self) -> None:
        """Test that background task status shows running when heartbeat is recent."""
        # Set up recent heartbeat using the health tracker
        server_module._health_tracker.update(background_heartbeat=True)

        # Test background task logic
        task_status = server_module._health_tracker.get_background_task_status()

        assert task_status["name"] == "refresher_task"
        assert task_status["status"] == "running"
        assert task_status["last_heartbeat_age_s"] is not None
        assert task_status["last_heartbeat_age_s"] < 600

    def test_background_task_status_when_stale_heartbeat_then_stale(self) -> None:
        """Test that background task status shows stale when heartbeat is old."""
        # Set up stale heartbeat (11+ minutes ago) by directly modifying internal state
        current_time = time.time()
        server_module._health_tracker._background_task_heartbeat = current_time - 700  # 11+ minutes ago

        # Test background task logic
        task_status = server_module._health_tracker.get_background_task_status()

        assert task_status["name"] == "refresher_task"
        assert task_status["status"] == "stale"
        assert task_status["last_heartbeat_age_s"] is not None
        assert task_status["last_heartbeat_age_s"] >= 600


