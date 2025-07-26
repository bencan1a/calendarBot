#!/usr/bin/env python3
"""
Debug script to analyze timezone calculation issues.
This script examines the actual time calculations being performed.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from calendarbot.utils.helpers import get_timezone_aware_now
from calendarbot.features.meeting_context import MeetingContextAnalyzer
from calendarbot.sources.manager import SourceManager


async def debug_timezone_calculations():
    """Debug the actual timezone calculations happening in the system."""
    print("=== TIMEZONE CALCULATION DEBUG ===")

    # Get current time in various formats
    system_now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    timezone_aware_now = get_timezone_aware_now()

    print(f"System datetime.now(): {system_now} (naive: {system_now.tzinfo is None})")
    print(f"UTC datetime.now(): {utc_now}")
    print(f"Timezone-aware now: {timezone_aware_now}")

    # Get actual calendar events
    print("\n=== ACTUAL CALENDAR EVENTS ===")
    try:
        source_manager = SourceManager()
        sources = source_manager.get_all_sources()

        if not sources:
            print("No calendar sources configured")
            return

        for source in sources:
            print(f"Source: {source.name}")
            try:
                events = await source.fetch_events()
                print(f"Found {len(events)} events")

                for event in events:
                    event_start = event.start.date_time
                    print(f"\nEvent: {event.subject}")
                    print(f"  Start time: {event_start}")
                    print(f"  Start timezone: {event.start.time_zone}")
                    print(f"  Is timezone-aware: {event_start.tzinfo is not None}")

                    # Calculate time differences using different methods
                    if event_start.tzinfo is None:
                        print("  WARNING: Event has naive datetime!")
                        # Try to make it timezone-aware for comparison
                        event_start_aware = event_start.replace(tzinfo=timezone_aware_now.tzinfo)
                    else:
                        event_start_aware = event_start

                    # Time differences
                    diff_system = event_start_aware - timezone_aware_now
                    hours_diff = diff_system.total_seconds() / 3600

                    print(f"  Time until event: {diff_system}")
                    print(f"  Hours until event: {hours_diff:.2f}")
                    print(f"  Minutes until event: {hours_diff * 60:.2f}")

            except Exception as e:
                print(f"Error fetching events from {source.name}: {e}")

    except Exception as e:
        print(f"Error accessing calendar sources: {e}")

    # Test meeting context analyzer
    print("\n=== MEETING CONTEXT ANALYZER TEST ===")
    try:
        analyzer = MeetingContextAnalyzer()
        source_manager = SourceManager()
        sources = source_manager.get_all_sources()

        all_events = []
        for source in sources:
            try:
                events = await source.fetch_events()
                all_events.extend(events)
            except Exception as e:
                print(f"Error fetching from {source.name}: {e}")

        if all_events:
            insights = analyzer.analyze_upcoming_meetings(all_events)
            print(f"Generated {len(insights)} insights")

            for insight in insights:
                print(f"\nInsight for: {insight['subject']}")
                print(f"  Time until meeting (minutes): {insight['time_until_meeting_minutes']}")
                print(
                    f"  Time until meeting (hours): {insight['time_until_meeting_minutes'] / 60:.2f}"
                )
                print(f"  Preparation needed: {insight['preparation_needed']}")

    except Exception as e:
        print(f"Error in meeting context analysis: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(debug_timezone_calculations())
