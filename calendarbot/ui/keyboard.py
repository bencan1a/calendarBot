"""Keyboard input handling for interactive navigation."""

import asyncio
import logging
import sys
from enum import Enum
from typing import Any, Callable, Dict, Optional

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

    def __init__(self):
        """Initialize keyboard handler."""
        self._running = False
        self._key_callbacks: Dict[KeyCode, Callable] = {}
        self._raw_key_callback: Optional[Callable[[str], None]] = None

        # Platform-specific setup
        self._setup_platform_input()

        logger.debug("Keyboard handler initialized")

    def _setup_platform_input(self):
        """Set up platform-specific keyboard input handling."""
        self._fallback_mode = False
        self._old_settings = None

        try:
            if sys.platform == "win32":
                import msvcrt

                self._getch = msvcrt.getch
                self._kbhit = msvcrt.kbhit
            else:
                # Unix-like systems (Linux, macOS) - simplified for raw mode
                def _getch():
                    """Read a single character in raw mode."""
                    return sys.stdin.read(1)

                def _kbhit():
                    """Check for available input using select."""
                    import select

                    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

                self._getch = _getch
                self._kbhit = _kbhit

        except ImportError as e:
            logger.warning(f"Could not import platform-specific keyboard modules: {e}")
            self._setup_fallback_input()

    def _setup_terminal(self):
        """Set up terminal for raw input mode on Unix systems."""
        if sys.platform != "win32":
            try:
                import termios

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

    def _setup_fallback_input(self):
        """Setup fallback input method if raw mode fails."""
        logger.info("Using fallback input method - press Enter after each key")
        self._fallback_mode = True

        def _getch_fallback():
            try:
                return input("Enter key (or 'left', 'right', 'space', 'esc'): ").strip()
            except EOFError:
                return "esc"

        def _kbhit_fallback():
            return True  # Always ready in fallback mode

        self._getch = _getch_fallback
        self._kbhit = _kbhit_fallback

    def _restore_terminal(self):
        """Restore terminal settings on Unix systems."""
        if sys.platform != "win32" and self._old_settings:
            try:
                import termios

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

        # Handle fallback mode with text input
        if self._fallback_mode:
            key_lower = key_data.lower().strip()
            if key_lower in ["left", "l", "←"]:
                return KeyCode.LEFT_ARROW
            elif key_lower in ["right", "r", "→"]:
                return KeyCode.RIGHT_ARROW
            elif key_lower in ["up", "u", "↑"]:
                return KeyCode.UP_ARROW
            elif key_lower in ["down", "d", "↓"]:
                return KeyCode.DOWN_ARROW
            elif key_lower in ["space", "s", " "]:
                return KeyCode.SPACE
            elif key_lower in ["esc", "escape", "e", "exit", "q"]:
                return KeyCode.ESCAPE
            elif key_lower in ["home", "h"]:
                return KeyCode.HOME
            elif key_lower in ["end"]:
                return KeyCode.END
            elif key_lower in ["enter", "\n", "\r"]:
                return KeyCode.ENTER
            else:
                return KeyCode.UNKNOWN

        # Handle single character keys in raw mode
        if len(key_data) == 1:
            char = key_data.lower()
            if char == " ":
                return KeyCode.SPACE
            elif char == "\x1b":  # ESC
                return KeyCode.ESCAPE
            elif char == "\r" or char == "\n":
                return KeyCode.ENTER
            else:
                return KeyCode.UNKNOWN

        # Handle escape sequences (arrow keys, etc.)
        if key_data.startswith("\x1b["):
            sequence = key_data[2:]
            if sequence == "A":
                return KeyCode.UP_ARROW
            elif sequence == "B":
                return KeyCode.DOWN_ARROW
            elif sequence == "C":
                return KeyCode.RIGHT_ARROW
            elif sequence == "D":
                return KeyCode.LEFT_ARROW
            elif sequence == "H" or sequence == "1~":
                return KeyCode.HOME
            elif sequence == "F" or sequence == "4~":
                return KeyCode.END

        # Windows-specific sequences
        if sys.platform == "win32":
            if key_data == b"\xe0":  # Special key prefix on Windows
                return KeyCode.UNKNOWN  # Need next byte
            elif key_data == b"H":  # Up arrow
                return KeyCode.UP_ARROW
            elif key_data == b"P":  # Down arrow
                return KeyCode.DOWN_ARROW
            elif key_data == b"M":  # Right arrow
                return KeyCode.RIGHT_ARROW
            elif key_data == b"K":  # Left arrow
                return KeyCode.LEFT_ARROW

        return KeyCode.UNKNOWN

    def register_key_handler(self, key_code: KeyCode, callback: Callable):
        """Register a callback for a specific key.

        Args:
            key_code: Key code to handle
            callback: Function to call when key is pressed
        """
        self._key_callbacks[key_code] = callback
        logger.debug(f"Registered handler for key: {key_code}")

    def register_raw_key_handler(self, callback: Callable[[str], None]):
        """Register a callback for raw key input.

        Args:
            callback: Function to call with raw key data
        """
        self._raw_key_callback = callback
        logger.debug("Registered raw key handler")

    def unregister_key_handler(self, key_code: KeyCode):
        """Unregister a key handler.

        Args:
            key_code: Key code to unregister
        """
        if key_code in self._key_callbacks:
            del self._key_callbacks[key_code]
            logger.debug(f"Unregistered handler for key: {key_code}")

    async def start_listening(self):
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

    def stop_listening(self):
        """Stop listening for keyboard input."""
        self._running = False
        logger.debug("Keyboard handler stop requested")

    async def _input_loop(self):
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
                else:
                    # Unix-like systems with improved escape sequence handling
                    if self._kbhit():
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
            except Exception as e:
                logger.error(f"Error in keyboard input loop: {e}")
                await asyncio.sleep(0.1)

    async def _read_key_sequence(self):
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
                        logger.debug(
                            f"Read escape char: {repr(next_char)}, sequence: {repr(sequence)}"
                        )

                        # Most escape sequences end with a letter or ~
                        if next_char.isalpha() or next_char == "~":
                            break
                    else:
                        # No more characters (timeout), sequence is complete
                        break

                logger.debug(f"Final escape sequence: {repr(sequence)}")
                return sequence
            else:
                return key_data

        except Exception as e:
            logger.debug(f"Error reading key sequence: {e}")
            return ""

    async def _handle_key_input(self, key_data: str):
        """Handle a key input.

        Args:
            key_data: Raw key data
        """
        try:
            # DEBUG: Log what we received and what it parses to
            key_code = self._parse_key_sequence(key_data)
            logger.info(f"DEBUG: Received key_data={repr(key_data)}, parsed as={key_code}")

            # Call raw key handler if registered
            if self._raw_key_callback:
                self._raw_key_callback(key_data)

            if key_code != KeyCode.UNKNOWN and key_code in self._key_callbacks:
                callback = self._key_callbacks[key_code]
                logger.info(f"DEBUG: Executing callback for {key_code}")
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

                logger.debug(f"Handled key: {key_code}")
            elif key_code == KeyCode.UNKNOWN:
                logger.debug(f"Unknown key sequence: {repr(key_data)}")

        except Exception as e:
            logger.error(f"Error handling key input: {e}")

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

        for key_code in self._key_callbacks:
            if key_code in key_descriptions:
                help_lines.append(key_descriptions[key_code])

        return " | ".join(help_lines) if help_lines else "No key handlers registered"
