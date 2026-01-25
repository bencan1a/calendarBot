"""Command-line entry for calendarbot_lite.

This module provides a tiny, import-light CLI that invokes the package's
run_server() entrypoint. Since the server is not implemented in this step,
calling the module will print a friendly message explaining next steps.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

# Import the local run_server function lazily to keep top-level imports cheap.
from . import run_server


def _create_parser() -> argparse.ArgumentParser:
    """Create argument parser for calendarbot_lite CLI.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="calendarbot_lite",
        description="CalendarBot Lite - minimal standalone calendar server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m calendarbot_lite                    # Start server on default port (8080)
  python -m calendarbot_lite --port 3000        # Start server on port 3000
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        help="Port number for the web server (default: 8080, or from CALENDARBOT_WEB_PORT env var)",
    )

    parser.add_argument(
        "--ui",
        choices=["none", "framebuffer"],
        default="none",
        help="UI display mode (default: none)",
    )

    parser.add_argument(
        "--display-mode",
        choices=["window", "fullscreen"],
        default="fullscreen",
        help="Display mode for UI (default: fullscreen)",
    )

    parser.add_argument(
        "--backend",
        choices=["local", "remote"],
        default="local",
        help="Backend type (default: local)",
    )

    parser.add_argument(
        "--backend-url",
        metavar="URL",
        help="URL for remote backend (required when --backend=remote)",
    )

    return parser


def main() -> NoReturn:
    """Run the calendarbot_lite CLI.

    This calls run_server() and catches NotImplementedError so that developers
    running the package during early development receive a clear message.
    """
    parser = _create_parser()
    args = parser.parse_args()

    # Validate argument combinations
    if args.ui == "framebuffer" and args.backend == "remote":
        if not args.backend_url:
            parser.error("--backend-url is required when using --backend remote")

    if args.display_mode != "fullscreen" and args.ui == "none":
        print(
            "Warning: --display-mode has no effect without --ui framebuffer",
            file=sys.stderr,
        )

    try:
        run_server(args)
        # If run_server() returns normally, exit successfully
        sys.exit(0)
    except NotImplementedError as exc:
        # User-friendly message for developers running `python -m calendarbot_lite`.
        print(
            "calendarbot_lite server is not implemented yet.\n\n"
            "To continue development:\n"
            "  - Implement the server in `calendarbot_lite.api.server` and expose a\n"
            "    start function called from `calendarbot_lite.run_server()`.\n"
            "  - Run the package in dev mode with: python -m calendarbot_lite\n"
        )
        # Print the underlying message for clarity in tests / automation.
        print(f"Details: {exc}")
        sys.exit(0)


if __name__ == "__main__":
    main()
