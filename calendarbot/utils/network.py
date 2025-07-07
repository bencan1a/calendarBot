"""Network utilities for CalendarBot."""

import logging
import socket
from typing import Optional


def get_local_network_interface() -> str:
    """
    Auto-detect the local network interface for safer binding.

    Returns the local network IP address (e.g., 192.168.1.x) instead of binding to all
    interfaces (0.0.0.0), which provides better security while maintaining network accessibility.

    Returns:
        str: Local network IP address, or fallback values with appropriate warnings
    """
    logger = logging.getLogger("calendarbot.network")

    try:
        # Method 1: Connect to a remote address to determine local interface
        # This doesn't actually send data, just determines routing
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use Google's public DNS (doesn't actually connect)
            s.connect(("8.8.8.8", 80))
            local_ip: str = s.getsockname()[0]

            # Validate that we got a private network address
            if _is_private_ip(local_ip):
                logger.info(f"Auto-detected local network interface: {local_ip}")
                return local_ip
            else:
                logger.warning(f"Detected public IP {local_ip}, falling back to localhost")
                return "127.0.0.1"

    except Exception as e:
        logger.warning(f"Failed to auto-detect network interface: {e}")

    try:
        # Method 2: Get hostname-based address
        hostname = socket.gethostname()
        hostname_ip: str = socket.gethostbyname(hostname)

        if _is_private_ip(hostname_ip) and hostname_ip != "127.0.0.1":
            logger.info(f"Detected network interface via hostname: {hostname_ip}")
            return hostname_ip

    except Exception as e:
        logger.warning(f"Failed to detect interface via hostname: {e}")

    # Fallback to localhost with security note
    logger.warning(
        "Could not auto-detect local network interface. Using localhost (127.0.0.1). "
        "Use --host 0.0.0.0 explicitly for network access."
    )
    return "127.0.0.1"


def _is_private_ip(ip: str) -> bool:
    """Check if IP address is in private ranges."""
    try:
        octets = [int(x) for x in ip.split(".")]

        # Must have exactly 4 octets for a valid IPv4 address
        if len(octets) != 4:
            return False

        # Private IP ranges:
        # 10.0.0.0/8 (10.0.0.0 - 10.255.255.255)
        # 172.16.0.0/12 (172.16.0.0 - 172.31.255.255)
        # 192.168.0.0/16 (192.168.0.0 - 192.168.255.255)

        if octets[0] == 10:
            return True
        elif octets[0] == 172 and 16 <= octets[1] <= 31:
            return True
        elif octets[0] == 192 and octets[1] == 168:
            return True
        elif ip == "127.0.0.1":
            return True  # Localhost

        return False

    except (ValueError, IndexError):
        return False


def validate_host_binding(host: str, warn_on_all_interfaces: bool = True) -> str:
    """
    Validate and potentially warn about host binding choices.

    Args:
        host: The host address to bind to
        warn_on_all_interfaces: Whether to warn when binding to all interfaces

    Returns:
        str: The validated host address
    """
    logger = logging.getLogger("calendarbot.network")

    if host == "0.0.0.0" and warn_on_all_interfaces:  # nosec B104
        logger.warning(
            "⚠️  SECURITY WARNING: Binding to all interfaces (0.0.0.0). "
            "This exposes the web server to your entire network. "
            "Consider using a specific IP address or localhost for better security."
        )
        logger.info(
            "💡 Tip: Use 'calendarbot --web' without --host to auto-detect your local network interface"
        )

    return host
