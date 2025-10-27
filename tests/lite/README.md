# CalendarBot Lite Tests

This directory contains all tests specifically for the **calendarbot_lite** module, which is the lightweight Alexa skill implementation.

## Organization

All lite-related tests are organized here for easy isolation and testing:

- `test_lite_fetcher.py` - HTTP client and ICS fetching tests
- `test_http_client.py` - Shared HTTP client and connection pool tests
- `test_lite_parser_streaming.py` - ICS parser streaming tests
- `test_rrule_streaming_optimization.py` - RRule expansion and worker pool tests
- `test_lite_done_for_day.py` - Done-for-day functionality tests
- `test_lite_logging.py` - Lite logging functionality tests
- `test_config_and_skipped_store.py` - Configuration and skipped event store tests
- `test_calendarbot_lite_harness.py` - Integration test harness
- `test_alexa_launch_intent.py` - Alexa launch intent handler tests
- `test_alexa_integration.py` - Alexa skill integration tests
- `test_alexa_ssml.py` - SSML generation and formatting tests
- `test_concurrency_system.py` - Concurrency system and worker pool tests
- `test_server_port_conflict.py` - Server port conflict handling tests

## Running Lite Tests Only

To run only the calendarbot_lite tests:

```bash
# Activate virtual environment
. venv/bin/activate

# Run all lite tests
pytest tests/lite/

# Run with coverage
pytest tests/lite/ --cov=calendarbot_lite --cov-report=term-missing

# Run specific test file
pytest tests/lite/test_lite_fetcher.py -v

# Run with markers
pytest tests/lite/ -m "not slow"
```

## Running All Other Tests (Excluding Lite)

To run the main calendarbot tests without lite tests:

```bash
# Run all tests except lite
pytest tests/ --ignore=tests/lite/

# With coverage for main calendarbot module only
pytest tests/ --ignore=tests/lite/ --cov=calendarbot --cov-report=term-missing
```

## Test Count

This directory contains **251 tests** covering the calendarbot_lite module.

## Related Code

Tests in this directory test code in:
- `calendarbot_lite/` - Main lite module directory
- `lambda_function.py` - AWS Lambda handler for Alexa skill
