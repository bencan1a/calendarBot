#!/usr/bin/env python3
"""
Debug script for reverse proxy connectivity issues.
Validates CalendarBot Lite service status and network connectivity.
"""

import asyncio
import socket
import subprocess

import aiohttp


async def check_calendarbot_lite_direct() -> bool:
    """Test direct connection to CalendarBot Lite."""
    print("🔍 Testing direct CalendarBot Lite connection...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8080/api/alexa/next-meeting",
                headers={"Authorization": "Bearer Uc39FIpUYa2BDIMjOUDyhzQk53qhQjHFxTpw-9P7wkA"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                print(f"✅ Direct connection: {response.status}")
                text = await response.text()
                print(f"   Response: {text[:100]}...")
                return response.status == 200
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        return False


def check_port_binding() -> bool:
    """Check if port 8080 is bound and listening."""
    print("🔍 Checking port 8080 binding...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", 8080))
        sock.close()
        if result == 0:
            print("✅ Port 8080 is listening")
            return True
        print("❌ Port 8080 is not accessible")
        return False
    except Exception as e:
        print(f"❌ Port check failed: {e}")
        return False


def check_processes() -> list:
    """Check for running CalendarBot processes."""
    print("🔍 Checking for CalendarBot processes...")
    try:
        result = subprocess.run(
            ["pgrep", "-f", "calendarbot"], check=False, capture_output=True, text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            print(f"✅ Found CalendarBot processes: {pids}")
            return pids
        print("❌ No CalendarBot processes found")
        return []
    except Exception as e:
        print(f"❌ Process check failed: {e}")
        return []


def check_caddy_status() -> bool:
    """Check if Caddy is running and configuration is valid."""
    print("🔍 Checking Caddy status...")
    try:
        # Check if Caddy is running
        result = subprocess.run(
            ["systemctl", "is-active", "caddy"], check=False, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Caddy service is active")
        else:
            print(f"❌ Caddy service status: {result.stdout.strip()}")
            return False

        # Check Caddy configuration
        result = subprocess.run(
            ["caddy", "validate", "--config", "/etc/caddy/Caddyfile"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ Caddy configuration is valid")
            return True
        print(f"❌ Caddy configuration error: {result.stderr}")
        return False
    except Exception as e:
        print(f"❌ Caddy check failed: {e}")
        return False


async def check_external_https() -> bool:
    """Test external HTTPS connection through Caddy."""
    print("🔍 Testing external HTTPS connection...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://ashwoodgrove.net/api/alexa/next-meeting",
                headers={"Authorization": "Bearer Uc39FIpUYa2BDIMjOUDyhzQk53qhQjHFxTpw-9P7wkA"},
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False,
            ) as response:
                print(f"✅ HTTPS connection: {response.status}")
                text = await response.text()
                print(f"   Response: {text[:100]}...")
                return response.status == 200
    except Exception as e:
        print(f"❌ HTTPS connection failed: {e}")
        return False


def check_firewall_rules():
    """Check basic firewall status."""
    print("🔍 Checking firewall status...")
    try:
        # Check ufw status
        result = subprocess.run(["ufw", "status"], check=False, capture_output=True, text=True)
        print(f"UFW Status: {result.stdout}")

        # Check iptables for any blocking rules
        result = subprocess.run(
            ["iptables", "-L", "-n"], check=False, capture_output=True, text=True
        )
        if "DROP" in result.stdout or "REJECT" in result.stdout:
            print("⚠️  Found potential blocking iptables rules")
        else:
            print("✅ No obvious blocking iptables rules")
    except Exception as e:
        print(f"❌ Firewall check failed: {e}")


async def run_diagnostics():
    """Run all diagnostic checks."""
    print("=" * 60)
    print("🔧 CalendarBot Lite Reverse Proxy Diagnostics")
    print("=" * 60)

    # Check processes first
    processes = check_processes()
    port_ok = check_port_binding()

    # If no processes or port not listening, CalendarBot Lite isn't running
    if not processes or not port_ok:
        print("\n❌ DIAGNOSIS: CalendarBot Lite is not running!")
        print("   Start it with: python -m calendarbot_lite --port 8080")
        return

    # Test direct connection
    direct_ok = await check_calendarbot_lite_direct()
    if not direct_ok:
        print("\n❌ DIAGNOSIS: CalendarBot Lite is running but not responding correctly!")
        print("   Check server logs and bearer token configuration")
        return

    # Check Caddy
    caddy_ok = check_caddy_status()
    if not caddy_ok:
        print("\n❌ DIAGNOSIS: Caddy configuration or service issue!")
        return

    # Test external connection
    https_ok = await check_external_https()
    if not https_ok:
        print("\n❌ DIAGNOSIS: External HTTPS connection failing!")
        print("   This could be:")
        print("   1. Router firewall blocking external access")
        print("   2. DNS not pointing to correct IP")
        print("   3. SSL certificate issues")
        check_firewall_rules()
    else:
        print("\n✅ ALL CHECKS PASSED - Reverse proxy is working!")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
