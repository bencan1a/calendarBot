"""
Unit tests for EInkWhatsNextRenderer integration with SharedStylingConstants.

These tests verify that the EInkWhatsNextRenderer properly integrates with
the SharedStylingConstants component for the unified rendering pipeline.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer

# Import shared styling components


def create_mock_display_capabilities(
    width: int = 400,
    height: int = 300,
    supports_partial_update: bool = True,
    supports_grayscale: bool = True,
    supports_red: bool = False,
) -> MagicMock:
    """Create mock display capabilities for testing.

    Args:
        width: Display width in pixels
        height: Display height in pixels
        supports_partial_update: Whether partial updates are supported
        supports_grayscale: Whether grayscale is supported
        supports_red: Whether red color is supported

    Returns:
        Mock display capabilities
    """
    capabilities = MagicMock()
    capabilities.width = width
    capabilities.height = height
    capabilities.supports_partial_update = supports_partial_update
    capabilities.supports_grayscale = supports_grayscale
    capabilities.supports_red = supports_red
    return capabilities


def create_mock_display(capabilities: Optional[MagicMock] = None) -> MagicMock:
    """Create mock display for testing.

    Args:
        capabilities: Optional display capabilities

    Returns:
        Mock display instance
    """
    display = MagicMock(spec=DisplayAbstractionLayer)
    display.capabilities = capabilities or create_mock_display_capabilities()
    display.initialize_called = False
    display.render_called = False
    display.render_buffer = None

    def mock_initialize():
        display.initialize_called = True
        return True

    def mock_render(content):
        display.render_called = True
        display.render_buffer = content
        return True

    def mock_get_capabilities():
        return display.capabilities

    display.initialize.side_effect = mock_initialize
    display.render.side_effect = mock_render
    display.get_capabilities.side_effect = mock_get_capabilities
    display.clear.return_value = True
    display.shutdown.return_value = True

    return display


def create_mock_event(
    subject: str = "Test Event",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    location: str = "Test Location",
    time_until_minutes: int = 30,
) -> MagicMock:
    """Create mock event for testing.

    Args:
        subject: Event subject
        start_time: Event start time
        end_time: Event end time
        location: Event location
        time_until_minutes: Minutes until event starts

    Returns:
        Mock event instance
    """
    event = MagicMock()
    event.subject = subject
    event.start_time = start_time or datetime.now() + timedelta(minutes=time_until_minutes)
    event.end_time = end_time or event.start_time + timedelta(hours=1)
    event.location = location
    event.time_until_minutes = time_until_minutes
    event.formatted_time_range = (
        f"{event.start_time.strftime('%H:%M')} - {event.end_time.strftime('%H:%M')}"
    )
    event.format_time_range.return_value = event.formatted_time_range
    return event


def create_mock_view_model(
    current_events: Optional[list[MagicMock]] = None,
    next_events: Optional[list[MagicMock]] = None,
    display_date: str = "2025-08-01",
) -> MagicMock:
    """Create mock view model for testing.

    Args:
        current_events: List of current events
        next_events: List of next events
        display_date: Display date

    Returns:
        Mock view model instance
    """
    view_model = MagicMock()
    view_model.current_events = current_events or []
    view_model.next_events = next_events or []
    view_model.display_date = display_date
    view_model.status_info = MagicMock()
    view_model.status_info.is_cached = False

    def get_next_event():
        return view_model.next_events[0] if view_model.next_events else None

    view_model.get_next_event.side_effect = get_next_event
    return view_model


@pytest.fixture
def mock_display() -> MagicMock:
    """Fixture for mock display.

    Returns:
        Mock display instance
    """
    return create_mock_display()


@pytest.fixture
def mock_settings() -> dict[str, Any]:
    """Fixture for mock settings.

    Returns:
        Mock settings dictionary
    """
    return {"display": {"type": "epaper"}}


@pytest.fixture
def mock_view_model_empty() -> MagicMock:
    """Fixture for empty view model.

    Returns:
        Empty view model
    """
    return create_mock_view_model()


@pytest.fixture
def mock_view_model_with_events() -> MagicMock:
    """Fixture for view model with events.

    Returns:
        View model with events
    """
    current_event = create_mock_event(
        subject="Current Meeting", time_until_minutes=0, location="Conference Room A"
    )
    next_event = create_mock_event(
        subject="Next Meeting", time_until_minutes=30, location="Conference Room B"
    )
    return create_mock_view_model(current_events=[current_event], next_events=[next_event])


@pytest.fixture
def mock_shared_styling() -> MagicMock:
    """Fixture for mock SharedStylingConstants.

    Returns:
        Mock SharedStylingConstants
    """
    mock = MagicMock()

    # Mock color constants
    mock.COLORS = {
        "background": "#ffffff",
        "background_secondary": "#f5f5f5",
        "text_primary": "#212529",
        "text_secondary": "#6c757d",
        "text_supporting": "#adb5bd",
        "accent": "#007bff",
        "urgent": "#dc3545",
    }

    # Mock typography constants
    mock.TYPOGRAPHY = {
        "html": {
            "countdown": "30px",
            "title": "24px",
            "subtitle": "18px",
            "body": "14px",
            "small": "12px",
        },
        "pil": {"countdown": 30, "title": 24, "subtitle": 18, "body": 14, "small": 12},
    }

    # Mock layout constants
    mock.LAYOUTS = {
        "web": {"width": "100%", "height": "100vh"},
        "epaper_waveshare_42": {"width": 400, "height": 300},
    }

    return mock


@pytest.fixture
def mock_get_colors_for_renderer() -> MagicMock:
    """Fixture for mock get_colors_for_renderer function.

    Returns:
        Mock get_colors_for_renderer function
    """
    mock = MagicMock()

    # Mock return value for "pil" renderer
    mock.return_value = {
        "background": 255,  # White in grayscale
        "background_secondary": 245,  # Light gray in grayscale
        "text_primary": 0,  # Black in grayscale
        "text_secondary": 100,  # Medium gray in grayscale
        "text_supporting": 173,  # Light gray in grayscale
        "accent": 50,  # Dark gray in grayscale (blue converted to grayscale)
        "urgent": 76,  # Medium gray in grayscale (red converted to grayscale)
    }

    return mock


@pytest.fixture
def mock_get_typography_for_renderer() -> MagicMock:
    """Fixture for mock get_typography_for_renderer function.

    Returns:
        Mock get_typography_for_renderer function
    """
    mock = MagicMock()

    # Mock return value for "pil" renderer
    mock.return_value = {"countdown": 30, "title": 24, "subtitle": 18, "body": 14, "small": 12}

    return mock


@pytest.fixture
def mock_get_layout_for_renderer() -> MagicMock:
    """Fixture for mock get_layout_for_renderer function.

    Returns:
        Mock get_layout_for_renderer function
    """
    mock = MagicMock()

    # Mock return value for "epaper" renderer
    mock.return_value = {"width": 400, "height": 300}

    return mock


class TestEInkWhatsNextRendererSharedStyling:
    """Test EInkWhatsNextRenderer integration with SharedStylingConstants."""

    def test_init_when_shared_styling_available_then_uses_shared_styling(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_shared_styling: MagicMock,
    ) -> None:
        """Test initialization with SharedStylingConstants.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_shared_styling: Mock SharedStylingConstants
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer"
        ) as mock_get_colors:
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer"
            ) as mock_get_typography:
                # Mock the get_colors_for_renderer and get_typography_for_renderer functions
                mock_get_colors.return_value = {"background": 255, "text_primary": 0, "accent": 50}
                mock_get_typography.return_value = {"countdown": 30, "title": 24}

                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Check that the renderer uses SharedStylingConstants
                mock_get_colors.assert_called_once_with("pil", mode="L")
                mock_get_typography.assert_called_once_with("pil")

                # Check that the renderer's colors and fonts are from SharedStylingConstants
                assert renderer._colors["background"] == 255
                assert renderer._colors["text_primary"] == 0
                assert renderer._colors["accent"] == 50

    def test_render_when_shared_styling_available_then_uses_shared_colors(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
        mock_shared_styling: MagicMock,
        mock_get_colors_for_renderer: MagicMock,
    ) -> None:
        """Test render method with SharedStylingConstants.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
            mock_shared_styling: Mock SharedStylingConstants
            mock_get_colors_for_renderer: Mock get_colors_for_renderer function
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer",
            mock_get_colors_for_renderer,
        ):
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer"
            ) as mock_get_typography:
                # Mock the get_typography_for_renderer function
                mock_get_typography.return_value = {
                    "countdown": 30,
                    "title": 24,
                    "subtitle": 18,
                    "body": 14,
                    "small": 12,
                }

                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Mock the internal render methods
                renderer._can_do_partial_update = MagicMock(return_value=False)
                renderer._render_full_image = MagicMock(return_value=Image.new("L", (100, 100)))

                # Render the view model
                result = renderer.render(mock_view_model_with_events)

                # Check that the renderer uses SharedStylingConstants colors
                mock_get_colors_for_renderer.assert_called_with("pil", mode="L")

                # Check that the result is a PIL Image
                assert isinstance(result, Image.Image)

    def test_render_zone1_when_shared_styling_available_then_uses_shared_typography(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_shared_styling: MagicMock,
        mock_get_typography_for_renderer: MagicMock,
    ) -> None:
        """Test _render_zone1_time_gap method with SharedStylingConstants.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_shared_styling: Mock SharedStylingConstants
            mock_get_typography_for_renderer: Mock get_typography_for_renderer function
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer"
        ) as mock_get_colors:
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer",
                mock_get_typography_for_renderer,
            ):
                # Mock the get_colors_for_renderer function
                mock_get_colors.return_value = {
                    "background": 255,
                    "background_secondary": 245,
                    "text_primary": 0,
                }

                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Create a mock ImageDraw
                mock_draw = MagicMock(spec=ImageDraw.ImageDraw)

                # Create a mock next event
                next_event = create_mock_event(subject="Test Event", time_until_minutes=30)

                # Mock the _draw_rounded_rectangle method
                renderer._draw_rounded_rectangle = MagicMock()

                # Call the _render_zone1_time_gap method
                renderer._render_zone1_time_gap(mock_draw, "L", next_event, 0, 0, 300, 130)

                # Check that the renderer uses SharedStylingConstants typography
                mock_get_typography_for_renderer.assert_called_with("pil")

                # Check that the _draw_rounded_rectangle method was called
                renderer._draw_rounded_rectangle.assert_called()

    def test_render_zone2_when_shared_styling_available_then_uses_shared_colors_and_typography(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_shared_styling: MagicMock,
        mock_get_colors_for_renderer: MagicMock,
        mock_get_typography_for_renderer: MagicMock,
    ) -> None:
        """Test _render_zone2_meeting_card method with SharedStylingConstants.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_shared_styling: Mock SharedStylingConstants
            mock_get_colors_for_renderer: Mock get_colors_for_renderer function
            mock_get_typography_for_renderer: Mock get_typography_for_renderer function
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer",
            mock_get_colors_for_renderer,
        ):
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer",
                mock_get_typography_for_renderer,
            ):
                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Create a mock ImageDraw
                mock_draw = MagicMock(spec=ImageDraw.ImageDraw)

                # Create a mock next event
                next_event = create_mock_event(subject="Test Event", time_until_minutes=30)

                # Mock the _draw_rounded_rectangle method
                renderer._draw_rounded_rectangle = MagicMock()

                # Call the _render_zone2_meeting_card method
                renderer._render_zone2_meeting_card(mock_draw, "L", next_event, 0, 130, 300, 200)

                # Check that the renderer uses SharedStylingConstants colors and typography
                mock_get_colors_for_renderer.assert_called_with("pil", mode="L")
                mock_get_typography_for_renderer.assert_called_with("pil")

                # Check that the _draw_rounded_rectangle method was called
                renderer._draw_rounded_rectangle.assert_called()

    def test_render_zone4_when_shared_styling_available_then_uses_shared_colors_and_typography(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
        mock_shared_styling: MagicMock,
        mock_get_colors_for_renderer: MagicMock,
        mock_get_typography_for_renderer: MagicMock,
    ) -> None:
        """Test _render_zone4_context method with SharedStylingConstants.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
            mock_shared_styling: Mock SharedStylingConstants
            mock_get_colors_for_renderer: Mock get_colors_for_renderer function
            mock_get_typography_for_renderer: Mock get_typography_for_renderer function
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer",
            mock_get_colors_for_renderer,
        ):
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer",
                mock_get_typography_for_renderer,
            ):
                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Create a mock ImageDraw
                mock_draw = MagicMock(spec=ImageDraw.ImageDraw)

                # Call the _render_zone4_context method
                renderer._render_zone4_context(
                    mock_draw,
                    "L",
                    mock_view_model_with_events,
                    0,
                    330,
                    300,
                    70,
                )

                # Check that the renderer uses SharedStylingConstants colors and typography
                mock_get_colors_for_renderer.assert_called_with("pil", mode="L")
                mock_get_typography_for_renderer.assert_called_with("pil")

    def test_render_full_image_when_shared_styling_available_then_uses_shared_layout(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
        mock_shared_styling: MagicMock,
        mock_get_layout_for_renderer: MagicMock,
    ) -> None:
        """Test _render_full_image method with SharedStylingConstants.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
            mock_shared_styling: Mock SharedStylingConstants
            mock_get_layout_for_renderer: Mock get_layout_for_renderer function
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer"
        ) as mock_get_colors:
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer"
            ) as mock_get_typography:
                with patch(
                    "calendarbot.display.epaper.integration.eink_whats_next_renderer.get_layout_for_renderer",
                    mock_get_layout_for_renderer,
                ):
                    # Mock the get_colors_for_renderer and get_typography_for_renderer functions
                    mock_get_colors.return_value = {"background": 255, "text_primary": 0}
                    mock_get_typography.return_value = {"countdown": 30, "title": 24}

                    # Initialize the renderer
                    renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                    # Mock the render zone methods
                    renderer._render_zone1_time_gap = MagicMock()
                    renderer._render_zone2_meeting_card = MagicMock()
                    renderer._render_zone4_context = MagicMock()

                    # Call the _render_full_image method
                    result = renderer._render_full_image(mock_view_model_with_events)

                    # Check that the renderer uses SharedStylingConstants layout
                    mock_get_layout_for_renderer.assert_called_with("epaper")

                    # Check that the result is a PIL Image with the correct dimensions
                    assert isinstance(result, Image.Image)
                    assert result.width == 400
                    assert result.height == 300

    def test_visual_consistency_when_compared_to_web_then_matches_styling(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_shared_styling: MagicMock,
    ) -> None:
        """Test visual consistency between web and e-paper renderers.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_shared_styling: Mock SharedStylingConstants
        """
        # Mock the imports - note that we're patching the imported functions directly
        with patch(
            "calendarbot.display.shared_styling.SharedStylingConstants", mock_shared_styling
        ):
            # Mock the CSS color values
            css_colors = {
                "background": "#ffffff",
                "background_secondary": "#f5f5f5",
                "text_primary": "#212529",
                "text_secondary": "#6c757d",
                "text_supporting": "#adb5bd",
                "accent": "#007bff",
                "urgent": "#dc3545",
            }

            # Mock the CSS typography values
            css_typography = {
                "countdown": "30px",
                "title": "24px",
                "subtitle": "18px",
                "body": "14px",
                "small": "12px",
            }

            # Check that SharedStylingConstants colors match CSS values
            for key, value in css_colors.items():
                assert key in mock_shared_styling.COLORS, f"COLORS should contain '{key}'"
                assert mock_shared_styling.COLORS[key].lower() == value.lower(), (
                    f"Color '{key}' should match CSS value"
                )

            # Check that SharedStylingConstants typography matches CSS values
            for key, value in css_typography.items():
                assert key in mock_shared_styling.TYPOGRAPHY["html"], (
                    f"HTML typography should contain '{key}'"
                )
                assert mock_shared_styling.TYPOGRAPHY["html"][key] == value, (
                    f"Typography '{key}' should match CSS value"
                )

                # Check that PIL values are numeric equivalents
                pil_value = int(value.replace("px", ""))
                assert mock_shared_styling.TYPOGRAPHY["pil"][key] == pil_value, (
                    f"PIL typography '{key}' should be numeric equivalent of CSS value"
                )
