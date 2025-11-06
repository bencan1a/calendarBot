# Kiosk Deployment Tests

This directory contains tests for the CalendarBot kiosk deployment system, which provides a robust, self-healing calendar display for Raspberry Pi devices.

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

### test_installer.py (33KB) - **Phase 1**
Tests for the automated kiosk installer script validation.

**Components Tested:**
- Configuration parsing and validation
- Dry-run mode (preview without system changes)
- State detection (fresh vs existing installation)
- Section-specific installation logic
- Backup mechanisms
- Error handling and recovery

**Key Test Areas:**
- YAML configuration parsing
- Installation section orchestration
- Idempotency verification
- Custom configuration options (ports, paths, tokens)
- Advanced options (apt, git, firewall)

**Example Tests:**
```python
# Configuration
test_installer_when_valid_config_then_loads_successfully()
test_installer_when_missing_username_then_validation_fails()

# Dry-run mode
test_installer_when_dry_run_then_shows_preview()
test_installer_when_dry_run_then_no_system_changes()

# Section validation
test_installer_when_only_section_1_then_skips_others()
test_installer_when_section_2_enabled_then_requires_section_1()
```

## Running Kiosk Tests

### Run all kiosk tests
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

# Installer tests only (Phase 1)
pytest tests/kiosk/test_installer.py
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

### System Requirements
- Bash shell (for script tests)
- Standard Unix utilities: `curl`, `jq`, `grep`, `awk`
- File system access for temporary test files

### Optional Dependencies
- `curl` - For webhook testing (some tests will skip if unavailable)
- `jq` - For JSON processing (some tests will skip if unavailable)

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

| Component | Tests | Coverage | File |
|-----------|-------|----------|------|
| **Watchdog (Python)** | 69 | 90%+ | test_watchdog.py |
| **Scripts (Enhanced)** | 37 | 70%+ | test_scripts_enhanced.py |
| **Scripts (Integration)** | 24 | ~30% | test_scripts_integration.py |
| **Installer** | 35 | TBD | test_installer.py |
| **Total** | **146** | - | All files |

## Contributing

When adding new kiosk tests:

1. **Watchdog tests** → Add to [test_watchdog.py](test_watchdog.py)
2. **Basic script tests** → Add to [test_scripts_integration.py](test_scripts_integration.py)
3. **Enhanced script tests** → Add to [test_scripts_enhanced.py](test_scripts_enhanced.py)
4. **Installer tests** → Add to [test_installer.py](test_installer.py)
5. Use appropriate test markers (`@pytest.mark.integration`, `@pytest.mark.unit`)
6. Include docstrings explaining what's being tested
7. Use temp directories to avoid permission issues
8. Clean up temporary files in teardown
9. Handle missing dependencies gracefully (use `pytest.skip()`)
