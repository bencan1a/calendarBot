# Test Suite

## Directory Structure

```
tests/
├── lite/           # Main pytest suite for calendarbot_lite (1,100+ tests)
│   ├── unit/       # Unit tests
│   ├── integration/# Integration tests
│   ├── performance/# Performance tests
│   └── smoke/      # Smoke tests
├── kiosk/          # Kiosk deployment tests (150+ tests)
├── fixtures/       # Shared test data and mocks
│   ├── ics/        # ICS calendar fixtures
│   └── *.py        # Mock factories
└── spec_runners/   # YAML-based E2E API validators (not pytest)
```

## Running Tests

### Primary Test Suite (pytest)

```bash
# Run all lite tests
./run_lite_tests.sh

# Run with coverage
./run_lite_tests.sh --coverage

# Run specific markers
pytest tests/lite/ -m "unit"
pytest tests/lite/ -m "integration"
pytest tests/lite/ -m "not slow"

# Run kiosk tests
pytest tests/kiosk/ -v
```

### YAML Spec Runners (E2E API validation)

These are separate from pytest - they launch real server processes.

```bash
# Run API spec tests
python -m tests.spec_runners.runner

# Run Alexa spec tests
python -m tests.spec_runners.alexa_runner
```

See [spec_runners/README.md](spec_runners/README.md) for details.

## Adding Tests

- **Unit tests:** `tests/lite/unit/test_<module>.py`
- **Integration tests:** `tests/lite/integration/test_<feature>.py`
- **Fixtures:** `tests/fixtures/`

## Test Quality Standards

See [docs/pytest-best-practices.md](../docs/pytest-best-practices.md):
- All assertions must be unconditional
- Test ONE specific outcome
- Mock external I/O, not business logic

## Test Markers

| Marker | Description |
|--------|-------------|
| `unit` | Fast, isolated unit tests |
| `integration` | Tests requiring multiple components |
| `smoke` | Quick validation tests |
| `slow` | Long-running tests (excluded from quick runs) |
| `performance` | Performance benchmarks |

## Coverage

```bash
# Run with coverage report
./run_lite_tests.sh --coverage

# Coverage HTML report generated at: htmlcov-lite/
```

Coverage is configured in `pyproject.toml` to measure `calendarbot_lite/` only.
