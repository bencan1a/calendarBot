#!/usr/bin/env python3
"""
Test script to reproduce websocket deprecation warnings.
"""

import asyncio
import sys
import warnings
from pathlib import Path

# Enable all warnings
warnings.filterwarnings("default")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pyppeteer import launch

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False
    print("❌ pyppeteer not available")
    sys.exit(1)


async def test_browser_launch():
    """Test browser launch to trigger websocket warnings."""
    print("🔍 Testing browser launch to catch websocket deprecation warnings...")

    browser = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-gpu",
        ],
        options={"ignoreHTTPSErrors": True, "defaultViewport": {"width": 1280, "height": 720}},
    )

    try:
        page = await browser.newPage()
        await page.goto("about:blank")
        title = await page.title()
        print(f"✅ Browser launched successfully, title: '{title}'")
    finally:
        await browser.close()
        print("🔄 Browser closed")


if __name__ == "__main__":
    print("🚀 Running WebSocket deprecation test...")
    asyncio.run(test_browser_launch())
    print("✅ Test completed")
