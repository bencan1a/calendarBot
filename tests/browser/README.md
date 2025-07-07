# Browser Automation Test Suite

This directory contains comprehensive browser automation tests for the CalendarBot web interface using Puppeteer (pyppeteer).

## Overview

The browser test suite provides end-to-end testing of the CalendarBot web interface across multiple dimensions:

- **Functional Testing**: Core application functionality and user workflows
- **API Integration**: Browser-based testing of REST API endpoints
- **Responsive Design**: Multi-viewport testing (mobile, tablet, desktop)
- **Visual Regression**: Screenshot comparison and UI consistency
- **Performance Testing**: Page load times, API response times, memory usage
- **Accessibility Testing**: WCAG compliance, keyboard navigation, screen reader support
- **Cross-Browser Compatibility**: JavaScript/CSS feature support validation

## Test Structure

### Core Infrastructure (`conftest.py`)
- **Browser fixtures**: Automated Puppeteer browser management
- **Page utilities**: Common page interaction helpers
- **Visual regression**: Screenshot capture and comparison tools
- **Performance tracking**: Timing and memory usage monitoring
- **Accessibility helpers**: WCAG compliance validation utilities

### Test Modules

#### 1. Web Interface Tests (`test_web_interface.py`)
Tests core application functionality:
- Calendar page loading and initialization
- Navigation controls (prev, next, today, week-start, week-end)
- Theme switching (eink, standard, eink-rpi)
- JavaScript functionality validation
- Keyboard navigation support
- Complete user workflow scenarios

#### 2. API Integration Tests (`test_api_integration.py`)
Browser-based API endpoint testing:
- `/api/navigate` - Calendar navigation
- `/api/theme` - Theme switching
- `/api/refresh` - Data refresh
- `/api/status` - Application status
- State persistence validation
- Error handling and recovery
- Concurrent API call testing

#### 3. Responsive Design Tests (`test_responsive_design.py`)
Multi-viewport testing:
- **Mobile**: 375x667 (iPhone SE)
- **Tablet**: 768x1024 (iPad)
- **Desktop**: 1920x1080 (Standard desktop)
- Touch gesture simulation
- Viewport transition testing
- CSS media query validation

#### 4. Visual Regression Tests (`test_visual_regression.py`)
UI consistency validation:
- Theme-specific screenshots
- Viewport-specific layouts
- Calendar state comparisons
- Interaction state capture
- Baseline management
- Difference highlighting

#### 5. Performance Tests (`test_performance.py`)
Application performance validation:
- Page load time analysis
- API response time monitoring
- JavaScript execution profiling
- Memory usage tracking
- Stress testing scenarios
- Performance threshold validation

#### 6. Accessibility Tests (`test_accessibility.py`)
WCAG compliance testing:
- Keyboard navigation validation
- ARIA label verification
- Color contrast analysis
- Screen reader compatibility
- Focus indicator visibility
- Touch target size validation

#### 7. Cross-Browser Tests (`test_cross_browser.py`)
Browser compatibility validation:
- JavaScript feature support
- DOM API compatibility
- CSS property support
- Error handling consistency

## Running Browser Tests

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure CalendarBot is running
python main.py &
```

### Test Execution

```bash
# Activate virtual environment
. venv/bin/activate

# Run all browser tests
python tests/run_tests.py --browser

# Run specific test categories
python tests/run_tests.py --accessibility
python tests/run_tests.py --visual-regression
python tests/run_tests.py --responsive
python tests/run_tests.py --cross-browser

# Run specific test files
python tests/run_tests.py --specific tests/browser/test_web_interface.py
python tests/run_tests.py --specific tests/browser/test_performance.py

# Include browser tests in fast critical path
python tests/run_tests.py --fast

# Full regression suite
python tests/run_tests.py --all
```

### Test Markers

The following pytest markers are available:

- `@pytest.mark.accessibility` - Accessibility compliance tests
- `@pytest.mark.visual_regression` - Visual regression tests (slower)
- `@pytest.mark.responsive` - Responsive design tests
- `@pytest.mark.cross_browser` - Cross-browser compatibility tests
- `@pytest.mark.slow` - Performance and stress tests
- `@pytest.mark.performance` - Performance-specific tests

## Configuration

### Browser Settings
- **Headless Mode**: Tests run in headless Chrome by default
- **Viewport**: Configurable per test scenario
- **Screenshots**: Captured on test failures and for visual regression
- **Timeouts**: Configurable wait times for page loads and interactions

### Visual Regression
- **Baselines**: Stored in `tests/browser/baselines/`
- **Screenshots**: Generated in `tests/browser/screenshots/`
- **Threshold**: Configurable pixel difference tolerance
- **Regeneration**: `--update-baselines` flag for baseline updates

### Performance Thresholds
- **Page Load**: < 2 seconds
- **API Response**: < 500ms
- **JavaScript Execution**: < 100ms
- **Memory Usage**: < 50MB increase per operation

## Test Data Management

### Fixtures
- **Mock calendar data**: Consistent test data across scenarios
- **Test databases**: Isolated test environment
- **Mock servers**: Controlled external dependencies

### State Management
- **Browser isolation**: Each test gets a fresh browser instance
- **Data cleanup**: Automatic test data cleanup
- **State reset**: Calendar state reset between tests

## Debugging and Troubleshooting

### Debug Mode
```bash
# Run with debug output
python tests/run_tests.py --browser -v -s

# Capture screenshots on failure
pytest tests/browser/ --capture=no --tb=short
```

### Common Issues

1. **Browser Launch Failures**
   - Ensure Chrome/Chromium is installed
   - Check system dependencies for Puppeteer
   - Verify headless mode compatibility

2. **Visual Regression Failures**
   - Review screenshot differences in `tests/browser/screenshots/`
   - Update baselines if changes are intentional
   - Check for timing-related rendering differences

3. **Performance Test Failures**
   - Verify system resources availability
   - Check for background processes affecting performance
   - Review performance threshold settings

4. **Accessibility Failures**
   - Validate HTML structure and ARIA attributes
   - Check keyboard navigation implementation
   - Verify color contrast ratios

## Continuous Integration

### CI Pipeline Integration
```yaml
# Example GitHub Actions configuration
- name: Run Browser Tests
  run: |
    . venv/bin/activate
    python main.py &
    sleep 5  # Allow server startup
    python tests/run_tests.py --browser --accessibility
    python tests/run_tests.py --responsive
```

### Test Reporting
- **Coverage**: HTML reports in `htmlcov/browser/`
- **Screenshots**: Visual test artifacts preserved
- **Performance**: Timing reports and trend analysis
- **Accessibility**: WCAG compliance reports

## Contributing

### Adding New Tests
1. Follow existing test patterns in respective modules
2. Use appropriate pytest markers for categorization
3. Include comprehensive docstrings and assertions
4. Consider performance impact and test execution time

### Visual Regression Updates
1. Review screenshot changes carefully
2. Update baselines only when UI changes are intentional
3. Document visual changes in commit messages
4. Test across multiple viewports when applicable

### Performance Test Guidelines
1. Set realistic performance thresholds
2. Account for CI environment variations
3. Use relative performance measurements when possible
4. Document performance requirements clearly

## Test Coverage Goals

- **Functional Coverage**: 100% of user-facing features
- **API Coverage**: 100% of REST endpoints
- **Responsive Coverage**: All supported viewports
- **Accessibility Coverage**: WCAG 2.1 AA compliance
- **Performance Coverage**: All critical user paths
- **Cross-Browser Coverage**: Modern browser feature sets

This comprehensive browser test suite ensures the CalendarBot web interface maintains high quality, performance, and accessibility standards across all supported platforms and browsers.
