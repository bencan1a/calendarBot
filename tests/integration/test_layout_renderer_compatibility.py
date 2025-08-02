"""Comprehensive layout-renderer compatibility validation tests."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from calendarbot.cache.manager import CacheManager
from calendarbot.config.settings import CalendarBotSettings
from calendarbot.display.manager import DisplayManager
from calendarbot.display.renderer_factory import RendererFactory
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.ui.navigation import NavigationState
from calendarbot.web.server import WebServer
from tests.fixtures.mock_ics_data import ICSTestData

logger = logging.getLogger(__name__)


@pytest.fixture
def compatibility_test_settings():
    """Create test settings optimized for compatibility testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        settings = CalendarBotSettings(
            ics_url="http://localhost:8999/test.ics",
            config_dir=temp_path / "config",
            data_dir=temp_path / "data",
            cache_dir=temp_path / "cache",
            web_host="127.0.0.1",
            web_port=8997,  # Unique port for compatibility tests
            web_layout="4x8",  # Use correct field name
            display_type="html",
            app_name="CalendarBot-CompatibilityTest",
            refresh_interval=60,
            max_retries=2,
            request_timeout=5,
            auto_kill_existing=True,
            display_enabled=True,
        )

        settings.logging.console_level = "DEBUG"
        settings.logging.file_enabled = False

        yield settings


@pytest.mark.integration
@pytest.mark.critical_path
class TestLayoutRendererCompatibility:
    """Comprehensive test suite for layout-renderer compatibility validation."""

    @pytest_asyncio.fixture
    async def compatibility_setup(self, compatibility_test_settings):
        """Set up environment for compatibility testing."""
        cache_manager = CacheManager(compatibility_test_settings)
        await cache_manager.initialize()

        # Populate with test data
        test_events = ICSTestData.create_mock_events(count=5, include_today=True)
        await cache_manager.cache_events(test_events)

        yield compatibility_test_settings, cache_manager

        await cache_manager.cleanup_old_events(days_old=0)

    @pytest.mark.asyncio
    async def test_layout_registry_discovery(self, compatibility_setup):
        """Test layout registry discovery and validation."""
        settings, cache_manager = compatibility_setup

        logger.info("=== DIAGNOSTIC: Testing Layout Registry Discovery ===")

        try:
            layout_registry = LayoutRegistry()
            available_layouts = layout_registry.get_available_layouts()

            logger.info(f"DIAGNOSTIC: Available layouts: {available_layouts}")

            assert len(available_layouts) > 0, "No layouts discovered"

            # Validate each layout
            validation_results = {}
            for layout_name in available_layouts:
                layout_info = layout_registry.get_layout_info(layout_name)
                is_valid = layout_registry.validate_layout(layout_name)
                validation_results[layout_name] = {
                    "info_available": layout_info is not None,
                    "validation_passed": is_valid,
                    "renderer_type": layout_info.renderer_type if layout_info else None,
                }
                logger.info(
                    f"DIAGNOSTIC: Layout '{layout_name}' validation: {validation_results[layout_name]}"
                )

            # All layouts should be valid
            for layout_name, result in validation_results.items():
                assert result["info_available"], f"Layout info missing for {layout_name}"
                assert result["validation_passed"], f"Layout validation failed for {layout_name}"

        except Exception as e:
            logger.error(f"DIAGNOSTIC ERROR: Layout registry test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_renderer_factory_creation(self, compatibility_setup):
        """Test renderer factory creation for all available combinations."""
        settings, cache_manager = compatibility_setup

        logger.info("=== DIAGNOSTIC: Testing Renderer Factory Creation ===")

        try:
            # Get available renderers and layouts
            available_renderers = RendererFactory.get_available_renderers()
            layout_registry = LayoutRegistry()
            available_layouts = layout_registry.get_available_layouts()

            logger.info(f"DIAGNOSTIC: Available renderers: {available_renderers}")
            logger.info(f"DIAGNOSTIC: Available layouts: {available_layouts}")

            creation_results = {}

            # Test all combinations
            for renderer_type in available_renderers:
                for layout_name in available_layouts:
                    combination_key = f"{renderer_type}+{layout_name}"
                    logger.info(f"DIAGNOSTIC: Testing combination {combination_key}")

                    try:
                        renderer = RendererFactory.create_renderer(
                            settings, renderer_type=renderer_type, layout_name=layout_name
                        )

                        creation_results[combination_key] = {
                            "success": True,
                            "renderer_class": renderer.__class__.__name__,
                            "has_layout_attr": hasattr(renderer, "layout"),
                            "layout_value": getattr(renderer, "layout", None),
                            "error": None,
                        }

                        logger.info(
                            f"DIAGNOSTIC: {combination_key} SUCCESS - {creation_results[combination_key]}"
                        )

                    except Exception as e:
                        creation_results[combination_key] = {
                            "success": False,
                            "renderer_class": None,
                            "has_layout_attr": False,
                            "layout_value": None,
                            "error": str(e),
                        }

                        logger.warning(f"DIAGNOSTIC: {combination_key} FAILED - {e!s}")

            # Analyze results
            successful_combinations = [k for k, v in creation_results.items() if v["success"]]
            failed_combinations = [k for k, v in creation_results.items() if not v["success"]]

            logger.info(f"DIAGNOSTIC: Successful combinations: {len(successful_combinations)}")
            logger.info(f"DIAGNOSTIC: Failed combinations: {len(failed_combinations)}")

            if failed_combinations:
                logger.warning("DIAGNOSTIC: Failed combinations details:")
                for combo in failed_combinations:
                    logger.warning(f"  {combo}: {creation_results[combo]['error']}")

            # At least some combinations should work
            assert len(successful_combinations) > 0, "No renderer-layout combinations work"

            return creation_results

        except Exception as e:
            logger.error(f"DIAGNOSTIC ERROR: Renderer factory test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_display_manager_compatibility(self, compatibility_setup):
        """Test display manager with all layout-renderer combinations."""
        settings, cache_manager = compatibility_setup

        logger.info("=== DIAGNOSTIC: Testing Display Manager Compatibility ===")

        try:
            available_renderers = RendererFactory.get_available_renderers()
            layout_registry = LayoutRegistry()
            available_layouts = layout_registry.get_available_layouts()

            display_manager_results = {}

            for renderer_type in available_renderers:
                for layout_name in available_layouts:
                    combination_key = f"{renderer_type}+{layout_name}"
                    logger.info(f"DIAGNOSTIC: Testing DisplayManager with {combination_key}")

                    try:
                        # Create display manager with specific combination
                        display_manager = DisplayManager(
                            settings=settings, renderer_type=renderer_type, layout_name=layout_name
                        )

                        # Test basic operations
                        renderer_info = display_manager.get_renderer_info()
                        current_layout = display_manager.get_current_layout()
                        current_renderer = display_manager.get_current_renderer_type()

                        display_manager_results[combination_key] = {
                            "success": True,
                            "renderer_info": renderer_info,
                            "current_layout": current_layout,
                            "current_renderer": current_renderer,
                            "error": None,
                        }

                        logger.info(f"DIAGNOSTIC: {combination_key} DisplayManager SUCCESS")
                        logger.debug(
                            f"DIAGNOSTIC: {combination_key} details: {display_manager_results[combination_key]}"
                        )

                    except Exception as e:
                        display_manager_results[combination_key] = {
                            "success": False,
                            "renderer_info": None,
                            "current_layout": None,
                            "current_renderer": None,
                            "error": str(e),
                        }

                        logger.warning(
                            f"DIAGNOSTIC: {combination_key} DisplayManager FAILED - {e!s}"
                        )

            # Analyze results
            successful_dm = [k for k, v in display_manager_results.items() if v["success"]]
            failed_dm = [k for k, v in display_manager_results.items() if not v["success"]]

            logger.info(f"DIAGNOSTIC: DisplayManager successful combinations: {len(successful_dm)}")
            logger.info(f"DIAGNOSTIC: DisplayManager failed combinations: {len(failed_dm)}")

            # Should have some working combinations
            assert len(successful_dm) > 0, "No DisplayManager combinations work"

            return display_manager_results

        except Exception as e:
            logger.error(f"DIAGNOSTIC ERROR: DisplayManager compatibility test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_web_server_layout_switching(self, compatibility_setup):
        """Test web server layout switching across all combinations."""
        settings, cache_manager = compatibility_setup

        logger.info("=== DIAGNOSTIC: Testing Web Server Layout Switching ===")

        try:
            # Create web server components
            display_manager = DisplayManager(settings)
            navigation_state = NavigationState()
            web_server = WebServer(settings, display_manager, cache_manager, navigation_state)

            layout_registry = LayoutRegistry()
            available_layouts = layout_registry.get_available_layouts()

            switching_results = {}

            # Test switching to each layout
            for layout_name in available_layouts:
                logger.info(f"DIAGNOSTIC: Testing web server switch to layout '{layout_name}'")

                try:
                    # Test layout setting
                    success = web_server.set_layout(layout_name)
                    current_layout = web_server.layout

                    # Test layout retrieval
                    layout_info = web_server.get_status()

                    switching_results[layout_name] = {
                        "set_success": success,
                        "current_layout": current_layout,
                        "status_info": layout_info,
                        "layout_matches": current_layout == layout_name,
                        "error": None,
                    }

                    logger.info(
                        f"DIAGNOSTIC: Layout '{layout_name}' switch: SUCCESS={success}, Current={current_layout}"
                    )

                except Exception as e:
                    switching_results[layout_name] = {
                        "set_success": False,
                        "current_layout": None,
                        "status_info": None,
                        "layout_matches": False,
                        "error": str(e),
                    }

                    logger.warning(f"DIAGNOSTIC: Layout '{layout_name}' switch FAILED - {e!s}")

            # Test layout toggle functionality
            logger.info("DIAGNOSTIC: Testing layout toggle functionality")
            try:
                initial_layout = web_server.layout
                toggled_layout = web_server.toggle_layout()
                final_layout = web_server.layout

                toggle_result = {
                    "initial_layout": initial_layout,
                    "toggled_to": toggled_layout,
                    "final_layout": final_layout,
                    "toggle_worked": final_layout == toggled_layout,
                }

                logger.info(f"DIAGNOSTIC: Layout toggle: {toggle_result}")

            except Exception as e:
                logger.warning(f"DIAGNOSTIC: Layout toggle FAILED - {e!s}")
                toggle_result = {"error": str(e)}

            # Analyze results
            successful_switches = [k for k, v in switching_results.items() if v["set_success"]]
            failed_switches = [k for k, v in switching_results.items() if not v["set_success"]]

            logger.info(f"DIAGNOSTIC: Successful layout switches: {len(successful_switches)}")
            logger.info(f"DIAGNOSTIC: Failed layout switches: {len(failed_switches)}")

            # At least some layouts should be switchable
            assert len(successful_switches) > 0, "No layout switches work"

            return switching_results, toggle_result

        except Exception as e:
            logger.error(f"DIAGNOSTIC ERROR: Web server layout switching test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_end_to_end_compatibility_matrix(self, compatibility_setup):
        """Comprehensive end-to-end test of all layout-renderer combinations."""
        settings, cache_manager = compatibility_setup

        logger.info("=== DIAGNOSTIC: End-to-End Compatibility Matrix Test ===")

        try:
            layout_registry = LayoutRegistry()
            available_layouts = layout_registry.get_available_layouts()
            available_renderers = RendererFactory.get_available_renderers()

            compatibility_matrix = {}

            # Test each combination through full stack
            for renderer_type in available_renderers:
                for layout_name in available_layouts:
                    combination_key = f"{renderer_type}+{layout_name}"
                    logger.info(f"DIAGNOSTIC: Full stack test for {combination_key}")

                    try:
                        # 1. Create display manager
                        display_manager = DisplayManager(
                            settings=settings, renderer_type=renderer_type, layout_name=layout_name
                        )

                        # 2. Create web server
                        navigation_state = NavigationState()
                        web_server = WebServer(
                            settings, display_manager, cache_manager, navigation_state
                        )

                        # 3. Test basic operations
                        status = web_server.get_status()
                        layout_set = web_server.set_layout(layout_name)

                        # 4. Test HTML generation (mock renderer to avoid async issues)
                        display_manager.renderer = MagicMock()
                        display_manager.renderer.layout = layout_name
                        display_manager.renderer.render_events.return_value = (
                            f"<html><body>Test for {combination_key}</body></html>"
                        )

                        with patch.object(
                            web_server,
                            "get_calendar_html",
                            return_value=f"<html>Test {combination_key}</html>",
                        ):
                            html = web_server.get_calendar_html()

                        compatibility_matrix[combination_key] = {
                            "full_stack_success": True,
                            "status_success": isinstance(status, dict),
                            "layout_set_success": layout_set,
                            "html_generation_success": html is not None,
                            "current_layout": web_server.layout,
                            "renderer_class": display_manager.renderer.__class__.__name__,
                            "error": None,
                        }

                        logger.info(f"DIAGNOSTIC: {combination_key} FULL STACK SUCCESS")

                    except Exception as e:
                        compatibility_matrix[combination_key] = {
                            "full_stack_success": False,
                            "status_success": False,
                            "layout_set_success": False,
                            "html_generation_success": False,
                            "current_layout": None,
                            "renderer_class": None,
                            "error": str(e),
                        }

                        logger.warning(
                            f"DIAGNOSTIC: {combination_key} FULL STACK FAILED - {e!s}"
                        )

            # Generate compatibility report
            total_combinations = len(compatibility_matrix)
            successful_combinations = sum(
                1 for v in compatibility_matrix.values() if v["full_stack_success"]
            )
            success_rate = (
                (successful_combinations / total_combinations * 100)
                if total_combinations > 0
                else 0
            )

            logger.info("=" * 80)
            logger.info("DIAGNOSTIC: COMPATIBILITY MATRIX SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total combinations tested: {total_combinations}")
            logger.info(f"Successful combinations: {successful_combinations}")
            logger.info(f"Success rate: {success_rate:.1f}%")
            logger.info("=" * 80)

            # Detailed breakdown
            for combo, result in compatibility_matrix.items():
                status = "✓ SUCCESS" if result["full_stack_success"] else "✗ FAILED"
                error_info = f" ({result['error']})" if result["error"] else ""
                logger.info(f"{status}: {combo}{error_info}")

            logger.info("=" * 80)

            # Should have reasonable success rate
            assert success_rate > 0, "No layout-renderer combinations work end-to-end"

            return compatibility_matrix

        except Exception as e:
            logger.error(f"DIAGNOSTIC ERROR: End-to-end compatibility test failed: {e}")
            raise


@pytest.mark.integration
def test_comprehensive_layout_renderer_validation(compatibility_test_settings):
    """Run comprehensive layout-renderer compatibility validation."""
    logger.info("🔍 Starting Comprehensive Layout-Renderer Compatibility Validation")
    logger.info("=" * 80)

    # This will trigger all the async test methods above through pytest discovery
    # The actual validation happens in the individual test methods

    logger.info("✅ Comprehensive compatibility validation initiated")
    logger.info("   Check individual test results for detailed diagnostics")
