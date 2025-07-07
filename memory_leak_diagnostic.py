#!/usr/bin/env python3
"""
Memory leak diagnostic script for browser automation tests.
This script helps identify the source of memory leaks in browser tests.
"""

import asyncio
import gc
import os
import sys
import time
from pathlib import Path

import psutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pyppeteer import launch

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False
    print("❌ pyppeteer not available")
    sys.exit(1)


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_chrome_processes():
    """Count Chrome processes currently running."""
    chrome_count = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] and "chrome" in proc.info["name"].lower():
                chrome_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return chrome_count


async def test_single_browser_lifecycle():
    """Test memory usage of a single browser lifecycle."""
    print("\n🧪 Testing single browser lifecycle...")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"Initial memory: {initial_memory:.1f} MB")
    print(f"Initial Chrome processes: {initial_chrome}")

    # Launch browser
    browser = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-gpu",
        ],
        options={"ignoreHTTPSErrors": True},
    )

    after_launch_memory = get_memory_usage()
    after_launch_chrome = get_chrome_processes()

    print(
        f"After launch memory: {after_launch_memory:.1f} MB (+{after_launch_memory - initial_memory:.1f})"
    )
    print(
        f"After launch Chrome processes: {after_launch_chrome} (+{after_launch_chrome - initial_chrome})"
    )

    # Create page
    page = await browser.newPage()
    await page.goto("about:blank")

    after_page_memory = get_memory_usage()
    print(
        f"After page creation: {after_page_memory:.1f} MB (+{after_page_memory - initial_memory:.1f})"
    )

    # Close browser
    await browser.close()

    # Wait a bit for cleanup
    await asyncio.sleep(2)
    gc.collect()

    after_close_memory = get_memory_usage()
    after_close_chrome = get_chrome_processes()

    print(
        f"After close memory: {after_close_memory:.1f} MB (+{after_close_memory - initial_memory:.1f})"
    )
    print(
        f"After close Chrome processes: {after_close_chrome} (+{after_close_chrome - initial_chrome})"
    )

    return {
        "memory_leak": after_close_memory - initial_memory,
        "chrome_leak": after_close_chrome - initial_chrome,
    }


async def test_multiple_browser_lifecycles(count=3):
    """Test memory usage of multiple browser lifecycles."""
    print(f"\n🧪 Testing {count} sequential browser lifecycles...")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"Initial memory: {initial_memory:.1f} MB")
    print(f"Initial Chrome processes: {initial_chrome}")

    results = []

    for i in range(count):
        print(f"\n--- Browser lifecycle {i+1}/{count} ---")

        # Launch browser
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
            ],
            options={"ignoreHTTPSErrors": True},
        )

        # Create page
        page = await browser.newPage()
        await page.goto("about:blank")

        current_memory = get_memory_usage()
        current_chrome = get_chrome_processes()

        print(f"  Memory: {current_memory:.1f} MB (+{current_memory - initial_memory:.1f})")
        print(f"  Chrome processes: {current_chrome} (+{current_chrome - initial_chrome})")

        # Close browser
        await browser.close()

        # Wait for cleanup
        await asyncio.sleep(1)
        gc.collect()

        final_memory = get_memory_usage()
        final_chrome = get_chrome_processes()

        results.append(
            {
                "iteration": i + 1,
                "memory_after_close": final_memory - initial_memory,
                "chrome_after_close": final_chrome - initial_chrome,
            }
        )

        print(f"  After close memory: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f})")
        print(f"  After close Chrome processes: {final_chrome} (+{final_chrome - initial_chrome})")

    return results


async def simulate_test_pattern():
    """Simulate the pattern used in test_integrated_browser_validation.py."""
    print("\n🧪 Simulating current test pattern...")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"Initial memory: {initial_memory:.1f} MB")
    print(f"Initial Chrome processes: {initial_chrome}")

    # Simulate the pattern from test_integrated_browser_validation_suite
    # which runs 3 tests sequentially, each creating its own browser

    for test_name in ["browser_core", "navigation", "calendar_display"]:
        print(f"\n--- Simulating {test_name} test ---")

        # Each test calls asyncio.run() which creates a new event loop
        # and launches a browser inside _test_browser_core_functionality

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

            current_memory = get_memory_usage()
            current_chrome = get_chrome_processes()

            print(
                f"  During test - Memory: {current_memory:.1f} MB (+{current_memory - initial_memory:.1f})"
            )
            print(
                f"  During test - Chrome processes: {current_chrome} (+{current_chrome - initial_chrome})"
            )

        finally:
            await browser.close()

        await asyncio.sleep(0.5)  # Brief cleanup time

        after_memory = get_memory_usage()
        after_chrome = get_chrome_processes()

        print(
            f"  After test - Memory: {after_memory:.1f} MB (+{after_memory - initial_memory:.1f})"
        )
        print(f"  After test - Chrome processes: {after_chrome} (+{after_chrome - initial_chrome})")

    # Final cleanup
    gc.collect()
    await asyncio.sleep(2)

    final_memory = get_memory_usage()
    final_chrome = get_chrome_processes()

    print(f"\n📊 Final Results:")
    print(f"Total memory increase: {final_memory - initial_memory:.1f} MB")
    print(f"Chrome processes leaked: {final_chrome - initial_chrome}")

    return {
        "total_memory_leak": final_memory - initial_memory,
        "total_chrome_leak": final_chrome - initial_chrome,
    }


async def main():
    """Run memory leak diagnostics."""
    print("🔍 Browser Memory Leak Diagnostic")
    print("=" * 50)

    # Test 1: Single browser lifecycle
    single_result = await test_single_browser_lifecycle()

    # Test 2: Multiple browser lifecycles
    multiple_results = await test_multiple_browser_lifecycles(3)

    # Test 3: Simulate actual test pattern
    test_pattern_result = await simulate_test_pattern()

    # Summary
    print("\n📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    print(f"Single browser memory leak: {single_result['memory_leak']:.1f} MB")
    print(f"Single browser Chrome leak: {single_result['chrome_leak']} processes")

    print(f"\nMultiple browsers final leak: {multiple_results[-1]['memory_after_close']:.1f} MB")
    print(f"Multiple browsers Chrome leak: {multiple_results[-1]['chrome_after_close']} processes")

    print(f"\nTest pattern total leak: {test_pattern_result['total_memory_leak']:.1f} MB")
    print(f"Test pattern Chrome leak: {test_pattern_result['total_chrome_leak']} processes")

    # Analysis
    print("\n🔍 ANALYSIS")
    print("=" * 50)

    if single_result["memory_leak"] > 50:
        print("❌ Significant memory leak detected in single browser lifecycle")
    if single_result["chrome_leak"] > 0:
        print("❌ Chrome processes not properly cleaned up")
    if multiple_results[-1]["memory_after_close"] > single_result["memory_leak"] * 2:
        print("❌ Memory leak accumulates across multiple browser instances")
    if test_pattern_result["total_memory_leak"] > 200:
        print("❌ Test pattern creates excessive memory usage")

    return {
        "single": single_result,
        "multiple": multiple_results,
        "test_pattern": test_pattern_result,
    }


if __name__ == "__main__":
    if not PYPPETEER_AVAILABLE:
        print("❌ pyppeteer not available")
        sys.exit(1)

    result = asyncio.run(main())
    print(f"\n✅ Diagnostic complete. Results: {result}")
