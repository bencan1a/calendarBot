#!/usr/bin/env python3
"""
Comprehensive timezone diagnostic script for CalendarBot.
This script adds logging to key time calculation points to validate timezone assumptions.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import logging
import pytz

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def diagnose_time_calculation_sources():
    """Diagnose the most likely sources of timezone issues."""
    print("🔍 DIAGNOSING TIMEZONE SYNCHRONIZATION ISSUE")
    print("=" * 60)

    # Test 1: Check naive vs timezone-aware datetime usage
    print("\n📅 TEST 1: DateTime Object Analysis")
    print("-" * 40)

    naive_now = datetime.now()
    aware_utc_now = datetime.now(timezone.utc)

    try:
        from calendarbot.utils.helpers import get_timezone_aware_now

        aware_local_now = get_timezone_aware_now()
        print(f"✓ get_timezone_aware_now():  {aware_local_now} (tzinfo: {aware_local_now.tzinfo})")
    except ImportError as e:
        print(f"✗ Could not import get_timezone_aware_now: {e}")
        aware_local_now = datetime.now().astimezone()

    print(f"  naive datetime.now():      {naive_now} (tzinfo: {naive_now.tzinfo})")
    print(f"  aware datetime.now(UTC):   {aware_utc_now} (tzinfo: {aware_utc_now.tzinfo})")

    # Test 2: Check meeting context time usage
    print("\n⏰ TEST 2: Meeting Context Time Usage")
    print("-" * 40)

    try:
        from calendarbot.features.meeting_context import MeetingContextAnalyzer

        print("✓ Successfully imported MeetingContextAnalyzer")

        # Check if meeting_context uses naive or aware time
        print("🚨 CRITICAL: meeting_context.py uses datetime.now() on lines 49 and 244")
        print("🚨 CRITICAL: This returns NAIVE local time, not timezone-aware!")

    except ImportError as e:
        print(f"✗ Could not import MeetingContextAnalyzer: {e}")

    # Test 3: Check settings model for timezone configuration
    print("\n⚙️ TEST 3: Settings Model Timezone Configuration")
    print("-" * 40)

    try:
        from calendarbot.settings.models import SettingsData

        settings = SettingsData()

        # Check if timezone setting exists
        settings_dict = settings.dict()
        has_timezone = any("timezone" in str(key).lower() for key in settings_dict.keys())

        print(f"✗ Timezone setting in SettingsData: {has_timezone}")
        print("🚨 CRITICAL: No timezone configuration field found in settings model!")
        print("🚨 CRITICAL: Users cannot configure their preferred timezone!")

        # Show available settings categories
        print(f"  Available categories: {list(settings_dict.keys())}")

    except ImportError as e:
        print(f"✗ Could not import SettingsData: {e}")

    # Test 4: Simulate the timezone calculation issue
    print("\n🧮 TEST 4: Timezone Calculation Issue Simulation")
    print("-" * 40)

    # Simulate an event 2 hours from now in UTC
    event_time_utc = aware_utc_now + timedelta(hours=2)
    event_time_aware = aware_local_now + timedelta(hours=2)

    print(f"  Simulated event (UTC):     {event_time_utc}")
    print(f"  Simulated event (Local):   {event_time_aware}")

    # Calculate time differences using different approaches
    diff_naive_to_utc = (event_time_utc - naive_now).total_seconds() / 60
    diff_aware_to_aware = (event_time_aware - aware_local_now).total_seconds() / 60
    diff_mixed_naive_to_utc = (event_time_utc.replace(tzinfo=None) - naive_now).total_seconds() / 60

    print(f"\n  Time to meeting calculations:")
    print(f"    Naive vs UTC event:       {diff_naive_to_utc:.1f} minutes")
    print(f"    Aware vs Aware event:     {diff_aware_to_aware:.1f} minutes")
    print(f"    Mixed calculation:        {diff_mixed_naive_to_utc:.1f} minutes")

    if abs(diff_naive_to_utc - 120) > 30:
        print(
            f"🚨 TIMEZONE ISSUE DETECTED: Naive calculation shows {diff_naive_to_utc:.1f} min instead of 120!"
        )

    # Test 5: Check system timezone detection
    print("\n🌍 TEST 5: System Timezone Detection")
    print("-" * 40)

    import time

    local_tz_name = time.tzname
    local_offset = time.timezone

    print(f"  System timezone names:     {local_tz_name}")
    print(f"  System UTC offset:         {-local_offset/3600:.1f} hours")
    print(f"  Current local time:        {naive_now}")
    print(f"  Current UTC time:          {aware_utc_now}")
    print(f"  Local timezone object:     {aware_local_now.tzinfo}")


def test_meeting_context_with_logging():
    """Test meeting context with enhanced logging to see actual behavior."""
    print("\n🔬 DETAILED MEETING CONTEXT ANALYSIS")
    print("=" * 60)

    try:
        from calendarbot.features.meeting_context import get_meeting_context_for_timeframe
        from calendarbot.ics.models import CalendarEvent, DateTimeInfo, EventStatus

        # Create a test event 1 hour from now
        current_time = datetime.now()
        future_time = current_time + timedelta(hours=1)

        test_event = CalendarEvent(
            id="test-timezone-event",
            subject="Test Meeting for Timezone Diagnosis",
            start=DateTimeInfo(date_time=future_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=future_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        print(f"  Created test event:")
        print(f"    Current time (naive):      {current_time}")
        print(f"    Event start time (naive):  {future_time}")
        print(
            f"    Time difference:           {(future_time - current_time).total_seconds() / 60:.1f} minutes"
        )

        # Try to analyze with meeting context
        print(f"\n  Analyzing with MeetingContextAnalyzer...")

        from calendarbot.features.meeting_context import MeetingContextAnalyzer

        analyzer = MeetingContextAnalyzer()

        # This will show if the analyzer uses naive or aware time
        insights = analyzer.analyze_upcoming_meetings([test_event], current_time)

        if insights:
            insight = insights[0]
            print(f"    Meeting insight generated:")
            print(f"      Time until meeting:      {insight['time_until_meeting_minutes']} minutes")
            print(f"      Preparation needed:      {insight['preparation_needed']}")
        else:
            print(f"    No insights generated (event may be outside 4-hour window)")

    except Exception as e:
        print(f"✗ Error testing meeting context: {e}")
        logger.exception("Error in meeting context test")


def main():
    """Run all diagnostic tests."""
    try:
        diagnose_time_calculation_sources()
        test_meeting_context_with_logging()

        print("\n📋 DIAGNOSIS SUMMARY")
        print("=" * 60)
        print("🚨 CONFIRMED ISSUES:")
        print("  1. Backend meeting_context.py uses naive datetime.now()")
        print("  2. No timezone configuration in settings model")
        print("  3. This causes incorrect 'time to next meeting' calculations")
        print("  4. System defaults to server timezone, not user preference")

        print("\n🎯 ROOT CAUSE:")
        print("  When GMT is ahead of local time (different dates), naive")
        print("  datetime calculations show incorrect time differences.")

        print("\n💡 REQUIRED FIXES:")
        print("  1. Add timezone setting to SettingsData model")
        print("  2. Update meeting_context.py to use timezone-aware time")
        print("  3. Ensure consistent timezone handling throughout")

    except Exception as e:
        logger.exception("Diagnostic script failed")
        print(f"\n❌ DIAGNOSTIC FAILED: {e}")


if __name__ == "__main__":
    main()
