# Makefile for CalendarBot Lite
# Provides common development tasks and quality checks

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: check-yaml
check-yaml: ## Validate YAML syntax in all YAML files
	@echo "Validating YAML syntax..."
	@yamllint --version
	@find . -type f \( -name "*.yaml" -o -name "*.yml" \) \
		! -path "./venv/*" \
		! -path "./.venv/*" \
		! -path "./node_modules/*" \
		! -path "./.git/*" \
		! -path "./htmlcov/*" \
		! -path "./build/*" \
		! -path "./dist/*" \
		-exec echo "Checking: {}" \; \
		-exec yamllint {} \;
	@echo "✓ YAML validation complete"

.PHONY: format
format: ## Format Python code with ruff
	@echo "Formatting code..."
	@. venv/bin/activate && ruff format calendarbot_lite
	@echo "✓ Code formatting complete"

.PHONY: lint
lint: ## Run ruff linter and auto-fix issues
	@echo "Running linter..."
	@. venv/bin/activate && ruff check calendarbot_lite --fix
	@echo "✓ Linting complete"

.PHONY: lint-check
lint-check: ## Run ruff linter without auto-fix
	@echo "Checking code style..."
	@. venv/bin/activate && ruff check calendarbot_lite
	@echo "✓ Lint check complete"

.PHONY: typecheck
typecheck: ## Run mypy type checker
	@echo "Running type checker..."
	@. venv/bin/activate && mypy calendarbot_lite
	@echo "✓ Type checking complete"

.PHONY: security
security: ## Run bandit security scanner
	@echo "Running security scan..."
	@. venv/bin/activate && bandit -r calendarbot_lite
	@echo "✓ Security scan complete"

.PHONY: test
test: ## Run tests
	@echo "Running tests..."
	@./run_lite_tests.sh
	@echo "✓ Tests complete"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	@./run_lite_tests.sh --coverage
	@echo "✓ Tests with coverage complete"

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	@./run_lite_tests.sh --markers "unit"
	@echo "✓ Unit tests complete"

.PHONY: test-fast
test-fast: ## Run fast tests (exclude slow tests)
	@echo "Running fast tests..."
	@./run_lite_tests.sh --markers "not slow"
	@echo "✓ Fast tests complete"

.PHONY: test-smoke
test-smoke: ## Run smoke tests
	@echo "Running smoke tests..."
	@./run_lite_tests.sh --markers "smoke"
	@echo "✓ Smoke tests complete"

.PHONY: check
check: check-yaml lint-check typecheck security ## Run all quality checks (YAML, lint, type, security)
	@echo "✓ All checks passed"

.PHONY: precommit
precommit: format lint typecheck test-fast ## Run pre-commit checks (format, lint, typecheck, fast tests)
	@echo "✓ Pre-commit checks complete"

.PHONY: clean
clean: ## Clean build artifacts and cache files
	@echo "Cleaning build artifacts..."
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	@rm -rf htmlcov/ htmlcov-lite/ coverage.xml .coverage
	@echo "✓ Cleanup complete"

.PHONY: install
install: ## Install dependencies in virtual environment
	@echo "Installing dependencies..."
	@. venv/bin/activate && pip install -e '.[dev]'
	@echo "✓ Dependencies installed"

.PHONY: install-test
install-test: ## Install test dependencies only
	@echo "Installing test dependencies..."
	@. venv/bin/activate && pip install -e '.[test]'
	@echo "✓ Test dependencies installed"

.PHONY: serve
serve: ## Run the CalendarBot Lite server
	@echo "Starting CalendarBot Lite server..."
	@. venv/bin/activate && python -m calendarbot_lite

.PHONY: pre-commit-run
pre-commit-run: ## Run pre-commit hooks on all files
	@echo "Running pre-commit hooks..."
	@. venv/bin/activate && pre-commit run --all-files
	@echo "✓ Pre-commit hooks complete"

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	@. venv/bin/activate && pre-commit install
	@echo "✓ Pre-commit hooks installed"

.DEFAULT_GOAL := help
