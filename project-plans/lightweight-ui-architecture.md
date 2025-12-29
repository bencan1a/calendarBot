# Lightweight UI Architecture Plan for CalendarBot Pi Zero 2W

**Date:** 2025-12-29  
**Status:** Architecture Planning Phase  
**Target Platform:** Raspberry Pi Zero 2W (512MB RAM, ARM Cortex-A53)

---

## Executive Summary

This document proposes a lightweight framebuffer-based UI for CalendarBot that eliminates the heavy dependencies of X Windows and Chromium browser (~200MB+ RAM overhead), replacing them with a minimal Python-based direct rendering solution (~10-20MB RAM overhead).

**Key Goals:**
1. Eliminate X11 and browser dependencies (~200MB RAM reduction)
2. Maintain visual fidelity to current HTML/CSS design
3. Reduce system complexity and failure points
4. Improve startup time and resource efficiency
5. Enable the backend server to run on a different device

---

## Current Architecture Analysis

### Current Stack (Heavy)
```
Pi Zero 2W → X11 Server → Chromium Browser → HTML/CSS/JS → Backend API
              (~100MB)     (~150MB)           (~10MB)      (localhost:8080)
Total RAM: ~260MB + system overhead
```

**Pain Points:**
- X11 server: heavyweight, complex configuration
- Chromium: massive memory footprint, can freeze/crash
- Browser stack: unnecessary overhead for static display
- Watchdog complexity: 3-level progressive recovery needed

### Proposed Stack (Lightweight)
```
Pi Zero 2W → Python Framebuffer UI → Backend API
              (~10-20MB)              (remote/local)
Total RAM: ~30-50MB including Python runtime
```

**Benefits:**
- No X11, no browser, no watchdog needed
- Direct framebuffer rendering (DRM/KMS or /dev/fb0)
- Simple systemd service with auto-restart
- Backend can run on different device
- Faster startup (<5s vs ~60s)

---

## Architecture Options Evaluated

### Option 1: Pygame Framebuffer (RECOMMENDED)
**Technology:** Python + pygame + SDL2 framebuffer backend

**Pros:**
- ✅ Pure Python, no compilation needed
- ✅ Pygame well-maintained, stable API
- ✅ Hardware-accelerated rendering where available
- ✅ TTF font support built-in
- ✅ No X11 required (SDL_VIDEODRIVER=kmsdrm or fbcon)
- ✅ Straightforward API for 2D graphics

**Cons:**
- ⚠️ Pygame dependency (~5MB installed)
- ⚠️ SDL2 system dependency (usually pre-installed on Pi OS)

**Memory Estimate:** 10-15MB RSS

**Implementation Complexity:** Low

---

### Option 2: Direct Framebuffer with PIL/Pillow
**Technology:** Python + Pillow + direct /dev/fb0 writes

**Pros:**
- ✅ Minimal dependencies (Pillow commonly available)
- ✅ Full control over rendering
- ✅ Lightest possible footprint

**Cons:**
- ⚠️ Manual framebuffer management (complex)
- ⚠️ No hardware acceleration
- ⚠️ Need to handle pixel formats manually
- ⚠️ More fragile across different Pi models

**Memory Estimate:** 8-12MB RSS

**Implementation Complexity:** High

---

### Option 3: Pygame Zero + PaperTTY Style
**Technology:** Python + pygame-zero + custom rendering

**Pros:**
- ✅ Simplified pygame API
- ✅ Good for static displays

**Cons:**
- ⚠️ Still based on pygame (same footprint)
- ⚠️ Less flexible than raw pygame

**Memory Estimate:** 12-18MB RSS

**Implementation Complexity:** Low-Medium

---

### Option 4: Custom Framebuffer Library (e.g., fbpy)
**Technology:** Python + custom framebuffer library

**Pros:**
- ✅ Potentially very lightweight

**Cons:**
- ❌ Unmaintained libraries
- ❌ Limited font support
- ❌ Compatibility issues

**Memory Estimate:** 8-12MB RSS

**Implementation Complexity:** High

---

### Option 5: Terminal UI (blessed/curses)
**Technology:** Python + blessed/rich terminal UI

**Pros:**
- ✅ Extremely lightweight
- ✅ No graphics stack needed
- ✅ Works over SSH

**Cons:**
- ❌ Cannot replicate current visual design
- ❌ ASCII-only, no proper fonts/sizing
- ❌ Poor user experience for kiosk display

**Implementation Complexity:** Low

**Verdict:** Not suitable for user-facing kiosk display

---

## Recommended Approach: Pygame Framebuffer

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi Zero 2W                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         CalendarBot Framebuffer UI (Python)          │  │
│  │                                                        │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │  │
│  │  │   Render    │  │  API Client  │  │   Layout    │ │  │
│  │  │   Engine    │  │              │  │   Engine    │ │  │
│  │  │  (pygame)   │  │  (aiohttp)   │  │             │ │  │
│  │  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘ │  │
│  │         │                │                 │         │  │
│  │         └────────────────┴─────────────────┘         │  │
│  │                          │                            │  │
│  │                ┌─────────▼─────────┐                 │  │
│  │                │  Event Loop       │                 │  │
│  │                │  (asyncio)        │                 │  │
│  │                └─────────┬─────────┘                 │  │
│  └──────────────────────────┼──────────────────────────┘  │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │   DRM/KMS or      │                   │
│                    │   /dev/fb0        │                   │
│                    │   (Framebuffer)   │                   │
│                    └─────────┬─────────┘                   │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │   HDMI Display    │                   │
│                    └───────────────────┘                   │
│                                                              │
│  Network: HTTP GET /api/whats-next → Backend Server        │
│           (localhost:8080 or remote IP)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Design

### 1. Core Components

#### 1.1 Render Engine (pygame-based)
```python
class FramebufferRenderer:
    """Direct framebuffer rendering using pygame.
    
    Responsibilities:
    - Initialize pygame with framebuffer backend
    - Render countdown timer with large fonts
    - Render meeting card with title/time/location
    - Render bottom status section
    - Handle screen updates efficiently
    """
    
    def __init__(self, width=480, height=800):
        # Initialize pygame with framebuffer
        os.environ['SDL_VIDEODRIVER'] = 'kmsdrm'  # or 'fbcon'
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        
    def render_countdown(self, value, units, label):
        """Render countdown section (top 300px)."""
        
    def render_meeting_card(self, title, time, location):
        """Render meeting details (middle 400px)."""
        
    def render_bottom_status(self, message):
        """Render status message (bottom 100px)."""
        
    def update_display(self):
        """Push rendered frame to display."""
        pygame.display.flip()
```

#### 1.2 API Client
```python
class CalendarAPIClient:
    """Async HTTP client for backend API.
    
    Responsibilities:
    - Poll /api/whats-next endpoint every 60 seconds
    - Handle network errors gracefully
    - Parse JSON response
    - Maintain connection state
    """
    
    async def fetch_whats_next(self, base_url: str) -> dict:
        """Fetch next meeting from backend API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/whats-next") as resp:
                return await resp.json()
```

#### 1.3 Layout Engine
```python
class LayoutEngine:
    """Convert API data to visual layout.
    
    Responsibilities:
    - Parse API response
    - Calculate countdown display
    - Format time strings
    - Apply visual state (normal/warning/critical)
    """
    
    def calculate_countdown_display(self, seconds_until: int) -> dict:
        """Convert seconds_until_start to display format."""
        hours = seconds_until // 3600
        minutes = (seconds_until % 3600) // 60
        
        return {
            'value': hours if hours > 0 else minutes,
            'primary_unit': 'HOURS' if hours > 0 else 'MINUTES',
            'secondary': f'{minutes} MINUTES' if hours > 0 else '',
            'state': 'critical' if seconds_until < 300 else 'normal'
        }
```

#### 1.4 Main Application
```python
class CalendarKioskApp:
    """Main application coordinator.
    
    Responsibilities:
    - Initialize all components
    - Run main event loop
    - Coordinate API polling and rendering
    - Handle graceful shutdown
    """
    
    async def run(self):
        """Main event loop."""
        while self.running:
            # Fetch data from API
            data = await self.api_client.fetch_whats_next()
            
            # Calculate layout
            layout = self.layout_engine.process(data)
            
            # Render to screen
            self.renderer.render_full_screen(layout)
            
            # Process pygame events (for clean exit)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # Wait before next update
            await asyncio.sleep(60)
```

---

### 2. Visual Design Replication

The goal is to **exactly replicate** the current HTML/CSS visual design using pygame drawing primitives.

#### 2.1 Layout Zones
```
┌─────────────────────────────────┐
│   Zone 1: Countdown Timer       │  300px
│   - Gray background             │
│   - Large centered number       │
│   - Unit labels                 │
├─────────────────────────────────┤
│   Zone 2: Meeting Card          │  400px
│   - White background            │
│   - Meeting title (large)       │
│   - Time range                  │
│   - Location (optional)         │
├─────────────────────────────────┤
│   Zone 3: Status Message        │  100px
│   - Gray background             │
│   - Centered text               │
└─────────────────────────────────┘
Total: 480x800 pixels
```

#### 2.2 Typography
```python
# Font definitions (matching CSS)
FONTS = {
    'countdown_label': pygame.font.SysFont('sans-serif', 21, bold=False),   # 21px, medium
    'countdown_value': pygame.font.SysFont('sans-serif', 78, bold=True),    # 78px, weight 900
    'countdown_units': pygame.font.SysFont('sans-serif', 18, bold=False),   # 18px, medium
    'meeting_title': pygame.font.SysFont('sans-serif', 40, bold=True),      # 2.5rem = 40px
    'meeting_time': pygame.font.SysFont('sans-serif', 18, bold=False),      # 18px, medium
    'meeting_location': pygame.font.SysFont('sans-serif', 14, bold=False),  # 14px
    'status_message': pygame.font.SysFont('sans-serif', 32, bold=False),    # 32px
}
```

#### 2.3 Color Palette (8-shade grayscale)
```python
# Exact match to CSS variables
COLORS = {
    'gray-1': (255, 255, 255),  # #ffffff - white
    'gray-2': (247, 247, 247),  # #f7f7f7
    'gray-3': (229, 229, 229),  # #e5e5e5
    'gray-4': (204, 204, 204),  # #cccccc
    'gray-5': (153, 153, 153),  # #999999
    'gray-6': (102, 102, 102),  # #666666
    'gray-7': (51, 51, 51),     # #333333
    'gray-8': (0, 0, 0),        # #000000 - black
}
```

#### 2.4 Rendering Functions
```python
def render_countdown_section(screen, data):
    """Render top countdown section (300px)."""
    # Background
    pygame.draw.rect(screen, COLORS['gray-2'], (0, 0, 480, 300))
    
    # Countdown container (rounded rect)
    container_rect = pygame.Rect(60, 50, 360, 200)  # Centered, 70% width
    pygame.draw.rect(screen, COLORS['gray-3'], container_rect, border_radius=12)
    pygame.draw.rect(screen, COLORS['gray-4'], container_rect, width=1, border_radius=12)
    
    # "STARTS IN" label
    label = FONTS['countdown_label'].render('STARTS IN', True, COLORS['gray-6'])
    screen.blit(label, (240 - label.get_width()//2, 70))
    
    # Large countdown number
    value_text = str(data['countdown_value'])
    value = FONTS['countdown_value'].render(value_text, True, COLORS['gray-8'])
    screen.blit(value, (240 - value.get_width()//2, 110))
    
    # Units
    units = FONTS['countdown_units'].render(data['countdown_units'], True, COLORS['gray-6'])
    screen.blit(units, (240 - units.get_width()//2, 200))
    
    if data.get('countdown_secondary'):
        secondary = FONTS['countdown_units'].render(data['countdown_secondary'], True, COLORS['gray-6'])
        screen.blit(secondary, (240 - secondary.get_width()//2, 220))

def render_meeting_card(screen, data):
    """Render middle meeting card section (400px)."""
    # Background
    pygame.draw.rect(screen, COLORS['gray-1'], (0, 300, 480, 400))
    
    # Card container (rounded rect with shadow)
    card_rect = pygame.Rect(40, 350, 400, 300)
    pygame.draw.rect(screen, COLORS['gray-1'], card_rect, border_radius=8)
    pygame.draw.rect(screen, COLORS['gray-4'], card_rect, width=1, border_radius=8)
    
    # Meeting title (large, centered, word-wrapped)
    title_font = FONTS['meeting_title']
    title_lines = wrap_text(data['meeting_title'], title_font, 360)
    y_offset = 380
    for line in title_lines:
        text = title_font.render(line, True, COLORS['gray-8'])
        screen.blit(text, (240 - text.get_width()//2, y_offset))
        y_offset += 50
    
    # Meeting time
    time_text = FONTS['meeting_time'].render(data['meeting_time'], True, COLORS['gray-6'])
    screen.blit(time_text, (240 - time_text.get_width()//2, y_offset + 10))
    
    # Meeting location (if present)
    if data.get('meeting_location'):
        loc_text = FONTS['meeting_location'].render(data['meeting_location'], True, COLORS['gray-5'])
        screen.blit(loc_text, (240 - loc_text.get_width()//2, y_offset + 40))

def render_bottom_status(screen, message):
    """Render bottom status section (100px)."""
    # Background
    pygame.draw.rect(screen, COLORS['gray-3'], (0, 700, 480, 100))
    
    # Centered status message
    status_font = FONTS['status_message']
    text = status_font.render(message, True, COLORS['gray-7'])
    screen.blit(text, (240 - text.get_width()//2, 730))
```

---

### 3. Deployment Architecture

#### 3.1 File Structure
```
/opt/calendarbot/
├── calendarbot_lite/           # Existing backend code
│   └── ...
├── framebuffer_ui/             # NEW: Lightweight UI
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── renderer.py             # Pygame rendering
│   ├── api_client.py           # Backend API client
│   ├── layout_engine.py        # Layout calculations
│   ├── config.py               # UI configuration
│   └── fonts/                  # TTF font files (optional)
└── venv/                       # Python virtualenv
```

#### 3.2 systemd Service
```ini
# /etc/systemd/system/calendarbot-display@.service
[Unit]
Description=CalendarBot Framebuffer Display for %i
After=network-online.target
Wants=network-online.target
# Optional: require backend on same machine
# Requires=calendarbot-lite@%i.service
# After=calendarbot-lite@%i.service

[Service]
Type=simple
User=%i
Environment="SDL_VIDEODRIVER=kmsdrm"
Environment="SDL_FBDEV=/dev/fb0"
Environment="CALENDARBOT_BACKEND_URL=http://localhost:8080"
WorkingDirectory=/home/%i/calendarbot
ExecStart=/home/%i/calendarbot/venv/bin/python -m framebuffer_ui.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 3.3 Configuration File
```yaml
# /home/user/.config/calendarbot-display/config.yaml
display:
  width: 480
  height: 800
  rotation: 0  # 0, 90, 180, 270

backend:
  url: "http://localhost:8080"  # or remote IP
  timeout: 10
  retry_attempts: 3

refresh:
  interval: 60  # seconds
  fast_mode_threshold: 300  # faster updates when meeting <5min away
  fast_mode_interval: 10  # seconds

fonts:
  # Use system fonts or custom TTF paths
  sans_serif: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
  sans_serif_bold: "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

logging:
  level: "INFO"
  file: "/var/log/calendarbot-display.log"
```

---

### 4. Implementation Phases

#### Phase 1: Core Rendering (Week 1)
- [ ] Set up framebuffer_ui package structure
- [ ] Implement FramebufferRenderer with pygame
- [ ] Create render functions for all 3 zones
- [ ] Test static rendering with mock data
- [ ] Verify visual match to current HTML/CSS design

**Deliverables:**
- Working pygame framebuffer renderer
- Pixel-perfect visual match to current design
- Screenshot comparison tests

---

#### Phase 2: API Integration (Week 1-2)
- [ ] Implement CalendarAPIClient
- [ ] Add LayoutEngine for data transformation
- [ ] Integrate async event loop
- [ ] Add error handling and retries
- [ ] Test with live backend API

**Deliverables:**
- Full API integration
- Live data updates every 60 seconds
- Graceful error handling

---

#### Phase 3: Configuration & Deployment (Week 2)
- [ ] Add YAML configuration support
- [ ] Create systemd service file
- [ ] Write installation script
- [ ] Test on Pi Zero 2W hardware
- [ ] Benchmark memory usage
- [ ] Create documentation

**Deliverables:**
- Automated installer
- systemd service configuration
- User documentation
- Performance benchmarks

---

#### Phase 4: Feature Parity (Week 3)
- [ ] Add fast refresh mode (<5min warning)
- [ ] Implement visual state changes (normal/warning/critical)
- [ ] Add connection status indicator
- [ ] Handle "no meetings" state
- [ ] Add graceful shutdown on SIGTERM

**Deliverables:**
- Feature-complete implementation
- All current UI features replicated
- Smooth graceful shutdown

---

#### Phase 5: Testing & Polish (Week 3-4)
- [ ] Unit tests for all components
- [ ] Integration tests with mock backend
- [ ] End-to-end tests on real hardware
- [ ] Performance optimization
- [ ] Memory leak testing
- [ ] Final documentation

**Deliverables:**
- Comprehensive test suite
- Performance validation
- Production-ready release

---

### 5. Dependencies

#### 5.1 Required Python Packages
```python
# Minimal dependencies
dependencies = [
    "pygame>=2.5.0",        # Framebuffer rendering (~5MB)
    "aiohttp>=3.8.0",       # Async HTTP client (already in project)
    "PyYAML>=6.0",          # Config file parsing (already in project)
    "python-dateutil>=2.8.0",  # Time formatting (already in project)
]
```

**Total New Dependencies:** 1 (pygame)

#### 5.2 System Dependencies (Raspberry Pi OS)
```bash
# SDL2 libraries (usually pre-installed)
sudo apt-get install -y \
    libsdl2-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libsdl2-image-2.0-0

# DRM/KMS support (for SDL_VIDEODRIVER=kmsdrm)
sudo apt-get install -y \
    libdrm2 \
    libgbm1

# Framebuffer support (alternative to DRM)
# Usually built into kernel, no extra packages needed
```

**Estimated Install Size:** ~10MB (SDL2 libraries)

---

### 6. Performance Targets

#### 6.1 Memory Usage
| Component | Target | Max Acceptable |
|-----------|--------|----------------|
| Python Runtime | 5MB | 8MB |
| Pygame | 5MB | 10MB |
| Application Code | 3MB | 5MB |
| Framebuffer | 2MB | 3MB |
| **Total RSS** | **15MB** | **25MB** |

**Comparison to Current:**
- Current: ~260MB (X11 + Chromium + backend)
- Proposed: ~15MB (UI only) + backend (on same or different device)
- **Savings: ~245MB** (94% reduction)

#### 6.2 Startup Time
| Metric | Target | Max Acceptable |
|--------|--------|----------------|
| Service Start | 2s | 5s |
| First Frame | 3s | 7s |
| First API Call | 4s | 10s |
| **Total Ready** | **5s** | **15s** |

**Comparison to Current:**
- Current: ~60s (X11 startup + Chromium launch + page load)
- Proposed: ~5s
- **Improvement: 12x faster startup**

#### 6.3 CPU Usage
| State | Target | Max Acceptable |
|-------|--------|----------------|
| Idle (no updates) | <1% | <2% |
| Rendering Update | <5% | <10% |
| API Fetch | <2% | <5% |
| **Average** | **<2%** | **<5%** |

---

### 7. Migration Strategy

#### 7.1 Backward Compatibility
The new framebuffer UI will be a **separate systemd service** that can run alongside or replace the current X11/Chromium kiosk:

```bash
# Option A: Run new UI alongside old (testing)
sudo systemctl start calendarbot-lite@user.service    # Backend
sudo systemctl start calendarbot-display@user.service # New UI
# Old X11 kiosk disabled

# Option B: Complete migration
sudo systemctl disable auto-login-x-session           # Disable old
sudo systemctl enable calendarbot-display@user.service # Enable new
```

#### 7.2 Rollback Plan
If issues arise, users can easily revert:

```bash
# Rollback to X11/Chromium kiosk
sudo systemctl disable calendarbot-display@user.service
sudo systemctl enable auto-login-x-session
sudo reboot
```

#### 7.3 Testing Period
- Deploy new UI as **opt-in beta** for 2-4 weeks
- Collect feedback and performance data
- Fix issues before making it default
- Maintain old kiosk system as fallback

---

### 8. Risk Assessment

#### 8.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| pygame framebuffer not working on Pi | Low | High | Test early on real hardware; fallback to PIL |
| Font rendering issues | Medium | Low | Bundle TTF fonts with package |
| SDL2 compatibility problems | Low | Medium | Document required SDL2 version |
| Network latency to remote backend | Low | Low | Add connection timeout and retry logic |
| Memory leaks in pygame | Low | Medium | Regular testing with memory profiler |

#### 8.2 Deployment Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| User configuration errors | Medium | Low | Provide sane defaults and validation |
| systemd service conflicts | Low | Low | Unique service names, proper dependencies |
| Permission issues (framebuffer) | Medium | Medium | Document udev rules for /dev/fb0 access |
| Breaking changes to backend API | Low | High | Version API responses, add compatibility layer |

---

### 9. Success Criteria

The lightweight UI implementation will be considered successful if:

1. ✅ **Memory Usage:** <25MB RSS (vs. current ~260MB)
2. ✅ **Startup Time:** <15s to first frame (vs. current ~60s)
3. ✅ **Visual Fidelity:** Pixel-accurate match to current HTML/CSS design
4. ✅ **Stability:** Runs 24/7 without crashes for 1+ week
5. ✅ **CPU Usage:** <5% average on Pi Zero 2W
6. ✅ **Remote Backend:** Successfully connects to backend on different device
7. ✅ **Feature Parity:** All current kiosk features replicated
8. ✅ **User Acceptance:** Positive feedback from initial testers

---

### 10. Future Enhancements (Out of Scope)

These features are **not included** in the initial implementation but could be added later:

- **Touch Support:** Handle touch events for skip button (would need input device handling)
- **Multiple Views:** Switch between "What's Next" and "Morning Summary"
- **Animations:** Smooth transitions between meetings
- **Screensaver Mode:** Dim display after inactivity
- **Multi-Monitor:** Support multiple displays
- **Rotation Support:** Auto-rotate for portrait/landscape
- **Theme Support:** Dark mode, custom color schemes
- **WiFi Status:** Display connection status icon
- **QR Code Display:** Show meeting join links as QR codes

---

## 11. Open Questions for Review

Before proceeding with implementation, please provide feedback on:

1. **Technology Choice:** Is pygame the right choice, or prefer direct PIL framebuffer?
2. **Deployment Model:** Should backend always run on same Pi, or allow remote backend?
3. **Configuration Approach:** YAML file vs. environment variables vs. both?
4. **Skip Button:** Current UI has skip button (touch). Framebuffer UI is read-only. Acceptable?
5. **Font Handling:** Bundle TTF fonts or rely on system fonts?
6. **Backward Compatibility:** Should old X11 kiosk remain available as fallback?
7. **Fast Refresh Mode:** Keep 60s polling, or add faster updates when meeting is imminent?
8. **Error Display:** Show connection errors on screen or just log them?
9. **Installation Method:** Integrated into existing install-kiosk.sh or separate script?
10. **Testing Requirements:** Unit tests only, or also E2E tests on real Pi hardware?

---

## 12. Next Steps After Approval

Once this architecture plan is approved:

1. Create `framebuffer_ui` package structure
2. Implement Phase 1 (Core Rendering) with pygame
3. Test rendering on Pi Zero 2W hardware
4. Take screenshots for visual comparison
5. Proceed to Phase 2 (API Integration)
6. Create PR with working prototype for review

**Estimated Timeline:** 3-4 weeks for full implementation and testing

---

## Appendix A: Pygame Setup for Framebuffer

### A.1 SDL Environment Variables
```bash
# Option 1: DRM/KMS (modern, hardware-accelerated)
export SDL_VIDEODRIVER=kmsdrm
export SDL_VIDEO_KMSDRM_DEVICE=/dev/dri/card0

# Option 2: Framebuffer (legacy, compatible)
export SDL_VIDEODRIVER=fbcon
export SDL_FBDEV=/dev/fb0
export SDL_VIDEODRIVER_FBCON_DEVICE=/dev/fb0

# Disable mouse cursor
export SDL_NOMOUSE=1
```

### A.2 udev Rules for Framebuffer Access
```bash
# /etc/udev/rules.d/99-framebuffer.rules
SUBSYSTEM=="graphics", KERNEL=="fb0", MODE="0660", GROUP="video"
SUBSYSTEM=="drm", KERNEL=="card0", MODE="0660", GROUP="video"

# Add user to video group
sudo usermod -a -G video $USER
```

### A.3 Test Pygame Framebuffer
```python
#!/usr/bin/env python3
"""Test pygame framebuffer rendering."""
import os
import pygame

# Set framebuffer mode
os.environ['SDL_VIDEODRIVER'] = 'kmsdrm'
os.environ['SDL_NOMOUSE'] = '1'

pygame.init()
screen = pygame.display.set_mode((480, 800))

# Fill screen with red
screen.fill((255, 0, 0))
pygame.display.flip()

# Wait 5 seconds
pygame.time.wait(5000)

pygame.quit()
```

---

## Appendix B: Alternative Rendering Libraries

### B.1 Direct Framebuffer (PIL)
```python
from PIL import Image, ImageDraw, ImageFont
import mmap
import os

# Open framebuffer
fb = os.open('/dev/fb0', os.O_RDWR)
fb_map = mmap.mmap(fb, 480*800*4, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

# Create PIL image
img = Image.new('RGB', (480, 800), color='white')
draw = ImageDraw.Draw(img)

# Draw text
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40)
draw.text((240, 400), 'Hello CalendarBot', font=font, fill='black', anchor='mm')

# Write to framebuffer
fb_map.write(img.tobytes())
fb_map.close()
os.close(fb)
```

### B.2 Graphics Library Comparison

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **pygame** | Clean API, hardware accel, active | ~5MB dependency | ✅ **Recommended** |
| **PIL/Pillow** | Common dependency, simple | Manual fb management, no accel | ⚠️ Fallback option |
| **cairo** | Professional graphics, PDF export | Heavy, complex | ❌ Too heavy |
| **tkinter** | Stdlib, no deps | Requires X11 | ❌ Defeats purpose |
| **curses** | Ultra-lightweight | ASCII only | ❌ Poor UX |

---

## Appendix C: Memory Profiling

### C.1 Profile Memory Usage
```bash
# Install memory profiler
pip install memory_profiler

# Profile the application
python -m memory_profiler framebuffer_ui/main.py

# Monitor RSS over time
watch -n 5 "ps aux | grep framebuffer_ui | grep -v grep"
```

### C.2 Expected Memory Breakdown
```
Component                RSS     Details
----------------------------------------------
Python Interpreter       5 MB    Base Python 3.12 runtime
pygame                   5 MB    SDL2 + pygame bindings
Application Code         3 MB    framebuffer_ui modules
aiohttp                  2 MB    HTTP client library
Framebuffer              2 MB    480x800x4 = 1.5MB buffer
Fonts (cached)           1 MB    Rendered font glyphs
----------------------------------------------
TOTAL                   18 MB    Well under 25MB target
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-29 | Principal Engineer | Initial architecture plan |

---

**END OF DOCUMENT**
