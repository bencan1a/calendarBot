# Comprehensive Testing Strategy for Meeting Selection Logic

## Overview

Testing strategy for the new "next meeting priority" business logic changes in both backend (`WhatsNextLogic._group_events()`) and frontend (`detectCurrentMeeting()`) components. This ensures correct meeting selection behavior across all scenarios.

## Testing Layers

### 1. Unit Tests

#### Backend Unit Tests: `tests/test_whats_next_logic.py`

**Test Class**: `TestWhatsNextLogicGroupEvents`

```python
class TestWhatsNextLogicGroupEvents:
    def test_group_events_when_has_upcoming_meetings_then_returns_next_first(self):
        # Test: Upcoming meetings are prioritized over current meetings
        
    def test_group_events_when_only_current_meetings_then_returns_current_first(self):
        # Test: Current meetings returned when no upcoming meetings
        
    def test_group_events_when_hidden_events_exist_then_filters_correctly(self):
        # Test: Hidden events are properly filtered from selection
        
    def test_group_events_when_no_visible_events_then_returns_empty_primary(self):
        # Test: No meetings available edge case
        
    def test_group_events_when_multiple_upcoming_then_returns_earliest(self):
        # Test: Earliest upcoming meeting is selected among multiple
        
    def test_group_events_when_meeting_transitions_then_updates_correctly(self):
        # Test: Meeting transitions from upcoming to current to past
```

**Test Data Setup**:
```python
@pytest.fixture
def sample_events():
    return [
        create_cached_event(start=now + timedelta(hours=1), title="Next Meeting"),
        create_cached_event(start=now - timedelta(minutes=30), end=now + timedelta(minutes=30), title="Current Meeting"),
        create_cached_event(start=now + timedelta(hours=2), title="Later Meeting"),
        create_cached_event(start=now - timedelta(hours=1), end=now - timedelta(minutes=30), title="Past Meeting")
    ]
```

#### Frontend Unit Tests: `tests/test_whats_next_view.py`

**Test Functions**:
```python
def test_detect_current_meeting_when_has_upcoming_then_selects_next():
    # Test: Frontend selects next meeting when available
    
def test_detect_current_meeting_when_only_current_then_selects_current():
    # Test: Frontend falls back to current meeting
    
def test_detect_current_meeting_when_hidden_events_then_filters():
    # Test: Frontend respects is_hidden flag
    
def test_detect_current_meeting_when_no_meetings_then_sets_null():
    # Test: No meetings available edge case
    
def test_countdown_timer_when_next_meeting_then_shows_start_time():
    # Test: Countdown shows time until next meeting starts
    
def test_countdown_timer_when_current_meeting_then_shows_end_time():
    # Test: Countdown shows time until current meeting ends
```

### 2. Integration Tests

#### Backend-Frontend Consistency Tests: `tests/test_integration_meeting_selection.py`

**Test Class**: `TestMeetingSelectionConsistency`

```python
class TestMeetingSelectionConsistency:
    def test_backend_frontend_select_same_meeting_upcoming_scenarios(self):
        # Test: Backend and frontend select identical meetings for upcoming scenarios
        
    def test_backend_frontend_select_same_meeting_current_scenarios(self):
        # Test: Backend and frontend select identical meetings for current scenarios
        
    def test_backend_frontend_handle_hidden_events_consistently(self):
        # Test: Both layers filter hidden events identically
        
    def test_api_response_matches_frontend_expectations(self):
        # Test: API data structure matches frontend parsing expectations
```

#### State Manager Integration Tests: `tests/test_whats_next_state_manager.py`

```python
def test_state_manager_loads_data_and_updates_globals():
    # Test: State manager correctly updates global variables from API
    
def test_state_manager_optimistic_hide_updates():
    # Test: Optimistic updates for hiding/unhiding events
    
def test_state_manager_error_recovery():
    # Test: Error handling and state recovery
```

### 3. End-to-End Tests

#### Browser Tests with Playwright MCP: `tests/test_whats_next_browser.py`

**Test Scenarios**:

```python
@pytest.mark.browser
class TestWhatsNextBrowserBehavior:
    async def test_displays_next_meeting_when_available(self, browser_page):
        # Test: UI shows next meeting when upcoming meetings exist
        
    async def test_displays_current_meeting_when_no_upcoming(self, browser_page):
        # Test: UI shows current meeting when no upcoming meetings
        
    async def test_countdown_timer_accuracy_for_next_meeting(self, browser_page):
        # Test: Countdown timer shows correct time for next meeting
        
    async def test_countdown_timer_accuracy_for_current_meeting(self, browser_page):
        # Test: Countdown timer shows correct time for current meeting
        
    async def test_hide_unhide_meeting_updates_selection(self, browser_page):
        # Test: Hiding/unhiding meetings updates displayed meeting
        
    async def test_auto_refresh_maintains_correct_selection(self, browser_page):
        # Test: Auto-refresh continues to show correct meeting
        
    async def test_meeting_transition_updates_display(self, browser_page):
        # Test: Display updates when meetings transition states
```

### 4. Edge Case Testing

#### Temporal Edge Cases: `tests/test_meeting_edge_cases.py`

```python
def test_meetings_with_identical_start_times():
    # Test: Multiple meetings starting at exactly the same time
    
def test_meeting_ending_exactly_when_next_starts():
    # Test: Back-to-back meetings with no gap
    
def test_meeting_spanning_multiple_days():
    # Test: Long meetings that span day boundaries
    
def test_timezone_boundary_meetings():
    # Test: Meetings during timezone transitions (DST)
    
def test_all_day_events_vs_timed_events():
    # Test: Priority between all-day and timed events
```

#### Data Edge Cases: `tests/test_data_edge_cases.py`

```python
def test_empty_calendar_response():
    # Test: No events returned from calendar sources
    
def test_malformed_event_data():
    # Test: Handling of corrupted or incomplete event data
    
def test_extremely_large_number_of_events():
    # Test: Performance with large event datasets
    
def test_events_with_missing_required_fields():
    # Test: Handling of events missing start_time, end_time, etc.
```

### 5. Performance Testing

#### Backend Performance: `tests/test_performance_backend.py`

```python
def test_group_events_performance_with_large_dataset():
    # Test: Performance of new logic with 1000+ events
    
def test_hidden_events_filtering_performance():
    # Test: Performance impact of hidden events filtering
    
def test_find_next_upcoming_event_performance():
    # Test: Performance of existing logic being reused
```

#### Frontend Performance: `tests/test_performance_frontend.py`

```python
def test_detect_current_meeting_performance():
    # Test: Frontend meeting detection performance
    
def test_countdown_timer_update_performance():
    # Test: Timer update performance with new logic
    
def test_state_manager_load_data_performance():
    # Test: State manager performance with new logic
```

## Test Data Management

### Fixture Setup: `tests/fixtures/meeting_scenarios.py`

```python
@pytest.fixture
def upcoming_meeting_scenario():
    """Scenario with multiple upcoming meetings"""
    return {
        'events': [...],
        'expected_primary': 'next_meeting_id',
        'current_time': datetime(2024, 1, 1, 10, 0)
    }

@pytest.fixture  
def current_meeting_scenario():
    """Scenario with only current meetings"""
    return {
        'events': [...],
        'expected_primary': 'current_meeting_id',
        'current_time': datetime(2024, 1, 1, 14, 30)
    }

@pytest.fixture
def hidden_events_scenario():
    """Scenario with hidden events that should be filtered"""
    return {
        'events': [...],
        'hidden_event_ids': ['hidden_1', 'hidden_2'],
        'expected_primary': 'visible_meeting_id'
    }
```

### Mock Configuration: `tests/mocks/calendar_service.py`

```python
class MockCalendarService:
    def __init__(self, events_data):
        self.events_data = events_data
        
    def get_events(self, start_time, end_time):
        return self.events_data
        
class MockSettingsService:
    def __init__(self, hidden_events=None):
        self.hidden_events = hidden_events or set()
        
    def get_hidden_events(self):
        return self.hidden_events
```

## Test Execution Strategy

### 1. Pre-Implementation Testing
```bash
# Run existing tests to establish baseline
pytest tests/ -v --cov=calendarbot

# Verify no existing regressions
pytest tests/test_whats_next* -v
```

### 2. Development Testing
```bash
# Run unit tests during development
pytest tests/test_whats_next_logic.py -v
pytest tests/test_whats_next_view.py -v

# Run integration tests after unit tests pass
pytest tests/test_integration_meeting_selection.py -v
```

### 3. Browser Testing
```bash
# Run browser tests with Playwright MCP
pytest tests/test_whats_next_browser.py -v --browser

# Visual regression testing
pytest tests/test_visual_regression.py -v --browser
```

### 4. Performance Testing
```bash
# Run performance tests separately
pytest tests/test_performance* -v --benchmark

# Memory usage testing
pytest tests/test_memory_usage.py -v
```

### 5. Full Test Suite
```bash
# Complete test suite before completion
pytest tests/ -v --cov=calendarbot --cov-report=html

# Ensure 100% coverage of new code
pytest tests/test_whats_next* -v --cov=calendarbot.display.whats_next_logic --cov=calendarbot.web.static.layouts.whats-next-view
```

## Testing Tools & Configuration

### Test Dependencies: `requirements-test.txt`
```
pytest>=7.0.0
pytest-asyncio>=0.21.0  
pytest-cov>=4.0.0
pytest-benchmark>=4.0.0
pytest-mock>=3.10.0
freezegun>=1.2.0  # For time-based testing
```

### Pytest Configuration: `pytest.ini`
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    browser: Browser-based tests requiring Playwright MCP
    performance: Performance and benchmark tests
    integration: Cross-component integration tests
    edge_case: Edge case and boundary condition tests
```

### Browser Test Configuration
```python
# Use Playwright MCP for browser automation
async def test_with_playwright_mcp():
    # Use MCP tools for browser interaction
    await use_mcp_tool('playwright', 'browser_navigate', {'url': 'http://localhost:8000'})
    await use_mcp_tool('playwright', 'browser_snapshot', {})
    # ... test assertions
```

## Success Criteria

### Unit Test Success
✅ **100% code coverage** for new meeting selection logic  
✅ **All edge cases covered** including empty datasets, hidden events, timezone boundaries  
✅ **Performance benchmarks met** for large event datasets  
✅ **No regressions** in existing functionality  

### Integration Test Success
✅ **Backend-frontend consistency** verified across all scenarios  
✅ **API contract compliance** maintained  
✅ **State management correctness** validated  
✅ **Error handling robustness** confirmed  

### Browser Test Success
✅ **UI correctly displays** next meetings when available  
✅ **Countdown timer accuracy** for both next and current meetings  
✅ **Real-time updates** work correctly  
✅ **Visual regression prevention** maintained  

### Performance Success
✅ **No performance degradation** from current implementation  
✅ **Sub-100ms response times** for meeting selection logic  
✅ **Memory usage within bounds** for large datasets  
✅ **Browser responsiveness maintained** during updates  

## Continuous Testing

### Pre-commit Hooks
```bash
# Run unit tests before commit
pytest tests/test_whats_next_logic.py tests/test_whats_next_view.py -q

# Run linting and type checking
flake8 calendarbot/display/whats_next_logic.py
mypy calendarbot/display/whats_next_logic.py
```

### CI/CD Integration
```yaml
# GitHub Actions workflow
test_meeting_logic:
  runs-on: ubuntu-latest
  steps:
    - name: Run Unit Tests
      run: pytest tests/test_whats_next* -v
    - name: Run Integration Tests  
      run: pytest tests/test_integration* -v
    - name: Run Browser Tests
      run: pytest tests/test_whats_next_browser.py -v --browser
```

This comprehensive testing strategy ensures the new meeting selection logic works correctly across all components and scenarios while maintaining system reliability and performance.