#!/bin/sh
# Ultra low-memory kiosk configuration
# Optimized for Raspberry Pi Zero 2W (512MB RAM)

export DISPLAY=:0
URL="http://127.0.0.1:8080/"
LOG="$HOME/kiosk/kiosk.log"
exec >>"$LOG" 2>&1

log() { printf '%s %s\n' "$(date '+[%a %d %b %T %Z %Y]')" "$*"; }

log "=== LOW-MEMORY SESSION ==="

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
sleep 2

# Power/blanking
xset s off -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# Wait for CalendarBot
log "Waiting for CalendarBot server..."
attempt=1
while [ $attempt -le 30 ]; do
  if curl --silent --fail --max-time 2 "$URL" > /dev/null 2>&1; then
    log "CalendarBot ready (attempt $attempt)"
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done

sleep 10

# Memory optimization: Clear cache before launch
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1 || true

log "Free memory before Chromium:"
free -h | grep Mem >> "$LOG"

log "Launching Chromium with auto-reload workaround..."
# Disable wrapper-added flags that conflict by unsetting CHROMIUM_FLAGS
unset CHROMIUM_FLAGS

/usr/lib/chromium/chromium \
  --kiosk "$URL" \
  --disable-dev-shm-usage \
  --disable-gpu \
  --in-process-gpu \
  --no-sandbox \
  --no-zygote \
  --disable-sync \
  --disable-translate \
  --no-first-run \
  --disable-breakpad \
  --disable-logging \
  --disable-crash-reporter \
  --disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process \
  --renderer-process-limit=1 \
  --disable-background-timer-throttling \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --disable-ipc-flooding-protection \
  --blink-settings=imagesEnabled=true \
  --js-flags="--max-old-space-size=96 --optimize-for-size" \
  2>&1 &

CHROMIUM_PID=$!
log "Chromium started (PID: $CHROMIUM_PID)"

# Wait for NetworkService to crash (~5 sec) and restart (~10 sec), then refresh
(
  sleep 60
  log "Sending F5 to refresh after NetworkService restart..."
  export DISPLAY=:0
  xdotool search --sync --onlyvisible --class "Chromium" key F5
  log "F5 sent"
) &

# Wait for Chromium to exit
wait $CHROMIUM_PID
log "Chromium exited: $?"