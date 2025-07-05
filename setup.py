"""Setup script for Calendar Bot application."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    # Filter out empty lines and comments
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="calendarbot",
    version="1.0.0",
    description="Microsoft 365 Calendar Display Bot for Raspberry Pi with e-ink display",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CalendarBot Team",
    author_email="support@calendarbot.local",
    url="https://github.com/calendarbot/calendarbot",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: System :: Hardware",
    ],
    keywords="calendar microsoft365 raspberry-pi e-ink display",
    entry_points={
        "console_scripts": [
            "calendarbot=calendarbot.main:main",
        ],
    },
    package_data={
        "calendarbot": ["py.typed"],
    },
    zip_safe=False,
)