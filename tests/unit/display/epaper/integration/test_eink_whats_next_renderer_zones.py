"""
Unit tests for the zone-specific rendering functionality of EInkWhatsNextRenderer.

These tests focus on the zone-specific rendering aspects:
- Zone 1 (Time gap) rendering with/without next event
- Zone 2 (Meeting card) rendering with different event data
- Zone 4 (Context) rendering with different states
- Layout and positioning verification
- Text truncation and formatting
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock, call
from typing import Any, Dict, List, Optional, Tuple, cast

from PIL import Image, ImageDraw, ImageFont

from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.whats_next_data_model import WhatsNextViewModel, EventData, StatusInfo
from calendarbot.display.whats_next_logic import WhatsNextLogic
from calendarbot.cache.models import CachedEvent


class MockDisplayCapabilities:
    """Mock display capabilities for testing."""
    
    def __init__(
        self,
        width: int = 300,
        height: int = 400,
        colors: int = 2,
        supports_partial_update: bool = True,
        supports_grayscale: bool = True,
        supports_red: bool = False
    ) -> None:
        """Initialize mock display capabilities.
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
            colors: Number of colors supported
            supports_partial_update: Whether partial updates are supported
            supports_grayscale: Whether grayscale is supported
            supports_red: Whether red color is supported
        """
        self.width = width
        self.height = height
        self.colors = colors
        self.supports_partial_update = supports_partial_update
        self.supports_grayscale = supports_grayscale
        self.supports_red = supports_red


class MockDisplay(DisplayAbstractionLayer):
    """Mock display for testing."""
    
    def __init__(
        self, 
        capabilities: Optional[MockDisplayCapabilities] = None,
        initialize_success: bool = True,
        render_success: bool = True
    ) -> None:
        """Initialize mock display.
        
        Args:
            capabilities: Optional display capabilities
            initialize_success: Whether initialize() should return success
            render_success: Whether render() should return success
        """
        self.capabilities = capabilities or MockDisplayCapabilities()
        self.initialize_called = False
        self.render_called = False
        self.render_buffer = None
        self.initialize_success = initialize_success
        self.render_success = render_success
    
    def initialize(self) -> bool:
        """Mock initialize method.
        
        Returns:
            True if initialization was successful based on initialize_success
        """
        self.initialize_called = True
        return self.initialize_success
    
    def render(self, buffer: Any) -> bool:
        """Mock render method.
        
        Args:
            buffer: Display buffer to render
            
        Returns:
            True if render was successful based on render_success
        """
        self.render_called = True
        self.render_buffer = buffer
        return self.render_success
    
    def get_capabilities(self) -> MockDisplayCapabilities:
        """Get display capabilities.
        
        Returns:
            Display capabilities
        """
        return self.capabilities
    
    def clear(self) -> bool:
        """Clear the display.
        
        Returns:
            True if clearing was successful
        """
        return True
    
    def shutdown(self) -> bool:
        """Shutdown the display.
        
        Returns:
            True if shutdown was successful
        """
        return True


class MockEventData:
    """Mock event data for testing."""
    
    def __init__(
        self,
        subject: str = "Test Event",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = "Test Location",
        time_until_minutes: int = 30,
        formatted_time_range: str = "10:00 - 11:00"
    ) -> None:
        """Initialize mock event data.
        
        Args:
            subject: Event subject
            start_time: Event start time
            end_time: Event end time
            location: Event location
            time_until_minutes: Minutes until event starts
            formatted_time_range: Formatted time range string
        """
        self.subject = subject
        self.start_time = start_time or datetime.now() + timedelta(minutes=time_until_minutes)
        self.end_time = end_time or self.start_time + timedelta(hours=1)
        self.location = location
        self.time_until_minutes = time_until_minutes
        self.formatted_time_range = formatted_time_range


class MockViewModel:
    """Mock view model for testing."""
    
    def __init__(
        self,
        current_events: Optional[List[MockEventData]] = None,
        next_events: Optional[List[MockEventData]] = None,
        display_date: str = "2025-08-01",
        is_cached: bool = False
    ) -> None:
        """Initialize mock view model.
        
        Args:
            current_events: List of current events
            next_events: List of next events
            display_date: Display date
            is_cached: Whether data is cached
        """
        self.current_events = current_events or []
        self.next_events = next_events or []
        self.display_date = display_date
        self.status_info = MagicMock()
        self.status_info.is_cached = is_cached
    
    def get_next_event(self) -> Optional[MockEventData]:
        """Get next event.
        
        Returns:
            Next event or None if no next events
        """
        return self.next_events[0] if self.next_events else None


@pytest.fixture
def mock_display() -> MockDisplay:
    """Fixture for mock display.
    
    Returns:
        Mock display instance
    """
    return MockDisplay()


@pytest.fixture
def mock_settings() -> Dict[str, Any]:
    """Fixture for mock settings.
    
    Returns:
        Mock settings dictionary
    """
    return {"display": {"type": "epaper"}}


@pytest.fixture
def mock_view_model_empty() -> MockViewModel:
    """Fixture for empty view model.
    
    Returns:
        Empty view model
    """
    return MockViewModel()


@pytest.fixture
def mock_view_model_with_next_event() -> MockViewModel:
    """Fixture for view model with next event.
    
    Returns:
        View model with next event
    """
    next_event = MockEventData(
        subject="Next Meeting",
        time_until_minutes=30,
        location="Conference Room B"
    )
    return MockViewModel(
        next_events=[next_event]
    )


@pytest.fixture
def mock_view_model_with_long_event_data() -> MockViewModel:
    """Fixture for view model with long event data for truncation testing.
    
    Returns:
        View model with long event data
    """
    next_event = MockEventData(
        subject="This is a very long event title that should be truncated in the renderer",
        time_until_minutes=45,
        location="This is a very long location name that should also be truncated in the renderer"
    )
    return MockViewModel(
        next_events=[next_event]
    )


@pytest.fixture
def mock_view_model_with_current_event() -> MockViewModel:
    """Fixture for view model with current event.
    
    Returns:
        View model with current event
    """
    current_event = MockEventData(
        subject="Current Meeting",
        time_until_minutes=0,
        location="Conference Room A"
    )
    return MockViewModel(
        current_events=[current_event]
    )


@pytest.fixture
def mock_view_model_with_cached_data() -> MockViewModel:
    """Fixture for view model with cached data.
    
    Returns:
        View model with cached data
    """
    next_event = MockEventData(
        subject="Next Meeting",
        time_until_minutes=30,
        location="Conference Room B"
    )
    return MockViewModel(
        next_events=[next_event],
        is_cached=True
    )


@pytest.fixture
def mock_renderer(mock_settings: Dict[str, Any], mock_display: MockDisplay) -> EInkWhatsNextRenderer:
    """Fixture for mock renderer with patched drawing methods.
    
    Args:
        mock_settings: Mock settings
        mock_display: Mock display
        
    Returns:
        Mock renderer instance
    """
    renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
    
    # Mock font loading to avoid system font dependencies
    renderer._fonts = {
        "countdown": MagicMock(spec=ImageFont.FreeTypeFont),
        "title": MagicMock(spec=ImageFont.FreeTypeFont),
        "subtitle": MagicMock(spec=ImageFont.FreeTypeFont),
        "body": MagicMock(spec=ImageFont.FreeTypeFont),
        "small": MagicMock(spec=ImageFont.FreeTypeFont)
    }
    
    # Mock text measurement
    for font_mock in renderer._fonts.values():
        font_mock.getbbox = MagicMock(return_value=(0, 0, 100, 20))
    
    # Mock drawing methods
    renderer._draw_rounded_rectangle = MagicMock()
    renderer._draw_rounded_rectangle_outline = MagicMock()
    
    return renderer


class TestEInkWhatsNextRendererZones:
    """Test zone-specific rendering functionality of EInkWhatsNextRenderer."""
    
    def test_render_zone1_when_no_next_event_then_renders_plenty_of_time(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test rendering Zone 1 with no next event.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        mock_draw.textbbox.return_value = (0, 0, 100, 20)
        
        # Call the zone rendering method with no next event
        mock_renderer._render_zone1_time_gap(
            draw=mock_draw,
            mode="L",
            next_event=None,
            x=0,
            y=0,
            width=300,
            height=130
        )
        
        # Verify the "Plenty of time" text was drawn
        text_calls = [call for call in mock_draw.text.call_args_list if "Plenty of time" in call[0][1]]
        assert len(text_calls) == 1, "Should draw 'Plenty of time' text"
        
        # Verify rounded rectangle was drawn
        assert mock_draw.textbbox.called, "Should measure text for positioning"
        assert mock_renderer._draw_rounded_rectangle.call_count > 0, "Should draw rounded rectangle container"
    
    def test_render_zone1_when_has_next_event_then_renders_time_remaining(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_next_event: MockViewModel
    ) -> None:
        """Test rendering Zone 1 with next event.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_next_event: Mock view model with next event
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        mock_draw.textbbox.return_value = (0, 0, 200, 30)
        
        # Get the next event
        next_event = mock_view_model_with_next_event.get_next_event()
        
        # Call the zone rendering method with next event
        mock_renderer._render_zone1_time_gap(
            draw=mock_draw,
            mode="L",
            next_event=next_event,
            x=0,
            y=0,
            width=300,
            height=130
        )
        
        # Verify the time remaining text was drawn
        text_calls = [call for call in mock_draw.text.call_args_list if "STARTS IN" in call[0][1]]
        assert len(text_calls) == 1, "Should draw time remaining text"
        
        # Verify the time text was drawn
        text_calls = [call[0][1] for call in mock_draw.text.call_args_list]
        assert any("MINUTES" in text for text in text_calls), "Should draw time remaining text"
        
        # Verify rounded rectangle was drawn
        assert mock_draw.textbbox.called, "Should measure text for positioning"
        assert mock_renderer._draw_rounded_rectangle.call_count > 0, "Should draw rounded rectangle container"
    
    def test_render_zone1_when_different_time_values_then_formats_correctly(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test rendering Zone 1 with different time values.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        mock_draw.textbbox.return_value = (0, 0, 200, 30)
        
        # Test with minutes < 60
        event_minutes = MockEventData(time_until_minutes=45)
        mock_renderer._render_zone1_time_gap(
            draw=mock_draw,
            mode="L",
            next_event=event_minutes,
            x=0,
            y=0,
            width=300,
            height=130
        )
        
        # Test with hours only (no remaining minutes)
        event_hours = MockEventData(time_until_minutes=120)
        mock_renderer._render_zone1_time_gap(
            draw=mock_draw,
            mode="L",
            next_event=event_hours,
            x=0,
            y=0,
            width=300,
            height=130
        )
        
        # Test with hours and minutes
        event_mixed = MockEventData(time_until_minutes=125)
        mock_renderer._render_zone1_time_gap(
            draw=mock_draw,
            mode="L",
            next_event=event_mixed,
            x=0,
            y=0,
            width=300,
            height=130
        )
        
        # Verify all three time formats were used
        text_calls = [call[0][1] for call in mock_draw.text.call_args_list]
        assert any("45 MINUTES" in text for text in text_calls), "Should format minutes correctly"
        assert any("2 HOURS" in text for text in text_calls), "Should format hours correctly"
        assert any("2 HOURS 5 MINUTES" in text for text in text_calls), "Should format hours and minutes correctly"
    
    def test_render_zone2_when_no_next_event_then_renders_nothing(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test rendering Zone 2 with no next event.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        
        # Call the zone rendering method with no next event
        mock_renderer._render_zone2_meeting_card(
            draw=mock_draw,
            mode="L",
            next_event=None,
            x=0,
            y=130,
            width=300,
            height=200
        )
        
        # Verify no drawing methods were called
        assert not mock_draw.text.called, "Should not draw any text"
        assert mock_renderer._draw_rounded_rectangle.call_count == 0, "Should not draw rounded rectangle"
    
    def test_render_zone2_when_has_next_event_then_renders_event_details(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_next_event: MockViewModel
    ) -> None:
        """Test rendering Zone 2 with next event.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_next_event: Mock view model with next event
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        
        # Get the next event
        next_event = mock_view_model_with_next_event.get_next_event()
        
        # Call the zone rendering method with next event
        mock_renderer._render_zone2_meeting_card(
            draw=mock_draw,
            mode="L",
            next_event=next_event,
            x=0,
            y=130,
            width=300,
            height=200
        )
        
        # Verify the event details were drawn
        text_calls = [call[0][1] for call in mock_draw.text.call_args_list]
        assert any(next_event.subject in text for text in text_calls), "Should draw event subject"
        assert any(next_event.formatted_time_range in text for text in text_calls), "Should draw time range"
        assert any(next_event.location in text for text in text_calls), "Should draw location"
        
        # Verify rounded rectangle was drawn
        assert mock_renderer._draw_rounded_rectangle.call_count > 0, "Should draw rounded rectangle container"
    
    def test_render_zone2_when_long_text_then_truncates_properly(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_long_event_data: MockViewModel
    ) -> None:
        """Test rendering Zone 2 with long text that needs truncation.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_long_event_data: Mock view model with long event data
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        
        # Get the next event with long data
        next_event = mock_view_model_with_long_event_data.get_next_event()
        
        # Call the zone rendering method with next event
        mock_renderer._render_zone2_meeting_card(
            draw=mock_draw,
            mode="L",
            next_event=next_event,
            x=0,
            y=130,
            width=300,
            height=200
        )
        
        # Verify the truncated text was drawn
        text_calls = [call[0][1] for call in mock_draw.text.call_args_list]
        
        # Subject should be truncated to 30 chars + "..."
        truncated_subject = next_event.subject[:30] + "..."
        assert any(truncated_subject in text for text in text_calls), "Should truncate long subject"
        
        # Location should be truncated to 25 chars + "..."
        truncated_location = f"📍 {next_event.location[:25]}..."
        assert any(truncated_location in text for text in text_calls), "Should truncate long location"
    
    def test_render_zone4_when_no_next_event_then_renders_focus_message(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_empty: MockViewModel
    ) -> None:
        """Test rendering Zone 4 with no next event.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_empty: Empty mock view model
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        mock_draw.textbbox.return_value = (0, 0, 150, 12)
        
        # Call the zone rendering method with empty view model
        mock_renderer._render_zone4_context(
            draw=mock_draw,
            mode="L",
            view_model=mock_view_model_empty,
            x=0,
            y=330,
            width=300,
            height=70
        )
        
        # Verify the focus message was drawn
        text_calls = [call for call in mock_draw.text.call_args_list if "Plenty of time to focus" in call[0][1]]
        assert len(text_calls) == 1, "Should draw focus message"
        
        # Verify text positioning was calculated
        assert mock_draw.textbbox.called, "Should measure text for positioning"
    
    def test_render_zone4_when_has_next_event_then_renders_appropriate_message(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_next_event: MockViewModel
    ) -> None:
        """Test rendering Zone 4 with next event.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_next_event: Mock view model with next event
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        mock_draw.textbbox.return_value = (0, 0, 150, 12)
        
        # Call the zone rendering method with view model containing next event
        mock_renderer._render_zone4_context(
            draw=mock_draw,
            mode="L",
            view_model=mock_view_model_with_next_event,
            x=0,
            y=330,
            width=300,
            height=70
        )
        
        # Verify an appropriate message was drawn based on time until next event
        text_calls = [call[0][1] for call in mock_draw.text.call_args_list]
        assert any(message in text for text in text_calls for message in [
            "Meeting starting soon",
            "Upcoming meeting",
            "Meeting within the hour",
            "Next meeting scheduled"
        ]), "Should draw appropriate message based on time until next event"
    
    def test_render_zone4_when_cached_data_then_renders_cached_message(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_cached_data: MockViewModel
    ) -> None:
        """Test rendering Zone 4 with cached data.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_cached_data: Mock view model with cached data
        """
        # Create a mock draw object
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
        mock_draw.textbbox.return_value = (0, 0, 150, 12)
        
        # Modify the next event to have no time_until_minutes to force fallback to cached status
        next_event = mock_view_model_with_cached_data.get_next_event()
        delattr(next_event, "time_until_minutes")
        
        # Call the zone rendering method with view model containing cached data
        mock_renderer._render_zone4_context(
            draw=mock_draw,
            mode="L",
            view_model=mock_view_model_with_cached_data,
            x=0,
            y=330,
            width=300,
            height=70
        )
        
        # Verify the cached data message was drawn
        text_calls = [call for call in mock_draw.text.call_args_list if "Cached data" in call[0][1]]
        assert len(text_calls) == 1, "Should draw cached data message"
    
    def test_render_full_image_when_called_then_renders_all_zones_with_correct_layout(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_next_event: MockViewModel
    ) -> None:
        """Test that full image rendering calls all zone rendering methods with correct layout.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_next_event: Mock view model with next event
        """
        # Mock the zone rendering methods
        mock_renderer._render_zone1_time_gap = MagicMock()
        mock_renderer._render_zone2_meeting_card = MagicMock()
        mock_renderer._render_zone4_context = MagicMock()
        
        # Call the full image rendering method
        result = mock_renderer._render_full_image(mock_view_model_with_next_event)
        
        # Verify the result is a PIL Image with correct dimensions
        assert isinstance(result, Image.Image)
        assert result.width == 300
        assert result.height == 400
        
        # Verify all zone rendering methods were called with correct parameters
        mock_renderer._render_zone1_time_gap.assert_called_once()
        zone1_args = mock_renderer._render_zone1_time_gap.call_args[0]
        assert zone1_args[3] == 0  # x
        assert zone1_args[4] == 0  # y
        assert zone1_args[5] == 300  # width
        assert zone1_args[6] == 130  # height
        
        mock_renderer._render_zone2_meeting_card.assert_called_once()
        zone2_args = mock_renderer._render_zone2_meeting_card.call_args[0]
        assert zone2_args[3] == 0  # x
        assert zone2_args[4] == 130  # y
        assert zone2_args[5] == 300  # width
        assert zone2_args[6] == 200  # height
        
        mock_renderer._render_zone4_context.assert_called_once()
        zone4_args = mock_renderer._render_zone4_context.call_args[0]
        assert zone4_args[3] == 0  # x
        assert zone4_args[4] == 330  # y
        assert zone4_args[5] == 300  # width
        assert zone4_args[6] == 70  # height
    
    def test_format_time_remaining_when_different_values_then_formats_correctly(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining method with different time values.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Test with minutes < 60
        result_minutes = mock_renderer._format_time_remaining(45)
        assert result_minutes == "45 MINUTES"
        
        # Test with hours only (no remaining minutes)
        result_hours = mock_renderer._format_time_remaining(120)
        assert result_hours == "2 HOURS"
        
        # Test with hours and minutes
        result_mixed = mock_renderer._format_time_remaining(125)
        assert result_mixed == "2 HOURS 5 MINUTES"
    
    def test_render_zones_when_different_display_modes_then_uses_correct_color_mode(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test zone rendering with different display color modes.
        
        Args:
            mock_settings: Mock settings
        """
        # Test with grayscale display
        grayscale_display = MockDisplay(
            MockDisplayCapabilities(
                supports_grayscale=True,
                supports_red=False
            )
        )
        grayscale_renderer = EInkWhatsNextRenderer(mock_settings, display=grayscale_display)
        
        # Test with RGB display
        rgb_display = MockDisplay(
            MockDisplayCapabilities(
                supports_grayscale=True,
                supports_red=True
            )
        )
        rgb_renderer = EInkWhatsNextRenderer(mock_settings, display=rgb_display)
        
        # Test with monochrome display
        mono_display = MockDisplay(
            MockDisplayCapabilities(
                supports_grayscale=False,
                supports_red=False
            )
        )
        mono_renderer = EInkWhatsNextRenderer(mock_settings, display=mono_display)
        
        # Create a simple view model
        view_model = MockViewModel(
            next_events=[MockEventData(subject="Test Event", time_until_minutes=30)]
        )
        
        # Render with each renderer
        grayscale_image = grayscale_renderer._render_full_image(view_model)
        rgb_image = rgb_renderer._render_full_image(view_model)
        mono_image = mono_renderer._render_full_image(view_model)
        
        # Verify correct image modes
        assert grayscale_image.mode == "L"
        assert rgb_image.mode == "RGB"
        assert mono_image.mode == "1"
    
    def test_render_zones_when_exception_occurs_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_next_event: MockViewModel
    ) -> None:
        """Test error handling during zone rendering.
        
        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_next_event: Mock view model with next event
        """
        # Mock zone1 rendering to raise an exception
        mock_renderer._render_zone1_time_gap = MagicMock(side_effect=ValueError("Zone 1 rendering error"))
        
        # Mock error image rendering to avoid PIL font issues
        mock_renderer._render_error_image = MagicMock(return_value=Image.new("L", (100, 100)))
        
        # Call the full image rendering method
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger") as mock_logger:
            # This should not raise an exception but should log the error
            result = mock_renderer.render(mock_view_model_with_next_event)
            
            # Verify error was logged
            mock_logger.exception.assert_called_once()
            
            # Verify an error image was returned
            assert isinstance(result, Image.Image)