"""Tests for rate limiting functionality.

This module tests the RateLimiter class and rate limiting middleware
to ensure proper protection against DoS attacks.
"""

import asyncio
import time

import pytest

from calendarbot_lite.api.middleware.rate_limiter import (
    RateLimitConfig,
    RateLimiter,
    get_bearer_token,
    get_client_ip,
)


class TestRateLimiter:
    """Test cases for RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a RateLimiter instance for testing."""
        config = RateLimitConfig(
            per_ip_limit=10,
            per_token_limit=20,
            burst_limit=5,
            burst_window_seconds=10,
        )
        return RateLimiter(config)

    async def test_allows_requests_under_limit(self, rate_limiter):
        """Test that requests under the limit are allowed."""
        await rate_limiter.start()
        try:
            # Make 3 requests (under limit of 10)
            for i in range(3):
                allowed, info = await rate_limiter.check_rate_limit("192.168.1.1")
                assert allowed, f"Request {i+1} should be allowed"
                assert info["remaining_ip"] >= 0
        finally:
            await rate_limiter.stop()

    async def test_rejects_requests_over_limit(self, rate_limiter):
        """Test that requests over the limit are rejected."""
        await rate_limiter.start()
        try:
            # Make 11 requests (limit is 10, but burst limit is 5)
            # So we expect 5 to be allowed (burst limit) and 6 to be rejected
            allowed_count = 0
            rejected_count = 0

            for i in range(11):
                allowed, info = await rate_limiter.check_rate_limit("192.168.1.1")
                if allowed:
                    allowed_count += 1
                else:
                    rejected_count += 1
                    assert info["retry_after"] > 0

            # Burst limit should kick in first (5 requests)
            assert allowed_count == 5, f"Should allow exactly 5 requests (burst limit), got {allowed_count}"
            assert rejected_count == 6, f"Should reject 6 requests, got {rejected_count}"
        finally:
            await rate_limiter.stop()

    async def test_burst_limit_protection(self, rate_limiter):
        """Test that burst limit prevents rapid fire requests."""
        await rate_limiter.start()
        try:
            # Make 6 rapid requests (burst limit is 5)
            allowed_count = 0
            rejected_count = 0

            for i in range(6):
                allowed, info = await rate_limiter.check_rate_limit("192.168.1.1")
                if allowed:
                    allowed_count += 1
                else:
                    rejected_count += 1

            assert rejected_count >= 1, "Should reject at least 1 burst request"
        finally:
            await rate_limiter.stop()

    async def test_separate_ip_tracking(self, rate_limiter):
        """Test that different IPs are tracked separately."""
        await rate_limiter.start()
        try:
            # Make 5 requests from IP 1
            for _ in range(5):
                allowed, _ = await rate_limiter.check_rate_limit("192.168.1.1")
                assert allowed

            # Make 5 requests from IP 2 (should also be allowed)
            for _ in range(5):
                allowed, _ = await rate_limiter.check_rate_limit("192.168.1.2")
                assert allowed
        finally:
            await rate_limiter.stop()

    async def test_token_based_rate_limiting(self, rate_limiter):
        """Test token-based rate limiting."""
        await rate_limiter.start()
        try:
            token = "test-token-123"

            # Note: burst limit is 5, so we'll hit that before token limit
            # Make 5 requests (will hit burst limit)
            for i in range(5):
                allowed, info = await rate_limiter.check_rate_limit("192.168.1.1", token)
                assert allowed, f"Request {i+1} should be allowed"

            # 6th request should be rejected (burst limit exceeded)
            allowed, info = await rate_limiter.check_rate_limit("192.168.1.1", token)
            assert not allowed, "Request 6 should be rejected due to burst limit"
            assert info["retry_after"] > 0

            # Check that token info is still tracked
            assert info["remaining_token"] is not None
        finally:
            await rate_limiter.stop()

    async def test_sliding_window_behavior(self, rate_limiter):
        """Test that sliding window allows requests as old ones expire."""
        # Use a config with very short windows for testing
        # Note: This test focuses on burst window recovery since the per-minute
        # window (60s) is too long for practical testing
        config = RateLimitConfig(
            per_ip_limit=100,  # Set high to avoid hitting this limit
            per_token_limit=100,
            burst_limit=2,  # Low burst limit
            burst_window_seconds=1,  # 1 second burst window
        )
        limiter = RateLimiter(config)
        await limiter.start()

        try:
            # Make 2 requests (at burst limit)
            allowed1, _ = await limiter.check_rate_limit("192.168.1.1")
            allowed2, _ = await limiter.check_rate_limit("192.168.1.1")
            assert allowed1 and allowed2, "First 2 requests should be allowed"

            # 3rd request should be rejected (burst limit)
            allowed3, info3 = await limiter.check_rate_limit("192.168.1.1")
            assert not allowed3, "3rd request should be rejected by burst limit"

            # Wait for burst window to pass
            await asyncio.sleep(1.5)

            # Should be able to make requests again (burst window expired)
            allowed4, _ = await limiter.check_rate_limit("192.168.1.1")
            assert allowed4, "Requests should be allowed after burst window expires"
        finally:
            await limiter.stop()

    async def test_statistics_tracking(self, rate_limiter):
        """Test that rate limiter tracks statistics correctly."""
        await rate_limiter.start()
        try:
            # Make some requests
            await rate_limiter.check_rate_limit("192.168.1.1")
            await rate_limiter.check_rate_limit("192.168.1.2")
            await rate_limiter.check_rate_limit("192.168.1.1", "token1")

            stats = rate_limiter.get_stats()

            assert stats["total_requests"] == 3
            assert stats["tracked_ips"] == 2
            assert stats["tracked_tokens"] == 1
            assert "config" in stats
            assert stats["config"]["per_ip_limit"] == 10
        finally:
            await rate_limiter.stop()

    async def test_cleanup_expired_entries(self, rate_limiter):
        """Test that expired entries are cleaned up."""
        await rate_limiter.start()
        try:
            # Make a request
            await rate_limiter.check_rate_limit("192.168.1.1")

            # Verify entry exists
            assert len(rate_limiter._ip_entries) == 1

            # Manually trigger cleanup (with old entries)
            await rate_limiter._cleanup_expired_entries()

            # Entry should still exist (not old enough)
            assert len(rate_limiter._ip_entries) == 1

            # Manually age the entry by modifying timestamp
            for entry in rate_limiter._ip_entries.values():
                entry.requests = [time.time() - 400]  # 400 seconds old

            # Trigger cleanup again
            await rate_limiter._cleanup_expired_entries()

            # Entry should be cleaned up now
            assert len(rate_limiter._ip_entries) == 0
        finally:
            await rate_limiter.stop()


class TestRateLimiterHelpers:
    """Test helper functions for rate limiting."""

    def test_get_client_ip_from_direct_connection(self):
        """Test extracting IP from direct connection."""

        class MockTransport:
            def get_extra_info(self, name):
                if name == "peername":
                    return ("192.168.1.100", 12345)
                return None

        class MockRequest:
            headers = {}
            transport = MockTransport()

        request = MockRequest()
        ip = get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header."""

        class MockTransport:
            def get_extra_info(self, name):
                if name == "peername":
                    return ("10.0.0.1", 12345)  # Proxy IP
                return None

        class MockRequest:
            headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
            transport = MockTransport()

        request = MockRequest()
        ip = get_client_ip(request)
        assert ip == "192.168.1.100", "Should extract original client IP"

    def test_get_bearer_token_valid(self):
        """Test extracting valid bearer token."""

        class MockRequest:
            headers = {"Authorization": "Bearer test-token-12345"}

        request = MockRequest()
        token = get_bearer_token(request)
        assert token == "test-token-12345"

    def test_get_bearer_token_missing(self):
        """Test extracting bearer token when missing."""

        class MockRequest:
            headers = {}

        request = MockRequest()
        token = get_bearer_token(request)
        assert token is None

    def test_get_bearer_token_invalid_format(self):
        """Test extracting bearer token with invalid format."""

        class MockRequest:
            headers = {"Authorization": "Basic dXNlcjpwYXNz"}

        request = MockRequest()
        token = get_bearer_token(request)
        assert token is None


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""

    def test_default_config_values(self):
        """Test that default config values are sensible."""
        config = RateLimitConfig()

        assert config.per_ip_limit == 100
        assert config.per_token_limit == 500
        assert config.burst_limit == 20
        assert config.burst_window_seconds == 10
        assert config.cleanup_interval == 300

    def test_custom_config_values(self):
        """Test that custom config values can be set."""
        config = RateLimitConfig(
            per_ip_limit=50,
            per_token_limit=200,
            burst_limit=10,
            burst_window_seconds=5,
        )

        assert config.per_ip_limit == 50
        assert config.per_token_limit == 200
        assert config.burst_limit == 10
        assert config.burst_window_seconds == 5


@pytest.mark.integration
class TestRateLimiterIntegration:
    """Integration tests for rate limiter with concurrent requests."""

    async def test_concurrent_requests_from_same_ip(self):
        """Test rate limiter handles concurrent requests correctly."""
        config = RateLimitConfig(per_ip_limit=5, burst_limit=5)
        limiter = RateLimiter(config)
        await limiter.start()

        try:
            # Make 10 concurrent requests from same IP
            tasks = [
                limiter.check_rate_limit("192.168.1.1")
                for _ in range(10)
            ]
            results = await asyncio.gather(*tasks)

            allowed_count = sum(1 for allowed, _ in results if allowed)
            rejected_count = sum(1 for allowed, _ in results if not allowed)

            # Should allow 5 and reject 5
            assert allowed_count == 5, f"Expected 5 allowed, got {allowed_count}"
            assert rejected_count == 5, f"Expected 5 rejected, got {rejected_count}"
        finally:
            await limiter.stop()

    async def test_concurrent_requests_different_ips(self):
        """Test rate limiter handles concurrent requests from different IPs."""
        config = RateLimitConfig(per_ip_limit=3, burst_limit=3)
        limiter = RateLimiter(config)
        await limiter.start()

        try:
            # Make concurrent requests from 5 different IPs
            tasks = [
                limiter.check_rate_limit(f"192.168.1.{i}")
                for i in range(1, 6)
                for _ in range(2)  # 2 requests per IP
            ]
            results = await asyncio.gather(*tasks)

            allowed_count = sum(1 for allowed, _ in results if allowed)

            # All requests should be allowed (under limit per IP)
            assert allowed_count == 10, "All requests should be allowed"
        finally:
            await limiter.stop()
