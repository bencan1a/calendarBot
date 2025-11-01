"""Health tracking and monitoring for calendarbot_lite server."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HealthStatus:
    """Health status information for the server."""

    status: str  # "ok", "degraded", or "critical"
    server_time_iso: str
    uptime_seconds: int
    pid: int
    event_count: int
    last_refresh_success_age_seconds: Optional[int]
    background_tasks: list[dict[str, Any]]


@dataclass
class SystemDiagnostics:
    """System diagnostics information."""

    platform: str
    python_version: str
    event_loop_running: bool


class HealthTracker:
    """Thread-safe health tracking for server monitoring."""

    def __init__(self) -> None:
        """Initialize health tracker with default values."""
        self._start_time: float = time.time()
        self._last_refresh_attempt: Optional[float] = None
        self._last_refresh_success: Optional[float] = None
        self._current_event_count: int = 0
        self._background_task_heartbeat: Optional[float] = None
        self._last_render_probe: Optional[float] = None
        self._last_render_probe_ok: bool = False
        self._last_render_probe_notes: Optional[str] = None

    def record_refresh_attempt(self) -> None:
        """Record that a refresh attempt was made."""
        self._last_refresh_attempt = time.time()

    def record_refresh_success(self, event_count: int) -> None:
        """Record a successful refresh with event count.

        Args:
            event_count: Number of events in the window after refresh
        """
        now = time.time()
        self._last_refresh_success = now
        self._current_event_count = event_count

    def record_background_heartbeat(self) -> None:
        """Record that background task is alive."""
        self._background_task_heartbeat = time.time()

    def record_render_probe(self, ok: bool, notes: Optional[str] = None) -> None:
        """Record render probe result.

        Args:
            ok: Whether render probe succeeded
            notes: Optional notes about the probe
        """
        self._last_render_probe = time.time()
        self._last_render_probe_ok = ok
        self._last_render_probe_notes = notes

    def update(
        self,
        *,
        refresh_attempt: bool = False,
        refresh_success: bool = False,
        event_count: Optional[int] = None,
        background_heartbeat: bool = False,
        render_probe_ok: Optional[bool] = None,
        render_probe_notes: Optional[str] = None,
    ) -> None:
        """Update multiple health tracking values atomically.

        This is the main update method that can set multiple values at once.

        Args:
            refresh_attempt: Mark a refresh attempt timestamp
            refresh_success: Mark a successful refresh timestamp
            event_count: Update current event count
            background_heartbeat: Update background task heartbeat
            render_probe_ok: Update render probe status
            render_probe_notes: Update render probe notes
        """
        now = time.time()

        if refresh_attempt:
            self._last_refresh_attempt = now

        if refresh_success:
            self._last_refresh_success = now

        if event_count is not None:
            self._current_event_count = event_count

        if background_heartbeat:
            self._background_task_heartbeat = now

        if render_probe_ok is not None:
            self._last_render_probe = now
            self._last_render_probe_ok = render_probe_ok
            if render_probe_notes is not None:
                self._last_render_probe_notes = render_probe_notes

    def get_uptime_seconds(self) -> int:
        """Get server uptime in seconds.

        Returns:
            Uptime in seconds since tracker initialization
        """
        return int(time.time() - self._start_time)

    def get_last_refresh_age_seconds(self) -> Optional[int]:
        """Get age of last successful refresh in seconds.

        Returns:
            Seconds since last successful refresh, or None if never refreshed
        """
        if self._last_refresh_success is None:
            return None
        return int(time.time() - self._last_refresh_success)

    def get_background_task_status(self) -> dict[str, Any]:
        """Get background task status.

        Returns:
            Dictionary with task status information
        """
        if self._background_task_heartbeat is None:
            return {
                "name": "refresher_task",
                "status": "unknown",
                "last_heartbeat_age_s": None,
            }

        heartbeat_age = int(time.time() - self._background_task_heartbeat)
        status = "running" if heartbeat_age < 600 else "stale"  # 10 minutes

        return {
            "name": "refresher_task",
            "status": status,
            "last_heartbeat_age_s": heartbeat_age,
        }

    def determine_overall_status(self) -> str:
        """Determine overall health status.

        Returns:
            "ok", "degraded", or "critical"
        """
        last_success_age = self.get_last_refresh_age_seconds()

        if self._last_refresh_success is None:
            return "degraded"  # Never had successful refresh

        if last_success_age is not None and last_success_age > 900:  # 15 minutes
            return "degraded"  # No successful refresh in 15+ minutes

        return "ok"

    def get_health_status(self, current_time_iso: str) -> HealthStatus:
        """Get comprehensive health status.

        Args:
            current_time_iso: Current time in ISO format

        Returns:
            HealthStatus object with all health information
        """
        return HealthStatus(
            status=self.determine_overall_status(),
            server_time_iso=current_time_iso,
            uptime_seconds=self.get_uptime_seconds(),
            pid=os.getpid(),
            event_count=self._current_event_count,
            last_refresh_success_age_seconds=self.get_last_refresh_age_seconds(),
            background_tasks=[self.get_background_task_status()],
        )

    def get_event_count(self) -> int:
        """Get current event count.

        Returns:
            Number of events currently in window
        """
        return self._current_event_count

    def get_last_refresh_success_timestamp(self) -> Optional[float]:
        """Get timestamp of last successful refresh.

        Returns:
            Unix timestamp of last successful refresh, or None if never refreshed
        """
        return self._last_refresh_success

    def get_last_refresh_attempt_timestamp(self) -> Optional[float]:
        """Get timestamp of last refresh attempt.

        Returns:
            Unix timestamp of last refresh attempt, or None if never attempted
        """
        return self._last_refresh_attempt

    def get_last_render_probe_timestamp(self) -> Optional[float]:
        """Get timestamp of last render probe.

        Returns:
            Unix timestamp of last render probe, or None if never probed
        """
        return self._last_render_probe

    def get_last_render_probe_ok(self) -> bool:
        """Get result of last render probe.

        Returns:
            True if last render probe succeeded, False otherwise
        """
        return self._last_render_probe_ok

    def get_last_render_probe_notes(self) -> Optional[str]:
        """Get notes from last render probe.

        Returns:
            Notes from last render probe, or None if no notes
        """
        return self._last_render_probe_notes


def get_system_diagnostics() -> SystemDiagnostics:
    """Get system diagnostics information.

    Returns:
        SystemDiagnostics with platform and runtime information
    """
    import asyncio
    import platform
    import sys

    # Check if event loop is running
    event_loop_running = False
    try:
        asyncio.get_running_loop()
        event_loop_running = True
    except RuntimeError:
        pass

    return SystemDiagnostics(
        platform=platform.platform(),
        python_version=sys.version.split()[0],
        event_loop_running=event_loop_running,
    )
