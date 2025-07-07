#!/usr/bin/env python3
"""
Coverage badge generation script for CalendarBot.

This script generates coverage badges for use in README files
and CI/CD pipelines based on coverage reports.
"""

import argparse
import json
import subprocess  # nosec B404 - validated subprocess usage with input sanitization
import sys
from pathlib import Path

try:
    import defusedxml.ElementTree as ET
except ImportError:
    # Fallback to standard library with warning
    import warnings
    import xml.etree.ElementTree as ET  # nosec B405 - fallback with explicit warning when defusedxml unavailable

    warnings.warn(
        "defusedxml not available. Using xml.etree.ElementTree which may be vulnerable to XML attacks. "
        "Install defusedxml for secure XML parsing.",
        UserWarning,
    )


def get_coverage_from_json(coverage_file: str = "coverage.json") -> float:
    """Extract coverage percentage from JSON report."""
    try:
        with open(coverage_file, "r") as f:
            data = json.load(f)
        return data["totals"]["percent_covered"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return 0.0


def get_coverage_from_xml(coverage_file: str = "coverage.xml") -> float:
    """Extract coverage percentage from XML report."""
    try:
        tree = ET.parse(
            coverage_file
        )  # nosec B314 - parsing local coverage files, not untrusted XML
        root = tree.getroot()

        # Find coverage element with line-rate attribute
        coverage_elem = root.find(".//coverage")
        if coverage_elem is not None:
            line_rate = float(coverage_elem.get("line-rate", 0))
            return line_rate * 100

        return 0.0
    except (FileNotFoundError, ET.ParseError, ValueError):
        return 0.0


def get_coverage_color(coverage: float) -> str:
    """Get badge color based on coverage percentage."""
    if coverage >= 90:
        return "brightgreen"
    elif coverage >= 80:
        return "green"
    elif coverage >= 70:
        return "yellowgreen"
    elif coverage >= 60:
        return "yellow"
    elif coverage >= 50:
        return "orange"
    else:
        return "red"


def _validate_url(url: str) -> bool:
    """Validate URL for security (only allow HTTPS schemes)."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    # Only allow HTTPS for external requests
    if parsed.scheme not in ["https"]:
        return False
    # Only allow shields.io domain for badge generation
    if not parsed.netloc.endswith("shields.io"):
        return False
    return True


def generate_shields_badge(coverage: float, output_file: str = "coverage-badge.svg") -> bool:
    """Generate coverage badge using shields.io API."""
    color = get_coverage_color(coverage)
    coverage_str = f"{coverage:.1f}%"

    url = f"https://img.shields.io/badge/coverage-{coverage_str}-{color}.svg"

    # Validate URL for security
    if not _validate_url(url):
        print(f"Error: Invalid or unsafe URL: {url}")
        return False

    try:
        import urllib.request

        urllib.request.urlretrieve(
            url, output_file
        )  # nosec B310 - URL validated for HTTPS and shields.io domain
        return True
    except Exception as e:
        print(f"Error generating badge: {e}")
        return False


def _validate_subprocess_args(cmd: list) -> bool:
    """Validate subprocess arguments for security."""
    if not cmd or len(cmd) == 0:
        return False

    # Ensure first argument is sys.executable (Python interpreter)
    if cmd[0] != sys.executable:
        return False

    # Ensure we're only running known safe modules
    if len(cmd) < 3 or cmd[1] != "-m":
        return False

    # Only allow genbadge module
    if cmd[2] != "genbadge":
        return False

    # Validate file paths don't contain dangerous characters
    for arg in cmd:
        if any(char in str(arg) for char in ["|", "&", ";", "`", "$"]):
            return False

    return True


def generate_genbadge_badge(coverage: float, output_dir: str = ".") -> bool:
    """Generate coverage badge using genbadge."""
    try:
        # Validate coverage value
        if not (0 <= coverage <= 100):
            print(f"Error: Invalid coverage value: {coverage}")
            return False

        # Create a temporary coverage file for genbadge
        temp_coverage = Path(output_dir) / "temp_coverage.xml"

        # Generate XML format for genbadge
        xml_content = f"""<?xml version="1.0" ?>
<coverage version="7.3.2" timestamp="{int(__import__('time').time())}" lines-valid="100" lines-covered="{int(coverage)}" line-rate="{coverage/100:.4f}" branches-valid="0" branches-covered="0" branch-rate="0" complexity="0">
    <sources>
        <source>.</source>
    </sources>
    <packages>
        <package name="." line-rate="{coverage/100:.4f}" branch-rate="0" complexity="0">
            <classes/>
        </package>
    </packages>
</coverage>"""

        with open(temp_coverage, "w") as f:
            f.write(xml_content)

        # Run genbadge with validated arguments
        cmd = [
            sys.executable,
            "-m",
            "genbadge",
            "coverage",
            "-i",
            str(temp_coverage),
            "-o",
            f"{output_dir}/coverage-badge.svg",
        ]

        # Validate subprocess arguments before execution
        if not _validate_subprocess_args(cmd):
            print("Error: Invalid subprocess arguments detected")
            temp_coverage.unlink(missing_ok=True)
            return False

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )  # nosec B603 - arguments validated with _validate_subprocess_args

        # Clean up temp file
        temp_coverage.unlink(missing_ok=True)

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Error: genbadge execution timed out")
        return False
    except Exception as e:
        print(f"Error generating genbadge: {e}")
        return False


def generate_markdown_badge(coverage: float) -> str:
    """Generate markdown badge link."""
    color = get_coverage_color(coverage)
    coverage_str = f"{coverage:.1f}%"

    badge_url = f"https://img.shields.io/badge/coverage-{coverage_str}-{color}.svg"
    return f"![Coverage]({badge_url})"


def generate_html_badge(coverage: float) -> str:
    """Generate HTML badge."""
    color = get_coverage_color(coverage)
    coverage_str = f"{coverage:.1f}%"

    badge_url = f"https://img.shields.io/badge/coverage-{coverage_str}-{color}.svg"
    return f'<img src="{badge_url}" alt="Coverage {coverage_str}" />'


def main():
    """Main entry point for badge generation."""
    parser = argparse.ArgumentParser(
        description="Generate coverage badges for CalendarBot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_coverage_badge.py                    # Generate from coverage.json
  python generate_coverage_badge.py --xml              # Generate from coverage.xml
  python generate_coverage_badge.py --output badges/   # Output to badges directory
  python generate_coverage_badge.py --format markdown  # Generate markdown link
  python generate_coverage_badge.py --format html      # Generate HTML tag
        """,
    )

    parser.add_argument("--input", "-i", help="Input coverage file")
    parser.add_argument("--xml", action="store_true", help="Use XML coverage file")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument(
        "--format", choices=["svg", "markdown", "html"], default="svg", help="Output format"
    )
    parser.add_argument(
        "--method",
        choices=["shields", "genbadge"],
        default="shields",
        help="Badge generation method",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Determine input file
    if args.input:
        input_file = args.input
    elif args.xml:
        input_file = "coverage.xml"
    else:
        input_file = "coverage.json"

    if args.verbose:
        print(f"Reading coverage from: {input_file}")

    # Extract coverage percentage
    if input_file.endswith(".xml"):
        coverage = get_coverage_from_xml(input_file)
    else:
        coverage = get_coverage_from_json(input_file)

    if coverage == 0.0:
        print(f"Error: Could not read coverage from {input_file}")
        return 1

    if args.verbose:
        print(f"Coverage: {coverage:.1f}%")
        print(f"Color: {get_coverage_color(coverage)}")

    # Generate badge based on format
    if args.format == "svg":
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)

        if args.method == "genbadge":
            success = generate_genbadge_badge(coverage, str(output_path))
        else:
            badge_file = output_path / "coverage-badge.svg"
            success = generate_shields_badge(coverage, str(badge_file))

        if success:
            print(f"✅ Badge generated successfully in {args.output}")
        else:
            print("❌ Failed to generate badge")
            return 1

    elif args.format == "markdown":
        markdown = generate_markdown_badge(coverage)
        print(markdown)

    elif args.format == "html":
        html = generate_html_badge(coverage)
        print(html)

    return 0


if __name__ == "__main__":
    sys.exit(main())
