#!/usr/bin/env python3
"""Debug script to validate source manager test issues."""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def check_fixture_availability():
    """Check what fixtures are available in conftest.py"""
    logger.info("=== FIXTURE AVAILABILITY CHECK ===")

    try:
        import tests.conftest as conftest_module

        fixtures = [
            name for name in dir(conftest_module) if name.endswith("_manager") or "source" in name
        ]

        logger.info(f"Available fixtures with 'manager' or 'source': {fixtures}")

        # Check specifically for source_manager
        if hasattr(conftest_module, "source_manager"):
            logger.info("✓ source_manager fixture found")
        else:
            logger.error("✗ source_manager fixture NOT found")

        if hasattr(conftest_module, "mock_source_manager"):
            logger.info("✓ mock_source_manager fixture found")
        else:
            logger.error("✗ mock_source_manager fixture NOT found")

    except Exception as e:
        logger.error(f"Error checking fixtures: {e}")


def check_source_manager_imports():
    """Check if SourceManager can be imported and instantiated"""
    logger.info("=== SOURCE MANAGER IMPORT CHECK ===")

    try:
        from calendarbot.sources.manager import SourceManager

        logger.info("✓ SourceManager import successful")

        # Try creating mock settings
        class MockSettings:
            def __init__(self):
                self.ics_url = None
                self.max_retries = 3
                self.retry_backoff_factor = 1.0

        settings = MockSettings()
        source_mgr = SourceManager(settings, None)
        logger.info("✓ SourceManager instantiation successful")

    except Exception as e:
        logger.error(f"Error with SourceManager: {e}")


def check_calendar_event_models():
    """Check CalendarEvent model imports"""
    logger.info("=== CALENDAR EVENT MODEL CHECK ===")

    try:
        # Test imports from both locations
        from calendarbot.cache.models import CalendarEvent as CacheCalendarEvent

        logger.info("✓ CalendarEvent from cache.models imported")

        from calendarbot.ics.models import CalendarEvent as IcsCalendarEvent

        logger.info("✓ CalendarEvent from ics.models imported")

        # Check if they're the same
        if CacheCalendarEvent == IcsCalendarEvent:
            logger.info("✓ Both CalendarEvent models are the same")
        else:
            logger.warning("⚠ CalendarEvent models are different!")
            logger.info(f"Cache model: {CacheCalendarEvent}")
            logger.info(f"ICS model: {IcsCalendarEvent}")

    except Exception as e:
        logger.error(f"Error with CalendarEvent models: {e}")


def check_auth_type_behavior():
    """Check how auth_type behaves in SourceManager"""
    logger.info("=== AUTH TYPE BEHAVIOR CHECK ===")

    try:
        from calendarbot.sources.manager import SourceManager

        class MockSettings:
            def __init__(self):
                self.ics_url = "https://example.com/test.ics"
                self.ics_auth_type = None  # Test with None
                self.max_retries = 3
                self.retry_backoff_factor = 1.0

        settings = MockSettings()
        source_mgr = SourceManager(settings, None)

        # Check what getattr returns for missing attributes
        auth_type = getattr(settings, "ics_auth_type", None)
        logger.info(f"auth_type from getattr: {auth_type} (type: {type(auth_type)})")

        # Check what happens with different values
        settings.ics_auth_type = "basic"
        auth_type2 = getattr(settings, "ics_auth_type", None)
        logger.info(f"auth_type with 'basic': {auth_type2}")

        # Check what happens when attribute doesn't exist
        delattr(settings, "ics_auth_type")
        auth_type3 = getattr(settings, "ics_auth_type", None)
        logger.info(f"auth_type when missing: {auth_type3}")

    except Exception as e:
        logger.error(f"Error checking auth_type behavior: {e}")


def main():
    """Run all diagnostic checks"""
    logger.info("Starting Source Manager test diagnostics...")

    check_fixture_availability()
    check_source_manager_imports()
    check_calendar_event_models()
    check_auth_type_behavior()

    logger.info("=== SUMMARY ===")
    logger.info("Based on test output, main issues are:")
    logger.info("1. Missing 'source_manager' fixture (8 ERROR tests)")
    logger.info("2. auth_type expectation mismatch (1 FAILED test)")
    logger.info("3. Possible CalendarEvent model import inconsistency")


if __name__ == "__main__":
    main()
