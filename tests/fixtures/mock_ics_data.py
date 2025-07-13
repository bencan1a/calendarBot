"""Mock ICS data and factory functions for testing."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List


class ICSTestData:
    """Factory for creating test CalendarEvent objects for testing."""

    @staticmethod
    def create_mock_events(count: int = 3, include_today: bool = False) -> List:
        """Create mock Microsoft Graph API-like events for testing."""
        from types import SimpleNamespace

        events = []
        now = datetime.now()
        base_date = now.date() if include_today else (now + timedelta(days=1)).date()

        for i in range(count):
            event_date = base_date + timedelta(days=i // 12)  # Spread across multiple days
            hour = 9 + (i % 12)  # Keep hours between 9-20
            start_time = datetime.combine(event_date, datetime.min.time().replace(hour=hour))
            end_time = start_time + timedelta(hours=1)

            # Create mock event with Microsoft Graph API structure
            event = SimpleNamespace(
                id=f"test-event-{i+1}",
                subject=f"Test Event {i+1}",
                body_preview=f"This is test event number {i+1}",
                start=SimpleNamespace(date_time=start_time, time_zone="UTC"),
                end=SimpleNamespace(date_time=end_time, time_zone="UTC"),
                is_all_day=False,
                show_as=SimpleNamespace(value="busy"),
                is_cancelled=False,
                is_organizer=True,
                location=SimpleNamespace(
                    display_name=f"Test Location {i+1}", address=f"Test Address {i+1}"
                ),
                is_online_meeting=False,
                online_meeting_url=None,
                web_link=f"https://example.com/event/{i+1}",
                is_recurring=False,
                series_master_id=None,
                last_modified_date_time=start_time,
            )

            # Add required methods for testing
            def is_current():
                return False

            def is_upcoming():
                return True

            event.is_current = is_current
            event.is_upcoming = is_upcoming
            events.append(event)

        return events

    @staticmethod
    def create_event_for_date(event_date, title: str):
        """Create a single Microsoft Graph API-like event for a specific date."""
        from types import SimpleNamespace

        start_time = datetime.combine(event_date, datetime.min.time().replace(hour=10))
        end_time = start_time + timedelta(hours=1)

        # Create mock event with Microsoft Graph API structure
        return SimpleNamespace(
            id=f"event-{title.lower().replace(' ', '-')}",
            subject=title,
            body_preview=f"Test event: {title}",
            start=SimpleNamespace(date_time=start_time, time_zone="UTC"),
            end=SimpleNamespace(date_time=end_time, time_zone="UTC"),
            is_all_day=False,
            show_as=SimpleNamespace(value="busy"),
            is_cancelled=False,
            is_organizer=True,
            location=SimpleNamespace(display_name="Test Location", address="Test Address"),
            is_online_meeting=False,
            online_meeting_url=None,
            web_link=f"https://example.com/event/{title.lower().replace(' ', '-')}",
            is_recurring=False,
            series_master_id=None,
            last_modified_date_time=start_time,
        )


class ICSDataFactory:
    """Factory for creating test ICS calendar data."""

    @staticmethod
    def create_basic_ics(event_count: int = 3) -> str:
        """Create basic ICS content with specified number of events."""
        now = datetime.now()

        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
"""

        for i in range(event_count):
            event_start = now + timedelta(hours=i * 2)
            event_end = event_start + timedelta(hours=1)

            ics_content += f"""BEGIN:VEVENT
UID:test-event-{i+1}@example.com
DTSTART:{event_start.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{event_end.strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Test Event {i+1}
DESCRIPTION:This is test event number {i+1}
LOCATION:Test Location {i+1}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
"""

        ics_content += "END:VCALENDAR"
        return ics_content

    @staticmethod
    def create_all_day_event_ics() -> str:
        """Create ICS with all-day events."""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:all-day-event@example.com
DTSTART;VALUE=DATE:{today.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{tomorrow.strftime("%Y%m%d")}
SUMMARY:All Day Test Event
DESCRIPTION:This is an all-day test event
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""

    @staticmethod
    def create_recurring_event_ics() -> str:
        """Create ICS with recurring events."""
        now = datetime.now()

        return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:recurring-event@example.com
DTSTART:{now.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{(now + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Weekly Recurring Meeting
DESCRIPTION:This meeting happens every week
LOCATION:Conference Room B
RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""

    @staticmethod
    def create_malformed_ics() -> str:
        """Create malformed ICS content for error testing."""
        return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
BEGIN:VEVENT
UID:malformed-event@example.com
DTSTART:INVALID_DATE_FORMAT
SUMMARY:Malformed Event
END:VEVENT
END:VCALENDAR"""

    @staticmethod
    def create_empty_ics() -> str:
        """Create empty ICS calendar."""
        return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
END:VCALENDAR"""

    @staticmethod
    def create_large_ics(event_count: int = 100) -> str:
        """Create large ICS content for performance testing."""
        now = datetime.now()

        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//CalendarBot Test//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
"""

        for i in range(event_count):
            # Spread events over several days
            event_start = now + timedelta(days=i // 10, hours=(i % 10) * 2)
            event_end = event_start + timedelta(hours=1)

            ics_content += f"""BEGIN:VEVENT
UID:large-test-event-{i+1}@example.com
DTSTART:{event_start.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{event_end.strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Large Test Event {i+1}
DESCRIPTION:Event {i+1} in large calendar test with lots of details and content to test parsing performance and memory usage during processing.
LOCATION:Location {i+1}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
"""

        ics_content += "END:VCALENDAR"
        return ics_content


class MockHTTPResponses:
    """Factory for creating mock HTTP responses."""

    @staticmethod
    def success_response(content: str, content_type: str = "text/calendar") -> Dict[str, Any]:
        """Create a successful HTTP response."""
        return {
            "status_code": 200,
            "content": content,
            "headers": {
                "Content-Type": content_type,
                "Content-Length": str(len(content)),
                "Last-Modified": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "ETag": f'"{hash(content) % 10000}"',
            },
        }

    @staticmethod
    def not_modified_response() -> Dict[str, Any]:
        """Create a 304 Not Modified response."""
        return {
            "status_code": 304,
            "content": "",
            "headers": {
                "Last-Modified": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "ETag": '"12345"',
            },
        }

    @staticmethod
    def auth_error_response() -> Dict[str, Any]:
        """Create a 401 authentication error response."""
        return {
            "status_code": 401,
            "content": "Unauthorized",
            "headers": {"Content-Type": "text/plain", "WWW-Authenticate": 'Basic realm="Test"'},
        }

    @staticmethod
    def not_found_response() -> Dict[str, Any]:
        """Create a 404 not found response."""
        return {
            "status_code": 404,
            "content": "Not Found",
            "headers": {"Content-Type": "text/plain"},
        }

    @staticmethod
    def server_error_response() -> Dict[str, Any]:
        """Create a 500 server error response."""
        return {
            "status_code": 500,
            "content": "Internal Server Error",
            "headers": {"Content-Type": "text/plain"},
        }

    @staticmethod
    def timeout_response() -> Dict[str, Any]:
        """Create a timeout scenario (no response)."""
        return {"timeout": True}


class SSRFTestCases:
    """Test cases for SSRF protection testing."""

    MALICIOUS_URLS = [
        # Localhost variations
        "http://localhost:80/",
        "http://127.0.0.1:80/",
        "http://[::1]:80/",
        # Private IP ranges
        "http://192.168.1.1/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        # URL encoding attempts
        "http://127.0.0.1:80/%2e%2e/",
        "http://127.0.0.1:80/..%2f",
        # Non-HTTP schemes
        "file:///etc/passwd",
        "ftp://internal.server/",
        "ldap://internal.server/",
        # IPv6 localhost
        "http://[::1]/",
        "http://[0:0:0:0:0:0:0:1]/",
        # Decimal IP representations
        "http://2130706433/",  # 127.0.0.1 in decimal
        # Hex IP representations
        "http://0x7f000001/",  # 127.0.0.1 in hex
    ]

    SAFE_URLS = [
        "https://calendar.google.com/calendar/ical/example.ics",
        "https://outlook.live.com/owa/calendar/example.ics",
        "https://example.com/calendar.ics",
        "http://public-server.com/calendar.ics",
        "https://calendars.office365.com/test.ics",
    ]


class DatabaseTestData:
    """Factory for creating test database records."""

    @staticmethod
    def create_cached_event_data(event_id: str = "test-1") -> Dict[str, Any]:
        """Create cached event data for database testing."""
        now = datetime.now()

        return {
            "id": f"cached_{event_id}",
            "graph_id": event_id,
            "subject": f"Test Event {event_id}",
            "body_preview": f"Test event body preview for {event_id}",
            "start_datetime": (now + timedelta(hours=1)).isoformat(),
            "end_datetime": (now + timedelta(hours=2)).isoformat(),
            "start_timezone": "UTC",
            "end_timezone": "UTC",
            "is_all_day": False,
            "show_as": "busy",
            "is_cancelled": False,
            "is_organizer": True,
            "location_display_name": "Test Location",
            "location_address": "123 Test St",
            "is_online_meeting": False,
            "online_meeting_url": None,
            "web_link": f"https://example.com/event/{event_id}",
            "is_recurring": False,
            "series_master_id": None,
            "cached_at": now.isoformat(),
            "last_modified": now.isoformat(),
        }

    @staticmethod
    def create_cache_metadata(
        last_update: datetime = None, successful_fetch: datetime = None, failures: int = 0
    ) -> Dict[str, Any]:
        """Create cache metadata for testing."""
        now = datetime.now()

        return {
            "id": 1,
            "last_update": (last_update or now).isoformat(),
            "last_successful_fetch": (successful_fetch or now).isoformat(),
            "consecutive_failures": failures,
            "last_error": None if failures == 0 else "Test error",
            "last_error_time": None if failures == 0 else now.isoformat(),
        }


class WebAPITestData:
    """Factory for creating web API test data."""

    @staticmethod
    def navigation_request(action: str) -> Dict[str, Any]:
        """Create navigation API request data."""
        return {"action": action}

    @staticmethod
    def layout_request(layout: str) -> Dict[str, Any]:
        """Create layout API request data."""
        return {"layout": layout}

    @staticmethod
    def expected_navigation_response(success: bool = True) -> Dict[str, Any]:
        """Create expected navigation API response."""
        return {
            "success": success,
            "html": "<html><body>Test Calendar Content</body></html>" if success else None,
        }

    @staticmethod
    def expected_status_response() -> Dict[str, Any]:
        """Create expected status API response."""
        return {
            "running": True,
            "host": "127.0.0.1",
            "port": 8998,
            "layout": "4x8",
            "interactive_mode": False,
            "current_date": datetime.now().date().isoformat(),
        }


# Utility functions for test data manipulation
def modify_ics_for_timezone_test(base_ics: str, timezone: str) -> str:
    """Modify ICS content to use specific timezone."""
    # Replace UTC timezone with specified timezone
    return base_ics.replace("Z", "").replace("DTSTART:", f"DTSTART;TZID={timezone}:")


def create_performance_test_ics(size_mb: float) -> str:
    """Create ICS content of approximately specified size in MB."""
    target_size = int(size_mb * 1024 * 1024)  # Convert MB to bytes
    base_ics = ICSDataFactory.create_basic_ics(1)

    # Calculate how many repetitions we need
    base_size = len(base_ics)
    repetitions = target_size // base_size

    # Create large content by repeating events
    large_ics = ICSDataFactory.create_large_ics(repetitions)

    return large_ics


def extract_events_from_ics(ics_content: str) -> List[Dict[str, str]]:
    """Extract event data from ICS content for validation."""
    events = []
    lines = ics_content.split("\n")
    current_event = {}
    in_event = False

    for line in lines:
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            current_event = {}
        elif line == "END:VEVENT":
            if current_event:
                events.append(current_event.copy())
            in_event = False
        elif in_event and ":" in line:
            key, value = line.split(":", 1)
            current_event[key] = value

    return events
