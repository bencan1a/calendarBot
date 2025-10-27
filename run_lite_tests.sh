#!/bin/bash
# Convenience script for running CalendarBot Lite tests

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Activate virtual environment
if [ -d "venv/bin" ]; then
    source venv/bin/activate
elif [ -d ".venv/bin" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found"
    exit 1
fi

echo -e "${BLUE}Running CalendarBot Lite tests...${NC}"
echo ""

# Parse command line arguments
COVERAGE=false
VERBOSE=""
MARKERS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE="-v"
            shift
            ;;
        --markers|-m)
            MARKERS="-m $2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c    Run with coverage report"
            echo "  --verbose, -v     Run with verbose output"
            echo "  --markers, -m     Run tests with specific markers (e.g., 'unit')"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                  # Run all lite tests"
            echo "  $0 --coverage       # Run with coverage"
            echo "  $0 -m 'not slow'    # Run fast tests only"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run tests
if [ "$COVERAGE" = true ]; then
    echo -e "${GREEN}Running with coverage...${NC}"
    pytest tests/lite/ $VERBOSE $MARKERS \
        --cov=calendarbot_lite \
        --cov-report=term-missing \
        --cov-report=html:htmlcov-lite
else
    pytest tests/lite/ $VERBOSE $MARKERS
fi

echo ""
echo -e "${GREEN}CalendarBot Lite tests completed!${NC}"
