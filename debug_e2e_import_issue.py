#!/usr/bin/env python3
"""Debug script to validate E2E import issue diagnosis."""

import os
import sys
import traceback
from pathlib import Path


def test_import_chain():
    """Test the import chain that's causing the E2E test failure."""

    print("=== E2E Import Issue Diagnosis ===")
    print(f"Python path: {sys.path[0]}")
    print(f"Working directory: {os.getcwd()}")
    print(f"CALENDARBOT_ICS_URL env var: {os.environ.get('CALENDARBOT_ICS_URL', 'NOT SET')}")

    # Check if config files exist
    config_paths = [
        Path("config/config.yaml"),
        Path.home() / ".config" / "calendarbot" / "config.yaml",
    ]

    print("\n=== Configuration File Check ===")
    for config_path in config_paths:
        exists = config_path.exists()
        print(f"Config file {config_path}: {'EXISTS' if exists else 'NOT FOUND'}")

    print("\n=== Step-by-step Import Test ===")

    # Test 1: Try importing config.settings directly
    print("1. Testing direct import of config.settings...")
    try:
        import config.settings

        print("   ✓ config.settings imported successfully")
        print(f"   Settings ICS URL: {getattr(config.settings.settings, 'ics_url', 'NOT SET')}")
    except Exception as e:
        print(f"   ✗ Failed to import config.settings: {e}")
        traceback.print_exc()
        return False

    # Test 2: Try importing calendarbot.main
    print("\n2. Testing import of calendarbot.main...")
    try:
        import calendarbot.main

        print("   ✓ calendarbot.main imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import calendarbot.main: {e}")
        traceback.print_exc()
        return False

    # Test 3: Try importing the E2E test file
    print("\n3. Testing import of E2E test file...")
    try:
        import tests.e2e.test_application_workflows

        print("   ✓ E2E test file imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import E2E test file: {e}")
        traceback.print_exc()
        return False

    print("\n=== All imports successful! ===")
    return True


def test_with_mock_env():
    """Test imports with mocked environment variable."""

    print("\n=== Testing with Mock Environment ===")

    # Set mock environment variable
    os.environ["CALENDARBOT_ICS_URL"] = "http://test.example.com/calendar.ics"
    print(f"Set CALENDARBOT_ICS_URL to: {os.environ['CALENDARBOT_ICS_URL']}")

    # Clear any already imported modules to force reimport
    modules_to_clear = [
        "config.settings",
        "calendarbot.main",
        "tests.e2e.test_application_workflows",
    ]

    for module in modules_to_clear:
        if module in sys.modules:
            print(f"Clearing cached module: {module}")
            del sys.modules[module]

    # Try importing again
    return test_import_chain()


if __name__ == "__main__":
    print("Starting E2E import issue diagnosis...")

    # Test without environment setup
    success = test_import_chain()

    if not success:
        # Test with mock environment
        success = test_with_mock_env()

    if success:
        print("\n✓ DIAGNOSIS: Import issue resolved with proper environment setup")
        print(
            "✓ ROOT CAUSE: Missing CALENDARBOT_ICS_URL environment variable during test collection"
        )
    else:
        print("\n✗ DIAGNOSIS: Additional issues beyond environment variable")

    # Clean up
    if "CALENDARBOT_ICS_URL" in os.environ:
        del os.environ["CALENDARBOT_ICS_URL"]
