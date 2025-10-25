#!/usr/bin/env python3
"""
Debug and fix SSL certificate issues with Caddy for CalendarBot Lite.
This addresses the real problem found in Caddy logs.
"""

import subprocess


def create_http_only_caddyfile():
    """Create a temporary HTTP-only Caddyfile for testing."""
    caddyfile_content = """
# Temporary HTTP-only configuration for testing
# This bypasses SSL certificate issues

ashwoodgrove.net {
    # Disable automatic HTTPS
    auto_https off
    
    # Serve HTTP only (port 80)
    
    reverse_proxy localhost:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto http
        header_up Authorization {header.Authorization}
    }
    
    log {
        output file /var/log/caddy/access.log
        level DEBUG
    }
}

# Alternative: Use IP address instead of domain name
# This completely bypasses DNS/SSL issues
# 50.35.60.201 {
#     reverse_proxy localhost:8080 {
#         header_up Authorization {header.Authorization}
#     }
# }
"""

    with open("scripts/http_only_caddyfile", "w") as f:
        f.write(caddyfile_content)

    print("✅ Created HTTP-only Caddyfile at scripts/http_only_caddyfile")


def create_local_cert_caddyfile():
    """Create Caddyfile with local self-signed certificate."""
    caddyfile_content = """
# Local self-signed certificate configuration
# Use this if you want HTTPS with self-signed cert

ashwoodgrove.net {
    # Use local CA for self-signed certificates
    tls internal
    
    reverse_proxy localhost:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto https
        header_up Authorization {header.Authorization}
    }
    
    log {
        output file /var/log/caddy/access.log
        level DEBUG
    }
}
"""

    with open("scripts/local_cert_caddyfile", "w") as f:
        f.write(caddyfile_content)

    print("✅ Created local certificate Caddyfile at scripts/local_cert_caddyfile")


def diagnose_network_connectivity():
    """Diagnose external network connectivity for Let's Encrypt."""
    print("🔍 Diagnosing network connectivity...")

    # Check if port 80 and 443 are open externally
    print("\n📡 Testing external port accessibility:")
    print("   Port 80 (HTTP): Required for Let's Encrypt HTTP-01 challenge")
    print("   Port 443 (HTTPS): Required for TLS-ALPN-01 challenge")
    print("   These must be open in your router/firewall for auto-SSL")

    # Check DNS resolution
    try:
        result = subprocess.run(
            ["nslookup", "ashwoodgrove.net"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        print("\n🔍 DNS Resolution:")
        print(result.stdout)
    except Exception as e:
        print(f"❌ DNS check failed: {e}")


def recommend_fix_strategy():
    """Recommend the best fix strategy based on the SSL issue."""
    print("\n" + "=" * 60)
    print("🔧 SSL CERTIFICATE FIX STRATEGIES")
    print("=" * 60)

    print("\n🎯 IMMEDIATE FIX (Recommended):")
    print("   Use HTTP-only configuration to test header forwarding:")
    print("   1. sudo cp scripts/http_only_caddyfile /etc/caddy/Caddyfile")
    print("   2. sudo systemctl restart caddy")
    print(
        "   3. Test: curl -H 'Authorization: Bearer ...' http://ashwoodgrove.net/api/alexa/next-meeting"
    )

    print("\n🔒 HTTPS WITH SELF-SIGNED (Alternative):")
    print("   Use local self-signed certificate:")
    print("   1. sudo cp scripts/local_cert_caddyfile /etc/caddy/Caddyfile")
    print("   2. sudo systemctl restart caddy")
    print(
        "   3. Test: curl -k -H 'Authorization: Bearer ...' https://ashwoodgrove.net/api/alexa/next-meeting"
    )

    print("\n🌐 FULL SSL FIX (Long-term):")
    print("   Fix Let's Encrypt certificate acquisition:")
    print("   1. Open ports 80 and 443 in router firewall")
    print("   2. Ensure ashwoodgrove.net points to your public IP")
    print("   3. Use the original Caddyfile with auto-HTTPS")

    print("\n⚠️  ALEXA REQUIREMENT:")
    print("   Amazon Alexa requires HTTPS endpoints in production.")
    print("   Use HTTP-only for testing, then implement full SSL fix.")


if __name__ == "__main__":
    print("🔧 CalendarBot Lite SSL Certificate Fix Tool")
    print("=" * 50)

    # Create configuration files
    create_http_only_caddyfile()
    create_local_cert_caddyfile()

    # Diagnose connectivity
    diagnose_network_connectivity()

    # Provide recommendations
    recommend_fix_strategy()
