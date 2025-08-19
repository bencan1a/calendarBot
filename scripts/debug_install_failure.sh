#!/bin/sh

# Debug script to validate install.sh failure assumptions
# This script tests the hypotheses about the installation failure

LOG_FILE="/tmp/calendarbot-install-debug.log"

log_debug() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') DEBUG: $1" | tee -a "$LOG_FILE"
}

log_debug "=== CalendarBot Install Debug Script ==="
log_debug "Testing failure assumptions..."

# Test 1: Check if CalendarBot is installed as a command
log_debug "Test 1: Checking CalendarBot command availability"
if command -v calendarbot >/dev/null 2>&1; then
    log_debug "✓ CalendarBot command found in PATH"
    version_output=$(calendarbot --version 2>&1)
    log_debug "  Version output: $version_output"
else
    log_debug "✗ CalendarBot command NOT found in PATH"
    log_debug "  This confirms hypothesis 1: CalendarBot package not installed"
fi

# Test 2: Check if Python package is available
log_debug "Test 2: Checking CalendarBot Python package"
if python3 -c "import calendarbot" 2>/dev/null; then
    log_debug "✓ CalendarBot Python package importable"
    python3 -c "from calendarbot.__main__ import main; print('Entry point accessible')" 2>/dev/null && \
        log_debug "✓ Main entry point accessible" || \
        log_debug "✗ Main entry point not accessible"
else
    log_debug "✗ CalendarBot Python package not importable"
fi

# Test 3: Check pip installation status
log_debug "Test 3: Checking pip installation status"
if pip show calendarbot >/dev/null 2>&1; then
    log_debug "✓ CalendarBot installed via pip"
    pip show calendarbot | grep Version | tee -a "$LOG_FILE"
else
    log_debug "✗ CalendarBot NOT installed via pip"
    log_debug "  This confirms the package needs pip installation first"
fi

# Test 4: Test alternative ways to run CalendarBot
log_debug "Test 4: Testing alternative execution methods"

# Try python -m calendarbot
if python3 -m calendarbot --version >/dev/null 2>&1; then
    log_debug "✓ 'python3 -m calendarbot' works"
else
    log_debug "✗ 'python3 -m calendarbot' fails"
fi

# Try direct execution from project directory
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
log_debug "  Project directory: $PROJECT_DIR"
if [ -f "$PROJECT_DIR/main.py" ]; then
    log_debug "✓ main.py found in project directory"
    if cd "$PROJECT_DIR" && python3 main.py --version >/dev/null 2>&1; then
        log_debug "✓ Direct main.py execution works"
    else
        log_debug "✗ Direct main.py execution fails"
    fi
else
    log_debug "✗ main.py not found in project directory"
fi

# Test 5: Simulate the bash context issue
log_debug "Test 5: Testing bash strict mode behavior"
{
    set -euo pipefail
    log_debug "✓ Bash strict mode enabled successfully"
    
    # Simulate the exact failure condition
    if ! command -v calendarbot >/dev/null 2>&1; then
        log_debug "Simulating CalendarBot command not found condition"
        log_debug "This would normally call error_exit and exit 1"
        # Don't actually exit to continue testing
    fi
    
    log_debug "✓ Bash strict mode test completed without context corruption"
} 2>&1 | tee -a "$LOG_FILE"

# Test 6: Check system requirements
log_debug "Test 6: Checking system requirements"
log_debug "  OS: $(uname -s)"
log_debug "  Shell: $SHELL"
log_debug "  Python version: $(python3 --version 2>&1)"
log_debug "  Pip version: $(pip --version 2>&1)"

# Test 7: Check current working directory and paths
log_debug "Test 7: Environment information"
log_debug "  Current directory: $(pwd)"
log_debug "  PATH: $PATH"
log_debug "  USER: ${USER:-unknown}"
log_debug "  HOME: ${HOME:-unknown}"

log_debug "=== Debug Complete ==="
log_debug "Review log file: $LOG_FILE"

echo ""
echo "Debug script completed. Key findings will help identify the root cause."
echo "Log file: $LOG_FILE"