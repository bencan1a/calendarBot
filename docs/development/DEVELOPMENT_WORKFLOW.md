# Development Workflow

## Overview

CalendarBot follows quality-first development practices with automated validation and consistent coding standards.

## Quick Setup

```bash
# Activate environment
. venv/bin/activate

# Install pre-commit hooks
pre-commit install

# Test setup
pre-commit run --all-files
```

## Code Quality Standards

### Type Annotations (Required)
All functions must include complete type annotations:

```python
from typing import Dict, List, Optional, Any

def process_events(events: List[Dict[str, Any]], timeout: Optional[int] = None) -> bool:
    """Process calendar events with full type safety."""
    pass
```

### Documentation (Required)
All functions must include comprehensive docstrings:

```python
def example_function(param: str) -> bool:
    """
    Brief description of function purpose.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param is invalid
    """
    pass
```

### Error Handling (Required)
Use explicit exception handling with logging:

```python
def robust_function(data: Dict[str, Any]) -> Optional[str]:
    """Function with comprehensive error handling."""
    try:
        # Validation logic
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Processing logic
        return process_data(data)
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### Unit Testing (Required)
Every function must have corresponding unit tests:

```python
# tests/test_module.py
def test_function_when_valid_input_then_returns_expected():
    """Test description following naming convention."""
    result = example_function("valid_input")
    assert result is True
    assert isinstance(result, bool)
```

## Development Workflow

### 1. Environment Setup
```bash
cd calendarbot
. venv/bin/activate
```

### 2. Code Development
- Write code with real-time MyPy type checking
- Include comprehensive type annotations
- Add detailed docstrings
- Implement robust error handling

### 3. Testing
```bash
# Run tests for changed files
pytest

# Run full test suite
pytest --cov=calendarbot tests/

# Type checking
mypy calendarbot/ --strict
```

### 4. Commit Process
```bash
# Standard commits (full validation)
git add .
git commit -m "feat: implement user authentication"

# Fast commits (emergency situations)
pre-commit run --config .pre-commit-config-fast.yaml
git commit -m "hotfix: critical security patch"
```

## Validation Tools

### Pre-commit Hooks
- **Standard Profile**: Full validation (~30-45 seconds)
  - MyPy type checking
  - Code formatting (black, isort)
  - Security scanning (bandit)
  - Test execution
  
- **Fast Profile**: Essential validation (~1 second)
  - Syntax checking
  - Basic formatting
  - Quick security scan

### Code Quality Metrics
- 100% type annotation coverage
- Comprehensive test coverage
- Consistent error handling patterns
- Complete documentation

## Best Practices

### ✅ Do:
- Write comprehensive type annotations for all functions
- Include detailed docstrings with Args/Returns/Raises
- Implement robust error handling with specific exceptions
- Create unit tests for every function
- Use descriptive variable names
- Validate input parameters explicitly
- Log errors with sufficient context

### ❌ Don't:
- Skip type annotations
- Use generic exception handling without logging
- Write functions without corresponding unit tests
- Bypass pre-commit hooks without good reason
- Use print() statements in production code
- Ignore MyPy warnings or errors
- Commit untested code to shared branches

## Performance Guidelines

### Smart Development
```bash
# Only test changed files (automatic)
git commit -m "Update auth module"  # Fast validation

# Full validation when needed
pre-commit run --all-files

# Parallel test execution
pytest -n auto tests/
```

### IDE Configuration
- Enable MyPy daemon for real-time type checking
- Configure format-on-save for consistent style
- Set up automatic import sorting
- Enable error highlighting for immediate feedback

## Emergency Workflows

For intensive development or emergency fixes:

```bash
# Switch to fast profile temporarily
PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml pre-commit install

# Or run fast validation manually
pre-commit run --config .pre-commit-config-fast.yaml

# Always follow up with full validation before merge
pre-commit run --all-files
```

## Integration with AI Tools

The codebase includes instructions in `.roo/rules/rules.md` that help AI coding assistants:
- Generate MyPy-compliant code automatically
- Create comprehensive unit tests
- Follow consistent documentation patterns
- Implement robust error handling

This ensures all generated code follows project standards automatically.