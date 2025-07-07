#!/usr/bin/env python3
"""Debug script to validate the entry point issue."""

import inspect
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Debug the entry point configuration issue."""
    print("=== ENTRY POINT DIAGNOSIS ===")

    # Import the main module
    try:
        import main

        print(f"✅ Successfully imported main module from: {main.__file__}")
    except Exception as e:
        print(f"❌ Failed to import main module: {e}")
        return

    # Check if main_entry exists
    if hasattr(main, "main_entry"):
        main_entry_func = getattr(main, "main_entry")
        print(f"✅ Found main_entry function: {main_entry_func}")

        # Check if it's a coroutine function
        if inspect.iscoroutinefunction(main_entry_func):
            print("🔍 DIAGNOSIS: main_entry is an ASYNC function (coroutine)")
            print("❌ PROBLEM: Entry points expect SYNCHRONOUS functions")
            print("💡 SOLUTION: Need a sync wrapper function")
        else:
            print("✅ main_entry is a synchronous function")
    else:
        print("❌ main_entry function not found in main module")

    # Check if main wrapper exists
    if hasattr(main, "main"):
        main_func = getattr(main, "main")
        print(f"✅ Found main wrapper function: {main_func}")

        # Check if it's a coroutine function
        if inspect.iscoroutinefunction(main_func):
            print("❌ main wrapper is ASYNC (should be sync)")
        else:
            print("✅ main wrapper is SYNCHRONOUS (correct)")
    else:
        print("❌ main wrapper function not found in main module")

    # Check entry point configuration
    print("\n=== ENTRY POINT CONFIGURATION ===")

    # Check setup.py
    setup_py = project_root / "setup.py"
    if setup_py.exists():
        content = setup_py.read_text()
        if "calendarbot=main:main" in content:
            print("✅ setup.py: calendarbot=main:main (FIXED)")
        elif "calendarbot=main:main_entry" in content:
            print("❌ setup.py: calendarbot=main:main_entry (OLD ASYNC)")
        else:
            print("❓ Entry point not found in setup.py")

    # Check pyproject.toml
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if 'calendarbot = "main:main"' in content:
            print('✅ pyproject.toml: calendarbot = "main:main" (FIXED)')
        elif 'calendarbot = "main:main_entry"' in content:
            print('❌ pyproject.toml: calendarbot = "main:main_entry" (OLD ASYNC)')
        else:
            print("❓ Entry point not found in pyproject.toml")

    print("\n=== RECOMMENDATION ===")
    print("Create a synchronous wrapper function that calls asyncio.run(main_entry())")
    print("Update entry points to point to the sync wrapper instead of async main_entry")


if __name__ == "__main__":
    main()
