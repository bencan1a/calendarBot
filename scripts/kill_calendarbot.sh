#!/bin/bash

# Helper script to kill any running calendarbot processes
# Usage: ./scripts/kill_calendarbot.sh [--force]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if force flag is provided
FORCE=false
if [[ "$1" == "--force" ]]; then
    FORCE=true
fi

echo -e "${YELLOW}🔍 Looking for running calendarbot processes...${NC}"

# Find processes that might be calendarbot related
PROCESSES=$(pgrep -af "calendarbot\|python.*calendarbot\|python.*main\.py" 2>/dev/null || true)

if [[ -z "$PROCESSES" ]]; then
    echo -e "${GREEN}✅ No calendarbot processes found running${NC}"
    exit 0
fi

echo -e "${YELLOW}Found the following processes:${NC}"
echo "$PROCESSES"
echo

if [[ "$FORCE" == "true" ]]; then
    echo -e "${RED}🔥 Force killing all calendarbot processes...${NC}"

    # Kill processes containing calendarbot
    pkill -f "calendarbot" 2>/dev/null || true

    # Kill python processes running calendarbot or main.py from this directory
    pkill -f "python.*calendarbot" 2>/dev/null || true
    pkill -f "python.*main\.py" 2>/dev/null || true

    echo -e "${GREEN}✅ All calendarbot processes have been terminated${NC}"
else
    echo -e "${YELLOW}Would you like to kill these processes? (y/N)${NC}"
    read -r response

    case "$response" in
        [yY][eE][sS]|[yY])
            echo -e "${RED}🔥 Killing calendarbot processes...${NC}"

            # Kill processes containing calendarbot
            pkill -f "calendarbot" 2>/dev/null || true

            # Kill python processes running calendarbot or main.py from this directory
            pkill -f "python.*calendarbot" 2>/dev/null || true
            pkill -f "python.*main\.py" 2>/dev/null || true

            echo -e "${GREEN}✅ All calendarbot processes have been terminated${NC}"
            ;;
        *)
            echo -e "${YELLOW}❌ No processes were killed${NC}"
            exit 0
            ;;
    esac
fi

# Wait a moment and check if any processes are still running
sleep 1
REMAINING=$(pgrep -af "calendarbot\|python.*calendarbot\|python.*main\.py" 2>/dev/null || true)

if [[ -n "$REMAINING" ]]; then
    echo -e "${RED}⚠️  Some processes may still be running:${NC}"
    echo "$REMAINING"
    echo -e "${YELLOW}You may need to use 'kill -9' manually for stubborn processes${NC}"
else
    echo -e "${GREEN}🎉 All calendarbot processes successfully terminated${NC}"
fi
