# Dependency Management Strategy

This document outlines the strategy for managing optional e-Paper hardware dependencies in the unified calendarbot package.

## Current Dependencies

The e-Paper functionality currently depends on the following hardware-specific libraries:

- **RPi.GPIO**: Raspberry Pi GPIO library for hardware control
- **spidev**: SPI interface library for communication with e-Paper display
- **Pillow**: Image processing library (not hardware-specific, but required for e-Paper)
- **numpy**: Numerical computing library (not hardware-specific, but used for image processing)
- **typing-extensions**: Type hinting extensions

## Challenges

1. **Hardware-Specific Dependencies**: RPi.GPIO and spidev are only available on Raspberry Pi and similar devices, and will fail to install on other platforms.

2. **Optional Functionality**: The e-Paper functionality is optional and should not be required for users who don't have the hardware.

3. **Graceful Degradation**: The application should still work without the e-Paper hardware, falling back to other display options.

## Proposed Solution: Optional Dependencies with Extras

We will use Python's "extras" feature in setup.py to define optional dependency groups. This allows users to install the package with or without the e-Paper dependencies.

### 1. Define Extras in setup.py

```python
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

### 2. Runtime Feature Detection

In addition to the setup.py changes, we'll implement runtime feature detection to gracefully handle missing dependencies:

```python
# In calendarbot/display/epaper/__init__.py

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

### 3. Lazy Loading of Hardware-Specific Modules

To prevent import errors when hardware dependencies are missing, we'll use lazy loading for hardware-specific modules:

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

# Lazy load e-Paper renderer if available
if EPAPER_AVAILABLE:
    try:
        from .epaper.renderers.eink_whats_next_renderer import EInkWhatsNextRenderer
        renderer_classes["eink-whats-next"] = EInkWhatsNextRenderer
    except ImportError:
        # This should not happen if EPAPER_AVAILABLE is True, but just in case
        pass
```

### 4. Installation Instructions

We'll provide clear installation instructions for users:

```
# Basic installation (without e-Paper support)
pip install calendarbot

# Installation with e-Paper support
pip install calendarbot[epaper]

# Installation for development
pip install calendarbot[dev]

# Installation with both e-Paper support and development tools
pip install calendarbot[epaper,dev]
```

## Benefits of This Approach

1. **Clean Installation**: Users who don't need e-Paper support can install the package without hardware-specific dependencies.

2. **Simple for e-Paper Users**: Users who need e-Paper support can install everything with a single command.

3. **Graceful Degradation**: The application will still work without e-Paper hardware, falling back to other display options.

4. **No Import Errors**: The lazy loading approach prevents import errors when hardware dependencies are missing.

5. **Platform-Specific Dependencies**: The platform specifiers in setup.py ensure that hardware-specific dependencies are only installed on compatible platforms.

## Implementation Notes

1. **Platform Detection**: The platform specifiers in setup.py use Python's platform detection to only install hardware-specific dependencies on compatible platforms.

2. **Runtime Detection**: The runtime detection in `__init__.py` provides a clean way to check if e-Paper hardware is available at runtime.

3. **Lazy Loading**: The lazy loading in renderer_factory.py prevents import errors when hardware dependencies are missing.

4. **Clear Documentation**: We'll provide clear documentation on how to install the package with or without e-Paper support.