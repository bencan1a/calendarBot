# Import and Integration Strategy

This document outlines the strategy for simplifying imports and eliminating complex fallbacks in the unified calendarbot package.

## Current Import Challenges

The current implementation has several import-related challenges:

1. **Cross-Package Imports with Fallbacks**: Both packages have complex try/except blocks to handle cases where the other package might not be available:

   ```python
   # In calendarbot/display/renderer_factory.py
   try:
       from calendarbot_epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
       EPAPER_AVAILABLE = True
   except ImportError:
       logger.info("calendarbot_epaper package not available - e-Paper rendering disabled")
       EInkWhatsNextRenderer = None
       EPAPER_AVAILABLE = False
   ```

   ```python
   # In calendarbot_epaper/integration/eink_whats_next_renderer.py
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

2. **Fallback Type Definitions**: When imports fail, the code creates fallback type definitions that might not match the actual types.

3. **Conditional Logic Based on Import Success**: The code has conditional logic based on whether imports succeeded, which adds complexity.

## Proposed Solution

With our unified package structure, we can eliminate these complex fallbacks and simplify the imports. Here's the strategy:

### 1. Feature Flag-Based Imports

Instead of try/except blocks for imports, we'll use feature flags to control imports:

```python
# In calendarbot/display/epaper/__init__.py
from typing import Tuple, Optional
import importlib.util

def check_epaper_availability() -> Tuple[bool, Optional[str]]:
    """Check if e-Paper hardware dependencies are available."""
    # Implementation as described in the dependency management strategy
    pass

# Export availability flag
EPAPER_AVAILABLE, EPAPER_UNAVAILABLE_REASON = check_epaper_availability()
```

### 2. Clean Imports with Feature Flags

In the renderer factory, we'll use the feature flag to conditionally import and register the e-Paper renderer:

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

### 3. Clean Implementation of e-Paper Renderer

The e-Paper renderer can now import from the main package without fallbacks:

```python
# In calendarbot/display/epaper/renderers/eink_whats_next_renderer.py
import logging
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

# Clean imports from main package
from calendarbot.display.renderer_interface import RendererInterface, InteractionEvent
from calendarbot.display.whats_next_data_model import WhatsNextViewModel, EventData
from calendarbot.display.whats_next_logic import WhatsNextLogic
from calendarbot.cache.models import CachedEvent

# Clean imports from epaper submodule
from ..abstraction import DisplayAbstractionLayer
from ..capabilities import DisplayCapabilities
from ..drivers.mock_eink_driver import EInkDriver
from ..utils.image_processor import ImageProcessor
from ..utils.colors import get_rendering_colors, convert_to_pil_color, EPaperColors

logger = logging.getLogger(__name__)

class EInkWhatsNextRenderer(RendererInterface):
    """E-Paper specialized renderer for What's Next view."""
    # Implementation...
```

### 4. Hardware Abstraction Layer

To further isolate hardware-specific code, we'll implement a hardware abstraction layer:

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

### 5. Simplified Device Detection

We'll simplify the device detection logic to use the feature flag:

```python
# In calendarbot/display/renderer_factory.py
@staticmethod
def detect_device_type() -> str:
    """Detect the device type based on hardware characteristics."""
    try:
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        logger.debug(f"Device detection: system={system}, machine={machine}")
        
        # Check for Raspberry Pi with e-Paper display
        if _is_raspberry_pi():
            from .epaper import EPAPER_AVAILABLE
            
            if EPAPER_AVAILABLE and _has_compact_display():
                logger.info("Detected Raspberry Pi with compact e-ink display")
                return "compact"
            else:
                logger.info("Detected standard Raspberry Pi")
                return "rpi"
        
        # Rest of the implementation...
    except Exception as e:
        logger.error(f"Device detection failed: {e}")
        return "unknown"
```

## Benefits of This Approach

1. **No Complex Fallbacks**: The code no longer needs complex try/except blocks for imports.

2. **Clean Type Definitions**: All type definitions are properly imported from their source.

3. **Centralized Feature Detection**: The availability of e-Paper hardware is checked in one place.

4. **Simplified Conditional Logic**: The code uses a simple feature flag to control behavior.

5. **Better Error Handling**: Hardware-specific errors are handled in a centralized way.

6. **Improved Testability**: The code is easier to test because it has fewer conditional paths.

## Implementation Notes

1. **Feature Flag**: The `EPAPER_AVAILABLE` flag is the central control point for e-Paper functionality.

2. **Hardware Abstraction**: The `HardwareManager` provides a clean abstraction for hardware-specific code.

3. **Clean Imports**: All imports are clean and direct, with no fallbacks.

4. **Centralized Error Handling**: Hardware-specific errors are handled in a centralized way.

5. **Simplified Device Detection**: The device detection logic is simplified to use the feature flag.