# Deduplication Performance Optimization

## Overview

This document describes the deduplication optimization work done to ensure O(n) complexity and meet performance targets for CalendarBot Lite.

## Problem Statement (from Issue)

**Original Issue:** Inefficient deduplication algorithm has O(n²) complexity for large calendars. Causes slow response times on calendars with many events.

**Target:** Deduplication <50ms for 1000 events with O(n) complexity

## Analysis Results

Upon investigation, the current implementations were **already O(n)** and performant:

### Current Performance (Baseline)

| Implementation | 1000 Events | 5000 Events | Complexity |
|----------------|-------------|-------------|------------|
| `LiteEventMerger.deduplicate_events()` | ~2.2ms | ~11.8ms | O(n) ✓ |
| `DeduplicationStage.process()` | ~0.24ms | ~1.4ms | O(n) ✓ |

**Target Status:** ✅ Already meeting target of <50ms for 1000 events

## Implementation Details

### Two Deduplication Implementations

1. **`LiteEventMerger.deduplicate_events()`** (calendarbot_lite/lite_event_merger.py)
   - Used for comprehensive deduplication during event parsing
   - Creates tuple keys with: (uid, subject, start_iso, end_iso, is_all_day, recurrence_id)
   - Handles RECURRENCE-ID overrides for recurring events
   - More thorough but slightly slower (~2.2ms for 1000 events)

2. **`DeduplicationStage.process()`** (calendarbot_lite/pipeline_stages.py)
   - Used in event processing pipeline
   - Simpler dict-based approach keyed only by event.id
   - Keeps events with more complete information
   - Faster for UID-only deduplication (~0.24ms for 1000 events)

### Algorithm Complexity

Both implementations use **O(n) hash-based lookups**:

```python
# O(n) approach using set/dict
seen = set()  # or dict
for event in events:  # O(n)
    key = create_key(event)  # O(1)
    if key not in seen:  # O(1) average case for hash lookup
        seen.add(key)  # O(1)
        deduplicated.append(event)
```

**Why not O(n²)?**
- No nested loops over events
- Hash-based set/dict lookups are O(1) average case
- Total complexity: O(n) * O(1) = O(n)

## Optimizations Applied

### 1. Documentation Updates
- Added explicit O(n) complexity guarantees in docstrings
- Documented performance characteristics and targets
- Added usage examples

### 2. Performance Tests
Created comprehensive test suite in `tests/lite/performance/test_deduplication_performance.py`:

- `test_deduplicate_events_large_calendar_target`: Verifies <50ms for 1000 events
- `test_deduplicate_linear_complexity`: Confirms O(n) scaling behavior
- `test_deduplicate_no_duplicates_overhead`: Best-case performance
- `test_deduplicate_many_duplicates`: High duplicate rate handling
- `test_pipeline_dedupe_target`: Pipeline-specific performance
- Tests for 100, 500, 1000, 2000, 5000 event calendars

### 3. Linear Complexity Verification

The tests verify O(n) complexity by checking that doubling input size roughly doubles execution time:

```python
# If truly O(n): time_2000 / time_1000 ≈ 2.0
# If O(n²): time_2000 / time_1000 ≈ 4.0
ratio = time_2 / time_1
assert 1.5 <= ratio <= 3.0  # Confirms O(n)
```

## Performance Results

### Benchmark Results (with 10% duplicate rate)

| Events | LiteEventMerger | DeduplicationStage | Target | Status |
|--------|-----------------|-------------------|--------|--------|
| 100 | 0.23ms | 0.03ms | - | ✅ |
| 500 | 1.09ms | 0.11ms | - | ✅ |
| **1000** | **2.21ms** | **0.24ms** | **<50ms** | ✅ |
| 2000 | 4.40ms | 0.48ms | - | ✅ |
| 5000 | 11.79ms | 1.37ms | - | ✅ |

### Throughput

- LiteEventMerger: ~450,000 events/sec
- DeduplicationStage: ~4,000,000 events/sec

## Usage Examples

### Using LiteEventMerger

```python
from calendarbot_lite.lite_event_merger import LiteEventMerger

merger = LiteEventMerger()
events = [...] # List of LiteCalendarEvent objects

# Remove duplicates (considers UID, times, subject, recurrence_id)
deduplicated = merger.deduplicate_events(events)
```

### Using DeduplicationStage in Pipeline

```python
from calendarbot_lite.pipeline_stages import DeduplicationStage, create_basic_pipeline

# In a pipeline
pipeline = create_basic_pipeline()
# Pipeline includes DeduplicationStage by default

context = ProcessingContext(events=events)
await pipeline.process(context)
# context.events now deduplicated
```

## Testing

### Run Performance Tests

```bash
# Run all performance tests
pytest tests/lite/performance/test_deduplication_performance.py -v

# Run specific performance markers
pytest -m performance -v

# Run with timing details
pytest tests/lite/performance/test_deduplication_performance.py -v --durations=10
```

### Run Unit Tests

```bash
# Deduplication unit tests
pytest tests/lite/unit/test_lite_event_merger.py -k deduplicate -v

# Pipeline tests
pytest tests/lite/unit/test_pipeline.py -v
```

## Preventing Regressions

### Automated Performance Testing

The performance tests in `test_deduplication_performance.py` will fail if:
- Deduplication takes >50ms for 1000 events
- Complexity appears worse than O(n) (ratio check fails)
- Any size class exceeds its threshold

### Continuous Integration

Add performance tests to CI pipeline:

```yaml
- name: Run Performance Tests
  run: pytest tests/lite/performance/ -v --tb=short
```

## Future Optimizations

While current performance exceeds targets, potential future optimizations include:

1. **Pre-compute datetime ISO strings** during event parsing to avoid repeated `.isoformat()` calls
2. **Parallel deduplication** for very large calendars (>10,000 events)
3. **Streaming deduplication** for memory-constrained environments
4. **Custom hash functions** optimized for event tuple keys

However, these are **not currently needed** given the excellent performance.

## Conclusion

**Status: ✅ COMPLETE**

- Deduplication already uses O(n) algorithms
- Performance target of <50ms for 1000 events is exceeded by 20x (actual: ~2ms)
- Comprehensive performance tests added to prevent regressions
- Documentation updated with complexity guarantees
- Both implementations verified and tested

The deduplication performance is **not a bottleneck** in CalendarBot Lite.
