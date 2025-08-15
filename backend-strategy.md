# Backend Logic Modification Strategy

## Target: `WhatsNextLogic._group_events()` Method

### Current Issue (Line 137)
```python
return current_events[:1], upcoming_events, later_events
```
**Problem**: Returns current meetings first, establishing wrong priority

### Solution Strategy

#### 1. Replace Priority Logic
**Current Logic**: 
- Priority 1: Current meetings (happening now)
- Priority 2: Upcoming meetings 
- Priority 3: Later meetings

**New Logic**:
- Priority 1: **Next upcoming meetings** (chronologically next)
- Priority 2: Current meetings (only if no upcoming meetings)
- Priority 3: Later meetings (unchanged)

#### 2. Leverage Existing Code
**Use `find_next_upcoming_event()` Logic**:
- Lines 179-264 already implement correct "next meeting" selection
- Handles hidden events filtering correctly
- Returns chronologically next upcoming event
- Can extract this logic into reusable method

#### 3. Specific Code Changes

**Step 1: Extract Next Meeting Selection Logic**
```python
def _find_primary_meeting(self, events: list[CachedEvent], current_time: datetime) -> Optional[CachedEvent]:
    """Find the primary meeting to display - prioritizes next upcoming over current.
    
    Args:
        events: List of cached events
        current_time: Current time reference
        
    Returns:
        Primary meeting to display or None
    """
    # Apply hidden events filter (reuse existing logic from find_next_upcoming_event)
    visible_events = self._filter_hidden_events(events)
    
    # Find next upcoming meeting (not started yet)
    upcoming_events = [e for e in visible_events if e.start_dt > current_time]
    if upcoming_events:
        upcoming_events.sort(key=lambda e: e.start_dt)
        return upcoming_events[0]
    
    # Fallback to current meeting if no upcoming meetings exist
    current_events = [e for e in visible_events if e.is_current()]
    if current_events:
        return current_events[0]
        
    return None
```

**Step 2: Update `_group_events()` Method**
```python
def _group_events(
    self, events: list[CachedEvent], current_time: datetime
) -> tuple[list[CachedEvent], list[CachedEvent], list[CachedEvent]]:
    """Group events with NEXT meeting priority logic.
    
    Returns:
        Tuple of (primary_meeting_list, remaining_upcoming, later_events)
    """
    if not events:
        return [], [], []

    # Find primary meeting using new priority logic
    primary_meeting = self._find_primary_meeting(events, current_time)
    
    # Filter out hidden events for remaining logic
    visible_events = self._filter_hidden_events(events)
    
    # Build remaining upcoming events (exclude primary meeting)
    upcoming_events = [e for e in visible_events if e.start_dt > current_time]
    upcoming_events.sort(key=lambda e: e.start_dt)
    
    if primary_meeting and primary_meeting in upcoming_events:
        # Remove primary from upcoming list
        upcoming_events = [e for e in upcoming_events if e.graph_id != primary_meeting.graph_id]
    
    # Later events remain unchanged
    later_events = upcoming_events[3:] if len(upcoming_events) > 3 else []
    
    # Return in expected format
    primary_list = [primary_meeting] if primary_meeting else []
    return primary_list, upcoming_events[:3], later_events
```

#### 4. Maintain API Contract
**Preserve Return Structure**:
- `tuple[list[CachedEvent], list[CachedEvent], list[CachedEvent]]`
- First list contains primary meeting (next or current)
- Second list contains remaining upcoming meetings  
- Third list contains later meetings

**Preserve Integration Points**:
- `create_view_model()` method unchanged
- `WhatsNextViewModel` structure unchanged
- API endpoint `/api/whats-next/data` response unchanged

#### 5. Hidden Events Handling
**Extract Reusable Filter Method**:
```python
def _filter_hidden_events(self, events: list[CachedEvent]) -> list[CachedEvent]:
    """Filter out hidden events using existing logic from find_next_upcoming_event."""
    # Reuse existing hidden events filtering logic (lines 192-245)
    # Handle both fresh settings and fallback settings
    # Return filtered events list
```

### Implementation Benefits

1. **Leverages Existing Code**: Uses proven `find_next_upcoming_event()` logic
2. **Maintains Contracts**: No API or data structure changes required
3. **Simple Change**: Single method modification with helper extraction
4. **Preserves Features**: Hidden events filtering, timezone handling intact
5. **Testable**: Clear separation of concerns for unit testing

### Risk Mitigation

1. **Backward Compatibility**: Not needed (single user app)
2. **Performance**: No degradation (same filtering logic)
3. **Timezone Issues**: Preserve existing `current_time` parameter usage
4. **Edge Cases**: Handle empty events list, no upcoming meetings scenarios

### Testing Requirements

1. **Unit Tests for `_find_primary_meeting()`**:
   - Next meeting exists: returns next meeting
   - No upcoming meetings: returns current meeting  
   - No meetings at all: returns None
   - Hidden events filtered correctly

2. **Unit Tests for Modified `_group_events()`**:
   - Primary meeting in first position
   - Remaining upcoming events correct
   - Later events unchanged
   - Tuple structure preserved

3. **Integration Tests**:
   - API endpoint returns correct meeting priority
   - View model generation works with new logic
   - Countdown timer receives correct meeting

### Dependencies

**Must Complete Before**:
- Backend unit tests for new logic
- Integration tests for API contract

**Must Complete After**:
- Frontend changes to handle new meeting priority
- Browser testing for countdown functionality