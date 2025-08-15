# RRULE Expansion System Architecture

## 🏗️ System Overview

This document defines the architecture for integrating RRULE expansion into CalendarBot's ICS parsing system while maintaining separation of concerns and backward compatibility.

## 📐 Architecture Principles

### 1. Separation of Concerns
- **RRuleExpander**: Dedicated class for RRULE processing
- **ICSParser**: Maintains existing responsibilities + RRULE integration
- **CalendarEvent**: Unchanged event model for compatibility

### 2. Modular Design
- Pluggable expansion system
- Configurable enable/disable
- Independent testing of components

### 3. Performance Optimization
- Lazy evaluation where possible
- Date range filtering
- Memory-efficient event generation

## 🔧 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CalendarBot ICS System                   │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      ICSParser                              │
│  ┌─────────────────────────────────────────────────────────┤
│  │ Existing Methods:                                       │
│  │ • parse_ics_content()                                   │
│  │ • _parse_event_component()                              │
│  │ • filter_phantom_recurring_events_conservative()       │
│  └─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┤
│  │ New Integration:                                        │
│  │ • _expand_recurring_events()         [NEW]             │
│  │ • _merge_expanded_events()           [NEW]             │
│  │ • _deduplicate_events()              [NEW]             │
│  └─────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   RRuleExpander                            │
│  ┌─────────────────────────────────────────────────────────┤
│  │ Core Methods:                                           │
│  │ • expand_rrule()                                        │
│  │ • parse_rrule_string()                                  │
│  │ • apply_exdates()                                       │
│  │ • generate_event_instances()                            │
│  │ • filter_by_date_range()                               │
│  └─────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   python-dateutil                          │
│                    (External Library)                       │
│  • rrule, WEEKLY, MO, FR, etc.                             │
│  • Date parsing and timezone handling                       │
└─────────────────────────────────────────────────────────────┘
```

## 🗂️ Module Structure

### New Module: `calendarbot/ics/rrule_expander.py`

```python
class RRuleExpander:
    """Client-side RRULE expansion for CalendarBot."""
    
    def __init__(self, settings: CalendarBotSettings):
        self.settings = settings
        self.expansion_window_days = settings.rrule_expansion_days
        self.enable_expansion = settings.enable_rrule_expansion
    
    def expand_rrule(
        self, 
        master_event: CalendarEvent,
        rrule_string: str,
        exdates: List[str] = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[CalendarEvent]:
        """Expand RRULE pattern into individual event instances."""
        
    def parse_rrule_string(self, rrule_string: str) -> dict:
        """Parse RRULE string into components."""
        
    def apply_exdates(
        self, 
        occurrences: List[datetime], 
        exdates: List[str]
    ) -> List[datetime]:
        """Remove excluded dates from occurrence list."""
        
    def generate_event_instances(
        self, 
        master_event: CalendarEvent,
        occurrences: List[datetime]
    ) -> List[CalendarEvent]:
        """Generate CalendarEvent instances for each occurrence."""
```

### Modified: `calendarbot/ics/parser.py`

```python
class ICSParser:
    """Enhanced ICS parser with RRULE expansion support."""
    
    def __init__(self, settings: CalendarBotSettings):
        self.settings = settings
        self.rrule_expander = RRuleExpander(settings)  # NEW
    
    def parse_ics_content(self, content: str) -> ICSParseResult:
        """Enhanced to include RRULE expansion."""
        # Existing logic...
        
        if self.settings.enable_rrule_expansion:
            expanded_events = self._expand_recurring_events(events)
            events = self._merge_expanded_events(events, expanded_events)
            events = self._deduplicate_events(events)
        
        return ICSParseResult(events=events, ...)
    
    def _expand_recurring_events(
        self, 
        events: List[CalendarEvent]
    ) -> List[CalendarEvent]:
        """NEW: Expand recurring events using RRuleExpander."""
        
    def _merge_expanded_events(
        self, 
        original_events: List[CalendarEvent],
        expanded_events: List[CalendarEvent]
    ) -> List[CalendarEvent]:
        """NEW: Merge expanded events with original events."""
        
    def _deduplicate_events(
        self, 
        events: List[CalendarEvent]
    ) -> List[CalendarEvent]:
        """NEW: Remove duplicate events based on UID and start time."""
```

## 🔄 Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw ICS Data  │ -> │   ICSParser     │ -> │ CalendarEvents  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Extract RRULE   │
                       │ Components      │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ RRuleExpander   │
                       │ - Parse RRULE   │
                       │ - Generate      │
                       │   Occurrences   │
                       │ - Apply EXDATE  │
                       │ - Create Events │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Merge & Dedupe  │
                       │ - Combine with  │
                       │   explicit      │
                       │   VEVENTs       │
                       │ - Remove dupes  │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Final Event     │
                       │ Collection      │
                       └─────────────────┘
```

## 🔧 Integration Points

### 1. Configuration Integration

```python
# calendarbot/config/settings.py
class CalendarBotSettings(BaseSettings):
    # Existing settings...
    
    # RRULE Expansion Settings
    enable_rrule_expansion: bool = Field(
        default=True, 
        description="Enable client-side RRULE expansion"
    )
    rrule_expansion_days: int = Field(
        default=365, 
        description="Days to expand recurring events (default: 1 year)"
    )
    rrule_max_occurrences: int = Field(
        default=1000,
        description="Maximum occurrences per recurring series"
    )
```

### 2. Event Model Integration

```python
# calendarbot/ics/models.py
class CalendarEvent(BaseModel):
    # Existing fields...
    
    # Enhanced for RRULE tracking
    is_expanded_instance: bool = Field(
        default=False, 
        description="True if generated from RRULE expansion"
    )
    rrule_master_uid: Optional[str] = Field(
        default=None,
        description="UID of master recurring event"
    )
```

### 3. Cache Integration

```python
# calendarbot/cache/manager.py
class CacheManager:
    def cache_events(self, api_events: List[CalendarEvent]) -> bool:
        # Existing logic handles expanded events transparently
        # No changes needed - expanded events are regular CalendarEvents
```

## 📊 Performance Considerations

### 1. Memory Optimization
- **Lazy Generation**: Generate events on-demand during date range queries
- **Chunked Processing**: Process large recurring series in chunks
- **Object Pooling**: Reuse CalendarEvent objects where possible

### 2. CPU Optimization
- **Early Filtering**: Apply date range filters before event generation
- **Caching**: Cache parsed RRULE patterns for repeated use
- **Parallel Processing**: Process multiple recurring series concurrently

### 3. Storage Optimization
- **Selective Caching**: Only cache expanded events within active date range
- **Compression**: Compress recurring event metadata for storage

## 🔒 Error Handling Strategy

```python
class RRuleExpansionError(Exception):
    """Base exception for RRULE expansion errors."""
    pass

class RRuleParseError(RRuleExpansionError):
    """Error parsing RRULE string."""
    pass

class RRuleGenerationError(RRuleExpansionError):
    """Error generating event instances."""
    pass

# Graceful degradation:
try:
    expanded_events = self.rrule_expander.expand_rrule(...)
except RRuleExpansionError as e:
    logger.warning(f"RRULE expansion failed: {e}")
    # Continue with original events only
    expanded_events = []
```

## 🧪 Testing Architecture

### 1. Unit Tests
- **RRuleExpander**: Isolated testing of expansion logic
- **ICSParser Integration**: Test parser modifications
- **Configuration**: Test settings integration

### 2. Integration Tests
- **End-to-End**: Full ICS parsing with RRULE expansion
- **Performance**: Memory and CPU usage validation
- **Real Scenarios**: Ani/Jayson meeting test cases

### 3. Mock Strategy
- **Mock dateutil**: For deterministic testing
- **Mock Settings**: For configuration testing
- **Test Data**: Synthetic ICS data with known RRULE patterns

## 🔄 Migration Strategy

### Phase 1: Development
1. Implement RRuleExpander as standalone module
2. Add configuration settings
3. Create comprehensive test suite

### Phase 2: Integration
1. Modify ICSParser to use RRuleExpander
2. Add merge and deduplication logic
3. Update documentation

### Phase 3: Deployment
1. Feature flag for gradual rollout
2. Performance monitoring
3. Bug fixes and optimization

## ✅ Architecture Validation

This architecture successfully addresses:

- ✅ **Separation of Concerns**: RRuleExpander is isolated and testable
- ✅ **Backward Compatibility**: No breaking changes to existing APIs
- ✅ **Performance**: Configurable expansion window and lazy evaluation
- ✅ **Maintainability**: Clear module boundaries and error handling
- ✅ **Testability**: Each component can be tested independently

---

**Document Version**: 1.0  
**Last Updated**: August 15, 2025  
**Author**: SPARC Architect  
**Review Status**: Ready for TDD Phase