"""Tests for RendererInterface and related components."""

from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from calendarbot.display.renderer_interface import InteractionEvent, RendererInterface
from calendarbot.display.whats_next_data_model import EventData, StatusInfo, WhatsNextViewModel


class MockInteractionEvent:
    """Mock implementation of InteractionEvent protocol for testing."""

    def __init__(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.data = data or {}


class TestRendererInterface:
    """Test RendererInterface abstract base class."""

    def test_renderer_interface_when_abstract_then_cannot_instantiate(self) -> None:
        """Test that RendererInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RendererInterface()  # type: ignore

    def test_renderer_interface_when_subclassed_without_implementation_then_cannot_instantiate(
        self,
    ) -> None:
        """Test that incomplete subclass cannot be instantiated."""

        class IncompleteRenderer(RendererInterface):
            pass

        with pytest.raises(TypeError):
            IncompleteRenderer()  # type: ignore

    def test_renderer_interface_when_properly_implemented_then_can_instantiate(self) -> None:
        """Test that properly implemented subclass can be instantiated."""

        class CompleteRenderer(RendererInterface):
            def render(self, view_model: WhatsNextViewModel) -> Any:
                return "rendered"

            def handle_interaction(self, interaction: InteractionEvent) -> None:
                return None

            def update_display(self, content: Any) -> bool:
                return True

            def render_error(self, error_message: str, cached_events=None) -> Any:
                return f"Error: {error_message}"

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                return f"Auth: {verification_uri} - {user_code}"

        renderer = CompleteRenderer()
        assert renderer is not None
        assert isinstance(renderer, RendererInterface)

    def test_concrete_renderer_when_methods_called_then_works_correctly(self) -> None:
        """Test that concrete renderer implementation works correctly."""

        class TestRenderer(RendererInterface):
            def __init__(self):
                self.last_rendered_content = None
                self.last_interaction = None
                self.display_updated = False

            def render(self, view_model: WhatsNextViewModel) -> str:
                self.last_rendered_content = f"Rendered: {view_model.display_date}"
                return self.last_rendered_content

            def handle_interaction(self, interaction: InteractionEvent) -> None:
                self.last_interaction = interaction

            def update_display(self, content: Any) -> bool:
                self.display_updated = True
                return True

            def render_error(self, error_message: str, cached_events=None) -> Any:
                return f"Error: {error_message}"

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                return f"Auth: {verification_uri} - {user_code}"

        renderer = TestRenderer()

        # Create sample view model
        status_info = StatusInfo(last_update=datetime(2025, 7, 14, 12, 0, 0), is_cached=False)

        view_model = WhatsNextViewModel(
            current_time=datetime(2025, 7, 14, 12, 0, 0),
            display_date="Monday, July 14",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        # Test render method
        result = renderer.render(view_model)
        assert result == "Rendered: Monday, July 14"
        assert renderer.last_rendered_content == "Rendered: Monday, July 14"

        # Test handle_interaction method
        interaction = MockInteractionEvent("click", {})
        renderer.handle_interaction(interaction)
        assert renderer.last_interaction == interaction

        # Test update_display method
        renderer.update_display("test content")
        assert renderer.display_updated is True


class TestInteractionEvent:
    """Test InteractionEvent protocol functionality."""

    def test_interaction_event_when_mock_object_then_accepts(self) -> None:
        """Test that InteractionEvent accepts objects with event_type and data."""

        def handle_event(event: InteractionEvent) -> str:
            return f"Event: {event.event_type}"

        interaction = MockInteractionEvent("click", {"x": 100, "y": 200})
        result = handle_event(interaction)
        assert result == "Event: click"

    def test_interaction_event_when_dict_with_proper_fields_then_accepts(self) -> None:
        """Test that InteractionEvent accepts dictionary with proper structure."""

        def handle_event(event: InteractionEvent) -> str:
            return f"Event type: {event.event_type}"

        # Use a class that implements the protocol rather than a raw dict
        class SimpleEvent:
            def __init__(self):
                self.event_type = "click"
                self.data = {"x": 100, "y": 200}

        event_obj = SimpleEvent()
        result = handle_event(event_obj)
        assert result == "Event type: click"

    def test_interaction_event_protocol_compliance(self) -> None:
        """Test that MockInteractionEvent properly implements the protocol."""

        def handle_event(event: InteractionEvent) -> str:
            return f"Received: {type(event).__name__}"

        # Test with MockInteractionEvent
        mock_event = MockInteractionEvent("test", {"key": "value"})
        assert handle_event(mock_event) == "Received: MockInteractionEvent"
        assert mock_event.event_type == "test"
        assert mock_event.data == {"key": "value"}


class TestRendererInterfaceIntegration:
    """Test integration scenarios with RendererInterface."""

    def test_multiple_renderers_when_same_interface_then_interchangeable(self) -> None:
        """Test that multiple renderers implementing the same interface are interchangeable."""

        class HTMLRenderer(RendererInterface):
            def render(self, view_model: WhatsNextViewModel) -> str:
                return f"<html>{view_model.display_date}</html>"

            def handle_interaction(self, interaction: InteractionEvent) -> None:
                pass

            def update_display(self, content: Any) -> bool:
                print(f"HTML display updated: {content}")
                return True

            def render_error(self, error_message: str, cached_events=None) -> Any:
                return f"<error>{error_message}</error>"

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                return f"<auth>{verification_uri} - {user_code}</auth>"

        class ConsoleRenderer(RendererInterface):
            def render(self, view_model: WhatsNextViewModel) -> str:
                return f"Console: {view_model.display_date}"

            def handle_interaction(self, interaction: InteractionEvent) -> None:
                pass

            def update_display(self, content: Any) -> bool:
                print(f"Console display updated: {content}")
                return True

            def render_error(self, error_message: str, cached_events=None) -> Any:
                return f"Console Error: {error_message}"

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                return f"Console Auth: {verification_uri} - {user_code}"

        # Create view model
        status_info = StatusInfo(last_update=datetime(2025, 7, 14, 12, 0, 0), is_cached=False)

        view_model = WhatsNextViewModel(
            current_time=datetime(2025, 7, 14, 12, 0, 0),
            display_date="Test Day",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        # Test that both renderers can be used interchangeably
        renderers = [HTMLRenderer(), ConsoleRenderer()]

        for renderer in renderers:
            # All renderers should implement the same interface
            assert hasattr(renderer, "render")
            assert hasattr(renderer, "handle_interaction")
            assert hasattr(renderer, "update_display")

            # All should be able to render the same view model
            result = renderer.render(view_model)
            assert "Test Day" in result

            # All should handle interactions
            interaction_result = renderer.handle_interaction("test")
            assert interaction_result is None

            # All should support display updates
            renderer.update_display("test content")

    def test_renderer_interface_with_complex_view_model_then_handles_correctly(self) -> None:
        """Test renderer interface with complex view model data."""

        class MockRenderer(RendererInterface):
            def __init__(self):
                self.rendered_events = []
                self.rendered_status = None

            def render(self, view_model: WhatsNextViewModel) -> Dict[str, Any]:
                self.rendered_events = view_model.next_events + view_model.current_events
                self.rendered_status = view_model.status_info

                return {
                    "date": view_model.display_date,
                    "event_count": len(self.rendered_events),
                    "status": "cached" if view_model.status_info.is_cached else "live",
                }

            def handle_interaction(self, interaction: InteractionEvent) -> None:
                pass

            def update_display(self, content: Any) -> bool:
                return True

            def render_error(self, error_message: str, cached_events=None) -> Any:
                return {"error": error_message}

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                return {"auth_uri": verification_uri, "code": user_code}

        # Create complex view model with events
        next_event = EventData(
            subject="Important Meeting",
            start_time=datetime(2025, 7, 14, 14, 0, 0),
            end_time=datetime(2025, 7, 14, 15, 0, 0),
            location="Board Room",
            is_current=False,
            is_upcoming=True,
            time_until_minutes=120,
        )

        current_event = EventData(
            subject="Current Call",
            start_time=datetime(2025, 7, 14, 12, 0, 0),
            end_time=datetime(2025, 7, 14, 13, 0, 0),
            location="Zoom",
            is_current=True,
            is_upcoming=False,
            time_until_minutes=None,
        )

        status_info = StatusInfo(
            last_update=datetime(2025, 7, 14, 12, 0, 0),
            is_cached=True,
            connection_status="Connected",
            relative_description="Today",
        )

        view_model = WhatsNextViewModel(
            current_time=datetime(2025, 7, 14, 12, 0, 0),
            display_date="Monday, July 14",
            next_events=[next_event],
            current_events=[current_event],
            later_events=[],
            status_info=status_info,
        )

        renderer = MockRenderer()
        result = renderer.render(view_model)

        assert result["date"] == "Monday, July 14"
        assert result["event_count"] == 2
        assert result["status"] == "cached"
        assert len(renderer.rendered_events) == 2
        assert renderer.rendered_status is not None
        assert renderer.rendered_status.is_cached is True

    def test_type_compliance_for_interface_methods(self) -> None:
        """Test that interface methods have proper type compliance."""

        class TypeTestRenderer(RendererInterface):
            def render(self, view_model: WhatsNextViewModel) -> str:
                assert isinstance(view_model, WhatsNextViewModel)
                return "test"

            def handle_interaction(self, interaction: InteractionEvent) -> None:
                # InteractionEvent can be Any, so no type assertion needed
                pass

            def update_display(self, content: Any) -> bool:
                # content can be Any, so no type assertion needed
                return True

            def render_error(self, error_message: str, cached_events=None) -> Any:
                return f"Error: {error_message}"

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                return f"Auth: {verification_uri} - {user_code}"

        renderer = TypeTestRenderer()

        # Create minimal view model for testing
        status_info = StatusInfo(last_update=datetime(2025, 7, 14, 12, 0, 0), is_cached=False)

        view_model = WhatsNextViewModel(
            current_time=datetime(2025, 7, 14, 12, 0, 0),
            display_date="Test",
            next_events=[],
            current_events=[],
            later_events=[],
            status_info=status_info,
        )

        # Test type compliance
        result = renderer.render(view_model)
        assert isinstance(result, str)

        interaction_result = renderer.handle_interaction(MockInteractionEvent("test", {}))
        assert interaction_result is None

        # update_display should not raise
        renderer.update_display("anything")
