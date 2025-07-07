#!/usr/bin/env python3
"""
Test Framework Validation Script
Validates that the sequential test framework is properly configured.
"""

import os
import subprocess
import sys
from pathlib import Path

import yaml


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a required file exists."""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} - MISSING")
        return False


def check_pytest_config() -> bool:
    """Validate pytest configuration."""
    print("\n📋 Checking pytest configuration...")

    issues = []

    # Check main pytest.ini
    if Path("pytest.ini").exists():
        with open("pytest.ini", "r") as f:
            lines = f.readlines()

        # Check for problematic parallel execution options (ignore comments)
        parallel_found = False
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue  # Skip comments and empty lines
            if "-n auto" in line or "--dist" in line:
                parallel_found = True
                break

        if parallel_found:
            issues.append("Found parallel execution options in pytest.ini")
        else:
            print("✓ No parallel execution options in pytest.ini")

        content = "".join(lines)
        if "timeout = " in content:
            print("✓ Timeout configuration found")
        else:
            issues.append("No timeout configuration found")

        if "asyncio_mode = auto" in content:
            print("✓ Asyncio mode configured")
        else:
            issues.append("Asyncio mode not configured")
    else:
        issues.append("pytest.ini not found")

    # Check tests/pytest.ini
    if Path("tests/pytest.ini").exists():
        with open("tests/pytest.ini", "r") as f:
            lines = f.readlines()

        # Check for parallel execution options (ignore comments)
        parallel_found = False
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue  # Skip comments and empty lines
            if "-n auto" in line:
                parallel_found = True
                break

        if parallel_found:
            issues.append("Found parallel execution in tests/pytest.ini")
        else:
            print("✓ No parallel execution in tests/pytest.ini")

    if issues:
        print(f"✗ Pytest configuration issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ Pytest configuration is valid")
        return True


def check_coverage_config() -> bool:
    """Validate coverage configuration."""
    print("\n📊 Checking coverage configuration...")

    if not Path(".coveragerc").exists():
        print("✗ .coveragerc not found")
        return False

    with open(".coveragerc", "r") as f:
        content = f.read()

    issues = []

    if "parallel = False" in content:
        print("✓ Coverage parallel execution disabled")
    else:
        issues.append("Coverage parallel execution not disabled")

    if "source = calendarbot" in content:
        print("✓ Coverage source configured")
    else:
        issues.append("Coverage source not configured")

    if issues:
        print(f"✗ Coverage configuration issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ Coverage configuration is valid")
        return True


def check_test_suite_config() -> bool:
    """Validate test suite configuration."""
    print("\n🧪 Checking test suite configuration...")

    if not Path("test_suite_config.yaml").exists():
        print("✗ test_suite_config.yaml not found")
        return False

    try:
        with open("test_suite_config.yaml", "r") as f:
            config = yaml.safe_load(f)

        # Check required sections
        required_sections = ["execution", "batches", "logging", "coverage"]
        missing_sections = []

        for section in required_sections:
            if section in config:
                print(f"✓ {section} section found")
            else:
                missing_sections.append(section)

        if missing_sections:
            print(f"✗ Missing sections: {missing_sections}")
            return False

        # Check execution mode
        if config.get("execution", {}).get("mode") == "sequential":
            print("✓ Sequential execution mode configured")
        else:
            print("✗ Sequential execution mode not configured")
            return False

        # Check batches
        batches = config.get("batches", {})
        if len(batches) > 0:
            print(f"✓ {len(batches)} test batches configured")
        else:
            print("✗ No test batches configured")
            return False

        return True

    except yaml.YAMLError as e:
        print(f"✗ YAML parsing error: {e}")
        return False
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def check_execution_script() -> bool:
    """Validate execution script."""
    print("\n🚀 Checking execution script...")

    script_path = Path("run_sequential_tests.py")

    if not script_path.exists():
        print("✗ run_sequential_tests.py not found")
        return False

    # Check if executable
    if os.access(script_path, os.X_OK):
        print("✓ Execution script is executable")
    else:
        print("⚠ Execution script is not executable (run: chmod +x run_sequential_tests.py)")

    # Check script content
    with open(script_path, "r") as f:
        content = f.read()

    if "SequentialTestRunner" in content:
        print("✓ SequentialTestRunner class found")
    else:
        print("✗ SequentialTestRunner class not found")
        return False

    if "activate_venv" in content:
        print("✓ Virtual environment activation check found")
    else:
        print("✗ Virtual environment activation check not found")
        return False

    return True


def check_dependencies() -> bool:
    """Check required dependencies."""
    print("\n📦 Checking dependencies...")

    # Map package names to their import names
    required_packages = {
        "pytest": "pytest",
        "pytest-asyncio": "pytest_asyncio",
        "pytest-timeout": "pytest_timeout",
        "pytest-cov": "pytest_cov",
        "pyyaml": "yaml",  # pyyaml package imports as 'yaml'
    }

    missing_packages = []

    for package, import_name in required_packages.items():
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {import_name}"], capture_output=True, text=True
            )

            if result.returncode == 0:
                print(f"✓ {package}")
            else:
                missing_packages.append(package)
        except Exception:
            missing_packages.append(package)

    if missing_packages:
        print(f"✗ Missing packages: {missing_packages}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False

    return True


def main():
    """Main validation function."""
    print("🔍 CalendarBot Sequential Test Framework Validation")
    print("=" * 60)

    checks = [
        (
            "Configuration files",
            lambda: all(
                [
                    check_file_exists("pytest.ini", "Main pytest config"),
                    check_file_exists(".coveragerc", "Coverage config"),
                    check_file_exists("test_suite_config.yaml", "Test suite config"),
                    check_file_exists("run_sequential_tests.py", "Execution script"),
                    check_file_exists("test_logging.conf", "Logging config"),
                    check_file_exists("tests/conftest.py", "Test fixtures"),
                ]
            ),
        ),
        ("Pytest configuration", check_pytest_config),
        ("Coverage configuration", check_coverage_config),
        ("Test suite configuration", check_test_suite_config),
        ("Execution script", check_execution_script),
        ("Dependencies", check_dependencies),
    ]

    all_passed = True

    for check_name, check_func in checks:
        print(f"\n{check_name}...")
        if not check_func():
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All validation checks PASSED!")
        print("\nTest framework is properly configured for sequential execution.")
        print("\nNext steps:")
        print("1. Run: ./run_sequential_tests.py --list-batches")
        print("2. Run: ./run_sequential_tests.py --batches fast_unit")
        print("3. Run: ./run_sequential_tests.py")
    else:
        print("❌ Some validation checks FAILED!")
        print("\nPlease fix the issues above before running tests.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
