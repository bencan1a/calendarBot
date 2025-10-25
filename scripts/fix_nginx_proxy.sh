#!/bin/bash
# Fix nginx to proxy to CalendarBot Lite instead of redirecting to HTTPS
# This addresses the real issue: nginx intercepting requests

set -e

echo "🔧 CalendarBot Lite nginx Proxy Fix"
echo "==================================="

if [[ $EUID -ne 0 ]]; then
   echo "❌ This script needs sudo access for nginx configuration"
   echo "   Run: sudo ./scripts/fix_nginx_proxy.sh"
   exit 1
fi

echo "🔍 Checking nginx configuration..."

# Find nginx config files
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"

echo "📁 Backing up current nginx configuration..."
cp -r /etc/nginx /etc/nginx.backup.$(date +%Y%m%d_%H%M%S)

# Create CalendarBot Lite nginx site configuration
echo "📝 Creating CalendarBot Lite nginx configuration..."
cat > $NGINX_SITES_AVAILABLE/calendarbot-lite << 'EOF'
# CalendarBot Lite nginx proxy configuration
server {
    listen 80;
    server_name ashwoodgrove.net;

    # Proxy all requests to CalendarBot Lite
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CRITICAL: Forward Authorization header
        proxy_pass_request_headers on;
        proxy_set_header Authorization $http_authorization;
    }

    # Enable logging for debugging
    access_log /var/log/nginx/calendarbot-access.log;
    error_log /var/log/nginx/calendarbot-error.log;
}
EOF

echo "🔗 Enabling CalendarBot Lite site..."
# Remove any existing default sites that might interfere
rm -f $NGINX_SITES_ENABLED/default
rm -f $NGINX_SITES_ENABLED/ashwoodgrove.net

# Enable the CalendarBot Lite site
ln -sf $NGINX_SITES_AVAILABLE/calendarbot-lite $NGINX_SITES_ENABLED/

echo "✅ Testing nginx configuration..."
if nginx -t; then
    echo "✅ nginx configuration test passed"
else
    echo "❌ nginx configuration test failed - restoring backup"
    rm -rf /etc/nginx
    mv /etc/nginx.backup.* /etc/nginx
    exit 1
fi

echo "🔄 Reloading nginx..."
systemctl reload nginx

echo "📊 Checking nginx status..."
if systemctl is-active --quiet nginx; then
    echo "✅ nginx is running"
else
    echo "❌ nginx failed to start"
    exit 1
fi

echo ""
echo "🎯 nginx proxy configuration complete!"
echo ""
echo "🧪 Testing the HTTP endpoint..."
echo "   URL: http://ashwoodgrove.net/api/alexa/next-meeting"
echo ""

# Test the endpoint
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

echo ""
echo "📋 Summary:"
echo "   ✅ nginx now proxies HTTP requests to CalendarBot Lite"
echo "   ✅ Authorization header forwarding enabled"
echo "   📁 Backup saved at: /etc/nginx.backup.*"
echo ""
echo "🔧 To restore original config:"
echo "   sudo rm -rf /etc/nginx && sudo mv /etc/nginx.backup.* /etc/nginx && sudo systemctl reload nginx"