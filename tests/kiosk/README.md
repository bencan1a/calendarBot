# Kiosk Deployment Tests

This directory contains tests for the CalendarBot kiosk deployment system, which provides a robust, self-healing calendar display for Raspberry Pi devices.

## Quick Reference (For Agents)

**Test Files:**
- `test_watchdog.py` (34KB) - Watchdog monitoring system (69 tests, ~2 min)
- `test_scripts_enhanced.py` (53KB) - Enhanced script tests (37 tests, ~1 min)
- `test_scripts_integration.py` (25KB) - Basic script tests (24 tests, ~30 sec)
- `test_installer.py` (71KB) - **Installer validation** (41 tests: 35 unit + 6 E2E, 10-15 min total)

**E2E Infrastructure:**
- `Dockerfile.e2e` - Docker image with systemd (Debian Bookworm)
- `docker-compose.e2e.yml` - Local dev environment
- `e2e_fixtures.py` - Container lifecycle management
- `e2e_helpers.py` - Installer execution and validation helpers

**Key Commands:**
```bash
# Run unit tests only (FAST - use in PR CI)
pytest tests/kiosk/ -m "not e2e"

# Run E2E tests (SLOW - 10-15 min, use nightly)
pytest tests/kiosk/test_installer.py::TestInstallerE2E -v

# Run specific E2E test
pytest tests/kiosk/test_installer.py::TestInstallerE2E::test_installer_when_section_1_then_installs_base_components -v
```

**CI/CD:**
- **PR CI**: Unit tests only (< 5 min) via smart test selector
- **Nightly**: Full E2E tests at 3 AM UTC via `.github/workflows/e2e-kiosk.yml`
- **Smart Selection**: Detects `kiosk/` file changes, includes kiosk unit tests (excludes E2E)

## Overview

The kiosk deployment tests validate the monitoring, recovery, and logging infrastructure that enables 24/7 uptime for CalendarBot kiosk displays. These tests cover both Python-based watchdog components and bash-based monitoring scripts.

## Test Files

### test_watchdog.py (889 lines)
Tests for the kiosk watchdog monitoring and recovery system.

**Components Tested:**
- `WatchdogState` - Persistent state management for recovery tracking
- `StructuredLogger` - JSON logging for monitoring events
- `SystemDiagnostics` - CPU load, memory, and resource monitoring
- `HealthChecker` - HTTP health checks and render probes
- `RecoveryManager` - Progressive recovery actions with rate limiting

**Key Test Areas:**
- State persistence and file locking
- Structured JSON logging
- System resource monitoring and degradation detection
- Health endpoint checking and render validation
- Recovery action rate limiting and cooldown
- Integration scenarios and escalation flows

**Example Tests:**
```python
# State management
test_load_state_when_file_missing_then_returns_defaults()
test_save_state_when_valid_data_then_persists_correctly()

# Health checking
test_check_health_endpoint_when_healthy_then_returns_true()
test_check_render_probe_when_marker_missing_then_returns_false()

# Recovery actions
test_restart_browser_when_successful_then_returns_true()
test_can_perform_action_when_rate_limited_then_returns_false()
```

### test_scripts_integration.py (628 lines)
Integration tests for kiosk bash scripts and their interaction with calendarbot_lite.

**Scripts Tested:**
- `log-shipper.sh` - Remote log shipping via webhooks
- `log-aggregator.sh` - Daily/weekly log aggregation
- `critical-event-filter.sh` - Critical event filtering and alerting
- `monitoring-status.sh` - System status dashboard

**Key Test Areas:**
- Script help and version commands
- Configuration via environment variables
- Webhook integration testing
- Log file processing and JSON output
- Script permissions and dependencies
- Cross-script data flow
- Integration with calendarbot_lite monitoring_logging module

**Example Tests:**
```python
# Script execution
test_log_shipper_when_help_then_shows_usage()
test_monitoring_status_when_health_then_shows_health_info()

# Integration
test_monitoring_logging_integration_when_server_import_then_no_errors()
test_structured_logging_schema_when_created_then_follows_specification()

# End-to-end
test_script_chain_when_executed_then_proper_data_flow()
```

### test_scripts_enhanced.py (593 lines) - **Phase 2**
Enhanced integration tests for monitoring script functionality and operational reliability.

**Scripts Tested (Deep Validation):**
- `log-aggregator.sh` - JSON report generation, retention, size limits
- `log-shipper.sh` - Webhook payloads, rate limiting, retry logic
- `critical-event-filter.sh` - Deduplication, hourly limits, state management
- `monitoring-status.sh` - System metrics, health checks, caching

**Key Test Areas:**
- JSON output structure validation
- Webhook payload formatting and authentication
- Rate limiting and deduplication logic
- State file persistence and management
- Configuration via environment variables
- Script constant validation (size limits, timeouts)
- Data flow between script components

**Test Classes:**
```python
@pytest.mark.integration
class TestLogAggregatorJsonOutput:       # 8 tests - JSON validation
class TestLogShipperWebhook:             # 6 tests - webhook integration
class TestCriticalEventFilterLogic:     # 5 tests - deduplication
class TestMonitoringStatusMetrics:      # 6 tests - metrics collection
class TestScriptDataFlow:                # 4 tests - integration flow
class TestScriptConfiguration:          # 4 tests - env vars & config

@pytest.mark.unit
class TestScriptConstants:              # 4 tests - constants validation
```

**Example Tests:**
```python
# JSON validation
test_log_aggregator_when_report_generated_then_valid_json_structure()
test_monitoring_status_when_json_output_then_valid_structure()

# Webhook integration
test_log_shipper_when_payload_created_then_valid_json()
test_log_shipper_when_rate_limited_then_skips_shipping()

# Deduplication & filtering
test_critical_filter_when_duplicate_events_then_has_dedup_logic()
test_critical_filter_when_hourly_limit_configured_then_has_throttling()

# Configuration
test_scripts_when_environment_vars_then_override_defaults()
test_log_shipper_when_constants_defined_then_reasonable_values()
```

### test_installer.py (71KB, 1994 lines) - **Phase 1 & 3**
Comprehensive tests for the automated kiosk installer, including both unit tests and E2E installation validation.

**Test Structure:**
- **Unit Tests (35 tests)**: Configuration parsing, dry-run mode, validation logic
- **E2E Tests (6 tests)**: Full installation in Docker containers with systemd

**Unit Test Classes:**
- `TestConfigurationParsing` - YAML config validation
- `TestDryRunMode` - Preview without system changes
- `TestStateDetection` - Fresh vs existing installation detection
- `TestErrorHandling` - Error recovery and logging
- `TestBackupMechanisms` - Configuration backup logic
- `TestSectionConfiguration` - Section-specific settings
- `TestConfigurationValidation` - Field validation rules
- `TestVerboseOutput` - Debug output formatting
- `TestUpdateMode` - Update flag behavior
- `TestAdvancedOptions` - APT, git, firewall options
- `TestKioskConfiguration` - Kiosk-specific settings
- `TestAlexaConfiguration` - Alexa integration settings
- `TestMonitoringConfiguration` - Monitoring settings

**E2E Test Classes (Phase 3):**
- `TestInstallerE2E` - 6 comprehensive installation tests
  - `test_installer_when_section_1_then_installs_base_components` - Base installation (CalendarBot server, venv, systemd)
  - `test_installer_when_section_2_then_installs_kiosk_components` - Kiosk mode (X session, Chromium, watchdog)
  - `test_installer_when_section_3_then_installs_alexa_components` - Alexa integration (Nginx, SSL, Caddy reverse proxy)
  - `test_installer_when_section_4_then_installs_monitoring_components` - Monitoring (cron jobs, log aggregation, rsyslog)
  - `test_installer_idempotency` - Runs installer twice to verify safe re-execution
  - `test_installer_update_mode` - Validates --update flag preserves customizations

**E2E Test Characteristics:**
- **Duration**: ~10-15 minutes for all 6 tests (~60-90s per test)
- **Environment**: Docker containers with systemd enabled (Debian Bookworm)
- **Validation**: Real package installation, file creation, service enablement
- **Coverage**: All 4 installation sections + idempotency + update mode

**Example Unit Tests:**
```python
# Configuration
test_installer_when_valid_config_then_loads_successfully()
test_installer_when_missing_username_then_validation_fails()

# Dry-run mode
test_installer_when_dry_run_then_shows_preview()
test_installer_when_dry_run_then_no_system_changes()
```

**Example E2E Tests:**
```python
# Run full installation in Docker container with systemd
test_installer_when_section_1_then_installs_base_components()
  # Validates: repo cloned, venv created, .env file, systemd service enabled

test_installer_idempotency()
  # Runs installer twice, verifies no errors and no file duplication
```

## E2E Test Infrastructure (Phase 3)

### Docker-Based E2E Testing
E2E tests use Docker containers with systemd to validate real installation behavior.

**Infrastructure Files:**
- `Dockerfile.e2e` (2.7KB) - Debian Bookworm base with systemd, Python, and build tools
- `docker-compose.e2e.yml` (583 bytes) - Local dev environment for E2E testing
- `e2e_fixtures.py` (7.9KB) - Pytest fixtures for container lifecycle management
- `e2e_helpers.py` (11KB) - Helper functions for running installer and validating results
- `conftest.py` (458 bytes) - Shared pytest configuration

**Container Features:**
- Systemd enabled (for service management testing)
- Privileged mode (for package installation)
- Workspace mounted at `/workspace` (for accessing installer scripts)
- Fresh container per test (ensures isolation)
- Automatic cleanup after tests

**Helper Functions (`e2e_helpers.py`):**
```python
run_installer_in_container(container, config_yaml, target_user="testuser")
  # Runs installer in container, returns (exit_code, stdout, stderr)

prepare_repository_in_container(container, target_user, target_path)
  # Copies workspace to container to avoid git clone authentication issues

container_file_exists(container, file_path)
  # Checks if file exists in container

container_read_file(container, file_path)
  # Reads file content from container

container_dir_exists(container, dir_path)
  # Checks if directory exists in container
```

### CI/CD Integration

**GitHub Actions Workflows:**

1. **Nightly E2E Tests** (`.github/workflows/e2e-kiosk.yml`)
   - Schedule: Every night at 3 AM UTC
   - Duration: ~20-25 minutes (includes Docker image build + test execution)
   - Trigger: Also available for manual runs via `workflow_dispatch`
   - Tests: All 6 E2E tests (Section 1-4, idempotency, update mode)
   - Purpose: Validates installer behavior end-to-end without affecting PR CI speed

2. **Smart Test Selection** (`scripts/smart_test_selector.py`)
   - Detects changes to `kiosk/` directory files
   - Automatically includes kiosk unit tests in PR CI runs
   - **Excludes E2E tests from PR CI** (too slow for rapid iteration)
   - E2E tests run nightly instead to catch integration issues

**Rationale:**
- **PR CI**: Fast feedback (< 5 min) with unit tests for kiosk file changes
- **Nightly**: Comprehensive E2E validation (10-15 min) to catch installer bugs

## Running Kiosk Tests

### Run all kiosk tests (excluding slow E2E)
```bash
pytest tests/kiosk/ -m "not slow"
```

### Run all tests including E2E
```bash
pytest tests/kiosk/
```

### Run specific test files
```bash
# Watchdog tests only
pytest tests/kiosk/test_watchdog.py

# Script integration tests only (basic)
pytest tests/kiosk/test_scripts_integration.py

# Enhanced script tests only (Phase 2)
pytest tests/kiosk/test_scripts_enhanced.py

# Installer unit tests only
pytest tests/kiosk/test_installer.py -m "not e2e"

# Installer E2E tests only (SLOW - 10-15 minutes)
pytest tests/kiosk/test_installer.py::TestInstallerE2E -v
```

### Run with coverage
```bash
pytest tests/kiosk/ --cov=kiosk --cov-report=html
```

### Run specific test categories
```bash
# State management tests
pytest tests/kiosk/test_watchdog.py::TestWatchdogState

# Script permission tests
pytest tests/kiosk/test_scripts_integration.py::TestScriptPermissions

# Integration scenarios
pytest tests/kiosk/test_watchdog.py::TestIntegrationScenarios

# Enhanced script tests by component
pytest tests/kiosk/test_scripts_enhanced.py::TestLogAggregatorJsonOutput
pytest tests/kiosk/test_scripts_enhanced.py::TestLogShipperWebhook
pytest tests/kiosk/test_scripts_enhanced.py::TestCriticalEventFilterLogic
```

## Test Dependencies

### Required Packages
- `pytest` - Test framework
- `pytest-asyncio` - Async test support (for integration tests)
- `pyyaml` - YAML configuration parsing

### E2E Test Dependencies (Phase 3)
- `docker` (Python package) - Docker SDK for container management
- `docker` (system) - Docker Engine installed and running
- `pytest-docker` - Optional, for advanced Docker fixtures

### System Requirements
- Bash shell (for script tests)
- Standard Unix utilities: `curl`, `jq`, `grep`, `awk`
- File system access for temporary test files
- **Docker Engine** - Required for E2E tests (install via `sudo apt-get install docker.io`)

### Optional Dependencies
- `curl` - For webhook testing (some tests will skip if unavailable)
- `jq` - For JSON processing (some tests will skip if unavailable)

### Installing E2E Dependencies
```bash
# Install Docker (if not already installed)
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER  # Add yourself to docker group (logout/login required)

# Install Python E2E dependencies
pip install -e .[e2e]
```

## Test Infrastructure

### Mock Components
Tests use mock implementations of watchdog components that simulate real behavior without requiring:
- Actual file locks
- System-level operations (reboots, service restarts)
- External webhook endpoints
- Running CalendarBot server

### Temporary Files
Tests create temporary directories for:
- State files (`test_state.json`)
- Log outputs
- Script working directories

All temporary files are automatically cleaned up after tests complete.

### Environment Variables
Script tests use environment variables for configuration:
```bash
CALENDARBOT_WATCHDOG_LOG_LEVEL=DEBUG
CALENDARBOT_WATCHDOG_DEBUG=true
CALENDARBOT_LOG_SHIPPER_ENABLED=true
CALENDARBOT_FILTER_DRY_RUN=true
```

## Test Markers

Tests use these pytest markers for categorization:

```python
@pytest.mark.unit           # Unit tests
@pytest.mark.integration    # Integration tests
@pytest.mark.asyncio        # Async tests
@pytest.mark.slow           # Slow-running tests
```

Run specific markers:
```bash
pytest tests/kiosk/ -m unit
pytest tests/kiosk/ -m integration
```

## Related Documentation

- **[kiosk/README.md](../../kiosk/README.md)** - Kiosk deployment overview
- **[kiosk/docs/2_KIOSK_WATCHDOG.md](../../kiosk/docs/2_KIOSK_WATCHDOG.md)** - Watchdog setup guide
- **[kiosk/docs/4_LOG_MANAGEMENT.md](../../kiosk/docs/4_LOG_MANAGEMENT.md)** - Log management guide
- **[tests/lite/](../lite/)** - CalendarBot Lite tests

## Architecture Context

The kiosk deployment uses this architecture:
```
Boot → systemd
  ├─> calendarbot-lite@user.service (CalendarBot server)
  ├─> Auto-login → .bash_profile → startx → .xinitrc → Chromium
  └─> calendarbot-kiosk-watchdog@user.service (monitoring)
```

These tests validate that the monitoring and recovery components work correctly to maintain 24/7 uptime.

## Troubleshooting

### Script tests fail with "command not found"
Some tests require bash utilities. Install missing tools:
```bash
sudo apt-get install curl jq
```

### "Permission denied" errors
Script tests check execute permissions. Ensure scripts are executable:
```bash
chmod +x kiosk/scripts/*.sh
```

### Tests skip with "Network unavailable"
Some webhook tests require network access. These tests gracefully skip if network is unavailable and won't cause test suite failures.

## Test Coverage Summary

| Component | Tests | Type | Duration | File |
|-----------|-------|------|----------|------|
| **Watchdog (Python)** | 69 | Unit/Integration | ~2 min | test_watchdog.py |
| **Scripts (Enhanced)** | 37 | Integration | ~1 min | test_scripts_enhanced.py |
| **Scripts (Integration)** | 24 | Integration | ~30 sec | test_scripts_integration.py |
| **Installer (Unit)** | 35 | Unit | ~30 sec | test_installer.py (non-E2E) |
| **Installer (E2E)** | 6 | E2E | **10-15 min** | test_installer.py (E2E) |
| **Total** | **171** | Mixed | ~15-20 min | All files |

**Note**: E2E tests run nightly (not in PR CI) due to duration. PR CI runs unit tests only for fast feedback.

## Contributing

When adding new kiosk tests:

1. **Watchdog tests** → Add to [test_watchdog.py](test_watchdog.py)
2. **Basic script tests** → Add to [test_scripts_integration.py](test_scripts_integration.py)
3. **Enhanced script tests** → Add to [test_scripts_enhanced.py](test_scripts_enhanced.py)
4. **Installer unit tests** → Add to [test_installer.py](test_installer.py) (non-E2E test classes)
5. **Installer E2E tests** → Add to `TestInstallerE2E` class in [test_installer.py](test_installer.py)

**Test Markers:**
- Use `@pytest.mark.integration` for integration tests
- Use `@pytest.mark.unit` for unit tests
- Use `@pytest.mark.e2e` for E2E tests (automatically marked as slow)
- Use `@pytest.mark.slow` for tests that take > 30 seconds

**Best Practices:**
- Include docstrings explaining what's being tested
- Use temp directories to avoid permission issues
- Clean up temporary files in teardown
- Handle missing dependencies gracefully (use `pytest.skip()`)
- **E2E tests**: Use helper functions from `e2e_helpers.py`
- **E2E tests**: Each test should use a fresh container (via `clean_container` fixture)
- **E2E tests**: Validate actual file contents, not just existence
