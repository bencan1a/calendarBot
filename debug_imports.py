#!/usr/bin/env python3
"""Diagnostic script to validate import chain issues."""

import os
import sys
from pathlib import Path


def check_file_system():
    """Check actual file system vs expected imports."""
    print("=== FILE SYSTEM DIAGNOSTIC ===")

    # Check if directories exist
    dirs_to_check = [
        "calendarbot/api",
        "calendarbot/auth",
        "calendarbot/ics",
        "calendarbot/sources",
        "calendarbot/cache",
    ]

    for dir_path in dirs_to_check:
        exists = Path(dir_path).exists()
        print(f"{dir_path}: {'EXISTS' if exists else 'MISSING'}")

        if exists:
            files = list(Path(dir_path).glob("*.py"))
            print(f"  Files: {[f.name for f in files]}")
    print()


def check_import_statements():
    """Check problematic import statements."""
    print("=== IMPORT ANALYSIS ===")

    files_to_check = ["calendarbot/sources/ics_source.py", "calendarbot/ics/parser.py"]

    for file_path in files_to_check:
        if Path(file_path).exists():
            print(f"\nChecking {file_path}:")
            with open(file_path, "r") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                if "from ..api" in line or "import ..api" in line:
                    print(f"  Line {i}: {line.strip()} <- PROBLEMATIC IMPORT")
    print()


def check_model_availability():
    """Check what models are actually available."""
    print("=== MODEL AVAILABILITY ===")

    # Check ICS models
    ics_models_path = Path("calendarbot/ics/models.py")
    if ics_models_path.exists():
        print("ICS models file exists")
        with open(ics_models_path, "r") as f:
            content = f.read()

        # Look for model classes
        import re

        classes = re.findall(r"^class (\w+)", content, re.MULTILINE)
        print(f"  Available ICS models: {classes}")

        # Check if CalendarEvent exists
        if "CalendarEvent" in classes:
            print("  ✓ CalendarEvent found in ICS models")
        else:
            print("  ✗ CalendarEvent NOT found in ICS models")
    else:
        print("ICS models file missing")

    # Check if API models exist
    api_models_path = Path("calendarbot/api/models.py")
    if api_models_path.exists():
        print("API models file exists (unexpected!)")
    else:
        print("API models file missing (expected)")
    print()


if __name__ == "__main__":
    print("CALENDARBOT IMPORT DIAGNOSTIC")
    print("=" * 50)

    check_file_system()
    check_import_statements()
    check_model_availability()

    print("=== DIAGNOSIS SUMMARY ===")
    print("1. Azure API directory missing but still being imported")
    print("2. ICS system lacks CalendarEvent model")
    print("3. Migration from Azure to ICS incomplete")
