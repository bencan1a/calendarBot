"""Unit tests for calendarbot.display.renderer_factory module."""

from unittest.mock import Mock, patch

import pytest

from calendarbot.display.renderer_factory import RendererFactory


class TestRendererFactory:
    """Test RendererFactory functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.display_enabled = True
        settings.web_layout = "4x8"
        return settings

    def test_create_renderer_console_type(self, mock_settings) -> None:
        """Test creating console renderer."""
        with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_console.return_value = mock_renderer

            result = RendererFactory.create_renderer("console", mock_settings)

            assert result == mock_renderer
            mock_console.assert_called_once_with(mock_settings)

    def test_create_renderer_html_type(self, mock_settings) -> None:
        """Test creating HTML renderer."""
        with patch("calendarbot.display.renderer_factory.HTMLRenderer") as mock_html:
            mock_renderer = Mock()
            mock_html.return_value = mock_renderer

            result = RendererFactory.create_renderer("html", mock_settings)

            assert result == mock_renderer
            mock_html.assert_called_once_with(mock_settings)

    def test_create_renderer_rpi_type(self, mock_settings) -> None:
        """Test creating Raspberry Pi renderer."""
        with patch("calendarbot.display.renderer_factory.RaspberryPiHTMLRenderer") as mock_rpi:
            mock_renderer = Mock()
            mock_rpi.return_value = mock_renderer

            result = RendererFactory.create_renderer("rpi", mock_settings)

            assert result == mock_renderer
            mock_rpi.assert_called_once_with(mock_settings)

    def test_create_renderer_compact_type(self, mock_settings) -> None:
        """Test creating compact eink renderer."""
        with patch("calendarbot.display.renderer_factory.CompactEInkRenderer") as mock_compact:
            mock_renderer = Mock()
            mock_compact.return_value = mock_renderer

            result = RendererFactory.create_renderer("compact", mock_settings)

            assert result == mock_renderer
            mock_compact.assert_called_once_with(mock_settings)

    def test_create_renderer_unknown_type_defaults_to_console(self, mock_settings) -> None:
        """Test creating renderer with unknown type defaults to console."""
        with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_console.return_value = mock_renderer

            result = RendererFactory.create_renderer("unknown_type", mock_settings)

            assert result == mock_renderer
            mock_console.assert_called_once_with(mock_settings)

    def test_create_renderer_handles_import_error(self, mock_settings) -> None:
        """Test creating renderer handles import errors gracefully."""
        with patch(
            "calendarbot.display.renderer_factory.HTMLRenderer",
            side_effect=ImportError("Module not found"),
        ):
            with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
                mock_renderer = Mock()
                mock_console.return_value = mock_renderer

                result = RendererFactory.create_renderer("html", mock_settings)

                # Should fallback to ConsoleRenderer when renderer cannot be imported
                assert result == mock_renderer
                mock_console.assert_called_once_with(mock_settings)

    def test_create_renderer_handles_instantiation_error(self, mock_settings) -> None:
        """Test creating renderer handles instantiation errors gracefully."""
        with patch(
            "calendarbot.display.renderer_factory.HTMLRenderer",
            side_effect=Exception("Cannot instantiate"),
        ):
            with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
                mock_renderer = Mock()
                mock_console.return_value = mock_renderer

                result = RendererFactory.create_renderer("html", mock_settings)

                # Should fallback to ConsoleRenderer when renderer cannot be instantiated
                assert result == mock_renderer
                mock_console.assert_called_once_with(mock_settings)

    def test_get_available_renderers(self) -> None:
        """Test getting list of available renderer types."""
        types = RendererFactory.get_available_renderers()

        expected_types = ["html", "rpi", "compact", "console", "whats-next", "eink-whats-next"]
        assert types == expected_types

    def test_detect_device_type_rpi_environment(self) -> None:
        """Test detecting device type in RPI environment."""
        with patch("calendarbot.display.renderer_factory._is_raspberry_pi", return_value=True):
            with patch(
                "calendarbot.display.renderer_factory._has_compact_display", return_value=False
            ):
                device_type = RendererFactory.detect_device_type()

                assert device_type == "rpi"

    def test_detect_device_type_compact_environment(self) -> None:
        """Test detecting device type in compact display environment."""
        with patch("calendarbot.display.renderer_factory._is_raspberry_pi", return_value=True):
            with patch(
                "calendarbot.display.renderer_factory._has_compact_display", return_value=True
            ):
                device_type = RendererFactory.detect_device_type()

                assert device_type == "compact"

    def test_detect_device_type_desktop_environment(self) -> None:
        """Test detecting device type in desktop environment."""
        with patch("calendarbot.display.renderer_factory._is_raspberry_pi", return_value=False):
            with patch("platform.system", return_value="Linux"):
                with patch("platform.machine", return_value="x86_64"):
                    device_type = RendererFactory.detect_device_type()

                    assert device_type == "desktop"

    def test_get_recommended_renderer(self, mock_settings) -> None:
        """Test getting recommended renderer for current device."""
        with patch(
            "calendarbot.display.renderer_factory.RendererFactory.detect_device_type",
            return_value="desktop",
        ):
            renderer_type = RendererFactory.get_recommended_renderer()

            assert renderer_type == "html"

    @pytest.mark.parametrize(
        "renderer_type,expected_class",
        [
            ("console", "ConsoleRenderer"),
            ("html", "HTMLRenderer"),
            ("rpi", "RaspberryPiHTMLRenderer"),
            ("compact", "CompactEInkRenderer"),
        ],
    )
    def test_create_renderer_type_mapping(
        self, mock_settings, renderer_type: str, expected_class: str
    ) -> None:
        """Test renderer type to class mapping."""
        mock_module = f"calendarbot.display.renderer_factory.{expected_class}"

        with patch(mock_module) as mock_renderer_class:
            mock_renderer = Mock()
            mock_renderer_class.return_value = mock_renderer

            result = RendererFactory.create_renderer(renderer_type, mock_settings)

            assert result == mock_renderer
            mock_renderer_class.assert_called_once_with(mock_settings)

    def test_create_renderer_with_keyword_arguments(self, mock_settings) -> None:
        """Test creating renderer with new keyword signature."""
        with patch("calendarbot.display.renderer_factory.HTMLRenderer") as mock_html:
            mock_renderer = Mock()
            mock_html.return_value = mock_renderer

            # Must provide at least one positional argument
            result = RendererFactory.create_renderer(
                mock_settings, renderer_type="html", layout_name="4x8"
            )

            assert result == mock_renderer
            assert mock_settings.web_layout == "4x8"
            mock_html.assert_called_once_with(mock_settings)

    def test_create_renderer_with_layout_name(self, mock_settings) -> None:
        """Test creating renderer with layout name updates settings."""
        with patch("calendarbot.display.renderer_factory.HTMLRenderer") as mock_html:
            mock_renderer = Mock()
            mock_html.return_value = mock_renderer

            result = RendererFactory.create_renderer(
                mock_settings, renderer_type="html", layout_name="3x4"
            )

            assert result == mock_renderer
            assert mock_settings.web_layout == "3x4"
            mock_html.assert_called_once_with(mock_settings)

    def test_create_renderer_auto_detection(self, mock_settings) -> None:
        """Test creating renderer with automatic device detection."""
        with patch(
            "calendarbot.display.renderer_factory.RendererFactory.detect_device_type",
            return_value="desktop",
        ):
            with patch("calendarbot.display.renderer_factory.HTMLRenderer") as mock_html:
                mock_renderer = Mock()
                mock_html.return_value = mock_renderer

                result = RendererFactory.create_renderer(mock_settings)

                assert result == mock_renderer
                mock_html.assert_called_once_with(mock_settings)


class TestRendererFactoryIntegration:
    """Test RendererFactory integration scenarios."""

    def test_factory_works_with_all_renderer_types(self) -> None:
        """Test factory can create all supported renderer types."""
        mock_settings = Mock()

        renderer_types = RendererFactory.get_available_renderers()

        for renderer_type in renderer_types:
            with patch(
                "calendarbot.display.renderer_factory._create_renderer_instance"
            ) as mock_create:
                mock_renderer = Mock()
                mock_create.return_value = mock_renderer

                result = RendererFactory.create_renderer(renderer_type, mock_settings)
                # Should not be None (assuming patches work)
                assert result is not None

    def test_factory_maintains_renderer_independence(self) -> None:
        """Test that factory creates independent renderer instances."""
        mock_settings = Mock()

        with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
            # Create different mock instances for each call
            mock_renderer1 = Mock()
            mock_renderer2 = Mock()
            mock_console.side_effect = [mock_renderer1, mock_renderer2]

            result1 = RendererFactory.create_renderer("console", mock_settings)
            result2 = RendererFactory.create_renderer("console", mock_settings)

            # Should be different instances
            assert result1 is not result2
            assert mock_console.call_count == 2

    def test_factory_error_recovery(self) -> None:
        """Test factory recovers gracefully from renderer creation failures."""
        mock_settings = Mock()

        # First call fails, second succeeds
        with patch("calendarbot.display.renderer_factory.HTMLRenderer") as mock_html:
            with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
                mock_fallback_renderer = Mock()
                mock_console.return_value = mock_fallback_renderer
                mock_html.side_effect = Exception("First call fails")

                # First call should fallback to console renderer
                result1 = RendererFactory.create_renderer("html", mock_settings)
                assert result1 == mock_fallback_renderer

                # Reset for second call
                mock_html.side_effect = None
                mock_success_renderer = Mock()
                mock_html.return_value = mock_success_renderer

                # Second call should succeed with HTML renderer
                result2 = RendererFactory.create_renderer("html", mock_settings)
                assert result2 == mock_success_renderer

    def test_device_detection_functions(self) -> None:
        """Test device detection helper functions."""
        # Test raspberry pi detection
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_exists.return_value = True
                mock_read.return_value = "Raspberry Pi"

                from calendarbot.display.renderer_factory import _is_raspberry_pi

                assert _is_raspberry_pi() is True

        # Test compact display detection
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            from calendarbot.display.renderer_factory import _has_compact_display

            result = _has_compact_display()
            # Should return True when SPI devices are found
            assert isinstance(result, bool)

    def test_device_to_renderer_mapping(self) -> None:
        """Test device type to renderer type mapping."""
        from calendarbot.display.renderer_factory import _map_device_to_renderer

        assert _map_device_to_renderer("compact") == "compact"
        assert _map_device_to_renderer("rpi") == "rpi"
        assert _map_device_to_renderer("desktop") == "html"
        assert _map_device_to_renderer("unknown") == "console"

    def test_create_renderer_instance_function(self) -> None:
        """Test the internal create renderer instance function."""
        mock_settings = Mock()

        with patch("calendarbot.display.renderer_factory.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_console.return_value = mock_renderer

            from calendarbot.display.renderer_factory import _create_renderer_instance

            result = _create_renderer_instance("console", mock_settings)

            assert result == mock_renderer
            mock_console.assert_called_once_with(mock_settings)

    def test_create_renderer_instance_invalid_type(self) -> None:
        """Test create renderer instance with invalid type raises error."""
        mock_settings = Mock()

        from calendarbot.display.renderer_factory import _create_renderer_instance

        with pytest.raises(ValueError, match="Unknown renderer type: invalid"):
            _create_renderer_instance("invalid", mock_settings)
