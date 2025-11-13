# Code Mode Rules (Non-Obvious Only)

## Application Context & Scale

**Personal project, single developer, resource-constrained deployment (Pi Zero 2W):**
- **Scale**: 1-5 users max, single instance, no enterprise patterns needed
- **Resources**: Optimize for <100MB RAM idle, efficient CPU usage on 1GB total RAM
- **Simplicity First**: Direct solutions over abstractions, minimal dependencies
- **Breaking Changes OK**: No backward compatibility burden, update and deploy
- **Heavy Deps**: Avoid - each library costs RAM and startup time on Pi Zero 2W

See main [AGENTS.md](../../AGENTS.md#-application-context--scale) for complete guidance.

## File Organization
- **Temporary Files**: ALL debug/test scripts go in `tmp/` (gitignored)
- **Project Reports**: Refactoring plans, analysis reports go in `tmp/` (not root)
- **Permanent Docs**: API docs, architecture go in `docs/` (version controlled)

## Project Structure Gotchas
- **Entry Points**: `calendarbot.__main__:main` vs `calendarbot_lite.run_server()` - different signatures
- **Import Light**: `calendarbot_lite` avoids heavy deps - check before adding imports

## Code Quality Automation
- **Format Script**: `python format_and_stage.py` runs until convergence (not one-shot like black)
- **Ruff Dual Role**: Handles BOTH linting AND formatting (replaces black + flake8)
- **Pre-commit**: Uses `fail_fast: true` - stops on first issue for quick feedback

## Type System
- **Self Exception**: Class methods don't type `self` parameter (only one in codebase)
- **Async Everywhere**: Core operations use asyncio - new code should follow pattern
- **Path Objects**: Use `pathlib.Path` not strings (enforced by linter rules)

## Testing Integration
- **Unit Test Requirement**: ALL new functions need tests - no exceptions for this project
- **Smart Execution**: `tests/suites/suite_manager.py execute-smart` auto-selects tests for changed files
- **Coverage Tracking**: Write tests to meet 70% line coverage (temp target until Jan 22, 2025)