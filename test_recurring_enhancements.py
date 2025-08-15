#!/usr/bin/env python3
"""Test script to validate recurring event enhancements."""

import asyncio
import os
import tempfile

from calendarbot.cache.database import DatabaseManager
from calendarbot.cache.models import RawEvent


async def test_recurring_enhancements():
    """Test the enhanced recurring event storage functionality."""
    print("🧪 Testing Enhanced Recurring Event Storage")
    print("=" * 50)

    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    try:
        # Initialize database manager
        db_manager = DatabaseManager(Path(temp_db_path))
        await db_manager.initialize()

        print("✅ Database initialized with new schema")

        # Test 1: Create master recurring pattern
        master_raw_event = RawEvent.create_from_ics(
            graph_id="recurring-meeting-master",
            subject="Weekly Team Meeting",
            start_datetime="2025-08-22T15:00:00",
            end_datetime="2025-08-22T16:00:00",
            start_timezone="Pacific Standard Time",
            end_timezone="Pacific Standard Time",
            ics_content="BEGIN:VEVENT\nUID:weekly-meeting\nSUMMARY:Weekly Team Meeting\nDTSTART;TZID=Pacific Standard Time:20250822T150000\nRRULE:FREQ=WEEKLY\nEND:VEVENT",
            is_recurring=True,
            is_instance=False,  # This is the master pattern
            recurrence_id=None,  # No recurrence ID for master
        )

        # Test 2: Create first instance (August 11th)
        instance1_raw_event = RawEvent.create_from_ics(
            graph_id="recurring-meeting-instance-1",
            subject="Weekly Team Meeting",
            start_datetime="2025-08-11T15:00:00",
            end_datetime="2025-08-11T16:00:00",
            start_timezone="Pacific Standard Time",
            end_timezone="Pacific Standard Time",
            ics_content="BEGIN:VEVENT\nUID:weekly-meeting\nSUMMARY:Weekly Team Meeting\nDTSTART;TZID=Pacific Standard Time:20250811T150000\nRECURRENCE-ID;TZID=Pacific Standard Time:20250811T150000\nEND:VEVENT",
            is_recurring=False,
            is_instance=True,  # This is an instance
            recurrence_id="20250811T150000",  # Original occurrence time
        )

        # Test 3: Create second instance (August 16th)
        instance2_raw_event = RawEvent.create_from_ics(
            graph_id="recurring-meeting-instance-2",
            subject="Weekly Team Meeting",
            start_datetime="2025-08-16T15:00:00",
            end_datetime="2025-08-16T16:00:00",
            start_timezone="Pacific Standard Time",
            end_timezone="Pacific Standard Time",
            ics_content="BEGIN:VEVENT\nUID:weekly-meeting\nSUMMARY:Weekly Team Meeting\nDTSTART;TZID=Pacific Standard Time:20250816T150000\nRECURRENCE-ID;TZID=Pacific Standard Time:20250816T150000\nEND:VEVENT",
            is_recurring=False,
            is_instance=True,  # This is an instance
            recurrence_id="20250816T150000",  # Original occurrence time
        )

        # Store all raw events
        raw_events = [master_raw_event, instance1_raw_event, instance2_raw_event]
        success = await db_manager.store_raw_events(raw_events)

        if success:
            print("✅ Successfully stored master pattern + 2 instances")

            # Query the database to verify structure
            print("\n📊 Querying enhanced raw_events data:")

            import aiosqlite

            async with aiosqlite.connect(temp_db_path) as db:
                # Check master patterns
                cursor = await db.execute("""
                    SELECT id, graph_id, subject, start_datetime, is_instance, recurrence_id, substr(raw_ics_content, 1, 100) as ics_preview
                    FROM raw_events 
                    WHERE is_instance = 0
                """)
                masters = await cursor.fetchall()

                print(f"\n🔧 Master Patterns ({len(masters)}):")
                for master in masters:
                    print(f"   ID: {master[0]}")
                    print(f"   Graph ID: {master[1]}")
                    print(f"   Subject: {master[2]}")
                    print(f"   Start: {master[3]}")
                    print(f"   Is Instance: {master[4]}")
                    print(f"   Recurrence ID: {master[5]}")
                    print(f"   ICS Preview: {master[6]}...")
                    print()

                # Check instances
                cursor = await db.execute("""
                    SELECT id, graph_id, subject, start_datetime, is_instance, recurrence_id, substr(raw_ics_content, 1, 100) as ics_preview
                    FROM raw_events 
                    WHERE is_instance = 1
                    ORDER BY start_datetime
                """)
                instances = await cursor.fetchall()

                print(f"📅 Recurrence Instances ({len(instances)}):")
                for instance in instances:
                    print(f"   ID: {instance[0]}")
                    print(f"   Graph ID: {instance[1]}")
                    print(f"   Subject: {instance[2]}")
                    print(f"   Start: {instance[3]}")
                    print(f"   Is Instance: {instance[4]}")
                    print(f"   Recurrence ID: {instance[5]}")
                    print(f"   ICS Preview: {instance[6]}...")
                    print()

                # Test queries that solve the original issue
                print("🔍 Debug Queries:")

                # Find all instances of the same recurring series
                cursor = await db.execute("""
                    SELECT COUNT(*) as total_records, 
                           COUNT(CASE WHEN is_instance = 1 THEN 1 END) as instances,
                           COUNT(CASE WHEN is_instance = 0 THEN 1 END) as masters
                    FROM raw_events
                """)
                counts = await cursor.fetchone()
                print(
                    f"   Total Records: {counts[0]} (instances: {counts[1]}, masters: {counts[2]})"
                )

                # Find specific recurrence instance
                cursor = await db.execute("""
                    SELECT id, start_datetime, recurrence_id 
                    FROM raw_events 
                    WHERE recurrence_id = '20250811T150000'
                """)
                aug11_instance = await cursor.fetchone()
                if aug11_instance:
                    print(f"   August 11th instance: {aug11_instance[0]} -> {aug11_instance[1]}")

                cursor = await db.execute("""
                    SELECT id, start_datetime, recurrence_id 
                    FROM raw_events 
                    WHERE recurrence_id = '20250816T150000'
                """)
                aug16_instance = await cursor.fetchone()
                if aug16_instance:
                    print(f"   August 16th instance: {aug16_instance[0]} -> {aug16_instance[1]}")

        else:
            print("❌ Failed to store raw events")

        print("\n" + "=" * 50)
        print("✨ Enhanced Recurring Event Storage Test Complete!")
        print("\n🎯 Benefits:")
        print("   - Master patterns AND individual instances stored separately")
        print("   - RECURRENCE-ID captured for precise instance identification")
        print("   - Individual VEVENT ICS content preserved for each")
        print("   - Complete debugging visibility into recurring event expansion")

    finally:
        # Clean up
        try:
            os.unlink(temp_db_path)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_recurring_enhancements())
