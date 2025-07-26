#!/usr/bin/env python3
"""Setup script for calendarbot_epaper package."""

import os

from setuptools import find_packages, setup  # type: ignore[import]

# Get version from __init__.py
with open(os.path.join(os.path.dirname(__file__), "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "0.1.0"

# Get long description from README.md
long_description = """
# CalendarBot e-Paper Display Integration

This package provides integration with Waveshare e-Paper displays for the CalendarBot project.
It supports the Waveshare 4.2inch e-Paper Module (B) v2 (400x300 pixels, black/white/red).

## Features

- Display abstraction layer for e-Paper displays
- Waveshare e-Paper display driver
- Rendering utilities for text optimization and refresh management
- Image processing utilities for e-Paper displays
"""

setup(
    name="calendarbot_epaper",
    version=version,
    description="CalendarBot e-Paper display integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CalendarBot Team",
    author_email="info@calendarbot.example.com",
    url="https://github.com/calendarbot/calendarbot_epaper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "RPi.GPIO>=0.7.0",
        "spidev>=3.5",
        "Pillow>=8.0.0",
        "numpy>=1.19.0",
        "typing-extensions>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=20.8b1",
            "isort>=5.0.0",
            "mypy>=0.800",
            "pylint>=2.5.0",
        ],
    },
)
