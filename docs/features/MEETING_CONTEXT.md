# Meeting Context Feature

**Version:** 1.0.0  
**Last Updated:** August 3, 2025  
**Module:** `calendarbot/features/meeting_context.py`  
**Status:** Implemented

## Overview

The Meeting Context feature provides intelligent analysis of calendar events to deliver contextual information about upcoming meetings. It helps users prepare for meetings by analyzing event details, classifying meeting types, and providing tailored preparation recommendations.

## Key Capabilities

- **Meeting Classification**: Automatically categorizes meetings into types (one-on-one, standup, review, interview, etc.)
- **Preparation Recommendations**: Generates context-specific preparation suggestions based on meeting type
- **Time-to-Meeting Awareness**: Calculates time remaining until meetings and flags those requiring immediate preparation
- **Comprehensive Context Analysis**: Provides detailed insights including attendee count, location requirements, and online meeting status

## Architecture

The Meeting Context feature is implemented through the following components:

### MeetingContextAnalyzer Class

The core component that analyzes calendar events and generates meeting insights.

```python
class MeetingContextAnalyzer:
    """Analyzes calendar events to provide meeting context and preparation insights."""

    def __init__(self, preparation_buffer_minutes: int = 15) -> None:
        # Initialize with configurable preparation buffer time
        
    def analyze_upcoming_meetings(
        self, events: list[CalendarEvent], current_time: Optional[datetime] = None
    ) -> list[dict[str, Any]]:
        # Main analysis method that processes events and returns insights
```

### Helper Functions

- `get_meeting_context_for_timeframe()`: Async function that provides a comprehensive meeting context summary for a specified timeframe
- `calculate_preparation_time_needed()`: Utility function that calculates recommended preparation time based on meeting characteristics

## Usage Examples

### Basic Usage

```python
from calendarbot.features.meeting_context import MeetingContextAnalyzer
from calendarbot.ics.models import CalendarEvent

# Create analyzer with default 15-minute preparation buffer
analyzer = MeetingContextAnalyzer()

# Analyze upcoming meetings
insights = analyzer.analyze_upcoming_meetings(events)

# Process insights
for insight in insights:
    if insight["preparation_needed"]:
        print(f"Prepare for: {insight['subject']}")
        for recommendation in insight["preparation_recommendations"]:
            print(f"- {recommendation}")
```

### Async Context Analysis

```python
from calendarbot.features.meeting_context import get_meeting_context_for_timeframe

# Get comprehensive meeting context for next 4 hours
context = await get_meeting_context_for_timeframe(events, hours_ahead=4)

# Access summary statistics
total_meetings = context["total_meetings"]
meetings_needing_prep = context["meetings_needing_preparation"]

# Access next meeting details
if context["next_meeting"]:
    next_meeting = context["next_meeting"]
    print(f"Next meeting: {next_meeting['subject']}")
    print(f"Time until meeting: {next_meeting['time_until_meeting_minutes']} minutes")
```

## API Reference

### MeetingContextAnalyzer

#### Constructor

```python
def __init__(self, preparation_buffer_minutes: int = 15) -> None
```

- **preparation_buffer_minutes**: Minutes before meeting to consider for preparation (default: 15)

#### Methods

```python
def analyze_upcoming_meetings(
    self, events: list[CalendarEvent], current_time: Optional[datetime] = None
) -> list[dict[str, Any]]
```

- **events**: List of calendar events to analyze
- **current_time**: Current time for analysis (defaults to now)
- **Returns**: List of meeting context insights with preparation recommendations
- **Raises**: ValueError if events list is empty or contains invalid data

### Helper Functions

```python
async def get_meeting_context_for_timeframe(
    events: list[CalendarEvent], hours_ahead: int = 4
) -> dict[str, Any]
```

- **events**: List of calendar events to analyze
- **hours_ahead**: Hours to look ahead for meeting analysis (default: 4)
- **Returns**: Dictionary containing meeting context summary and insights
- **Raises**: ValueError if hours_ahead is negative or events is empty

```python
def calculate_preparation_time_needed(meeting_type: str, attendee_count: int) -> int
```

- **meeting_type**: Type of meeting (from _classify_meeting_type)
- **attendee_count**: Number of attendees
- **Returns**: Recommended preparation time in minutes
- **Raises**: ValueError if attendee_count is negative

## Integration Points

The Meeting Context feature integrates with the following CalendarBot components:

- **ICS Processing**: Uses `CalendarEvent` models from the ICS module
- **Display System**: Provides context data that can be rendered in various display formats
- **Web Interface**: Can be integrated into web views to show meeting preparation information

## Configuration

The Meeting Context feature has minimal configuration requirements:

- **Preparation Buffer**: Configurable through the `MeetingContextAnalyzer` constructor
- **Analysis Timeframe**: Configurable through the `hours_ahead` parameter in `get_meeting_context_for_timeframe()`

No additional configuration files or environment variables are required.

## Limitations

- Meeting classification is based on simple keyword matching and may not accurately classify all meeting types
- Preparation recommendations are generic and not personalized to individual user preferences
- The feature does not currently integrate with external context sources (e.g., documents, emails)