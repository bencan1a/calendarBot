#!/usr/bin/env python3
"""
Diagnostic script to analyze package structure discrepancy issue.

This script will help identify the root cause of the ModuleNotFoundError
for 'calendarbot.sources' by comparing local vs installed package structures.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def check_package_locations() -> Dict[str, Any]:
    """Check where calendarbot packages are located."""
    print("=== PACKAGE LOCATION ANALYSIS ===")

    locations = {
        "local_sources_exists": False,
        "pipx_location": None,
        "local_location": None,
        "python_path": sys.path,
        "current_dir": os.getcwd(),
    }

    # Check local sources module
    local_sources = Path("calendarbot/sources")
    locations["local_sources_exists"] = local_sources.exists()
    locations["local_location"] = (
        str(Path("calendarbot").absolute()) if Path("calendarbot").exists() else None
    )

    print(f"Local sources module exists: {locations['local_sources_exists']}")
    print(f"Current directory: {locations['current_dir']}")
    print(f"Local calendarbot location: {locations['local_location']}")

    # Find pipx installation
    try:
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "calendarbot" in result.stdout:
            print("✓ CalendarBot found in pipx installations")
            # Extract location from pipx info
            pipx_info = subprocess.run(
                ["pipx", "list", "--verbose"], capture_output=True, text=True
            )
            lines = pipx_info.stdout.split("\n")
            for line in lines:
                if "calendarbot" in line and "site-packages" in line:
                    locations["pipx_location"] = line.strip()
                    break
        else:
            print("✗ CalendarBot not found in pipx installations")
    except FileNotFoundError:
        print("✗ pipx not found")

    print(f"Pipx location: {locations['pipx_location']}")

    return locations


def check_import_paths() -> Dict[str, Any]:
    """Check Python import behavior."""
    print("\n=== IMPORT PATH ANALYSIS ===")

    import_info = {
        "can_import_calendarbot": False,
        "calendarbot_file_location": None,
        "can_import_sources": False,
        "sources_location": None,
        "import_error": None,
    }

    # Test importing calendarbot
    try:
        import calendarbot

        import_info["can_import_calendarbot"] = True
        import_info["calendarbot_file_location"] = (
            str(calendarbot.__file__) if hasattr(calendarbot, "__file__") else None
        )
        print(f"✓ Can import calendarbot from: {import_info['calendarbot_file_location']}")

        # Test importing sources
        try:
            from calendarbot import sources

            import_info["can_import_sources"] = True
            import_info["sources_location"] = (
                str(sources.__file__) if hasattr(sources, "__file__") else None
            )
            print(f"✓ Can import calendarbot.sources from: {import_info['sources_location']}")
        except ImportError as e:
            import_info["import_error"] = str(e)
            print(f"✗ Cannot import calendarbot.sources: {e}")

    except ImportError as e:
        import_info["import_error"] = str(e)
        print(f"✗ Cannot import calendarbot: {e}")

    return import_info


def check_installed_structure() -> Dict[str, Any]:
    """Check the structure of installed package vs local."""
    print("\n=== PACKAGE STRUCTURE COMPARISON ===")

    structure_info = {"local_modules": [], "installed_modules": [], "missing_in_installed": []}

    # Check local structure
    local_calendarbot = Path("calendarbot")
    if local_calendarbot.exists():
        for item in local_calendarbot.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                structure_info["local_modules"].append(item.name)
        print(f"Local modules: {structure_info['local_modules']}")

    # Check installed structure
    try:
        import calendarbot

        if hasattr(calendarbot, "__file__"):
            installed_path = Path(calendarbot.__file__).parent
            for item in installed_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    structure_info["installed_modules"].append(item.name)
            print(f"Installed modules: {structure_info['installed_modules']}")

            # Find missing modules
            structure_info["missing_in_installed"] = [
                mod
                for mod in structure_info["local_modules"]
                if mod not in structure_info["installed_modules"]
            ]
            print(f"Missing in installed: {structure_info['missing_in_installed']}")
    except Exception as e:
        print(f"Cannot check installed structure: {e}")

    return structure_info


def check_version_info() -> Dict[str, Any]:
    """Check version information."""
    print("\n=== VERSION INFORMATION ===")

    version_info = {"python_version": sys.version, "local_version": None, "installed_version": None}

    print(f"Python version: {version_info['python_version']}")

    # Check local version
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
            for line in content.split("\n"):
                if line.strip().startswith("version ="):
                    version_info["local_version"] = line.split("=")[1].strip().strip("\"'")
                    break
        print(f"Local version (pyproject.toml): {version_info['local_version']}")
    except Exception as e:
        print(f"Cannot read local version: {e}")

    # Check installed version
    try:
        result = subprocess.run(["calendarbot", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_info["installed_version"] = result.stdout.strip()
            print(f"Installed version: {version_info['installed_version']}")
        else:
            print("Cannot get installed version via --version")
    except Exception as e:
        print(f"Cannot get installed version: {e}")

    return version_info


def generate_diagnostic_report() -> None:
    """Generate comprehensive diagnostic report."""
    print("CALENDARBOT PACKAGE STRUCTURE DIAGNOSTIC")
    print("=" * 50)

    locations = check_package_locations()
    imports = check_import_paths()
    structure = check_installed_structure()
    versions = check_version_info()

    print("\n" + "=" * 50)
    print("DIAGNOSIS SUMMARY")
    print("=" * 50)

    # Analyze the results
    if locations["local_sources_exists"] and not imports["can_import_sources"]:
        print("🔍 DIAGNOSIS: Package structure discrepancy detected!")
        print("   - Local codebase HAS sources module")
        print("   - Installed package MISSING sources module")
        print("   - Running pipx-installed version instead of local development code")

        if structure["missing_in_installed"]:
            print(f"   - Missing modules in installed version: {structure['missing_in_installed']}")

        print("\n🔧 RECOMMENDED SOLUTIONS:")
        print("   1. Reinstall package: pipx reinstall calendarbot")
        print("   2. Use local development mode: python -m calendarbot --web")
        print("   3. Install in development mode: pipx install -e .")

    elif not locations["local_sources_exists"]:
        print("🔍 DIAGNOSIS: Local sources module missing!")
        print("   - This indicates local codebase is incomplete")

    elif imports["can_import_sources"]:
        print("🔍 DIAGNOSIS: No import issues detected")
        print("   - This is unexpected given the error report")

    else:
        print("🔍 DIAGNOSIS: Complex import issue")
        print("   - Further investigation needed")

    print(f"\n📍 Current execution context:")
    print(f"   - Working directory: {locations['current_dir']}")
    print(f"   - Python executable: {sys.executable}")
    if imports["calendarbot_file_location"]:
        print(f"   - Calendarbot loaded from: {imports['calendarbot_file_location']}")


if __name__ == "__main__":
    generate_diagnostic_report()
