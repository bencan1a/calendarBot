# CalendarBot Lite: Algorithm Documentation

This document provides high-level overviews of the key algorithms in CalendarBot Lite, explaining their purpose, design decisions, and how they handle edge cases.

**Target Audience:** Contributors, maintainers, and developers onboarding to the codebase.

**Last Updated:** 2025-11-05

---

## Table of Contents

1. [RRULE Expansion Logic](#1-rrule-expansion-logic)
2. [Event Deduplication Algorithm](#2-event-deduplication-algorithm)
3. [Timezone Handling Logic](#3-timezone-handling-logic)
4. [Streaming Parser State Machine](#4-streaming-parser-state-machine)
5. [Status Mapping Logic](#5-status-mapping-logic)

---

## 1. RRULE Expansion Logic

**File:** [calendarbot_lite/lite_rrule_expander.py](../calendarbot_lite/lite_rrule_expander.py)

### Purpose
Converts recurring event patterns (RRULE) from RFC 5545 into individual event instances, enabling Alexa to query "what's on my calendar today" and get accurate results.

### High-Level Overview

```
Master Event: "Team Meeting (FREQ=WEEKLY;BYDAY=MO)"
           ↓
    [RRULE Expander]
           ↓
Individual Instances:
  - 2025-11-04 Team Meeting
  - 2025-11-11 Team Meeting
  - 2025-11-18 Team Meeting
  - ... (up to expansion window)
```

### Key Design Decisions

1. **Infinite vs Finite Events**
   - **Finite events** (with COUNT/UNTIL): Expand from master event start date
   - **Infinite events** (no COUNT/UNTIL): Start expansion from max(now - 7 days, master_start)
   - **Why:** Old infinite recurring events would generate thousands of past occurrences, hitting limits before reaching current dates (DATA LOSS bug)

2. **Expansion Window**
   - Default: 365 days forward from current time
   - Configurable via `expansion_days_window` setting
   - **Why:** Balance between comprehensive calendar view and memory constraints on Pi Zero 2W

3. **EXDATE Handling**
   - Excludes specific dates from expansion (e.g., cancelled instances)
   - Supports timezone-aware matching with 1-minute tolerance
   - **Why:** Users reschedule or cancel individual recurring instances

4. **Async Streaming Architecture**
   - Yields events one-by-one instead of materializing full list
   - Cooperative multitasking with `asyncio.sleep(0)` every 50 events
   - **Why:** Prevents blocking on Pi Zero 2W for large recurring series

5. **Time Budget & Limits**
   - Max 250 occurrences per rule (configurable)
   - 200ms time budget per expansion (configurable)
   - **Why:** DoS protection against malicious/malformed RRULE patterns

### Edge Cases

- **RECURRENCE-ID instances** (moved meetings): Added to EXDATE list to suppress normal expansion
- **All-day events**: Duration = 1 day instead of 1 hour
- **Timezone-aware EXDATE**: Preserves TZID parameter for correct matching
- **Missing DTEND**: Uses DURATION if present, otherwise defaults to 1 hour

### RFC 5545 Compliance
Delegates core RRULE parsing to `python-dateutil.rrule` library for RFC 5545 compliance.

---

## 2. Event Deduplication Algorithm

**File:** [calendarbot_lite/lite_event_merger.py](../calendarbot_lite/lite_event_merger.py)

### Purpose
Removes duplicate events and handles RECURRENCE-ID overrides (moved recurring instances) to ensure clean, accurate calendar data.

### High-Level Overview

```
Input: Original events + Expanded recurring instances
         ↓
[Phase 1: Collect RECURRENCE-ID Overrides]
         ↓
[Phase 2: Suppress Overridden Expanded Occurrences]
         ↓
[Phase 3: Merge Original + Filtered Expanded]
         ↓
[Phase 4: Deduplicate by UID + Time + RECURRENCE-ID]
         ↓
Output: Clean event list with overrides properly handled
```

### Key Design Decisions

1. **RECURRENCE-ID Override Processing**
   - **Problem:** When a user moves a recurring meeting, the ICS file contains:
     - Original master event with RRULE
     - Modified instance with RECURRENCE-ID pointing to original time
   - **Solution:** Suppress the expanded occurrence matching the RECURRENCE-ID time
   - **Why:** Without this, users see both the original and moved meeting

2. **Deduplication Key**
   - Uses tuple: `(UID, subject, start_time, end_time, is_all_day, recurrence_id)`
   - **Why each field:**
     - `UID`: Different events with same time (e.g., two separate recurring series)
     - `recurrence_id`: Modified instances must not be deduplicated with master

3. **Performance Optimization**
   - Hash-based set lookups: O(n) complexity
   - Pre-computed keys to minimize attribute access
   - **Why:** Deduplication runs on every calendar fetch (frequently)

### Edge Cases

- **Multiple RECURRENCE-ID instances**: Each has unique recurrence_id in deduplication key
- **Events with same UID but different times**: Kept (different instances)
- **Recurring masters that failed expansion**: Kept in output (preserved for debugging)

---

## 3. Timezone Handling Logic

**File:** [calendarbot_lite/timezone_utils.py](../calendarbot_lite/timezone_utils.py)

### Purpose
Converts between timezone representations (Windows names, IANA identifiers, UTC offsets) and ensures consistent timezone handling across the application.

### High-Level Overview

```
Input: Timezone string (various formats)
         ↓
[Strategy 1: Windows → IANA mapping]
         ↓ (if not found)
[Strategy 2: Alias resolution (US/Pacific → America/Los_Angeles)]
         ↓ (if not found)
[Strategy 3: Validate with zoneinfo]
         ↓ (if not found)
[Strategy 4: Fallback to Pacific time]
         ↓
Output: Canonical IANA timezone identifier
```

### Key Design Decisions

1. **Comprehensive Windows Timezone Mapping**
   - **Why needed:** Microsoft Outlook/Exchange ICS files use Windows timezone names
   - **Examples:**
     - "Pacific Standard Time" → "America/Los_Angeles"
     - "Eastern Standard Time" → "America/New_York"
   - **Coverage:** ~100 timezone mappings worldwide

2. **Never Fallback to UTC**
   - **Default fallback:** "America/Los_Angeles" (Pacific time)
   - **Why:** This is a personal calendar app for a US user; UTC would show wrong times
   - **Design decision:** Better to be wrong consistently than randomly wrong

3. **DST Auto-Correction**
   - Detects when provided UTC offset doesn't match actual DST status
   - Example: "2025-03-15T10:00:00-08:00" (PST) but March 15 is PDT (-07:00)
   - Automatically corrects to proper Pacific timezone with DST
   - **Why:** Handles test time overrides with incorrect timezone offsets

4. **Timezone Alias Resolution**
   - Handles obsolete/deprecated IANA names (e.g., "US/Pacific" → "America/Los_Angeles")
   - **Why:** Older ICS files or legacy systems use deprecated timezone names

### Edge Cases

- **Test time overrides** via `CALENDARBOT_TEST_TIME` environment variable
- **Naive datetimes**: Assumed to be in server timezone, then converted to UTC
- **Invalid timezone identifiers**: Fall back to Pacific time with warning log

---

## 4. Streaming Parser State Machine

**File:** [calendarbot_lite/lite_streaming_parser.py](../calendarbot_lite/lite_streaming_parser.py)

### Purpose
Parses large ICS files (up to 50MB) in memory-efficient chunks without loading entire file, critical for Pi Zero 2W's limited RAM (~500MB total).

### High-Level Overview

```
HTTP Response Byte Stream
         ↓
[Incremental UTF-8 Decoder]
         ↓
[Line Folding Handler] ← RFC 5545: Lines can be folded with leading whitespace
         ↓
[Event Boundary Detection] ← BEGIN:VEVENT / END:VEVENT
         ↓
[Parse Complete Event with icalendar library]
         ↓
[Memory-Bounded Buffer] ← Max 1000 events
         ↓
Yield LiteCalendarEvent instances
```

### Key Design Decisions

1. **Chunk-Based Processing**
   - **Chunk size:** 8KB (configurable)
   - **Why:** Balance between I/O efficiency and memory usage
   - **Challenge:** Must handle boundaries:
     - Line breaks mid-chunk
     - Event boundaries mid-chunk
     - Line folding across chunks

2. **Line Folding Across Chunks**
   - **RFC 5545:** Long lines can be folded with CRLF + whitespace
   - **Example:**
     ```
     DESCRIPTION:This is a very long description that spans multiple
      lines and is folded with leading whitespace
     ```
   - **Solution:** `_pending_folded_line` buffer tracks incomplete folded sequences
   - **Why:** Ensures long DESCRIPTION/SUMMARY fields are parsed correctly

3. **Event Boundary Handling**
   - Buffers event lines until `END:VEVENT` detected
   - Only then parses complete event with icalendar library
   - **Why:** icalendar library requires complete VEVENT blocks

4. **DoS Protection (CWE-835)**
   - **Iteration limit:** 10,000 iterations max
   - **Time limit:** 30 seconds wall-clock time
   - **Why:** Prevents infinite loops from malformed/malicious ICS files
   - **Logged as:** SECURITY events for audit trail

5. **Duplicate Detection**
   - Tracks UIDs + RECURRENCE-IDs during streaming
   - Detects when same event appears multiple times (network corruption)
   - **Circuit breaker:** Terminates parsing if corruption threshold exceeded
   - **Why:** Network issues can cause corrupted responses with repeated events

6. **Memory-Bounded Buffer**
   - Max 1000 events stored (configurable)
   - Stops accepting events after limit, continues streaming to detect corruption
   - **Why:** Pi Zero 2W has ~100MB RAM budget; 1000 events ≈ 10MB

### Edge Cases

- **Incomplete events at EOF**: Logged as error, not yielded
- **Malformed events**: Logged as warning, parsing continues
- **Empty chunks**: Skipped, parsing continues
- **UTF-8 decode errors**: `errors='replace'` substitutes � character

### Performance Considerations
- **Memory:** Constant ~10MB regardless of file size (streaming + bounded buffer)
- **CPU:** Minimal overhead on Pi Zero 2W; yields to event loop every 50 events

---

## 5. Status Mapping Logic

**File:** [calendarbot_lite/lite_event_parser.py](../calendarbot_lite/lite_event_parser.py):150-246

### Purpose
Maps iCalendar TRANSP/STATUS properties and Microsoft-specific markers to CalendarBot's internal status enum (BUSY, FREE, TENTATIVE) for accurate free/busy queries.

### High-Level Overview

```
Input: TRANSP, STATUS, X-MICROSOFT-* properties
         ↓
[Priority-Based Rule Evaluation]
         ↓
Output: LiteEventStatus (BUSY | FREE | TENTATIVE)
```

### Priority-Ordered Rules

The algorithm evaluates rules in strict priority order (first match wins):

| Priority | Condition | Result | Rationale |
|----------|-----------|--------|-----------|
| 1 | `X-OUTLOOK-DELETED=TRUE` | FREE | Microsoft phantom events (deleted but still in ICS) |
| 2 | `X-MICROSOFT-CDO-BUSYSTATUS=FREE` (non-Following) | FREE | Microsoft busy status override |
| 3 | `X-MICROSOFT-CDO-BUSYSTATUS=FREE` + Following | TENTATIVE | Following meetings show as tentative |
| 4 | `STATUS=CANCELLED` | FREE | Standard iCalendar cancelled events |
| 5 | `STATUS=TENTATIVE` | TENTATIVE | Standard iCalendar tentative events |
| 6 | `TRANSP=TRANSPARENT` + `STATUS=CONFIRMED` | TENTATIVE | Special case: transparent but confirmed |
| 7 | `TRANSP=TRANSPARENT` | FREE | Standard iCalendar free time |
| 8 | `SUMMARY` contains "Following:" | TENTATIVE | Calendar keyword for follow-up items |
| Default | None of above | BUSY | Standard opaque/confirmed events |

### Key Design Decisions

1. **Microsoft Vendor Extensions**
   - **Problem:** Outlook/Exchange uses proprietary properties not in RFC 5545
   - **Solution:** Check Microsoft-specific markers at highest priority
   - **Examples:**
     - `X-OUTLOOK-DELETED`: Deleted events that still appear in ICS feed
     - `X-MICROSOFT-CDO-BUSYSTATUS`: Overrides standard TRANSP property

2. **Priority-Based Rules (Refactored in Issue #58)**
   - **Old approach:** Nested if/else with guard clauses (hard to understand)
   - **New approach:** Table of `(condition, result, rule_name)` tuples
   - **Benefits:**
     - Clear evaluation order
     - Easy to add/remove rules
     - Self-documenting with rule names
     - Better logging for debugging

3. **"Following:" Meeting Heuristic**
   - **Pattern:** Users create "Following: <topic>" placeholder events
   - **Behavior:** Treat as tentative (less urgent than busy)
   - **Why:** Domain-specific knowledge for this user's calendar patterns

4. **TRANSPARENT + CONFIRMED Special Case**
   - **Problem:** Some calendar clients mark confirmed events as transparent
   - **Solution:** Map to TENTATIVE instead of FREE
   - **Why:** Prevents important events from being treated as free time

### Edge Cases

- **Multiple Microsoft markers present**: Deletion marker takes highest priority
- **Missing TRANSP property**: Defaults to OPAQUE per RFC 5545
- **Case sensitivity**: All string comparisons use `.upper()` for consistency
- **No STATUS property**: Falls through to TRANSP or default evaluation

### RFC 5545 Compliance

Standard iCalendar properties:
- `TRANSP`: OPAQUE (default, shows as busy) | TRANSPARENT (free time)
- `STATUS`: TENTATIVE | CONFIRMED | CANCELLED

Microsoft extensions are vendor-specific and not part of RFC 5545.

---

## References

- **RFC 5545:** Internet Calendaring and Scheduling Core Object Specification (iCalendar)
- **Python-dateutil:** RRULE parsing library (RFC 5545 compliant)
- **icalendar:** Python iCalendar library for ICS parsing

---

## Contributing

When modifying these algorithms:

1. **Update this documentation** if you change core behavior
2. **Add edge case comments** in the code itself
3. **Write tests** for new edge cases
4. **Consider resource constraints**: Pi Zero 2W has ~100MB RAM budget, 1GHz CPU

---

**For detailed implementation details**, see the source files referenced at the start of each section.
