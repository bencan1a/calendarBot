#!/usr/bin/env python3
"""Manual test to demonstrate in-progress meeting acknowledgment.

Run this script to see how the launch summary responds when:
1. No meeting is in progress
2. A meeting is currently in progress
3. A meeting is in progress with no next meeting
"""

import asyncio
import datetime
from unittest.mock import Mock

from calendarbot_lite.alexa.alexa_handlers import LaunchSummaryHandler
from calendarbot_lite.alexa.alexa_presentation import PlainTextPresenter
from calendarbot_lite.calendar.lite_models import LiteCalendarEvent, LiteDateTimeInfo


async def test_scenario(scenario_name: str, test_time: datetime.datetime, events: list) -> None:
    """Test a specific scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"Current time: {test_time.strftime('%I:%M %p %Z')}")
    print(f"{'='*80}")
    
    # Create handler
    mock_time_provider = Mock(return_value=test_time)
    mock_skipped_store = Mock()
    mock_skipped_store.is_skipped = Mock(return_value=False)
    presenter = PlainTextPresenter()
    
    handler = LaunchSummaryHandler(
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=presenter,
        duration_formatter=lambda s: f"in {s // 60} minutes" if s > 0 else "now",
        iso_serializer=lambda dt: dt.isoformat(),
    )
    
    # Create mock request
    mock_request = Mock()
    mock_request.query = {"tz": "UTC"}
    
    # Call handler
    response = await handler.handle_request(mock_request, tuple(events), test_time)
    
    # Display results
    import json
    data = json.loads(response.body)
    
    print(f"\nEvents in calendar:")
    for ev in events:
        start_time = ev.start.date_time if hasattr(ev.start, 'date_time') else ev.start.date
        end_time = ev.end.date_time if hasattr(ev.end, 'date_time') else ev.end.date
        if isinstance(start_time, datetime.datetime):
            print(f"  - {ev.subject}: {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
        else:
            print(f"  - {ev.subject}: All day event")
    
    print(f"\n📢 Speech Output:")
    print(f"   \"{data['speech_text']}\"")
    
    if data.get("next_meeting"):
        print(f"\n📅 Next Meeting Info:")
        print(f"   Subject: {data['next_meeting']['subject']}")
        print(f"   Seconds until: {data['next_meeting']['seconds_until_start']}")
    
    print()


async def main() -> None:
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("DEMONSTRATION: Launch Summary with In-Progress Meeting Detection")
    print("="*80)
    
    # Base date: 2025-11-05
    base_date = datetime.date(2025, 11, 5)
    
    # Create test events
    morning_meeting = LiteCalendarEvent(
        id="morning-standup",
        subject="Morning Standup",
        start=LiteDateTimeInfo(date_time=datetime.datetime.combine(base_date, datetime.time(10, 0), tzinfo=datetime.timezone.utc)),
        end=LiteDateTimeInfo(date_time=datetime.datetime.combine(base_date, datetime.time(11, 0), tzinfo=datetime.timezone.utc)),
        is_all_day=False,
    )
    
    afternoon_meeting = LiteCalendarEvent(
        id="afternoon-meeting",
        subject="Afternoon Meeting",
        start=LiteDateTimeInfo(date_time=datetime.datetime.combine(base_date, datetime.time(13, 0), tzinfo=datetime.timezone.utc)),
        end=LiteDateTimeInfo(date_time=datetime.datetime.combine(base_date, datetime.time(14, 0), tzinfo=datetime.timezone.utc)),
        is_all_day=False,
    )
    
    # Scenario 1: Before any meetings (9:00 AM)
    await test_scenario(
        "Before any meetings",
        datetime.datetime.combine(base_date, datetime.time(9, 0), tzinfo=datetime.timezone.utc),
        [morning_meeting, afternoon_meeting]
    )
    
    # Scenario 2: During morning meeting (10:15 AM)
    await test_scenario(
        "During morning meeting (IN PROGRESS)",
        datetime.datetime.combine(base_date, datetime.time(10, 15), tzinfo=datetime.timezone.utc),
        [morning_meeting, afternoon_meeting]
    )
    
    # Scenario 3: Between meetings (11:30 AM)
    await test_scenario(
        "Between meetings",
        datetime.datetime.combine(base_date, datetime.time(11, 30), tzinfo=datetime.timezone.utc),
        [morning_meeting, afternoon_meeting]
    )
    
    # Scenario 4: During afternoon meeting (last of the day) (1:30 PM)
    await test_scenario(
        "During afternoon meeting (last of the day)",
        datetime.datetime.combine(base_date, datetime.time(13, 30), tzinfo=datetime.timezone.utc),
        [morning_meeting, afternoon_meeting]
    )
    
    print("\n" + "="*80)
    print("✅ Demonstration complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
