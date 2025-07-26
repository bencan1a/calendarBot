#!/usr/bin/env python3
"""
Debug script to validate pytest failure assumptions.

Root Cause Analysis:
1. Missing functions in interactive.py module
2. Timezone pytz import path issues
3. Display manager mock behavior inconsistency
4. Renderer factory test expectations outdated
5. Module export misalignment

This script validates each assumption with logging.
"""

import logging
import sys
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def validate_interactive_module() -> Dict[str, Any]:
    """Validate missing functions in interactive module."""
    logger.info("🔍 VALIDATING: Interactive module missing functions")

    try:
        from calendarbot.cli.modes import interactive

        # Check what functions actually exist
        actual_exports = getattr(interactive, "__all__", [])
        actual_functions = [
            name
            for name in dir(interactive)
            if callable(getattr(interactive, name)) and not name.startswith("_")
        ]

        # Expected by tests
        expected_exports = [
            "run_interactive_mode",
            "setup_interactive_logging",
            "create_interactive_controller",
        ]

        missing_functions = [func for func in expected_exports if not hasattr(interactive, func)]

        result = {
            "status": "CONFIRMED" if missing_functions else "NOT_FOUND",
            "actual_exports": actual_exports,
            "actual_functions": actual_functions,
            "expected_exports": expected_exports,
            "missing_functions": missing_functions,
        }

        if missing_functions:
            logger.error(f"✗ CONFIRMED: Missing functions: {missing_functions}")
        else:
            logger.info("✓ All expected functions exist")

        return result

    except Exception as e:
        logger.error(f"✗ ERROR validating interactive module: {e}")
        return {"status": "ERROR", "error": str(e)}


def validate_pytz_import_issue() -> Dict[str, Any]:
    """Validate pytz import path issues in helpers."""
    logger.info("🔍 VALIDATING: Pytz import path issue")

    try:
        import calendarbot.utils.helpers as helpers

        # Check if pytz is available as module attribute
        has_pytz_attr = hasattr(helpers, "pytz")

        # Check if pytz is imported in module
        import inspect

        source = inspect.getsource(helpers)
        has_pytz_import = "import pytz" in source

        # Check actual import locations in source
        pytz_lines = [line.strip() for line in source.split("\n") if "pytz" in line]

        result = {
            "status": "CONFIRMED" if not has_pytz_attr else "NOT_FOUND",
            "has_pytz_attr": has_pytz_attr,
            "has_pytz_import": has_pytz_import,
            "pytz_lines": pytz_lines,
        }

        if not has_pytz_attr:
            logger.error("✗ CONFIRMED: pytz not available as module attribute for patching")
        else:
            logger.info("✓ pytz available as module attribute")

        return result

    except Exception as e:
        logger.error(f"✗ ERROR validating pytz import: {e}")
        return {"status": "ERROR", "error": str(e)}


def validate_renderer_factory_expectations() -> Dict[str, Any]:
    """Validate renderer factory test expectations."""
    logger.info("🔍 VALIDATING: Renderer factory expectations")

    try:
        from calendarbot.display.renderer_factory import RendererFactory

        actual_renderers = RendererFactory.get_available_renderers()
        expected_by_test = ["html", "rpi", "compact", "console", "whats-next"]

        result = {
            "status": "CONFIRMED" if actual_renderers != expected_by_test else "NOT_FOUND",
            "actual_renderers": actual_renderers,
            "expected_by_test": expected_by_test,
            "extra_renderers": [r for r in actual_renderers if r not in expected_by_test],
            "missing_renderers": [r for r in expected_by_test if r not in actual_renderers],
        }

        if actual_renderers != expected_by_test:
            logger.error(
                f"✗ CONFIRMED: Renderer mismatch. Actual: {actual_renderers}, Expected: {expected_by_test}"
            )
        else:
            logger.info("✓ Renderer expectations match")

        return result

    except Exception as e:
        logger.error(f"✗ ERROR validating renderer factory: {e}")
        return {"status": "ERROR", "error": str(e)}


def validate_display_manager_mock_setup() -> Dict[str, Any]:
    """Validate display manager mock behavior."""
    logger.info("🔍 VALIDATING: Display manager mock behavior")

    try:
        # Look at the failing test to understand the issue
        test_file_path = "tests/unit/test_display_manager.py"

        with open(test_file_path, "r") as f:
            content = f.read()

        # Look for the failing test
        failing_test_line = None
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "test_display_error_success" in line:
                failing_test_line = i
                break

        test_details = []
        if failing_test_line:
            # Get context around the failing test
            start = max(0, failing_test_line - 5)
            end = min(len(lines), failing_test_line + 20)
            test_details = lines[start:end]

        result = {
            "status": "ANALYSIS",
            "failing_test_line": failing_test_line,
            "test_context": test_details,
            "issue": "Mock display_with_clear not being called as expected",
        }

        logger.info("✓ Display manager test analysis completed")
        return result

    except Exception as e:
        logger.error(f"✗ ERROR validating display manager: {e}")
        return {"status": "ERROR", "error": str(e)}


def main() -> None:
    """Run all validation checks."""
    logger.info("🚀 Starting pytest failure validation...")

    results: Dict[str, Any] = {}

    # Run all validations
    results["interactive_module"] = validate_interactive_module()
    results["pytz_import"] = validate_pytz_import_issue()
    results["renderer_factory"] = validate_renderer_factory_expectations()
    results["display_manager"] = validate_display_manager_mock_setup()

    # Summary
    logger.info("\n📋 VALIDATION SUMMARY:")
    confirmed_issues = 0

    for check_name, result in results.items():
        status = result.get("status", "UNKNOWN")
        if status == "CONFIRMED":
            confirmed_issues += 1
            logger.error(f"  ✗ {check_name.replace('_', ' ').title()}: ISSUE CONFIRMED")
        elif status == "ERROR":
            logger.error(f"  ⚠ {check_name.replace('_', ' ').title()}: VALIDATION ERROR")
        else:
            logger.info(f"  ✓ {check_name.replace('_', ' ').title()}: OK or needs further analysis")

    logger.info(f"\n🎯 DIAGNOSIS CONFIDENCE: {confirmed_issues}/4 issues confirmed")

    if confirmed_issues >= 2:
        logger.info("✅ High confidence in diagnosis - ready to proceed with fixes")
    else:
        logger.warning("⚠ Low confidence - may need additional investigation")


if __name__ == "__main__":
    main()
