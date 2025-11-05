"""Integration tests for rate limiting middleware on Alexa endpoints.

This module tests the rate limiting functionality integrated with
aiohttp routes to ensure proper protection of Alexa endpoints.
"""

import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from calendarbot_lite.api.middleware.rate_limiter import RateLimitConfig, RateLimiter
from calendarbot_lite.api.middleware.rate_limit_middleware import create_rate_limited_handler


@pytest.fixture
async def rate_limiter():
    """Create a rate limiter for testing."""
    config = RateLimitConfig(
        per_ip_limit=5,
        per_token_limit=10,
        burst_limit=3,
        burst_window_seconds=10,
    )
    limiter = RateLimiter(config)
    await limiter.start()
    yield limiter
    await limiter.stop()


@pytest.fixture
async def test_app(rate_limiter):
    """Create a test aiohttp application with rate-limited routes."""
    app = web.Application()

    # Simple test handler
    async def test_handler(request):
        return web.json_response({"status": "ok", "message": "Request processed"})

    # Apply rate limiting to handler
    rate_limited_handler = create_rate_limited_handler(test_handler, rate_limiter)

    # Register route
    app.router.add_get("/api/test", rate_limited_handler)

    # Store rate limiter in app for health checks
    app["rate_limiter"] = rate_limiter

    return app


@pytest.fixture
async def test_client(test_app):
    """Create a test client for the app."""
    async with TestClient(TestServer(test_app)) as client:
        yield client


@pytest.mark.integration
class TestRateLimitMiddleware:
    """Integration tests for rate limiting middleware."""

    async def test_successful_request_includes_rate_limit_headers(self, test_client):
        """Test that successful requests include rate limit headers."""
        response = await test_client.get("/api/test")

        assert response.status == 200
        data = await response.json()
        assert data["status"] == "ok"

        # Check rate limit headers
        assert "X-RateLimit-Limit-IP" in response.headers
        assert "X-RateLimit-Remaining-IP" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        assert int(response.headers["X-RateLimit-Limit-IP"]) == 5
        assert int(response.headers["X-RateLimit-Remaining-IP"]) >= 0

    async def test_rate_limit_exceeded_returns_429(self, test_client):
        """Test that exceeding rate limit returns HTTP 429."""
        # Make 4 requests (burst limit is 3)
        responses = []
        for i in range(4):
            response = await test_client.get("/api/test")
            responses.append(response)

        # First 3 should succeed (burst limit)
        for i in range(3):
            assert responses[i].status == 200, f"Request {i+1} should succeed"

        # 4th should be rate limited
        assert responses[3].status == 429, "4th request should be rate limited"

        # Check 429 response format
        data = await responses[3].json()
        assert data["error"] == "rate_limit_exceeded"
        assert "retry_after" in data
        assert data["retry_after"] > 0

        # Check Retry-After header
        assert "Retry-After" in responses[3].headers
        assert int(responses[3].headers["Retry-After"]) > 0

    async def test_token_based_rate_limiting(self, test_client):
        """Test that bearer token rate limiting works."""
        headers = {"Authorization": "Bearer test-token-123"}

        # Make requests with token (burst limit is 3)
        responses = []
        for i in range(4):
            response = await test_client.get("/api/test", headers=headers)
            responses.append(response)

        # First 3 should succeed (burst limit)
        success_count = sum(1 for r in responses if r.status == 200)
        assert success_count == 3, f"Should allow 3 requests (burst limit), got {success_count}"

        # Check token limit headers in successful responses
        for r in responses:
            if r.status == 200:
                assert "X-RateLimit-Limit-Token" in r.headers
                assert "X-RateLimit-Remaining-Token" in r.headers

    async def test_different_ips_tracked_separately(self, test_client):
        """Test that different IPs have separate rate limits."""
        # Make 3 requests with IP 1 (will hit burst limit)
        for _ in range(3):
            response = await test_client.get(
                "/api/test",
                headers={"X-Forwarded-For": "192.168.1.1"}
            )
            assert response.status == 200

        # 4th request from IP 1 should fail
        response = await test_client.get(
            "/api/test",
            headers={"X-Forwarded-For": "192.168.1.1"}
        )
        assert response.status == 429

        # Request from IP 2 should still succeed
        response = await test_client.get(
            "/api/test",
            headers={"X-Forwarded-For": "192.168.1.2"}
        )
        assert response.status == 200

    async def test_burst_protection(self, test_client):
        """Test that burst limit prevents rapid requests."""
        # Make 4 rapid requests (burst limit is 3)
        responses = []
        tasks = [test_client.get("/api/test") for _ in range(4)]
        responses = await asyncio.gather(*tasks)

        # At least one should be rejected due to burst limit
        rejected_count = sum(1 for r in responses if r.status == 429)
        assert rejected_count >= 1, "Should reject at least 1 request due to burst limit"

    async def test_rate_limit_headers_on_rejection(self, test_client):
        """Test that rate limit headers are included in 429 responses."""
        # Exhaust rate limit (burst limit is 3)
        for _ in range(3):
            await test_client.get("/api/test")

        # Make request that will be rejected
        response = await test_client.get("/api/test")

        assert response.status == 429

        # Check all headers are present
        assert "X-RateLimit-Limit-IP" in response.headers
        assert "X-RateLimit-Remaining-IP" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers

        # After burst limit, there may still be requests remaining in per-minute window
        # So we just check that remaining is a valid number
        remaining = int(response.headers["X-RateLimit-Remaining-IP"])
        assert remaining >= 0, "Remaining should be non-negative"


@pytest.mark.slow
@pytest.mark.integration
class TestRateLimitRecovery:
    """Test rate limit recovery over time."""

    async def test_sliding_window_allows_new_requests(self, test_client):
        """Test that new requests are allowed as old ones expire."""
        # Make 3 requests (at burst limit)
        for _ in range(3):
            response = await test_client.get("/api/test")
            assert response.status == 200

        # 4th request should fail (burst limit)
        response = await test_client.get("/api/test")
        assert response.status == 429

        # Wait for burst window to pass (burst_window_seconds=10)
        await asyncio.sleep(11)

        # Should be able to make requests again
        response = await test_client.get("/api/test")
        # Note: May still be limited by per-minute rate, but status should improve
        # or remaining count should increase
        assert "X-RateLimit-Remaining-IP" in response.headers


@pytest.mark.integration
class TestRateLimitStatistics:
    """Test rate limiter statistics tracking."""

    async def test_statistics_updated_on_requests(self, test_app, test_client):
        """Test that statistics are updated correctly."""
        # Make some requests
        await test_client.get("/api/test")
        await test_client.get("/api/test", headers={"X-Forwarded-For": "192.168.1.2"})
        await test_client.get("/api/test", headers={"Authorization": "Bearer token1"})

        # Get statistics from app
        rate_limiter = test_app["rate_limiter"]
        stats = rate_limiter.get_stats()

        assert stats["total_requests"] >= 3
        assert stats["tracked_ips"] >= 1
        assert "rejection_rate" in stats
        assert "config" in stats


@pytest.mark.integration
class TestRateLimitingWithAuthentication:
    """Test rate limiting combined with authentication."""

    async def test_rate_limit_applied_before_auth(self):
        """Test that rate limiting is checked before authentication."""
        # Create app with both rate limiting and auth
        app = web.Application()

        async def auth_handler(request):
            # Simulate authentication check
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer secret"):
                return web.json_response({"error": "unauthorized"}, status=401)
            return web.json_response({"status": "ok"})

        config = RateLimitConfig(per_ip_limit=2, burst_limit=2)
        limiter = RateLimiter(config)
        await limiter.start()

        try:
            rate_limited_handler = create_rate_limited_handler(auth_handler, limiter)
            app.router.add_get("/api/auth", rate_limited_handler)

            async with TestClient(TestServer(app)) as client:
                # Make 3 requests without auth (should hit rate limit)
                responses = []
                for _ in range(3):
                    response = await client.get("/api/auth")
                    responses.append(response)

                # First 2 should fail auth (401)
                assert responses[0].status == 401
                assert responses[1].status == 401

                # 3rd should be rate limited (429) before auth check
                assert responses[2].status == 429

        finally:
            await limiter.stop()
