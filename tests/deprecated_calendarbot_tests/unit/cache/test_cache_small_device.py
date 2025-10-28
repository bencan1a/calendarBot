from unittest.mock import MagicMock

import pytest

from calendarbot.config.optimization import OptimizationConfig, reset_optimization_config
from calendarbot.config.settings import get_settings, reset_settings
from calendarbot.optimization.cache_manager import CacheManager, reset_cache_manager


@pytest.mark.asyncio
async def test_cache_defaults_normal_device():
    """Default (non-small-device) should preserve larger defaults."""
    reset_settings()
    reset_optimization_config()
    settings = get_settings()
    settings.optimization.small_device = False

    config = OptimizationConfig()
    cm = CacheManager(config=config)
    try:
        assert cm._l1_maxsize >= 500
        assert cm._l2_size_limit >= 50 * 1024 * 1024
    finally:
        await cm.clear_cache("both")
        reset_cache_manager()
        reset_settings()
        reset_optimization_config()


@pytest.mark.asyncio
async def test_cache_small_device_overrides():
    """When small_device is True cache sizes/ttls should be reduced."""
    reset_settings()
    reset_optimization_config()
    settings = get_settings()
    settings.optimization.small_device = True

    cm = CacheManager()
    try:
        assert cm._l1_maxsize == 50
        assert cm._l1_ttl == 120
        assert cm._l2_size_limit == 15 * 1024 * 1024
    finally:
        await cm.clear_cache("both")
        reset_cache_manager()
        reset_settings()
        reset_optimization_config()


@pytest.mark.asyncio
async def test_logging_level_reduced():
    """Ensure frequent cache ops use DEBUG; INFO should not be used for frequent ops."""
    reset_settings()
    reset_optimization_config()
    settings = get_settings()
    settings.optimization.small_device = True

    cm = CacheManager()
    # Replace logger after initialization so we don't inherit module-level info log
    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    cm.logger = mock_logger

    try:
        await cm.set("key1", {"v": 1})
        await cm.get("key1")

        # Frequent paths should call debug
        assert mock_logger.debug.called
        # And should not call info for frequent debug messages
        assert not mock_logger.info.called
    finally:
        await cm.clear_cache("both")
        reset_cache_manager()
        reset_settings()
        reset_optimization_config()
