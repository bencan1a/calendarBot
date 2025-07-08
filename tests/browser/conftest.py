"""
Proper browser test fixtures to prevent memory leaks.
This file contains properly implemented async fixtures for browser testing.
"""

import asyncio
import os
from typing import AsyncGenerator

import psutil
import pytest
import pytest_asyncio

# Apply warning filters for websockets deprecation warnings
try:
    from calendarbot.utils.warnings_filter import filter_warnings

    filter_warnings()
except ImportError:
    # Fallback if the warning filter module is not available
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning, message="remove loop argument")

try:
    from pyppeteer import launch
    from pyppeteer.browser import Browser
    from pyppeteer.page import Page

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False
    Browser = None
    Page = None

# Skip all tests if pyppeteer is not available
pytestmark = pytest.mark.skipif(
    not PYPPETEER_AVAILABLE, reason="pyppeteer not available for browser tests"
)


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_chrome_processes():
    """Count Chrome processes currently running."""
    chrome_count = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "chrome" in proc.info["name"].lower():
                chrome_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return chrome_count


@pytest_asyncio.fixture(scope="function")
async def browser() -> AsyncGenerator[Browser, None]:
    """
    Create a Puppeteer browser instance for testing.

    This fixture properly manages browser lifecycle to prevent memory leaks:
    - Uses proper async fixture with scope="function"
    - Ensures browser.close() is always called
    - Includes memory monitoring
    - Uses optimal Chrome args for test environments
    """
    if not PYPPETEER_AVAILABLE:
        pytest.skip("pyppeteer not available")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    print(f"\n🟢 Creating browser - Memory: {initial_memory:.1f} MB, Chrome: {initial_chrome}")

    browser_instance = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-ipc-flooding-protection",
            "--memory-pressure-off",
            "--max_old_space_size=2048",
        ],
        options={"ignoreHTTPSErrors": True, "defaultViewport": {"width": 1280, "height": 720}},
    )

    after_launch_memory = get_memory_usage()
    after_launch_chrome = get_chrome_processes()

    print(
        f"🟢 Browser launched - Memory: {after_launch_memory:.1f} MB (+{after_launch_memory - initial_memory:.1f}), Chrome: {after_launch_chrome} (+{after_launch_chrome - initial_chrome})"
    )

    try:
        yield browser_instance
    except Exception as e:
        print(f"❌ Browser test error: {e}")
        raise
    finally:
        print("🟢 Cleaning up browser...")

        try:
            # Close all pages first
            pages = await browser_instance.pages()
            for page in pages:
                try:
                    await page.close()
                except Exception as e:
                    print(f"⚠️  Warning: Error closing page: {e}")

            # Close browser
            await browser_instance.close()

        except Exception as e:
            print(f"❌ Error during browser cleanup: {e}")

        # Brief wait for cleanup
        await asyncio.sleep(0.5)

        final_memory = get_memory_usage()
        final_chrome = get_chrome_processes()

        print(
            f"🟢 Browser cleaned up - Memory: {final_memory:.1f} MB (+{final_memory - initial_memory:.1f}), Chrome: {final_chrome} (+{final_chrome - initial_chrome})"
        )


@pytest_asyncio.fixture(scope="function")
async def page(browser: Browser) -> AsyncGenerator[Page, None]:
    """
    Create a new page in the browser.

    This fixture ensures proper page lifecycle management:
    - Creates page from browser fixture
    - Enables request interception for better control
    - Handles dialogs and console messages
    - Ensures page.close() is always called
    """
    print("🟢 Creating browser page...")

    page_instance = await browser.newPage()

    # Enable request interception for better control
    await page_instance.setRequestInterception(True)

    # Log network requests for debugging (but don't print to reduce noise)
    async def on_request(request):
        # Just continue requests without logging to reduce memory
        await request.continue_()

    page_instance.on("request", on_request)

    # Log console messages but limit verbosity
    def on_console(msg):
        if msg.type == "error":
            print(f"Browser console error: {msg.text}")

    page_instance.on("console", on_console)

    # Handle dialogs
    page_instance.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

    try:
        yield page_instance
    finally:
        print("🟢 Cleaning up browser page...")
        try:
            await page_instance.close()
        except Exception as e:
            print(f"⚠️  Warning: Error closing page: {e}")


class BrowserTestUtils:
    """Utility class for browser testing operations."""

    @staticmethod
    async def wait_for_element(page: Page, selector: str, timeout: int = 5000):
        """Wait for element to appear."""
        try:
            await page.waitForSelector(selector, {"timeout": timeout})
            return True
        except Exception:
            return False

    @staticmethod
    async def is_element_visible(page: Page, selector: str) -> bool:
        """Check if element is visible."""
        try:
            element = await page.querySelector(selector)
            if element:
                is_visible = await page.evaluate(
                    "el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)",
                    element,
                )
                return is_visible
            return False
        except Exception:
            return False

    @staticmethod
    async def get_element_text(page: Page, selector: str) -> str:
        """Get text content of element."""
        try:
            element = await page.querySelector(selector)
            if element:
                return await page.evaluate("el => el.textContent", element)
            return ""
        except Exception:
            return ""

    @staticmethod
    async def wait_for_api_call(page: Page, api_endpoint: str):
        """Context manager to wait for API calls."""

        class APIWaiter:
            def __init__(self, page, endpoint):
                self.page = page
                self.endpoint = endpoint
                self.response_received = False

            async def __aenter__(self):
                def on_response(response):
                    if self.endpoint in response.url:
                        self.response_received = True

                self.page.on("response", on_response)
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Wait briefly for response
                for _ in range(10):  # 1 second total
                    if self.response_received:
                        break
                    await asyncio.sleep(0.1)

        return APIWaiter(page, api_endpoint)


@pytest.fixture
def browser_utils() -> BrowserTestUtils:
    """Provide browser testing utilities."""
    return BrowserTestUtils()


# Memory monitoring fixture
@pytest.fixture(autouse=True)
def monitor_memory(request):
    """Monitor memory usage before and after each test."""

    # Improved browser test detection
    is_browser_test = (
        "browser" in request.node.name  # Test name contains 'browser'
        or "browser" in str(request.fspath)  # Test file is in browser directory
        or hasattr(request.node, "pytestmark")
        and any(
            mark.name == "browser" for mark in getattr(request.node, "pytestmark", [])
        )  # Has browser marker
    )

    if not is_browser_test:
        # For non-browser tests, yield None and return
        yield None
        return

    # Browser test detected - start memory monitoring
    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    yield None  # Yield None to satisfy pytest fixture requirements

    # Post-test memory monitoring
    final_memory = get_memory_usage()
    final_chrome = get_chrome_processes()

    memory_increase = final_memory - initial_memory
    chrome_increase = final_chrome - initial_chrome

    # Warning thresholds
    if memory_increase > 100:  # 100MB
        print(f"⚠️  WARNING: High memory increase: {memory_increase:.1f} MB")

    if chrome_increase > 0:
        print(f"⚠️  WARNING: Chrome processes not cleaned up: +{chrome_increase}")

    # Store in test node for potential reporting
    request.node.memory_increase = memory_increase
    request.node.chrome_increase = chrome_increase
