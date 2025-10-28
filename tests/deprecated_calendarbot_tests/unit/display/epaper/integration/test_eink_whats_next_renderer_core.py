"""
Unit tests for the core functionality of EInkWhatsNextRenderer.

These tests focus on the core rendering logic, initialization,
error handling, and integration with WhatsNextLogic.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from calendarbot.cache.models import CachedEvent
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.renderer_interface import InteractionEvent
from calendarbot.display.whats_next_logic import WhatsNextLogic


def create_mock_display_capabilities(
    width: int = 300,
    height: int = 400,
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

    def mock_render(buffer):
        display.render_called = True
        display.render_buffer = buffer
        return True

    def mock_get_capabilities():
        return display.capabilities

    display.initialize.side_effect = mock_initialize
    display.render.side_effect = mock_render
    display.get_capabilities.side_effect = mock_get_capabilities

    return display


def create_mock_event(
    subject: str = "Test Event",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    location: str = "Test Location",
    time_until_minutes: int = 30,
    is_current: bool = False,
    is_upcoming: bool = False,
) -> MagicMock:
    """Create mock event for testing.

    Args:
        subject: Event subject
        start_time: Event start time
        end_time: Event end time
        location: Event location
        time_until_minutes: Minutes until event starts
        is_current: Whether this is a current event
        is_upcoming: Whether this is an upcoming event

    Returns:
        Mock event instance
    """
    event = MagicMock()
    event.subject = subject
    event.start_time = start_time or datetime.now() + timedelta(minutes=time_until_minutes)
    event.end_time = end_time or event.start_time + timedelta(hours=1)
    event.location = location
    event.time_until_minutes = time_until_minutes
    event.duration_minutes = int((event.end_time - event.start_time).total_seconds() / 60)
    event.formatted_time_range = (
        f"{event.start_time.strftime('%H:%M')} - {event.end_time.strftime('%H:%M')}"
    )
    event.is_current = is_current
    event.is_upcoming = is_upcoming
    event.organizer = "Test Organizer"
    event.attendees = ["Attendee 1", "Attendee 2"]
    event.format_time_range.return_value = event.formatted_time_range
    return event


def create_mock_status_info(
    is_cached: bool = False,
    connection_status: str = "connected",
    relative_description: str = "now",
    interactive_mode: bool = False,
    selected_date: Optional[str] = None,
) -> MagicMock:
    """Create mock status info for testing.

    Args:
        is_cached: Whether data is cached
        connection_status: Connection status
        relative_description: Relative time description
        interactive_mode: Whether in interactive mode
        selected_date: Selected date if any

    Returns:
        Mock status info instance
    """
    status_info = MagicMock()
    status_info.is_cached = is_cached
    status_info.last_update = datetime.now()
    status_info.connection_status = connection_status
    status_info.relative_description = relative_description
    status_info.interactive_mode = interactive_mode
    status_info.selected_date = selected_date
    return status_info


def create_mock_view_model(
    current_events: Optional[list[MagicMock]] = None,
    next_events: Optional[list[MagicMock]] = None,
    later_events: Optional[list[MagicMock]] = None,
    display_date: str = "2025-08-01",
    current_time: Optional[datetime] = None,
    status_info: Optional[MagicMock] = None,
) -> MagicMock:
    """Create mock view model for testing.

    Args:
        current_events: List of current events
        next_events: List of next events
        later_events: List of later events
        display_date: Display date
        current_time: Current time
        status_info: Status information

    Returns:
        Mock view model instance
    """
    view_model = MagicMock()
    view_model.current_events = current_events or []
    view_model.next_events = next_events or []
    view_model.later_events = later_events or []
    view_model.display_date = display_date
    view_model.current_time = current_time or datetime.now()

    # Use provided status_info or create a default one
    view_model.status_info = status_info or create_mock_status_info()

    view_model.weather_info = None
    view_model.settings_data = None

    def get_next_event():
        return view_model.next_events[0] if view_model.next_events else None

    def get_current_event():
        return view_model.current_events[0] if view_model.current_events else None

    def has_events():
        return bool(view_model.next_events or view_model.current_events or view_model.later_events)

    view_model.get_next_event.side_effect = get_next_event
    view_model.get_current_event.side_effect = get_current_event
    view_model.has_events.side_effect = has_events
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
        subject="Current Meeting",
        time_until_minutes=0,
        location="Conference Room A",
        is_current=True,
        is_upcoming=False,
    )
    next_event = create_mock_event(
        subject="Next Meeting",
        time_until_minutes=30,
        location="Conference Room B",
        is_current=False,
        is_upcoming=True,
    )
    later_event = create_mock_event(
        subject="Later Meeting",
        time_until_minutes=120,
        location="Conference Room C",
        is_current=False,
        is_upcoming=True,
    )
    return create_mock_view_model(
        current_events=[current_event],
        next_events=[next_event],
        later_events=[later_event],
        current_time=datetime.now(),
    )


@pytest.fixture
def mock_cached_events() -> list[CachedEvent]:
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
        self, mock_settings: dict[str, Any]
    ) -> None:
        """Test initialization with default display.

        Args:
            mock_settings: Mock settings
        """
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.EInkDriver"
        ) as mock_driver:
            mock_driver.return_value = create_mock_display()
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
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
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
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
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
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
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
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        self, mock_settings: dict[str, Any], mock_display: MagicMock
    ) -> None:
        """Test update_display method with exception.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        test_image = Image.new("L", (100, 100))

        # Mock the image processor to raise an exception
        renderer.image_processor.convert_to_display_format = MagicMock(
            side_effect=ValueError("Test error")
        )

        result = renderer.update_display(test_image)

        assert result is False
        assert mock_display.initialize_called is True
        assert mock_display.render_called is False

    def test_render_from_events_when_valid_events_then_creates_view_model_and_renders(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_cached_events: list[CachedEvent],
    ) -> None:
        """Test render_from_events method with valid events.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            mock_cached_events: Mock cached events
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

        # Mock the logic and render methods
        mock_view_model = create_mock_view_model()
        renderer.logic.create_view_model = MagicMock(return_value=mock_view_model)
        renderer.render = MagicMock(return_value=Image.new("L", (100, 100)))

        status_info = {"status": "ok"}
        result = renderer.render_from_events(mock_cached_events, status_info)

        assert isinstance(result, Image.Image)
        renderer.logic.create_view_model.assert_called_once_with(mock_cached_events, status_info)
        renderer.render.assert_called_once_with(mock_view_model)

    def test_can_do_partial_update_when_conditions_met_then_returns_true(
        self, mock_settings: dict[str, Any], mock_display: MagicMock
    ) -> None:
        """Test _can_do_partial_update method when conditions are met.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

        # Create two identical view models
        event1 = create_mock_event(subject="Event 1")
        event2 = create_mock_event(subject="Event 2")

        last_vm = create_mock_view_model(
            current_events=[event1], next_events=[event2], display_date="2025-08-01"
        )

        current_vm = create_mock_view_model(
            current_events=[event1], next_events=[event2], display_date="2025-08-01"
        )

        # Set last view model
        renderer._last_view_model = last_vm

        result = renderer._can_do_partial_update(current_vm)

        assert result is True

    def test_can_do_partial_update_when_no_last_view_model_then_returns_false(
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_view_model_with_events: MagicMock,
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
        self, mock_settings: dict[str, Any], mock_view_model_with_events: MagicMock
    ) -> None:
        """Test _can_do_partial_update method when display doesn't support partial update.

        Args:
            mock_settings: Mock settings
            mock_view_model_with_events: Mock view model with events
        """
        # Create display that doesn't support partial updates
        mock_display = create_mock_display(
            create_mock_display_capabilities(supports_partial_update=False)
        )
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

        # Set last view model
        renderer._last_view_model = mock_view_model_with_events

        result = renderer._can_do_partial_update(mock_view_model_with_events)

        assert result is False

    def test_render_error_when_valid_message_then_returns_image(
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        self,
        mock_settings: dict[str, Any],
        mock_display: MagicMock,
        mock_cached_events: list[CachedEvent],
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
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new"
        ) as mock_new:
            mock_new.side_effect = ValueError("Image creation error")

            result = renderer.render_error(error_message)

            assert isinstance(result, Image.Image)
            renderer._render_error_image.assert_called_once()
            assert "Critical error" in renderer._render_error_image.call_args[0][0]

    def test_render_authentication_prompt_when_valid_params_then_returns_image(
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.Image.new"
        ) as mock_new:
            mock_new.side_effect = ValueError("Image creation error")

            result = renderer.render_authentication_prompt(verification_uri, user_code)

            assert isinstance(result, Image.Image)
            renderer._render_error_image.assert_called_once()
            assert "Authentication prompt error" in renderer._render_error_image.call_args[0][0]

    def test_handle_interaction_when_refresh_event_then_clears_cache(
        self, mock_settings: dict[str, Any], mock_display: MagicMock
    ) -> None:
        """Test handle_interaction method with refresh event.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        renderer._last_rendered_content = b"test_content"
        renderer._last_view_model = create_mock_view_model()

        # Create refresh interaction event
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "refresh"

        renderer.handle_interaction(interaction)

        assert renderer._last_rendered_content is None
        assert renderer._last_view_model is None

    def test_handle_interaction_when_button_press_event_then_logs_button_id(
        self, mock_settings: dict[str, Any], mock_display: MagicMock
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

        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"
        ) as mock_logger:
            renderer.handle_interaction(interaction)
            mock_logger.info.assert_called_once_with("Button press: test_button")


# Aliases for backward compatibility with test_eink_whats_next_renderer_html.py
MockDisplay = create_mock_display
MockEvent = create_mock_event
MockStatusInfo = create_mock_status_info
MockViewModel = create_mock_view_model
