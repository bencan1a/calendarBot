"""
Unit tests for SharedStylingConstants.

These tests verify that the SharedStylingConstants module provides consistent styling
constants for both web (HTML) and e-paper (PIL) rendering to ensure visual consistency
across different output formats.
"""

from unittest.mock import patch

# Import the implemented SharedStylingConstants
from calendarbot.display.shared_styling import (
    SharedStylingConstants,
    convert_web_to_pil_color,
    get_colors_for_renderer,
    get_layout_for_renderer,
    get_typography_for_renderer,
)


class TestSharedStylingConstants:
    """Test the SharedStylingConstants class."""

    def test_colors_when_accessed_then_contains_required_keys(self) -> None:
        """Test that COLORS contains all required keys."""
        # Get the colors from the implemented SharedStylingConstants
        colors = SharedStylingConstants.COLORS

        # Required color keys
        required_keys = [
            "background",
            "background_secondary",
            "text_primary",
            "text_secondary",
            "text_supporting",
            "accent",
            "urgent",
        ]

        for key in required_keys:
            assert key in colors, f"COLORS should contain '{key}'"
            assert colors[key].startswith("#"), f"Color '{key}' should be a hex value"
            assert len(colors[key]) == 7, f"Color '{key}' should be a 6-digit hex value"

    def test_typography_when_accessed_then_contains_html_and_pil_formats(self) -> None:
        """Test that TYPOGRAPHY contains both HTML and PIL formats."""
        # Get the typography from the implemented SharedStylingConstants
        typography = SharedStylingConstants.TYPOGRAPHY

        # Check structure
        assert "html" in typography, "TYPOGRAPHY should contain 'html' key"
        assert "pil" in typography, "TYPOGRAPHY should contain 'pil' key"

        # Required typography keys
        required_keys = ["countdown", "title", "subtitle", "body", "small"]

        # Check HTML typography
        for key in required_keys:
            assert key in typography["html"], f"HTML typography should contain '{key}'"
            assert isinstance(typography["html"][key], str), (
                f"HTML typography '{key}' should be a string"
            )
            assert "px" in typography["html"][key], f"HTML typography '{key}' should include 'px'"

        # Check PIL typography
        for key in required_keys:
            assert key in typography["pil"], f"PIL typography should contain '{key}'"
            assert isinstance(typography["pil"][key], int), (
                f"PIL typography '{key}' should be an integer"
            )

    def test_layouts_when_accessed_then_contains_web_and_epaper_formats(self) -> None:
        """Test that LAYOUTS contains both web and e-paper formats."""
        # Get the layouts from the implemented SharedStylingConstants
        layouts = SharedStylingConstants.LAYOUTS

        # Check structure
        assert "web" in layouts, "LAYOUTS should contain 'web' key"
        assert "epaper_waveshare_42" in layouts, "LAYOUTS should contain 'epaper_waveshare_42' key"

        # Check web layout
        assert "width" in layouts["web"], "Web layout should contain 'width'"
        assert "height" in layouts["web"], "Web layout should contain 'height'"
        assert layouts["web"]["width"] == "100%", "Web width should be '100%'"
        assert layouts["web"]["height"] == "100vh", "Web height should be '100vh'"

        # Check e-paper layout
        assert "width" in layouts["epaper_waveshare_42"], "E-paper layout should contain 'width'"
        assert "height" in layouts["epaper_waveshare_42"], "E-paper layout should contain 'height'"
        assert layouts["epaper_waveshare_42"]["width"] == 400, "E-paper width should be 400"
        assert layouts["epaper_waveshare_42"]["height"] == 300, "E-paper height should be 300"

    def test_get_colors_for_renderer_when_html_then_returns_hex_values(self) -> None:
        """Test that get_colors_for_renderer returns hex values for HTML renderer."""
        # Get colors from the implemented function
        colors = get_colors_for_renderer("html")

        # Check that colors are hex values
        for key, value in colors.items():
            assert isinstance(value, str), f"HTML color '{key}' should be a string"
            assert value.startswith("#"), f"HTML color '{key}' should be a hex value"

    def test_get_colors_for_renderer_when_pil_then_returns_pil_compatible_values(self) -> None:
        """Test that get_colors_for_renderer returns PIL-compatible values for PIL renderer."""
        # Get colors from the implemented function
        colors = get_colors_for_renderer("pil", mode="L")

        # Check that colors are PIL-compatible (integers for grayscale)
        for key, value in colors.items():
            assert isinstance(value, int), f"PIL color '{key}' should be an integer"
            assert 0 <= value <= 255, f"PIL color '{key}' should be between 0 and 255"

    def test_get_typography_for_renderer_when_html_then_returns_px_values(self) -> None:
        """Test that get_typography_for_renderer returns px values for HTML renderer."""
        # Get typography from the implemented function
        typography = get_typography_for_renderer("html")

        # Check that typography values are px strings
        for key, value in typography.items():
            assert isinstance(value, str), f"HTML typography '{key}' should be a string"
            assert "px" in value, f"HTML typography '{key}' should include 'px'"

    def test_get_typography_for_renderer_when_pil_then_returns_integer_values(self) -> None:
        """Test that get_typography_for_renderer returns integer values for PIL renderer."""
        # Get typography from the implemented function
        typography = get_typography_for_renderer("pil")

        # Check that typography values are integers
        for key, value in typography.items():
            assert isinstance(value, int), f"PIL typography '{key}' should be an integer"
            assert value > 0, f"PIL typography '{key}' should be positive"

    def test_get_layout_for_renderer_when_html_then_returns_responsive_values(self) -> None:
        """Test that get_layout_for_renderer returns responsive values for HTML renderer."""
        # Get layout from the implemented function
        layout = get_layout_for_renderer("html")

        # Check that layout values are responsive
        assert layout["width"] == "100%", "HTML width should be '100%'"
        assert layout["height"] == "100vh", "HTML height should be '100vh'"

    def test_get_layout_for_renderer_when_epaper_then_returns_fixed_dimensions(self) -> None:
        """Test that get_layout_for_renderer returns fixed dimensions for e-paper renderer."""
        # Get layout from the implemented function
        layout = get_layout_for_renderer("epaper")

        # Check that layout values are fixed dimensions
        assert layout["width"] == 400, "E-paper width should be 400"
        assert layout["height"] == 300, "E-paper height should be 300"

    def test_convert_web_to_pil_color_when_hex_then_returns_pil_compatible_value(self) -> None:
        """Test that convert_web_to_pil_color converts hex to PIL-compatible value."""
        # Test black color conversion
        black_hex = "#000000"
        black_pil = convert_web_to_pil_color(black_hex, mode="L")
        assert black_pil == 0, "Black should convert to 0 in grayscale mode"

        # Test white color conversion
        white_hex = "#ffffff"
        white_pil = convert_web_to_pil_color(white_hex, mode="L")
        assert white_pil == 255, "White should convert to 255 in grayscale mode"

        # Test RGB mode
        rgb_pil = convert_web_to_pil_color("#ff0000", mode="RGB")
        assert rgb_pil == (255, 0, 0), "Red should convert to (255, 0, 0) in RGB mode"

    def test_color_consistency_when_compared_to_css_then_matches_values(self) -> None:
        """Test that color constants match the values in the CSS."""
        # Get colors from the implemented SharedStylingConstants
        colors = SharedStylingConstants.COLORS

        # CSS color values from whats-next-view.css
        css_colors = {
            "background": "#ffffff",  # --gray-1
            "background_secondary": "#f5f5f5",  # --gray-2
            "text_primary": "#212529",  # --text-primary
            "text_secondary": "#6c757d",  # --text-secondary
            "text_supporting": "#adb5bd",  # --text-supporting
            "accent": "#007bff",  # --accent
            "urgent": "#dc3545",  # --urgent
        }

        # Check that colors match CSS values
        for key, value in css_colors.items():
            assert key in colors, f"COLORS should contain '{key}'"
            assert colors[key].lower() == value.lower(), f"Color '{key}' should match CSS value"

    def test_typography_consistency_when_compared_to_css_then_matches_values(self) -> None:
        """Test that typography constants match the values in the CSS."""
        # Get typography from the implemented SharedStylingConstants
        typography = SharedStylingConstants.TYPOGRAPHY

        # CSS typography values from whats-next-view.css
        css_typography = {
            "countdown": "30px",  # Based on countdown-time font-size
            "title": "24px",  # Based on meeting-title font-size
            "subtitle": "18px",  # Based on subtitle font-size
            "body": "14px",  # Based on body text font-size
            "small": "12px",  # Based on small text font-size
        }

        # Check that typography matches CSS values
        for key, value in css_typography.items():
            assert key in typography["html"], f"HTML typography should contain '{key}'"
            assert typography["html"][key] == value, f"Typography '{key}' should match CSS value"

            # Check that PIL values are numeric equivalents
            pil_value = int(value.replace("px", ""))
            assert typography["pil"][key] == pil_value, (
                f"PIL typography '{key}' should be numeric equivalent of CSS value"
            )

    def test_layout_consistency_when_compared_to_css_then_matches_values(self) -> None:
        """Test that layout constants match the values in the CSS."""
        # Get layouts from the implemented SharedStylingConstants
        layouts = SharedStylingConstants.LAYOUTS

        # CSS layout values from whats-next-view.css
        css_layouts = {
            "web": {"width": "100%", "height": "100vh"},
            "epaper_waveshare_42": {"width": 400, "height": 300},
        }

        # Check that layouts match CSS values
        for layout_key, layout_values in css_layouts.items():
            assert layout_key in layouts, f"LAYOUTS should contain '{layout_key}'"
            for key, value in layout_values.items():
                assert key in layouts[layout_key], f"Layout '{layout_key}' should contain '{key}'"
                assert layouts[layout_key][key] == value, (
                    f"Layout '{layout_key}.{key}' should match CSS value"
                )


class TestSharedStylingIntegration:
    """Test the integration of SharedStylingConstants with other components."""

    def test_integration_when_imported_by_eink_renderer_then_provides_consistent_styling(
        self,
    ) -> None:
        """Test that SharedStylingConstants can be imported by EInkWhatsNextRenderer."""
        # Import the implemented SharedStylingConstants and EInkWhatsNextRenderer
        from calendarbot.display.epaper.integration.eink_whats_next_renderer import (
            EInkWhatsNextRenderer,
        )
        from calendarbot.display.shared_styling import (
            get_colors_for_renderer,
        )

        # Mock the get_colors_for_renderer function to use our SharedStylingConstants
        with patch(
            "calendarbot.display.shared_styling.get_colors_for_renderer",
            side_effect=get_colors_for_renderer,
        ):
            # Create a renderer instance
            renderer = EInkWhatsNextRenderer({"display": {"type": "epaper"}})

            # Check that renderer uses colors from SharedStylingConstants
            assert "background" in renderer._colors
            assert "text_primary" in renderer._colors

    def test_integration_when_imported_by_html_renderer_then_provides_consistent_styling(
        self,
    ) -> None:
        """Test that SharedStylingConstants can be imported by WhatsNextRenderer."""
        # Import the implemented SharedStylingConstants
        from calendarbot.display.shared_styling import SharedStylingConstants
        from calendarbot.display.whats_next_renderer import WhatsNextRenderer

        # We're using WhatsNextRenderer instead of WhatsNextHTMLRenderer
        with patch(
            "calendarbot.display.whats_next_renderer.SharedStylingConstants", SharedStylingConstants
        ):
            # Create a renderer instance
            renderer = WhatsNextRenderer({"display": {"type": "html"}})

            # Check that the renderer's _get_css_styles method uses SharedStylingConstants
            css = renderer._get_css_styles()
            assert SharedStylingConstants.COLORS["background"] in css
            assert SharedStylingConstants.COLORS["text_primary"] in css
