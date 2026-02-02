# YAML Spec Runners

E2E API validation tests that launch real server processes.

## Overview

These are **not pytest tests**. They:
1. Start CalendarBot Lite server
2. Start HTTP server for ICS fixtures
3. Call `/api/whats-next` with datetime overrides
4. Validate responses against YAML specifications

## Usage

```bash
# Activate venv first
. venv/bin/activate

# Run API spec tests
python -m tests.spec_runners.runner

# Run with custom specs
python -m tests.spec_runners.runner --specs path/to/specs.yaml

# Run Alexa spec tests
python -m tests.spec_runners.alexa_runner
```

## Files

- `runner.py` - Main test runner for `/api/whats-next` endpoint
- `alexa_runner.py` - Alexa-specific test runner for Alexa endpoints
- `specs.yaml` - API test specifications (31 scenarios)
- `alexa_specs.yaml` - Alexa intent specifications
- `utils.py` - Helper utilities (port finding, process management, etc.)

## Adding Tests

Edit `specs.yaml` to add new test cases:

```yaml
- test_id: my_new_test
  description: What this test validates
  category: recurring
  ics_file: my-fixture.ics
  datetime_override: '2025-11-05T08:00:00-07:00'
  expected:
    meeting:
      subject: Expected Subject
      start_iso: '2025-11-05T16:00:00Z'
```

## Pytest Integration

These runners are also used by pytest integration tests:
- `tests/lite/integration/test_lite_runner.py` - Runs specs via pytest
- `tests/lite/integration/test_alexa_runner.py` - Runs Alexa specs via pytest
