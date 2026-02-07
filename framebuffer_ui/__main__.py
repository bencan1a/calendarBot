"""Entry point for running framebuffer_ui as a module.

Usage:
    python -m framebuffer_ui
"""

import asyncio

from framebuffer_ui.main import main

if __name__ == "__main__":
    asyncio.run(main())
