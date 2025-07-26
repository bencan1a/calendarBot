#!/usr/bin/env python3
"""
Diagnostic script to validate assumptions about display test failures.
"""

import inspect
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def validate_method_existence():
    """Check if expected methods exist in their expected locations."""
    print("=== METHOD EXISTENCE VALIDATION ===")

    try:
        from calendarbot.display.whats_next_data_model import WhatsNextViewModel
        from calendarbot.display.whats_next_logic import WhatsNextLogic
        from calendarbot.display.whats_next_renderer import WhatsNextRenderer

        # Check WhatsNextRenderer methods
        renderer_methods = [
            method for method in dir(WhatsNextRenderer) if not method.startswith("__")
        ]
        print(f"WhatsNextRenderer methods: {renderer_methods}")

        # Check if _find_next_upcoming_event exists in renderer
        has_find_method = hasattr(WhatsNextRenderer, "_find_next_upcoming_event")
        print(f"WhatsNextRenderer._find_next_upcoming_event exists: {has_find_method}")

        # Check if it exists in logic instead
        logic_has_find_method = hasattr(WhatsNextLogic, "find_next_upcoming_event")
        print(f"WhatsNextLogic.find_next_upcoming_event exists: {logic_has_find_method}")

        # Check WhatsNextLogic methods
        logic_methods = [method for method in dir(WhatsNextLogic) if not method.startswith("__")]
        print(f"WhatsNextLogic methods: {logic_methods}")

        # Check data model functions
        try:
            from calendarbot.utils.helpers import get_timezone_aware_now

            print("get_timezone_aware_now found in utils.helpers: True")
        except ImportError:
            print("get_timezone_aware_now found in utils.helpers: False")

        # Check utils.helpers
        try:
            from calendarbot.utils.helpers import get_timezone_aware_now

            print("get_timezone_aware_now found in utils.helpers: True")
        except ImportError:
            print("get_timezone_aware_now found in utils.helpers: False")

    except ImportError as e:
        print(f"Import error: {e}")


def validate_interface_implementations():
    """Check RendererInterface implementation details."""
    print("\n=== INTERFACE IMPLEMENTATION VALIDATION ===")

    try:
        from calendarbot.display.renderer_interface import RendererInterface
        from calendarbot.display.whats_next_renderer import WhatsNextRenderer

        # Get method signatures
        interface_methods = [
            method
            for method in dir(RendererInterface)
            if not method.startswith("__") and callable(getattr(RendererInterface, method, None))
        ]
        print(f"RendererInterface abstract methods: {interface_methods}")

        # Check WhatsNextRenderer implementation
        renderer_methods = [
            method
            for method in dir(WhatsNextRenderer)
            if not method.startswith("__") and callable(getattr(WhatsNextRenderer, method, None))
        ]
        print(f"WhatsNextRenderer methods: {renderer_methods}")

        # Check handle_interaction signature
        if hasattr(WhatsNextRenderer, "handle_interaction"):
            sig = inspect.signature(WhatsNextRenderer.handle_interaction)
            print(f"WhatsNextRenderer.handle_interaction signature: {sig}")

    except ImportError as e:
        print(f"Import error: {e}")


def validate_debug_time_logic():
    """Check debug time handling in WhatsNextLogic."""
    print("\n=== DEBUG TIME LOGIC VALIDATION ===")

    try:
        from unittest.mock import MagicMock

        from calendarbot.display.whats_next_logic import WhatsNextLogic

        # Create mock settings
        mock_settings = MagicMock()
        logic = WhatsNextLogic(mock_settings)

        # Check initial state
        print(f"Initial _debug_time: {logic._debug_time}")

        # Test set_debug_time
        from datetime import datetime

        test_time = datetime(2025, 7, 14, 15, 30, 0)
        logic.set_debug_time(test_time)
        print(f"After setting debug time: {logic._debug_time}")

        # Test get_current_time behavior
        current_time = logic.get_current_time()
        print(f"get_current_time returned: {current_time}")
        print(f"Type: {type(current_time)}")

    except Exception as e:
        print(f"Error in debug time validation: {e}")


def main():
    """Run all validations."""
    print("DIAGNOSTIC: Display Test Failures")
    print("=" * 50)

    validate_method_existence()
    validate_interface_implementations()
    validate_debug_time_logic()

    print("\n=== SUMMARY ===")
    print("Check the output above to validate our assumptions about the test failures.")


if __name__ == "__main__":
    main()
