#!/usr/bin/env python3
"""
Test script to validate parallel execution memory amplification theory.
"""

import asyncio
import concurrent.futures
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
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "chrome" in proc.info["name"].lower():
                chrome_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return chrome_count


async def single_browser_test(test_id):
    """Simulate a single browser test (like what pytest would run)."""
    print(f"Starting browser test {test_id}")

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
        await asyncio.sleep(2)

        memory = get_memory_usage()
        chrome_count = get_chrome_processes()

        print(f"Test {test_id} - Memory: {memory:.1f} MB, Chrome processes: {chrome_count}")

        return {"test_id": test_id, "memory": memory, "chrome_count": chrome_count}

    finally:
        await browser.close()
        print(f"Closed browser for test {test_id}")


async def test_sequential_execution(num_tests=4):
    """Test sequential browser test execution."""
    print(f"\n🔄 Testing {num_tests} sequential browser tests...")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"Initial: {initial_memory:.1f} MB, {initial_chrome} Chrome processes")

    results = []
    for i in range(num_tests):
        result = await single_browser_test(i + 1)
        results.append(result)

        # Brief cleanup time
        await asyncio.sleep(1)

    # Final cleanup
    await asyncio.sleep(2)

    final_memory = get_memory_usage()
    final_chrome = get_chrome_processes()

    print(
        f"Final: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f}), {final_chrome} Chrome processes (+{final_chrome - initial_chrome})"
    )

    return {
        "type": "sequential",
        "memory_increase": final_memory - initial_memory,
        "chrome_increase": final_chrome - initial_chrome,
        "results": results,
    }


async def test_parallel_execution(num_tests=4):
    """Test parallel browser test execution (simulating pytest -n auto)."""
    print(f"\n⚡ Testing {num_tests} parallel browser tests...")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"Initial: {initial_memory:.1f} MB, {initial_chrome} Chrome processes")

    # Run all tests concurrently (like pytest -n auto would)
    tasks = [single_browser_test(i + 1) for i in range(num_tests)]
    results = await asyncio.gather(*tasks)

    # Brief cleanup time
    await asyncio.sleep(2)

    final_memory = get_memory_usage()
    final_chrome = get_chrome_processes()

    print(
        f"Final: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f}), {final_chrome} Chrome processes (+{final_chrome - initial_chrome})"
    )

    return {
        "type": "parallel",
        "memory_increase": final_memory - initial_memory,
        "chrome_increase": final_chrome - initial_chrome,
        "results": results,
    }


async def test_mixed_execution_pattern():
    """Test the mixed pattern from the actual test suite."""
    print(f"\n🔀 Testing mixed execution pattern (test_integrated_browser_validation_suite)...")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"Initial: {initial_memory:.1f} MB, {initial_chrome} Chrome processes")

    # This simulates test_integrated_browser_validation_suite which runs 3 tests sequentially
    # but each test creates its own browser instance

    test_results = []

    for test_name in ["browser_core", "navigation", "calendar_display"]:
        print(f"\n--- Running {test_name} test ---")

        # Each test creates its own browser (as in the current implementation)
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
            await asyncio.sleep(1)

            during_memory = get_memory_usage()
            during_chrome = get_chrome_processes()

            print(f"  During {test_name}: {during_memory:.1f} MB, {during_chrome} Chrome processes")

        finally:
            await browser.close()

        # Brief wait between tests
        await asyncio.sleep(0.5)

        after_memory = get_memory_usage()
        after_chrome = get_chrome_processes()

        print(f"  After {test_name}: {after_memory:.1f} MB, {after_chrome} Chrome processes")

        test_results.append(
            {
                "test": test_name,
                "memory_after": after_memory - initial_memory,
                "chrome_after": after_chrome - initial_chrome,
            }
        )

    # Final cleanup
    await asyncio.sleep(2)

    final_memory = get_memory_usage()
    final_chrome = get_chrome_processes()

    print(
        f"Final: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f}), {final_chrome} Chrome processes (+{final_chrome - initial_chrome})"
    )

    return {
        "type": "mixed",
        "memory_increase": final_memory - initial_memory,
        "chrome_increase": final_chrome - initial_chrome,
        "test_results": test_results,
    }


async def main():
    """Run parallel execution tests."""
    print("🔍 Parallel Execution Memory Impact Test")
    print("=" * 60)

    # Test 1: Sequential execution
    sequential_result = await test_sequential_execution(4)

    # Wait for cleanup
    await asyncio.sleep(3)

    # Test 2: Parallel execution
    parallel_result = await test_parallel_execution(4)

    # Wait for cleanup
    await asyncio.sleep(3)

    # Test 3: Mixed pattern (actual test suite)
    mixed_result = await test_mixed_execution_pattern()

    # Summary
    print("\n📊 EXECUTION PATTERN COMPARISON")
    print("=" * 60)
    print(
        f"Sequential execution - Memory: {sequential_result['memory_increase']:.1f} MB, Chrome: {sequential_result['chrome_increase']}"
    )
    print(
        f"Parallel execution   - Memory: {parallel_result['memory_increase']:.1f} MB, Chrome: {parallel_result['chrome_increase']}"
    )
    print(
        f"Mixed pattern       - Memory: {mixed_result['memory_increase']:.1f} MB, Chrome: {mixed_result['chrome_increase']}"
    )

    # Analysis
    print("\n🔍 ANALYSIS")
    print("=" * 60)

    if parallel_result["memory_increase"] > sequential_result["memory_increase"] * 1.5:
        print("❌ PARALLEL EXECUTION SIGNIFICANTLY AMPLIFIES MEMORY USAGE")
        print(
            f"   Parallel uses {parallel_result['memory_increase'] / sequential_result['memory_increase']:.1f}x more memory than sequential"
        )

    if parallel_result["chrome_increase"] > sequential_result["chrome_increase"]:
        print("❌ PARALLEL EXECUTION LEAVES MORE CHROME PROCESSES")

    if mixed_result["memory_increase"] > 300:  # 300MB threshold
        print("❌ CURRENT TEST PATTERN USES EXCESSIVE MEMORY")

    return {"sequential": sequential_result, "parallel": parallel_result, "mixed": mixed_result}


if __name__ == "__main__":
    if not PYPPETEER_AVAILABLE:
        print("❌ pyppeteer not available")
        sys.exit(1)

    result = asyncio.run(main())
    print(f"\n✅ Parallel execution test complete.")
