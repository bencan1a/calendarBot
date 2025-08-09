#!/bin/sh
# CalendarBot Kiosk X11 Session

# Set up environment
export DISPLAY=:0
export XDG_SESSION_TYPE=x11

# Configure X11 for kiosk mode
xset s off         # Disable screensaver
xset -dpms         # Disable DPMS power management
xset s noblank     # Prevent screen blanking

# Set 480x800 portrait orientation
xrandr --output HDMI-1 --rotate left

# Hide cursor after 0.1 seconds of inactivity
unclutter -idle 0.1 -root &

# Configure touch input if available
xinput set-prop "touchscreen" "Coordinate Transformation Matrix" 0 1 0 -1 0 1 0 0 1 2>/dev/null || true

# Start window manager (lightweight)
openbox-session &

# Keep X11 session alive
while true; do
    sleep 3600
done