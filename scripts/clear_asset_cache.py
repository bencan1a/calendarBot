#!/usr/bin/env python3
"""
Clear asset cache to force reload of updated JavaScript files.
"""

import sys

import requests


def clear_cache(host="192.168.1.45", port=8080):
    """Clear the web server's asset cache."""
    url = f"http://{host}:{port}/api/cache/clear"

    try:
        print(f"Clearing asset cache at {url}...")
        response = requests.post(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cache cleared successfully: {result.get('message', 'OK')}")
            return True
        print(f"❌ Cache clear failed: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to server: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = "192.168.1.100"

    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 8080

    success = clear_cache(host, port)
    sys.exit(0 if success else 1)
