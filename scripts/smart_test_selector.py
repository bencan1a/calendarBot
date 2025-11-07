#!/usr/bin/env python3
"""
Smart Test Selector

Identifies tests affected by code changes to enable faster CI runs.
Uses git diff and coverage data to determine which tests need to run.

Usage:
    python scripts/smart_test_selector.py [--base-branch BRANCH] [--output FILE]

Arguments:
    --base-branch: Branch to compare against (default: origin/main)
    --output: Output file for selected tests (default: .pytest-selected-tests.txt)
    --coverage-file: Coverage data file (default: .coverage)
    --verbose: Enable verbose output
    --fallback-threshold: If >N% of files changed, run full suite (default: 30)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Set


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Exit code: {e.returncode}", file=sys.stderr)
        print(f"Output: {e.stdout}", file=sys.stderr)
        print(f"Error: {e.stderr}", file=sys.stderr)
        raise


def get_changed_files(base_branch: str = "origin/main", verbose: bool = False) -> List[str]:
    """Get list of changed Python files and kiosk files compared to base branch."""
    # First try to compare with base branch
    result = run_command(
        ["git", "diff", "--name-only", base_branch, "HEAD"],
        check=False,
    )

    if result.returncode != 0:
        # Fallback: compare with HEAD~1 if base branch doesn't exist
        if verbose:
            print(f"Warning: Could not compare with {base_branch}, using HEAD~1", file=sys.stderr)
        result = run_command(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            check=False,
        )

        if result.returncode != 0:
            # Last fallback: get unstaged/staged changes
            if verbose:
                print("Warning: Could not compare with HEAD~1, checking working tree", file=sys.stderr)
            result = run_command(["git", "diff", "--name-only"], check=False)

    changed = []
    for f in result.stdout.splitlines():
        if not Path(f).exists():
            continue
        # Include Python files OR kiosk directory files
        if f.endswith('.py') or f.startswith('kiosk/'):
            changed.append(f)

    if verbose:
        print(f"Found {len(changed)} changed files (Python + kiosk)")
        for f in changed:
            print(f"  - {f}")

    return changed


def get_total_python_files(source_dir: str = "calendarbot_lite") -> int:
    """Count total Python files in source directory."""
    source_path = Path(source_dir)
    if not source_path.exists():
        return 0

    return len(list(source_path.rglob("*.py")))


def find_affected_tests_from_coverage(
    changed_files: List[str],
    coverage_file: str = ".coverage",
    verbose: bool = False,
) -> Set[str]:
    """Find tests that cover the changed files using coverage.py data."""
    affected_tests = set()

    # Check if coverage file exists
    coverage_path = Path(coverage_file)
    if not coverage_path.exists():
        if verbose:
            print(f"Warning: Coverage file {coverage_file} not found", file=sys.stderr)
        return affected_tests

    try:
        from coverage import Coverage

        cov = Coverage(data_file=coverage_file)
        cov.load()
        data = cov.get_data()

        # Get all measured files (includes both source and test files)
        measured_files = list(data.measured_files())

        if verbose:
            print(f"Coverage data contains {len(measured_files)} measured files")

        # For each changed file, find tests that executed it
        for changed_file in changed_files:
            changed_path = str(Path(changed_file).resolve())

            # Find test files that covered this changed file
            for measured_file in measured_files:
                # Check if this is a test file
                if "test_" in measured_file or measured_file.startswith("tests/"):
                    # Check if this test touched the changed file
                    # We do this by checking if both files are in the coverage data
                    # and the test file has executed lines
                    if changed_path in measured_files:
                        affected_tests.add(measured_file)

        if verbose:
            print(f"Found {len(affected_tests)} affected tests from coverage data")

    except ImportError:
        if verbose:
            print("Warning: coverage module not available", file=sys.stderr)
    except Exception as e:
        if verbose:
            print(f"Error reading coverage data: {e}", file=sys.stderr)

    return affected_tests


def find_affected_tests_from_imports(
    changed_files: List[str],
    test_dir: str = "tests/lite",
    verbose: bool = False,
) -> Set[str]:
    """Find tests that import or reference changed files (heuristic approach)."""
    affected_tests = set()
    test_path = Path(test_dir)

    if not test_path.exists():
        if verbose:
            print(f"Warning: Test directory {test_dir} not found", file=sys.stderr)
        return affected_tests

    # Get module names from changed files
    changed_modules = set()
    for changed_file in changed_files:
        # Convert file path to module name
        # e.g., calendarbot_lite/server.py -> calendarbot_lite.server
        module_path = Path(changed_file)
        if module_path.suffix == ".py":
            module_name = str(module_path.with_suffix("")).replace("/", ".")
            changed_modules.add(module_name)
            # Also add the file name without extension
            changed_modules.add(module_path.stem)

    if verbose:
        print(f"Checking for imports of: {', '.join(changed_modules)}")

    # Search test files for imports or references
    for test_file in test_path.rglob("test_*.py"):
        try:
            content = test_file.read_text()
            # Check if any changed module is referenced in the test file
            for module in changed_modules:
                if module in content:
                    affected_tests.add(str(test_file))
                    if verbose:
                        print(f"  {test_file.name} references {module}")
                    break
        except Exception as e:
            if verbose:
                print(f"Warning: Could not read {test_file}: {e}", file=sys.stderr)

    return affected_tests


def get_critical_path_tests(test_dir: str = "tests/lite", verbose: bool = False) -> Set[str]:
    """Get tests marked as critical path (always run these)."""
    critical_tests = set()
    test_path = Path(test_dir)

    if not test_path.exists():
        return critical_tests

    # Find tests with @pytest.mark.critical_path or @pytest.mark.critical
    for test_file in test_path.rglob("test_*.py"):
        try:
            content = test_file.read_text()
            if "@pytest.mark.critical" in content or "@pytest.mark.critical_path" in content:
                critical_tests.add(str(test_file))
                if verbose:
                    print(f"  Critical: {test_file.name}")
        except Exception as e:
            if verbose:
                print(f"Warning: Could not read {test_file}: {e}", file=sys.stderr)

    return critical_tests


def main():
    """Main entry point for smart test selector."""
    parser = argparse.ArgumentParser(
        description="Smart test selector based on code changes and coverage data"
    )
    parser.add_argument(
        "--base-branch",
        default="origin/main",
        help="Branch to compare against (default: origin/main)",
    )
    parser.add_argument(
        "--output",
        default=".pytest-selected-tests.txt",
        help="Output file for selected tests",
    )
    parser.add_argument(
        "--coverage-file",
        default=".coverage",
        help="Coverage data file (default: .coverage)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--fallback-threshold",
        type=float,
        default=30.0,
        help="If >N%% of files changed, run full suite (default: 30)",
    )
    parser.add_argument(
        "--test-dir",
        default="tests/lite",
        help="Test directory to search (default: tests/lite)",
    )
    parser.add_argument(
        "--source-dir",
        default="calendarbot_lite",
        help="Source directory to analyze (default: calendarbot_lite)",
    )

    args = parser.parse_args()

    # Get changed files
    changed_files = get_changed_files(args.base_branch, args.verbose)

    if not changed_files:
        print("No Python files changed - recommend running critical path tests only")
        # Get critical tests
        critical_tests = get_critical_path_tests(args.test_dir, args.verbose)
        output_path = Path(args.output)

        if critical_tests:
            output_path.write_text("\n".join(sorted(critical_tests)))
            print(f"Selected {len(critical_tests)} critical path tests")
        else:
            # Write marker indicating no additional tests needed (critical path already ran)
            output_path.write_text("# NO_TESTS_NEEDED\n")
            print("No critical path tests found - writing NO_TESTS_NEEDED marker")

        print(f"Output written to: {args.output}")
        return 0

    # Check if too many files changed (fallback to full suite)
    total_files = get_total_python_files(args.source_dir)
    if total_files > 0:
        change_percentage = (len(changed_files) / total_files) * 100
        if change_percentage > args.fallback_threshold:
            print(
                f"Large change detected: {len(changed_files)}/{total_files} files "
                f"({change_percentage:.1f}%) - recommend running full test suite"
            )
            # Create empty output file to signal full suite
            Path(args.output).write_text("")
            return 0

    # Find affected tests using multiple strategies
    affected_tests = set()

    # Strategy 1: Coverage-based (most accurate)
    coverage_tests = find_affected_tests_from_coverage(
        changed_files,
        args.coverage_file,
        args.verbose,
    )
    affected_tests.update(coverage_tests)

    # Strategy 2: Import-based (heuristic fallback)
    import_tests = find_affected_tests_from_imports(
        changed_files,
        args.test_dir,
        args.verbose,
    )
    affected_tests.update(import_tests)

    # Strategy 3: Kiosk file mapping (check if any kiosk/ files changed)
    kiosk_files_changed = any(f.startswith('kiosk/') for f in changed_files)
    kiosk_tests = set()
    if kiosk_files_changed:
        # If kiosk files changed, include kiosk unit tests (not slow E2E tests)
        kiosk_test_dir = Path("tests/kiosk")
        if kiosk_test_dir.exists():
            # Include only non-E2E kiosk tests (E2E tests run nightly)
            for test_file in kiosk_test_dir.glob("test_*.py"):
                # Skip E2E tests (they run nightly due to ~10min duration)
                if "test_installer.py" not in str(test_file):
                    kiosk_tests.add(str(test_file))

            if args.verbose:
                print(f"Kiosk files changed - including {len(kiosk_tests)} kiosk unit tests (E2E tests run nightly)")

        affected_tests.update(kiosk_tests)

    # Always include critical path tests
    critical_tests = get_critical_path_tests(args.test_dir, args.verbose)
    affected_tests.update(critical_tests)

    if not affected_tests:
        print("No affected tests found - recommend running full test suite")
        Path(args.output).write_text("")
        return 0

    # Write output
    output_path = Path(args.output)
    output_path.write_text("\n".join(sorted(affected_tests)))

    # Summary
    print(f"\n{'='*60}")
    print(f"Changed files: {len(changed_files)}")
    print(f"Affected tests: {len(affected_tests)}")
    print(f"  - From coverage: {len(coverage_tests)}")
    print(f"  - From imports: {len(import_tests)}")
    print(f"  - From kiosk changes: {len(kiosk_tests)}")
    print(f"  - Critical path: {len(critical_tests)}")
    print(f"{'='*60}")
    print(f"\nOutput written to: {args.output}")
    print("\nTo run selected tests:")
    print(f"  pytest $(cat {args.output})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
