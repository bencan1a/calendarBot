"""Calendar Bot CLI execution modes.

This module provides the mode registry and execution handlers for different
Calendar Bot operational modes including interactive, web, and daemon modes.

This is part of the architectural refactoring to establish proper CLI
module structure within the calendarbot package.
"""

from typing import Any, Callable

from .daemon import run_daemon_mode

# Mode registry for available execution modes
MODE_REGISTRY: dict[str, dict[str, Any]] = {
    "interactive": {
        "name": "Interactive Mode",
        "description": "Interactive console navigation with arrow key controls",
        "handler": None,  # Will be set during Phase 2 migration
        "requires_display": True,
        "async_mode": True,
    },
    "web": {
        "name": "Web Server Mode",
        "description": "Web-based calendar interface with browser viewing",
        "handler": None,  # Will be set during Phase 2 migration
        "requires_display": False,
        "async_mode": True,
    },
    "epaper": {
        "name": "E-Paper Mode",
        "description": "E-paper display mode with hardware detection and PNG fallback",
        "handler": None,  # Will be set during Phase 2 migration
        "requires_display": True,
        "async_mode": True,
    },
    "daemon": {
        "name": "Daemon Mode",
        "description": "Background daemon mode for continuous operation",
        "handler": run_daemon_mode,
        "requires_display": False,
        "async_mode": True,
    },
}


def get_available_modes() -> dict[str, dict[str, Any]]:
    """Get all available execution modes.

    Returns:
        Dictionary of mode names to mode information
    """
    return MODE_REGISTRY.copy()


def register_mode(name: str, handler: Callable[..., Any], **kwargs: Any) -> None:
    """Register a new execution mode.

    This function allows dynamic registration of new modes during
    Phase 2 migration when handlers are moved from root main.py.

    Args:
        name: Mode name identifier
        handler: Async function to handle mode execution
        **kwargs: Additional mode configuration
    """
    MODE_REGISTRY[name] = {
        "name": kwargs.get("display_name", name.title()),
        "description": kwargs.get("description", f"{name} mode"),
        "handler": handler,
        "requires_display": kwargs.get("requires_display", False),
        "async_mode": kwargs.get("async_mode", True),
        **kwargs,
    }


def get_mode_handler(mode_name: str) -> Callable[..., Any]:
    """Get handler function for specified mode.

    Args:
        mode_name: Name of the mode

    Returns:
        Handler function for the mode

    Raises:
        KeyError: If mode is not registered
    """
    if mode_name not in MODE_REGISTRY:
        raise KeyError(f"Unknown mode: {mode_name}")

    handler = MODE_REGISTRY[mode_name]["handler"]
    if handler is None:
        raise RuntimeError(f"Handler not yet migrated for mode: {mode_name}")

    # At this point handler is not None, so we can safely return it
    return handler  # type: ignore


async def execute_mode(mode_name: str, args: Any) -> int:
    """Execute the specified mode with given arguments.

    This function will coordinate mode execution during Phase 2 migration
    when mode handlers are moved from root main.py.

    Args:
        mode_name: Name of the mode to execute
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        handler = get_mode_handler(mode_name)

        # Execute handler (all current modes are async)
        if MODE_REGISTRY[mode_name]["async_mode"]:
            result = await handler(args)
            return int(result) if result is not None else 0
        result = handler(args)
        return int(result) if result is not None else 0

    except KeyError as e:
        print(f"Error: {e}")
        return 1
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Mode handlers will be available after Phase 2 migration")
        return 1
    except Exception as e:
        print(f"Mode execution error: {e}")
        return 1


__all__ = [
    "MODE_REGISTRY",
    "execute_mode",
    "get_available_modes",
    "get_mode_handler",
    "register_mode",
    "run_daemon_mode",
]
