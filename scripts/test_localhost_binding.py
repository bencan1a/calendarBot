#!/usr/bin/env python3
"""Test script to validate localhost vs host IP binding and accessibility."""

import socket
import subprocess
import time
import urllib.error
import urllib.request


def get_local_ip():
    """Get the local network IP address."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "192.168.1.45"  # fallback


def test_socket_binding(port=8888):
    """Test how sockets bind to different addresses."""
    print(f"=== Socket Binding Test (Port {port}) ===")

    bind_addresses = ["0.0.0.0", "127.0.0.1", get_local_ip()]

    for addr in bind_addresses:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((addr, port))
            sock.listen(1)

            # Test connections from different addresses
            test_addresses = ["127.0.0.1", "localhost", get_local_ip()]

            print(f"✓ Successfully bound to {addr}:{port}")

            for test_addr in test_addresses:
                try:
                    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_sock.settimeout(2)
                    client_sock.connect((test_addr, port))
                    client_sock.close()
                    print(f"  ✓ Connection successful from {test_addr}")
                except Exception as e:
                    print(f"  ✗ Connection failed from {test_addr}: {e}")

            sock.close()
            port += 1  # Increment port for next test

        except Exception as e:
            print(f"✗ Failed to bind to {addr}:{port}: {e}")

    print()


def test_actual_server_binding():
    """Test the actual calendarbot_lite server binding."""
    print("=== CalendarBot Lite Server Binding Test ===")

    # Start server on a test port
    test_port = 8777

    try:
        # Start the server process
        cmd = f"bash -c 'cd /home/bencan/projects/calendarBot && source venv/bin/activate && CALENDARBOT_SERVER_PORT={test_port} python -m calendarbot_lite'"

        print(f"Starting server on port {test_port}...")
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Give server time to start
        time.sleep(3)

        # Test connectivity from different addresses
        local_ip = get_local_ip()
        test_urls = [
            f"http://localhost:{test_port}/",
            f"http://127.0.0.1:{test_port}/",
            f"http://{local_ip}:{test_port}/",
        ]

        for url in test_urls:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    print(f"✓ {url} - Status: {response.status}")
            except urllib.error.URLError as e:
                print(f"✗ {url} - Error: {e}")
            except Exception as e:
                print(f"✗ {url} - Unexpected error: {e}")

        # Check what the server is actually bound to
        try:
            result = subprocess.run(
                ["netstat", "-tlpn", f"| grep {test_port}"],
                check=False,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout:
                print(f"Server binding: {result.stdout.strip()}")
        except Exception:
            print("Could not check server binding")

        # Terminate the server
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    except Exception as e:
        print(f"Failed to test server: {e}")

    print()


def check_localhost_resolution():
    """Check if localhost resolves correctly."""
    print("=== Localhost Resolution Check ===")

    try:
        localhost_ip = socket.gethostbyname("localhost")
        print(f"localhost resolves to: {localhost_ip}")
    except Exception as e:
        print(f"localhost resolution failed: {e}")

    try:
        result = subprocess.run(
            ["ping", "-c", "1", "localhost"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✓ localhost ping successful")
        else:
            print(f"✗ localhost ping failed: {result.stderr}")
    except Exception as e:
        print(f"ping test failed: {e}")

    print()


if __name__ == "__main__":
    print("CalendarBot Lite Localhost Binding Diagnostics")
    print("=" * 50)

    local_ip = get_local_ip()
    print(f"Local IP detected: {local_ip}")
    print()

    check_localhost_resolution()
    test_socket_binding()
    test_actual_server_binding()
