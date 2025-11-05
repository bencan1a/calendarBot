# GitHub Copilot Agent Setup Instructions

This document provides instructions for configuring GitHub repository secrets required by the Copilot coding agent environment.

## Overview

The `.github/workflows/copilot-setup-steps.yml` workflow automatically configures the development environment when GitHub Copilot starts a coding session. To enable full functionality, you need to configure GitHub Actions secrets for environment variables.

## Required GitHub Actions Secrets

### How to Add Secrets

1. Navigate to your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

### Secret Configuration

#### 1. `CALENDARBOT_ICS_URL` ⚠️ **REQUIRED**

**Purpose**: ICS calendar feed URL for calendar operations

**Value**: Your calendar's ICS feed URL

**Examples**:
```
# Office 365/Outlook
https://outlook.office365.com/owa/calendar/your-calendar-id/calendar.ics

# Google Calendar (requires public sharing)
https://calendar.google.com/calendar/ical/your-email%40gmail.com/public/basic.ics

# iCloud
https://p01-caldav.icloud.com/published/2/your-calendar-url
```

**How to get your ICS URL**:
- **Office 365**: Calendar settings → Shared calendars → Publish calendar → ICS link
- **Google Calendar**: Calendar settings → Integrate calendar → Secret address in iCal format
- **iCloud**: Calendar app → Share calendar → Public Calendar → Copy link

**Why required**: The calendar parsing functionality cannot work without a valid ICS feed. Most tests and features require this to be set.

---

#### 2. `CALENDARBOT_ALEXA_BEARER_TOKEN` (Optional)

**Purpose**: Authentication token for Alexa skill integration testing

**Value**: Your Alexa skill bearer token (obtain from Amazon Developer Console)

**When needed**: 
- Only required if testing Alexa skill integration
- Not needed for basic calendar operations
- Can be omitted if you don't use Alexa features

**Default behavior if not set**: Alexa endpoints will return authentication errors, but core calendar functionality will work normally.

---

## Workflow Features

The Copilot setup workflow provides:

### 1. ✅ Dependency Caching
- Reuses the same caching strategy as `ci.yml`
- Cache key: `venv-{os}-py{version}-{hash(requirements.txt, pyproject.toml)}`
- Avoids reinstalling dependencies on every session
- Significantly faster setup times after first run

### 2. ✅ Pre-commit Installation
- Automatically installs pre-commit hooks from `.pre-commit-config.yaml`
- Configures hooks for:
  - Code formatting (ruff)
  - Type checking (mypy)
  - Security scanning (bandit)
  - YAML/JSON validation
  - Critical path tests

### 3. ✅ Development Tools
Installs and configures:
- `pytest` - Testing framework
- `ruff` - Fast Python linter and formatter
- `mypy` - Static type checker
- `bandit` - Security vulnerability scanner
- `pre-commit` - Git hook manager
- Additional dev dependencies from `pyproject.toml`

### 4. ✅ Environment Variables
Creates `.env` file with:
- Secrets from GitHub Actions
- Safe defaults for development
- Non-interactive mode for CI
- Debug logging enabled

## Verifying Setup

After configuring secrets, the workflow will:

1. ✅ Cache and restore virtual environment
2. ✅ Install dependencies only if cache miss
3. ✅ Configure pre-commit hooks
4. ✅ Create `.env` with your secrets
5. ✅ Verify imports and tools
6. ✅ Display environment summary

## Troubleshooting

### Issue: "CALENDARBOT_ICS_URL not set"

**Symptom**: Tests fail with calendar fetch errors

**Solution**: 
1. Go to repository Settings → Secrets and variables → Actions
2. Add `CALENDARBOT_ICS_URL` secret with your ICS feed URL
3. Restart the Copilot session or re-run the workflow

### Issue: "Pre-commit hooks not running"

**Symptom**: Code formatting checks don't run automatically

**Solution**:
```bash
# Manually install hooks
pre-commit install --install-hooks

# Verify installation
pre-commit --version
pre-commit run --all-files --hook-stage manual trailing-whitespace
```

### Issue: "Dependencies not cached"

**Symptom**: Slow setup on every session

**Solution**: The cache key includes hashes of `requirements.txt` and `pyproject.toml`. If you modify these files, the cache is invalidated (expected behavior). After the first run with new dependencies, subsequent runs will be fast.

### Issue: "Module import errors"

**Symptom**: `ImportError: No module named 'calendarbot_lite'`

**Solution**:
```bash
# Ensure you're in the virtual environment
source venv/bin/activate

# Reinstall in editable mode
pip install -e .[dev]
```

## Environment Variable Reference

### Core Variables (Set by Workflow)

| Variable | Source | Purpose |
|----------|--------|---------|
| `CALENDARBOT_ICS_URL` | Secret | Calendar feed URL |
| `CALENDARBOT_WEB_HOST` | Default | Server bind address (0.0.0.0) |
| `CALENDARBOT_WEB_PORT` | Default | Server port (8080) |
| `CALENDARBOT_REFRESH_INTERVAL` | Default | Refresh seconds (300) |
| `CALENDARBOT_DEBUG` | Default | Enable debug logging (true) |
| `CALENDARBOT_LOG_LEVEL` | Default | Log level (DEBUG) |
| `CALENDARBOT_NONINTERACTIVE` | Default | Disable prompts (true) |
| `CALENDARBOT_TEST_TIME` | Default | Fixed time for testing |
| `CALENDARBOT_ALEXA_BEARER_TOKEN` | Secret | Alexa auth token (optional) |

### Additional Variables (Add as needed)

You can add more secrets following the same pattern:

1. Add secret in GitHub: Settings → Secrets and variables → Actions
2. Update `.github/workflows/copilot-setup-steps.yml`:
   ```yaml
   CALENDARBOT_YOUR_VAR=${{ secrets.CALENDARBOT_YOUR_VAR || 'default' }}
   ```

## Testing the Setup

After configuration, test the environment:

```bash
# Verify Python and dependencies
python --version
pip list | grep -E "(pytest|ruff|mypy)"

# Check environment variables
cat .env

# Run quick tests
pytest tests/lite/ -m smoke -v

# Verify pre-commit
pre-commit run --all-files --hook-stage manual trailing-whitespace

# Start the server
python -m calendarbot_lite
```

## Additional Resources

- **GitHub Actions Secrets Documentation**: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **Copilot Agent Customization**: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment
- **CalendarBot Configuration**: See `.env.example` in repository root
- **Development Guide**: See `AGENTS.md` for agent-specific guidance

## Security Notes

⚠️ **Important Security Considerations**:

1. **Never commit `.env` files** - They contain sensitive data
2. **Use GitHub Secrets** - Secrets are encrypted and not exposed in logs
3. **Rotate tokens regularly** - Especially if they may have been compromised
4. **Limit secret scope** - Only add secrets that are actually needed
5. **Review workflow logs** - Ensure secrets aren't accidentally logged

The workflow uses `secrets.*` syntax which ensures values are masked in logs and not exposed in pull requests from forks.

## Support

If you encounter issues:

1. Check GitHub Actions logs for the workflow run
2. Review this document for troubleshooting steps
3. Consult `AGENTS.md` for development patterns
4. Check `.env.example` for all available configuration options
