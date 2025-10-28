"""Tests for --kill-duplicates CLI flag functionality."""

from unittest.mock import MagicMock, patch

from calendarbot.cli.config import apply_cli_overrides
from calendarbot.cli.parser import create_parser


class TestKillDuplicatesFlag:
    """Test the --kill-duplicates CLI flag functionality."""

    def test_kill_duplicates_flag_parsing(self):
        """Test that --kill-duplicates flag is properly parsed."""
        parser = create_parser()

        # Test flag is parsed correctly
        args = parser.parse_args(["--kill-duplicates"])
        assert hasattr(args, "kill_duplicates")
        assert args.kill_duplicates is True

        # Test default behavior (flag not present)
        args = parser.parse_args([])
        assert hasattr(args, "kill_duplicates")
        assert args.kill_duplicates is False

    def test_kill_duplicates_flag_enables_auto_kill_existing(self):
        """Test that --kill-duplicates flag enables auto_kill_existing setting."""
        # Mock settings object
        mock_settings = MagicMock()
        mock_settings.auto_kill_existing = False  # Default should be False

        # Mock args with kill_duplicates flag
        mock_args = MagicMock()
        mock_args.kill_duplicates = True

        # Mock other attributes that might be checked
        for attr in ["renderer", "layout", "display_type", "rpi", "compact", "epaper"]:
            setattr(
                mock_args, attr, None if attr in ["renderer", "layout", "display_type"] else False
            )

        # Apply CLI overrides
        result = apply_cli_overrides(mock_settings, mock_args)

        # Verify auto_kill_existing was enabled
        assert result.auto_kill_existing is True

    def test_kill_duplicates_flag_disabled_by_default(self):
        """Test that auto_kill_existing remains False when flag is not used."""
        # Mock settings object
        mock_settings = MagicMock()
        mock_settings.auto_kill_existing = False  # Default should be False

        # Mock args without kill_duplicates flag
        mock_args = MagicMock()
        mock_args.kill_duplicates = False

        # Mock other attributes that might be checked
        for attr in ["renderer", "layout", "display_type", "rpi", "compact", "epaper"]:
            setattr(
                mock_args, attr, None if attr in ["renderer", "layout", "display_type"] else False
            )

        # Apply CLI overrides
        result = apply_cli_overrides(mock_settings, mock_args)

        # Verify auto_kill_existing remains disabled
        assert result.auto_kill_existing is False

    def test_kill_duplicates_flag_with_web_mode(self):
        """Test --kill-duplicates flag works correctly with web mode."""
        parser = create_parser()

        # Test combined flags
        args = parser.parse_args(["--web", "--kill-duplicates", "--port", "3000"])

        assert args.web is True
        assert args.kill_duplicates is True
        assert args.port == 3000

    def test_kill_duplicates_logging_output(self):
        """Test that enabling kill_duplicates produces expected log output."""
        # Mock settings object
        mock_settings = MagicMock()
        mock_settings.auto_kill_existing = False

        # Mock args with kill_duplicates flag
        mock_args = MagicMock()
        mock_args.kill_duplicates = True

        # Mock other attributes
        for attr in ["renderer", "layout", "display_type", "rpi", "compact", "epaper"]:
            setattr(
                mock_args, attr, None if attr in ["renderer", "layout", "display_type"] else False
            )

        # Mock logger to capture debug message
        with patch("calendarbot.cli.config.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Apply CLI overrides
            apply_cli_overrides(mock_settings, mock_args)

            # Verify debug log was called with our expected message (among potentially others)
            mock_logger.debug.assert_any_call(
                "Enabled auto_kill_existing from --kill-duplicates flag"
            )
