# Migration Plan

This document outlines the step-by-step plan for migrating code from the separate calendarbot_epaper package into the unified calendarbot package structure.

## Migration Approach

The migration will follow these principles:

1. **Incremental Changes**: Make changes in small, testable increments
2. **Maintain Functionality**: Ensure all functionality continues to work throughout the migration
3. **Minimize Disruption**: Minimize disruption to existing code and users
4. **Test-Driven**: Test each change thoroughly before proceeding

## Prerequisites

Before beginning the migration:

1. Create a new branch for the migration work
2. Ensure all tests are passing in the current state
3. Create a backup of the current code

## Migration Steps

### Phase 1: Create New Directory Structure

1. Create the new directory structure in calendarbot:

```bash
# Create new directories
mkdir -p calendarbot/display/renderers
mkdir -p calendarbot/display/epaper/renderers
mkdir -p calendarbot/display/epaper/drivers/waveshare
mkdir -p calendarbot/display/epaper/utils
```

### Phase 2: Move Display Abstraction Layer

1. Move display abstraction files:

```bash
# Move display abstraction files
cp calendarbot_epaper/display/abstraction.py calendarbot/display/epaper/abstraction.py
cp calendarbot_epaper/display/capabilities.py calendarbot/display/epaper/capabilities.py
cp calendarbot_epaper/display/region.py calendarbot/display/epaper/region.py
```

2. Update imports in the moved files:

```python
# In calendarbot/display/epaper/abstraction.py, capabilities.py, region.py
# Change imports like:
# from ..utils.logging import logger
# To:
# from calendarbot.utils.logging import logger
```

### Phase 3: Move Drivers

1. Move driver files:

```bash
# Move driver files
cp calendarbot_epaper/drivers/eink_driver.py calendarbot/display/epaper/drivers/eink_driver.py
cp calendarbot_epaper/drivers/mock_eink_driver.py calendarbot/display/epaper/drivers/mock_eink_driver.py
cp calendarbot_epaper/drivers/waveshare/epd4in2b_v2.py calendarbot/display/epaper/drivers/waveshare/epd4in2b_v2.py
cp calendarbot_epaper/drivers/waveshare/utils.py calendarbot/display/epaper/drivers/waveshare/utils.py
```

2. Update imports in the moved files:

```python
# In calendarbot/display/epaper/drivers/*.py
# Change imports like:
# from ..display.capabilities import DisplayCapabilities
# To:
# from calendarbot.display.epaper.capabilities import DisplayCapabilities
```

### Phase 4: Move Utilities

1. Move utility files:

```bash
# Move utility files
cp calendarbot_epaper/utils/colors.py calendarbot/display/epaper/utils/colors.py
cp calendarbot_epaper/utils/image_processing.py calendarbot/display/epaper/utils/image_processing.py
cp calendarbot_epaper/utils/image_processor.py calendarbot/display/epaper/utils/image_processor.py
```

2. Update imports in the moved files:

```python
# In calendarbot/display/epaper/utils/*.py
# Change imports like:
# from ..display.capabilities import DisplayCapabilities
# To:
# from calendarbot.display.epaper.capabilities import DisplayCapabilities
```

### Phase 5: Move Renderers

1. Move existing renderers to the new renderers directory:

```bash
# Move existing renderers
cp calendarbot/display/html_renderer.py calendarbot/display/renderers/html_renderer.py
cp calendarbot/display/console_renderer.py calendarbot/display/renderers/console_renderer.py
cp calendarbot/display/whats_next_renderer.py calendarbot/display/renderers/whats_next_renderer.py
cp calendarbot/display/rpi_html_renderer.py calendarbot/display/renderers/rpi_html_renderer.py
cp calendarbot/display/compact_eink_renderer.py calendarbot/display/renderers/compact_eink_renderer.py
```

2. Move e-Paper renderer:

```bash
# Move e-Paper renderer
cp calendarbot_epaper/integration/eink_whats_next_renderer.py calendarbot/display/epaper/renderers/eink_whats_next_renderer.py
```

3. Update imports in the moved files:

```python
# In calendarbot/display/renderers/*.py
# Change imports like:
# from .renderer_interface import RendererInterface
# To:
# from calendarbot.display.renderer_interface import RendererInterface
```

```python
# In calendarbot/display/epaper/renderers/eink_whats_next_renderer.py
# Change imports like:
# from calendarbot.display.renderer_interface import RendererInterface
# To:
# from calendarbot.display.renderer_interface import RendererInterface
# (No change needed for imports from calendarbot)

# Change imports like:
# from ..display.abstraction import DisplayAbstractionLayer
# To:
# from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
```

### Phase 6: Create Feature Detection Module

1. Create the e-Paper feature detection module:

```bash
# Create e-Paper __init__.py
touch calendarbot/display/epaper/__init__.py
```

2. Implement the feature detection logic:

```python
# In calendarbot/display/epaper/__init__.py
"""e-Paper display functionality for CalendarBot."""

import logging
import importlib.util
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def check_epaper_availability() -> Tuple[bool, Optional[str]]:
    """
    Check if e-Paper hardware dependencies are available.
    
    Returns:
        Tuple of (is_available, reason)
    """
    # Check for RPi.GPIO
    if importlib.util.find_spec("RPi.GPIO") is None:
        return False, "RPi.GPIO not available"
    
    # Check for spidev
    if importlib.util.find_spec("spidev") is None:
        return False, "spidev not available"
    
    # Check for PIL/Pillow
    if importlib.util.find_spec("PIL") is None:
        return False, "PIL/Pillow not available"
    
    # All dependencies available
    return True, None

# Export availability flag
EPAPER_AVAILABLE, EPAPER_UNAVAILABLE_REASON = check_epaper_availability()

if EPAPER_AVAILABLE:
    logger.info("e-Paper hardware dependencies available")
else:
    logger.info(f"e-Paper hardware dependencies not available: {EPAPER_UNAVAILABLE_REASON}")
```

### Phase 7: Update RendererFactory

1. Update the renderer factory to use the new structure:

```python
# In calendarbot/display/renderer_factory.py
from typing import Dict, Type, Any, cast

from .renderer_protocol import RendererProtocol
from .renderers.html_renderer import HTMLRenderer
from .renderers.console_renderer import ConsoleRenderer
from .renderers.whats_next_renderer import WhatsNextRenderer
from .renderers.rpi_html_renderer import RaspberryPiHTMLRenderer
from .renderers.compact_eink_renderer import CompactEInkRenderer

# Import e-Paper availability flag
from .epaper import EPAPER_AVAILABLE

# Dictionary of renderer classes
renderer_classes: Dict[str, Type[RendererProtocol]] = {
    "html": HTMLRenderer,
    "rpi": RaspberryPiHTMLRenderer,
    "compact": CompactEInkRenderer,
    "console": ConsoleRenderer,
    "whats-next": WhatsNextRenderer,
}

# Conditionally register e-Paper renderer if available
if EPAPER_AVAILABLE:
    from .epaper.renderers.eink_whats_next_renderer import EInkWhatsNextRenderer
    renderer_classes["eink-whats-next"] = EInkWhatsNextRenderer
```

### Phase 8: Update setup.py

1. Update setup.py to include the new optional dependencies:

```python
# In setup.py
setup(
    name="calendarbot",
    version=version,
    # ... other setup parameters ...
    install_requires=[
        # Core dependencies that everyone needs
        "Pillow>=8.0.0",
        "numpy>=1.19.0",
        "typing-extensions>=4.0.0",
        # ... other core dependencies ...
    ],
    extras_require={
        # Optional e-Paper dependencies
        "epaper": [
            "RPi.GPIO>=0.7.0; platform_system=='Linux' and platform_machine in ('armv7l', 'armv6l', 'aarch64')",
            "spidev>=3.5; platform_system=='Linux' and platform_machine in ('armv7l', 'armv6l', 'aarch64')",
        ],
        # Development dependencies
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=20.8b1",
            "isort>=5.0.0",
            "mypy>=0.800",
            "pylint>=2.5.0",
        ],
    },
)
```

### Phase 9: Update Tests

1. Move e-Paper tests to the new structure:

```bash
# Move e-Paper tests
mkdir -p tests/unit/display/epaper
cp -r tests/unit/epaper/* tests/unit/display/epaper/
```

2. Update imports in the moved tests:

```python
# In tests/unit/display/epaper/*.py
# Change imports like:
# from calendarbot_epaper.display.abstraction import DisplayAbstractionLayer
# To:
# from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
```

### Phase 10: Create Hardware Abstraction Layer

1. Create the hardware abstraction layer:

```bash
# Create hardware.py
touch calendarbot/display/epaper/hardware.py
```

2. Implement the hardware abstraction layer:

```python
# In calendarbot/display/epaper/hardware.py
import logging
import importlib.util
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class HardwareManager:
    """Manages hardware-specific functionality for e-Paper displays."""
    
    @staticmethod
    def get_driver(driver_type: str, **kwargs: Any) -> Optional["EInkDriver"]:
        """
        Get an e-Paper driver instance if hardware is available.
        
        Args:
            driver_type: Type of driver to create
            **kwargs: Additional arguments for driver initialization
            
        Returns:
            Driver instance or None if hardware not available
        """
        from . import EPAPER_AVAILABLE
        
        if not EPAPER_AVAILABLE:
            logger.warning("e-Paper hardware not available, using mock driver")
            from .drivers.mock_eink_driver import EInkDriver
            return EInkDriver(**kwargs)
            
        if driver_type == "waveshare_4in2b_v2":
            try:
                from .drivers.waveshare.epd4in2b_v2 import EPD4in2bV2
                return EPD4in2bV2(**kwargs)
            except ImportError:
                logger.warning("Waveshare driver not available, using mock driver")
                from .drivers.mock_eink_driver import EInkDriver
                return EInkDriver(**kwargs)
        else:
            logger.warning(f"Unknown driver type: {driver_type}, using mock driver")
            from .drivers.mock_eink_driver import EInkDriver
            return EInkDriver(**kwargs)
```

### Phase 11: Clean Up

1. Remove the old files:

```bash
# Remove old renderer files
rm calendarbot/display/html_renderer.py
rm calendarbot/display/console_renderer.py
rm calendarbot/display/whats_next_renderer.py
rm calendarbot/display/rpi_html_renderer.py
rm calendarbot/display/compact_eink_renderer.py

# Keep calendarbot_epaper for now, but mark it as deprecated
# We'll remove it in a future release
```

2. Update imports in any remaining files:

```python
# In any remaining files that import the old renderers
# Change imports like:
# from .html_renderer import HTMLRenderer
# To:
# from .renderers.html_renderer import HTMLRenderer
```

## Testing Strategy

After each phase:

1. Run unit tests to ensure functionality is maintained
2. Fix any failing tests before proceeding to the next phase
3. Manually test the application to ensure it works as expected

## Rollback Plan

If issues are encountered:

1. Revert to the previous state
2. Fix the issues
3. Try again

## Post-Migration Tasks

After the migration is complete:

1. Update documentation to reflect the new structure
2. Create a deprecation notice for calendarbot_epaper
3. Plan for the eventual removal of calendarbot_epaper

## Timeline

The migration should be completed in a single development cycle to minimize disruption. Each phase should take approximately 1-2 hours, for a total of 1-2 days of development time.