# Event Processing Pipeline Architecture

## Overview

The Event Processing Pipeline provides a flexible, extensible architecture for processing calendar events through multiple stages. This document describes the pipeline pattern, available stages, and usage examples.

## Core Concepts

### Pipeline Pattern

The pipeline pattern allows you to compose independent processing stages into a sequence. Each stage:
- Receives a `ProcessingContext` with events and configuration
- Performs its specific processing task
- Returns a `ProcessingResult` with events and any errors/warnings
- Can modify the context for downstream stages

### Benefits

1. **Modularity**: Each stage is independent and testable in isolation
2. **Extensibility**: Easy to add new stages without modifying existing code
3. **Clarity**: Explicit flow with clear inputs/outputs at each stage
4. **Observability**: Built-in logging and error tracking at each stage
5. **Flexibility**: Stages can be reordered or conditionally skipped

## Architecture Components

### ProcessingContext

Dataclass that holds all state passed between pipeline stages:

```python
@dataclass
class ProcessingContext:
    # Configuration
    rrule_expansion_days: int = 14
    event_window_size: int = 50
    max_stored_events: int = 1000

    # Time context
    now: Optional[datetime] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None

    # Processing state
    raw_content: Optional[str] = None  # Raw ICS content
    raw_components: List[Any] = field(default_factory=list)
    events: List[LiteCalendarEvent] = field(default_factory=list)

    # Metadata
    source_url: Optional[str] = None
    calendar_metadata: dict[str, Any] = field(default_factory=dict)

    # User preferences
    skipped_event_ids: set[str] = field(default_factory=set)
    user_email: Optional[str] = None
```

### ProcessingResult

Result object returned by each stage:

```python
@dataclass
class ProcessingResult:
    success: bool = True
    events: List[LiteCalendarEvent] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Statistics
    events_in: int = 0
    events_out: int = 0
    events_filtered: int = 0
    stage_name: str = ""
```

### EventProcessor Protocol

Interface that all pipeline stages must implement:

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

### EventProcessingPipeline

Orchestrator that executes stages in sequence:

```python
class EventProcessingPipeline:
    def add_stage(self, stage: EventProcessor) -> "EventProcessingPipeline":
        """Add stage (builder pattern)."""
        ...

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Execute all stages in sequence."""
        ...
```

## Available Stages

### Core Processing Stages

#### 1. ParseStage
**Purpose**: Parse raw ICS content into LiteCalendarEvent objects
**Input**: `context.raw_content` (ICS string)
**Output**: `context.events` (parsed events)
**Location**: `calendarbot_lite/pipeline_stages.py::ParseStage`

```python
from calendarbot_lite.pipeline_stages import ParseStage

parser = LiteICSParser(settings)
stage = ParseStage(parser)
```

#### 2. ExpansionStage
**Purpose**: Expand recurring events using RRULE patterns
**Input**: `context.events` (with recurring masters)
**Output**: `context.events` (with expanded instances)
**Location**: `calendarbot_lite/pipeline_stages.py::ExpansionStage`

```python
from calendarbot_lite.pipeline_stages import ExpansionStage

stage = ExpansionStage(parser)
```

#### 3. DeduplicationStage
**Purpose**: Remove duplicate events by ID, keeping the one with most info
**Input**: `context.events` (possibly with duplicates)
**Output**: `context.events` (deduplicated)
**Location**: `calendarbot_lite/pipeline_stages.py::DeduplicationStage`

```python
from calendarbot_lite.pipeline_stages import DeduplicationStage

stage = DeduplicationStage()
```

#### 4. SortStage
**Purpose**: Sort events by start time
**Input**: `context.events` (any order)
**Output**: `context.events` (sorted by start time)
**Location**: `calendarbot_lite/pipeline_stages.py::SortStage`

```python
from calendarbot_lite.pipeline_stages import SortStage

stage = SortStage()
```

### Filtering Stages

#### 5. SkippedEventsFilterStage
**Purpose**: Filter out user-skipped events
**Input**: `context.events` + `context.skipped_event_ids`
**Output**: `context.events` (filtered)
**Location**: `calendarbot_lite/pipeline_stages.py::SkippedEventsFilterStage`

```python
from calendarbot_lite.pipeline_stages import SkippedEventsFilterStage

stage = SkippedEventsFilterStage()
# Uses context.skipped_event_ids set
```

#### 6. TimeWindowStage
**Purpose**: Filter events to specific time range
**Input**: `context.events` + `context.window_start/end`
**Output**: `context.events` (within window)
**Location**: `calendarbot_lite/pipeline_stages.py::TimeWindowStage`

```python
from calendarbot_lite.pipeline_stages import TimeWindowStage

stage = TimeWindowStage()
# Uses context.window_start and context.window_end
```

#### 7. EventLimitStage
**Purpose**: Limit events to maximum count
**Input**: `context.events`
**Output**: `context.events` (first N events)
**Location**: `calendarbot_lite/pipeline_stages.py::EventLimitStage`

```python
from calendarbot_lite.pipeline_stages import EventLimitStage

stage = EventLimitStage(max_events=50)
# Or uses context.event_window_size
```

## Usage Examples

### Example 1: Basic Post-Processing Pipeline

For already-parsed events that need cleanup:

```python
from calendarbot_lite.pipeline import EventProcessingPipeline, ProcessingContext
from calendarbot_lite.pipeline_stages import (
    DeduplicationStage,
    SkippedEventsFilterStage,
    TimeWindowStage,
    EventLimitStage
)

# Build pipeline
pipeline = (
    EventProcessingPipeline()
    .add_stage(DeduplicationStage())
    .add_stage(SkippedEventsFilterStage())
    .add_stage(TimeWindowStage())
    .add_stage(EventLimitStage())
)

# Process events
context = ProcessingContext(
    events=my_parsed_events,
    skipped_event_ids={"event-123"},
    event_window_size=50,
    window_start=datetime.now(timezone.utc),
    window_end=datetime.now(timezone.utc) + timedelta(days=7)
)

result = await pipeline.process(context)

if result.success:
    print(f"Processed {result.events_out} events")
    final_events = context.events
else:
    print(f"Errors: {result.errors}")
```

### Example 2: Complete ICS Processing Pipeline

For complete ICS-to-events processing:

```python
from calendarbot_lite.lite_parser import LiteICSParser
from calendarbot_lite.pipeline import ProcessingContext
from calendarbot_lite.pipeline_stages import create_complete_pipeline

# Create parser and pipeline
parser = LiteICSParser(settings)
pipeline = create_complete_pipeline(parser)

# Process ICS content
context = ProcessingContext(
    raw_content=ics_content,
    source_url="https://example.com/calendar.ics",
    skipped_event_ids={"event-456"},
    event_window_size=100,
    rrule_expansion_days=30
)

result = await pipeline.process(context)

if result.success:
    print(f"Successfully processed {result.events_out} events")
    print(f"Warnings: {len(result.warnings)}")

    for event in context.events:
        print(f"  - {event.subject} at {event.start.date_time}")
else:
    print(f"Processing failed: {result.errors}")
```

### Example 3: Custom Pipeline

Build your own custom pipeline:

```python
from calendarbot_lite.pipeline import EventProcessingPipeline
from calendarbot_lite.pipeline_stages import (
    ParseStage,
    ExpansionStage,
    DeduplicationStage,
    SortStage
)

# Custom pipeline - just parse, expand, dedup, and sort
pipeline = (
    EventProcessingPipeline()
    .add_stage(ParseStage(parser))
    .add_stage(ExpansionStage(parser))
    .add_stage(DeduplicationStage())
    .add_stage(SortStage())
    # Skip filtering and limiting
)

context = ProcessingContext(raw_content=ics_content)
result = await pipeline.process(context)
```

## Factory Functions

Pre-built pipeline configurations are available via factory functions:

### create_basic_pipeline()

Post-processing pipeline for already-parsed events:

```python
from calendarbot_lite.pipeline_stages import create_basic_pipeline

pipeline = create_basic_pipeline()
# Includes: Deduplication → Filtering → Windowing → Limiting
```

### create_complete_pipeline(parser)

Complete ICS processing pipeline:

```python
from calendarbot_lite.pipeline_stages import create_complete_pipeline

parser = LiteICSParser(settings)
pipeline = create_complete_pipeline(parser)
# Includes all 7 stages: Parse → Expand → Dedup → Sort → Filter → Window → Limit
```

## Creating Custom Stages

To create your own pipeline stage, implement the `EventProcessor` protocol:

```python
from calendarbot_lite.pipeline import EventProcessor, ProcessingContext, ProcessingResult

class MyCustomStage:
    """Custom stage description."""

    def __init__(self):
        self._name = "MyCustomStage"

    @property
    def name(self) -> str:
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events)
        )

        try:
            # Your processing logic here
            processed_events = []
            for event in context.events:
                # Transform/filter event
                if should_include(event):
                    processed_events.append(event)

            context.events = processed_events
            result.events = processed_events
            result.events_out = len(processed_events)
            result.success = True

            return result

        except Exception as e:
            result.add_error(f"Processing failed: {e}")
            return result
```

Then use it in a pipeline:

```python
pipeline = (
    EventProcessingPipeline()
    .add_stage(ParseStage(parser))
    .add_stage(MyCustomStage())  # Your custom stage
    .add_stage(DeduplicationStage())
)
```

## Logging and Observability

The pipeline provides comprehensive logging at each stage:

```
INFO  Starting pipeline with 7 stages
DEBUG Executing stage 1/7: Parse
INFO  Parsed 25 events from ICS content (12458 bytes)
INFO  Stage 1/7 (Parse) completed: success=True, events_in=0, events_out=25, warnings=0, errors=0

DEBUG Executing stage 2/7: RRULEExpansion
INFO  RRULE expansion: 25 → 47 events (22 instances generated)
INFO  Stage 2/7 (RRULEExpansion) completed: success=True, events_in=25, events_out=47, warnings=0, errors=0

DEBUG Executing stage 3/7: Deduplication
WARNING [Deduplication] Removed 2 duplicate events
INFO  Stage 3/7 (Deduplication) completed: success=True, events_in=47, events_out=45, warnings=1, errors=0

INFO  Pipeline completed successfully: 45 events, 1 warnings
```

## Error Handling

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

## Testing Pipeline Stages

Each stage can be tested in isolation:

```python
import pytest
from calendarbot_lite.pipeline import ProcessingContext
from calendarbot_lite.pipeline_stages import DeduplicationStage

@pytest.mark.asyncio
async def test_deduplication():
    # Create test events with duplicates
    event1 = create_event("event-1", "Meeting")
    event2 = create_event("event-1", "Meeting")  # Duplicate

    context = ProcessingContext(events=[event1, event2])
    stage = DeduplicationStage()
    result = await stage.process(context)

    assert result.success
    assert result.events_out == 1  # Duplicate removed
    assert len(context.events) == 1
```

## Performance Considerations

- **Stage Ordering**: Place filtering stages early to reduce work for downstream stages
- **Memory**: Use streaming parser for large ICS files (handled by ParseStage)
- **Parallelization**: Future enhancement could run independent stages in parallel
- **Caching**: Consider caching parsed events to avoid re-parsing

## Migration Guide

### Migrating Existing Code

**Before** (manual processing):
```python
# Fetch ICS
response = await fetcher.fetch_ics(source)
ics_content = response.content

# Parse
parser = LiteICSParser(settings)
parse_result = parser.parse_ics_content_optimized(ics_content)
events = parse_result.events

# Manual deduplication
unique_events = {}
for event in events:
    if event.id not in unique_events:
        unique_events[event.id] = event
events = list(unique_events.values())

# Manual sorting
events = sorted(events, key=lambda e: e.start.date_time)

# Manual filtering
events = [e for e in events if e.id not in skipped_ids]
```

**After** (pipeline):
```python
pipeline = create_complete_pipeline(parser)

context = ProcessingContext(
    raw_content=ics_content,
    skipped_event_ids=skipped_ids
)

result = await pipeline.process(context)
events = context.events
```

## Future Enhancements

Potential future stages:

1. **ValidationStage** - Validate event data quality
2. **EnrichmentStage** - Add AI-generated summaries or metadata
3. **CachingStage** - Cache parsed events for performance
4. **NotificationStage** - Trigger notifications for new events
5. **TransformStage** - Convert to different event formats
6. **AggregationStage** - Combine events from multiple sources

## References

- **Implementation**: `calendarbot_lite/pipeline.py`
- **Stages**: `calendarbot_lite/pipeline_stages.py`
- **Tests**: `tests/lite/test_pipeline.py`
- **Flow Documentation**: `EVENT_PROCESSING_FLOW.md`
