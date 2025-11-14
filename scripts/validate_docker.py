#!/usr/bin/env python3
"""
Docker configuration validator for CalendarBot.

This script validates the Docker setup without requiring a full build,
checking that all necessary files exist and are properly configured.
"""

import os
import sys
from pathlib import Path


def validate_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    if not Path(filepath).exists():
        print(f"❌ Missing: {description} ({filepath})")
        return False
    print(f"✓ Found: {description}")
    return True


def validate_dockerfile() -> bool:
    """Validate Dockerfile exists and contains required directives."""
    filepath = "Dockerfile"
    if not validate_file_exists(filepath, "Dockerfile"):
        return False

    with open(filepath) as f:
        content = f.read()

    required = [
        ("FROM", "Base image declaration"),
        ("EXPOSE 8080", "Port exposure"),
        ("WORKDIR", "Working directory"),
        ("CMD", "Container command"),
        ("HEALTHCHECK", "Health check"),
    ]

    all_valid = True
    for directive, description in required:
        if directive in content:
            print(f"  ✓ Contains: {description}")
        else:
            print(f"  ❌ Missing: {description} ({directive})")
            all_valid = False

    return all_valid


def validate_docker_compose() -> bool:
    """Validate docker-compose.yml exists and contains required sections."""
    filepath = "docker-compose.yml"
    if not validate_file_exists(filepath, "Docker Compose configuration"):
        return False

    with open(filepath) as f:
        content = f.read()

    required = [
        ("services:", "Services definition"),
        ("ports:", "Port mapping"),
        ("env_file:", "Environment file"),
        ("healthcheck:", "Health check"),
        ("networks:", "Network configuration"),
    ]

    all_valid = True
    for directive, description in required:
        if directive in content:
            print(f"  ✓ Contains: {description}")
        else:
            print(f"  ❌ Missing: {description} ({directive})")
            all_valid = False

    return all_valid


def validate_dockerignore() -> bool:
    """Validate .dockerignore exists."""
    return validate_file_exists(".dockerignore", "Docker ignore file")


def validate_env_template() -> bool:
    """Validate .env.docker template exists."""
    filepath = ".env.docker"
    if not validate_file_exists(filepath, "Docker environment template"):
        return False

    with open(filepath) as f:
        content = f.read()

    required = [
        "CALENDARBOT_ICS_URL",
        "CALENDARBOT_WEB_HOST",
        "CALENDARBOT_WEB_PORT",
    ]

    all_valid = True
    for var in required:
        if var in content:
            print(f"  ✓ Contains: {var}")
        else:
            print(f"  ❌ Missing: {var}")
            all_valid = False

    return all_valid


def validate_documentation() -> bool:
    """Validate Docker documentation exists."""
    return validate_file_exists("DOCKER.md", "Docker documentation")


def validate_dependencies() -> bool:
    """Validate required dependency files exist."""
    files = [
        ("requirements.txt", "Python requirements"),
        ("pyproject.toml", "Project configuration"),
        ("README.md", "Project README"),
    ]

    all_valid = True
    for filepath, description in files:
        if not validate_file_exists(filepath, description):
            all_valid = False

    return all_valid


def validate_application() -> bool:
    """Validate application code exists."""
    files = [
        ("calendarbot_lite/__init__.py", "CalendarBot Lite package"),
        ("calendarbot_lite/__main__.py", "Application entry point"),
        ("main.py", "VSCode entry point"),
    ]

    all_valid = True
    for filepath, description in files:
        if not validate_file_exists(filepath, description):
            all_valid = False

    return all_valid


def main() -> int:
    """Run all validations."""
    print("=" * 60)
    print("CalendarBot Docker Configuration Validator")
    print("=" * 60)
    print()

    # Change to repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)
    print(f"Working directory: {Path.cwd()}")
    print()

    validations = [
        ("Dockerfile", validate_dockerfile),
        ("Docker Compose", validate_docker_compose),
        ("Docker Ignore", validate_dockerignore),
        ("Environment Template", validate_env_template),
        ("Documentation", validate_documentation),
        ("Dependencies", validate_dependencies),
        ("Application", validate_application),
    ]

    results = {}
    for name, validator in validations:
        print(f"\n{name}:")
        print("-" * 60)
        results[name] = validator()

    print("\n" + "=" * 60)
    print("Validation Summary:")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All validations passed!")
        print("\nDocker configuration is ready for use.")
        print("\nNext steps:")
        print("  1. Copy .env.docker to .env and configure")
        print("  2. Run: docker-compose up -d")
        print("  3. Access: http://localhost:8080")
        return 0
    print("\n❌ Some validations failed!")
    print("\nPlease fix the issues above before using Docker.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
