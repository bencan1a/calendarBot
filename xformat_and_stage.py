#!/usr/bin/env python3
"""
Integrated format-and-stage script that handles multiple iterations.

This script replaces the need for separate formatting and auto-staging hooks
by performing the complete cycle in iterations until stable.
"""

import hashlib
import subprocess  # nosec
import sys
from pathlib import Path
from typing import Optional


def get_staged_files() -> list[str]:
    """Get list of staged Python files from calendarbot_lite/ directory only."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [
            f
            for f in result.stdout.strip().split("\n")
            if f.endswith(".py") and f.startswith("calendarbot_lite/") and f
        ]
    except subprocess.CalledProcessError:
        return []


def get_file_hash(filepath: str) -> Optional[str]:
    """Get hash of file content for change detection."""
    try:
        with Path(filepath).open("rb") as f:
            return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
    except (FileNotFoundError, PermissionError):
        return None


def run_formatter(command: list[str], files: list[str]) -> bool:
    """Run a formatter command on files and return True if any files were modified."""
    if not files:
        return False

    # Get file hashes before formatting
    before_hashes = {f: get_file_hash(f) for f in files}
    print(f"    Before hashes: {before_hashes}")

    try:
        # Run the formatter
        cmd = command + files
        print(f"    Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        print(f"    Command result: return_code={result.returncode}")
        if result.stdout:
            print(f"    stdout: {result.stdout}")
        if result.stderr:
            print(f"    stderr: {result.stderr}")

        # Check if any files were actually modified
        after_hashes = {f: get_file_hash(f) for f in files}
        print(f"    After hashes: {after_hashes}")

        modified_files = [f for f in files if before_hashes.get(f) != after_hashes.get(f)]
        modified = len(modified_files) > 0

        if modified:
            print(f"✓ {' '.join(command[:2])} modified files: {modified_files}")
        else:
            print(f"  {' '.join(command[:2])} made no changes")

        return modified

    except subprocess.CalledProcessError as e:
        print(f"✗ Formatter failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return False


def get_staged_vs_working_differences(files: list[str]) -> list[str]:
    """Get list of files that differ between staging area and working directory."""
    different_files = []

    for filepath in files:
        try:
            # Check if file differs between staging area and working directory
            subprocess.run(
                ["git", "diff", "--name-only", "--cached", filepath],
                capture_output=True,
                text=True,
                check=True,
            )

            # If git diff --cached returns the filename, it means the staged version
            # differs from HEAD, but we need to check if working dir differs from staged
            result2 = subprocess.run(
                ["git", "diff", "--name-only", filepath],
                capture_output=True,
                text=True,
                check=True,
            )

            # If the file appears in git diff (working vs staging), it needs re-staging
            if result2.stdout.strip():
                different_files.append(filepath)
                print(
                    f"    Found difference in {filepath}: working directory differs from staging area"
                )

        except subprocess.CalledProcessError:  # noqa: PERF203
            # If git diff fails, assume the file needs staging
            different_files.append(filepath)

    return different_files


def stage_files(files: list[str]) -> bool:
    """Stage the specified files."""
    if not files:
        return True

    try:
        subprocess.run(["git", "add", *files], check=True, capture_output=True)
        print(f"✓ Re-staged {len(files)} files: {files}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to stage files: {e}")
        return False


def main() -> int:
    """Main execution function."""
    print("🔄 Starting integrated format-and-stage process...")

    # Get initially staged files
    staged_files = get_staged_files()
    if not staged_files:
        print("No Python files staged for commit.")
        return 0

    print(f"📁 Found {len(staged_files)} staged Python files: {staged_files}")

    # Define formatters to run
    formatters = [
        ["python", "-m", "ruff", "format", "--quiet"],
        ["python", "-m", "ruff", "check", "--fix", "--quiet"],
    ]

    max_iterations = 5  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Iteration {iteration}:")

        any_changes = False

        # Run each formatter
        for formatter_cmd in formatters:
            formatter_name = formatter_cmd[2]  # format or check
            print(f"  Running {formatter_name}...")

            if run_formatter(formatter_cmd, staged_files):
                any_changes = True
                # Re-stage the modified files
                if not stage_files(staged_files):
                    print(f"✗ Failed to re-stage files after {formatter_name}")
                    return 1

        # If no formatting changes were made, check for staging differences
        if not any_changes:
            print(f"  No formatting changes in iteration {iteration}")
            print("  Checking for staging differences...")

            # Check if any staged files differ from working directory
            different_files = get_staged_vs_working_differences(staged_files)

            if different_files:
                print(f"  Found {len(different_files)} files that need re-staging")
                if not stage_files(different_files):
                    print("✗ Failed to re-stage different files")
                    return 1
                any_changes = True  # Continue to next iteration to verify
            else:
                print(f"✅ Converged after {iteration} iteration(s) - no more changes needed")
                break
    else:
        print(f"⚠️  Reached maximum iterations ({max_iterations}) - stopping")
        return 1

    print("🎉 Format-and-stage process completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
