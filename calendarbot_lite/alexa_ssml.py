"""Enhanced SSML speech response generation for calendarbot_lite Alexa integration.

This module provides lightweight, string-based SSML generation optimized for Pi Zero 2W
performance constraints. Generates urgency-aware speech responses with proper SSML
validation and fallback handling.

Performance targets:
- Generation time: <100ms (target <50ms for urgent)
- Memory overhead: <1MB
- SSML length: <500 characters default
"""

import logging
import re
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# SSML template constants for performance optimization
WRAP_SPEAK = "<speak>{body}</speak>"
PROSODY = '<prosody rate="{rate}" pitch="{pitch}">{text}</prosody>'
PROSODY_RATE = '<prosody rate="{rate}">{text}</prosody>'
EMPHASIS_STRONG = '<emphasis level="strong">{text}</emphasis>'
EMPHASIS_MODERATE = '<emphasis level="moderate">{text}</emphasis>'
EMPHASIS_REDUCED = '<emphasis level="reduced">{text}</emphasis>'
BREAK = '<break time="{t}s"/>'

# Regex patterns for time detection and tag preservation (compiled once for performance)
# Pattern for times: H:MM am/pm or HH:MM am/pm
TIME_PATTERN = re.compile(r'\b(\d{1,2}):(\d{2})\s+(am|pm)\b', re.IGNORECASE)
# Pattern for say-as tags: <say-as ...>...</say-as>
SAY_AS_TAG_PATTERN = re.compile(r'(<say-as[^>]*>.*?</say-as>)', re.DOTALL)

# Configuration defaults
DEFAULT_CONFIG = {
    "enable_ssml": True,
    "ssml_max_chars": 500,
    "allowed_tags": {"speak", "prosody", "emphasis", "break", "say-as"},
    "duration_threshold_long": 3600,  # Include duration if >3600s (60 minutes)
    "duration_threshold_short": 900,  # Include duration if <900s (15 minutes)
    "title_max_chars": 50,
}

# Urgency thresholds (seconds)
URGENCY_FAST_THRESHOLD = 300  # 5 minutes
URGENCY_STANDARD_THRESHOLD = 3600  # 1 hour


def render_meeting_ssml(
    meeting: dict[str, Any], config: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Render full SSML for next-meeting intent with urgency-based pacing.

    Args:
        meeting: Meeting data dict with subject, seconds_until_start, duration_spoken,
                location, is_online_meeting, etc.
        config: Optional configuration overrides

    Returns:
        Complete SSML string (<speak>...</speak>) or None if generation/validation fails

    Raises:
        Exception: Logs errors and returns None for graceful fallback
    """
    try:
        if not meeting or not isinstance(meeting, dict):
            logger.warning("Invalid meeting data for SSML generation")
            return None

        # Merge config with defaults
        cfg = {**DEFAULT_CONFIG, **(config or {})}

        if not cfg.get("enable_ssml", True):
            return None

        # Extract meeting data
        subject = meeting.get("subject", "Untitled meeting")
        seconds_until = meeting.get("seconds_until_start", 0)
        duration_spoken = meeting.get("duration_spoken", "")
        location = meeting.get("location", "")
        is_online = meeting.get("is_online_meeting", False)

        # Determine urgency and build content
        urgency = _select_urgency(seconds_until)

        # Escape and truncate title
        safe_subject = _escape_text_for_ssml(subject)
        truncated_subject = _truncate_title(safe_subject, cfg["title_max_chars"])

        # Build SSML fragments based on urgency
        fragments = []

        if urgency == "fast":
            # Fast-paced urgent template
            emphasized_title = EMPHASIS_STRONG.format(text=truncated_subject)
            time_phrase = _escape_text_for_ssml(duration_spoken)
            urgent_time = PROSODY.format(rate="fast", pitch="high", text=time_phrase)

            body_text = f"Your meeting {emphasized_title} starts in {urgent_time}"
            fragments.append(PROSODY_RATE.format(rate="fast", text=body_text))

        elif urgency == "standard":
            # Standard pacing template
            emphasized_title = EMPHASIS_MODERATE.format(text=truncated_subject)
            time_phrase = _escape_text_for_ssml(duration_spoken)

            fragments.extend(
                [
                    f"Your meeting {emphasized_title}",
                    BREAK.format(t="0.3"),
                    f"starts {time_phrase}.",
                ]
            )

        else:  # relaxed
            # Relaxed pacing template
            emphasized_title = EMPHASIS_MODERATE.format(text=truncated_subject)
            time_phrase = _escape_text_for_ssml(duration_spoken)

            opening = f"Your next meeting is {emphasized_title}."
            timing = f"It starts {time_phrase}."

            fragments.extend(
                [
                    PROSODY.format(rate="medium", pitch="medium", text=opening),
                    BREAK.format(t="0.5"),
                    timing,
                ]
            )

        # Add location information if available
        if location and not is_online:
            safe_location = _escape_text_for_ssml(location)
            location_phrase = EMPHASIS_REDUCED.format(text=safe_location)
            fragments.extend([BREAK.format(t="0.2"), f"in {location_phrase}"])
        elif is_online:
            fragments.extend([BREAK.format(t="0.2"), "joining online"])

        # Note: Removed duration section as duration_spoken represents time until start,
        # not actual meeting duration. The timing is already included in the main message.

        # Compose final SSML
        body = _compose_fragments(fragments)
        ssml = WRAP_SPEAK.format(body=body)

        # Validate before returning
        if validate_ssml(ssml, cfg["ssml_max_chars"], cfg["allowed_tags"]):
            logger.debug("Generated meeting SSML: %d chars, urgency=%s", len(ssml), urgency)
            return ssml
        logger.warning("Meeting SSML validation failed, length=%d", len(ssml))
        return None

    except Exception as e:
        logger.error("SSML generation failed for meeting: %s", e, exc_info=True)
        return None


def render_time_until_ssml(
    seconds_until: int,
    meeting: Optional[dict[str, Any]] = None,
    config: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Render concise SSML for time-until-next intent (time-first approach).

    Args:
        seconds_until: Seconds until next meeting
        meeting: Optional meeting data for additional context
        config: Optional configuration overrides

    Returns:
        Complete SSML string (<speak>...</speak>) or None if generation/validation fails

    Raises:
        Exception: Logs errors and returns None for graceful fallback
    """
    try:
        # Merge config with defaults
        cfg = {**DEFAULT_CONFIG, **(config or {})}

        if not cfg.get("enable_ssml", True):
            return None

        # Use the duration helper directly from passed meeting data
        # to avoid circular import issues
        if meeting and meeting.get("duration_spoken"):
            duration_spoken = meeting["duration_spoken"]
        # Simple fallback duration formatting if no meeting data provided
        elif seconds_until < 60:
            duration_spoken = f"{seconds_until} seconds"
        elif seconds_until < 3600:
            minutes = seconds_until // 60
            duration_spoken = f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds_until // 3600
            remaining_minutes = (seconds_until % 3600) // 60
            if remaining_minutes == 0:
                duration_spoken = f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                duration_spoken = f"{hours} hour{'s' if hours != 1 else ''} and {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"

        # Determine urgency for time phrasing
        urgency = _select_urgency(seconds_until)

        fragments = []

        # Clean up duration_spoken for time-until phrasing
        # Remove "in " prefix if present since we'll reconstruct the sentence properly
        clean_duration = (
            duration_spoken.replace("in ", "", 1)
            if duration_spoken.startswith("in ")
            else duration_spoken
        )

        if urgency == "fast":
            # Urgent time-first response
            time_phrase = _escape_text_for_ssml(clean_duration)
            urgent_time = PROSODY.format(rate="fast", pitch="high", text=time_phrase)
            fragments.append(f"{urgent_time} until your next meeting.")

        else:
            # Standard/relaxed time response
            time_phrase = _escape_text_for_ssml(clean_duration)
            emphasized_time = EMPHASIS_STRONG.format(text=time_phrase)
            fragments.append(f"{emphasized_time} until your next meeting.")

        # Optionally add meeting title with reduced emphasis
        if meeting and meeting.get("subject"):
            subject = meeting.get("subject", "")
            safe_subject = _escape_text_for_ssml(subject)
            truncated_subject = _truncate_title(safe_subject, cfg["title_max_chars"])
            reduced_title = EMPHASIS_REDUCED.format(text=truncated_subject)

            fragments.extend([BREAK.format(t="0.2"), f"Your meeting is {reduced_title}."])

        # Compose final SSML
        body = _compose_fragments(fragments)
        ssml = WRAP_SPEAK.format(body=body)

        # Validate with stricter length limit for time-until responses
        max_chars = min(cfg["ssml_max_chars"], 300)  # User story requirement
        if validate_ssml(ssml, max_chars, cfg["allowed_tags"]):
            logger.debug("Generated time-until SSML: %d chars, urgency=%s", len(ssml), urgency)
            return ssml
        logger.warning("Time-until SSML validation failed, length=%d", len(ssml))
        return None

    except Exception as e:
        logger.error("SSML generation failed for time-until: %s", e, exc_info=True)
        return None


def render_done_for_day_ssml(
    has_meetings_today: bool, speech_text: str, config: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Render SSML for done-for-day intent with appropriate emphasis and pacing.

    Args:
        has_meetings_today: Whether there were meetings today
        speech_text: Plain text speech content to convert to SSML
        config: Optional configuration overrides

    Returns:
        Complete SSML string (<speak>...</speak>) or None if generation/validation fails

    Raises:
        Exception: Logs errors and returns None for graceful fallback
    """
    try:
        if not isinstance(speech_text, str) or not speech_text.strip():
            logger.warning("Invalid speech text for done-for-day SSML generation")
            return None

        # Merge config with defaults
        cfg = {**DEFAULT_CONFIG, **(config or {})}

        if not cfg.get("enable_ssml", True):
            return None

        # Wrap time patterns with <say-as> tags BEFORE escaping
        speech_with_times = _wrap_times_with_say_as(speech_text.strip())

        # Escape the speech text for SSML (preserving <say-as> tags)
        safe_speech = _escape_text_for_ssml_preserving_tags(speech_with_times)

        fragments = []

        if has_meetings_today:
            # Handle different meeting scenarios
            if "you&apos;ll be done at" in safe_speech.lower():
                # Future completion time - emphasize the time
                if " at " in safe_speech:
                    parts = safe_speech.split(" at ", 1)
                    if len(parts) == 2:
                        intro_part = parts[0]  # "You'll be done"
                        time_part = parts[1].rstrip(".")  # "6:00 pm"
                        fragments.extend(
                            [intro_part, " at ", EMPHASIS_STRONG.format(text=time_part), "."]
                        )
                    else:
                        fragments.append(PROSODY_RATE.format(rate="medium", text=safe_speech))
                else:
                    fragments.append(PROSODY_RATE.format(rate="medium", text=safe_speech))
            elif "you&apos;re all done for today" in safe_speech.lower():
                # Celebratory tone for being finished
                fragments.append(EMPHASIS_STRONG.format(text=safe_speech))
            elif "couldn&apos;t determine" in safe_speech.lower():
                # Error/uncertainty case - moderate emphasis
                fragments.append(EMPHASIS_MODERATE.format(text=safe_speech))
            else:
                # Generic meeting-related message with moderate emphasis
                fragments.append(EMPHASIS_MODERATE.format(text=safe_speech))
        # No meetings today - relaxed, positive tone
        elif "no meetings today" in safe_speech.lower():
            # Handle new launch intent format: "No meetings today, you're free until {meeting} {time}"
            if "you&apos;re free until" in safe_speech.lower():
                # Parse the launch intent format
                if " until " in safe_speech:
                    parts = safe_speech.split(" until ", 1)
                    if len(parts) == 2:
                        intro_part = parts[0].strip()  # "No meetings today, you're free"
                        meeting_part = parts[1].rstrip(".")  # "{meeting} {time}"

                        # Split meeting part to emphasize the meeting name
                        # Look for the last " in " to separate meeting name from time
                        if " in " in meeting_part:
                            meeting_time_parts = meeting_part.rsplit(" in ", 1)
                            if len(meeting_time_parts) == 2:
                                meeting_name = meeting_time_parts[0].strip()
                                time_part = meeting_time_parts[1].strip()

                                fragments.extend(
                                    [
                                        PROSODY.format(
                                            rate="medium", pitch="medium", text=intro_part
                                        ),
                                        " until ",
                                        EMPHASIS_MODERATE.format(text=meeting_name),
                                        BREAK.format(t="0.3"),
                                        f" in {time_part}.",
                                    ]
                                )
                            else:
                                # Fallback if parsing fails
                                fragments.append(
                                    PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                                )
                        else:
                            # Fallback if no " in " found
                            fragments.append(
                                PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                            )
                    else:
                        # Fallback if split fails
                        fragments.append(
                            PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                        )
                else:
                    # Fallback if no " until " found
                    fragments.append(
                        PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                    )
            # Split and emphasize the positive aspects for old format
            elif "Enjoy your free day!" in safe_speech:
                parts = safe_speech.split("Enjoy your free day!")
                if len(parts) == 2:
                    no_meetings_part = parts[0].strip().rstrip(".")
                    fragments.extend(
                        [
                            PROSODY.format(
                                rate="medium", pitch="medium", text=no_meetings_part + "."
                            ),
                            BREAK.format(t="0.4"),
                            EMPHASIS_MODERATE.format(text="Enjoy your free day!"),
                        ]
                    )
                else:
                    # Fallback
                    fragments.append(
                        PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                    )
            else:
                # Simple no meetings message
                fragments.append(PROSODY.format(rate="medium", pitch="medium", text=safe_speech))
        else:
            # Generic no meetings with relaxed pacing
            fragments.append(PROSODY_RATE.format(rate="medium", text=safe_speech))

        # Compose final SSML
        body = _compose_fragments(fragments)
        ssml = WRAP_SPEAK.format(body=body)

        # Validate before returning
        if validate_ssml(ssml, cfg["ssml_max_chars"], cfg["allowed_tags"]):
            logger.debug(
                "Generated done-for-day SSML: %d chars, has_meetings=%s",
                len(ssml),
                has_meetings_today,
            )
            return ssml
        logger.warning("Done-for-day SSML validation failed, length=%d", len(ssml))
        return None

    except Exception as e:
        logger.error("SSML generation failed for done-for-day: %s", e, exc_info=True)
        return None


def render_morning_summary_ssml(
    summary_result: Any, config: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Render SSML for morning summary with natural evening/night context.

    Args:
        summary_result: MorningSummaryResult object with speech text and analysis
        config: Optional configuration overrides

    Returns:
        Complete SSML string (<speak>...</speak>) or None if generation/validation fails

    Raises:
        Exception: Logs errors and returns None for graceful fallback
    """
    try:
        if not summary_result or not hasattr(summary_result, "speech_text"):
            logger.warning("Invalid summary result for morning summary SSML generation")
            return None

        # Merge config with defaults
        cfg = {**DEFAULT_CONFIG, **(config or {})}

        if not cfg.get("enable_ssml", True):
            return None

        # Extract speech text
        speech_text = summary_result.speech_text
        if not isinstance(speech_text, str) or not speech_text.strip():
            logger.warning("Invalid speech text for morning summary SSML")
            return None

        # Wrap time patterns with <say-as> tags BEFORE escaping
        speech_with_times = _wrap_times_with_say_as(speech_text.strip())

        # Escape the speech text for SSML (preserving <say-as> tags)
        safe_speech = _escape_text_for_ssml_preserving_tags(speech_with_times)

        fragments = []

        # Check for early start patterns and handle accordingly
        early_start_flag = getattr(summary_result, "early_start_flag", False)

        if early_start_flag and (
            "you start early" in safe_speech.lower() or "early at" in safe_speech.lower()
        ):
            # Handle early start with emphasis on urgency
            if "good evening" in safe_speech.lower():
                # Split greeting from content
                parts = safe_speech.split(".", 1)
                if len(parts) >= 2:
                    greeting_part = parts[0].strip() + "."
                    content_part = parts[1].strip()

                    fragments.extend(
                        [
                            PROSODY.format(rate="medium", pitch="medium", text=greeting_part),
                            BREAK.format(t="0.4"),
                        ]
                    )

                    # Emphasize early start information
                    if "you start early" in content_part.lower():
                        early_parts = content_part.split("you start early", 1)
                        if len(early_parts) == 2:
                            before_early = early_parts[0].strip()
                            after_early = early_parts[1].strip()

                            fragments.extend(
                                [
                                    before_early + " " if before_early else "",
                                    EMPHASIS_STRONG.format(text="You start early"),
                                    after_early,
                                ]
                            )
                        else:
                            fragments.append(EMPHASIS_MODERATE.format(text=content_part))
                    else:
                        fragments.append(EMPHASIS_MODERATE.format(text=content_part))
                else:
                    fragments.append(
                        PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                    )
            # No greeting, just emphasize early start
            elif "you start early" in safe_speech.lower():
                early_parts = safe_speech.split("you start early", 1)
                if len(early_parts) == 2:
                    before_early = early_parts[0].strip()
                    after_early = early_parts[1].strip()

                    fragments.extend(
                        [
                            before_early + " " if before_early else "",
                            EMPHASIS_STRONG.format(text="You start early"),
                            after_early,
                        ]
                    )
                else:
                    fragments.append(EMPHASIS_MODERATE.format(text=safe_speech))
            else:
                fragments.append(EMPHASIS_MODERATE.format(text=safe_speech))

        elif "completely free morning" in safe_speech.lower():
            # Handle free morning with positive emphasis
            if "good evening" in safe_speech.lower():
                parts = safe_speech.split(".", 1)
                if len(parts) >= 2:
                    greeting_part = parts[0].strip() + "."
                    content_part = parts[1].strip()

                    fragments.extend(
                        [
                            PROSODY.format(rate="medium", pitch="medium", text=greeting_part),
                            BREAK.format(t="0.4"),
                            EMPHASIS_MODERATE.format(text=content_part),
                        ]
                    )
                else:
                    fragments.append(
                        PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                    )
            # Emphasize the positive aspect of free time
            elif "completely free" in safe_speech.lower():
                free_parts = safe_speech.split("completely free", 1)
                if len(free_parts) == 2:
                    before_free = free_parts[0].strip()
                    after_free = free_parts[1].strip()

                    fragments.extend(
                        [
                            before_free + " " if before_free else "",
                            EMPHASIS_MODERATE.format(text="completely free"),
                            after_free,
                        ]
                    )
                else:
                    fragments.append(
                        PROSODY.format(rate="medium", pitch="medium", text=safe_speech)
                    )
            else:
                fragments.append(PROSODY.format(rate="medium", pitch="medium", text=safe_speech))

        # Standard morning summary - natural conversational flow
        elif "good evening" in safe_speech.lower():
            # Split greeting from content for natural pacing
            parts = safe_speech.split(".", 1)
            if len(parts) >= 2:
                greeting_part = parts[0].strip() + "."
                content_part = parts[1].strip()

                fragments.extend(
                    [
                        PROSODY.format(rate="medium", pitch="medium", text=greeting_part),
                        BREAK.format(t="0.3"),
                        content_part,
                    ]
                )
            else:
                fragments.append(PROSODY.format(rate="medium", pitch="medium", text=safe_speech))
        else:
            # No greeting, natural flow
            fragments.append(safe_speech)

        # Compose final SSML
        body = _compose_fragments(fragments)
        ssml = WRAP_SPEAK.format(body=body)

        # Validate before returning
        if validate_ssml(ssml, cfg["ssml_max_chars"], cfg["allowed_tags"]):
            logger.debug(
                "Generated morning summary SSML: %d chars, early_start=%s",
                len(ssml),
                early_start_flag,
            )
            return ssml
        logger.warning("Morning summary SSML validation failed, length=%d", len(ssml))
        return None

    except Exception as e:
        logger.error("SSML generation failed for morning summary: %s", e, exc_info=True)
        return None


def validate_ssml(ssml: str, max_chars: int = 500, allowed_tags: Optional[set[str]] = None) -> bool:
    """Fast, linear SSML validation for server-side safety.

    Args:
        ssml: SSML string to validate
        max_chars: Maximum allowed character length
        allowed_tags: Set of allowed SSML tag names (defaults to basic set)

    Returns:
        True if SSML is valid, False otherwise

    Raises:
        Exception: Logs validation failures and returns False
    """
    try:
        if not isinstance(ssml, str):
            logger.warning("SSML validation failed: not a string")
            return False

        # Basic trimming and empty check
        ssml_trimmed = ssml.strip()
        if not ssml_trimmed:
            logger.warning("SSML validation failed: empty string")
            return False

        # Must start and end with speak tags
        if not (ssml_trimmed.startswith("<speak>") and ssml_trimmed.endswith("</speak>")):
            logger.warning("SSML validation failed: missing <speak> wrapper tags")
            return False

        # Length check
        if len(ssml) > max_chars:
            logger.warning(
                "SSML validation failed: exceeds %d char limit (%d)", max_chars, len(ssml)
            )
            return False

        # Tag balance and allowlist check
        default_allowed = {"speak", "prosody", "emphasis", "break", "say-as"}
        tags_allowed = allowed_tags or default_allowed

        if not _basic_tag_balance_check(ssml_trimmed, tags_allowed):
            logger.warning("SSML validation failed: tag balance or allowlist violation")
            return False

        return True

    except Exception as e:
        logger.error("SSML validation error: %s", e, exc_info=True)
        return False


# Internal helper functions


def _wrap_times_with_say_as(text: str) -> str:
    """Wrap time patterns in text with SSML <say-as interpret-as="time"> tags.

    This function detects time patterns like "9:30 am", "12:00 pm", "noon" in plain text
    and wraps them with SSML tags for natural Alexa pronunciation.

    Args:
        text: Plain text containing time references

    Returns:
        Text with time patterns wrapped in <say-as> tags

    Examples:
        >>> _wrap_times_with_say_as("Meeting at 9:30 am")
        'Meeting at <say-as interpret-as="time">9:30am</say-as>'
        >>> _wrap_times_with_say_as("noon meeting")
        'noon meeting'  # noon doesn't need say-as tag
    """
    if not isinstance(text, str):
        return ""

    def replace_time(match: re.Match[str]) -> str:
        hour = match.group(1)
        minute = match.group(2)
        period = match.group(3).lower()
        # SSML format: no space before am/pm per Alexa SSML spec
        time_str = f"{hour}:{minute}{period}"
        return f'<say-as interpret-as="time">{time_str}</say-as>'

    return TIME_PATTERN.sub(replace_time, text)


def _select_urgency(seconds_until: int) -> Literal["fast", "standard", "relaxed"]:
    """Select urgency level based on time until meeting.

    Args:
        seconds_until: Seconds until meeting starts

    Returns:
        Urgency level: 'fast', 'standard', or 'relaxed'
    """
    if seconds_until <= URGENCY_FAST_THRESHOLD:
        return "fast"
    if seconds_until <= URGENCY_STANDARD_THRESHOLD:
        return "standard"
    return "relaxed"


def _escape_xml_chars(text: str) -> str:
    """Escape XML special characters in text.

    Args:
        text: Text to escape

    Returns:
        Text with XML special characters escaped
    """
    escaped = text.replace("&", "&amp;")
    escaped = escaped.replace("<", "&lt;")
    escaped = escaped.replace(">", "&gt;")
    escaped = escaped.replace('"', "&quot;")
    escaped = escaped.replace("'", "&apos;")
    # Remove control characters that could break SSML
    return "".join(char for char in escaped if ord(char) >= 32 or char in ["\n", "\t"])


def _escape_text_for_ssml_preserving_tags(text: str) -> str:
    """Escape special characters in text for safe SSML inclusion while preserving SSML tags.

    This function escapes XML special characters but preserves legitimate SSML tags
    like <say-as> that have been intentionally added.

    Args:
        text: Text with potential SSML tags to escape

    Returns:
        SSML-safe text with escaped characters but preserved tags
    """
    if not isinstance(text, str):
        return ""

    # Split text into tag and non-tag segments using pre-compiled pattern
    segments = SAY_AS_TAG_PATTERN.split(text)

    result_segments = []
    for segment in segments:
        # Check if this segment is a complete say-as tag by verifying it matches the pattern
        if segment and SAY_AS_TAG_PATTERN.match(segment):
            # This is a complete, valid say-as tag - preserve it as is
            result_segments.append(segment)
        else:
            # This is regular text - escape it using shared logic
            result_segments.append(_escape_xml_chars(segment))

    return "".join(result_segments)


def _escape_text_for_ssml(text: str) -> str:
    """Escape special characters in text for safe SSML inclusion.

    Args:
        text: Raw text to escape

    Returns:
        SSML-safe text with escaped characters
    """
    if not isinstance(text, str):
        return ""

    return _escape_xml_chars(text)


def _truncate_title(text: str, max_chars: int = 50) -> str:
    """Truncate title at word boundaries when possible.

    Args:
        text: Text to truncate
        max_chars: Maximum character limit (default 50)

    Returns:
        Truncated text with "..." suffix if needed
    """
    if not isinstance(text, str) or len(text) <= max_chars:
        return text

    # Reserve 3 characters for "..."
    truncate_at = max_chars - 3

    # Try to find last space before the limit
    space_pos = text.rfind(" ", 0, truncate_at)
    if space_pos > max_chars // 2:  # Only use space if it's not too early
        return text[:space_pos] + "..."
    return text[:truncate_at] + "..."


def _compose_fragments(fragments: list[str]) -> str:
    """Efficiently compose SSML fragments into final body.

    Args:
        fragments: List of SSML fragment strings

    Returns:
        Composed SSML body content
    """
    if not fragments:
        return ""

    return "".join(fragments)


def _basic_tag_balance_check(ssml: str, allowed_tags: set[str]) -> bool:
    """Perform basic tag balance validation using simple stack-based checking.

    Args:
        ssml: SSML string to check
        allowed_tags: Set of allowed tag names

    Returns:
        True if tags are balanced and allowed, False otherwise
    """
    tag_stack: list[str] = []
    i = 0

    while i < len(ssml):
        if ssml[i] == "<":
            # Find the end of the tag
            end = ssml.find(">", i)
            if end == -1:
                return False  # Malformed tag

            tag_content = ssml[i + 1 : end]

            # Skip self-closing tags (like <break time="0.3s"/>)
            if tag_content.endswith("/"):
                tag_name = tag_content[:-1].strip().split()[0]
                if tag_name not in allowed_tags:
                    return False
                i = end + 1
                continue

            # Handle closing tags
            if tag_content.startswith("/"):
                tag_name = tag_content[1:].strip()
                if not tag_stack or tag_stack[-1] != tag_name:
                    return False  # Unmatched closing tag
                tag_stack.pop()
            else:
                # Opening tag - extract tag name (before any attributes)
                tag_name = tag_content.split()[0]
                if tag_name not in allowed_tags:
                    return False
                tag_stack.append(tag_name)

            i = end + 1
        else:
            i += 1

    # All tags should be closed
    return len(tag_stack) == 0


def _should_include_duration(seconds_until: int, config: dict[str, Any]) -> bool:
    """Determine if duration should be included based on meeting length thresholds.

    Args:
        seconds_until: Seconds until meeting
        config: Configuration with duration thresholds

    Returns:
        True if duration should be included in speech
    """
    # Note: This is a placeholder - actual duration would come from meeting data
    # For now, we include duration for urgent meetings as they might be short
    # and for very long meetings (>1 hour away) as they might be long

    long_threshold = config.get("duration_threshold_long", 3600)
    short_threshold = config.get("duration_threshold_short", 900)

    return seconds_until <= short_threshold or seconds_until > long_threshold
