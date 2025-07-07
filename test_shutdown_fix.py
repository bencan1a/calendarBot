#!/usr/bin/env python3
"""Unit test for the shutdown fix."""

import asyncio
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestWebServerShutdown(unittest.TestCase):
    """Test web server shutdown improvements."""

    def setUp(self):
        """Set up test fixtures."""
        from calendarbot.web.server import WebServer
        from config.settings import CalendarBotSettings

        # Create mock dependencies
        self.mock_settings = CalendarBotSettings()
        self.mock_settings.web_host = "127.0.0.1"
        self.mock_settings.web_port = 8081
        self.mock_settings.auto_kill_existing = False

        self.mock_display_manager = MagicMock()
        self.mock_cache_manager = MagicMock()

        self.web_server = WebServer(
            settings=self.mock_settings,
            display_manager=self.mock_display_manager,
            cache_manager=self.mock_cache_manager,
        )

    def test_shutdown_timeout_handling(self):
        """Test that shutdown doesn't hang indefinitely."""
        # Mock a hanging server.shutdown() call
        mock_server = MagicMock()

        def hanging_shutdown():
            time.sleep(10)  # Simulate hanging shutdown

        mock_server.shutdown.side_effect = hanging_shutdown
        mock_server.server_close = MagicMock()

        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        mock_thread.join = MagicMock()

        self.web_server.server = mock_server
        self.web_server.server_thread = mock_thread
        self.web_server.running = True

        # Test that stop() completes within reasonable time
        start_time = time.time()
        self.web_server.stop()
        end_time = time.time()

        # Should complete in less than 5 seconds (3s timeout + buffer)
        self.assertLess(end_time - start_time, 5.0)
        self.assertFalse(self.web_server.running)
        mock_server.server_close.assert_called_once()

    def test_shutdown_with_normal_server(self):
        """Test normal shutdown scenario."""
        mock_server = MagicMock()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False

        self.web_server.server = mock_server
        self.web_server.server_thread = mock_thread
        self.web_server.running = True

        self.web_server.stop()

        mock_server.shutdown.assert_called_once()
        mock_server.server_close.assert_called_once()
        mock_thread.join.assert_called_once()
        self.assertFalse(self.web_server.running)

    def test_shutdown_when_already_stopped(self):
        """Test shutdown when server is already stopped."""
        self.web_server.running = False

        # Should return early without errors
        self.web_server.stop()
        self.assertFalse(self.web_server.running)

    def test_concurrent_shutdown_calls(self):
        """Test multiple simultaneous shutdown calls."""
        mock_server = MagicMock()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False

        self.web_server.server = mock_server
        self.web_server.server_thread = mock_thread
        self.web_server.running = True

        # Call stop() from multiple threads
        def call_stop():
            self.web_server.stop()

        threads = []
        for _ in range(3):
            t = threading.Thread(target=call_stop)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=2.0)

        # Should handle concurrent calls gracefully
        self.assertFalse(self.web_server.running)


if __name__ == "__main__":
    unittest.main()
