"""Shared fixtures for display tests to reduce repetitive mock setups."""

from unittest.mock import MagicMock, Mock

import pytest
from PIL import Image

from calendarbot.cache.models import CachedEvent


@pytest.fixture
def mock_layout_registry():
    """Create mock layout registry with common setup."""
    registry = Mock()
    registry.get_available_layouts.return_value = ["4x8", "whats-next-view"]
    registry.validate_layout.return_value = True
    registry.get_default_layout.return_value = "4x8"
    return registry


@pytest.fixture
def mock_renderer_factory():
    """Create mock renderer factory with common setup."""
    factory = Mock()
    mock_renderer = Mock()
    factory.create_renderer.return_value = mock_renderer
    return factory


@pytest.fixture
def mock_renderer():
    """Create a basic mock renderer."""
    renderer = Mock()
    renderer.render_events.return_value = "rendered content"
    renderer.render_error.return_value = "error content"
    renderer.render_authentication_prompt.return_value = "auth content"
    renderer.display_with_clear = Mock()
    renderer.update_display = Mock()
    renderer.clear_screen.return_value = True
    return renderer


@pytest.fixture
def mock_settings():
    """Create mock settings with common configuration."""
    settings = Mock()
    settings.display_type = "console"
    settings.web_layout = "4x8"
    settings.display_enabled = True
    return settings


@pytest.fixture
def mock_display_capabilities():
    """Create mock display capabilities for e-paper tests."""
    capabilities = Mock()
    capabilities.width = 300
    capabilities.height = 400
    capabilities.colors = 2
    capabilities.supports_partial_update = True
    capabilities.supports_grayscale = True
    capabilities.supports_red = False
    return capabilities


@pytest.fixture
def mock_pil_image():
    """Create mock PIL Image to avoid expensive image operations."""
    mock_img = MagicMock(spec=Image.Image)
    mock_img.size = (100, 50)
    mock_img.width = 100
    mock_img.height = 50
    mock_img.mode = "RGB"
    mock_img.convert.return_value = mock_img
    mock_img.getdata.return_value = [(255, 255, 255)] * 5000  # White pixels
    return mock_img


@pytest.fixture
def sample_cached_events() -> list[CachedEvent]:
    """Create sample cached events for testing."""
    return [
        CachedEvent(
            id="1",
            graph_id="graph-1",
            subject="Test Event 1",
            start_datetime="2024-01-01T10:00:00Z",
            end_datetime="2024-01-01T11:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            cached_at="2024-01-01T09:00:00Z",
        ),
        CachedEvent(
            id="2",
            graph_id="graph-2",
            subject="Test Event 2",
            start_datetime="2024-01-01T14:00:00Z",
            end_datetime="2024-01-01T15:00:00Z",
            start_timezone="UTC",
            end_timezone="UTC",
            cached_at="2024-01-01T09:00:00Z",
        ),
    ]


@pytest.fixture
def mock_display_manager_setup(
    mock_settings, mock_layout_registry, mock_renderer_factory, mock_renderer
):
    """Complete display manager setup with all required mocks."""
    return {
        "settings": mock_settings,
        "layout_registry": mock_layout_registry,
        "renderer_factory": mock_renderer_factory,
        "renderer": mock_renderer,
    }
