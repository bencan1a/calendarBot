#!/usr/bin/env python3
"""Minimal diagnostic test for setup_wizard infinite loop detection."""

import logging
import signal
import sys
import threading
import time
from unittest.mock import MagicMock, Mock, patch

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def timeout_handler(signum, frame):
    """Handle timeout to prevent infinite execution."""
    logger.error("TIMEOUT: Test execution exceeded 30 seconds - likely infinite loop detected")
    print("🚨 INFINITE LOOP DETECTED - Test terminated after 30 seconds")
    sys.exit(1)


def monitor_memory_cpu():
    """Monitor memory and CPU usage during test execution."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024  # MB

    while True:
        try:
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()

            memory_growth = memory_mb - start_memory
            if memory_growth > 100:  # More than 100MB growth
                logger.warning(f"MEMORY GROWTH: {memory_growth:.1f}MB, CPU: {cpu_percent:.1f}%")

            if memory_growth > 1000:  # More than 1GB growth
                logger.error(f"EXCESSIVE MEMORY: {memory_growth:.1f}MB - terminating")
                os.kill(os.getpid(), signal.SIGTERM)

            time.sleep(1)
        except:
            break


def test_configure_ics_url_recursion():
    """Test the specific recursive call in configure_ics_url that might cause infinite loop."""
    logger.info("🔍 Testing configure_ics_url recursion...")

    # Set timeout for safety
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)  # 30 second timeout

    # Start memory/CPU monitoring in background
    monitor_thread = threading.Thread(target=monitor_memory_cpu, daemon=True)
    monitor_thread.start()

    try:
        from calendarbot.setup_wizard import SetupWizard

        wizard = SetupWizard()

        # Create mock that would trigger the recursion bug
        with patch("builtins.input") as mock_input:
            with patch("builtins.print") as mock_print:
                # This sequence should trigger the recursive call on line 264
                mock_input.side_effect = [
                    "https://wrong-pattern.com/test.ics",  # URL that doesn't match outlook pattern
                    "n",  # Don't continue with this URL (triggers recursion)
                    "https://wrong-pattern.com/test.ics",  # Same wrong URL again
                    "n",  # Don't continue again (would create infinite recursion)
                    "https://wrong-pattern.com/test.ics",  # And again...
                    "n",  # This pattern would continue infinitely
                ] * 1000  # Repeat many times to detect infinite loop

                logger.info("📞 Calling configure_ics_url with 'outlook' service...")
                result = wizard.configure_ics_url("outlook")
                logger.info(f"✅ configure_ics_url completed successfully: {result}")

    except Exception as e:
        logger.error(f"❌ Exception during test: {e}")
        raise
    finally:
        signal.alarm(0)  # Cancel timeout

    logger.info("✅ Test completed without infinite loop")


def test_get_input_while_loop():
    """Test the while True loop in get_input method."""
    logger.info("🔍 Testing get_input while loop...")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(15)  # 15 second timeout

    try:
        from calendarbot.setup_wizard import SetupWizard

        wizard = SetupWizard()

        with patch("builtins.input") as mock_input:
            with patch("builtins.print") as mock_print:
                # Test case that could cause infinite loop if validation fails repeatedly
                mock_input.side_effect = [
                    ""
                ] * 1000  # Empty responses that might cause infinite required field loop

                logger.info("📞 Calling get_input with required=True...")
                # This should loop infinitely if there's a bug
                result = wizard.get_input("Test prompt", required=True)
                logger.info(f"✅ get_input completed: {result}")

    except Exception as e:
        logger.error(f"❌ Exception during get_input test: {e}")
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    print("🚀 Starting diagnostic tests for setup_wizard infinite loop...")
    print("⏰ Tests will timeout after 30 seconds if infinite loop detected")
    print("📊 Memory and CPU usage will be monitored")
    print()

    try:
        # Test 1: Recursive call issue
        test_configure_ics_url_recursion()
        print("✅ Test 1 PASSED: No infinite recursion in configure_ics_url")

        # Test 2: Input validation loop
        test_get_input_while_loop()
        print("✅ Test 2 PASSED: No infinite loop in get_input")

        print("\n🎉 All diagnostic tests passed - infinite loop source not in these methods")

    except Exception as e:
        print(f"\n🚨 INFINITE LOOP DETECTED: {e}")
        sys.exit(1)
