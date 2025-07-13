# Layout Development Guide

**Document Version:** 1.0  
**Last Updated:** January 12, 2025  
**Target Audience:** Developers, UI/UX Designers, Contributors

## Overview

This guide provides comprehensive instructions for creating, configuring, and integrating new layouts into the CalendarBot system. The layout system supports dynamic discovery, validation, and resource management for flexible UI rendering across different devices and display types.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Layout Structure](#layout-structure)
3. [Configuration Reference](#configuration-reference)
4. [CSS Development](#css-development)
5. [JavaScript Development](#javascript-development)
6. [Testing Layouts](#testing-layouts)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### Creating Your First Layout

1. **Create Layout Directory**
   ```bash
   mkdir calendarbot/web/static/layouts/my-layout
   cd calendarbot/web/static/layouts/my-layout
   ```

2. **Create Configuration File**
   ```bash
   touch layout.json
   ```

3. **Add Basic Configuration**
   ```json
   {
     "name": "my-layout",
     "display_name": "My Custom Layout",
     "description": "A custom layout for specific use case",
     "version": "1.0.0",
     "capabilities": {
       "grid_dimensions": {
         "columns": 3,
         "rows": 5
       }
     },
     "resources": {
       "css": ["my-layout.css"],
       "js": ["my-layout.js"]
     },
     "fallback_layouts": ["4x8", "console"]
   }
   ```

4. **Create CSS File**
   ```bash
   touch my-layout.css
   ```

5. **Create JavaScript File** (Optional)
   ```bash
   touch my-layout.js
   ```

6. **Test Layout**
   ```bash
   # From project root
   . venv/bin/activate
   calendarbot --web --layout my-layout
   ```

## Layout Structure

### Directory Organization

```
calendarbot/web/static/layouts/my-layout/
├── layout.json              # Required: Layout configuration
├── my-layout.css           # Required: Layout styles
├── my-layout.js            # Optional: Layout JavaScript
├── assets/                 # Optional: Layout-specific assets
│   ├── icons/
│   ├── images/
│   └── fonts/
├── themes/                 # Optional: Theme variations
│   ├── dark.css
│   ├── light.css
│   └── eink.css
└── README.md              # Optional: Layout documentation
```

### File Naming Conventions

- **Configuration**: Always named `layout.json`
- **CSS Files**: Should match layout name (e.g., `my-layout.css`)
- **JavaScript Files**: Should match layout name (e.g., `my-layout.js`)
- **Theme Files**: Use descriptive names (e.g., `dark.css`, `eink.css`)

## Configuration Reference

### Complete Configuration Schema

```json
{
  "name": "layout-name",
  "display_name": "Human Readable Name",
  "description": "Detailed description of layout purpose and features",
  "version": "1.0.0",
  "orientation": "landscape|portrait|responsive",
  
  "dimensions": {
    "min_width": 300,
    "min_height": 400,
    "optimal_width": 480,
    "optimal_height": 800,
    "max_width": 1920,
    "max_height": 1080,
    "fixed_dimensions": false,
    "disable_resize": false
  },
  
  "display_types": [
    "lcd",
    "oled",
    "eink",
    "web"
  ],
  
  "themes": [
    "standard",
    "dark",
    "eink",
    "high-contrast"
  ],
  
  "capabilities": {
    "grid_dimensions": {
      "columns": 4,
      "rows": 8
    },
    "display_modes": ["landscape", "portrait", "responsive"],
    "supported_devices": ["desktop", "tablet", "mobile", "rpi"],
    "animations": true,
    "layout_switching": true,
    "touch_support": true,
    "keyboard_navigation": true
  },
  
  "features": {
    "responsive": true,
    "touch_support": true,
    "keyboard_navigation": true,
    "auto_refresh": true,
    "theme_switching": true,
    "layout_switching": true,
    "animations": true,
    "mobile_optimized": false,
    "accessibility_compliant": true
  },
  
  "resources": {
    "css": [
      {
        "file": "layout.css",
        "media": "screen",
        "priority": 1,
        "theme": "default"
      },
      {
        "file": "print.css",
        "media": "print",
        "priority": 2
      }
    ],
    "js": [
      {
        "file": "layout.js",
        "type": "module",
        "priority": 1,
        "defer": true,
        "async": false
      }
    ],
    "fonts": [
      {
        "family": "Custom Font",
        "url": "fonts/custom-font.woff2",
        "weight": "400",
        "style": "normal"
      }
    ]
  },
  
  "compatibility": {
    "min_screen_width": 320,
    "min_screen_height": 240,
    "max_screen_width": 3840,
    "max_screen_height": 2160,
    "supports_touch": true,
    "supports_keyboard": true,
    "supports_mouse": true,
    "accessibility_features": [
      "keyboard_navigation",
      "focus_management",
      "screen_reader_support",
      "high_contrast_mode"
    ]
  },
  
  "performance": {
    "bundle_size_css": "~25KB",
    "bundle_size_js": "~20KB",
    "render_complexity": "low|medium|high",
    "memory_usage": "low|medium|high",
    "gpu_acceleration": false
  },
  
  "fallback_layouts": [
    "similar-layout",
    "4x8",
    "3x4",
    "console"
  ],
  
  "metadata": {
    "created": "2025-01-12",
    "author": "Your Name",
    "license": "MIT",
    "repository": "https://github.com/your-repo",
    "tags": [
      "responsive",
      "touch-enabled",
      "desktop"
    ],
    "changelog": {
      "1.0.0": "Initial release"
    }
  }
}
```

### Required Fields

- `name`: Unique layout identifier (must match directory name)
- `display_name`: Human-readable layout name
- `version`: Semantic version string
- `capabilities`: Layout capabilities object
- `resources`: CSS/JS resource definitions

### Optional Fields

All other fields are optional but recommended for complete layout definitions.

## CSS Development

### Base CSS Structure

```css
/* Layout Name: My Custom Layout */
/* Version: 1.0.0 */
/* Description: Custom layout for specific device */

/* ===========================================
   BASE STYLES
   =========================================== */

/* Reset and base styles */
html, body {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Layout container - adjust dimensions as needed */
body {
    width: 480px;
    height: 800px;
    background-color: white;
    overflow: hidden;
    position: relative;
}

/* ===========================================
   HEADER STYLES
   =========================================== */

.calendar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 2px solid #dee2e6;
    background: #ffffff;
}

.header-navigation {
    display: flex;
    align-items: center;
    gap: 1rem;
    width: 100%;
}

.nav-arrow-left,
.nav-arrow-right {
    padding: 0.5rem;
    border: 1px solid #dee2e6;
    background: transparent;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.header-date {
    flex: 1;
    text-align: center;
    font-weight: 500;
}

/* ===========================================
   CONTENT STYLES
   =========================================== */

.calendar-content {
    padding: 1.5rem;
    height: calc(100% - 80px);
    overflow-y: auto;
}

.section-title {
    font-size: 1.2rem;
    margin: 1.5rem 0 1rem 0;
    font-weight: bold;
}

/* ===========================================
   EVENT STYLES
   =========================================== */

.current-event {
    padding: 1.5rem;
    border: 2px solid #007bff;
    border-radius: 8px;
    margin-bottom: 1rem;
    background: #ffffff;
}

.upcoming-event {
    padding: 1rem;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    margin-bottom: 1rem;
    background: #ffffff;
}

.later-event {
    padding: 0.5rem 0;
    border-bottom: 1px solid #dee2e6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.event-title {
    font-weight: bold;
    margin-bottom: 0.5rem;
}

.event-time {
    font-size: 0.9rem;
    opacity: 0.8;
}

/* ===========================================
   RESPONSIVE DESIGN
   =========================================== */

@media (max-width: 480px) {
    body {
        width: 100vw;
        height: 100vh;
    }
    
    .calendar-header {
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .calendar-content {
        padding: 1rem;
    }
}

/* ===========================================
   THEME VARIATIONS
   =========================================== */

.theme-dark {
    background: #1a1a1a;
    color: #ffffff;
}

.theme-dark .calendar-header {
    background: #2d2d2d;
    border-bottom-color: #444444;
}

.theme-dark .current-event,
.theme-dark .upcoming-event {
    background: #2d2d2d;
    border-color: #444444;
}

/* E-ink optimized theme */
.theme-eink {
    background: #ffffff;
    color: #000000;
}

.theme-eink * {
    transition: none !important;
    animation: none !important;
}

.theme-eink .current-event,
.theme-eink .upcoming-event {
    border-radius: 0;
    box-shadow: none;
}
```

### CSS Best Practices

1. **Use CSS Custom Properties** for consistent theming:
   ```css
   :root {
     --primary-color: #007bff;
     --secondary-color: #6c757d;
     --background-color: #ffffff;
     --text-color: #212529;
   }
   ```

2. **Implement Responsive Design** with mobile-first approach:
   ```css
   /* Mobile first */
   .element {
     width: 100%;
   }
   
   /* Desktop */
   @media (min-width: 768px) {
     .element {
       width: 50%;
     }
   }
   ```

3. **Support Theme Switching**:
   ```css
   .theme-dark .element {
     background: var(--dark-background);
     color: var(--dark-text);
   }
   ```

4. **Optimize for Performance**:
   ```css
   /* Use transform for animations */
   .element {
     transform: translateX(0);
     transition: transform 0.3s ease;
   }
   
   /* Avoid expensive properties */
   .element:hover {
     transform: translateX(10px);
     /* Instead of changing layout properties */
   }
   ```

## JavaScript Development

### Basic JavaScript Structure

```javascript
/**
 * Layout Name: My Custom Layout
 * Version: 1.0.0
 * Description: Custom layout JavaScript functionality
 */

class MyCustomLayout {
    constructor() {
        this.layoutName = 'my-layout';
        this.version = '1.0.0';
        this.isInitialized = false;
        
        this.init();
    }
    
    /**
     * Initialize layout-specific functionality
     */
    init() {
        if (this.isInitialized) return;
        
        this.setupEventListeners();
        this.setupKeyboardNavigation();
        this.setupTouchHandlers();
        this.setupThemeSupport();
        
        this.isInitialized = true;
        console.log(`${this.layoutName} v${this.version} initialized`);
    }
    
    /**
     * Setup event listeners for layout interactions
     */
    setupEventListeners() {
        // Navigation button handlers
        const leftArrow = document.querySelector('.nav-arrow-left');
        const rightArrow = document.querySelector('.nav-arrow-right');
        
        if (leftArrow) {
            leftArrow.addEventListener('click', () => this.navigatePrevious());
        }
        
        if (rightArrow) {
            rightArrow.addEventListener('click', () => this.navigateNext());
        }
        
        // Theme toggle handler
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }
    
    /**
     * Setup keyboard navigation
     */
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (event) => {
            switch (event.key) {
                case 'ArrowLeft':
                    event.preventDefault();
                    this.navigatePrevious();
                    break;
                case 'ArrowRight':
                    event.preventDefault();
                    this.navigateNext();
                    break;
                case ' ':
                    event.preventDefault();
                    this.navigateToday();
                    break;
                case 't':
                case 'T':
                    if (!event.ctrlKey && !event.metaKey) {
                        event.preventDefault();
                        this.toggleTheme();
                    }
                    break;
            }
        });
    }
    
    /**
     * Setup touch gesture handlers
     */
    setupTouchHandlers() {
        let startX = 0;
        let startY = 0;
        
        document.addEventListener('touchstart', (event) => {
            startX = event.touches[0].clientX;
            startY = event.touches[0].clientY;
        });
        
        document.addEventListener('touchend', (event) => {
            const endX = event.changedTouches[0].clientX;
            const endY = event.changedTouches[0].clientY;
            
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Horizontal swipe detection
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    this.navigatePrevious();
                } else {
                    this.navigateNext();
                }
            }
        });
    }
    
    /**
     * Setup theme support
     */
    setupThemeSupport() {
        // Detect system theme preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        
        prefersDark.addEventListener('change', (event) => {
            if (event.matches) {
                this.setTheme('dark');
            } else {
                this.setTheme('light');
            }
        });
    }
    
    /**
     * Navigate to previous period
     */
    navigatePrevious() {
        const currentUrl = new URL(window.location);
        const currentDate = new Date(currentUrl.searchParams.get('date') || new Date());
        
        currentDate.setDate(currentDate.getDate() - 1);
        
        currentUrl.searchParams.set('date', currentDate.toISOString().split('T')[0]);
        window.location.href = currentUrl.toString();
    }
    
    /**
     * Navigate to next period
     */
    navigateNext() {
        const currentUrl = new URL(window.location);
        const currentDate = new Date(currentUrl.searchParams.get('date') || new Date());
        
        currentDate.setDate(currentDate.getDate() + 1);
        
        currentUrl.searchParams.set('date', currentDate.toISOString().split('T')[0]);
        window.location.href = currentUrl.toString();
    }
    
    /**
     * Navigate to today
     */
    navigateToday() {
        const currentUrl = new URL(window.location);
        const today = new Date().toISOString().split('T')[0];
        
        currentUrl.searchParams.set('date', today);
        window.location.href = currentUrl.toString();
    }
    
    /**
     * Toggle between themes
     */
    toggleTheme() {
        const body = document.body;
        const currentTheme = body.className.match(/theme-(\w+)/)?.[1] || 'standard';
        
        const themes = ['standard', 'dark', 'eink'];
        const currentIndex = themes.indexOf(currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        const nextTheme = themes[nextIndex];
        
        this.setTheme(nextTheme);
    }
    
    /**
     * Set specific theme
     * @param {string} theme - Theme name to apply
     */
    setTheme(theme) {
        const body = document.body;
        
        // Remove existing theme classes
        body.className = body.className.replace(/theme-\w+/g, '').trim();
        
        // Add new theme class
        body.classList.add(`theme-${theme}`);
        
        // Store theme preference
        localStorage.setItem('calendar-theme', theme);
        
        // Emit theme change event
        const event = new CustomEvent('themeChanged', {
            detail: { theme: theme }
        });
        document.dispatchEvent(event);
    }
    
    /**
     * Cleanup layout resources
     */
    destroy() {
        // Remove event listeners and cleanup resources
        this.isInitialized = false;
        console.log(`${this.layoutName} destroyed`);
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new MyCustomLayout();
    });
} else {
    new MyCustomLayout();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MyCustomLayout;
}
```

### JavaScript Best Practices

1. **Use Modern ES6+ Features**:
   ```javascript
   // Destructuring
   const { width, height } = element.getBoundingClientRect();
   
   // Arrow functions
   const handleClick = (event) => {
       event.preventDefault();
       // Handle click
   };
   
   // Template literals
   const message = `Layout ${name} loaded successfully`;
   ```

2. **Implement Error Handling**:
   ```javascript
   try {
       this.initializeFeature();
   } catch (error) {
       console.error(`Failed to initialize feature: ${error.message}`);
       // Fallback behavior
   }
   ```

3. **Use Async/Await for API Calls**:
   ```javascript
   async fetchLayoutData() {
       try {
           const response = await fetch('/api/layout-data');
           const data = await response.json();
           return data;
       } catch (error) {
           console.error('Failed to fetch layout data:', error);
           return null;
       }
   }
   ```

4. **Implement Proper Cleanup**:
   ```javascript
   destroy() {
       // Remove event listeners
       this.removeEventListeners();
       
       // Clear timers
       if (this.refreshTimer) {
           clearInterval(this.refreshTimer);
       }
       
       // Cleanup DOM references
       this.elements = null;
   }
   ```

## Testing Layouts

### Manual Testing Checklist

1. **Layout Loading**
   - [ ] Layout loads without errors
   - [ ] CSS resources load correctly
   - [ ] JavaScript initializes properly
   - [ ] Fallback layouts work when primary fails

2. **Visual Testing**
   - [ ] Layout renders correctly at target dimensions
   - [ ] All themes display properly
   - [ ] Responsive breakpoints work
   - [ ] Typography is readable
   - [ ] Colors meet accessibility standards

3. **Functionality Testing**
   - [ ] Navigation controls work
   - [ ] Keyboard navigation functions
   - [ ] Touch gestures respond correctly
   - [ ] Theme switching works
   - [ ] Auto-refresh functions (if enabled)

4. **Performance Testing**
   - [ ] Layout loads within acceptable time
   - [ ] CSS/JS bundle sizes are reasonable
   - [ ] Memory usage is acceptable
   - [ ] No JavaScript errors in console

5. **Accessibility Testing**
   - [ ] Keyboard navigation covers all functions
   - [ ] Screen reader compatibility
   - [ ] Focus management works correctly
   - [ ] Color contrast meets WCAG guidelines

### Automated Testing

Create test files in `tests/unit/layout/`:

```python
# tests/unit/layout/test_my_layout.py
import pytest
from pathlib import Path
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.layout.resource_manager import ResourceManager

class TestMyLayout:
    """Test my custom layout functionality."""
    
    @pytest.fixture
    def layout_registry(self):
        """Create layout registry for testing."""
        layouts_dir = Path(__file__).parent.parent.parent.parent / "calendarbot/web/static/layouts"
        return LayoutRegistry(layouts_dir=layouts_dir)
    
    @pytest.fixture
    def resource_manager(self, layout_registry):
        """Create resource manager for testing."""
        return ResourceManager(layout_registry)
    
    def test_layout_discovery(self, layout_registry):
        """Test that my layout is discovered correctly."""
        layouts = layout_registry.get_available_layouts()
        assert "my-layout" in layouts
    
    def test_layout_validation(self, layout_registry):
        """Test that my layout configuration is valid."""
        assert layout_registry.validate_layout("my-layout")
    
    def test_layout_info(self, layout_registry):
        """Test layout information retrieval."""
        layout_info = layout_registry.get_layout_info("my-layout")
        assert layout_info is not None
        assert layout_info.name == "my-layout"
        assert layout_info.version == "1.0.0"
    
    def test_css_resources(self, resource_manager):
        """Test CSS resource loading."""
        css_urls = resource_manager.get_css_urls("my-layout")
        assert len(css_urls) > 0
        assert any("my-layout.css" in url for url in css_urls)
    
    def test_js_resources(self, resource_manager):
        """Test JavaScript resource loading."""
        js_urls = resource_manager.get_js_urls("my-layout")
        # Assuming layout has JavaScript
        if js_urls:
            assert any("my-layout.js" in url for url in js_urls)
    
    def test_fallback_chain(self, layout_registry):
        """Test fallback chain functionality."""
        layout_info = layout_registry.get_layout_info("my-layout")
        fallback_chain = layout_info.fallback_chain
        assert "4x8" in fallback_chain or "console" in fallback_chain
```

### Browser Testing

Test layouts across different browsers and devices:

```bash
# Start development server
. venv/bin/activate
calendarbot --web --port 8080

# Test URLs:
# http://localhost:8080/calendar?layout=my-layout
# http://localhost:8080/calendar?layout=my-layout&theme=dark
# http://localhost:8080/calendar?layout=my-layout&date=2025-01-15
```

### Performance Testing

Use browser dev tools to check:

1. **Network Tab**: Resource loading times
2. **Performance Tab**: Rendering performance
3. **Memory Tab**: Memory usage patterns
4. **Console Tab**: JavaScript errors

## Best Practices

### Design Principles

1. **Mobile-First Design**
   - Start with mobile layout
   - Progressive enhancement for larger screens
   - Touch-friendly interactive elements

2. **Accessibility First**
   - Semantic HTML structure
   - Proper ARIA labels
   - Keyboard navigation support
   - Color contrast compliance

3. **Performance Optimization**
   - Minimize CSS/JS bundle sizes
   - Use CSS transforms for animations
   - Lazy load non-critical resources
   - Optimize images and fonts

4. **Theme Support**
   - Support multiple themes
   - Use CSS custom properties
   - Test with high contrast mode
   - Consider e-ink display optimization

### Code Quality

1. **CSS Organization**
   ```css
   /* Use logical section organization */
   /* 1. Reset and base styles */
   /* 2. Layout and grid */
   /* 3. Components */
   /* 4. Utilities */
   /* 5. Theme variations */
   /* 6. Media queries */
   ```

2. **JavaScript Modularity**
   ```javascript
   // Use classes and modules
   class LayoutManager {
       constructor() {
           this.modules = new Map();
       }
       
       addModule(name, module) {
           this.modules.set(name, module);
       }
   }
   ```

3. **Documentation**
   - Comment complex CSS rules
   - Document JavaScript functions
   - Include usage examples
   - Maintain changelog

### Testing Strategy

1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test layout system integration
3. **Visual Tests**: Screenshot comparison testing
4. **Manual Tests**: User interaction testing

## Troubleshooting

### Common Issues

1. **Layout Not Loading**
   ```
   Error: Layout 'my-layout' not found
   ```
   **Solution**: Check layout directory name matches configuration name

2. **CSS Not Applying**
   ```
   Error: Failed to load CSS resource
   ```
   **Solution**: Verify CSS file path in layout.json

3. **JavaScript Errors**
   ```
   Error: Cannot read property 'addEventListener' of null
   ```
   **Solution**: Check DOM element selectors and initialization timing

4. **Theme Not Switching**
   ```
   Issue: Theme toggle not working
   ```
   **Solution**: Verify theme CSS classes and JavaScript theme handler

### Debug Commands

```bash
# Check layout discovery
python -c "
from calendarbot.layout.registry import LayoutRegistry
registry = LayoutRegistry()
print('Available layouts:', registry.get_available_layouts())
"

# Validate specific layout
python -c "
from calendarbot.layout.registry import LayoutRegistry
registry = LayoutRegistry()
print('Layout valid:', registry.validate_layout('my-layout'))
print('Layout info:', registry.get_layout_info('my-layout'))
"

# Check resource URLs
python -c "
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.layout.resource_manager import ResourceManager
registry = LayoutRegistry()
manager = ResourceManager(registry)
print('CSS URLs:', manager.get_css_urls('my-layout'))
print('JS URLs:', manager.get_js_urls('my-layout'))
"
```

### Logging and Monitoring

Enable debug logging to troubleshoot layout issues:

```python
import logging
logging.getLogger('calendarbot.layout').setLevel(logging.DEBUG)
```

Check logs for layout discovery and resource loading messages.

## Advanced Topics

### Custom Themes

Create theme-specific CSS files:

```css
/* themes/accessibility.css */
.theme-accessibility {
    --primary-color: #000000;
    --background-color: #ffffff;
    --text-color: #000000;
    --border-width: 3px;
    --font-size-multiplier: 1.5;
}

.theme-accessibility * {
    border-width: var(--border-width) !important;
    font-size: calc(1rem * var(--font-size-multiplier)) !important;
}
```

### Dynamic Resource Loading

Implement conditional resource loading:

```javascript
class AdaptiveLayout {
    async loadResources() {
        // Load based on device capabilities
        if (this.isHighDPI()) {
            await this.loadHighDPIAssets();
        }
        
        if (this.isTouchDevice()) {
            await this.loadTouchEnhancements();
        }
        
        if (this.isSlowConnection()) {
            await this.loadLightweightVersion();
        }
    }
}
```

### Layout Analytics

Track layout usage and performance:

```javascript
class LayoutAnalytics {
    trackLayoutLoad(layoutName, loadTime) {
        // Send analytics data
        console.log(`Layout ${layoutName} loaded in ${loadTime}ms`);
    }
    
    trackUserInteraction(action, element) {
        // Track user interactions
        console.log(`User ${action} on ${element}`);
    }
}
```

## Contributing

When contributing new layouts to the project:

1. **Follow Naming Conventions**
   - Use kebab-case for layout names
   - Use descriptive names
   - Avoid conflicts with existing layouts

2. **Include Complete Documentation**
   - Layout README.md
   - Configuration comments
   - Usage examples

3. **Test Thoroughly**
   - Multiple browsers
   - Different screen sizes
   - Various themes
   - Accessibility tools

4. **Submit Pull Request**
   - Include layout in appropriate directory
   - Add tests for layout functionality
   - Update relevant documentation

---

For additional support or questions about layout development, please refer to the main [Architecture Documentation](../architecture/ARCHITECTURE.md) or submit an issue in the project repository.