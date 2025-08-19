"""
Tests for unclutter integration in BrowserManager.

This module tests the cursor hiding functionality provided by unclutter
integration in the BrowserManager class for kiosk mode operation.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from calendarbot.kiosk.browser_manager import BrowserConfig, BrowserManager, BrowserState


class TestBrowserManagerUnclutter:
    """Test BrowserManager unclutter integration."""

    @pytest.fixture
    def unclutter_config(self) -> BrowserConfig:
        """Create test configuration with unclutter enabled."""
        return BrowserConfig(
            hide_cursor=True,
            unclutter_idle_seconds=0.1,
            unclutter_executable="unclutter",
        )

    @pytest.fixture
    def no_unclutter_config(self) -> BrowserConfig:
        """Create test configuration with unclutter disabled."""
        return BrowserConfig(
            hide_cursor=False,
        )

    @pytest.fixture
    def browser_manager(self, unclutter_config: BrowserConfig) -> BrowserManager:
        """Create BrowserManager instance for testing."""
        return BrowserManager(unclutter_config)

    async def test_start_unclutter_when_enabled_and_available(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _start_unclutter starts process when enabled and available."""
        with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
            # Mock 'which' command success
            mock_run.return_value = Mock(returncode=0)

            # Mock unclutter process
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process is running
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = await browser_manager._start_unclutter()

            assert result is True
            assert browser_manager._unclutter_process == mock_process

            # Verify 'which' command was called
            mock_run.assert_called_once_with(
                ["which", "unclutter"], check=True, capture_output=True, text=True
            )

            # Verify unclutter process was started with correct args
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            assert args[0] == ["unclutter", "-idle", "0.1", "-root"]
            assert "DISPLAY" in kwargs["env"]
            assert kwargs["env"]["DISPLAY"] == ":0"

    async def test_start_unclutter_when_disabled(self, no_unclutter_config: BrowserConfig) -> None:
        """Test _start_unclutter returns True when disabled."""
        manager = BrowserManager(no_unclutter_config)

        with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
            result = await manager._start_unclutter()

            assert result is True
            assert manager._unclutter_process is None
            mock_run.assert_not_called()
            mock_popen.assert_not_called()

    async def test_start_unclutter_when_not_available(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _start_unclutter handles unclutter not being available."""
        with patch("subprocess.run") as mock_run:
            # Mock 'which' command failure
            mock_run.side_effect = subprocess.CalledProcessError(1, "which")

            result = await browser_manager._start_unclutter()

            assert result is False
            assert browser_manager._unclutter_process is None

    async def test_start_unclutter_process_exits_immediately(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _start_unclutter handles process exiting immediately."""
        with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
            # Mock 'which' command success
            mock_run.return_value = Mock(returncode=0)

            # Mock unclutter process that exits immediately
            mock_process = Mock()
            mock_process.poll.return_value = 1  # Process has exited
            mock_popen.return_value = mock_process

            result = await browser_manager._start_unclutter()

            assert result is False
            assert browser_manager._unclutter_process is None

    async def test_start_unclutter_exception_handling(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _start_unclutter handles exceptions gracefully."""
        with patch("subprocess.run") as mock_run:
            # Mock exception during startup
            mock_run.side_effect = Exception("Test exception")

            result = await browser_manager._start_unclutter()

            assert result is False
            assert browser_manager._unclutter_process is None

    async def test_stop_unclutter_graceful_termination(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _stop_unclutter gracefully terminates process."""
        # Set up mock unclutter process
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process exits after terminate
        browser_manager._unclutter_process = mock_process

        await browser_manager._stop_unclutter()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_not_called()
        assert browser_manager._unclutter_process is None

    async def test_stop_unclutter_force_kill(self, browser_manager: BrowserManager) -> None:
        """Test _stop_unclutter force kills if graceful termination fails."""
        # Set up mock unclutter process that doesn't respond to terminate
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running after terminate
        browser_manager._unclutter_process = mock_process

        await browser_manager._stop_unclutter()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert browser_manager._unclutter_process is None

    async def test_stop_unclutter_when_no_process(self, browser_manager: BrowserManager) -> None:
        """Test _stop_unclutter handles no process gracefully."""
        browser_manager._unclutter_process = None

        # Should not raise exception
        await browser_manager._stop_unclutter()

        assert browser_manager._unclutter_process is None

    async def test_stop_unclutter_exception_handling(self, browser_manager: BrowserManager) -> None:
        """Test _stop_unclutter handles exceptions during termination."""
        # Set up mock unclutter process that raises exception
        mock_process = Mock()
        mock_process.terminate.side_effect = Exception("Test exception")
        browser_manager._unclutter_process = mock_process

        # Should not raise exception
        await browser_manager._stop_unclutter()

        assert browser_manager._unclutter_process is None

    async def test_browser_start_includes_unclutter(self, browser_manager: BrowserManager) -> None:
        """Test browser startup includes unclutter when enabled."""
        with (
            patch.object(browser_manager, "_launch_process") as mock_launch,
            patch.object(browser_manager, "_start_monitoring") as mock_monitoring,
            patch.object(browser_manager, "_start_unclutter") as mock_unclutter,
            patch.object(browser_manager, "_wait_for_responsive") as mock_responsive,
        ):
            # Mock successful browser launch
            mock_process = Mock()
            mock_process.pid = 12345
            mock_launch.return_value = mock_process
            mock_unclutter.return_value = True
            mock_responsive.return_value = True

            result = await browser_manager.start_browser("http://localhost:8080")

            assert result is True
            mock_unclutter.assert_called_once()

    async def test_browser_stop_includes_unclutter(self, browser_manager: BrowserManager) -> None:
        """Test browser shutdown includes unclutter cleanup."""
        # Set up browser as running
        browser_manager._process = Mock()
        browser_manager._process.poll.return_value = 0  # Process exits
        browser_manager._state = BrowserState.RUNNING

        with (
            patch.object(browser_manager, "_stop_monitoring") as mock_monitoring,
            patch.object(browser_manager, "_stop_unclutter") as mock_unclutter,
        ):
            result = await browser_manager.stop_browser()

            assert result is True
            mock_unclutter.assert_called_once()

    async def test_cleanup_process_state_includes_unclutter(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _cleanup_process_state clears unclutter process."""
        browser_manager._unclutter_process = Mock()
        browser_manager._process = Mock()

        browser_manager._cleanup_process_state()

        assert browser_manager._unclutter_process is None
        assert browser_manager._process is None
        assert browser_manager._state == BrowserState.STOPPED

    async def test_handle_startup_failure_includes_unclutter(
        self, browser_manager: BrowserManager
    ) -> None:
        """Test _handle_startup_failure includes unclutter cleanup."""
        with (
            patch.object(browser_manager, "_stop_monitoring") as mock_monitoring,
            patch.object(browser_manager, "_stop_unclutter") as mock_unclutter,
        ):
            await browser_manager._handle_startup_failure("Test error")

            mock_unclutter.assert_called_once()
            assert browser_manager._state == BrowserState.FAILED


class TestBrowserConfigUnclutter:
    """Test BrowserConfig unclutter settings."""

    def test_default_unclutter_config(self) -> None:
        """Test default unclutter configuration."""
        config = BrowserConfig()

        assert config.hide_cursor is True
        assert config.unclutter_idle_seconds == 0.1
        assert config.unclutter_executable == "unclutter"

    def test_custom_unclutter_config(self) -> None:
        """Test custom unclutter configuration."""
        config = BrowserConfig(
            hide_cursor=False,
            unclutter_idle_seconds=5.0,
            unclutter_executable="/usr/bin/unclutter",
        )

        assert config.hide_cursor is False
        assert config.unclutter_idle_seconds == 5.0
        assert config.unclutter_executable == "/usr/bin/unclutter"
