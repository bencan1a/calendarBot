#!/bin/sh
# Minimal kiosk X session for Chromium + Matchbox

export DISPLAY=:0
URL="http://$(hostname -I | awk '{print $1}'):8080"
LOG="$HOME/kiosk/kiosk.log"
exec >>"$LOG" 2>&1

log() { printf '%s %s\n' "$(date '+[%a %d %b %T %Z %Y]')" "$*"; }

log "Starting kiosk session"

# Ensure session D-Bus
if ! pgrep -u "$USER" dbus-daemon >/dev/null 2>&1; then
  if command -v dbus-launch >/dev/null 2>&1; then
    eval "$(dbus-launch --sh-syntax)"
    log "Started session D-Bus: $DBUS_SESSION_BUS_ADDRESS"
  else
    log "Warning: dbus-launch not found"
  fi
fi

# Environment tweaks to minimize RAM/GPU
export LIBGL_ALWAYS_SOFTWARE=1
export GSK_RENDERER=cairo
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export WEBKIT_DISABLE_WEBGL=1
export JSC_useJIT=0
export GTK_A11Y=none
export WEBKIT_DISABLE_MEDIACODECS=1

# Power/blanking
xset s off -dpms
xset s noblank

# Cursor hide
#unclutter -idle 0 &

# Start minimal WM
matchbox-window-manager -use_cursor no &

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

# Wait more seconds for rendering readiness
sleep 15

#chromium launch
log "launching chromium"
chromium --no-memcheck --temp-profile --kiosk --enable-low-end-device-mode --noerrdialogs "$URL"

log "chromium exited"