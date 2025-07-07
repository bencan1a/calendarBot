"""Debug what happens with empty URL in run_simple_wizard."""

from unittest.mock import mock_open, patch

from calendarbot.setup_wizard import run_simple_wizard


def debug_empty_url():
    """Debug what print calls are made with empty URL."""
    print("=== DEBUGGING EMPTY URL SCENARIO ===")

    with patch("builtins.input") as mock_input:
        with patch("builtins.print") as mock_print:
            mock_input.return_value = ""  # Empty URL

            result = run_simple_wizard()

            print(f"Function returned: {result}")
            print(f"Total print calls: {len(mock_print.call_args_list)}")

            for i, call in enumerate(mock_print.call_args_list):
                print(f"Call {i}: args={call.args}, kwargs={call.kwargs}")
                if call.args:
                    print(f"  Content: {repr(call.args[0])}")
                else:
                    print(f"  No args (empty print)")


if __name__ == "__main__":
    debug_empty_url()
