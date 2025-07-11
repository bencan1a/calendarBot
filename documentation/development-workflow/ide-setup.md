# IDE Setup Guide

## VSCode Configuration

### Required Extensions

#### Type Checking & Python Support
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "ms-python.isort",
    "ms-python.black-formatter",
    "ms-toolsai.jupyter"
  ]
}
```

#### Code Quality & Formatting
- **Black Formatter**: Automatic code formatting
- **isort**: Import sorting and organization
- **MyPy**: Real-time type checking
- **Python**: Core Python language support

### VSCode Settings

Create or update `.vscode/settings.json`:

```json
{
  // Python Configuration
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.terminal.activateEnvironment": true,
  
  // MyPy Integration
  "mypy-type-checker.importStrategy": "fromEnvironment",
  "mypy-type-checker.preferDaemon": true,
  "mypy-type-checker.reportingScope": "workspace",
  "mypy-type-checker.args": [
    "--config-file=pyproject.toml",
    "--show-error-codes",
    "--no-color-output"
  ],
  
  // Formatting on Save
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  
  // Black Formatter
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.tabSize": 4,
    "editor.insertSpaces": true
  },
  
  // Import Sorting
  "isort.args": [
    "--profile=black",
    "--line-length=100"
  ],
  
  // Error Display
  "python.analysis.typeCheckingMode": "basic",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  
  // File Associations
  "files.associations": {
    "*.py": "python",
    ".pre-commit-config*.yaml": "yaml"
  }
}
```

### Workspace Configuration

Create `.vscode/launch.json` for debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "CalendarBot: Main App",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/calendarbot/main.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

## MyPy Daemon Setup

### Enable Daemon Mode
The MyPy daemon provides near-instantaneous type checking feedback:

```bash
# Start daemon (automatic with VSCode extension)
dmypy start

# Check daemon status
dmypy status

# Restart if needed
dmypy restart
```

### Configuration Benefits
- **Real-time feedback**: Type errors appear instantly as you type
- **Incremental checking**: Only re-checks modified files
- **Performance**: 10-100x faster than traditional mypy runs
- **IDE integration**: Seamless error highlighting and suggestions

## Terminal Configuration

### Pre-commit Integration
Add to your shell profile (`.bashrc`, `.zshrc`):

```bash
# CalendarBot aliases
alias cb-activate=". venv/bin/activate"
alias cb-commit="pre-commit run --all-files"
alias cb-fast="pre-commit run --config .pre-commit-config-fast.yaml"
alias cb-test="pytest tests/ -v"

# Auto-activate when entering project
function auto_activate() {
    if [[ -f "./venv/bin/activate" ]]; then
        source ./venv/bin/activate
    fi
}

# Add to your prompt or use with cd
```

### Git Hooks Integration
```bash
# Install hooks (one-time setup)
pre-commit install

# Install fast profile for emergency development
PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml pre-commit install --install-hooks
```

## Development Workflow

### Daily Development Flow

1. **Start Development Session**
   ```bash
   cd calendarbot
   . venv/bin/activate
   code .  # Opens with all settings applied
   ```

2. **Real-time Feedback**
   - Type errors appear instantly in editor
   - Import organization on save
   - Code formatting on save
   - Immediate syntax validation

3. **Commit Process**
   ```bash
   # Standard commit (full validation)
   git add .
   git commit -m "feature: implement new functionality"
   
   # Fast commit (emergency/intensive development)
   git add .
   PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml git commit -m "wip: rapid iteration"
   ```

### Emergency Development Mode

When you need to commit frequently during intensive development:

```bash
# Switch to fast hooks temporarily
pre-commit uninstall
PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml pre-commit install

# Your intensive development session...

# Switch back to standard hooks
pre-commit uninstall
pre-commit install
```

## Troubleshooting

### MyPy Issues

**Problem**: MyPy daemon not starting
```bash
# Solution: Reset daemon
dmypy kill
dmypy start

# Check Python path
which python
echo $PYTHONPATH
```

**Problem**: Import errors in MyPy
```bash
# Solution: Install stub packages
pip install types-requests types-python-dateutil
# Check pyproject.toml for complete list
```

### Performance Issues

**Problem**: Slow IDE response
```bash
# Solution: Restart MyPy daemon
dmypy restart

# Check daemon status
dmypy status

# Disable real-time checking temporarily
# In VSCode: Command Palette > "MyPy: Disable"
```

### Extension Conflicts

**Problem**: Conflicting formatters
- Check only one Python formatter is enabled
- Verify `editor.defaultFormatter` setting
- Disable conflicting extensions

**Problem**: Import sorting conflicts
- Ensure isort and Black profiles match
- Check `.pre-commit-config.yaml` args consistency
- Verify isort extension settings

## Next Steps

1. Install and configure all recommended extensions
2. Verify MyPy daemon is running properly
3. Test the workflow with a small code change
4. Proceed to [Pre-commit Profiles](./pre-commit-profiles.md) for validation setup