#!/bin/sh
# Coverage collection helper script for CalendarBot
# Usage: ./scripts/run_coverage.sh [individual|full|module|unit|integration|browser|diagnose] [module_name]

set -e

# Activate virtual environment
. venv/bin/activate

# Pre-cleanup function to kill hanging processes
cleanup_processes() {
    echo "🧹 Cleaning up any hanging processes..."
    # Kill hanging Chrome processes from previous test runs
    pkill -f "chrome.*--test-type" 2>/dev/null || true
    pkill -f "chromium.*--test-type" 2>/dev/null || true
    # Kill hanging pytest processes (but not this one)
    pgrep -f pytest | grep -v $$ | xargs kill -TERM 2>/dev/null || true
    sleep 1
}

# Function to run tests with timeout protection
run_with_timeout() {
    local timeout_duration="$1"
    shift
    echo "⏱️ Running with ${timeout_duration}s timeout: $*"

    timeout "$timeout_duration" "$@" || {
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "❌ Tests timed out after ${timeout_duration}s"
            cleanup_processes
            return 124
        else
            return $exit_code
        fi
    }
}

case "${1:-full}" in
    "individual")
        if [ -z "$2" ]; then
            echo "Usage: $0 individual <module_name>"
            echo "Example: $0 individual calendarbot.validation.runner"
            exit 1
        fi
        echo "🧪 Running individual module coverage for: $2"
        cleanup_processes
        pytest tests/unit/test_*.py --cov="$2" --cov-report=term-missing --cov-report=html --cov-report=xml
        ;;
    "module")
        if [ -z "$2" ]; then
            echo "Usage: $0 module <test_file>"
            echo "Example: $0 module tests/unit/test_validation_runner.py"
            exit 1
        fi
        # Extract module name from test file
        module_name=$(echo "$2" | sed 's|tests/unit/test_||; s|\.py$||; s|_|.|g')
        echo "🧪 Running coverage for test file: $2 -> module: calendarbot.$module_name"
        cleanup_processes
        pytest "$2" --cov="calendarbot.$module_name" --cov-report=term-missing --cov-report=html --cov-report=xml
        ;;
    "unit")
        echo "🚀 Running unit tests with coverage..."
        cleanup_processes
        run_with_timeout 300 pytest tests/unit/ -m "unit or fast" --cov=calendarbot --cov-report=term-missing --cov-report=html:htmlcov_unit --cov-report=xml:coverage_unit.xml --cov-report=json:coverage_unit.json
        ;;
    "integration")
        echo "🔗 Running integration tests with coverage..."
        cleanup_processes
        run_with_timeout 600 pytest tests/integration/ -m "integration" --cov=calendarbot --cov-report=term-missing --cov-report=html:htmlcov_integration --cov-report=xml:coverage_integration.xml --cov-report=json:coverage_integration.json
        ;;
    "browser")
        echo "🌐 Running browser tests with coverage and timeout protection..."
        cleanup_processes
        # Pre-kill any Chrome processes
        pkill -f "chrome" 2>/dev/null || true
        run_with_timeout 900 pytest tests/browser/ -m "browser" --cov=calendarbot.web --cov-report=term-missing --cov-report=html:htmlcov_browser --cov-report=xml:coverage_browser.xml --cov-report=json:coverage_browser.json
        # Post-cleanup for browser tests
        cleanup_processes
        ;;
    "diagnose")
        echo "🔍 Running test suite diagnostics..."
        echo "📊 Test Discovery Analysis:"
        pytest --collect-only -q | grep -c "test session starts\|collected.*items" || true

        echo "📂 Test Structure Analysis:"
        find tests/ -name "test_*.py" | wc -l
        find tests/ -name "conftest.py" | head -5

        echo "⚙️ Configuration Check:"
        pytest --markers | grep -E "(unit|integration|browser|e2e)" || echo "Custom markers not found"

        echo "🧪 Quick Smoke Test (5 tests max):"
        cleanup_processes
        run_with_timeout 60 pytest tests/ --maxfail=1 -x -q --tb=line | head -20
        ;;
    "full")
        echo "🚀 Running full test suite coverage..."
        cleanup_processes

        # Remove old coverage files to prevent context mixing
        rm -f .coverage* coverage*.xml coverage*.json
        rm -rf htmlcov*

        echo "📊 Starting comprehensive test execution..."
        run_with_timeout 1800 pytest --cov=calendarbot --cov-report=term-missing --cov-report=html --cov-report=xml --cov-report=json

        # Final cleanup
        cleanup_processes
        ;;
    *)
        echo "Usage: $0 [individual|full|module|unit|integration|browser|diagnose] [module_name|test_file]"
        echo ""
        echo "🧪 Test Categories:"
        echo "  unit         - Fast unit tests (5min timeout)"
        echo "  integration  - Integration tests (10min timeout)"
        echo "  browser      - Browser tests with cleanup (15min timeout)"
        echo "  full         - Complete test suite (30min timeout)"
        echo ""
        echo "🔧 Utilities:"
        echo "  diagnose     - Analyze test suite configuration and run smoke test"
        echo "  individual   - Test specific module coverage"
        echo "  module       - Test specific test file coverage"
        echo ""
        echo "Examples:"
        echo "  $0 diagnose                               # Check test suite health"
        echo "  $0 unit                                   # Fast unit tests only"
        echo "  $0 browser                                # Browser tests with cleanup"
        echo "  $0 full                                   # Complete test suite"
        echo "  $0 individual calendarbot.setup_wizard   # Individual module coverage"
        echo "  $0 module tests/unit/test_setup_wizard.py # Test-specific coverage"
        exit 1
        ;;
esac

echo "✅ Coverage analysis complete!"
