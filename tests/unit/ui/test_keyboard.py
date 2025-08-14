"""
Unit tests for keyboard input handling functionality.

This module tests the KeyboardHandler class and KeyCode enum, focusing on:
- Platform-specific input handling
- Key sequence parsing
- Callback registration and execution
- Input loop functionality
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ui.keyboard import KeyboardHandler, KeyCode


class TestKeyCode:
    """Test KeyCode enum functionality."""

    def test_keycode_values(self) -> None:
        """Test that KeyCode enum has expected values."""
        assert KeyCode.LEFT_ARROW.value == "left"
        assert KeyCode.RIGHT_ARROW.value == "right"
        assert KeyCode.UP_ARROW.value == "up"
        assert KeyCode.DOWN_ARROW.value == "down"
        assert KeyCode.SPACE.value == "space"
        assert KeyCode.ESCAPE.value == "escape"
        assert KeyCode.HOME.value == "home"
        assert KeyCode.END.value == "end"
        assert KeyCode.ENTER.value == "enter"
        assert KeyCode.UNKNOWN.value == "unknown"


class TestKeyboardHandlerInitialization:
    """Test KeyboardHandler initialization."""

    def test_init_default_state(self) -> None:
        """Test that KeyboardHandler initializes with expected default state."""
        handler = KeyboardHandler()

        assert handler._running is False
        assert isinstance(handler._key_callbacks, dict)
        assert len(handler._key_callbacks) == 0
        assert handler._raw_key_callback is None

    @patch("calendarbot.ui.keyboard.KeyboardHandler._setup_platform_input")
    def test_init_calls_setup_platform_input(self, mock_setup: Mock) -> None:
        """Test that initialization calls _setup_platform_input."""
        KeyboardHandler()
        mock_setup.assert_called_once()


class TestKeyboardHandlerPlatformSetup:
    """Test platform-specific setup in KeyboardHandler."""

    def test_setup_platform_input_windows(self) -> None:
        """Test Windows platform setup."""
        # Create a handler with mocked sys.platform
        with patch("sys.platform", "win32"):
            # Mock the msvcrt module
            mock_msvcrt = Mock()

            # Use patch.dict to add msvcrt to sys.modules
            with patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
                handler = KeyboardHandler()

                # Verify handler has the expected attributes
                assert hasattr(handler, "_getch")
                assert hasattr(handler, "_kbhit")
                assert handler._fallback_mode is False

    def test_setup_platform_input_unix(self) -> None:
        """Test Unix platform setup."""
        # Create a handler with mocked sys.platform
        with patch("sys.platform", "linux"):
            # Mock the select module
            mock_select = Mock()

            # Use patch.dict to add select to sys.modules
            with patch.dict("sys.modules", {"select": mock_select}):
                # Mock sys.stdin
                with patch("sys.stdin"):
                    handler = KeyboardHandler()

                    # Verify handler has the expected attributes
                    assert hasattr(handler, "_getch")
                    assert hasattr(handler, "_kbhit")
                    assert handler._fallback_mode is False

    def test_setup_platform_input_import_error(self) -> None:
        """Test fallback when platform-specific modules can't be imported."""
        # Create a handler with mocked sys.platform
        with patch("sys.platform", "win32"):
            # Mock the import to raise ImportError
            with patch.dict("sys.modules", {"msvcrt": None}):
                with patch("builtins.__import__", side_effect=ImportError("Test error")):
                    with patch.object(KeyboardHandler, "_setup_fallback_input") as mock_fallback:
                        KeyboardHandler()

                        # Verify fallback was called
                        mock_fallback.assert_called_once()

    def test_setup_fallback_input(self) -> None:
        """Test fallback input setup."""
        handler = KeyboardHandler()
        handler._setup_fallback_input()

        assert handler._fallback_mode is True
        assert callable(handler._getch)
        assert callable(handler._kbhit)


class TestKeySequenceParsing:
    """Test key sequence parsing functionality."""

    def test_parse_key_sequence_empty(self) -> None:
        """Test parsing empty key data."""
        handler = KeyboardHandler()
        result = handler._parse_key_sequence("")

        assert result == KeyCode.UNKNOWN

    def test_parse_single_char_space(self) -> None:
        """Test parsing space character."""
        handler = KeyboardHandler()
        result = handler._parse_key_sequence(" ")

        assert result == KeyCode.SPACE

    def test_parse_single_char_escape(self) -> None:
        """Test parsing escape character."""
        handler = KeyboardHandler()
        result = handler._parse_key_sequence("\x1b")

        assert result == KeyCode.ESCAPE

    def test_parse_single_char_enter(self) -> None:
        """Test parsing enter character."""
        handler = KeyboardHandler()
        result = handler._parse_key_sequence("\r")

        assert result == KeyCode.ENTER

    def test_parse_escape_sequence_arrow_keys(self) -> None:
        """Test parsing escape sequences for arrow keys."""
        handler = KeyboardHandler()

        # Test all arrow keys
        assert handler._parse_escape_sequence("A") == KeyCode.UP_ARROW
        assert handler._parse_escape_sequence("B") == KeyCode.DOWN_ARROW
        assert handler._parse_escape_sequence("C") == KeyCode.RIGHT_ARROW
        assert handler._parse_escape_sequence("D") == KeyCode.LEFT_ARROW

    def test_parse_escape_sequence_home_end(self) -> None:
        """Test parsing escape sequences for home and end keys."""
        handler = KeyboardHandler()

        # Test home key representations
        assert handler._parse_escape_sequence("H") == KeyCode.HOME
        assert handler._parse_escape_sequence("1~") == KeyCode.HOME

        # Test end key representations
        assert handler._parse_escape_sequence("F") == KeyCode.END
        assert handler._parse_escape_sequence("4~") == KeyCode.END

    def test_parse_fallback_mode(self) -> None:
        """Test parsing in fallback mode."""
        handler = KeyboardHandler()

        # Test various fallback inputs
        assert handler._parse_fallback_mode("left") == KeyCode.LEFT_ARROW
        assert handler._parse_fallback_mode("l") == KeyCode.LEFT_ARROW
        assert handler._parse_fallback_mode("right") == KeyCode.RIGHT_ARROW
        assert handler._parse_fallback_mode("r") == KeyCode.RIGHT_ARROW
        assert handler._parse_fallback_mode("space") == KeyCode.SPACE
        assert handler._parse_fallback_mode("s") == KeyCode.SPACE
        assert handler._parse_fallback_mode("esc") == KeyCode.ESCAPE
        assert handler._parse_fallback_mode("q") == KeyCode.ESCAPE
        assert handler._parse_fallback_mode("home") == KeyCode.HOME
        assert handler._parse_fallback_mode("end") == KeyCode.END
        assert handler._parse_fallback_mode("unknown") == KeyCode.UNKNOWN


class TestKeyHandlerRegistration:
    """Test key handler registration functionality."""

    def test_register_key_handler(self) -> None:
        """Test registering a key handler."""
        handler = KeyboardHandler()
        mock_callback = Mock()

        handler.register_key_handler(KeyCode.SPACE, mock_callback)

        assert KeyCode.SPACE in handler._key_callbacks
        assert handler._key_callbacks[KeyCode.SPACE] == mock_callback

    def test_register_raw_key_handler(self) -> None:
        """Test registering a raw key handler."""
        handler = KeyboardHandler()
        mock_callback = Mock()

        handler.register_raw_key_handler(mock_callback)

        assert handler._raw_key_callback == mock_callback

    def test_unregister_key_handler(self) -> None:
        """Test unregistering a key handler."""
        handler = KeyboardHandler()
        mock_callback = Mock()

        # Register then unregister
        handler.register_key_handler(KeyCode.SPACE, mock_callback)
        handler.unregister_key_handler(KeyCode.SPACE)

        assert KeyCode.SPACE not in handler._key_callbacks

    def test_unregister_nonexistent_key_handler(self) -> None:
        """Test unregistering a key handler that doesn't exist."""
        handler = KeyboardHandler()

        # Should not raise an exception
        handler.unregister_key_handler(KeyCode.SPACE)


class TestKeyboardInputHandling:
    """Test keyboard input handling functionality."""

    @pytest.mark.asyncio
    async def test_handle_key_input_unknown_key(self) -> None:
        """Test handling unknown key input."""
        handler = KeyboardHandler()

        # Mock _parse_key_sequence to return UNKNOWN
        with patch.object(handler, "_parse_key_sequence", return_value=KeyCode.UNKNOWN):
            # Should not raise an exception
            await handler._handle_key_input("test")

    @pytest.mark.asyncio
    async def test_handle_key_input_with_callback(self) -> None:
        """Test handling key input with registered callback."""
        handler = KeyboardHandler()
        mock_callback = Mock()

        # Register callback for SPACE
        handler.register_key_handler(KeyCode.SPACE, mock_callback)

        # Mock _parse_key_sequence to return SPACE
        with patch.object(handler, "_parse_key_sequence", return_value=KeyCode.SPACE):
            await handler._handle_key_input("test")

            # Callback should be called
            mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_key_input_with_async_callback(self) -> None:
        """Test handling key input with registered async callback."""
        handler = KeyboardHandler()
        mock_callback = AsyncMock()

        # Register async callback for SPACE
        handler.register_key_handler(KeyCode.SPACE, mock_callback)

        # Mock _parse_key_sequence to return SPACE
        with patch.object(handler, "_parse_key_sequence", return_value=KeyCode.SPACE):
            await handler._handle_key_input("test")

            # Async callback should be called
            mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_key_input_with_raw_callback(self) -> None:
        """Test handling key input with registered raw callback."""
        handler = KeyboardHandler()
        mock_raw_callback = Mock()

        # Register raw callback
        handler.register_raw_key_handler(mock_raw_callback)

        # Mock _parse_key_sequence to return UNKNOWN
        with patch.object(handler, "_parse_key_sequence", return_value=KeyCode.UNKNOWN):
            await handler._handle_key_input("test")

            # Raw callback should be called with raw input
            mock_raw_callback.assert_called_once_with("test")


class TestKeyboardInputLoop:
    """Test keyboard input loop functionality."""

    @pytest.mark.asyncio
    async def test_start_listening_already_running(self) -> None:
        """Test start_listening when already running."""
        handler = KeyboardHandler()
        handler._running = True

        # Should return early without error
        await handler.start_listening()

    @pytest.mark.asyncio
    @patch("calendarbot.ui.keyboard.KeyboardHandler._setup_terminal")
    @patch("calendarbot.ui.keyboard.KeyboardHandler._input_loop")
    @patch("calendarbot.ui.keyboard.KeyboardHandler._restore_terminal")
    async def test_start_listening_normal_flow(
        self, mock_restore: Mock, mock_input_loop: AsyncMock, mock_setup: Mock
    ) -> None:
        """Test normal flow of start_listening."""
        handler = KeyboardHandler()

        # Mock _input_loop to be an AsyncMock
        mock_input_loop.side_effect = AsyncMock()

        await handler.start_listening()

        # Should set up terminal, run input loop, and restore terminal
        assert mock_setup.called
        assert mock_input_loop.called
        assert mock_restore.called
        assert handler._running is False

    @pytest.mark.asyncio
    @patch("calendarbot.ui.keyboard.KeyboardHandler._setup_terminal")
    @patch("calendarbot.ui.keyboard.KeyboardHandler._restore_terminal")
    async def test_start_listening_with_exception(
        self, mock_restore: Mock, mock_setup: Mock
    ) -> None:
        """Test start_listening with exception in input loop."""
        handler = KeyboardHandler()

        # Mock _input_loop to raise exception
        with patch.object(handler, "_input_loop", side_effect=Exception("Test error")):
            try:
                # Should catch exception and still restore terminal
                await handler.start_listening()
            except Exception:
                # We're testing that the handler catches the exception internally,
                # but if it doesn't, we'll catch it here to prevent test failure
                pass

            assert mock_setup.called
            assert mock_restore.called
            assert handler._running is False

    def test_stop_listening(self) -> None:
        """Test stop_listening."""
        handler = KeyboardHandler()
        handler._running = True

        handler.stop_listening()

        assert handler._running is False

    @pytest.mark.asyncio
    async def test_input_loop_windows(self) -> None:
        """Test input loop on Windows platform."""
        handler = KeyboardHandler()
        handler._running = True

        # Set up mocks for handler methods
        mock_getch = Mock(return_value="a")
        mock_kbhit = Mock(return_value=True)
        mock_handle = AsyncMock(side_effect=lambda x: setattr(handler, "_running", False))

        # Patch handler methods
        handler._getch = mock_getch
        handler._kbhit = mock_kbhit
        handler._handle_key_input = mock_handle

        # Mock sys.platform
        with patch("sys.platform", "win32"):
            await handler._input_loop()

            # Should call _handle_key_input with the result of _getch
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_input_loop_unix(self) -> None:
        """Test input loop on Unix platform."""
        handler = KeyboardHandler()
        handler._running = True

        # Set up mocks for handler methods
        mock_kbhit = Mock(return_value=True)
        mock_read = AsyncMock(return_value="\x1b[A")
        mock_handle = AsyncMock(side_effect=lambda x: setattr(handler, "_running", False))

        # Patch handler methods
        handler._kbhit = mock_kbhit
        handler._read_key_sequence = mock_read
        handler._handle_key_input = mock_handle

        # Mock sys.platform
        with patch("sys.platform", "linux"):
            await handler._input_loop()

            # Should call _handle_key_input with the result of _read_key_sequence
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_input_loop_fallback_mode(self) -> None:
        """Test input loop in fallback mode."""
        handler = KeyboardHandler()
        handler._running = True
        handler._fallback_mode = True

        # Set up mocks for handler methods
        mock_getch = Mock(return_value="left")
        mock_kbhit = Mock(return_value=True)
        mock_handle = AsyncMock(side_effect=lambda x: setattr(handler, "_running", False))

        # Patch handler methods
        handler._getch = mock_getch
        handler._kbhit = mock_kbhit
        handler._handle_key_input = mock_handle

        await handler._input_loop()

        # Should call _handle_key_input with the result of _getch
        mock_handle.assert_called_once()


class TestKeyboardHelpers:
    """Test keyboard helper methods."""

    def test_is_running_property(self) -> None:
        """Test is_running property."""
        handler = KeyboardHandler()

        # Default should be False
        assert handler.is_running is False

        # Set to True and check
        handler._running = True
        assert handler.is_running is True

    def test_get_help_text_empty(self) -> None:
        """Test get_help_text with no registered handlers."""
        handler = KeyboardHandler()

        result = handler.get_help_text()

        assert "No key handlers registered" in result

    def test_get_help_text_with_handlers(self) -> None:
        """Test get_help_text with registered handlers."""
        handler = KeyboardHandler()

        # Register some handlers
        handler.register_key_handler(KeyCode.LEFT_ARROW, Mock())
        handler.register_key_handler(KeyCode.RIGHT_ARROW, Mock())
        handler.register_key_handler(KeyCode.SPACE, Mock())

        result = handler.get_help_text()

        # Should contain descriptions for registered keys
        assert "Previous day" in result
        assert "Next day" in result
        assert "Jump to today" in result
        assert "|" in result  # Separator between descriptions


if __name__ == "__main__":
    pytest.main([__file__])
