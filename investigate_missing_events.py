#!/usr/bin/env python3
"""Investigate discrepancies in 'Ani <> Ben- 1:1- Bi Weekly' meeting storage."""

import asyncio
from datetime import datetime
from pathlib import Path

import aiosqlite


async def investigate_meeting():
    """Investigate the missing events and discrepancies."""

    db_path = Path.home() / ".whatsnexter" / "calendarcache.db"

    print("🔍 Investigating 'Ani <> Ben- 1:1- Bi Weekly' Meeting Discrepancies")
    print("=" * 70)

    async with aiosqlite.connect(db_path) as db:
        # 1. Get all raw_events for this meeting
        print("\n📊 RAW EVENTS (7 total):")
        print("-" * 50)
        cursor = await db.execute("""
            SELECT 
                id,
                graph_id,
                subject,
                start_datetime,
                end_datetime,
                is_instance,
                recurrence_id,
                substr(raw_ics_content, 1, 100) as ics_preview
            FROM raw_events 
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
            ORDER BY start_datetime
        """)
        raw_events = await cursor.fetchall()

        for idx, event in enumerate(raw_events, 1):
            start_dt = datetime.fromisoformat(event[3])
            print(f"\n{idx}. Raw Event ID: {event[0]}")
            print(f"   Graph ID: {event[1]}")
            print(f"   Subject: {event[2]}")
            print(f"   Start: {start_dt.strftime('%Y-%m-%d %H:%M')} ({start_dt.strftime('%A')})")
            print(f"   Is Instance: {event[5]}")
            print(f"   Recurrence ID: {event[6]}")

        # 2. Get all cached_events for this meeting
        print("\n\n📊 CACHED EVENTS (3 total):")
        print("-" * 50)
        cursor = await db.execute("""
            SELECT 
                id,
                graph_id,
                subject,
                start_datetime,
                end_datetime,
                is_recurring,
                series_master_id
            FROM cached_events 
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
            ORDER BY start_datetime
        """)
        cached_events = await cursor.fetchall()

        for idx, event in enumerate(cached_events, 1):
            start_dt = datetime.fromisoformat(event[3])
            print(f"\n{idx}. Cached Event ID: {event[0]}")
            print(f"   Graph ID: {event[1]}")
            print(f"   Subject: {event[2]}")
            print(f"   Start: {start_dt.strftime('%Y-%m-%d %H:%M')} ({start_dt.strftime('%A')})")
            print(f"   Is Recurring: {event[5]}")
            print(f"   Series Master ID: {event[6]}")

        # 3. Check for events on August 18th
        print("\n\n🔍 CHECKING AUGUST 18TH:")
        print("-" * 50)

        # Check if ANY events exist on August 18th in raw_events
        cursor = await db.execute("""
            SELECT COUNT(*) 
            FROM raw_events 
            WHERE date(start_datetime) = '2025-08-18'
        """)
        aug18_raw_count = await cursor.fetchone()
        print(f"Total raw events on 2025-08-18: {aug18_raw_count[0]}")

        # Check if ANY events exist on August 18th in cached_events
        cursor = await db.execute("""
            SELECT COUNT(*) 
            FROM cached_events 
            WHERE date(start_datetime) = '2025-08-18'
        """)
        aug18_cached_count = await cursor.fetchone()
        print(f"Total cached events on 2025-08-18: {aug18_cached_count[0]}")

        # List some events on August 18th to confirm other events are there
        print("\nSample events on 2025-08-18:")
        cursor = await db.execute("""
            SELECT subject, start_datetime 
            FROM cached_events 
            WHERE date(start_datetime) = '2025-08-18'
            LIMIT 5
        """)
        aug18_samples = await cursor.fetchall()
        for event in aug18_samples:
            print(f"  - {event[0]} at {event[1]}")

        # 4. Analyze the discrepancy patterns
        print("\n\n📈 DISCREPANCY ANALYSIS:")
        print("-" * 50)

        # Get graph_ids that are in raw but not in cached
        cursor = await db.execute("""
            SELECT DISTINCT r.graph_id, r.start_datetime, r.subject
            FROM raw_events r
            LEFT JOIN cached_events c ON r.graph_id = c.graph_id
            WHERE r.subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
              AND c.graph_id IS NULL
            ORDER BY r.start_datetime
        """)
        missing_in_cached = await cursor.fetchall()

        if missing_in_cached:
            print(
                f"\n⚠️  Found {len(missing_in_cached)} events in raw_events but NOT in cached_events:"
            )
            for event in missing_in_cached:
                start_dt = datetime.fromisoformat(event[1])
                print(f"   - Graph ID: {event[0]}")
                print(
                    f"     Date: {start_dt.strftime('%Y-%m-%d %H:%M')} ({start_dt.strftime('%A')})"
                )

        # 5. Check for any filtering patterns
        print("\n\n🔬 FILTERING ANALYSIS:")
        print("-" * 50)

        # Check if missing events have any common patterns
        cursor = await db.execute("""
            SELECT 
                is_cancelled,
                show_as,
                is_recurring,
                COUNT(*) as count
            FROM raw_events
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
            GROUP BY is_cancelled, show_as, is_recurring
        """)
        patterns = await cursor.fetchall()

        print("Raw events grouped by attributes:")
        for pattern in patterns:
            print(
                f"  is_cancelled={pattern[0]}, show_as={pattern[1]}, is_recurring={pattern[2]}: {pattern[3]} events"
            )

        # 6. Look for the specific August 18th instance in raw ICS content
        print("\n\n🔎 SEARCHING FOR AUGUST 18TH IN ICS CONTENT:")
        print("-" * 50)

        # Search for any mention of August 18 in raw ICS content
        cursor = await db.execute("""
            SELECT id, subject, substr(raw_ics_content, 1, 500)
            FROM raw_events
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
              AND (raw_ics_content LIKE '%20250818%' 
                   OR raw_ics_content LIKE '%2025-08-18%'
                   OR raw_ics_content LIKE '%August 18%')
        """)
        aug18_mentions = await cursor.fetchall()

        if aug18_mentions:
            print(f"Found {len(aug18_mentions)} mentions of August 18 in ICS content")
            for mention in aug18_mentions:
                print(f"\n  Event: {mention[0]}")
                print(f"  ICS Preview: {mention[2]}...")
        else:
            print("❌ No mentions of August 18 found in raw ICS content")

            # Check if there's an RRULE that would generate Aug 18
            cursor = await db.execute("""
                SELECT id, substr(raw_ics_content, 1, 1000)
                FROM raw_events
                WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
                  AND raw_ics_content LIKE '%RRULE%'
                LIMIT 1
            """)
            rrule_event = await cursor.fetchone()

            if rrule_event:
                print("\n📅 Found RRULE in master pattern:")
                # Extract RRULE from content
                import re

                rrule_match = re.search(r"RRULE:([^\r\n]+)", rrule_event[1])
                if rrule_match:
                    print(f"  RRULE: {rrule_match.group(1)}")

                # Extract DTSTART
                dtstart_match = re.search(r"DTSTART[^:]*:([^\r\n]+)", rrule_event[1])
                if dtstart_match:
                    print(f"  DTSTART: {dtstart_match.group(1)}")

                # Check if the pattern would generate Aug 18
                print("\n  Checking if pattern generates August 18th...")
                # Parse the start date and check bi-weekly pattern
                if (
                    dtstart_match
                    and "FREQ=WEEKLY" in rrule_event[1]
                    and "INTERVAL=2" in rrule_event[1]
                ):
                    # This is a bi-weekly pattern
                    print("  ✓ This is a bi-weekly pattern")
                    print("  ⚠️  August 18th SHOULD be included based on bi-weekly recurrence")


if __name__ == "__main__":
    asyncio.run(investigate_meeting())
