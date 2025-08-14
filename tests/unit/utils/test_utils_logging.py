"""Comprehensive tests for calendarbot.utils.logging module."""

import logging
import os
import tempfile
from collections import deque
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from calendarbot.utils.logging import (
    VERBOSE,
    AutoColoredFormatter,
    SplitDisplayHandler,
    TimestampedFileHandler,
    apply_command_line_overrides,
    get_log_level,
    get_logger,
    setup_logging,
)


class TestVerboseLogging:
    """Test VERBOSE custom log level functionality."""

    def test_verbose_level_value(self) -> None:
        """Test VERBOSE level has correct numeric value."""
        assert VERBOSE == 15
        assert VERBOSE > logging.DEBUG
        assert VERBOSE < logging.INFO

    def test_verbose_level_name(self) -> None:
        """Test VERBOSE level name is registered."""
        assert logging.getLevelName(VERBOSE) == "VERBOSE"
        assert logging.getLevelName("VERBOSE") == VERBOSE

    def test_verbose_method_added_to_logger(self) -> None:
        """Test verbose method is added to Logger class."""
        logger = logging.getLogger("test_verbose")
        assert hasattr(logger, "verbose")
        assert callable(logger.verbose)

    def test_verbose_method_functionality(self) -> None:
        """Test verbose method logs at VERBOSE level."""
        logger = logging.getLogger("test_verbose_func")
        logger.setLevel(VERBOSE)

        with patch.object(logger, "_log") as mock_log:
            logger.verbose("test message", "arg1", key="value")  # type: ignore

            mock_log.assert_called_once_with(VERBOSE, "test message", ("arg1",), key="value")

    def test_verbose_method_respects_level(self) -> None:
        """Test verbose method respects logger level."""
        logger = logging.getLogger("test_verbose_level")
        logger.setLevel(logging.INFO)  # Above VERBOSE

        with patch.object(logger, "_log") as mock_log:
            logger.verbose("test message")  # type: ignore

            mock_log.assert_not_called()


class TestGetLogLevel:
    """Test get_log_level function."""

    def test_standard_log_levels(self) -> None:
        """Test standard logging levels."""
        assert get_log_level("DEBUG") == logging.DEBUG
        assert get_log_level("INFO") == logging.INFO
        assert get_log_level("WARNING") == logging.WARNING
        assert get_log_level("ERROR") == logging.ERROR
        assert get_log_level("CRITICAL") == logging.CRITICAL

    def test_verbose_log_level(self) -> None:
        """Test custom VERBOSE log level."""
        assert get_log_level("VERBOSE") == VERBOSE

    def test_case_insensitive(self) -> None:
        """Test case insensitive level names."""
        assert get_log_level("debug") == logging.DEBUG
        assert get_log_level("info") == logging.INFO
        assert get_log_level("verbose") == VERBOSE

    def test_invalid_level_returns_default(self) -> None:
        """Test invalid level name returns INFO as default."""
        result = get_log_level("INVALID_LEVEL")
        assert result == logging.INFO


class TestAutoColoredFormatter:
    """Test AutoColoredFormatter class."""

    def test_initialization_with_colors_enabled(self) -> None:
        """Test formatter initialization with colors enabled."""
        formatter = AutoColoredFormatter("%(message)s", enable_colors=True)

        assert formatter.enable_colors is True
        assert formatter.color_mode in ["truecolor", "basic", "none"]

    def test_initialization_with_colors_disabled(self) -> None:
        """Test formatter initialization with colors disabled."""
        formatter = AutoColoredFormatter("%(message)s", enable_colors=False)

        assert formatter.enable_colors is False
        assert formatter.color_mode == "none"

    @patch("calendarbot.utils.logging.sys.stdout")
    def test_color_detection_no_tty(self, mock_stdout: Any) -> None:
        """Test color detection when not a TTY."""
        mock_stdout.isatty.return_value = False

        formatter = AutoColoredFormatter("%(message)s")

        assert formatter.color_mode == "none"

    @patch("calendarbot.utils.logging.sys.stdout")
    @patch("calendarbot.utils.logging.os.environ", {"TERM": "xterm-256color"})
    def test_color_detection_truecolor(self, mock_stdout: Any) -> None:
        """Test truecolor detection."""
        mock_stdout.isatty.return_value = True

        formatter = AutoColoredFormatter("%(message)s")

        assert formatter.color_mode == "truecolor"

    @patch("calendarbot.utils.logging.sys.stdout")
    @patch("calendarbot.utils.logging.os.environ", {"COLORTERM": "truecolor"})
    def test_color_detection_colorterm_truecolor(self, mock_stdout: Any) -> None:
        """Test truecolor detection via COLORTERM."""
        mock_stdout.isatty.return_value = True

        formatter = AutoColoredFormatter("%(message)s")

        assert formatter.color_mode == "truecolor"

    @patch("calendarbot.utils.logging.sys.stdout")
    @patch("calendarbot.utils.logging.os.environ", {"TERM": "xterm-color"})
    def test_color_detection_basic(self, mock_stdout: Any) -> None:
        """Test basic color detection."""
        mock_stdout.isatty.return_value = True

        formatter = AutoColoredFormatter("%(message)s")

        assert formatter.color_mode == "basic"

    @patch("calendarbot.utils.logging.sys.stdout")
    def test_color_detection_dumb_terminal(self, mock_stdout: Any) -> None:
        """Test no color for dumb terminal."""
        mock_stdout.isatty.return_value = True

        with patch.dict("calendarbot.utils.logging.os.environ", {"TERM": "dumb"}, clear=True):
            formatter = AutoColoredFormatter("%(message)s")

            assert formatter.color_mode == "none"

    @patch("calendarbot.utils.logging.os.name", "nt")
    @patch("calendarbot.utils.logging.os.environ", {"WT_SESSION": "12345"})
    @patch("calendarbot.utils.logging.sys.stdout")
    def test_windows_terminal_detection(self, mock_stdout: Any) -> None:
        """Test Windows Terminal detection."""
        mock_stdout.isatty.return_value = True

        formatter = AutoColoredFormatter("%(message)s")

        assert formatter.color_mode == "truecolor"

    def test_format_with_no_colors(self) -> None:
        """Test formatting with no colors."""
        formatter = AutoColoredFormatter("%(levelname)s - %(message)s", enable_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert result == "INFO - test message"
        assert "\033[" not in result  # No ANSI codes

    def test_format_with_colors(self) -> None:
        """Test formatting with colors."""
        formatter = AutoColoredFormatter("%(levelname)s - %(message)s", enable_colors=True)
        formatter.color_mode = "basic"  # Force basic colors for predictable testing

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "test message" in result
        assert "\033[31m" in result or "\033[91m" in result  # Red color codes

    def test_format_unknown_level_no_color(self) -> None:
        """Test formatting unknown log level doesn't break."""
        formatter = AutoColoredFormatter("%(levelname)s - %(message)s", enable_colors=True)
        formatter.color_mode = "basic"

        record = logging.LogRecord(
            name="test",
            level=25,
            pathname="",
            lineno=0,  # Custom level
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.levelname = "CUSTOM"

        result = formatter.format(record)

        assert "CUSTOM - test message" in result

    @patch("calendarbot.utils.logging.sys.stdout")
    def test_no_isatty_attribute(self, mock_stdout: Any) -> None:
        """Test handling when stdout has no isatty attribute."""
        del mock_stdout.isatty  # Remove isatty attribute

        formatter = AutoColoredFormatter("%(message)s")

        assert formatter.color_mode == "none"


class TestTimestampedFileHandler:
    """Test TimestampedFileHandler class."""

    def test_initialization(self) -> None:
        """Test handler initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = TimestampedFileHandler(temp_dir, prefix="test", max_files=3)

            assert handler.log_dir == Path(temp_dir)
            assert handler.prefix == "test"
            assert handler.max_files == 3
            assert handler.log_dir.exists()

    def test_timestamped_filename_creation(self) -> None:
        """Test timestamped filename is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("calendarbot.utils.logging.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20230101_120000"

                handler = TimestampedFileHandler(temp_dir, prefix="test")

                expected_path = Path(temp_dir) / "test_20230101_120000.log"
                assert Path(handler.baseFilename) == expected_path

    def test_directory_creation(self) -> None:
        """Test log directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "nested" / "logs"

            TimestampedFileHandler(nested_dir)

            assert nested_dir.exists()

    def test_cleanup_old_files(self) -> None:
        """Test cleanup of old log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Create old log files
            for i in range(5):
                old_file = log_dir / f"test_{i}.log"
                old_file.touch()

            # Mock datetime to ensure consistent timestamp
            with patch("calendarbot.utils.logging.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "current"

                TimestampedFileHandler(log_dir, prefix="test", max_files=3)

            # Should keep only max_files (3) most recent files plus the new one
            remaining_files = list(log_dir.glob("test_*.log"))
            assert len(remaining_files) <= 4  # 3 old + 1 new

    def test_cleanup_ignores_errors(self) -> None:
        """Test cleanup ignores file deletion errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Create a log file
            old_file = log_dir / "test_old.log"
            old_file.touch()

            # Mock unlink to raise OSError
            with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
                with patch("calendarbot.utils.logging.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = "current"

                    # Should not raise exception
                    TimestampedFileHandler(log_dir, prefix="test", max_files=1)

    def test_pathlib_path_input(self) -> None:
        """Test handler accepts pathlib.Path input."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            handler = TimestampedFileHandler(log_dir)

            assert handler.log_dir == log_dir

    def test_default_parameters(self) -> None:
        """Test default parameter values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = TimestampedFileHandler(temp_dir)

            assert handler.prefix == "calendarbot"
            assert handler.max_files == 5


class TestSplitDisplayHandler:
    """Test SplitDisplayHandler class."""

    def test_initialization(self) -> None:
        """Test handler initialization."""
        mock_display_manager = MagicMock()
        handler = SplitDisplayHandler(mock_display_manager, max_log_lines=10)

        assert handler.display_manager == mock_display_manager
        assert handler.max_log_lines == 10
        assert isinstance(handler.log_buffer, deque)
        assert handler.log_buffer.maxlen == 10

    def test_emit_adds_to_buffer(self) -> None:
        """Test emit adds formatted message to buffer."""
        mock_display_manager = MagicMock()
        handler = SplitDisplayHandler(mock_display_manager, max_log_lines=3)
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert len(handler.log_buffer) == 1
        assert "test message" in handler.log_buffer[0]

    def test_emit_updates_display_manager(self) -> None:
        """Test emit updates display manager with log buffer."""
        mock_renderer = MagicMock()
        mock_renderer.update_log_area = MagicMock()

        mock_display_manager = MagicMock()
        mock_display_manager.renderer = mock_renderer

        handler = SplitDisplayHandler(mock_display_manager)
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_renderer.update_log_area.assert_called_once_with(["test message"])

    def test_emit_no_renderer_no_error(self) -> None:
        """Test emit handles missing renderer gracefully."""
        mock_display_manager = MagicMock()
        mock_display_manager.renderer = None

        handler = SplitDisplayHandler(mock_display_manager)
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should not raise exception
        handler.emit(record)

    def test_emit_no_update_log_area_method(self) -> None:
        """Test emit handles missing update_log_area method gracefully."""
        mock_renderer = MagicMock()
        del mock_renderer.update_log_area  # Remove method

        mock_display_manager = MagicMock()
        mock_display_manager.renderer = mock_renderer

        handler = SplitDisplayHandler(mock_display_manager)
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should not raise exception
        handler.emit(record)

    def test_emit_exception_handling(self) -> None:
        """Test emit handles exceptions gracefully."""
        mock_display_manager = MagicMock()
        mock_display_manager.renderer.update_log_area.side_effect = Exception("Display error")

        handler = SplitDisplayHandler(mock_display_manager)
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should not raise exception
        handler.emit(record)

    def test_buffer_max_length_respected(self) -> None:
        """Test log buffer respects max length."""
        mock_display_manager = MagicMock()
        handler = SplitDisplayHandler(mock_display_manager, max_log_lines=2)
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Add 3 messages to buffer with max 2
        for i in range(3):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        assert len(handler.log_buffer) == 2
        # Should contain the 2 most recent messages
        assert "message 1" in handler.log_buffer[0]
        assert "message 2" in handler.log_buffer[1]


class TestSetupLogging:
    """Test setup_logging function."""

    def test_basic_setup(self) -> None:
        """Test basic logging setup."""
        logger = setup_logging("INFO")

        assert logger.name == "calendarbot"
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1  # At least console handler

    def test_debug_level_setup(self) -> None:
        """Test setup with DEBUG level."""
        logger = setup_logging("DEBUG")

        assert logger.level == logging.DEBUG

    def test_invalid_level_defaults_to_info(self) -> None:
        """Test invalid level defaults to INFO."""
        logger = setup_logging("INVALID")

        assert logger.level == logging.INFO

    def test_file_logging_enabled(self) -> None:
        """Test setup with file logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = "test.log"
            log_dir = Path(temp_dir)

            logger = setup_logging("INFO", log_file=log_file, log_dir=log_dir)

            # Should have console + file handlers
            assert len(logger.handlers) >= 2

            # Check log file was created
            assert (log_dir / log_file).exists()

    def test_file_logging_without_dir(self) -> None:
        """Test file logging without specifying directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                log_file = "test.log"

                logger = setup_logging("INFO", log_file=log_file)

                assert len(logger.handlers) >= 2
                assert Path(log_file).exists()
            finally:
                os.chdir(original_cwd)

    def test_third_party_loggers_configured(self) -> None:
        """Test third-party logger levels are configured."""
        setup_logging("INFO")

        assert logging.getLogger("aiohttp").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("msal").level == logging.WARNING

    def test_handlers_cleared_on_setup(self) -> None:
        """Test existing handlers are cleared on setup."""
        logger = logging.getLogger("calendarbot")
        dummy_handler = logging.StreamHandler()
        logger.addHandler(dummy_handler)

        setup_logging("INFO")

        assert dummy_handler not in logger.handlers


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_namespaced_logger(self) -> None:
        """Test returns logger with calendarbot namespace."""
        logger = get_logger("test_module")

        assert logger.name == "calendarbot.test_module"
        assert isinstance(logger, logging.Logger)

    def test_different_modules_different_loggers(self) -> None:
        """Test different modules get different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 != logger2
        assert logger1.name != logger2.name


class TestApplyCommandLineOverrides:
    """Test apply_command_line_overrides function."""

    def test_log_level_override(self) -> None:
        """Test log level command line override."""
        mock_settings = MagicMock()
        mock_settings.logging.console_level = "INFO"
        mock_settings.logging.file_level = "INFO"

        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.verbose = False
        mock_args.quiet = False

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.console_level == "DEBUG"
        assert result.logging.file_level == "DEBUG"

    def test_verbose_override(self) -> None:
        """Test verbose command line override."""
        mock_settings = MagicMock()
        mock_settings.logging.console_level = "INFO"
        mock_settings.logging.file_level = "INFO"

        mock_args = MagicMock()
        mock_args.verbose = True
        mock_args.quiet = False
        mock_args.log_level = None

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.console_level == "VERBOSE"
        assert result.logging.file_level == "VERBOSE"

    def test_quiet_override(self) -> None:
        """Test quiet command line override."""
        mock_settings = MagicMock()
        mock_settings.logging.console_level = "INFO"

        mock_args = MagicMock()
        mock_args.quiet = True

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.console_level == "ERROR"

    def test_log_dir_override(self) -> None:
        """Test log directory command line override."""
        mock_settings = MagicMock()
        mock_settings.logging.file_directory = "/old/path"

        mock_args = MagicMock()
        mock_args.log_dir = "/new/path"

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.file_directory == "/new/path"

    def test_no_log_colors_override(self) -> None:
        """Test no log colors command line override."""
        mock_settings = MagicMock()
        mock_settings.logging.console_colors = True

        mock_args = MagicMock()
        mock_args.no_log_colors = True

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.console_colors is False

    def test_max_log_files_override(self) -> None:
        """Test max log files command line override."""
        mock_settings = MagicMock()
        mock_settings.logging.max_log_files = 5

        mock_args = MagicMock()
        mock_args.max_log_files = 10

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.max_log_files == 10

    def test_missing_attributes_ignored(self) -> None:
        """Test missing command line attributes are ignored."""
        mock_settings = MagicMock()
        original_level = mock_settings.logging.console_level

        mock_args = MagicMock()
        # Simulate missing attributes
        del mock_args.log_level
        del mock_args.verbose
        del mock_args.quiet

        result = apply_command_line_overrides(mock_settings, mock_args)

        # Should remain unchanged
        assert result.logging.console_level == original_level

    def test_none_values_ignored(self) -> None:
        """Test None values are ignored."""
        mock_settings = MagicMock()
        original_level = mock_settings.logging.console_level

        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.verbose = False  # False, not True
        mock_args.quiet = False

        result = apply_command_line_overrides(mock_settings, mock_args)

        # Should remain unchanged since log_level is None and others are False
        assert result.logging.console_level == original_level

    def test_all_overrides_combined(self) -> None:
        """Test multiple overrides applied together."""
        mock_settings = MagicMock()
        mock_settings.logging.console_level = "INFO"
        mock_settings.logging.file_level = "INFO"
        mock_settings.logging.file_directory = "/old/path"
        mock_settings.logging.console_colors = True
        mock_settings.logging.max_log_files = 5

        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.verbose = False  # Should be overridden by log_level
        mock_args.quiet = False
        mock_args.log_dir = "/new/path"
        mock_args.no_log_colors = True
        mock_args.max_log_files = 10

        result = apply_command_line_overrides(mock_settings, mock_args)

        assert result.logging.console_level == "DEBUG"  # log_level takes precedence
        assert result.logging.file_level == "DEBUG"
        assert result.logging.file_directory == "/new/path"
        assert result.logging.console_colors is False
        assert result.logging.max_log_files == 10


class TestLoggingIntegration:
    """Integration tests for logging module."""

    def test_verbose_logger_with_formatter(self) -> None:
        """Test verbose logging with custom formatter."""
        import io

        logger = logging.getLogger("test_integration")
        logger.setLevel(VERBOSE)
        logger.handlers.clear()  # Clear any existing handlers

        # Create string stream to capture output
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        formatter = AutoColoredFormatter("%(levelname)s - %(message)s", enable_colors=False)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Test verbose logging
        logger.verbose("test verbose message")  # type: ignore

        # Get the captured output
        output = stream.getvalue()
        assert "VERBOSE - test verbose message" in output

    def test_timestamped_handler_with_rotation(self) -> None:
        """Test timestamped handler with file rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple log files to test rotation
            log_dir = Path(temp_dir)
            for i in range(3):
                (log_dir / f"test_{i}.log").touch()

            # Create handler with max_files=2
            TimestampedFileHandler(log_dir, prefix="test", max_files=2)

            # Should have kept only 2 old files + 1 new file
            log_files = list(log_dir.glob("test_*.log"))
            assert len(log_files) <= 3  # 2 old + 1 new
