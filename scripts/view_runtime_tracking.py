#!/usr/bin/env python3
"""View CalendarBot runtime tracking data."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3


def format_memory(mb: float) -> str:
    """Format memory in human-readable format."""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.1f} MB"


def view_runtime_tracking_data(hours: int = 24) -> None:
    """
    View runtime tracking data from the database.

    Args:
        hours: Number of hours to look back
    """
    print(f"\n🔍 CalendarBot Runtime Tracking Data (Last {hours} hours)")
    print("=" * 70)

    # Connect directly to database for more flexibility
    db_path = Path.home() / ".local/share/calendarbot/benchmarking/benchmark_results.db"

    if not db_path.exists():
        print("❌ No benchmark database found")
        print(f"Expected at: {db_path}")
        return

    conn = sqlite3.connect(db_path)

    # Look for entries with resource_stats in metadata
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    cursor = conn.execute(
        """
        SELECT benchmark_name, category, timestamp, metadata, mean_value
        FROM benchmark_results
        WHERE metadata LIKE '%resource_stats%'
        AND timestamp > ?
        ORDER BY timestamp DESC
        LIMIT 50
    """,
        [cutoff],
    )

    entries = cursor.fetchall()

    if not entries:
        print(f"❌ No runtime tracking entries found in the last {hours} hours")
        print("\n💡 To generate runtime tracking data, run:")
        print("   calendarbot --track-runtime --web --port 8080")
        print("   (Let it run for a few seconds, then close with Ctrl+C)")
        return

    print(f"📊 Found {len(entries)} runtime tracking entries:")
    print()

    for name, category, timestamp, metadata_json, _mean_value in entries:
        try:
            # Parse timestamp for readable format
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = dt.strftime("%m-%d %H:%M:%S")

            print(f"🕒 {time_str} | {name} ({category})")

            if metadata_json:
                metadata = json.loads(metadata_json)

                # Show session info if available
                session_name = metadata.get("session_name", "N/A")
                print(f"   📋 Session: {session_name}")

                if "resource_stats" in metadata:
                    rs = metadata["resource_stats"]

                    # Core metrics
                    duration = rs.get("duration_seconds", 0)
                    cpu_max = rs.get("cpu_percent_max", 0)
                    cpu_median = rs.get("cpu_percent_median", 0)
                    mem_max_mb = rs.get("memory_rss_mb_max", 0)
                    mem_median_mb = rs.get("memory_rss_mb_median", 0)
                    sample_count = rs.get("sample_count", 0)

                    print(f"   ⏱️  Duration: {duration:.1f}s")
                    print(f"   🖥️  CPU: {cpu_median:.1f}% median, {cpu_max:.1f}% max")
                    print(
                        f"   💾 Memory: {format_memory(mem_median_mb)} median, {format_memory(mem_max_mb)} max"
                    )
                    print(f"   📈 Samples: {sample_count}")
                else:
                    print("   ⚠️  No resource stats found in metadata")

            print()

        except Exception as e:
            print(f"   ❌ Error parsing entry: {e}")
            print()

    # Summary statistics
    print("\n📈 Summary Statistics")
    print("-" * 30)

    total_entries = len(entries)

    # Calculate averages for entries with resource_stats
    durations = []
    cpu_medians = []
    cpu_maxes = []
    mem_medians = []
    mem_maxes = []
    sample_counts = []

    for _, _, _, metadata_json, _ in entries:
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                if "resource_stats" in metadata:
                    rs = metadata["resource_stats"]
                    durations.append(rs.get("duration_seconds", 0))
                    cpu_medians.append(rs.get("cpu_percent_median", 0))
                    cpu_maxes.append(rs.get("cpu_percent_max", 0))
                    mem_medians.append(rs.get("memory_rss_mb_median", 0))
                    mem_maxes.append(rs.get("memory_rss_mb_max", 0))
                    sample_counts.append(rs.get("sample_count", 0))
            except (json.JSONDecodeError, KeyError):
                continue

    if durations:
        avg_duration = sum(durations) / len(durations)
        avg_cpu_median = sum(cpu_medians) / len(cpu_medians)
        avg_cpu_max = sum(cpu_maxes) / len(cpu_maxes)
        avg_mem_median = sum(mem_medians) / len(mem_medians)
        avg_mem_max = sum(mem_maxes) / len(mem_maxes)
        avg_samples = sum(sample_counts) / len(sample_counts)

        print(f"📊 Entries with resource stats: {len(durations)}/{total_entries}")
        print(f"⏱️  Average duration: {avg_duration:.1f}s")
        print(f"🖥️  Average CPU: {avg_cpu_median:.1f}% median, {avg_cpu_max:.1f}% max")
        print(
            f"💾 Average memory: {format_memory(avg_mem_median)} median, {format_memory(avg_mem_max)} max"
        )
        print(f"📈 Average samples per session: {avg_samples:.1f}")

    conn.close()


def list_all_categories() -> None:
    """List all available categories in the database."""
    print("\n📂 Available Categories in Database")
    print("=" * 40)

    db_path = Path.home() / ".local/share/calendarbot/benchmarking/benchmark_results.db"

    if not db_path.exists():
        print("❌ No benchmark database found")
        return

    conn = sqlite3.connect(db_path)

    # Get all categories with counts
    cursor = conn.execute("""
        SELECT category, COUNT(*) as count
        FROM benchmark_results
        GROUP BY category
        ORDER BY count DESC
    """)

    categories = cursor.fetchall()

    if not categories:
        print("❌ No categories found in database")
        return

    print(f"Found {len(categories)} categories:")
    print()

    for category, count in categories:
        print(f"📁 {category}: {count} entries")

    # Check which categories have resource_stats
    print("\n🔍 Categories with Runtime Tracking Data:")
    print("-" * 45)

    cursor = conn.execute("""
        SELECT category, COUNT(*) as count
        FROM benchmark_results
        WHERE metadata LIKE '%resource_stats%'
        GROUP BY category
        ORDER BY count DESC
    """)

    rt_categories = cursor.fetchall()

    if rt_categories:
        for category, count in rt_categories:
            print(f"📊 {category}: {count} entries with resource_stats")
    else:
        print("❌ No entries with resource_stats found")

    conn.close()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="View CalendarBot runtime tracking data")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument(
        "--categories", "-c", action="store_true", help="List all categories in database"
    )

    args = parser.parse_args()

    try:
        if args.categories:
            list_all_categories()
        else:
            view_runtime_tracking_data(hours=args.hours)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
