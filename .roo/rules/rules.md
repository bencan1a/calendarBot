You are running in sh not bash
Activate the python venv before running the app by calling ". venv/bin/activate" from the project directory. Do not call 'source'

# MyPy Compliance Requirements
Always write MyPy-compliant code with full type annotations:
- ALL function parameters must have type annotations
- ALL function return types must be explicitly annotated (use -> None for void functions)
- Use typing imports: from typing import Any, Dict, List, Optional, Union, Tuple, Callable
- For async functions: use async def function_name() -> ReturnType:
- For class methods: include self parameter without type, annotate others
- Use Optional[Type] for parameters that can be None
- Use Union[Type1, Type2] for parameters accepting multiple types
- Use Dict[str, Any] for flexible dictionaries
- Use List[Type] for typed lists
- For complex nested types: Dict[str, List[Dict[str, Any]]]

# Type Annotation Examples (follow these patterns exactly):
```python
def simple_function(name: str, age: int) -> str:
    return f"{name} is {age}"

def optional_params(data: Optional[Dict[str, Any]] = None) -> bool:
    return data is not None

async def async_function(url: str, timeout: int = 30) -> Dict[str, Any]:
    # async implementation
    return {"status": "success"}

class ExampleClass:
    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        self.config = config
    
    def process_data(self, items: List[str]) -> Tuple[bool, Optional[str]]:
        return True, None
```

# Unit Test Requirements
Write comprehensive unit tests for ALL new functions:
- Create test file in tests/ directory matching the module structure
- Test filename: test_[module_name].py
- Use pytest framework with fixtures
- Test normal cases, edge cases, and error conditions
- Use descriptive test method names: test_function_name_when_condition_then_expected
- Mock external dependencies and API calls
- Test async functions with pytest.mark.asyncio
- Assert return types match annotations
- Include docstrings explaining test purpose

# Unit Test Examples:
```python
import pytest
from unittest.mock import Mock, patch
from your_module import your_function

def test_simple_function_when_valid_input_then_returns_formatted_string():
    """Test that simple_function formats name and age correctly."""
    result = simple_function("Alice", 30)
    assert result == "Alice is 30"
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_async_function_when_called_then_returns_dict():
    """Test async function returns expected dictionary structure."""
    result = await async_function("http://example.com")
    assert isinstance(result, dict)
    assert "status" in result

@patch('your_module.external_api_call')
def test_function_with_mock_when_api_fails_then_handles_error(mock_api):
    """Test function handles API failure gracefully."""
    mock_api.side_effect = Exception("API Error")
    result = your_function_that_calls_api()
    assert result is None
```

# Code Quality Standards
- Use descriptive variable names matching the codebase style
- Add comprehensive docstrings with Args, Returns, Raises sections
- Handle exceptions explicitly with try/except blocks
- Use logging instead of print statements for production code
- Follow existing codebase patterns for imports and structure
- Prioritize using the most common library in the community
- Use Path objects for file operations, not string concatenation
- Validate input parameters and raise appropriate exceptions

# Documentation Requirements
- All functions must have detailed docstrings
- Include type information in docstrings that matches annotations
- Document exceptions that can be raised
- Provide usage examples in docstrings for complex functions

# Error Handling Patterns
```python
def robust_function(data: Dict[str, Any]) -> Optional[str]:
    """
    Process data safely with proper error handling.
    
    Args:
        data: Dictionary containing processing data
        
    Returns:
        Processed result string or None if processing fails
        
    Raises:
        ValueError: If data format is invalid
        KeyError: If required keys are missing
    """
    try:
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
            
        required_key = data["required_field"]  # May raise KeyError
        return f"Processed: {required_key}"
        
    except KeyError as e:
        logger.error(f"Missing required field: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing data: {e}")
        return None
```
