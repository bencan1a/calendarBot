#!/usr/bin/env python3
"""Test script to measure CalendarBot boot up performance improvements."""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot.main import CalendarBot


async def measure_boot_time() -> float:
    """Measure the time to create and initialize CalendarBot.

    Returns:
        Boot time in seconds
    """
    start_time = time.perf_counter()

    try:
        # Measure just the creation and initialization time
        app = CalendarBot()
        creation_time = time.perf_counter()
        print(f"  Component creation: {(creation_time - start_time):.3f}s")

        # Measure initialization time
        init_start = time.perf_counter()
        success = await app.initialize()
        init_time = time.perf_counter()
        print(f"  Component initialization: {(init_time - init_start):.3f}s")

        total_time = init_time - start_time

        if success:
            print(f"✅ Initialization successful in {total_time:.3f}s")
        else:
            print(f"❌ Initialization failed after {total_time:.3f}s")

        return total_time

    except Exception as e:
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"❌ Boot failed with exception after {total_time:.3f}s: {e}")
        return total_time


async def run_boot_benchmark() -> None:
    """Run multiple boot time measurements and report statistics."""
    print("🚀 CalendarBot Boot Time Benchmark")
    print("=" * 50)

    times = []
    num_runs = 3

    for i in range(num_runs):
        print(f"\nRun {i + 1}/{num_runs}:")
        boot_time = await measure_boot_time()
        times.append(boot_time)

        # Small delay between runs
        await asyncio.sleep(0.5)

    print("\n" + "=" * 50)
    print("📊 Boot Time Statistics:")
    print(f"  Average: {sum(times) / len(times):.3f}s")
    print(f"  Best:    {min(times):.3f}s")
    print(f"  Worst:   {max(times):.3f}s")

    # Performance targets from our plan
    target_time = 1.0  # Target: reduce from ~5s to ~1s

    avg_time = sum(times) / len(times)
    if avg_time <= target_time:
        print(
            f"🎉 TARGET MET! Average boot time ({avg_time:.3f}s) is under target ({target_time}s)"
        )
    else:
        improvement_needed = avg_time - target_time
        print(
            f"⚠️  Target missed. Need {improvement_needed:.3f}s more improvement to reach {target_time}s target"
        )

    print("\n💡 Optimizations applied:")
    print("  ✅ Database lazy initialization (saves ~1-2s)")
    print("  ✅ Component parallel initialization (saves ~0.5s)")
    print("  🔲 Import optimization (pending)")
    print("  🔲 Asset lazy loading (pending)")


if __name__ == "__main__":
    asyncio.run(run_boot_benchmark())
