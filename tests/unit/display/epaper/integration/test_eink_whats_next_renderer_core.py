"""
Unit tests for the core functionality of EInkWhatsNextRenderer.

These tests focus on the core rendering logic, initialization,
error handling, and integration with WhatsNextLogic.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.whats_next_data_model import WhatsNextViewModel, EventData
from calendarbot.display.whats_next_logic import WhatsNextLogic
from calendarbot.cache.models import CachedEvent
from calendarbot.display.renderer_interface import InteractionEvent


class MockDisplayCapabilities:
    """Mock display capabilities for testing."""
    
    def __init__(
        self,
        width: int = 300,
        height: int = 400,
        supports_partial_update: bool = True,
        supports_grayscale: bool = True,
        supports_red: bool = False
    ) -> None:
        """Initialize mock display capabilities.
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
            supports_partial_update: Whether partial updates are supported
            supports_grayscale: Whether grayscale is supported
            supports_red: Whether red color is supported
        """
        self.width = width
        self.height = height
        self.supports_partial_update = supports_partial_update
        self.supports_grayscale = supports_grayscale
        self.supports_red = supports_red


class MockDisplay(DisplayAbstractionLayer):
    """Mock display for testing."""
    
    def __init__(self, capabilities: Optional[MockDisplayCapabilities] = None) -> None:
        """Initialize mock display.
        
        Args:
            capabilities: Optional display capabilities
        """
        self.capabilities = capabilities or MockDisplayCapabilities()
        self.initialize_called = False
        self.render_called = False
        self.render_buffer = None
    
    def initialize(self) -> bool:
        """Mock initialize method.
        
        Returns:
            True if initialization was successful
        """
        self.initialize_called = True
        return True
    
    def render(self, buffer: Any) -> bool:
        """Mock render method.
        
        Args:
            buffer: Display buffer to render
            
        Returns:
            True if render was successful
        """
        self.render_called = True
        self.render_buffer = buffer
        return True
    
    def get_capabilities(self) -> MockDisplayCapabilities:
        """Get display capabilities.
        
        Returns:
            Display capabilities
        """
        return self.capabilities


class MockEvent:
    """Mock event for testing."""
    
    def __init__(
        self,
        subject: str = "Test Event",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: str = "Test Location",
        time_until_minutes: int = 30,
        is_current: bool = False,
        is_upcoming: bool = False
    ) -> None:
        """Initialize mock event.
        
        Args:
            subject: Event subject
            start_time: Event start time
            end_time: Event end time
            location: Event location
            time_until_minutes: Minutes until event starts
            is_current: Whether this is a current event
            is_upcoming: Whether this is an upcoming event
        """
        self.subject = subject
        self.start_time = start_time or datetime.now() + timedelta(minutes=time_until_minutes)
        self.end_time = end_time or self.start_time + timedelta(hours=1)
        self.location = location
        self.time_until_minutes = time_until_minutes
        self.duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)
        self.formatted_time_range = f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
        self.is_current = is_current
        self.is_upcoming = is_upcoming
        self.organizer = "Test Organizer"
        self.attendees = ["Attendee 1", "Attendee 2"]
    
    def format_time_range(self) -> str:
        """Format time range.
        
        Returns:
            Formatted time range
        """
        return self.formatted_time_range


class MockStatusInfo:
    """Mock status info for testing."""
    
    def __init__(
        self,
        is_cached: bool = False,
        connection_status: str = "connected",
        relative_description: str = "now",
        interactive_mode: bool = False,
        selected_date: Optional[str] = None
    ) -> None:
        """Initialize mock status info.
        
        Args:
            is_cached: Whether data is cached
            connection_status: Connection status
            relative_description: Relative time description
            interactive_mode: Whether in interactive mode
            selected_date: Selected date if any
        """
        self.is_cached = is_cached
        self.last_update = datetime.now()
        self.connection_status = connection_status
        self.relative_description = relative_description
        self.interactive_mode = interactive_mode
        self.selected_date = selected_date


class MockViewModel:
    """Mock view model for testing."""
    
    def __init__(
        self,
        current_events: Optional[List[MockEvent]] = None,
        next_events: Optional[List[MockEvent]] = None,
        later_events: Optional[List[MockEvent]] = None,
        display_date: str = "2025-08-01",
        current_time: Optional[datetime] = None,
        status_info: Optional[MockStatusInfo] = None
    ) -> None:
        """Initialize mock view model.
        
        Args:
            current_events: List of current events
            next_events: List of next events
            later_events: List of later events
            display_date: Display date
            current_time: Current time
            status_info: Status information
        """
        self.current_events = current_events or []
        self.next_events = next_events or []
        self.later_events = later_events or []
        self.display_date = display_date
        self.current_time = current_time or datetime.now()
        
        # Use provided status_info or create a default one
        self.status_info = status_info or MockStatusInfo()
        
        self.weather_info = None
        self.settings_data = None
    
    def get_next_event(self) -> Optional[MockEvent]:
        """Get next event.
        
        Returns:
            Next event or None if no next events
        """
        return self.next_events[0] if self.next_events else None
    
    def get_current_event(self) -> Optional[MockEvent]:
        """Get current event.
        
        Returns:
            Current event or None if no current events
        """
        return self.current_events[0] if self.current_events else None
    
    def has_events(self) -> bool:
        """Check if there are any events to display.
        
        Returns:
            True if there are any events, False otherwise
        """
        return bool(self.next_events or self.current_events or self.later_events)


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
def mock_view_model_with_events() -> MockViewModel:
    """Fixture for view model with events.
    
    Returns:
        View model with events
    """
    current_event = MockEvent(
        subject="Current Meeting",
        time_until_minutes=0,
        location="Conference Room A",
        is_current=True,
        is_upcoming=False
    )
    next_event = MockEvent(
        subject="Next Meeting",
        time_until_minutes=30,
        location="Conference Room B",
        is_current=False,
        is_upcoming=True
    )
    later_event = MockEvent(
        subject="Later Meeting",
        time_until_minutes=120,
        location="Conference Room C",
        is_current=False,
        is_upcoming=True
    )
    return MockViewModel(
        current_events=[current_event],
        next_events=[next_event],
        later_events=[later_event],
        current_time=datetime.now()
    )


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


class TestEInkWhatsNextRendererCore:
    """Test core functionality of EInkWhatsNextRenderer."""
    
    def test_init_when_default_display_then_creates_eink_driver(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test initialization with default display.
        
        Args:
            mock_settings: Mock settings
        """
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.EInkDriver") as mock_driver:
            mock_driver.return_value = MockDisplay()
            renderer = EInkWhatsNextRenderer(mock_settings)
            
            assert renderer.settings == mock_settings
            assert isinstance(renderer.logic, WhatsNextLogic)
            assert renderer.display is not None
            assert renderer._last_rendered_content is None
            assert renderer._last_view_model is None
            assert isinstance(renderer._fonts, dict)
            assert isinstance(renderer._colors, dict)
            mock_driver.assert_called_once()
    
    def test_init_when_custom_display_then_uses_provided_display(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test initialization with custom display.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        assert renderer.settings == mock_settings
        assert isinstance(renderer.logic, WhatsNextLogic)
        assert renderer.display is mock_display
        assert renderer.capabilities is mock_display.capabilities
    
    def test_render_when_valid_view_model_then_returns_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, mock_view_model_with_events: MockViewModel
    ) -> None:
        """Test render method with valid view model.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the HTML converter to be None to skip HTML-to-PNG conversion
        with patch.object(renderer, "html_converter", None):
            # Mock the internal render methods
            renderer._can_do_partial_update = MagicMock(return_value=False)
            renderer._render_full_image = MagicMock(return_value=Image.new("L", (100, 100)))
            
            result = renderer.render(mock_view_model_with_events)
            
            assert isinstance(result, Image.Image)
            renderer._can_do_partial_update.assert_called_once_with(mock_view_model_with_events)
            renderer._render_full_image.assert_called_once_with(mock_view_model_with_events)
            assert renderer._last_view_model == mock_view_model_with_events
            assert renderer._last_rendered_content is not None
    
    def test_render_when_partial_update_possible_then_uses_partial_update(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, mock_view_model_with_events: MockViewModel
    ) -> None:
        """Test render method with partial update.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the HTML converter to be None to skip HTML-to-PNG conversion
        with patch.object(renderer, "html_converter", None):
            # Mock the internal render methods
            renderer._can_do_partial_update = MagicMock(return_value=True)
            renderer._render_partial_update = MagicMock(return_value=Image.new("L", (100, 100)))
            
            result = renderer.render(mock_view_model_with_events)
            
            assert isinstance(result, Image.Image)
            renderer._can_do_partial_update.assert_called_once_with(mock_view_model_with_events)
            renderer._render_partial_update.assert_called_once_with(mock_view_model_with_events)
    
    def test_render_when_exception_occurs_then_returns_error_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, mock_view_model_with_events: MockViewModel
    ) -> None:
        """Test render method with exception.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the HTML converter to be None to skip HTML-to-PNG conversion
        with patch.object(renderer, "html_converter", None):
            # Mock the internal render methods to raise an exception
            renderer._can_do_partial_update = MagicMock(side_effect=ValueError("Test error"))
            renderer._render_error_image = MagicMock(return_value=Image.new("L", (100, 100)))
            
            result = renderer.render(mock_view_model_with_events)
            
            assert isinstance(result, Image.Image)
            renderer._can_do_partial_update.assert_called_once_with(mock_view_model_with_events)
            renderer._render_error_image.assert_called_once()
            assert "Test error" in renderer._render_error_image.call_args[0][0]
    
    def test_update_display_when_valid_image_then_returns_true(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test update_display method with valid image.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        test_image = Image.new("L", (100, 100))
        
        # Mock the image processor
        renderer.image_processor.convert_to_display_format = MagicMock(return_value=b"test_buffer")
        
        result = renderer.update_display(test_image)
        
        assert result is True
        assert mock_display.initialize_called is True
        assert mock_display.render_called is True
        assert mock_display.render_buffer == b"test_buffer"
        renderer.image_processor.convert_to_display_format.assert_called_once_with(
            test_image, mock_display.capabilities
        )
    
    def test_update_display_when_initialize_fails_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test update_display method when initialize fails.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        test_image = Image.new("L", (100, 100))
        
        # Mock initialize to fail
        mock_display.initialize = MagicMock(return_value=False)
        
        result = renderer.update_display(test_image)
        
        assert result is False
        mock_display.initialize.assert_called_once()
        assert mock_display.render_called is False
    
    def test_update_display_when_exception_occurs_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test update_display method with exception.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        test_image = Image.new("L", (100, 100))
        
        # Mock the image processor to raise an exception
        renderer.image_processor.convert_to_display_format = MagicMock(side_effect=ValueError("Test error"))
        
        result = renderer.update_display(test_image)
        
        assert result is False
        assert mock_display.initialize_called is True
        assert mock_display.render_called is False
    
    def test_render_from_events_when_valid_events_then_creates_view_model_and_renders(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, mock_cached_events: List[CachedEvent]
    ) -> None:
        """Test render_from_events method with valid events.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_cached_events: Mock cached events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the logic and render methods
        mock_view_model = MockViewModel()
        renderer.logic.create_view_model = MagicMock(return_value=mock_view_model)
        renderer.render = MagicMock(return_value=Image.new("L", (100, 100)))
        
        status_info = {"status": "ok"}
        result = renderer.render_from_events(mock_cached_events, status_info)
        
        assert isinstance(result, Image.Image)
        renderer.logic.create_view_model.assert_called_once_with(mock_cached_events, status_info)
        renderer.render.assert_called_once_with(mock_view_model)
    
    def test_can_do_partial_update_when_conditions_met_then_returns_true(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test _can_do_partial_update method when conditions are met.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Create two identical view models
        event1 = MockEvent(subject="Event 1")
        event2 = MockEvent(subject="Event 2")
        
        last_vm = MockViewModel(
            current_events=[event1],
            next_events=[event2],
            display_date="2025-08-01"
        )
        
        current_vm = MockViewModel(
            current_events=[event1],
            next_events=[event2],
            display_date="2025-08-01"
        )
        
        # Set last view model
        renderer._last_view_model = last_vm
        
        result = renderer._can_do_partial_update(current_vm)
        
        assert result is True
    
    def test_can_do_partial_update_when_no_last_view_model_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, mock_view_model_with_events: MockViewModel
    ) -> None:
        """Test _can_do_partial_update method with no last view model.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_view_model_with_events: Mock view model with events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # No last view model
        renderer._last_view_model = None
        
        result = renderer._can_do_partial_update(mock_view_model_with_events)
        
        assert result is False
    
    def test_can_do_partial_update_when_display_doesnt_support_partial_update_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_view_model_with_events: MockViewModel
    ) -> None:
        """Test _can_do_partial_update method when display doesn't support partial update.
        
        Args:
            mock_settings: Mock settings
            mock_view_model_with_events: Mock view model with events
        """
        # Create display that doesn't support partial updates
        mock_display = MockDisplay(MockDisplayCapabilities(supports_partial_update=False))
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Set last view model
        renderer._last_view_model = mock_view_model_with_events
        
        result = renderer._can_do_partial_update(mock_view_model_with_events)
        
        assert result is False
    
    def test_render_error_when_valid_message_then_returns_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test render_error method with valid message.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        error_message = "Test error message"
        
        result = renderer.render_error(error_message)
        
        assert isinstance(result, Image.Image)
    
    def test_render_error_when_cached_events_provided_then_includes_events_in_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, mock_cached_events: List[CachedEvent]
    ) -> None:
        """Test render_error method with cached events.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_cached_events: Mock cached events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        error_message = "Test error message"
        
        result = renderer.render_error(error_message, mock_cached_events)
        
        assert isinstance(result, Image.Image)
    
    def test_render_error_when_exception_occurs_then_returns_error_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test render_error method with exception.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        error_message = "Test error message"
        
        # Create a mock for _render_error_image that returns a valid image
        renderer._render_error_image = MagicMock(return_value=Image.new("L", (100, 100)))
        
        # Mock Image.new to raise an exception on first call only
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new") as mock_new:
            mock_new.side_effect = ValueError("Image creation error")
            
            result = renderer.render_error(error_message)
            
            assert isinstance(result, Image.Image)
            renderer._render_error_image.assert_called_once()
            assert "Critical error" in renderer._render_error_image.call_args[0][0]
    
    def test_render_authentication_prompt_when_valid_params_then_returns_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test render_authentication_prompt method with valid parameters.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        verification_uri = "https://example.com/verify"
        user_code = "ABC123"
        
        result = renderer.render_authentication_prompt(verification_uri, user_code)
        
        assert isinstance(result, Image.Image)
    
    def test_render_authentication_prompt_when_exception_occurs_then_returns_error_image(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test render_authentication_prompt method with exception.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        verification_uri = "https://example.com/verify"
        user_code = "ABC123"
        
        # Create a mock for _render_error_image that returns a valid image
        renderer._render_error_image = MagicMock(return_value=Image.new("L", (100, 100)))
        
        # Mock Image.new to raise an exception
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new") as mock_new:
            mock_new.side_effect = ValueError("Image creation error")
            
            result = renderer.render_authentication_prompt(verification_uri, user_code)
            
            assert isinstance(result, Image.Image)
            renderer._render_error_image.assert_called_once()
            assert "Authentication prompt error" in renderer._render_error_image.call_args[0][0]
    
    def test_handle_interaction_when_refresh_event_then_clears_cache(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test handle_interaction method with refresh event.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        renderer._last_rendered_content = b"test_content"
        renderer._last_view_model = MockViewModel()
        
        # Create refresh interaction event
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "refresh"
        
        renderer.handle_interaction(interaction)
        
        assert renderer._last_rendered_content is None
        assert renderer._last_view_model is None
    
    def test_handle_interaction_when_button_press_event_then_logs_button_id(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test handle_interaction method with button press event.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Create button press interaction event
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "button_press"
        interaction.data = {"button_id": "test_button"}
        
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger") as mock_logger:
            renderer.handle_interaction(interaction)
            mock_logger.info.assert_called_once_with("Button press: test_button")