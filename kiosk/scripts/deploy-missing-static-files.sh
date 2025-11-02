#!/bin/bash
# Deploy missing static files to Pi
# This script finds where calendarbot_lite is running from and copies the static files

set -e

USER="${1:-bencan}"

echo "========================================="
echo "Deploy Missing Static Files"
echo "========================================="
echo ""

# Check if running on the Pi (as bencan user) or needs sudo
if [ "$EUID" -eq 0 ]; then
    echo "Running as root"
    RUN_AS_USER="sudo -u $USER"
else
    echo "Running as user: $(whoami)"
    RUN_AS_USER=""
fi

echo ""
echo "Step 1: Finding where calendarbot_lite is installed..."
echo ""

# Find the actual Python module location
PYTHON_BIN="/home/$USER/calendarbot/venv/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    echo "ERROR: Python venv not found at $PYTHON_BIN"
    exit 1
fi

# Get the actual package location
PACKAGE_DIR=$($PYTHON_BIN -c "import calendarbot_lite; import os; print(os.path.dirname(calendarbot_lite.__file__))" 2>/dev/null || echo "")

if [ -z "$PACKAGE_DIR" ]; then
    echo "ERROR: Could not find calendarbot_lite package"
    echo "Is calendarbot_lite installed in the venv?"
    echo ""
    echo "You may need to install it first:"
    echo "  cd /home/$USER/calendarbot"
    echo "  . venv/bin/activate"
    echo "  pip install -e /home/$USER/calendarBot/calendarbot_lite"
    exit 1
fi

echo "Found calendarbot_lite at: $PACKAGE_DIR"
echo ""

echo "Step 2: Checking which static files are missing..."
echo ""

MISSING_FILES=()

for file in whatsnext.html whatsnext.css whatsnext.js; do
    if [ ! -f "$PACKAGE_DIR/$file" ]; then
        echo "  ❌ Missing: $file"
        MISSING_FILES+=("$file")
    else
        echo "  ✓ Found: $file"
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo ""
    echo "All static files are present. No action needed."
    exit 0
fi

echo ""
echo "Step 3: Finding source files..."
echo ""

# Look for the source repository
SOURCE_DIR="/home/$USER/calendarBot/calendarbot_lite"
if [ ! -d "$SOURCE_DIR" ]; then
    SOURCE_DIR="/home/$USER/calendarbot/calendarbot_lite"
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "ERROR: Could not find source directory"
    echo "Looked in:"
    echo "  /home/$USER/calendarBot/calendarbot_lite"
    echo "  /home/$USER/calendarbot/calendarbot_lite"
    exit 1
fi

echo "Found source directory: $SOURCE_DIR"
echo ""

echo "Step 4: Copying missing files..."
echo ""

for file in "${MISSING_FILES[@]}"; do
    SOURCE_FILE="$SOURCE_DIR/$file"
    DEST_FILE="$PACKAGE_DIR/$file"

    if [ ! -f "$SOURCE_FILE" ]; then
        echo "  ❌ Source file not found: $SOURCE_FILE"
        continue
    fi

    echo "  Copying $file..."
    if [ -n "$RUN_AS_USER" ]; then
        $RUN_AS_USER cp "$SOURCE_FILE" "$DEST_FILE"
    else
        cp "$SOURCE_FILE" "$DEST_FILE"
    fi

    # Verify the copy
    if [ -f "$DEST_FILE" ]; then
        echo "  ✓ Copied successfully"
    else
        echo "  ❌ Copy failed"
    fi
done

echo ""
echo "Step 5: Verifying deployment..."
echo ""

ALL_PRESENT=true
for file in whatsnext.html whatsnext.css whatsnext.js; do
    if [ ! -f "$PACKAGE_DIR/$file" ]; then
        echo "  ❌ Still missing: $file"
        ALL_PRESENT=false
    else
        SIZE=$(stat -f%z "$PACKAGE_DIR/$file" 2>/dev/null || stat -c%s "$PACKAGE_DIR/$file" 2>/dev/null)
        echo "  ✓ Present: $file ($SIZE bytes)"
    fi
done

echo ""
echo "========================================="
if [ "$ALL_PRESENT" = true ]; then
    echo "Deployment Complete!"
    echo "========================================="
    echo ""
    echo "Static files are now in place at:"
    echo "  $PACKAGE_DIR"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Restart the CalendarBot service:"
    echo "   sudo systemctl restart calendarbot-kiosk@$USER.service"
    echo ""
    echo "2. Wait 10 seconds for service to start"
    echo ""
    echo "3. Check if browser heartbeat is working:"
    echo "   curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'"
    echo ""
    echo "4. Test the JavaScript file is served:"
    echo "   curl -s http://127.0.0.1:8080/whatsnext.js | head -20"
    echo ""
else
    echo "Deployment Failed"
    echo "========================================="
    echo ""
    echo "Some files are still missing. Please check the errors above."
fi
