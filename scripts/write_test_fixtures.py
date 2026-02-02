#!/usr/bin/env python3
import os
from pathlib import Path

ICS_DIR = Path("tests/fixtures/ics")
ICS_DIR.mkdir(parents=True, exist_ok=True)

fixtures = {
    "single-meeting.ics": """# Single meeting fixture
# Scenario: one-off meeting (UTC timestamps) used for single_meeting test
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:single-meeting-20251105-001@example.com
DTSTAMP:20250101T000000Z
SEQUENCE:1
DTSTART:20251105T160000Z
DTEND:20251105T170000Z
SUMMARY:Team Standup
DESCRIPTION:One-off team standup for testing whats-next selection
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
""",
    "daily-recurring.ics": """# Daily recurring fixture
# Daily meeting with COUNT=5
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
METHOD:PUBLISH
BEGIN:VEVENT
UID:daily-recurring-202511-001@example.com
DTSTAMP:20250101T000000Z
SEQUENCE:1
DTSTART:20251103T170000Z
DTEND:20251103T173000Z
SUMMARY:Daily Sync
RRULE:FREQ=DAILY;COUNT=5
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
""",
    "recurring-with-exdate.ics": """# Weekly recurring with EXDATE
# One instance explicitly excluded via EXDATE
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
METHOD:PUBLISH
BEGIN:VEVENT
UID:weekly-planning-202511-001@example.com
DTSTAMP:20250101T000000Z
SEQUENCE:1
DTSTART:20251103T180000Z
DTEND:20251103T190000Z
SUMMARY:Weekly Planning
RRULE:FREQ=WEEKLY;COUNT=6
EXDATE:20251110T180000Z
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
""",
    "tz-event.ics": """# Timezone-aware event (America/New_York)
# Event stored in New York timezone; expectations will be in UTC
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
METHOD:PUBLISH
BEGIN:VTIMEZONE
TZID:America/New_York
BEGIN:STANDARD
DTSTART:20231105T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZNAME:EST
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:20240310T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
TZNAME:EDT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:tz-event-202511-001@example.com
DTSTART;TZID=America/New_York:20251115T100000
DTEND;TZID=America/New_York:20251115T110000
SUMMARY:Cross-Timezone Call
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
""",
    "all-day-event.ics": """# All-day event fixture
# One-day all-day event using DATE values
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
METHOD:PUBLISH
BEGIN:VEVENT
UID:all-day-20251110-001@example.com
DTSTAMP:20250101T000000Z
DTSTART;VALUE=DATE:20251110
DTEND;VALUE=DATE:20251111
SUMMARY:Company Holiday
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
""",
    "dst-transition.ics": """# DST transition and overlapping events (America/Los_Angeles)
# Two timed events scheduled at the ambiguous 01:30 local time on DST end date (2025-11-02)
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot Test//Test Calendar//EN
METHOD:PUBLISH
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:DAYLIGHT
DTSTART:20250309T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
END:DAYLIGHT
BEGIN:STANDARD
DTSTART:20251102T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:dst-event-1@example.com
DTSTART;TZID=America/Los_Angeles:20251102T013000
DTEND;TZID=America/Los_Angeles:20251102T023000
SUMMARY:DST Ambiguous Meeting A
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
UID:dst-event-2@example.com
DTSTART;TZID=America/Los_Angeles:20251102T013000
DTEND;TZID=America/Los_Angeles:20251102T023000
SUMMARY:DST Ambiguous Meeting B
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
""",
}

for name, content in fixtures.items():
    path = ICS_DIR / name
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")

# Overwrite specs.yaml in tests/spec_runners
SPEC_PATH = Path("tests/spec_runners/specs.yaml")
specs = """version: "1.0"
description: "Integration test suite for calendarbot_lite API (generated fixtures)"

tests:
  - test_id: "single_meeting_20251105"
    description: "Single meeting scheduled for future execution"
    category: "single_meeting"
    ics_file: "single-meeting.ics"
    datetime_override: "2025-11-05T08:00:00-07:00"
    expected:
      events:
        - start_datetime: "2025-11-05T16:00:00Z"
          end_datetime: "2025-11-05T17:00:00Z"
          summary: "Team Standup"
          uid: "single-meeting-20251105-001@example.com"
    metadata:
      source: "generated"
      author: "roo-code"

  - test_id: "daily_recurring_202511"
    description: "Daily recurring meeting pattern (COUNT=5)"
    category: "recurring"
    ics_file: "daily-recurring.ics"
    datetime_override: "2025-11-03T16:00:00Z"
    expected:
      events:
        - start_datetime: "2025-11-03T17:00:00Z"
          end_datetime: "2025-11-03T17:30:00Z"
          summary: "Daily Sync"
          uid: "daily-recurring-202511-001@example.com"
    metadata:
      source: "generated"
      author: "roo-code"

  - test_id: "recurring_with_exdate_202511"
    description: "Weekly recurring meeting with EXDATE excluding 2025-11-10"
    category: "exception"
    ics_file: "recurring-with-exdate.ics"
    datetime_override: "2025-11-03T10:00:00Z"
    expected:
      events:
        - start_datetime: "2025-11-03T18:00:00Z"
          end_datetime: "2025-11-03T19:00:00Z"
          summary: "Weekly Planning"
          uid: "weekly-planning-202511-001@example.com"
        - start_datetime: "2025-11-17T18:00:00Z"
          end_datetime: "2025-11-17T19:00:00Z"
          summary: "Weekly Planning"
          uid: "weekly-planning-202511-001@example.com"
    metadata:
      source: "generated"
      author: "roo-code"

  - test_id: "timezone_event_202511"
    description: "Event stored in America/New_York timezone; expectation normalized to UTC"
    category: "timezone"
    ics_file: "tz-event.ics"
    datetime_override: "2025-11-15T09:00:00-05:00"
    expected:
      events:
        - start_datetime: "2025-11-15T15:00:00Z"
          end_datetime: "2025-11-15T16:00:00Z"
          summary: "Cross-Timezone Call"
          uid: "tz-event-202511-001@example.com"
    metadata:
      source: "generated"
      author: "roo-code"

  - test_id: "all_day_event_202511"
    description: "Single all-day event using DATE values"
    category: "all_day"
    ics_file: "all-day-event.ics"
    datetime_override: "2025-11-09T12:00:00-07:00"
    expected:
      events:
        - start_datetime: "2025-11-10T00:00:00Z"
          end_datetime: "2025-11-11T00:00:00Z"
          summary: "Company Holiday"
          uid: "all-day-20251110-001@example.com"
    metadata:
      source: "generated"
      author: "roo-code"

  - test_id: "dst_transition_timezone_202511"
    description: "Events scheduled at the ambiguous 01:30 local time on DST end date (timezone transition)"
    category: "timezone_transition"
    ics_file: "dst-transition.ics"
    datetime_override: "2025-10-30T00:00:00-07:00"
    expected:
      events:
        - start_datetime: "2025-11-02T08:30:00Z"
          end_datetime: "2025-11-02T09:30:00Z"
          summary: "DST Ambiguous Meeting A"
          uid: "dst-event-1@example.com"
    metadata:
      source: "generated"
      author: "roo-code"
      notes: "Expect the expander to pick the first occurrence mapping to UTC; verify handling of ambiguous local times"

  - test_id: "dst_transition_overlapping_202511"
    description: "Two events that overlap at the same local time across DST boundary"
    category: "overlapping"
    ics_file: "dst-transition.ics"
    datetime_override: "2025-10-30T00:00:00-07:00"
    expected:
      events:
        - start_datetime: "2025-11-02T08:30:00Z"
          end_datetime: "2025-11-02T09:30:00Z"
          summary: "DST Ambiguous Meeting A"
          uid: "dst-event-1@example.com"
        - start_datetime: "2025-11-02T08:30:00Z"
          end_datetime: "2025-11-02T09:30:00Z"
          summary: "DST Ambiguous Meeting B"
          uid: "dst-event-2@example.com"
    metadata:
      source: "generated"
      author: "roo-code"
"""

SPEC_PATH.write_text(specs, encoding="utf-8")
print(f"Wrote {SPEC_PATH}")

print("Fixture generation complete.")

if __name__ == '__main__':
    pass