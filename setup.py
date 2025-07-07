"""Enhanced setup script for Calendar Bot application with modern packaging standards."""

import os
import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def post_install_setup():
    """Post-installation setup to create configuration directories and show setup guidance."""
    try:
        # Create user configuration directories
        config_dir = Path.home() / ".config" / "calendarbot"
        data_dir = Path.home() / ".local" / "share" / "calendarbot"
        cache_dir = Path.home() / ".cache" / "calendarbot"

        # Create directories with proper permissions
        for directory in [config_dir, data_dir, cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            if hasattr(os, "chmod"):
                os.chmod(directory, 0o755)

        # Check if configuration exists
        config_file = config_dir / "config.yaml"
        if not config_file.exists():
            print("\n" + "=" * 60)
            print("📅 Calendar Bot Installation Complete!")
            print("=" * 60)
            print(f"Configuration directory: {config_dir}")
            print(f"Data directory: {data_dir}")
            print(f"Cache directory: {cache_dir}")
            print("\n🔧 Next Steps:")
            print("1. Run 'calendarbot --setup' to configure your calendar")
            print("2. Or manually create config.yaml in the config directory")
            print("3. Run 'calendarbot --help' to see all available options")
            print("\n📖 Documentation:")
            print("- Configuration guide: See config/config.yaml.example")
            print("- Usage examples: Run 'calendarbot --help'")
            print("=" * 60)

    except Exception as e:
        print(f"Warning: Post-install setup failed: {e}")
        print("You may need to create configuration directories manually.")


class PostInstallCommand(install):
    """Custom install command with post-install setup."""

    def run(self):
        install.run(self)
        post_install_setup()


class PostDevelopCommand(develop):
    """Custom develop command with post-install setup."""

    def run(self):
        develop.run(self)
        post_install_setup()


# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements with enhanced parsing
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
dev_requirements = []

if requirements_file.exists():
    content = requirements_file.read_text().strip()
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Separate development dependencies
        if "pytest" in line or "development" in line.lower() or "testing" in line.lower():
            dev_requirements.append(line)
        else:
            requirements.append(line)

# Enhanced metadata for better PyPI presence
setup(
    name="calendarbot",
    version="1.0.0",
    description="ICS Calendar Display Bot for Raspberry Pi with e-ink display and web interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CalendarBot Team",
    author_email="support@calendarbot.local",
    url="https://github.com/calendarbot/calendarbot",
    project_urls={
        "Documentation": "https://github.com/calendarbot/calendarbot#readme",
        "Source": "https://github.com/calendarbot/calendarbot",
        "Tracker": "https://github.com/calendarbot/calendarbot/issues",
    },
    # Package configuration
    packages=find_packages(exclude=["tests*", "docs*"]),
    include_package_data=True,
    # Dependencies
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements
        + [
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "rpi": [
            "RPi.GPIO>=0.7.1",
            "spidev>=3.5",
        ],
    },
    # Python version requirement
    python_requires=">=3.8",
    # Enhanced classifiers for better discoverability
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: System :: Hardware",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Communications",
        "Framework :: AsyncIO",
    ],
    # Enhanced keywords for better searchability
    keywords="calendar ics microsoft365 outlook google-calendar raspberry-pi e-ink display web-interface async",
    # Entry points
    entry_points={
        "console_scripts": [
            "calendarbot=calendarbot.__main__:main",  # Points to main function in package
        ],
    },
    # Package data
    package_data={
        "calendarbot": [
            "py.typed",
            "web/static/*.css",
            "web/static/*.js",
            "web/templates/*.html",
        ],
        "config": [
            "config.yaml.example",
        ],
    },
    # Additional data files
    data_files=[
        ("share/doc/calendarbot", ["README.md", "INSTALL.md", "USAGE.md"]),
        ("share/calendarbot/config", ["config/config.yaml.example"]),
    ],
    # Custom install commands
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    },
    # Build configuration
    zip_safe=False,
    # Platform-specific requirements
    platforms=["linux", "macos"],
)
