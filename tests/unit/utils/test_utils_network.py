"""Comprehensive tests for calendarbot.utils.network module."""

from unittest.mock import MagicMock, patch

import pytest

from calendarbot.utils.network import (
    _is_private_ip,
    get_local_network_interface,
    validate_host_binding,
)


class TestGetLocalNetworkInterface:
    """Test get_local_network_interface function."""

    @patch("calendarbot.utils.network.socket.socket")
    def test_successful_detection_private_ip(self, mock_socket):
        """Test successful detection of private IP."""
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.100", 80)
        mock_socket.return_value.__enter__.return_value = mock_sock

        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = get_local_network_interface()

            assert result == "192.168.1.100"
            mock_logger.return_value.info.assert_called_with(
                "Auto-detected local network interface: 192.168.1.100"
            )

    @patch("calendarbot.utils.network.socket.socket")
    def test_public_ip_fallback_to_localhost(self, mock_socket):
        """Test fallback to localhost when public IP detected."""
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("8.8.8.8", 80)  # Public IP
        mock_socket.return_value.__enter__.return_value = mock_sock

        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = get_local_network_interface()

            assert result == "127.0.0.1"
            mock_logger.return_value.warning.assert_called_with(
                "Detected public IP 8.8.8.8, falling back to localhost"
            )

    @patch("calendarbot.utils.network.socket.socket")
    def test_socket_exception_hostname_fallback(self, mock_socket):
        """Test fallback to hostname method when socket fails."""
        mock_socket.side_effect = Exception("Connection failed")

        with patch("calendarbot.utils.network.socket.gethostname", return_value="test-host"):
            with patch("calendarbot.utils.network.socket.gethostbyname", return_value="10.0.0.50"):
                with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
                    result = get_local_network_interface()

                    assert result == "10.0.0.50"
                    mock_logger.return_value.warning.assert_called_with(
                        "Failed to auto-detect network interface: Connection failed"
                    )
                    mock_logger.return_value.info.assert_called_with(
                        "Detected network interface via hostname: 10.0.0.50"
                    )

    @patch("calendarbot.utils.network.socket.socket")
    def test_hostname_localhost_fallback(self, mock_socket):
        """Test fallback when hostname returns localhost."""
        mock_socket.side_effect = Exception("Connection failed")

        with patch("calendarbot.utils.network.socket.gethostname", return_value="localhost"):
            with patch("calendarbot.utils.network.socket.gethostbyname", return_value="127.0.0.1"):
                with patch("calendarbot.utils.network.logging.getLogger"):
                    result = get_local_network_interface()

                    assert result == "127.0.0.1"
                    # Should continue to final fallback since 127.0.0.1 is not preferred

    @patch("calendarbot.utils.network.socket.socket")
    def test_all_methods_fail_final_fallback(self, mock_socket):
        """Test final fallback when all methods fail."""
        mock_socket.side_effect = Exception("Socket failed")

        with patch(
            "calendarbot.utils.network.socket.gethostname", side_effect=Exception("Hostname failed")
        ):
            with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
                result = get_local_network_interface()

                assert result == "127.0.0.1"
                mock_logger.return_value.warning.assert_called_with(
                    "Could not auto-detect local network interface. Using localhost (127.0.0.1). "
                    "Use --host 0.0.0.0 explicitly for network access."
                )

    @patch("calendarbot.utils.network.socket.socket")
    def test_hostname_exception_final_fallback(self, mock_socket):
        """Test final fallback when hostname method raises exception."""
        mock_socket.side_effect = Exception("Socket failed")

        with patch("calendarbot.utils.network.socket.gethostname", return_value="test-host"):
            with patch(
                "calendarbot.utils.network.socket.gethostbyname",
                side_effect=Exception("DNS failed"),
            ):
                with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
                    result = get_local_network_interface()

                    assert result == "127.0.0.1"
                    # The final fallback message should be called
                    mock_logger.return_value.warning.assert_called_with(
                        "Could not auto-detect local network interface. Using localhost (127.0.0.1). Use --host 0.0.0.0 explicitly for network access."
                    )

    @patch("calendarbot.utils.network.socket.socket")
    def test_non_private_hostname_ip_fallback(self, mock_socket):
        """Test fallback when hostname IP is not private."""
        mock_socket.side_effect = Exception("Socket failed")

        with patch("calendarbot.utils.network.socket.gethostname", return_value="test-host"):
            with patch(
                "calendarbot.utils.network.socket.gethostbyname", return_value="203.0.113.1"
            ):  # Public IP
                with patch("calendarbot.utils.network.logging.getLogger"):
                    result = get_local_network_interface()

                    assert result == "127.0.0.1"


class TestIsPrivateIp:
    """Test _is_private_ip function."""

    def test_class_a_private_range(self):
        """Test Class A private IP range (10.0.0.0/8)."""
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("10.255.255.255") is True
        assert _is_private_ip("10.123.45.67") is True

    def test_class_b_private_range(self):
        """Test Class B private IP range (172.16.0.0/12)."""
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("172.31.255.255") is True
        assert _is_private_ip("172.20.1.1") is True

    def test_class_c_private_range(self):
        """Test Class C private IP range (192.168.0.0/16)."""
        assert _is_private_ip("192.168.0.1") is True
        assert _is_private_ip("192.168.255.255") is True
        assert _is_private_ip("192.168.1.100") is True

    def test_localhost(self):
        """Test localhost IP."""
        assert _is_private_ip("127.0.0.1") is True

    def test_public_ips(self):
        """Test public IP addresses."""
        public_ips = [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "203.0.113.1",  # Documentation range
            "198.51.100.1",  # Documentation range
            "172.15.255.255",  # Just outside Class B private
            "172.32.0.1",  # Just outside Class B private
            "11.0.0.1",  # Just outside Class A private
            "193.168.1.1",  # Similar to Class C but different
        ]

        for ip in public_ips:
            assert _is_private_ip(ip) is False, f"Should be public: {ip}"

    def test_invalid_ip_formats(self):
        """Test invalid IP address formats."""
        invalid_ips = [
            "invalid",
            "192.168.1",  # Missing octet
            "192.168.1.1.1",  # Extra octet
            "256.1.1.1",  # Invalid octet value
            "192.168.-1.1",  # Negative octet
            "192.168.abc.1",  # Non-numeric octet
            "",  # Empty string
            "192.168.1.",  # Trailing dot
            ".192.168.1.1",  # Leading dot
        ]

        for ip in invalid_ips:
            assert _is_private_ip(ip) is False, f"Should be invalid: {ip}"

    def test_edge_cases_class_b(self):
        """Test edge cases for Class B private range."""
        # Just inside the range
        assert _is_private_ip("172.16.0.0") is True
        assert _is_private_ip("172.31.255.255") is True

        # Just outside the range
        assert _is_private_ip("172.15.255.255") is False
        assert _is_private_ip("172.32.0.0") is False

    def test_zero_values(self):
        """Test IP addresses with zero values."""
        assert _is_private_ip("10.0.0.0") is True
        assert _is_private_ip("192.168.0.0") is True
        assert _is_private_ip("172.16.0.0") is True


class TestValidateHostBinding:
    """Test validate_host_binding function."""

    def test_all_interfaces_warning_enabled(self):
        """Test warning when binding to all interfaces with warning enabled."""
        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = validate_host_binding("0.0.0.0", warn_on_all_interfaces=True)

            assert result == "0.0.0.0"
            mock_logger.return_value.warning.assert_called_with(
                "⚠️  SECURITY WARNING: Binding to all interfaces (0.0.0.0). "
                "This exposes the web server to your entire network. "
                "Consider using a specific IP address or localhost for better security."
            )
            mock_logger.return_value.info.assert_called_with(
                "💡 Tip: Use 'calendarbot --web' without --host to auto-detect your local network interface"
            )

    def test_all_interfaces_warning_disabled(self):
        """Test no warning when binding to all interfaces with warning disabled."""
        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = validate_host_binding("0.0.0.0", warn_on_all_interfaces=False)

            assert result == "0.0.0.0"
            mock_logger.return_value.warning.assert_not_called()
            mock_logger.return_value.info.assert_not_called()

    def test_specific_host_no_warning(self):
        """Test no warning when binding to specific host."""
        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = validate_host_binding("192.168.1.100", warn_on_all_interfaces=True)

            assert result == "192.168.1.100"
            mock_logger.return_value.warning.assert_not_called()
            mock_logger.return_value.info.assert_not_called()

    def test_localhost_no_warning(self):
        """Test no warning when binding to localhost."""
        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = validate_host_binding("127.0.0.1", warn_on_all_interfaces=True)

            assert result == "127.0.0.1"
            mock_logger.return_value.warning.assert_not_called()
            mock_logger.return_value.info.assert_not_called()

    def test_empty_host_no_warning(self):
        """Test no warning for empty host string."""
        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = validate_host_binding("", warn_on_all_interfaces=True)

            assert result == ""
            mock_logger.return_value.warning.assert_not_called()
            mock_logger.return_value.info.assert_not_called()

    @pytest.mark.parametrize(
        "host",
        [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.1.1",
            "127.0.0.1",
            "localhost",
            "example.com",
            "::1",  # IPv6 localhost
        ],
    )
    def test_various_hosts_no_warning(self, host):
        """Test various host formats don't trigger warning."""
        with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
            result = validate_host_binding(host, warn_on_all_interfaces=True)

            assert result == host
            mock_logger.return_value.warning.assert_not_called()


class TestNetworkModuleIntegration:
    """Integration tests for network module functions."""

    def test_get_interface_and_validate_integration(self):
        """Test integration between get_local_network_interface and validate_host_binding."""
        with patch("calendarbot.utils.network.socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.getsockname.return_value = ("192.168.1.100", 80)
            mock_socket.return_value.__enter__.return_value = mock_sock

            # Get interface
            interface = get_local_network_interface()

            # Validate it (should not warn)
            with patch("calendarbot.utils.network.logging.getLogger") as mock_logger:
                result = validate_host_binding(interface, warn_on_all_interfaces=True)

                assert result == "192.168.1.100"
                mock_logger.return_value.warning.assert_not_called()

    def test_private_ip_detection_comprehensive(self):
        """Comprehensive test of private IP detection across ranges."""
        # Test boundary values for all private ranges
        test_cases = [
            # Class A: 10.0.0.0/8
            ("10.0.0.0", True),
            ("10.255.255.255", True),
            ("9.255.255.255", False),
            ("11.0.0.0", False),
            # Class B: 172.16.0.0/12
            ("172.16.0.0", True),
            ("172.31.255.255", True),
            ("172.15.255.255", False),
            ("172.32.0.0", False),
            # Class C: 192.168.0.0/16
            ("192.168.0.0", True),
            ("192.168.255.255", True),
            ("192.167.255.255", False),
            ("192.169.0.0", False),
            # Localhost
            ("127.0.0.1", True),
            ("127.0.0.0", True),
            ("127.255.255.255", True),
        ]

        for ip, expected in test_cases:
            assert _is_private_ip(ip) == expected, (
                f"IP {ip} should be {'private' if expected else 'public'}"
            )

    def test_error_handling_robustness(self):
        """Test error handling robustness across module functions."""
        # Test _is_private_ip with malformed inputs
        malformed_inputs = [None, 123, [], {}, object()]

        for bad_input in malformed_inputs:
            try:
                result = _is_private_ip(str(bad_input))
                # Should return False for any malformed input
                assert result is False
            except Exception:
                # Should not raise exceptions for any input
                pytest.fail(f"_is_private_ip raised exception for input: {bad_input}")
