"""RRULE expansion logic for CalendarBot Lite ICS parser."""

# ruff: noqa: I001
import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, UTC
import logging
import time
from typing import Any, Optional
from collections.abc import AsyncIterator
import uuid

from dateutil.rrule import rrulestr, rruleset

from .lite_models import LiteCalendarEvent, LiteDateTimeInfo

logger = logging.getLogger(__name__)


@dataclass
class RRuleExpanderConfig:
    """Configuration for RRULE expansion.

    Consolidates all RRULE-related settings with explicit defaults.
    """

    # Worker pool settings
    rrule_worker_concurrency: int = 1
    max_occurrences_per_rule: int = 250
    expansion_days_window: int = 365
    expansion_time_budget_ms_per_rule: int = 200
    expansion_yield_frequency: int = 50

    # Legacy expander settings
    rrule_expansion_days: int = 365
    enable_rrule_expansion: bool = True

    @classmethod
    def from_settings(cls, settings: Any) -> "RRuleExpanderConfig":
        """Extract RRULE configuration from settings object.

        Args:
            settings: Configuration object with RRULE settings

        Returns:
            RRuleExpanderConfig with values from settings or defaults
        """
        return cls(
            rrule_worker_concurrency=getattr(settings, "rrule_worker_concurrency", 1),
            max_occurrences_per_rule=getattr(settings, "max_occurrences_per_rule", 250),
            expansion_days_window=getattr(settings, "expansion_days_window", 365),
            expansion_time_budget_ms_per_rule=getattr(settings, "expansion_time_budget_ms_per_rule", 200),
            expansion_yield_frequency=getattr(settings, "expansion_yield_frequency", 50),
            rrule_expansion_days=getattr(settings, "rrule_expansion_days", 365),
            enable_rrule_expansion=getattr(settings, "enable_rrule_expansion", True),
        )


class RRuleWorkerPool:
    """Async worker pool for RRULE expansion to maintain responsive Pi Zero 2W performance.

    Implements bounded concurrency and cooperative multitasking for CPU-intensive RRULE expansion.
    """

    def __init__(self, settings: Any):
        """Initialize worker pool with configuration settings.

        Args:
            settings: Configuration object with worker pool settings
        """
        self.settings = settings

        # Extract configuration using centralized config class
        config = RRuleExpanderConfig.from_settings(settings)
        self.concurrency = config.rrule_worker_concurrency
        self.max_occurrences = config.max_occurrences_per_rule
        self.expansion_days = config.expansion_days_window
        self.time_budget_ms = config.expansion_time_budget_ms_per_rule
        self.yield_frequency = config.expansion_yield_frequency

        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._active_tasks: set[asyncio.Task] = set()

        logger.debug(
            "RRuleWorkerPool initialized: concurrency=%d, max_occurrences=%d, "
            "expansion_days=%d, time_budget_ms=%d, yield_frequency=%d",
            self.concurrency,
            self.max_occurrences,
            self.expansion_days,
            self.time_budget_ms,
            self.yield_frequency,
        )

    async def expand_rrule_stream(
        self,
        master_event: LiteCalendarEvent,
        rrule_string: str,
        exdates: Optional[list[str]] = None,
    ) -> AsyncIterator[LiteCalendarEvent]:
        """Expand RRULE pattern asynchronously with true streaming (no list materialization).

        Args:
            master_event: Master recurring event template
            rrule_string: RRULE pattern string
            exdates: Optional list of excluded dates

        Yields:
            Individual LiteCalendarEvent instances for each occurrence

        Raises:
            LiteRRuleExpansionError: If RRULE expansion fails
        """
        async with self._semaphore:
            event_subject = getattr(master_event, "subject", "")
            logger.debug(
                "Starting streaming RRULE expansion for event %s, subject: %r",
                getattr(master_event, "id", "<no-id>"),
                event_subject,
            )

            start_time = time.time()

            try:
                # Set up expansion window
                # For recurring events, we need to balance two concerns:
                # 1. RRULE semantics require starting from the event's original start date
                # 2. Old recurring events would generate too many past occurrences, hitting
                #    max_occurrences limit before reaching current dates (DATA LOSS bug)
                #
                # Solution: For infinite recurring events (no COUNT/UNTIL), start from
                # max(now - 7 days, master_start) to avoid the data loss bug.
                # For events with COUNT/UNTIL, always start from master_start to honor those constraints.

                # Get current time, respecting test overrides
                now = self._get_current_time()
                master_start = master_event.start.date_time

                # Normalize master_start to UTC for comparison
                if master_start.tzinfo is None:
                    master_start_utc = master_start.replace(tzinfo=UTC)
                else:
                    master_start_utc = master_start.astimezone(UTC)

                # Check if this is an infinite recurring event (no COUNT or UNTIL)
                # We check the RRULE string directly to avoid accessing private members
                is_infinite = 'COUNT=' not in rrule_string.upper() and 'UNTIL=' not in rrule_string.upper()
                
                # For infinite recurring events, start from recent past to avoid data loss
                # For finite events (COUNT/UNTIL), start from master_start to honor constraints
                if is_infinite and master_start_utc < (now - timedelta(days=7)):
                    # Old infinite recurring event: start from recent past
                    lookback_start = now - timedelta(days=7)
                    start_date = lookback_start
                    logger.debug(
                        "Using lookback window for old infinite recurring event: "
                        "master_start=%s, lookback_start=%s",
                        master_start_utc,
                        lookback_start
                    )
                else:
                    # Finite event or recent event: start from master_start
                    start_date = master_start_utc
                
                end_date = now + timedelta(days=self.expansion_days)

                # Parse RRULE and build rruleset with exdates
                rule_set = rruleset()

                parsed_rule = rrulestr(rrule_string, dtstart=master_event.start.date_time)
                if isinstance(parsed_rule, rruleset):
                    rule_set = parsed_rule
                else:
                    rule_set.rrule(parsed_rule)

                # Apply EXDATEs if provided
                logger.debug("EXDATE processing for event %s: exdates=%r", event_subject, exdates)
                if exdates:
                    logger.debug("Processing %d EXDATE entries", len(exdates))
                    for i, ex in enumerate(exdates):
                        try:
                            ex_dt = self._parse_datetime(ex)
                            logger.debug(
                                "EXDATE %d: raw='%s' parsed=%r tzinfo=%r",
                                i,
                                ex,
                                ex_dt,
                                ex_dt.tzinfo if hasattr(ex_dt, "tzinfo") else None,
                            )
                            if ex_dt.tzinfo is None:
                                ex_dt = ex_dt.replace(tzinfo=UTC)
                                logger.debug("EXDATE %d: added UTC timezone -> %r", i, ex_dt)
                            else:
                                ex_dt = ex_dt.astimezone(UTC)
                                logger.debug("EXDATE %d: converted to UTC -> %r", i, ex_dt)
                            rule_set.exdate(ex_dt)
                            logger.debug("EXDATE %d: successfully added to ruleset", i)
                        except Exception as ex_e:
                            logger.warning(f"Failed to parse EXDATE '{ex}': {ex_e}")
                            continue
                else:
                    logger.debug("No EXDATE entries provided for event %s", event_subject)

                # Normalize window datetimes
                start_window = (
                    start_date.replace(tzinfo=UTC)
                    if start_date.tzinfo is None
                    else start_date.astimezone(UTC)
                )
                end_window = (
                    end_date.replace(tzinfo=UTC)
                    if end_date.tzinfo is None
                    else end_date.astimezone(UTC)
                )

                # Stream occurrences directly from iterator without materialization
                event_count = 0
                for i, occurrence in enumerate(
                    rule_set.between(start_window, end_window, inc=True)
                ):
                    # Check time budget
                    elapsed_ms = (time.time() - start_time) * 1000
                    if elapsed_ms > self.time_budget_ms:
                        logger.warning(
                            "RRULE streaming exceeded time budget (%dms > %dms) after %d events",
                            elapsed_ms,
                            self.time_budget_ms,
                            i,
                        )
                        break

                    # Check occurrence limit
                    if i >= self.max_occurrences:
                        logger.debug(
                            "RRULE streaming limited to %d occurrences for Pi Zero 2W",
                            self.max_occurrences,
                        )
                        break

                    # Normalize occurrence
                    if not isinstance(occurrence, datetime):
                        continue
                    normalized_occurrence = (
                        occurrence.replace(tzinfo=UTC)
                        if occurrence.tzinfo is None
                        else occurrence.astimezone(UTC)
                    )

                    # Generate event instance
                    duration = master_event.end.date_time - master_event.start.date_time
                    end_time = normalized_occurrence + duration

                    instance_id = (
                        f"{master_event.id}_{normalized_occurrence.strftime('%Y%m%dT%H%M%S')}_"
                        f"{uuid.uuid4().hex[:8]}"
                    )

                    event = LiteCalendarEvent(
                        id=instance_id,
                        subject=master_event.subject,
                        body_preview=master_event.body_preview,
                        start=LiteDateTimeInfo(
                            date_time=normalized_occurrence,
                            time_zone=master_event.start.time_zone,
                        ),
                        end=LiteDateTimeInfo(
                            date_time=end_time,
                            time_zone=master_event.end.time_zone,
                        ),
                        is_all_day=master_event.is_all_day,
                        show_as=master_event.show_as,
                        is_cancelled=master_event.is_cancelled,
                        is_organizer=master_event.is_organizer,
                        location=master_event.location,
                        is_online_meeting=master_event.is_online_meeting,
                        online_meeting_url=master_event.online_meeting_url,
                        is_recurring=False,
                        is_expanded_instance=True,
                        rrule_master_uid=master_event.id,
                        last_modified_date_time=master_event.last_modified_date_time,
                    )

                    yield event
                    event_count += 1

                    # Cooperative yield to event loop
                    if i % self.yield_frequency == 0:
                        await asyncio.sleep(0)

                logger.debug(
                    "Streaming RRULE expansion completed: event=%s, yielded=%d events, elapsed=%.1fms",
                    getattr(master_event, "id", "<no-id>"),
                    event_count,
                    (time.time() - start_time) * 1000,
                )

            except Exception as e:
                logger.exception(
                    "Streaming RRULE expansion failed for event %s",
                    getattr(master_event, "id", "<no-id>"),
                )
                raise LiteRRuleExpansionError(f"Failed to stream RRULE expansion: {e}") from e

    async def expand_event_async(
        self,
        master_event: LiteCalendarEvent,
        rrule_string: str,
        exdates: Optional[list[str]] = None,
    ) -> AsyncIterator[LiteCalendarEvent]:
        """Expand RRULE pattern asynchronously with cooperative multitasking.

        Args:
            master_event: Master recurring event template
            rrule_string: RRULE pattern string
            exdates: Optional list of excluded dates

        Yields:
            Individual LiteCalendarEvent instances for each occurrence
        """
        # Delegate to the streaming implementation
        async for event in self.expand_rrule_stream(master_event, rrule_string, exdates):
            yield event

    def _get_current_time(self) -> datetime:
        """Get current time, respecting test time overrides.

        Returns:
            Current datetime in UTC timezone
        """
        import os

        # Check for test time override
        test_time = os.environ.get("CALENDARBOT_TEST_TIME")
        if test_time:
            try:
                from dateutil import parser
                # Parse the test time and convert to UTC
                dt = parser.parse(test_time)
                return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
            except Exception as e:
                logger.warning(f"Invalid CALENDARBOT_TEST_TIME: {test_time}, error: {e}")

        # Return current UTC time
        return datetime.now(UTC)

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string in various formats.

        Delegates to TimezoneParser for simplified, maintainable parsing.

        Args:
            datetime_str: Datetime string (ISO format, RRULE format, or timezone-aware EXDATE)

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If datetime format is invalid
        """
        from .lite_datetime_utils import TimezoneParser

        parser = TimezoneParser()
        return parser.parse_datetime(datetime_str)

    async def expand_event_to_list(
        self,
        master_event: LiteCalendarEvent,
        rrule_string: str,
        exdates: Optional[list[str]] = None,
    ) -> list[LiteCalendarEvent]:
        """Expand RRULE pattern and return as list.

        Args:
            master_event: Master recurring event template
            rrule_string: RRULE pattern string
            exdates: Optional list of excluded dates

        Returns:
            List of expanded LiteCalendarEvent instances
        """
        events = []
        async for event in self.expand_event_async(master_event, rrule_string, exdates):
            events.append(event)  # noqa: PERF401
        return events

    async def shutdown(self) -> None:
        """Shutdown worker pool and cancel active tasks."""
        logger.debug("Shutting down RRuleWorkerPool")

        # Cancel all active tasks
        for task in self._active_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        self._active_tasks.clear()
        logger.debug("RRuleWorkerPool shutdown complete")


# Global worker pool instance (created on first use)
_worker_pool: Optional[RRuleWorkerPool] = None


def get_worker_pool(settings: Any) -> RRuleWorkerPool:
    """Get or create the global RRULE worker pool.

    Args:
        settings: Configuration settings

    Returns:
        RRuleWorkerPool instance
    """
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = RRuleWorkerPool(settings)
    return _worker_pool


# Backwards-compatibility shims
# Some callsites (including older parser paths) expect these names:
# - expand_events_streaming (an async generator)
# - LiteRRuleExpander class with expand_event / expand_rrule methods
#
# Provide thin wrappers that delegate to the current worker-pool based implementation.

async def expand_events_streaming(
    events_with_rrules: list[tuple[Any, str, Optional[list[str]]]],
    settings: Any,
) -> AsyncIterator[Any]:
    """Compatibility async generator: yields expanded events for each (event, rrule, exdates).

    Delegates to get_worker_pool(settings).expand_rrule_stream for each tuple.
    """
    if not events_with_rrules:
        return
    pool = get_worker_pool(settings)
    for ev, rrule_str, exdates in events_with_rrules:
        try:
            async for inst in pool.expand_rrule_stream(ev, rrule_str, exdates):
                yield inst
        except Exception:
            logger.exception("expand_events_streaming: failed to stream expansion for %s", getattr(ev, "id", None))
            continue


class LiteRRuleExpander(RRuleWorkerPool):
    """RRULE expander with both async and sync interfaces.

    Provides:
    - Async streaming expansion (from RRuleWorkerPool)
    - Legacy sync methods for backward compatibility
    - Helper methods for parsing and event generation
    """

    def __init__(self, settings: Any):
        """Initialize expander with settings.

        Args:
            settings: Configuration object with RRULE expansion settings
        """
        super().__init__(settings)

        # Additional settings for legacy methods
        config = RRuleExpanderConfig.from_settings(settings)
        self.expansion_window_days = config.rrule_expansion_days
        self.enable_expansion = config.enable_rrule_expansion

    def expand_event(self, master_event: Any, rrule_string: str, exdates: Optional[list[str]] = None) -> list[Any]:
        """Legacy synchronous-style wrapper returning a list of expanded events.

        Delegates to expand_event_to_list via asyncio.run for callers that expect a blocking call.

        Note: Cannot be called from within an async context. Use expand_event_async() instead.
        """
        def check_not_in_event_loop() -> None:
            """Ensure we're not already in an event loop."""
            try:
                asyncio.get_running_loop()
                # If we get here, we're already in an event loop - can't use asyncio.run()
                raise RuntimeError(
                    "expand_event() cannot be called from async context. "
                    "Use expand_event_async() or await expand_event_to_list() instead."
                )
            except RuntimeError as e:
                # Check if this is the "no running event loop" error (which is what we want)
                if "no running event loop" not in str(e).lower():
                    # This is our custom error about being in async context
                    raise
                # No event loop running - safe to proceed

        try:
            check_not_in_event_loop()
            return asyncio.run(self.expand_event_to_list(master_event, rrule_string, exdates))
        except Exception:
            logger.exception("LiteRRuleExpander.expand_event failed for master %s", getattr(master_event, "id", None))
            return []

    def expand_rrule(self, master_event: Any, rrule_string: str, exdates: Optional[list[str]] = None) -> list[Any]:
        """Alias for expand_event to support older callers that used expand_rrule."""
        return self.expand_event(master_event, rrule_string, exdates)

    def parse_rrule_string(self, rrule_string: str) -> dict:
        """Parse RRULE string into components.

        Args:
            rrule_string: RRULE string (e.g. "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")

        Returns:
            Dictionary with parsed RRULE components

        Raises:
            LiteRRuleParseError: If RRULE string is invalid
        """
        if not rrule_string or not rrule_string.strip():
            raise LiteRRuleParseError("Empty RRULE string")

        try:
            # Split RRULE into key=value pairs
            parts = rrule_string.split(";")
            rrule_dict = {}

            for part in parts:
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "freq":
                    rrule_dict["freq"] = value.upper()  # type: ignore[assignment]
                elif key == "interval":
                    rrule_dict["interval"] = int(value)  # type: ignore[assignment]
                elif key == "byday":
                    # Split comma-separated BYDAY values
                    rrule_dict["byday"] = [day.strip().upper() for day in value.split(",")]  # type: ignore[assignment]
                elif key == "until":
                    # Parse UNTIL datetime
                    rrule_dict["until"] = self._parse_datetime(value)  # type: ignore[assignment]
                elif key == "count":
                    rrule_dict["count"] = int(value)  # type: ignore[assignment]
                else:
                    # Store other parameters for future extension
                    rrule_dict[key] = value

            # Validate required components
            if "freq" not in rrule_dict or not rrule_dict.get("freq"):
                raise LiteRRuleParseError("RRULE missing required FREQ parameter")

            return rrule_dict

        except (ValueError, AttributeError) as e:
            raise LiteRRuleParseError(f"Invalid RRULE format: {rrule_string}") from e

    def apply_exdates(
        self, occurrences: list[datetime], exdates: Optional[list[str]]
    ) -> list[datetime]:
        """Remove excluded dates from occurrence list.

        Args:
            occurrences: List of datetime occurrences
            exdates: List of excluded dates in ISO format

        Returns:
            Filtered list of occurrences with excluded dates removed
        """
        if not exdates:
            return occurrences

        excluded_datetimes = set()

        for exdate_str in exdates:
            try:
                exdate = self._parse_datetime(exdate_str)
                # Normalize to UTC for consistent comparison
                if exdate.tzinfo is None:
                    exdate = exdate.replace(tzinfo=UTC)
                else:
                    exdate = exdate.astimezone(UTC)
                excluded_datetimes.add(exdate)
            except Exception as e:
                logger.warning(f"Failed to parse EXDATE {exdate_str}: {e}")
                continue  # nosec B112 - skip malformed EXDATE, logged above

        # Filter out excluded datetimes with tolerance for minor time differences
        filtered_occurrences = []
        for occurrence in occurrences:
            # Normalize occurrence to UTC
            normalized_occurrence = (
                occurrence.astimezone(UTC) if occurrence.tzinfo else occurrence.replace(tzinfo=UTC)
            )

            # Check if this occurrence matches any excluded datetime (within 1 minute tolerance)
            is_excluded = any(
                abs((normalized_occurrence - excluded_dt).total_seconds()) < 60
                for excluded_dt in excluded_datetimes
            )

            if not is_excluded:
                filtered_occurrences.append(occurrence)

        logger.debug(f"Filtered {len(occurrences) - len(filtered_occurrences)} excluded datetimes")
        return filtered_occurrences

    def generate_event_instances(
        self,
        master_event: LiteCalendarEvent,
        occurrences: list[datetime],
    ) -> list[LiteCalendarEvent]:
        """Generate LiteCalendarEvent instances for each occurrence.

        Args:
            master_event: Master recurring event template
            occurrences: List of datetime occurrences

        Returns:
            List of LiteCalendarEvent instances
        """
        events = []

        for occurrence in occurrences:
            # Calculate event duration
            duration = master_event.end.date_time - master_event.start.date_time
            end_time = occurrence + duration

            # Create unique ID for this instance
            instance_id = (
                f"{master_event.id}_{occurrence.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
            )

            # Create new event instance
            event = LiteCalendarEvent(
                id=instance_id,
                subject=master_event.subject,
                body_preview=master_event.body_preview,
                start=LiteDateTimeInfo(
                    date_time=occurrence,
                    time_zone=master_event.start.time_zone,
                ),
                end=LiteDateTimeInfo(
                    date_time=end_time,
                    time_zone=master_event.end.time_zone,
                ),
                is_all_day=master_event.is_all_day,
                show_as=master_event.show_as,
                is_cancelled=master_event.is_cancelled,
                is_organizer=master_event.is_organizer,
                location=master_event.location,
                is_online_meeting=master_event.is_online_meeting,
                online_meeting_url=master_event.online_meeting_url,
                is_recurring=False,  # Instances are not recurring
                is_expanded_instance=True,  # Mark as expanded
                rrule_master_uid=master_event.id,  # Reference to master
                last_modified_date_time=master_event.last_modified_date_time,
            )

            events.append(event)

        return events


async def expand_events_async(
    events_with_rrules: list[tuple[Any, str, Optional[list[str]]]],
    settings: Any,
) -> list[Any]:
    """Expand multiple events with RRULE patterns using streaming worker pool.

    Args:
        events_with_rrules: List of (event, rrule_string, exdates) tuples
        settings: Configuration settings

    Returns:
        List of all expanded events (flattened)
    """
    if not events_with_rrules:
        return []

    worker_pool = get_worker_pool(settings)
    all_expanded = []

    # Process events with streaming consumption to avoid memory spikes
    for i, (event, rrule_str, exdates) in enumerate(events_with_rrules):
        try:
            # Stream events one by one for incremental memory usage
            async for expanded_event in worker_pool.expand_rrule_stream(event, rrule_str, exdates):
                all_expanded.append(expanded_event)

                # Yield control periodically for large expansions
                if len(all_expanded) % 50 == 0:
                    await asyncio.sleep(0)

        except Exception as ex:
            logger.warning("RRULE expansion failed for event %d: %s", i, ex)
            continue

    return all_expanded


class LiteRRuleExpansionError(Exception):
    """Base exception for RRULE expansion errors."""


class LiteRRuleParseError(LiteRRuleExpansionError):
    """Error parsing RRULE string."""


class RRuleOrchestrator:
    """Centralized RRULE expansion orchestration.

    Consolidates all RRULE-related logic including:
    - Building UID mappings between components and events
    - Collecting expansion candidates with RRULE patterns
    - Handling EXDATE properties and RECURRENCE-ID instances
    - Executing async RRULE expansion via worker pool

    This class provides a clean interface for ICS parsers to expand recurring events
    without needing to understand the low-level expansion mechanics.
    """

    def __init__(self, settings: Any, event_parser: Any):
        """Initialize RRULE orchestrator.

        Args:
            settings: Configuration settings for expansion (rrule_expansion_days, etc.)
            event_parser: Event parser instance for collecting EXDATE properties
        """
        self.settings = settings
        self.event_parser = event_parser
        self.worker_pool = get_worker_pool(settings)

    def expand_recurring_events(
        self,
        events: list[Any],
        raw_components: list[Any],
    ) -> list[Any]:
        """Expand recurring events using RRULE patterns.

        This is the main entry point for RRULE expansion. It:
        1. Builds mappings of UIDs to components and events
        2. Collects expansion candidates (events with RRULE)
        3. Executes async RRULE expansion

        Args:
            events: List of parsed calendar events
            raw_components: List of raw iCalendar components for RRULE extraction

        Returns:
            List of expanded event instances
        """
        # Phase 1: Build mappings of UIDs to components and events
        component_map, events_by_id = self._build_component_and_event_maps(
            events, raw_components
        )

        # Phase 2: Collect RRULE expansion candidates
        candidates = self._collect_expansion_candidates(
            component_map, events_by_id, events
        )

        # Phase 3: Execute async RRULE expansion
        return self._execute_expansion(candidates)


    def _build_component_and_event_maps(
        self,
        events: list[Any],
        raw_components: list[Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Build mappings of UIDs to components and parsed events.

        Creates two maps prioritizing recurring masters over instances:
        1. component_map: UID -> raw iCalendar component
        2. events_by_id: UID -> parsed LiteCalendarEvent

        Args:
            events: List of parsed calendar events
            raw_components: List of raw iCalendar components

        Returns:
            Tuple of (component_map, events_by_id)
        """
        # Build component map: UID -> component, prioritizing recurring masters
        component_map = {}
        for component in raw_components:
            try:
                comp_uid = str(component.get("UID"))
            except Exception:
                comp_uid = None
            if not comp_uid:
                continue

            # If we haven't seen this UID yet, store it
            if comp_uid not in component_map:
                component_map[comp_uid] = component
            else:
                # Prefer a component that contains an RRULE (recurring master) over instances
                existing = component_map[comp_uid]
                existing_has_rrule = bool(existing.get("RRULE"))
                current_has_rrule = bool(component.get("RRULE"))
                if not existing_has_rrule and current_has_rrule:
                    component_map[comp_uid] = component

        # Build events map: UID -> parsed event, prioritizing recurring masters
        events_by_id: dict[str, Any] = {}
        for e in events:
            event_id = getattr(e, "id", None)
            if not event_id:
                continue

            # If we haven't seen this UID yet, add it
            if event_id not in events_by_id:
                events_by_id[event_id] = e
            else:
                # Prefer recurring masters over instances
                existing = events_by_id[event_id]
                if not getattr(existing, "is_recurring", False) and getattr(e, "is_recurring", False):
                    events_by_id[event_id] = e

        return component_map, events_by_id

    def _collect_expansion_candidates(
        self,
        component_map: dict[str, Any],
        events_by_id: dict[str, Any],
        events: list[Any],
    ) -> list[tuple[Any, str, Optional[list[str]]]]:
        """Collect RRULE expansion candidates from components.

        For each component with an RRULE, creates a candidate tuple containing:
        - The event object (parsed or synthesized)
        - The RRULE string
        - Optional list of EXDATE strings

        Args:
            component_map: Mapping of UID -> raw component
            events_by_id: Mapping of UID -> parsed event
            events: List of all parsed events (for RECURRENCE-ID detection)

        Returns:
            List of (event, rrule_string, exdates) tuples for expansion
        """
        candidates: list[tuple[Any, str, Optional[list[str]]]] = []

        for comp_uid, component in component_map.items():
            try:
                # Only consider components that contain an RRULE
                if not component.get("RRULE"):
                    continue

                # Extract RRULE property robustly
                rrule_prop = component.get("RRULE")
                if hasattr(rrule_prop, "to_ical"):
                    rrule_string = rrule_prop.to_ical().decode("utf-8")
                else:
                    rrule_string = str(rrule_prop)

                # Collect EXDATE properties
                exdates = self._collect_exdates(component, events, comp_uid)

                # Get or create candidate event
                candidate_event = self._get_or_create_candidate_event(
                    comp_uid, component, events_by_id
                )

                candidates.append(
                    (candidate_event, rrule_string, exdates if exdates else None)
                )
            except Exception as e:
                logger.warning("Failed to build RRULE candidate for UID=%s: %s", comp_uid, e)
                continue

        return candidates

    def _collect_exdates(
        self,
        component: Any,
        events: list[Any],
        comp_uid: str,
    ) -> list[str]:
        """Collect EXDATE properties and RECURRENCE-ID instances.

        Args:
            component: Raw iCalendar component
            events: List of all parsed events
            comp_uid: Component UID

        Returns:
            List of EXDATE strings (including RECURRENCE-IDs)
        """
        # Collect EXDATE props using event parser helper
        exdate_props = self.event_parser._collect_exdate_props(component) or []  # noqa: SLF001
        exdates: list[str] = []

        if exdate_props:
            if not isinstance(exdate_props, list):
                exdate_props = [exdate_props]
            for exdate in exdate_props:
                try:
                    if hasattr(exdate, "to_ical"):
                        exdate_str = exdate.to_ical().decode("utf-8")
                        tzid = (
                            exdate.params["TZID"]
                            if hasattr(exdate, "params") and "TZID" in exdate.params
                            else None
                        )
                        parts = [p.strip() for p in exdate_str.split(",") if p.strip()]
                        exdates.extend([f"TZID={tzid}:{p}" if tzid else p for p in parts])
                    else:
                        exdate_str = str(exdate)
                        exdates.extend([q.strip() for q in exdate_str.split(",") if q.strip()])
                except Exception:
                    continue  # nosec B112 - skip malformed EXDATE values

        # Add RECURRENCE-ID instances to exdates to exclude them from normal expansion
        for event in events:
            if (getattr(event, "id", None) == comp_uid and
                hasattr(event, "recurrence_id") and event.recurrence_id):
                exdates.append(event.recurrence_id)
                logger.debug(
                    f"Adding RECURRENCE-ID to exdates for {comp_uid}: {event.recurrence_id}"
                )

        return exdates

    def _get_or_create_candidate_event(
        self,
        comp_uid: str,
        component: Any,
        events_by_id: dict[str, Any],
    ) -> Any:
        """Get parsed event or create synthetic candidate for expansion.

        Args:
            comp_uid: Component UID
            component: Raw iCalendar component
            events_by_id: Mapping of UID -> parsed event

        Returns:
            Event object (parsed or synthetic _SimpleEvent)
        """
        # Prefer using the parsed event if present (has richer metadata)
        parsed_event = events_by_id.get(comp_uid)
        if parsed_event:
            return parsed_event

        # Import helper classes from lite_parser
        from .lite_parser import _SimpleEvent, _DateTimeWrapper

        # Synthesize a lightweight event object with minimal attributes
        candidate_event = _SimpleEvent()
        
        # Initialize is_all_day flag (will be set to True if date-only event detected)
        candidate_event.is_all_day = False

        # Decode DTSTART/DTEND from the raw component
        try:
            dtstart_raw = component.decoded("DTSTART")
            dtend_raw = component.decoded("DTEND") if "DTEND" in component else None

            # Wrap start and end in simple containers expected by expander
            if isinstance(dtstart_raw, datetime):
                candidate_event.start = _DateTimeWrapper(dtstart_raw)
            elif isinstance(dtstart_raw, date):
                # Handle date-only events (all-day events like birthdays, holidays)
                # Convert date to datetime at midnight UTC
                dt = datetime.combine(dtstart_raw, datetime.min.time())
                candidate_event.start = _DateTimeWrapper(dt.replace(tzinfo=UTC))
                candidate_event.is_all_day = True
            else:
                # fallback parse string - try both datetime and date formats
                dt_str = str(component.get("DTSTART"))
                try:
                    # Try datetime format first
                    dt = datetime.strptime(dt_str.rstrip("Z"), "%Y%m%dT%H%M%S")
                    candidate_event.start = _DateTimeWrapper(dt.replace(tzinfo=UTC))
                except ValueError:
                    # Try date format for all-day events
                    dt = datetime.strptime(dt_str, "%Y%m%d")
                    candidate_event.start = _DateTimeWrapper(dt.replace(tzinfo=UTC))
                    candidate_event.is_all_day = True

            if dtend_raw and isinstance(dtend_raw, datetime):
                candidate_event.end = _DateTimeWrapper(dtend_raw)
            elif dtend_raw and isinstance(dtend_raw, date):
                # Handle date-only end for all-day events
                dt = datetime.combine(dtend_raw, datetime.min.time())
                candidate_event.end = _DateTimeWrapper(dt.replace(tzinfo=UTC))
            elif dtend_raw:
                dt_str = str(component.get("DTEND"))
                try:
                    # Try datetime format first
                    dt = datetime.strptime(dt_str.rstrip("Z"), "%Y%m%dT%H%M%S")
                    candidate_event.end = _DateTimeWrapper(dt.replace(tzinfo=UTC))
                except ValueError:
                    # Try date format for all-day events
                    dt = datetime.strptime(dt_str, "%Y%m%d")
                    candidate_event.end = _DateTimeWrapper(dt.replace(tzinfo=UTC))
            else:
                # If DTEND missing, approximate using duration
                # For all-day events, use 1 day; for timed events, use 1 hour
                duration = timedelta(days=1) if candidate_event.is_all_day else timedelta(hours=1)
                candidate_event.end = _DateTimeWrapper(
                    candidate_event.start.date_time + duration
                )
        except Exception:
            # Last-resort defaults
            now = datetime.now(UTC)
            candidate_event.start = _DateTimeWrapper(now)
            candidate_event.end = _DateTimeWrapper(now + timedelta(hours=1))

        # Minimal metadata to make expansion operate
        candidate_event.id = comp_uid
        candidate_event.subject = (
            str(component.get("SUMMARY", "")) if component.get("SUMMARY") else ""
        )
        candidate_event.body_preview = ""  # Default empty body preview
        candidate_event.is_recurring = True
        # Note: is_all_day is already set during date/datetime parsing
        candidate_event.is_cancelled = False
        candidate_event.is_online_meeting = False
        candidate_event.online_meeting_url = None
        candidate_event.last_modified_date_time = None

        return candidate_event

    def _execute_expansion(
        self,
        candidates: list[tuple[Any, str, Optional[list[str]]]],
    ) -> list[Any]:
        """Execute RRULE expansion for candidates using async streaming.

        Now uses AsyncOrchestrator to handle event loop detection and execution.

        Args:
            candidates: List of (event, rrule_string, exdates) tuples

        Returns:
            List of expanded event instances
        """
        expanded_instances: list[dict[str, Any]] = []

        if not candidates:
            return expanded_instances

        # Import AsyncOrchestrator for centralized async execution
        from .async_utils import get_global_orchestrator

        orchestrator = get_global_orchestrator()

        # Define async collector
        async def _collect_expansions(cands):  # type: ignore[no-untyped-def]
            instances = []
            try:
                instances.extend(
                    [
                        inst
                        async for inst in expand_events_streaming(cands, self.settings)
                    ]
                )
            except Exception as _e:
                logger.exception("expand_events_streaming failed")
            return instances

        # Execute the async collector using orchestrator from sync context
        try:
            instances = orchestrator.run_coroutine_from_sync(
                lambda: _collect_expansions(candidates),
                timeout=None  # No timeout for RRULE expansion
            )
        except Exception as e:
            logger.warning("Failed to expand RRULE candidates: %s", e)
            instances = []

        # Collect expanded instances
        for inst in instances:
            try:
                expanded_instances.append(inst)
            except Exception:
                # Defensive: skip malformed instances
                continue  # nosec B112 - skip malformed expanded instances

        return expanded_instances
