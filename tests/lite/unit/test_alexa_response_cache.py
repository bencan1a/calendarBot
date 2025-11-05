"""Tests for Alexa response cache."""

import pytest

from calendarbot_lite.alexa.alexa_response_cache import ResponseCache

pytestmark = pytest.mark.unit


def test_response_cache_basic():
    """Test basic cache operations."""
    cache = ResponseCache(max_size=10)

    # Generate cache key
    key = cache.generate_key("TestHandler", {"tz": "UTC"})
    assert key.startswith("TestHandler:0:")

    # Cache should be empty initially
    assert cache.get(key) is None
    assert cache.get_stats()["misses"] == 1

    # Set a response
    response = {"test": "data"}
    cache.set(key, response)

    # Should get the cached response back
    cached = cache.get(key)
    assert cached == response
    assert cache.get_stats()["hits"] == 1

    # Stats should show 1 hit and 1 miss
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 50.0


def test_response_cache_invalidation():
    """Test cache invalidation."""
    cache = ResponseCache()

    # Add some entries
    key1 = cache.generate_key("Handler1", {"tz": "UTC"})
    key2 = cache.generate_key("Handler2", {"tz": "America/Los_Angeles"})

    cache.set(key1, {"data": "1"})
    cache.set(key2, {"data": "2"})

    # Both should be cached
    assert cache.get(key1) == {"data": "1"}
    assert cache.get(key2) == {"data": "2"}

    # Invalidate all
    cache.invalidate_all()

    # Both should be invalidated
    assert cache.get(key1) is None
    assert cache.get(key2) is None

    # Stats should show invalidation
    stats = cache.get_stats()
    assert stats["invalidations"] == 1
    assert stats["current_size"] == 0
    assert stats["window_version"] == 1


def test_response_cache_fifo_eviction():
    """Test FIFO eviction when cache is full."""
    cache = ResponseCache(max_size=3)

    # Add 3 entries
    for i in range(3):
        key = cache.generate_key(f"Handler{i}", {"id": i})
        cache.set(key, {"data": i})

    assert cache.get_stats()["current_size"] == 3
    assert cache.get_stats()["evictions"] == 0

    # Add a 4th entry - should evict oldest
    key = cache.generate_key("Handler3", {"id": 3})
    cache.set(key, {"data": 3})

    assert cache.get_stats()["current_size"] == 3
    assert cache.get_stats()["evictions"] == 1


def test_response_cache_different_params():
    """Test that different parameters generate different keys."""
    cache = ResponseCache()

    key1 = cache.generate_key("Handler", {"tz": "UTC"})
    key2 = cache.generate_key("Handler", {"tz": "America/Los_Angeles"})
    key3 = cache.generate_key("Handler", {"tz": "UTC", "extra": "param"})

    # All keys should be different
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3


def test_response_cache_window_version():
    """Test that window version invalidates old entries."""
    cache = ResponseCache()

    key = cache.generate_key("Handler", {"tz": "UTC"})
    cache.set(key, {"data": "original"})

    # Should get cached response
    assert cache.get(key) == {"data": "original"}

    # Invalidate (simulates window refresh)
    cache.invalidate_all()

    # Old key should not work (different window version)
    assert cache.get(key) is None

    # New key after invalidation should work
    new_key = cache.generate_key("Handler", {"tz": "UTC"})
    cache.set(new_key, {"data": "new"})
    assert cache.get(new_key) == {"data": "new"}

    # Keys should be different (different window version)
    assert key != new_key
