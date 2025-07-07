#!/usr/bin/env python3
"""
Minimal test to reproduce the browser memory leak issue.
This demonstrates the current problematic approach vs the fixed approach.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import psutil
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pyppeteer import launch

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False

pytest_plugins = ("pytest_asyncio",)


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_chrome_processes():
    """Count Chrome processes currently running."""
    chrome_count = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "chrome" in proc.info["name"].lower():
                chrome_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return chrome_count


class TestMemoryLeakReproduction:
    """Test class to reproduce and fix memory leak."""

    def test_problematic_approach_single(self):
        """Single test using the current problematic approach (asyncio.run)."""
        print(f"\n🔴 PROBLEMATIC: Testing single browser with asyncio.run")

        initial_memory = get_memory_usage()
        initial_chrome = get_chrome_processes()

        print(f"Initial: {initial_memory:.1f} MB, {initial_chrome} Chrome processes")

        # This is the problematic pattern from current tests
        result = asyncio.run(self._single_browser_test())

        final_memory = get_memory_usage()
        final_chrome = get_chrome_processes()

        print(
            f"Final: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f}), {final_chrome} Chrome processes (+{final_chrome - initial_chrome})"
        )

        assert result

        # Store results for comparison
        self.problematic_memory_increase = final_memory - initial_memory
        self.problematic_chrome_increase = final_chrome - initial_chrome

    async def _single_browser_test(self):
        """Single browser test using current approach."""
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
            ],
            options={"ignoreHTTPSErrors": True, "defaultViewport": {"width": 1280, "height": 720}},
        )

        try:
            page = await browser.newPage()
            await page.goto("about:blank")

            # Simulate test work
            title = await page.title()
            assert title == ""  # about:blank has empty title

            return True

        finally:
            await browser.close()

    def test_problematic_approach_multiple(self):
        """Multiple tests using problematic approach to amplify the leak."""
        print(f"\n🔴 PROBLEMATIC: Testing 3 sequential browsers with asyncio.run")

        initial_memory = get_memory_usage()
        initial_chrome = get_chrome_processes()

        print(f"Initial: {initial_memory:.1f} MB, {initial_chrome} Chrome processes")

        # Run multiple tests each using asyncio.run (current problematic pattern)
        for i in range(3):
            result = asyncio.run(self._single_browser_test())
            assert result

            current_memory = get_memory_usage()
            current_chrome = get_chrome_processes()
            print(
                f"  After test {i+1}: {current_memory:.1f} MB (+{current_memory - initial_memory:.1f}), {current_chrome} Chrome (+{current_chrome - initial_chrome})"
            )

        final_memory = get_memory_usage()
        final_chrome = get_chrome_processes()

        print(
            f"Final: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f}), {final_chrome} Chrome processes (+{final_chrome - initial_chrome})"
        )

        # Store results for comparison
        self.problematic_multiple_memory = final_memory - initial_memory
        self.problematic_multiple_chrome = final_chrome - initial_chrome


# Test using proper async fixtures (the fix)
@pytest.fixture
async def browser_session():
    """Proper async fixture for browser management."""
    print("🟢 FIXED: Creating browser session via async fixture")

    browser = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-gpu",
        ],
        options={"ignoreHTTPSErrors": True, "defaultViewport": {"width": 1280, "height": 720}},
    )

    try:
        yield browser
    finally:
        print("🟢 FIXED: Cleaning up browser session via async fixture")
        await browser.close()


@pytest.fixture
async def browser_page(browser_session):
    """Proper async fixture for page management."""
    page = await browser_session.newPage()

    try:
        yield page
    finally:
        await page.close()


class TestMemoryLeakFixed:
    """Test class using proper async fixtures (the fix)."""

    @pytest.mark.asyncio
    async def test_fixed_approach_single(self, browser_page):
        """Single test using proper async fixtures."""
        print(f"\n🟢 FIXED: Testing single browser with async fixtures")

        initial_memory = get_memory_usage()
        initial_chrome = get_chrome_processes()

        print(f"Initial: {initial_memory:.1f} MB, {initial_chrome} Chrome processes")

        # Use the fixture-provided browser page
        await browser_page.goto("about:blank")

        # Simulate test work
        title = await browser_page.title()
        assert title == ""  # about:blank has empty title

        current_memory = get_memory_usage()
        current_chrome = get_chrome_processes()

        print(
            f"During test: {current_memory:.1f} MB (+{current_memory - initial_memory:.1f}), {current_chrome} Chrome processes (+{current_chrome - initial_chrome})"
        )

        # The cleanup happens automatically via fixture teardown

    @pytest.mark.asyncio
    async def test_fixed_approach_multiple_1(self, browser_page):
        """First of multiple tests using proper async fixtures."""
        print(f"\n🟢 FIXED: Test 1/3 with async fixtures")

        await browser_page.goto("about:blank")
        title = await browser_page.title()
        assert title == ""

        memory = get_memory_usage()
        chrome = get_chrome_processes()
        print(f"  Test 1 memory: {memory:.1f} MB, Chrome: {chrome}")

    @pytest.mark.asyncio
    async def test_fixed_approach_multiple_2(self, browser_page):
        """Second of multiple tests using proper async fixtures."""
        print(f"\n🟢 FIXED: Test 2/3 with async fixtures")

        await browser_page.goto("about:blank")
        title = await browser_page.title()
        assert title == ""

        memory = get_memory_usage()
        chrome = get_chrome_processes()
        print(f"  Test 2 memory: {memory:.1f} MB, Chrome: {chrome}")

    @pytest.mark.asyncio
    async def test_fixed_approach_multiple_3(self, browser_page):
        """Third of multiple tests using proper async fixtures."""
        print(f"\n🟢 FIXED: Test 3/3 with async fixtures")

        await browser_page.goto("about:blank")
        title = await browser_page.title()
        assert title == ""

        memory = get_memory_usage()
        chrome = get_chrome_processes()
        print(f"  Test 3 memory: {memory:.1f} MB, Chrome: {chrome}")


if __name__ == "__main__":
    if not PYPPETEER_AVAILABLE:
        print("❌ pyppeteer not available")
        sys.exit(1)

    # Run tests manually for demonstration
    print("🧪 Running Memory Leak Reproduction Tests")
    print("=" * 60)

    test_instance = TestMemoryLeakReproduction()

    print("\nPhase 1: Demonstrating problematic approach...")
    test_instance.test_problematic_approach_single()
    time.sleep(2)  # Allow cleanup
    test_instance.test_problematic_approach_multiple()

    print(f"\n📊 PROBLEMATIC APPROACH RESULTS:")
    print(f"Single test memory increase: {test_instance.problematic_memory_increase:.1f} MB")
    print(f"Single test Chrome increase: {test_instance.problematic_chrome_increase}")
    print(f"Multiple tests memory increase: {test_instance.problematic_multiple_memory:.1f} MB")
    print(f"Multiple tests Chrome increase: {test_instance.problematic_multiple_chrome}")

    print("\n💡 The fixed approach would be demonstrated via pytest with proper async fixtures")
    print("   Run: python -m pytest test_memory_leak_reproduction.py::TestMemoryLeakFixed -v")
