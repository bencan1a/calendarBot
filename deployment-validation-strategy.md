# Simple Deployment and Validation Strategy

## Overview

Simplified deployment strategy for the next meeting priority logic changes in WhatsnextView. Focus on essential validation and straightforward deployment procedures for a single user stateless application.

## Pre-Deployment Validation

### 1. Code Quality Check

```bash
#!/bin/sh
# Basic pre-deployment validation
set -e

echo "🔍 Running pre-deployment checks..."

# Activate virtual environment
. venv/bin/activate

# Run unit tests
echo "Running unit tests..."
python -m pytest tests/test_whats_next_logic.py -v

# Run integration tests if they exist
if [ -f "tests/test_integration_meeting_selection.py" ]; then
    echo "Running integration tests..."
    python -m pytest tests/test_integration_meeting_selection.py -v
fi

# Check for linting errors
echo "Checking code quality..."
python -m flake8 calendarbot/display/whats_next_logic.py || echo "Warning: linting issues found"

echo "✅ Pre-deployment validation completed"
```

### 2. Smoke Test

```bash
#!/bin/sh
# Simple smoke test
echo "🚀 Starting smoke test..."

# Start application with timeout for safety
timeout 15s calendarbot --web --port 8080 &
APP_PID=$!

# Wait for startup
sleep 3

# Basic connectivity test
if curl -f http://localhost:8080 >/dev/null 2>&1; then
    echo "✅ Application started successfully"
else
    echo "❌ Application failed to start"
    kill $APP_PID 2>/dev/null || true
    exit 1
fi

# Clean up
kill $APP_PID 2>/dev/null || true
echo "✅ Smoke test completed"
```

## Deployment Procedure

### Simple Deployment Steps

1. **Create Backup**:
   ```bash
   # Backup current files
   cp calendarbot/display/whats_next_logic.py calendarbot/display/whats_next_logic.py.backup
   cp calendarbot/web/static/layouts/whats-next-view/whats-next-view.js calendarbot/web/static/layouts/whats-next-view/whats-next-view.js.backup
   ```

2. **Deploy Changes**:
   ```bash
   # Apply the code changes (via git pull or manual file updates)
   git pull origin main
   # OR manually copy new files
   ```

3. **Restart Application**:
   ```bash
   # Kill existing process
   pkill -f "calendarbot --web" || true
   
   # Start new process
   calendarbot --web --port 8080
   ```

## Post-Deployment Validation

### Basic Health Check

```bash
#!/bin/sh
# Simple post-deployment validation
echo "🔍 Validating deployment..."

# Wait for application to start
sleep 5

# Test basic functionality
if curl -f http://localhost:8080 >/dev/null 2>&1; then
    echo "✅ Application is responding"
else
    echo "❌ Application health check failed"
    exit 1
fi

# Optional: Test API endpoint if available
if curl -f http://localhost:8080/api/whats-next/data >/dev/null 2>&1; then
    echo "✅ API endpoint is working"
else
    echo "⚠️ API endpoint check failed or not available"
fi

echo "✅ Basic validation completed"
```

### Manual Testing Checklist

**Visual Verification**:
- [ ] Application loads in browser
- [ ] Meetings are displayed correctly
- [ ] Next meeting is prioritized over current meeting
- [ ] Countdown timer shows correct time
- [ ] Hide/unhide functionality works
- [ ] No JavaScript errors in browser console

**Functional Testing**:
- [ ] Test with no meetings scheduled
- [ ] Test with only current meetings
- [ ] Test with only future meetings
- [ ] Test with both current and future meetings
- [ ] Test hide/unhide of meetings
- [ ] Test auto-refresh (wait 30 seconds)

## Rollback Procedure

### Manual Rollback

If issues are discovered:

```bash
#!/bin/sh
# Simple rollback procedure
echo "🔄 Rolling back changes..."

# Stop application
pkill -f "calendarbot --web" || true

# Restore backup files
if [ -f "calendarbot/display/whats_next_logic.py.backup" ]; then
    cp calendarbot/display/whats_next_logic.py.backup calendarbot/display/whats_next_logic.py
    echo "✅ Backend rolled back"
else
    echo "❌ Backend backup not found!"
fi

if [ -f "calendarbot/web/static/layouts/whats-next-view/whats-next-view.js.backup" ]; then
    cp calendarbot/web/static/layouts/whats-next-view/whats-next-view.js.backup calendarbot/web/static/layouts/whats-next-view/whats-next-view.js
    echo "✅ Frontend rolled back"
else
    echo "❌ Frontend backup not found!"
fi

# Restart with previous version
calendarbot --web --port 8080

echo "✅ Rollback completed"
```

## Success Criteria

**Deployment is successful when**:
- [ ] Application starts without errors
- [ ] Next meetings are displayed when available (not current meetings)
- [ ] Countdown timer shows correct time until next meeting starts
- [ ] All existing functionality (hide/unhide, auto-refresh) works
- [ ] No JavaScript errors in browser console
- [ ] Performance is similar to previous version

**Key Behavioral Changes to Verify**:
1. **Primary Change**: When both current and next meetings exist, next meeting is displayed
2. **Countdown Logic**: Timer shows time until next meeting starts (not current meeting end)
3. **Edge Cases**: Handles consecutive meetings, no meetings, and all-hidden meetings correctly

## Troubleshooting

### Common Issues

**Application Won't Start**:
- Check for syntax errors in Python files
- Verify virtual environment is activated
- Check for missing dependencies

**Meeting Selection Not Working**:
- Verify `_group_events()` method changes in `whats_next_logic.py`
- Check `detectCurrentMeeting()` function in frontend JavaScript
- Ensure both backend and frontend use same priority logic

**Countdown Timer Issues**:
- Check timezone handling in both backend and frontend
- Verify meeting time calculations
- Test with different meeting scenarios

### Log Analysis

Check application logs for errors:
```bash
# Check recent logs
tail -f logs/app.log

# Look for specific errors
grep -i error logs/app.log
grep -i "meeting" logs/app.log
```

## Deployment Timeline

**Phase 1: Pre-Deployment** (30 minutes)
- Run validation scripts
- Create backups
- Review changes one final time

**Phase 2: Deployment** (15 minutes)
- Deploy code changes
- Restart application
- Basic health checks

**Phase 3: Validation** (30 minutes)
- Manual testing checklist
- Browser testing
- Edge case verification

**Phase 4: Monitoring** (24 hours)
- Periodic manual checks
- User feedback collection
- Performance observation

This simple approach ensures safe deployment while avoiding unnecessary complexity for a single user stateless application.