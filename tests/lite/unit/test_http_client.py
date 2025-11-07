"""Unit tests for calendarbot_lite.http_client module."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from calendarbot_lite.core.http_client import (
    StreamingHTTPResponse,
    close_all_clients,
    get_client_health,
    get_fallback_client,
    get_shared_client,
    record_client_error,
    record_client_success,
    stream_request_with_peek,
)

pytestmark = pytest.mark.unit


class TestSharedHTTPClient:
    """Test shared HTTP client management."""

    async def test_get_shared_client_creates_new_client(self):
        """Test that get_shared_client creates a new client with Pi Zero 2W limits."""
        # Cleanup any existing clients
        await close_all_clients()

        client = await get_shared_client("test_client")

        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed
        # Note: httpx.AsyncClient limits are internal, so we just verify
        # the client was created successfully with our configuration

        # Cleanup
        await close_all_clients()

    async def test_get_shared_client_reuses_existing_client(self):
        """Test that get_shared_client reuses existing clients."""
        # Cleanup any existing clients
        await close_all_clients()

        client1 = await get_shared_client("test_client")
        client2 = await get_shared_client("test_client")

        assert client1 is client2

        # Cleanup
        await close_all_clients()

    async def test_get_shared_client_different_ids(self):
        """Test that different client IDs create separate clients."""
        # Cleanup any existing clients
        await close_all_clients()

        client1 = await get_shared_client("test_client_1")
        client2 = await get_shared_client("test_client_2")

        assert client1 is not client2

        # Cleanup
        await close_all_clients()

    async def test_close_all_clients_closes_all(self):
        """Test that close_all_clients properly closes all clients."""
        # Create multiple clients
        client1 = await get_shared_client("test_client_1")
        client2 = await get_shared_client("test_client_2")

        assert not client1.is_closed
        assert not client2.is_closed

        await close_all_clients()

        assert client1.is_closed
        assert client2.is_closed

    async def test_get_fallback_client_creates_temporary_client(self):
        """Test that get_fallback_client creates a temporary client."""
        client = await get_fallback_client()

        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

        # Cleanup
        await client.aclose()

    async def test_health_tracking_records_errors(self):
        """Test that client health tracking records errors correctly."""
        await close_all_clients()

        # Record errors and verify state changes
        await record_client_error("test_client")

        # Verify first error recorded
        health = await get_client_health("test_client")
        assert health["error_count"] == 1
        assert health["last_error_time"] > 0

        # Record more errors
        await record_client_error("test_client")
        await record_client_error("test_client")

        # Verify error count increased
        health = await get_client_health("test_client")
        assert health["error_count"] == 3
        assert health["last_error_time"] > 0

        # This should trigger client recreation (3 errors >= HEALTH_ERROR_THRESHOLD)
        client = await get_shared_client("test_client")
        assert isinstance(client, httpx.AsyncClient)

        # Verify health was reset after recreation
        health_after_recreate = await get_client_health("test_client")
        assert health_after_recreate["error_count"] == 0
        assert "created_time" in health_after_recreate

        await close_all_clients()

    async def test_health_tracking_records_success(self):
        """Test that client health tracking records success correctly."""
        await close_all_clients()

        # Record some errors and verify state
        await record_client_error("test_client")
        await record_client_error("test_client")

        # Verify errors were recorded
        health = await get_client_health("test_client")
        assert health["error_count"] == 2
        assert health["last_error_time"] > 0

        # Record success and verify error count reset
        await record_client_success("test_client")

        # Verify error count was reset to 0
        health_after_success = await get_client_health("test_client")
        assert health_after_success["error_count"] == 0
        # last_error_time remains but error_count is reset

        # Client should still be healthy and reusable
        client = await get_shared_client("test_client")
        assert isinstance(client, httpx.AsyncClient)

        await close_all_clients()


class TestStreamingHTTPResponse:
    """Test streaming HTTP response wrapper."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock httpx.Response."""
        response = Mock(spec=httpx.Response)
        response.headers = httpx.Headers({"content-type": "text/calendar"})
        response.status_code = 200
        response.raise_for_status = Mock()
        response.aiter_bytes = AsyncMock()
        return response

    def test_streaming_response_initialization(self, mock_response):
        """Test StreamingHTTPResponse initialization."""
        streaming_resp = StreamingHTTPResponse(mock_response)

        assert streaming_resp.response is mock_response
        assert streaming_resp._initial_bytes is None
        assert not streaming_resp._peek_consumed

    async def test_peek_initial_bytes(self, mock_response):
        """Test peek_initial_bytes functionality."""

        async def mock_aiter_bytes(chunk_size=None):
            yield b"test data"

        mock_response.aiter_bytes = mock_aiter_bytes

        streaming_resp = StreamingHTTPResponse(mock_response)

        initial_bytes = await streaming_resp.peek_initial_bytes(4)
        assert initial_bytes == b"test data"

    async def test_peek_already_consumed_raises_error(self, mock_response):
        """Test that peek raises error when already consumed."""

        async def mock_aiter_bytes(chunk_size=None):
            yield b"test"

        mock_response.aiter_bytes = mock_aiter_bytes

        streaming_resp = StreamingHTTPResponse(mock_response)
        streaming_resp._peek_consumed = True

        with pytest.raises(RuntimeError, match="Peek has already been consumed"):
            await streaming_resp.peek_initial_bytes()

    async def test_iter_bytes_with_peek(self, mock_response):
        """Test iter_bytes_with_peek includes peeked bytes."""

        async def mock_aiter_bytes(chunk_size=None):
            yield b"more data"

        mock_response.aiter_bytes = mock_aiter_bytes

        streaming_resp = StreamingHTTPResponse(mock_response)
        streaming_resp._initial_bytes = b"initial"

        chunks = []
        async for chunk in streaming_resp.iter_bytes_with_peek():
            chunks.append(chunk)

        assert chunks[0] == b"initial"
        assert b"more data" in chunks

    async def test_read_full_content(self, mock_response):
        """Test read_full_content combines all bytes."""

        async def mock_aiter_bytes(chunk_size=None):
            yield b"chunk1"
            yield b"chunk2"

        mock_response.aiter_bytes = mock_aiter_bytes

        streaming_resp = StreamingHTTPResponse(mock_response)
        streaming_resp._initial_bytes = b"initial"

        full_content = await streaming_resp.read_full_content()
        assert full_content == b"initialchunk1chunk2"

    def test_headers_property(self, mock_response):
        """Test headers property access."""
        streaming_resp = StreamingHTTPResponse(mock_response)
        assert streaming_resp.headers == mock_response.headers

    def test_status_code_property(self, mock_response):
        """Test status_code property access."""
        streaming_resp = StreamingHTTPResponse(mock_response)
        assert streaming_resp.status_code == mock_response.status_code

    def test_raise_for_status(self, mock_response):
        """Test raise_for_status delegation."""
        streaming_resp = StreamingHTTPResponse(mock_response)
        streaming_resp.raise_for_status()
        mock_response.raise_for_status.assert_called_once()


class TestStreamRequestWithPeek:
    """Test stream_request_with_peek functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock httpx.AsyncClient."""
        client = Mock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def mock_response(self):
        """Create a mock httpx.Response."""
        response = Mock(spec=httpx.Response)
        response.headers = httpx.Headers({"content-type": "text/calendar"})
        response.status_code = 200
        response.raise_for_status = Mock()
        response.aiter_bytes = AsyncMock()
        return response

    async def test_stream_request_with_peek_success(self, mock_client, mock_response):
        """Test successful stream request with peek."""
        # Setup mock stream context manager
        stream_context = AsyncMock()
        stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        stream_context.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = Mock(return_value=stream_context)

        result = await stream_request_with_peek(mock_client, "GET", "http://example.com")

        assert isinstance(result, StreamingHTTPResponse)
        assert result.response is mock_response
        mock_client.stream.assert_called_once_with("GET", "http://example.com")


@pytest.fixture(autouse=True)
async def cleanup_shared_clients():
    """Cleanup shared clients after each test."""
    yield
    # Cleanup after each test
    await close_all_clients()
