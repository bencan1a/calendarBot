#!/bin/bash
# Diagnostic script for kiosk issues

echo "========================================="
echo "CalendarBot Kiosk Diagnostics"
echo "========================================="
echo ""

echo "[1] Checking server status..."
curl -s http://127.0.0.1:8080/api/health | jq '.'

echo ""
echo "[2] Checking if browser heartbeat JavaScript is in HTML..."
curl -s http://127.0.0.1:8080/ | grep -A5 -B5 "browser-heartbeat" || echo "NOT FOUND!"

echo ""
echo "[3] Checking server logs for errors..."
sudo journalctl -u calendarbot-kiosk@bencan.service -n 50 --no-pager | grep -i error

echo ""
echo "[4] Checking if xdotool can find browser window..."
DISPLAY=:0 xdotool search --class chromium 2>&1

echo ""
echo "[5] Testing soft reload command..."
DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5 2>&1

echo ""
echo "[6] Checking processes..."
echo "X server:"
ps aux | grep Xorg | grep -v grep
echo ""
echo "Browser:"
ps aux | grep chromium | grep -v grep | head -3

echo ""
echo "[7] Checking hostname resolution..."
hostname -I
echo "IPv4 only:"
hostname -I | awk '{print $1}'

echo ""
echo "========================================="
echo "Diagnostics Complete"
echo "========================================="
