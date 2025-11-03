"""iCalendar parser with Microsoft Outlook compatibility - CalendarBot Lite version."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, cast

from icalendar import Calendar, Event as ICalEvent

from .lite_attendee_parser import LiteAttendeeParser
from .lite_datetime_utils import LiteDateTimeParser
from .lite_event_merger import LiteEventMerger
from .lite_event_parser import LiteEventComponentParser
from .lite_models import (
    LiteAttendee,
    LiteCalendarEvent,
    LiteICSParseResult,
)
from .lite_rrule_expander import LiteRRuleExpander
from .lite_streaming_parser import (
    MAX_ICS_SIZE_BYTES,
    MAX_ICS_SIZE_WARNING,
    STREAMING_THRESHOLD,
    LiteICSContentTooLargeError,
    LiteStreamingICSParser,
)

logger = logging.getLogger(__name__)

# NOTE: LiteStreamingICSParser has been moved to lite_streaming_parser module
# and is now imported at the top of this file

# NOTE: _ensure_timezone_aware has been moved to lite_datetime_utils module
# and is now imported at the top of this file


def _is_production_mode() -> bool:
    """Simple production mode check for calendarbot_lite."""
    import os

    return os.environ.get("CALENDARBOT_PRODUCTION", "false").lower() in ("true", "1")


# Internal helper classes for RRULE expansion
# These classes are used to create lightweight event representations for recurring events


class _SimpleEvent:
    """Lightweight event representation for RRULE expansion.

    Used as a fallback when a full parsed event is not available.
    Contains minimal attributes needed for recurring event expansion.
    """

    def __init__(self) -> None:
        """Initialize a simple event with default None values."""
        self.start: Any = None
        self.end: Any = None
        self.id: Any = None
        self.subject: Any = None
        self.body_preview: Any = None
        self.is_recurring: Any = None
        self.is_all_day: Any = None
        self.is_cancelled: Any = None
        self.is_online_meeting: Any = None
        self.online_meeting_url: Any = None
        self.last_modified_date_time: Any = None


class _DateTimeWrapper:
    """Wrapper for datetime objects used in event expansion.

    Provides a consistent interface for date_time and time_zone attributes
    expected by the RRULE expander.
    """

    def __init__(self, dt: Any) -> None:
        """Initialize datetime wrapper.

        Args:
            dt: Datetime object to wrap
        """
        self.date_time = dt
        # Preserve timezone info if present, else default to UTC
        self.time_zone = getattr(dt, "tzinfo", timezone.utc)


class LiteICSParser:
    """iCalendar parser with Microsoft Outlook compatibility - CalendarBot Lite version."""

    def __init__(self, settings: Any) -> None:
        """Initialize ICS parser.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.rrule_expander = LiteRRuleExpander(settings)
        self._streaming_parser = LiteStreamingICSParser()
        self._datetime_parser = LiteDateTimeParser()
        self._attendee_parser = LiteAttendeeParser()
        self._event_parser = LiteEventComponentParser(
            self._datetime_parser, self._attendee_parser, settings
        )
        self._event_merger = LiteEventMerger()

        # Initialize RRULE orchestrator for centralized expansion logic
        from .lite_rrule_expander import RRuleOrchestrator
        self._rrule_orchestrator = RRuleOrchestrator(settings, self._event_parser)

        logger.debug("Lite ICS parser initialized")

    def _build_component_and_event_maps(
        self,
        events: list[LiteCalendarEvent],
        raw_components: list[ICalEvent],
    ) -> tuple[dict[str, ICalEvent], dict[str, LiteCalendarEvent]]:
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
        events_by_id: dict[str, LiteCalendarEvent] = {}
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
        component_map: dict[str, ICalEvent],
        events_by_id: dict[str, LiteCalendarEvent],
        events: list[LiteCalendarEvent],
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
        component: ICalEvent,
        events: list[LiteCalendarEvent],
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
        exdate_props = self._event_parser._collect_exdate_props(component) or []  # noqa: SLF001
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
        component: ICalEvent,
        events_by_id: dict[str, LiteCalendarEvent],
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

        # Synthesize a lightweight event object with minimal attributes
        candidate_event = _SimpleEvent()  # type: ignore[assignment]

        # Decode DTSTART/DTEND from the raw component
        try:
            dtstart_raw = component.decoded("DTSTART")
            dtend_raw = component.decoded("DTEND") if "DTEND" in component else None

            # Wrap start and end in simple containers expected by expander
            if isinstance(dtstart_raw, datetime):
                candidate_event.start = _DateTimeWrapper(dtstart_raw)  # type: ignore[assignment]
            else:
                # fallback parse string
                candidate_event.start = _DateTimeWrapper(  # type: ignore[assignment]
                    self._parse_datetime(component.get("DTSTART"))
                )

            if dtend_raw and isinstance(dtend_raw, datetime):
                candidate_event.end = _DateTimeWrapper(dtend_raw)  # type: ignore[assignment]
            elif dtend_raw:
                candidate_event.end = _DateTimeWrapper(self._parse_datetime(component.get("DTEND")))  # type: ignore[assignment]
            else:
                # If DTEND missing, approximate using duration of one hour
                candidate_event.end = _DateTimeWrapper(  # type: ignore[assignment]
                    candidate_event.start.date_time + timedelta(hours=1)
                )
        except Exception:
            # Last-resort defaults
            now = datetime.now(timezone.utc)
            candidate_event.start = _DateTimeWrapper(now)  # type: ignore[assignment]
            candidate_event.end = _DateTimeWrapper(now + timedelta(hours=1))  # type: ignore[assignment]

        # Minimal metadata to make expansion operate
        candidate_event.id = comp_uid
        candidate_event.subject = (
            str(component.get("SUMMARY", "")) if component.get("SUMMARY") else ""
        )
        candidate_event.body_preview = ""  # Default empty body preview
        candidate_event.is_recurring = True
        candidate_event.is_all_day = False
        candidate_event.is_cancelled = False
        candidate_event.is_online_meeting = False
        candidate_event.online_meeting_url = None
        candidate_event.last_modified_date_time = None

        return candidate_event

    def _orchestrate_rrule_expansion(
        self,
        candidates: list[tuple[Any, str, Optional[list[str]]]],
    ) -> list[LiteCalendarEvent]:
        """Execute RRULE expansion for candidates using async streaming.

        Now uses AsyncOrchestrator to handle event loop detection and execution.

        Args:
            candidates: List of (event, rrule_string, exdates) tuples

        Returns:
            List of expanded event instances
        """
        expanded_instances: list[LiteCalendarEvent] = []

        if not candidates:
            return expanded_instances

        # Import expansion function
        try:
            from .lite_rrule_expander import expand_events_streaming
        except Exception:
            expand_events_streaming = None  # type: ignore[assignment]

        if not expand_events_streaming:  # type: ignore[truthy-function]
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
                logger.exception("expand_events_streaming failed: %s")
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

    def _should_use_streaming(self, ics_content: str) -> bool:
        """Determine if streaming parser should be used based on content size.

        Args:
            ics_content: ICS content to check

        Returns:
            True if streaming should be used, False otherwise

        Raises:
            TypeError: If content is None
            AttributeError: If content doesn't have required string methods
        """
        if ics_content is None:
            raise TypeError("ICS content cannot be None")

        if not hasattr(ics_content, "encode"):
            raise AttributeError("ICS content must be a string with encode method")

        if not ics_content:
            return False

        content_size = len(ics_content.encode("utf-8"))
        return content_size >= STREAMING_THRESHOLD

    def parse_ics_content_optimized(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> LiteICSParseResult:
        """Parse ICS content using optimal method based on size.

        Automatically chooses between streaming (for large files) and
        traditional parsing (for small files) to optimize memory usage.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with events and metadata
        """
        if self._should_use_streaming(ics_content):
            logger.debug(f"Using streaming parser for large ICS content ({len(ics_content)} bytes)")
            return self._parse_with_streaming(ics_content, source_url)

        logger.debug(f"Using traditional parser for small ICS content ({len(ics_content)} bytes)")
        return self.parse_ics_content(ics_content, source_url)

    def _parse_with_streaming(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> LiteICSParseResult:
        """Parse ICS content using streaming parser with memory-bounded processing."""
        try:
            # Initialize result tracking - NO event accumulation
            filtered_events: list[LiteCalendarEvent] = []  # Only store final filtered results
            raw_components: list[Any] = []  # Store raw components for RRULE expansion
            # Superset to retain raw VEVENT components (including RRULE masters) even if filtered out
            raw_components_superset: list[Any] = []
            warnings = []
            errors = []
            total_components = 0
            event_count = 0
            recurring_event_count = 0
            calendar_metadata = {}

            # Memory-bounded processing: limit stored events for typical calendar view usage
            max_stored_events = 1000  # Increased to handle calendars with many recurring events

            # Process stream with immediate filtering to prevent memory accumulation
            for item in self._streaming_parser.parse_stream(ics_content):
                if item["type"] == "event":
                    try:
                        # Parse the iCalendar component using existing logic
                        component = item["component"]
                        calendar_metadata.update(item["metadata"])
                        # Always collect raw components into a superset so RRULE masters are available later
                        # Retain RRULE master components preferentially if superset grows too large.
                        raw_components_superset.append(component)
                        try:
                            max_superset = getattr(
                                self.settings, "raw_components_superset_limit", 1500
                            )
                        except Exception:
                            max_superset = 1500
                        # If we exceed the superset limit, drop older non-master components first,
                        # but always keep components that contain an RRULE (recurring masters).
                        if len(raw_components_superset) > max_superset:
                            # Rebuild a compacted list keeping RRULE-containing components and the newest items
                            keep = []
                            # Keep all master components (those that have RRULE)
                            masters = [c for c in raw_components_superset if bool(c.get("RRULE"))]
                            # Then take newest non-master items up to the limit
                            non_masters = [
                                c for c in raw_components_superset if not bool(c.get("RRULE"))
                            ]
                            # Keep last N non-masters where N fills to max_superset when combined with masters
                            space_for_nonmasters = max(0, max_superset - len(masters))
                            keep = masters + non_masters[-space_for_nonmasters:]
                            raw_components_superset = keep

                        # DEBUG: log raw component fields prior to mapping to LiteCalendarEvent
                        try:
                            raw_summary = component.get("SUMMARY")
                            raw_description = component.get("DESCRIPTION")
                            raw_attendees = component.get("ATTENDEE")
                            logger.debug(
                                "Streaming parser received component - "
                                f"SUMMARY={raw_summary!r}, DESCRIPTION_present={bool(raw_description)}, ATTENDEE={raw_attendees!s}"
                            )
                        except Exception:
                            logger.debug(
                                "Streaming parser - failed to read raw component fields",
                                exc_info=True,
                            )

                        # Use existing event parsing logic
                        event = self._parse_event_component(
                            cast("ICalEvent", component),
                            calendar_metadata.get("X-WR-TIMEZONE"),
                        )

                        # DEBUG: log mapped event fields for validation
                        if event:
                            try:
                                attendees_len = len(event.attendees) if event.attendees else 0
                            except Exception:
                                attendees_len = -1
                            logger.debug(
                                "Streaming parser mapped event - "
                                f"subject={getattr(event, 'subject', None)!r}, "
                                f"body_preview_present={bool(getattr(event, 'body_preview', None))}, "
                                f"attendees_count={attendees_len}"
                            )

                        if event:
                            event_count += 1
                            total_components += 1

                            if event.is_recurring:
                                recurring_event_count += 1

                            # Apply filtering immediately to prevent memory accumulation
                            if event.is_busy_status and not event.is_cancelled:
                                # Only store filtered events, and cap the total
                                if len(filtered_events) < max_stored_events:
                                    filtered_events.append(event)
                                    # Store raw component for RRULE expansion (needed for recurring events)
                                    raw_components.append(component)
                                elif len(filtered_events) == max_stored_events:
                                    warning = f"Event limit reached ({max_stored_events}), truncating results"
                                    warnings.append(warning)
                                    logger.warning(warning)

                            # Explicitly release event object for garbage collection
                            del event

                    except Exception as e:
                        warning = f"Failed to parse streamed event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

                elif item["type"] == "error":
                    errors.append(item["error"])

            # If there were errors during streaming, return failure
            if errors:
                return LiteICSParseResult(
                    success=False,
                    error_message="; ".join(errors),
                    warnings=warnings,
                    source_url=source_url,
                )

            logger.debug(
                f"Streaming parser processed {len(filtered_events)} events "
                f"({event_count} total events, {len(filtered_events)} busy/tentative)",
            )

            # IMPORTANT: Expand recurring events (RRULE) to generate instances
            # This was missing from the streaming parser, causing recurring events
            # to not show their future occurrences
            expanded_events = []
            if recurring_event_count > 0:
                try:
                    # Pass the raw components we collected for RRULE expansion
                    # Use the superset of raw components collected during streaming so RRULE masters
                    # are available even if filtered_events was capped or filtered.
                    expanded_events = self._expand_recurring_events(
                        filtered_events, raw_components_superset
                    )
                    if expanded_events:
                        # Merge expanded events with original events and deduplicate
                        filtered_events = self._merge_expanded_events(
                            filtered_events, expanded_events
                        )
                        logger.debug(
                            f"Streaming parser: Added {len(expanded_events)} expanded recurring event instances"
                        )
                except Exception as e:
                    logger.warning(f"Failed to expand recurring events in streaming parser: {e}")
                    # Continue with unexpanded events

            return LiteICSParseResult(
                success=True,
                events=filtered_events,
                calendar_name=calendar_metadata.get("X-WR-CALNAME"),
                calendar_description=calendar_metadata.get("X-WR-CALDESC"),
                timezone=calendar_metadata.get("X-WR-TIMEZONE"),
                total_components=total_components,
                event_count=event_count,
                recurring_event_count=recurring_event_count,
                warnings=warnings,
                ics_version=calendar_metadata.get("VERSION"),
                prodid=calendar_metadata.get("PRODID"),
                raw_content=None,  # Don't store raw content for large files
                source_url=source_url,
            )

        except Exception as e:
            logger.exception("Failed to parse ICS content with streaming parser")
            return LiteICSParseResult(
                success=False,
                error_message=str(e),
                source_url=source_url,
            )

    def _validate_ics_size(self, ics_content: str) -> None:
        """Validate ICS content size before processing.

        Args:
            ics_content: Raw ICS content to validate

        Raises:
            LiteICSContentTooLargeError: If content exceeds maximum size limit
        """
        if not ics_content:
            return

        size_bytes = len(ics_content.encode("utf-8"))

        if size_bytes > MAX_ICS_SIZE_BYTES:
            logger.error(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit",
            )
            raise LiteICSContentTooLargeError(
                f"ICS content too large: {size_bytes} bytes exceeds {MAX_ICS_SIZE_BYTES} limit",
            )

        if size_bytes > MAX_ICS_SIZE_WARNING:
            logger.warning(
                f"Large ICS content detected: {size_bytes} bytes "
                f"(threshold: {MAX_ICS_SIZE_WARNING})",
            )

    def parse_ics_content(
        self,
        ics_content: str,
        source_url: Optional[str] = None,
    ) -> LiteICSParseResult:
        """Parse ICS content into structured calendar events.

        Automatically chooses optimal parsing method based on content size.
        For large files (>10MB), uses streaming parser to reduce memory usage.

        Args:
            ics_content: Raw ICS file content
            source_url: Optional source URL for audit trail

        Returns:
            Parse result with events and metadata including raw content
        """
        if not ics_content or not ics_content.strip():
            logger.warning("Empty ICS content provided")
            return LiteICSParseResult(
                success=False,
                error_message="Empty ICS content",
                source_url=source_url,
            )

        # Use optimized parsing method that automatically selects strategy
        if self._should_use_streaming(ics_content):
            logger.debug(f"Using streaming parser for large ICS content ({len(ics_content)} bytes)")
            return self._parse_with_streaming(ics_content, source_url)

        # Initialize variables that might be used in error handling
        raw_content = None

        try:
            logger.debug("Starting traditional ICS content parsing")

            # Capture raw content and validate size (with error handling)
            # Only store full raw ICS content in development environment
            if not _is_production_mode():
                try:
                    self._validate_ics_size(ics_content)
                    raw_content = ics_content
                    logger.debug(f"Raw ICS content captured: {len(ics_content)} bytes")
                except LiteICSContentTooLargeError:
                    logger.exception("ICS content too large, skipping raw content storage")
                    raise  # Re-raise to stop processing
                except Exception as e:
                    logger.warning(f"Failed to capture raw ICS content: {e}")
                    # Continue parsing without raw content

            # Parse the calendar
            calendar = Calendar.from_ical(ics_content)

            # Extract calendar metadata
            calendar_name = self._get_calendar_property(cast("Calendar", calendar), "X-WR-CALNAME")
            calendar_description = self._get_calendar_property(
                cast("Calendar", calendar),
                "X-WR-CALDESC",
            )
            timezone_str = self._get_calendar_property(cast("Calendar", calendar), "X-WR-TIMEZONE")
            prodid = self._get_calendar_property(cast("Calendar", calendar), "PRODID")
            version = self._get_calendar_property(cast("Calendar", calendar), "VERSION")

            # Parse events
            events = []
            raw_components = []  # Store raw components for phantom filtering
            total_components = 0
            event_count = 0
            recurring_event_count = 0
            warnings = []

            for component in calendar.walk():
                total_components += 1

                if component.name == "VEVENT":
                    try:
                        event = self._parse_event_component(
                            cast("ICalEvent", component),
                            timezone_str,
                        )
                        if event:
                            events.append(event)
                            raw_components.append(component)  # Store raw component
                            event_count += 1

                            if event.is_recurring:
                                recurring_event_count += 1

                    except Exception as e:
                        warning = f"Failed to parse event: {e}"
                        warnings.append(warning)
                        logger.warning(warning)

            # Apply RRULE expansion if enabled
            expanded_events = []
            if getattr(self.settings, "enable_rrule_expansion", True):
                try:
                    expanded_events = self._expand_recurring_events(events, raw_components)
                    if expanded_events:
                        # Merge expanded events with original events and deduplicate
                        events = self._merge_expanded_events(events, expanded_events)
                        events = self._deduplicate_events(events)
                        logger.debug(
                            f"Added {len(expanded_events)} expanded recurring event instances"
                        )
                except Exception as e:
                    logger.warning(f"RRULE expansion failed, continuing without expansion: {e}")
                    # Continue with original events only

            # Filter to only busy/tentative events (same as Graph API behavior)
            # TODO: This should respect the filter_busy_only configuration setting
            filtered_events = [e for e in events if e.is_busy_status and not e.is_cancelled]

            logger.debug(
                f"Parsed {len(filtered_events)} events from ICS content "
                f"({event_count} total events, {len(filtered_events)} busy/tentative)",
            )

            return LiteICSParseResult(
                success=True,
                events=filtered_events,
                calendar_name=calendar_name,
                calendar_description=calendar_description,
                timezone=timezone_str,
                total_components=total_components,
                event_count=event_count,
                recurring_event_count=recurring_event_count,
                warnings=warnings,
                ics_version=version,
                prodid=prodid,
                raw_content=raw_content,
                source_url=source_url,
            )

        except Exception as e:
            logger.exception("Failed to parse ICS content")
            return LiteICSParseResult(
                success=False,
                error_message=str(e),
                raw_content=raw_content,
                source_url=source_url,
            )

    def _parse_event_component(
        self,
        component: ICalEvent,
        default_timezone: Optional[str] = None,
    ) -> Optional[LiteCalendarEvent]:
        """Parse a single VEVENT component into LiteCalendarEvent.

        Delegates to LiteEventComponentParser for actual parsing logic.

        Args:
            component: iCalendar VEVENT component
            default_timezone: Default timezone for the calendar

        Returns:
            Parsed LiteCalendarEvent or None if parsing fails
        """
        return self._event_parser.parse_event_component(component, default_timezone)

    def _parse_datetime(self, dt_prop: Any, default_timezone: Optional[str] = None) -> datetime:
        """Parse iCalendar datetime property.

        Delegates to LiteDateTimeParser for actual parsing logic.

        Args:
            dt_prop: iCalendar datetime property
            default_timezone: Default timezone if none specified

        Returns:
            Parsed datetime with timezone
        """
        return self._datetime_parser.parse_datetime(dt_prop, default_timezone)

    def _parse_datetime_optional(self, dt_prop: Any) -> Optional[datetime]:
        """Parse optional datetime property.

        Delegates to LiteDateTimeParser for actual parsing logic.

        Args:
            dt_prop: iCalendar datetime property or None

        Returns:
            Parsed datetime or None
        """
        return self._datetime_parser.parse_datetime_optional(dt_prop)

    # NOTE: _parse_status has been moved to LiteEventComponentParser in lite_event_parser.py
    # NOTE: _map_transparency_to_status has been moved to LiteEventComponentParser in lite_event_parser.py

    def _parse_attendee(self, attendee_prop: Any) -> Optional[LiteAttendee]:
        """Parse attendee from iCalendar property.

        Delegates to LiteAttendeeParser for actual parsing logic.

        Args:
            attendee_prop: iCalendar ATTENDEE property

        Returns:
            Parsed LiteAttendee or None
        """
        return self._attendee_parser.parse_attendee(attendee_prop)

    def _get_calendar_property(self, calendar: Calendar, prop_name: str) -> Optional[str]:
        """Get calendar-level property.

        Args:
            calendar: iCalendar Calendar object
            prop_name: Property name to get

        Returns:
            Property value as string or None
        """
        try:
            prop = calendar.get(prop_name)
            return str(prop) if prop else None
        except Exception:
            return None

    def filter_busy_events(self, events: list[LiteCalendarEvent]) -> list[LiteCalendarEvent]:
        """Filter to only show busy/tentative events.

        Args:
            events: List of calendar events

        Returns:
            Filtered list of events
        """
        return [event for event in events if event.is_busy_status and not event.is_cancelled]

    def validate_ics_content(self, ics_content: str) -> bool:
        """Validate that content is valid ICS format.

        Args:
            ics_content: ICS content to validate

        Returns:
            True if valid ICS format, False otherwise
        """
        try:
            if not ics_content or not ics_content.strip():
                logger.debug("Empty ICS content provided for validation")
                return False

            # Check for required ICS markers
            if "BEGIN:VCALENDAR" not in ics_content:
                logger.debug("Missing BEGIN:VCALENDAR marker")
                return False

            if "END:VCALENDAR" not in ics_content:
                logger.debug("Missing END:VCALENDAR marker")
                return False

            # Try to parse with icalendar
            Calendar.from_ical(ics_content)

            logger.debug(f"Valid ICS content parsed successfully: {len(ics_content)} bytes")
            return True

        except Exception as e:
            logger.debug(f"ICS validation failed: {e}")
            return False

    # NOTE: _collect_exdate_props has been moved to LiteEventComponentParser in lite_event_parser.py

    def _expand_recurring_events(
        self,
        events: list[LiteCalendarEvent],
        raw_components: list[ICalEvent],
    ) -> list[LiteCalendarEvent]:
        """Expand recurring events using RRuleOrchestrator.

        This method now delegates all RRULE expansion logic to the centralized
        RRuleOrchestrator, which handles:
        1. Building component and event maps
        2. Collecting expansion candidates
        3. Executing async RRULE expansion

        Args:
            events: List of parsed calendar events
            raw_components: List of raw iCalendar components for RRULE extraction

        Returns:
            List of expanded event instances
        """
        # Delegate to RRuleOrchestrator for centralized RRULE expansion
        return self._rrule_orchestrator.expand_recurring_events(events, raw_components)

    def _merge_expanded_events(
        self,
        original_events: list[LiteCalendarEvent],
        expanded_events: list[LiteCalendarEvent],
    ) -> list[LiteCalendarEvent]:
        """Merge expanded events with original events.

        Delegates to LiteEventMerger for actual merging logic.

        Args:
            original_events: Original parsed events
            expanded_events: Expanded recurring event instances

        Returns:
            Combined list of events
        """
        return self._event_merger.merge_expanded_events(original_events, expanded_events)

    def _deduplicate_events(self, events: list[LiteCalendarEvent]) -> list[LiteCalendarEvent]:
        """Remove duplicate events based on UID and start time.

        Delegates to LiteEventMerger for actual deduplication logic.

        Args:
            events: List of calendar events to deduplicate

        Returns:
            Deduplicated list of events
        """
        return self._event_merger.deduplicate_events(events)
