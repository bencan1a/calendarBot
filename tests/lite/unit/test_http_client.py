"""Unit tests for calendarbot_lite.http_client module."""

import httpx
import pytest

from calendarbot_lite.core.http_client import (
    close_all_clients,
    get_fallback_client,
    get_shared_client,
    record_client_error,
    record_client_success,
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

    async def test_health_tracking_recreates_client_after_errors(self):
        """Test that client is recreated after reaching error threshold."""
        await close_all_clients()

        # Create initial client
        client1 = await get_shared_client("test_client")
        assert isinstance(client1, httpx.AsyncClient)

        # Record 3 errors to trigger recreation threshold
        await record_client_error("test_client")
        await record_client_error("test_client")
        await record_client_error("test_client")

        # Get client again - should be a new instance due to error threshold
        client2 = await get_shared_client("test_client")
        assert isinstance(client2, httpx.AsyncClient)
        # The old client should be closed and a new one created
        assert client1.is_closed
        assert client1 is not client2

        await close_all_clients()

    async def test_health_tracking_success_prevents_recreation(self):
        """Test that recording success resets error count, preventing recreation."""
        await close_all_clients()

        # Create initial client
        client1 = await get_shared_client("test_client")
        assert isinstance(client1, httpx.AsyncClient)

        # Record 2 errors (below threshold)
        await record_client_error("test_client")
        await record_client_error("test_client")

        # Record success - this should reset error count
        await record_client_success("test_client")

        # Record 1 more error (count should be 1, not 3)
        await record_client_error("test_client")

        # Get client again - should be the same instance (no recreation)
        client2 = await get_shared_client("test_client")
        assert client1 is client2

        await close_all_clients()


@pytest.fixture(autouse=True)
async def cleanup_shared_clients():
    """Cleanup shared clients after each test."""
    yield
    # Cleanup after each test
    await close_all_clients()
