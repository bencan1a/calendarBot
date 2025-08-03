# Dynamic Resource Integration Feature

**Version:** 1.0.0  
**Last Updated:** August 3, 2025  
**Related Modules:** 
- `calendarbot/layout/resource_manager.py`
- `calendarbot/layout/registry.py`
- `calendarbot/display/html_renderer.py`
**Status:** Implemented

## Overview

The Dynamic Resource Integration feature provides a flexible system for loading and managing layout-specific resources (CSS, JavaScript) in CalendarBot's web interface. This feature enables layouts to define their own resources, which are then dynamically loaded and integrated into the HTML output, allowing for modular and extensible UI components.

## Key Capabilities

- **Dynamic Resource Discovery**: Automatically discovers and loads layout-specific CSS and JavaScript files
- **Resource URL Generation**: Creates appropriate URLs for web resources based on layout configuration
- **Fallback Chain Support**: Implements graceful degradation with fallback layouts when resources are missing
- **Error Resilience**: Maintains functionality even when resource loading fails
- **Layout-Specific Styling**: Enables each layout to define its own visual appearance and behavior

## Architecture

The Dynamic Resource Integration feature is implemented through the following components:

### ResourceManager Class

The core component that manages dynamic loading of layout resources.

```python
class ResourceManager:
    """Manages dynamic loading of layout resources."""
    
    def __init__(self, layout_registry: LayoutRegistry) -> None:
        # Initialize with layout registry for layout information
        
    def get_css_urls(self, layout_name: str) -> list[str]:
        # Generate URLs for layout-specific CSS resources
        
    def get_js_urls(self, layout_name: str) -> list[str]:
        # Generate URLs for layout-specific JavaScript resources
```

### Integration with HTMLRenderer

The HTMLRenderer uses the ResourceManager to incorporate layout-specific resources into the rendered HTML.

```python
class HTMLRenderer:
    """Renders calendar events as HTML with dynamic layout resources."""
    
    def __init__(self, settings: Any) -> None:
        # Initialize with layout registry and resource manager
        
    def _get_dynamic_resources(self) -> tuple[list[str], list[str]]:
        # Get CSS and JS resources for the current layout
```

## Usage Examples

### Basic Resource Loading

```python
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.layout.resource_manager import ResourceManager

# Create layout registry
registry = LayoutRegistry()

# Create resource manager
resource_manager = ResourceManager(registry)

# Get CSS URLs for a specific layout
css_urls = resource_manager.get_css_urls("4x8")
# Result: ["/static/layouts/4x8/4x8.css", "/static/layouts/4x8/common.css"]

# Get JavaScript URLs for a specific layout
js_urls = resource_manager.get_js_urls("4x8")
# Result: ["/static/layouts/4x8/4x8.js", "/static/layouts/4x8/navigation.js"]
```

### Integration with HTML Rendering

```python
from calendarbot.display.html_renderer import HTMLRenderer

# Create HTML renderer with settings
settings = get_settings()  # Your settings object
renderer = HTMLRenderer(settings)

# Render events with dynamic resources
html_output = renderer.render_events(events)
# HTML includes appropriate <link> and <script> tags for the layout
```

## Resource Configuration

Each layout defines its resources in a `layout.json` configuration file:

```json
{
  "name": "4x8",
  "display_name": "4×8 Landscape",
  "resources": {
    "css": [
      {
        "file": "4x8.css",
        "media": "screen",
        "priority": 1
      },
      {
        "file": "common.css",
        "media": "screen",
        "priority": 2
      }
    ],
    "js": [
      {
        "file": "4x8.js",
        "type": "module",
        "priority": 1,
        "defer": true
      },
      {
        "file": "navigation.js",
        "type": "module",
        "priority": 2,
        "defer": true
      }
    ]
  },
  "fallback_layouts": ["3x4", "console"]
}
```

## Directory Structure

Resources are organized in a consistent directory structure:

```
calendarbot/web/static/layouts/
├── 4x8/
│   ├── layout.json          # Layout configuration
│   ├── 4x8.css              # Layout-specific CSS
│   ├── common.css           # Shared CSS
│   ├── 4x8.js               # Layout-specific JavaScript
│   └── navigation.js        # Navigation functionality
├── 3x4/
│   ├── layout.json
│   ├── 3x4.css
│   └── 3x4.js
└── whats-next-view/
    ├── layout.json
    ├── whats-next-view.css
    └── whats-next-view.js
```

## API Reference

### ResourceManager

#### Constructor

```python
def __init__(self, layout_registry: LayoutRegistry) -> None
```

- **layout_registry**: The layout registry for accessing layout information

#### Methods

```python
def get_css_urls(self, layout_name: str) -> list[str]
```

- **layout_name**: Name of the layout to get CSS URLs for
- **Returns**: List of CSS URLs for the specified layout

```python
def get_js_urls(self, layout_name: str) -> list[str]
```

- **layout_name**: Name of the layout to get JavaScript URLs for
- **Returns**: List of JavaScript URLs for the specified layout

### HTMLRenderer Integration

```python
def _get_dynamic_resources(self) -> tuple[list[str], list[str]]
```

- **Returns**: Tuple containing (css_files, js_files) for the current layout

```python
def _get_fallback_css_file(self) -> str
```

- **Returns**: Fallback CSS filename if dynamic loading fails

```python
def _get_fallback_js_file(self) -> str
```

- **Returns**: Fallback JavaScript filename if dynamic loading fails

## Error Handling

The Dynamic Resource Integration feature includes robust error handling:

1. **Missing Layouts**: Falls back to default layouts when requested layout is not found
2. **Resource Loading Failures**: Maintains functionality with fallback resources
3. **Malformed Configuration**: Gracefully handles invalid layout configuration
4. **Resource Manager Initialization Failures**: HTMLRenderer remains functional even if ResourceManager fails

## Integration Points

The Dynamic Resource Integration feature integrates with the following CalendarBot components:

- **Layout System**: Uses LayoutRegistry to discover and validate layouts
- **Display System**: Integrates with HTMLRenderer for web output
- **Web Server**: Serves the dynamically generated HTML with appropriate resources

## Limitations

- Currently only supports CSS and JavaScript resources (no images or other asset types)
- Resource URLs are generated assuming a specific web server structure
- No support for external CDN resources (all resources must be local)
- No minification or bundling of resources for production deployment