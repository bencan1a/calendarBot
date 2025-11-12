"""Tests for Alexa integration in calendarbot_lite."""

import datetime
from unittest.mock import Mock

import pytest

from calendarbot_lite.api.server import (
    _check_bearer_token,
    _format_duration_spoken,
    _serialize_iso,
)

pytestmark = pytest.mark.unit


class TestBearerTokenAuth:
    """Test bearer token authentication."""

    def test_check_bearer_token_with_valid_token(self):
        """Test valid bearer token authentication."""
        request = Mock()
        request.headers = {"Authorization": "Bearer test-token-123"}

        result = _check_bearer_token(request, "test-token-123")
        assert result is True

    def test_check_bearer_token_with_invalid_token(self):
        """Test invalid bearer token authentication."""
        request = Mock()
        request.headers = {"Authorization": "Bearer wrong-token"}

        result = _check_bearer_token(request, "test-token-123")
        assert result is False

    def test_check_bearer_token_with_missing_header(self):
        """Test missing authorization header."""
        request = Mock()
        request.headers = {}

        result = _check_bearer_token(request, "test-token-123")
        assert result is False

    def test_check_bearer_token_with_malformed_header(self):
        """Test malformed authorization header."""
        request = Mock()
        request.headers = {"Authorization": "Basic dGVzdA=="}

        result = _check_bearer_token(request, "test-token-123")
        assert result is False

    def test_check_bearer_token_with_no_required_token(self):
        """Test when no token is required (auth disabled)."""
        request = Mock()
        request.headers = {}

        result = _check_bearer_token(request, None)
        assert result is True


class TestDurationFormatting:
    """Test duration formatting for speech."""

    def test_format_duration_spoken_seconds(self):
        """Test formatting seconds."""
        assert _format_duration_spoken(30) == "in 30 seconds"
        assert _format_duration_spoken(1) == "in 1 seconds"

    def test_format_duration_spoken_minutes(self):
        """Test formatting minutes."""
        assert _format_duration_spoken(60) == "in 1 minute"
        assert _format_duration_spoken(120) == "in 2 minutes"
        assert _format_duration_spoken(90) == "in 1 minute"

    def test_format_duration_spoken_hours(self):
        """Test formatting hours."""
        assert _format_duration_spoken(3600) == "in 1 hour"
        assert _format_duration_spoken(7200) == "in 2 hours"
        assert _format_duration_spoken(3660) == "in 1 hour and 1 minute"
        assert _format_duration_spoken(3720) == "in 1 hour and 2 minutes"
        assert _format_duration_spoken(7260) == "in 2 hours and 1 minute"
        assert _format_duration_spoken(7320) == "in 2 hours and 2 minutes"

    def test_format_duration_spoken_past(self):
        """Test formatting negative durations."""
        assert _format_duration_spoken(-30) == "in the past"


class TestAlexaEndpointsIntegration:
    """Test Alexa-specific API endpoints integration."""

    @pytest.mark.asyncio
    async def test_bearer_token_environment_variable_loading(self):
        """Test that bearer token can be loaded from environment."""
        import os

        from calendarbot_lite.api.server import _build_default_config_from_env

        # Mock environment variable
        original_value = os.environ.get("CALENDARBOT_ALEXA_BEARER_TOKEN")
        os.environ["CALENDARBOT_ALEXA_BEARER_TOKEN"] = "test-env-token"

        try:
            # Current implementation reads CALENDARBOT_ALEXA_BEARER_TOKEN into the config
            config = _build_default_config_from_env()
            # Should include the environment-derived token
            assert config.get("alexa_bearer_token") == "test-env-token"
        finally:
            if original_value is not None:
                os.environ["CALENDARBOT_ALEXA_BEARER_TOKEN"] = original_value
            else:
                os.environ.pop("CALENDARBOT_ALEXA_BEARER_TOKEN", None)

    def test_auth_flow_documentation(self):
        """Document the authentication flow for Alexa integration."""
        # This test serves as documentation of the auth flow

        # 1. User configures alexa_bearer_token in config
        # 2. CalendarBot lite server starts with this token
        # 3. Alexa skill backend makes requests with Authorization: Bearer <token>
        # 4. Server validates token before serving calendar data

        assert True  # Documentation test


class TestSerializationHelpers:
    """Test serialization helper functions."""

    def test_serialize_iso_with_timezone(self):
        """Test ISO serialization with timezone."""
        dt = datetime.datetime(2023, 10, 25, 14, 30, 0, tzinfo=datetime.timezone.utc)
        result = _serialize_iso(dt)
        assert result == "2023-10-25T14:30:00Z"

    def test_serialize_iso_without_timezone(self):
        """Test ISO serialization without timezone (assumes UTC)."""
        dt = datetime.datetime(2023, 10, 25, 14, 30, 0)
        result = _serialize_iso(dt)
        assert result == "2023-10-25T14:30:00Z"

    def test_serialize_iso_with_none(self):
        """Test ISO serialization with None."""
        result = _serialize_iso(None)
        assert result is None


class TestAlexaSsmlIntegration:
    """Integration tests for SSML generation with Alexa endpoints."""

    def test_alexa_ssml_module_imports_correctly(self):
        """Test that SSML module can be imported."""
        try:
            from calendarbot_lite.alexa.alexa_ssml import (
                render_meeting_ssml,
                render_time_until_ssml,
                validate_ssml,
            )
            assert render_meeting_ssml is not None
            assert render_time_until_ssml is not None
            assert validate_ssml is not None
        except ImportError as e:
            pytest.fail(f"SSML module import failed: {e}")

    def test_ssml_integration_with_meeting_data_structure(self):
        """Test SSML generation with meeting data structure from endpoints."""
        from calendarbot_lite.alexa.alexa_ssml import render_meeting_ssml

        # Mock meeting data structure as would be created by alexa_next_meeting endpoint
        meeting_data = {
            "subject": "Daily Standup",
            "seconds_until_start": 300,  # 5 minutes
            "duration_spoken": "in 5 minutes",
            "location": "Conference Room A",
            "is_online_meeting": False,
        }

        result = render_meeting_ssml(meeting_data)
        if result is not None:
            assert result.startswith("<speak>")
            assert result.endswith("</speak>")
            assert "Daily Standup" in result

    def test_ssml_integration_with_time_until_data_structure(self):
        """Test SSML generation with time-until data structure from endpoints."""
        from calendarbot_lite.alexa.alexa_ssml import render_time_until_ssml

        # Mock data structure as would be used by alexa_time_until_next endpoint
        seconds_until = 1800  # 30 minutes
        meeting_data = {
            "subject": "Team Meeting",
            "duration_spoken": "in 30 minutes",
        }

        result = render_time_until_ssml(seconds_until, meeting_data)
        if result is not None:
            assert result.startswith("<speak>")
            assert result.endswith("</speak>")
            assert "30 minute" in result or "minutes" in result

    def test_ssml_fallback_behavior_with_invalid_data(self):
        """Test SSML generation fallback with invalid meeting data."""
        from calendarbot_lite.alexa.alexa_ssml import render_meeting_ssml, render_time_until_ssml

        # Test invalid meeting data - should return None for graceful fallback
        assert render_meeting_ssml(None) is None  # type: ignore
        assert render_meeting_ssml({}) is None

        # Test invalid time data
        assert render_time_until_ssml("invalid") is None  # type: ignore

    def test_ssml_performance_constraints_integration(self):
        """Test SSML generation meets performance constraints."""
        import time

        from calendarbot_lite.alexa.alexa_ssml import render_meeting_ssml

        # Test data for performance measurement
        meeting_data = {
            "subject": "Performance Test Meeting",
            "seconds_until_start": 300,
            "duration_spoken": "in 5 minutes",
            "location": "Test Room",
            "is_online_meeting": False,
        }

        # Measure SSML generation time
        start_time = time.perf_counter()
        result = render_meeting_ssml(meeting_data)
        generation_time = time.perf_counter() - start_time

        # Should complete within 100ms (architectural requirement)
        assert generation_time < 0.1, f"SSML generation took {generation_time:.3f}s, exceeds 100ms limit"

        # SSML must be generated for valid meeting data
        assert result is not None, "SSML must be generated for valid meeting data"
        assert len(result) <= 500, f"SSML length {len(result)} exceeds 500 character limit"

        # Verify SSML structure is valid
        assert result.startswith("<speak>"), "SSML must start with <speak> tag"
        assert result.endswith("</speak>"), "SSML must end with </speak> tag"

    def test_ssml_character_limits_integration(self):
        """Test SSML respects character limits across all scenarios."""
        from calendarbot_lite.alexa.alexa_ssml import render_meeting_ssml, render_time_until_ssml

        # Test with very long meeting title
        long_meeting_data = {
            "subject": "A" * 200,  # Very long title
            "seconds_until_start": 300,
            "duration_spoken": "in 5 minutes",
            "location": "B" * 100,  # Long location
            "is_online_meeting": False,
        }

        result = render_meeting_ssml(long_meeting_data)
        # SSML generation might return None if content exceeds limits or is truncated too much
        # But if it returns a value, it must respect character limits
        if result is not None:
            assert len(result) <= 500, "Meeting SSML should respect 500 char limit"
            assert result.startswith("<speak>"), "SSML must start with <speak> tag"
            assert result.endswith("</speak>"), "SSML must end with </speak> tag"

        # Test time-until with long title
        time_result = render_time_until_ssml(1800, long_meeting_data)
        if time_result is not None:
            assert len(time_result) <= 300, "Time-until SSML should respect 300 char limit"
            assert time_result.startswith("<speak>"), "SSML must start with <speak> tag"
            assert time_result.endswith("</speak>"), "SSML must end with </speak> tag"

    def test_urgency_mapping_integration(self):
        """Test urgency-based SSML generation across time thresholds."""
        from calendarbot_lite.alexa.alexa_ssml import _select_urgency, render_meeting_ssml

        # Test urgency threshold boundaries
        test_cases = [
            (60, "fast"),      # 1 minute - urgent
            (300, "fast"),     # 5 minutes - boundary of fast
            (301, "standard"), # Just over 5 minutes
            (1800, "standard"), # 30 minutes
            (3600, "standard"), # 1 hour - boundary of standard
            (3601, "relaxed"), # Just over 1 hour
            (7200, "relaxed"), # 2 hours
        ]

        for seconds_until, expected_urgency in test_cases:
            urgency = _select_urgency(seconds_until)
            assert urgency == expected_urgency, f"Expected {expected_urgency} for {seconds_until}s, got {urgency}"

            # Test that SSML generation works for each urgency level
            meeting_data = {
                "subject": "Test Meeting",
                "seconds_until_start": seconds_until,
                "duration_spoken": f"in {seconds_until // 60} minutes",
                "location": "",
                "is_online_meeting": False,
            }

            result = render_meeting_ssml(meeting_data)
            # SSML must be generated for valid meeting data
            assert result is not None, f"SSML must be generated for urgency level {expected_urgency}"
            assert result.startswith("<speak>"), "SSML must start with <speak> tag"
            assert result.endswith("</speak>"), "SSML must end with </speak> tag"

    def test_special_character_escaping_integration(self):
        """Test that special characters are properly escaped in SSML output."""
        from calendarbot_lite.alexa.alexa_ssml import _escape_text_for_ssml, render_meeting_ssml

        # Test characters that need escaping
        special_chars_test = {
            "Meeting & Discussion": "&amp;",
            "Review <Draft>": "&lt;",
            'Project "Alpha"': "&quot;",
            "John's Meeting": "&apos;",
        }

        for original, expected_escape in special_chars_test.items():
            escaped = _escape_text_for_ssml(original)
            assert expected_escape in escaped, f"Failed to escape {original}"

            # Test in full SSML generation
            meeting_data = {
                "subject": original,
                "seconds_until_start": 1800,
                "duration_spoken": "in 30 minutes",
                "location": "",
                "is_online_meeting": False,
            }

            result = render_meeting_ssml(meeting_data)
            # SSML must be generated for valid meeting data
            assert result is not None, f"SSML must be generated for meeting with special characters: {original}"
            assert expected_escape in result, f"SSML output should contain escaped version of {original}"
            # Verify SSML structure
            assert result.startswith("<speak>"), "SSML must start with <speak> tag"
            assert result.endswith("</speak>"), "SSML must end with </speak> tag"

    def test_location_handling_integration(self):
        """Test location and online meeting handling in SSML."""
        from calendarbot_lite.alexa.alexa_ssml import render_meeting_ssml

        base_meeting = {
            "subject": "Test Meeting",
            "seconds_until_start": 1800,
            "duration_spoken": "in 30 minutes",
        }

        # Test physical location
        physical_meeting = {**base_meeting, "location": "Conference Room A", "is_online_meeting": False}
        result = render_meeting_ssml(physical_meeting)
        # SSML must be generated for valid meeting data
        assert result is not None, "SSML must be generated for meeting with physical location"
        assert "Conference Room A" in result, "Location should be included in SSML"
        assert 'level="reduced"' in result, "Location should have reduced emphasis"
        # Verify SSML structure
        assert result.startswith("<speak>"), "SSML must start with <speak> tag"
        assert result.endswith("</speak>"), "SSML must end with </speak> tag"

        # Test online meeting
        online_meeting = {**base_meeting, "location": "https://zoom.us/j/123", "is_online_meeting": True}
        result = render_meeting_ssml(online_meeting)
        # SSML must be generated for online meetings
        assert result is not None, "SSML must be generated for online meeting"
        assert "joining online" in result, "Online meeting phrase should be included"
        assert "zoom.us" not in result, "URL should not appear in speech"
        # Verify SSML structure
        assert result.startswith("<speak>"), "SSML must start with <speak> tag"
        assert result.endswith("</speak>"), "SSML must end with </speak> tag"

    def test_title_truncation_integration(self):
        """Test title truncation functionality in SSML generation."""
        from calendarbot_lite.alexa.alexa_ssml import _truncate_title, render_meeting_ssml

        # Test word boundary truncation
        long_title = "Very Long Meeting Title That Should Be Truncated At Word Boundaries"
        truncated = _truncate_title(long_title, 30)
        assert len(truncated) <= 30
        assert truncated.endswith("...")

        # Test in SSML generation
        meeting_data = {
            "subject": long_title,
            "seconds_until_start": 1800,
            "duration_spoken": "in 30 minutes",
            "location": "",
            "is_online_meeting": False,
        }

        result = render_meeting_ssml(meeting_data)
        # SSML must be generated even for long titles (should truncate)
        assert result is not None, "SSML must be generated for meeting with long title (should truncate)"
        assert "..." in result, "Long title should be truncated with ellipsis"
        assert len(result) <= 500, "SSML must respect 500 character limit"
        # Verify SSML structure
        assert result.startswith("<speak>"), "SSML must start with <speak> tag"
        assert result.endswith("</speak>"), "SSML must end with </speak> tag"

    def test_validation_integration_with_generated_ssml(self):
        """Test that generated SSML passes validation checks."""
        from calendarbot_lite.alexa.alexa_ssml import (
            render_meeting_ssml,
            render_time_until_ssml,
            validate_ssml,
        )

        # Test various meeting scenarios generate valid SSML
        test_meetings = [
            {
                "subject": "Quick Sync",
                "seconds_until_start": 180,  # 3 minutes - urgent
                "duration_spoken": "in 3 minutes",
                "location": "",
                "is_online_meeting": False,
            },
            {
                "subject": "Team Standup",
                "seconds_until_start": 1500,  # 25 minutes - standard
                "duration_spoken": "in 25 minutes",
                "location": "Meeting Room B",
                "is_online_meeting": False,
            },
            {
                "subject": "All Hands",
                "seconds_until_start": 7200,  # 2 hours - relaxed
                "duration_spoken": "in 2 hours",
                "location": "",
                "is_online_meeting": True,
            },
        ]

        for meeting_data in test_meetings:
            # Test meeting SSML
            meeting_ssml = render_meeting_ssml(meeting_data)
            # SSML must be generated for valid meeting data
            assert meeting_ssml is not None, f"SSML must be generated for meeting: {meeting_data['subject']}"
            assert validate_ssml(meeting_ssml), f"Generated meeting SSML failed validation: {meeting_ssml}"
            # Verify XML is well-formed
            import xml.etree.ElementTree as ET
            try:
                # Add Amazon namespace declaration if needed for XML parsing
                ssml_to_parse = meeting_ssml
                if 'amazon:' in meeting_ssml and 'xmlns:amazon=' not in meeting_ssml:
                    ssml_to_parse = meeting_ssml.replace(
                        '<speak>',
                        '<speak xmlns:amazon="https://developer.amazon.com/alexa/ssml">',
                        1
                    )
                ET.fromstring(ssml_to_parse)
            except ET.ParseError as e:
                pytest.fail(f"SSML is not well-formed XML: {e}")

            # Test time-until SSML
            time_ssml = render_time_until_ssml(meeting_data["seconds_until_start"], meeting_data)
            # SSML must be generated for time-until queries
            assert time_ssml is not None, f"SSML must be generated for time-until: {meeting_data['subject']}"
            assert validate_ssml(time_ssml, max_chars=300), f"Generated time SSML failed validation: {time_ssml}"
            # Verify XML is well-formed
            try:
                # Add Amazon namespace declaration if needed for XML parsing
                ssml_to_parse = time_ssml
                if 'amazon:' in time_ssml and 'xmlns:amazon=' not in time_ssml:
                    ssml_to_parse = time_ssml.replace(
                        '<speak>',
                        '<speak xmlns:amazon="https://developer.amazon.com/alexa/ssml">',
                        1
                    )
                ET.fromstring(ssml_to_parse)
            except ET.ParseError as e:
                pytest.fail(f"Time SSML is not well-formed XML: {e}")

    def test_config_override_integration(self):
        """Test SSML generation with configuration overrides."""
        from calendarbot_lite.alexa.alexa_ssml import render_meeting_ssml, render_time_until_ssml

        meeting_data = {
            "subject": "Config Test Meeting",
            "seconds_until_start": 1800,
            "duration_spoken": "in 30 minutes",
            "location": "",
            "is_online_meeting": False,
        }

        # Test with SSML disabled
        config_disabled = {"enable_ssml": False}
        result = render_meeting_ssml(meeting_data, config_disabled)
        assert result is None, "SSML should not be generated when disabled in config"

        # Test with custom character limit
        config_short = {"ssml_max_chars": 100}
        result = render_meeting_ssml(meeting_data, config_short)
        # SSML generation might return None if content can't fit in custom limit
        # But if it returns a value, it must respect the limit
        if result is not None:
            assert len(result) <= 100, "SSML must respect custom character limit"
            assert result.startswith("<speak>"), "SSML must start with <speak> tag"
            assert result.endswith("</speak>"), "SSML must end with </speak> tag"

        # Test time-until with disabled SSML
        time_result = render_time_until_ssml(1800, meeting_data, config_disabled)
        assert time_result is None, "Time-until SSML should not be generated when disabled in config"
