#!/usr/bin/env python3
"""Development environment setup script for Calendar Bot."""

import argparse
import json
import logging
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DevelopmentSetup:
    """Development environment setup and management."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.venv_path = project_root / "venv"
        self.config_path = project_root / "config"

        # Development tools configuration
        self.dev_tools = {
            "black": ">=23.0.0",
            "isort": ">=5.12.0",
            "mypy": ">=1.0.0",
            "pytest": ">=7.4.0",
            "pytest-asyncio": ">=0.21.0",
            "pytest-cov": ">=4.0.0",
            "pre-commit": ">=3.0.0",
            "flake8": ">=6.0.0",
            "bandit": ">=1.7.0",
        }

        logger.info(f"Development setup for: {project_root}")

    def run_command(
        self,
        command: List[str],
        check: bool = True,
        capture_output: bool = False,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess:
        """Run a command with logging."""
        if cwd is None:
            cwd = self.project_root

        logger.debug(f"Running: {' '.join(command)} (cwd: {cwd})")

        try:
            result = subprocess.run(
                command, check=check, capture_output=capture_output, text=True, cwd=cwd
            )

            if capture_output and result.stdout:
                logger.debug(f"Output: {result.stdout.strip()}")

            return result

        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            if capture_output and e.stderr:
                logger.error(f"Error: {e.stderr.strip()}")
            raise

    def create_virtual_environment(self, force: bool = False) -> bool:
        """Create Python virtual environment for development."""
        logger.info("Setting up Python virtual environment")

        if self.venv_path.exists():
            if force:
                logger.info("Removing existing virtual environment")
                import shutil

                shutil.rmtree(self.venv_path)
            else:
                logger.info("Virtual environment already exists")
                return True

        try:
            # Create virtual environment
            logger.info(f"Creating virtual environment: {self.venv_path}")
            venv.create(self.venv_path, with_pip=True)

            # Upgrade pip
            pip_path = self.get_pip_path()
            self.run_command([str(pip_path), "install", "--upgrade", "pip"])

            logger.info("Virtual environment created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create virtual environment: {e}")
            return False

    def get_pip_path(self) -> Path:
        """Get pip executable path."""
        if os.name == "nt":  # Windows
            return self.venv_path / "Scripts" / "pip.exe"
        else:  # Unix/Linux/macOS
            return self.venv_path / "bin" / "pip"

    def get_python_path(self) -> Path:
        """Get Python executable path."""
        if os.name == "nt":  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix/Linux/macOS
            return self.venv_path / "bin" / "python"

    def install_dependencies(self) -> bool:
        """Install project and development dependencies."""
        logger.info("Installing project dependencies")

        pip_path = self.get_pip_path()

        try:
            # Install main requirements
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                logger.info("Installing main requirements")
                self.run_command([str(pip_path), "install", "-r", str(requirements_file)])

            # Install development tools
            logger.info("Installing development tools")
            for tool, version in self.dev_tools.items():
                self.run_command([str(pip_path), "install", f"{tool}{version}"])

            # Install project in editable mode
            logger.info("Installing project in editable mode")
            self.run_command([str(pip_path), "install", "-e", "."])

            logger.info("Dependencies installed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False

    def setup_pre_commit(self) -> bool:
        """Setup pre-commit hooks."""
        logger.info("Setting up pre-commit hooks")

        # Create pre-commit config if it doesn't exist
        precommit_config = self.project_root / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            logger.info("Creating pre-commit configuration")
            config_content = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements
      - id: check-docstring-first

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-python-dateutil]
"""

            with open(precommit_config, "w") as f:
                f.write(config_content)

        try:
            # Install pre-commit hooks
            python_path = self.get_python_path()
            self.run_command([str(python_path), "-m", "pre_commit", "install"])

            logger.info("Pre-commit hooks installed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup pre-commit: {e}")
            return False

    def create_development_config(self) -> bool:
        """Create development configuration files."""
        logger.info("Creating development configuration")

        try:
            # Create development config directory
            dev_config_dir = self.project_root / "config" / "development"
            dev_config_dir.mkdir(parents=True, exist_ok=True)

            # Create development config file
            dev_config_file = dev_config_dir / "config.yaml"
            if not dev_config_file.exists():
                dev_config_content = """# Development Configuration for Calendar Bot
# This file is for development/testing purposes

# ICS Calendar Configuration
ics:
  url: "https://calendar.google.com/calendar/ical/YOUR_CALENDAR_ID/basic.ics"
  auth_type: "none"
  verify_ssl: true
  timeout: 30

# Application Settings
app_name: "CalendarBot-Dev"
refresh_interval: 60        # Faster refresh for development
cache_ttl: 600             # Shorter cache for development

# Logging Configuration (verbose for development)
log_level: "DEBUG"
log_file: "logs/calendarbot-dev.log"

# Display Settings
display_enabled: true
display_type: "console"

# Web Interface Settings
web:
  enabled: true
  port: 8080
  host: "127.0.0.1"        # Localhost only for development
  theme: "eink-rpi"
  auto_refresh: 30         # Faster refresh for development

# Raspberry Pi E-ink Settings
rpi:
  enabled: false
  display_width: 480
  display_height: 800
  refresh_mode: "partial"
  auto_theme: true

# Development-specific settings
development:
  hot_reload: true
  debug_mode: true
  test_data_enabled: true
"""

                with open(dev_config_file, "w") as f:
                    f.write(dev_config_content)

                logger.info(f"Development config created: {dev_config_file}")

            # Create testing config
            test_config_file = dev_config_dir / "test_config.yaml"
            if not test_config_file.exists():
                test_config_content = """# Test Configuration for Calendar Bot
# This file is used during automated testing

# ICS Calendar Configuration (mock for testing)
ics:
  url: "http://localhost:8080/test/calendar.ics"
  auth_type: "none"
  verify_ssl: false
  timeout: 5

# Application Settings
app_name: "CalendarBot-Test"
refresh_interval: 10       # Very fast for testing
cache_ttl: 60             # Very short cache for testing

# Logging Configuration
log_level: "INFO"
log_file: null            # No file logging during tests

# Display Settings
display_enabled: false    # Disable display during tests
display_type: "console"

# Web Interface Settings
web:
  enabled: false          # Disabled during tests
  port: 8081             # Different port to avoid conflicts
  host: "127.0.0.1"
  theme: "eink-rpi"
  auto_refresh: 10

# Testing-specific settings
testing:
  mock_data: true
  fast_mode: true
  skip_network: false
"""

                with open(test_config_file, "w") as f:
                    f.write(test_config_content)

                logger.info(f"Test config created: {test_config_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to create development config: {e}")
            return False

    def create_development_scripts(self) -> bool:
        """Create development helper scripts."""
        logger.info("Creating development scripts")

        try:
            scripts_dir = self.project_root / "scripts" / "dev"
            scripts_dir.mkdir(parents=True, exist_ok=True)

            # Create development runner script
            dev_run_script = scripts_dir / "run_dev.py"
            dev_run_content = """#!/usr/bin/env python3
\"\"\"Development runner script for Calendar Bot.\"\"\"

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    \"\"\"Run Calendar Bot in development mode.\"\"\"
    os.environ['CALENDARBOT_CONFIG'] = str(project_root / "config" / "development" / "config.yaml")

    # Run with development configuration
    cmd = [sys.executable, "-m", "calendarbot", "--web", "--verbose"]

    print(f"Starting Calendar Bot in development mode...")
    print(f"Config: {os.environ.get('CALENDARBOT_CONFIG')}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\\nDevelopment server stopped")

if __name__ == "__main__":
    main()
"""

            with open(dev_run_script, "w") as f:
                f.write(dev_run_content)
            dev_run_script.chmod(0o755)

            # Create test runner script
            test_run_script = scripts_dir / "run_tests.py"
            test_run_content = """#!/usr/bin/env python3
\"\"\"Test runner script for Calendar Bot.\"\"\"

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    \"\"\"Run Calendar Bot tests.\"\"\"
    os.environ['CALENDARBOT_CONFIG'] = str(project_root / "config" / "development" / "test_config.yaml")

    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=calendarbot",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ]

    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    print(f"Running Calendar Bot tests...")
    print(f"Config: {os.environ.get('CALENDARBOT_CONFIG')}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    subprocess.run(cmd, cwd=project_root)

if __name__ == "__main__":
    main()
"""

            with open(test_run_script, "w") as f:
                f.write(test_run_content)
            test_run_script.chmod(0o755)

            # Create lint script
            lint_script = scripts_dir / "lint.py"
            lint_content = """#!/usr/bin/env python3
\"\"\"Code quality checker for Calendar Bot.\"\"\"

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent

def run_tool(name, cmd):
    \"\"\"Run a development tool.\"\"\"
    print(f"\\n{'='*60}")
    print(f"Running {name}")
    print('='*60)

    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        if result.returncode == 0:
            print(f"✅ {name} passed")
        else:
            print(f"❌ {name} failed")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return False

def main():
    \"\"\"Run all code quality tools.\"\"\"
    tools = [
        ("Black (code formatting)", [sys.executable, "-m", "black", ".", "--check"]),
        ("isort (import sorting)", [sys.executable, "-m", "isort", ".", "--check-only"]),
        ("Flake8 (style guide)", [sys.executable, "-m", "flake8", "."]),
        ("MyPy (type checking)", [sys.executable, "-m", "mypy", "calendarbot"]),
        ("Bandit (security)", [sys.executable, "-m", "bandit", "-r", "calendarbot"]),
    ]

    results = []
    for name, cmd in tools:
        success = run_tool(name, cmd)
        results.append((name, success))

    # Summary
    print(f"\\n{'='*60}")
    print("Code Quality Summary")
    print('='*60)

    passed = 0
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
        if success:
            passed += 1

    print(f"\\n🎯 {passed}/{len(results)} tools passed")

    if passed == len(results):
        print("🎉 All code quality checks passed!")
        return 0
    else:
        print("⚠️  Some code quality checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""

            with open(lint_script, "w") as f:
                f.write(lint_content)
            lint_script.chmod(0o755)

            logger.info("Development scripts created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create development scripts: {e}")
            return False

    def create_vscode_config(self) -> bool:
        """Create VS Code configuration for development."""
        logger.info("Creating VS Code configuration")

        try:
            vscode_dir = self.project_root / ".vscode"
            vscode_dir.mkdir(exist_ok=True)

            # Settings
            settings_file = vscode_dir / "settings.json"
            settings_content = {
                "python.defaultInterpreterPath": str(self.get_python_path()),
                "python.linting.enabled": True,
                "python.linting.flake8Enabled": True,
                "python.linting.mypyEnabled": True,
                "python.formatting.provider": "black",
                "python.sortImports.path": str(self.venv_path / "bin" / "isort"),
                "editor.formatOnSave": True,
                "editor.codeActionsOnSave": {"source.organizeImports": True},
                "files.exclude": {
                    "**/__pycache__": True,
                    "**/*.pyc": True,
                    ".mypy_cache": True,
                    ".pytest_cache": True,
                    "htmlcov": True,
                },
            }

            with open(settings_file, "w") as f:
                json.dump(settings_content, f, indent=4)

            # Launch configuration
            launch_file = vscode_dir / "launch.json"
            launch_content = {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "Calendar Bot - Interactive",
                        "type": "python",
                        "request": "launch",
                        "module": "calendarbot",
                        "args": ["--interactive", "--verbose"],
                        "console": "integratedTerminal",
                        "env": {
                            "CALENDARBOT_CONFIG": str(
                                self.project_root / "config" / "development" / "config.yaml"
                            )
                        },
                    },
                    {
                        "name": "Calendar Bot - Web",
                        "type": "python",
                        "request": "launch",
                        "module": "calendarbot",
                        "args": ["--web", "--verbose", "--auto-open"],
                        "console": "integratedTerminal",
                        "env": {
                            "CALENDARBOT_CONFIG": str(
                                self.project_root / "config" / "development" / "config.yaml"
                            )
                        },
                    },
                    {
                        "name": "Calendar Bot - Test Mode",
                        "type": "python",
                        "request": "launch",
                        "module": "calendarbot",
                        "args": ["--test-mode", "--verbose"],
                        "console": "integratedTerminal",
                        "env": {
                            "CALENDARBOT_CONFIG": str(
                                self.project_root / "config" / "development" / "test_config.yaml"
                            )
                        },
                    },
                ],
            }

            with open(launch_file, "w") as f:
                json.dump(launch_content, f, indent=4)

            # Tasks
            tasks_file = vscode_dir / "tasks.json"
            tasks_content = {
                "version": "2.0.0",
                "tasks": [
                    {
                        "label": "Run Tests",
                        "type": "shell",
                        "command": str(self.get_python_path()),
                        "args": ["scripts/dev/run_tests.py"],
                        "group": "test",
                        "presentation": {
                            "echo": True,
                            "reveal": "always",
                            "focus": False,
                            "panel": "shared",
                        },
                    },
                    {
                        "label": "Code Quality Check",
                        "type": "shell",
                        "command": str(self.get_python_path()),
                        "args": ["scripts/dev/lint.py"],
                        "group": "build",
                        "presentation": {
                            "echo": True,
                            "reveal": "always",
                            "focus": False,
                            "panel": "shared",
                        },
                    },
                    {
                        "label": "Format Code",
                        "type": "shell",
                        "command": str(self.get_python_path()),
                        "args": ["-m", "black", "."],
                        "group": "build",
                    },
                ],
            }

            with open(tasks_file, "w") as f:
                json.dump(tasks_content, f, indent=4)

            logger.info("VS Code configuration created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create VS Code config: {e}")
            return False

    def setup_development_environment(self, force_venv: bool = False) -> bool:
        """Setup complete development environment."""
        logger.info("Setting up Calendar Bot development environment")

        steps = [
            ("Creating virtual environment", lambda: self.create_virtual_environment(force_venv)),
            ("Installing dependencies", self.install_dependencies),
            ("Setting up pre-commit hooks", self.setup_pre_commit),
            ("Creating development config", self.create_development_config),
            ("Creating development scripts", self.create_development_scripts),
            ("Creating VS Code config", self.create_vscode_config),
        ]

        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            try:
                if not step_func():
                    logger.error(f"Setup failed at step: {step_name}")
                    return False
            except Exception as e:
                logger.error(f"Setup failed at step '{step_name}': {e}")
                return False

        logger.info("Development environment setup completed successfully!")
        self._show_development_instructions()
        return True

    def _show_development_instructions(self):
        """Show post-setup development instructions."""
        print("\n" + "=" * 60)
        print("🛠️  Calendar Bot Development Environment Ready!")
        print("=" * 60)
        print(f"📁 Project root: {self.project_root}")
        print(f"🐍 Virtual environment: {self.venv_path}")
        print(f"⚙️  Development config: {self.project_root}/config/development/")

        print("\n🚀 Quick Start:")
        print("   source venv/bin/activate          # Activate virtual environment")
        print("   python scripts/dev/run_dev.py     # Start development server")
        print("   python scripts/dev/run_tests.py   # Run tests")
        print("   python scripts/dev/lint.py        # Run code quality checks")

        print("\n🔧 Development Commands:")
        print("   python -m calendarbot --web --verbose     # Web interface with debug")
        print("   python -m calendarbot --test-mode         # Run validation tests")
        print("   python -m calendarbot --setup             # Setup wizard")

        print("\n📝 Code Quality:")
        print("   black .                            # Format code")
        print("   isort .                            # Sort imports")
        print("   mypy calendarbot                   # Type checking")
        print("   pytest --cov=calendarbot          # Run tests with coverage")

        print("\n📚 Configuration:")
        print("   config/development/config.yaml     # Development settings")
        print("   config/development/test_config.yaml # Test settings")
        print("   .vscode/                           # VS Code configuration")
        print("=" * 60)


def main():
    """Main development setup entry point."""
    parser = argparse.ArgumentParser(description="Calendar Bot Development Environment Setup")

    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Project root directory",
    )

    parser.add_argument(
        "--force-venv", action="store_true", help="Force recreate virtual environment"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate project root
    if not args.project_root.exists():
        logger.error(f"Project root does not exist: {args.project_root}")
        return 1

    # Setup development environment
    dev_setup = DevelopmentSetup(args.project_root)

    try:
        success = dev_setup.setup_development_environment(args.force_venv)
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Setup cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
