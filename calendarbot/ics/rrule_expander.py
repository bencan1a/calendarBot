"""RRULE expansion logic for CalendarBot ICS parser."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from dateutil.rrule import DAILY, HOURLY, MINUTELY, MONTHLY, SECONDLY, WEEKLY, YEARLY, rrule

from ..config.settings import CalendarBotSettings
from .models import CalendarEvent, DateTimeInfo

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

    def expand_rrule(
        self,
        master_event: CalendarEvent,
        rrule_string: str,
        exdates: Optional[list[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[CalendarEvent]:
        """Expand RRULE pattern into individual event instances.

        Args:
            master_event: Master recurring event containing pattern
            rrule_string: RRULE string to expand (e.g. "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")
            exdates: List of excluded dates in ISO format
            start_date: Start of expansion window (defaults to event start)
            end_date: End of expansion window (defaults to start + expansion_window_days)

        Returns:
            List of CalendarEvent instances for each occurrence

        Raises:
            RRuleExpansionError: If expansion fails
        """
        if not self.enable_expansion:
            return []

        try:
            # Parse RRULE components
            rrule_params = self.parse_rrule_string(rrule_string)

            # Set expansion window
            if start_date is None:
                start_date = master_event.start.date_time
            if end_date is None:
                start_date_naive = (
                    start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
                )
                end_date = start_date_naive + timedelta(days=self.expansion_window_days)

            # Generate occurrences using dateutil.rrule
            occurrences = self._generate_occurrences(
                master_event, rrule_params, start_date, end_date
            )

            # Apply EXDATE exclusions
            if exdates:
                occurrences = self.apply_exdates(occurrences, exdates)

            # Filter by date range
            occurrences = self._filter_by_date_range(occurrences, start_date, end_date)

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
                    rrule_dict["freq"] = value.upper()
                elif key == "interval":
                    rrule_dict["interval"] = int(value)
                elif key == "byday":
                    # Split comma-separated BYDAY values
                    rrule_dict["byday"] = [day.strip().upper() for day in value.split(",")]
                elif key == "until":
                    # Parse UNTIL datetime
                    rrule_dict["until"] = self._parse_datetime(value)
                elif key == "count":
                    rrule_dict["count"] = int(value)
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
