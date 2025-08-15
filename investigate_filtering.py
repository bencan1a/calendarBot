#!/usr/bin/env python3
"""Deep dive investigation into filtering and recurrence_id bug."""

import asyncio
import re
from datetime import datetime
from pathlib import Path

import aiosqlite


async def investigate_filtering():
    """Investigate filtering logic and recurrence_id bug."""

    db_path = Path.home() / ".local" / "share" / "calendarbot" / "calendar_cache.db"

    print("🔬 Deep Dive: Filtering Logic & Recurrence ID Bug Investigation")
    print("=" * 75)

    async with aiosqlite.connect(db_path) as db:
        # 1. Examine the recurrence_id bug more closely
        print("\n🐛 RECURRENCE ID BUG ANALYSIS:")
        print("-" * 50)
        cursor = await db.execute("""
            SELECT 
                id,
                graph_id,
                recurrence_id,
                substr(raw_ics_content, 1, 1500) as ics_content
            FROM raw_events 
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
              AND is_instance = 1
            ORDER BY start_datetime
        """)
        instances = await cursor.fetchall()

        for idx, instance in enumerate(instances, 1):
            print(f"\n{idx}. Instance: {instance[0]}")
            print(f"   Graph ID: {instance[1]}")
            print(f"   Recurrence ID (BUGGY): {instance[2]}")

            # Parse the ICS content to find the actual RECURRENCE-ID
            ics_content = instance[3]
            recurrence_id_match = re.search(r"RECURRENCE-ID[^:]*:([^\r\n]+)", ics_content)
            if recurrence_id_match:
                print(f"   Actual RECURRENCE-ID: {recurrence_id_match.group(1)}")
            else:
                print("   ❌ No RECURRENCE-ID found in ICS content")

            # Look for DTSTART to understand the actual instance time
            dtstart_match = re.search(r"DTSTART[^:]*:([^\r\n]+)", ics_content)
            if dtstart_match:
                print(f"   DTSTART: {dtstart_match.group(1)}")

        # 2. Examine master patterns with RRULE
        print("\n\n📅 MASTER PATTERN RRULE ANALYSIS:")
        print("-" * 50)
        cursor = await db.execute("""
            SELECT 
                id,
                graph_id,
                start_datetime,
                substr(raw_ics_content, 1, 2000) as ics_content
            FROM raw_events 
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
              AND is_instance = 0
              AND raw_ics_content LIKE '%RRULE%'
            ORDER BY start_datetime
        """)
        masters = await cursor.fetchall()

        for idx, master in enumerate(masters, 1):
            print(f"\n{idx}. Master Pattern: {master[0]}")
            print(f"   Graph ID: {master[1]}")
            print(f"   Start: {master[2]}")

            ics_content = master[3]

            # Extract RRULE
            rrule_match = re.search(r"RRULE:([^\r\n]+)", ics_content)
            if rrule_match:
                print(f"   RRULE: {rrule_match.group(1)}")

            # Extract DTSTART
            dtstart_match = re.search(r"DTSTART[^:]*:([^\r\n]+)", ics_content)
            if dtstart_match:
                print(f"   DTSTART: {dtstart_match.group(1)}")

            # Extract UNTIL if present
            until_match = re.search(r"UNTIL=([^;^\r^\n]+)", ics_content)
            if until_match:
                print(f"   UNTIL: {until_match.group(1)}")

            # Check for any EXDATE (excluded dates)
            exdate_matches = re.findall(r"EXDATE[^:]*:([^\r\n]+)", ics_content)
            if exdate_matches:
                print(f"   EXDATES: {exdate_matches}")

        # 3. Check what's happening during the cache process
        print("\n\n🔄 CACHE FILTERING INVESTIGATION:")
        print("-" * 50)

        # Compare graph_ids between raw and cached
        cursor = await db.execute("""
            SELECT 
                r.graph_id as raw_graph_id,
                r.start_datetime as raw_start,
                c.graph_id as cached_graph_id,
                c.start_datetime as cached_start,
                CASE 
                    WHEN c.graph_id IS NULL THEN 'MISSING_FROM_CACHED'
                    WHEN r.start_datetime != c.start_datetime THEN 'DIFFERENT_START_TIME'
                    ELSE 'MATCHED'
                END as status
            FROM raw_events r
            LEFT JOIN cached_events c ON r.graph_id = c.graph_id
            WHERE r.subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
            ORDER BY r.start_datetime
        """)
        comparisons = await cursor.fetchall()

        missing_count = 0
        time_diff_count = 0
        matched_count = 0

        for comp in comparisons:
            status = comp[4]
            if status == "MISSING_FROM_CACHED":
                missing_count += 1
                raw_start = datetime.fromisoformat(comp[1])
                print(f"   ❌ MISSING: {comp[0][:20]}... ({raw_start.strftime('%Y-%m-%d %H:%M')})")
            elif status == "DIFFERENT_START_TIME":
                time_diff_count += 1
                raw_start = datetime.fromisoformat(comp[1])
                cached_start = datetime.fromisoformat(comp[3])
                print(
                    f"   ⚠️  TIME DIFF: {comp[0][:20]}... Raw: {raw_start.strftime('%Y-%m-%d %H:%M')} vs Cached: {cached_start.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                matched_count += 1

        print(
            f"\n   Summary: {matched_count} matched, {time_diff_count} time differences, {missing_count} missing from cached"
        )

        # 4. Check for any bi-weekly patterns that would include August 18
        print("\n\n📊 BI-WEEKLY PATTERN CALCULATION:")
        print("-" * 50)

        # Get the earliest start date from masters
        cursor = await db.execute("""
            SELECT start_datetime, raw_ics_content
            FROM raw_events 
            WHERE subject LIKE '%Ani%Ben%1:1%Bi Weekly%'
              AND is_instance = 0
            ORDER BY start_datetime
            LIMIT 1
        """)
        earliest_master = await cursor.fetchone()

        if earliest_master:
            start_dt = datetime.fromisoformat(earliest_master[0])
            print(
                f"   Earliest master start: {start_dt.strftime('%Y-%m-%d %H:%M')} ({start_dt.strftime('%A')})"
            )

            # Calculate bi-weekly occurrences
            from datetime import timedelta

            current = start_dt
            target_date = datetime(2025, 8, 18)

            print(f"   Checking if bi-weekly pattern reaches {target_date.strftime('%Y-%m-%d')}:")

            count = 0
            while current <= target_date and count < 50:  # Safety limit
                if current.date() == target_date.date():
                    print(
                        f"   ✅ MATCH FOUND: {current.strftime('%Y-%m-%d %H:%M')} ({current.strftime('%A')})"
                    )
                    break
                if abs((current.date() - target_date.date()).days) <= 1:
                    print(
                        f"   📅 Close match: {current.strftime('%Y-%m-%d %H:%M')} ({current.strftime('%A')})"
                    )

                current += timedelta(weeks=2)  # Bi-weekly = every 2 weeks
                count += 1
            else:
                print(
                    f"   ❌ No bi-weekly occurrence found for August 18th after checking {count} iterations"
                )

        # 5. Search for any August 18 events in ALL tables to understand where they're going
        print("\n\n🔍 COMPREHENSIVE AUGUST 18TH SEARCH:")
        print("-" * 50)

        # Check if August 18 events exist with different subjects
        cursor = await db.execute("""
            SELECT subject, start_datetime, graph_id
            FROM cached_events 
            WHERE date(start_datetime) = '2025-08-18'
              AND (subject LIKE '%Ani%' OR subject LIKE '%Ben%' OR subject LIKE '%1:1%')
        """)
        aug18_related = await cursor.fetchall()

        if aug18_related:
            print(f"   Found {len(aug18_related)} related events on August 18th:")
            for event in aug18_related:
                start_dt = datetime.fromisoformat(event[1])
                print(f"   - {event[0]} at {start_dt.strftime('%H:%M')}")
        else:
            print("   ❌ No Ani/Ben related events found on August 18th")


if __name__ == "__main__":
    asyncio.run(investigate_filtering())
