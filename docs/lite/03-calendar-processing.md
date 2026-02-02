# Calendar Processing Component

**Component:** 3 of 5 - Calendar Data Layer
**Purpose:** ICS parsing, RRULE expansion, event filtering, prioritization, pipeline orchestration
**Last Updated:** 2025-11-03

---

## Table of Contents

1. [Overview](#overview)
2. [Core Modules](#core-modules)
3. [Key Interfaces & Data Structures](#key-interfaces--data-structures)
4. [Integration Points](#integration-points)
5. [Common Usage Patterns](#common-usage-patterns)
6. [Code Examples](#code-examples)
7. [Related Documentation](#related-documentation)

---

## Overview

### Purpose

The Calendar Processing component is the domain logic core of calendarbot_lite, responsible for transforming ICS calendar feeds into structured, filtered, and prioritized event data. It handles RFC 5545 compliant ICS parsing, RRULE-based recurring event expansion, event deduplication and merging, time-based filtering, and business logic prioritization.

### Position in Architecture

This component bridges the HTTP Server and Alexa Integration layers, consuming raw ICS data and producing structured calendar events:

```
┌──────────────────────────────────────────────────┐
│     HTTP Server & Routing (Component 1)          │
│  Background refresh → Fetch orchestrator          │
└───────────────┬──────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────┐
│     Calendar Processing (this component)          │
│  Fetch → Parse → Expand → Filter → Prioritize    │
└───────────────┬──────────────────────────────────┘
                │
                ├──────────────────┬──────────────────┐
                ▼                  ▼                  ▼
         Alexa Integration   API Routes      Event Window
```

**References:**
- Architecture context: [`tmp/component_analysis.md`](../../tmp/component_analysis.md#L206-L277)
- Server integration: [`docs/lite/01-server-http-routing.md`](01-server-http-routing.md#L152-L194)
- Alexa consumption: [`docs/lite/02-alexa-integration.md`](02-alexa-integration.md#L88-L125)

### Key Design Patterns

1. **Pipeline Architecture** - Multi-stage event processing with modular stages
2. **Streaming Parser** - Memory-efficient chunked ICS parsing for large files
3. **Worker Pool Pattern** - Bounded concurrency for CPU-intensive RRULE expansion
4. **Event Merging** - RECURRENCE-ID override handling and deduplication
5. **Smart Fallback** - Preserves existing data when sources fail

---

## Core Modules

### ICS Fetching

#### [`lite_fetcher.py`](../../calendarbot_lite/lite_fetcher.py)

**Purpose:** HTTP client for downloading ICS calendar files with retry logic and connection pooling.

**Key Classes:**
- [`LiteICSFetcher`](../../calendarbot_lite/lite_fetcher.py:80-100) - Async HTTP client for ICS downloads
  - `fetch_calendar()` - Main fetch method with retry and backoff
  - Uses shared HTTP client for connection reuse (see [`http_client.py`](../../calendarbot_lite/http_client.py))
- [`LiteSecurityEventLogger`](../../calendarbot_lite/lite_fetcher.py:50-73) - Security event logging

**Exception Hierarchy:**
- `LiteICSFetchError` - Base exception
- `LiteICSAuthError` - Authentication failures (401, 403)
- `LiteICSNetworkError` - Network connectivity issues
- `LiteICSTimeoutError` - Request timeouts

**Responsibilities:**
- HTTP fetching with configurable timeouts
- Exponential backoff with jitter
- Connection pooling via shared client
- Security event logging for URL access

---

### ICS Parsing

#### [`lite_streaming_parser.py`](../../calendarbot_lite/lite_streaming_parser.py)

**Purpose:** Memory-efficient streaming ICS parser for large calendar files.

**Key Classes:**
- [`LiteStreamingICSParser`](../../calendarbot_lite/lite_streaming_parser.py:43-67) - Chunked streaming parser
  - `parse_stream()` - Yields events as they're found in the ICS stream
  - Handles line folding across chunk boundaries
  - Processes 8KB chunks by default

**Constants:**
- `MAX_ICS_SIZE_BYTES` = 50MB - Hard limit for ICS file size
- `MAX_ICS_SIZE_WARNING` = 10MB - Warning threshold
- `STREAMING_THRESHOLD` = 10MB - When to use streaming vs. traditional parsing

**Responsibilities:**
- Chunked ICS parsing to minimize memory usage
- Event boundary detection across chunks
- Calendar metadata extraction
- Size validation and warnings

---

#### [`lite_event_parser.py`](../../calendarbot_lite/lite_event_parser.py)

**Purpose:** Parses individual VEVENT components into structured event objects.

**Key Classes:**
- [`LiteEventComponentParser`](../../calendarbot_lite/lite_event_parser.py:27-45) - VEVENT → LiteCalendarEvent conversion
  - [`parse_event_component()`](../../calendarbot_lite/lite_event_parser.py:47-60) - Main parsing method
  - Extracts properties: UID, SUMMARY, DTSTART, DTEND, LOCATION, ATTENDEES
  - Handles timezone conversion and all-day events
  - Detects online meetings (Microsoft-specific URLs)

**Responsibilities:**
- VEVENT component parsing
- Attendee and organizer extraction
- Recurrence metadata (RRULE, EXDATE, RECURRENCE-ID)
- Event status and transparency mapping
- Created/modified timestamp parsing

---

#### [`lite_parser.py`](../../calendarbot_lite/lite_parser.py)

**Purpose:** Coordinator for ICS parsing, integrating streaming parser and event parser.

**Key Classes:**
- [`LiteICSParser`](../../calendarbot_lite/lite_parser.py:87-100) - Main parser coordinator
  - Orchestrates streaming parser, event parser, and RRULE expander
  - Produces [`LiteICSParseResult`](../../calendarbot_lite/lite_models.py:46-65)
  - Handles parser component initialization

**Helper Classes:**
- `_SimpleEvent` - Lightweight event representation for fallbacks
- `_DateTimeWrapper` - Datetime wrapper for RRULE expander

**Responsibilities:**
- Parser component coordination
- ICS format detection and validation
- Parser result aggregation
- Production mode optimization

---

### Recurring Event Expansion

#### [`lite_rrule_expander.py`](../../calendarbot_lite/lite_rrule_expander.py)

**Purpose:** Expands recurring events using RFC 5545 RRULE specifications with bounded resources.

**Key Classes:**
- [`RRuleWorkerPool`](../../calendarbot_lite/lite_rrule_expander.py:61-94) - Async worker pool for CPU-intensive expansion
  - `expand_rrule_stream()` - Expands recurring events with cooperative multitasking
  - Bounded concurrency (default: 1 worker for Pi Zero 2W)
  - Time budget enforcement (200ms per rule)
  - Yield frequency for event loop responsiveness

- [`RRuleExpanderConfig`](../../calendarbot_lite/lite_rrule_expander.py:22-58) - Configuration dataclass
  - `rrule_worker_concurrency` - Worker pool size
  - `max_occurrences_per_rule` - Occurrence limit (250 default)
  - `expansion_days_window` - Expansion window (365 days)
  - `expansion_time_budget_ms_per_rule` - CPU time limit

**Responsibilities:**
- RRULE string parsing and expansion
- EXDATE handling (exception dates)
- Bounded CPU usage for resource-constrained devices
- Instance ID generation for expanded events
- RRULE master UID tracking

---

### Event Management

#### [`lite_event_merger.py`](../../calendarbot_lite/lite_event_merger.py)

**Purpose:** Merges expanded recurring events with original events, handling RECURRENCE-ID overrides.

**Key Classes:**
- [`LiteEventMerger`](../../calendarbot_lite/lite_event_merger.py:16-76) - Event merging and deduplication
  - `merge_expanded_events()` - Combines original and expanded events
  - `_collect_recurrence_overrides()` - Identifies RECURRENCE-ID instances
  - `_filter_overridden_occurrences()` - Suppresses expanded instances that were moved

**Responsibilities:**
- RECURRENCE-ID override processing (moved/modified instances)
- Expanded event and original event merging
- Duplicate suppression
- Master recurring event handling

---

#### [`event_filter.py`](../../calendarbot_lite/event_filter.py)

**Purpose:** Filters events based on time, timezone, and business logic.

**Key Classes:**
- [`EventFilter`](../../calendarbot_lite/event_filter.py:58-69) - Time-based event filtering
  - `filter_upcoming_events()` - Filters to future events
  - Handles timezone-aware and timezone-naive datetimes safely

- [`SmartFallbackHandler`](../../calendarbot_lite/event_filter.py:15-55) - Fallback logic when sources fail
  - `should_preserve_existing_window()` - Determines if cached events should be preserved
  - Detects all-sources-failed scenarios
  - Identifies suspicious zero-event results

**Responsibilities:**
- Future event filtering
- Timezone-aware datetime comparison
- Smart fallback to cached events
- Network corruption detection

---

#### [`event_prioritizer.py`](../../calendarbot_lite/event_prioritizer.py)

**Purpose:** Prioritizes events for "what's next" queries with business logic.

**Key Classes:**
- [`EventPrioritizer`](../../calendarbot_lite/event_prioritizer.py:26-36) - Business logic prioritization
  - `find_next_event()` - Finds next displayable event with prioritization
  - Skips focus time events
  - Skips user-skipped events
  - Prioritizes business meetings over lunch when occurring within 30 minutes

- [`EventCategory`](../../calendarbot_lite/event_prioritizer.py:18-24) - Event categorization enum
  - `BUSINESS`, `LUNCH`, `FOCUS_TIME`

**Responsibilities:**
- Next event selection with business rules
- Focus time event filtering
- User skip management
- Time-based event grouping and prioritization

---

### Pipeline Architecture

#### [`pipeline.py`](../../calendarbot_lite/pipeline.py)

**Purpose:** Orchestrates multi-stage event processing with explicit error handling.

**Key Classes:**
- [`ProcessingContext`](../../calendarbot_lite/pipeline.py:32-67) - Context passed between stages
  - Configuration: RRULE window, event limits
  - Time context: now, window_start, window_end
  - Processing state: raw_content, events
  - Metadata: source_url, calendar_metadata
  - User preferences: skipped_event_ids, user_email

- [`ProcessingResult`](../../calendarbot_lite/pipeline.py:70-98) - Stage result with errors/warnings
  - `success` - Stage success/failure flag
  - `events` - Processed events
  - `warnings`, `errors` - Observability messages
  - Statistics: events_in, events_out, events_filtered

- [`EventProcessor`](../../calendarbot_lite/pipeline.py:101-125) - Protocol for pipeline stages
  - `async def process(context)` - Stage processing method
  - `name` property - Stage name for logging

- [`EventProcessingPipeline`](../../calendarbot_lite/pipeline.py:128-262) - Pipeline orchestrator
  - `add_stage()` - Adds stage to pipeline
  - `process()` - Executes all stages sequentially
  - Error aggregation and logging

**Responsibilities:**
- Stage coordination and sequencing
- Context propagation between stages
- Error and warning collection
- Processing statistics tracking
- Stage lifecycle management

### Pipeline Benefits

1. **Modularity**: Each stage is independent and testable in isolation
2. **Extensibility**: Easy to add new stages without modifying existing code
3. **Clarity**: Explicit flow with clear inputs/outputs at each stage
4. **Observability**: Built-in logging and error tracking at each stage
5. **Flexibility**: Stages can be reordered or conditionally skipped

### Pipeline Logging

The pipeline provides comprehensive logging at each stage:

```
INFO  Starting pipeline with 7 stages
DEBUG Executing stage 1/7: Parse
INFO  Parsed 25 events from ICS content (12458 bytes)
INFO  Stage 1/7 (Parse) completed: success=True, events_in=0, events_out=25

DEBUG Executing stage 2/7: RRULEExpansion
INFO  RRULE expansion: 25 → 47 events (22 instances generated)
INFO  Stage 2/7 (RRULEExpansion) completed: success=True, events_in=25, events_out=47

DEBUG Executing stage 3/7: Deduplication
WARNING [Deduplication] Removed 2 duplicate events
INFO  Stage 3/7 (Deduplication) completed: success=True, events_in=47, events_out=45

INFO  Pipeline completed successfully: 45 events, 1 warnings
```

### Pipeline Error Handling

Stages can fail gracefully with detailed error messages:

```python
result = await pipeline.process(context)

if not result.success:
    print("Pipeline failed!")
    for error in result.errors:
        print(f"  ERROR: {error}")
    for warning in result.warnings:
        print(f"  WARNING: {warning}")
```

If a stage fails critically, the pipeline stops and returns the error:

```
ERROR [Parse] ICS parsing failed: Invalid calendar format
ERROR Pipeline stopped at stage 1 (Parse) due to failure
```

---

### Additional Modules

#### [`lite_datetime_utils.py`](../../calendarbot_lite/lite_datetime_utils.py)

**Purpose:** DateTime parsing and timezone utilities for ICS events.

**Key Classes:**
- `LiteDateTimeParser` - DateTime property parsing
  - Handles timezone-aware and naive datetimes
  - UTC normalization
  - All-day event detection

**Responsibilities:**
- DTSTART/DTEND parsing
- Timezone conversion
- All-day event handling

---

#### [`lite_attendee_parser.py`](../../calendarbot_lite/lite_attendee_parser.py)

**Purpose:** Parses ATTENDEE properties from VEVENT components.

**Key Classes:**
- `LiteAttendeeParser` - Attendee extraction
  - Parses CN (common name), EMAIL, ROLE, PARTSTAT
  - Organizer detection

**Responsibilities:**
- Attendee list parsing
- Response status extraction
- Attendee type classification

---

#### [`lite_parser_telemetry.py`](../../calendarbot_lite/lite_parser_telemetry.py)

**Purpose:** Parser performance telemetry and metrics.

**Key Classes:**
- `ParserTelemetry` - Lightweight metrics tracking
  - Parse duration
  - Event counts
  - Error rates

**Responsibilities:**
- Parser performance monitoring
- Debugging support
- Optimization guidance

---

## Key Interfaces & Data Structures

### Event Models

**[`LiteCalendarEvent`](../../calendarbot_lite/lite_models.py:265-326)** - Primary event model:

```python
class LiteCalendarEvent(BaseModel):
    # Core properties
    id: str
    subject: str
    body_preview: Optional[str]

    # Time information
    start: LiteDateTimeInfo
    end: LiteDateTimeInfo
    is_all_day: bool

    # Status
    show_as: LiteEventStatus  # free, tentative, busy, oof, workingElsewhere
    is_cancelled: bool

    # Attendees
    is_organizer: bool
    location: Optional[LiteLocation]
    attendees: Optional[list[LiteAttendee]]

    # Recurrence
    is_recurring: bool
    recurrence_id: Optional[str]  # RECURRENCE-ID for moved instances
    is_expanded_instance: bool    # Generated from RRULE
    rrule_master_uid: Optional[str]  # Master event UID

    # Metadata
    created_date_time: Optional[datetime]
    last_modified_date_time: Optional[datetime]

    # Online meeting
    is_online_meeting: bool
    online_meeting_url: Optional[str]
```

**Supporting Models:**
- [`LiteDateTimeInfo`](../../calendarbot_lite/lite_models.py:234-243) - DateTime with timezone
- [`LiteLocation`](../../calendarbot_lite/lite_models.py:246-252) - Location details
- [`LiteAttendee`](../../calendarbot_lite/lite_models.py:254-262) - Attendee information
- [`LiteEventStatus`](../../calendarbot_lite/lite_models.py:205-213) - Show-as status enum

---

### Pipeline Stage Protocol

All pipeline stages must implement:

```python
class EventProcessor(Protocol):
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Process events according to this stage's responsibility."""
        ...

    @property
    def name(self) -> str:
        """Name of this processing stage for logging."""
        ...
```

**Example stages** (see [`pipeline_stages.py`](../../calendarbot_lite/pipeline_stages.py)):
- `ParseStage` - ICS parsing + RRULE expansion
- `DeduplicationStage` - Remove duplicates
- `SkippedEventsFilterStage` - Filter user-skipped events
- `TimeWindowStage` - Apply time window
- `EventLimitStage` - Limit to display size

---

### Parser Output Formats

**ICS Parse Result:**

```python
class LiteICSParseResult(BaseModel):
    events: list[LiteCalendarEvent]
    warnings: list[str]
    calendar_metadata: dict[str, Any]
    parse_duration_ms: float
```

**ICS Response:**

```python
class LiteICSResponse(BaseModel):
    content: str  # Raw ICS content
    status_code: int
    fetch_duration_ms: float
```

---

## Integration Points

### How Calendar Data Flows to Consumers

**Background Refresh Cycle** (from [`server.py`](../../calendarbot_lite/server.py:795-1088)):

```python
# 1. Fetch ICS from sources
fetch_results = await fetch_orchestrator.fetch_all_sources(...)

# 2. Parse ICS → events (per source)
for result in fetch_results:
    parse_result = await parser.parse_ics(result.content)
    # Pipeline 1: Per-source processing

# 3. Combine all sources
all_events = combine_source_events(parse_results)

# 4. Post-processing pipeline (Pipeline 2)
final_result = await post_processing_pipeline.process(context)

# 5. Atomic window update
async with window_lock:
    event_window_ref[0] = tuple(final_result.events)

# 6. Precompute Alexa responses (Pipeline 3)
await precompute_alexa_responses(event_window_ref, ...)
```

---

### Fetch Orchestrator Integration

The Calendar Processing component integrates with [`fetch_orchestrator.py`](../../calendarbot_lite/fetch_orchestrator.py) for multi-source coordination:

```python
class FetchOrchestrator:
    async def fetch_all_sources(
        self,
        sources: list[LiteICSSource],
        fetcher: LiteICSFetcher,
    ) -> list[LiteICSResponse]:
        """Fetch multiple sources with bounded concurrency."""
        ...
```

**Features:**
- Parallel source fetching with timeout
- Bounded concurrency (respects system limits)
- Individual source failure isolation

---

### Pipeline Types

The system uses **3 distinct pipeline types**:

**Pipeline 1: Per-Source Processing**
- Parse ICS content
- Expand RRULE occurrences
- Deduplicate within source
- Sort by start time

**Pipeline 2: Post-Processing**
- Combine all sources
- Filter skipped events
- Apply time window
- Limit to display size

**Pipeline 3: Alexa Precomputation**
- Precompute common responses
- Cache in `_precomputed_responses`
- Reduces Alexa handler latency

---

### Health Tracking Integration

Calendar processing reports metrics to [`health_tracker.py`](../../calendarbot_lite/health_tracker.py):

```python
health_tracker.record_refresh_attempt()
health_tracker.record_event_count(len(events))
health_tracker.record_parse_duration(parse_duration_ms)
```

---

## Common Usage Patterns

### Parsing ICS Feeds

```python
from calendarbot_lite.lite_parser import LiteICSParser

# Initialize parser
settings = get_settings()
parser = LiteICSParser(settings)

# Parse ICS content
ics_content = await fetch_ics_from_url(url)
result = await parser.parse_ics(ics_content)

# Access parsed events
for event in result.events:
    print(f"{event.subject}: {event.start.date_time}")
```

---

### Expanding Recurring Events

```python
from calendarbot_lite.lite_rrule_expander import RRuleWorkerPool, RRuleExpanderConfig

# Initialize worker pool
config = RRuleExpanderConfig.from_settings(settings)
worker_pool = RRuleWorkerPool(settings)

# Expand recurring event
rrule_string = "FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=10"
exdates = ["20240101T090000Z"]

async for expanded_event in worker_pool.expand_rrule_stream(
    master_event=recurring_event,
    rrule_string=rrule_string,
    exdates=exdates
):
    print(f"Occurrence: {expanded_event.start.date_time}")
```

---

### Adding Custom Filters

```python
from calendarbot_lite.pipeline import ProcessingContext, ProcessingResult, EventProcessor

class CustomFilterStage:
    """Example: Filter events by subject keyword."""

    @property
    def name(self) -> str:
        return "CustomFilterStage"

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        result = ProcessingResult(stage_name=self.name)
        result.events_in = len(context.events)

        # Filter events
        filtered = [
            event for event in context.events
            if "meeting" in event.subject.lower()
        ]

        result.events = filtered
        result.events_out = len(filtered)
        result.events_filtered = result.events_in - result.events_out

        return result
```

---

### Implementing Pipeline Stages

```python
from calendarbot_lite.pipeline import EventProcessingPipeline, ProcessingContext

# Create pipeline
pipeline = EventProcessingPipeline()

# Add stages
pipeline.add_stage(ParseStage(parser))
pipeline.add_stage(DeduplicationStage())
pipeline.add_stage(CustomFilterStage())
pipeline.add_stage(EventLimitStage(limit=50))

# Execute pipeline
context = ProcessingContext(
    raw_content=ics_content,
    rrule_expansion_days=14,
    event_window_size=50
)
result = await pipeline.process(context)

# Check result
if result.success:
    print(f"Processed {len(result.events)} events")
else:
    print(f"Errors: {result.errors}")
```

---

### Testing Calendar Processing

```python
import pytest
from calendarbot_lite.lite_event_parser import LiteEventComponentParser
from icalendar import Event as ICalEvent

@pytest.mark.asyncio
async def test_parse_simple_event():
    """Test parsing a simple non-recurring event."""
    # Create test component
    component = ICalEvent()
    component.add("UID", "test-event-123")
    component.add("SUMMARY", "Test Meeting")
    component.add("DTSTART", datetime(2024, 1, 1, 9, 0, 0))
    component.add("DTEND", datetime(2024, 1, 1, 10, 0, 0))

    # Parse
    parser = LiteEventComponentParser(
        datetime_parser=LiteDateTimeParser(),
        attendee_parser=LiteAttendeeParser()
    )
    event = parser.parse_event_component(component)

    # Assert
    assert event is not None
    assert event.subject == "Test Meeting"
    assert event.is_recurring is False
```

---

## Code Examples

### Example 1: ICS Parsing

```python
from calendarbot_lite.lite_parser import LiteICSParser
from calendarbot_lite.config_manager import ConfigManager

async def parse_calendar_feed(ics_url: str):
    """Parse an ICS calendar feed and print events."""
    # Initialize components
    config = ConfigManager()
    settings = config.get_settings()
    parser = LiteICSParser(settings)

    # Fetch ICS content
    async with aiohttp.ClientSession() as session:
        async with session.get(ics_url) as resp:
            ics_content = await resp.text()

    # Parse events
    result = await parser.parse_ics(ics_content)

    # Print results
    print(f"Parsed {len(result.events)} events")
    for event in result.events[:5]:  # First 5 events
        print(f"- {event.subject} at {event.start.date_time}")

    if result.warnings:
        print(f"Warnings: {result.warnings}")

    return result.events
```

---

### Example 2: RRULE Expansion

```python
from calendarbot_lite.lite_rrule_expander import RRuleWorkerPool
from datetime import datetime, timezone

async def expand_weekly_meeting():
    """Expand a weekly recurring meeting."""
    # Create master event
    master_event = LiteCalendarEvent(
        id="weekly-standup",
        subject="Weekly Standup",
        start=LiteDateTimeInfo(
            date_time=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            time_zone="UTC"
        ),
        end=LiteDateTimeInfo(
            date_time=datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc),
            time_zone="UTC"
        ),
        is_recurring=True
    )

    # RRULE: Every Monday and Wednesday for 4 weeks
    rrule = "FREQ=WEEKLY;BYDAY=MO,WE;COUNT=8"

    # Initialize worker pool
    worker_pool = RRuleWorkerPool(settings)

    # Expand occurrences
    occurrences = []
    async for occurrence in worker_pool.expand_rrule_stream(
        master_event=master_event,
        rrule_string=rrule
    ):
        occurrences.append(occurrence)
        print(f"Occurrence: {occurrence.start.date_time}")

    return occurrences
```

---

### Example 3: Custom Filter Implementation

```python
from calendarbot_lite.pipeline import ProcessingContext, ProcessingResult
import re

class EmailDomainFilterStage:
    """Filter events by attendee email domain."""

    def __init__(self, allowed_domains: set[str]):
        self.allowed_domains = allowed_domains

    @property
    def name(self) -> str:
        return "EmailDomainFilterStage"

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        result = ProcessingResult(stage_name=self.name)
        result.events_in = len(context.events)

        filtered = []
        for event in context.events:
            if not event.attendees:
                # Keep events without attendees
                filtered.append(event)
                continue

            # Check if any attendee is from allowed domain
            has_allowed_domain = any(
                self._is_allowed_domain(att.email)
                for att in event.attendees
            )

            if has_allowed_domain:
                filtered.append(event)

        result.events = filtered
        result.events_out = len(filtered)
        result.events_filtered = result.events_in - result.events_out

        return result

    def _is_allowed_domain(self, email: str) -> bool:
        """Check if email domain is allowed."""
        match = re.search(r'@([\w.-]+)$', email)
        if not match:
            return False
        domain = match.group(1)
        return domain in self.allowed_domains

# Usage
pipeline = EventProcessingPipeline()
pipeline.add_stage(EmailDomainFilterStage({"example.com", "company.com"}))
```

---

### Example 4: Pipeline Stage Implementation

```python
from calendarbot_lite.pipeline import ProcessingContext, ProcessingResult

class WorkingHoursFilterStage:
    """Filter events to working hours only (9 AM - 5 PM)."""

    def __init__(self, start_hour: int = 9, end_hour: int = 17):
        self.start_hour = start_hour
        self.end_hour = end_hour

    @property
    def name(self) -> str:
        return "WorkingHoursFilterStage"

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        result = ProcessingResult(stage_name=self.name)
        result.events_in = len(context.events)

        filtered = []
        for event in context.events:
            start_time = event.start.date_time
            hour = start_time.hour

            if self.start_hour <= hour < self.end_hour:
                filtered.append(event)
            else:
                result.add_warning(
                    f"Filtered out-of-hours event: {event.subject} at {start_time}"
                )

        result.events = filtered
        result.events_out = len(filtered)
        result.events_filtered = result.events_in - result.events_out

        return result
```

---

### Example 5: Event Prioritization Usage

```python
from calendarbot_lite.event_prioritizer import EventPrioritizer
from datetime import datetime, timezone

async def get_next_meeting(events: tuple[LiteCalendarEvent, ...]):
    """Get the next prioritized meeting."""
    # Initialize prioritizer
    def is_focus_time(event: LiteCalendarEvent) -> bool:
        return "focus time" in event.subject.lower()

    prioritizer = EventPrioritizer(focus_time_checker=is_focus_time)

    # Find next event
    now = datetime.now(timezone.utc)
    next_event_tuple = prioritizer.find_next_event(
        events=events,
        now=now,
        skipped_store=None
    )

    if next_event_tuple:
        event, seconds_until = next_event_tuple
        minutes_until = seconds_until / 60
        print(f"Next meeting: {event.subject} in {minutes_until:.0f} minutes")
        return event
    else:
        print("No upcoming meetings")
        return None
```

---

## Related Documentation

### Component Documentation
- **Previous:** [`01-server-http-routing.md`](01-server-http-routing.md) - HTTP Server & Routing
- **Next:** [`02-alexa-integration.md`](02-alexa-integration.md) - Alexa Integration

### Architecture References
- **Component Analysis:** [`tmp/component_analysis.md`](../../tmp/component_analysis.md#L206-L277) - Calendar Processing overview
- **AGENTS.md:** [`AGENTS.md`](../../AGENTS.md#L93-L139) - Calendar Processing in architecture
- **PIPELINE_ARCHITECTURE.md:** [`docs/PIPELINE_ARCHITECTURE.md`](../PIPELINE_ARCHITECTURE.md) - Detailed pipeline design

### Module-Specific Documentation
- **RRULE Debug Script:** [`scripts/debug_recurring_events.py`](../../scripts/debug_recurring_events.py) - RRULE expansion debugging
- **Test Fixtures:** [`tests/fixtures/ics/`](../../tests/fixtures/ics/) - ICS test files

### External References
- **RFC 5545:** iCalendar specification - [https://tools.ietf.org/html/rfc5545](https://tools.ietf.org/html/rfc5545)
- **icalendar library:** Python ICS parser - [https://github.com/collective/icalendar](https://github.com/collective/icalendar)
- **dateutil.rrule:** RRULE expansion - [https://dateutil.readthedocs.io/en/stable/rrule.html](https://dateutil.readthedocs.io/en/stable/rrule.html)

---

**Last Updated:** 2025-11-03
**Component:** Calendar Processing (3 of 5)
**Status:** Active - Core domain logic layer