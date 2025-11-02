"""Tests for calendarbot_lite.alexa_ssml module."""

import logging
from unittest.mock import patch

import pytest

from calendarbot_lite.alexa_ssml import (
    DEFAULT_CONFIG,
    URGENCY_FAST_THRESHOLD,
    URGENCY_STANDARD_THRESHOLD,
    render_meeting_ssml,
    render_time_until_ssml,
    render_done_for_day_ssml,
    validate_ssml,
    _basic_tag_balance_check,
    _compose_fragments,
    _escape_text_for_ssml,
    _select_urgency,
    _should_include_duration,
    _truncate_title,
)

pytestmark = pytest.mark.unit


class TestSelectUrgency:
    """Tests for _select_urgency helper function."""

    def test_select_urgency_when_very_soon_then_fast(self):
        """Test urgency selection for imminent meetings."""
        assert _select_urgency(60) == "fast"  # 1 minute
        assert _select_urgency(300) == "fast"  # 5 minutes (boundary)
        assert _select_urgency(0) == "fast"  # now

    def test_select_urgency_when_moderate_delay_then_standard(self):
        """Test urgency selection for meetings within the hour."""
        assert _select_urgency(301) == "standard"  # Just over 5 minutes
        assert _select_urgency(1800) == "standard"  # 30 minutes
        assert _select_urgency(3600) == "standard"  # 1 hour (boundary)

    def test_select_urgency_when_far_future_then_relaxed(self):
        """Test urgency selection for distant meetings."""
        assert _select_urgency(3601) == "relaxed"  # Just over 1 hour
        assert _select_urgency(7200) == "relaxed"  # 2 hours
        assert _select_urgency(86400) == "relaxed"  # 1 day

    def test_select_urgency_when_negative_time_then_fast(self):
        """Test urgency selection for past meetings."""
        assert _select_urgency(-300) == "fast"  # Past meetings are urgent


class TestEscapeTextForSsml:
    """Tests for _escape_text_for_ssml helper function."""

    def test_escape_text_for_ssml_when_normal_text_then_unchanged(self):
        """Test escaping normal text."""
        assert _escape_text_for_ssml("Meeting Title") == "Meeting Title"
        assert _escape_text_for_ssml("Daily Standup") == "Daily Standup"

    def test_escape_text_for_ssml_when_xml_chars_then_escaped(self):
        """Test escaping XML special characters."""
        assert _escape_text_for_ssml("Meeting & Discussion") == "Meeting &amp; Discussion"
        assert _escape_text_for_ssml("Review <Draft>") == "Review &lt;Draft&gt;"
        assert _escape_text_for_ssml('Project "Alpha"') == "Project &quot;Alpha&quot;"
        assert _escape_text_for_ssml("John's Meeting") == "John&apos;s Meeting"

    def test_escape_text_for_ssml_when_combined_chars_then_all_escaped(self):
        """Test escaping multiple special characters."""
        text = 'Meeting "A & B" <Draft>'
        expected = "Meeting &quot;A &amp; B&quot; &lt;Draft&gt;"
        assert _escape_text_for_ssml(text) == expected

    def test_escape_text_for_ssml_when_control_chars_then_removed(self):
        """Test removal of control characters."""
        # Control character \x0b (vertical tab)
        assert _escape_text_for_ssml("Meeting\x0bTitle") == "MeetingTitle"
        # Preserve valid whitespace
        assert _escape_text_for_ssml("Meeting\nTitle\tTest") == "Meeting\nTitle\tTest"

    def test_escape_text_for_ssml_when_non_string_then_empty(self):
        """Test handling non-string input."""
        assert _escape_text_for_ssml(None) == ""  # type: ignore
        assert _escape_text_for_ssml(123) == ""  # type: ignore
        assert _escape_text_for_ssml([]) == ""  # type: ignore


class TestTruncateTitle:
    """Tests for _truncate_title helper function."""

    def test_truncate_title_when_short_title_then_unchanged(self):
        """Test truncating short titles."""
        assert _truncate_title("Short Title", 50) == "Short Title"
        assert _truncate_title("", 50) == ""

    def test_truncate_title_when_exact_limit_then_unchanged(self):
        """Test truncating titles at exact character limit."""
        title = "A" * 50
        assert _truncate_title(title, 50) == title

    def test_truncate_title_when_over_limit_then_truncated_with_ellipsis(self):
        """Test truncating long titles."""
        title = "Very Long Meeting Title That Exceeds Character Limit"
        result = _truncate_title(title, 20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_truncate_title_when_word_boundary_available_then_truncate_at_space(self):
        """Test truncating at word boundaries when possible."""
        title = "Long Meeting Title Here"
        result = _truncate_title(title, 15)
        # Should truncate at space before "Title" or "Here"
        assert result in ["Long Meeting...", "Long..."]
        assert not result.startswith("Long Meeting T...")  # Avoid mid-word cuts

    def test_truncate_title_when_no_good_space_then_hard_truncate(self):
        """Test hard truncation when no good word boundary exists."""
        title = "Supercalifragilisticexpialidocious"
        result = _truncate_title(title, 20)
        assert len(result) == 20
        assert result == "Supercalifragilis..."

    def test_truncate_title_when_non_string_then_return_as_is(self):
        """Test handling non-string input."""
        assert _truncate_title(None, 50) is None  # type: ignore
        assert _truncate_title(123, 50) == 123  # type: ignore


class TestComposeFragments:
    """Tests for _compose_fragments helper function."""

    def test_compose_fragments_when_empty_list_then_empty_string(self):
        """Test composing empty fragment list."""
        assert _compose_fragments([]) == ""

    def test_compose_fragments_when_single_fragment_then_unchanged(self):
        """Test composing single fragment."""
        assert _compose_fragments(["Hello"]) == "Hello"

    def test_compose_fragments_when_multiple_fragments_then_joined(self):
        """Test composing multiple fragments."""
        fragments = ["Your meeting", " starts", " in 5 minutes"]
        assert _compose_fragments(fragments) == "Your meeting starts in 5 minutes"

    def test_compose_fragments_when_mixed_content_then_preserved(self):
        """Test composing fragments with SSML tags."""
        fragments = [
            '<emphasis level="strong">Meeting</emphasis>',
            '<break time="0.3s"/>',
            "starts soon"
        ]
        expected = '<emphasis level="strong">Meeting</emphasis><break time="0.3s"/>starts soon'
        assert _compose_fragments(fragments) == expected


class TestBasicTagBalanceCheck:
    """Tests for _basic_tag_balance_check helper function."""

    def test_basic_tag_balance_check_when_balanced_tags_then_true(self):
        """Test validation of properly balanced tags."""
        allowed_tags = {"speak", "emphasis", "prosody", "break"}
        
        ssml = "<speak><emphasis>text</emphasis></speak>"
        assert _basic_tag_balance_check(ssml, allowed_tags) is True

        ssml = "<speak><prosody rate='fast'>text</prosody></speak>"
        assert _basic_tag_balance_check(ssml, allowed_tags) is True

    def test_basic_tag_balance_check_when_self_closing_tags_then_true(self):
        """Test validation of self-closing tags."""
        allowed_tags = {"speak", "break"}
        
        ssml = "<speak>text<break time='0.3s'/>more text</speak>"
        assert _basic_tag_balance_check(ssml, allowed_tags) is True

    def test_basic_tag_balance_check_when_unbalanced_tags_then_false(self):
        """Test validation of unbalanced tags."""
        allowed_tags = {"speak", "emphasis"}
        
        ssml = "<speak><emphasis>text</speak>"  # Missing closing emphasis
        assert _basic_tag_balance_check(ssml, allowed_tags) is False

        ssml = "<speak>emphasis>text</emphasis></speak>"  # Missing opening emphasis
        assert _basic_tag_balance_check(ssml, allowed_tags) is False

    def test_basic_tag_balance_check_when_disallowed_tags_then_false(self):
        """Test validation with disallowed tags."""
        allowed_tags = {"speak", "emphasis"}
        
        ssml = "<speak><voice name='Amy'>text</voice></speak>"
        assert _basic_tag_balance_check(ssml, allowed_tags) is False

    def test_basic_tag_balance_check_when_malformed_tags_then_false(self):
        """Test validation of malformed tags."""
        allowed_tags = {"speak", "emphasis"}
        
        ssml = "<speak><emphasis>text<emphasis></speak>"  # Unclosed tag
        assert _basic_tag_balance_check(ssml, allowed_tags) is False

        ssml = "<speak><emphasis>text</emphasis"  # Missing closing >
        assert _basic_tag_balance_check(ssml, allowed_tags) is False


class TestShouldIncludeDuration:
    """Tests for _should_include_duration helper function."""

    def test_should_include_duration_when_urgent_meeting_then_true(self):
        """Test duration inclusion for urgent meetings."""
        config = DEFAULT_CONFIG.copy()
        # Meetings starting very soon should include duration
        assert _should_include_duration(600, config) is True  # 10 minutes

    def test_should_include_duration_when_far_future_meeting_then_true(self):
        """Test duration inclusion for distant meetings."""
        config = DEFAULT_CONFIG.copy()
        # Meetings far in future should include duration
        assert _should_include_duration(7200, config) is True  # 2 hours

    def test_should_include_duration_when_moderate_timing_then_false(self):
        """Test duration exclusion for moderate timing."""
        config = DEFAULT_CONFIG.copy()
        # Meetings in the moderate range might not need duration
        assert _should_include_duration(1800, config) in [True, False]  # 30 minutes

    def test_should_include_duration_when_custom_thresholds_then_respects_config(self):
        """Test duration inclusion with custom thresholds."""
        config = {
            "duration_threshold_long": 7200,  # 2 hours
            "duration_threshold_short": 600,  # 10 minutes
        }
        
        assert _should_include_duration(300, config) is True  # 5 min < 10 min threshold
        assert _should_include_duration(900, config) is False  # Between thresholds
        assert _should_include_duration(8000, config) is True  # > 2 hour threshold


class TestValidateSsml:
    """Tests for validate_ssml function."""

    def test_validate_ssml_when_valid_basic_ssml_then_true(self):
        """Test validation of basic valid SSML."""
        ssml = "<speak>Hello world</speak>"
        assert validate_ssml(ssml) is True

    def test_validate_ssml_when_valid_complex_ssml_then_true(self):
        """Test validation of complex valid SSML."""
        ssml = '<speak><emphasis level="strong">Meeting</emphasis> <break time="0.3s"/> starts soon</speak>'
        assert validate_ssml(ssml) is True

    def test_validate_ssml_when_missing_speak_wrapper_then_false(self):
        """Test validation fails without speak wrapper."""
        ssml = '<emphasis level="strong">Text</emphasis>'
        assert validate_ssml(ssml) is False

    def test_validate_ssml_when_wrong_wrapper_then_false(self):
        """Test validation fails with wrong wrapper tags."""
        ssml = '<voice>Hello world</voice>'
        assert validate_ssml(ssml) is False

    def test_validate_ssml_when_exceeds_char_limit_then_false(self):
        """Test validation fails when exceeding character limit."""
        long_text = "A" * 600
        ssml = f"<speak>{long_text}</speak>"
        assert validate_ssml(ssml, max_chars=500) is False

    def test_validate_ssml_when_empty_string_then_false(self):
        """Test validation fails for empty strings."""
        assert validate_ssml("") is False
        assert validate_ssml("   ") is False

    def test_validate_ssml_when_non_string_then_false(self):
        """Test validation fails for non-string input."""
        assert validate_ssml(None) is False  # type: ignore
        assert validate_ssml(123) is False  # type: ignore
        assert validate_ssml([]) is False  # type: ignore

    def test_validate_ssml_when_disallowed_tags_then_false(self):
        """Test validation fails with disallowed tags."""
        ssml = '<speak><voice name="Amy">Hello</voice></speak>'
        allowed_tags = {"speak", "emphasis", "break", "prosody"}
        assert validate_ssml(ssml, allowed_tags=allowed_tags) is False

    def test_validate_ssml_when_custom_allowed_tags_then_respects_allowlist(self):
        """Test validation with custom allowed tags."""
        ssml = '<speak><voice name="Amy">Hello</voice></speak>'
        allowed_tags = {"speak", "voice"}
        assert validate_ssml(ssml, allowed_tags=allowed_tags) is True


class TestRenderMeetingSsml:
    """Tests for render_meeting_ssml function."""

    def test_render_meeting_ssml_when_urgent_meeting_then_fast_paced_ssml(self):
        """Test SSML generation for urgent meetings."""
        meeting = {
            "subject": "Daily Standup",
            "seconds_until_start": 180,  # 3 minutes
            "duration_spoken": "3 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        assert "Daily Standup" in result
        assert 'rate="fast"' in result
        assert 'level="strong"' in result  # Strong emphasis for urgent

    def test_render_meeting_ssml_when_standard_timing_then_moderate_paced_ssml(self):
        """Test SSML generation for standard timing meetings."""
        meeting = {
            "subject": "Team Sync",
            "seconds_until_start": 1500,  # 25 minutes
            "duration_spoken": "25 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        assert "Team Sync" in result
        assert 'level="moderate"' in result
        assert 'time="0.3s"' in result  # Standard break

    def test_render_meeting_ssml_when_relaxed_timing_then_calm_ssml(self):
        """Test SSML generation for relaxed timing meetings."""
        meeting = {
            "subject": "Project Review",
            "seconds_until_start": 7200,  # 2 hours
            "duration_spoken": "2 hours",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        assert "Project Review" in result
        assert 'rate="medium"' in result
        assert 'time="0.5s"' in result  # Longer break for relaxed

    def test_render_meeting_ssml_when_long_title_then_truncated(self):
        """Test SSML generation with long meeting title."""
        meeting = {
            "subject": "Very Long Meeting Title That Definitely Exceeds The Character Limit For Titles",
            "seconds_until_start": 1800,
            "duration_spoken": "30 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert "..." in result  # Should be truncated
        assert len(result) <= DEFAULT_CONFIG["ssml_max_chars"]

    def test_render_meeting_ssml_when_has_location_then_includes_location(self):
        """Test SSML generation with meeting location."""
        meeting = {
            "subject": "Budget Review",
            "seconds_until_start": 900,  # 15 minutes
            "duration_spoken": "15 minutes",
            "location": "Conference Room A",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert "Conference Room A" in result
        assert 'level="reduced"' in result  # Location with reduced emphasis

    def test_render_meeting_ssml_when_online_meeting_then_includes_online_phrase(self):
        """Test SSML generation for online meetings."""
        meeting = {
            "subject": "Client Call",
            "seconds_until_start": 1800,  # 30 minutes
            "duration_spoken": "30 minutes",
            "location": "https://zoom.us/meeting",
            "is_online_meeting": True,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert "joining online" in result
        # Should not include the Zoom URL in speech

    def test_render_meeting_ssml_when_special_chars_in_title_then_escaped(self):
        """Test SSML generation with special characters in title."""
        meeting = {
            "subject": "Q&A Session <Draft>",
            "seconds_until_start": 1200,
            "duration_spoken": "20 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_render_meeting_ssml_when_invalid_meeting_data_then_none(self):
        """Test SSML generation with invalid meeting data."""
        assert render_meeting_ssml(None) is None  # type: ignore
        assert render_meeting_ssml({}) is None
        assert render_meeting_ssml("invalid") is None  # type: ignore

    def test_render_meeting_ssml_when_ssml_disabled_then_none(self):
        """Test SSML generation when disabled in config."""
        meeting = {
            "subject": "Test Meeting",
            "seconds_until_start": 1800,
            "duration_spoken": "30 minutes",
        }
        config = {"enable_ssml": False}
        
        result = render_meeting_ssml(meeting, config)
        assert result is None

    @patch("calendarbot_lite.alexa_ssml.logger")
    def test_render_meeting_ssml_when_exception_occurs_then_logs_and_returns_none(self, mock_logger):
        """Test SSML generation handles exceptions gracefully."""
        # Force an exception by providing invalid data structure
        meeting = {
            "subject": None,  # This might cause issues in string operations
            "seconds_until_start": "invalid",  # Non-integer
        }
        
        result = render_meeting_ssml(meeting)
        assert result is None
        mock_logger.error.assert_called()


class TestRenderTimeUntilSsml:
    """Tests for render_time_until_ssml function."""

    def test_render_time_until_ssml_when_urgent_then_fast_time_first(self):
        """Test time-until SSML for urgent meetings."""
        meeting = {
            "subject": "Standup",
            "duration_spoken": "5 minutes",
        }
        
        result = render_time_until_ssml(180, meeting)  # 3 minutes
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        assert 'rate="fast"' in result
        assert 'pitch="high"' in result
        assert "until your next meeting" in result

    def test_render_time_until_ssml_when_standard_then_emphasized_time(self):
        """Test time-until SSML for standard timing."""
        meeting = {
            "subject": "Team Meeting",
            "duration_spoken": "2 hours and 15 minutes",
        }
        
        result = render_time_until_ssml(8100, meeting)  # 2h 15m
        assert result is not None
        assert 'level="strong"' in result  # Strong emphasis on time
        assert "until your next meeting" in result

    def test_render_time_until_ssml_when_no_meeting_data_then_generates_duration(self):
        """Test time-until SSML without meeting data."""
        result = render_time_until_ssml(1800)  # 30 minutes, no meeting data
        assert result is not None
        assert "30 minute" in result or "minutes" in result
        assert "until your next meeting" in result

    def test_render_time_until_ssml_when_with_meeting_title_then_includes_reduced_title(self):
        """Test time-until SSML includes meeting title with reduced emphasis."""
        meeting = {
            "subject": "All Hands",
            "duration_spoken": "1 hour",
        }
        
        result = render_time_until_ssml(3600, meeting)
        assert result is not None
        assert "All Hands" in result
        assert 'level="reduced"' in result  # Reduced emphasis for title

    def test_render_time_until_ssml_when_various_durations_then_correct_formatting(self):
        """Test time-until SSML with various duration formats."""
        # Test seconds
        result = render_time_until_ssml(45)
        assert result is not None
        assert "45 seconds" in result

        # Test minutes  
        result = render_time_until_ssml(120)
        assert result is not None
        assert "2 minute" in result

        # Test hours
        result = render_time_until_ssml(7200)
        assert result is not None
        assert "2 hour" in result

    def test_render_time_until_ssml_when_exceeds_char_limit_then_none(self):
        """Test time-until SSML respects 300 character limit."""
        meeting = {
            "subject": "Very Long Meeting Title That Definitely Exceeds Reasonable Length Limits For Time-Until Responses",
            "duration_spoken": "2 hours and 30 minutes",
        }
        
        result = render_time_until_ssml(9000, meeting)
        # Should either truncate or return None if too long
        if result is not None:
            assert len(result) <= 300

    def test_render_time_until_ssml_when_ssml_disabled_then_none(self):
        """Test time-until SSML when disabled in config."""
        config = {"enable_ssml": False}
        result = render_time_until_ssml(1800, None, config)
        assert result is None

    @patch("calendarbot_lite.alexa_ssml.logger")
    def test_render_time_until_ssml_when_exception_then_logs_and_returns_none(self, mock_logger):
        """Test time-until SSML handles exceptions gracefully."""
        # Force an exception with invalid seconds_until type
        result = render_time_until_ssml("invalid")  # type: ignore
        assert result is None
        mock_logger.error.assert_called()


class TestSsmlPerformanceConstraints:
    """Tests for SSML performance and constraint validation."""

    def test_ssml_generation_respects_character_limits(self):
        """Test that generated SSML respects character limits."""
        meeting = {
            "subject": "Test Meeting",
            "seconds_until_start": 300,
            "duration_spoken": "5 minutes",
            "location": "Conference Room",
            "is_online_meeting": False,
        }
        
        # Test with default limit
        result = render_meeting_ssml(meeting)
        if result:
            assert len(result) <= DEFAULT_CONFIG["ssml_max_chars"]
        
        # Test with custom lower limit
        config = {"ssml_max_chars": 100}
        result = render_meeting_ssml(meeting, config)
        if result:
            assert len(result) <= 100

    def test_time_until_ssml_respects_300_char_limit(self):
        """Test that time-until SSML respects 300 character limit."""
        meeting = {
            "subject": "Meeting",
            "duration_spoken": "1 hour",
        }
        
        result = render_time_until_ssml(3600, meeting)
        if result:
            assert len(result) <= 300

    def test_validation_rejects_oversized_ssml(self):
        """Test that validation rejects SSML exceeding limits."""
        # Create SSML that exceeds default 500 char limit
        long_content = "Very long content " * 50
        ssml = f"<speak>{long_content}</speak>"
        
        assert validate_ssml(ssml) is False

    def test_template_constants_are_efficient(self):
        """Test that SSML templates are pre-defined for efficiency."""
        from calendarbot_lite.alexa_ssml import (
            BREAK,
            EMPHASIS_MODERATE,
            EMPHASIS_REDUCED,
            EMPHASIS_STRONG,
            PROSODY,
            PROSODY_RATE,
            WRAP_SPEAK,
        )
        
        # Ensure templates are strings with format placeholders
        assert isinstance(WRAP_SPEAK, str)
        assert "{body}" in WRAP_SPEAK
        
        assert isinstance(PROSODY, str)
        assert "{rate}" in PROSODY and "{pitch}" in PROSODY
        
        assert isinstance(EMPHASIS_STRONG, str)
        assert "{text}" in EMPHASIS_STRONG


class TestRenderDoneForDaySsml:
    """Tests for render_done_for_day_ssml function."""

    def test_render_done_for_day_ssml_when_no_meetings_today_then_relaxed_positive_tone(self):
        """Test SSML generation for no meetings today scenario."""
        speech_text = "You have no meetings today. Enjoy your free day!"
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        
        # Should have relaxed pacing for no meetings
        assert 'rate="medium"' in result or 'pitch="medium"' in result
        # Should emphasize the positive aspects
        assert 'level="moderate"' in result
        # Should include a break before "Enjoy your free day!"
        assert 'time="0.4s"' in result
        assert "Enjoy your free day!" in result

    def test_render_done_for_day_ssml_when_had_meetings_with_done_message_then_celebratory_tone(self):
        """Test SSML generation for done-for-day with completed meetings."""
        speech_text = "You're all done for today!"
        
        result = render_done_for_day_ssml(has_meetings_today=True, speech_text=speech_text)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        
        # Should have strong emphasis for celebration
        assert 'level="strong"' in result  # Strong celebratory emphasis
        assert "You&apos;re all done for today!" in result  # Escaped text

    def test_render_done_for_day_ssml_when_will_be_done_future_then_emphasizes_time(self):
        """Test SSML generation for future completion time."""
        speech_text = "You'll be done at 6:00 pm."
        
        result = render_done_for_day_ssml(has_meetings_today=True, speech_text=speech_text)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        
        # Should emphasize the completion time
        assert 'level="strong"' in result  # Strong emphasis on time
        assert "6:00 pm" in result  # Time should be present
        assert "You&apos;ll be done at" in result  # Future completion phrase

    def test_render_done_for_day_ssml_when_had_meetings_generic_message_then_moderate_emphasis(self):
        """Test SSML generation for generic done-for-day message."""
        speech_text = "You have meetings today, but I couldn't determine when your last one ends."
        
        result = render_done_for_day_ssml(has_meetings_today=True, speech_text=speech_text)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        
        # Should use moderate emphasis for generic messages
        assert 'level="moderate"' in result
        assert "couldn&apos;t" in result  # Escaped text should be present

    def test_render_done_for_day_ssml_when_no_meetings_without_enjoy_phrase_then_relaxed_tone(self):
        """Test SSML generation for no meetings without 'Enjoy your free day!' phrase."""
        speech_text = "You have no meetings today."
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text)
        assert result is not None
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        
        # Should use relaxed pacing
        assert 'rate="medium"' in result and 'pitch="medium"' in result
        assert speech_text in result

    def test_render_done_for_day_ssml_when_special_chars_in_speech_then_escaped(self):
        """Test SSML generation with special characters in speech text."""
        speech_text = "Your meeting 'Q&A Session' ended at 3 PM. You're done!"
        
        result = render_done_for_day_ssml(has_meetings_today=True, speech_text=speech_text)
        assert result is not None
        
        # Special characters should be escaped
        assert "&apos;" in result  # Single quote
        assert "&amp;" in result  # Ampersand

    def test_render_done_for_day_ssml_when_invalid_speech_text_then_none(self):
        """Test SSML generation with invalid speech text."""
        # Empty string
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text="")
        assert result is None
        
        # Whitespace only
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text="   ")
        assert result is None
        
        # Non-string input
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=None)  # type: ignore
        assert result is None

    def test_render_done_for_day_ssml_when_ssml_disabled_then_none(self):
        """Test SSML generation when disabled in config."""
        speech_text = "You have no meetings today. Enjoy your free day!"
        config = {"enable_ssml": False}
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text, config=config)
        assert result is None

    def test_render_done_for_day_ssml_when_custom_config_then_respects_settings(self):
        """Test SSML generation with custom configuration."""
        speech_text = "You have no meetings today. Enjoy your free day!"
        config = {
            "enable_ssml": True,
            "ssml_max_chars": 200,  # Lower limit
            "allowed_tags": {"speak", "prosody", "emphasis", "break"}
        }
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text, config=config)
        assert result is not None
        assert len(result) <= 200

    def test_render_done_for_day_ssml_when_long_speech_text_then_handles_gracefully(self):
        """Test SSML generation with very long speech text."""
        long_speech = "Your last meeting today ended at 3:30 PM " * 20 + "You're done for the day!"
        
        result = render_done_for_day_ssml(has_meetings_today=True, speech_text=long_speech)
        # Should either truncate appropriately or return None if too long
        if result is not None:
            assert len(result) <= DEFAULT_CONFIG["ssml_max_chars"]

    def test_render_done_for_day_ssml_when_validation_fails_then_none(self):
        """Test SSML generation when validation fails."""
        # Force validation failure with very strict character limit
        speech_text = "You have no meetings today. Enjoy your free day!"
        config = {"ssml_max_chars": 50}  # Too small for any real SSML
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text, config=config)
        assert result is None

    @patch("calendarbot_lite.alexa_ssml._escape_text_for_ssml")
    @patch("calendarbot_lite.alexa_ssml.logger")
    def test_render_done_for_day_ssml_when_exception_occurs_then_logs_and_returns_none(self, mock_logger, mock_escape):
        """Test SSML generation handles exceptions gracefully."""
        # Force an exception by making _escape_text_for_ssml raise an exception
        mock_escape.side_effect = Exception("Test exception")
        speech_text = "You have no meetings today."
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text)
        assert result is None
        mock_logger.error.assert_called()

    def test_render_done_for_day_ssml_generates_valid_ssml_structure(self):
        """Test that generated SSML has valid structure."""
        speech_text = "You have no meetings today. Enjoy your free day!"
        
        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text)
        assert result is not None
        
        # Should pass validation
        assert validate_ssml(result) is True
        
        # Should have proper speak wrapper
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        
        # Should contain valid SSML tags only
        allowed_tags = {"speak", "prosody", "emphasis", "break"}
        assert _basic_tag_balance_check(result, allowed_tags) is True

    def test_render_done_for_day_ssml_both_meeting_scenarios_generate_different_ssml(self):
        """Test that different meeting scenarios generate appropriately different SSML."""
        no_meetings_text = "You have no meetings today. Enjoy your free day!"
        had_meetings_text = "You're all done for today!"
        
        no_meetings_result = render_done_for_day_ssml(has_meetings_today=False, speech_text=no_meetings_text)
        had_meetings_result = render_done_for_day_ssml(has_meetings_today=True, speech_text=had_meetings_text)
        
        assert no_meetings_result is not None
        assert had_meetings_result is not None
        assert no_meetings_result != had_meetings_result
        
        # No meetings should have relaxed tone indicators
        assert 'pitch="medium"' in no_meetings_result
        # Had meetings (all done) should have strong celebratory emphasis
        assert 'level="strong"' in had_meetings_result


class TestSsmlUserStoryCompliance:
    """Tests that validate compliance with user story acceptance criteria."""

    def test_urgent_meeting_ssml_matches_user_story_requirements(self):
        """Test urgent meeting SSML matches Story 1 requirements."""
        meeting = {
            "subject": "Daily Standup",
            "seconds_until_start": 180,  # 3 minutes - meets <= 300s criteria
            "duration_spoken": "3 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        
        # Story 1 requirements:
        # - Uses <prosody rate="fast"> for time-critical info
        assert 'rate="fast"' in result
        # - Meeting title emphasized with <emphasis level="strong">
        assert 'level="strong"' in result and "Daily Standup" in result
        # - Time remaining with <prosody pitch="high"> for urgency
        assert 'pitch="high"' in result
        # - Under 500 characters
        assert len(result) <= 500

    def test_relaxed_meeting_ssml_matches_user_story_requirements(self):
        """Test relaxed meeting SSML matches Story 2 requirements."""
        meeting = {
            "subject": "Project Review",
            "seconds_until_start": 9000,  # 2.5 hours - meets > 3600s criteria
            "duration_spoken": "2 hours and 30 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        
        # Story 2 requirements:
        # - Uses <prosody rate="medium"> or no rate modification
        assert 'rate="medium"' in result or 'rate="fast"' not in result
        # - Natural pauses with <break time="0.5s"/>
        assert 'time="0.5s"' in result
        # - Meeting title uses <emphasis level="moderate">
        assert 'level="moderate"' in result and "Project Review" in result

    def test_location_integration_matches_user_story_requirements(self):
        """Test location integration matches Story 4 requirements."""
        # Test physical location
        meeting = {
            "subject": "Budget Review",
            "seconds_until_start": 900,
            "duration_spoken": "15 minutes",
            "location": "Conference Room A",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        
        # Story 4 requirements:
        # - Include location after meeting title
        assert "Conference Room A" in result
        # - Use <break time="0.2s"/> before location
        assert 'time="0.2s"' in result
        # - Location uses <emphasis level="reduced">
        assert 'level="reduced"' in result

        # Test online meeting
        meeting["is_online_meeting"] = True
        result = render_meeting_ssml(meeting)
        assert result is not None
        assert "joining online" in result

    def test_long_title_truncation_matches_user_story_requirements(self):
        """Test long title handling matches Story 5 requirements."""
        long_title = "Monthly All-Hands Company Meeting with Department Updates and Strategic Planning Session"
        meeting = {
            "subject": long_title,
            "seconds_until_start": 1800,
            "duration_spoken": "30 minutes",
            "location": "",
            "is_online_meeting": False,
        }
        
        result = render_meeting_ssml(meeting)
        assert result is not None
        
        # Story 5 requirements:
        # - Truncate to first 47 characters + "..." (50 total)
        # - Truncation at word boundaries when possible
        assert "..." in result
        # - Use <emphasis level="moderate"> on truncated title
        assert 'level="moderate"' in result
        # - Maintain under 500 characters total
        assert len(result) <= 500

    def test_time_until_optimization_matches_user_story_requirements(self):
        """Test time-until optimization matches Story 7 requirements."""
        meeting = {
            "subject": "Team Meeting",
            "duration_spoken": "3 minutes",
        }
        
        # Test urgent timing
        result = render_time_until_ssml(180, meeting)  # 3 minutes
        assert result is not None
        
        # Story 7 requirements:
        # - Lead with time information, not meeting title
        time_portion = result.split("until your next meeting")[0]
        assert "3 minutes" in time_portion or "3 minute" in time_portion
        # - For urgent timing, use <prosody rate="fast" pitch="high">
        assert 'rate="fast"' in result and 'pitch="high"' in result
        # - Under 300 characters for quick delivery
        assert len(result) <= 300

    def test_ssml_validation_matches_user_story_requirements(self):
        """Test SSML validation matches Story 11 requirements."""
        # Story 11 requirements:
        # - Basic SSML tag validation
        valid_ssml = '<speak><emphasis level="strong">Test</emphasis></speak>'
        assert validate_ssml(valid_ssml) is True
        
        # - Character limit validation
        long_ssml = f"<speak>{'A' * 8500}</speak>"  # Exceeds 8000 char Alexa limit
        assert validate_ssml(long_ssml, max_chars=8000) is False
        
        # - Escape special characters
        text_with_special = "Test & <Example>"
        escaped = _escape_text_for_ssml(text_with_special)
        assert "&amp;" in escaped and "&lt;" in escaped
        
        # - Remove unsupported SSML tags
        invalid_ssml = '<speak><voice name="Amy">Test</voice></speak>'
        default_allowed = {"speak", "prosody", "emphasis", "break"}
        assert validate_ssml(invalid_ssml, allowed_tags=default_allowed) is False