#!/usr/bin/env python3
"""Analyze the raw ICS patterns to understand the recurrence rules."""

from datetime import datetime, timedelta


def analyze_ani_ben_patterns():
    """Analyze the Ani <> Ben meeting patterns from raw ICS data."""
    print("🔍 Analyzing Ani <> Ben Meeting Patterns from Raw ICS")
    print("=" * 60)

    # From the raw ICS data, I found two different series:

    # Series 1: bi-weekly Fridays until April 25, 2025
    series1_start = datetime(2025, 4, 25, 11, 30)  # April 25, 2025 11:30
    series1_until = datetime(2025, 4, 25, 18, 30)  # UNTIL=20250425T183000Z
    print("\n📅 Series 1 (Fridays):")
    print(f"   Start: {series1_start.strftime('%Y-%m-%d %H:%M')} ({series1_start.strftime('%A')})")
    print(f"   Until: {series1_until.strftime('%Y-%m-%d %H:%M')}")
    print("   Pattern: FREQ=WEEKLY;INTERVAL=2;BYDAY=FR (bi-weekly Fridays)")

    # Series 2: bi-weekly Mondays until August 3, 2026
    series2_start = datetime(2025, 5, 26, 8, 30)  # May 26, 2025 08:30
    series2_until = datetime(2026, 8, 3, 15, 30)  # UNTIL=20260803T153000Z
    print("\n📅 Series 2 (Mondays):")
    print(f"   Start: {series2_start.strftime('%Y-%m-%d %H:%M')} ({series2_start.strftime('%A')})")
    print(f"   Until: {series2_until.strftime('%Y-%m-%d %H:%M')}")
    print("   Pattern: FREQ=WEEKLY;INTERVAL=2;BYDAY=MO (bi-weekly Mondays)")
    print("   Has EXDATE: 20250623T083000 (June 23, 2025 - excluded)")

    # Check if August 18, 2025 falls on the bi-weekly Monday pattern
    target_date = datetime(2025, 8, 18)
    print(
        f"\n🎯 Target Date Analysis: {target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')})"
    )

    # Series 1 ends before August, so check Series 2
    print("\n⚡ Series 2 Analysis (bi-weekly Mondays):")

    current = series2_start
    occurrence_count = 0
    found_august_18 = False

    print(f"   Calculating bi-weekly Mondays from {series2_start.strftime('%Y-%m-%d')}:")

    while current <= series2_until and occurrence_count < 100:  # Safety limit
        occurrence_count += 1
        date_str = current.strftime("%Y-%m-%d")
        day_name = current.strftime("%A")

        # Check if this is the target date
        if current.date() == target_date.date():
            found_august_18 = True
            print(f"   🎯 MATCH: Occurrence #{occurrence_count}: {date_str} ({day_name}) ✅")
            break
        if abs((current.date() - target_date.date()).days) <= 7:
            print(f"   📅 Close: Occurrence #{occurrence_count}: {date_str} ({day_name})")
        elif occurrence_count <= 10:
            print(f"   📅 Early: Occurrence #{occurrence_count}: {date_str} ({day_name})")

        # Move to next bi-weekly occurrence (every 14 days)
        current += timedelta(weeks=2)

    if found_august_18:
        print("\n✅ CONCLUSION: August 18, 2025 SHOULD be included in the bi-weekly Monday pattern")
        print("   The recurring rule generates this date correctly.")
    else:
        print("\n❌ CONCLUSION: August 18, 2025 does NOT fall on a bi-weekly Monday")
        print(f"   Checked {occurrence_count} occurrences up to {current.strftime('%Y-%m-%d')}")

    # Check what day August 18, 2025 actually is
    print(f"\n📊 August 18, 2025 is a {target_date.strftime('%A')}")
    if target_date.strftime("%A") == "Monday":
        print("   ✅ It IS a Monday, so it should be included in the bi-weekly Monday pattern")
    else:
        print(
            "   ❌ It is NOT a Monday, so it wouldn't be included in the bi-weekly Monday pattern"
        )

    # Also check the excluded date
    excluded_date = datetime(2025, 6, 23, 8, 30)
    print(
        f"\n🚫 Excluded Date: {excluded_date.strftime('%Y-%m-%d %H:%M')} ({excluded_date.strftime('%A')})"
    )
    print("   This date is explicitly excluded with EXDATE")


if __name__ == "__main__":
    analyze_ani_ben_patterns()
