# Architecture Comparison: Current vs. Proposed

## Current Architecture (Heavy)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Raspberry Pi Zero 2W                         │
│                    (512MB RAM, ARM Cortex-A53)                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  systemd boot sequence                                      │ │
│  │                                                              │ │
│  │  1. calendarbot-lite@user.service                          │ │
│  │     └─> Python backend server                   ~30MB RSS │ │
│  │                                                              │ │
│  │  2. Auto-login to tty1                                      │ │
│  │     └─> .bash_profile                                       │ │
│  │         └─> startx                                          │ │
│  │             └─> .xinitrc                                    │ │
│  │                 └─> X11 Server (Xorg)          ~100MB RSS │ │
│  │                     └─> Chromium Browser        ~150MB RSS │ │
│  │                         └─> HTML/CSS/JS         ~10MB RSS │ │
│  │                             └─> Fetch API                   │ │
│  │                                 └─> localhost:8080          │ │
│  │                                                              │ │
│  │  3. calendarbot-kiosk-watchdog@user.service                │ │
│  │     └─> Monitor browser heartbeat              ~5MB RSS   │ │
│  │         ├─> Level 0: Soft reload (F5 key)                  │ │
│  │         ├─> Level 1: Browser restart                       │ │
│  │         └─> Level 2: X session restart                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  TOTAL MEMORY: ~295MB RSS                                       │
│  STARTUP TIME: ~60 seconds                                      │
│  COMPLEXITY: 6 processes, 3-level watchdog                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Current Stack Breakdown

| Component | Memory (RSS) | Purpose | Issues |
|-----------|--------------|---------|--------|
| Backend Server | 30MB | ICS parsing, API server | ✅ Efficient |
| X11 Server | 100MB | Display server | ❌ Heavy, complex |
| Chromium | 150MB | Web browser | ❌ Very heavy, can freeze |
| HTML/CSS/JS | 10MB | UI rendering | ✅ Works but unnecessary |
| Watchdog | 5MB | Health monitoring | ⚠️ Needed due to complexity |
| **TOTAL** | **295MB** | | ❌ Too much for Pi Zero 2W |

---

## Proposed Architecture (Lightweight)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Raspberry Pi Zero 2W                         │
│                    (512MB RAM, ARM Cortex-A53)                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  systemd boot sequence                                      │ │
│  │                                                              │ │
│  │  1. calendarbot-lite@user.service (optional - can be remote)│ │
│  │     └─> Python backend server                   ~30MB RSS │ │
│  │                                                              │ │
│  │  2. calendarbot-display@user.service                        │ │
│  │     └─> Python framebuffer UI                   ~15MB RSS │ │
│  │         ├─> pygame (SDL2 + DRM/KMS)             ~5MB     │ │
│  │         ├─> API client (aiohttp)                ~2MB     │ │
│  │         ├─> Layout engine                       ~3MB     │ │
│  │         └─> Framebuffer (480x800x4)             ~2MB     │ │
│  │             └─> Direct rendering to /dev/fb0 or DRM       │ │
│  │                 └─> Fetch API every 60s                    │ │
│  │                     └─> localhost:8080 OR remote IP        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  TOTAL MEMORY: ~45MB RSS (both services on same Pi)            │
│               ~15MB RSS (backend on different device)          │
│  STARTUP TIME: ~5 seconds                                       │
│  COMPLEXITY: 1-2 processes, no watchdog needed                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed Stack Breakdown

| Component | Memory (RSS) | Purpose | Benefits |
|-----------|--------------|---------|----------|
| Backend Server* | 30MB | ICS parsing, API server | ✅ Can run remotely |
| Framebuffer UI | 15MB | Direct rendering + API client | ✅ Lightweight |
| pygame/SDL2 | 5MB | Graphics rendering | ✅ Hardware accelerated |
| API Client | 2MB | Async HTTP to backend | ✅ Simple |
| **TOTAL** | **45MB*** | | ✅ 84% reduction |

\* Backend optional on same Pi - can run on different device for only 15MB total

---

## Side-by-Side Comparison

### Deployment Scenario A: All on Pi Zero 2W

```
┌──────────────────────┐     ┌──────────────────────┐
│   Current Stack      │     │   Proposed Stack     │
├──────────────────────┤     ├──────────────────────┤
│ X11 Server   100MB   │     │ (eliminated)         │
│ Chromium     150MB   │     │ (eliminated)         │
│ HTML/JS       10MB   │     │ (eliminated)         │
│ Watchdog       5MB   │     │ (eliminated)         │
│ Backend       30MB   │     │ Backend       30MB   │
│                      │     │ Framebuffer   15MB   │
├──────────────────────┤     ├──────────────────────┤
│ TOTAL:      ~295MB   │     │ TOTAL:       ~45MB   │
│ Startup:     ~60s    │     │ Startup:      ~5s    │
└──────────────────────┘     └──────────────────────┘
        ↓                             ↓
   IMPROVEMENT:  84% memory reduction, 12x faster startup
```

### Deployment Scenario B: Backend on Different Device

```
┌──────────────────────────────────────────────────────────┐
│                Pi Zero 2W (Display Only)                 │
├──────────────────────────────────────────────────────────┤
│ Framebuffer UI: 15MB                                     │
│ Startup: ~5s                                             │
└──────────────────────────────────────────────────────────┘
                      │
                      │ HTTP GET /api/whats-next
                      │ every 60 seconds
                      ▼
┌──────────────────────────────────────────────────────────┐
│         Another Device (Pi 4, Desktop, Cloud)            │
├──────────────────────────────────────────────────────────┤
│ calendarbot-lite backend: 30MB                           │
│ ICS parsing, RRULE expansion, API serving                │
└──────────────────────────────────────────────────────────┘

RESULT: Only 15MB on Pi Zero 2W, backend runs on more powerful hardware
```

---

## Visual Rendering Comparison

### Current (Browser-based)

```
┌─────────────────────────────────────────────────────┐
│ Chromium Browser Process                            │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │ HTML DOM Tree                               │    │
│  │   <div class="countdown-container">         │    │
│  │     <div class="countdown-time">9</div>     │    │
│  │   </div>                                    │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
│  ┌────────────────────────────────────────────┐    │
│  │ CSS Style Computation (Blink Engine)        │    │
│  │   - Layout calculation                      │    │
│  │   - Style matching                          │    │
│  │   - Paint layer generation                  │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
│  ┌────────────────────────────────────────────┐    │
│  │ JavaScript Engine (V8)                      │    │
│  │   - API polling (fetch)                     │    │
│  │   - DOM manipulation                        │    │
│  │   - Event handling                          │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
│  ┌────────────────────────────────────────────┐    │
│  │ Compositor                                  │    │
│  │   - Layer compositing                       │    │
│  │   - GPU acceleration                        │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
└───────────┼─────────────────────────────────────────┘
            ↓
┌───────────────────────────────────────────────────┐
│ X11 Server                                        │
│   - Window management                              │
│   - Coordinate transformation                      │
│   - Pixmap rendering                               │
└───────────┼───────────────────────────────────────┘
            ↓
┌───────────────────────────────────────────────────┐
│ Linux Kernel DRM/KMS                              │
│   - Mode setting                                   │
│   - Framebuffer allocation                         │
└───────────┼───────────────────────────────────────┘
            ↓
        [Display]

COMPLEXITY: 5+ layers of abstraction
MEMORY: ~260MB for rendering stack alone
```

### Proposed (Direct Framebuffer)

```
┌─────────────────────────────────────────────────────┐
│ Python Framebuffer UI Process                       │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │ API Response (dict)                         │    │
│  │   {                                         │    │
│  │     "meeting": {...},                       │    │
│  │     "seconds_until_start": 35820            │    │
│  │   }                                         │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
│  ┌────────────────────────────────────────────┐    │
│  │ Layout Engine (Python)                      │    │
│  │   - Calculate countdown display             │    │
│  │   - Format time strings                     │    │
│  │   - Determine visual state                  │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
│  ┌────────────────────────────────────────────┐    │
│  │ pygame Renderer (SDL2)                      │    │
│  │   - Draw rectangles (zones)                 │    │
│  │   - Render TTF text                         │    │
│  │   - Apply colors                            │    │
│  └────────────────────────────────────────────┘    │
│           ↓                                          │
└───────────┼─────────────────────────────────────────┘
            ↓
┌───────────────────────────────────────────────────┐
│ SDL2 Video Backend (kmsdrm or fbcon)             │
│   - Direct buffer write                            │
└───────────┼───────────────────────────────────────┘
            ↓
┌───────────────────────────────────────────────────┐
│ Linux Kernel DRM/KMS or /dev/fb0                  │
│   - Hardware framebuffer                           │
└───────────┼───────────────────────────────────────┘
            ↓
        [Display]

COMPLEXITY: 2 layers (Python app + SDL2 backend)
MEMORY: ~15MB total
```

---

## Reliability Comparison

### Current System Failure Points

```
Boot → systemd
  │
  ├─> calendarbot-lite service
  │   └─> ✅ Backend (reliable)
  │
  ├─> Auto-login → .bash_profile → startx
  │   ├─> ❌ X server can fail (crash, config issues)
  │   └─> ❌ Chromium can freeze/crash
  │       └─> 🩹 Watchdog Level 0: Soft reload (F5)
  │           └─> 🩹 Watchdog Level 1: Browser restart
  │               └─> 🩹 Watchdog Level 2: X restart
  │
  └─> calendarbot-watchdog service
      └─> ⚠️ Complex recovery logic needed

FAILURE MODES: 3+ (X crash, browser freeze, JS error)
RECOVERY: 3-level progressive escalation
MTBF: Days to weeks (browser stability issues)
```

### Proposed System Failure Points

```
Boot → systemd
  │
  ├─> calendarbot-lite service (optional - can be remote)
  │   └─> ✅ Backend (reliable)
  │
  └─> calendarbot-display service
      └─> ✅ Python UI (simple, single process)
          └─> systemd auto-restart on crash

FAILURE MODES: 1 (Python process crash)
RECOVERY: systemd automatic restart (built-in)
MTBF: Weeks to months (Python stability)
```

---

## Performance Metrics

### Memory Pressure on Pi Zero 2W (512MB RAM)

```
┌────────────────────────────────────────────────────┐
│ Current System Memory Usage                        │
├────────────────────────────────────────────────────┤
│ System (kernel, init, etc)      150MB              │
│ CalendarBot stack                295MB              │
│ Available for other processes     67MB              │
├────────────────────────────────────────────────────┤
│ TOTAL RAM                        512MB              │
│ Memory Pressure: HIGH ⚠️                           │
│ Swapping: LIKELY ⚠️                                │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ Proposed System Memory Usage                       │
├────────────────────────────────────────────────────┤
│ System (kernel, init, etc)      150MB              │
│ CalendarBot stack                 45MB (or 15MB)   │
│ Available for other processes    317MB (or 347MB)  │
├────────────────────────────────────────────────────┤
│ TOTAL RAM                        512MB              │
│ Memory Pressure: LOW ✅                            │
│ Swapping: UNLIKELY ✅                              │
└────────────────────────────────────────────────────┘

IMPROVEMENT: 250MB (53%) more free memory
```

### Startup Sequence Timing

```
Current System:
──────────────────────────────────────────────────────────────>
0s      10s     20s     30s     40s     50s     60s     70s
├───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│       │       │       │       │       │       │       │
└─ Boot ────┬─── X11 starts ───┬─── Chromium ──┬─ Page loads
            │                  │               │
            └─ ~15s delay      └─ ~30s delay  └─ ~15s delay
                                                      ▲
                                                  Display Ready
                                            TOTAL: ~60 seconds

Proposed System:
────────────────────>
0s      5s      10s
├───────┼───────┤
│       │       │
└─ Boot ─┬─ UI starts ─▲
         │             │
         └─ ~3s delay  └─ Display Ready
                  TOTAL: ~5 seconds

IMPROVEMENT: 12x faster (55 seconds saved)
```

---

## Code Complexity Comparison

### Current: HTML + CSS + JS
- **Files:** 3 (whatsnext.html, whatsnext.css, whatsnext.js)
- **Lines of Code:** ~1000 lines total
- **Technologies:** HTML5, CSS3, JavaScript ES6+
- **Dependencies:** Browser runtime (Chromium)
- **State Management:** JavaScript in-memory
- **API Client:** Fetch API with retry logic

### Proposed: Python + pygame
- **Files:** ~5 (main.py, renderer.py, api_client.py, layout_engine.py, config.py)
- **Lines of Code:** ~800 lines estimated
- **Technologies:** Python 3.12, pygame 2.5+
- **Dependencies:** pygame (~5MB)
- **State Management:** Python dataclasses
- **API Client:** aiohttp with retry logic

**Simplicity:** Similar code complexity, but no browser/X11 overhead

---

## Development & Testing

### Current Development Cycle
1. Edit HTML/CSS/JS
2. Reload browser (can use dev tools)
3. Test on Pi (deploy files)
4. Debug browser console
5. Check watchdog behavior

### Proposed Development Cycle
1. Edit Python code
2. Run locally with mock backend
3. Test on Pi (systemctl restart)
4. Debug Python logs
5. No watchdog needed

**Advantage:** Faster iteration, simpler debugging

---

## Conclusion

The proposed pygame-based framebuffer UI offers:

✅ **84% memory reduction** (295MB → 45MB on same Pi)  
✅ **94% reduction** (260MB → 15MB with remote backend)  
✅ **12x faster startup** (60s → 5s)  
✅ **Simpler architecture** (no X11, no browser, no watchdog)  
✅ **More reliable** (fewer failure points)  
✅ **Pixel-perfect visual match** to current design  
✅ **Remote backend support** (backend can run elsewhere)  
✅ **Lower complexity** (2 processes vs 6+)  
✅ **Better Pi Zero 2W fit** (low resource usage)

**Recommendation:** Proceed with implementation using pygame + DRM/KMS framebuffer approach.
