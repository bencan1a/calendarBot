# Pre-commit Hook Profiles

## Overview

This project uses two pre-commit configurations to support different development scenarios:

- **Standard Profile** (`.pre-commit-config.yaml`): Full validation suite for comprehensive quality assurance
- **Fast Profile** (`.pre-commit-config-fast.yaml`): Essential validation for rapid development cycles

## Standard Profile (Default)

### Configuration: `.pre-commit-config.yaml`

#### Validation Stages

1. **File Syntax Validation**
   - YAML, JSON, TOML syntax checking
   - Python AST validation
   - Merge conflict detection
   - Large file prevention

2. **Security Scanning**
   - Bandit vulnerability detection
   - Secret scanning
   - Dependency security checks

3. **Type Checking**
   - MyPy static analysis
   - Smart file selection (only changed files)
   - Incremental type checking

4. **Code Quality**
   - Black code formatting
   - Import sorting (isort)
   - Line length enforcement
   - Documentation requirements

5. **Testing**
   - Smart test selection based on file changes
   - Parallel test execution
   - Coverage requirements

### Usage

```bash
# Install standard hooks (default)
pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Run on specific files
pre-commit run --files calendarbot/features/new_feature.py

# Run specific hook
pre-commit run mypy --all-files
```

### Performance Characteristics

- **Full validation**: 30-45 seconds (all files)
- **Smart mode**: 15-25 seconds (changed files only)
- **Security only**: 10-15 seconds
- **Type checking**: 5-10 seconds (incremental)

### When to Use

✅ **Recommended for:**
- Regular feature development
- Code reviews and pull requests
- Release preparation
- CI/CD pipeline execution
- Final validation before merges

❌ **Not ideal for:**
- Rapid prototyping with frequent commits
- Emergency bug fixes requiring immediate commits
- Intensive refactoring sessions
- Learning/experimental development

## Fast Profile (Emergency)

### Configuration: `.pre-commit-config-fast.yaml`

#### Essential Checks Only

1. **Critical Syntax Validation**
   - YAML, JSON, TOML syntax
   - Python AST parsing
   - Merge conflict detection

2. **Basic Code Quality**
   - Black formatting (with `--fast` flag)
   - Import sorting
   - File size limits

3. **Immediate Feedback**
   - Under 1 second execution time
   - Fail-fast on critical errors
   - Minimal but essential validation

### Usage

```bash
# Temporary switch to fast profile
pre-commit run --config .pre-commit-config-fast.yaml

# Install fast profile permanently (emergency mode)
pre-commit uninstall
PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml pre-commit install

# Switch back to standard profile
pre-commit uninstall
pre-commit install
```

### Performance Characteristics

- **Total execution**: ~0.67 seconds
- **Syntax validation**: ~0.2 seconds
- **Code formatting**: ~0.3 seconds
- **File checks**: ~0.17 seconds

### When to Use

✅ **Ideal for:**
- Emergency bug fixes
- Rapid prototyping sessions
- Intensive refactoring with frequent commits
- Learning new features/APIs
- When standard profile blocks workflow

❌ **Not recommended for:**
- Production releases
- Code reviews
- Security-sensitive changes
- Final implementation validation

## Profile Comparison

| Feature | Standard Profile | Fast Profile |
|---------|------------------|---------------|
| **Execution Time** | 30-45s (full) / 15-25s (smart) | ~0.67s |
| **Type Checking** | Full MyPy analysis | None |
| **Security Scanning** | Bandit + secret detection | None |
| **Testing** | Smart test selection | None |
| **Code Quality** | Comprehensive | Basic formatting only |
| **Use Case** | Production development | Emergency/prototype |

## Smart Hook Features

### File Change Detection

The standard profile includes intelligent file tracking:

```bash
# Only runs relevant tests for changed files
# Example: If you modify calendarbot/auth.py
# Only runs: tests/test_auth.py and related integration tests
```

### Incremental Validation

```bash
# MyPy daemon tracks file changes
# Only re-checks modified files and dependencies
# Dramatically reduces type checking time
```

### Parallel Execution

```bash
# Multiple hooks run simultaneously when possible
# Security scanning + formatting can run in parallel
# Test suites use multiple CPU cores
```

## Configuration Management

### Environment Variables

```bash
# Override default config
export PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml

# Skip specific hooks temporarily
export SKIP=mypy,bandit

# Enable debug mode
export PRECOMMIT_DEBUG=1
```

### Git Hook Integration

```bash
# Check current hook configuration
cat .git/hooks/pre-commit

# Verify which config is active
grep -r "config" .git/hooks/

# Manual hook execution
.git/hooks/pre-commit
```

## Advanced Usage

### Custom Hook Combinations

```bash
# Run only type checking from standard profile
pre-commit run mypy --config .pre-commit-config.yaml

# Run fast formatting + standard security
pre-commit run black isort --config .pre-commit-config-fast.yaml
pre-commit run bandit --config .pre-commit-config.yaml
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run pre-commit (standard)
  run: pre-commit run --all-files
  
- name: Run pre-commit (fast for PR validation)
  run: pre-commit run --config .pre-commit-config-fast.yaml --all-files
  if: github.event_name == 'pull_request'
```

### Profile Switching Scripts

Create `scripts/dev-mode.sh`:
```bash
#!/bin/bash
echo "Switching to fast development mode..."
pre-commit uninstall
PRECOMMIT_CONFIG=.pre-commit-config-fast.yaml pre-commit install
echo "✅ Fast mode enabled. Use 'scripts/prod-mode.sh' to switch back."
```

Create `scripts/prod-mode.sh`:
```bash
#!/bin/bash
echo "Switching to standard production mode..."
pre-commit uninstall
pre-commit install
echo "✅ Standard mode enabled."
```

## Troubleshooting

### Hook Failures

**Problem**: Standard profile too slow
```bash
# Solution: Use smart mode (default) or fast profile
git add specific_files.py
git commit -m "message"  # Only runs hooks on changed files

# Or switch to fast profile temporarily
pre-commit run --config .pre-commit-config-fast.yaml
```

**Problem**: Fast profile not catching issues
```bash
# Solution: Run standard validation manually before important commits
pre-commit run --all-files  # Full validation
git commit -m "message"     # Fast validation only
```

### Configuration Issues

**Problem**: Wrong profile active
```bash
# Check current configuration
pre-commit --version
cat .git/hooks/pre-commit | grep config

# Reset to standard
pre-commit uninstall
pre-commit install
```

**Problem**: Hooks not running
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install --install-hooks

# Verify installation
pre-commit run --all-files
```

## Best Practices

### Development Workflow

1. **Start with standard profile** for new features
2. **Switch to fast profile** during intensive development
3. **Return to standard profile** before code review
4. **Always use standard profile** for final commits

### Team Guidelines

- **Document profile switches** in commit messages
- **Use fast profile sparingly** - not for production code
- **Run full validation** before pushing to shared branches
- **Include profile choice** in development documentation

### Emergency Procedures

```bash
# Emergency commit workflow
git add .
pre-commit run --config .pre-commit-config-fast.yaml
git commit -m "emergency: critical bug fix - fast validation only"

# Follow up with full validation
pre-commit run --all-files
git commit --amend -m "emergency: critical bug fix - validated"
```

## Next Steps

1. Choose appropriate profile for your current development phase
2. Set up profile switching scripts for easy transitions
3. Learn [Roocode Instructions](./roocode-instructions.md) for code quality enforcement
4. Understand [Testing Strategy](./testing-strategy.md) for comprehensive validation