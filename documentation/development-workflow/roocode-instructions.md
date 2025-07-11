# Roocode Instructions Guide

## Overview

The `.roo/rules/rules.md` file contains enhanced instructions that enforce the prevention-first development approach through automated code quality requirements. These instructions are designed to work seamlessly with AI coding assistants to maintain consistent, high-quality code.

## Core Principles

### MyPy Compliance Requirements

All code must include comprehensive type annotations:

```python
# ✅ Correct - Full type annotations
def process_user_data(
    user_id: str, 
    preferences: Dict[str, Any], 
    timeout: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Process user data with full type safety.
    
    Args:
        user_id: Unique identifier for the user
        preferences: User preference dictionary
        timeout: Optional timeout in seconds
        
    Returns:
        Tuple of (success_flag, error_message)
        
    Raises:
        ValueError: If user_id is empty
        TypeError: If preferences is not a dictionary
    """
    try:
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        if not isinstance(preferences, dict):
            raise TypeError("Preferences must be a dictionary")
            
        # Processing logic here
        return True, None
        
    except Exception as e:
        logger.error(f"Failed to process user data: {e}")
        return False, str(e)

# ❌ Incorrect - Missing type annotations
def process_user_data(user_id, preferences, timeout=None):
    # No type safety, no documentation
    return True, None
```

### Automatic Unit Test Generation

Every new function requires comprehensive test coverage:

```python
# For the function above, this test file would be auto-generated:
# tests/test_user_processor.py

import pytest
from unittest.mock import Mock, patch
from calendarbot.user_processor import process_user_data

def test_process_user_data_when_valid_input_then_returns_success():
    """Test that process_user_data handles valid input correctly."""
    user_id = "user123"
    preferences = {"theme": "dark", "notifications": True}
    
    result = process_user_data(user_id, preferences)
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] is True
    assert result[1] is None

def test_process_user_data_when_empty_user_id_then_raises_value_error():
    """Test that empty user_id raises ValueError."""
    with pytest.raises(ValueError, match="User ID cannot be empty"):
        process_user_data("", {"theme": "dark"})

def test_process_user_data_when_invalid_preferences_then_raises_type_error():
    """Test that non-dict preferences raises TypeError."""
    with pytest.raises(TypeError, match="Preferences must be a dictionary"):
        process_user_data("user123", "invalid_preferences")

@pytest.mark.asyncio
async def test_process_user_data_when_timeout_specified_then_respects_limit():
    """Test that timeout parameter is properly handled."""
    result = process_user_data("user123", {"theme": "dark"}, timeout=30)
    assert result[0] is True

def test_process_user_data_when_processing_fails_then_returns_error():
    """Test error handling when processing fails."""
    with patch('calendarbot.user_processor.logger') as mock_logger:
        # Test error conditions
        result = process_user_data("user123", {})
        
        # Verify error logging occurred
        mock_logger.error.assert_called()
```

## Enforcement Patterns

### Type Annotation Requirements

```python
# Required imports for type annotations
from typing import Any, Dict, List, Optional, Union, Tuple, Callable

# Function signatures must include all type information
def complex_function(
    data: Dict[str, List[str]],
    callback: Callable[[str], bool],
    options: Optional[Dict[str, Any]] = None
) -> Union[str, None]:
    """Comprehensive type annotation example."""
    pass

# Async functions must specify return types
async def fetch_data(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Async function with proper typing."""
    pass

# Class methods include proper typing
class DataProcessor:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
    
    def process(self, items: List[str]) -> Tuple[bool, Optional[str]]:
        """Process items with full type safety."""
        pass
```

### Documentation Standards

```python
def example_function(param1: str, param2: Optional[int] = None) -> bool:
    """
    Brief description of what the function does.
    
    Detailed explanation if needed. This should explain the purpose,
    behavior, and any important implementation details.
    
    Args:
        param1: Description of the first parameter
        param2: Description of the optional parameter, defaults to None
        
    Returns:
        Description of the return value and its meaning
        
    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is negative
        
    Example:
        >>> result = example_function("test", 42)
        >>> assert result is True
    """
    # Implementation with comprehensive error handling
    pass
```

### Error Handling Patterns

```python
def robust_api_call(endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Make API call with comprehensive error handling.
    
    Args:
        endpoint: API endpoint URL
        data: Request data dictionary
        
    Returns:
        API response data or None if request fails
        
    Raises:
        ValueError: If endpoint is invalid
        requests.RequestException: If network request fails
    """
    try:
        # Input validation
        if not endpoint or not endpoint.startswith('http'):
            raise ValueError(f"Invalid endpoint: {endpoint}")
        
        # API call logic
        response = requests.post(endpoint, json=data, timeout=30)
        response.raise_for_status()
        
        return response.json()
        
    except requests.Timeout:
        logger.error(f"API call timeout for endpoint: {endpoint}")
        return None
    except requests.RequestException as e:
        logger.error(f"API call failed for {endpoint}: {e}")
        return None
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in API call: {e}")
        return None
```

## Validation Against Existing Codebase

### Pattern Consistency

The roocode instructions were validated against existing project files:

```python
# Example from calendarbot/setup_wizard.py (existing pattern)
def collect_user_preferences() -> Dict[str, Any]:
    """
    Collect and validate user configuration preferences.
    
    Returns:
        Dictionary containing validated user preferences
        
    Raises:
        ValueError: If user input is invalid
        KeyboardInterrupt: If user cancels setup
    """
    # This pattern matches our roocode requirements
```

### Integration Testing

Example feature implementation following roocode patterns:

```python
# calendarbot/features/meeting_context.py
class MeetingContextAnalyzer:
    """Analyzes meeting context for intelligent calendar management."""
    
    def __init__(self, calendar_data: Dict[str, Any]) -> None:
        """
        Initialize the meeting context analyzer.
        
        Args:
            calendar_data: Dictionary containing calendar configuration
            
        Raises:
            ValueError: If calendar_data is invalid
        """
        if not isinstance(calendar_data, dict):
            raise ValueError("Calendar data must be a dictionary")
        self.calendar_data = calendar_data

    def analyze_meeting_context(
        self, 
        meeting_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Analyze meeting context for scheduling optimization.
        
        Args:
            meeting_data: Dictionary containing meeting information
            
        Returns:
            Tuple of (analysis_success, error_message)
            
        Raises:
            ValueError: If meeting_data format is invalid
        """
        try:
            # Validation logic
            if not meeting_data or "title" not in meeting_data:
                raise ValueError("Meeting data must include title")
            
            # Analysis logic here
            return True, None
            
        except Exception as e:
            logger.error(f"Meeting analysis failed: {e}")
            return False, str(e)
```

## AI Assistant Integration

### Prompt Engineering

The roocode instructions are designed to work with AI coding assistants:

```markdown
# Example AI Prompt Integration
When implementing the `calculate_time_remaining` function:

1. AI reads roocode instructions from .roo/rules/rules.md
2. Generates MyPy-compliant function with full type annotations
3. Creates comprehensive docstring with Args/Returns/Raises
4. Implements robust error handling patterns
5. Auto-generates corresponding unit tests in tests/ directory
6. Validates against existing codebase patterns
```

### Code Generation Templates

```python
# Template pattern for new functions
def new_function(param1: TYPE, param2: Optional[TYPE] = None) -> RETURN_TYPE:
    """
    [BRIEF_DESCRIPTION]
    
    [DETAILED_DESCRIPTION]
    
    Args:
        param1: [DESCRIPTION]
        param2: [DESCRIPTION], defaults to None
        
    Returns:
        [DESCRIPTION]
        
    Raises:
        [EXCEPTION]: [CONDITION]
        
    Example:
        >>> result = new_function("test")
        >>> assert isinstance(result, RETURN_TYPE)
    """
    try:
        # Input validation
        if not param1:
            raise ValueError("param1 cannot be empty")
        
        # Main logic
        # ...
        
        return result
        
    except SpecificException as e:
        logger.error(f"Specific error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return default_value
```

## Quality Metrics

### Compliance Checking

```bash
# Verify MyPy compliance
mypy calendarbot/ --strict

# Check test coverage
pytest --cov=calendarbot tests/ --cov-report=html

# Validate documentation
pydocstyle calendarbot/

# Security scanning
bandit -r calendarbot/
```

### Success Criteria

- **100% type annotation coverage** - All functions include complete type information
- **Comprehensive test coverage** - All functions have corresponding unit tests
- **Consistent error handling** - All functions use standardized error patterns
- **Complete documentation** - All functions include docstrings with Args/Returns/Raises

## Benefits

### For Development

- **Immediate Quality Feedback** - AI assistants generate compliant code automatically
- **Consistency Enforcement** - All code follows the same patterns and standards
- **Reduced Manual Review** - Automated compliance checking catches issues early
- **Faster Onboarding** - New developers follow established patterns from day one

### For Maintenance

- **Predictable Code Structure** - All functions follow the same format
- **Comprehensive Testing** - High confidence in code changes
- **Clear Error Handling** - Debugging is straightforward and systematic
- **Type Safety** - Runtime errors caught at development time

## Common Patterns

### Async Function Example

```python
async def fetch_calendar_events(
    calendar_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> List[Dict[str, Any]]:
    """
    Fetch calendar events within date range.
    
    Args:
        calendar_id: Unique identifier for calendar
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        List of event dictionaries
        
    Raises:
        ValueError: If date range is invalid
        CalendarAPIError: If API request fails
    """
    try:
        if start_date >= end_date:
            raise ValueError("Start date must be before end date")
        
        # Async API call
        events = await calendar_api.get_events(
            calendar_id, start_date, end_date
        )
        
        return events
        
    except CalendarAPIError as e:
        logger.error(f"Calendar API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}")
        return []
```

### Class-based Pattern

```python
class EventProcessor:
    """Process calendar events with comprehensive validation."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize event processor.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        self._validate_config(config)
        self.config = config
    
    def process_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process list of calendar events.
        
        Args:
            events: List of raw event dictionaries
            
        Returns:
            List of processed event dictionaries
            
        Raises:
            ValueError: If events list is invalid
        """
        # Implementation following roocode patterns
        pass
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration dictionary."""
        # Private method following same patterns
        pass
```

## Next Steps

1. Review existing code against roocode patterns
2. Understand [Testing Strategy](./testing-strategy.md) for comprehensive validation
3. Learn [Best Practices](./best-practices.md) for optimal development workflow
4. Explore [Troubleshooting](./troubleshooting.md) for common issues and solutions