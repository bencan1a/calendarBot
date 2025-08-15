#!/usr/bin/env python3
"""
CalendarBot Environment Setup Script

Configures environment variables during installation or setup.
Creates and updates .env file with appropriate production/development settings.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def read_existing_env(env_file: Path) -> dict[str, str]:
    """Read existing .env file and return as dictionary."""
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def write_env_file(env_file: Path, env_vars: dict[str, str]) -> None:
    """Write environment variables to .env file."""
    with open(env_file, "w") as f:
        f.write("# CalendarBot Environment Configuration\n")
        f.write("# This file contains the actual configuration values for this application\n\n")

        # Group related variables
        groups = {
            "ICS Calendar Configuration": ["CALENDARBOT_ICS_URL", "CALENDARBOT_ICS_AUTH_TYPE"],
            "Application Settings": [
                "CALENDARBOT_APP_NAME",
                "CALENDARBOT_REFRESH_INTERVAL",
                "CALENDARBOT_CACHE_TTL",
            ],
            "Display Settings": ["CALENDARBOT_DISPLAY_ENABLED", "CALENDARBOT_DISPLAY_TYPE"],
            "Logging Configuration": [
                "CALENDARBOT_LOGGING__CONSOLE_LEVEL",
                "CALENDARBOT_LOGGING__FILE_ENABLED",
                "CALENDARBOT_LOGGING__FILE_LEVEL",
            ],
            "Build Configuration": ["CALENDARBOT_ENV", "CALENDARBOT_DEBUG"],
        }

        for group_name, var_names in groups.items():
            f.write(f"# {group_name}\n")
            for var_name in var_names:
                if var_name in env_vars:
                    value = env_vars[var_name]
                    # Add comments for certain variables
                    if var_name == "CALENDARBOT_ENV":
                        f.write("# Set environment mode: production, development, or debug\n")
                    elif var_name == "CALENDARBOT_DEBUG":
                        f.write("# Debug flag (alternative to CALENDARBOT_ENV)\n")
                        f.write("# Set to true for development mode, false for production\n")

                    # Comment out CALENDARBOT_DEBUG by default since CALENDARBOT_ENV is preferred
                    prefix = "# " if var_name == "CALENDARBOT_DEBUG" else ""
                    f.write(f"{prefix}{var_name}={value}\n")
            f.write("\n")


def setup_production_env() -> dict[str, str]:
    """Set up environment variables for production deployment."""
    return {
        "CALENDARBOT_ENV": "production",
        "CALENDARBOT_DEBUG": "false",
        "CALENDARBOT_APP_NAME": "CalendarBot",
        "CALENDARBOT_REFRESH_INTERVAL": "300",
        "CALENDARBOT_CACHE_TTL": "3600",
        "CALENDARBOT_DISPLAY_ENABLED": "true",
        "CALENDARBOT_DISPLAY_TYPE": "console",
        "CALENDARBOT_LOGGING__CONSOLE_LEVEL": "WARNING",
        "CALENDARBOT_LOGGING__FILE_ENABLED": "true",
        "CALENDARBOT_LOGGING__FILE_LEVEL": "INFO",
    }


def setup_development_env() -> dict[str, str]:
    """Set up environment variables for development."""
    return {
        "CALENDARBOT_ENV": "development",
        "CALENDARBOT_DEBUG": "true",
        "CALENDARBOT_APP_NAME": "CalendarBot-Dev",
        "CALENDARBOT_REFRESH_INTERVAL": "60",
        "CALENDARBOT_CACHE_TTL": "300",
        "CALENDARBOT_DISPLAY_ENABLED": "true",
        "CALENDARBOT_DISPLAY_TYPE": "console",
        "CALENDARBOT_LOGGING__CONSOLE_LEVEL": "DEBUG",
        "CALENDARBOT_LOGGING__FILE_ENABLED": "true",
        "CALENDARBOT_LOGGING__FILE_LEVEL": "DEBUG",
    }


def prompt_for_setup_mode() -> str:
    """Prompt user for setup mode."""
    print("CalendarBot Environment Setup")
    print("=" * 40)
    print("Choose your setup mode:")
    print("1. Production (optimized for deployment)")
    print("2. Development (debug features enabled)")
    print("3. Keep existing settings")

    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("Invalid choice. Please enter 1, 2, or 3.")


def main():
    """Main setup function."""
    project_root = get_project_root()
    env_file = project_root / ".env"

    print("Setting up environment for CalendarBot")
    print(f"Project root: {project_root}")
    print(f"Environment file: {env_file}")

    # Read existing environment variables
    existing_vars = read_existing_env(env_file)

    # Handle command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        choice = prompt_for_setup_mode()
        mode_map = {"1": "production", "2": "development", "3": "keep"}
        mode = mode_map[choice]

    if mode == "production":
        print("\n🚀 Setting up PRODUCTION environment...")
        env_vars = setup_production_env()
        # Preserve existing non-build configuration
        for key, value in existing_vars.items():
            if not key.startswith(("CALENDARBOT_ENV", "CALENDARBOT_DEBUG")):
                env_vars[key] = value
    elif mode == "development":
        print("\n🔧 Setting up DEVELOPMENT environment...")
        env_vars = setup_development_env()
        # Preserve existing non-build configuration
        for key, value in existing_vars.items():
            if not key.startswith(("CALENDARBOT_ENV", "CALENDARBOT_DEBUG")):
                env_vars[key] = value
    elif mode == "keep":
        print("\n📋 Keeping existing environment settings...")
        env_vars = existing_vars
        # Ensure build configuration variables exist
        if "CALENDARBOT_ENV" not in env_vars:
            env_vars["CALENDARBOT_ENV"] = "production"
        if "CALENDARBOT_DEBUG" not in env_vars:
            env_vars["CALENDARBOT_DEBUG"] = "false"
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python setup_env.py [production|development|keep]")
        sys.exit(1)

    # Write the environment file
    write_env_file(env_file, env_vars)

    print(f"\n✅ Environment configuration written to {env_file}")
    print(f"📝 Environment mode: {env_vars.get('CALENDARBOT_ENV', 'production')}")

    # Show debug asset exclusion info
    if env_vars.get("CALENDARBOT_ENV") == "production":
        print("\n📊 Production optimizations enabled:")
        print("   • Debug JavaScript assets will be excluded")
        print("   • Estimated heap reduction: ~45MB")
        print("   • Target files: settings-panel.js, settings-api.js, gesture-handler.js")
    else:
        print("\n🔧 Development mode enabled:")
        print("   • All JavaScript assets available for debugging")
        print("   • Debug logging enabled")

    print("\n🎯 Setup complete! CalendarBot is ready to run.")
    print("💡 Run 'calendarbot --web --port 8080' to start the application")


if __name__ == "__main__":
    main()
