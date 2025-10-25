#!/bin/bash
# HTTP-Only Test Script for CalendarBot Lite
# This bypasses SSL issues to test if header forwarding works

set -e

echo "🔧 CalendarBot Lite HTTP-Only Test"
echo "=================================="

# Check if running as root for systemctl commands
if [[ $EUID -ne 0 && "$1" != "--check-only" ]]; then
   echo "❌ This script needs sudo access for Caddy configuration"
   echo "   Run: sudo ./scripts/test_http_only.sh"
   echo "   Or:  ./scripts/test_http_only.sh --check-only  (to just test without changing config)"
   exit 1
fi

# Function to test the HTTP endpoint
test_http_endpoint() {
    echo "🧪 Testing HTTP endpoint..."
    echo "   URL: http://ashwoodgrove.net/api/alexa/next-meeting"
    echo "   Bearer Token: Uc39FIpUYa2BDIMjOUDyhzQk53qhQjHFxTpw-9P7wkA"
    echo ""
    
    # Test the HTTP endpoint
    echo "📡 Making HTTP request..."
    if curl -v -H "Authorization: Bearer Uc39FIpUYa2BDIMjOUDyhzQk53qhQjHFxTpw-9P7wkA" \
            http://ashwoodgrove.net/api/alexa/next-meeting \
            --connect-timeout 10 \
            --max-time 30; then
        echo ""
        echo "✅ HTTP test completed - check response above"
    else
        echo ""
        echo "❌ HTTP test failed"
    fi
}

# If only checking, just run the test
if [[ "$1" == "--check-only" ]]; then
    test_http_endpoint
    exit 0
fi

echo "📁 Backing up current Caddyfile..."
cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup.$(date +%Y%m%d_%H%M%S)

echo "🔄 Installing HTTP-only Caddyfile..."
cp /home/bencan/projects/calendarBot/scripts/http_only_caddyfile /etc/caddy/Caddyfile

echo "✅ Validating new Caddyfile..."
if caddy validate --config /etc/caddy/Caddyfile; then
    echo "✅ Caddyfile validation passed"
else
    echo "❌ Caddyfile validation failed - restoring backup"
    cp /etc/caddy/Caddyfile.backup.* /etc/caddy/Caddyfile
    exit 1
fi

echo "🔄 Restarting Caddy service..."
systemctl restart caddy

echo "⏳ Waiting for Caddy to start..."
sleep 3

echo "📊 Checking Caddy status..."
if systemctl is-active --quiet caddy; then
    echo "✅ Caddy is running"
else
    echo "❌ Caddy failed to start - check logs:"
    echo "   sudo journalctl -u caddy --lines=10 --no-pager"
    exit 1
fi

echo ""
echo "🎯 HTTP-only configuration applied successfully!"
echo "   Now testing the endpoint..."
echo ""

# Test the endpoint
test_http_endpoint

echo ""
echo "📋 Next Steps:"
echo "   1. If HTTP test works ✅ → Header forwarding is fixed, SSL was the issue"
echo "   2. If HTTP test fails ❌ → There's still a header forwarding problem"
echo "   3. For production: Need to fix SSL certificates (ports 80/443 firewall)"
echo ""
echo "📁 Backup saved at: /etc/caddy/Caddyfile.backup.*"
echo "🔧 Restore with: sudo cp /etc/caddy/Caddyfile.backup.* /etc/caddy/Caddyfile && sudo systemctl restart caddy"