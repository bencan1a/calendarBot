# Troubleshooting Guide

## Common Issues and Solutions

### Pre-commit Hook Issues

#### Issue: Pre-commit hooks taking too long

**Symptoms:**
- Commits taking 5+ minutes
- Development workflow feeling sluggish
- Frequent timeouts during validation

**Solutions:**

1. **Switch to Fast Profile Temporarily**
   ```bash
   # Quick solution for immediate productivity
   pre-commit run --config .pre-commit-config-fast.yaml
   
   # For extended intensive development
   pre-commit uninstall
   PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml pre-commit install
   ```

2. **Use Smart Validation (Default)**
   ```bash
   # Only validates changed files (should be default)
   git add specific_files.py
   git commit -m "message"  # Fast validation on changed files only
   
   # Force full validation when needed
   pre-commit run --all-files
   ```

3. **Optimize Hook Performance**
   ```bash
   # Update to latest hook versions
   pre-commit autoupdate
   
   # Clear cache if corrupted
   pre-commit clean
   pre-commit install --install-hooks
   ```

#### Issue: Pre-commit hooks failing on valid code

**Symptoms:**
- MyPy errors on correct code
- Import sorting conflicts
- Black formatting inconsistencies

**Solutions:**

1. **MyPy Configuration Issues**
   ```bash
   # Check MyPy configuration
   mypy --show-config
   
   # Restart MyPy daemon
   dmypy kill
   dmypy start
   
   # Install missing stub packages
   pip install types-requests types-python-dateutil
   # Check pyproject.toml for complete list
   ```

2. **Import Sorting Conflicts**
   ```bash
   # Fix import conflicts between isort and Black
   isort --profile=black --check-only calendarbot/
   
   # Apply fixes
   isort --profile=black calendarbot/
   ```

3. **Reset Hook Configuration**
   ```bash
   # Complete reset of pre-commit setup
   pre-commit uninstall
   pre-commit clean
   pre-commit install --install-hooks
   pre-commit run --all-files
   ```

### MyPy Daemon Issues

#### Issue: MyPy daemon not starting or crashing

**Symptoms:**
- No real-time type checking in IDE
- `dmypy status` shows "No daemon running"
- Frequent daemon crashes

**Solutions:**

1. **Basic Daemon Troubleshooting**
   ```bash
   # Check daemon status
   dmypy status
   
   # Kill and restart daemon
   dmypy kill
   dmypy start
   
   # Check Python environment
   which python
   echo $PYTHONPATH
   ```

2. **Configuration Issues**
   ```bash
   # Verify MyPy configuration
   mypy --show-config
   
   # Test MyPy without daemon
   mypy calendarbot/ --config-file=pyproject.toml
   
   # Check for configuration conflicts
   grep -r mypy .vscode/ pyproject.toml
   ```

3. **VSCode Integration Problems**
   ```json
   // In .vscode/settings.json - Reset MyPy settings
   {
     "mypy-type-checker.preferDaemon": false,
     "mypy-type-checker.reportingScope": "file"
   }
   
   // Then re-enable daemon after verification
   {
     "mypy-type-checker.preferDaemon": true,
     "mypy-type-checker.reportingScope": "workspace"
   }
   ```

### IDE Configuration Issues

#### Issue: VSCode not applying formatting on save

**Symptoms:**
- Code not formatted automatically
- Import sorting not working
- Inconsistent code style

**Solutions:**

1. **Check Extension Status**
   ```bash
   # In VSCode Command Palette (Ctrl+Shift+P)
   # > Python: Select Interpreter
   # Ensure ./venv/bin/python is selected
   
   # Check if extensions are enabled
   # Extensions: Black Formatter, isort, Python
   ```

2. **Verify Settings Configuration**
   ```json
   // .vscode/settings.json
   {
     "editor.formatOnSave": true,
     "editor.codeActionsOnSave": {
       "source.organizeImports": true
     },
     "[python]": {
       "editor.defaultFormatter": "ms-python.black-formatter"
     }
   }
   ```

3. **Extension Conflicts**
   ```bash
   # Disable conflicting formatters
   # Check for: autopep8, yapf, other Python formatters
   # Keep only Black Formatter enabled
   ```

#### Issue: Type checking not showing errors in real-time

**Symptoms:**
- No red underlines for type errors
- MyPy errors only appear during pre-commit
- Inconsistent error highlighting

**Solutions:**

1. **MyPy Extension Configuration**
   ```json
   // .vscode/settings.json
   {
     "mypy-type-checker.importStrategy": "fromEnvironment",
     "mypy-type-checker.preferDaemon": true,
     "mypy-type-checker.args": [
       "--config-file=pyproject.toml",
       "--show-error-codes"
     ]
   }
   ```

2. **Python Analysis Settings**
   ```json
   {
     "python.analysis.typeCheckingMode": "basic",
     "python.linting.enabled": true,
     "python.linting.mypyEnabled": true
   }
   ```

### Type Annotation Issues

#### Issue: MyPy reporting errors on correct type annotations

**Symptoms:**
- "Name 'List' is not defined" errors
- "Module has no attribute" errors
- Import-related type errors

**Solutions:**

1. **Missing Type Imports**
   ```python
   # ✅ Correct - Import all needed types
   from typing import Any, Dict, List, Optional, Union, Tuple, Callable
   
   # For Python 3.9+, you can also use built-in types
   from __future__ import annotations
   
   def function(items: list[str]) -> dict[str, any]:
       pass
   ```

2. **Stub Package Installation**
   ```bash
   # Install missing stub packages
   pip install types-requests types-python-dateutil types-PyYAML
   
   # Check what stubs are needed
   mypy --install-types calendarbot/
   ```

3. **Configuration Issues**
   ```toml
   # pyproject.toml - Ensure proper MyPy configuration
   [tool.mypy]
   python_version = "3.9"
   strict = true
   warn_return_any = true
   warn_unused_configs = true
   
   # Exclude problematic modules if needed
   [[tool.mypy.overrides]]
   module = "problematic_module.*"
   ignore_missing_imports = true
   ```

### Testing Issues

#### Issue: Tests failing due to import errors

**Symptoms:**
- "ModuleNotFoundError" in tests
- Tests can't find project modules
- Inconsistent test behavior

**Solutions:**

1. **Python Path Configuration**
   ```bash
   # Ensure project root is in Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   
   # Or use pytest configuration
   # pytest.ini or pyproject.toml
   [tool.pytest.ini_options]
   pythonpath = ["."]
   testpaths = ["tests"]
   ```

2. **Virtual Environment Issues**
   ```bash
   # Verify virtual environment is active
   which python
   which pytest
   
   # Reinstall in development mode
   pip install -e .
   ```

3. **Test Structure Problems**
   ```python
   # Ensure proper imports in tests
   import sys
   from pathlib import Path
   
   # Add project root to path if needed
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root))
   
   from calendarbot.module import function
   ```

### Performance Issues

#### Issue: Development environment running slowly

**Symptoms:**
- Slow IDE response
- Long MyPy checking times
- Sluggish file operations

**Solutions:**

1. **MyPy Daemon Optimization**
   ```bash
   # Check daemon memory usage
   ps aux | grep dmypy
   
   # Restart daemon if using too much memory
   dmypy restart
   
   # Use file-level checking for large projects
   # In .vscode/settings.json
   "mypy-type-checker.reportingScope": "file"
   ```

2. **Pre-commit Cache Management**
   ```bash
   # Clear pre-commit cache
   pre-commit clean
   
   # Check cache size
   du -sh ~/.cache/pre-commit/
   
   # Remove old cached environments
   pre-commit gc
   ```

3. **VSCode Performance Tuning**
   ```json
   // .vscode/settings.json
   {
     "files.watcherExclude": {
       "**/.git/objects/**": true,
       "**/node_modules/**": true,
       "**/.venv/**": true,
       "**/venv/**": true
     },
     "search.exclude": {
       "**/venv": true,
       "**/.venv": true
     }
   }
   ```

### Git and Version Control Issues

#### Issue: Pre-commit hooks not running on commit

**Symptoms:**
- Code committed without validation
- No pre-commit output during git commit
- Inconsistent validation across team

**Solutions:**

1. **Hook Installation Verification**
   ```bash
   # Check if hooks are installed
   ls -la .git/hooks/pre-commit
   
   # Reinstall hooks
   pre-commit install
   
   # Verify hook content
   cat .git/hooks/pre-commit
   ```

2. **Git Configuration Issues**
   ```bash
   # Check git configuration
   git config --list | grep hook
   
   # Ensure hooks are enabled
   git config core.hooksPath .git/hooks
   ```

3. **Manual Hook Execution**
   ```bash
   # Test hooks manually
   pre-commit run --all-files
   
   # Run specific hook
   pre-commit run mypy --all-files
   
   # Skip hooks temporarily (emergency only)
   git commit --no-verify -m "emergency commit"
   ```

### Environment and Dependencies

#### Issue: Package import errors after setup

**Symptoms:**
- "No module named 'calendarbot'" errors
- Import errors for project modules
- Inconsistent module resolution

**Solutions:**

1. **Development Installation**
   ```bash
   # Install project in development mode
   pip install -e .
   
   # Verify installation
   pip list | grep calendarbot
   
   # Check Python path
   python -c "import sys; print(sys.path)"
   ```

2. **Virtual Environment Issues**
   ```bash
   # Recreate virtual environment
   deactivate
   rm -rf venv
   python -m venv venv
   . venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Package Configuration**
   ```python
   # Ensure setup.py or pyproject.toml is correct
   # pyproject.toml example
   [build-system]
   requires = ["setuptools>=45", "wheel"]
   build-backend = "setuptools.build_meta"
   
   [project]
   name = "calendarbot"
   packages = ["calendarbot"]
   ```

## Emergency Procedures

### Critical Bug Fix Workflow

When you need to bypass normal validation for emergency fixes:

```bash
# 1. Quick commit with fast validation
git add .
pre-commit run --config .pre-commit-config-fast.yaml
git commit -m "hotfix: critical security issue - fast validation only"

# 2. Push immediately
git push origin main

# 3. Follow up with full validation
pre-commit run --all-files
git commit --amend -m "hotfix: critical security issue - fully validated"
git push --force-with-lease origin main
```

### Complete Environment Reset

When everything is broken and you need a fresh start:

```bash
# 1. Backup current work
git stash
git branch backup-$(date +%Y%m%d-%H%M%S)

# 2. Clean environment
deactivate
rm -rf venv
rm -rf .mypy_cache
pre-commit uninstall
pre-commit clean

# 3. Fresh setup
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
pip install -e .
pre-commit install
pre-commit run --all-files

# 4. Restore work
git stash pop
```

### Recovery from Corrupted Hooks

```bash
# Remove all pre-commit artifacts
pre-commit uninstall
rm -rf ~/.cache/pre-commit/
rm -rf .git/hooks/pre-commit*

# Reinstall fresh
pre-commit install --install-hooks
pre-commit run --all-files
```

## Getting Help

### Diagnostic Information Collection

When seeking help, provide this information:

```bash
# Environment information
python --version
which python
pip list | grep -E "(mypy|black|isort|pre-commit)"

# Pre-commit status
pre-commit --version
cat .pre-commit-config.yaml | head -20

# MyPy daemon status
dmypy status

# Git hooks status
ls -la .git/hooks/
cat .git/hooks/pre-commit | head -10

# VSCode extensions
code --list-extensions | grep -E "(python|mypy|black)"
```

### Log Files and Debugging

```bash
# Enable debug mode for pre-commit
PRECOMMIT_DEBUG=1 pre-commit run --all-files

# MyPy verbose output
mypy --verbose calendarbot/

# Check VSCode logs
# Help > Toggle Developer Tools > Console
# Look for Python and extension errors
```

### Contact Points

- **Documentation**: Check this guide and other files in `documentation/development-workflow/`
- **Codebase Issues**: Review existing code patterns in `calendarbot/` for examples
- **Configuration**: Check `.vscode/settings.json`, `pyproject.toml`, and `.pre-commit-config.yaml`

## Prevention

### Proactive Monitoring

1. **Regular Maintenance**
   ```bash
   # Weekly maintenance routine
   pre-commit autoupdate
   pip list --outdated
   dmypy restart
   ```

2. **Team Synchronization**
   ```bash
   # Ensure team uses same tool versions
   pip freeze > requirements-dev.txt
   pre-commit --version >> requirements-dev.txt
   ```

3. **Configuration Backup**
   ```bash
   # Keep working configurations in version control
   git add .vscode/ .pre-commit-config*.yaml pyproject.toml
   git commit -m "config: update development environment"
   ```

By following these troubleshooting steps and prevention measures, you can maintain a smooth prevention-first development workflow even when issues arise.