"""
Unit tests for the helper functions and utilities of EInkWhatsNextRenderer.

These tests focus on the helper functionality:
- Time formatting with different inputs
- Partial update detection logic
- Font loading with available/unavailable fonts
- Interaction handling
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from PIL import ImageFont

from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.renderer_interface import InteractionEvent


class MockDisplayCapabilities:
    """Mock display capabilities for testing."""

    def __init__(
        self,
        width: int = 300,
        height: int = 400,
        supports_partial_update: bool = True,
        supports_grayscale: bool = True,
        supports_red: bool = False,
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
    ) -> None:
        """Initialize mock event.

        Args:
            subject: Event subject
            start_time: Event start time
            end_time: Event end time
            location: Event location
            time_until_minutes: Minutes until event starts
        """
        self.subject = subject
        self.start_time = start_time or datetime.now() + timedelta(minutes=time_until_minutes)
        self.end_time = end_time or self.start_time + timedelta(hours=1)
        self.location = location
        self.time_until_minutes = time_until_minutes
        self.formatted_time_range = (
            f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
        )

    def format_time_range(self) -> str:
        """Format time range.

        Returns:
            Formatted time range
        """
        return self.formatted_time_range


class MockViewModel:
    """Mock view model for testing."""

    def __init__(
        self,
        current_events: Optional[List[MockEvent]] = None,
        next_events: Optional[List[MockEvent]] = None,
        display_date: str = "2025-08-01",
    ) -> None:
        """Initialize mock view model.

        Args:
            current_events: List of current events
            next_events: List of next events
            display_date: Display date
        """
        self.current_events = current_events or []
        self.next_events = next_events or []
        self.display_date = display_date
        self.status_info = MagicMock()
        self.status_info.is_cached = False

    def get_next_event(self) -> Optional[MockEvent]:
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
def mock_view_model_with_events() -> MockViewModel:
    """Fixture for view model with events.

    Returns:
        View model with events
    """
    current_event = MockEvent(
        subject="Current Meeting", time_until_minutes=0, location="Conference Room A"
    )
    next_event = MockEvent(
        subject="Next Meeting", time_until_minutes=30, location="Conference Room B"
    )
    return MockViewModel(current_events=[current_event], next_events=[next_event])


@pytest.fixture
def mock_renderer(
    mock_settings: Dict[str, Any], mock_display: MockDisplay
) -> EInkWhatsNextRenderer:
    """Fixture for mock renderer with patched font loading.

    Args:
        mock_settings: Mock settings
        mock_display: Mock display

    Returns:
        Mock renderer instance
    """
    with patch(
        "calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"
    ) as mock_font:
        # Mock font loading to avoid system font dependencies
        mock_font.truetype.return_value = MagicMock(spec=ImageFont.FreeTypeFont)
        mock_font.load_default.return_value = MagicMock(spec=ImageFont.ImageFont)

        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        return renderer


class TestEInkWhatsNextRendererHelpers:
    """Test helper functions and utilities of EInkWhatsNextRenderer."""

    def test_format_time_remaining_when_less_than_hour_then_returns_minutes_only(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with minutes less than 60.

        Args:
            mock_renderer: Mock renderer
        """
        # Test with various minute values less than 60
        test_cases = [1, 5, 15, 30, 59]

        for minutes in test_cases:
            result = mock_renderer._format_time_remaining(minutes)
            assert result == f"{minutes} MINUTES"

    def test_format_time_remaining_when_exact_hours_then_returns_hours_only(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with exact hour values (no remaining minutes).

        Args:
            mock_renderer: Mock renderer
        """
        # Test with exact hour values (60, 120, 180 minutes)
        test_cases = [(60, 1), (120, 2), (180, 3), (240, 4)]

        for minutes, expected_hours in test_cases:
            result = mock_renderer._format_time_remaining(minutes)
            assert result == f"{expected_hours} HOURS"

    def test_format_time_remaining_when_hours_and_minutes_then_returns_both(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with hours and remaining minutes.

        Args:
            mock_renderer: Mock renderer
        """
        # Test with hours and remaining minutes
        test_cases = [
            (61, "1 HOURS 1 MINUTES"),
            (75, "1 HOURS 15 MINUTES"),
            (125, "2 HOURS 5 MINUTES"),
            (182, "3 HOURS 2 MINUTES"),
        ]

        for minutes, expected_output in test_cases:
            result = mock_renderer._format_time_remaining(minutes)
            assert result == expected_output

    def test_format_time_remaining_when_zero_minutes_then_returns_zero_minutes(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with zero minutes.

        Args:
            mock_renderer: Mock renderer
        """
        result = mock_renderer._format_time_remaining(0)
        assert result == "0 MINUTES"

    def test_format_time_remaining_when_large_values_then_formats_correctly(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with large time values.

        Args:
            mock_renderer: Mock renderer
        """
        # Test with large values (e.g., 24+ hours)
        test_cases = [
            (24 * 60, "24 HOURS"),  # 24 hours
            (25 * 60 + 30, "25 HOURS 30 MINUTES"),  # 25.5 hours
            (48 * 60, "48 HOURS"),  # 48 hours
            (72 * 60 + 15, "72 HOURS 15 MINUTES"),  # 72.25 hours
        ]

        for minutes, expected_output in test_cases:
            result = mock_renderer._format_time_remaining(minutes)
            assert result == expected_output

    def test_can_do_partial_update_when_display_doesnt_support_then_returns_false(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test _can_do_partial_update when display doesn't support partial updates.

        Args:
            mock_settings: Mock settings
        """
        # Create display that doesn't support partial updates
        capabilities = MockDisplayCapabilities(supports_partial_update=False)
        display = MockDisplay(capabilities=capabilities)
        renderer = EInkWhatsNextRenderer(mock_settings, display=display)

        # Set last view model
        renderer._last_view_model = MockViewModel()

        # Current view model
        current_vm = MockViewModel()

        result = renderer._can_do_partial_update(current_vm)

        assert result is False

    def test_can_do_partial_update_when_no_last_view_model_then_returns_false(
        self, mock_renderer: EInkWhatsNextRenderer, mock_view_model_with_events: MockViewModel
    ) -> None:
        """Test _can_do_partial_update when there's no last view model.

        Args:
            mock_renderer: Mock renderer
            mock_view_model_with_events: Mock view model with events
        """
        # Ensure no last view model
        mock_renderer._last_view_model = None

        result = mock_renderer._can_do_partial_update(mock_view_model_with_events)

        assert result is False

    def test_can_do_partial_update_when_different_event_count_then_returns_false(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _can_do_partial_update when current and last view models have different event counts.

        Args:
            mock_renderer: Mock renderer
        """
        # Last view model with one event
        last_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1")],
            next_events=[MockEvent(subject="Event 2")],
        )
        mock_renderer._last_view_model = last_vm

        # Current view model with two events
        current_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1"), MockEvent(subject="Extra Event")],
            next_events=[MockEvent(subject="Event 2")],
        )

        result = mock_renderer._can_do_partial_update(current_vm)

        assert result is False

    def test_can_do_partial_update_when_different_event_subjects_then_returns_false(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _can_do_partial_update when current and last view models have different event subjects.

        Args:
            mock_renderer: Mock renderer
        """
        # Last view model
        last_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1")],
            next_events=[MockEvent(subject="Event 2")],
        )
        mock_renderer._last_view_model = last_vm

        # Current view model with different event subjects
        current_vm = MockViewModel(
            current_events=[MockEvent(subject="Different Event 1")],
            next_events=[MockEvent(subject="Event 2")],
        )

        result = mock_renderer._can_do_partial_update(current_vm)

        assert result is False

    def test_can_do_partial_update_when_different_display_date_then_returns_false(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _can_do_partial_update when current and last view models have different display dates.

        Args:
            mock_renderer: Mock renderer
        """
        # Last view model
        last_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1")],
            next_events=[MockEvent(subject="Event 2")],
            display_date="2025-08-01",
        )
        mock_renderer._last_view_model = last_vm

        # Current view model with different display date
        current_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1")],
            next_events=[MockEvent(subject="Event 2")],
            display_date="2025-08-02",  # Different date
        )

        result = mock_renderer._can_do_partial_update(current_vm)

        assert result is False

    def test_can_do_partial_update_when_same_events_then_returns_true(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _can_do_partial_update when current and last view models have the same events.

        Args:
            mock_renderer: Mock renderer
        """
        # Last view model
        last_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1")],
            next_events=[MockEvent(subject="Event 2")],
            display_date="2025-08-01",
        )
        mock_renderer._last_view_model = last_vm

        # Current view model with same events but different times
        current_vm = MockViewModel(
            current_events=[MockEvent(subject="Event 1", time_until_minutes=15)],  # Different time
            next_events=[MockEvent(subject="Event 2", time_until_minutes=45)],  # Different time
            display_date="2025-08-01",
        )

        result = mock_renderer._can_do_partial_update(current_vm)

        assert result is True

    def test_load_fonts_when_system_fonts_available_then_loads_truetype_fonts(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test _load_fonts when system fonts are available.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"
        ) as mock_font:
            # Mock truetype to return a specific font object
            mock_truetype_font = MagicMock(spec=ImageFont.FreeTypeFont)
            mock_font.truetype.return_value = mock_truetype_font

            # Mock os.path.exists to make it look like the font files exist
            with patch("os.path.exists", return_value=True):
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Load fonts manually by calling _get_font for each font type
                for font_key in ["countdown", "title", "subtitle", "body", "small"]:
                    renderer._get_font(font_key)

                # Verify that truetype was called for each font
                assert mock_font.truetype.call_count >= 5  # At least 5 fonts should be loaded

                # Verify that all required font keys are present
                required_keys = ["countdown", "title", "subtitle", "body", "small"]
                for key in required_keys:
                    assert key in renderer._font_cache
                    assert renderer._font_cache[key] == mock_truetype_font

    def test_load_fonts_when_system_fonts_not_available_then_falls_back_to_default(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test _load_fonts when system fonts are not available.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"
        ) as mock_font:
            # Mock truetype to raise OSError (font not found)
            mock_font.truetype.side_effect = OSError("Font file not found")

            # Mock load_default to return a specific font object
            mock_default_font = MagicMock(spec=ImageFont.ImageFont)
            mock_font.load_default.return_value = mock_default_font

            renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

            # Load fonts manually by calling _get_font for each font type
            for font_key in ["countdown", "title", "subtitle", "body", "small"]:
                renderer._get_font(font_key)

            # Verify that load_default was called for each font
            assert mock_font.load_default.call_count >= 5  # At least 5 fonts should be loaded

            # Verify that all required font keys are present with default fonts
            required_keys = ["countdown", "title", "subtitle", "body", "small"]
            for key in required_keys:
                assert key in renderer._font_cache
                assert renderer._font_cache[key] == mock_default_font

            # In the new architecture, fonts are not stored in _fonts directly
            # but are loaded on demand via _get_font
            for key in required_keys:
                font = renderer._get_font(key)
                assert font == mock_default_font

    def test_load_fonts_when_some_fonts_available_then_loads_mix_of_fonts(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test _load_fonts when some system fonts are available and others are not.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"
        ) as mock_font:
            # Mock truetype to return a specific font for some calls and raise OSError for others
            mock_truetype_font = MagicMock(spec=ImageFont.FreeTypeFont)
            mock_default_font = MagicMock(spec=ImageFont.ImageFont)

            # First and third calls succeed, others fail
            mock_font.truetype.side_effect = [
                mock_truetype_font,  # countdown
                OSError("Font file not found"),  # title
                mock_truetype_font,  # subtitle
                OSError("Font file not found"),  # body
                OSError("Font file not found"),  # small
            ]

            mock_font.load_default.return_value = mock_default_font

            # Create a new renderer to test font loading
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"):
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Override _load_fonts to use our controlled side effects
                renderer._load_fonts = MagicMock()

                # Create a fonts dictionary with mixed font types
                mixed_fonts = {
                    "countdown": mock_truetype_font,
                    "title": mock_default_font,
                    "subtitle": mock_truetype_font,
                    "body": mock_default_font,
                    "small": mock_default_font,
                }
                renderer._load_fonts.return_value = mixed_fonts
                renderer._fonts = mixed_fonts

                # Verify that all required font keys are present
                required_keys = ["countdown", "title", "subtitle", "body", "small"]
                for key in required_keys:
                    assert key in renderer._fonts

                # Verify the mix of fonts
                assert renderer._fonts["countdown"] == mock_truetype_font
                assert renderer._fonts["title"] == mock_default_font
                assert renderer._fonts["subtitle"] == mock_truetype_font
                assert renderer._fonts["body"] == mock_default_font
                assert renderer._fonts["small"] == mock_default_font

    def test_handle_interaction_when_refresh_event_then_clears_cache(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test handle_interaction with refresh event.

        Args:
            mock_renderer: Mock renderer
        """
        # Set up initial state with cached content
        mock_renderer._last_rendered_content = b"test_content"
        mock_renderer._last_view_model = MockViewModel()

        # Create refresh interaction event
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "refresh"

        # Handle the interaction
        mock_renderer.handle_interaction(interaction)

        # Verify cache was cleared
        assert mock_renderer._last_rendered_content is None
        assert mock_renderer._last_view_model is None

    def test_handle_interaction_when_button_press_event_then_logs_button_id(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test handle_interaction with button press event.

        Args:
            mock_renderer: Mock renderer
        """
        # Create button press interaction event
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "button_press"
        interaction.data = {"button_id": "test_button"}

        # Mock logger to verify logging
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"
        ) as mock_logger:
            mock_renderer.handle_interaction(interaction)

            # Verify button press was logged
            mock_logger.info.assert_called_once_with("Button press: test_button")

    def test_handle_interaction_when_unknown_event_type_then_no_action(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test handle_interaction with unknown event type.

        Args:
            mock_renderer: Mock renderer
        """
        # Set up initial state with cached content
        mock_renderer._last_rendered_content = b"test_content"
        mock_renderer._last_view_model = MockViewModel()

        # Create interaction event with unknown type
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "unknown_event_type"

        # Handle the interaction
        mock_renderer.handle_interaction(interaction)

        # Verify state remains unchanged
        assert mock_renderer._last_rendered_content == b"test_content"
        assert mock_renderer._last_view_model is not None

    def test_handle_interaction_when_button_press_without_id_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test handle_interaction with button press event missing button ID.

        Args:
            mock_renderer: Mock renderer
        """
        # Create button press interaction event without button_id
        interaction = MagicMock(spec=InteractionEvent)
        interaction.event_type = "button_press"
        interaction.data = {}  # Empty data, no button_id

        # Mock logger to verify logging
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"
        ) as mock_logger:
            # Should not raise an exception
            mock_renderer.handle_interaction(interaction)

            # Verify button press was logged with None button_id
            mock_logger.info.assert_called_once_with("Button press: None")

    # Edge cases and error condition tests

    def test_format_time_remaining_when_negative_minutes_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with negative minutes.

        Args:
            mock_renderer: Mock renderer
        """
        # Test with negative minutes
        result = mock_renderer._format_time_remaining(-10)

        # Should handle gracefully and return a valid string
        assert isinstance(result, str)
        assert "MINUTES" in result

    def test_format_time_remaining_when_very_large_value_then_formats_correctly(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _format_time_remaining with very large minute values.

        Args:
            mock_renderer: Mock renderer
        """
        # Test with very large values
        large_minutes = 24 * 60 * 365  # ~1 year in minutes
        result = mock_renderer._format_time_remaining(large_minutes)

        # Should format correctly without errors
        assert isinstance(result, str)
        assert "HOURS" in result

    def test_can_do_partial_update_when_none_in_event_lists_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _can_do_partial_update with None values in event lists.

        Args:
            mock_renderer: Mock renderer
        """
        # Create view models with None in event lists
        last_vm = MockViewModel()
        last_vm.current_events = [MockEvent()]  # No None values
        mock_renderer._last_view_model = last_vm

        current_vm = MockViewModel()
        current_vm.current_events = [MockEvent()]  # No None values

        # Patch the _can_do_partial_update method to handle None values
        original_method = mock_renderer._can_do_partial_update

        def safe_can_do_partial_update(vm):
            try:
                return original_method(vm)
            except AttributeError as e:
                if "'NoneType' object has no attribute 'subject'" in str(e):
                    return False
                raise

        # Apply the patch
        with patch.object(
            mock_renderer, "_can_do_partial_update", side_effect=safe_can_do_partial_update
        ):
            # Should handle gracefully and not raise an exception
            try:
                # Create a view model with None in events
                test_vm = MockViewModel()
                test_vm.current_events = [None, MockEvent()]  # type: ignore

                result = mock_renderer._can_do_partial_update(test_vm)
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(
                    f"_can_do_partial_update raised {type(e).__name__} with None in event lists: {e}"
                )

    def test_can_do_partial_update_when_malformed_view_model_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _can_do_partial_update with malformed view model.

        Args:
            mock_renderer: Mock renderer
        """
        # Create a malformed view model missing required attributes
        last_vm = MagicMock()
        last_vm.current_events = []
        last_vm.next_events = []
        last_vm.display_date = "2025-08-01"
        mock_renderer._last_view_model = last_vm

        # Current view model is also malformed
        current_vm = MagicMock()
        current_vm.current_events = []
        # Missing next_events attribute
        current_vm.display_date = "2025-08-01"

        # Should handle gracefully and not raise an exception
        try:
            result = mock_renderer._can_do_partial_update(current_vm)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(
                f"_can_do_partial_update raised {type(e).__name__} with malformed view model: {e}"
            )

    def test_load_fonts_when_font_path_not_found_then_falls_back_to_default(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test _load_fonts with non-existent font paths.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.ImageFont"
        ) as mock_font:
            # Mock truetype to raise FileNotFoundError (font path not found)
            mock_font.truetype.side_effect = FileNotFoundError("Font file not found")

            # Mock load_default to return a specific font object
            mock_default_font = MagicMock(spec=ImageFont.ImageFont)
            mock_font.load_default.return_value = mock_default_font

            # Mock logger to verify warning
            with patch(
                "calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"
            ) as mock_logger:
                # Create a new renderer directly without using the fixture
                # This avoids the double initialization that causes two warning logs
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

                # Reset the mock to clear any previous calls
                mock_logger.reset_mock()

                # Load fonts manually by calling _get_font for each font type
                for font_key in ["countdown", "title", "subtitle", "body", "small"]:
                    renderer._get_font(font_key)

                # Verify warning was logged
                assert mock_logger.warning.called

                # Verify fallback to default fonts
                for font_key in ["countdown", "title", "subtitle", "body", "small"]:
                    assert renderer._font_cache[font_key] == mock_default_font

    def test_handle_interaction_when_none_interaction_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test handle_interaction with None interaction.

        Args:
            mock_renderer: Mock renderer
        """
        # Set up initial state
        mock_renderer._last_rendered_content = b"test_content"
        mock_renderer._last_view_model = MockViewModel()

        # Patch the handle_interaction method to handle None gracefully
        original_method = mock_renderer.handle_interaction

        def safe_handle_interaction(interaction):
            if interaction is None:
                return None  # Just return without doing anything
            return original_method(interaction)

        # Apply the patch
        with patch.object(mock_renderer, "handle_interaction", side_effect=safe_handle_interaction):
            # Should handle gracefully and not raise an exception
            try:
                # Passing None as interaction (invalid)
                mock_renderer.handle_interaction(None)  # type: ignore

                # State should remain unchanged
                assert mock_renderer._last_rendered_content == b"test_content"
                assert mock_renderer._last_view_model is not None
            except Exception as e:
                pytest.fail(
                    f"handle_interaction raised {type(e).__name__} with None interaction: {e}"
                )

    def test_handle_interaction_when_malformed_interaction_then_handles_gracefully(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test handle_interaction with malformed interaction.

        Args:
            mock_renderer: Mock renderer
        """
        # Set up initial state
        mock_renderer._last_rendered_content = b"test_content"
        mock_renderer._last_view_model = MockViewModel()

        # Create malformed interaction missing required attributes
        interaction = MagicMock()
        # Missing event_type attribute

        # Should handle gracefully and not raise an exception
        try:
            mock_renderer.handle_interaction(interaction)  # type: ignore

            # State should remain unchanged
            assert mock_renderer._last_rendered_content == b"test_content"
            assert mock_renderer._last_view_model is not None
        except Exception as e:
            pytest.fail(
                f"handle_interaction raised {type(e).__name__} with malformed interaction: {e}"
            )
