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

# Clear the screen
clear

# Run framebuffer UI
echo "Starting CalendarBot Framebuffer UI..."
python -m calendarbot_lite --ui framebuffer --backend local

# If it exits, wait before returning to shell
echo ""
echo "CalendarBot exited. Press Enter to continue..."
read
