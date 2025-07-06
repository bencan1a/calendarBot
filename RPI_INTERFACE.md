# Raspberry Pi E-ink Interface

The CalendarBot now includes specialized support for Raspberry Pi e-ink displays with 800x480px resolution. This interface is optimized for e-ink displays with enhanced contrast, touch-friendly navigation, and component-based layout design.

## Features

- **800x480px Optimized Layout**: Fixed viewport specifically designed for common e-ink display dimensions
- **E-ink Optimized Theme**: High contrast black/white design with optimized fonts and spacing
- **Component-based Event Cards**: Clean, structured event display with optimal readability
- **Touch-friendly Navigation**: Large buttons and interactive elements for touch interaction
- **Efficient Rendering**: Minimized DOM updates for faster e-ink refresh cycles
- **Theme Switching**: Seamless switching between standard, e-ink, and RPI themes

## Quick Start

### Command Line Usage

Enable RPI mode with the `--rpi` flag:

```bash
# Basic RPI mode with web interface
python main.py --web --rpi

# RPI mode with custom dimensions
python main.py --web --rpi --rpi-width 800 --rpi-height 480

# RPI mode with specific port
python main.py --web --rpi --port 3000
```

### Configuration File

Add RPI settings to your `config/config.yaml`:

```yaml
# Display settings
display_type: "rpi"

# RPI-specific configuration
rpi:
  enabled: true
  display_width: 800
  display_height: 480
  refresh_mode: "partial"  # or "full"
  auto_theme: true

# Web server settings
web:
  enabled: true
  port: 8080
  theme: "eink-rpi"
```

## Configuration Options

### Display Settings

- **`display_type`**: Set to `"rpi"` to enable RPI HTML renderer
- **`rpi_enabled`**: Boolean flag to enable RPI optimizations
- **`rpi_display_width`**: Display width in pixels (default: 800)
- **`rpi_display_height`**: Display height in pixels (default: 480)
- **`rpi_refresh_mode`**: E-ink refresh mode (`"partial"` or `"full"`)
- **`rpi_auto_theme`**: Automatically use e-ink optimized theme

### Command Line Arguments

```bash
--rpi, --rpi-mode          Enable Raspberry Pi e-ink display mode
--rpi-width WIDTH          RPI display width in pixels (default: 800)
--rpi-height HEIGHT        RPI display height in pixels (default: 480)  
--rpi-refresh-mode MODE    E-ink refresh mode: partial, full (default: partial)
```

## Interface Layout

The RPI interface uses a CSS Grid layout with three main areas:

### Header Area
- **Left**: Navigation controls (Today button in interactive mode)
- **Center**: Calendar title and status information
- **Right**: Theme toggle button

### Content Area
- **Current Events**: Large, prominent display of ongoing meetings
- **Next Up**: Upcoming events in the next few hours
- **Later Today**: Compact list of remaining events

### Navigation Bar (Bottom)
- **Left**: Previous day button (`‹`)
- **Center**: Current date display
- **Right**: Next day button (`›`)

## Theme System

The RPI interface supports three themes accessible via the theme toggle button:

1. **`eink`**: Standard e-ink optimized theme
2. **`standard`**: Regular web interface theme  
3. **`eink-rpi`**: RPI-specific e-ink theme with component optimization

Themes can be switched:
- **Web Interface**: Click the 🎨 theme toggle button
- **API**: `POST /api/theme` with `{"theme": "eink-rpi"}`
- **Configuration**: Set `web_theme: "eink-rpi"` in config

## Files and Components

### Core Files
- **Renderer**: [`calendarbot/display/rpi_html_renderer.py`](calendarbot/display/rpi_html_renderer.py)
- **CSS**: [`calendarbot/web/static/eink-rpi.css`](calendarbot/web/static/eink-rpi.css)
- **JavaScript**: [`calendarbot/web/static/eink-rpi.js`](calendarbot/web/static/eink-rpi.js)

### Integration Points
- **Display Manager**: Auto-detects and instantiates RPI renderer
- **Web Server**: Serves RPI-specific assets and supports theme switching
- **Settings**: Configuration management for RPI-specific options

## API Endpoints

All standard CalendarBot API endpoints work with RPI mode:

- **`GET /`**: Main calendar interface (RPI optimized when enabled)
- **`POST /api/navigate`**: Navigate between dates
- **`POST /api/theme`**: Switch themes
- **`GET /api/refresh`**: Refresh calendar data
- **`GET /api/status`**: Get system status

## Browser Compatibility

The RPI interface is tested with:
- **Chromium** on Raspberry Pi OS
- **Firefox** on Raspberry Pi OS
- **WebKit-based browsers** for kiosk mode

## Performance Optimization

### E-ink Specific Features
- **Minimal DOM updates**: Reduces unnecessary e-ink refreshes
- **High contrast design**: Optimized for black/white e-ink displays
- **Large touch targets**: 44px minimum for finger navigation
- **Simplified animations**: Reduced motion for faster rendering

### Recommended Settings
```yaml
rpi:
  refresh_mode: "partial"  # Faster updates for interactive use
  auto_theme: true         # Automatically optimize theme
  
web:
  auto_refresh: 300        # 5-minute refresh interval
```

## Troubleshooting

### Common Issues

**RPI renderer not loading**:
- Check `display_type: "rpi"` in configuration
- Verify `--rpi` flag is used in command line
- Ensure all RPI files are present in the project

**Layout issues on non-800x480 displays**:
- Adjust `rpi_display_width` and `rpi_display_height` settings
- Consider using standard HTML renderer for different dimensions

**Theme not switching**:
- Verify theme toggle button is visible and functional
- Check browser console for JavaScript errors
- Ensure [`eink-rpi.css`](calendarbot/web/static/eink-rpi.css) file is accessible

### Debug Mode

Enable debug logging to troubleshoot RPI interface issues:

```bash
python main.py --web --rpi --log-level DEBUG
```

## Integration Examples

### Basic Kiosk Setup
```bash
# Start RPI interface in kiosk mode
python main.py --web --rpi --port 8080 --auto-open

# Or configure in systemd service
ExecStart=/usr/bin/python3 /path/to/calendarbot/main.py --web --rpi
```

### Custom Configuration
```yaml
# config/config.yaml
display_type: "rpi"
rpi:
  enabled: true
  display_width: 800
  display_height: 480
  auto_theme: true
web:
  enabled: true
  port: 8080
  theme: "eink-rpi"
  auto_refresh: 300
```

This integration provides a complete, production-ready e-ink interface for Raspberry Pi deployments while maintaining full compatibility with existing CalendarBot functionality.