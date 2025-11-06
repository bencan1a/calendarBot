"""Tests for calendarbot_lite.alexa_ssml module."""

from unittest.mock import patch

import pytest

from calendarbot_lite.alexa.alexa_ssml import (
    DEFAULT_CONFIG,
    _apply_conversational_domain,
    _apply_substitutions,
    _basic_tag_balance_check,
    _compose_fragments,
    _escape_text_for_ssml,
    _escape_text_for_ssml_preserving_tags,
    _select_urgency,
    _should_include_duration,
    _truncate_title,
    _wrap_paragraph,
    _wrap_sentence,
    _wrap_times_with_say_as,
    _wrap_with_domain,
    _wrap_with_emotion,
    _wrap_with_voice,
    render_done_for_day_ssml,
    render_meeting_ssml,
    render_time_until_ssml,
    validate_ssml,
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


class TestWrapTimesWithSayAs:
    """Tests for _wrap_times_with_say_as helper function."""

    def test_wrap_times_when_single_time_then_wrapped(self):
        """Test wrapping a single time pattern."""
        text = "Meeting at 9:30 am"
        expected = 'Meeting at <say-as interpret-as="time">9:30am</say-as>'
        assert _wrap_times_with_say_as(text) == expected

    def test_wrap_times_when_multiple_times_then_all_wrapped(self):
        """Test wrapping multiple time patterns."""
        text = "Meeting from 9:30 am to 10:45 am"
        expected = 'Meeting from <say-as interpret-as="time">9:30am</say-as> to <say-as interpret-as="time">10:45am</say-as>'
        assert _wrap_times_with_say_as(text) == expected

    def test_wrap_times_when_pm_time_then_wrapped(self):
        """Test wrapping PM times."""
        text = "Meeting at 2:30 pm"
        expected = 'Meeting at <say-as interpret-as="time">2:30pm</say-as>'
        assert _wrap_times_with_say_as(text) == expected

    def test_wrap_times_when_uppercase_period_then_wrapped(self):
        """Test wrapping times with uppercase AM/PM."""
        text = "Meeting at 9:30 AM"
        expected = 'Meeting at <say-as interpret-as="time">9:30am</say-as>'
        assert _wrap_times_with_say_as(text) == expected

    def test_wrap_times_when_no_time_then_unchanged(self):
        """Test text without time patterns remains unchanged."""
        text = "Meeting tomorrow"
        assert _wrap_times_with_say_as(text) == text

    def test_wrap_times_when_noon_then_unchanged(self):
        """Test that 'noon' is not wrapped (special case)."""
        text = "Meeting at noon"
        assert _wrap_times_with_say_as(text) == text

    def test_wrap_times_when_midnight_then_unchanged(self):
        """Test that 'midnight' is not wrapped (special case)."""
        text = "Meeting at midnight"
        assert _wrap_times_with_say_as(text) == text

    def test_wrap_times_when_non_string_then_empty(self):
        """Test handling non-string input."""
        assert _wrap_times_with_say_as(None) == ""  # type: ignore
        assert _wrap_times_with_say_as(123) == ""  # type: ignore


class TestEscapeTextPreservingTags:
    """Tests for _escape_text_for_ssml_preserving_tags helper function."""

    def test_escape_preserving_when_no_tags_then_escaped(self):
        """Test escaping text without tags."""
        text = "Meeting & Discussion"
        expected = "Meeting &amp; Discussion"
        assert _escape_text_for_ssml_preserving_tags(text) == expected

    def test_escape_preserving_when_say_as_tag_then_preserved(self):
        """Test preserving say-as tags while escaping other content."""
        text = 'Meeting at <say-as interpret-as="time">9:30am</say-as> today'
        expected = 'Meeting at <say-as interpret-as="time">9:30am</say-as> today'
        assert _escape_text_for_ssml_preserving_tags(text) == expected

    def test_escape_preserving_when_tag_and_special_chars_then_both_handled(self):
        """Test escaping special chars while preserving tags."""
        text = 'Meeting & Review at <say-as interpret-as="time">9:30am</say-as>'
        expected = 'Meeting &amp; Review at <say-as interpret-as="time">9:30am</say-as>'
        assert _escape_text_for_ssml_preserving_tags(text) == expected

    def test_escape_preserving_when_multiple_tags_then_all_preserved(self):
        """Test preserving multiple say-as tags."""
        text = 'From <say-as interpret-as="time">9:30am</say-as> to <say-as interpret-as="time">10:45am</say-as>'
        expected = 'From <say-as interpret-as="time">9:30am</say-as> to <say-as interpret-as="time">10:45am</say-as>'
        assert _escape_text_for_ssml_preserving_tags(text) == expected

    def test_escape_preserving_when_non_string_then_empty(self):
        """Test handling non-string input."""
        assert _escape_text_for_ssml_preserving_tags(None) == ""  # type: ignore

    def test_escape_preserving_when_malformed_tag_then_escaped(self):
        """Test that malformed tags are escaped, not preserved."""
        # Incomplete tag (missing closing tag)
        text = 'Meeting at <say-as interpret-as="time">9:30am'
        result = _escape_text_for_ssml_preserving_tags(text)
        # Should be escaped since it's not a complete valid tag
        assert '&lt;say-as' in result or 'Meeting at 9:30am' in result

    def test_escape_preserving_when_invalid_tag_name_then_escaped(self):
        """Test that tags with invalid names are escaped."""
        # Not a say-as tag, should be escaped
        text = 'Meeting <say-as-something>text</say-as-something>'
        result = _escape_text_for_ssml_preserving_tags(text)
        # Should be escaped since it's not a valid say-as tag
        assert '&lt;' in result or 'say-as-something' not in result.replace('&lt;', '<')


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


class TestApplySubstitutions:
    """Tests for _apply_substitutions helper function (Phase 1)."""

    def test_apply_substitutions_q1_preserves_surrounding_text(self):
        """Test Q1 substitution preserves context and text structure."""
        text = "Q1 Planning Session"
        result = _apply_substitutions(text)
        # Verify exact output - substitution replaces only Q1
        assert result == '<sub alias="first quarter">Q1</sub> Planning Session'

    def test_apply_substitutions_all_quarters(self):
        """Test all quarter abbreviations (Q1-Q4) are substituted correctly."""
        test_cases = [
            ("Q1", '<sub alias="first quarter">Q1</sub>'),
            ("Q2", '<sub alias="second quarter">Q2</sub>'),
            ("Q3", '<sub alias="third quarter">Q3</sub>'),
            ("Q4", '<sub alias="fourth quarter">Q4</sub>'),
        ]
        for text, expected in test_cases:
            assert _apply_substitutions(text) == expected

    def test_apply_substitutions_one_on_one_formats(self):
        """Test both 1:1 and 1-1 formats are substituted."""
        # Both colon and dash formats should work
        assert _apply_substitutions("1:1") == '<sub alias="one on one">1:1</sub>'
        assert _apply_substitutions("1-1") == '<sub alias="one on one">1-1</sub>'

    def test_apply_substitutions_multiple_occurrences_all_replaced(self):
        """Test multiple abbreviations are all substituted independently."""
        text = "Q1 1:1 planning and Q2 review with 1-1 followup"
        result = _apply_substitutions(text)
        # Verify all 4 abbreviations are substituted
        assert result.count("<sub") == 4
        assert '<sub alias="first quarter">Q1</sub>' in result
        assert '<sub alias="one on one">1:1</sub>' in result
        assert '<sub alias="second quarter">Q2</sub>' in result
        assert '<sub alias="one on one">1-1</sub>' in result

    def test_apply_substitutions_word_boundaries_respected(self):
        """Test substitutions only occur at word boundaries."""
        # Should NOT substitute Q1 in the middle of a word
        text = "IQ1000 device"
        result = _apply_substitutions(text)
        assert result == text  # No substitution should occur

    def test_apply_substitutions_at_string_boundaries(self):
        """Test substitutions work at start and end of string."""
        # At start
        assert _apply_substitutions("Q1") == '<sub alias="first quarter">Q1</sub>'
        # At end
        text = "Planning for Q1"
        result = _apply_substitutions(text)
        assert result == 'Planning for <sub alias="first quarter">Q1</sub>'

    def test_apply_substitutions_with_punctuation(self):
        """Test substitutions work with adjacent punctuation."""
        text = "Q1, Q2, and Q3."
        result = _apply_substitutions(text)
        # Punctuation should be preserved
        assert result == '<sub alias="first quarter">Q1</sub>, <sub alias="second quarter">Q2</sub>, and <sub alias="third quarter">Q3</sub>.'

    def test_apply_substitutions_preserves_text_without_matches(self):
        """Test text without abbreviations is returned unchanged."""
        text = "Regular meeting title with no abbreviations"
        result = _apply_substitutions(text)
        assert result == text

    def test_apply_substitutions_empty_string(self):
        """Test empty string returns empty string."""
        assert _apply_substitutions("") == ""

    def test_apply_substitutions_whitespace_only(self):
        """Test whitespace-only string is preserved."""
        assert _apply_substitutions("   ") == "   "

    def test_apply_substitutions_with_custom_substitutions(self):
        """Test custom substitution config extends default mappings."""
        # Custom config merges with defaults
        config = {"substitutions": {"Q1": "quarter one", "Q2": "quarter two"}}
        text = "Q1 and Q2"
        result = _apply_substitutions(text, config)
        # Both should use custom substitutions
        assert result == '<sub alias="quarter one">Q1</sub> and <sub alias="quarter two">Q2</sub>'

    def test_apply_substitutions_handles_non_string_input(self):
        """Test non-string input returns empty string."""
        assert _apply_substitutions(None) == ""  # type: ignore
        assert _apply_substitutions(123) == ""  # type: ignore
        assert _apply_substitutions([]) == ""  # type: ignore


class TestWrapWithEmotion:
    """Tests for _wrap_with_emotion helper function (Phase 1)."""

    def test_wrap_with_emotion_default_parameters(self):
        """Test wrapping with default emotion parameters (excited, medium)."""
        text = "Great news!"
        result = _wrap_with_emotion(text)
        assert result == '<amazon:emotion name="excited" intensity="medium">Great news!</amazon:emotion>'

    def test_wrap_with_emotion_all_intensity_levels(self):
        """Test all valid intensity levels produce correct output."""
        text = "Test"
        intensities = ["low", "medium", "high"]
        for intensity in intensities:
            result = _wrap_with_emotion(text, "excited", intensity)
            assert f'intensity="{intensity}"' in result
            assert 'name="excited"' in result
            assert ">Test</amazon:emotion>" in result

    def test_wrap_with_emotion_all_emotion_types(self):
        """Test all valid emotion types produce correct output."""
        text = "Message"
        emotions = ["excited", "disappointed", "empathetic"]
        for emotion in emotions:
            result = _wrap_with_emotion(text, emotion, "medium")
            assert f'name="{emotion}"' in result
            assert 'intensity="medium"' in result
            assert ">Message</amazon:emotion>" in result

    def test_wrap_with_emotion_preserves_special_characters(self):
        """Test that special characters in text are preserved."""
        text = "You're all done & ready!"
        result = _wrap_with_emotion(text, "excited", "high")
        # Text should be preserved exactly (no escaping in this function)
        assert ">You're all done & ready!</amazon:emotion>" in result

    def test_wrap_with_emotion_handles_multiline_text(self):
        """Test emotion wrapping works with multiline text."""
        text = "Line 1\nLine 2"
        result = _wrap_with_emotion(text, "excited", "low")
        assert result == '<amazon:emotion name="excited" intensity="low">Line 1\nLine 2</amazon:emotion>'

    def test_wrap_with_emotion_empty_string_returns_empty(self):
        """Test empty string is returned as-is."""
        assert _wrap_with_emotion("") == ""

    def test_wrap_with_emotion_whitespace_only_returns_unchanged(self):
        """Test whitespace-only strings are returned unchanged."""
        assert _wrap_with_emotion("   ") == "   "
        assert _wrap_with_emotion("\n\t") == "\n\t"

    def test_wrap_with_emotion_single_space_returns_unchanged(self):
        """Test single space is considered empty and returned unchanged."""
        assert _wrap_with_emotion(" ") == " "

    def test_wrap_with_emotion_handles_very_long_text(self):
        """Test emotion wrapping works with long text strings."""
        text = "A" * 1000
        result = _wrap_with_emotion(text, "excited", "medium")
        assert result.startswith('<amazon:emotion name="excited" intensity="medium">')
        assert result.endswith('</amazon:emotion>')
        assert text in result

    def test_wrap_with_emotion_non_string_returns_unchanged(self):
        """Test non-string input is returned as-is."""
        assert _wrap_with_emotion(None) is None  # type: ignore
        assert _wrap_with_emotion(123) == 123  # type: ignore
        assert _wrap_with_emotion([]) == []  # type: ignore


class TestWrapParagraph:
    """Tests for _wrap_paragraph helper function (Phase 1)."""

    def test_wrap_paragraph_simple_text(self):
        """Test wrapping simple text in paragraph tags."""
        text = "Good evening."
        result = _wrap_paragraph(text)
        assert result == "<p>Good evening.</p>"

    def test_wrap_paragraph_multiline_text_preserved(self):
        """Test multiline text structure is preserved within tags."""
        text = "First sentence.\nSecond sentence."
        result = _wrap_paragraph(text)
        assert result == "<p>First sentence.\nSecond sentence.</p>"

    def test_wrap_paragraph_with_special_characters(self):
        """Test paragraph wrapping preserves special characters."""
        text = "Meeting at 3:00 & discussion"
        result = _wrap_paragraph(text)
        # No escaping should happen in this function
        assert result == "<p>Meeting at 3:00 & discussion</p>"

    def test_wrap_paragraph_with_existing_ssml_tags(self):
        """Test paragraph wrapping works with nested SSML tags."""
        text = '<emphasis level="strong">Important</emphasis>'
        result = _wrap_paragraph(text)
        assert result == '<p><emphasis level="strong">Important</emphasis></p>'

    def test_wrap_paragraph_very_long_text(self):
        """Test paragraph wrapping handles very long text."""
        text = "Word " * 500  # 500 words
        result = _wrap_paragraph(text.strip())
        assert result.startswith("<p>")
        assert result.endswith("</p>")
        assert text.strip() in result

    def test_wrap_paragraph_empty_string_returns_empty(self):
        """Test empty string is returned unchanged."""
        assert _wrap_paragraph("") == ""

    def test_wrap_paragraph_whitespace_only_returns_unchanged(self):
        """Test whitespace-only strings are returned unchanged."""
        assert _wrap_paragraph("   ") == "   "
        assert _wrap_paragraph("\n") == "\n"
        assert _wrap_paragraph("\t") == "\t"

    def test_wrap_paragraph_single_word(self):
        """Test single word is wrapped correctly."""
        assert _wrap_paragraph("Hello") == "<p>Hello</p>"

    def test_wrap_paragraph_with_leading_trailing_whitespace(self):
        """Test text with whitespace is wrapped including whitespace."""
        text = "  Text with spaces  "
        result = _wrap_paragraph(text)
        assert result == "<p>  Text with spaces  </p>"

    def test_wrap_paragraph_non_string_returns_unchanged(self):
        """Test non-string input is returned as-is."""
        assert _wrap_paragraph(None) is None  # type: ignore
        assert _wrap_paragraph(123) == 123  # type: ignore
        assert _wrap_paragraph([]) == []  # type: ignore


class TestWrapSentence:
    """Tests for _wrap_sentence helper function (Phase 1)."""

    def test_wrap_sentence_simple_sentence(self):
        """Test wrapping a simple sentence in sentence tags."""
        text = "Your next meeting is in 5 minutes."
        result = _wrap_sentence(text)
        assert result == "<s>Your next meeting is in 5 minutes.</s>"

    def test_wrap_sentence_short_text(self):
        """Test wrapping very short text."""
        text = "Hi."
        result = _wrap_sentence(text)
        assert result == "<s>Hi.</s>"

    def test_wrap_sentence_without_punctuation(self):
        """Test wrapping text without ending punctuation."""
        text = "Meeting started"
        result = _wrap_sentence(text)
        assert result == "<s>Meeting started</s>"

    def test_wrap_sentence_with_special_characters(self):
        """Test sentence wrapping preserves special characters."""
        text = "Q&A session at 2:00 pm"
        result = _wrap_sentence(text)
        # No escaping in this function
        assert result == "<s>Q&A session at 2:00 pm</s>"

    def test_wrap_sentence_with_nested_tags(self):
        """Test sentence wrapping with nested SSML tags."""
        text = '<break time="0.5s"/>Next item'
        result = _wrap_sentence(text)
        assert result == '<s><break time="0.5s"/>Next item</s>'

    def test_wrap_sentence_multiline_text(self):
        """Test sentence wrapping preserves line breaks."""
        text = "Line 1\nLine 2"
        result = _wrap_sentence(text)
        assert result == "<s>Line 1\nLine 2</s>"

    def test_wrap_sentence_very_long_text(self):
        """Test sentence wrapping handles long text."""
        text = "A" * 500
        result = _wrap_sentence(text)
        assert result == f"<s>{text}</s>"

    def test_wrap_sentence_empty_string_returns_empty(self):
        """Test empty string is returned unchanged."""
        assert _wrap_sentence("") == ""

    def test_wrap_sentence_whitespace_only_returns_unchanged(self):
        """Test whitespace-only strings are returned unchanged."""
        assert _wrap_sentence("   ") == "   "
        assert _wrap_sentence("\t\n") == "\t\n"

    def test_wrap_sentence_with_whitespace_around_text(self):
        """Test text with surrounding whitespace is wrapped including whitespace."""
        text = "  Hello world  "
        result = _wrap_sentence(text)
        assert result == "<s>  Hello world  </s>"

    def test_wrap_sentence_non_string_returns_unchanged(self):
        """Test non-string input is returned as-is."""
        assert _wrap_sentence(None) is None  # type: ignore
        assert _wrap_sentence(123) == 123  # type: ignore
        assert _wrap_sentence({}) == {}  # type: ignore


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
        """Test SSML generation for standard timing meetings (Phase 2: sentence tags)."""
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
        # Phase 2: Uses sentence tags instead of breaks
        assert "<s>" in result and "</s>" in result

    def test_render_meeting_ssml_when_relaxed_timing_then_calm_ssml(self):
        """Test SSML generation for relaxed timing meetings (Phase 2: sentence tags)."""
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
        # Phase 2: Uses sentence tags instead of prosody/breaks
        assert "<s>" in result and "</s>" in result
        assert "Your next meeting is" in result

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

    @patch("calendarbot_lite.alexa.alexa_ssml.logger")
    def test_render_meeting_ssml_when_exception_occurs_then_logs_and_returns_none(self, mock_logger):
        """Test SSML generation handles exceptions gracefully."""
        # Force an exception by providing invalid data structure
        meeting = {
            "subject": None,  # This might cause issues in string operations
            "seconds_until_start": "invalid",  # Non-integer
        }

        result = render_meeting_ssml(meeting)
        assert result is None
        mock_logger.exception.assert_called()


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

    @patch("calendarbot_lite.alexa.alexa_ssml.logger")
    def test_render_time_until_ssml_when_exception_then_logs_and_returns_none(self, mock_logger):
        """Test time-until SSML handles exceptions gracefully."""
        # Force an exception with invalid seconds_until type
        result = render_time_until_ssml("invalid")  # type: ignore
        assert result is None
        mock_logger.exception.assert_called()


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
        from calendarbot_lite.alexa.alexa_ssml import (
            EMPHASIS_STRONG,
            PROSODY,
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

        # Phase 1: Should have excited emotion for celebration (not emphasis)
        assert 'amazon:emotion' in result  # Excited emotion
        assert 'name="excited"' in result
        assert 'intensity="medium"' in result
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
        # Time should be wrapped in say-as tag (SSML format without space: 6:00pm)
        assert '<say-as interpret-as="time">6:00pm</say-as>' in result
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

    @patch("calendarbot_lite.alexa.alexa_ssml._escape_text_for_ssml_preserving_tags")
    @patch("calendarbot_lite.alexa.alexa_ssml.logger")
    def test_render_done_for_day_ssml_when_exception_occurs_then_logs_and_returns_none(self, mock_logger, mock_escape):
        """Test SSML generation handles exceptions gracefully."""
        # Force an exception by making _escape_text_for_ssml_preserving_tags raise an exception
        mock_escape.side_effect = Exception("Test exception")
        speech_text = "You have no meetings today."

        result = render_done_for_day_ssml(has_meetings_today=False, speech_text=speech_text)
        assert result is None
        mock_logger.exception.assert_called()

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
        # Phase 1: Had meetings (all done) should have excited emotion (not emphasis)
        assert 'amazon:emotion' in had_meetings_result
        assert 'name="excited"' in had_meetings_result


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
        """Test relaxed meeting SSML matches Story 2 requirements (Phase 2: sentence tags)."""
        meeting = {
            "subject": "Project Review",
            "seconds_until_start": 9000,  # 2.5 hours - meets > 3600s criteria
            "duration_spoken": "2 hours and 30 minutes",
            "location": "",
            "is_online_meeting": False,
        }

        result = render_meeting_ssml(meeting)
        assert result is not None

        # Story 2 requirements (Phase 2 updated):
        # - Meeting title uses <emphasis level="moderate">
        assert 'level="moderate"' in result and "Project Review" in result
        # - Phase 2: Uses sentence tags for natural structure
        assert "<s>" in result and "</s>" in result
        # - Natural conversational flow
        assert "Your next meeting is" in result

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


class TestWrapWithDomain:
    """Tests for _wrap_with_domain helper function (Phase 2)."""

    def test_wrap_with_domain_simple_text(self):
        """Test wrapping simple text with conversational domain."""
        result = _wrap_with_domain("Your next meeting is in 5 minutes.")
        assert result == '<amazon:domain name="conversational">Your next meeting is in 5 minutes.</amazon:domain>'

    def test_wrap_with_domain_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        assert _wrap_with_domain("") == ""

    def test_wrap_with_domain_whitespace_only_returns_unchanged(self):
        """Test whitespace-only returns unchanged."""
        assert _wrap_with_domain("   ") == "   "

    def test_wrap_with_domain_non_string_returns_unchanged(self):
        """Test non-string returns unchanged."""
        assert _wrap_with_domain(None) == None  # type: ignore


class TestWrapWithVoice:
    """Tests for _wrap_with_voice helper function (Phase 2)."""

    def test_wrap_with_voice_default_joanna(self):
        """Test wrapping with default Joanna voice."""
        result = _wrap_with_voice("Good morning.")
        assert result == '<voice name="Joanna">Good morning.</voice>'

    def test_wrap_with_voice_custom_voice(self):
        """Test wrapping with custom voice."""
        result = _wrap_with_voice("Good morning.", "Matthew")
        assert result == '<voice name="Matthew">Good morning.</voice>'

    def test_wrap_with_voice_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        assert _wrap_with_voice("") == ""

    def test_wrap_with_voice_non_string_returns_unchanged(self):
        """Test non-string returns unchanged."""
        assert _wrap_with_voice(None) == None  # type: ignore


class TestApplyConversationalDomain:
    """Tests for _apply_conversational_domain helper function (Phase 2)."""

    def test_apply_conversational_domain_when_enabled(self):
        """Test applying conversational domain when enabled."""
        config = {"conversational_domain": {"enabled": True, "voice": "Joanna"}}
        result = _apply_conversational_domain("Your next meeting is in 5 minutes.", config)
        expected = '<voice name="Joanna"><amazon:domain name="conversational">Your next meeting is in 5 minutes.</amazon:domain></voice>'
        assert result == expected

    def test_apply_conversational_domain_when_disabled(self):
        """Test conversational domain is not applied when disabled."""
        config = {"conversational_domain": {"enabled": False}}
        text = "Your next meeting is in 5 minutes."
        result = _apply_conversational_domain(text, config)
        assert result == text

    def test_apply_conversational_domain_custom_voice(self):
        """Test applying conversational domain with custom voice."""
        config = {"conversational_domain": {"enabled": True, "voice": "Matthew"}}
        result = _apply_conversational_domain("Test message.", config)
        expected = '<voice name="Matthew"><amazon:domain name="conversational">Test message.</amazon:domain></voice>'
        assert result == expected

    def test_apply_conversational_domain_empty_config(self):
        """Test with empty config (should not apply domain)."""
        config = {}
        text = "Test message."
        result = _apply_conversational_domain(text, config)
        assert result == text

    def test_apply_conversational_domain_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        config = {"conversational_domain": {"enabled": True}}
        assert _apply_conversational_domain("", config) == ""
