#!/usr/bin/env python3
"""
Debug script to add enhanced header logging to CalendarBot Lite temporarily.
This will help us see exactly what headers Caddy is forwarding.
"""

import sys
from pathlib import Path

# Add the parent directory to Python path to import calendarbot_lite
sys.path.insert(0, str(Path(__file__).parent.parent))


def patch_bearer_token_check():
    """Patch the bearer token check to log all received headers."""
    import calendarbot_lite.server as server_module

    # Store original function
    original_check = server_module._check_bearer_token

    def debug_check_bearer_token(request):
        """Enhanced bearer token check with header logging."""
        print("\n=== DEBUG: Headers received ===")
        for name, value in request.headers.items():
            if name.lower() == "authorization":
                print(f"🔑 {name}: {value}")
            else:
                print(f"📋 {name}: {value}")
        print("=== End Headers ===\n")

        # Call original function
        return original_check(request)

    # Replace the function
    server_module._check_bearer_token = debug_check_bearer_token
    print("✅ Patched bearer token check with debug logging")


if __name__ == "__main__":
    print("🔧 This script patches CalendarBot Lite to show debug headers")
    print("Run this and then start CalendarBot Lite:")
    print("  python scripts/debug_headers.py")
    print("  python -m calendarbot_lite --port 8080")

    patch_bearer_token_check()
