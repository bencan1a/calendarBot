# Test Migration Strategy

This document outlines the strategy for migrating tests and maintaining test coverage during the restructuring of the calendarbot and calendarbot_epaper packages.

## Current Testing Structure

The current testing structure includes:

1. **Main Package Tests**: Tests for the calendarbot package in `tests/unit/`, `tests/integration/`, etc.
2. **E-Paper Tests**: Tests for the calendarbot_epaper package in `tests/unit/epaper/`

## Test Migration Principles

The test migration will follow these principles:

1. **Maintain Coverage**: Ensure that all functionality continues to be tested
2. **Test-Driven Migration**: Use tests to verify that functionality is preserved during migration
3. **Incremental Changes**: Migrate tests in small, manageable increments
4. **Parallel Testing**: Run tests for both old and new structures during the transition
5. **Comprehensive Verification**: Verify all aspects of functionality, including edge cases

## Test Migration Steps

### Phase 1: Establish Baseline Coverage

1. Run the current test suite to establish a baseline coverage report:

```bash
# Generate coverage report for current structure
pytest --cov=calendarbot --cov=calendarbot_epaper tests/
```

2. Save the coverage report for later comparison:

```bash
# Save coverage report
coverage html -d coverage-baseline
```

### Phase 2: Create Test Fixtures for New Structure

1. Create test fixtures for the new structure:

```python
# In tests/conftest.py

@pytest.fixture
def mock_epaper_available():
    """Mock e-Paper hardware as available."""
    with patch("calendarbot.display.epaper.EPAPER_AVAILABLE", True):
        yield

@pytest.fixture
def mock_epaper_unavailable():
    """Mock e-Paper hardware as unavailable."""
    with patch("calendarbot.display.epaper.EPAPER_AVAILABLE", False):
        yield
```

### Phase 3: Migrate Display Abstraction Tests

1. Move display abstraction tests:

```bash
# Create new test directory
mkdir -p tests/unit/display/epaper

# Move display abstraction tests
cp tests/unit/epaper/display/* tests/unit/display/epaper/
```

2. Update imports in the moved tests:

```python
# In tests/unit/display/epaper/*.py
# Change imports like:
# from calendarbot_epaper.display.abstraction import DisplayAbstractionLayer
# To:
# from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
```

3. Run the tests to verify functionality:

```bash
# Run tests for display abstraction
pytest tests/unit/display/epaper/
```

### Phase 4: Migrate Driver Tests

1. Move driver tests:

```bash
# Create new test directory
mkdir -p tests/unit/display/epaper/drivers
mkdir -p tests/unit/display/epaper/drivers/waveshare

# Move driver tests
cp tests/unit/epaper/drivers/* tests/unit/display/epaper/drivers/
cp tests/unit/epaper/drivers/waveshare/* tests/unit/display/epaper/drivers/waveshare/
```

2. Update imports in the moved tests:

```python
# In tests/unit/display/epaper/drivers/*.py
# Change imports like:
# from calendarbot_epaper.drivers.eink_driver import EInkDriver
# To:
# from calendarbot.display.epaper.drivers.eink_driver import EInkDriver
```

3. Run the tests to verify functionality:

```bash
# Run tests for drivers
pytest tests/unit/display/epaper/drivers/
```

### Phase 5: Migrate Utility Tests

1. Move utility tests:

```bash
# Create new test directory
mkdir -p tests/unit/display/epaper/utils

# Move utility tests
cp tests/unit/epaper/utils/* tests/unit/display/epaper/utils/
```

2. Update imports in the moved tests:

```python
# In tests/unit/display/epaper/utils/*.py
# Change imports like:
# from calendarbot_epaper.utils.colors import EPaperColors
# To:
# from calendarbot.display.epaper.utils.colors import EPaperColors
```

3. Run the tests to verify functionality:

```bash
# Run tests for utilities
pytest tests/unit/display/epaper/utils/
```

### Phase 6: Migrate Integration Tests

1. Move integration tests:

```bash
# Create new test directory
mkdir -p tests/unit/display/epaper/renderers

# Move integration tests
cp tests/unit/epaper/integration/* tests/unit/display/epaper/renderers/
```

2. Update imports in the moved tests:

```python
# In tests/unit/display/epaper/renderers/*.py
# Change imports like:
# from calendarbot_epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
# To:
# from calendarbot.display.epaper.renderers.eink_whats_next_renderer import EInkWhatsNextRenderer
```

3. Run the tests to verify functionality:

```bash
# Run tests for integration
pytest tests/unit/display/epaper/renderers/
```

### Phase 7: Create Tests for New Components

1. Create tests for the new feature detection module:

```python
# In tests/unit/display/epaper/test_init.py
import pytest
from unittest.mock import patch, Mock

def test_check_epaper_availability_when_all_dependencies_available_then_returns_true():
    """Test that check_epaper_availability returns True when all dependencies are available."""
    with patch("importlib.util.find_spec", return_value=Mock()):
        from calendarbot.display.epaper import check_epaper_availability
        
        is_available, reason = check_epaper_availability()
        
        assert is_available is True
        assert reason is None

def test_check_epaper_availability_when_rpi_gpio_missing_then_returns_false():
    """Test that check_epaper_availability returns False when RPi.GPIO is missing."""
    def mock_find_spec(name):
        if name == "RPi.GPIO":
            return None
        return Mock()
    
    with patch("importlib.util.find_spec", side_effect=mock_find_spec):
        from calendarbot.display.epaper import check_epaper_availability
        
        is_available, reason = check_epaper_availability()
        
        assert is_available is False
        assert reason == "RPi.GPIO not available"
```

2. Create tests for the hardware abstraction layer:

```python
# In tests/unit/display/epaper/test_hardware.py
import pytest
from unittest.mock import patch, Mock

def test_get_driver_when_epaper_available_and_waveshare_driver_then_returns_waveshare_driver():
    """Test that get_driver returns Waveshare driver when e-Paper is available."""
    with patch("calendarbot.display.epaper.EPAPER_AVAILABLE", True):
        from calendarbot.display.epaper.hardware import HardwareManager
        from calendarbot.display.epaper.drivers.waveshare.epd4in2b_v2 import EPD4in2bV2
        
        with patch("calendarbot.display.epaper.drivers.waveshare.epd4in2b_v2.EPD4in2bV2") as mock_driver:
            mock_driver.return_value = Mock()
            
            driver = HardwareManager.get_driver("waveshare_4in2b_v2")
            
            assert driver is not None
            assert isinstance(driver, EPD4in2bV2)
```

### Phase 8: Update RendererFactory Tests

1. Update the RendererFactory tests to use the new structure:

```python
# In tests/unit/test_renderer_factory.py
import pytest
from unittest.mock import patch, Mock

def test_get_available_renderers_when_epaper_available_then_includes_eink():
    """Test that get_available_renderers includes eink-whats-next when e-Paper is available."""
    with patch("calendarbot.display.epaper.EPAPER_AVAILABLE", True):
        from calendarbot.display.renderer_factory import RendererFactory
        
        available = RendererFactory.get_available_renderers()
        
        assert "eink-whats-next" in available
```

### Phase 9: Verify Full Test Coverage

1. Run the full test suite to verify coverage:

```bash
# Run all tests
pytest
```

2. Generate a coverage report:

```bash
# Generate coverage report
pytest --cov=calendarbot tests/
```

3. Compare with the baseline coverage:

```bash
# Compare coverage reports
coverage html -d coverage-new
```

4. Identify and address any gaps in coverage.

### Phase 10: Create Integration Tests for New Structure

1. Create integration tests that verify the end-to-end functionality:

```python
# In tests/integration/test_epaper_integration.py
import pytest
from unittest.mock import patch, Mock

def test_renderer_factory_when_epaper_available_then_creates_eink_renderer():
    """Test that RendererFactory creates EInkWhatsNextRenderer when e-Paper is available."""
    with patch("calendarbot.display.epaper.EPAPER_AVAILABLE", True):
        from calendarbot.display.renderer_factory import RendererFactory
        from calendarbot.display.epaper.renderers.eink_whats_next_renderer import EInkWhatsNextRenderer
        
        with patch("calendarbot.display.epaper.renderers.eink_whats_next_renderer.EInkWhatsNextRenderer") as mock_renderer:
            mock_renderer.return_value = Mock()
            
            renderer = RendererFactory.create_renderer(renderer_type="eink-whats-next", settings=Mock())
            
            assert renderer is not None
            assert isinstance(renderer, EInkWhatsNextRenderer)
```

## Test Maintenance Strategy

After the migration is complete:

1. **Continuous Testing**: Run tests regularly to ensure functionality is maintained
2. **Coverage Monitoring**: Monitor test coverage to ensure it remains high
3. **Test Refactoring**: Refactor tests as needed to improve maintainability
4. **Test Documentation**: Document test strategies and patterns

## Handling Test Failures

If tests fail during migration:

1. **Identify Root Cause**: Determine why the test is failing
2. **Fix Implementation**: Update the implementation to fix the issue
3. **Verify Fix**: Run the test again to verify the fix
4. **Document Issue**: Document the issue and solution for future reference

## Test Deprecation Strategy

Once the migration is complete and all tests are passing:

1. **Mark Old Tests as Deprecated**: Add deprecation notices to the old tests
2. **Plan for Removal**: Plan for the eventual removal of the old tests
3. **Communicate Timeline**: Communicate the timeline for removal to the team

## Conclusion

This test migration strategy ensures that all functionality continues to be tested throughout the migration process. By following this strategy, we can be confident that the restructured code will work as expected.