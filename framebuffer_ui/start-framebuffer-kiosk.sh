#!/bin/bash
# CalendarBot Framebuffer Kiosk Startup Script
# Run from TTY login to launch framebuffer UI

set -e

# Only run on TTY1 (console)
if [ "$(tty)" != "/dev/tty1" ]; then
    echo "Framebuffer kiosk only runs on tty1, current: $(tty)"
    exit 0
fi

# Wait for network to be ready
echo "Waiting for network..."
for i in {1..30}; do
    if ping -c 1 -W 1 8.8.8.8 &>/dev/null; then
        echo "Network ready"
        break
    fi
    sleep 1
done

# Change to calendarbot directory
cd ~/calendarbot

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Export SDL settings (will be overridden by auto-detection in renderer.py)
export SDL_NOMOUSE=1
export SDL_FBDEV=/dev/fb0
export SDL_AUDIODRIVER=dummy

# Create log directory
LOG_DIR="$HOME/calendarbot/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/framebuffer-kiosk-$(date +%Y%m%d-%H%M%S).log"

# Clear the screen
clear

# Give user time to cancel before starting
echo "========================================="
echo "CalendarBot Framebuffer Kiosk"
echo "========================================="
echo ""
echo "Starting in 30 seconds..."
echo "Press Ctrl+C to cancel"
echo ""

# Countdown with ability to interrupt
for i in {30..1}; do
    echo -ne "Starting in $i seconds...\r"
    sleep 1
done
echo ""
echo ""

# Run framebuffer UI with detailed logging
echo "Starting CalendarBot Framebuffer UI..."
echo "Logging to: $LOG_FILE"
echo ""

# Enable debug logging
export CALENDARBOT_LOG_LEVEL=DEBUG

# Run and capture all output
python -m calendarbot_lite --ui framebuffer --backend local 2>&1 | tee "$LOG_FILE"

# If it exits, show exit status and wait
EXIT_CODE=$?
echo ""
echo "CalendarBot exited with code: $EXIT_CODE"
echo "Log saved to: $LOG_FILE"
echo ""
if [ $EXIT_CODE -ne 0 ]; then
    echo "=== Last 20 lines of log ==="
    tail -n 20 "$LOG_FILE"
    echo "=========================="
fi
echo ""
echo "Press Enter to continue..."
read
