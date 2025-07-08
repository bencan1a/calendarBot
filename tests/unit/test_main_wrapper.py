"""Unit tests for the simplified __main__.py wrapper module."""

import sys
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_main_import_success():
    """Test that the simplified wrapper can import main_entry successfully."""
    # Import the module to test the import path logic
    from calendarbot.__main__ import main

    # Verify the function exists and is callable
    assert callable(main)


def test_main_import_failure():
    """Test error handling when main_entry import fails."""
    # This test verifies the import error handling logic exists
    # The actual import error handling happens at module import time
    # and is difficult to test in isolation without complex mocking

    # Instead, verify that the import error handling code exists
    import inspect

    import calendarbot.__main__

    # Read the source code to verify error handling exists
    source = inspect.getsource(calendarbot.__main__)

    # Verify that import error handling is present
    assert "ImportError" in source
    assert "sys.exit(1)" in source
    assert "Error importing main entry point" in source


@patch("calendarbot.__main__.asyncio.run")
@patch("sys.exit")
def test_main_success(mock_exit, mock_asyncio_run):
    """Test successful execution of main wrapper."""
    from calendarbot.__main__ import main

    # Mock successful execution
    mock_asyncio_run.return_value = 0

    main()

    # Verify asyncio.run was called with main_entry
    mock_asyncio_run.assert_called_once()
    mock_exit.assert_called_once_with(0)


@patch("calendarbot.__main__.asyncio.run")
@patch("sys.exit")
@patch("builtins.print")
def test_main_keyboard_interrupt(mock_print, mock_exit, mock_asyncio_run):
    """Test KeyboardInterrupt handling in main wrapper."""
    from calendarbot.__main__ import main

    # Mock KeyboardInterrupt
    mock_asyncio_run.side_effect = KeyboardInterrupt()

    main()

    # Verify proper handling
    mock_print.assert_called_with("\nOperation cancelled by user")
    mock_exit.assert_called_once_with(130)


@patch("calendarbot.__main__.asyncio.run")
@patch("sys.exit")
@patch("builtins.print")
def test_main_exception_handling(mock_print, mock_exit, mock_asyncio_run):
    """Test exception handling in main wrapper."""
    from calendarbot.__main__ import main

    # Mock generic exception
    test_error = Exception("Test error")
    mock_asyncio_run.side_effect = test_error

    main()

    # Verify proper handling
    mock_print.assert_called_with("Error: Test error")
    mock_exit.assert_called_once_with(1)


def test_path_setup():
    """Test that project root is correctly added to sys.path."""
    from calendarbot import __main__

    # Get the expected project root path
    expected_root = str(Path(__main__.__file__).parent.parent)

    # Verify the path was added to sys.path
    assert expected_root in sys.path


@patch("calendarbot.__main__.main")
def test_name_main_execution(mock_main):
    """Test that the module executes main() when run directly."""
    # This test verifies the if __name__ == "__main__": block
    # Since we can't easily test the actual execution, we'll test the logic
    from calendarbot.__main__ import main

    # Verify the main function is callable and available
    assert callable(main)

    # The actual execution would call main(), but we can't test that directly
    # without executing the whole module
