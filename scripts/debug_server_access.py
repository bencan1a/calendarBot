#!/usr/bin/env python3
"""Debug script to diagnose calendarbot_lite server localhost access issues."""

import os
import socket
import subprocess
import sys


def check_environment_variables():
    """Check environment variables that might affect server binding."""
    print("=== Environment Variables ===")
    relevant_vars = [
        "CALENDARBOT_WEB_HOST",
        "CALENDARBOT_SERVER_BIND",
        "CALENDARBOT_WEB_PORT",
        "CALENDARBOT_SERVER_PORT",
        "CALENDARBOT_ICS_URL",
        "CALENDARBOT_DEBUG",
    ]

    for var in relevant_vars:
        value = os.environ.get(var)
        if value:
            print(f"{var}={value}")
        else:
            print(f"{var}=<not set>")
    print()


def check_port_availability(port):
    """Check if a port is available for binding."""
    print(f"=== Port {port} Availability ===")
    for host in ["localhost", "127.0.0.1", "0.0.0.0"]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((host, port))
            sock.close()
            print(f"✓ Port {port} available on {host}")
        except OSError as e:
            print(f"✗ Port {port} on {host}: {e}")
    print()


def check_active_servers():
    """Check what servers are currently running."""
    print("=== Active Servers ===")
    try:
        result = subprocess.run(
            ["netstat", "-tlpn"], check=False, capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.split("\n")
        for line in lines:
            if (
                ":80" in line
                or ":81" in line
                or ":82" in line
                or ":83" in line
                or ":84" in line
                or ":85" in line
            ):
                print(line.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("Could not check active servers (netstat not available)")
    print()


def check_firewall_rules():
    """Check basic firewall rules that might block localhost."""
    print("=== Firewall Check ===")
    try:
        # Check iptables
        result = subprocess.run(
            ["iptables", "-L", "INPUT", "-n"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "DROP" in result.stdout or "REJECT" in result.stdout:
            print("⚠ Found DROP/REJECT rules in iptables:")
            for line in result.stdout.split("\n"):
                if "DROP" in line or "REJECT" in line:
                    print(f"  {line.strip()}")
        else:
            print("✓ No obvious blocking rules in iptables")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("Could not check iptables (may need sudo or iptables not installed)")
    print()


def test_http_connectivity(port):
    """Test HTTP connectivity to localhost."""
    print(f"=== HTTP Connectivity Test (Port {port}) ===")
    import urllib.error
    import urllib.request

    for host in ["localhost", "127.0.0.1"]:
        url = f"http://{host}:{port}/"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                print(f"✓ HTTP {host}:{port} - Status: {response.status}")
        except urllib.error.URLError as e:
            print(f"✗ HTTP {host}:{port} - Error: {e}")
        except Exception as e:
            print(f"✗ HTTP {host}:{port} - Unexpected error: {e}")
    print()


if __name__ == "__main__":
    print("CalendarBot Lite Server Access Diagnostics")
    print("=" * 50)

    check_environment_variables()
    check_port_availability(8080)
    check_port_availability(8081)
    check_active_servers()
    check_firewall_rules()

    # Test connectivity if a port argument is provided
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            test_http_connectivity(port)
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
