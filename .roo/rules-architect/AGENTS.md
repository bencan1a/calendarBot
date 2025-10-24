# Architect Mode Rules (Non-Obvious Only)

## System Architecture Constraints
- **Dual Codebase Strategy**: `calendarbot/` (full-featured) vs `calendarbot_lite/` (minimal) - intentional separation for different use cases
- **Async-First Design**: Core operations built on asyncio - maintain this pattern for consistency
- **Single User Context**: No multi-tenancy concerns - simplifies architecture decisions

## Testing Architecture
- **Tiered Test Strategy**: Critical Path (<5min), Full Regression (20-30min), Smart Selection (file-based)
- **Process Isolation**: Browser tests require host IP binding, not localhost due to binding restrictions
- **Sequential Execution**: Parallel testing disabled due to pytest-xdist communication failures

## Build System Design
- **Iterative Formatting**: `format_and_stage.py` continues until convergence (unlike standard one-pass tools)
- **Unified Linting**: Ruff replaces both black and flake8 - single tool for consistency
- **Smart Dependencies**: `calendarbot_lite` deliberately avoids heavy imports for minimal footprint

## Quality Gates
- **Coverage Flexibility**: 70% target (temp from 85%) allows development velocity while maintaining quality
- **Fail-Fast CI**: Pre-commit stops on first issue for quick feedback cycles
- **Automatic Cleanup**: Scripts handle hanging browser processes to prevent resource exhaustion

## Infrastructure Patterns
- **MCP Integration**: Playwright MCP preferred over manual browser control for consistency
- **Debug Variables**: `CALENDARBOT_DEBUG=true` enables deep logging without code modification
- **Script Lifecycle**: Debug scripts in `/scripts/` are temporary tools, not permanent infrastructure