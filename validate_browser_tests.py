#!/usr/bin/env python3
"""
Validate browser test suite infrastructure and dependencies.
This script diagnoses issues with the simplified browser test suite.
"""

import asyncio
import sys
import time
from pathlib import Path


def check_dependencies():
    """Check if all required dependencies are available."""
    print("=== Checking Dependencies ===")

    try:
        import pytest

        print(f"✓ pytest: {pytest.__version__}")
    except ImportError:
        print("✗ pytest not available")
        return False

    try:
        import pyppeteer

        print(f"✓ pyppeteer: {pyppeteer.__version__}")
    except ImportError:
        print("✗ pyppeteer not available")
        return False

    try:
        import pytest_asyncio

        print(f"✓ pytest-asyncio: {pytest_asyncio.__version__}")
    except ImportError:
        print("✗ pytest-asyncio not available")
        return False

    try:
        from calendarbot.web.server import WebServer

        print("✓ WebServer import successful")
    except ImportError as e:
        print(f"✗ WebServer import failed: {e}")
        return False

    try:
        from calendarbot.cache.manager import CacheManager

        print("✓ CacheManager import successful")
    except ImportError as e:
        print(f"✗ CacheManager import failed: {e}")
        return False

    return True


async def test_web_server_startup():
    """Test if web server can start successfully."""
    print("\n=== Testing Web Server Startup ===")

    try:
        import tempfile

        from calendarbot.cache.manager import CacheManager
        from calendarbot.display.manager import DisplayManager
        from calendarbot.ui.navigation import NavigationState
        from calendarbot.web.server import WebServer
        from config.settings import CalendarBotSettings

        # Create test settings
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            settings = CalendarBotSettings(
                ics_url="http://localhost:8999/test.ics",
                config_dir=temp_path / "config",
                data_dir=temp_path / "data",
                cache_dir=temp_path / "cache",
                web_host="127.0.0.1",
                web_port=8998,  # Use different port
                web_theme="standard",
            )

            # Initialize components
            cache_manager = CacheManager(settings)
            await cache_manager.initialize()

            display_manager = DisplayManager(settings)
            navigation_state = NavigationState()

            # Create web server
            web_server = WebServer(settings, display_manager, cache_manager, navigation_state)

            # Try to start server
            print("Starting web server...")
            web_server.start()

            # Wait a moment
            await asyncio.sleep(2)

            print(f"✓ Web server started on {settings.web_host}:{settings.web_port}")

            # Stop server
            web_server.stop()
            print("✓ Web server stopped successfully")

            return True

    except Exception as e:
        print(f"✗ Web server startup failed: {e}")
        return False


async def test_browser_launch():
    """Test if browser can launch successfully."""
    print("\n=== Testing Browser Launch ===")

    try:
        from pyppeteer import launch

        print("Launching browser...")
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
            ],
        )

        print("✓ Browser launched successfully")

        # Create a page
        page = await browser.newPage()
        print("✓ Page created successfully")

        # Navigate to a simple page
        await page.goto("data:text/html,<h1>Test</h1>")
        print("✓ Navigation successful")

        # Close browser
        await page.close()
        await browser.close()
        print("✓ Browser closed successfully")

        return True

    except Exception as e:
        print(f"✗ Browser launch failed: {e}")
        return False


def count_test_files():
    """Count the number of test files in the simplified suite."""
    print("\n=== Analyzing Test Suite ===")

    browser_test_dir = Path("tests/browser")
    if not browser_test_dir.exists():
        print("✗ Browser test directory not found")
        return 0

    test_files = list(browser_test_dir.glob("test_*.py"))
    print(f"Found {len(test_files)} test files:")

    total_tests = 0
    for test_file in test_files:
        try:
            content = test_file.read_text()
            # Count test methods
            test_methods = content.count("def test_")
            total_tests += test_methods
            print(f"  - {test_file.name}: {test_methods} tests")
        except Exception as e:
            print(f"  - {test_file.name}: Error reading file - {e}")

    print(f"Total estimated tests: {total_tests}")
    return total_tests


def analyze_test_complexity():
    """Analyze the complexity of the simplified test suite."""
    print("\n=== Test Complexity Analysis ===")

    simplified_files = [
        "test_web_interface.py",
        "test_responsive_design.py",
        "test_api_integration.py",
    ]

    total_lines = 0
    for filename in simplified_files:
        file_path = Path(f"tests/browser/{filename}")
        if file_path.exists():
            lines = len(file_path.read_text().splitlines())
            total_lines += lines
            print(f"  - {filename}: {lines} lines")
        else:
            print(f"  - {filename}: Not found")

    print(f"Total simplified test suite: ~{total_lines} lines")

    # Compare to original (based on context)
    original_estimate = 3000  # From the task description
    reduction = ((original_estimate - total_lines) / original_estimate) * 100
    print(f"Reduction from original: ~{reduction:.1f}%")


async def main():
    """Main validation function."""
    print("Browser Test Suite Validation")
    print("=" * 50)

    start_time = time.time()

    # Check dependencies
    deps_ok = check_dependencies()

    # Test components
    if deps_ok:
        server_ok = await test_web_server_startup()
        browser_ok = await test_browser_launch()
    else:
        server_ok = False
        browser_ok = False

    # Analyze test suite
    test_count = count_test_files()
    analyze_test_complexity()

    # Summary
    print("\n=== Validation Summary ===")
    print(f"Dependencies: {'✓ OK' if deps_ok else '✗ FAILED'}")
    print(f"Web Server: {'✓ OK' if server_ok else '✗ FAILED'}")
    print(f"Browser Launch: {'✓ OK' if browser_ok else '✗ FAILED'}")
    print(f"Test Files Found: {test_count}")

    execution_time = time.time() - start_time
    print(f"Validation Time: {execution_time:.2f} seconds")

    # Recommendations
    print("\n=== Recommendations ===")

    if not deps_ok:
        print("- Install missing dependencies with: pip install pyppeteer pytest-asyncio")

    if not server_ok:
        print("- Check web server configuration and port availability")
        print("- Ensure all CalendarBot components are properly installed")

    if not browser_ok:
        print("- Install Chrome/Chromium for pyppeteer")
        print("- Check system resources and permissions")

    if deps_ok and server_ok and browser_ok:
        print("- All infrastructure components are working")
        print("- Browser tests should be ready to run")
        print("- Consider running tests with shorter timeouts: pytest --timeout=30")

    success = deps_ok and server_ok and browser_ok
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nValidation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nValidation failed: {e}")
        sys.exit(1)
