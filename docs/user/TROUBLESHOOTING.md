# User Troubleshooting Guide

## Common Issues

### Display Blank
- **Console**: Verify display is enabled in `SETUP.md` configuration
- **Web Interface**: Check server at `http://localhost:8080` is reachable

### Calendar Not Displaying
- Confirm ICS URL is correctly configured (follow test instructions from USAGE.md)
- Validate calendar credentials haven't expired (perform OAuth refresh token check)

### High Latency in Web Mode
- Ensure port configuration in `SETUP.md` matches router settings
- Perform penetration testing (SECURITY.md) to rule out SSL/TLS bottlenecks

## Advanced Debugging

### Diagnostic Logging
```sh
export CALENDARBOT_LOG_MODE="VERBOSE"
. venv/bin/activate
python main.py --verbose
```

### Component-specific Tests
#### Rendering Verification
- Interactive Mode: Run `python main.py --display-only 4x8`
- 3x4 Compact Test: `python main.py --display-type 3x4 --layout compact`

### Known Issue: FastAPI 0.62 Compatibility
- Temporary fix: Downgrade to FastAPI 0.60 until new release
```sh
pip uninstall fastapi -y && pip install fastapi==0.60
```
