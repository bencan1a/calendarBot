#!/usr/bin/env python3
"""Test if .isoformat() preserves timezone information correctly."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calendarbot.utils.helpers import get_timezone_aware_now


def test_isoformat_timezone():
    """Test if .isoformat() preserves timezone correctly."""
    print("Testing .isoformat() timezone preservation...")

    # Get PST time
    pst_time = get_timezone_aware_now()
    print(f"PST datetime object: {pst_time}")
    print(f"PST timezone: {pst_time.tzinfo}")

    # Convert to ISO format (what HTML renderer does)
    iso_format = pst_time.isoformat()
    print(f"ISO format result: {iso_format}")

    # Check if timezone info is preserved
    if iso_format.endswith("-07:00") or iso_format.endswith("-08:00"):
        print("✅ PASS: .isoformat() preserves PST timezone")
        return True
    elif iso_format.endswith("Z") or iso_format.endswith("+00:00"):
        print("❌ FAIL: .isoformat() converted to UTC")
        return False
    else:
        print(f"❓ UNKNOWN: Unexpected timezone format: {iso_format}")
        return False


if __name__ == "__main__":
    success = test_isoformat_timezone()
    exit(0 if success else 1)
