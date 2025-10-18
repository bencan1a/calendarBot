# CalendarBot Kiosk Verification Guide

Purpose
A concise verification and troubleshooting checklist to confirm CalendarBot is installed and running as a kiosk on Raspberry Pi OS using the --pi-optimized configuration (Epiphany).

Preflight / pre-boot checks
- Confirm network:
  ```sh
  ping -c 3 8.8.8.8
  # Expect: 3 packets transmitted, 3 received
  ```
- Confirm disk space:
  ```sh
  df -h /
  # Expect: Available > ~500MB
  ```
- Confirm kiosk user (installer precedence: environment variable `KIOSK_USER`, first installer arg, or default to invoking user):
  ```sh
  echo "KIOSK_USER=${KIOSK_USER:-$USER}"
  # Expect: intended kiosk username
  ```
- Confirm service is enabled:
  ```sh
  sudo systemctl is-enabled calendarbot-kiosk@${USER}.service
  # Expect: "enabled"
  ```
- Confirm autologin override exists:
  ```sh
  test -f /etc/systemd/system/getty@tty1.service.d/override.conf && echo "PASS" || echo "FAIL"
  # Expect: PASS
  ```
- Inspect autologin contents:
  ```sh
  sudo sed -n '1,40p' /etc/systemd/system/getty@tty1.service.d/override.conf
  # Expect lines:
  # [Service]
  # ExecStart=
  # ExecStart=-/sbin/agetty --autologin <USER> --noclear %I $TERM
  ```

Smoke Test Checklist (copy/paste ready)

1) Service status
```sh
sudo systemctl status calendarbot-kiosk@${USER}.service --no-pager
```
Expected:
- Active: active (running)
- A Main PID present
- "Started" message referring to CalendarBot or web server

Failure signs:
- "failed", "inactive (dead)", or "start-limit-hit"

2) Recent service logs (startup)
```sh
sudo journalctl -u calendarbot-kiosk@${USER}.service --no-pager -n 200
```
Look for:
- Successful startup messages (e.g., "Binding to port 8080", "Server started")
- No Python tracebacks, ImportError, ModuleNotFoundError, or permissions errors

3) Process using venv python
```sh
ps -eo user,pid,cmd | grep "[p]ython.*calendarbot" || true
```
Expected:
- Command showing `/home/<USER>/calendarbot/venv/bin/python -m calendarbot --web --port 8080 --pi-optimized`
- Process owner equals the kiosk user

4) Port listening
```sh
ss -tlnp | grep :8080 || netstat -tlnp | grep :8080
```
Expected:
- A LISTEN line with a `python` process bound to `:8080`

5) HTTP response
```sh
IP=$(hostname -I | awk '{print $1}')
curl -I "http://${IP}:8080" || curl -s "http://${IP}:8080" | sed -n '1,5p'
```
Expected:
- HTTP/1.1 200 OK (or HTML output starting with <!DOCTYPE html> / <html>)

6) X11 basic checks (kiosk display)
```sh
command -v xdpyinfo >/dev/null && echo "xdpyinfo: installed" || echo "xdpyinfo: missing"
command -v xset >/dev/null && echo "xset: installed" || echo "xset: missing"
# If X is running:
DISPLAY=:0 xdpyinfo >/dev/null 2>&1 && echo "X: running" || echo "X: not running"
```
Expected:
- xdpyinfo/xset present (installed via apt) and X running if kiosk should be active

7) Browser process (Epiphany) — only if kiosk UI should be visible
```sh
ps aux | grep "[e]piphany" || true
```
Expected:
- epiphany-browser process running with kiosk URL (http://<IP>:8080) when kiosk is active

8) Autologin file confirmed
```sh
sudo cat /etc/systemd/system/getty@tty1.service.d/override.conf
```
Expected:
```
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin <USER> --noclear %I $TERM
```

Troubleshooting snippets and remediation

A) Service fails to start / crashed
- Capture logs:
  ```sh
  sudo journalctl -u calendarbot-kiosk@${USER}.service --no-pager -n 500
  ```
- Common fixes:
  - ModuleNotFoundError / calendarbot import errors:
    ```sh
    cd /home/${USER}/calendarbot
    /home/${USER}/calendarbot/venv/bin/python -m pip install -e .
    sudo systemctl restart calendarbot-kiosk@${USER}.service
    ```
  - Permission errors:
    ```sh
    sudo chown -R ${USER}:${USER} /home/${USER}/calendarbot
    sudo systemctl restart calendarbot-kiosk@${USER}.service
    ```
  - Address already in use:
    ```sh
    sudo lsof -i :8080
    sudo kill <pid>
    sudo systemctl restart calendarbot-kiosk@${USER}.service
    ```

B) Missing system dependencies (re-run apt)
```sh
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl ca-certificates \
  python3 python3-venv python3-pip python3-dev build-essential libssl-dev libffi-dev libsqlite3-dev \
  xserver-xorg xinit x11-xserver-utils openbox unclutter dbus-x11 \
  epiphany-browser gir1.2-webkit2-4.0
```
After install, re-run venv pip install steps (below) and restart service.

C) Epiphany / libwebkit issues
- Check libwebkit package:
  ```sh
  apt-cache policy libwebkit2gtk-4.0-*
  ```
- If epiphany fails to launch, confirm gir1.2-webkit2-4.0 is installed and libwebkit2gtk present; consider running:
  ```sh
  sudo apt-get install -y libwebkit2gtk-4.0-37
  ```

D) venv or pip errors
- Recreate venv and reinstall:
  ```sh
  cd /home/${USER}/calendarbot
  rm -rf venv
  python3 -m venv venv
  venv/bin/python -m pip install --upgrade pip setuptools wheel
  venv/bin/python -m pip install -r requirements.txt
  venv/bin/python -m pip install -e .
  sudo systemctl restart calendarbot-kiosk@${USER}.service
  ```

Field engineer quick checklist (pass/fail criteria)
1. Service active: `sudo systemctl is-active calendarbot-kiosk@${USER}.service` → PASS if `active`
2. HTTP 200: `curl -s -o /dev/null -w "%{http_code}" http://$(hostname -I | awk '{print $1}'):8080` → PASS if `200`
3. Process present: `pgrep -f "python.*calendarbot"` → PASS if count >=1
4. Logs clean: `sudo journalctl -u calendarbot-kiosk@${USER}.service --since "1 hour ago" | grep -i -c error` → PASS if `0`
5. Autologin: `test -f /etc/systemd/system/getty@tty1.service.d/override.conf` → PASS if exists
6. venv exists: `test -x /home/${USER}/calendarbot/venv/bin/python` → PASS if executable exists

Verification one-shot script (copy/paste)
```sh
#!/bin/sh
IP_ADDR=$(hostname -I | awk '{print $1}')
echo "=== CalendarBot Kiosk Quick-Verify ==="

# 1 Service
if sudo systemctl is-active --quiet calendarbot-kiosk@${USER}.service; then echo "Service: PASS"; else echo "Service: FAIL"; fi

# 2 Port
if ss -tln | grep -q :8080; then echo "Port 8080: PASS"; else echo "Port 8080: FAIL"; fi

# 3 HTTP
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://${IP_ADDR}:8080")
if [ "$HTTP_CODE" = "200" ]; then echo "HTTP 200: PASS"; else echo "HTTP 200: FAIL (code=$HTTP_CODE)"; fi

# 4 Process
if pgrep -f "python.*calendarbot" >/dev/null; then echo "Process: PASS"; else echo "Process: FAIL"; fi

# 5 Recent errors
ERRS=$(sudo journalctl -u calendarbot-kiosk@${USER}.service --since "10 minutes ago" | grep -i -c "error")
if [ "$ERRS" -eq 0 ]; then echo "Logs: PASS"; else echo "Logs: FAIL ($ERRS errors)"; fi

# 6 Autologin
if [ -f /etc/systemd/system/getty@tty1.service.d/override.conf ]; then echo "Autologin: PASS"; else echo "Autologin: FAIL"; fi

echo "=== Quick-Verify Complete ==="
echo "Web UI: http://${IP_ADDR}:8080"
```

Notes
- Service template: ensure ExecStart in [`kiosk/service/calendarbot-kiosk.service`](kiosk/service/calendarbot-kiosk.service:1) or `/etc/systemd/system/calendarbot-kiosk@.service` is:
  ```
  ExecStart=/home/%i/calendarbot/venv/bin/python -m calendarbot --web --port 8080 --pi-optimized
  ```
- Epiphany is recommended for minimal dependency. If you prefer Chromium, replace `epiphany-browser` with `chromium-browser` (larger footprint).
- E-paper support is intentionally omitted for `--pi-optimized`. Enabling e-paper requires additional packages and SPI/GPIO configuration (not covered here).

----
End of document.