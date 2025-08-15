# RRULE Expansion System Specification

## 🎯 Executive Summary

This specification defines the requirements for implementing client-side RRULE (recurrence rule) expansion in CalendarBot to resolve missing recurring events. The system will generate individual event instances from RRULE patterns using python-dateutil.

## 🐛 Problem Statement

### Current Issue
- CalendarBot parser only processes explicit VEVENT components from ICS feeds
- Missing recurring event instances that should be generated from RRULE patterns
- Specific missing events identified:
  - **Ani <> Ben - 1:1- Bi Weekly**: Missing August 18, 2025 (bi-weekly Monday)
  - **Jayson <> Ben - 1:1- Weekly**: Missing August 15, 2025 (weekly Friday)

### Root Cause
Exchange server provides RRULE patterns but not all individual VEVENT instances. CalendarBot lacks client-side expansion logic.

## 📋 Functional Requirements

### FR1: RRULE Pattern Support
- **FR1.1**: Support FREQ=WEEKLY with INTERVAL=1 (weekly) and INTERVAL=2 (bi-weekly)
- **FR1.2**: Support BYDAY patterns (MO, TU, WE, TH, FR, SA, SU)
- **FR1.3**: Support UNTIL date termination
- **FR1.4**: Support COUNT-based termination
- **FR1.5**: Handle timezone-aware recurrence patterns

### FR2: EXDATE Exclusion Handling
- **FR2.1**: Parse and apply EXDATE properties to exclude specific occurrences
- **FR2.2**: Support multiple EXDATE values in comma-separated format
- **FR2.3**: Support timezone-aware EXDATE values

### FR3: Event Generation
- **FR3.1**: Generate individual CalendarEvent instances for each recurrence
- **FR3.2**: Preserve all event properties from master pattern
- **FR3.3**: Apply recurrence-specific datetime adjustments
- **FR3.4**: Assign unique IDs to generated instances

### FR4: Integration Requirements
- **FR4.1**: Seamlessly integrate with existing ICS parser workflow
- **FR4.2**: Merge generated events with explicit VEVENTs from server
- **FR4.3**: Prevent duplicate events when both RRULE and explicit VEVENT exist
- **FR4.4**: Maintain backward compatibility with existing functionality

### FR5: Performance Requirements
- **FR5.1**: Apply date range filtering to limit expansion scope
- **FR5.2**: Support configurable expansion window (default: 1 year)
- **FR5.3**: Handle large recurring series efficiently (1000+ occurrences)
- **FR5.4**: Lazy evaluation for memory optimization

## 🚫 Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: RRULE expansion must complete within 5 seconds for typical calendars
- **NFR1.2**: Memory usage must not exceed 100MB for expansion operations
- **NFR1.3**: Support calendars with up to 50 recurring series

### NFR2: Reliability
- **NFR2.1**: Graceful degradation when RRULE parsing fails
- **NFR2.2**: Comprehensive error logging for debugging
- **NFR2.3**: Validation of generated event data

### NFR3: Maintainability
- **NFR3.1**: Modular design with clear separation of concerns
- **NFR3.2**: Comprehensive unit test coverage (>95%)
- **NFR3.3**: Integration tests for real-world scenarios
- **NFR3.4**: Documentation for configuration and troubleshooting

## 🎯 Success Criteria

### Primary Success Criteria
1. **Ani <> Ben meeting**: August 18, 2025 appears in parsed events
2. **Jayson <> Ben meeting**: August 15, 2025 appears in parsed events
3. **No regressions**: Existing functionality remains intact
4. **Performance**: No significant impact on parsing speed

### Secondary Success Criteria
1. **EXDATE handling**: Excluded dates properly removed from recurrence
2. **Deduplication**: No duplicate events between RRULE and explicit VEVENTs
3. **Edge cases**: Proper handling of DST transitions, leap years, etc.

## 🔧 Technical Constraints

### TC1: Dependencies
- **TC1.1**: Must use existing python-dateutil library (v2.9.0.post0)
- **TC1.2**: No additional external dependencies
- **TC1.3**: Compatible with Python 3.12+

### TC2: Architecture
- **TC2.1**: Implement as separate RRuleExpander class
- **TC2.2**: Integrate through existing ICSParser without breaking changes
- **TC2.3**: Maintain existing event model structure

### TC3: Configuration
- **TC3.1**: RRULE expansion must be configurable (enable/disable)
- **TC3.2**: Expansion date range must be configurable
- **TC3.3**: No hardcoded environment variables

## 📊 Implementation Scope

### In Scope
- WEEKLY frequency patterns with INTERVAL and BYDAY
- EXDATE exclusion handling
- Date range filtering
- Integration with existing CalendarEvent model
- Comprehensive testing suite

### Out of Scope (Future Iterations)
- DAILY, MONTHLY, YEARLY frequency patterns
- BYMONTH, BYWEEKNO, BYYEARDAY complex patterns
- RDATE (recurrence dates) support
- Complex timezone conversion logic

## 🧪 Test Scenarios

### TS1: Core RRULE Patterns
- Bi-weekly Monday pattern (Ani <> Ben scenario)
- Weekly Friday pattern (Jayson <> Ben scenario)
- Weekly pattern with multiple EXDATE values

### TS2: Edge Cases
- RRULE spanning daylight saving time transitions
- UNTIL date boundary conditions
- Empty expansion results
- Malformed RRULE patterns

### TS3: Integration Tests
- Full ICS parsing with RRULE expansion enabled
- Performance tests with large recurring series
- Memory usage validation

## 🔄 Implementation Phases

### Phase 1: Core RRuleExpander
- Basic RRULE parsing and expansion
- CalendarEvent generation
- Unit tests for core functionality

### Phase 2: EXDATE Support
- EXDATE parsing and application
- Timezone handling for exclusions
- Integration tests

### Phase 3: Parser Integration
- Modify ICSParser to use RRuleExpander
- Event deduplication logic
- End-to-end testing

### Phase 4: Validation & Documentation
- Real-world scenario testing
- Performance optimization
- Comprehensive documentation

## 📝 Acceptance Criteria

The implementation is considered complete when:

1. ✅ All functional requirements are implemented
2. ✅ All test scenarios pass
3. ✅ Performance requirements are met
4. ✅ Missing Ani and Jayson meetings are correctly generated
5. ✅ No regressions in existing functionality
6. ✅ Code review and documentation completed

---

**Document Version**: 1.0  
**Last Updated**: August 15, 2025  
**Author**: SPARC Orchestrator  
**Review Status**: Pending Architecture Phase