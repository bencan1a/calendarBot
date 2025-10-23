"""Network utilities for CalendarBot."""

import logging
import socket


def get_local_network_interface() -> str:
    """
    Auto-detect the local network interface for safer binding.

    Returns 0.0.0.0 to bind to all interfaces, making the server accessible via both
    localhost (127.0.0.1) and the external network IP address.

    Returns:
        str: "0.0.0.0" to bind to all available interfaces
    """
    logger = logging.getLogger("calendarbot.network")

    # Bind to all interfaces to support both localhost and external access
    logger.debug("Binding to all interfaces (0.0.0.0) for localhost and network access")

    # Also try to detect and log the actual network IP for user information
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use Google's public DNS (doesn't actually connect)
            s.connect(("8.8.8.8", 80))
            local_ip: str = s.getsockname()[0]

            if _is_private_ip(local_ip) and local_ip != "127.0.0.1":
                logger.debug(
                    f"Server will be accessible at: http://localhost and http://{local_ip}"
                )
    except Exception:
        # If we can't detect the IP, that's okay - the binding will still work
        pass

    return "0.0.0.0"  # nosec


def _is_private_ip(ip: str) -> bool:
    """Check if IP address is in private ranges."""
    try:
        octets = [int(x) for x in ip.split(".")]

        # Must have exactly 4 octets for a valid IPv4 address
        if len(octets) != 4:
            return False

        # Validate that all octets are in valid range (0-255)
        for octet in octets:
            if not (0 <= octet <= 255):
                return False

        # Private IP ranges:
        # 10.0.0.0/8 (10.0.0.0 - 10.255.255.255)
        # 172.16.0.0/12 (172.16.0.0 - 172.31.255.255)
        # 192.168.0.0/16 (192.168.0.0 - 192.168.255.255)

        if octets[0] == 10 or (octets[0] == 172 and 16 <= octets[1] <= 31):
            return True
        if octets[0] == 192 and octets[1] == 168:
            return True
        return octets[0] == 127  # Localhost range (127.0.0.0/8)

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
        logger.debug(
            "Server binding to all interfaces (0.0.0.0) for dual access. "
            "The server will be accessible via both localhost and your network IP address."
        )

        # Try to show the actual network IP for user convenience
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip: str = s.getsockname()[0]
                if _is_private_ip(local_ip) and local_ip != "127.0.0.1":
                    logger.debug(f"💡 Access URLs: http://localhost and http://{local_ip}")
        except Exception:
            pass

    return host
