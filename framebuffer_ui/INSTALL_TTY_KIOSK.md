# CalendarBot Framebuffer Kiosk - TTY Auto-Login Setup

This guide configures the Raspberry Pi to automatically login to TTY1 (console) and run the framebuffer UI, avoiding X11 entirely.

## Why TTY Login Instead of Systemd Service?

pygame's SDL2 framebuffer drivers (`kmsdrm` and `fbcon`) require running from a virtual terminal (TTY) context. Running from systemd doesn't provide this context, causing drivers to fail.

## Installation Steps

### 1. Make startup script executable

```bash
cd ~/calendarbot/framebuffer_ui
chmod +x start-framebuffer-kiosk.sh
```

### 2. Configure auto-login on TTY1

Create systemd drop-in directory:

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d/
```

Create override configuration:

```bash
sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin USERNAME --noclear %I \$TERM
EOF
```

**Replace `USERNAME` with your actual username (e.g., `bencan`).**

### 3. Add kiosk startup to login script

Add to your `~/.bash_profile` (or `~/.profile` if bash_profile doesn't exist):

```bash
# CalendarBot Framebuffer Kiosk
# Only run on tty1 and only if not already running
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$CALENDARBOT_KIOSK_RUNNING" ]; then
    export CALENDARBOT_KIOSK_RUNNING=1
    exec ~/calendarbot/framebuffer_ui/start-framebuffer-kiosk.sh
fi
```

**Quick command to add it:**

```bash
cat >> ~/.bash_profile <<'EOF'

# CalendarBot Framebuffer Kiosk
# Only run on tty1 and only if not already running
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$CALENDARBOT_KIOSK_RUNNING" ]; then
    export CALENDARBOT_KIOSK_RUNNING=1
    exec ~/calendarbot/framebuffer_ui/start-framebuffer-kiosk.sh
fi
EOF
```

### 4. Disable systemd service (if enabled)

```bash
# Stop and disable the systemd service
sudo systemctl stop calendarbot-display@USERNAME.service
sudo systemctl disable calendarbot-display@USERNAME.service

# Also disable X11 kiosk if running
sudo systemctl stop calendarbot-kiosk-watchdog@USERNAME.service
sudo systemctl disable calendarbot-kiosk-watchdog@USERNAME.service
```

### 5. Reboot to start kiosk

```bash
sudo reboot
```

The Pi will:
1. Boot up
2. Auto-login to TTY1 as your user
3. Run the startup script
4. Launch the framebuffer UI

## Verifying Installation

After reboot, the display should show the calendar UI. If you need to check logs or debug:

### Access via SSH

SSH into the Pi from another machine:

```bash
ssh USERNAME@raspberry-pi-ip
```

### Check if kiosk is running

```bash
ps aux | grep framebuffer_ui
```

### View logs

The framebuffer UI logs to stdout/stderr, which goes to systemd journal:

```bash
journalctl -t start-framebuffer-kiosk -f
```

### Manual restart

If you need to restart the kiosk:

```bash
# Kill the current instance
pkill -f framebuffer_ui

# Restart (if logged in via SSH)
sudo systemctl restart getty@tty1.service
```

Or simply reboot:

```bash
sudo reboot
```

## Stopping the Kiosk

### Temporary (until reboot)

SSH in and kill the process:

```bash
pkill -f framebuffer_ui
```

### Permanent

Remove the kiosk startup from `~/.bash_profile`:

```bash
nano ~/.bash_profile
# Delete or comment out the CalendarBot section
```

Or disable auto-login:

```bash
sudo rm /etc/systemd/system/getty@tty1.service.d/autologin.conf
sudo systemctl daemon-reload
```

## Troubleshooting

### Display shows "offscreen" driver

This means pygame couldn't access the framebuffer. Check:

```bash
# 1. Verify framebuffer exists
ls -la /dev/fb0

# 2. Check permissions
groups  # Should include 'video' group

# 3. Check which TTY you're on
tty  # Should be /dev/tty1
```

### Kiosk doesn't start on boot

Check auto-login configuration:

```bash
# Verify auto-login is configured
sudo systemctl status getty@tty1.service

# Check .bash_profile
cat ~/.bash_profile | grep -A 5 CALENDARBOT
```

### Need to access shell on TTY1

Press `Ctrl+C` to exit the framebuffer UI, or:

1. SSH from another machine
2. Switch to TTY2: Press `Ctrl+Alt+F2`
3. Login manually
4. Kill the process: `pkill -f framebuffer_ui`

## Performance

Expected resource usage:
- **Memory**: ~15-25MB RSS (vs ~260MB for X11+Chromium)
- **CPU**: <1% idle, <5% during updates
- **Startup**: <5 seconds (vs ~60s for X11+Chromium)

## Comparison: TTY Auto-Login vs Systemd Service

| Aspect | TTY Auto-Login | Systemd Service |
|--------|----------------|-----------------|
| Framebuffer Access | ✅ Works | ❌ Doesn't work |
| SDL Video Drivers | ✅ kmsdrm/fbcon available | ❌ Only dummy works |
| Setup Complexity | Simple | Complex |
| Debugging | Easy (SSH access) | Harder (journalctl) |
| Auto-restart on crash | No (manual reboot) | Yes (systemd) |

**Recommendation:** Use TTY auto-login for framebuffer pygame apps.

## See Also

- [framebuffer_ui/README.md](README.md) - Framebuffer UI documentation
- [kiosk/README.md](../kiosk/README.md) - X11 kiosk alternative
