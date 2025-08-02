"""Keyboard input handling for interactive navigation."""

import asyncio
import logging
import sys
from collections.abc import Awaitable
from enum import Enum
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)


class KeyCode(Enum):
    """Key codes for navigation commands."""

    LEFT_ARROW = "left"
    RIGHT_ARROW = "right"
    UP_ARROW = "up"
    DOWN_ARROW = "down"
    SPACE = "space"
    ESCAPE = "escape"
    HOME = "home"
    END = "end"
    ENTER = "enter"
    UNKNOWN = "unknown"


class KeyboardHandler:
    """Handles keyboard input for interactive navigation."""

    def __init__(self) -> None:
        """Initialize keyboard handler."""
        self._running = False
        self._key_callbacks: dict[
            KeyCode, Union[Callable[[], None], Callable[[], Awaitable[None]]]
        ] = {}
        self._raw_key_callback: Optional[Callable[[str], None]] = None

        # Platform-specific setup
        self._setup_platform_input()

        logger.debug("Keyboard handler initialized")

    def _setup_platform_input(self) -> None:
        """Set up platform-specific keyboard input handling."""
        self._fallback_mode = False
        self._old_settings: Optional[list[Any]] = None

        try:
            if sys.platform == "win32":
                import msvcrt  # noqa: PLC0415

                self._getch = msvcrt.getch
                self._kbhit = msvcrt.kbhit
            else:
                # Unix-like systems (Linux, macOS) - simplified for raw mode
                def _getch() -> str:
                    """Read a single character in raw mode."""
                    return sys.stdin.read(1)

                def _kbhit() -> bool:
                    """Check for available input using select."""
                    import select  # noqa: PLC0415

                    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

                self._getch = _getch
                self._kbhit = _kbhit

        except ImportError as e:
            logger.warning(f"Could not import platform-specific keyboard modules: {e}")
            self._setup_fallback_input()

    def _setup_terminal(self) -> None:
        """Set up terminal for raw input mode on Unix systems."""
        if sys.platform != "win32":
            try:
                import termios  # noqa: PLC0415

                fd = sys.stdin.fileno()
                self._old_settings = termios.tcgetattr(fd)

                # Create new settings for raw mode using termios directly
                new_settings = termios.tcgetattr(fd)
                new_settings[3] &= ~(
                    termios.ICANON | termios.ECHO
                )  # Disable canonical mode and echo
                new_settings[6][termios.VMIN] = 0  # Don't wait for characters
                new_settings[6][termios.VTIME] = 1  # Wait 0.1 seconds for input

                termios.tcsetattr(fd, termios.TCSAFLUSH, new_settings)
                logger.debug("Terminal set to raw input mode with timeout")

            except Exception as e:
                logger.warning(f"Could not set terminal to raw mode: {e}")
                self._setup_fallback_input()

    def _setup_fallback_input(self) -> None:
        """Setup fallback input method if raw mode fails."""
        logger.info("Using fallback input method - press Enter after each key")
        self._fallback_mode = True

        def _getch_fallback() -> str:
            try:
                return input("Enter key (or 'left', 'right', 'space', 'esc'): ").strip()
            except EOFError:
                return "esc"

        def _kbhit_fallback() -> bool:
            return True  # Always ready in fallback mode

        self._getch = _getch_fallback
        self._kbhit = _kbhit_fallback

    def _restore_terminal(self) -> None:
        """Restore terminal settings on Unix systems."""
        if sys.platform != "win32" and self._old_settings:
            try:
                import termios  # noqa: PLC0415

                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)

                logger.debug("Terminal settings restored")
            except Exception as e:
                logger.warning(f"Could not restore terminal settings: {e}")

    def _parse_key_sequence(self, key_data: str) -> KeyCode:
        """Parse key sequence and return corresponding KeyCode.

        Args:
            key_data: Raw key data from input

        Returns:
            Corresponding KeyCode
        """
        if not key_data:
            return KeyCode.UNKNOWN

        # Use appropriate parsing method based on mode
        if self._fallback_mode:
            return self._parse_fallback_mode(key_data)
        if len(key_data) == 1:
            return self._parse_single_char(key_data)
        if key_data.startswith("\x1b["):
            return self._parse_escape_sequence(key_data[2:])
        if sys.platform == "win32":
            return self._parse_windows_sequence(key_data)

        return KeyCode.UNKNOWN

    def _parse_fallback_mode(self, key_data: str) -> KeyCode:
        """Parse key input in fallback mode.

        Args:
            key_data: Raw key data from input

        Returns:
            Corresponding KeyCode
        """
        # Mapping of fallback mode inputs to KeyCodes
        fallback_mappings = {
            "left": KeyCode.LEFT_ARROW,
            "l": KeyCode.LEFT_ARROW,
            "←": KeyCode.LEFT_ARROW,
            "right": KeyCode.RIGHT_ARROW,
            "r": KeyCode.RIGHT_ARROW,
            "→": KeyCode.RIGHT_ARROW,
            "up": KeyCode.UP_ARROW,
            "u": KeyCode.UP_ARROW,
            "↑": KeyCode.UP_ARROW,
            "down": KeyCode.DOWN_ARROW,
            "d": KeyCode.DOWN_ARROW,
            "↓": KeyCode.DOWN_ARROW,
            "space": KeyCode.SPACE,
            "s": KeyCode.SPACE,
            " ": KeyCode.SPACE,
            "esc": KeyCode.ESCAPE,
            "escape": KeyCode.ESCAPE,
            "e": KeyCode.ESCAPE,
            "exit": KeyCode.ESCAPE,
            "q": KeyCode.ESCAPE,
            "home": KeyCode.HOME,
            "h": KeyCode.HOME,
            "end": KeyCode.END,
            "enter": KeyCode.ENTER,
            "\n": KeyCode.ENTER,
            "\r": KeyCode.ENTER,
        }

        key_lower = key_data.lower().strip()
        return fallback_mappings.get(key_lower, KeyCode.UNKNOWN)

    def _parse_single_char(self, key_data: str) -> KeyCode:
        """Parse a single character input.

        Args:
            key_data: Single character input

        Returns:
            Corresponding KeyCode
        """
        char = key_data.lower()

        # Mapping of single characters to KeyCodes
        char_mappings = {
            " ": KeyCode.SPACE,
            "\x1b": KeyCode.ESCAPE,  # ESC
            "\r": KeyCode.ENTER,
            "\n": KeyCode.ENTER,
        }

        return char_mappings.get(char, KeyCode.UNKNOWN)

    def _parse_escape_sequence(self, sequence: str) -> KeyCode:
        """Parse an escape sequence.

        Args:
            sequence: The escape sequence without the '\x1b[' prefix

        Returns:
            Corresponding KeyCode
        """
        # Mapping of escape sequences to KeyCodes
        escape_mappings = {
            "A": KeyCode.UP_ARROW,
            "B": KeyCode.DOWN_ARROW,
            "C": KeyCode.RIGHT_ARROW,
            "D": KeyCode.LEFT_ARROW,
        }

        # Home and End keys can have multiple representations
        if sequence in {"H", "1~"}:
            return KeyCode.HOME
        if sequence in {"F", "4~"}:
            return KeyCode.END

        return escape_mappings.get(sequence, KeyCode.UNKNOWN)

    def _parse_windows_sequence(self, key_data: Union[str, bytes]) -> KeyCode:
        """Parse Windows-specific key sequences.

        Args:
            key_data: Raw key data from Windows input, can be str or bytes

        Returns:
            Corresponding KeyCode
        """
        # Mapping of Windows-specific sequences to KeyCodes
        windows_mappings = {
            b"\xe0": KeyCode.UNKNOWN,  # Special key prefix, need next byte
            b"H": KeyCode.UP_ARROW,
            b"P": KeyCode.DOWN_ARROW,
            b"M": KeyCode.RIGHT_ARROW,
            b"K": KeyCode.LEFT_ARROW,
        }

        # Handle the case where key_data is a string
        if isinstance(key_data, str):
            # Try to encode to bytes for comparison
            try:
                key_bytes = key_data.encode("latin1")
                return windows_mappings.get(key_bytes, KeyCode.UNKNOWN)
            except (UnicodeError, AttributeError):
                return KeyCode.UNKNOWN

        # If key_data is already bytes
        return windows_mappings.get(key_data, KeyCode.UNKNOWN)

    def register_key_handler(
        self, key_code: KeyCode, callback: Union[Callable[[], None], Callable[[], Awaitable[None]]]
    ) -> None:
        """Register a callback for a specific key.

        Args:
            key_code: Key code to handle
            callback: Function to call when key is pressed
        """
        self._key_callbacks[key_code] = callback
        logger.debug(f"Registered handler for key: {key_code}")

    def register_raw_key_handler(self, callback: Callable[[str], None]) -> None:
        """Register a callback for raw key input.

        Args:
            callback: Function to call with raw key data
        """
        self._raw_key_callback = callback
        logger.debug("Registered raw key handler")

    def unregister_key_handler(self, key_code: KeyCode) -> None:
        """Unregister a key handler.

        Args:
            key_code: Key code to unregister
        """
        if key_code in self._key_callbacks:
            del self._key_callbacks[key_code]
            logger.debug(f"Unregistered handler for key: {key_code}")

    async def start_listening(self) -> None:
        """Start listening for keyboard input."""
        if self._running:
            logger.warning("Keyboard handler already running")
            return

        self._running = True
        self._setup_terminal()

        logger.info("Started keyboard input listening")
        logger.debug(f"Platform: {sys.platform}")
        logger.debug(f"Old terminal settings stored: {self._old_settings is not None}")

        try:
            await self._input_loop()
        finally:
            self._restore_terminal()
            self._running = False
            logger.info("Stopped keyboard input listening")

    def stop_listening(self) -> None:
        """Stop listening for keyboard input."""
        self._running = False
        logger.debug("Keyboard handler stop requested")

    async def _input_loop(self) -> None:
        """Main input loop for capturing keystrokes."""
        while self._running:
            try:
                # Handle fallback mode differently
                if self._fallback_mode:
                    if self._kbhit():
                        key_data = self._getch()
                        if key_data:
                            await self._handle_key_input(key_data)
                    await asyncio.sleep(0.1)  # Longer delay for fallback mode
                    continue

                # Check for available input in raw mode
                if sys.platform == "win32":
                    if self._kbhit():
                        key_data = self._getch()
                        if isinstance(key_data, bytes):
                            key_data = key_data.decode("utf-8", errors="ignore")
                    else:
                        await asyncio.sleep(0.05)
                        continue
                # Unix-like systems with improved escape sequence handling
                elif self._kbhit():
                    key_data = await self._read_key_sequence()
                else:
                    await asyncio.sleep(0.05)
                    continue

                # Parse and handle the key
                if key_data:
                    await self._handle_key_input(key_data)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Error in keyboard input loop")
                await asyncio.sleep(0.1)

    async def _read_key_sequence(self) -> str:
        """Read a complete key sequence, handling escape sequences properly."""
        try:
            key_data = self._getch()

            # If it's an escape character, try to read the full sequence
            if key_data == "\x1b":
                sequence = key_data

                # With VTIME=1, _getch() will timeout if no more chars available
                # Try to read the remaining escape sequence characters
                while len(sequence) < 8:  # Max reasonable escape sequence length
                    next_char = self._getch()
                    if next_char:  # Got a character
                        sequence += next_char
                        logger.debug(f"Read escape char: {next_char!r}, sequence: {sequence!r}")

                        # Most escape sequences end with a letter or ~
                        if next_char.isalpha() or next_char == "~":
                            break
                    else:
                        # No more characters (timeout), sequence is complete
                        break

                logger.debug(f"Final escape sequence: {sequence!r}")
                return str(sequence)
            return str(key_data)

        except Exception as e:
            logger.debug(f"Error reading key sequence: {e}")
            return ""

    async def _handle_key_input(self, key_data: str) -> None:
        """Handle a key input.

        Args:
            key_data: Raw key data
        """
        try:
            # Log what we received and what it parses to
            key_code = self._parse_key_sequence(key_data)
            logger.debug(f"Received key_data={key_data!r}, parsed as={key_code}")

            # Call raw key handler if registered
            if self._raw_key_callback:
                self._raw_key_callback(key_data)

            if key_code != KeyCode.UNKNOWN and key_code in self._key_callbacks:
                callback = self._key_callbacks[key_code]
                logger.debug(f"Executing callback for {key_code}")
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

                logger.debug(f"Handled key: {key_code}")
            elif key_code == KeyCode.UNKNOWN:
                logger.debug(f"Unknown key sequence: {key_data!r}")

        except Exception:
            logger.exception("Error handling key input")

    @property
    def is_running(self) -> bool:
        """Check if keyboard handler is currently running."""
        return self._running

    def get_help_text(self) -> str:
        """Get help text for registered key handlers.

        Returns:
            Formatted help text
        """
        help_lines = []

        key_descriptions = {
            KeyCode.LEFT_ARROW: "← Previous day",
            KeyCode.RIGHT_ARROW: "→ Next day",
            KeyCode.SPACE: "Space: Jump to today",
            KeyCode.ESCAPE: "ESC: Exit navigation",
            KeyCode.HOME: "Home: Start of week",
            KeyCode.END: "End: End of week",
        }

        help_lines = [
            key_descriptions[key_code]
            for key_code in self._key_callbacks
            if key_code in key_descriptions
        ]

        return " | ".join(help_lines) if help_lines else "No key handlers registered"
