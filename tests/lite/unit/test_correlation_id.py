"""Tests for correlation ID middleware and distributed tracing functionality."""

import asyncio
import uuid

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from calendarbot_lite.middleware import correlation_id_middleware, get_request_id
from calendarbot_lite.api.middleware.correlation_id import request_id_var


class TestCorrelationIdMiddleware(AioHTTPTestCase):
    """Test correlation ID middleware functionality."""

    async def get_application(self):
        """Create test application with correlation ID middleware."""
        app = web.Application(middlewares=[correlation_id_middleware])

        async def test_handler(request):
            """Test handler that returns correlation ID."""
            correlation_id = request.get("correlation_id", "not-set")
            context_id = get_request_id()
            return web.json_response(
                {"correlation_id": correlation_id, "context_id": context_id}
            )

        app.router.add_get("/test", test_handler)
        return app

    @unittest_run_loop
    async def test_correlation_id_from_x_request_id_header(self):
        """Test correlation ID extraction from X-Request-ID header."""
        test_id = "test-request-id-12345"
        resp = await self.client.request("GET", "/test", headers={"X-Request-ID": test_id})
        assert resp.status == 200

        data = await resp.json()
        assert data["correlation_id"] == test_id
        assert data["context_id"] == test_id

        # Check response header
        assert resp.headers.get("X-Request-ID") == test_id

    @unittest_run_loop
    async def test_correlation_id_from_x_correlation_id_header(self):
        """Test correlation ID extraction from X-Correlation-ID header."""
        test_id = "correlation-id-67890"
        resp = await self.client.request(
            "GET", "/test", headers={"X-Correlation-ID": test_id}
        )
        assert resp.status == 200

        data = await resp.json()
        assert data["correlation_id"] == test_id
        assert data["context_id"] == test_id

    @unittest_run_loop
    async def test_correlation_id_from_x_amzn_trace_id_header(self):
        """Test correlation ID extraction from X-Amzn-Trace-Id header (AWS)."""
        test_id = "Root=1-abc123-def456"
        resp = await self.client.request("GET", "/test", headers={"X-Amzn-Trace-Id": test_id})
        assert resp.status == 200

        data = await resp.json()
        assert data["correlation_id"] == test_id
        assert data["context_id"] == test_id

    @unittest_run_loop
    async def test_correlation_id_header_priority(self):
        """Test correlation ID header priority (X-Amzn-Trace-Id > X-Request-ID)."""
        aws_id = "Root=1-aws-trace"
        request_id = "x-request-id-value"

        resp = await self.client.request(
            "GET",
            "/test",
            headers={"X-Amzn-Trace-Id": aws_id, "X-Request-ID": request_id},
        )
        assert resp.status == 200

        data = await resp.json()
        # AWS trace ID should take priority
        assert data["correlation_id"] == aws_id

    @unittest_run_loop
    async def test_correlation_id_generation(self):
        """Test automatic correlation ID generation when no header present."""
        resp = await self.client.request("GET", "/test")
        assert resp.status == 200

        data = await resp.json()
        # Should be a valid UUID
        correlation_id = data["correlation_id"]
        assert correlation_id != "not-set"
        assert correlation_id != "no-request-id"
        
        # Verify it's a valid UUID format
        try:
            uuid.UUID(correlation_id)
        except ValueError:
            pytest.fail(f"Generated correlation ID is not a valid UUID: {correlation_id}")

        # Should be returned in response header
        assert resp.headers.get("X-Request-ID") == correlation_id

    @unittest_run_loop
    async def test_correlation_id_in_response_header(self):
        """Test correlation ID is added to response headers."""
        test_id = "response-header-test-id"
        resp = await self.client.request("GET", "/test", headers={"X-Request-ID": test_id})
        assert resp.status == 200

        # Check response header contains the correlation ID
        assert resp.headers.get("X-Request-ID") == test_id


class TestCorrelationIdContext:
    """Test correlation ID context variable functionality."""

    def test_get_request_id_no_context(self):
        """Test get_request_id returns default when no context."""
        # Clear any existing context
        request_id_var.set("")
        result = get_request_id()
        assert result == "no-request-id"

    def test_get_request_id_with_context(self):
        """Test get_request_id returns value from context."""
        test_id = "context-test-id-123"
        request_id_var.set(test_id)
        
        result = get_request_id()
        assert result == test_id
        
        # Clean up
        request_id_var.set("")

    @pytest.mark.asyncio
    async def test_context_isolation_between_coroutines(self):
        """Test correlation IDs are isolated between concurrent coroutines."""
        results = []

        async def task(task_id: str):
            """Set and retrieve correlation ID in isolated context."""
            request_id_var.set(task_id)
            await asyncio.sleep(0.01)  # Yield to other tasks
            retrieved_id = get_request_id()
            results.append((task_id, retrieved_id))

        # Run multiple tasks concurrently
        tasks = [task(f"task-{i}") for i in range(5)]
        await asyncio.gather(*tasks)

        # Each task should retrieve its own correlation ID
        for expected_id, retrieved_id in results:
            assert expected_id == retrieved_id


class TestCorrelationIdLogging:
    """Test correlation ID integration with logging."""

    def test_correlation_id_filter_no_context(self):
        """Test CorrelationIdFilter adds 'no-request-id' when no context."""
        from calendarbot_lite.calendar.lite_logging import CorrelationIdFilter
        import logging

        log_filter = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Clear context
        request_id_var.set("")

        # Apply filter
        result = log_filter.filter(record)
        assert result is True
        assert hasattr(record, "request_id")
        assert record.request_id == "no-request-id"  # type: ignore[attr-defined]

    def test_correlation_id_filter_with_context(self):
        """Test CorrelationIdFilter adds correlation ID from context."""
        from calendarbot_lite.calendar.lite_logging import CorrelationIdFilter
        import logging

        log_filter = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Set context
        test_id = "logging-test-id-456"
        request_id_var.set(test_id)

        # Apply filter
        result = log_filter.filter(record)
        assert result is True
        assert hasattr(record, "request_id")
        assert record.request_id == test_id  # type: ignore[attr-defined]

        # Clean up
        request_id_var.set("")


class TestCorrelationIdPropagation:
    """Test correlation ID propagation to external services."""

    @pytest.mark.asyncio
    async def test_http_client_includes_correlation_id(self):
        """Test HTTP client includes correlation ID in outgoing requests."""
        # This is an integration test that would need actual HTTP client usage
        # For now, we test the helper function
        from calendarbot_lite.core.http_client import _get_headers_with_correlation_id

        # Set correlation ID in context
        test_id = "http-client-test-id"
        request_id_var.set(test_id)

        # Get headers
        headers = _get_headers_with_correlation_id()

        # Should include correlation ID
        assert "X-Request-ID" in headers
        assert headers["X-Request-ID"] == test_id

        # Clean up
        request_id_var.set("")

    @pytest.mark.asyncio
    async def test_http_client_no_correlation_id_when_not_set(self):
        """Test HTTP client doesn't include invalid correlation ID."""
        from calendarbot_lite.core.http_client import _get_headers_with_correlation_id

        # Clear context
        request_id_var.set("")

        # Get headers
        headers = _get_headers_with_correlation_id()

        # Should not include X-Request-ID
        assert "X-Request-ID" not in headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
