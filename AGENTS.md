# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Critical Non-Obvious Patterns

- **Dual Projects**: `calendarbot/` (full app) vs `calendarbot_lite/` (standalone) - different entry points and commands
- **Environment**: ALWAYS activate venv first: `. venv/bin/activate` - module import failures usually mean venv not activated
- **Debug Mode**: `CALENDARBOT_DEBUG=true` forces DEBUG logging without code changes
- **Browser Testing**: Use host IP (e.g., 192.168.1.45:8080), not localhost - localhost binding fails

## Build/Test Commands

- **Test Coverage**: `./scripts/run_coverage.sh [unit|integration|browser|full|diagnose]` - manages timeouts and cleanup
- **Format+Stage**: `python format_and_stage.py` - iterative formatting until stable (not standard ruff)
- **Smart Tests**: `python tests/suites/suite_manager.py execute-smart` - runs only tests for changed files
- **Coverage Target**: 70% (temporarily reduced from 85% until Jan 22, 2025)
- **Parallel Tests**: Disabled due to pytest-xdist stability issues

## Testing Architecture

- **Critical Path**: <5min CI suite via `tests/suites/critical_path.py`
- **Full Regression**: 20-30min via `tests/suites/full_regression.py` 
- **Test Manager**: `tests/suites/suite_manager.py` coordinates execution and tracks performance
- **Process Cleanup**: Scripts kill hanging Chrome/pytest processes automatically

## Code Style

- **Linter**: Ruff handles both linting AND formatting (replaces black)
- **Line Length**: 100 chars (non-standard)
- **Type Annotations**: Required on ALL parameters/returns except class `self`
- **Imports**: Combined imports, split on trailing comma, `calendarbot` as first-party

## Entry Points

- Main app: `calendarbot --web --port PORT` or `python -m calendarbot`
- Lite app: `python -m calendarbot_lite --port PORT`
- Jest tests: `npm test` (uses jsdom environment)

Includes content from existing CLAUDE.md for compatibility.