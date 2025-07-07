"""Unit tests for network utilities."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.utils.network import (
    _is_private_ip,
    get_local_network_interface,
    validate_host_binding,
)


class TestPrivateIPValidation:
    """Test private IP address validation."""

    def test_is_private_ip_valid_ranges(self):
        """Test that private IP ranges are correctly identified."""
        # Test 10.x.x.x range
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("10.255.255.255") is True

        # Test 172.16-31.x.x range
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("172.31.255.255") is True

        # Test 192.168.x.x range
        assert _is_private_ip("192.168.1.1") is True
        assert _is_private_ip("192.168.255.255") is True

        # Test localhost
        assert _is_private_ip("127.0.0.1") is True

    def test_is_private_ip_public_ranges(self):
        """Test that public IP ranges are correctly identified."""
        # Public IP examples
        assert _is_private_ip("8.8.8.8") is False
        assert _is_private_ip("1.1.1.1") is False
        assert _is_private_ip("172.15.0.1") is False  # Just outside private range
        assert _is_private_ip("172.32.0.1") is False  # Just outside private range

    def test_is_private_ip_invalid_format(self):
        """Test handling of invalid IP formats."""
        assert _is_private_ip("invalid") is False
        assert _is_private_ip("192.168.1") is False
        assert _is_private_ip("192.168.1.1.1") is False
        assert _is_private_ip("") is False


class TestNetworkInterfaceDetection:
    """Test network interface detection."""

    @patch("socket.socket")
    def test_get_local_network_interface_success(self, mock_socket):
        """Test successful network interface detection."""
        # Mock socket behavior
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.100", 12345)
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = get_local_network_interface()

        assert result == "192.168.1.100"
        mock_sock.connect.assert_called_once_with(("8.8.8.8", 80))

    @patch("socket.socket")
    def test_get_local_network_interface_public_ip_fallback(self, mock_socket):
        """Test fallback when public IP is detected."""
        # Mock socket to return public IP
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("8.8.8.8", 12345)
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = get_local_network_interface()

        assert result == "127.0.0.1"

    @patch("socket.gethostbyname")
    @patch("socket.gethostname")
    @patch("socket.socket")
    def test_get_local_network_interface_hostname_fallback(
        self, mock_socket, mock_gethostname, mock_gethostbyname
    ):
        """Test fallback to hostname-based detection."""
        # First method fails
        mock_socket.side_effect = Exception("Network error")

        # Hostname method succeeds
        mock_gethostname.return_value = "testhost"
        mock_gethostbyname.return_value = "192.168.1.50"

        result = get_local_network_interface()

        assert result == "192.168.1.50"

    @patch("socket.gethostbyname")
    @patch("socket.gethostname")
    @patch("socket.socket")
    def test_get_local_network_interface_complete_fallback(
        self, mock_socket, mock_gethostname, mock_gethostbyname
    ):
        """Test complete fallback to localhost."""
        # All methods fail
        mock_socket.side_effect = Exception("Network error")
        mock_gethostname.side_effect = Exception("Hostname error")

        result = get_local_network_interface()

        assert result == "127.0.0.1"

    @patch("socket.gethostbyname")
    @patch("socket.gethostname")
    @patch("socket.socket")
    def test_get_local_network_interface_hostname_localhost_fallback(
        self, mock_socket, mock_gethostname, mock_gethostbyname
    ):
        """Test fallback when hostname returns localhost."""
        # First method fails
        mock_socket.side_effect = Exception("Network error")

        # Hostname method returns localhost
        mock_gethostname.return_value = "testhost"
        mock_gethostbyname.return_value = "127.0.0.1"

        result = get_local_network_interface()

        assert result == "127.0.0.1"


class TestHostBindingValidation:
    """Test host binding validation."""

    def test_validate_host_binding_all_interfaces_warning(self, caplog):
        """Test warning when binding to all interfaces."""
        import logging

        caplog.set_level(logging.WARNING)

        result = validate_host_binding("0.0.0.0", warn_on_all_interfaces=True)

        assert result == "0.0.0.0"
        assert "SECURITY WARNING" in caplog.text
        assert "Binding to all interfaces" in caplog.text

    def test_validate_host_binding_no_warning_when_disabled(self, caplog):
        """Test no warning when warning is disabled."""
        import logging

        caplog.set_level(logging.WARNING)

        result = validate_host_binding("0.0.0.0", warn_on_all_interfaces=False)

        assert result == "0.0.0.0"
        assert "SECURITY WARNING" not in caplog.text

    def test_validate_host_binding_specific_ip_no_warning(self, caplog):
        """Test no warning for specific IP addresses."""
        import logging

        caplog.set_level(logging.WARNING)

        result = validate_host_binding("192.168.1.100", warn_on_all_interfaces=True)

        assert result == "192.168.1.100"
        assert "SECURITY WARNING" not in caplog.text

    def test_validate_host_binding_localhost_no_warning(self, caplog):
        """Test no warning for localhost."""
        import logging

        caplog.set_level(logging.WARNING)

        result = validate_host_binding("127.0.0.1", warn_on_all_interfaces=True)

        assert result == "127.0.0.1"
        assert "SECURITY WARNING" not in caplog.text


@pytest.mark.unit
class TestNetworkUtilsIntegration:
    """Integration tests for network utilities."""

    def test_network_detection_integration(self):
        """Test that network detection functions work together."""
        # This is a basic integration test that ensures the functions
        # can be called without errors in a real environment
        host = get_local_network_interface()
        validated_host = validate_host_binding(host, warn_on_all_interfaces=False)

        # Should return a valid IP address format
        assert isinstance(host, str)
        assert isinstance(validated_host, str)
        assert host == validated_host

        # Should be a valid private IP or localhost
        assert _is_private_ip(host) is True
