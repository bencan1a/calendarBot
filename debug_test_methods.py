#!/usr/bin/env python3
"""
Debug script to check which SourceManager methods exist vs what test_ics.py expects
"""

import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import inspect

from calendarbot.sources import SourceManager
from config.settings import settings


def check_source_manager_methods():
    """Check what methods exist on SourceManager"""
    print("=== SourceManager Method Analysis ===\n")

    # Get all methods on SourceManager
    methods = inspect.getmembers(SourceManager, predicate=inspect.ismethod)
    functions = inspect.getmembers(SourceManager, predicate=inspect.isfunction)
    all_methods = dict(methods + functions)

    print("Available SourceManager methods:")
    for name, method in sorted(all_methods.items()):
        if not name.startswith("_"):
            sig = inspect.signature(method)
            print(f"  - {name}{sig}")

    print("\n=== Test Script Expected Methods ===\n")

    expected_calls = [
        ("get_source_info", "await source_manager.get_source_info()"),
        ("health_check", "await source_manager.health_check()"),
        ("fetch_events_for_date", "await source_manager.fetch_events_for_date(date)"),
        ("fetch_events_for_range", "await source_manager.fetch_events_for_range(start, end)"),
        ("get_metrics", "await source_manager.get_metrics()"),
    ]

    for method_name, call_example in expected_calls:
        if method_name in all_methods:
            sig = inspect.signature(all_methods[method_name])
            print(f"✅ {method_name} EXISTS - {method_name}{sig}")
            print(f"   Test calls: {call_example}")
        else:
            print(f"❌ {method_name} MISSING")
            print(f"   Test calls: {call_example}")
        print()


if __name__ == "__main__":
    check_source_manager_methods()
