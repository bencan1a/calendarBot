# Best Practices Guide

## Prevention-First Development Guidelines

### Development Workflow Best Practices

#### Daily Development Routine

1. **Start with Environment Preparation**
   ```bash
   cd calendarbot
   . venv/bin/activate
   code .  # Opens with all prevention-first settings
   ```

2. **Develop with Real-time Feedback**
   - Let MyPy daemon provide instant type checking
   - Use format-on-save for consistent code style
   - Write tests alongside implementation (TDD)
   - Validate roocode compliance as you code

3. **Commit with Confidence**
   ```bash
   # Standard development commits
   git add .
   git commit -m "feat: implement user authentication"
   
   # Emergency commits when needed
   pre-commit run --config .pre-commit-config-fast.yaml
   git commit -m "hotfix: critical security patch"
   ```

#### Code Quality Guidelines

**✅ Do:**
- Write comprehensive type annotations for all functions
- Include detailed docstrings with Args/Returns/Raises
- Implement robust error handling with specific exception types
- Create unit tests for every function (following roocode patterns)
- Use descriptive variable names that convey intent
- Validate input parameters explicitly
- Log errors with sufficient context for debugging

**❌ Don't:**
- Skip type annotations ("I'll add them later")
- Use generic exception handling without logging
- Write functions without corresponding unit tests
- Bypass pre-commit hooks without good reason
- Use print() statements in production code
- Ignore MyPy warnings or errors
- Commit untested code to shared branches

### Type Annotation Best Practices

#### Comprehensive Coverage

```python
# ✅ Excellent - Complete type coverage
from typing import Dict, List, Optional, Union, Tuple, Any, Callable

def process_calendar_events(
    events: List[Dict[str, Any]],
    filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
    sort_by: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Process calendar events with optional filtering and sorting.
    
    Args:
        events: List of event dictionaries
        filter_func: Optional function to filter events
        sort_by: Optional field name to sort by
        
    Returns:
        Tuple of (processed_events, count)
        
    Raises:
        ValueError: If sort_by field doesn't exist in events
    """
    # Implementation with full type safety
    
# ❌ Poor - Missing type information
def process_calendar_events(events, filter_func=None, sort_by=None):
    # No type safety, unclear interface
    pass
```

#### Complex Type Patterns

```python
# Nested data structures
UserPreferences = Dict[str, Union[str, int, bool, List[str]]]
CalendarEvent = Dict[str, Any]
ProcessingResult = Tuple[bool, Optional[str], List[CalendarEvent]]

def advanced_processing(
    user_prefs: UserPreferences,
    events: List[CalendarEvent]
) -> ProcessingResult:
    """Handle complex nested types with clarity."""
    pass

# Generic types for reusability
from typing import TypeVar, Generic

T = TypeVar('T')

class DataProcessor(Generic[T]):
    def process(self, data: T) -> T:
        """Generic processor for any data type."""
        return data
```

### Error Handling Patterns

#### Hierarchical Exception Handling

```python
# Custom exception hierarchy
class CalendarBotError(Exception):
    """Base exception for CalendarBot."""
    pass

class ConfigurationError(CalendarBotError):
    """Configuration-related errors."""
    pass

class APIError(CalendarBotError):
    """External API errors."""
    pass

class ValidationError(CalendarBotError):
    """Data validation errors."""
    pass

# Usage with specific handling
def connect_to_calendar_api(config: Dict[str, str]) -> bool:
    """
    Connect to calendar API with comprehensive error handling.
    
    Args:
        config: API configuration dictionary
        
    Returns:
        True if connection successful
        
    Raises:
        ConfigurationError: If config is invalid
        APIError: If API connection fails
    """
    try:
        # Validate configuration
        if "api_key" not in config:
            raise ConfigurationError("API key missing from configuration")
        
        # Attempt connection
        response = api_client.connect(config["api_key"])
        
        if not response.success:
            raise APIError(f"API connection failed: {response.error}")
        
        return True
        
    except ConfigurationError:
        logger.error("Configuration error in calendar API connection")
        raise  # Re-raise specific exceptions
    except APIError:
        logger.error("API connection failed")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in API connection: {e}")
        raise APIError(f"Unexpected connection error: {e}")
```

### Testing Best Practices

#### Comprehensive Test Coverage

```python
# Complete test suite example
import pytest
from unittest.mock import Mock, patch, AsyncMock
from calendarbot.processors import EventProcessor

class TestEventProcessor:
    """Test suite following roocode patterns."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance for testing."""
        config = {"max_events": 100, "timeout": 30}
        return EventProcessor(config)
    
    def test_init_when_valid_config_then_creates_processor(self):
        """Test successful processor initialization."""
        config = {"max_events": 50}
        processor = EventProcessor(config)
        
        assert processor.config == config
        assert isinstance(processor, EventProcessor)
    
    def test_init_when_invalid_config_then_raises_error(self):
        """Test initialization with invalid configuration."""
        with pytest.raises(ValueError, match="Configuration must be a dictionary"):
            EventProcessor("invalid_config")
    
    @pytest.mark.asyncio
    async def test_process_events_when_valid_data_then_returns_results(self, processor):
        """Test event processing with valid data."""
        events = [
            {"id": "1", "title": "Meeting", "start": "2024-01-01T09:00:00"},
            {"id": "2", "title": "Call", "start": "2024-01-01T10:00:00"}
        ]
        
        result = await processor.process_events(events)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all("processed" in event for event in result)
    
    @patch('calendarbot.processors.external_api')
    def test_process_events_when_api_fails_then_handles_gracefully(self, mock_api, processor):
        """Test graceful handling of API failures."""
        mock_api.process.side_effect = Exception("API Error")
        
        events = [{"id": "1", "title": "Test"}]
        result = processor.process_events(events)
        
        assert result == []
        mock_api.process.assert_called_once()
```

#### Test Organization

```
tests/
├── unit/                 # Unit tests for individual components
│   ├── test_auth.py
│   ├── test_calendar.py
│   └── test_processors.py
├── integration/          # Integration tests
│   ├── test_api_integration.py
│   └── test_workflow.py
├── fixtures/            # Test data and fixtures
│   ├── sample_events.json
│   └── test_configs.py
└── conftest.py          # Shared test configuration
```

### Performance Best Practices

#### Efficient Development Workflow

1. **Use Smart Pre-commit Hooks**
   ```bash
   # Only test changed files (default behavior)
   git commit -m "Update user auth module"  # Fast validation
   
   # Full validation when needed
   pre-commit run --all-files  # Comprehensive check
   ```

2. **Leverage MyPy Daemon**
   ```bash
   # Check daemon status
   dmypy status
   
   # Restart if performance degrades
   dmypy restart
   ```

3. **Optimize Test Execution**
   ```bash
   # Run specific test modules
   pytest tests/unit/test_auth.py -v
   
   # Parallel execution
   pytest -n auto tests/
   
   # Coverage for specific modules
   pytest --cov=calendarbot.auth tests/unit/test_auth.py
   ```

#### Code Optimization Patterns

```python
# ✅ Efficient - Early validation and exit
def process_large_dataset(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process large dataset efficiently."""
    # Early validation
    if not data:
        return []
    
    # Validate first item to catch issues early
    if not isinstance(data[0], dict):
        raise ValueError("Data must be list of dictionaries")
    
    # Process with efficient patterns
    return [process_item(item) for item in data if is_valid(item)]

# ❌ Inefficient - Late validation, unnecessary processing
def process_large_dataset(data):
    processed = []
    for item in data:  # No early exit
        try:
            result = expensive_operation(item)
            if validate_result(result):  # Late validation
                processed.append(result)
        except:
            pass  # Silent failures
    return processed
```

### Security Best Practices

#### Secure Coding Patterns

```python
from pathlib import Path
import secrets
from typing import Optional

def secure_file_operation(filename: str, content: str) -> bool:
    """
    Perform secure file operations with validation.
    
    Args:
        filename: Target filename (validated)
        content: Content to write
        
    Returns:
        True if operation successful
        
    Raises:
        ValueError: If filename is invalid
        SecurityError: If path traversal detected
    """
    try:
        # Use Path objects for security
        file_path = Path(filename).resolve()
        
        # Validate against path traversal
        if not str(file_path).startswith(str(Path.cwd())):
            raise SecurityError("Path traversal detected")
        
        # Secure file writing
        with file_path.open('w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        logger.error(f"Secure file operation failed: {e}")
        raise

def generate_secure_token() -> str:
    """Generate cryptographically secure token."""
    return secrets.token_urlsafe(32)
```

#### Input Validation

```python
def validate_user_input(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize user input.
    
    Args:
        user_data: Raw user input dictionary
        
    Returns:
        Validated and sanitized data
        
    Raises:
        ValidationError: If input is invalid
    """
    # Required fields validation
    required_fields = ["email", "name"]
    for field in required_fields:
        if field not in user_data:
            raise ValidationError(f"Required field missing: {field}")
    
    # Email validation
    email = user_data["email"].strip().lower()
    if "@" not in email or len(email) < 5:
        raise ValidationError("Invalid email format")
    
    # Name sanitization
    name = user_data["name"].strip()
    if len(name) < 2 or len(name) > 100:
        raise ValidationError("Name must be 2-100 characters")
    
    return {
        "email": email,
        "name": name,
        "created_at": datetime.utcnow().isoformat()
    }
```

### Documentation Best Practices

#### Comprehensive Function Documentation

```python
def complex_calendar_operation(
    calendar_id: str,
    start_date: datetime,
    end_date: datetime,
    filters: Optional[Dict[str, Any]] = None,
    sort_options: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Perform complex calendar operations with multiple parameters.
    
    This function retrieves calendar events within a date range, applies
    optional filters, and returns both the events and metadata about the
    operation.
    
    Args:
        calendar_id: Unique identifier for the target calendar
        start_date: Beginning of the date range (inclusive)
        end_date: End of the date range (exclusive)
        filters: Optional dictionary of filter criteria:
            - "status": List of event statuses to include
            - "attendees": Minimum number of attendees
            - "duration": Tuple of (min_minutes, max_minutes)
        sort_options: Optional list of fields to sort by:
            - Supported: ["start_time", "duration", "attendee_count"]
            - Prefix with "-" for descending order
            
    Returns:
        Tuple containing:
            - List of event dictionaries matching criteria
            - Metadata dictionary with operation statistics:
                - "total_found": Total events before filtering
                - "filtered_count": Events after applying filters
                - "processing_time_ms": Operation duration
                
    Raises:
        ValueError: If date range is invalid or calendar_id is empty
        CalendarAPIError: If calendar service is unavailable
        FilterError: If filter criteria are malformed
        
    Example:
        >>> from datetime import datetime, timedelta
        >>> start = datetime.now()
        >>> end = start + timedelta(days=7)
        >>> events, stats = complex_calendar_operation(
        ...     "cal123",
        ...     start,
        ...     end,
        ...     filters={"status": ["confirmed"], "attendees": 2},
        ...     sort_options=["start_time", "-duration"]
        ... )
        >>> print(f"Found {len(events)} events")
        >>> print(f"Processing took {stats['processing_time_ms']}ms")
        
    Note:
        This function uses caching for repeated requests within a 5-minute
        window. Cache keys are based on calendar_id and date range.
    """
    # Implementation follows all patterns above
    pass
```

### Team Collaboration Best Practices

#### Code Review Guidelines

1. **Pre-Review Checklist**
   - All pre-commit hooks pass
   - MyPy validation successful
   - Unit tests written and passing
   - Documentation complete

2. **Review Focus Areas**
   - Type annotation completeness
   - Error handling robustness
   - Test coverage adequacy
   - Security considerations

3. **Merge Requirements**
   - Standard pre-commit profile validation
   - Peer review approval
   - CI/CD pipeline success
   - Documentation updates

#### Branch Management

```bash
# Feature development workflow
git checkout -b feature/user-authentication
# Develop with prevention-first practices
git commit -m "feat: implement secure user auth"  # Standard validation
git push origin feature/user-authentication

# Emergency hotfix workflow
git checkout -b hotfix/security-patch
# Use fast profile for rapid iteration
PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml git commit -m "hotfix: security patch"
# Follow up with full validation before merge
pre-commit run --all-files
git commit --amend -m "hotfix: security patch - fully validated"
```

## Summary

The prevention-first approach emphasizes:
- **Quality by default** - Make good practices automatic
- **Early feedback** - Catch issues during development
- **Consistent patterns** - Predictable code structure
- **Comprehensive testing** - High confidence in changes
- **Security awareness** - Proactive vulnerability prevention

By following these best practices, you'll maintain high code quality while maximizing development efficiency and team productivity.