"""Unit tests for calendarbot_lite.dependencies module.

Tests cover the dependency injection container and app dependencies dataclass.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from calendarbot_lite.core.dependencies import AppDependencies, DependencyContainer


@pytest.mark.unit
@pytest.mark.fast
class TestAppDependencies:
    """Tests for AppDependencies dataclass."""

    def test_app_dependencies_when_created_then_stores_all_fields(self) -> None:
        """Test AppDependencies dataclass initialization."""
        mock_config = Mock()
        mock_http_client = Mock()
        mock_health_tracker = Mock()
        event_window_ref = [()]
        mock_lock = Mock()
        mock_stop_event = Mock()
        
        deps = AppDependencies(
            config=mock_config,
            event_window_ref=event_window_ref,
            window_lock=mock_lock,
            stop_event=mock_stop_event,
            skipped_store=None,
            shared_http_client=mock_http_client,
            health_tracker=mock_health_tracker,
            config_manager=None,
            event_filter=Mock(),
            window_manager=Mock(),
            fetch_orchestrator=Mock(),
            time_provider=Mock(),
            get_config_value=Mock(),
            get_server_timezone=Mock(),
            get_fallback_timezone=Mock(),
            serialize_iso=Mock(),
            event_to_api_model=Mock(),
            is_focus_time_event=Mock(),
            format_duration_spoken=Mock(),
            get_system_diagnostics=Mock(),
            log_monitoring_event=Mock(),
            ssml_renderers={},
        )
        
        assert deps.config is mock_config
        assert deps.shared_http_client is mock_http_client
        assert deps.health_tracker is mock_health_tracker
        assert deps.event_window_ref is event_window_ref
        assert deps.window_lock is mock_lock
        assert deps.stop_event is mock_stop_event
        assert deps.skipped_store is None
        assert deps.ssml_renderers == {}

    def test_app_dependencies_when_with_skipped_store_then_stores_value(self) -> None:
        """Test AppDependencies with skipped store."""
        mock_skipped_store = Mock()
        
        deps = AppDependencies(
            config=Mock(),
            event_window_ref=[()],
            window_lock=Mock(),
            stop_event=Mock(),
            skipped_store=mock_skipped_store,
            shared_http_client=Mock(),
            health_tracker=Mock(),
            config_manager=None,
            event_filter=Mock(),
            window_manager=Mock(),
            fetch_orchestrator=Mock(),
            time_provider=Mock(),
            get_config_value=Mock(),
            get_server_timezone=Mock(),
            get_fallback_timezone=Mock(),
            serialize_iso=Mock(),
            event_to_api_model=Mock(),
            is_focus_time_event=Mock(),
            format_duration_spoken=Mock(),
            get_system_diagnostics=Mock(),
            log_monitoring_event=Mock(),
            ssml_renderers={},
        )
        
        assert deps.skipped_store is mock_skipped_store


@pytest.mark.unit
@pytest.mark.fast
class TestDependencyContainer:
    """Tests for DependencyContainer factory."""

    def test_build_dependencies_when_called_then_returns_app_dependencies(self) -> None:
        """Test building dependencies returns AppDependencies instance."""
        mock_config = Mock()
        mock_skipped_store = Mock()
        mock_http_client = Mock()

        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"):

            deps = DependencyContainer.build_dependencies(
                mock_config, mock_skipped_store, mock_http_client
            )

            assert isinstance(deps, AppDependencies)
            assert deps.config is mock_config
            assert deps.skipped_store is mock_skipped_store
            assert deps.shared_http_client is mock_http_client

    def test_build_dependencies_when_called_then_initializes_health_tracker(self) -> None:
        """Test building dependencies initializes HealthTracker."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker") as mock_ht_class, \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"):

            mock_ht_instance = Mock()
            mock_ht_class.return_value = mock_ht_instance

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            mock_ht_class.assert_called_once_with()
            assert deps.health_tracker is mock_ht_instance

    def test_build_dependencies_when_called_then_creates_event_window_state(self) -> None:
        """Test building dependencies creates event window state."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"), \
             patch("asyncio.Lock") as mock_lock_class, \
             patch("asyncio.Event") as mock_event_class:

            mock_lock = Mock()
            mock_stop_event = Mock()
            mock_lock_class.return_value = mock_lock
            mock_event_class.return_value = mock_stop_event

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            assert deps.event_window_ref == [()]
            assert deps.window_lock is mock_lock
            assert deps.stop_event is mock_stop_event

    def test_build_dependencies_when_called_then_initializes_event_filter(self) -> None:
        """Test building dependencies initializes EventFilter."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter") as mock_ef_class, \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"), \
             patch("calendarbot_lite.core.timezone_utils.get_server_timezone") as mock_get_tz, \
             patch("calendarbot_lite.core.timezone_utils.get_fallback_timezone") as mock_get_fb:

            mock_ef_instance = Mock()
            mock_ef_class.return_value = mock_ef_instance

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            mock_ef_class.assert_called_once_with(mock_get_tz, mock_get_fb)
            assert deps.event_filter is mock_ef_instance

    def test_build_dependencies_when_called_then_initializes_window_manager(self) -> None:
        """Test building dependencies initializes EventWindowManager."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter") as mock_ef_class, \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager") as mock_wm_class, \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler") as mock_fb_class:

            mock_ef_instance = Mock()
            mock_fb_instance = Mock()
            mock_wm_instance = Mock()
            mock_ef_class.return_value = mock_ef_instance
            mock_fb_class.return_value = mock_fb_instance
            mock_wm_class.return_value = mock_wm_instance

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            mock_wm_class.assert_called_once_with(mock_ef_instance, mock_fb_instance)
            assert deps.window_manager is mock_wm_instance

    def test_build_dependencies_when_called_then_initializes_fetch_orchestrator(
        self,
    ) -> None:
        """Test building dependencies initializes FetchOrchestrator."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker") as mock_ht_class, \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager") as mock_wm_class, \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator") as mock_fo_class, \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"):

            mock_ht_instance = Mock()
            mock_wm_instance = Mock()
            mock_fo_instance = Mock()
            mock_ht_class.return_value = mock_ht_instance
            mock_wm_class.return_value = mock_wm_instance
            mock_fo_class.return_value = mock_fo_instance

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            # Verify FetchOrchestrator was called with expected arguments
            assert mock_fo_class.called
            assert deps.fetch_orchestrator is mock_fo_instance

    def test_build_dependencies_when_ssml_available_then_loads_renderers(self) -> None:
        """Test building dependencies loads SSML renderers when available."""
        mock_meeting_ssml = Mock()
        mock_time_until_ssml = Mock()
        mock_done_ssml = Mock()

        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"), \
             patch("calendarbot_lite.alexa.alexa_ssml.render_meeting_ssml", mock_meeting_ssml), \
             patch("calendarbot_lite.alexa.alexa_ssml.render_time_until_ssml", mock_time_until_ssml), \
             patch("calendarbot_lite.alexa.alexa_ssml.render_done_for_day_ssml", mock_done_ssml):

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            assert "meeting" in deps.ssml_renderers
            assert "time_until" in deps.ssml_renderers
            assert "done_for_day" in deps.ssml_renderers
            assert deps.ssml_renderers["meeting"] is mock_meeting_ssml
            assert deps.ssml_renderers["time_until"] is mock_time_until_ssml
            assert deps.ssml_renderers["done_for_day"] is mock_done_ssml

    def test_build_dependencies_when_ssml_import_fails_then_empty_renderers(self) -> None:
        """Test building dependencies handles missing SSML module."""
        # Store the original import function
        import builtins
        original_import = builtins.__import__

        # Patch the import to raise ImportError for alexa_ssml
        def mock_import(name, *args, **kwargs):
            if 'alexa_ssml' in name:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"), \
             patch("builtins.__import__", side_effect=mock_import):

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            assert deps.ssml_renderers == {}

    def test_build_dependencies_when_called_then_sets_utility_functions(self) -> None:
        """Test building dependencies sets utility functions."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"), \
             patch("calendarbot_lite.core.timezone_utils.now_utc") as mock_now_utc, \
             patch("calendarbot_lite.core.config_manager.get_config_value") as mock_get_config, \
             patch("calendarbot_lite.core.timezone_utils.get_server_timezone") as mock_get_tz, \
             patch("calendarbot_lite.core.timezone_utils.get_fallback_timezone") as mock_get_fb, \
             patch("calendarbot_lite.core.health_tracker.get_system_diagnostics") as mock_diag:

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            assert deps.time_provider is mock_now_utc
            assert deps.get_config_value is mock_get_config
            assert deps.get_server_timezone is mock_get_tz
            assert deps.get_fallback_timezone is mock_get_fb
            assert deps.get_system_diagnostics is mock_diag

    def test_build_dependencies_when_none_skipped_store_then_accepts_none(self) -> None:
        """Test building dependencies accepts None for skipped store."""
        with patch("calendarbot_lite.core.health_tracker.HealthTracker"), \
             patch("calendarbot_lite.domain.event_filter.EventFilter"), \
             patch("calendarbot_lite.domain.event_filter.EventWindowManager"), \
             patch("calendarbot_lite.domain.fetch_orchestrator.FetchOrchestrator"), \
             patch("calendarbot_lite.domain.event_filter.SmartFallbackHandler"):

            deps = DependencyContainer.build_dependencies(Mock(), None, Mock())

            assert deps.skipped_store is None
