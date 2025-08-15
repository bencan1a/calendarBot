# API Data Structure Preservation Requirements

## Critical API Contracts That MUST Be Preserved

### 1. `/api/whats-next/data` JSON Response Structure

**Endpoint**: `POST /api/whats-next/data`

**Current Response Format** (MUST MAINTAIN):
```json
{
    "events": [
        {
            "graph_id": "string",
            "title": "string", 
            "start_time": "ISO-8601-datetime",
            "end_time": "ISO-8601-datetime",
            "location": "string|null",
            "description": "string|null",
            "is_hidden": "boolean"
        }
    ],
    "layout_name": "whats-next-view",
    "last_updated": "ISO-8601-datetime",
    "layout_config": {
        "showHiddenEvents": "boolean",
        "maxEvents": "number",
        "timeFormat": "string"
    }
}
```

**Preservation Requirements**:
- Event object structure MUST remain identical
- All field names and types MUST be preserved
- `graph_id` field MUST remain primary identifier
- `is_hidden` boolean MUST continue to work for event filtering
- ISO-8601 datetime format MUST be maintained for timezone compatibility

### 2. Backend `WhatsNextLogic._group_events()` Return Structure

**Current Signature** (MUST MAINTAIN):
```python
def _group_events(
    self, events: list[CachedEvent], current_time: datetime
) -> tuple[list[CachedEvent], list[CachedEvent], list[CachedEvent]]:
```

**Return Tuple Structure** (MUST PRESERVE):
- `(primary_events, upcoming_events, later_events)`
- Position 0: Primary meeting list (length 0 or 1)
- Position 1: Remaining upcoming meetings (max 3)  
- Position 2: Later meetings (remaining after first 3 upcoming)

**Critical Contract Points**:
- Tuple structure and positions MUST NOT change
- List types MUST remain `list[CachedEvent]`
- First list MUST contain 0 or 1 events (primary meeting)
- Second list MUST contain filtered upcoming events
- Third list MUST contain later events as before

### 3. `WhatsNextViewModel` Data Structure

**Current Structure** (MUST MAINTAIN):
```python
@dataclass
class WhatsNextViewModel:
    current_time: datetime
    display_date: str
    next_events: list[EventData]      # From upcoming_events[:3]
    current_events: list[EventData]   # From current_events[:1] -> primary_events
    later_events: list[EventData]     # From upcoming_events[3:8] -> later_events
    status_info: StatusInfo
```

**Field Mapping Changes** (Internal Only):
- `current_events`: Now populated from `primary_events` (could be next OR current)
- `next_events`: Now populated from remaining `upcoming_events[:3]`  
- `later_events`: Unchanged from `later_events`

**External Contract Preservation**:
- Field names MUST remain identical
- Data types MUST remain unchanged
- Frontend receives same structure regardless of internal logic changes

### 4. `EventData` Object Structure

**Current Structure** (MUST MAINTAIN):
```python
@dataclass
class EventData:
    graph_id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    description: Optional[str]
    time_until_start: Optional[str]
    time_until_end: Optional[str]
    is_current: bool
    formatted_time_range: str
```

**Preservation Requirements**:
- All field names and types MUST be preserved
- `from_cached_event()` class method MUST continue to work
- Timezone-aware datetime fields MUST be maintained
- `formatted_time_range` MUST continue to provide timezone-correct display

### 5. Frontend Global Variables (Backward Compatibility)

**Global State Variables** (MUST MAINTAIN):
```javascript
let currentMeeting = null;           // Meeting object or null
let upcomingMeetings = [];           // Array of meeting objects  
let lastDataUpdate = null;           // Date object
```

**Structure Requirements**:
- `currentMeeting`: Object with same fields (graph_id, title, start_time, end_time, location, description)
- `upcomingMeetings`: Array of meeting objects with consistent structure
- Field access patterns MUST remain functional: `currentMeeting.title`, `currentMeeting.start_time`, etc.

### 6. WhatsNextStateManager Interface

**Public Methods** (MUST MAINTAIN):
```javascript
class WhatsNextStateManager {
    async loadData()                    // Returns data object
    getState()                         // Returns state object  
    getEvents()                        // Returns events array
    async hideEvent(graphId)           // Returns boolean success
    async unhideEvent(graphId)         // Returns boolean success
    addEventListener(type, callback)    // Event registration
    removeEventListener(type, callback) // Event removal
}
```

**Event Types** (MUST PRESERVE):
- `'stateChanged'`: Fired on state updates
- `'dataLoaded'`: Fired after successful data load
- `'eventHidden'`: Fired after event hide operation
- `'eventUnhidden'`: Fired after event unhide operation  
- `'error'`: Fired on error conditions

### 7. Hidden Events API Endpoints

**Hide Event Endpoint** (MUST MAINTAIN):
```
POST /api/events/hide
Content-Type: application/json
Body: {"graph_id": "string"}
Response: {"success": boolean, "events": [...]}
```

**Unhide Event Endpoint** (MUST MAINTAIN):
```
POST /api/events/unhide  
Content-Type: application/json
Body: {"graph_id": "string"}
Response: {"success": boolean, "events": [...]}
```

## Implementation Strategy for Contract Preservation

### 1. Internal Logic Changes Only
- Modify internal meeting selection priority ONLY
- Keep all external interfaces identical
- Change what goes into `primary_events` but not the structure

### 2. Data Flow Mapping
```
OLD: current_events[:1] -> current_events field -> "current meeting" display
NEW: primary_events[:1] -> current_events field -> "next meeting" display
```

**Critical**: Frontend receives same field name (`current_events`) but with different semantic meaning

### 3. Testing Strategy for Contract Preservation

**API Contract Tests**:
- Verify JSON response structure unchanged
- Validate all field names and types preserved  
- Confirm event object structure identical
- Test `graph_id` field functionality

**Interface Tests**:
- Verify `_group_events()` tuple structure preserved
- Confirm `WhatsNextViewModel` field names unchanged
- Test global variable backward compatibility
- Validate state manager interface unchanged

**Integration Tests**:
- Test hidden events API endpoints unchanged
- Verify countdown timer receives expected data structure
- Confirm event filtering works with preserved `is_hidden` field

### 4. Documentation Updates Required

**API Documentation**:
- Update semantic meaning: "`current_events` field now contains primary meeting (next or current)"
- Clarify business logic change while preserving technical contract
- Document that external structure remains identical

**Internal Documentation**:
- Map old field semantics to new field semantics
- Document internal logic changes vs external interface preservation
- Clarify data flow changes for maintenance teams

## Risk Mitigation

1. **Breaking Changes Prevention**: All external contracts preserved exactly
2. **Regression Testing**: Comprehensive tests for all preserved interfaces
3. **Gradual Rollout**: Backend changes first, then frontend alignment
4. **Fallback Strategy**: Can revert internal logic while keeping interfaces intact

## Success Criteria

✅ **Zero Breaking Changes**: All existing API contracts function identically
✅ **Semantic Correctness**: Internal logic matches requirements (next meeting priority)  
✅ **Backward Compatibility**: Existing global variables and methods work unchanged
✅ **Data Integrity**: All field types, names, and structures preserved exactly