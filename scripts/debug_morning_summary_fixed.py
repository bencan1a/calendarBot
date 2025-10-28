#!/usr/bin/env python3
"""Debug script for morning summary issue - trace where meetings are being lost."""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calendarbot_lite.morning_summary import MorningSummaryService, MorningSummaryRequest
from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo, LiteEventStatus

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_events():
    """Create test events that match the bug report scenario."""
    # Create events for TOMORROW, not today (morning summary analyzes tomorrow morning)
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    logger.info(f"Creating events for tomorrow: {tomorrow.date()}")
    
    events = [
        # Focus Time block: 8:00-10:30 AM
        LiteCalendarEvent(
            id="focus-1",
            subject="Focus Time",
            start=LiteDateTimeInfo(date_time=tomorrow.replace(hour=8)),
            end=LiteDateTimeInfo(date_time=tomorrow.replace(hour=10, minute=30)),
            show_as=LiteEventStatus.BUSY,
            is_all_day=False
        ),
        # Meeting 1: 8:30 AM (overlaps with Focus Time)
        LiteCalendarEvent(
            id="meeting-1",
            subject="Meeting 1",
            start=LiteDateTimeInfo(date_time=tomorrow.replace(hour=8, minute=30)),
            end=LiteDateTimeInfo(date_time=tomorrow.replace(hour=9)),
            show_as=LiteEventStatus.BUSY,
            is_all_day=False
        ),
        # Meeting 2: 9:30 AM (overlaps with Focus Time)
        LiteCalendarEvent(
            id="meeting-2", 
            subject="Meeting 2",
            start=LiteDateTimeInfo(date_time=tomorrow.replace(hour=9, minute=30)),
            end=LiteDateTimeInfo(date_time=tomorrow.replace(hour=10)),
            show_as=LiteEventStatus.BUSY,
            is_all_day=False
        ),
        # Meeting 3: 10:30 AM
        LiteCalendarEvent(
            id="meeting-3",
            subject="Meeting 3", 
            start=LiteDateTimeInfo(date_time=tomorrow.replace(hour=10, minute=30)),
            end=LiteDateTimeInfo(date_time=tomorrow.replace(hour=11)),
            show_as=LiteEventStatus.BUSY,
            is_all_day=False
        ),
        # Meeting 4: 11:00 AM
        LiteCalendarEvent(
            id="meeting-4",
            subject="Meeting 4",
            start=LiteDateTimeInfo(date_time=tomorrow.replace(hour=11)),
            end=LiteDateTimeInfo(date_time=tomorrow.replace(hour=11, minute=30)),
            show_as=LiteEventStatus.BUSY,
            is_all_day=False
        ),
        # Focus Time block: 11:30 AM - 12:00 PM
        LiteCalendarEvent(
            id="focus-2",
            subject="Focus Time",
            start=LiteDateTimeInfo(date_time=tomorrow.replace(hour=11, minute=30)),
            end=LiteDateTimeInfo(date_time=tomorrow.replace(hour=12)),
            show_as=LiteEventStatus.BUSY,
            is_all_day=False
        ),
    ]
    
    return events

async def debug_morning_summary():
    """Debug the morning summary processing pipeline."""
    logger.info("=== MORNING SUMMARY BUG INVESTIGATION (FIXED) ===")
    
    # Create test events for TOMORROW
    events = create_test_events()
    logger.info(f"Created {len(events)} test events for tomorrow")
    
    for i, event in enumerate(events):
        logger.info(f"Event {i+1}: '{event.subject}' | {event.start.date_time} - {event.end.date_time} | "
                   f"show_as={event.show_as} | is_busy_status={event.is_busy_status}")
    
    # Create morning summary service
    service = MorningSummaryService()
    
    # Create request
    request = MorningSummaryRequest(timezone="UTC")
    
    # Generate summary 
    logger.info("Generating morning summary...")
    result = await service.generate_summary(events, request)
    
    # Log results
    logger.info("=== RESULTS ===")
    logger.info(f"Total meeting equivalents: {result.total_meetings_equivalent}")
    logger.info(f"Early start flag: {result.early_start_flag}")
    logger.info(f"Density: {result.density}")
    logger.info(f"Meeting insights count: {len(result.meeting_insights)}")
    logger.info(f"Free blocks count: {len(result.free_blocks)}")
    logger.info(f"Speech text: {result.speech_text}")
    
    # Expected: 4.0 meeting equivalents (4 real meetings, 2 Focus Time blocks should not count)
    expected_equivalents = 4.0
    
    if result.total_meetings_equivalent == 0.0:
        logger.error("BUG CONFIRMED: total_meetings_equivalent is 0.0 when it should be 4.0")
        if "completely free morning" in result.speech_text:
            logger.error("BUG CONFIRMED: Speech text says 'completely free morning'")
    elif result.total_meetings_equivalent == expected_equivalents:
        logger.info("SUCCESS: Bug appears to be fixed - meetings counted correctly")
    else:
        logger.warning(f"PARTIAL: Got {result.total_meetings_equivalent} equivalents, expected {expected_equivalents}")
    
    # Log individual meeting insights for debugging
    if result.meeting_insights:
        logger.info("=== MEETING INSIGHTS ===")
        for i, insight in enumerate(result.meeting_insights):
            logger.info(f"Insight {i+1}: '{insight.subject}' at {insight.start_time}")
    else:
        logger.error("NO MEETING INSIGHTS FOUND - this indicates the real meetings were filtered out")
    
    return result

if __name__ == "__main__":
    asyncio.run(debug_morning_summary())