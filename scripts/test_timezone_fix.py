#!/usr/bin/env python3
"""Test script to verify timezone fix is working correctly."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calendarbot.utils.helpers import get_timezone_aware_now
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def test_timezone_fix():
    """Test that timezone fix returns PST time instead of UTC."""
    print("Testing timezone fix...")

    # Test 1: No timezone specified (should default to PST)
    print("\n1. Testing default timezone (should be PST):")
    pst_time = get_timezone_aware_now()
    print(f"   Result: {pst_time.isoformat()}")
    print(f"   Timezone: {pst_time.tzinfo}")

    # Test 2: Explicit PST timezone
    print("\n2. Testing explicit America/Los_Angeles timezone:")
    explicit_pst_time = get_timezone_aware_now("America/Los_Angeles")
    print(f"   Result: {explicit_pst_time.isoformat()}")
    print(f"   Timezone: {explicit_pst_time.tzinfo}")

    # Test 3: Compare with UTC
    print("\n3. Comparison with UTC:")
    import pytz
    from datetime import datetime

    utc_time = datetime.now(pytz.utc)
    print(f"   UTC time: {utc_time.isoformat()}")
    print(f"   PST time: {pst_time.isoformat()}")

    # Calculate offset
    offset_hours = (pst_time.utcoffset().total_seconds() / 3600) if pst_time.utcoffset() else 0
    print(f"   Offset from UTC: {offset_hours} hours")

    # Verify it's actually PST/PDT
    if abs(offset_hours + 8) < 1 or abs(offset_hours + 7) < 1:  # PST is UTC-8, PDT is UTC-7
        print("   ✅ PASS: Time is in PST/PDT timezone")
        return True
    else:
        print("   ❌ FAIL: Time is not in PST/PDT timezone")
        return False


if __name__ == "__main__":
    success = test_timezone_fix()
    exit(0 if success else 1)
