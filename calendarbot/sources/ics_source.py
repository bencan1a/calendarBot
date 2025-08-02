"""ICS calendar source handler."""

import logging
import time
from datetime import datetime
from typing import Any, NoReturn, Optional

from ..ics import AuthType, ICSAuth, ICSFetcher, ICSParser, ICSSource
from ..ics.exceptions import ICSAuthError, ICSError, ICSNetworkError, ICSParseError
from ..ics.models import CalendarEvent
from .exceptions import SourceConnectionError, SourceDataError, SourceError
from .models import SourceConfig, SourceHealthCheck, SourceMetrics

logger = logging.getLogger(__name__)


class ICSSourceHandler:
    """Handler for ICS calendar sources."""

    def __init__(self, config: SourceConfig, settings: Any):
        """Initialize ICS source handler.

        Args:
            config: Source configuration
            settings: Application settings
        """
        self.config = config
        self.settings = settings

        # Initialize ICS components
        self.fetcher = ICSFetcher(settings)
        self.parser = ICSParser(settings)

        # Create ICS source configuration
        self.ics_source = self._create_ics_source()

        # Tracking
        self.health = SourceHealthCheck()
        self.metrics = SourceMetrics()

        # Caching support
        self._last_etag: Optional[str] = None
        self._last_modified: Optional[str] = None

        logger.info(f"ICS source handler initialized for {config.name}")

    def _create_ics_source(self) -> ICSSource:
        """Create ICS source configuration from source config.

        Returns:
            ICS source configuration
        """
        # Extract authentication
        auth = ICSAuth(type=AuthType.NONE)

        if self.config.auth_type:
            if self.config.auth_type.lower() == "basic":
                auth = ICSAuth(
                    type=AuthType.BASIC,
                    username=self.config.auth_config.get("username"),
                    password=self.config.auth_config.get("password"),
                )
            elif self.config.auth_type.lower() == "bearer":
                auth = ICSAuth(
                    type=AuthType.BEARER, bearer_token=self.config.auth_config.get("token")
                )

        return ICSSource(
            name=self.config.name,
            url=self.config.url,
            auth=auth,
            refresh_interval=self.config.refresh_interval,
            timeout=self.config.timeout,
            custom_headers=self.config.custom_headers,
            validate_ssl=self.config.validate_ssl,
        )

    async def fetch_events(self, use_cache: bool = True) -> list[CalendarEvent]:
        """Fetch calendar events from ICS source.

        Args:
            use_cache: Whether to use conditional requests for caching

        Returns:
            List of calendar events

        Raises:
            SourceError: If fetch fails
        """
        if not self.config.enabled:
            raise SourceError(f"Source {self.config.name} is disabled")

        start_time = time.time()

        try:
            logger.debug(f"Fetching events from ICS source: {self.config.name}")

            async with self.fetcher as fetcher:
                # Prepare conditional headers for caching
                conditional_headers = None
                if use_cache and (self._last_etag or self._last_modified):
                    conditional_headers = fetcher.get_conditional_headers(
                        self._last_etag, self._last_modified
                    )
                    logger.debug(
                        f"Using conditional headers - etag={self._last_etag}, last_modified={self._last_modified}"
                    )
                else:
                    logger.debug(
                        f"No conditional headers - use_cache={use_cache}, etag={self._last_etag}, last_modified={self._last_modified}"
                    )

                # Fetch ICS content
                response = await fetcher.fetch_ics(self.ics_source, conditional_headers)

                logger.debug(
                    f"ICS response - success={response.success}, is_not_modified={response.is_not_modified}"
                )

                if not response.success:
                    error_msg = response.error_message or "Unknown fetch error"
                    self._raise_connection_error(error_msg)

                # Handle 304 Not Modified
                if response.is_not_modified:
                    logger.debug("Got 304 Not Modified, returning empty list")
                    # Return empty list - caller should use cached events
                    return []

                # Update cache headers
                if response.etag:
                    self._last_etag = response.etag
                if response.last_modified:
                    self._last_modified = response.last_modified

                # Parse ICS content
                if response.content is None:
                    error_msg = "Empty ICS content received"
                    self._raise_data_error(error_msg)

                parse_result = self.parser.parse_ics_content(response.content)

                if not parse_result.success:
                    error_msg = parse_result.error_message or "Failed to parse ICS content"
                    self._raise_data_error(error_msg)

                # Record success
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                self._record_success(response_time, len(parse_result.events))

                logger.debug(
                    f"Successfully fetched {len(parse_result.events)} events from {self.config.name}"
                )

                return parse_result.events

        except ICSAuthError as e:
            error_msg = f"Authentication failed: {e.message}"
            self._raise_connection_error(error_msg, e)

        except ICSNetworkError as e:
            error_msg = f"Network error: {e.message}"
            self._raise_connection_error(error_msg, e)

        except ICSParseError as e:
            error_msg = f"Parse error: {e.message}"
            self._raise_data_error(error_msg, e)

        except ICSError as e:
            error_msg = f"ICS error: {e.message}"
            self._raise_source_error(error_msg, e)

        except Exception as e:
            error_msg = f"Unexpected error: {e!s}"
            self._raise_source_error(error_msg, e)

    async def test_connection(self) -> SourceHealthCheck:
        """Test connection to ICS source.

        Returns:
            Health check result
        """
        start_time = time.time()
        health_check = SourceHealthCheck()

        try:
            logger.debug(f"Testing connection to {self.config.name}")

            async with self.fetcher as fetcher:
                # Test basic connectivity
                is_connected = await fetcher.test_connection(self.ics_source)

                if not is_connected:
                    health_check.update_error("Connection test failed")
                    return health_check

                # Test full fetch and parse
                events = await self.fetch_events(use_cache=False)

                response_time = (time.time() - start_time) * 1000
                health_check.update_success(response_time, len(events))

                logger.info(f"Connection test successful for {self.config.name}")

        except Exception as e:
            error_msg = f"Connection test failed: {e!s}"
            health_check.update_error(error_msg)
            logger.exception(f"Connection test failed for {self.config.name}")

        return health_check

    async def get_todays_events(self, timezone: str = "UTC") -> list[CalendarEvent]:
        """Fetch today's calendar events.

        Args:
            timezone: Timezone for filtering (currently not used for ICS)

        Returns:
            List of today's calendar events
        """
        all_events = await self.fetch_events()

        # Filter to today's events
        from ..utils.helpers import get_timezone_aware_now  # noqa: PLC0415

        today = get_timezone_aware_now().date()
        todays_events = []

        for event in all_events:
            event_date = event.start.date_time.date()
            if event_date == today:
                todays_events.append(event)

        return todays_events

    async def get_events_for_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch events for a specific date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of events in date range
        """
        all_events = await self.fetch_events()

        # Filter events within date range
        filtered_events = []

        for event in all_events:
            event_start = event.start.date_time
            event_end = event.end.date_time

            # Check if event overlaps with date range
            if event_start <= end_date and event_end >= start_date:
                filtered_events.append(event)

        return filtered_events

    def _record_success(self, response_time_ms: float, event_count: int) -> None:
        """Record successful operation.

        Args:
            response_time_ms: Response time in milliseconds
            event_count: Number of events fetched
        """
        self.metrics.record_success(response_time_ms, event_count)
        self.health.update_success(response_time_ms, event_count)

    def _record_failure(self, error_message: str) -> None:
        """Record failed operation.

        Args:
            error_message: Error message
        """
        self.metrics.record_failure(error_message)
        self.health.update_error(error_message)

    def _raise_connection_error(
        self, error_message: str, from_exception: Optional[Exception] = None
    ) -> NoReturn:
        """Record failure and raise SourceConnectionError.

        Args:
            error_message: Error message
            from_exception: Optional exception to chain

        Raises:
            SourceConnectionError: Always raised after recording failure
        """
        self._record_failure(error_message)
        if from_exception:
            raise SourceConnectionError(error_message, self.config.name) from from_exception
        raise SourceConnectionError(error_message, self.config.name)

    def _raise_data_error(
        self, error_message: str, from_exception: Optional[Exception] = None
    ) -> NoReturn:
        """Record failure and raise SourceDataError.

        Args:
            error_message: Error message
            from_exception: Optional exception to chain

        Raises:
            SourceDataError: Always raised after recording failure
        """
        self._record_failure(error_message)
        if from_exception:
            raise SourceDataError(error_message, self.config.name) from from_exception
        raise SourceDataError(error_message, self.config.name)

    def _raise_source_error(
        self, error_message: str, from_exception: Optional[Exception] = None
    ) -> NoReturn:
        """Record failure and raise SourceError.

        Args:
            error_message: Error message
            from_exception: Optional exception to chain

        Raises:
            SourceError: Always raised after recording failure
        """
        self._record_failure(error_message)
        if from_exception:
            raise SourceError(error_message, self.config.name) from from_exception
        raise SourceError(error_message, self.config.name)

    def get_status(self) -> dict[str, Any]:
        """Get current source status.

        Returns:
            Status information dictionary
        """
        return {
            "name": self.config.name,
            "type": self.config.type,
            "enabled": self.config.enabled,
            "url": self.config.url,
            "health_status": self.health.status,
            "last_successful_fetch": self.metrics.last_successful_fetch,
            "success_rate": self.metrics.success_rate,
            "consecutive_failures": self.metrics.consecutive_failures,
            "last_event_count": self.metrics.last_event_count,
            "avg_response_time_ms": self.metrics.avg_response_time_ms,
            "total_requests": self.metrics.total_requests,
            "last_error": self.metrics.last_error,
            "cache_headers": {"etag": self._last_etag, "last_modified": self._last_modified},
        }

    def clear_cache_headers(self) -> None:
        """Clear cached HTTP headers to force full refresh."""
        self._last_etag = None
        self._last_modified = None
        logger.debug(f"Cache headers cleared for {self.config.name}")

    def update_config(self, new_config: SourceConfig) -> None:
        """Update source configuration.

        Args:
            new_config: New configuration
        """
        self.config = new_config
        self.ics_source = self._create_ics_source()

        # Clear cache headers if URL changed
        if self.config.url != new_config.url:
            self.clear_cache_headers()

        logger.info(f"Configuration updated for {self.config.name}")

    def is_healthy(self) -> bool:
        """Check if source is healthy.

        Returns:
            True if source is healthy, False otherwise
        """
        return self.health.is_healthy and self.config.enabled

    def get_health_check(self) -> SourceHealthCheck:
        """Get current health check result.

        Returns:
            Current health check
        """
        return self.health

    def get_metrics(self) -> SourceMetrics:
        """Get current metrics.

        Returns:
            Current metrics
        """
        return self.metrics
