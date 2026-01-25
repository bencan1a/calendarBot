"""Async API client for CalendarBot backend.

This module provides a resilient HTTP client for fetching meeting data
from the /api/whats-next endpoint with exponential backoff retry logic.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from framebuffer_ui.config import Config

logger = logging.getLogger(__name__)


class CalendarAPIClient:
    """Async HTTP client for backend API.

    Handles:
    - Polling /api/whats-next endpoint
    - Graceful error handling with retry logic
    - Connection state tracking
    - Resilient error display (only after 15+ minutes)

    The client implements "silent retry" behavior - transient network
    errors are retried without displaying error messages to the user.
    Only after 15 minutes of consecutive failures will an error be shown.
    """

    def __init__(self, config: Config):
        """Initialize API client.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.endpoint = config.get_api_endpoint("/api/whats-next")

        # State tracking
        self.last_success_time: float | None = None
        self.consecutive_failures: int = 0
        self.last_successful_data: dict[str, Any] | None = None

        # Session (created on first use)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session.

        Returns:
            Active ClientSession
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.api_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

        return self._session

    async def fetch_whats_next(self) -> dict[str, Any]:
        """Fetch next meeting from backend API.

        This method implements resilient error handling:
        - On success: return data and reset failure counters
        - On transient error: return cached data if available
        - On persistent error (15+ min): raise exception for error display

        Returns:
            API response data (fresh or cached)

        Raises:
            Exception: After 15+ minutes of consecutive failures
        """
        try:
            session = await self._get_session()

            async with session.get(
                self.endpoint,
                headers={"Accept": "application/json", "Cache-Control": "no-cache"},
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Success - update state
                self.last_success_time = time.time()
                self.consecutive_failures = 0
                self.last_successful_data = data

                # Log response details
                has_meeting = data.get("meeting") is not None
                logger.debug(
                    "API fetch successful - has_meeting: %s",
                    has_meeting,
                )

                return data

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            Exception,
        ) as error:
            # Failure - track it
            self.consecutive_failures += 1

            logger.warning(
                "API fetch failed (attempt %d): %s",
                self.consecutive_failures,
                error,
            )

            # Check if we should show error to user
            if self.should_show_error():
                # Persistent failure - propagate error for display
                logger.error(
                    "API fetch has been failing for 15+ minutes - showing error"
                )
                raise

            # Transient failure - return cached data if available
            if self.last_successful_data is not None:
                logger.info("Using cached data from last successful fetch")
                return self.last_successful_data

            # No cached data available - return empty response
            logger.warning("No cached data available - returning empty response")
            return {}

    def should_show_error(self) -> bool:
        """Check if errors should be displayed to user.

        Errors are only shown after 15+ minutes of consecutive failures.
        This prevents transient network blips from showing error messages.

        Returns:
            True if error should be displayed, False otherwise
        """
        # If we've never succeeded, wait for multiple failures
        if self.last_success_time is None:
            # Wait for at least 15 failures at 60s intervals = 15 minutes
            return self.consecutive_failures >= 15

        # If we have succeeded before, check time since last success
        time_since_success = time.time() - self.last_success_time
        return time_since_success >= self.config.error_threshold

    async def close(self) -> None:
        """Close the HTTP session.

        Should be called during shutdown to cleanly close connections.
        """
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("API client session closed")
