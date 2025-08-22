#!/usr/bin/env python3
"""Debug script to validate HTMLRenderer method signature."""

import inspect
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot.display.html_renderer import HTMLRenderer


def analyze_method_signature():
    """Analyze the _build_html_template method signature."""
    print("=== HTMLRenderer._build_html_template Method Signature Analysis ===")

    # Get the method signature
    method = HTMLRenderer._build_html_template
    sig = inspect.signature(method)

    print(f"Method: {method}")
    print(f"Signature: {sig}")
    print("\nParameters:")
    for param_name, param in sig.parameters.items():
        print(f"  {param_name}: {param.annotation} = {param.default}")

    # Check if 'interactive_mode' parameter exists
    has_interactive_mode = "interactive_mode" in sig.parameters
    print(f"\nHas 'interactive_mode' parameter: {has_interactive_mode}")

    # Show what the failing tests are trying to call
    print("\n=== Test Call Patterns ===")
    print("Test calls are trying to use:")
    print("  interactive_mode=True  (line 59, 89)")
    print("  interactive_mode=False (line 199)")

    print(
        f"\nCONCLUSION: {'✅ Parameter exists' if has_interactive_mode else '❌ Parameter MISSING - This is the problem!'}"
    )


if __name__ == "__main__":
    analyze_method_signature()
