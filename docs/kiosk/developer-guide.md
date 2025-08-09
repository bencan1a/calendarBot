# CalendarBot Kiosk Mode - Developer Documentation

**Technical integration guide for developers working with CalendarBot kiosk mode**

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Component Relationships](#component-relationships)
- [Integration with CalendarBot Infrastructure](#integration-with-calendarbot-infrastructure)
- [Configuration System](#configuration-system)
- [Extension Guidelines](#extension-guidelines)
- [Testing Framework](#testing-framework)
- [Performance Optimization](#performance-optimization)
- [API Reference](#api-reference)
- [Development Workflow](#development-workflow)

## Architecture Overview

### System Architecture

CalendarBot kiosk mode is built on a layered architecture optimized for Raspberry Pi Zero 2W constraints:

```
┌─────────────────────────────────────────────────────────┐
│                    Systemd Services                     │
├─────────────────────────────────────────────────────────┤
│  calendarbot-kiosk.service  │  calendarbot-kiosk-setup │
│  calendarbot-network-wait   │  (dependency services)   │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                   Kiosk Manager                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────┐ │
│  │  Startup        │ │   Health        │ │  Process   │ │
│  │  Orchestrator   │ │   Monitor       │ │  Manager   │ │
│  └─────────────────┘ └─────────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                 Browser Manager                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────┐ │
│  │  Process        │ │   Memory        │ │  Crash     │ │
│  │  Lifecycle      │ │   Monitor       │ │  Recovery  │ │
│  └─────────────────┘ └─────────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│              CalendarBot Web Infrastructure              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────┐ │
│  │  Shared Web     │ │   Calendar      │ │  Display   │ │
│  │  Server         │ │   Engine        │ │  Views     │ │
│  └─────────────────┘ └─────────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                   Chromium Browser                      │
│           (Full-screen kiosk mode)                      │
└─────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. KioskManager (`calendarbot/kiosk/manager.py`)

Central orchestrator with 4-phase startup workflow:

```python
from calendarbot.kiosk.manager import KioskManager
from calendarbot.settings.kiosk_models import KioskSettings

class KioskManager:
    """Central kiosk orchestrator with 4-phase startup."""
    
    def __init__(self, settings: KioskSettings):
        self.settings = settings
        self.browser_manager = BrowserManager(settings)
        
    async def start_kiosk(self) -> None:
        """Execute 4-phase startup workflow."""
        await self._phase_1_start_web_server()
        await self._phase_2_wait_for_readiness()
        await self._phase_3_launch_browser()
        await self._phase_4_monitor_health()
```

#### 2. BrowserManager (`calendarbot/kiosk/browser_manager.py`)

Browser process lifecycle management with Pi Zero 2W optimizations:

```python
from calendarbot.kiosk.browser_manager import BrowserManager

class BrowserManager:
    """Chromium browser process management with memory optimization."""
    
    def __init__(self, settings: KioskSettings):
        self.settings = settings
        self.process: Optional[subprocess.Popen] = None
        
    async def launch_browser(self, url: str) -> None:
        """Launch Chromium with Pi Zero 2W optimized flags."""
        flags = self._get_chromium_flags()
        self.process = await self._start_process(flags, url)
        
    def _get_chromium_flags(self) -> List[str]:
        """Get Pi Zero 2W optimized Chromium flags."""
        return [
            '--kiosk',
            '--no-sandbox',
            '--disable-gpu',
            f'--max_old_space_size={self.settings.memory_limit_mb}',
            '--memory-pressure-off',
            '--enable-low-end-device-mode',
            # ... additional optimization flags
        ]
```

#### 3. Settings System (`calendarbot/settings/kiosk_models.py`)

Type-safe configuration with Pydantic models:

```python
from pydantic import BaseModel, Field, validator

class KioskSettings(BaseModel):
    """Complete kiosk configuration with validation."""
    
    display: KioskDisplaySettings = KioskDisplaySettings()
    browser: KioskBrowserSettings = KioskBrowserSettings()
    performance: KioskPerformanceSettings = KioskPerformanceSettings()
    
    @validator('browser')
    def validate_pi_zero_constraints(cls, v):
        if v.memory_limit_mb > 150:
            raise ValueError('Memory limit too high for Pi Zero 2W')
        return v
```

## Component Relationships

### Key Integration Points

1. **Leverages Existing Infrastructure**: Uses CalendarBot's DaemonManager and SharedWebServer
2. **Memory-Constrained Design**: All components optimized for 512MB RAM
3. **Error Recovery**: Exponential backoff restart logic throughout
4. **Health Monitoring**: Continuous monitoring with automatic remediation

### Startup Sequence

```python
async def startup_workflow():
    # Phase 1: Start web infrastructure
    daemon_manager = DaemonManager()
    await daemon_manager.start_web_server()
    
    # Phase 2: Wait for readiness
    await wait_for_web_server(port=8080, timeout=60)
    
    # Phase 3: Launch browser
    browser_manager = BrowserManager(settings)
    await browser_manager.launch_browser("http://localhost:8080/whats-next-view")
    
    # Phase 4: Monitor health
    await start_health_monitoring_loop()
```

## Integration with CalendarBot Infrastructure

### Shared Web Server Integration

```python
from calendarbot.daemon.manager import DaemonManager

class KioskWebIntegration:
    def __init__(self):
        self.daemon_manager = DaemonManager()
        
    async def start_web_server(self) -> None:
        """Start shared web server for kiosk display."""
        await self.daemon_manager.start_shared_web_server()
        await self._verify_kiosk_routes()
```

### CLI Integration

```python
from calendarbot.cli.base import BaseCommand

class KioskCommand(BaseCommand):
    def setup_parser(self, parser):
        parser.add_argument('--kiosk', action='store_true')
        parser.add_argument('--kiosk-setup', action='store_true')
        
    async def handle_kiosk(self, args):
        settings = self.load_kiosk_settings()
        kiosk_manager = KioskManager(settings)
        await kiosk_manager.start_kiosk()
```

## Configuration System

### Pydantic Models

```python
class KioskDisplaySettings(BaseModel):
    resolution: str = Field(default="800x480", regex=r"^\d+x\d+$")
    orientation: str = Field(default="portrait")
    fullscreen: bool = True

class KioskBrowserSettings(BaseModel):
    memory_limit_mb: int = Field(default=80, ge=40, le=200)
    cache_size_mb: int = Field(default=20, ge=5, le=100)
    
    @validator('memory_limit_mb')
    def validate_memory_for_pi_zero(cls, v):
        if v > 150:
            raise ValueError("Memory limit too high for Pi Zero 2W")
        return v

class KioskSettings(BaseModel):
    display: KioskDisplaySettings = KioskDisplaySettings()
    browser: KioskBrowserSettings = KioskBrowserSettings()
```

### Configuration Loading

```python
class KioskConfigurationManager:
    def load_settings(self) -> KioskSettings:
        config_file = Path.home() / '.config' / 'calendarbot' / 'kiosk.yaml'
        if config_file.exists():
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
            return KioskSettings(**config_data)
        return KioskSettings()  # Defaults
```

## Extension Guidelines

### Creating Custom Layouts

```python
from flask import render_template
from calendarbot.web.base import BaseWebView

class CustomKioskLayout(BaseWebView):
    def register_routes(self, app):
        @app.route('/custom-kiosk-view')
        def custom_view():
            events = self._get_kiosk_events()
            return render_template('kiosk/custom.html', 
                                 events=events, kiosk_mode=True)
```

### Adding Kiosk Modules

```python
from abc import ABC, abstractmethod

class KioskModule(ABC):
    @abstractmethod
    async def get_data(self) -> Dict[str, Any]:
        pass

class WeatherModule(KioskModule):
    async def get_data(self) -> Dict[str, Any]:
        # Fetch weather data
        return {'temperature': 22, 'condition': 'sunny'}
```

## Testing Framework

### Unit Tests

```python
# tests/unit/kiosk/test_manager.py
class TestKioskManager:
    @pytest.mark.asyncio
    async def test_startup_workflow(self, mock_settings):
        manager = KioskManager(mock_settings)
        await manager.start_kiosk()
        # Verify all phases completed
```

### Integration Tests

```python
# tests/integration/kiosk/test_pi_zero_constraints.py
class TestPiZeroConstraints:
    @pytest.mark.asyncio
    async def test_memory_limits(self):
        # Verify memory usage stays under Pi Zero 2W limits
        assert memory_usage < 400 * 1024 * 1024  # 400MB
```

## Performance Optimization

### Pi Zero 2W Specific Optimizations

1. **Memory Management**: 80MB browser limit, GPU memory split
2. **CPU Optimization**: 80% quota, process throttling
3. **Storage Optimization**: Cache limits, log rotation
4. **Browser Flags**: Low-end device mode, memory pressure settings

### Monitoring

```python
class MemoryMonitor:
    def __init__(self, limit_mb: int = 80):
        self.limit_bytes = limit_mb * 1024 * 1024
        
    async def check_memory_usage(self) -> bool:
        usage = self._get_browser_memory()
        return usage < self.limit_bytes
```

## API Reference

### Core Classes

- **`KioskManager`**: Central orchestrator
- **`BrowserManager`**: Browser process management  
- **`KioskSettings`**: Configuration model
- **`KioskConfigurationManager`**: Configuration loading/saving

### Key Methods

- **`KioskManager.start_kiosk()`**: Start kiosk mode
- **`BrowserManager.launch_browser(url)`**: Launch browser
- **`BrowserManager.restart_browser()`**: Restart browser process
- **`KioskSettings.validate()`**: Validate configuration

### Configuration Files

- **`~/.config/calendarbot/kiosk.yaml`**: Main kiosk configuration
- **`/boot/config.txt`**: Hardware configuration
- **Service files**: `/etc/systemd/system/calendarbot-kiosk*.service`

## Development Workflow

### Local Development

```bash
# Start kiosk in development mode
./venv/bin/python -m calendarbot --kiosk --debug

# Test configuration
./venv/bin/python -m calendarbot --validate-config

# Run tests
pytest tests/unit/kiosk/ tests/integration/kiosk/
```

### Deployment Process

1. **Install**: `sudo scripts/kiosk/install-calendarbot-kiosk.sh`
2. **Configure**: `./venv/bin/python -m calendarbot --kiosk-setup`
3. **Validate**: `sudo scripts/kiosk/validate-kiosk-installation.sh`
4. **Monitor**: `journalctl -u calendarbot-kiosk.service -f`

### Debugging

```bash
# Check service status
systemctl status calendarbot-kiosk.service

# View logs
journalctl -u calendarbot-kiosk.service --since "1 hour ago"

# Memory diagnostics
./venv/bin/python -m calendarbot --memory-report

# Manual browser test
chromium-browser --kiosk http://localhost:8080/whats-next-view
```

---

This developer documentation provides the essential technical information for integrating with and extending CalendarBot's kiosk mode functionality. For complete implementation details, refer to the source code in [`calendarbot/kiosk/`](../../calendarbot/kiosk/).
