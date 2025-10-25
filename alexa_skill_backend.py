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
from typing import Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration from environment variables
CALENDARBOT_ENDPOINT = os.environ.get("CALENDARBOT_ENDPOINT", "")
CALENDARBOT_BEARER_TOKEN = os.environ.get("CALENDARBOT_BEARER_TOKEN", "")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))


class AlexaResponse:
    """Helper class to build Alexa response format."""

    def __init__(self, speech_text: str, should_end_session: bool = True):
        self.speech_text = speech_text
        self.should_end_session = should_end_session

    def to_dict(self) -> dict[str, Any]:
        """Convert to Alexa response format."""
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": self.speech_text},
                "shouldEndSession": self.should_end_session,
            },
        }


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
        logger.info(f"Calling calendarbot API: {url}")
        response = urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT)  # nosec

        if response.status == 200:
            data = json.loads(response.read().decode("utf-8"))
            logger.info(f"API response received: status={response.status}")
            return data
        logger.error(f"API returned non-200 status: {response.status}")
        raise Exception(f"API returned status {response.status}")  # noqa: TRY002, TRY301

    except urllib.error.HTTPError as e:
        logger.exception(f"HTTP error calling API: {e.code} {e.reason}")
        if e.code == 401:
            raise Exception("Authentication failed - check bearer token")  # noqa: B904, TRY002
        raise Exception(f"API request failed: {e.code} {e.reason}")  # noqa: B904, TRY002

    except urllib.error.URLError as e:
        logger.exception(f"URL error calling API: {e.reason}")
        raise Exception(f"Cannot reach calendarbot server: {e.reason}")  # noqa: B904, TRY002

    except Exception:
        logger.exception("Unexpected error calling API")
        raise


def handle_get_next_meeting_intent() -> AlexaResponse:
    """Handle GetNextMeetingIntent - returns next meeting info."""
    try:
        data = call_calendarbot_api("/api/alexa/next-meeting")

        if data.get("meeting") is None:
            speech_text = data.get("speech_text", "You have no upcoming meetings.")
        else:
            speech_text = data["meeting"].get("speech_text", "You have a meeting coming up.")

        return AlexaResponse(speech_text)

    except Exception:
        logger.exception("Error in GetNextMeetingIntent")
        return AlexaResponse(
            "Sorry, I'm having trouble accessing your calendar right now. Please try again later."
        )


def handle_get_time_until_next_meeting_intent() -> AlexaResponse:
    """Handle GetTimeUntilNextMeetingIntent - returns time until next meeting."""
    try:
        data = call_calendarbot_api("/api/alexa/time-until-next")
        speech_text = data.get("speech_text", "You have no upcoming meetings.")
        return AlexaResponse(speech_text)

    except Exception:
        logger.exception("Error in GetTimeUntilNextMeetingIntent")
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


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001, PLR0911
    """AWS Lambda handler for Alexa skill requests.

    Args:
        event: Alexa request event
        context: Lambda context (unused)

    Returns:
        Alexa response dictionary
    """
    try:
        logger.info(f"Received Alexa request: {json.dumps(event, default=str)}")

        # Validate request structure
        if "request" not in event:
            logger.error("Invalid request: missing 'request' field")
            return AlexaResponse("Sorry, I received an invalid request.").to_dict()

        request = event["request"]
        request_type = request.get("type")

        if request_type == "LaunchRequest":
            speech_text = (
                "Welcome to Calendar Bot. You can ask me about your next meeting "
                "or how long until your next meeting."
            )
            return AlexaResponse(speech_text, should_end_session=False).to_dict()

        if request_type == "IntentRequest":
            intent_name = request.get("intent", {}).get("name")

            if intent_name == "GetNextMeetingIntent":
                return handle_get_next_meeting_intent().to_dict()

            if intent_name == "GetTimeUntilNextMeetingIntent":
                return handle_get_time_until_next_meeting_intent().to_dict()

            if intent_name == "AMAZON.HelpIntent":
                return handle_help_intent().to_dict()

            if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
                return handle_stop_intent().to_dict()

            logger.warning(f"Unknown intent: {intent_name}")
            speech_text = (
                "I don't understand that request. You can ask me what's your next meeting "
                "or how long until your next meeting."
            )
            return AlexaResponse(speech_text).to_dict()

        if request_type == "SessionEndedRequest":
            # No response needed for session end
            return {}

        logger.warning(f"Unknown request type: {request_type}")
        return AlexaResponse("Sorry, I don't understand that type of request.").to_dict()

    except Exception:
        logger.exception("Unexpected error in lambda_handler")
        return AlexaResponse("Sorry, something went wrong. Please try again later.").to_dict()


# For local testing
if __name__ == "__main__":
    # Example test events
    test_next_meeting_event = {
        "request": {"type": "IntentRequest", "intent": {"name": "GetNextMeetingIntent"}}
    }

    test_time_until_event = {
        "request": {"type": "IntentRequest", "intent": {"name": "GetTimeUntilNextMeetingIntent"}}
    }

    print("Testing GetNextMeetingIntent:")
    print(json.dumps(lambda_handler(test_next_meeting_event, None), indent=2))

    print("\nTesting GetTimeUntilNextMeetingIntent:")
    print(json.dumps(lambda_handler(test_time_until_event, None), indent=2))
