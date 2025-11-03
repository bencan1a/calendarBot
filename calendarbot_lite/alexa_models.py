"""Pydantic models for Alexa request validation."""

from __future__ import annotations

import zoneinfo
from datetime import date as dt_date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AlexaRequestParams(BaseModel):
    """Base request parameters for all Alexa handlers.

    Attributes:
        tz: Optional IANA timezone identifier (e.g., "America/Los_Angeles")
    """

    tz: Optional[str] = Field(None, description="IANA timezone identifier")

    @field_validator("tz")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone is a valid IANA timezone.

        Args:
            v: Timezone string to validate

        Returns:
            The validated timezone string

        Raises:
            ValueError: If timezone is invalid
        """
        if v is not None:
            try:
                zoneinfo.ZoneInfo(v)
            except zoneinfo.ZoneInfoNotFoundError:
                raise ValueError(f"Invalid timezone: {v!r}") from None
        return v


class NextMeetingRequestParams(AlexaRequestParams):
    """Request parameters for NextMeetingHandler.

    Inherits all parameters from AlexaRequestParams.
    """



class TimeUntilRequestParams(AlexaRequestParams):
    """Request parameters for TimeUntilHandler.

    Inherits all parameters from AlexaRequestParams.
    """



class DoneForDayRequestParams(AlexaRequestParams):
    """Request parameters for DoneForDayHandler.

    Inherits all parameters from AlexaRequestParams.
    """



class LaunchSummaryRequestParams(AlexaRequestParams):
    """Request parameters for LaunchSummaryHandler.

    Inherits all parameters from AlexaRequestParams.
    """



class MorningSummaryRequestParams(BaseModel):
    """Request parameters for MorningSummaryHandler.

    Attributes:
        date: Optional ISO date string (YYYY-MM-DD) for which day to summarize
        timezone: IANA timezone identifier (defaults to server timezone or UTC)
        detail_level: Level of detail for the summary (brief, normal, detailed)
        prefer_ssml: Whether to prefer SSML output if available
        max_events: Maximum number of events to include in summary (1-100)
    """

    date: Optional[str] = Field(
        None,
        description="ISO date string (YYYY-MM-DD) for which day to summarize",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    timezone: str = Field(
        "UTC", description="IANA timezone identifier", alias="timezone"
    )
    detail_level: Literal["brief", "normal", "detailed"] = Field(
        "normal", description="Level of detail for the summary"
    )
    prefer_ssml: bool = Field(False, description="Whether to prefer SSML output")
    max_events: int = Field(
        50, ge=1, le=100, description="Maximum number of events to include"
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is a valid IANA timezone.

        Args:
            v: Timezone string to validate

        Returns:
            The validated timezone string

        Raises:
            ValueError: If timezone is invalid
        """
        try:
            zoneinfo.ZoneInfo(v)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"Invalid timezone: {v!r}") from None
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is a valid ISO date string.

        Args:
            v: Date string to validate

        Returns:
            The validated date string

        Raises:
            ValueError: If date format is invalid
        """
        if v is not None:
            try:
                # Parse to validate format
                dt_date.fromisoformat(v)
            except ValueError as e:
                raise ValueError(f"Invalid date format: {v!r}. Expected YYYY-MM-DD") from e
        return v

    @model_validator(mode="before")
    @classmethod
    def parse_prefer_ssml(cls, data: dict) -> dict:
        """Parse prefer_ssml from string to boolean if needed.

        Args:
            data: Raw data dictionary

        Returns:
            Processed data dictionary
        """
        if isinstance(data, dict) and "prefer_ssml" in data:
            value = data["prefer_ssml"]
            if isinstance(value, str):
                data["prefer_ssml"] = value.lower() == "true"
        return data

    @model_validator(mode="before")
    @classmethod
    def parse_max_events(cls, data: dict) -> dict:
        """Parse max_events from string to int if needed.

        Args:
            data: Raw data dictionary

        Returns:
            Processed data dictionary

        Raises:
            ValueError: If max_events cannot be parsed as integer
        """
        if isinstance(data, dict) and "max_events" in data:
            value = data["max_events"]
            if isinstance(value, str):
                try:
                    data["max_events"] = int(value)
                except ValueError as e:
                    raise ValueError(f"Invalid max_events value: {value!r}. Expected integer") from e
        return data

    class Config:
        """Pydantic model configuration."""

        # Allow population by field name or alias
        populate_by_name = True
