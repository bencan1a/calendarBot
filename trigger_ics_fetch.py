#!/usr/bin/env python3
"""Trigger ICS fetch to capture raw content for debugging."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path so we can import calendarbot
sys.path.insert(0, str(Path(__file__).parent))

from calendarbot.sources.manager import SourceManager


async def trigger_fetch():
    """Trigger ICS fetch to capture raw data."""
    print("🔍 Triggering ICS fetch to capture raw content...")

    # Initialize settings
    settings = CalendarBotSettings()

    # Initialize source manager
    source_manager = SourceManager(settings)

    try:
        # Fetch events from all sources
        print("📡 Fetching events from all ICS sources...")
        events = await source_manager.fetch_and_cache_events()

        print(f"✅ Successfully fetched {len(events)} events")

        # Check for raw ICS dump files
        debug_dir = Path.home() / ".local" / "share" / "calendarbot" / "debug_ics"
        if debug_dir.exists():
            ics_files = list(debug_dir.glob("*.ics"))
            if ics_files:
                print("\n🔍 Raw ICS files captured:")
                for ics_file in sorted(ics_files, key=lambda f: f.stat().st_mtime, reverse=True):
                    size = ics_file.stat().st_size
                    print(f"  📄 {ics_file.name} ({size:,} bytes)")

                # Show the most recent file path
                latest_file = max(ics_files, key=lambda f: f.stat().st_mtime)
                print(f"\n📂 Latest raw ICS file: {latest_file}")
            else:
                print("❌ No raw ICS files found in debug directory")
        else:
            print("❌ Debug directory not found")

    except Exception as e:
        print(f"❌ Error during fetch: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(trigger_fetch())
