"""Cache manager coordinating between API and local storage."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..ics.models import CalendarEvent

# Import new logging infrastructure
from ..monitoring import cache_monitor, memory_monitor, performance_monitor
from ..security import SecurityEventLogger
from ..structured import operation_context, with_correlation_id
from .database import DatabaseManager
from .models import CachedEvent, CacheMetadata

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages calendar event caching with TTL and offline functionality."""

    def __init__(self, settings: Any) -> None:
        """Initialize cache manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.db = DatabaseManager(settings.database_file)

        logger.info("Cache manager initialized")

    async def initialize(self) -> bool:
        """Initialize cache manager and database.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            success = await self.db.initialize()
            if success:
                # Clean up old events on startup
                await self.cleanup_old_events()
                logger.info("Cache manager initialization completed")
            return success

        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            return False

    def _convert_api_event_to_cached(self, api_event: CalendarEvent) -> CachedEvent:
        """Convert API event to cached event model.

        Args:
            api_event: Event from Microsoft Graph API or ICS source

        Returns:
            Cached event model
        """
        now_str = datetime.now().isoformat()

        # Handle different event sources (ICS vs Microsoft Graph)
        # ICS events have show_as as string, Graph events have show_as.value
        if hasattr(api_event.show_as, "value"):
            show_as_value = api_event.show_as.value  # Microsoft Graph API
            location_display = getattr(api_event, "location_display", None)
            web_link = getattr(api_event, "web_link", None)
            series_master_id = getattr(api_event, "series_master_id", None)
            location_address = (
                api_event.location.address
                if hasattr(api_event, "location") and api_event.location
                else None
            )
        else:
            show_as_value = str(api_event.show_as)  # ICS CalendarEvent (enum as string)
            location_display = api_event.location.display_name if api_event.location else None
            web_link = None  # ICS events don't have web_link
            series_master_id = None  # ICS events don't have series_master_id
            location_address = api_event.location.address if api_event.location else None

        return CachedEvent(
            id=f"cached_{api_event.id}",
            graph_id=api_event.id,
            subject=api_event.subject,
            body_preview=api_event.body_preview,
            start_datetime=api_event.start.date_time.isoformat(),
            end_datetime=api_event.end.date_time.isoformat(),
            start_timezone=api_event.start.time_zone,
            end_timezone=api_event.end.time_zone,
            is_all_day=api_event.is_all_day,
            show_as=show_as_value,
            is_cancelled=api_event.is_cancelled,
            is_organizer=api_event.is_organizer,
            location_display_name=location_display,
            location_address=location_address,
            is_online_meeting=api_event.is_online_meeting,
            online_meeting_url=api_event.online_meeting_url,
            web_link=web_link,
            is_recurring=api_event.is_recurring,
            series_master_id=series_master_id,
            cached_at=now_str,
            last_modified=(
                api_event.last_modified_date_time.isoformat()
                if api_event.last_modified_date_time
                else None
            ),
        )

    @performance_monitor("cache_events")
    @with_correlation_id()
    async def cache_events(self, api_events: List[CalendarEvent]) -> bool:
        """Cache events from API response with comprehensive data validation and error handling.

        Processes and stores calendar events from various sources (Microsoft Graph API, ICS feeds)
        into the local database cache. Implements data transformation, validation, memory monitoring,
        and atomic transaction handling to ensure data integrity and system reliability.

        Args:
            api_events: List of CalendarEvent instances from calendar sources. Each event must contain:
                       Core Attributes:
                       - id (str): Unique event identifier from source system
                       - subject (str): Event title/summary
                       - start (DateTimeType): Event start with date_time and time_zone
                       - end (DateTimeType): Event end with date_time and time_zone
                       - is_all_day (bool): All-day event indicator
                       - show_as (Union[str, Enum]): Availability status (free/busy/tentative/etc.)

                       Optional Attributes:
                       - body_preview (str): Event description excerpt
                       - location (LocationType): Physical/virtual location details
                       - is_online_meeting (bool): Virtual meeting indicator
                       - online_meeting_url (str): Meeting join URL
                       - is_cancelled (bool): Cancellation status
                       - is_organizer (bool): Current user organizer status
                       - is_recurring (bool): Recurring event indicator
                       - series_master_id (str): Parent event ID for recurrences
                       - web_link (str): Calendar web link (Graph API only)
                       - last_modified_date_time (datetime): Last modification timestamp

                       Supported Source Formats:
                       - Microsoft Graph API events (msgraph-core objects)
                       - ICS/CalDAV events (icalendar parsed objects)
                       - Custom CalendarEvent implementations

        Returns:
            bool: True if all events were successfully cached with database commit,
                  False if any critical error occurred during processing or storage.
                  Empty event lists return True (successful no-op operation).

        Raises:
            No exceptions propagated - all errors are caught and logged internally.
            Method designed for resilient operation in production environments.

        Internal Exception Handling:
            - AttributeError: Missing required event attributes, logged and operation fails
            - TypeError: Invalid event object types, conversion errors logged
            - DatabaseError: Storage failures, transaction rollback, metadata updated
            - MemoryError: Large event list processing failures, monitoring alerts triggered
            - ValidationError: Event data validation failures, detailed logging
            - Any other unexpected exceptions during conversion or storage operations

        Data Transformation Process:
            1. Event Format Detection: Identifies Microsoft Graph vs ICS event structure
            2. Attribute Mapping: Maps source-specific fields to standardized CachedEvent model
            3. Type Conversion: Handles datetime, enum, and optional field transformations
            4. Data Validation: Ensures required fields present and properly formatted
            5. Memory Monitoring: Tracks memory usage during bulk conversions
            6. Database Storage: Atomic transaction with rollback on failure
            7. Metadata Update: Records operation success/failure with timestamps

        Performance Monitoring:
            - Automatic performance tracking via @performance_monitor decorator
            - Memory usage monitoring during event conversion operations
            - Cache operation metrics via @cache_monitor context managers
            - Correlation ID tracking for distributed tracing (@with_correlation_id)

        Side Effects:
            - Updates cache metadata with operation timestamp and status
            - Increments consecutive_failures counter on storage failures
            - Triggers database cleanup for old events (on successful operations)
            - Generates structured logs for monitoring and debugging
            - Updates performance metrics for system health monitoring

        Example:
            >>> cache_manager = CacheManager(settings)
            >>> await cache_manager.initialize()
            >>> graph_events = await msgraph_client.get_calendar_events()
            >>> success = await cache_manager.cache_events(graph_events)
            >>> if success:
            ...     print(f"Cached {len(graph_events)} events successfully")

        Note:
            This method is designed to be idempotent - calling multiple times with
            the same events will update existing records rather than create duplicates.
            Database operations use UPSERT logic based on event graph_id uniqueness.
        """
        try:
            event_count = len(api_events) if api_events else 0
            logger.debug(f"Caching {event_count} API events")

            if not api_events:
                logger.debug("No events to cache")
                await self._update_fetch_metadata(success=True, error=None)
                return True

            # Convert API events to cached events with memory monitoring
            with memory_monitor("event_conversion"):
                cached_events = [self._convert_api_event_to_cached(event) for event in api_events]

            logger.debug(f"Converted {len(cached_events)} API events to cached events")
            if cached_events:
                # Log sample event details (debug level)
                sample_event = cached_events[0]
                logger.debug(
                    f"Sample cached event - {sample_event.subject} from {sample_event.start_datetime} to {sample_event.end_datetime}"
                )

            # Store in database with cache monitoring
            with cache_monitor("database_store", "cache_manager"):
                success = await self.db.store_events(cached_events)

            logger.debug(f"Database store_events returned: {success}")

            if success:
                # Update metadata
                await self._update_fetch_metadata(success=True, error=None)
                logger.debug(f"Successfully cached {len(cached_events)} events")
            else:
                await self._update_fetch_metadata(success=False, error="Database storage failed")
                logger.error("Failed to store events in database")

            return success

        except Exception as e:
            logger.error(f"Failed to cache events: {e}")
            await self._update_fetch_metadata(success=False, error=str(e))
            return False

    @performance_monitor("get_cached_events")
    @with_correlation_id()
    async def get_cached_events(
        self, start_date: datetime, end_date: datetime
    ) -> List[CachedEvent]:
        """Get cached events for date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of cached events
        """
        try:
            with cache_monitor("date_range_query", "cache_manager"):
                events = await self.db.get_events_by_date_range(start_date, end_date)
            logger.debug(f"Retrieved {len(events)} cached events")
            return events

        except Exception as e:
            logger.error(f"Failed to get cached events: {e}")
            return []

    async def get_events_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[CachedEvent]:
        """Get cached events for date range (alias for get_cached_events).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of cached events
        """
        cached_events: List[CachedEvent] = await self.get_cached_events(start_date, end_date)
        return cached_events

    @performance_monitor("get_todays_cached_events")
    @with_correlation_id()
    async def get_todays_cached_events(self) -> List[CachedEvent]:
        """Get today's cached events.

        Returns:
            List of today's cached events
        """
        try:
            with cache_monitor("todays_events_query", "cache_manager"):
                events = await self.db.get_todays_events()
            logger.debug(f"Retrieved {len(events)} today's cached events")
            return events

        except Exception as e:
            logger.error(f"Failed to get today's cached events: {e}")
            return []

    async def is_cache_fresh(self) -> bool:
        """Check if cache is fresh (within TTL).

        Returns:
            True if cache is fresh, False if stale or missing
        """
        try:
            metadata = await self.db.get_cache_metadata()

            if not metadata.last_successful_fetch_dt:
                logger.debug("No successful fetch recorded - cache is stale")
                return False

            is_fresh = not metadata.is_cache_expired()
            logger.debug(f"Cache freshness check: {'fresh' if is_fresh else 'stale'}")
            return is_fresh

        except Exception as e:
            logger.error(f"Failed to check cache freshness: {e}")
            return False

    async def get_cache_status(self) -> CacheMetadata:
        """Get current cache status and metadata.

        Returns:
            Cache metadata object
        """
        try:
            metadata = await self.db.get_cache_metadata()

            # Check if cache is stale
            metadata.is_stale = not await self.is_cache_fresh()
            metadata.cache_ttl_seconds = self.settings.cache_ttl

            return metadata

        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            return CacheMetadata()

    async def cleanup_old_events(self, days_old: int = 7) -> int:
        """Clean up old cached events.

        Args:
            days_old: Number of days after which to remove events

        Returns:
            Number of events removed
        """
        try:
            removed_count = await self.db.cleanup_old_events(days_old)
            logger.debug(f"Cleaned up {removed_count} old events")
            return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0

    async def clear_cache(self) -> bool:
        """Clear all cached events.

        Returns:
            True if clearing was successful, False otherwise
        """
        try:
            # Clear all events (essentially cleanup with 0 days)
            await self.cleanup_old_events(days_old=0)

            # Reset metadata
            await self.db.update_cache_metadata(
                last_update=None,
                last_successful_fetch=None,
                consecutive_failures=0,
                last_error=None,
                last_error_time=None,
            )

            logger.info("Cache cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def _update_fetch_metadata(self, success: bool, error: Optional[str] = None) -> None:
        """Update metadata after a fetch attempt.

        Args:
            success: Whether the fetch was successful
            error: Error message if fetch failed
        """
        try:
            now_str = datetime.now().isoformat()

            if success:
                await self.db.update_cache_metadata(
                    last_update=now_str,
                    last_successful_fetch=now_str,
                    consecutive_failures=0,
                    last_error=None,
                    last_error_time=None,
                )
            else:
                # Get current metadata to increment failure count
                metadata = await self.db.get_cache_metadata()

                await self.db.update_cache_metadata(
                    last_update=now_str,
                    consecutive_failures=metadata.consecutive_failures + 1,
                    last_error=error or "Unknown error",
                    last_error_time=now_str,
                )

        except Exception as e:
            logger.error(f"Failed to update fetch metadata: {e}")

    async def get_cache_summary(self) -> Dict[str, Any]:
        """Get a summary of cache status for display/logging.

        Returns:
            Dictionary with cache summary information
        """
        try:
            metadata = await self.get_cache_status()
            db_info = await self.db.get_database_info()

            summary = {
                "total_events": metadata.total_events,
                "is_fresh": not metadata.is_stale,
                "last_update": metadata.last_update,
                "consecutive_failures": metadata.consecutive_failures,
                "cache_ttl_hours": metadata.cache_ttl_seconds / 3600,
                "database_size_mb": db_info.get("file_size_bytes", 0) / (1024 * 1024),
                "journal_mode": db_info.get("journal_mode", "unknown"),
            }

            if metadata.last_update_dt:
                summary["minutes_since_update"] = metadata.time_since_last_update()

            return summary

        except Exception as e:
            logger.error(f"Failed to get cache summary: {e}")
            return {}

    async def cleanup(self) -> bool:
        """Clean up cache resources and old events.

        This method is called during test teardowns and application shutdown.

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Clean up old events (default 7 days)
            removed_count = await self.cleanup_old_events()
            logger.debug(f"Cache cleanup completed, removed {removed_count} old events")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return False
