"""Renderer protocol interface for type consistency."""

from typing import Any, Dict, List, Optional, Protocol

from ..cache.models import CachedEvent


class RendererProtocol(Protocol):
    """Protocol defining the interface that all renderers must implement."""

    def render_events(
        self, events: List[CachedEvent], status_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render events to formatted output.

        Args:
            events: List of cached events to display
            status_info: Additional status information

        Returns:
            Formatted string for display
        """
        ...

    def render_error(
        self, error_message: str, cached_events: Optional[List[CachedEvent]] = None
    ) -> str:
        """Render an error message with optional cached events.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show

        Returns:
            Formatted error display
        """
        ...

    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> str:
        """Render authentication prompt for device code flow.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter

        Returns:
            Formatted authentication prompt
        """
        ...


class ConsoleRendererProtocol(RendererProtocol, Protocol):
    """Extended protocol for console-specific renderers."""

    def clear_screen(self) -> None:
        """Clear the console screen."""
        ...

    def display_with_clear(self, content: str) -> None:
        """Display content after clearing screen.

        Args:
            content: Content to display
        """
        ...

    def enable_split_display(self, max_log_lines: int = 5) -> None:
        """Enable split display mode for interactive logging.

        Args:
            max_log_lines: Maximum number of log lines to show
        """
        ...

    def disable_split_display(self) -> None:
        """Disable split display mode."""
        ...

    def update_log_area(self, log_lines: List[str]) -> None:
        """Update the reserved log area with new log lines.

        Args:
            log_lines: List of formatted log messages
        """
        ...
