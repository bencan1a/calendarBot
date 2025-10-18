# Raspberry Pi Kiosk Installation Guide

Install CalendarBot as a kiosk on fresh Raspberry Pi OS with --pi-optimized mode using Epiphany browser for minimal dependencies.

## Preflight Checks

Verify network connectivity, sufficient disk space (>2GB), and that you have a target kiosk user. The installer determines KIOSK_USER from environment variable `KIOSK_USER`, first script argument, or defaults to the invoking user.

```bash
ping -c 1 google.com  # Network check
df -h /               # Disk space check
whoami                # Current user (will be kiosk user if not specified)
```

## Install System Dependencies

Run the following command to install all required packages non-interactively:

```bash
sudo apt-get update -y && sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl ca-certificates \
  python3 python3-venv python3-pip python3-dev build-essential libssl-dev libffi-dev libsqlite3-dev \
  xserver-xorg xinit x11-xserver-utils openbox unclutter dbus-x11 \
  epiphany-browser gir1.2-webkit2-4.0
```

## Setup Python Environment

Clone the repository and create the Python virtual environment:

```bash
# Clone repository (if not already present)
git clone <repository-url> calendarbot
cd calendarbot

# Create and configure virtual environment
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip setuptools wheel
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m pip install -e .
```

## Install Systemd Service and Configure Autologin

Copy the service template to systemd directory:

```bash
sudo cp kiosk/service/calendarbot-kiosk.service /etc/systemd/system/calendarbot-kiosk@.service
```

The service uses this exact ExecStart command:

```
ExecStart=/home/%i/calendarbot/venv/bin/python -m calendarbot --web --port 8080 --pi-optimized
```

Configure autologin for the kiosk user by creating the getty override:

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable calendarbot-kiosk@$USER.service
sudo systemctl start calendarbot-kiosk@$USER.service
```

## Install Kiosk Scripts and Set Permissions

Copy kiosk scripts to user home directory and set proper permissions:

```bash
mkdir -p ~/bin
cp kiosk/scripts/start-kiosk.sh ~/bin/start-kiosk.sh
cp kiosk/scripts/.xinitrc ~/.xinitrc
chmod +x ~/bin/start-kiosk.sh ~/.xinitrc
```

## Verification

Check service status and web server response:

```bash
# Verify service is active
sudo systemctl status calendarbot-kiosk@$USER.service

# Check service logs (should show startup without tracebacks)
sudo journalctl -u calendarbot-kiosk@$USER.service --no-pager -l

# Test web server response
curl -I http://$(hostname -I | awk '{print $1}'):8080
```

Service should show "active (running)" status and curl should return HTTP 200 response.

## Notes and Troubleshooting

**Browser Choice**: Epiphany is recommended over Chromium for lower resource usage and fewer dependencies on Pi hardware.

**E-paper Support**: Intentionally omitted for --pi-optimized mode. If needed later, install additional packages (`python3-pil python3-spidev python3-rpi.gpio`) and configure SPI/GPIO.

**WebKit Version**: If Epiphany fails to start, check WebKit library availability:
```bash
apt-cache policy libwebkit2gtk-4.0-37 libwebkit2gtk-4.0-dev
```

**Common Issues**:
- Service fails: Check Python venv path in service file matches actual installation
- Browser won't start: Verify X11 dependencies and autologin configuration
- Network unreachable: Ensure Pi has network access and port 8080 is not blocked

## One-Shot Installation Commands

For automated deployment on fresh Raspberry Pi OS, run these commands in sequence:

```bash
# 1. Install system packages
sudo apt-get update -y && sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates python3 python3-venv python3-pip python3-dev build-essential libssl-dev libffi-dev libsqlite3-dev xserver-xorg xinit x11-xserver-utils openbox unclutter dbus-x11 epiphany-browser gir1.2-webkit2-4.0

# 2. Clone and setup project
git clone <repository-url> calendarbot && cd calendarbot

# 3. Create Python environment
python3 -m venv venv && venv/bin/python -m pip install --upgrade pip setuptools wheel && venv/bin/python -m pip install -r requirements.txt && venv/bin/python -m pip install -e .

# 4. Install systemd service
sudo cp kiosk/service/calendarbot-kiosk.service /etc/systemd/system/calendarbot-kiosk@.service

# 5. Configure autologin
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d && echo -e "[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin $USER --noclear %I \\\$TERM" | sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf

# 6. Enable and start service
sudo systemctl daemon-reload && sudo systemctl enable calendarbot-kiosk@$USER.service && sudo systemctl start calendarbot-kiosk@$USER.service

# 7. Install kiosk scripts
mkdir -p ~/bin && cp kiosk/scripts/start-kiosk.sh ~/bin/start-kiosk.sh && cp kiosk/scripts/.xinitrc ~/.xinitrc && chmod +x ~/bin/start-kiosk.sh ~/.xinitrc

# 8. Verify installation
sudo systemctl status calendarbot-kiosk@$USER.service && curl -I http://$(hostname -I | awk '{print $1}'):8080