"""Entry point for `python -m calendarbot` command."""

import sys
import asyncio
from pathlib import Path

# Add project root to path to ensure imports work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import main_entry

if __name__ == "__main__":
    # Run the main entry point
    exit_code = asyncio.run(main_entry())
    sys.exit(exit_code)