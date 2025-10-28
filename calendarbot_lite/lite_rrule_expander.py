"""RRULE expansion logic for CalendarBot Lite ICS parser."""

# ruff: noqa: I001
import asyncio
import contextlib
from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any, Optional
from collections.abc import AsyncIterator
import uuid

from dateutil.rrule import (
    DAILY,
    HOURLY,
    MINUTELY,
    MONTHLY,
    SECONDLY,
    WEEKLY,
    YEARLY,
    rrule,
    rrulestr,
    rruleset,
)

from .lite_models import LiteCalendarEvent, LiteDateTimeInfo

UTC = timezone.utc

logger = logging.getLogger(__name__)


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
        self.concurrency = getattr(settings, "rrule_worker_concurrency", 1)
        self.max_occurrences = getattr(settings, "max_occurrences_per_rule", 250)
        self.expansion_days = getattr(settings, "expansion_days_window", 365)
        self.time_budget_ms = getattr(settings, "expansion_time_budget_ms_per_rule", 200)
        self.yield_frequency = getattr(settings, "expansion_yield_frequency", 50)

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

            # Check if this might be the missing Ani/Ben recurring event
            start_time = time.time()

            try:
                # Set up expansion window
                start_date = master_event.start.date_time
                end_date = start_date + timedelta(days=self.expansion_days)

                # Parse RRULE and build rruleset with exdates
                rule_set = rruleset()

                try:
                    parsed_rule = rrulestr(rrule_string, dtstart=master_event.start.date_time)
                    if isinstance(parsed_rule, rruleset):
                        rule_set = parsed_rule
                    else:
                        rule_set.rrule(parsed_rule)
                except Exception:
                    # Fallback parsing
                    parsed_rule = rrulestr(rrule_string, dtstart=master_event.start.date_time)
                    if isinstance(parsed_rule, rruleset):
                        rule_set = parsed_rule
                    else:
                        rule_set.rrule(parsed_rule)

                # Apply EXDATEs if provided
                if exdates:
                    for ex in exdates:
                        try:
                            ex_dt = self._parse_datetime_for_streaming(ex)
                            if ex_dt.tzinfo is None:
                                ex_dt = ex_dt.replace(tzinfo=UTC)
                            else:
                                ex_dt = ex_dt.astimezone(UTC)
                            rule_set.exdate(ex_dt)
                        except Exception as ex_e:  # noqa: PERF203
                            logger.warning(f"Failed to parse EXDATE '{ex}': {ex_e}")
                            continue

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
                        logger.warning(
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

    def _parse_datetime_for_streaming(self, datetime_str: str) -> datetime:
        """Parse datetime string for streaming operations (lightweight version).

        Args:
            datetime_str: Datetime string in various formats

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If datetime format is invalid
        """
        # Handle timezone-aware EXDATE format: TZID=timezone:YYYYMMDDTHHMMSS
        if datetime_str.startswith("TZID="):
            try:
                _tzid_part, dt_part = datetime_str.split(":", 1)
                dt_part_clean = dt_part.rstrip("Z")
                dt = datetime.strptime(dt_part_clean, "%Y%m%dT%H%M%S")

                if dt_part.endswith("Z"):
                    return dt.replace(tzinfo=UTC)
                # For streaming, assume UTC for performance
                return dt.replace(tzinfo=UTC)
            except Exception:
                # Fall through to standard parsing
                pass

        # Standard parsing for streaming (optimized)
        dt_str = datetime_str.rstrip("Z")

        # Try most common format first
        try:
            dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
            if datetime_str.endswith("Z"):
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            pass

        # Fallback to other formats
        formats = ["%Y-%m-%dT%H:%M:%S", "%Y%m%d", "%Y-%m-%d"]
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str, fmt)
                if datetime_str.endswith("Z"):
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:  # noqa: PERF203
                continue

        raise ValueError(f"Unable to parse datetime: {datetime_str}")

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
    global _worker_pool  # noqa: PLW0603
    if _worker_pool is None:
        _worker_pool = RRuleWorkerPool(settings)
    return _worker_pool


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

        except Exception as ex:  # noqa: PERF203
            logger.warning("RRULE expansion failed for event %d: %s", i, ex)
            continue

    return all_expanded


async def expand_events_streaming(
    events_with_rrules: list[tuple[Any, str, Optional[list[str]]]],
    settings: Any,
) -> AsyncIterator[Any]:
    """Expand multiple events with RRULE patterns using pure streaming (no materialization).

    Args:
        events_with_rrules: List of (event, rrule_string, exdates) tuples
        settings: Configuration settings

    Yields:
        Individual expanded LiteCalendarEvent instances
    """
    if not events_with_rrules:
        return

    worker_pool = get_worker_pool(settings)

    # Stream events without materialization for maximum memory efficiency
    for i, (event, rrule_str, exdates) in enumerate(events_with_rrules):
        try:
            # Stream events directly without intermediate collection
            async for expanded_event in worker_pool.expand_rrule_stream(event, rrule_str, exdates):
                yield expanded_event

        except Exception as ex:  # noqa: PERF203
            logger.warning("RRULE streaming expansion failed for event %d: %s", i, ex)
            continue


class LiteRRuleExpansionError(Exception):
    """Base exception for RRULE expansion errors."""


class LiteRRuleParseError(LiteRRuleExpansionError):
    """Error parsing RRULE string."""


class LiteRRuleExpander:
    """Client-side RRULE expansion for CalendarBot Lite.

    This class handles expansion of RRULE patterns into individual LiteCalendarEvent
    instances using python-dateutil. It supports WEEKLY patterns with EXDATE
    exclusions and proper timezone handling.
    """

    def __init__(self, settings: object):
        """Initialize LiteRRuleExpander with settings.

        Args:
            settings: CalendarBot configuration settings object
        """
        self.settings = settings
        self.expansion_window_days = getattr(settings, "rrule_expansion_days", 365)
        self.enable_expansion = getattr(settings, "enable_rrule_expansion", True)

    def expand_rrule(
        self,
        master_event: LiteCalendarEvent,
        rrule_string: str,
        exdates: Optional[list[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[LiteCalendarEvent]:
        """Expand RRULE pattern into individual event instances using dateutil's rruleset/rrulestr.

        This implementation defers full RRULE parsing to dateutil to preserve all
        standard RRULE fields (BYDAY, BYMONTHDAY, BYMONTH, UNTIL, COUNT, etc.)
        and uses an rruleset so EXDATE exclusions are applied precisely.
        """
        if not self.enable_expansion:
            return []

        try:
            # Establish expansion window
            if start_date is None:
                start_date = master_event.start.date_time
            if end_date is None:
                # Preserve timezone awareness when creating the expansion window.
                # Previously we deliberately stripped tzinfo which produced
                # offset-naive end_date and caused comparisons to fail inside
                # dateutil. Use timezone-aware arithmetic instead.
                end_date = start_date + timedelta(days=self.expansion_window_days)

            # Build an rruleset and parse the RRULE with the correct dtstart
            rule_set = rruleset()

            try:
                parsed_rule = rrulestr(rrule_string, dtstart=master_event.start.date_time)
                # rrulestr can return either an rrule or an rruleset.
                # If it's an rruleset already, use it directly; otherwise add the rrule to our set.
                if isinstance(parsed_rule, rruleset):
                    rule_set = parsed_rule
                else:
                    rule_set.rrule(parsed_rule)
            except Exception:
                # Fallback: try parsing again and treat result similarly
                parsed_rule = rrulestr(rrule_string, dtstart=master_event.start.date_time)
                if isinstance(parsed_rule, rruleset):
                    rule_set = parsed_rule
                else:
                    rule_set.rrule(parsed_rule)

            # Defensive normalization of internal rruleset/rrule datetimes:
            # dateutil may store naive datetimes inside the parsed rrule/rruleset.
            # Normalize internal dt values (dtstart, _until, _exdate items) to timezone-aware UTC
            try:
                # If rule_set is a rruleset instance, it may contain internal lists of exdates and rrules
                exlist = getattr(rule_set, "_exdate", None)
                if exlist:
                    normalized_exlist = []
                    for ex in exlist:
                        try:
                            if ex is None:
                                continue
                            if ex.tzinfo is None:
                                normalized_ex = ex.replace(tzinfo=UTC)
                            else:
                                normalized_ex = ex.astimezone(UTC)
                            normalized_exlist.append(normalized_ex)
                        except Exception:
                            normalized_exlist.append(ex)
                    # Assign normalized exdate list; suppress assignment errors
                    with contextlib.suppress(Exception):
                        rule_set._exdate = normalized_exlist  # type: ignore[attr-defined]  # noqa: SLF001

                # Normalize any rrules contained in the set
                rrules_internal = getattr(rule_set, "_rrule", None)
                if rrules_internal:
                    # Normalize dtstart/until for all internal rules (single try to avoid try/except in loop)
                    try:
                        for rr in rrules_internal:
                            dtstart = getattr(rr, "_dtstart", None)
                            if dtstart is not None:
                                normalized_dtstart = (
                                    dtstart.replace(tzinfo=UTC)
                                    if dtstart.tzinfo is None
                                    else dtstart.astimezone(UTC)
                                )
                                rr._dtstart = normalized_dtstart  # type: ignore[attr-defined]  # noqa: SLF001
                            until = getattr(rr, "_until", None)
                            if until is not None:
                                normalized_until = (
                                    until.replace(tzinfo=UTC)
                                    if until.tzinfo is None
                                    else until.astimezone(UTC)
                                )
                                rr._until = normalized_until  # type: ignore[attr-defined]  # noqa: SLF001
                    except Exception:
                        # Defensive: continue if normalization fails for the group
                        pass
            except Exception:
                # Defensive: do not let normalization errors stop expansion; proceed and rely on later normalization
                logger.debug(
                    "RRULE expansion: internal normalization of parsed rule failed, continuing"
                )

            # Apply EXDATEs precisely by parsing each EXDATE string and normalizing to UTC-aware datetimes
            if exdates:
                for ex in exdates:
                    try:
                        ex_dt = self._parse_datetime(ex)
                        # Normalize EXDATE to timezone-aware UTC to avoid naive/aware comparisons inside dateutil
                        if ex_dt.tzinfo is None:
                            ex_dt = ex_dt.replace(tzinfo=UTC)
                        else:
                            ex_dt = ex_dt.astimezone(UTC)
                        rule_set.exdate(ex_dt)
                    except Exception as ex_e:  # noqa: PERF203
                        logger.warning(f"Failed to parse or normalize EXDATE '{ex}': {ex_e}")
                        continue

            # Normalize window datetimes to timezone-aware UTC to avoid
            # "can't compare offset-naive and offset-aware datetimes" errors
            def _ensure_utc_aware(dt: datetime) -> datetime:
                if dt is None:
                    return dt
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=UTC)
                return dt.astimezone(UTC)

            start_window = _ensure_utc_aware(start_date)
            end_window = _ensure_utc_aware(end_date)

            # Collect occurrences within the date window
            try:
                # Debug: log RRULE expansion inputs
                # TARGETED DEBUG: Enhanced logging for Ani/Ben meeting
                event_subject = getattr(master_event, "subject", "")
                is_ani_ben_meeting = "Ani" in str(event_subject) and "Ben" in str(event_subject)

                if is_ani_ben_meeting:
                    logger.info("🔍 TARGETED DEBUG: Ani/Ben meeting RRULE expansion:")
                    logger.info("  Subject: %r", event_subject)
                    logger.info("  UID: %s", getattr(master_event, "id", "<no-id>"))
                    logger.info(
                        "  Master event start: %s", master_event.start.date_time.isoformat()
                    )
                    logger.info(
                        "  Master event timezone: %s",
                        getattr(master_event.start.date_time, "tzinfo", "None"),
                    )
                    logger.info("  RRULE: %s", rrule_string)
                    logger.info("  EXDATEs: %s", exdates)
                    logger.info(
                        "  Expansion window start: %s",
                        start_window.isoformat() if start_window else "<none>",
                    )
                    logger.info(
                        "  Expansion window end: %s",
                        end_window.isoformat() if end_window else "<none>",
                    )

                    # Check if target time (8:30 AM PDT on 2025-10-27) is in expansion window
                    import zoneinfo
                    from datetime import datetime

                    target_time_pdt = datetime(2025, 10, 27, 8, 30).replace(
                        tzinfo=zoneinfo.ZoneInfo("America/Los_Angeles")
                    )
                    target_time_utc = target_time_pdt.astimezone(UTC)
                    logger.info(
                        "  Target time we're looking for (PDT): %s", target_time_pdt.isoformat()
                    )
                    logger.info(
                        "  Target time we're looking for (UTC): %s", target_time_utc.isoformat()
                    )

                    if start_window and end_window:
                        in_window = start_window <= target_time_utc <= end_window
                        logger.info("  Is target time in expansion window? %s", in_window)
                        if not in_window:
                            logger.warning("  ❌ TARGET TIME IS OUTSIDE EXPANSION WINDOW!")
                else:
                    logger.debug(
                        "RRULE expansion: uid=%s dtstart=%s rrule=%s exdates=%s window_start=%s window_end=%s",
                        getattr(master_event, "id", "<no-id>"),
                        master_event.start.date_time.isoformat(),
                        rrule_string,
                        exdates,
                        start_window.isoformat() if start_window else "<none>",
                        end_window.isoformat() if end_window else "<none>",
                    )
            except Exception:
                logger.debug("RRULE expansion: failed to serialize debug metadata for master_event")

            raw_occurrences = list(rule_set.between(start_window, end_window, inc=True))

            # Normalize occurrences to timezone-aware UTC to avoid naive/aware comparison issues
            occurrences = []
            for occ in raw_occurrences:
                # Normalize occurrences deterministically; avoid try/except in loop for performance
                if not isinstance(occ, datetime):
                    continue
                normalized = occ.replace(tzinfo=UTC) if occ.tzinfo is None else occ.astimezone(UTC)
                occurrences.append(normalized)

            # Debug: log number of occurrences and first few values
            try:
                sample_occurrences = [dt.isoformat() for dt in occurrences[:10]]
                logger.debug(
                    "RRULE expansion result: uid=%s occurrences=%d sample=%s",
                    getattr(master_event, "id", "<no-id>"),
                    len(occurrences),
                    sample_occurrences,
                )
            except Exception:
                logger.debug(
                    "RRULE expansion: failed to serialize occurrence datetimes for logging"
                )

            # Limit number of occurrences
            max_occurrences = getattr(self.settings, "rrule_max_occurrences", 1000)
            if len(occurrences) > max_occurrences:
                logger.warning(f"Limiting RRULE expansion to {max_occurrences} occurrences")
                occurrences = occurrences[:max_occurrences]

            # Generate LiteCalendarEvent instances
            return self.generate_event_instances(master_event, occurrences)

        except Exception as e:
            logger.exception("RRULE expansion failed")
            raise LiteRRuleExpansionError(f"Failed to expand RRULE: {e}") from e

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
            if "freq" not in rrule_dict:
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
            except Exception as e:  # noqa: PERF203
                logger.warning(f"Failed to parse EXDATE {exdate_str}: {e}")
                continue

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

    def _generate_occurrences_streaming(
        self,
        master_event: LiteCalendarEvent,
        rrule_params: dict,
        start_date: datetime,
        end_date: datetime,
        max_occurrences: int = 250,
        time_budget_ms: int = 200,
    ) -> list[datetime]:
        """Generate occurrence datetimes using dateutil.rrule with Pi Zero 2W limits.

        Args:
            master_event: Master event with start time
            rrule_params: Parsed RRULE parameters
            start_date: Window start (unused in current implementation)
            end_date: Window end (unused in current implementation)
            max_occurrences: Maximum occurrences to generate (Pi Zero 2W limit)
            time_budget_ms: Time budget in milliseconds (Pi Zero 2W limit)

        Returns:
            List of occurrence datetimes (limited by Pi Zero 2W constraints)
        """
        try:
            start_time = time.time()

            # Map frequency to dateutil constants
            freq_map = {
                "SECONDLY": SECONDLY,
                "MINUTELY": MINUTELY,
                "HOURLY": HOURLY,
                "DAILY": DAILY,
                "WEEKLY": WEEKLY,
                "MONTHLY": MONTHLY,
                "YEARLY": YEARLY,
            }

            freq = freq_map.get(rrule_params["freq"])
            if freq is None:
                raise LiteRRuleExpansionError(f"Unsupported frequency: {rrule_params['freq']}")  # noqa: TRY301

            # Map weekdays to dateutil constants
            weekday_map = {
                "MO": 0,
                "TU": 1,
                "WE": 2,
                "TH": 3,
                "FR": 4,
                "SA": 5,
                "SU": 6,
            }

            # Build rrule parameters
            kwargs = {
                "freq": freq,
                "dtstart": master_event.start.date_time,
                "interval": rrule_params.get("interval", 1),
            }

            # Add UNTIL or COUNT if specified
            if "until" in rrule_params:
                kwargs["until"] = rrule_params["until"]
            elif "count" in rrule_params:
                kwargs["count"] = rrule_params["count"]

            # Add BYDAY if specified
            if "byday" in rrule_params:
                byweekday = [
                    weekday_map[day] for day in rrule_params["byday"] if day in weekday_map
                ]
                if byweekday:
                    kwargs["byweekday"] = byweekday

            # Generate occurrences using iterator to avoid memory spike
            rule = rrule(**kwargs)
            occurrences = []

            for i, occurrence in enumerate(rule):
                # Check time budget
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms > time_budget_ms:
                    logger.warning(
                        "RRULE occurrence generation exceeded time budget (%dms > %dms) after %d items",
                        elapsed_ms,
                        time_budget_ms,
                        i,
                    )
                    break

                # Check occurrence limit
                if i >= max_occurrences:
                    logger.warning(
                        "RRULE occurrence generation limited to %d occurrences for Pi Zero 2W",
                        max_occurrences,
                    )
                    break

                occurrences.append(occurrence)

            return occurrences

        except Exception as e:
            raise LiteRRuleExpansionError(f"Failed to generate occurrences: {e}") from e

    def _generate_occurrences(
        self,
        master_event: LiteCalendarEvent,
        rrule_params: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[datetime]:
        """Generate occurrence datetimes using dateutil.rrule.

        Args:
            master_event: Master event with start time
            rrule_params: Parsed RRULE parameters
            start_date: Window start (unused in current implementation)
            end_date: Window end (unused in current implementation)

        Returns:
            List of occurrence datetimes
        """
        # Use streaming version with Pi Zero 2W defaults
        max_occurrences = getattr(self.settings, "rrule_max_occurrences_per_rule", 250)
        time_budget_ms = getattr(self.settings, "expansion_time_budget_ms_per_rule", 200)

        return self._generate_occurrences_streaming(
            master_event,
            rrule_params,
            start_date,
            end_date,
            max_occurrences,
            time_budget_ms,
        )

    def _filter_by_date_range(
        self,
        occurrences: list[datetime],
        start_date: datetime,
        end_date: datetime,
    ) -> list[datetime]:
        """Filter occurrences by date range.

        Args:
            occurrences: List of occurrence datetimes
            start_date: Range start
            end_date: Range end

        Returns:
            Filtered list of occurrences
        """

        # Normalize timezone handling - convert all to same timezone awareness
        def normalize_datetime(dt: datetime) -> datetime:
            """Normalize datetime to timezone-aware UTC if needed."""
            if dt.tzinfo is None:
                # Naive datetime - assume UTC
                return dt.replace(tzinfo=UTC)
            return dt

        start_date_normalized = normalize_datetime(start_date)
        end_date_normalized = normalize_datetime(end_date)

        return [
            occurrence
            for occurrence in occurrences
            if start_date_normalized <= normalize_datetime(occurrence) <= end_date_normalized
        ]

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string in various formats.

        Args:
            datetime_str: Datetime string (ISO format, RRULE format, or timezone-aware EXDATE)

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If datetime format is invalid
        """
        # Handle timezone-aware EXDATE format: TZID=Pacific Standard Time:20250623T083000
        if datetime_str.startswith("TZID="):
            try:
                tzid_part, dt_part = datetime_str.split(":", 1)
                tzid = tzid_part.replace("TZID=", "").strip()

                # Handle "Z" suffix (UTC indicator)
                dt_part_clean = dt_part.rstrip("Z")

                # Parse the datetime part
                dt = datetime.strptime(dt_part_clean, "%Y%m%dT%H%M%S")

                # Handle special timezone cases
                if tzid == "UTC" or dt_part.endswith("Z"):
                    # UTC timezone - simple case
                    return dt.replace(tzinfo=UTC)
                # previous branch returned; use separate if to avoid unreachable elif warning
                timezone_name = "America/Los_Angeles" if tzid == "Pacific Standard Time" else tzid

                # Apply timezone and convert to UTC
                try:
                    # Try zoneinfo first (preferred)
                    from zoneinfo import ZoneInfo  # noqa: PLC0415 - deliberate runtime fallback import

                    tz = ZoneInfo(timezone_name)
                    dt_with_tz = dt.replace(tzinfo=tz)
                    return dt_with_tz.astimezone(UTC)
                except (ImportError, Exception):
                    try:
                        # Fallback to pytz
                        import pytz  # noqa: PLC0415 - deliberate runtime fallback import

                        tz = pytz.timezone(timezone_name)
                        dt_with_tz = tz.localize(dt)
                        return dt_with_tz.astimezone(UTC)
                    except Exception:
                        # Last fallback - assume UTC
                        logger.warning(f"Could not parse timezone {tzid}, assuming UTC")
                        return dt.replace(tzinfo=UTC)

            except Exception as e:
                logger.warning(f"Failed to parse timezone-aware EXDATE {datetime_str}: {e}")
                # Fall through to standard parsing

        # Remove timezone suffix for basic parsing
        dt_str = datetime_str.rstrip("Z")

        # Try various datetime formats
        formats = [
            "%Y%m%dT%H%M%S",  # 20250623T083000
            "%Y-%m-%dT%H:%M:%S",  # 2025-06-23T08:30:00
            "%Y%m%d",  # 20250623
            "%Y-%m-%d",  # 2025-06-23
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str, fmt)
                # If original string had 'Z', assume UTC
                if datetime_str.endswith("Z"):
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:  # noqa: PERF203
                continue

        raise ValueError(f"Unable to parse datetime: {datetime_str}")
