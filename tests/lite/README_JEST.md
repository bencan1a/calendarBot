# Jest Tests for CalendarBot Lite

## Overview

This directory contains Jest tests for the JavaScript components of CalendarBot Lite.

## Test Files

### `whatsnext.test.js`

Comprehensive test suite for `calendarbot_lite/whatsnext.js` - the What's Next View JavaScript functionality.

**Status**: ✅ **All 22 tests passing**

**Coverage**:
- 75.6% statements
- 58.21% branches
- 76.19% functions
- 75.3% lines

#### Test Categories

**Initialization (4 tests - ✅ all passing)**
- Verifies the script initializes correctly
- Tests DOM element caching
- Validates error handling for missing elements
- Confirms polling starts on initialization

**API Calls (3 tests - ✅ all passing)**
- Tests `/api/whats-next` endpoint is called
- Validates correct HTTP headers are sent
- Confirms 60-second polling interval

**Display Updates (6 tests - ✅ all passing)**
- ✅ Updates DOM with meeting title
- ✅ Displays countdown in hours format
- ✅ Displays countdown in minutes format
- ✅ Applies critical CSS class when < 5 minutes
- ✅ Applies warning CSS class when < 15 minutes
- ✅ Shows "No upcoming meetings" when no data

**Bottom Section Context Messages (3 tests - ✅ all passing)**
- ✅ "Starting very soon" for meetings < 2 minutes
- ✅ "Meeting in progress" for started meetings
- ✅ "Plenty of time" for meetings > 60 minutes

**Polling Behavior (2 tests - ✅ all passing)**
- ✅ Stops polling when page is hidden
- ✅ Resumes polling when page becomes visible

**Cleanup (2 tests - ✅ all passing)**
- ✅ Cleanup on beforeunload event
- ✅ Cleanup function stops polling

**Error Handling (2 tests - ✅ all passing)**
- ✅ Retry logic for network errors
- ✅ HTTP error handling

## Running Tests

```bash
# Run all Jest tests
npm test

# Run only whatsnext tests
npm test -- whatsnext.test.js

# Run with coverage report
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

## Test Configuration

Jest configuration is in `jest.config.js`:
- Test environment: jsdom
- Test patterns: `tests/lite/**/*.test.js`
- Coverage from: `calendarbot_lite/**/*.js`
- Coverage thresholds: 60% (55% for branches)

## Key Implementation Details

The test suite uses:
- `jest.useFakeTimers()` for controlling time-based operations
- `jest.advanceTimersByTimeAsync()` for properly handling async operations with timers
- `mockImplementation()` for consistent mock behavior across all async operations
- jsdom for DOM manipulation testing

## Future Improvements

1. Add tests for skip meeting functionality (button click → API call → page reload)
2. Add tests for online/offline event handling edge cases
3. Increase branch coverage to 60%+ (currently 58.21%)
4. Add integration tests with actual backend API mocking
