#!/bin/bash

# Quick kill script for calendarbot processes - no questions asked
# Usage: ./scripts/quick_kill.sh

echo "🔥 Killing all calendarbot processes..."

# Kill all calendarbot related processes
pkill -f "calendarbot" 2>/dev/null || true
pkill -f "python.*calendarbot" 2>/dev/null || true
pkill -f "python.*main\.py" 2>/dev/null || true

# Also kill any python processes that might be running from this directory
pkill -f "python.*$(basename "$PWD")" 2>/dev/null || true

echo "✅ Done! All calendarbot processes should be terminated."

# Quick check
sleep 0.5
REMAINING=$(pgrep -af "calendarbot\|python.*calendarbot\|python.*main\.py" 2>/dev/null || true)
if [[ -n "$REMAINING" ]]; then
    echo "⚠️  Some processes may still be running:"
    echo "$REMAINING"
else
    echo "🎉 All processes successfully killed."
fi