"""E-Paper display integration for CalendarBot.

This module provides core e-paper functionality including:
- Display abstraction layer for e-paper hardware
- Specialized renderers for e-paper displays
- Hardware drivers and utilities
- PNG fallback emulation when hardware unavailable

Core Components:
- DisplayAbstractionLayer: Hardware abstraction
- EInkWhatsNextRenderer: Specialized What's Next view renderer
- Hardware detection with automatic PNG fallback
"""

from .abstraction import DisplayAbstractionLayer
from .capabilities import DisplayCapabilities
from .drivers.mock_eink_driver import EInkDriver
from .integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from .region import Region
from .utils.colors import EPaperColors, get_rendering_colors

__all__ = [
    "DisplayAbstractionLayer",
    "DisplayCapabilities",
    "EInkDriver",
    "EInkWhatsNextRenderer",
    "EPaperColors",
    "Region",
    "get_rendering_colors",
]

# E-Paper availability flag for runtime detection
EPAPER_AVAILABLE = True
