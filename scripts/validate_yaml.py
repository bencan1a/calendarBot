#!/usr/bin/env python3
"""Validate YAML syntax in workflow files."""

import glob
import sys

import yaml


def main() -> int:
    """Validate all YAML workflow files."""
    print("Validating YAML files...")

    files = sorted(
        glob.glob(".github/workflows/*.yml") + glob.glob(".github/workflows/*.yaml")
    )

    if not files:
        print("No YAML files found in .github/workflows/")
        return 1

    errors = False
    for file in files:
        print(f"Checking {file}...")
        try:
            with open(file) as f:
                yaml.safe_load(f)
            print(f"  ✓ Valid")
        except yaml.YAMLError as e:
            print(f"  ✗ YAML error: {e}")
            errors = True
        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors = True

    if errors:
        print("\n❌ Some YAML files have errors")
        return 1

    print("\n✅ All YAML files are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
