"""
Shared styling constants for consistent visual appearance across different renderers.

This module provides styling constants and utility functions to ensure visual consistency
between web (HTML) and e-paper (PIL) renderers. It extracts styling values from the
WhatsNextRenderer CSS and provides them in formats suitable for different rendering backends.
"""

from typing import Any, ClassVar, Literal, Union, cast


class SharedStylingConstants:
    """
    Shared styling constants for consistent visual appearance across different renderers.

    Provides color, typography, and layout constants in formats suitable for both
    web (HTML) and e-paper (PIL) rendering to ensure visual consistency.
    """

    # Color constants extracted from WhatsNextRenderer CSS
    COLORS: ClassVar[dict[str, str]] = {
        "background": "#ffffff",  # White background
        "background_secondary": "#f5f5f5",  # Light gray for secondary backgrounds
        "text_primary": "#212529",  # Dark gray for primary text
        "text_secondary": "#6c757d",  # Medium gray for secondary text
        "text_supporting": "#adb5bd",  # Light gray for supporting text
        "accent": "#007bff",  # Blue for accent elements
        "urgent": "#dc3545",  # Red for urgent elements
    }

    # Typography constants with both HTML and PIL formats
    TYPOGRAPHY: ClassVar[dict[str, dict[str, Any]]] = {
        "html": {
            "countdown": "30px",  # Large font for countdown timer
            "title": "24px",  # Large font for titles
            "subtitle": "18px",  # Medium font for subtitles
            "body": "14px",  # Regular font for body text
            "small": "12px",  # Small font for supporting text
        },
        "pil": {
            "countdown": 30,  # Numeric equivalent for PIL
            "title": 24,
            "subtitle": 18,
            "body": 14,
            "small": 12,
        },
    }

    # Layout constants for different display types
    LAYOUTS: ClassVar[dict[str, dict[str, Any]]] = {
        "web": {
            "width": "100%",  # Responsive width
            "height": "100vh",  # Viewport height
        },
        "epaper_waveshare_42": {
            "width": 400,  # Fixed width for Waveshare 4.2" e-paper display
            "height": 300,  # Fixed height for Waveshare 4.2" e-paper display
        },
    }


def get_colors_for_renderer(
    renderer_type: Literal["html", "pil"], mode: str = "L"
) -> dict[str, Union[str, int, tuple[int, int, int]]]:
    """
    Get colors formatted for the specified renderer type.

    Args:
        renderer_type: Type of renderer ("html" or "pil")
        mode: PIL image mode for PIL renderer ("1", "L", or "RGB")

    Returns:
        Dictionary of colors formatted for the specified renderer

    Raises:
        ValueError: If renderer_type is not supported
    """
    if renderer_type == "html":
        # Cast to the expected return type to satisfy type checker
        return cast(dict[str, Union[str, int, tuple[int, int, int]]], SharedStylingConstants.COLORS)
    if renderer_type == "pil":
        return {
            key: convert_web_to_pil_color(value, mode)
            for key, value in SharedStylingConstants.COLORS.items()
        }
    raise ValueError(f"Unsupported renderer type: {renderer_type}")


def get_typography_for_renderer(
    renderer_type: Literal["html", "pil"],
) -> dict[str, Union[str, int]]:
    """
    Get typography formatted for the specified renderer type.

    Args:
        renderer_type: Type of renderer ("html" or "pil")

    Returns:
        Dictionary of typography values formatted for the specified renderer

    Raises:
        ValueError: If renderer_type is not supported
    """
    if renderer_type == "html":
        return SharedStylingConstants.TYPOGRAPHY["html"]
    if renderer_type == "pil":
        return SharedStylingConstants.TYPOGRAPHY["pil"]
    raise ValueError(f"Unsupported renderer type: {renderer_type}")


def get_layout_for_renderer(renderer_type: Literal["html", "epaper"]) -> dict[str, Union[str, int]]:
    """
    Get layout dimensions for the specified renderer type.

    Args:
        renderer_type: Type of renderer ("html" or "epaper")

    Returns:
        Dictionary of layout dimensions for the specified renderer

    Raises:
        ValueError: If renderer_type is not supported
    """
    if renderer_type == "html":
        return SharedStylingConstants.LAYOUTS["web"]
    if renderer_type == "epaper":
        return SharedStylingConstants.LAYOUTS["epaper_waveshare_42"]
    raise ValueError(f"Unsupported renderer type: {renderer_type}")


def convert_web_to_pil_color(hex_color: str, mode: str = "L") -> Union[int, tuple[int, int, int]]:
    """
    Convert a web hex color to a PIL-compatible color value.

    Args:
        hex_color: Hex color string (e.g., "#ffffff")
        mode: PIL image mode ("1", "L", or "RGB")

    Returns:
        Color value in PIL-compatible format

    Raises:
        ValueError: If hex_color format is invalid or mode is not supported
    """
    if not hex_color.startswith("#") or len(hex_color) != 7:
        raise ValueError(f"Invalid hex color format: {hex_color}")

    try:
        # Extract RGB components
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        if mode == "1":  # Monochrome (1-bit)
            # Convert to 0 or 1 based on luminance threshold
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return 0 if luminance < 128 else 1

        if mode == "L":  # Grayscale (8-bit)
            # Convert to grayscale using luminance formula
            return int(0.299 * r + 0.587 * g + 0.114 * b)

        if mode == "RGB":  # RGB color
            return (r, g, b)

        raise ValueError(f"Unsupported PIL image mode: {mode}")  # noqa: TRY301

    except ValueError as e:
        raise ValueError(f"Invalid hex color: {hex_color}") from e
