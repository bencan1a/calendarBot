#!/usr/bin/env python3
"""Minimal test to isolate exact infinite loop location in setup_wizard."""

import logging
import signal
import sys
from unittest.mock import patch

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def timeout_handler(signum, frame):
    logger.error("TIMEOUT: Infinite loop detected")
    print("🚨 INFINITE LOOP DETECTED")
    sys.exit(1)


def test_get_input_infinite_loop():
    """Test if get_input method has infinite loop with empty responses."""
    logger.info("Testing get_input method...")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)  # 10 second timeout

    try:
        from calendarbot.setup_wizard import SetupWizard

        wizard = SetupWizard()

        # Test the specific pattern that causes infinite loop
        with patch("builtins.input") as mock_input:
            with patch("builtins.print"):
                # This should cause infinite loop if required=True and we keep providing empty responses
                mock_input.return_value = ""  # Always return empty string

                logger.info("Calling get_input with required=True and empty responses...")
                result = wizard.get_input("Test prompt", required=True)
                logger.info(f"get_input returned: {result}")

    except Exception as e:
        logger.error(f"Exception: {e}")
        raise
    finally:
        signal.alarm(0)


def test_validate_url_loop():
    """Test if validate_url causes issues."""
    logger.info("Testing validate_url method...")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)

    try:
        from calendarbot.setup_wizard import SetupWizard

        wizard = SetupWizard()

        # Test URL validation that might cause issues
        result = wizard.validate_url("https://wrong-pattern.com/test.ics")
        logger.info(f"validate_url returned: {result}")

    except Exception as e:
        logger.error(f"Exception in validate_url: {e}")
        raise
    finally:
        signal.alarm(0)


def test_get_input_with_validation():
    """Test get_input with validation function that might loop."""
    logger.info("Testing get_input with validation...")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)

    try:
        from calendarbot.setup_wizard import SetupWizard

        wizard = SetupWizard()

        with patch("builtins.input") as mock_input:
            with patch("builtins.print"):
                # Provide a URL that fails validation repeatedly
                mock_input.side_effect = ["invalid_url"] * 100  # Invalid URL 100 times

                logger.info("Calling get_input with validation that always fails...")
                result = wizard.get_input("Test", required=True, validate_func=wizard.validate_url)
                logger.info(f"get_input with validation returned: {result}")

    except Exception as e:
        logger.error(f"Exception in get_input with validation: {e}")
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    print("🔍 Testing individual methods for infinite loops...")

    try:
        # Test 1: Basic get_input with empty responses
        test_get_input_infinite_loop()
        print("✅ Test 1 passed: get_input doesn't loop infinitely with empty responses")

    except Exception as e:
        print(f"🚨 Test 1 FAILED: get_input has infinite loop - {e}")
        sys.exit(1)

    try:
        # Test 2: URL validation
        test_validate_url_loop()
        print("✅ Test 2 passed: validate_url works correctly")

    except Exception as e:
        print(f"🚨 Test 2 FAILED: validate_url has issues - {e}")
        sys.exit(1)

    try:
        # Test 3: get_input with failing validation
        test_get_input_with_validation()
        print("✅ Test 3 passed: get_input with validation doesn't loop infinitely")

    except Exception as e:
        print(f"🚨 Test 3 FAILED: get_input with validation has infinite loop - {e}")
        sys.exit(1)

    print("🎉 All tests passed - investigating other potential causes...")
