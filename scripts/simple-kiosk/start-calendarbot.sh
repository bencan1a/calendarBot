#!/bin/bash
# CalendarBot Web Server Startup Script

set -e

# Auto-detect project directory (script's parent directory)
SCRIPT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"
CALENDARBOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$CALENDARBOT_DIR/venv"
PORT=8080

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Check if CalendarBot is already running
if pgrep -f "calendarbot.*--web" > /dev/null; then
    log "CalendarBot web server is already running"
    exit 0
fi

log "Starting CalendarBot web server..."
log "Project directory: $CALENDARBOT_DIR"

# Validate directories exist
if [ ! -d "$CALENDARBOT_DIR" ]; then
    log "ERROR: CalendarBot directory not found: $CALENDARBOT_DIR"
    exit 1
fi

if [ ! -d "$VENV_PATH" ]; then
    log "ERROR: Virtual environment not found: $VENV_PATH"
    log "Please run: cd $CALENDARBOT_DIR && python3 -m venv venv && source venv/bin/activate && pip install -e ."
    exit 1
fi

# Change to CalendarBot directory
cd "$CALENDARBOT_DIR"

# Activate virtual environment and start CalendarBot
log "Activating virtual environment: $VENV_PATH"
source "$VENV_PATH/bin/activate"

# Start CalendarBot web server
log "Starting CalendarBot on port $PORT"
exec python -m calendarbot --web --port $PORT