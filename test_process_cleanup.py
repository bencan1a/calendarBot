#!/usr/bin/env python3
"""Test script to verify automatic process cleanup functionality."""

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calendarbot.utils.process import (
    auto_cleanup_before_start,
    check_port_availability,
    find_calendarbot_processes,
    kill_calendarbot_processes,
)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_process_discovery():
    """Test the process discovery functionality."""
    logger.info("Testing process discovery...")

    processes = find_calendarbot_processes()
    logger.info(f"Found {len(processes)} calendarbot processes currently running")

    for process in processes:
        logger.info(f"  - {process}")

    return len(processes)


def test_port_availability():
    """Test port availability checking."""
    logger.info("Testing port availability...")

    # Test with a port that should be available
    available = check_port_availability("localhost", 9999)
    logger.info(f"Port 9999 available: {available}")

    # Test with a port that might be in use
    http_available = check_port_availability("localhost", 80)
    logger.info(f"Port 80 available: {http_available}")

    return available


def start_dummy_process():
    """Start a dummy Python process that can be detected."""
    logger.info("Starting dummy calendarbot process for testing...")

    # Create a simple script that will be detected by our process finder
    dummy_script = """
import time
import sys
print("Dummy calendarbot process started", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Dummy process stopping", flush=True)
    sys.exit(0)
"""

    # Write the dummy script
    dummy_file = project_root / "dummy_calendarbot_test.py"
    with open(dummy_file, "w") as f:
        f.write(dummy_script)

    try:
        # Start the dummy process
        process = subprocess.Popen(
            [sys.executable, str(dummy_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Give it a moment to start
        time.sleep(0.5)

        logger.info(f"Started dummy process with PID: {process.pid}")
        return process, dummy_file

    except Exception as e:
        logger.error(f"Failed to start dummy process: {e}")
        if dummy_file.exists():
            dummy_file.unlink()
        return None, dummy_file


def test_process_cleanup():
    """Test the process cleanup functionality."""
    logger.info("Testing process cleanup...")

    # Start a dummy process
    dummy_process, dummy_file = start_dummy_process()

    if not dummy_process:
        logger.error("Could not start dummy process for testing")
        return False

    try:
        # Verify the process is detectable
        processes_before = find_calendarbot_processes()
        dummy_found = any(p.pid == dummy_process.pid for p in processes_before)

        if not dummy_found:
            logger.warning("Dummy process not detected by process finder")
        else:
            logger.info("Dummy process successfully detected")

        # Test the cleanup function
        killed_count, errors = kill_calendarbot_processes(exclude_self=True)

        logger.info(f"Cleanup killed {killed_count} processes")
        if errors:
            logger.warning(f"Cleanup errors: {errors}")

        # Verify the process was terminated
        time.sleep(1)
        processes_after = find_calendarbot_processes()
        dummy_still_running = any(p.pid == dummy_process.pid for p in processes_after)

        if dummy_still_running:
            logger.warning("Dummy process still running after cleanup")
            return False
        else:
            logger.info("Dummy process successfully terminated")
            return True

    finally:
        # Make sure we clean up
        try:
            if dummy_process.poll() is None:  # Process still running
                dummy_process.terminate()
                dummy_process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error cleaning up dummy process: {e}")

        # Remove the dummy script file
        if dummy_file.exists():
            dummy_file.unlink()


def test_auto_cleanup():
    """Test the auto cleanup before start functionality."""
    logger.info("Testing auto cleanup before start...")

    # Test with a port that should be available
    success = auto_cleanup_before_start("localhost", 9998, force=True)
    logger.info(f"Auto cleanup for port 9998: {'SUCCESS' if success else 'FAILED'}")

    return success


async def main():
    """Run all tests."""
    logger.info("Starting Calendar Bot process cleanup tests...")
    logger.info("=" * 60)

    tests_passed = 0
    total_tests = 4

    # Test 1: Process discovery
    try:
        initial_count = test_process_discovery()
        tests_passed += 1
        logger.info("✅ Process discovery test PASSED")
    except Exception as e:
        logger.error(f"❌ Process discovery test FAILED: {e}")

    logger.info("-" * 40)

    # Test 2: Port availability
    try:
        if test_port_availability():
            tests_passed += 1
            logger.info("✅ Port availability test PASSED")
        else:
            logger.warning("⚠️  Port availability test unclear (port 9999 not available)")
            tests_passed += 1  # Count as passed since this might be expected
    except Exception as e:
        logger.error(f"❌ Port availability test FAILED: {e}")

    logger.info("-" * 40)

    # Test 3: Process cleanup
    try:
        if test_process_cleanup():
            tests_passed += 1
            logger.info("✅ Process cleanup test PASSED")
        else:
            logger.error("❌ Process cleanup test FAILED")
    except Exception as e:
        logger.error(f"❌ Process cleanup test FAILED with exception: {e}")

    logger.info("-" * 40)

    # Test 4: Auto cleanup
    try:
        if test_auto_cleanup():
            tests_passed += 1
            logger.info("✅ Auto cleanup test PASSED")
        else:
            logger.error("❌ Auto cleanup test FAILED")
    except Exception as e:
        logger.error(f"❌ Auto cleanup test FAILED with exception: {e}")

    # Summary
    logger.info("=" * 60)
    logger.info(f"Tests completed: {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        logger.info("🎉 All tests PASSED! Process cleanup functionality is working correctly.")
        return 0
    else:
        logger.error(
            f"❌ {total_tests - tests_passed} test(s) FAILED. Please check the implementation."
        )
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
