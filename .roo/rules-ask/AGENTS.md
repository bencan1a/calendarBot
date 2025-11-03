# Ask Mode Rules (Non-Obvious Only)

## File Organization
- **Temporary Files**: Use `tmp/` for any temporary analysis or debug files (gitignored)
- **Documentation**: Permanent docs in `docs/`, temporary reports in `tmp/`

## Documentation Context
- **CLAUDE.md**: Comprehensive existing documentation - refer to this for standard patterns and commands
- **Dual Architecture**: Separate `calendarbot/` (full) and `calendarbot_lite/` (minimal) codebases with different capabilities
- **Coverage History**: Target reduced from 85% to 70% temporarily until Jan 22, 2025 - context for coverage questions

## Non-Standard Tools
- **Test Suite Manager**: `tests/suites/suite_manager.py` provides intelligent test selection and execution tracking
- **Format Iterations**: `format_and_stage.py` runs until code stabilizes (not single-pass like standard formatters)
- **Smart Coverage**: `./scripts/run_coverage.sh` with multiple modes and automatic process cleanup

## Configuration Quirks
- **Ruff Dual Role**: Single tool for both linting AND formatting (replaces black + flake8)
- **Jest Environment**: Uses jsdom with host IP (192.168.1.45:8080) for browser testing
- **Parallel Disabled**: pytest-xdist causes stability issues - tests run sequentially

## Development Context
- **Single User App**: No backward compatibility concerns - always replace vs extend
- **MCP Integration**: Playwright MCP preferred over manual browser testing
- **Debug Scripts**: Created in `/scripts/` and removed after use (not permanent tooling)