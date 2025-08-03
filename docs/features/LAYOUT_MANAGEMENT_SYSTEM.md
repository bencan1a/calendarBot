# Layout Management System

**Version:** 1.0.0  
**Last Updated:** August 3, 2025  
**Related Modules:** 
- `calendarbot/layout/registry.py`
- `calendarbot/layout/resource_manager.py`
- `calendarbot/web/static/layouts/`
**Status:** Implemented

## Overview

The Layout Management System provides a flexible framework for defining, discovering, and rendering different calendar layouts in CalendarBot. It enables the application to adapt its display to various screen sizes, orientations, and device types while maintaining a consistent user experience. The system supports dynamic layout switching, fallback mechanisms, and resource management.

## Key Capabilities

- **Dynamic Layout Discovery**: Automatically discovers and validates layouts from the filesystem
- **Layout Configuration**: Standardized JSON-based layout configuration format
- **Fallback Chain Support**: Graceful degradation with configurable fallback layouts
- **Resource Management**: Coordinated loading of layout-specific CSS and JavaScript
- **Renderer Integration**: Seamless integration with different renderer types
- **Device Adaptation**: Layouts optimized for different display types (web, e-ink, console)

## Architecture

The Layout Management System consists of two primary components:

### LayoutRegistry

The central registry for dynamic layout discovery and management.

```python
class LayoutRegistry:
    """Central registry for dynamic layout discovery and management."""
    
    def __init__(self, layouts_dir: Optional[Path] = None) -> None:
        # Initialize with optional custom layouts directory
        
    def discover_layouts(self) -> dict[str, Any]:
        # Discover available layouts from the filesystem
        
    def validate_layout(self, layout_name: str) -> bool:
        # Validate layout configuration
        
    def get_layout_with_fallback(self, layout_name: str) -> Any:
        # Get layout with fallback chain resolution
        
    def get_renderer_type(self, layout_name: str) -> str:
        # Get appropriate renderer type for layout
```

### ResourceManager

Manages dynamic loading of layout resources.

```python
class ResourceManager:
    """Manages dynamic loading of layout resources."""
    
    def __init__(self, layout_registry: LayoutRegistry) -> None:
        # Initialize with layout registry
        
    def get_css_urls(self, layout_name: str) -> list[str]:
        # Get CSS URLs for layout
        
    def get_js_urls(self, layout_name: str) -> list[str]:
        # Get JavaScript URLs for layout
        
    def inject_layout_resources(self, template: str, layout_name: str) -> str:
        # Inject resources into HTML template
        
    def validate_layout_resources(self, layout_name: str) -> bool:
        # Validate that all required resources exist
```

## Layout Configuration Format

Each layout is defined by a `layout.json` configuration file with the following structure:

```json
{
  "name": "4x8",
  "display_name": "4×8 Landscape",
  "description": "Standard landscape layout optimized for 4×8 inch displays",
  "version": "1.0.0",
  "orientation": "landscape",
  "dimensions": {
    "min_width": 480,
    "min_height": 800,
    "optimal_width": 480,
    "optimal_height": 800,
    "fixed_dimensions": true
  },
  "capabilities": {
    "grid_dimensions": {
      "columns": 4,
      "rows": 8
    },
    "display_modes": ["landscape", "standard"],
    "supported_devices": ["lcd", "oled", "web"],
    "animations": true,
    "layout_switching": true
  },
  "resources": {
    "css": [
      {
        "file": "4x8.css",
        "media": "screen",
        "priority": 1
      }
    ],
    "js": [
      {
        "file": "4x8.js",
        "type": "module",
        "priority": 1,
        "defer": true
      }
    ]
  },
  "fallback_layouts": ["3x4", "console"],
  "compatibility": {
    "min_screen_width": 320,
    "min_screen_height": 240,
    "supports_touch": true,
    "supports_keyboard": true,
    "accessibility_features": [
      "keyboard_navigation",
      "focus_management",
      "screen_reader_support"
    ]
  }
}
```

## Directory Structure

Layouts are organized in a consistent directory structure:

```
calendarbot/web/static/layouts/
├── 4x8/
│   ├── layout.json          # Layout configuration
│   ├── 4x8.css              # Layout styles
│   ├── 4x8.js               # Layout JavaScript
│   └── assets/              # Optional: layout-specific assets
├── 3x4/
│   ├── layout.json
│   ├── 3x4.css
│   └── 3x4.js
├── whats-next-view/
│   ├── layout.json          # Specialized countdown layout
│   ├── whats-next-view.css  # E-ink optimized styles
│   ├── whats-next-view.js   # Meeting detection logic
│   └── assets/
│       └── countdown-icons/ # Countdown-specific icons
└── custom-layout/
    ├── layout.json
    ├── custom.css
    ├── custom.js
    └── themes/
        ├── dark.css
        └── light.css
```

## Usage Examples

### Basic Layout Registry Usage

```python
from calendarbot.layout.registry import LayoutRegistry
from pathlib import Path

# Create layout registry with default layouts directory
registry = LayoutRegistry()

# Discover available layouts
layouts = registry.discover_layouts()
print(f"Found {len(layouts)} layouts: {', '.join(layouts.keys())}")

# Get layout with fallback
layout_info = registry.get_layout_with_fallback("4x8")
print(f"Using layout: {layout_info.name}")

# Check if layout is valid
is_valid = registry.validate_layout("custom-layout")
if not is_valid:
    print("Custom layout configuration is invalid")
```

### Resource Manager Integration

```python
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.layout.resource_manager import ResourceManager

# Create layout registry
registry = LayoutRegistry()

# Create resource manager
resource_manager = ResourceManager(registry)

# Get CSS and JS URLs for a layout
css_urls = resource_manager.get_css_urls("4x8")
js_urls = resource_manager.get_js_urls("4x8")

# Inject resources into HTML template
html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Calendar</title>
    <!-- RESOURCES_PLACEHOLDER -->
</head>
<body>
    <div class="calendar-container">
        <!-- Calendar content -->
    </div>
</body>
</html>"""

enhanced_html = resource_manager.inject_layout_resources(html_template, "4x8")
```

### Web Server Integration

```python
from calendarbot.web.server import WebServer
from calendarbot.layout.registry import LayoutRegistry

# In web server initialization
def initialize_server(self):
    self.layout_registry = LayoutRegistry()
    self.resource_manager = ResourceManager(self.layout_registry)
    
# In request handler
def handle_calendar_request(self, request):
    layout_name = request.query.get("layout", self.default_layout)
    layout_info = self.layout_registry.get_layout_with_fallback(layout_name)
    
    # Get resources
    css_urls = self.resource_manager.get_css_urls(layout_info.name)
    js_urls = self.resource_manager.get_js_urls(layout_info.name)
    
    # Render calendar with appropriate layout
    html = self.display_manager.render_calendar(events, layout_info.name)
    
    return html
```

## API Reference

### LayoutRegistry

#### Constructor

```python
def __init__(self, layouts_dir: Optional[Path] = None) -> None
```

- **layouts_dir**: Optional custom directory for layouts (defaults to `calendarbot/web/static/layouts/`)

#### Methods

```python
def discover_layouts(self) -> dict[str, Any]
```

- **Returns**: Dictionary of layout names to layout information

```python
def validate_layout(self, layout_name: str) -> bool
```

- **layout_name**: Name of layout to validate
- **Returns**: True if layout is valid, False otherwise

```python
def get_layout_with_fallback(self, layout_name: str) -> Any
```

- **layout_name**: Name of layout to get
- **Returns**: Layout information object, falling back to alternative layouts if necessary
- **Raises**: ValueError if no valid layout can be found in the fallback chain

```python
def get_renderer_type(self, layout_name: str) -> str
```

- **layout_name**: Name of layout to get renderer type for
- **Returns**: Renderer type string (e.g., "html", "console", "epaper")

### ResourceManager

#### Constructor

```python
def __init__(self, layout_registry: LayoutRegistry) -> None
```

- **layout_registry**: Layout registry for accessing layout information

#### Methods

```python
def get_css_urls(self, layout_name: str) -> list[str]
```

- **layout_name**: Name of layout to get CSS URLs for
- **Returns**: List of CSS URLs for the layout

```python
def get_js_urls(self, layout_name: str) -> list[str]
```

- **layout_name**: Name of layout to get JavaScript URLs for
- **Returns**: List of JavaScript URLs for the layout

```python
def inject_layout_resources(self, template: str, layout_name: str) -> str
```

- **template**: HTML template to inject resources into
- **layout_name**: Name of layout to get resources for
- **Returns**: HTML with injected resource references

```python
def validate_layout_resources(self, layout_name: str) -> bool
```

- **layout_name**: Name of layout to validate resources for
- **Returns**: True if all required resources exist, False otherwise

## Integration Points

The Layout Management System integrates with the following CalendarBot components:

- **Display System**: Provides layout information to renderers
- **Web Server**: Enables dynamic layout switching via URL parameters
- **E-Paper Display**: Supports specialized layouts for e-ink displays
- **HTML Renderer**: Injects layout-specific resources into HTML output

## Creating Custom Layouts

To create a custom layout:

1. Create a new directory in `calendarbot/web/static/layouts/` with your layout name
2. Create a `layout.json` configuration file with required metadata
3. Create CSS and JavaScript files for your layout
4. Add any layout-specific assets in an `assets/` subdirectory
5. Restart CalendarBot to discover the new layout

Example minimal layout configuration:

```json
{
  "name": "my-custom-layout",
  "display_name": "My Custom Layout",
  "description": "A custom layout for specific display needs",
  "version": "1.0.0",
  "orientation": "landscape",
  "resources": {
    "css": [{"file": "my-custom-layout.css", "media": "screen", "priority": 1}],
    "js": [{"file": "my-custom-layout.js", "type": "module", "priority": 1}]
  },
  "fallback_layouts": ["4x8", "3x4"]
}
```

## Limitations

- No hot-reloading of layouts (requires application restart)
- Limited validation of layout resources (basic existence checks only)
- No support for layout-specific templates (uses common HTML structure)
- No automatic adaptation to screen size (must manually select appropriate layout)
- No layout versioning or migration support