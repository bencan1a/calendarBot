# User Troubleshooting Guide

## Common Issues

### Display Blank
- **Console**: Verify display is enabled in `SETUP.md` configuration
- **Web Interface**: Check server at `http://<host-ip>:8080` is reachable

### Calendar Not Displaying
- Confirm ICS URL is correctly configured (follow test instructions from USAGE.md)
- Validate calendar credentials haven't expired (perform OAuth refresh token check)

### High Latency in Web Mode
- Ensure port configuration in `SETUP.md` matches router settings
- Check network connectivity and firewall settings

## Advanced Debugging

### Diagnostic Logging
```sh
export CALENDARBOT_LOG_LEVEL="DEBUG"
. venv/bin/activate
calendarbot --verbose
```

### Component-specific Tests
#### Rendering Verification
- Interactive Mode: Run `calendarbot --interactive`
- E-Paper Mode Test: `calendarbot --epaper`
- Web Mode Test: `calendarbot --web --port 8080`

### Testing ICS Connectivity
```sh
# Test ICS connectivity with verbose logging
calendarbot --test-mode --components ics --verbose
```

### Cache Management
```sh
# Clear cache and fetch fresh data
rm -rf ~/.cache/calendarbot/*
calendarbot --web
