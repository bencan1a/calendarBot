# CALENDARBOT DEVELOPMENT RULES

## FILE ORGANIZATION
**CRITICAL: Follow these conventions when creating files:**
- **Temporary/Debug Scripts**: Write to `tmp/` directory (debugging scripts, temporary analysis)
- **Project Reports/Analysis**: Write to `tmp/` directory (refactoring plans, code analysis, work item tracking)
- **Permanent Documentation**: Write to `docs/` directory (API docs, architecture guides, deployment guides)
- **Configuration Files**: Root directory only (CLAUDE.md, AGENTS.md, README.md)

The `tmp/` directory is gitignored. Do NOT create analysis reports or temporary files in the project root.

## ENVIRONMENT & EXECUTION
IMPORTANT - you must ALWAYS active the python venv BEFORE Running python code
IMPORTANT - if a module appears to not be installed, this is usually because the venv has not been activated.
run `. venv/bin/activate` every time!!
- **App Execution**: `calendarbot --web --port PORT`
- **Browser Testing**: Use host IP, not localhost

## MCP SERVER USAGE
- **Playwright MCP**: For browser automation, UI testing, and visual validation
  - Use for: page navigation, element interaction, screenshot capture
  - Preferred over manual browser testing for UX validation

- **Context7 MCP**: For documentation and code examples
  - First call `resolve-library-id` to get library ID
  - Then use `get-library-docs` with the ID and topic

## PROJECT CONTEXT
1. **Personal Application**: Single developer, 1-5 users max, deployed on Raspberry Pi Zero 2W (1GB RAM)
2. **No Backward Compatibility**: Breaking changes acceptable, no versioning/migration needed
3. **Always Replace**: Never build optional code to preserve existing paths
4. **Resource Efficiency**: Optimize for low memory (<100MB idle) and CPU usage on constrained hardware
5. **Simplicity Over Patterns**: Avoid enterprise patterns (circuit breakers, service mesh, complex caching)
6. **Minimal Dependencies**: Each library costs RAM - critical for Pi Zero 2W deployment

See [AGENTS.md](../AGENTS.md#-application-context--scale) for complete scale and context guidance.

## TESTING WORKFLOW
1. **Smoke Test**: Run (with timeout for safety) `calendarbot --web`, fix errors first
2. **Unit Tests**: Cover ALL new functions
3. **Pre-Completion**: Run full test suite, fix all failures
4. **Browser Tests**: Required for UX changes, use Playwright MCP
5. **Debug Scripts**: Create in `/scripts`, remove when complete

## TYPE ANNOTATIONS
- **Required**: ALL parameters/returns typed
- **Patterns**: Use proper typing syntax for functions, collections, optionals, etc.
- **Classes**: self untyped, all other parameters typed

## UNIT TESTING STANDARDS
- **Structure**: `tests/test_[module].py`, pytest
- **Naming**: `test_function_when_condition_then_expected`
- **Coverage**: Normal/edge/error cases, mock externals, async tests

## CODE QUALITY REQUIREMENTS
- **Naming**: Descriptive, codebase-consistent
- **Documentation**: Comprehensive docstrings (Args, Returns, Raises)
- **Error Handling**: Explicit try/except, logging over print
- **Dependencies**: Community-standard libraries, Path objects
- **Structure**: Follow existing patterns, organized imports
- **Linting**: ENsure no linter errors exist after code is written

## ERROR HANDLING
- Validate inputs at function start
- Use specific exception types
- Log errors with context
- Return appropriate fallback values

## REPORTING STANDARDS
- **Style**: Concise, factual, minimal flowery language
- **Task Completion**: Brief status reports, avoid excessive enthusiasm
