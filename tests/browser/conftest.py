"""
Optimized browser test fixtures with improved reliability and timeout handling.
This configuration prevents hanging tests and ensures proper cleanup.
"""

import asyncio
import os
import signal
from pathlib import Path
from typing import AsyncGenerator, Optional

import psutil
import pytest
import pytest_asyncio

# Apply warning filters for websockets deprecation warnings
try:
    from calendarbot.utils.warnings_filter import filter_warnings

    filter_warnings()
except ImportError:
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning, message="remove loop argument")

try:
    from pyppeteer import launch
    from pyppeteer.browser import Browser
    from pyppeteer.page import Page

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False

    # Create stub classes for type checking when pyppeteer is not available
    class Browser:
        pass

    class Page:
        pass

    Browser = None
    Page = None

# Skip all tests if pyppeteer is not available
pytestmark = pytest.mark.skipif(
    not PYPPETEER_AVAILABLE, reason="pyppeteer not available for browser tests"
)


def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


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


async def force_cleanup_chrome():
    """Force cleanup of any remaining Chrome processes."""
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if (
                    proc.info["name"]
                    and "chrome" in proc.info["name"].lower()
                    and proc.info["cmdline"]
                    and "--test-type" in " ".join(proc.info["cmdline"])
                ):
                    proc.terminate()
                    await asyncio.sleep(0.1)
                    if proc.is_running():
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass  # Ignore cleanup errors


def get_chrome_executable():
    """Get Chrome executable path, checking common locations."""
    # Check common locations for Chrome/Chromium
    common_paths = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chrome",
    ]

    for path in common_paths:
        if Path(path).exists():
            return path

    # Return None to let pyppeteer handle default discovery
    return None


@pytest_asyncio.fixture(scope="function")
async def browser() -> AsyncGenerator[Optional[Browser], None]:
    """
    Optimized browser test fixtures with improved reliability and timeout handling.

    Features:
    - Aggressive timeout management to prevent hanging
    - Simplified launch args for better stability
    - Force cleanup to prevent resource leaks
    - Better error handling and recovery
    """
    if not PYPPETEER_AVAILABLE:
        pytest.skip("pyppeteer not available")

    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()
    browser_instance = None

    try:
        # Launch browser with timeout protection
        chrome_path = get_chrome_executable()
        launch_options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-web-security",
                "--no-first-run",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--test-type",  # Mark as test process for cleanup
                "--memory-pressure-off",
                "--single-process",  # Simplified process model
            ],
            "options": {
                "ignoreHTTPSErrors": True,
                "defaultViewport": {"width": 1280, "height": 720},
                "timeout": 30000,  # 30 second launch timeout
            },
        }

        if chrome_path:
            launch_options["executablePath"] = chrome_path

        launch_task = asyncio.create_task(launch(**launch_options))

        # Wait for launch with timeout
        try:
            browser_instance = await asyncio.wait_for(launch_task, timeout=30.0)
        except asyncio.TimeoutError:
            launch_task.cancel()
            await force_cleanup_chrome()
            pytest.skip("Browser launch timed out after 30 seconds")

        if not browser_instance:
            pytest.skip("Failed to create browser instance")

        # Verify browser is responsive
        try:
            pages = await asyncio.wait_for(browser_instance.pages(), timeout=5.0)
        except asyncio.TimeoutError:
            await browser_instance.close()
            pytest.skip("Browser not responsive after launch")

        print(
            f"🟢 Browser launched - Memory: {get_memory_usage():.1f} MB, Chrome: {get_chrome_processes()}"
        )

        yield browser_instance

    except Exception as e:
        print(f"❌ Browser test error: {e}")
        if browser_instance:
            try:
                await asyncio.wait_for(browser_instance.close(), timeout=5.0)
            except:
                pass
        await force_cleanup_chrome()
        pytest.skip(f"Browser test failed: {e}")

    finally:
        # Aggressive cleanup with timeouts
        print("🟢 Cleaning up browser...")

        if browser_instance:
            try:
                # Close all pages first with timeout
                pages_task = asyncio.create_task(browser_instance.pages())
                try:
                    pages = await asyncio.wait_for(pages_task, timeout=3.0)
                    for page in pages:
                        try:
                            await asyncio.wait_for(page.close(), timeout=2.0)
                        except:
                            pass
                except asyncio.TimeoutError:
                    pages_task.cancel()

                # Close browser with timeout
                await asyncio.wait_for(browser_instance.close(), timeout=5.0)

            except Exception as e:
                print(f"⚠️ Warning: Browser cleanup error: {e}")

        # Force cleanup any remaining processes
        await force_cleanup_chrome()

        # Brief wait for system cleanup
        await asyncio.sleep(0.5)

        final_memory = get_memory_usage()
        final_chrome = get_chrome_processes()
        print(f"🟢 Browser cleaned up - Memory: {final_memory:.1f} MB, Chrome: {final_chrome}")


@pytest_asyncio.fixture(scope="function")
async def page(browser: Optional[Browser]) -> AsyncGenerator[Optional[Page], None]:
    """
    Create a browser page with timeout protection and simplified event handling.
    """
    if not browser:
        pytest.skip("No browser instance available")

    page_instance = None

    try:
        # Create page with timeout
        page_instance = await asyncio.wait_for(browser.newPage(), timeout=10.0)

        # Minimal setup to prevent hanging
        await page_instance.setRequestInterception(False)  # Disable to prevent hanging

        # Simple console error logging only
        def on_console(msg):
            if msg.type == "error":
                print(f"Browser console error: {msg.text}")

        page_instance.on("console", on_console)

        # Handle dialogs with timeout
        async def handle_dialog(dialog):
            try:
                await asyncio.wait_for(dialog.accept(), timeout=2.0)
            except:
                pass

        page_instance.on("dialog", lambda dialog: asyncio.create_task(handle_dialog(dialog)))

        yield page_instance

    except Exception as e:
        print(f"❌ Page creation error: {e}")
        if page_instance:
            try:
                await asyncio.wait_for(page_instance.close(), timeout=3.0)
            except:
                pass
        pytest.skip(f"Page creation failed: {e}")

    finally:
        if page_instance:
            try:
                await asyncio.wait_for(page_instance.close(), timeout=3.0)
            except Exception as e:
                print(f"⚠️ Warning: Page cleanup error: {e}")


class BrowserTestUtils:
    """Simplified utility class for browser testing operations with timeout protection."""

    @staticmethod
    async def wait_for_element(page: Page, selector: str, timeout: int = 5000):
        """Wait for element to appear with better error handling."""
        try:
            await asyncio.wait_for(
                page.waitForSelector(selector, {"timeout": timeout}), timeout=timeout / 1000 + 1
            )
            return True
        except Exception:
            return False

    @staticmethod
    async def is_element_visible(page: Page, selector: str) -> bool:
        """Check if element is visible with timeout protection."""
        try:
            element = await asyncio.wait_for(page.querySelector(selector), timeout=2.0)
            if element:
                is_visible = await asyncio.wait_for(
                    page.evaluate(
                        "el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)",
                        element,
                    ),
                    timeout=2.0,
                )
                return is_visible
            return False
        except Exception:
            return False

    @staticmethod
    async def get_element_text(page: Page, selector: str) -> str:
        """Get text content of element with timeout protection."""
        try:
            element = await asyncio.wait_for(page.querySelector(selector), timeout=2.0)
            if element:
                return await asyncio.wait_for(
                    page.evaluate("el => el.textContent", element), timeout=2.0
                )
            return ""
        except Exception:
            return ""

    @staticmethod
    async def navigate_with_timeout(page: Page, url: str, timeout: int = 10000):
        """Navigate to URL with timeout protection."""
        try:
            await asyncio.wait_for(
                page.goto(url, {"timeout": timeout, "waitUntil": "networkidle0"}),
                timeout=timeout / 1000 + 2,
            )
            return True
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False


@pytest.fixture
def browser_utils() -> BrowserTestUtils:
    """Provide browser testing utilities."""
    return BrowserTestUtils()


# Enhanced memory monitoring for browser tests
@pytest.fixture(autouse=True)
def monitor_browser_memory(request):
    """Monitor memory usage and enforce cleanup for browser tests."""

    # Check if this is a browser test
    is_browser_test = (
        "browser" in request.node.name.lower()
        or "browser" in str(request.fspath).lower()
        or any(
            mark.name == "browser"
            for mark in getattr(request.node, "pytestmark", [])
            if hasattr(mark, "name")
        )
    )

    if not is_browser_test:
        yield None
        return

    # Browser test detected
    initial_memory = get_memory_usage()
    initial_chrome = get_chrome_processes()

    yield None

    # Post-test monitoring and cleanup
    final_memory = get_memory_usage()
    final_chrome = get_chrome_processes()

    memory_increase = final_memory - initial_memory
    chrome_increase = final_chrome - initial_chrome

    # Warning thresholds
    if memory_increase > 150:  # 150MB warning threshold
        print(f"⚠️ WARNING: High memory increase: {memory_increase:.1f} MB")

    if chrome_increase > 0:
        print(f"⚠️ WARNING: Chrome processes not cleaned up: +{chrome_increase}")
        # Force cleanup on excessive chrome processes
        if chrome_increase > 3:
            asyncio.run(force_cleanup_chrome())

    # Store metrics for reporting
    request.node.memory_increase = memory_increase
    request.node.chrome_increase = chrome_increase


# Test timeout management
@pytest.fixture(autouse=True)
def browser_test_timeout(request):
    """Apply aggressive timeouts to browser tests to prevent hanging."""

    is_browser_test = (
        "browser" in request.node.name.lower()
        or "browser" in str(request.fspath).lower()
        or any(
            mark.name == "browser"
            for mark in getattr(request.node, "pytestmark", [])
            if hasattr(mark, "name")
        )
    )

    if not is_browser_test:
        yield
        return

    # Set alarm for browser tests (Linux/Unix only)
    def timeout_handler(signum, frame):
        print("⏰ Browser test timeout - forcing cleanup")
        asyncio.run(force_cleanup_chrome())
        raise TimeoutError("Browser test exceeded 60 second timeout")

    # Only set alarm on Unix systems
    if hasattr(signal, "SIGALRM"):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)  # 60 second hard timeout for browser tests

        try:
            yield
        finally:
            signal.alarm(0)  # Cancel alarm
            signal.signal(signal.SIGALRM, old_handler)
    else:
        yield
