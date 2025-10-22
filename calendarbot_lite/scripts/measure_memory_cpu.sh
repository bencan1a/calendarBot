#!/bin/sh
# measure_memory_cpu.sh - smoke script for calendarbot_lite
# Purpose: start the lite server briefly, sample memory/CPU, then stop the server.
# Example: PORT=8081 BIND=127.0.0.1 ./calendarbot_lite/scripts/measure_memory_cpu.sh
# Note: This is a smoke script for local/dev only (e.g., Pi Zero 2W). Uses only POSIX sh and standard proc utils.

set -eu

# Optional environment overrides (defaults)
: "${PORT:=8080}"
: "${BIND:=127.0.0.1}"

# Find python executable (prefer python3)
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "ERROR: python3 or python not found in PATH" >&2
  exit 1
fi

echo "Using Python: $PYTHON"
echo "PORT=$PORT BIND=$BIND"

# Log file for server stdout/stderr
LOGFILE="$(pwd)/calendarbot_lite_smoke.log"
echo "Server log: $LOGFILE"

# Start server in background.
# The invoked module and flags are intentionally simple; adjust if your server module accepts different args.
echo "Starting calendarbot_lite server..."
PYTHONPATH=. "$PYTHON" -m calendarbot_lite.server --bind "$BIND" --port "$PORT" >"$LOGFILE" 2>&1 &
PID=$!
echo "Server started with PID $PID"

# Cleanup function to stop server; will be invoked on exit or interrupt.
cleanup() {
  if [ -n "${PID-}" ]; then
    if kill -0 "$PID" >/dev/null 2>&1; then
      echo "Stopping server (PID $PID)..."
      kill "$PID" >/dev/null 2>&1 || true
      # wait up to 5 seconds for graceful exit
      i=0
      while kill -0 "$PID" >/dev/null 2>&1 && [ "$i" -lt 5 ]; do
        sleep 1
        i=$((i + 1))
      done
      if kill -0 "$PID" >/dev/null 2>&1; then
        echo "Server did not exit, forcing kill..."
        kill -9 "$PID" >/dev/null 2>&1 || true
      else
        echo "Server stopped."
      fi
    fi
  fi
}

# Ensure cleanup runs on script exit/interrupt
trap 'cleanup' INT TERM EXIT

echo "Waiting 10s for server to initialize..."
sleep 10

# Verify server is still running
if ! kill -0 "$PID" >/dev/null 2>&1; then
  echo "ERROR: server (PID $PID) is not running after startup wait. See log:" >&2
  sed -n '1,200p' "$LOGFILE" >&2 || true
  exit 2
fi

# Sample stats using ps (portable)
echo "Sampling process stats for PID $PID..."
echo "ps output:"
ps -p "$PID" -o pid,etimes,rss,pcpu || true

# Capture numeric values without headers for JSON-like summary
PS_VALUES=$(ps -p "$PID" -o pid=,etimes=,rss=,pcpu= 2>/dev/null || true)
if [ -n "$PS_VALUES" ]; then
  # Normalize whitespace and assign
  set -- $PS_VALUES
  SAMP_PID=$1
  ELAPSED=$2
  RSS=$3
  PCPU=$4
else
  SAMP_PID=null
  ELAPSED=null
  RSS=null
  PCPU=null
fi

# Optionally attempt a top snapshot in batch mode (non-fatal if unavailable)
if command -v top >/dev/null 2>&1; then
  echo "Attempting top snapshot (batch mode)..."
  # Many Linux tops support -b -n1 -p PID. Try it; if it fails, skip quietly.
  if top -b -n1 -p "$PID" > /tmp/calendarbot_lite_top.out 2>/dev/null; then
    echo "top snapshot:"
    cat /tmp/calendarbot_lite_top.out
  else
    echo "top not usable in batch mode on this system; skipping top snapshot."
  fi
else
  echo "top not found; skipping top snapshot."
fi

# Print one-line JSON-like summary for easy parsing
printf '{ "pid": %s, "elapsed_s": %s, "rss_kb": %s, "pcpu": %s }\n' "$SAMP_PID" "$ELAPSED" "$RSS" "$PCPU"

# Remove trap and perform cleanup now (so EXIT does not attempt again)
trap - INT TERM EXIT
cleanup

echo "Done."
exit 0