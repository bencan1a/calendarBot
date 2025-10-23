# CALENDARBOT DEVELOPMENT RULES

## ENVIRONMENT & EXECUTION
IMPORTANT - you must ALWAYS active the python venv BEFORE Running python code. 
IMPORTANT - if a module appears to not be installed, this is usually because the venv has not been activated.
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
1. This is a single user stateless application
2. Never worry about backward compatibility or migration
3. Never build code as optional to preserve existing code paths
4. Always replace existing code with new code when making improvements

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
