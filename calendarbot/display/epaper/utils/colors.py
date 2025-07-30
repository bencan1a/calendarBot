"""
Color constants for e-Paper displays.

Extracts the grayscale color palette from the WhatsNext web CSS
to ensure consistency between web and e-Paper rendering.
"""

from typing import Dict, Tuple, Union


# E-Paper color palette extracted from calendarbot/web/static/layouts/whats-next-view/whats-next-view.css
class EPaperColors:
    """
    Color constants for e-Paper displays matching web CSS.

    Based on the 8-shade grayscale palette from WhatsNext view CSS:
    - :root section (lines 66-94)
    - .theme-eink section (lines 792-798)
    """

    # 8-Shade grayscale palette (from CSS :root section)
    GRAY_1 = "#ffffff"  # Lightest - 21:1 contrast with gray-8
    GRAY_2 = "#f5f5f5"  # Very light - 18.5:1 contrast with gray-8
    GRAY_3 = "#e0e0e0"  # Light - 12.6:1 contrast with gray-8
    GRAY_4 = "#bdbdbd"  # Medium light - 7.0:1 contrast with gray-8
    GRAY_5 = "#757575"  # Medium - 4.5:1 contrast with gray-1
    GRAY_6 = "#424242"  # Medium dark - 9.7:1 contrast with gray-1
    GRAY_7 = "#212121"  # Dark - 16.0:1 contrast with gray-1
    GRAY_8 = "#000000"  # Darkest - 21:1 contrast with gray-1

    # E-ink specific colors (from CSS .theme-eink section)
    EINK_BLACK = "#000000"
    EINK_DARK_GRAY = "#333333"
    EINK_MEDIUM_GRAY = "#666666"
    EINK_LIGHT_GRAY = "#cccccc"
    EINK_WHITE = "#ffffff"

    # Semantic color assignments (from CSS --background-primary, --text-primary, etc.)
    BACKGROUND_PRIMARY = GRAY_1  # --background-primary: var(--gray-1)
    BACKGROUND_SECONDARY = GRAY_2  # --background-secondary: var(--gray-2)
    BACKGROUND_TERTIARY = GRAY_3  # --background-tertiary: var(--gray-3)

    TEXT_CRITICAL = GRAY_8  # --text-critical: var(--gray-8) - 21:1 contrast
    TEXT_PRIMARY = GRAY_8  # --text-primary: var(--gray-8) - 21:1 contrast
    TEXT_SECONDARY = GRAY_6  # --text-secondary: var(--gray-6) - 9.7:1 contrast
    TEXT_SUPPORTING = GRAY_5  # --text-supporting: var(--gray-5) - 4.5:1 contrast
    TEXT_MUTED = GRAY_5  # --text-muted: var(--gray-5) - 4.5:1 contrast
    TEXT_CAPTION = GRAY_5  # --text-caption: var(--gray-5) - 4.5:1 contrast

    BORDER_LIGHT = GRAY_3  # --border-light: var(--gray-3)
    BORDER_MEDIUM = GRAY_4  # --border-medium: var(--gray-4)
    BORDER_STRONG = GRAY_6  # --border-strong: var(--gray-6)
    BORDER_CRITICAL = GRAY_8  # --border-critical: var(--gray-8)

    SURFACE_RAISED = GRAY_1  # --surface-raised: var(--gray-1)
    SURFACE_SUNKEN = GRAY_2  # --surface-sunken: var(--gray-2)
    SURFACE_RECESSED = GRAY_3  # --surface-recessed: var(--gray-3)


def get_epaper_color_palette() -> Dict[str, str]:
    """
    Get the complete e-Paper color palette.

    Returns:
        Dictionary mapping semantic color names to hex values
    """
    return {
        # Grayscale shades
        "gray_1": EPaperColors.GRAY_1,
        "gray_2": EPaperColors.GRAY_2,
        "gray_3": EPaperColors.GRAY_3,
        "gray_4": EPaperColors.GRAY_4,
        "gray_5": EPaperColors.GRAY_5,
        "gray_6": EPaperColors.GRAY_6,
        "gray_7": EPaperColors.GRAY_7,
        "gray_8": EPaperColors.GRAY_8,
        # E-ink specific
        "eink_black": EPaperColors.EINK_BLACK,
        "eink_dark_gray": EPaperColors.EINK_DARK_GRAY,
        "eink_medium_gray": EPaperColors.EINK_MEDIUM_GRAY,
        "eink_light_gray": EPaperColors.EINK_LIGHT_GRAY,
        "eink_white": EPaperColors.EINK_WHITE,
        # Semantic backgrounds
        "background_primary": EPaperColors.BACKGROUND_PRIMARY,
        "background_secondary": EPaperColors.BACKGROUND_SECONDARY,
        "background_tertiary": EPaperColors.BACKGROUND_TERTIARY,
        # Semantic text colors
        "text_critical": EPaperColors.TEXT_CRITICAL,
        "text_primary": EPaperColors.TEXT_PRIMARY,
        "text_secondary": EPaperColors.TEXT_SECONDARY,
        "text_supporting": EPaperColors.TEXT_SUPPORTING,
        "text_muted": EPaperColors.TEXT_MUTED,
        "text_caption": EPaperColors.TEXT_CAPTION,
        # Semantic borders
        "border_light": EPaperColors.BORDER_LIGHT,
        "border_medium": EPaperColors.BORDER_MEDIUM,
        "border_strong": EPaperColors.BORDER_STRONG,
        "border_critical": EPaperColors.BORDER_CRITICAL,
        # Semantic surfaces
        "surface_raised": EPaperColors.SURFACE_RAISED,
        "surface_sunken": EPaperColors.SURFACE_SUNKEN,
        "surface_recessed": EPaperColors.SURFACE_RECESSED,
    }


def get_rendering_colors() -> Dict[str, str]:
    """
    Get colors optimized for e-Paper rendering.

    Returns:
        Dictionary of colors for common rendering scenarios
    """
    return {
        "background": EPaperColors.BACKGROUND_PRIMARY,
        "background_secondary": EPaperColors.BACKGROUND_SECONDARY,  # Gray backgrounds for containers
        "text_title": EPaperColors.TEXT_PRIMARY,  # High contrast for titles
        "text_body": EPaperColors.TEXT_PRIMARY,  # High contrast for body text
        "text_subtitle": EPaperColors.TEXT_SECONDARY,  # Medium contrast for subtitles
        "text_meta": EPaperColors.TEXT_MUTED,  # Lower contrast for metadata
        # Add missing keys expected by renderer
        "text_primary": EPaperColors.TEXT_PRIMARY,  # Primary text color (black)
        "text_secondary": EPaperColors.TEXT_SECONDARY,  # Secondary text color (medium gray)
        "text_supporting": EPaperColors.TEXT_SUPPORTING,  # Supporting text color (light gray)
        "border": EPaperColors.BORDER_MEDIUM,  # Medium border contrast
        "accent": EPaperColors.EINK_BLACK,  # Maximum contrast for accents
    }


def convert_to_pil_color(hex_color: str, mode: str = "L") -> Union[str, int, Tuple[int, int, int]]:
    """
    Convert hex color to PIL-compatible format based on image mode.

    Args:
        hex_color: Hex color string (e.g., "#333333")
        mode: PIL image mode ("1", "L", "RGB")

    Returns:
        Color in appropriate format for PIL

    Raises:
        ValueError: If hex_color format is invalid
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
            luminance = int(0.299 * r + 0.587 * g + 0.114 * b)
            return luminance

        if mode == "RGB":  # RGB color
            return (r, g, b)

        raise ValueError(f"Unsupported PIL image mode: {mode}")

    except ValueError as e:
        raise ValueError(f"Invalid hex color: {hex_color}") from e


def is_grayscale_color(hex_color: str) -> bool:
    """
    Check if a hex color is grayscale (R=G=B values).

    Args:
        hex_color: Hex color string to check

    Returns:
        True if color is grayscale, False otherwise

    Raises:
        ValueError: If hex_color format is invalid
    """
    if not hex_color.startswith("#") or len(hex_color) != 7:
        raise ValueError(f"Invalid hex color format: {hex_color}")

    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return r == g == b
    except ValueError as e:
        raise ValueError(f"Invalid hex color: {hex_color}") from e


def validate_epaper_palette() -> Tuple[bool, Dict[str, str]]:
    """
    Validate that all colors in the e-Paper palette are grayscale-compliant.

    Returns:
        Tuple of (all_valid, validation_report)
    """
    palette = get_epaper_color_palette()
    report = {}
    all_valid = True

    for name, color in palette.items():
        try:
            is_valid = is_grayscale_color(color)
            report[name] = "valid" if is_valid else f"invalid: {color} not grayscale"
            if not is_valid:
                all_valid = False
        except ValueError as e:
            report[name] = f"error: {e}"
            all_valid = False

    return all_valid, report


# Convenience constants for direct use
WHITE = EPaperColors.EINK_WHITE
BLACK = EPaperColors.EINK_BLACK
LIGHT_GRAY = EPaperColors.EINK_LIGHT_GRAY
MEDIUM_GRAY = EPaperColors.EINK_MEDIUM_GRAY
DARK_GRAY = EPaperColors.EINK_DARK_GRAY
