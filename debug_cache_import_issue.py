#!/usr/bin/env python3
"""Diagnostic script to identify cache manager import issues."""

import sys
import traceback


def test_cache_imports():
    """Test each level of cache imports to identify the exact failure point."""

    print("🔍 Testing Cache Manager Import Chain...")
    print("=" * 60)

    # Test 1: Base cache package
    try:
        print("1. Testing: import calendarbot.cache")
        import calendarbot.cache

        print("   ✅ SUCCESS: calendarbot.cache imported")
    except Exception as e:
        print(f"   ❌ FAILED: calendarbot.cache - {e}")
        traceback.print_exc()
        return False

    # Test 2: Cache manager direct import
    try:
        print("\n2. Testing: from calendarbot.cache import CacheManager")
        from calendarbot.cache import CacheManager

        print("   ✅ SUCCESS: CacheManager imported")
    except Exception as e:
        print(f"   ❌ FAILED: CacheManager import - {e}")
        traceback.print_exc()
        return False

    # Test 3: Cache models import
    try:
        print("\n3. Testing: from calendarbot.cache import CachedEvent")
        from calendarbot.cache import CachedEvent

        print("   ✅ SUCCESS: CachedEvent imported")
    except Exception as e:
        print(f"   ❌ FAILED: CachedEvent import - {e}")
        traceback.print_exc()
        return False

    # Test 4: Direct manager module import
    try:
        print("\n4. Testing: from calendarbot.cache.manager import CacheManager")
        from calendarbot.cache.manager import CacheManager

        print("   ✅ SUCCESS: Direct CacheManager import")
    except Exception as e:
        print(f"   ❌ FAILED: Direct CacheManager import - {e}")
        traceback.print_exc()
        return False

    # Test 5: Direct models import
    try:
        print("\n5. Testing: from calendarbot.cache.models import CachedEvent")
        from calendarbot.cache.models import CachedEvent

        print("   ✅ SUCCESS: Direct CachedEvent import")
    except Exception as e:
        print(f"   ❌ FAILED: Direct CachedEvent import - {e}")
        traceback.print_exc()
        return False

    print("\n✅ ALL CACHE IMPORTS SUCCESSFUL!")
    return True


def test_dependency_imports():
    """Test the dependencies that cache manager relies on."""

    print("\n🔧 Testing Cache Manager Dependencies...")
    print("=" * 60)

    dependencies = [
        ("calendarbot.monitoring", ["cache_monitor", "memory_monitor", "performance_monitor"]),
        ("calendarbot.security", ["SecurityEventLogger"]),
        ("calendarbot.structured", ["operation_context", "with_correlation_id"]),
    ]

    for module_name, items in dependencies:
        try:
            print(f"\nTesting: {module_name}")
            module = __import__(module_name, fromlist=items)

            for item in items:
                if hasattr(module, item):
                    print(f"   ✅ {item} available")
                else:
                    print(f"   ❌ {item} MISSING")

        except Exception as e:
            print(f"   ❌ FAILED to import {module_name}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    print("🪲 Cache Manager Import Diagnostic")
    print("=" * 60)

    # Test individual dependencies first
    test_dependency_imports()

    # Then test cache imports
    success = test_cache_imports()

    if success:
        print("\n🎉 Cache imports are working correctly!")
        print("The issue may be in test setup or fixture configuration.")
    else:
        print("\n💥 Cache import chain broken - dependencies missing!")

    sys.exit(0 if success else 1)
