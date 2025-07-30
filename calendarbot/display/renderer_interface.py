"""Abstract base class interface for renderers to implement."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from ..cache.models import CachedEvent

logger = logging.getLogger(__name__)


class InteractionEvent(Protocol):
    """Protocol defining the structure of interaction events."""

    event_type: str
    data: Dict[str, Any]


# Import the WhatsNextViewModel from the new data model
from .whats_next_data_model import WhatsNextViewModel


class RendererInterface(ABC):
    """Abstract base class that all renderers must implement."""

    @abstractmethod
    def render(self, view_model: WhatsNextViewModel) -> Any:
        """Render the view model to appropriate output format.

        Args:
            view_model: Data model containing all information needed for rendering

        Returns:
            Rendered output in format appropriate for the renderer
        """

    @abstractmethod
    def handle_interaction(self, interaction: InteractionEvent) -> None:
        """Handle user interactions.

        Args:
            interaction: Interaction event to handle
        """

    @abstractmethod
    def render_error(
        self, error_message: str, cached_events: Optional[List[CachedEvent]] = None
    ) -> Any:
        """Render an error message with optional cached events.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show

        Returns:
            Rendered error output
        """

    @abstractmethod
    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
        """Render authentication prompt for device code flow.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter

        Returns:
            Rendered authentication prompt
        """

    @abstractmethod
    def update_display(self, content: Any) -> bool:
        """Update the physical display with rendered content.

        Args:
            content: Rendered content to display

        Returns:
            True if update was successful, False otherwise
        """
