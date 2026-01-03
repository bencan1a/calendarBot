"""Entry point for running framebuffer_ui as a module.

Usage:
    python -m framebuffer_ui
"""

from framebuffer_ui.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
