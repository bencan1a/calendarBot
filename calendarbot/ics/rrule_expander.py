"""RRULE expansion logic for CalendarBot ICS parser."""

# ruff: noqa: I001
import contextlib
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
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

from ..config.settings import CalendarBotSettings
from .models import CalendarEvent, DateTimeInfo

UTC = timezone.utc

logger = logging.getLogger(__name__)


class RRuleExpansionError(Exception):
    """Base exception for RRULE expansion errors."""


class RRuleParseError(RRuleExpansionError):
    """Error parsing RRULE string."""


class RRuleExpander:
    """Client-side RRULE expansion for CalendarBot.

    This class handles expansion of RRULE patterns into individual CalendarEvent
    instances using python-dateutil. It supports WEEKLY patterns with EXDATE
    exclusions and proper timezone handling.
    """

    def __init__(self, settings: CalendarBotSettings):
        """Initialize RRuleExpander with settings.

        Args:
            settings: CalendarBot configuration settings
        """
        self.settings = settings
        self.expansion_window_days = getattr(settings, "rrule_expansion_days", 365)
        self.enable_expansion = getattr(settings, "enable_rrule_expansion", True)

    def expand_rrule(  # noqa: PLR0912, PLR0915
        self,
        master_event: CalendarEvent,
        rrule_string: str,
        exdates: Optional[list[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[CalendarEvent]:
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

            # Generate CalendarEvent instances
            return self.generate_event_instances(master_event, occurrences)

        except Exception as e:
            logger.exception("RRULE expansion failed")
            raise RRuleExpansionError(f"Failed to expand RRULE: {e}") from e

    def parse_rrule_string(self, rrule_string: str) -> dict:
        """Parse RRULE string into components.

        Args:
            rrule_string: RRULE string (e.g. "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")

        Returns:
            Dictionary with parsed RRULE components

        Raises:
            RRuleParseError: If RRULE string is invalid
        """
        if not rrule_string or not rrule_string.strip():
            raise RRuleParseError("Empty RRULE string")

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
                raise RRuleParseError("RRULE missing required FREQ parameter")

            return rrule_dict

        except (ValueError, AttributeError) as e:
            raise RRuleParseError(f"Invalid RRULE format: {rrule_string}") from e

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

        excluded_dates = set()

        for exdate_str in exdates:
            try:
                exdate = self._parse_datetime(exdate_str)
                # Convert to date for comparison (ignore time)
                excluded_dates.add(exdate.date())
            except Exception as e:  # noqa: PERF203
                logger.warning(f"Failed to parse EXDATE {exdate_str}: {e}")
                continue

        # Filter out excluded dates
        filtered_occurrences = [
            occurrence for occurrence in occurrences if occurrence.date() not in excluded_dates
        ]

        logger.debug(f"Filtered {len(occurrences) - len(filtered_occurrences)} excluded dates")
        return filtered_occurrences

    def generate_event_instances(
        self,
        master_event: CalendarEvent,
        occurrences: list[datetime],
    ) -> list[CalendarEvent]:
        """Generate CalendarEvent instances for each occurrence.

        Args:
            master_event: Master recurring event template
            occurrences: List of datetime occurrences

        Returns:
            List of CalendarEvent instances
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
            event = CalendarEvent(
                id=instance_id,
                subject=master_event.subject,
                body_preview=master_event.body_preview,
                start=DateTimeInfo(
                    date_time=occurrence,
                    time_zone=master_event.start.time_zone,
                ),
                end=DateTimeInfo(
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

    def _generate_occurrences(
        self,
        master_event: CalendarEvent,
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
        try:
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
                raise RRuleExpansionError(f"Unsupported frequency: {rrule_params['freq']}")  # noqa: TRY301

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

            # Generate occurrences
            rule = rrule(**kwargs)
            return list(rule)

        except Exception as e:
            raise RRuleExpansionError(f"Failed to generate occurrences: {e}") from e

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
            datetime_str: Datetime string (ISO format or RRULE format)

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If datetime format is invalid
        """
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
