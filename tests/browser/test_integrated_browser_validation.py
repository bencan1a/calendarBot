#!/usr/bin/env python3
"""
Integrated browser validation tests for pytest.
Converts the working simple_browser_validation.py approach to pytest format.
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False

from calendarbot.cache.manager import CacheManager
from calendarbot.config.settings import CalendarBotSettings
from calendarbot.display.manager import DisplayManager
from calendarbot.sources.manager import SourceManager
from calendarbot.ui.navigation import NavigationState
from calendarbot.web.server import WebServer

# Skip all tests if pyppeteer is not available
pytestmark = pytest.mark.skipif(
    not PYPPETEER_AVAILABLE, reason="pyppeteer not available for browser tests"
)


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


@pytest.fixture
def test_settings():
    """Create test settings for browser testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        settings = CalendarBotSettings(
            ics_url="http://localhost:8999/test.ics",
            config_dir=temp_path / "config",
            data_dir=temp_path / "data",
            cache_dir=temp_path / "cache",
            web_host="127.0.0.1",
            web_port=8996,  # Use different port to avoid conflicts
            web_layout="4x8",
            app_name="CalendarBot-IntegratedTest",
            refresh_interval=60,
            max_retries=2,
            request_timeout=5,
            auto_kill_existing=True,
            display_enabled=True,
        )

        settings.logging.console_level = "DEBUG"
        settings.logging.file_enabled = False

        yield settings


async def _setup_web_server(settings):
    """Setup web server with mock renderer."""
    # Create required components
    cache_manager = CacheManager(settings)
    await cache_manager.initialize()

    source_manager = SourceManager(settings, cache_manager)
    display_manager = DisplayManager(settings)
    navigation_state = NavigationState()

    # Create web server
    web_server = WebServer(settings, display_manager, cache_manager, navigation_state)

    # Mock the HTML renderer with comprehensive test content
    mock_renderer = MagicMock()
    mock_renderer.layout = settings.web_layout
    mock_renderer.render_events.return_value = """
    <!DOCTYPE html>
    <html class="layout-4x8">
    <head>
        <title>Calendar Bot - Integrated Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; }
            .nav-btn { padding: 10px; margin: 5px; cursor: pointer; }
            .event-item { padding: 10px; margin: 5px; border: 1px solid #ccc; }
            .status-line { margin-top: 20px; font-size: 12px; }
        </style>
        <script>
            window.calendarBot = {
                initialized: true,
                layout: '4x8',
                navigate: function(direction) {
                    console.log('Navigate:', direction);
                    return fetch('/api/navigate/' + direction, {method: 'POST'});
                },
                getCurrentTheme: function() {
                    return this.layout;
                },
                toggleTheme: function() {
                    this.layout = this.layout === '4x8' ? '3x4' : '4x8';
                    document.documentElement.className = 'layout-' + this.layout;
                    document.getElementById('current-layout').textContent = this.layout;
                    return fetch('/api/layout', {method: 'POST'});
                }
            };

            window.navigate = function(direction) {
                return window.calendarBot.navigate(direction);
            };

            window.toggleTheme = function() {
                return window.calendarBot.toggleTheme();
            };

            window.getCurrentTheme = function() {
                return window.calendarBot.getCurrentTheme();
            };

            console.log('CalendarBot integrated test initialized');
        </script>
    </head>
    <body>
        <div class="header">
            <h1 class="calendar-title">Calendar for Today</h1>
            <div class="navigation-controls">
                <button class="nav-btn" data-action="prev" onclick="calendarBot.navigate('prev')">&larr; Previous</button>
                <button class="nav-btn" data-action="next" onclick="calendarBot.navigate('next')">Next &rarr;</button>
            </div>
        </div>
        <div class="calendar-content">
            <div class="events-section">
                <h3>Today's Events</h3>
                <div class="event-item">
                    <strong>10:00 AM - 11:00 AM</strong><br>
                    Integrated Test Meeting - Browser validation via pytest
                </div>
            </div>
            <div class="date-info">
                <span class="current-date">Test Date - Integrated</span>
            </div>
        </div>
        <div class="status-line">
            Ready • Theme: <span id="current-layout">4x8</span> • Integrated Test Mode
        </div>
    </body>
    </html>
    """

    display_manager.renderer = mock_renderer
    return web_server, cache_manager


async def _test_browser_core_functionality(settings):
    """Core browser functionality test using working approach."""
    web_server, cache_manager = await _setup_web_server(settings)

    try:
        # Start web server
        web_server.start()
        await asyncio.sleep(1)  # Give server time to start

        # Launch browser with system Chromium
        chrome_path = get_chrome_executable()
        launch_options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
            "options": {
                "ignoreHTTPSErrors": True,
                "defaultViewport": {"width": 1280, "height": 720},
            },
        }

        if chrome_path:
            launch_options["executablePath"] = chrome_path

        browser = await launch(**launch_options)

        try:
            # Create page and navigate
            page = await browser.newPage()

            # Navigate to the web server
            server_url = f"http://{settings.web_host}:{settings.web_port}"

            await page.goto(server_url, {"waitUntil": "networkidle0", "timeout": 8000})

            # Test 1: Check page title
            title = await page.title()
            assert "Calendar Bot" in title, f"Expected 'Calendar Bot' in title, got: {title}"

            # Test 2: Check CalendarBot JavaScript initialization
            calendar_bot_ready = await page.evaluate(
                "window.calendarBot && window.calendarBot.initialized"
            )
            assert calendar_bot_ready, "CalendarBot JavaScript not initialized"

            # Test 3: Check navigation buttons are present
            nav_buttons = await page.querySelectorAll(".nav-btn")
            assert (
                len(nav_buttons) >= 2
            ), f"Expected at least 2 navigation buttons, found {len(nav_buttons)}"

            # Test 4: Check calendar content is displayed
            events_section = await page.querySelector(".events-section")
            assert events_section, "Events section not found"

            # Test 5: Check layout detection
            layout = await page.evaluate("window.calendarBot.layout")
            assert layout == "4x8", f"Expected layout '4x8', got: {layout}"

            # Test 6: Test responsive design (mobile viewport)
            await page.setViewport({"width": 375, "height": 667, "isMobile": True})
            await asyncio.sleep(0.5)

            # Check that page still renders correctly on mobile
            mobile_title = await page.querySelector(".calendar-title")
            assert mobile_title, "Calendar title not found in mobile view"

            # Reset to desktop
            await page.setViewport({"width": 1280, "height": 720, "isMobile": False})
            await asyncio.sleep(0.5)

        finally:
            await browser.close()

    finally:
        web_server.stop()
        await cache_manager.cleanup_old_events(days_old=0)


@pytest.mark.browser
@pytest.mark.smoke
@pytest.mark.timeout(60)  # 60 second timeout
def test_browser_view_rendering(test_settings):
    """Test that the browser view renders correctly."""
    start_time = time.time()

    # Use asyncio.run to avoid pytest-asyncio event loop conflicts
    asyncio.run(_test_browser_core_functionality(test_settings))

    elapsed = time.time() - start_time
    print(f"\n📊 Browser rendering test completed in {elapsed:.2f} seconds")


async def _test_navigation_functionality(settings):
    """Test navigation forward/back functionality."""
    web_server, cache_manager = await _setup_web_server(settings)

    try:
        web_server.start()
        await asyncio.sleep(1)

        chrome_path = get_chrome_executable()
        launch_options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
            "options": {
                "ignoreHTTPSErrors": True,
                "defaultViewport": {"width": 1280, "height": 720},
            },
        }

        if chrome_path:
            launch_options["executablePath"] = chrome_path

        browser = await launch(**launch_options)

        try:
            page = await browser.newPage()
            server_url = f"http://{settings.web_host}:{settings.web_port}"
            await page.goto(server_url, {"waitUntil": "networkidle0", "timeout": 8000})

            # Test navigation button clicks
            next_button = await page.querySelector('[data-action="next"]')
            assert next_button, "Next button not found"

            prev_button = await page.querySelector('[data-action="prev"]')
            assert prev_button, "Previous button not found"

            # Test JavaScript navigation functions
            navigate_exists = await page.evaluate('typeof window.navigate === "function"')
            assert navigate_exists, "Navigate function not available"

            # Test layout toggle functionality
            toggle_layout_exists = await page.evaluate('typeof window.toggleTheme === "function"')
            assert toggle_layout_exists, "Toggle layout function not available"

        finally:
            await browser.close()

    finally:
        web_server.stop()
        await cache_manager.cleanup_old_events(days_old=0)


@pytest.mark.browser
@pytest.mark.smoke
def test_navigation_forward_back(test_settings):
    """Test navigation forward/back functionality."""
    start_time = time.time()

    asyncio.run(_test_navigation_functionality(test_settings))

    elapsed = time.time() - start_time
    print(f"\n📊 Navigation test completed in {elapsed:.2f} seconds")


async def _test_calendar_information_display(settings):
    """Test calendar information display functionality."""
    web_server, cache_manager = await _setup_web_server(settings)

    try:
        web_server.start()
        await asyncio.sleep(1)

        chrome_path = get_chrome_executable()
        launch_options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
            "options": {
                "ignoreHTTPSErrors": True,
                "defaultViewport": {"width": 1280, "height": 720},
            },
        }

        if chrome_path:
            launch_options["executablePath"] = chrome_path

        browser = await launch(**launch_options)

        try:
            page = await browser.newPage()
            server_url = f"http://{settings.web_host}:{settings.web_port}"
            await page.goto(server_url, {"waitUntil": "networkidle0", "timeout": 8000})

            # Check calendar content sections
            calendar_content = await page.querySelector(".calendar-content")
            assert calendar_content, "Calendar content not found"

            events_section = await page.querySelector(".events-section")
            assert events_section, "Events section not found"

            # Check date information
            date_info = await page.querySelector(".current-date")
            assert date_info, "Date information not found"

            # Check status line
            status_line = await page.querySelector(".status-line")
            assert status_line, "Status line not found"

            # Check status line contains layout info
            status_text = await page.evaluate('document.querySelector(".status-line").textContent')
            assert "Theme:" in status_text, "Theme information not in status line"

        finally:
            await browser.close()

    finally:
        web_server.stop()
        await cache_manager.cleanup_old_events(days_old=0)


@pytest.mark.browser
@pytest.mark.smoke
def test_calendar_information_display(test_settings):
    """Test calendar information display functionality."""
    start_time = time.time()

    asyncio.run(_test_calendar_information_display(test_settings))

    elapsed = time.time() - start_time
    print(f"\n📊 Calendar information test completed in {elapsed:.2f} seconds")


@pytest.mark.browser
def test_integrated_browser_validation_suite(test_settings):
    """Run all three core browser tests in sequence."""
    start_time = time.time()

    print("\n🚀 Running Integrated Browser Validation Suite")
    print("=" * 60)

    # Test 1: Browser view rendering
    print("📄 Testing browser view rendering...")
    asyncio.run(_test_browser_core_functionality(test_settings))
    print("✓ Browser view rendering: PASSED")

    # Test 2: Navigation functionality
    print("🧭 Testing navigation functionality...")
    asyncio.run(_test_navigation_functionality(test_settings))
    print("✓ Navigation functionality: PASSED")

    # Test 3: Calendar information display
    print("📅 Testing calendar information display...")
    asyncio.run(_test_calendar_information_display(test_settings))
    print("✓ Calendar information display: PASSED")

    elapsed = time.time() - start_time
    print(f"\n🎉 All browser tests passed in {elapsed:.2f} seconds!")
    print("✅ Integrated browser validation: COMPLETE")


if __name__ == "__main__":
    # Allow running as standalone for debugging
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        settings = CalendarBotSettings(
            ics_url="http://localhost:8999/test.ics",
            config_dir=temp_path / "config",
            data_dir=temp_path / "data",
            cache_dir=temp_path / "cache",
            web_host="127.0.0.1",
            web_port=8996,
            web_layout="4x8",
            app_name="CalendarBot-Standalone",
            refresh_interval=60,
            max_retries=2,
            request_timeout=5,
            auto_kill_existing=True,
            display_enabled=True,
        )
        settings.logging.console_level = "DEBUG"
        settings.logging.file_enabled = False

        # Run the integrated test
        result = asyncio.run(_test_browser_core_functionality(settings))
        print(f"Standalone test result: {result}")
