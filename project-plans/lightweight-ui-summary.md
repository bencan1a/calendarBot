# Lightweight UI Architecture - Executive Summary

**Date:** 2025-12-29  
**Status:** ✅ **Approved - Ready for Implementation**

---

## Problem Statement

The current CalendarBot kiosk runs X11 + Chromium browser on Raspberry Pi Zero 2W:
- **Memory Usage:** ~260MB (X11: 100MB, Chromium: 150MB, other: 10MB)
- **Complexity:** Multiple failure points requiring 3-level watchdog recovery
- **Startup Time:** ~60 seconds from boot to display
- **Resource Waste:** Heavy browser stack for static calendar display

---

## Proposed Solution

Replace X11 + Chromium with **lightweight Python framebuffer UI using pygame**:

```
BEFORE: Pi Zero 2W → X11 → Chromium → HTML/CSS/JS → Backend API (~260MB)
AFTER:  Pi Zero 2W → Python + pygame → Backend API (~15MB)
```

**Memory Savings:** 94% reduction (260MB → 15MB)  
**Startup Improvement:** 12x faster (60s → 5s)  
**Complexity Reduction:** No X11, no browser, no watchdog needed

---

## Key Benefits

1. **💾 Massive Memory Savings:** <25MB vs. ~260MB
2. **⚡ Fast Startup:** <5s vs. ~60s 
3. **🎯 Simpler Architecture:** Direct framebuffer rendering, no X11/browser
4. **🌐 Remote Backend Support:** Backend can run on different device
5. **🔒 More Reliable:** Single process vs. complex browser stack
6. **🎨 Visual Fidelity:** Pixel-perfect replication of current HTML/CSS design

---

## Technology Stack

### Recommended: Pygame + Framebuffer

**Core Technology:**
- Python 3.12+
- pygame 2.5+ (SDL2 framebuffer backend)
- aiohttp (async HTTP client)
- DRM/KMS or /dev/fb0 framebuffer

**Why pygame:**
- ✅ Clean, stable API
- ✅ Hardware-accelerated rendering
- ✅ No X11 required (SDL_VIDEODRIVER=kmsdrm)
- ✅ TTF font support built-in
- ✅ Only 1 new dependency (~5MB)

**Memory Estimate:** 15MB RSS (target), 25MB max acceptable

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ CalendarBot Framebuffer UI (Python)                     │
│                                                          │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Renderer     │  │  API Client  │  │   Layout    │ │
│  │  (pygame)     │  │  (aiohttp)   │  │   Engine    │ │
│  └───────┬───────┘  └───────┬──────┘  └──────┬──────┘ │
│          │                  │                 │         │
│          └──────────────────┴─────────────────┘         │
│                      │                                   │
│            ┌─────────▼─────────┐                        │
│            │  Event Loop       │                        │
│            │  (asyncio)        │                        │
│            └─────────┬─────────┘                        │
└──────────────────────┼──────────────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │  DRM/KMS Framebuffer│
            └──────────┬──────────┘
                       │
            ┌──────────▼──────────┐
            │  HDMI Display       │
            └─────────────────────┘
```

**API Communication:**
- HTTP GET `/api/whats-next` every 60 seconds
- Backend can be localhost or remote IP address
- Graceful error handling and retries

---

## Visual Design

The framebuffer UI will **exactly replicate** the current HTML/CSS design:

### Layout (480x800 pixels)
```
┌─────────────────────────────┐
│ Zone 1: Countdown (300px)   │  ← Gray background, large number
│   "STARTS IN"               │
│   "9 HOURS"                 │
│   "58 MINUTES"              │
├─────────────────────────────┤
│ Zone 2: Meeting (400px)     │  ← White card with details
│   "Data and Information..." │
│   "07:00 AM - 08:00 AM"     │
│   Location (optional)       │
├─────────────────────────────┤
│ Zone 3: Status (100px)      │  ← Gray background, status text
│   "Next meeting"            │
└─────────────────────────────┘
```

### Typography & Colors
- **Fonts:** Match CSS exactly (21px, 78px, 40px, etc.)
- **Colors:** 8-shade grayscale palette from CSS
- **Rendering:** pygame drawing primitives + TTF fonts

---

## Implementation Plan

### Phase 1: Core Rendering (Week 1)
- Set up framebuffer_ui package
- Implement pygame renderer for all 3 zones
- Test visual match with screenshots

### Phase 2: API Integration (Week 1-2)
- Implement async API client
- Add layout engine for data transformation
- Test with live backend

### Phase 3: Deployment (Week 2)
- Create systemd service
- Write installation script
- Test on Pi Zero 2W
- Benchmark performance

### Phase 4: Feature Parity (Week 3)
- Fast refresh mode (<5min to meeting)
- Visual state changes (normal/warning/critical)
- Connection status handling

### Phase 5: Testing & Polish (Week 3-4)
- Unit tests
- Integration tests
- Performance optimization
- Documentation

**Total Timeline:** 3-4 weeks

---

## Dependencies

### New Python Packages
- `pygame>=2.5.0` - Framebuffer rendering (~5MB)

### Existing (Already in Project)
- `aiohttp>=3.8.0` - Async HTTP client
- `PyYAML>=6.0` - Config parsing
- `python-dateutil>=2.8.0` - Time formatting

### System (Raspberry Pi OS)
```bash
sudo apt-get install -y libsdl2-2.0-0 libsdl2-ttf-2.0-0 libdrm2 libgbm1
```
**Install Size:** ~10MB

---

## Deployment

### systemd Service
```ini
# /etc/systemd/system/calendarbot-display@.service
[Unit]
Description=CalendarBot Framebuffer Display
After=network-online.target

[Service]
Type=simple
User=%i
Environment="SDL_VIDEODRIVER=kmsdrm"
Environment="CALENDARBOT_BACKEND_URL=http://localhost:8080"
ExecStart=/home/%i/calendarbot/venv/bin/python -m framebuffer_ui.main
Restart=always

[Install]
WantedBy=multi-user.target
```

### Installation
```bash
# Enable and start
sudo systemctl enable calendarbot-display@bencan.service
sudo systemctl start calendarbot-display@bencan.service

# Disable old X11 kiosk (optional)
sudo systemctl disable auto-login-x-session
```

---

## Performance Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Memory (RSS)** | ~260MB | <25MB | **94% reduction** |
| **Startup Time** | ~60s | <5s | **12x faster** |
| **CPU (idle)** | ~5% | <2% | **60% reduction** |
| **Components** | X11+Browser+Backend | UI+Backend | **Simpler** |

---

## Migration Strategy

### Backward Compatible
- New UI runs as separate systemd service
- Can run alongside old X11 kiosk for testing
- Easy rollback if issues arise

### Testing Period
- Deploy as **opt-in beta** for 2-4 weeks
- Collect feedback and performance data
- Make default after validation

### Rollback
```bash
# Revert to old kiosk if needed
sudo systemctl disable calendarbot-display@user.service
sudo systemctl enable auto-login-x-session
sudo reboot
```

---

## Success Criteria

Implementation is successful if:

1. ✅ Memory: <25MB RSS (vs. current ~260MB)
2. ✅ Startup: <15s to first frame (vs. current ~60s)
3. ✅ Visual: Pixel-accurate match to HTML/CSS design
4. ✅ Stability: 24/7 uptime for 1+ week without crashes
5. ✅ CPU: <5% average on Pi Zero 2W
6. ✅ Remote: Connects to backend on different device
7. ✅ Features: All current kiosk features replicated
8. ✅ Acceptance: Positive user feedback

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| pygame not working on Pi | High | Test early on real hardware; PIL fallback |
| Font rendering issues | Low | Bundle TTF fonts with package |
| Network latency (remote) | Low | Add timeout and retry logic |
| Memory leaks | Medium | Regular testing with profiler |

---

## Architecture Decisions ✅

**User review complete. The following decisions have been made:**

1. **Technology:** ✅ **Pygame approved** for framebuffer rendering
2. **Backend Location:** ✅ **Allow remote backend** (already supported via HTTP API)
3. **Configuration:** ✅ **Use existing .env** configuration mechanism
4. **Skip Button:** ⚠️ **Attempt touch input** if feasible; user prefers capability but willing to live without
5. **Font Handling:** ✅ **Bundle TTF fonts** with package
6. **Backward Compatibility:** ✅ **Keep X11 kiosk** as fallback; new UI as alternative mode
7. **Refresh Rate:** ✅ **60s polling** (no adaptive refresh)
8. **Error Display:** ✅ **On-screen, but resilient** (only show after 15+ minutes of failures)
9. **Installation:** ✅ **Separate installer** based on install-kiosk.sh (stripped down)
10. **Testing:** ✅ **Unit tests** provided; manual E2E on Pi by user

---

## Next Steps

**After approval:**
1. Create framebuffer_ui package structure
2. Implement Phase 1 (Core Rendering)
3. Test on Pi Zero 2W hardware
4. Screenshots for visual comparison
5. Submit PR with working prototype

---

## Files

**Full Details:** [`lightweight-ui-architecture.md`](./lightweight-ui-architecture.md) (28KB)  
**This Summary:** [`lightweight-ui-summary.md`](./lightweight-ui-summary.md) (8KB)

---

**Status:** 🟡 Awaiting Approval  
**Timeline:** 3-4 weeks after approval  
**Contact:** Principal Engineer
