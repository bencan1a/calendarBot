# WhatsnextView Architecture Analysis

## Current Implementation Analysis

### Core Problem Statement
WhatsnextView currently prioritizes **current meetings** over **next meetings** for display, but requirements specify that **next meetings** should always be prioritized regardless of current meeting status.

### Critical Code Locations

#### Backend Issue - `whats_next_logic.py:137`
```python
return current_events[:1], upcoming_events, later_events
```
**Problem**: Returns current_events first in tuple, establishing wrong priority

#### Frontend Issue - `whats-next-view.js:1794-1807`
```javascript
// Check if meeting is currently happening
if (now >= meetingStart && now <= meetingEnd) {
    currentMeeting = meeting;
    break;
}
// Check if meeting is upcoming  
if (meetingStart > now) {
    currentMeeting = meeting;
    break;
}
```
**Problem**: Checks current meetings first, exits early without considering next meetings

### Existing Correct Logic Available

#### Backend - `find_next_upcoming_event()` at lines 179-264
- **Already implements correct "next meeting" logic**
- Filters hidden events properly
- Returns chronologically next upcoming event
- Can be leveraged for the fix

### Data Flow Architecture

```mermaid
graph TD
    A[Calendar Sources] --> B[WhatsNextLogic._group_events]
    B --> C[create_view_model]
    C --> D[/api/whats-next/data endpoint]
    D --> E[WhatsNextStateManager.loadData]
    E --> F[Frontend detectCurrentMeeting]
    F --> G[UI Display]
    
    B1[find_next_upcoming_event] -.-> B
    
    style B fill:#ffcccc
    style F fill:#ffcccc
    style B1 fill:#ccffcc
```

### Current Meeting Selection Logic

#### Backend Priority (WRONG):
1. Current meetings (happening now)
2. Next upcoming meetings
3. Later meetings

#### Frontend Priority (WRONG):
1. Current meetings (happening now) 
2. Next upcoming meetings

#### Required Priority (CORRECT):
1. **Next upcoming meetings (chronologically next)**
2. Current meetings (only if no upcoming meetings exist)

### API Data Structures (PRESERVE)
- Event objects: `{graph_id, title, start_time, end_time, location, description, is_hidden}`
- View model: `WhatsNextViewModel` structure maintained
- JSON response format maintained
- Timezone handling preserved

### Integration Points
1. **Backend-Frontend**: `/api/whats-next/data` JSON contract
2. **State Management**: WhatsNextStateManager event handling
3. **UI Updates**: Countdown timer integration
4. **Event Filtering**: Hidden events system

### Risk Areas
1. **Timezone Calculations**: Must preserve existing timezone-aware time handling
2. **Countdown Logic**: Must work with next meeting start times vs current meeting end times  
3. **Consecutive Meetings**: Back-to-back meeting edge cases
4. **Performance**: Maintain existing optimization patterns

### Testing Requirements
1. **Unit Tests**: Backend `_group_events()` and `find_next_upcoming_event()`
2. **Integration Tests**: API endpoint data flow
3. **Frontend Tests**: Meeting selection logic and state manager
4. **Browser Tests**: UI countdown and meeting display
5. **Edge Case Tests**: Consecutive meetings, timezone boundaries, hidden events

### Implementation Approach
- **NO BACKWARD COMPATIBILITY** needed (single user application)
- **COMPLETE REPLACEMENT** of meeting selection logic
- **PRESERVE** all existing API contracts and data structures
- **LEVERAGE** existing `find_next_upcoming_event()` logic

## Key Constraints
- Maintain 480×800 display layout
- Preserve existing CSS styling  
- Keep countdown timer functionality
- Maintain timezone handling
- Preserve event filtering system
- No migration strategy required