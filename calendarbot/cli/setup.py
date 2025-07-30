"""Setup wizard functionality for Calendar Bot CLI.

This module provides the setup wizard interface and integration
for first-time configuration of Calendar Bot.
"""



async def run_setup_wizard() -> int:
    """Run the configuration setup wizard.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Import the comprehensive setup wizard
        from calendarbot.setup_wizard import run_setup_wizard as run_async_wizard, run_simple_wizard

        # Check if user wants full wizard or simple wizard
        print("\n" + "=" * 60)
        print("📅 Calendar Bot Configuration Wizard")
        print("=" * 60)
        print("Choose setup mode:")
        print("1. Full wizard (recommended) - Interactive setup with testing and templates")
        print("2. Quick setup - Basic configuration")
        print()

        choice = input("Enter choice (1 or 2) [1]: ").strip()

        if choice == "2":
            # Run simple wizard
            print("Running quick setup...")
            success = run_simple_wizard()
            return 0 if success else 1
        # Run full async wizard
        print("Running full interactive wizard...")
        success = await run_async_wizard()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


async def run_async_setup_wizard() -> int:
    """Run the asynchronous setup wizard.

    This function provides async wrapper for the setup wizard functionality
    that will be integrated during Phase 2 migration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Import async wizard from existing module
        from calendarbot.setup_wizard import run_setup_wizard as run_async_wizard

        # Placeholder for async wizard execution
        print("Async setup wizard placeholder - will be integrated in Phase 2")
        success = await run_async_wizard()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


def run_simple_setup_wizard() -> int:
    """Run simplified synchronous setup wizard.

    This function provides integration with the simple setup wizard
    from the existing setup_wizard.py module.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Import simple wizard from existing module
        from calendarbot.setup_wizard import run_simple_wizard

        # Placeholder for simple wizard execution
        print("Simple setup wizard placeholder - will be integrated in Phase 2")
        success = run_simple_wizard()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


__all__ = [
    "run_async_setup_wizard",
    "run_setup_wizard",
    "run_simple_setup_wizard",
]
