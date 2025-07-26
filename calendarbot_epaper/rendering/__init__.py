"""Rendering utilities for e-Paper displays."""

# Import from integration module instead
try:
    from ..integration.eink_whats_next_renderer import EInkWhatsNextRenderer

    __all__ = ["EInkWhatsNextRenderer"]
except ImportError:
    __all__ = []
