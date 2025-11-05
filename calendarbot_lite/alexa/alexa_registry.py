"""Registry pattern for Alexa intent handlers.

This module provides a decorator-based registry system for registering Alexa intent handlers.
New intents can be added by simply decorating the handler class.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypeVar

if TYPE_CHECKING:
    from calendarbot_lite.alexa.alexa_handlers import AlexaEndpointBase

# TypeVar for preserving handler class types through the decorator
_HandlerT = TypeVar("_HandlerT", bound="AlexaEndpointBase")


@dataclass
class HandlerInfo:
    """Metadata about a registered Alexa handler.

    Attributes:
        intent: The Alexa intent name (e.g., "GetNextMeetingIntent")
        route: The HTTP route path (e.g., "/api/alexa/next-meeting")
        handler_class: The handler class to instantiate
        description: Human-readable description of the handler
        ssml_enabled: Whether SSML output is supported for this handler
        cache_enabled: Whether response caching should be enabled
        precompute_enabled: Whether precomputation is supported
    """

    intent: str
    route: str
    handler_class: type[AlexaEndpointBase]
    description: str
    ssml_enabled: bool = True
    cache_enabled: bool = True
    precompute_enabled: bool = False


class AlexaHandlerRegistry:
    """Registry for Alexa intent handlers.

    Provides a decorator-based system for registering handlers and
    automatically generating routes.

    Example:
        @AlexaHandlerRegistry.register(
            intent="GetNextMeetingIntent",
            route="/api/alexa/next-meeting",
            description="Returns next upcoming meeting",
            ssml_enabled=True
        )
        class NextMeetingHandler(AlexaEndpointBase):
            ...
    """

    _handlers: ClassVar[dict[str, HandlerInfo]] = {}

    @classmethod
    def register(
        cls,
        intent: str,
        route: str,
        description: str,
        ssml_enabled: bool = True,
        cache_enabled: bool = True,
        precompute_enabled: bool = False,
    ) -> Callable[[type[_HandlerT]], type[_HandlerT]]:
        """Decorator to register an Alexa handler.

        Args:
            intent: Alexa intent name (e.g., "GetNextMeetingIntent")
            route: HTTP route path (e.g., "/api/alexa/next-meeting")
            description: Human-readable description
            ssml_enabled: Whether SSML output is supported (default: True)
            cache_enabled: Whether response caching should be enabled (default: True)
            precompute_enabled: Whether precomputation is supported (default: False)

        Returns:
            Decorator function that registers the handler class

        Example:
            @AlexaHandlerRegistry.register(
                intent="GetNextMeetingIntent",
                route="/api/alexa/next-meeting",
                description="Returns next upcoming meeting"
            )
            class NextMeetingHandler(AlexaEndpointBase):
                pass
        """

        def decorator(handler_class: type[_HandlerT]) -> type[_HandlerT]:
            """Register the handler class and return it unchanged."""
            cls._handlers[intent] = HandlerInfo(
                intent=intent,
                route=route,
                handler_class=handler_class,  # type: ignore[arg-type]
                description=description,
                ssml_enabled=ssml_enabled,
                cache_enabled=cache_enabled,
                precompute_enabled=precompute_enabled,
            )
            return handler_class

        return decorator

    @classmethod
    def get_handlers(cls) -> dict[str, HandlerInfo]:
        """Get all registered handlers.

        Returns:
            Dictionary mapping intent names to HandlerInfo objects
        """
        return cls._handlers.copy()

    @classmethod
    def get_handler(cls, intent: str) -> HandlerInfo | None:
        """Get a specific handler by intent name.

        Args:
            intent: Alexa intent name

        Returns:
            HandlerInfo object or None if not found
        """
        return cls._handlers.get(intent)

    @classmethod
    def get_routes(cls) -> dict[str, HandlerInfo]:
        """Get all registered routes.

        Returns:
            Dictionary mapping route paths to HandlerInfo objects
        """
        return {info.route: info for info in cls._handlers.values()}

    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers.

        Note: This is primarily useful for testing.
        """
        cls._handlers.clear()

    @classmethod
    def list_intents(cls) -> list[str]:
        """List all registered intent names.

        Returns:
            List of intent names
        """
        return list(cls._handlers.keys())

    @classmethod
    def list_routes(cls) -> list[str]:
        """List all registered route paths.

        Returns:
            List of route paths
        """
        return [info.route for info in cls._handlers.values()]


def get_handler_info_summary() -> str:
    """Get a summary of all registered handlers.

    Returns:
        Formatted string with handler information

    Example:
        >>> print(get_handler_info_summary())
        Registered Alexa Handlers:
        - GetNextMeetingIntent (/api/alexa/next-meeting)
          Returns next upcoming meeting
          SSML: Yes | Cache: Yes | Precompute: Yes
        ...
    """
    handlers = AlexaHandlerRegistry.get_handlers()
    if not handlers:
        return "No Alexa handlers registered."

    lines = ["Registered Alexa Handlers:"]
    for intent, info in sorted(handlers.items()):
        lines.append(f"- {intent} ({info.route})")
        lines.append(f"  {info.description}")
        features = []
        if info.ssml_enabled:
            features.append("SSML: Yes")
        if info.cache_enabled:
            features.append("Cache: Yes")
        if info.precompute_enabled:
            features.append("Precompute: Yes")
        if features:
            lines.append(f"  {' | '.join(features)}")
        lines.append("")  # Empty line between handlers

    return "\n".join(lines)
