"""Unit tests for Alexa skill backend timezone configuration."""

import os
from contextlib import contextmanager

import pytest


pytestmark = pytest.mark.unit


@contextmanager
def clean_timezone_env(**env_vars):
    """Context manager to set timezone environment variable."""
    # Save original value
    original = os.environ.get("CALENDARBOT_DEFAULT_TIMEZONE")

    try:
        # Clear timezone var
        os.environ.pop("CALENDARBOT_DEFAULT_TIMEZONE", None)
        # Set the ones we want
        os.environ.update(env_vars)
        yield
    finally:
        # Restore original value
        if original is not None:
            os.environ["CALENDARBOT_DEFAULT_TIMEZONE"] = original
        else:
            os.environ.pop("CALENDARBOT_DEFAULT_TIMEZONE", None)


class TestAlexaSkillBackendTimezone:
    """Tests for Alexa skill backend timezone configuration."""

    def test_get_default_timezone_with_configured_timezone(self):
        """Should return configured timezone when valid."""
        # Need to import after setting env var for proper initialization
        with clean_timezone_env(CALENDARBOT_DEFAULT_TIMEZONE="America/New_York"):
            # Import after setting env var to ensure it picks up the new value
            import importlib
            import sys

            # Remove module from cache to force reimport with new env var
            if "calendarbot_lite.alexa_skill_backend" in sys.modules:
                importlib.reload(sys.modules["calendarbot_lite.alexa_skill_backend"])

            from calendarbot_lite.alexa.alexa_skill_backend import get_default_timezone

            timezone = get_default_timezone()
            assert timezone == "America/New_York"

    def test_get_default_timezone_without_configuration(self):
        """Should return default timezone when not configured."""
        with clean_timezone_env():
            # Import after clearing env var
            import importlib
            import sys

            # Remove module from cache to force reimport with new env var
            if "calendarbot_lite.alexa_skill_backend" in sys.modules:
                importlib.reload(sys.modules["calendarbot_lite.alexa_skill_backend"])

            from calendarbot_lite.alexa.alexa_skill_backend import get_default_timezone

            timezone = get_default_timezone()
            assert timezone == "America/Los_Angeles"

    def test_get_default_timezone_with_invalid_timezone(self):
        """Should fall back to default when timezone is invalid."""
        with clean_timezone_env(CALENDARBOT_DEFAULT_TIMEZONE="Invalid/Timezone"):
            # Import after setting env var
            import importlib
            import sys

            # Remove module from cache to force reimport with new env var
            if "calendarbot_lite.alexa_skill_backend" in sys.modules:
                importlib.reload(sys.modules["calendarbot_lite.alexa_skill_backend"])

            from calendarbot_lite.alexa.alexa_skill_backend import get_default_timezone

            timezone = get_default_timezone()
            assert timezone == "America/Los_Angeles"

    def test_get_default_timezone_validates_multiple_timezones(self):
        """Should validate various IANA timezone formats."""
        valid_timezones = [
            "America/Los_Angeles",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "UTC",
            "Australia/Sydney",
            "America/Chicago",
            "Europe/Paris",
        ]

        for tz in valid_timezones:
            with clean_timezone_env(CALENDARBOT_DEFAULT_TIMEZONE=tz):
                # Import after setting env var
                import importlib
                import sys

                # Remove module from cache to force reimport with new env var
                if "calendarbot_lite.alexa_skill_backend" in sys.modules:
                    importlib.reload(sys.modules["calendarbot_lite.alexa_skill_backend"])

                from calendarbot_lite.alexa.alexa_skill_backend import get_default_timezone

                result = get_default_timezone()
                assert result == tz, f"Failed to validate timezone: {tz}"

    def test_get_default_timezone_handles_zoneinfo_import(self):
        """Should properly use zoneinfo for timezone validation."""
        with clean_timezone_env(CALENDARBOT_DEFAULT_TIMEZONE="Europe/London"):
            import importlib
            import sys

            # Remove module from cache to force reimport with new env var
            if "calendarbot_lite.alexa_skill_backend" in sys.modules:
                importlib.reload(sys.modules["calendarbot_lite.alexa_skill_backend"])

            from calendarbot_lite.alexa.alexa_skill_backend import get_default_timezone

            # This should not raise an exception
            timezone = get_default_timezone()
            assert timezone == "Europe/London"

            # Verify zoneinfo can create a ZoneInfo object with this timezone
            import zoneinfo

            tz_obj = zoneinfo.ZoneInfo(timezone)
            assert tz_obj is not None
