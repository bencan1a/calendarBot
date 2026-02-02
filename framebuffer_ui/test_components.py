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
from datetime import datetime, timedelta

from framebuffer_ui.api_client import CalendarAPIClient
from framebuffer_ui.config import Config
from framebuffer_ui.layout_engine import LayoutEngine

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
            "seconds_until_start": int(
                (start_time - datetime.now()).total_seconds()
            ),
        }
    }

    layout = engine.process(mock_data)
    assert layout.has_data, "Should have meeting data"
    assert layout.countdown is not None, "Should have countdown"
    assert layout.countdown.value == 9, "Should show 9 hours"
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
    assert layout.countdown.value == 3, f"Should show 3 minutes, got {layout.countdown.value}"
    assert layout.countdown.primary_unit == "MINUTES", "Should show MINUTES"
    assert layout.countdown.state == "critical", "Should be critical state"
    logger.info("✓ Test 2 passed: Critical meeting (3m away)")

    # Test 3: No meetings
    no_meetings_data = {}

    layout = engine.process(no_meetings_data)
    assert not layout.has_data, "Should have no meeting data"
    assert layout.meeting is not None, "Should have fallback meeting display"
    assert (
        layout.meeting.title == "No upcoming meetings"
    ), "Should show no meetings message"
    logger.info("✓ Test 3 passed: No meetings")

    logger.info("✅ Layout engine tests passed!")


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
            logger.info(
                "  Seconds until: %s", meeting.get("seconds_until_start")
            )

        logger.info("✅ API client test passed!")

    except Exception as error:
        logger.error("❌ API client test failed: %s", error)
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

    # Test API client (requires backend)
    await test_api_client()

    logger.info("")
    logger.info("=" * 60)
    logger.info("All tests passed! ✅")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        logger.exception("Tests failed: %s", error)
        sys.exit(1)
