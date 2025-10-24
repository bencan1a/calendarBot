# Debug Mode Rules (Non-Obvious Only)

## Environment Variables
- **CALENDARBOT_DEBUG=true**: Forces DEBUG logging without code changes - use this first
- **Module Imports**: If imports fail, usually means venv not activated - check this before debugging code

## Process Management
- **Hanging Processes**: `./scripts/run_coverage.sh` includes automatic Chrome/pytest cleanup
- **Multiple Terminals**: Current workspace often has 9+ active terminals - check which are relevant
- **Process Killing**: Scripts automatically handle `pkill -f "chrome.*--test-type"` and pytest cleanup

## Test Debugging
- **Smart Test Selection**: `python tests/suites/suite_manager.py execute-smart` runs only changed-file tests
- **Timeout Issues**: Tests have 60s individual timeouts, use `./scripts/run_coverage.sh diagnose` for health checks
- **Parallel Disabled**: pytest-xdist causes BrokenPipeError - tests run sequentially for stability

## Network & Binding
- **Localhost Fails**: Browser testing requires host IP (192.168.1.45:8080), not localhost binding
- **Port Conflicts**: Multiple calendarbot_lite instances on ports 8081-8099 may be running

## Log Investigation
- **Dual Apps**: calendarbot vs calendarbot_lite have different logging setups and entry points
- **Coverage Failures**: 70% temp threshold (not 85%) until Jan 22, 2025 - check this before investigating test issues