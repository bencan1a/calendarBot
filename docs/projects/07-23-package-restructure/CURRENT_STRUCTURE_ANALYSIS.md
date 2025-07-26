# Current Structure Analysis

This document analyzes the current structure of the calendarbot and calendarbot_epaper packages, their dependencies, and integration points.

## Package Structure Overview

### calendarbot_epaper Package

```
calendarbot_epaper/
├── __init__.py                 # Package initialization
├── display/                    # Display abstraction layer
│   ├── __init__.py
│   ├── abstraction.py          # Display abstraction layer interfaces
│   ├── capabilities.py         # Display capabilities model
│   └── region.py               # Region model for partial updates
├── drivers/                    # Display drivers
│   ├── __init__.py
│   ├── eink_driver.py          # Base e-ink driver interface
│   ├── mock_eink_driver.py     # Mock driver for testing
│   └── waveshare/              # Waveshare-specific drivers
│       ├── __init__.py
│       ├── epd4in2b_v2.py      # Waveshare 4.2inch e-Paper Module (B) v2 driver
│       └── utils.py            # Utility functions for Waveshare drivers
├── integration/                # Integration with calendarbot
│   ├── __init__.py
│   └── eink_whats_next_renderer.py # E-ink renderer for WhatsNext view
├── rendering/                  # Rendering utilities
│   └── __init__.py
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── colors.py               # Color mapping utilities
│   ├── image_processing.py     # Image processing utilities
│   ├── image_processor.py      # Image processor
│   └── logging.py              # Logging utilities
├── setup.py                    # Package setup file
└── requirements.txt            # Package dependencies
```

### calendarbot Package (Display-Related Components)

```
calendarbot/
├── display/
│   ├── __init__.py
│   ├── renderer_interface.py   # Abstract base class for renderers
│   ├── renderer_protocol.py    # Protocol definition for renderers
│   ├── renderer_factory.py     # Factory for creating renderers
│   ├── whats_next_renderer.py  # Web-based WhatsNext renderer
│   ├── html_renderer.py        # HTML renderer
│   ├── console_renderer.py     # Console renderer
│   ├── compact_eink_renderer.py # Compact e-ink renderer
│   └── rpi_html_renderer.py    # Raspberry Pi HTML renderer
└── ...
```

## Dependencies

### calendarbot_epaper Dependencies

From `setup.py` and `requirements.txt`:

```
# Core dependencies
RPi.GPIO>=0.7.0
spidev>=3.5
Pillow>=8.0.0
numpy>=1.19.0
typing-extensions>=4.0.0

# Development dependencies
pytest>=6.0.0
pytest-cov>=2.10.0
black>=20.8b1
isort>=5.0.0
mypy>=0.800
pylint>=2.5.0
```

### Hardware-Specific Dependencies

- **RPi.GPIO**: Raspberry Pi GPIO library for hardware control
- **spidev**: SPI interface library for communication with e-Paper display

### Integration Points

1. **RendererFactory Integration**:
   - In `calendarbot/display/renderer_factory.py`, there's a try/except block to import the e-Paper renderer:
   ```python
   try:
       from calendarbot_epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
       EPAPER_AVAILABLE = True
   except ImportError:
       logger.info("calendarbot_epaper package not available - e-Paper rendering disabled")
       EInkWhatsNextRenderer = None
       EPAPER_AVAILABLE = False
   ```
   - The factory adds the e-Paper renderer to available renderers if it's available:
   ```python
   if EPAPER_AVAILABLE and EInkWhatsNextRenderer is not None:
       renderer_classes["eink-whats-next"] = EInkWhatsNextRenderer
   ```

2. **Renderer Interface Implementation**:
   - `EInkWhatsNextRenderer` in `calendarbot_epaper/integration/eink_whats_next_renderer.py` implements the `RendererInterface` from `calendarbot/display/renderer_interface.py`
   - It has similar try/except blocks for importing calendarbot components:
   ```python
   try:
       # Import CalendarBot components
       from calendarbot.display.renderer_interface import RendererInterface, InteractionEvent
       from calendarbot.display.whats_next_data_model import WhatsNextViewModel, EventData
       from calendarbot.display.whats_next_logic import WhatsNextLogic
       from calendarbot.cache.models import CachedEvent
   except ImportError as e:
       # Handle case where calendarbot is not installed
       logging.warning(f"CalendarBot components not available: {e}")
       RendererInterface = object
       InteractionEvent = Dict[str, Any]
       WhatsNextViewModel = Dict[str, Any]
       EventData = Dict[str, Any]
       WhatsNextLogic = object
       CachedEvent = Dict[str, Any]
   ```

3. **Color Consistency**:
   - `calendarbot_epaper/utils/colors.py` extracts color palette from web CSS to ensure consistency between web and e-Paper rendering
   - Comment in the file: `# E-Paper color palette extracted from calendarbot/web/static/layouts/whats-next-view/whats-next-view.css`

## Testing Structure

Tests for e-Paper functionality are in `tests/unit/epaper/` with the following structure:

```
tests/unit/epaper/
├── display/          # Tests for display abstraction
├── drivers/          # Tests for display drivers
├── integration/      # Tests for integration with calendarbot
│   └── test_calendarbot_integration.py
└── utils/            # Tests for utility functions
```

## Current Issues

1. **Complex Import Fallbacks**: Both packages have complex try/except blocks to handle cases where the other package might not be available.

2. **Separate Package Management**: Having two separate packages with their own setup.py and requirements.txt adds complexity to installation and maintenance.

3. **Hardware Dependencies**: The e-Paper functionality depends on hardware-specific libraries (RPi.GPIO, spidev) that might not be available on all platforms.

4. **Duplicated Code**: Some functionality might be duplicated between the two packages.

5. **Testing Complexity**: Tests are spread across different directories, making it harder to maintain comprehensive test coverage.