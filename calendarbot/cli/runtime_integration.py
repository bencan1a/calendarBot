"""Runtime tracking integration for Calendar Bot CLI modes.

This module provides utilities for integrating the RuntimeResourceTracker
with different application modes (web, interactive, epaper, etc.).
"""

import logging
from typing import Any, Optional

from calendarbot.monitoring.runtime_tracker import RuntimeResourceTracker

logger = logging.getLogger(__name__)


def create_runtime_tracker(settings: Any) -> Optional[RuntimeResourceTracker]:
    """Create and configure a RuntimeResourceTracker based on settings.

    Args:
        settings: Application settings containing runtime tracking configuration

    Returns:
        Configured RuntimeResourceTracker if enabled, None otherwise
    """
    if not getattr(settings, "runtime_tracking", None) or not getattr(
        settings.runtime_tracking, "enabled", False
    ):
        return None

    try:
        # Extract runtime tracking configuration
        sampling_interval = getattr(settings.runtime_tracking, "sampling_interval", 1.0)
        # With simplified CLI, automatically enable saving when tracking is enabled
        save_samples = getattr(settings.runtime_tracking, "save_samples", True)

        # Create and configure the tracker (no session_name in constructor)
        tracker = RuntimeResourceTracker(
            settings=settings,
            sampling_interval=sampling_interval,
            save_individual_samples=save_samples,
        )

        logger.info(
            f"Created runtime tracker with interval={sampling_interval}s, save_samples={save_samples}"
        )
        return tracker

    except Exception as e:
        logger.error(f"Failed to create runtime tracker: {e}")
        return None


def start_runtime_tracking(
    tracker: Optional[RuntimeResourceTracker],
    operation_name: str = "application",
    session_name: Optional[str] = None,
) -> bool:
    """Start runtime tracking for an operation.

    Args:
        tracker: RuntimeResourceTracker instance or None
        operation_name: Name of the operation being tracked
        session_name: Optional session name for the tracking session

    Returns:
        True if tracking was started, False otherwise
    """
    if not tracker:
        return False

    try:
        # Use session_name if provided, otherwise use operation_name
        actual_session_name = session_name or operation_name

        session_id = tracker.start_tracking(
            session_name=actual_session_name, metadata={"operation": operation_name}
        )

        logger.info(
            f"Started runtime tracking for operation: {operation_name} (session: {session_id})"
        )
        print(f"Runtime tracking started for: {operation_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to start runtime tracking for {operation_name}: {e}")
        print(f"Warning: Could not start runtime tracking - {e}")
        return False


def stop_runtime_tracking(
    tracker: Optional[RuntimeResourceTracker], operation_name: str = "application"
) -> bool:
    """Stop runtime tracking and log results.

    Args:
        tracker: RuntimeResourceTracker instance or None
        operation_name: Name of the operation being tracked

    Returns:
        True if tracking was stopped successfully, False otherwise
    """
    if not tracker:
        return False

    try:
        stats = tracker.stop_tracking()

        if stats:
            # Log comprehensive summary with correct attribute names
            logger.info(
                f"Runtime tracking complete for {operation_name} - "
                f"Duration={stats.duration_seconds:.2f}s, "
                f"CPU_median={stats.cpu_median:.1f}%, "
                f"CPU_max={stats.cpu_maximum:.1f}%, "
                f"Memory_median={stats.memory_median_mb:.1f}MB, "
                f"Memory_max={stats.memory_maximum_mb:.1f}MB, "
                f"Samples={stats.total_samples}"
            )

            # User-friendly output
            print(f"Runtime tracking completed for: {operation_name}")
            print(f"   CPU Usage - Median: {stats.cpu_median:.1f}%, Max: {stats.cpu_maximum:.1f}%")
            print(
                f"   Memory Usage - Median: {stats.memory_median_mb:.1f}MB, Max: {stats.memory_maximum_mb:.1f}MB"
            )
            print(f"   Samples Collected: {stats.total_samples}")
            print(f"   Duration: {stats.duration_seconds:.2f} seconds")

            # Check if results were saved to database
            if hasattr(stats, "metadata") and stats.metadata.get("saved_to_database"):
                print("   Results saved to performance database")

        logger.info(f"Stopped runtime tracking for operation: {operation_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to stop runtime tracking for {operation_name}: {e}")
        print(f"Warning: Error stopping runtime tracking - {e}")
        return False
