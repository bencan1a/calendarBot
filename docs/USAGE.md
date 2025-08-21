# Usage Guide

## Basic Operation

### Web Interface

```bash
calendarbot --web
```

Opens web interface at `http://<host-ip>:8080`

**Options:**
```bash
calendarbot --web --port 3000        # Custom port
calendarbot --web --auto-open         # Auto-open browser
```

**Layouts:**
- **4x8**: Standard desktop layout (480x800px)
- **3x4**: Compact layout (300x400px)
- **whats-next-view**: Meeting countdown display

```bash
calendarbot --web --display_type 4x8
calendarbot --web --web_layout whats-next-view
```

### E-Paper Display

```bash
calendarbot --epaper
```

Optimized for e-ink displays with auto-hardware detection.

## Configuration

### Quick Setup

```bash
calendarbot --setup
```

Interactive wizard to configure your ICS calendar feed.

### Manual Configuration

Create `config.yaml`:

```yaml
ics:
  url: "https://calendar.example.com/calendar.ics"
  auth_type: "none"  # none, basic, bearer
  username: "user"   # for basic auth
  password: "pass"   # for basic auth
  token: "token"     # for bearer auth

app_name: "CalendarBot"
refresh_interval: 300  # seconds

web:
  enabled: true
  port: 8080
  theme: "4x8"
```

### Environment Variables

```bash
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="none"
export CALENDARBOT_LOG_LEVEL="INFO"
```

## Calendar Sources

Supports any RFC 5545 compliant calendar:

- **Microsoft Outlook/Office 365**: Published calendar ICS URLs
- **Google Calendar**: Secret iCal format URLs  
- **Apple iCloud Calendar**: Public calendar ICS URLs
- **CalDAV Servers**: Nextcloud, Radicale, SOGo
- **Any ICS feed**: Direct `.ics` file URLs

## Troubleshooting

**Events not displaying:**
- Verify ICS URL is accessible
- Check authentication settings
- Review logs: `calendarbot --verbose`

**Web interface issues:**
- Try different port: `calendarbot --web --port 3000`
- Check firewall settings
- Use host IP instead of localhost

**Performance issues:**
```bash
calendarbot --test-mode  # Validate system components
```

**Logs:**
```bash
export CALENDARBOT_LOG_LEVEL="DEBUG"
calendarbot --verbose
```

## Testing

```bash
calendarbot --test-mode                    # Quick validation
calendarbot --test-mode --components ics   # Test ICS connectivity