# CALENDARBOT DEVELOPMENT RULES

## ENVIRONMENT & EXECUTION
- **Shell**: sh (not bash)
- **Python venv**: `. venv/bin/activate` (not `source`)
- **App Execution**: Always use `calendarbot --web --port PORT` with additional options as needed
- **Browser Testing**: Use host IP, not localhost; prefer curl over browser tools/pypeteer

## FEATURE DEVELOPMENT WORKFLOW
- **Project Structure**: Orchestrator mode creates `/docs/projects/MM-DD-short-descriptive-name/` for substantial new features only
- **Research Reports**: Store feature research in project folder, format for LLM efficiency
- **Orchestrator Flow**: Sequential task distribution based on relevance assessment

## TESTING WORKFLOW
1. **Smoke Test**: Execute `calendarbot --web`, inspect logs for errors, resolve before proceeding
2. **Unit Tests**: Comprehensive coverage for ALL new functions after smoke test passes
3. **Pre-Completion**: Run full unit test suite, fix all failures before task completion
4. **Browser Tests**: Required for UX changes, address all failures
5. **Test Engineering**: Use Python Test Engineer or Jest Test Engineer modes for test development/fixing
6. **Debug Scripts**: Create in `/scripts` directory, remove when debugging complete

## TYPE ANNOTATIONS (MYPY COMPLIANCE)
**Required**: ALL parameters/returns typed. Use `from typing import Any, Dict, List, Optional, Union, Tuple, Callable`

**Patterns**:
- Functions: `def func(param: Type) -> ReturnType:`
- Optional: `Optional[Type]` for nullable
- Multiple types: `Union[Type1, Type2]`
- Collections: `List[Type]`, `Dict[str, Any]`
- Async: `async def func() -> Type:`
- Classes: self untyped, others typed

**Template**:
```python
def func(name: str, data: Optional[Dict[str, Any]] = None) -> bool:
    return data is not None

async def async_func(url: str, timeout: int = 30) -> Dict[str, Any]:
    return {"status": "success"}

class Example:
    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
    
    def process(self, items: List[str]) -> Tuple[bool, Optional[str]]:
        return True, None
```

## UNIT TESTING STANDARDS
**Structure**: `tests/test_[module].py`, pytest framework, descriptive names: `test_function_when_condition_then_expected`

**Coverage**: Normal/edge/error cases, mock externals, `@pytest.mark.asyncio` for async, assert type compliance

**Template**:
```python
import pytest
from unittest.mock import patch

def test_func_when_valid_input_then_returns_expected():
    """Test description."""
    result = func("test", 30)
    assert result == "expected"
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_async_func_when_called_then_returns_dict():
    result = await async_func("url")
    assert isinstance(result, dict)

@patch('module.external_call')
def test_func_when_api_fails_then_handles_error(mock_api):
    mock_api.side_effect = Exception("Error")
    assert func_with_api() is None
```

## CODE QUALITY REQUIREMENTS
- **Naming**: Descriptive, codebase-consistent
- **Documentation**: Comprehensive docstrings (Args, Returns, Raises), usage examples for complex functions
- **Error Handling**: Explicit try/except, logging over print, input validation
- **Dependencies**: Community-standard libraries, Path objects for files
- **Structure**: Follow existing patterns, imports organization

## ERROR HANDLING PATTERN
```python
def robust_func(data: Dict[str, Any]) -> Optional[str]:
    """
    Process data with error handling.
    
    Args:
        data: Processing input dictionary
        
    Returns:
        Result string or None on failure
        
    Raises:
        ValueError: Invalid data format
        KeyError: Missing required fields
    """
    try:
        if not isinstance(data, dict):
            raise ValueError("Data must be dictionary")
        return f"Processed: {data['required_field']}"
    except KeyError as e:
        logger.error(f"Missing field: {e}")
        return None
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return None
```

## REPORTING STANDARDS
- **Style**: Concise, factual, minimal flowery language
- **Task Completion**: Brief status reports, avoid excessive enthusiasm
- **Assessment Documents**: Direct technical summaries, not formal review presentations

## RESEARCH REPORT STANDARDS
- **Format**: Dense information structure, minimal context overhead
- **Compatibility**: Sequential LLM task processing
- **Storage**: Feature-specific project folders
- **Efficiency**: Optimized for LLM analysis and consumption
