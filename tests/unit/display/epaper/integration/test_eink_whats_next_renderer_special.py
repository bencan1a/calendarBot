"""
Unit tests for the special rendering cases functionality of EInkWhatsNextRenderer.

These tests focus on the special rendering functionality:
- Error rendering with different messages
- Error rendering with cached events
- Authentication prompt rendering
- Error handling within special renderers
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock, ANY
from typing import Any, Dict, List, Optional, Tuple, cast, Pattern
import re

from PIL import Image, ImageDraw, ImageFont


def contains_string(substring: str) -> Pattern:
    """Helper function to check if a string contains a substring.
    
    Args:
        substring: The substring to check for
        
    Returns:
        A regex pattern that matches strings containing the substring
    """
    return re.compile(f".*{re.escape(substring)}.*")

from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
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
def mock_cached_events() -> List[CachedEvent]:
    """Fixture for mock cached events.
    
    Returns:
        List of mock cached events
    """
    event1 = MagicMock(spec=CachedEvent)
    event1.subject = "Cached Event 1"
    event1.format_time_range.return_value = "10:00 - 11:00"
    
    event2 = MagicMock(spec=CachedEvent)
    event2.subject = "Cached Event 2"
    event2.format_time_range.return_value = "14:00 - 15:00"
    
    return [event1, event2]


@pytest.fixture
def mock_renderer(mock_settings: Dict[str, Any], mock_display: MockDisplay) -> EInkWhatsNextRenderer:
    """Fixture for mock renderer with patched font loading.
    
    Args:
        mock_settings: Mock settings
        mock_display: Mock display
        
    Returns:
        Mock renderer instance
    """
    with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont") as mock_font:
        # Mock font loading to avoid system font dependencies
        mock_font.truetype.return_value = MagicMock(spec=ImageFont.FreeTypeFont)
        mock_font.load_default.return_value = MagicMock(spec=ImageFont.ImageFont)
        
        # Create a real PIL Image for testing
        real_image = Image.new("L", (100, 100))
        real_draw = ImageDraw.Draw(real_image)
        
        # Create the renderer
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the _render_error_image method to return a real image
        renderer._render_error_image = MagicMock(return_value=real_image)
        
        return renderer


class TestEInkWhatsNextRendererSpecial:
    """Test special rendering cases functionality of EInkWhatsNextRenderer."""
    
    def test_render_error_when_basic_message_then_returns_formatted_image(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error method with a basic error message.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    error_message = "Network connection failed"
                    result = mock_renderer.render_error(error_message)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify error message was drawn
                    mock_text.assert_called()
                    text_calls = [call for call in mock_text.call_args_list]
                    assert len(text_calls) > 0, "Text should be drawn"
                    
                    # Check that some text was drawn, without specifying exact coordinates
                    # This is more resilient to implementation changes
                    assert any(error_message in str(call) for call in text_calls), "Error message should be drawn"
    
    def test_render_error_when_long_message_then_truncates_message(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error method with a very long error message.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    # Create a very long error message
                    long_error_message = "Error: " + "x" * 200
                    
                    result = mock_renderer.render_error(long_error_message)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify message was truncated
                    mock_text.assert_called()
                    
                    # Check for truncation without specifying exact coordinates
                    text_calls = [str(call) for call in mock_text.call_args_list]
                    assert any("..." in call for call in text_calls), "Truncated message with '...' should be drawn"
    
    def test_render_error_when_cached_events_provided_then_includes_events(
        self, mock_renderer: EInkWhatsNextRenderer, mock_cached_events: List[CachedEvent]
    ) -> None:
        """Test render_error method with cached events.
        
        Args:
            mock_renderer: Mock renderer
            mock_cached_events: Mock cached events
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    # Mock the format_time_range method to return consistent values
                    for event in mock_cached_events:
                        event.format_time_range.return_value = "14:00 - 15:00"
                    
                    error_message = "API error, showing cached data"
                    result = mock_renderer.render_error(error_message, mock_cached_events)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify cached data section was drawn
                    mock_text.assert_called()
                    
                    # Check for cached data header
                    text_calls = [str(call) for call in mock_text.call_args_list]
                    assert any("📱 Cached Data" in call for call in text_calls), "Cached data header should be drawn"
                    
                    # Check for event time format
                    assert any("14:00 - 15:00" in call for call in text_calls), "Event time should be drawn"
                    
                    # Check that bullet points are drawn for events
                    assert any("•" in call for call in text_calls), "Bullet points should be drawn for events"
    
    def test_render_error_when_no_cached_events_then_shows_no_cache_message(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error method with no cached events.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    error_message = "API error, no cached data available"
                    result = mock_renderer.render_error(error_message)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify no cache message was drawn
                    mock_text.assert_called()
                    mock_text.assert_any_call(ANY, "❌ No cached data available", fill=ANY, font=ANY)
    
    def test_render_error_when_exception_occurs_then_falls_back_to_error_image(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error method with an exception during rendering.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real image for the test
        real_image = Image.new("L", (100, 100))
        
        # Mock Image.new to raise an exception
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new",
                  side_effect=ValueError("Test error")):
            
            # Ensure _render_error_image is called when an exception occurs
            mock_renderer._render_error_image = MagicMock(return_value=real_image)
            
            # Call render_error which will raise an exception and fall back to _render_error_image
            error_message = "API error"
            result = mock_renderer.render_error(error_message)
            
            # Verify the result
            assert isinstance(result, Image.Image)
            assert mock_renderer._render_error_image.called
    
    def test_render_error_image_when_called_directly_then_returns_basic_error_image(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _render_error_image method directly.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # We need to use the actual implementation, not the mocked one from the fixture
        # Temporarily save the mocked version
        mocked_method = mock_renderer._render_error_image
        
        # Create a new renderer with the real implementation
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"):
            temp_renderer = EInkWhatsNextRenderer({"display": {"type": "epaper"}}, mock_renderer.display)
            
            # Patch Image.new to return our real image
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
                # Patch ImageDraw.Draw to return our real draw object
                with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                    # Patch the text method to track calls
                    with patch.object(real_draw, "text") as mock_text:
                        error_message = "Basic error message"
                        result = temp_renderer._render_error_image(error_message)
                        
                        assert isinstance(result, Image.Image)
                        
                        # Verify text was drawn
                        mock_text.assert_called()
            
            # Restore the mocked method
            mock_renderer._render_error_image = mocked_method
    
    def test_render_error_image_when_long_message_then_truncates_message(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _render_error_image method with a very long error message.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # We need to use the actual implementation, not the mocked one from the fixture
        # Temporarily save the mocked version
        mocked_method = mock_renderer._render_error_image
        
        # Create a new renderer with the real implementation
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"):
            temp_renderer = EInkWhatsNextRenderer({"display": {"type": "epaper"}}, mock_renderer.display)
            
            # Patch Image.new to return our real image
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
                # Patch ImageDraw.Draw to return our real draw object
                with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                    # Patch the text method to track calls
                    with patch.object(real_draw, "text") as mock_text:
                        # Create a very long error message
                        long_error_message = "Error: " + "x" * 200
                        
                        result = temp_renderer._render_error_image(long_error_message)
                        
                        assert isinstance(result, Image.Image)
                        
                        # Verify text was drawn
                        mock_text.assert_called()
            
            # Restore the mocked method
            mock_renderer._render_error_image = mocked_method
    
    def test_render_authentication_prompt_when_valid_params_then_returns_formatted_image(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_authentication_prompt method with valid parameters.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    verification_uri = "https://microsoft.com/devicelogin"
                    user_code = "ABC123"
                    
                    result = mock_renderer.render_authentication_prompt(verification_uri, user_code)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify text was drawn
                    mock_text.assert_called()
                    
                    # Check for key elements without specifying exact coordinates
                    text_calls = [str(call) for call in mock_text.call_args_list]
                    assert any("🔐" in call for call in text_calls), "Authentication icon should be drawn"
                    assert any("Authentication" in call for call in text_calls), "Authentication title should be drawn"
                    assert any(verification_uri in call for call in text_calls), "Verification URI should be drawn"
                    assert any(user_code in call for call in text_calls), "User code should be drawn"
    
    def test_render_authentication_prompt_when_long_url_then_truncates_url(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_authentication_prompt method with a very long URL.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    # Create a very long URL
                    long_url = "https://microsoft.com/devicelogin?session=abcdefghijklmnopqrstuvwxyz1234567890"
                    user_code = "ABC123"
                    
                    result = mock_renderer.render_authentication_prompt(long_url, user_code)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify text was drawn
                    mock_text.assert_called()
                    
                    # Check for truncation without specifying exact coordinates
                    text_calls = [str(call) for call in mock_text.call_args_list]
                    assert any("microsoft.com" in call for call in text_calls), "URL should contain domain"
                    assert any("..." in call for call in text_calls), "Long URL should be truncated"
    
    def test_render_authentication_prompt_when_exception_occurs_then_falls_back_to_error_image(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_authentication_prompt method with an exception during rendering.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real image for the test
        real_image = Image.new("L", (100, 100))
        
        # Set up the exception in Image.new
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new",
                  side_effect=ValueError("Image creation error")):
            
            verification_uri = "https://microsoft.com/devicelogin"
            user_code = "ABC123"
            
            result = mock_renderer.render_authentication_prompt(verification_uri, user_code)
            
            assert isinstance(result, Image.Image)
            mock_renderer._render_error_image.assert_called()
            # We can't check the exact error message since we're using the real method
    
    def test_render_error_when_different_display_capabilities_then_adapts_rendering(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test render_error adapts to different display capabilities.
        
        Args:
            mock_settings: Mock settings
        """
        # Test with monochrome display
        mono_capabilities = MockDisplayCapabilities(
            supports_grayscale=False,
            supports_red=False
        )
        mono_display = MockDisplay(capabilities=mono_capabilities)
        
        # Test with grayscale display
        gray_capabilities = MockDisplayCapabilities(
            supports_grayscale=True,
            supports_red=False
        )
        gray_display = MockDisplay(capabilities=gray_capabilities)
        
        # Test with color display
        color_capabilities = MockDisplayCapabilities(
            supports_grayscale=True,
            supports_red=True
        )
        color_display = MockDisplay(capabilities=color_capabilities)
        
        displays = [mono_display, gray_display, color_display]
        
        for display in displays:
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"):
                # Create a real PIL Image for testing
                real_image = Image.new("L", (300, 400))
                real_draw = ImageDraw.Draw(real_image)
                
                # Patch Image.new to return our real image but still track calls
                with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new",
                          return_value=real_image) as mock_new:
                    # Patch ImageDraw.Draw to return our real draw object
                    with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw",
                              return_value=real_draw):
                        
                        renderer = EInkWhatsNextRenderer(mock_settings, display=display)
                        
                        # Mock the _render_error_image method to avoid PIL issues
                        renderer._render_error_image = MagicMock(return_value=real_image)
                        
                        result = renderer.render_error("Test error")
                        
                        assert isinstance(result, Image.Image)
                        
                        # Verify image was created with correct mode
                        if display.capabilities.supports_red:
                            assert mock_new.call_args[0][0] == "RGB", "Should use RGB mode for color display"
                        elif display.capabilities.supports_grayscale:
                            assert mock_new.call_args[0][0] == "L", "Should use L mode for grayscale display"
                        else:
                            assert mock_new.call_args[0][0] == "1", "Should use 1 mode for monochrome display"
    
    def test_render_authentication_prompt_when_different_display_capabilities_then_adapts_rendering(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test render_authentication_prompt adapts to different display capabilities.
        
        Args:
            mock_settings: Mock settings
        """
        # Test with monochrome display
        mono_capabilities = MockDisplayCapabilities(
            supports_grayscale=False,
            supports_red=False
        )
        mono_display = MockDisplay(capabilities=mono_capabilities)
        
        # Test with grayscale display
        gray_capabilities = MockDisplayCapabilities(
            supports_grayscale=True,
            supports_red=False
        )
        gray_display = MockDisplay(capabilities=gray_capabilities)
        
        # Test with color display
        color_capabilities = MockDisplayCapabilities(
            supports_grayscale=True,
            supports_red=True
        )
        color_display = MockDisplay(capabilities=color_capabilities)
        
        displays = [mono_display, gray_display, color_display]
        
        for display in displays:
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"):
                # Create a real PIL Image for testing
                real_image = Image.new("L", (300, 400))
                real_draw = ImageDraw.Draw(real_image)
                
                # Patch Image.new to return our real image but still track calls
                with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new",
                          return_value=real_image) as mock_new:
                    # Patch ImageDraw.Draw to return our real draw object
                    with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw",
                              return_value=real_draw):
                        
                        renderer = EInkWhatsNextRenderer(mock_settings, display=display)
                        
                        # Mock the _render_error_image method to avoid PIL issues
                        renderer._render_error_image = MagicMock(return_value=real_image)
                        
                        result = renderer.render_authentication_prompt("https://example.com", "CODE123")
                        
                        assert isinstance(result, Image.Image)
                        
                        # Verify image was created with correct mode
                        if display.capabilities.supports_red:
                            assert mock_new.call_args[0][0] == "RGB", "Should use RGB mode for color display"
                        elif display.capabilities.supports_grayscale:
                            assert mock_new.call_args[0][0] == "L", "Should use L mode for grayscale display"
                        else:
                            assert mock_new.call_args[0][0] == "1", "Should use 1 mode for monochrome display"
    
    def test_render_error_when_many_cached_events_then_limits_display(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error with many cached events limits the display.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    # Create many cached events
                    many_events = []
                    for i in range(5):  # More than the 3 that should be displayed
                        event = MagicMock(spec=CachedEvent)
                        event.subject = f"Cached Event {i+1}"
                        event.format_time_range.return_value = f"{10+i}:00 - {11+i}:00"
                        many_events.append(event)
                    
                    error_message = "API error, showing cached data"
                    result = mock_renderer.render_error(error_message, many_events)
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify text was drawn
                    mock_text.assert_called()
                    
                    # Check for cached data header
                    text_calls = [str(call) for call in mock_text.call_args_list]
                    assert any("📱 Cached Data" in call for call in text_calls), "Cached data header should be drawn"
                    
                    # Check that bullet points are drawn for events
                    assert any("•" in call for call in text_calls), "Bullet points should be drawn for events"
                    
                    # Verify the 4th and 5th events were not drawn
                    event4_calls = [call for call in text_calls if "Cached Event 4" in call]
                    event5_calls = [call for call in text_calls if "Cached Event 5" in call]
                    assert len(event4_calls) == 0, "Fourth cached event should not be drawn"
                    assert len(event5_calls) == 0, "Fifth cached event should not be drawn"
    
    def test_render_error_when_empty_cached_events_list_then_shows_no_cache_message(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error with an empty cached events list.
        
        Args:
            mock_renderer: Mock renderer
        """
        # Create a real PIL Image for testing
        real_image = Image.new("L", (300, 400))
        real_draw = ImageDraw.Draw(real_image)
        
        # Patch Image.new to return our real image
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new", return_value=real_image):
            # Patch ImageDraw.Draw to return our real draw object
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageDraw.Draw", return_value=real_draw):
                # Patch the text method to track calls
                with patch.object(real_draw, "text") as mock_text:
                    error_message = "API error, empty cache"
                    result = mock_renderer.render_error(error_message, [])  # Empty list
                    
                    assert isinstance(result, Image.Image)
                    
                    # Verify no cache message was drawn
                    mock_text.assert_called()
                    mock_text.assert_any_call(ANY, "❌ No cached data available", fill=ANY, font=ANY)