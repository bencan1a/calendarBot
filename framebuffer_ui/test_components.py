#!/usr/bin/env python3
"""Test framebuffer UI components without requiring display.

This script tests the API client and layout engine independently
without requiring pygame or a display.

Usage:
    python test_framebuffer_components.py
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Any

from framebuffer_ui.api_client import CalendarAPIClient
from framebuffer_ui.config import Config
from framebuffer_ui.layout_engine import LayoutEngine
from framebuffer_ui.main import CalendarKioskApp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_layout_engine() -> None:
    """Test layout engine with mock data."""
    logger.info("Testing layout engine...")

    engine = LayoutEngine()

    # Test 1: Meeting in 9 hours
    start_time = datetime.now() + timedelta(hours=9, minutes=58)
    mock_data = {
        "meeting": {
            "subject": "Data and Information Deep Dive",
            "start_iso": start_time.isoformat(),
            "duration_seconds": 3600,
            "location": "Microsoft Teams Meeting",
            "seconds_until_start": int((start_time - datetime.now()).total_seconds()),
        }
    }

    layout = engine.process(mock_data)
    assert layout.has_data, "Should have meeting data"
    assert layout.countdown is not None, "Should have countdown"
    assert layout.countdown.value == 9, f"Should show 9 hours, got {layout.countdown.value}"
    assert layout.countdown.primary_unit == "HOURS", "Should show HOURS"
    assert layout.countdown.state == "normal", "Should be normal state"
    logger.info("✓ Test 1 passed: Normal meeting (9h away)")

    # Test 2: Meeting in 3 minutes (critical)
    critical_data = {
        "meeting": {
            "subject": "Important Meeting",
            "start_iso": (datetime.now() + timedelta(seconds=200)).isoformat(),
            "duration_seconds": 1800,
            "location": "Conference Room A",
            "seconds_until_start": 200,  # Just over 3 minutes
        }
    }

    layout = engine.process(critical_data)
    assert layout.countdown is not None, "Should have countdown"
    assert layout.countdown.value == 3, f"Should show 3 minutes, got {layout.countdown.value}"
    assert layout.countdown.primary_unit == "MINUTES", "Should show MINUTES"
    assert layout.countdown.state == "critical", "Should be critical state"
    logger.info("✓ Test 2 passed: Critical meeting (3m away)")

    # Test 3: No meetings
    no_meetings_data: dict[str, Any] = {}

    layout = engine.process(no_meetings_data)
    assert not layout.has_data, "Should have no meeting data"
    assert layout.meeting is not None, "Should have fallback meeting display"
    assert layout.meeting.title == "No upcoming meetings", "Should show no meetings message"
    logger.info("✓ Test 3 passed: No meetings")

    logger.info("✅ Layout engine tests passed!")


def test_countdown_adjustment() -> None:
    """Test countdown adjustment based on elapsed time."""
    logger.info("Testing countdown adjustment...")

    config = Config.from_env()
    app = CalendarKioskApp(config)

    # Test 1: Meeting in 600 seconds (10 minutes)
    cached_data = {
        "meeting": {
            "subject": "Test Meeting",
            "start_iso": (datetime.now() + timedelta(seconds=600)).isoformat(),
            "duration_seconds": 1800,
            "location": "Teams",
            "seconds_until_start": 600,
        }
    }

    # Simulate 30 seconds elapsed
    fetch_time = time.time() - 30

    # Adjust countdown
    adjusted = app._adjust_countdown_data(cached_data, fetch_time)  # noqa: SLF001

    # Should be 570 seconds now (600 - 30)
    assert adjusted["meeting"]["seconds_until_start"] == 570, (
        f"Expected 570, got {adjusted['meeting']['seconds_until_start']}"
    )
    logger.info("✓ Test 1 passed: 30 seconds elapsed (600s -> 570s)")

    # Test 2: Meeting already passed
    old_data = {
        "meeting": {
            "subject": "Past Meeting",
            "start_iso": (datetime.now() - timedelta(seconds=100)).isoformat(),
            "duration_seconds": 1800,
            "location": "Teams",
            "seconds_until_start": 50,
        }
    }

    # Simulate 100 seconds elapsed (would make countdown negative)
    fetch_time = time.time() - 100

    # Adjust countdown
    adjusted = app._adjust_countdown_data(old_data, fetch_time)  # noqa: SLF001

    # Should be 0 (max(0, 50 - 100))
    assert adjusted["meeting"]["seconds_until_start"] == 0, (
        f"Expected 0 for negative countdown, got {adjusted['meeting']['seconds_until_start']}"
    )
    logger.info("✓ Test 2 passed: Negative countdown clamped to 0")

    # Test 3: No meeting data
    empty_data: dict[str, Any] = {}
    fetch_time = time.time() - 10

    adjusted = app._adjust_countdown_data(empty_data, fetch_time)  # noqa: SLF001

    # Should return empty data unchanged
    assert adjusted == empty_data, "Empty data should be unchanged"
    logger.info("✓ Test 3 passed: Empty data unchanged")

    # Test 4: None fetch time
    adjusted = app._adjust_countdown_data(cached_data, None)  # noqa: SLF001

    # Should return data unchanged
    assert adjusted["meeting"]["seconds_until_start"] == 600, (
        "Data should be unchanged when fetch_time is None"
    )
    logger.info("✓ Test 4 passed: None fetch_time returns unchanged data")

    logger.info("✅ Countdown adjustment tests passed!")


async def test_api_client() -> None:
    """Test API client with live backend."""
    logger.info("Testing API client...")

    config = Config.from_env()
    logger.info("Backend URL: %s", config.backend_url)

    client = CalendarAPIClient(config)

    try:
        # Fetch from live backend
        data = await client.fetch_whats_next()

        logger.info("API Response:")
        logger.info("  Has meeting: %s", "meeting" in data)

        if "meeting" in data:
            meeting = data["meeting"]
            logger.info("  Subject: %s", meeting.get("subject"))
            logger.info("  Start: %s", meeting.get("start_iso"))
            logger.info("  Location: %s", meeting.get("location"))
            logger.info("  Seconds until: %s", meeting.get("seconds_until_start"))

        logger.info("✅ API client test passed!")

    except Exception:
        logger.exception("❌ API client test failed")
        raise

    finally:
        await client.close()


async def main() -> None:
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Testing Framebuffer UI Components")
    logger.info("=" * 60)

    # Test layout engine (no dependencies)
    test_layout_engine()

    logger.info("")

    # Test countdown adjustment (no dependencies)
    test_countdown_adjustment()

    logger.info("")

    # Test API client (requires backend)
    await test_api_client()

    logger.info("")
    logger.info("=" * 60)
    logger.info("All tests passed! ✅")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logger.exception("Tests failed")
        sys.exit(1)
