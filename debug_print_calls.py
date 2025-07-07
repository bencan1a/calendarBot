"""Debug script to analyze print calls in the failing tests."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Import the function under test
from calendarbot.setup_wizard import run_simple_wizard


def debug_print_calls():
    """Debug what print calls are being made."""
    print("=== DEBUGGING PRINT CALLS ===")

    # Test 1: URL Warning test
    print("\n1. Testing URL warning scenario (ftp:// URL)...")

    with patch("builtins.input") as mock_input:
        with patch("builtins.print") as mock_print:
            mock_input.return_value = "ftp://test.com/calendar.ics"

            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.mkdir"):
                    with patch("builtins.open", mock_open()):
                        try:
                            result = run_simple_wizard()
                            print(f"Result: {result}")
                        except Exception as e:
                            print(f"Exception during execution: {e}")

                        print(f"Total print calls: {len(mock_print.call_args_list)}")
                        for i, call in enumerate(mock_print.call_args_list):
                            print(f"  Call {i}: args={call.args}, kwargs={call.kwargs}")
                            if call.args:
                                print(f"    First arg: {repr(call.args[0])}")
                            else:
                                print(f"    NO ARGS - this would cause IndexError!")

    print("\n" + "=" * 50)

    # Test 2: Empty URL test
    print("\n2. Testing empty URL scenario...")

    with patch("builtins.input") as mock_input:
        with patch("builtins.print") as mock_print:
            mock_input.return_value = ""

            try:
                result = run_simple_wizard()
                print(f"Result: {result}")
            except Exception as e:
                print(f"Exception during execution: {e}")

            print(f"Total print calls: {len(mock_print.call_args_list)}")
            for i, call in enumerate(mock_print.call_args_list):
                print(f"  Call {i}: args={call.args}, kwargs={call.kwargs}")
                if call.args:
                    print(f"    First arg: {repr(call.args[0])}")
                else:
                    print(f"    NO ARGS - this would cause IndexError!")


if __name__ == "__main__":
    debug_print_calls()
