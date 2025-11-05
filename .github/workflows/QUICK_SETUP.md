# Quick Setup Guide for GitHub Copilot Agent

## TL;DR

Configure these 2 items to enable full Copilot agent functionality:

### 1. Add Required Secret

Go to: **Repository Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value | Required? |
|-------------|-------|-----------|
| `CALENDARBOT_ICS_URL` | Your ICS calendar feed URL | ✅ Yes |
| `CALENDARBOT_ALEXA_BEARER_TOKEN` | Your Alexa bearer token | ⏭️ Optional |

### 2. Workflow Auto-Runs

The workflow `.github/workflows/copilot-setup-steps.yml` automatically runs when GitHub Copilot starts a coding session. No manual trigger needed!

## Getting Your ICS URL

### Office 365/Outlook
1. Go to Calendar settings
2. Click "Shared calendars"
3. Click "Publish a calendar"
4. Copy the ICS link

### Google Calendar
1. Go to Calendar settings
2. Find "Integrate calendar" section
3. Copy "Secret address in iCal format"

### iCloud
1. Open Calendar app
2. Right-click calendar → Share calendar
3. Enable "Public Calendar"
4. Copy the link

## What Gets Configured

When Copilot agent starts, the workflow automatically:

- ✅ Sets up Python 3.12
- ✅ Creates virtual environment with cached dependencies
- ✅ Installs all dev tools (pytest, ruff, mypy, bandit, pre-commit)
- ✅ Configures pre-commit hooks from `.pre-commit-config.yaml`
- ✅ Creates `.env` file with your secrets and safe defaults
- ✅ Verifies everything works

## Verification

After adding secrets, check the workflow ran successfully:

1. Go to **Actions** tab in your repository
2. Look for "Copilot Environment Setup" workflow runs
3. ✅ Green checkmark = ready to code!
4. ❌ Red X = check logs and troubleshoot

## Common Issues

**Problem**: Tests fail with "ICS URL not configured"
**Solution**: Add `CALENDARBOT_ICS_URL` secret (see above)

**Problem**: Pre-commit hooks don't run
**Solution**: Run manually: `pre-commit install --install-hooks`

**Problem**: Dependencies not cached / slow setup
**Solution**: Cache builds after first run with new dependencies

## Need More Details?

See the full documentation: `.github/workflows/COPILOT_SETUP_INSTRUCTIONS.md`

## Test Your Setup

```bash
# Activate environment
source venv/bin/activate

# Run quick tests
pytest tests/lite/ -m smoke -v

# Start server
python -m calendarbot_lite
```

---

**That's it!** Add the `CALENDARBOT_ICS_URL` secret and you're ready to code with GitHub Copilot. 🚀
