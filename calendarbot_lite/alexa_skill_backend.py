"""
Amazon Alexa Skill Backend for CalendarBot Lite Integration

This module provides an AWS Lambda handler that integrates with calendarbot_lite
to answer calendar queries via Alexa voice interface.

Usage:
- Deploy as AWS Lambda function
- Configure CALENDARBOT_ENDPOINT and CALENDARBOT_BEARER_TOKEN environment variables
- Register as Alexa Custom Skill endpoint

Supported Intents:
- GetNextMeetingIntent: "What's my next meeting?"
- GetTimeUntilNextMeetingIntent: "How long until my next meeting?"
"""

import json
import logging
import os
import urllib.error

# Lightweight HTTP client - using urllib to avoid external dependencies
import urllib.request
from typing import Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration from environment variables
CALENDARBOT_ENDPOINT = os.environ.get("CALENDARBOT_ENDPOINT", "")
CALENDARBOT_BEARER_TOKEN = os.environ.get("CALENDARBOT_BEARER_TOKEN", "")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))


def get_default_timezone() -> str:
    """Get default timezone from environment with validation.

    Returns:
        Valid IANA timezone string (defaults to America/Los_Angeles)

    Note:
        This function validates the timezone and falls back gracefully
        if the configured timezone is invalid.
    """
    import zoneinfo

    # Get timezone from environment, default to Pacific time
    timezone = os.environ.get("CALENDARBOT_DEFAULT_TIMEZONE", "America/Los_Angeles")

    # Validate timezone
    try:
        zoneinfo.ZoneInfo(timezone)
        return timezone
    except Exception:
        logger.warning("Invalid timezone %r, falling back to America/Los_Angeles", timezone)
        return "America/Los_Angeles"


class AlexaResponse:
    """Helper class to build Alexa response format with SSML support."""

    def __init__(
        self,
        speech_text: str,
        should_end_session: bool = True,
        reprompt_text: Optional[str] = None,
        card_title: str = "Next Meeting",
        ssml: Optional[str] = None,
    ):
        self.speech_text = speech_text
        self.should_end_session = should_end_session
        self.reprompt_text = reprompt_text
        self.card_title = card_title
        self.ssml = ssml

    def to_dict(self) -> dict[str, Any]:
        # Prefer SSML if available and valid, otherwise use plain text
        output_speech = self._build_output_speech()

        resp: dict[str, Any] = {
            "version": "1.0",
            "sessionAttributes": {},
            "response": {
                "outputSpeech": output_speech,
                "card": {
                    "type": "Simple",
                    "title": self.card_title or "Calendar Bot Says...",
                    "content": self.speech_text,  # Card always uses plain text
                },
                "shouldEndSession": self.should_end_session,
            },
        }
        if not self.should_end_session:
            # Reprompt is recommended when the session stays open
            reprompt = self.reprompt_text or "You can ask, what's my next meeting?"
            resp["response"]["reprompt"] = {"outputSpeech": {"type": "PlainText", "text": reprompt}}
        return resp

    def _build_output_speech(self) -> dict[str, Any]:
        """Build outputSpeech section, preferring SSML when available."""
        if self.ssml and self._validate_ssml(self.ssml):
            logger.info("Using SSML for speech output")
            return {"type": "SSML", "ssml": self.ssml}
        else:  # noqa: RET505
            if self.ssml:
                logger.warning("SSML validation failed, falling back to PlainText")
            return {"type": "PlainText", "text": self.speech_text}

    def _validate_ssml(self, ssml: str) -> bool:
        """Basic SSML validation for Lambda use."""
        if not isinstance(ssml, str):
            return False

        # Must start and end with speak tags
        ssml_stripped = ssml.strip()
        if not (ssml_stripped.startswith("<speak>") and ssml_stripped.endswith("</speak>")):
            logger.warning("SSML validation failed: missing <speak> tags")
            return False

        # Basic length check (avoid overly long SSML)
        if len(ssml) > 8000:  # Alexa SSML limit is ~8KB
            logger.warning("SSML validation failed: exceeds length limit")
            return False

        return True


def call_calendarbot_api(endpoint_path: str) -> dict[str, Any]:
    """Call calendarbot_lite API endpoint with authentication.

    Args:
        endpoint_path: API path (e.g., "/api/alexa/next-meeting")

    Returns:
        JSON response from API

    Raises:
        Exception: On HTTP error or timeout
    """
    if not CALENDARBOT_ENDPOINT:
        raise ValueError("CALENDARBOT_ENDPOINT environment variable not set")

    if not CALENDARBOT_BEARER_TOKEN:
        raise ValueError("CALENDARBOT_BEARER_TOKEN environment variable not set")

    url = urljoin(CALENDARBOT_ENDPOINT.rstrip("/") + "/", endpoint_path.lstrip("/"))

    # Create request with bearer token
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {CALENDARBOT_BEARER_TOKEN}")
    request.add_header("User-Agent", "AlexaSkill/1.0 CalendarBot")

    try:
        logger.info("Calling calendarbot API: %s", url)
        response = urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT)  # nosec

        if response.status == 200:
            data = json.loads(response.read().decode("utf-8"))
            logger.info("API response received: status=%d", response.status)
            logger.info("API response data: %s", json.dumps(data))
            return data
        logger.error("API returned non-200 status: %d", response.status)
        raise Exception(f"API returned status {response.status}")  # noqa: TRY002

    except urllib.error.HTTPError as e:
        logger.exception("HTTP error calling API: %d %s", e.code, e.reason)
        if e.code == 401:
            raise Exception("Authentication failed - check bearer token")  # noqa: B904, TRY002
        raise Exception(f"API request failed: {e.code} {e.reason}")  # noqa: B904, TRY002

    except urllib.error.URLError as e:
        logger.exception("URL error calling API: %s", e.reason)
        raise Exception(f"Cannot reach calendarbot server: {e.reason}")  # noqa: B904, TRY002

    except Exception:
        logger.exception("Unexpected error calling API")
        raise


def handle_get_next_meeting_intent() -> AlexaResponse:
    """Handle GetNextMeetingIntent - returns next meeting info with SSML support."""
    try:
        data = call_calendarbot_api("/api/alexa/next-meeting")

        # Extract speech text and SSML from response
        if data.get("meeting") is None:
            speech_text = data.get("speech_text", "You have no upcoming meetings.")
            ssml = data.get("ssml")  # Top-level SSML for no meetings
        else:
            meeting = data["meeting"]
            speech_text = meeting.get("speech_text", "You have a meeting coming up.")
            ssml = meeting.get("ssml")  # Meeting-level SSML

        logger.info("Extracted speech text: %s", speech_text)
        if ssml:
            logger.info("Extracted SSML: %s", ssml)

        alexa_response = AlexaResponse(speech_text, ssml=ssml)
        logger.info("Alexa response: %s", json.dumps(alexa_response.to_dict()))
        return alexa_response

    except Exception:
        logger.exception("Error in GetNextMeetingIntent")
        return AlexaResponse(
            "Sorry, I'm having trouble accessing your calendar right now. Please try again later."
        )


def handle_get_time_until_next_meeting_intent() -> AlexaResponse:
    """Handle GetTimeUntilNextMeetingIntent - returns time until next meeting with SSML support."""
    try:
        data = call_calendarbot_api("/api/alexa/time-until-next")

        # Extract speech text and SSML from response
        speech_text = data.get("speech_text", "You have no upcoming meetings.")
        ssml = data.get("ssml")  # SSML for time-until response

        logger.info("Extracted speech text: %s", speech_text)
        if ssml:
            logger.info("Extracted SSML: %s", ssml)

        return AlexaResponse(speech_text, ssml=ssml)

    except Exception:
        logger.exception("Error in GetTimeUntilNextMeetingIntent")
        return AlexaResponse(
            "Sorry, I'm having trouble accessing your calendar right now. Please try again later."
        )


def handle_get_done_for_day_intent() -> AlexaResponse:
    """Handle GetDoneForDayIntent - returns done for the day summary with SSML support."""
    try:
        data = call_calendarbot_api("/api/alexa/done-for-day")

        # Extract speech text and SSML from response
        speech_text = data.get("speech_text", "You have no meetings today.")
        ssml = data.get("ssml")  # SSML for done-for-day response

        logger.info("Extracted speech text: %s", speech_text)
        if ssml:
            logger.info("Extracted SSML: %s", ssml)

        return AlexaResponse(speech_text, ssml=ssml, card_title="Done For The Day")

    except Exception:
        logger.exception("Error in GetDoneForDayIntent")
        return AlexaResponse(
            "Sorry, I'm having trouble accessing your calendar right now. Please try again later."
        )


def handle_launch_intent() -> AlexaResponse:
    """Handle LaunchRequest with intelligent context switching.

    During the day (when there are still meetings left today):
    - Use existing behavior: call /api/alexa/launch-summary for current day info

    After current day's meetings are done:
    - Switch to morning summary mode for next day preparation
    - Call /api/alexa/morning-summary to preview tomorrow's schedule
    """
    try:
        # First, get current day status to determine switching logic
        launch_data = call_calendarbot_api("/api/alexa/launch-summary")

        # Check if there are remaining meetings today
        has_meetings_today = launch_data.get("has_meetings_today", False)
        next_meeting = launch_data.get("next_meeting")

        # Intelligent switching logic:
        # If no meetings today OR no more meetings today, switch to morning summary
        if not has_meetings_today or (has_meetings_today and not next_meeting):
            logger.info("Launch Intent: Switching to morning summary mode (done for today)")

            try:
                # Switch to morning summary for next day preparation
                import zoneinfo
                from datetime import datetime, timedelta

                # Calculate tomorrow's date
                now = datetime.now(zoneinfo.ZoneInfo("UTC"))
                tomorrow = now + timedelta(days=1)
                tomorrow_date = tomorrow.strftime("%Y-%m-%d")

                # Call morning summary endpoint with appropriate parameters
                from urllib.parse import urlencode

                query_params = {
                    "date": tomorrow_date,
                    "timezone": get_default_timezone(),
                    "prefer_ssml": "true",
                    "detail_level": "normal",
                    "max_events": "50",
                }
                morning_summary_url = f"/api/alexa/morning-summary?{urlencode(query_params)}"
                morning_data = call_calendarbot_api(morning_summary_url)

                # Extract speech text and SSML from morning summary response
                speech_text = morning_data.get(
                    "speech_text", "I couldn't generate your morning summary."
                )
                ssml = morning_data.get("ssml")

                logger.info("Morning summary speech text: %s", speech_text)
                if ssml:
                    logger.info("Morning summary SSML generated: %d characters", len(ssml))

                return AlexaResponse(speech_text, ssml=ssml, card_title="Tomorrow Morning Summary")

            except Exception as e:
                logger.warning(
                    "Failed to get morning summary, falling back to launch summary: %s", e
                )
                # Fall back to regular launch summary if morning summary fails
                speech_text = launch_data.get(
                    "speech_text", "I couldn't get your calendar information."
                )
                ssml = launch_data.get("ssml")
                return AlexaResponse(speech_text, ssml=ssml, card_title="Calendar Summary")

        else:
            # Still have meetings today - use existing launch summary behavior
            logger.info("Launch Intent: Using current day mode (meetings remaining today)")

            speech_text = launch_data.get(
                "speech_text", "I couldn't get your calendar information."
            )
            ssml = launch_data.get("ssml")  # SSML for launch summary response

            logger.info("Extracted launch summary speech text: %s", speech_text)
            if ssml:
                logger.info("Extracted launch summary SSML: %d characters", len(ssml))

            return AlexaResponse(speech_text, ssml=ssml, card_title="Calendar Summary")

    except Exception:
        logger.exception("Error in LaunchRequest")
        return AlexaResponse(
            "Sorry, I'm having trouble accessing your calendar right now. Please try again later."
        )


def handle_help_intent() -> AlexaResponse:
    """Handle AMAZON.HelpIntent."""
    speech_text = (
        "I can help you with your calendar. You can ask me things like: "
        "What's my next meeting? Or, how long until my next meeting?"
    )
    return AlexaResponse(speech_text, should_end_session=False)


def handle_stop_intent() -> AlexaResponse:
    """Handle AMAZON.StopIntent and AMAZON.CancelIntent."""
    return AlexaResponse("Goodbye!")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """AWS Lambda handler for Alexa skill requests.

    Args:
        event: Alexa request event
        context: Lambda context (unused)

    Returns:
        Alexa response dictionary
    """
    try:
        logger.info("Received Alexa request: %s", json.dumps(event, default=str))

        # Validate request structure
        if "request" not in event:
            logger.error("Invalid request: missing 'request' field")
            return AlexaResponse("Sorry, I received an invalid request.").to_dict()

        request = event["request"]
        request_type = request.get("type")

        if request_type == "LaunchRequest":
            alexa_response = handle_launch_intent().to_dict()
            logger.info("Lambda returning launch response: %s", json.dumps(alexa_response))
            return alexa_response

        if request_type == "IntentRequest":
            intent_name = request.get("intent", {}).get("name")

            if intent_name == "GetNextMeetingIntent":
                alexa_response = handle_get_next_meeting_intent().to_dict()
                logger.info("Lambda returning response: %s", json.dumps(alexa_response))
                return alexa_response

            if intent_name == "GetTimeUntilNextMeetingIntent":
                return handle_get_time_until_next_meeting_intent().to_dict()

            if intent_name == "GetDoneForDayIntent":
                return handle_get_done_for_day_intent().to_dict()

            if intent_name == "AMAZON.HelpIntent":
                return handle_help_intent().to_dict()

            if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
                return handle_stop_intent().to_dict()

            logger.warning("Unknown intent: %s", intent_name)
            speech_text = (
                "I don't understand that request. You can ask me what's your next meeting, "
                "how long until your next meeting, or if you're done for the day."
            )
            return AlexaResponse(speech_text).to_dict()

        if request_type == "SessionEndedRequest":
            # No response needed for session end
            return {}

        logger.warning("Unknown request type: %s", request_type)
        return AlexaResponse("Sorry, I don't understand that type of request.").to_dict()

    except Exception:
        logger.exception("Unexpected error in lambda_handler")
        return AlexaResponse("Sorry, something went wrong. Please try again later.").to_dict()


# For local testing
if __name__ == "__main__":
    # Example test events
    test_next_meeting_event: dict[str, Any] = {
        "request": {"type": "IntentRequest", "intent": {"name": "GetNextMeetingIntent"}}
    }

    test_time_until_event: dict[str, Any] = {
        "request": {"type": "IntentRequest", "intent": {"name": "GetTimeUntilNextMeetingIntent"}}
    }

    test_done_for_day_event: dict[str, Any] = {
        "request": {"type": "IntentRequest", "intent": {"name": "GetDoneForDayIntent"}}
    }

    print("Testing GetNextMeetingIntent:")
    print(json.dumps(lambda_handler(test_next_meeting_event, None), indent=2))

    print("\nTesting GetTimeUntilNextMeetingIntent:")
    print(json.dumps(lambda_handler(test_time_until_event, None), indent=2))

    print("\nTesting GetDoneForDayIntent:")
    print(json.dumps(lambda_handler(test_done_for_day_event, None), indent=2))
