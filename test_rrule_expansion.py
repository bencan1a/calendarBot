#!/usr/bin/env python3
"""Test RRULE expansion using python-dateutil to verify the solution."""

import sys
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dateutil.parser import parse as parse_date
    from dateutil.rrule import FR, MO, WEEKLY, rrule

    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False


def test_rrule_expansion():
    """Test if client-side RRULE expansion would solve the missing events."""

    print("🧪 Testing Client-Side RRULE Expansion")
    print("=" * 45)

    if not DATEUTIL_AVAILABLE:
        print("❌ python-dateutil not available - cannot test RRULE expansion")
        print("   Install with: pip install python-dateutil")
        return

    # Test Case 1: Ani <> Ben bi-weekly Mondays
    print("\n📅 TEST 1: Ani <> Ben - 1:1- Bi Weekly")
    print("RRULE: FREQ=WEEKLY;UNTIL=20260803T153000Z;INTERVAL=2;BYDAY=MO")

    start_date1 = datetime(2025, 5, 26, 8, 30)  # May 26, 2025 08:30
    until_date1 = datetime(2026, 8, 3, 15, 30)  # August 3, 2026 15:30
    target_aug18 = datetime(2025, 8, 18)

    # Create RRULE for bi-weekly Mondays
    rule1 = rrule(WEEKLY, dtstart=start_date1, until=until_date1, interval=2, byweekday=MO)

    # Generate occurrences and check for August 18
    occurrences1 = list(rule1)
    found_aug18 = False

    print(f"Generated {len(occurrences1)} occurrences:")
    for i, occurrence in enumerate(occurrences1[:15], 1):
        date_str = occurrence.strftime("%Y-%m-%d (%A)")
        if occurrence.date() == target_aug18.date():
            found_aug18 = True
            print(f"  {i:2d}. {date_str} 🎯 TARGET FOUND!")
        elif i <= 10:
            print(f"  {i:2d}. {date_str}")

    print(f"\n✅ August 18, 2025 found in RRULE expansion: {found_aug18}")

    # Test Case 2: Jayson <> Ben weekly Fridays
    print("\n\n📅 TEST 2: Jayson <> Ben - 1:1- Weekly")
    print("RRULE: FREQ=WEEKLY;UNTIL=20260814T180000Z;INTERVAL=1;BYDAY=FR")

    start_date2 = datetime(2025, 6, 6, 11, 0)  # June 6, 2025 11:00
    until_date2 = datetime(2026, 8, 14, 18, 0)  # August 14, 2026 18:00
    target_aug15 = datetime(2025, 8, 15)

    # Create RRULE for weekly Fridays
    rule2 = rrule(WEEKLY, dtstart=start_date2, until=until_date2, interval=1, byweekday=FR)

    # Generate occurrences and check for August 15
    occurrences2 = list(rule2)
    found_aug15 = False

    print(f"Generated {len(occurrences2)} occurrences:")
    for i, occurrence in enumerate(occurrences2[:15], 1):
        date_str = occurrence.strftime("%Y-%m-%d (%A)")
        if occurrence.date() == target_aug15.date():
            found_aug15 = True
            print(f"  {i:2d}. {date_str} 🎯 TARGET FOUND!")
        elif i <= 12:
            print(f"  {i:2d}. {date_str}")

    print(f"\n✅ August 15, 2025 found in RRULE expansion: {found_aug15}")

    # Summary
    print("\n\n🎯 SOLUTION VALIDATION")
    print("=" * 25)

    if found_aug18 and found_aug15:
        print("✅ CLIENT-SIDE RRULE EXPANSION SOLVES THE PROBLEM!")
        print("\n📋 Implementation Steps:")
        print("1. Add python-dateutil dependency to CalendarBot")
        print("2. Modify ICS parser to expand RRULE patterns")
        print("3. Generate individual events for each recurrence")
        print("4. Handle EXDATE exclusions properly")
        print("5. Merge generated events with explicit VEVENTs")
    else:
        print("❌ RRULE expansion doesn't generate expected dates")
        print("   Further investigation needed")

    print("\n🔍 Missing Events Analysis:")
    print(f"   Ani <> Ben Aug 18: {'FOUND' if found_aug18 else 'MISSING'} in RRULE expansion")
    print(f"   Jayson Aug 15: {'FOUND' if found_aug15 else 'MISSING'} in RRULE expansion")


if __name__ == "__main__":
    test_rrule_expansion()
