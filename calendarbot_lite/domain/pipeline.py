"""Event processing pipeline architecture for calendarbot_lite.

This module provides a flexible, extensible pipeline for processing calendar events
through multiple stages. The pipeline pattern enables:
- Clear separation of concerns
- Easy testing of individual stages
- Extensibility for new processing stages
- Explicit error handling and logging

Usage:
    pipeline = EventProcessingPipeline()
    pipeline.add_stage(FetchStage(...))
    pipeline.add_stage(ParseStage(...))
    pipeline.add_stage(ExpansionStage(...))

    context = ProcessingContext(...)
    result = await pipeline.process(context)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol

from calendarbot_lite.calendar.lite_models import LiteCalendarEvent

logger = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    """Context passed between pipeline stages.

    Contains all data and configuration needed for event processing.
    Stages can read from and write to this context.
    """

    # Configuration
    rrule_expansion_days: int = 14
    event_window_size: int = 50
    max_stored_events: int = 1000
    enable_streaming: bool = True

    # Time context
    now: Optional[datetime] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None

    # Processing state (modified by stages)
    raw_content: Optional[str] = None  # Raw ICS content
    raw_components: list[Any] = field(default_factory=list)  # iCalendar components
    events: list[LiteCalendarEvent] = field(default_factory=list)  # Parsed events
    filtered_events: list[LiteCalendarEvent] = field(default_factory=list)  # After filtering

    # Metadata
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    calendar_metadata: dict[str, Any] = field(default_factory=dict)

    # User preferences
    skipped_event_ids: set[str] = field(default_factory=set)
    user_email: Optional[str] = None

    # Stage-specific data (extensible)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result from a pipeline stage or complete pipeline execution.

    Contains processed events plus error/warning information for observability.
    """

    success: bool = True
    events: list[LiteCalendarEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Statistics
    events_in: int = 0  # Events received by stage
    events_out: int = 0  # Events emitted by stage
    events_filtered: int = 0  # Events removed by stage
    stage_name: str = ""

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning("[%s] %s", self.stage_name, message)

    def add_error(self, message: str) -> None:
        """Add an error message and mark as failed."""
        self.errors.append(message)
        self.success = False
        logger.error("[%s] %s", self.stage_name, message)


class EventProcessor(Protocol):
    """Protocol for a single stage in the event processing pipeline.

    Each stage:
    - Receives a ProcessingContext
    - Performs its processing task
    - Returns a ProcessingResult with events and any errors/warnings
    - Can modify the context for downstream stages
    """

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Process events according to this stage's responsibility.

        Args:
            context: Processing context with events and configuration

        Returns:
            Result with processed events and any errors/warnings
        """
        ...

    @property
    def name(self) -> str:
        """Name of this processing stage for logging."""
        ...


class EventProcessingPipeline:
    """Orchestrates event processing through multiple stages.

    The pipeline executes stages in sequence, passing the processing context
    between stages. Each stage can:
    - Transform events
    - Filter events
    - Add metadata
    - Raise errors/warnings

    Example:
        pipeline = EventProcessingPipeline()
        pipeline.add_stage(FetchStage(fetcher))
        pipeline.add_stage(ParseStage(parser))
        pipeline.add_stage(ExpansionStage(expander))

        context = ProcessingContext(
            source_url="https://example.com/calendar.ics",
            rrule_expansion_days=14
        )
        result = await pipeline.process(context)

        if result.success:
            print(f"Processed {result.events_out} events")
        else:
            print(f"Errors: {result.errors}")
    """

    def __init__(self) -> None:
        """Initialize empty pipeline."""
        self.stages: list[EventProcessor] = []
        self._enable_telemetry: bool = True

    def add_stage(self, stage: EventProcessor) -> EventProcessingPipeline:
        """Add a processing stage to the pipeline (builder pattern).

        Args:
            stage: Event processor to add

        Returns:
            Self for method chaining
        """
        self.stages.append(stage)
        logger.debug("Added stage to pipeline: %s", stage.name)
        return self

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Execute all pipeline stages in sequence.

        Args:
            context: Processing context with initial state

        Returns:
            Aggregated result from all stages
        """
        logger.debug("Starting pipeline with %d stages", len(self.stages))

        # Aggregate result across all stages
        aggregated_result = ProcessingResult(
            stage_name="Pipeline",
            events_in=0,
        )

        try:
            # Execute stages in sequence
            for i, stage in enumerate(self.stages):
                stage_num = i + 1
                logger.debug("Executing stage %d/%d: %s", stage_num, len(self.stages), stage.name)

                # Execute stage
                try:
                    stage_result = await stage.process(context)

                    # Log stage completion
                    logger.debug(
                        "Stage %s/%s (%s) completed: success=%s, events_in=%s, events_out=%s, warnings=%s, errors=%s",
                        stage_num,
                        len(self.stages),
                        stage.name,
                        stage_result.success,
                        stage_result.events_in,
                        stage_result.events_out,
                        len(stage_result.warnings),
                        len(stage_result.errors),
                    )

                    # Aggregate warnings and errors
                    aggregated_result.warnings.extend(stage_result.warnings)
                    aggregated_result.errors.extend(stage_result.errors)

                    # If stage failed critically, stop pipeline
                    if not stage_result.success:
                        aggregated_result.success = False
                        logger.error(
                            "Pipeline stopped at stage %s (%s) due to failure",
                            stage_num,
                            stage.name,
                        )
                        return aggregated_result

                    # Merge stage metadata
                    aggregated_result.metadata.update(stage_result.metadata)

                except Exception as e:
                    # Handle unexpected stage errors
                    error_msg = f"Stage {stage.name} raised exception: {e}"
                    aggregated_result.add_error(error_msg)
                    logger.exception("Stage %s failed with exception", stage.name)
                    return aggregated_result

            # Pipeline completed successfully
            aggregated_result.success = True
            aggregated_result.events = context.events
            aggregated_result.events_out = len(context.events)

            logger.info(
                "Pipeline completed successfully: %s events, %s warnings",
                aggregated_result.events_out,
                len(aggregated_result.warnings),
            )

            return aggregated_result

        except Exception as e:
            # Handle unexpected pipeline errors
            aggregated_result.success = False
            aggregated_result.add_error(f"Pipeline execution failed: {e}")
            logger.exception("Pipeline execution failed with exception")
            return aggregated_result

    def clear_stages(self) -> None:
        """Remove all stages from the pipeline."""
        self.stages.clear()
        logger.debug("Cleared all pipeline stages")

    def __repr__(self) -> str:
        """String representation of pipeline."""
        stage_names = [stage.name for stage in self.stages]
        return f"EventProcessingPipeline(stages={stage_names})"
