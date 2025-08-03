# CALENDARBOT DEVELOPMENT RULES

## CONPORT INTEGRATION
- **Status Prefix**: Begin ALL responses with `[CONPORT_ACTIVE]` or `[CONPORT_INACTIVE]`
- **Initialization**: Check for `context_portal/context.db`, load existing context or offer to create new
  - If database exists: Load product context, active context, recent decisions/progress/patterns
  - If no database: Ask user to initialize, optionally bootstrap from `projectBrief.md`
- **Usage Criteria**: Use for architecture changes, new features, major refactoring; skip for bug fixes, minor tweaks
- **Core Workflow**: Check context → work → log decisions/progress → update context
- **Key Tools**: `log_decision` (architectural choices), `log_progress` (task tracking), `update_active_context` (session focus), `update_product_context` (project changes)
- **Sync Command**: Use `Sync ConPort` to update database with session information
- **Context Retrieval**: Use `semantic_search_conport` for conceptual queries, `search_*_fts` for keyword searches
- **Error Handling**: If conport tools fail, set status to `[CONPORT_INACTIVE]` and continue without context
- **Detailed Guidance**: See [`docs/architecture/CONPORT_USAGE_GUIDE.md`](docs/architecture/CONPORT_USAGE_GUIDE.md) for initialization sequences, tool parameters, and advanced patterns

## ENVIRONMENT & EXECUTION
- **Shell**: sh (not bash)
- **Python venv**: `. venv/bin/activate` (not `source`)
- **App Execution**: `calendarbot --web --port PORT`
- **Browser Testing**: Use host IP, not localhost

## MCP SERVER USAGE
- **Playwright MCP**: For browser automation, UI testing, and visual validation
  - Use for: page navigation, element interaction, screenshot capture
  - Preferred over manual browser testing for UX validation

- **Context7 MCP**: For documentation and code examples
  - First call `resolve-library-id` to get library ID
  - Then use `get-library-docs` with the ID and topic

## TESTING WORKFLOW
1. **Smoke Test**: Run `calendarbot --web`, fix errors first
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

## ERROR HANDLING
- Validate inputs at function start
- Use specific exception types
- Log errors with context
- Return appropriate fallback values

## REPORTING STANDARDS
- **Style**: Concise, factual, minimal flowery language
- **Task Completion**: Brief status reports, avoid excessive enthusiasm
