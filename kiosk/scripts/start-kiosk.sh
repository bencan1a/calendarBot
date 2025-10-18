#!/bin/bash

# Get the Pi's first non-loopback IPv4 address
IP_ADDR=$(hostname -I | awk '{print $1}')
URL="http://${IP_ADDR}:8080"

echo "Using IP address: $IP_ADDR"
echo "Waiting for CalendarBot to be ready at $URL..."

# Export display for X commands
export DISPLAY=:0

MAX_RETRIES=30
RETRIES=0

until curl --silent --fail "$URL" > /dev/null; do
  echo "Waiting for CalendarBot..."
  sleep 2
  ((RETRIES++))
  if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
    echo "CalendarBot did not respond after $((MAX_RETRIES * 2)) seconds."
    exit 1
  fi
done

echo "CalendarBot is up — waiting for X server..."

# Wait for X server (checks if :0 is available)
TRIES=0
until xdpyinfo >/dev/null 2>&1; do
  sleep 1
  ((TRIES++))
  if [ "$TRIES" -ge 15 ]; then
    echo "X server did not become available."
    exit 1
  fi
done

# Optional: Let the screen stay awake
xset -dpms
xset s off
xset s noblank

# Start unclutter to hide the mouse pointer after 1 second of inactivity
unclutter -idle 1 &

# Start window manager (non-blocking)
openbox &

# Then launch Epiphany (WebKit) as the main foreground process in kiosk mode
exec epiphany-browser --kiosk "$URL"