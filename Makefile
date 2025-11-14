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
	@. venv/bin/activate && yamllint --version
	@. venv/bin/activate && find . -type f \( -name "*.yaml" -o -name "*.yml" \) \
		! -path "./venv/*" \
		! -path "./.venv/*" \
		! -path "./node_modules/*" \
		! -path "./.git/*" \
		! -path "./htmlcov/*" \
		! -path "./build/*" \
		! -path "./dist/*" \
		-print0 | xargs -0 yamllint
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
	@./run_lite_tests.sh -m unit
	@echo "✓ Unit tests complete"

.PHONY: test-fast
test-fast: ## Run fast tests (exclude slow tests)
	@echo "Running fast tests..."
	@./run_lite_tests.sh -m "not slow"
	@echo "✓ Fast tests complete"

.PHONY: test-smoke
test-smoke: ## Run smoke tests
	@echo "Running smoke tests..."
	@./run_lite_tests.sh -m smoke
	@echo "✓ Smoke tests complete"

.PHONY: check
check: ## Run all quality checks (YAML, lint, type, security) with error summary
	@echo "Running all quality checks..."
	@echo ""
	@failed=0; \
	echo "1/4 Checking YAML syntax..."; \
	if $(MAKE) -s check-yaml 2>&1 | grep -v "^make"; then \
		echo "  ✓ YAML validation passed"; \
	else \
		echo "  ✗ YAML validation failed"; \
		failed=$$((failed + 1)); \
	fi; \
	echo ""; \
	echo "2/4 Checking code style (ruff)..."; \
	if $(MAKE) -s lint-check 2>&1 | grep -v "^make"; then \
		echo "  ✓ Lint check passed"; \
	else \
		echo "  ✗ Lint check failed"; \
		failed=$$((failed + 1)); \
	fi; \
	echo ""; \
	echo "3/4 Checking types (mypy)..."; \
	if $(MAKE) -s typecheck 2>&1 | grep -v "^make"; then \
		echo "  ✓ Type check passed"; \
	else \
		echo "  ✗ Type check failed"; \
		failed=$$((failed + 1)); \
	fi; \
	echo ""; \
	echo "4/4 Checking security (bandit)..."; \
	if $(MAKE) -s security 2>&1 | grep -v "^make"; then \
		echo "  ✓ Security scan passed"; \
	else \
		echo "  ✗ Security scan failed"; \
		failed=$$((failed + 1)); \
	fi; \
	echo ""; \
	echo "========================================"; \
	if [ $$failed -eq 0 ]; then \
		echo "✓ All checks passed (0 failures)"; \
		exit 0; \
	else \
		echo "✗ $$failed check(s) failed"; \
		echo "Run individual checks for details:"; \
		echo "  make check-yaml"; \
		echo "  make lint-check"; \
		echo "  make typecheck"; \
		echo "  make security"; \
		exit 1; \
	fi

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

# Docker targets
.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t calendarbot-lite:latest .
	@echo "✓ Docker image built"

.PHONY: docker-build-no-cache
docker-build-no-cache: ## Build Docker image without cache
	@echo "Building Docker image (no cache)..."
	docker build --no-cache -t calendarbot-lite:latest .
	@echo "✓ Docker image built"

.PHONY: docker-up
docker-up: ## Start Docker container with docker-compose
	@echo "Starting Docker container..."
	docker-compose up -d
	@echo "✓ Docker container started"
	@echo "Access at: http://localhost:8080"

.PHONY: docker-down
docker-down: ## Stop Docker container
	@echo "Stopping Docker container..."
	docker-compose down
	@echo "✓ Docker container stopped"

.PHONY: docker-logs
docker-logs: ## View Docker container logs
	docker-compose logs -f

.PHONY: docker-ps
docker-ps: ## Show Docker container status
	docker-compose ps

.PHONY: docker-restart
docker-restart: ## Restart Docker container
	@echo "Restarting Docker container..."
	docker-compose restart
	@echo "✓ Docker container restarted"

.PHONY: docker-clean
docker-clean: ## Remove Docker containers, images, and volumes
	@echo "Cleaning Docker resources..."
	docker-compose down -v
	docker rmi calendarbot-lite:latest 2>/dev/null || true
	@echo "✓ Docker resources cleaned"

.PHONY: docker-shell
docker-shell: ## Open shell in running Docker container
	docker-compose exec calendarbot bash

.PHONY: docker-test
docker-test: ## Test Docker container health
	@echo "Testing Docker container health..."
	@curl -f http://localhost:8080/api/health && echo "\n✓ Container is healthy" || echo "\n✗ Container health check failed"

.DEFAULT_GOAL := help
