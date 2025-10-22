"""Command-line entry for calendarbot_lite.

This module provides a tiny, import-light CLI that invokes the package's
run_server() entrypoint. Since the server is not implemented in this step,
calling the module will print a friendly message explaining next steps.
"""

from __future__ import annotations

import sys
from typing import NoReturn

# Import the local run_server function lazily to keep top-level imports cheap.
from . import run_server


def main() -> NoReturn:
    """Run the calendarbot_lite CLI.

    This calls run_server() and catches NotImplementedError so that developers
    running the package during early development receive a clear message.
    """
    try:
        run_server()
    except NotImplementedError as exc:
        # User-friendly message for developers running `python -m calendarbot_lite`.
        print(
            "calendarbot_lite server is not implemented yet.\n\n"
            "To continue development:\n"
            "  - Implement the server in `calendarbot_lite.server` and expose a\n"
            "    start function called from `calendarbot_lite.run_server()`.\n"
            "  - Run the package in dev mode with: python -m calendarbot_lite\n"
        )
        # Print the underlying message for clarity in tests / automation.
        print(f"Details: {exc}")
        sys.exit(0)


if __name__ == "__main__":
    main()
