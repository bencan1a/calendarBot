#!/bin/bash

export DISPLAY=:0
URL="http://$(hostname -I | awk '{print $1}'):8080"

# Log everything for debugging
exec >> "/home/$(whoami)/kiosk/kiosk.log" 2>&1
echo "[$(date)] Starting kiosk session"

# Start Openbox window manager
openbox &

# Disable screen blanking and power management
echo "[$(date)] Disabling screen blanking..."
xset s off          # Disable screensaver
xset -dpms          # Disable DPMS power management
xset s noblank      # Prevent screen blanking

# Wait for web server (max 60 seconds)
echo "[$(date)] Waiting for CalendarBot..."
for _ in {1..30}; do
  if curl --silent --fail "$URL" > /dev/null; then
    echo "[$(date)] CalendarBot is up"
    break
  fi
  echo "[$(date)] Still waiting..."
  sleep 2
done

# Wait 2 more seconds for rendering readiness
sleep 15

# Launch Chromium in kiosk mode
echo "[$(date)] Launching Chromium..."
exec chromium-browser --kiosk --app="$URL" \
  --noerrdialogs --disable-infobars --disable-restore-session-state \
  --disable-session-crashed-bubble --no-sandbox --disable-features=TranslateUI