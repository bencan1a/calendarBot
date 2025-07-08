#!/bin/sh
# Coverage collection helper script for CalendarBot
# Usage: ./scripts/run_coverage.sh [individual|full|module] [module_name]

set -e

# Activate virtual environment
. venv/bin/activate

case "${1:-full}" in
    "individual")
        if [ -z "$2" ]; then
            echo "Usage: $0 individual <module_name>"
            echo "Example: $0 individual calendarbot.validation.runner"
            exit 1
        fi
        echo "Running individual module coverage for: $2"
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
        echo "Running coverage for test file: $2 -> module: calendarbot.$module_name"
        pytest "$2" --cov="calendarbot.$module_name" --cov-report=term-missing --cov-report=html --cov-report=xml
        ;;
    "full")
        echo "Running full test suite coverage..."
        pytest --cov=calendarbot --cov-report=term-missing --cov-report=html --cov-report=xml --cov-report=json
        ;;
    *)
        echo "Usage: $0 [individual|full|module] [module_name|test_file]"
        echo ""
        echo "Examples:"
        echo "  $0 full                                    # Full suite coverage"
        echo "  $0 individual calendarbot.setup_wizard    # Individual module coverage"
        echo "  $0 module tests/unit/test_setup_wizard.py # Test-specific coverage"
        exit 1
        ;;
esac

echo "Coverage analysis complete!"
