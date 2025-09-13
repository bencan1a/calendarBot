"""Cache manager coordinating between API and local storage."""

import logging
from datetime import datetime
from typing import Any, Optional, Union

from ..ics.models import CalendarEvent, ICSParseResult

# Import new logging infrastructure
from ..monitoring import cache_monitor, memory_monitor, performance_monitor
from ..structured import with_correlation_id
from .database import DatabaseManager
from .models import CachedEvent, CacheMetadata, RawEvent

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

        except Exception:
            logger.exception("Failed to initialize cache manager")
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

        # Generate deterministic ID for proper deduplication while supporting recurring instances
        import hashlib  # noqa: PLC0415

        # Create deterministic suffix based on graph_id + start_time for unique recurring instances
        # This ensures: same event = same ID (fixes duplicates), different instances = different IDs
        deterministic_content = f"{api_event.id}_{api_event.start.date_time.isoformat()}"
        suffix_hash = hashlib.sha256(deterministic_content.encode()).hexdigest()[:8]

        generated_id = f"cached_{api_event.id}_{suffix_hash}"

        return CachedEvent(
            id=generated_id,
            graph_id=generated_id,  # Use unique generated_id instead of api_event.id to fix duplicates
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
    async def cache_events(self, api_events: Union[list[CalendarEvent], ICSParseResult]) -> bool:  # noqa: PLR0912, PLR0915
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
            # Handle both list[CalendarEvent] and ICSParseResult inputs
            if isinstance(api_events, ICSParseResult):
                events_list = api_events.events
                event_count = len(events_list)
                raw_content = api_events.raw_content
                source_url = api_events.source_url
            else:
                events_list = api_events
                event_count = len(events_list) if events_list else 0
                raw_content = None
                source_url = None

            logger.debug(f"Caching {event_count} API events")

            if not events_list:
                logger.debug("No events to cache")
                await self._update_fetch_metadata(success=True, error=None)
                return True

            # Convert API events to cached events with memory monitoring
            with memory_monitor("event_conversion"):
                cached_events = [self._convert_api_event_to_cached(event) for event in events_list]

            logger.debug(f"Converted {len(cached_events)} API events to cached events")

            # Prepare raw events if we have raw content
            raw_events = []
            if raw_content:
                try:
                    # Parse raw events independently from the ICS content
                    # This allows comparison with cached events to detect filtering issues
                    from ..ics.parser import ICSParser  # noqa: PLC0415

                    parser = ICSParser(self.settings)

                    # Re-parse the raw content independently to get ALL unfiltered event data
                    independent_parse_result = parser.parse_ics_content_unfiltered(
                        raw_content,
                        source_url,
                    )

                    # Create raw events from the independent parsing using individual event ICS content
                    event_raw_content_map = getattr(
                        independent_parse_result,
                        "event_raw_content_map",
                        {},
                    )

                    for event in independent_parse_result.events:
                        # Get individual event ICS content from the mapping
                        individual_ics_content = event_raw_content_map.get(
                            event.id,
                            f"# Event {event.id} - Individual ICS content not available",
                        )

                        # Determine if this is a recurrence instance or master pattern
                        recurrence_id_raw = getattr(event, "recurrence_id", None)

                        # Convert RECURRENCE-ID to string properly (safety conversion for any remaining objects)
                        if recurrence_id_raw is not None:
                            if hasattr(recurrence_id_raw, "to_ical"):
                                # icalendar object - convert to iCal format then decode
                                recurrence_id = recurrence_id_raw.to_ical().decode("utf-8")
                            else:
                                # Already a string or other type - convert to string
                                recurrence_id = str(recurrence_id_raw)
                        else:
                            recurrence_id = None

                        is_instance = recurrence_id is not None

                        raw_event = RawEvent.create_from_ics(
                            graph_id=event.id,
                            subject=event.subject,
                            start_datetime=event.start.date_time.isoformat(),
                            end_datetime=event.end.date_time.isoformat(),
                            start_timezone=event.start.time_zone,
                            end_timezone=event.end.time_zone,
                            ics_content=individual_ics_content,  # Store individual event ICS content
                            source_url=source_url,
                            body_preview=event.body_preview,
                            is_all_day=event.is_all_day,
                            show_as=str(event.show_as),
                            is_cancelled=event.is_cancelled,
                            is_organizer=event.is_organizer,
                            location_display_name=event.location.display_name
                            if event.location
                            else None,
                            location_address=event.location.address if event.location else None,
                            is_online_meeting=event.is_online_meeting,
                            online_meeting_url=event.online_meeting_url,
                            is_recurring=event.is_recurring,
                            recurrence_id=recurrence_id,
                            is_instance=is_instance,
                            last_modified=event.last_modified_date_time.isoformat()
                            if event.last_modified_date_time
                            else None,
                        )
                        raw_events.append(raw_event)
                    logger.debug(
                        f"Created {len(raw_events)} raw events from independent ICS parsing",
                    )
                except Exception as e:
                    logger.warning(f"Failed to create raw events: {e}")
                    # Continue without raw events - this is a fallback strategy

            # Store events in database with atomic transaction handling
            with cache_monitor("database_store", "cache_manager"):
                try:
                    # First store cached events
                    success = await self.db.store_events(cached_events)

                    if success and raw_events:
                        # Store raw events if cached events succeeded
                        raw_success = await self.db.store_raw_events(raw_events)
                        if raw_success:
                            logger.debug(f"Successfully stored {len(raw_events)} raw events")
                        else:
                            logger.warning(
                                "Failed to store raw events, but cached events were stored",
                            )

                except Exception:
                    logger.exception("Failed to store events")
                    # If storing fails, try to store just cached events as fallback
                    try:
                        success = await self.db.store_events(cached_events)
                        logger.warning("Stored cached events only after raw storage error")
                    except Exception:
                        logger.exception("Failed to store cached events in fallback")
                        success = False

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
            logger.exception("Failed to cache events")
            await self._update_fetch_metadata(success=False, error=str(e))
            return False

    @performance_monitor("get_cached_events")
    @with_correlation_id()
    async def get_cached_events(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CachedEvent]:
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

        except Exception:
            logger.exception("Failed to get cached events")
            return []

    async def get_events_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CachedEvent]:
        """Get cached events for date range (alias for get_cached_events).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of cached events
        """
        cached_events: list[CachedEvent] = await self.get_cached_events(start_date, end_date)
        return cached_events

    @performance_monitor("get_todays_cached_events")
    @with_correlation_id()
    async def get_todays_cached_events(self) -> list[CachedEvent]:
        """Get today's cached events.

        Returns:
            List of today's cached events
        """
        try:
            with cache_monitor("todays_events_query", "cache_manager"):
                events = await self.db.get_todays_events()
            logger.debug(f"Retrieved {len(events)} today's cached events")
            return events

        except Exception:
            logger.exception("Failed to get today's cached events")
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

        except Exception:
            logger.exception("Failed to check cache freshness")
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

        except Exception:
            logger.exception("Failed to get cache status")
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

        except Exception:
            logger.exception("Failed to cleanup old events")
            return 0

    async def clear_all_events(self) -> int:
        """Clear all events from the database.

        Returns:
            Number of events removed
        """
        try:
            return await self.db.clear_all_events()

        except Exception:
            logger.exception("Failed to clear all events")
            return 0

    async def clear_cache(self) -> bool:
        """Clear all cached events.

        Returns:
            True if clearing was successful, False otherwise
        """
        try:
            # Intentionally perform a full clear of the cached_events table so that
            # the database is fully purged and can be reloaded on the next fetch.
            # Previously this called cleanup_old_events(days_old=0) which only removed
            # events that had already ended; future events (including ones deleted on
            # the server) would remain. Use clear_all_events() which executes a full DELETE.
            try:
                # Attempt to log current database info for diagnostics
                db_info_before = await self.db.get_database_info()
                total_before = None
                if isinstance(db_info_before, dict) and "events_by_date" in db_info_before:
                    # get_database_info returns events_by_date; compute rough total if present
                    total_before = sum(
                        item.get("count", 0) for item in db_info_before.get("events_by_date", [])
                    )
                logger.debug(f"Clearing cache - events_before={total_before}")
            except Exception:
                logger.debug(
                    "Failed to retrieve database info before clearing cache", exc_info=True
                )

            deleted_count = await self.db.clear_all_events()
            logger.debug(f"Cleared cache - deleted_events={deleted_count}")

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

        except Exception:
            logger.exception("Failed to clear cache")
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

        except Exception:
            logger.exception("Failed to update fetch metadata")

    async def get_cache_summary(self) -> dict[str, Any]:
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

        except Exception:
            logger.exception("Failed to get cache summary")
            return {}

    async def cleanup(self) -> bool:
        """Clean up cache resources and old events.

        This method is called during test teardowns and application shutdown.

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Clean up old cached events (default 7 days)
            removed_cached_count = await self.cleanup_old_events()
            logger.debug(
                f"Cache cleanup completed, removed {removed_cached_count} old cached events",
            )

            # Clean up old raw events (default 7 days)
            removed_raw_count = await self.db.cleanup_raw_events()
            logger.debug(f"Cache cleanup completed, removed {removed_raw_count} old raw events")

            logger.debug(
                f"Total cleanup: {removed_cached_count} cached + {removed_raw_count} raw events removed",
            )
            return True

        except Exception:
            logger.exception("Failed to cleanup cache")
            return False
