#!/usr/bin/env python3
"""Test script for framebuffer UI visual validation.

This script runs the framebuffer UI in windowed mode for testing
before deploying to actual hardware.

Usage:
    # Test with live backend
    python test_framebuffer_ui.py

    # Test with mock data
    python test_framebuffer_ui.py --mock
"""

import argparse
import asyncio
import logging
import os
import platform
import sys
from datetime import datetime, timedelta

# Ensure windowed mode for testing
# Set appropriate SDL driver for each platform
if platform.system() != "Darwin":
    # Linux/other: Use x11 for windowed mode testing
    os.environ["SDL_VIDEODRIVER"] = "x11"
# Mac: Don't set SDL_VIDEODRIVER - let renderer auto-detect Cocoa

os.environ["SDL_NOMOUSE"] = "0"  # Show mouse for testing

from framebuffer_ui.config import Config
from framebuffer_ui.layout_engine import LayoutEngine
from framebuffer_ui.renderer import FramebufferRenderer

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def get_mock_api_response() -> dict:
    """Generate mock API response for testing.

    Returns:
        Mock /api/whats-next response
    """
    # Meeting starts in 9 hours 58 minutes
    start_time = datetime.now() + timedelta(hours=9, minutes=58)

    return {
        "meeting": {
            "meeting_id": "test-123",
            "subject": "Data and Information Deep Dive",
            "description": "",
            "attendees": [],
            "start_iso": start_time.isoformat(),
            "duration_seconds": 3600,  # 1 hour
            "location": "Microsoft Teams Meeting",
            "seconds_until_start": int(
                (start_time - datetime.now()).total_seconds()
            ),
        }
    }


def get_mock_critical_response() -> dict:
    """Generate mock response for critical state (meeting starting soon).

    Returns:
        Mock response with meeting in 3 minutes
    """
    start_time = datetime.now() + timedelta(minutes=3)

    return {
        "meeting": {
            "meeting_id": "test-critical",
            "subject": "Important Meeting",
            "description": "",
            "attendees": [],
            "start_iso": start_time.isoformat(),
            "duration_seconds": 1800,  # 30 minutes
            "location": "Conference Room A",
            "seconds_until_start": int(
                (start_time - datetime.now()).total_seconds()
            ),
        }
    }


def get_mock_no_meetings_response() -> dict:
    """Generate mock response for no meetings.

    Returns:
        Empty mock response
    """
    return {}


async def test_visual_rendering(mock_mode: bool = False) -> None:
    """Test visual rendering with different states.

    Args:
        mock_mode: If True, use mock data; if False, use live backend
    """
    # Load config
    config = Config.from_env()

    # Override display size for testing window
    config.display_width = 480
    config.display_height = 800

    logger.info("Starting visual test (mock_mode=%s)", mock_mode)
    logger.info("Backend URL: %s", config.backend_url)

    # Create components
    renderer = FramebufferRenderer(config)
    layout_engine = LayoutEngine()

    try:
        if mock_mode:
            # Test with mock data
            logger.info("Testing with MOCK data...")

            # Test 1: Normal meeting (9 hours away)
            logger.info("Test 1: Normal meeting (9h away)")
            mock_data = get_mock_api_response()
            layout = layout_engine.process(mock_data)
            renderer.render(layout)
            await asyncio.sleep(3)

            # Test 2: Critical meeting (3 minutes away)
            logger.info("Test 2: Critical meeting (3m away)")
            critical_data = get_mock_critical_response()
            layout = layout_engine.process(critical_data)
            renderer.render(layout)
            await asyncio.sleep(3)

            # Test 3: No meetings
            logger.info("Test 3: No meetings")
            no_meetings_data = get_mock_no_meetings_response()
            layout = layout_engine.process(no_meetings_data)
            renderer.render(layout)
            await asyncio.sleep(3)

        else:
            # Test with live backend
            logger.info("Testing with LIVE backend...")

            from framebuffer_ui.api_client import CalendarAPIClient

            api_client = CalendarAPIClient(config)

            try:
                # Fetch live data
                data = await api_client.fetch_whats_next()
                logger.info("Received data: %s", data)

                # Process and render
                layout = layout_engine.process(data)
                renderer.render(layout)

                logger.info("Live data rendered successfully")
                logger.info("Window will stay open for 10 seconds...")

                await asyncio.sleep(10)

            finally:
                await api_client.close()

        logger.info("Visual test complete")

    finally:
        renderer.cleanup()


def main() -> None:
    """Main entry point for test script."""
    parser = argparse.ArgumentParser(
        description="Test framebuffer UI visual rendering"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of live backend",
    )

    args = parser.parse_args()

    try:
        asyncio.run(test_visual_rendering(mock_mode=args.mock))
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as error:
        logger.exception("Test failed: %s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
