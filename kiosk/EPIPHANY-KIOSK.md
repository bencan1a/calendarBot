# Epiphany (WebKit) Kiosk — Implementation & Maintenance

Overview

- Purpose: Replace Chromium with Epiphany (WebKitGTK) for Pi Zero2 kiosk to reduce memory/CPU usage and improve reliability on constrained hardware.

Changes made

- Replaced Chromium launch in [`kiosk/scripts/start-kiosk.sh:51`](kiosk/scripts/start-kiosk.sh:51).
- Updated installer dependency list in [`kiosk/install.sh:176`](kiosk/install.sh:176).
- Service file remains referenced at [`kiosk/service/calendarbot-kiosk.service:10`](kiosk/service/calendarbot-kiosk.service:10) (no change).

Required packages

- `epiphany-browser`
- `gir1.2-webkit2-4.0` (WebKitGTK GObject introspection)
- Optionally: OS-specific `libwebkit2gtk-4.0-<version>` package (name varies by distribution/release)

Installation commands (run on the Pi)

sudo apt-get update && sudo apt-get install -y epiphany-browser
sudo apt-get install -y gir1.2-webkit2-4.0 || true

Exact configuration edits

- Start script: replaced
  Old (was at [`kiosk/scripts/start-kiosk.sh:51`](kiosk/scripts/start-kiosk.sh:51)):
  exec chromium-browser --kiosk --app="$URL" --noerrdialogs --disable-infobars --disable-restore-session-state --disable-session-crashed-bubble --no-sandbox --disable-features=TranslateUI
  New:
  exec epiphany-browser --kiosk "$URL"

- Installer: replaced dependency "chromium-browser" with "epiphany-browser" in [`kiosk/install.sh:176`](kiosk/install.sh:176).

Deployment steps

1. Install packages (see "Installation commands" above).
2. Ensure you have the latest repository changes (the start script and installer edits are included in the repo).
3. If using the installer script, re-run it so the systemd service and scripts are copied/installed.
4. Enable and start systemd service:
   sudo systemctl enable calendarbot-kiosk@<user>.service
   sudo systemctl start calendarbot-kiosk@<user>.service

Testing checklist

- Smoke test: From another machine open http://<pi-ip>:8080/whats-next
- JS feature check: Open Epiphany (non-kiosk) and run in the address bar:
  javascript:console.log(typeof fetch, typeof (async function(){}))
  Expect "function" and "function".
- Network check: verify hide button triggers a POST /api/events/hide (see [`tests/integration/test_phase_3_browser_validation.py:48`](tests/integration/test_phase_3_browser_validation.py:48)).
- Visual: verify countdown timers continue and optimistic UI updates occur.

Troubleshooting

- If window.fetch is undefined or async errors occur, check WebKitGTK version:
  dpkg -l | grep libwebkit2gtk
- If the installed WebKitGTK is too old, consider upgrading OS packages or using backports.
- Temporary workaround: add a small fetch polyfill into the served web assets:
  Include https://unpkg.com/whatwg-fetch@3.6.2/dist/fetch.umd.js in your HTML before other scripts.

Logs

- Watch service logs:
  journalctl -u calendarbot-kiosk@<user>.service -f
- Epiphany user session errors may appear in ~/.xsession-errors or system journal.

Revert

- To revert to Chromium:
  - Change [`kiosk/scripts/start-kiosk.sh:51`](kiosk/scripts/start-kiosk.sh:51) back to the original Chromium exec line.
  - Restore `"chromium-browser"` in the deps array at [`kiosk/install.sh:176`](kiosk/install.sh:176).

Known challenges & resolutions

1) WebKitGTK version variability
   - Challenge: Older Raspberry Pi OS images may ship older libwebkit2gtk lacking modern APIs.
   - Resolution: Test on the target image; prefer upgrading or backports. If upgrade is impossible, provide a fetch polyfill and minimal ES polyfills as needed.

2) Limited CLI flags vs Chromium
   - Challenge: Epiphany exposes fewer command-line flags for suppressing dialogs and UI controls.
   - Resolution: Rely on the openbox session and systemd restart behavior. Keep unclutter/openbox/xset configuration as-is.

3) Automated tests and CI
   - Challenge: Playwright tests and CI may rely on Chromium; switching the device runtime does not require changing CI.
   - Resolution: Keep CI running against Playwright's `chromium` or `webkit` as appropriate; only the kiosk device runtime is changed.

Next steps & maintenance

- Run compatibility verification on an actual Pi Zero2 image and record the libwebkit2gtk version.
- If frequent WebKit regressions appear, consider embedding a WebKitGTK view inside the application (via PyGObject or pywebview) for tighter control — request "Embed WebKitGTK" if you'd like an implementation plan.

Contact

For follow-up or to proceed with embedding WebKit, request "Embed WebKitGTK".