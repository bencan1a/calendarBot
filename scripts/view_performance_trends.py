#!/usr/bin/env python3
"""View CalendarBot performance trends over time."""

import argparse
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calendarbot.benchmarking.models import BenchmarkStatus
from calendarbot.benchmarking.storage import BenchmarkResultStorage


def format_memory(mb: float) -> str:
    """Format memory in human-readable format."""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.1f} MB"


def view_performance_trends(days: int = 7, category: str = "performance_monitoring") -> None:
    """
    View performance trends over time.

    Args:
        days: Number of days to look back
        category: Benchmark category to filter by
    """
    storage = BenchmarkResultStorage()

    print(f"\n🔍 CalendarBot Performance Trends (Last {days} days)")
    print("=" * 60)

    # Get recent results
    results = storage.get_benchmark_results(
        category=category, status=BenchmarkStatus.COMPLETED, limit=200
    )

    if not results:
        print(f"❌ No performance data found for category '{category}'")
        print("\n💡 To generate performance data, run:")
        print("   pytest tests/test_performance_monitoring.py -v -s")
        return

    # Group by benchmark name
    by_benchmark = {}
    for result in results:
        name = result.benchmark_name.replace("perf_", "")  # Clean name
        if name not in by_benchmark:
            by_benchmark[name] = []
        by_benchmark[name].append(result)

    # Display trends
    for benchmark_name, benchmark_results in by_benchmark.items():
        print(f"\n📊 {benchmark_name.replace('_', ' ').title()}")
        print("-" * 40)

        # Sort by timestamp (newest first)
        benchmark_results.sort(key=lambda x: x.timestamp, reverse=True)

        # Show recent results
        for i, result in enumerate(benchmark_results[:5]):
            timestamp = result.timestamp.strftime("%m-%d %H:%M")

            # Extract metrics
            resource_metrics = result.get_metadata("resource_metrics", {})
            memory_mb = resource_metrics.get("current_memory_mb", 0)
            cpu_percent = resource_metrics.get("current_cpu_percent", 0)
            memory_delta = resource_metrics.get("memory_delta_mb", 0)

            # Format output
            execution_ms = result.mean_value * 1000
            memory_str = format_memory(memory_mb)
            delta_str = f"({memory_delta:+.1f} MB)" if memory_delta != 0 else ""

            print(
                f"  {timestamp}: {execution_ms:6.1f}ms | {memory_str:>8} {delta_str:>10} | CPU: {cpu_percent:4.1f}%"
            )

        # Calculate trends
        if len(benchmark_results) >= 2:
            recent_exec = benchmark_results[0].mean_value
            older_exec = benchmark_results[-1].mean_value
            exec_change = ((recent_exec - older_exec) / older_exec) * 100 if older_exec > 0 else 0

            recent_mem = (
                benchmark_results[0]
                .get_metadata("resource_metrics", {})
                .get("current_memory_mb", 0)
            )
            older_mem = (
                benchmark_results[-1]
                .get_metadata("resource_metrics", {})
                .get("current_memory_mb", 0)
            )
            mem_change = ((recent_mem - older_mem) / older_mem) * 100 if older_mem > 0 else 0

            # Trend indicators
            exec_trend = "🔴" if exec_change > 10 else "🟢" if exec_change < -10 else "🟡"
            mem_trend = "🔴" if mem_change > 10 else "🟢" if mem_change < -10 else "🟡"

            print(
                f"  Trends: {exec_trend} Exec {exec_change:+.1f}% | {mem_trend} Memory {mem_change:+.1f}%"
            )


def get_performance_summary() -> None:
    """Get a summary of all performance data."""
    storage = BenchmarkResultStorage()

    print("\n📈 Performance Data Summary")
    print("=" * 40)

    # Get all performance results
    results = storage.get_benchmark_results(category="performance_monitoring", limit=1000)

    if not results:
        print("❌ No performance data found")
        return

    # Calculate summary stats
    total_runs = len(results)
    successful_runs = sum(1 for r in results if r.status == BenchmarkStatus.COMPLETED)
    unique_benchmarks = len(set(r.benchmark_name for r in results))

    # Date range
    timestamps = [r.timestamp for r in results]
    date_range = f"{min(timestamps).strftime('%Y-%m-%d')} to {max(timestamps).strftime('%Y-%m-%d')}"

    print(f"📊 Total benchmark runs: {total_runs}")
    print(f"✅ Successful runs: {successful_runs} ({successful_runs / total_runs * 100:.1f}%)")
    print(f"🎯 Unique benchmarks: {unique_benchmarks}")
    print(f"📅 Date range: {date_range}")

    # Recent performance
    recent_results = [r for r in results if r.status == BenchmarkStatus.COMPLETED][-10:]
    if recent_results:
        avg_exec_time = sum(r.mean_value for r in recent_results) / len(recent_results)

        # Average memory from metadata
        memory_values = []
        for r in recent_results:
            mem = r.get_metadata("resource_metrics", {}).get("current_memory_mb", 0)
            if mem > 0:
                memory_values.append(mem)

        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0

        print("\n🔄 Recent Performance (last 10 runs):")
        print(f"   Average execution: {avg_exec_time * 1000:.1f}ms")
        if avg_memory > 0:
            print(f"   Average memory: {format_memory(avg_memory)}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="View CalendarBot performance trends")
    parser.add_argument("--days", "-d", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument(
        "--category", "-c", default="performance_monitoring", help="Benchmark category"
    )
    parser.add_argument("--summary", "-s", action="store_true", help="Show performance summary")

    args = parser.parse_args()

    try:
        if args.summary:
            get_performance_summary()
        else:
            view_performance_trends(days=args.days, category=args.category)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
