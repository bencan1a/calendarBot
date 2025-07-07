#!/usr/bin/env python3
"""Test script for enhanced logging system implementation."""

import asyncio
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from calendarbot.display.console_renderer import ConsoleRenderer
from calendarbot.utils.logging import (
    VERBOSE,
    AutoColoredFormatter,
    SplitDisplayHandler,
    TimestampedFileHandler,
    apply_command_line_overrides,
    setup_enhanced_logging,
)
from config.settings import CalendarBotSettings, LoggingSettings


class MockDisplayManager:
    """Mock display manager for testing."""

    def __init__(self):
        self.settings = CalendarBotSettings()
        self.renderer = ConsoleRenderer(self.settings)


class MockArgs:
    """Mock command line arguments for testing."""

    def __init__(self, **kwargs):
        # Set default values
        self.verbose = False
        self.quiet = False
        self.log_level = None
        self.console_level = None
        self.file_level = None
        self.log_dir = None
        self.no_file_logging = False
        self.no_console_logging = False
        self.no_log_colors = False
        self.no_split_display = False
        self.max_log_files = None
        self.log_lines = None

        # Override with provided values
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_custom_verbose_level():
    """Test custom VERBOSE log level."""
    print("🧪 Testing custom VERBOSE log level...")

    # Test that VERBOSE level is properly defined
    assert VERBOSE == 15
    assert logging.getLevelName(VERBOSE) == "VERBOSE"

    # Test logger can use verbose level
    logger = logging.getLogger("test_verbose")
    logger.setLevel(logging.DEBUG)

    # Add a test handler to capture output
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    # Test verbose method exists and works
    assert hasattr(logger, "verbose")
    logger.verbose("This is a verbose message")

    logger.removeHandler(handler)
    print("✅ Custom VERBOSE level working correctly")


def test_auto_colored_formatter():
    """Test AutoColoredFormatter functionality."""
    print("🧪 Testing AutoColoredFormatter...")

    # Test color detection
    formatter = AutoColoredFormatter(enable_colors=True)
    assert formatter.color_mode in ["none", "basic", "truecolor"]

    # Test disabled colors
    formatter_no_color = AutoColoredFormatter(enable_colors=False)
    assert formatter_no_color.color_mode == "none"

    # Test formatting
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    assert "Test message" in formatted

    print("✅ AutoColoredFormatter working correctly")


def test_timestamped_file_handler():
    """Test TimestampedFileHandler functionality."""
    print("🧪 Testing TimestampedFileHandler...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create handler
        handler = TimestampedFileHandler(log_dir=temp_path, prefix="test_calendarbot", max_files=3)

        # Check file was created
        log_files = list(temp_path.glob("test_calendarbot_*.log"))
        assert len(log_files) == 1

        # Test log writing
        logger = logging.getLogger("test_file")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("Test log message")
        handler.close()

        # Check file contains message
        log_content = log_files[0].read_text()
        assert "Test log message" in log_content

        logger.removeHandler(handler)

    print("✅ TimestampedFileHandler working correctly")


def test_split_display_handler():
    """Test SplitDisplayHandler functionality."""
    print("🧪 Testing SplitDisplayHandler...")

    # Create mock display manager
    display_manager = MockDisplayManager()

    # Create handler
    handler = SplitDisplayHandler(display_manager, max_log_lines=3)

    # Test log buffering
    assert len(handler.log_buffer) == 0

    # Create test log records
    for i in range(5):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=i + 1,
            msg=f"Test message {i+1}",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

    # Should only keep last 3 messages
    assert len(handler.log_buffer) == 3
    assert "Test message 5" in handler.log_buffer[-1]

    print("✅ SplitDisplayHandler working correctly")


def test_logging_settings():
    """Test LoggingSettings integration."""
    print("🧪 Testing LoggingSettings integration...")

    # Test default settings
    settings = CalendarBotSettings()
    assert hasattr(settings, "logging")
    assert isinstance(settings.logging, LoggingSettings)

    # Test settings values
    assert settings.logging.console_enabled == True
    assert settings.logging.console_level == "INFO"
    assert settings.logging.file_enabled == True
    assert settings.logging.max_log_files == 5

    print("✅ LoggingSettings integration working correctly")


def test_command_line_overrides():
    """Test command-line argument override system."""
    print("🧪 Testing command-line override system...")

    settings = CalendarBotSettings()

    # Test verbose flag
    args = MockArgs(verbose=True)
    updated_settings = apply_command_line_overrides(settings, args)
    assert updated_settings.logging.console_level == "VERBOSE"
    assert updated_settings.logging.file_level == "VERBOSE"

    # Test quiet flag
    args = MockArgs(quiet=True)
    updated_settings = apply_command_line_overrides(settings, args)
    assert updated_settings.logging.console_level == "ERROR"

    # Test log level override
    args = MockArgs(log_level="DEBUG")
    updated_settings = apply_command_line_overrides(settings, args)
    assert updated_settings.logging.console_level == "DEBUG"
    assert updated_settings.logging.file_level == "DEBUG"

    # Test color disable
    args = MockArgs(no_log_colors=True)
    updated_settings = apply_command_line_overrides(settings, args)
    assert updated_settings.logging.console_colors == False

    print("✅ Command-line override system working correctly")


def test_enhanced_logging_setup():
    """Test complete enhanced logging setup."""
    print("🧪 Testing enhanced logging setup...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create settings with custom log directory
        settings = CalendarBotSettings()
        settings.logging.file_directory = temp_dir
        settings.logging.file_prefix = "test_enhanced"
        settings.logging.max_log_files = 2

        # Set up enhanced logging
        logger = setup_enhanced_logging(settings, interactive_mode=False)

        # Test logging at different levels
        logger.debug("Debug message")
        logger.verbose("Verbose message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Check log file was created
        log_files = list(Path(temp_dir).glob("test_enhanced_*.log"))
        assert len(log_files) == 1

        # Check log file contains messages
        log_content = log_files[0].read_text()
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content

    print("✅ Enhanced logging setup working correctly")


def test_console_renderer_split_display():
    """Test ConsoleRenderer split display functionality."""
    print("🧪 Testing ConsoleRenderer split display...")

    settings = CalendarBotSettings()
    renderer = ConsoleRenderer(settings)

    # Test split display enable/disable
    assert renderer.log_area_enabled == False

    renderer.enable_split_display(max_log_lines=3)
    assert renderer.log_area_enabled == True
    assert renderer.max_log_lines == 3

    # Test log area update
    test_logs = ["Log message 1", "Log message 2", "Log message 3", "Log message 4"]
    renderer.update_log_area(test_logs)

    # Should keep only last 3 messages
    assert len(renderer.log_area_lines) == 3
    assert "Log message 4" in renderer.log_area_lines

    # Test status info
    status = renderer.get_log_area_status()
    assert status["enabled"] == True
    assert status["max_lines"] == 3
    assert status["current_lines"] == 3

    renderer.disable_split_display()
    assert renderer.log_area_enabled == False

    print("✅ ConsoleRenderer split display working correctly")


async def run_all_tests():
    """Run all enhanced logging tests."""
    print("🚀 Starting Enhanced Logging System Tests\n")

    try:
        test_custom_verbose_level()
        test_auto_colored_formatter()
        test_timestamped_file_handler()
        test_split_display_handler()
        test_logging_settings()
        test_command_line_overrides()
        test_enhanced_logging_setup()
        test_console_renderer_split_display()

        print("\n🎉 All Enhanced Logging Tests Passed!")
        print("✨ Enhanced logging system is ready for production use!")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def demo_logging_features():
    """Demonstrate enhanced logging features."""
    print("\n🎭 Enhanced Logging Features Demo")
    print("=" * 50)

    # Create settings for demo
    settings = CalendarBotSettings()

    # Set up enhanced logging
    logger = setup_enhanced_logging(settings, interactive_mode=False)

    print("\n📝 Logging at different levels:")
    logger.debug("This is a DEBUG message (detailed info for developers)")
    logger.verbose("This is a VERBOSE message (detailed operational info)")
    logger.info("This is an INFO message (general information)")
    logger.warning("This is a WARNING message (something needs attention)")
    logger.error("This is an ERROR message (something went wrong)")

    print("\n🎨 Color support is auto-detected based on terminal capabilities")
    print("📁 Log files use timestamped naming: calendarbot_YYYYMMDD_HHMMSS.log")
    print("🔄 Only the last 5 log files are kept automatically")
    print("⚙️  Configuration priority: Command-line > Environment > YAML > Defaults")

    print("\n✅ Demo completed!")


if __name__ == "__main__":
    print("Enhanced Logging System Test Suite")
    print("=" * 40)

    # Run tests
    success = asyncio.run(run_all_tests())

    if success:
        # Run demo
        demo_logging_features()
        sys.exit(0)
    else:
        sys.exit(1)
