"""Tests for DisplayAbstractionLayer Protocol."""

from typing import Any, Optional

import pytest

from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.capabilities import DisplayCapabilities


class MockDisplayAbstractionLayer:
    """Mock implementation of DisplayAbstractionLayer for testing."""

    def __init__(
        self,
        initialize_return: bool = True,
        render_return: bool = True,
        clear_return: bool = True,
        shutdown_return: bool = True,
    ) -> None:
        """Initialize mock display abstraction layer.

        Args:
            initialize_return: Value to return from initialize method
            render_return: Value to return from render method
            clear_return: Value to return from clear method
            shutdown_return: Value to return from shutdown method
        """
        self.initialize_called = False
        self.render_called = False
        self.render_content: Optional[Any] = None
        self.clear_called = False
        self.shutdown_called = False
        self.get_capabilities_called = False

        self.initialize_return = initialize_return
        self.render_return = render_return
        self.clear_return = clear_return
        self.shutdown_return = shutdown_return

        # Default capabilities
        self.capabilities = DisplayCapabilities(
            width=800,
            height=600,
            colors=2,
            supports_partial_update=True,
            supports_grayscale=False,
            supports_red=False,
        )

    def initialize(self) -> bool:
        """Initialize the display hardware.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        self.initialize_called = True
        return self.initialize_return

    def render(self, content: Any) -> bool:
        """Render content to the display.

        Args:
            content: Content to render

        Returns:
            bool: True if rendering successful, False otherwise
        """
        self.render_called = True
        self.render_content = content
        return self.render_return

    def clear(self) -> bool:
        """Clear the display.

        Returns:
            bool: True if clearing successful, False otherwise
        """
        self.clear_called = True
        return self.clear_return

    def shutdown(self) -> bool:
        """Shutdown the display hardware.

        Returns:
            bool: True if shutdown successful, False otherwise
        """
        self.shutdown_called = True
        return self.shutdown_return

    def get_capabilities(self) -> DisplayCapabilities:
        """Get display capabilities.

        Returns:
            DisplayCapabilities: Object containing display capabilities
        """
        self.get_capabilities_called = True
        return self.capabilities


class TestDisplayAbstractionLayer:
    """Test suite for DisplayAbstractionLayer Protocol."""

    def test_protocol_when_implemented_then_type_checks_pass(self) -> None:
        """Test that a class implementing the protocol passes type checks."""
        # Arrange & Act
        mock_display: DisplayAbstractionLayer = MockDisplayAbstractionLayer()

        # Assert - No type errors should occur
        assert isinstance(mock_display, MockDisplayAbstractionLayer)

    def test_initialize_when_called_then_returns_expected_value(self) -> None:
        """Test initialize method returns expected value."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(initialize_return=True)

        # Act
        result = mock_display.initialize()

        # Assert
        assert mock_display.initialize_called is True
        assert result is True

    def test_initialize_when_fails_then_returns_false(self) -> None:
        """Test initialize method returns False when initialization fails."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(initialize_return=False)

        # Act
        result = mock_display.initialize()

        # Assert
        assert mock_display.initialize_called is True
        assert result is False

    def test_render_when_called_with_content_then_stores_content(self) -> None:
        """Test render method stores content and returns expected value."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(render_return=True)
        test_content = "test content"

        # Act
        result = mock_display.render(test_content)

        # Assert
        assert mock_display.render_called is True
        assert mock_display.render_content == test_content
        assert result is True

    def test_render_when_fails_then_returns_false(self) -> None:
        """Test render method returns False when rendering fails."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(render_return=False)
        test_content = "test content"

        # Act
        result = mock_display.render(test_content)

        # Assert
        assert mock_display.render_called is True
        assert mock_display.render_content == test_content
        assert result is False

    def test_clear_when_called_then_returns_expected_value(self) -> None:
        """Test clear method returns expected value."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(clear_return=True)

        # Act
        result = mock_display.clear()

        # Assert
        assert mock_display.clear_called is True
        assert result is True

    def test_clear_when_fails_then_returns_false(self) -> None:
        """Test clear method returns False when clearing fails."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(clear_return=False)

        # Act
        result = mock_display.clear()

        # Assert
        assert mock_display.clear_called is True
        assert result is False

    def test_shutdown_when_called_then_returns_expected_value(self) -> None:
        """Test shutdown method returns expected value."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(shutdown_return=True)

        # Act
        result = mock_display.shutdown()

        # Assert
        assert mock_display.shutdown_called is True
        assert result is True

    def test_shutdown_when_fails_then_returns_false(self) -> None:
        """Test shutdown method returns False when shutdown fails."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer(shutdown_return=False)

        # Act
        result = mock_display.shutdown()

        # Assert
        assert mock_display.shutdown_called is True
        assert result is False

    def test_get_capabilities_when_called_then_returns_capabilities(self) -> None:
        """Test get_capabilities method returns DisplayCapabilities object."""
        # Arrange
        mock_display = MockDisplayAbstractionLayer()
        expected_capabilities = DisplayCapabilities(
            width=800,
            height=600,
            colors=2,
            supports_partial_update=True,
            supports_grayscale=False,
            supports_red=False,
        )

        # Act
        result = mock_display.get_capabilities()

        # Assert
        assert mock_display.get_capabilities_called is True
        assert isinstance(result, DisplayCapabilities)
        assert result.width == expected_capabilities.width
        assert result.height == expected_capabilities.height
        assert result.colors == expected_capabilities.colors
        assert result.supports_partial_update == expected_capabilities.supports_partial_update
        assert result.supports_grayscale == expected_capabilities.supports_grayscale
        assert result.supports_red == expected_capabilities.supports_red

    def test_protocol_usage_in_function(self) -> None:
        """Test using the protocol as a type annotation in a function."""
        # Define a function that uses the protocol
        def use_display(display: DisplayAbstractionLayer) -> bool:
            display.initialize()
            display.render("test")
            display.clear()
            capabilities = display.get_capabilities()
            display.shutdown()
            return isinstance(capabilities, DisplayCapabilities)

        # Arrange
        mock_display = MockDisplayAbstractionLayer()

        # Act
        result = use_display(mock_display)

        # Assert
        assert result is True
        assert mock_display.initialize_called is True
        assert mock_display.render_called is True
        assert mock_display.clear_called is True
        assert mock_display.get_capabilities_called is True
        assert mock_display.shutdown_called is True